from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from db import get_connection
from decorators import roles_required
from services import log_status, refresh_sla_overdue, remove_image, save_image

worker_bp = Blueprint('worker', __name__, url_prefix='/worker')


@worker_bp.route('/dashboard')
@roles_required('worker')
def dashboard():
    refresh_sla_overdue()
    status_filter = request.args.get('status', '').strip()
    clauses = ['assigned_worker_id=%s']
    params = [session['user_id']]
    if status_filter:
        clauses.append('status=%s')
        params.append(status_filter)

    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            f'''
            SELECT *, TIMESTAMPDIFF(HOUR, created_at, NOW()) AS age_hours
            FROM complaints
            WHERE {' AND '.join(clauses)}
            ORDER BY is_escalated DESC, severity_score DESC, created_at ASC
            ''',
            tuple(params),
        )
        complaints = cursor.fetchall()
        cursor.execute(
            '''
            SELECT COUNT(*) total,
                   SUM(status='Assigned') assigned,
                   SUM(status='In Progress') in_progress,
                   SUM(status='Resolved') resolved,
                   SUM(is_escalated=1 AND status NOT IN ('Resolved','Verified')) overdue
            FROM complaints WHERE assigned_worker_id=%s
            ''',
            (session['user_id'],),
        )
        stats = cursor.fetchone()
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

    return render_template('worker_dashboard.html', complaints=complaints, stats=stats, status_filter=status_filter)


@worker_bp.route('/complaints/<int:complaint_id>/start', methods=['POST'])
@roles_required('worker')
def start_work(complaint_id):
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            'SELECT status FROM complaints WHERE complaint_id=%s AND assigned_worker_id=%s',
            (complaint_id, session['user_id']),
        )
        complaint = cursor.fetchone()
        if not complaint:
            return render_template('403.html'), 403
        if complaint['status'] != 'Assigned':
            flash('Only assigned complaints can be moved to In Progress.', 'warning')
        else:
            cursor.execute(
                "UPDATE complaints SET status='In Progress', started_at=NOW() WHERE complaint_id=%s",
                (complaint_id,),
            )
            log_status(conn, complaint_id, 'Assigned', 'In Progress', session['user_id'], 'Municipal worker started work.')
            conn.commit()
            flash('Complaint marked In Progress.', 'success')
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
    return redirect(url_for('citizen.complaint_detail', complaint_id=complaint_id))


@worker_bp.route('/complaints/<int:complaint_id>/resolve', methods=['POST'])
@roles_required('worker')
def resolve(complaint_id):
    note = request.form.get('resolution_note', '').strip()
    resolution_image = request.files.get('resolution_image')
    if len(note) < 5:
        flash('Add a short resolution note before marking the issue resolved.', 'danger')
        return redirect(url_for('citizen.complaint_detail', complaint_id=complaint_id))

    saved_resolution = None
    if resolution_image and resolution_image.filename:
        try:
            saved_resolution = save_image(resolution_image, 'resolution')
        except ValueError as exc:
            flash(str(exc), 'danger')
            return redirect(url_for('citizen.complaint_detail', complaint_id=complaint_id))

    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            'SELECT status FROM complaints WHERE complaint_id=%s AND assigned_worker_id=%s',
            (complaint_id, session['user_id']),
        )
        complaint = cursor.fetchone()
        if not complaint:
            remove_image(saved_resolution)
            return render_template('403.html'), 403
        if complaint['status'] != 'In Progress':
            remove_image(saved_resolution)
            flash('Only In Progress complaints can be resolved.', 'warning')
        else:
            cursor.execute(
                '''
                UPDATE complaints
                SET status='Resolved', resolved_at=NOW(), resolution_note=%s,
                    resolution_image_path=COALESCE(%s, resolution_image_path)
                WHERE complaint_id=%s
                ''',
                (note, saved_resolution, complaint_id),
            )
            log_status(conn, complaint_id, 'In Progress', 'Resolved', session['user_id'], note)
            conn.commit()
            flash('Complaint marked Resolved. The citizen can now verify the work.', 'success')
    except Exception:
        if conn:
            conn.rollback()
        remove_image(saved_resolution)
        flash('Could not update the complaint.', 'danger')
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
    return redirect(url_for('citizen.complaint_detail', complaint_id=complaint_id))
