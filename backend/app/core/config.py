import os
from dotenv import load_dotenv

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@postgres:5432/infra_db"
)

load_dotenv()

class Config:
    """Base configuration."""
    
    # Database
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'sudhar.db')
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    
    # Upload settings
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
    
    # Abuse Prevention
    VERIFICATION_THRESHOLD = int(os.getenv('VERIFICATION_THRESHOLD', 3))
    DUPLICATE_HAMMING_THRESHOLD = int(os.getenv('DUPLICATE_HAMMING_THRESHOLD', 5))
    PHOTO_SIMILARITY_MIN = int(os.getenv('PHOTO_SIMILARITY_MIN', 10))
    PHOTO_SIMILARITY_MAX = int(os.getenv('PHOTO_SIMILARITY_MAX', 25))
    
    # GPS Settings
    GPS_PROXIMITY_KM = float(os.getenv('GPS_PROXIMITY_KM', 0.1))  # 100 meters
    NEARBY_RADIUS_KM = float(os.getenv('NEARBY_RADIUS_KM', 5.0))  # 5 km
    
    # Time Settings
    MAX_PHOTO_AGE_HOURS = int(os.getenv('MAX_PHOTO_AGE_HOURS', 24))
    RECENT_PHOTO_HOURS = int(os.getenv('RECENT_PHOTO_HOURS', 1))
    
    # Scoring
    SCORE_GPS_MATCH = int(os.getenv('SCORE_GPS_MATCH', 50))
    SCORE_GPS_MISMATCH = int(os.getenv('SCORE_GPS_MISMATCH', -40))
    SCORE_NO_GPS = int(os.getenv('SCORE_NO_GPS', -20))
    SCORE_NO_EXIF = int(os.getenv('SCORE_NO_EXIF', -30))
    SCORE_RECENT_PHOTO = int(os.getenv('SCORE_RECENT_PHOTO', 30))
    SCORE_PHOTO_24H = int(os.getenv('SCORE_PHOTO_24H', 10))
    SCORE_OLD_PHOTO = int(os.getenv('SCORE_OLD_PHOTO', -20))
    SCORE_CAMERA_META = int(os.getenv('SCORE_CAMERA_META', 10))
    SCORE_DUPLICATE = int(os.getenv('SCORE_DUPLICATE', -60))
    SCORE_FAKE_THRESHOLD = int(os.getenv('SCORE_FAKE_THRESHOLD', -50))
    
    # Firebase Cloud Messaging
    FCM_ENABLED = os.getenv('FCM_ENABLED', 'false').lower() == 'true'
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    # WebSocket
    WEBSOCKET_ENABLED = os.getenv('WEBSOCKET_ENABLED', 'false').lower() == 'true'
    WEBSOCKET_URL = os.getenv('WEBSOCKET_URL', 'http://localhost:3000')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'sudhar.log')
    
    # Security
    ENABLE_RATE_LIMITING = os.getenv('ENABLE_RATE_LIMITING', 'true').lower() == 'true'
    RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', 60))
    
    # API
    API_VERSION = 'v1'
    API_PREFIX = f'/api/{API_VERSION}'


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    DATABASE_PATH = ':memory:'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(env=None):
    """Get configuration based on environment."""
    if env is None:
        env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])