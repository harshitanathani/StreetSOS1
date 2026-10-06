from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_connection
from services import valid_email

auth_bp = Blueprint('auth', __name__)


def _role_destination(role):
    if role == 'admin':
        return 'admin.dashboard'
    if role == 'worker':
        return 'worker.dashboard'
    return 'citizen.dashboard'


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for(_role_destination(session.get('role'))))

    form = {'name': '', 'email': ''}
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        form.update(name=name, email=email)

        if len(name) < 2:
            flash('Please enter your full name.', 'danger')
        elif not valid_email(email):
            flash('Please enter a valid email address.', 'danger')
        elif len(password) < 6:
            flash('Password must contain at least 6 characters.', 'danger')
        elif password != confirm:
            flash('Passwords do not match.', 'danger')
        else:
            conn = cursor = None
            try:
                conn = get_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute('SELECT user_id FROM users WHERE email = %s', (email,))
                if cursor.fetchone():
                    flash('An account with this email already exists.', 'danger')
                else:
                    cursor.execute(
                        '''
                        INSERT INTO users (name, email, password_hash, role)
                        VALUES (%s, %s, %s, 'citizen')
                        ''',
                        (name, email, generate_password_hash(password)),
                    )
                    conn.commit()
                    flash('Account created successfully. Please login.', 'success')
                    return redirect(url_for('auth.login'))
            except Exception:
                if conn:
                    conn.rollback()
                flash('Could not create the account. Check the database connection and try again.', 'danger')
            finally:
                if cursor:
                    cursor.close()
                if conn and conn.is_connected():
                    conn.close()

    return render_template('register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for(_role_destination(session.get('role'))))

    email = ''
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        conn = cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM users WHERE email = %s AND is_active = 1', (email,))
            user = cursor.fetchone()
            if not user or not check_password_hash(user['password_hash'], password):
                flash('Invalid email or password.', 'danger')
            else:
                session.clear()
                session.permanent = True
                session['user_id'] = user['user_id']
                session['name'] = user['name']
                session['email'] = user['email']
                session['role'] = user['role']
                session['department'] = user['department']
                flash(f"Welcome back, {user['name']}.", 'success')
                return redirect(url_for(_role_destination(user['role'])))
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    return render_template('login.html', email=email)


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))
