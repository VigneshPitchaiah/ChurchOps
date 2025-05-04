import os
from datetime import timedelta

class Config:
    """Base configuration class"""
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(24))
    
    # Database
    SQLALCHEMY_DATABASE_URI = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True  # Enable SQL query logging
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }
    
    # Caching
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Asset compilation
    ASSETS_DEBUG = False
    ASSETS_AUTO_BUILD = True

    # CORS
    CORS_ORIGINS = '*'
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    
    # Performance
    JSON_SORT_KEYS = False  # Prevents extra sorting work
    JSONIFY_PRETTYPRINT_REGULAR = False  # Reduces payload size
    
    # Miscellaneous
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
