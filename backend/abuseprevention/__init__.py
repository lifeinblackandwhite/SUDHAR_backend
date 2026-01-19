"""
SUDHAR Abuse Prevention Package

Simplified image validation system with four core checks:
1. AI Detection - Ensures image is not AI-generated
2. EXIF Validation - Verifies image timestamp and freshness
3. GPS Matching - Confirms image location matches user location
4. Web Existence - Checks if image already exists online/in database
"""

from .service import ImageValidationService, ImageValidationResult, get_db_connection
from .validators import (
    AIDetectionValidator,
    EXIFValidator,
    GPSValidator,
    WebExistenceValidator,
    ValidationResult
)
from .models import ImageValidation, KnownImageHash, create_tables
from .config import Config, get_config

__version__ = '2.0.0'

__all__ = [
    # Main service
    'ImageValidationService',
    'ImageValidationResult',
    'get_db_connection',
    
    # Validators
    'AIDetectionValidator',
    'EXIFValidator',
    'GPSValidator',
    'WebExistenceValidator',
    'ValidationResult',
    
    # Models
    'ImageValidation',
    'KnownImageHash',
    'create_tables',
    
    # Config
    'Config',
    'get_config'
]