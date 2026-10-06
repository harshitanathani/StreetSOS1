from datetime import datetime, timedelta

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from db import get_connection
from decorators import login_required, roles_required
from services import (
    ISSUE_TYPES,
    LOCATION_TYPES,
    badge_for_verified,
    calculate_severity,
    generate_public_id,
    log_status,
    refresh_sla_overdue,
    remove_image,
    save_image,
)

citizen_bp = Blueprint('citizen', __name__)


def _leaderboard_rows():
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            '''
            SELECT u.user_id, u.name,
                   SUM(CASE WHEN c.status = 'Verified' THEN 1 ELSE 0 END) AS verified_count
            FROM users u
            LEFT JOIN complaints c ON c.citizen_id = u.user_id
            WHERE u.role = 'citizen' AND u.is_active = 1
            GROUP BY u.user_id, u.name
            ORDER BY verified_count DESC, u.name ASC
            '''
        )
        rows = cursor.fetchall()
        for index, row in enumerate(rows, start=1):
            row['rank'] = index
            row['badge'] = badge_for_verified(int(row['verified_count'] or 0))['name']
        return rows
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@citizen_bp.route('/citizen/dashboard')
@roles_required('citizen')
def dashboard():
    refresh_sla_overdue()
    status_filter = request.args.get('status', '').strip()
    category_filter = request.args.get('category', '').strip()

    clauses = ['citizen_id = %s']
    params = [session['user_id']]
    if status_filter:
        clauses.append('status = %s')
        params.append(status_filter)
    if category_filter:
        clauses.append('category = %s')
        params.append(category_filter)

    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            f'''
            SELECT *, TIMESTAMPDIFF(HOUR, created_at, NOW()) AS age_hours
            FROM complaints
            WHERE {' AND '.join(clauses)}
            ORDER BY is_escalated DESC, severity_score DESC, created_at DESC
            ''',
            tuple(params),
        )
        complaints = cursor.fetchall()

        cursor.execute(
            '''
            SELECT
                COUNT(*) AS total,
                SUM(status IN ('Reported','Assigned','In Progress')) AS active,
                SUM(status = 'Resolved') AS resolved,
                SUM(status = 'Verified') AS verified,
                SUM(is_escalated = 1 AND status NOT IN ('Resolved','Verified')) AS overdue
            FROM complaints WHERE citizen_id = %s
            ''',
            (session['user_id'],),
        )
        stats = cursor.fetchone()
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

    leaderboard = _leaderboard_rows()
    me = next((row for row in leaderboard if row['user_id'] == session['user_id']), None)
    badge = badge_for_verified(int((me or {}).get('verified_count') or 0))

    return render_template(
        'citizen_dashboard.html',
        complaints=complaints,
        stats=stats,
        rank=(me or {}).get('rank'),
        badge=badge,
        status_filter=status_filter,
        category_filter=category_filter,
    )


