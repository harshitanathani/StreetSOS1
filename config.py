import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-this-secret-key-before-deployment')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'YOUR_MYSQL_PASSWORD')
    DB_NAME = os.getenv('DB_NAME', 'streetsos')
    SLA_HOURS = int(os.getenv('SLA_HOURS', '48'))
    MAX_UPLOAD_MB = int(os.getenv('MAX_UPLOAD_MB', '5'))
    MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024
    UPLOAD_FOLDER = str(BASE_DIR / 'static' / 'uploads')
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=6)
    DEBUG = os.getenv('FLASK_DEBUG', '1') == '1'
