from getpass import getpass

from werkzeug.security import generate_password_hash

from app import app
from db import get_connection

DEMO_USERS = [
    ('StreetSOS Admin', 'admin@streetsos.local', 'Admin@123', 'admin', None),
    ('Road Worker', 'road.worker@streetsos.local', 'Worker@123', 'worker', 'Road'),
    ('General Worker', 'general.worker@streetsos.local', 'Worker@123', 'worker', 'General'),
    ('Demo Citizen', 'citizen@streetsos.local', 'Citizen@123', 'citizen', None),
]

with app.app_context():
    conn = get_connection()
    cursor = conn.cursor()
    for name, email, password, role, department in DEMO_USERS:
        cursor.execute('SELECT user_id FROM users WHERE email=%s', (email,))
        if cursor.fetchone():
            continue
        cursor.execute(
            '''INSERT INTO users(name,email,password_hash,role,department)
               VALUES(%s,%s,%s,%s,%s)''',
            (name, email, generate_password_hash(password), role, department),
        )
    conn.commit()
    cursor.close()
    conn.close()

print('Demo users created (existing emails were skipped).')
print('Admin: admin@streetsos.local / Admin@123')
print('Road worker: road.worker@streetsos.local / Worker@123')
print('General worker: general.worker@streetsos.local / Worker@123')
print('Citizen: citizen@streetsos.local / Citizen@123')
