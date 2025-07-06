import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration class.""" 
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'
    
    # Database configuration with PostgreSQL as default, SQLite as fallback
    if os.environ.get('DATABASE_URL'):
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    elif os.environ.get('USE_POSTGRESQL', '').lower() == 'true':
        # PostgreSQL configuration
        from urllib.parse import quote_plus
        DB_USER = os.environ.get('DB_USER', 'journal_user')
        DB_PASSWORD = os.environ.get('DB_PASSWORD', 'change_me_in_production')
        DB_HOST = os.environ.get('DB_HOST', 'localhost')
        DB_PORT = os.environ.get('DB_PORT', '5432')
        DB_NAME = os.environ.get('DB_NAME', 'journal_db')
        # URL encode password to handle special characters
        SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    else:
        # SQLite fallback
        SQLALCHEMY_DATABASE_URI = 'sqlite:///journal.db'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Email settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.mailgun.org')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@journal-app.com')
    
    # Application specific settings
    APP_NAME = 'Journal App'
    APP_URL = os.environ.get('APP_URL', 'http://localhost:5000')
    
    # File upload settings
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads/photos')
    ALLOWED_PHOTO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MEGABYTE = 1024 * 1024
    MAX_CONTENT_LENGTH = 16 * MEGABYTE  # 16MB max upload size
    
    # Security settings
    COMMON_PASSWORDS = {
        'password', '123456', 'qwerty', 'admin', 'welcome', 'letmein', 'monkey',
        'dragon', '111111', '123123', '654321', 'master', 'sunshine', '12345678',
        'password123', 'abc123', 'football', 'baseball', 'princess', 'iloveyou',
        'trustno1', 'superman', 'hello', 'charlie', 'freedom', 'whatever', 'asdfgh',
        'zxcvbn', '1qaz2wsx', 'password1', 'temp123', 'passw0rd', '123qwe'
    }
