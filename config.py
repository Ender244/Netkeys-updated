import os
from datetime import timedelta

class Config:
    """Base configuration"""
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_ENV') == 'development'
    
    # Security
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'admin123'
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = not DEBUG
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # File paths
    STOCK_FILE = os.environ.get('STOCK_FILE') or 'stock.enc'
    KEY_FILE = os.environ.get('KEY_FILE') or 'secret.key'
    USERS_FILE = os.environ.get('USERS_FILE') or 'users.json'
    SESSIONS_FILE = os.environ.get('SESSIONS_FILE') or 'sessions.json'
    
    # Validation
    COOKIE_MIN_LENGTH = int(os.environ.get('COOKIE_MIN_LENGTH', 50))
    COOKIE_CHECK_LIVE = os.environ.get('COOKIE_CHECK_LIVE', 'false').lower() == 'true'
    TOKEN_TIMEOUT = 3600  # 1 hour
    
class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True

def get_config():
    """Get appropriate config based on environment"""
    env = os.environ.get('FLASK_ENV', 'development')
    if env == 'production':
        return ProductionConfig()
    return DevelopmentConfig()
