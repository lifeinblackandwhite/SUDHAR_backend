"""
Image Validation Service for Abuse Prevention.

Orchestrates all validators and provides a unified interface for image validation.
"""

import hashlib
import io
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

import imagehash
import psycopg2
from PIL import Image

from .validators import (
    AIDetectionValidator,
    EXIFValidator,
    GPSValidator,
    WebExistenceValidator,
    ValidationResult
)
from .config import Config

logger = logging.getLogger(__name__)


@dataclass
class ImageValidationResult:
    """Complete result of image validation."""
    
    is_valid: bool
    overall_score: int
    checks: Dict[str, Dict]
    reasons: List[str]
    image_hash: str
    phash: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "is_valid": self.is_valid,
            "overall_score": self.overall_score,
            "checks": self.checks,
            "reasons": self.reasons,
            "image_hash": self.image_hash,
            "phash": self.phash,
            "timestamp": self.timestamp
        }


class ImageValidationService:
    """
    Unified service for image validation.
    
    Orchestrates four validators:
    1. AI Detection - Ensure image is not AI-generated
    2. EXIF Validation - Verify image was taken recently
    3. GPS Validation - Match image location to user location
    4. Web Existence - Check if image exists online/in database
    """
    
    def __init__(self, db_connection=None, config: Config = None):
        """
        Initialize the validation service.
        
        Args:
            db_connection: PostgreSQL database connection (optional)
            config: Configuration object (optional, uses defaults)
        """
        self.config = config or Config()
        self.db = db_connection
        
        # Initialize validators
        self.ai_validator = AIDetectionValidator(
            threshold=getattr(self.config, 'AI_DETECTION_THRESHOLD', 0.7)
        )
        self.exif_validator = EXIFValidator(
            max_age_hours=getattr(self.config, 'MAX_PHOTO_AGE_HOURS', 24)
        )
        self.gps_validator = GPSValidator(
            max_distance_km=getattr(self.config, 'GPS_MAX_DISTANCE_KM', 0.5)
        )
        self.web_validator = WebExistenceValidator(
            db_connection=db_connection,
            hamming_threshold=getattr(self.config, 'DUPLICATE_HAMMING_THRESHOLD', 5)
        )
    
    def validate_image(
        self,
        image_data: bytes,
        user_latitude: float,
        user_longitude: float,
        store_hash: bool = True
    ) -> ImageValidationResult:
        """
        Validate an image through all four checks.
        
        Args:
            image_data: Raw image bytes
            user_latitude: User's current latitude
            user_longitude: User's current longitude
            store_hash: Whether to store the image hash after validation
            
        Returns:
            ImageValidationResult with all check results
        """
        try:
            # Open image
            image = Image.open(io.BytesIO(image_data))
            
            # Calculate hashes
            sha256_hash = hashlib.sha256(image_data).hexdigest()
            phash = str(imagehash.phash(image, hash_size=16))
            
            # Run all validators
            checks = {}
            reasons = []
            total_score = 0
            all_passed = True
            
            # 1. AI Detection Check
            ai_result = self.ai_validator.validate(image)
            checks['ai_detection'] = ai_result.to_dict()
            total_score += ai_result.score
            if not ai_result.passed:
                all_passed = False
                reasons.append(f"AI Check Failed: {ai_result.reason}")
            
            # 2. EXIF Freshness Check
            exif_result = self.exif_validator.validate(image)
            checks['exif_freshness'] = exif_result.to_dict()
            total_score += exif_result.score
            if not exif_result.passed:
                all_passed = False
                reasons.append(f"EXIF Check Failed: {exif_result.reason}")
            
            # 3. GPS Location Match
            gps_result = self.gps_validator.validate(
                image,
                user_latitude=user_latitude,
                user_longitude=user_longitude
            )
            checks['gps_match'] = gps_result.to_dict()
            total_score += gps_result.score
            if not gps_result.passed:
                all_passed = False
                reasons.append(f"GPS Check Failed: {gps_result.reason}")
            
            # 4. Web Existence Check
            web_result = self.web_validator.validate(image)
            checks['web_existence'] = web_result.to_dict()
            total_score += web_result.score
            if not web_result.passed:
                all_passed = False
                reasons.append(f"Web Check Failed: {web_result.reason}")
            
            # Normalize score to 0-100
            normalized_score = max(0, min(100, total_score))
            
            # Create result
            result = ImageValidationResult(
                is_valid=all_passed,
                overall_score=normalized_score,
                checks=checks,
                reasons=reasons if reasons else ["All checks passed"],
                image_hash=sha256_hash,
                phash=phash
            )
            
            # Log to database
            if self.db:
                self._log_validation(result, user_latitude, user_longitude)
            
            # Store hash for future comparison
            if store_hash and all_passed and self.db:
                self.web_validator.store_hash(image, source_type='submission')
            
            return result
            
        except Exception as e:
            logger.error(f"Image validation failed: {str(e)}")
            return ImageValidationResult(
                is_valid=False,
                overall_score=0,
                checks={"error": {"passed": False, "reason": str(e)}},
                reasons=[f"Validation error: {str(e)}"],
                image_hash="",
                phash=""
            )
    
    def _log_validation(
        self,
        result: ImageValidationResult,
        user_latitude: float,
        user_longitude: float
    ) -> None:
        """Log validation result to database."""
        try:
            cursor = self.db.cursor()
            
            # Extract details from checks
            ai_check = result.checks.get('ai_detection', {})
            exif_check = result.checks.get('exif_freshness', {})
            gps_check = result.checks.get('gps_match', {})
            web_check = result.checks.get('web_existence', {})
            
            cursor.execute("""
                INSERT INTO image_validations (
                    image_hash, phash, is_valid, overall_score,
                    ai_detection_passed, ai_detection_score, ai_detection_reason,
                    exif_valid, exif_timestamp, exif_age_hours, exif_reason,
                    gps_matched, gps_distance_km, exif_latitude, exif_longitude,
                    user_latitude, user_longitude, gps_reason,
                    web_check_passed, found_online, web_check_reason,
                    validation_reasons
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s
                )
            """, (
                result.image_hash,
                result.phash,
                result.is_valid,
                result.overall_score,
                ai_check.get('passed'),
                ai_check.get('confidence'),
                ai_check.get('reason'),
                exif_check.get('passed'),
                exif_check.get('timestamp'),
                exif_check.get('age_hours'),
                exif_check.get('reason'),
                gps_check.get('passed'),
                gps_check.get('distance_km'),
                gps_check.get('exif_latitude'),
                gps_check.get('exif_longitude'),
                user_latitude,
                user_longitude,
                gps_check.get('reason'),
                web_check.get('passed'),
                web_check.get('found_online', False),
                web_check.get('reason'),
                str(result.reasons)
            ))
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log validation: {str(e)}")
            try:
                self.db.rollback()
            except:
                pass


def get_db_connection(config: Config = None) -> psycopg2.extensions.connection:
    """
    Get a PostgreSQL database connection.
    
    Args:
        config: Configuration object (optional)
        
    Returns:
        psycopg2 connection object
    """
    config = config or Config()
    
    # Parse DATABASE_URL or use individual settings
    db_url = getattr(config, 'DATABASE_URL', None)
    
    if db_url:
        # Parse PostgreSQL URL
        # Format: postgresql://user:password@host:port/database
        import re
        match = re.match(
            r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', 
            db_url
        )
        if match:
            user, password, host, port, database = match.groups()
            return psycopg2.connect(
                host=host,
                port=int(port),
                database=database,
                user=user,
                password=password
            )
    
    # Default connection settings matching docker-compose.yml
    return psycopg2.connect(
        host='postgres',
        port=5432,
        database='infra_db',
        user='postgres',
        password='postgres'
    )
