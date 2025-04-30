import os
from dotenv import load_dotenv
from datetime import timedelta

# Load environment variables
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')

    # Check if running on PythonAnywhere
    if 'PYTHONANYWHERE_DOMAIN' in os.environ:
        # PythonAnywhere MySQL configuration
        MYSQL_USER = os.getenv('MYSQL_USER', 'Francis17')
        MYSQL_HOST = os.getenv('MYSQL_HOST', 'Francis17.mysql.pythonanywhere-services.com')
        MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
        MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'Francis17$default')

        # Use PyMySQL as the MySQL driver
        SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DATABASE}'
    else:
        # Local SQLite configuration
        SQLALCHEMY_DATABASE_URI = 'sqlite:///uvote.db'

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Base upload folder
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')

    # Specific upload directories
    CANDIDATE_IMAGES = os.path.join(UPLOAD_FOLDER, 'images', 'candidates')
    PARTY_IMAGES = os.path.join(UPLOAD_FOLDER, 'party_images')
    USER_LISTS = os.path.join(UPLOAD_FOLDER, 'user_lists')

    # Create all required directories
    for directory in [UPLOAD_FOLDER, CANDIDATE_IMAGES, PARTY_IMAGES, USER_LISTS]:
        os.makedirs(directory, exist_ok=True)

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.getenv('WTF_CSRF_SECRET_KEY', 'csrf-secret-key')
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@uvote.com')  # Default admin email if not set in environment
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)