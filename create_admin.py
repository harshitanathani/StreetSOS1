from getpass import getpass

from werkzeug.security import generate_password_hash

from app import app
from db import get_connection
from services import valid_email

name = input('Admin name: ').strip()
email = input('Admin email: ').strip().lower()
password = getpass('Admin password (minimum 6 characters): ')

if len(name) < 2 or not valid_email(email) or len(password) < 6:
    raise SystemExit('Invalid name, email or password.')

with app.app_context():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users WHERE email=%s', (email,))
    if cursor.fetchone():
        raise SystemExit('That email already exists.')
    cursor.execute(
        "INSERT INTO users(name,email,password_hash,role) VALUES(%s,%s,%s,'admin')",
        (name, email, generate_password_hash(password)),
    )
    conn.commit()
    cursor.close()
    conn.close()

print('Admin account created successfully.')