@citizen_bp.route('/complaints/new', methods=['GET', 'POST'])
@roles_required('citizen')
def new_complaint():
    if request.method == 'POST':
        category = request.form.get('category', '').strip()
        issue_type = request.form.get('issue_type', '').strip()
        location_type = request.form.get('location_type', '').strip()
        description = request.form.get('description', '').strip()
        area = request.form.get('area', '').strip()
        street = request.form.get('street', '').strip()
        landmark = request.form.get('landmark', '').strip()
        latitude = request.form.get('latitude', '').strip()
        longitude = request.form.get('longitude', '').strip()
        image = request.files.get('image')

        if category not in ISSUE_TYPES:
            flash('Select a valid complaint category.', 'danger')
            return render_template('complaint_form.html', issue_types=ISSUE_TYPES, location_types=LOCATION_TYPES)
        if issue_type not in ISSUE_TYPES[category]:
            flash('Select a valid issue type for the chosen category.', 'danger')
            return render_template('complaint_form.html', issue_types=ISSUE_TYPES, location_types=LOCATION_TYPES)
        if location_type not in LOCATION_TYPES:
            flash('Select a valid road/area type.', 'danger')
            return render_template('complaint_form.html', issue_types=ISSUE_TYPES, location_types=LOCATION_TYPES)
        if len(description) < 10:
            flash('Describe the problem in at least 10 characters.', 'danger')
            return render_template('complaint_form.html', issue_types=ISSUE_TYPES, location_types=LOCATION_TYPES)
        if not area:
            flash('Area / locality is required.', 'danger')
            return render_template('complaint_form.html', issue_types=ISSUE_TYPES, location_types=LOCATION_TYPES)

        try:
            lat = float(latitude)
            lng = float(longitude)
            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                raise ValueError
        except ValueError:
            flash('Select a valid location using GPS or the map pin.', 'danger')
            return render_template('complaint_form.html', issue_types=ISSUE_TYPES, location_types=LOCATION_TYPES)

        saved_image = None
        try:
            saved_image = save_image(image, 'complaint')
        except ValueError as exc:
            flash(str(exc), 'danger')
            return render_template('complaint_form.html', issue_types=ISSUE_TYPES, location_types=LOCATION_TYPES)

        score, severity = calculate_severity(category, issue_type, location_type)
        public_id = generate_public_id()
        created_at = datetime.now()
        sla_deadline = created_at + timedelta(hours=current_app.config['SLA_HOURS'])

        conn = cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO complaints
                (public_id, citizen_id, category, issue_type, location_type, description,
                 image_path, area, street, landmark, latitude, longitude,
                 severity_score, severity_label, status, created_at, sla_deadline)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Reported',%s,%s)
                ''',
                (
                    public_id, session['user_id'], category, issue_type, location_type,
                    description, saved_image, area, street or None, landmark or None,
                    lat, lng, score, severity, created_at, sla_deadline,
                ),
            )
            complaint_id = cursor.lastrowid
            log_status(conn, complaint_id, None, 'Reported', session['user_id'], 'Complaint submitted by citizen.')
            conn.commit()
            flash(f'Complaint {public_id} submitted successfully.', 'success')
            return redirect(url_for('citizen.complaint_detail', complaint_id=complaint_id))
        except Exception:
            if conn:
                conn.rollback()
            remove_image(saved_image)
            flash('Could not save the complaint. Please try again.', 'danger')
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    return render_template('complaint_form.html', issue_types=ISSUE_TYPES, location_types=LOCATION_TYPES)


@citizen_bp.route('/complaints/<int:complaint_id>')
@login_required
def complaint_detail(complaint_id):
    refresh_sla_overdue()
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            '''
            SELECT c.*, citizen.name AS citizen_name,
                   worker.name AS worker_name, worker.department AS worker_department
            FROM complaints c
            JOIN users citizen ON citizen.user_id = c.citizen_id
            LEFT JOIN users worker ON worker.user_id = c.assigned_worker_id
            WHERE c.complaint_id = %s
            ''',
            (complaint_id,),
        )
        complaint = cursor.fetchone()
        if not complaint:
            return render_template('404.html'), 404

        role = session.get('role')
        if role == 'citizen' and complaint['citizen_id'] != session['user_id']:
            return render_template('403.html'), 403
        if role == 'worker' and complaint['assigned_worker_id'] != session['user_id']:
            return render_template('403.html'), 403

        cursor.execute(
            '''
            SELECT h.*, u.name AS changed_by_name
            FROM complaint_status_history h
            LEFT JOIN users u ON u.user_id = h.changed_by
            WHERE h.complaint_id = %s
            ORDER BY h.changed_at ASC, h.history_id ASC
            ''',
            (complaint_id,),
        )
        history = cursor.fetchall()
        return render_template('complaint_detail.html', complaint=complaint, history=history)
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@citizen_bp.route('/complaints/<int:complaint_id>/verify', methods=['POST'])
@roles_required('citizen')
def verify_resolution(complaint_id):
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            'SELECT citizen_id, status FROM complaints WHERE complaint_id = %s',
            (complaint_id,),
        )
        complaint = cursor.fetchone()
        if not complaint or complaint['citizen_id'] != session['user_id']:
            return render_template('403.html'), 403
        if complaint['status'] != 'Resolved':
            flash('Only a resolved complaint can be verified.', 'warning')
        else:
            cursor.execute(
                "UPDATE complaints SET status='Verified', verified_at=NOW() WHERE complaint_id=%s",
                (complaint_id,),
            )
            log_status(conn, complaint_id, 'Resolved', 'Verified', session['user_id'], 'Resolution verified by citizen.')
            conn.commit()
            flash('Resolution verified. Thank you for helping improve your city.', 'success')
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
    return redirect(url_for('citizen.complaint_detail', complaint_id=complaint_id))


@citizen_bp.route('/leaderboard')
@login_required
def leaderboard():
    rows = _leaderboard_rows()
    return render_template('leaderboard.html', rows=rows)
