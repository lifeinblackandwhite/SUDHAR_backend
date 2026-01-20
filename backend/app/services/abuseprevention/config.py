"""
Configuration for the Abuse Prevention module.
Uses the existing PostgreSQL database from docker-compose.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration settings for abuse prevention."""
    
    # Database - uses existing PostgreSQL from docker-compose
    DATABASE_URL = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:postgres@postgres:5432/infra_db'
    )
    
    # For local development (outside Docker)
    DATABASE_URL_LOCAL = os.getenv(
        'DATABASE_URL_LOCAL',
        'postgresql://postgres:postgres@localhost:5433/infra_db'
    )
    
    # Validation thresholds
    MAX_PHOTO_AGE_HOURS = int(os.getenv('MAX_PHOTO_AGE_HOURS', 24))
    GPS_MAX_DISTANCE_KM = float(os.getenv('GPS_MAX_DISTANCE_KM', 0.5))
    AI_DETECTION_THRESHOLD = float(os.getenv('AI_DETECTION_THRESHOLD', 0.7))
    DUPLICATE_HAMMING_THRESHOLD = int(os.getenv('DUPLICATE_HAMMING_THRESHOLD', 5))
    
    # Upload settings
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
    
    # External APIs (optional - for future integration)
    TINEYE_API_KEY = os.getenv('TINEYE_API_KEY')
    AI_DETECTION_API_KEY = os.getenv('AI_DETECTION_API_KEY')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # API settings
    API_VERSION = 'v1'
    API_PREFIX = f'/api/{API_VERSION}'
    
    @classmethod
    def is_allowed_file(cls, filename: str) -> bool:
        """Check if file extension is allowed."""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in cls.ALLOWED_EXTENSIONS


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    # Use local database URL for development outside Docker
    DATABASE_URL = Config.DATABASE_URL_LOCAL


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': Config
}


def get_config(env: str = None) -> Config:
    """
    Get configuration based on environment.
    
    Args:
        env: Environment name (development, production, testing)
        
    Returns:
        Configuration class
    """
    if env is None:
        env = os.getenv('FLASK_ENV', 'default')
    return config.get(env, config['default'])