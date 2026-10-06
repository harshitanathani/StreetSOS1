import os
import re
import uuid
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from flask import current_app
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

from db import get_connection

ISSUE_TYPES = {
    'Road': ['Pothole', 'Damaged Road', 'Road Obstruction'],
    'Garbage': ['Overflowing Bin', 'Illegal Dumping', 'Uncollected Waste'],
    'Drainage': ['Blocked Drain', 'Waterlogging', 'Open Drain'],
    'Lighting': ['Broken Streetlight', 'Flickering Light', 'Dark Stretch'],
}

LOCATION_TYPES = ['Highway', 'Main Road', 'Residential Area', 'Market / Public Area', 'Other']

CATEGORY_BASE = {'Road': 6, 'Drainage': 6, 'Garbage': 4, 'Lighting': 3}
LOCATION_WEIGHT = {'Highway': 3, 'Main Road': 2, 'Residential Area': 1, 'Market / Public Area': 2, 'Other': 1}
ISSUE_WEIGHT = {
    'Pothole': 2, 'Damaged Road': 2, 'Road Obstruction': 1,
    'Overflowing Bin': 1, 'Illegal Dumping': 2, 'Uncollected Waste': 1,
    'Blocked Drain': 2, 'Waterlogging': 3, 'Open Drain': 2,
    'Broken Streetlight': 1, 'Flickering Light': 0, 'Dark Stretch': 2,
}

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}


def valid_email(email):
    return bool(re.fullmatch(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email or ''))


def calculate_severity(category, issue_type, location_type):
    score = CATEGORY_BASE.get(category, 1)
    score += ISSUE_WEIGHT.get(issue_type, 0)
    score += LOCATION_WEIGHT.get(location_type, 1)
    score = max(1, min(10, score))
    if score >= 9:
        label = 'Critical'
    elif score >= 7:
        label = 'High'
    elif score >= 4:
        label = 'Medium'
    else:
        label = 'Low'
    return score, label


def badge_for_verified(count):
    if count >= 10:
        return {'name': 'Road Warrior', 'next': None, 'remaining': 0}
    if count >= 5:
        return {'name': 'Street Guardian', 'next': 'Road Warrior', 'remaining': 10 - count}
    if count >= 3:
        return {'name': 'Neighbourhood Helper', 'next': 'Street Guardian', 'remaining': 5 - count}
    if count >= 1:
        return {'name': 'Civic Starter', 'next': 'Neighbourhood Helper', 'remaining': 3 - count}
    return {'name': 'New Citizen', 'next': 'Civic Starter', 'remaining': 1}


def generate_public_id():
    return 'SOS-' + datetime.now().strftime('%y%m%d') + '-' + uuid.uuid4().hex[:6].upper()


def save_image(file_storage, prefix='issue'):
    if not file_storage or not file_storage.filename:
        raise ValueError('Please select an image.')

    original = secure_filename(file_storage.filename)
    if '.' not in original:
        raise ValueError('Image must be PNG, JPG, JPEG or WEBP.')

    extension = original.rsplit('.', 1)[1].lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError('Image must be PNG, JPG, JPEG or WEBP.')

    try:
        file_storage.stream.seek(0)
        image = Image.open(file_storage.stream)
        image.verify()
        file_storage.stream.seek(0)
    except (UnidentifiedImageError, OSError):
        raise ValueError('The uploaded file is not a valid image.')

    filename = f'{prefix}_{uuid.uuid4().hex}.{extension}'
    destination = Path(current_app.config['UPLOAD_FOLDER']) / filename
    file_storage.save(destination)
    return filename


def remove_image(filename):
    if not filename:
        return
    path = Path(current_app.config['UPLOAD_FOLDER']) / filename
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def log_status(conn, complaint_id, from_status, to_status, changed_by=None, note=None):
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT INTO complaint_status_history
        (complaint_id, from_status, to_status, changed_by, note)
        VALUES (%s, %s, %s, %s, %s)
        ''',
        (complaint_id, from_status, to_status, changed_by, note),
    )
    cursor.close()


def refresh_sla_overdue():
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            '''
            SELECT complaint_id, status
            FROM complaints
            WHERE is_escalated = 0
              AND status NOT IN ('Resolved', 'Verified')
              AND sla_deadline < NOW()
            '''
        )
        overdue = cursor.fetchall()
        for row in overdue:
            cursor.execute(
                '''
                UPDATE complaints
                SET is_escalated = 1, escalated_at = NOW()
                WHERE complaint_id = %s
                ''',
                (row['complaint_id'],),
            )
            log_status(
                conn,
                row['complaint_id'],
                row['status'],
                row['status'],
                None,
                'Automatically escalated after exceeding the 48-hour SLA.',
            )
        conn.commit()
        return len(overdue)
    except Exception:
        if conn:
            conn.rollback()
        return 0
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def _scheduled_sla_scan(app):
    with app.app_context():
        refresh_sla_overdue()


def start_sla_scheduler(app):
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        lambda: _scheduled_sla_scan(app),
        'interval',
        minutes=1,
        id='streetsos_sla_scan',
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    return scheduler
