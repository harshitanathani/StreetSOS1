from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

from db import get_connection
from decorators import roles_required
from services import ISSUE_TYPES, log_status, refresh_sla_overdue, valid_email

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/dashboard')
@roles_required('admin')
def dashboard():
    refresh_sla_overdue()
    filters = {
        'search': request.args.get('search', '').strip(),
        'category': request.args.get('category', '').strip(),
        'severity': request.args.get('severity', '').strip(),
        'status': request.args.get('status', '').strip(),
        'overdue': request.args.get('overdue', '').strip(),
    }

    clauses = []
    params = []
    if filters['search']:
        clauses.append('(c.public_id LIKE %s OR c.area LIKE %s OR citizen.name LIKE %s)')
        term = f"%{filters['search']}%"
        params.extend([term, term, term])
    if filters['category']:
        clauses.append('c.category = %s')
        params.append(filters['category'])
    if filters['severity']:
        clauses.append('c.severity_label = %s')
        params.append(filters['severity'])
    if filters['status']:
        clauses.append('c.status = %s')
        params.append(filters['status'])
    if filters['overdue'] == '1':
        clauses.append("c.is_escalated = 1 AND c.status NOT IN ('Resolved','Verified')")

    where = ('WHERE ' + ' AND '.join(clauses)) if clauses else ''
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            f'''
            SELECT c.*, citizen.name AS citizen_name,
                   worker.name AS worker_name, worker.department AS worker_department,
                   TIMESTAMPDIFF(HOUR, c.created_at, NOW()) AS age_hours
            FROM complaints c
            JOIN users citizen ON citizen.user_id = c.citizen_id
            LEFT JOIN users worker ON worker.user_id = c.assigned_worker_id
            {where}
            ORDER BY c.is_escalated DESC, c.severity_score DESC, c.created_at ASC
            ''',
            tuple(params),
        )
        complaints = cursor.fetchall()

        cursor.execute(
            '''
            SELECT user_id, name, email, department
            FROM users
            WHERE role='worker' AND is_active=1
            ORDER BY department, name
            '''
        )
        workers = cursor.fetchall()

        cursor.execute(
            '''
            SELECT COUNT(*) total,
                   SUM(status IN ('Reported','Assigned','In Progress')) active,
                   SUM(severity_label IN ('Critical','High') AND status NOT IN ('Resolved','Verified')) priority,
                   SUM(is_escalated=1 AND status NOT IN ('Resolved','Verified')) overdue,
                   SUM(status='Verified') verified
            FROM complaints
            '''
        )
        stats = cursor.fetchone()
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

    return render_template(
        'admin_dashboard.html',
        complaints=complaints,
        workers=workers,
        filters=filters,
        stats=stats,
        categories=list(ISSUE_TYPES.keys()),
    )


@admin_bp.route('/complaints/<int:complaint_id>/assign', methods=['POST'])
@roles_required('admin')
def assign_worker(complaint_id):
    worker_id = request.form.get('worker_id', '').strip()
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM complaints WHERE complaint_id=%s', (complaint_id,))
        complaint = cursor.fetchone()
        if not complaint:
            return render_template('404.html'), 404
        if complaint['status'] in ('Resolved', 'Verified'):
            flash('Resolved or verified complaints cannot be reassigned.', 'warning')
            return redirect(url_for('admin.dashboard'))

        cursor.execute(
            "SELECT user_id, name, department FROM users WHERE user_id=%s AND role='worker' AND is_active=1",
            (worker_id,),
        )
        worker = cursor.fetchone()
        if not worker:
            flash('Select a valid worker.', 'danger')
            return redirect(url_for('admin.dashboard'))
        if worker['department'] not in (complaint['category'], 'General'):
            flash(f"{worker['name']} belongs to {worker['department']}; choose a {complaint['category']} or General worker.", 'danger')
            return redirect(url_for('admin.dashboard'))

        old_status = complaint['status']
        new_status = 'Assigned' if old_status == 'Reported' else old_status
        cursor.execute(
            '''
            UPDATE complaints
            SET assigned_worker_id=%s,
                status=%s,
                assigned_at=COALESCE(assigned_at, NOW())
            WHERE complaint_id=%s
            ''',
            (worker_id, new_status, complaint_id),
        )
        note = f"Assigned to {worker['name']} ({worker['department']} department)."
        log_status(conn, complaint_id, old_status, new_status, session['user_id'], note)
        conn.commit()
        flash('Worker assignment updated successfully.', 'success')
    except Exception:
        if conn:
            conn.rollback()
        flash('Could not assign the worker.', 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/workers', methods=['GET', 'POST'])
@roles_required('admin')
def workers():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        department = request.form.get('department', '').strip()
        password = request.form.get('password', '')
        valid_departments = list(ISSUE_TYPES.keys()) + ['General']

        if len(name) < 2:
            flash('Enter the worker name.', 'danger')
        elif not valid_email(email):
            flash('Enter a valid worker email.', 'danger')
        elif department not in valid_departments:
            flash('Choose a valid department.', 'danger')
        elif len(password) < 6:
            flash('Temporary password must contain at least 6 characters.', 'danger')
        else:
            conn = cursor = None
            try:
                conn = get_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute('SELECT user_id FROM users WHERE email=%s', (email,))
                if cursor.fetchone():
                    flash('That email is already in use.', 'danger')
                else:
                    cursor.execute(
                        '''
                        INSERT INTO users (name,email,password_hash,role,department)
                        VALUES (%s,%s,%s,'worker',%s)
                        ''',
                        (name, email, generate_password_hash(password), department),
                    )
                    conn.commit()
                    flash('Worker account created.', 'success')
                    return redirect(url_for('admin.workers'))
            finally:
                if cursor:
                    cursor.close()
                if conn and conn.is_connected():
                    conn.close()

    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            '''
            SELECT u.user_id, u.name, u.email, u.department, u.is_active, u.created_at,
                   COUNT(c.complaint_id) AS assigned_count,
                   SUM(c.status IN ('Assigned','In Progress')) AS active_count
            FROM users u
            LEFT JOIN complaints c ON c.assigned_worker_id = u.user_id
            WHERE u.role='worker'
            GROUP BY u.user_id
            ORDER BY u.department, u.name
            '''
        )
        worker_rows = cursor.fetchall()
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

    return render_template('manage_workers.html', workers=worker_rows, departments=list(ISSUE_TYPES.keys()) + ['General'])


@admin_bp.route('/workers/<int:user_id>/toggle', methods=['POST'])
@roles_required('admin')
def toggle_worker(user_id):
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET is_active = NOT is_active WHERE user_id=%s AND role='worker'",
            (user_id,),
        )
        conn.commit()
        flash('Worker account status updated.', 'success')
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
    return redirect(url_for('admin.workers'))
