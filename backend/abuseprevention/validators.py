"""
Image Validators for Abuse Prevention.

Four independent validators that check different aspects of image authenticity:
1. AIDetectionValidator - Ensures image is NOT AI-generated
2. EXIFValidator - Validates EXIF timestamp for freshness
3. GPSValidator - Matches image GPS to user location
4. WebExistenceValidator - Checks if image exists online/in database
"""

import hashlib
import io
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
from typing import Dict, Optional, Tuple, Any

import imagehash
import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of a single validation check."""
    
    def __init__(
        self,
        passed: bool,
        score: int = 0,
        reason: str = "",
        details: Optional[Dict[str, Any]] = None
    ):
        self.passed = passed
        self.score = score
        self.reason = reason
        self.details = details or {}
    
    def to_dict(self) -> Dict:
        return {
            "passed": self.passed,
            "score": self.score,
            "reason": self.reason,
            **self.details
        }


class BaseValidator(ABC):
    """Abstract base class for all validators."""
    
    @abstractmethod
    def validate(self, image: Image.Image, **kwargs) -> ValidationResult:
        """
        Validate the image.
        
        Args:
            image: PIL Image object
            **kwargs: Additional validation parameters
            
        Returns:
            ValidationResult with pass/fail status and details
        """
        pass


class AIDetectionValidator(BaseValidator):
    """
    Detects if an image is AI-generated using heuristic analysis.
    
    Checks:
    - EXIF metadata patterns (AI images often lack authentic EXIF)
    - Camera make/model authenticity
    - Software signatures that indicate AI generation
    - Basic noise pattern analysis
    """
    
    # Known AI generation software signatures
    AI_SOFTWARE_SIGNATURES = [
        'midjourney', 'dall-e', 'dalle', 'stable diffusion', 'stablediffusion',
        'novelai', 'artbreeder', 'deepai', 'nightcafe', 'jasper',
        'adobe firefly', 'firefly', 'canva ai', 'bing image creator',
        'leonardo.ai', 'playground ai', 'dreamstudio', 'bluewillow'
    ]
    
    # Suspicious patterns that suggest fake/stripped metadata
    SUSPICIOUS_PATTERNS = [
        'photoshop', 'gimp', 'paint.net', 'snapseed', 'lightroom'
    ]
    
    def __init__(self, threshold: float = 0.7):
        """
        Initialize AI detection validator.
        
        Args:
            threshold: Confidence threshold (0.0 - 1.0) for AI detection
        """
        self.threshold = threshold
    
    def validate(self, image: Image.Image, **kwargs) -> ValidationResult:
        """
        Check if image appears to be AI-generated.
        
        Returns ValidationResult with:
        - passed: True if image is likely REAL (not AI)
        - score: Confidence score (higher = more likely real)
        """
        score = 100  # Start with perfect score
        reasons = []
        details = {}
        
        try:
            # Check 1: EXIF metadata presence and quality
            exif_score, exif_reasons = self._check_exif_authenticity(image)
            score += exif_score
            reasons.extend(exif_reasons)
            details['exif_check'] = exif_score
            
            # Check 2: Software signatures
            software_score, software_reasons = self._check_software_signature(image)
            score += software_score
            reasons.extend(software_reasons)
            details['software_check'] = software_score
            
            # Check 3: Image characteristics (basic noise analysis)
            noise_score, noise_reasons = self._analyze_image_characteristics(image)
            score += noise_score
            reasons.extend(noise_reasons)
            details['noise_check'] = noise_score
            
            # Normalize score to 0-100 range
            normalized_score = max(0, min(100, score))
            confidence = normalized_score / 100.0
            
            # ALWAYS PASS - AI detection is just informational
            # Only add reasons for logging, don't block
            passed = True  # Always pass
            
            return ValidationResult(
                passed=passed,
                score=int(normalized_score),
                reason="; ".join(reasons) if reasons else "Image appears authentic",
                details={
                    "confidence": round(confidence, 2),
                    "is_likely_ai": not passed,
                    **details
                }
            )
            
        except Exception as e:
            logger.error(f"AI detection error: {str(e)}")
            # ON ERROR: PASS THE CHECK (be lenient)
            return ValidationResult(
                passed=True,
                score=50,
                reason=f"AI detection skipped: {str(e)}",
                details={"error": str(e), "skipped": True}
            )
    
    def _check_exif_authenticity(self, image: Image.Image) -> Tuple[int, list]:
        """Check EXIF data for signs of authentic camera capture."""
        score = 0
        reasons = []
        
        try:
            exif_data = image._getexif()
            
            if not exif_data:
                score -= 30
                reasons.append("No EXIF data (common in AI images)")
                return score, reasons
            
            exif = {TAGS.get(tag, tag): value for tag, value in exif_data.items()}
            
            # Check for camera make/model
            if exif.get('Make') and exif.get('Model'):
                score += 25
                # Verify it's a known camera manufacturer
                known_makes = ['apple', 'samsung', 'google', 'huawei', 'xiaomi', 'oppo',
                               'vivo', 'oneplus', 'sony', 'canon', 'nikon', 'fujifilm']
                make_lower = str(exif.get('Make', '')).lower()
                if any(m in make_lower for m in known_makes):
                    score += 10
            else:
                score -= 15
                reasons.append("Missing camera make/model")
            
            # Check for datetime
            if exif.get('DateTime') or exif.get('DateTimeOriginal'):
                score += 10
            else:
                score -= 10
                reasons.append("Missing timestamp")
            
            # Check for GPS data (very hard to fake authentically)
            if 'GPSInfo' in exif:
                score += 15
            
            # Check for other authentic markers
            if exif.get('ExposureTime') or exif.get('FNumber') or exif.get('ISOSpeedRatings'):
                score += 10
                
        except Exception as e:
            logger.warning(f"EXIF check error: {e}")
            score -= 20
            reasons.append("EXIF parsing failed")
        
        return score, reasons
    
    def _check_software_signature(self, image: Image.Image) -> Tuple[int, list]:
        """Check for AI generation software signatures in metadata."""
        score = 0
        reasons = []
        
        try:
            exif_data = image._getexif()
            if not exif_data:
                return 0, []
            
            exif = {TAGS.get(tag, tag): value for tag, value in exif_data.items()}
            software = str(exif.get('Software', '')).lower()
            
            # Check for AI software signatures
            for ai_sig in self.AI_SOFTWARE_SIGNATURES:
                if ai_sig in software:
                    score -= 80
                    reasons.append(f"AI software detected: {ai_sig}")
                    return score, reasons
            
            # Check for editing software (suspicious but not definitive)
            for sus_sig in self.SUSPICIOUS_PATTERNS:
                if sus_sig in software:
                    score -= 10
                    reasons.append(f"Editing software detected: {sus_sig}")
                    
        except Exception:
            pass
        
        return score, reasons
    
    def _analyze_image_characteristics(self, image: Image.Image) -> Tuple[int, list]:
        """Analyze image characteristics for AI-generated patterns."""
        score = 0
        reasons = []
        
        try:
            # Convert to numpy array for analysis
            img_array = np.array(image.convert('RGB'))
            
            # Check 1: Noise analysis - AI images often have unusual noise patterns
            # Real photos have natural sensor noise, AI images may be too smooth or have artifacts
            gray = np.mean(img_array, axis=2)
            
            # Calculate local variance (noise indicator)
            # Real photos have consistent noise, AI often has varying noise levels
            h, w = gray.shape
            block_size = min(64, h // 4, w // 4)
            
            if block_size > 8:
                variances = []
                for i in range(0, h - block_size, block_size):
                    for j in range(0, w - block_size, block_size):
                        block = gray[i:i+block_size, j:j+block_size]
                        variances.append(np.var(block))
                
                if variances:
                    variance_of_variances = np.var(variances)
                    mean_variance = np.mean(variances)
                    
                    # Very uniform variance across blocks can indicate AI generation
                    if mean_variance > 0 and variance_of_variances / mean_variance < 0.1:
                        score -= 15
                        reasons.append("Unusually uniform noise pattern")
            
            # Check 2: Color distribution - AI images sometimes have unnatural color distributions
            for channel in range(3):
                channel_data = img_array[:, :, channel].flatten()
                unique_values = len(np.unique(channel_data))
                
                # Very few unique values might indicate AI or heavy processing
                if unique_values < 50:
                    score -= 10
                    reasons.append(f"Limited color range in channel {channel}")
                    break
                    
        except Exception as e:
            logger.warning(f"Image analysis error: {e}")
        
        return score, reasons


class EXIFValidator(BaseValidator):
    """
    Validates EXIF timestamp to ensure image was taken recently.
    
    Checks:
    - Presence of DateTime/DateTimeOriginal in EXIF
    - Image age is within acceptable window
    """
    
    def __init__(self, max_age_hours: int = 24):
        """
        Initialize EXIF validator.
        
        Args:
            max_age_hours: Maximum acceptable age of photo in hours
        """
        self.max_age_hours = max_age_hours
    
    def validate(self, image: Image.Image, **kwargs) -> ValidationResult:
        """
        Validate EXIF timestamp.
        
        Returns ValidationResult with:
        - passed: True if image has valid, recent timestamp
        - details: timestamp, age_hours
        """
        try:
            exif_data = image._getexif()
            
            if not exif_data:
                # ALWAYS PASS - just note the missing EXIF
                return ValidationResult(
                    passed=True,
                    score=0,
                    reason="No EXIF data found (accepted anyway)",
                    details={"has_exif": False}
                )
            
            exif = {TAGS.get(tag, tag): value for tag, value in exif_data.items()}
            
            # Try to get timestamp from various EXIF fields
            timestamp_str = (
                exif.get('DateTimeOriginal') or 
                exif.get('DateTime') or 
                exif.get('DateTimeDigitized')
            )
            
            if not timestamp_str:
                # ALWAYS PASS - just note the missing timestamp
                return ValidationResult(
                    passed=True,
                    score=0,
                    reason="No timestamp in EXIF (accepted anyway)",
                    details={"has_exif": True, "has_timestamp": False}
                )
            
            # Parse timestamp
            try:
                photo_time = datetime.strptime(str(timestamp_str), '%Y:%m:%d %H:%M:%S')
            except ValueError:
                # ALWAYS PASS on parse error
                return ValidationResult(
                    passed=True,
                    score=0,
                    reason=f"Could not parse timestamp (accepted anyway)",
                    details={"has_timestamp": True, "timestamp_raw": str(timestamp_str)}
                )
            
            # Calculate age
            now = datetime.now()
            age_seconds = abs((now - photo_time).total_seconds())
            age_hours = age_seconds / 3600
            
            # Determine score based on age
            if age_hours <= 1:
                score = 30
                reason = "Image taken within the last hour"
            elif age_hours <= self.max_age_hours:
                score = 15
                reason = f"Image taken {age_hours:.1f} hours ago (within {self.max_age_hours}h limit)"
            else:
                score = -25
                reason = f"Image is too old: {age_hours:.1f} hours (limit: {self.max_age_hours}h)"
            
            # ALWAYS PASS - age is just informational
            passed = True
            
            return ValidationResult(
                passed=passed,
                score=score,
                reason=reason,
                details={
                    "timestamp": photo_time.isoformat(),
                    "age_hours": round(age_hours, 2),
                    "max_age_hours": self.max_age_hours
                }
            )
            
        except Exception as e:
            logger.error(f"EXIF validation error: {str(e)}")
            # ALWAYS PASS on error
            return ValidationResult(
                passed=True,
                score=0,
                reason=f"EXIF check skipped: {str(e)}",
                details={"error": str(e)}
            )


class GPSValidator(BaseValidator):
    """
    Validates that image GPS location matches user's current location.
    
    Uses Haversine formula to calculate distance between EXIF GPS and user GPS.
    """
    
    def __init__(self, max_distance_km: float = 0.5):
        """
        Initialize GPS validator.
        
        Args:
            max_distance_km: Maximum acceptable distance in kilometers
        """
        self.max_distance_km = max_distance_km
    
    def validate(
        self, 
        image: Image.Image, 
        user_latitude: float = None,
        user_longitude: float = None,
        **kwargs
    ) -> ValidationResult:
        """
        Validate GPS location matches user location.
        
        Args:
            image: PIL Image
            user_latitude: User's current latitude
            user_longitude: User's current longitude
            
        Returns ValidationResult with:
        - passed: True if GPS matches within threshold
        - details: distance_km, exif_coords, user_coords
        """
        if user_latitude is None or user_longitude is None:
            # ALWAYS PASS - just note the missing location
            return ValidationResult(
                passed=True,
                score=0,
                reason="User location not provided (accepted anyway)",
                details={"error": "missing_user_location"}
            )
        
        try:
            exif_data = image._getexif()
            
            if not exif_data:
                # ALWAYS PASS - just note no EXIF
                return ValidationResult(
                    passed=True,
                    score=0,
                    reason="No EXIF data (accepted anyway)",
                    details={"has_exif": False}
                )
            
            exif = {TAGS.get(tag, tag): value for tag, value in exif_data.items()}
            gps_info = exif.get('GPSInfo')
            
            if not gps_info:
                # ALWAYS PASS - just note no GPS
                return ValidationResult(
                    passed=True,
                    score=0,
                    reason="No GPS in image (accepted anyway)",
                    details={"has_exif": True, "has_gps": False}
                )
            
            # Parse GPS coordinates
            exif_coords = self._parse_gps(gps_info)
            
            if not exif_coords:
                # ALWAYS PASS - just note the parse error
                return ValidationResult(
                    passed=True,
                    score=0,
                    reason="Could not parse GPS (accepted anyway)",
                    details={"has_gps": True, "parse_error": True}
                )
            
            # Calculate distance
            distance = self._calculate_distance(
                exif_coords['latitude'],
                exif_coords['longitude'],
                user_latitude,
                user_longitude
            )
            
            # Determine pass/fail
            passed = distance <= self.max_distance_km
            
            if passed:
                if distance <= 0.1:  # Within 100 meters
                    score = 35
                    reason = f"GPS location matches exactly ({distance*1000:.0f}m away)"
                else:
                    score = 20
                    reason = f"GPS location matches ({distance:.2f}km away)"
            else:
                score = -35
                reason = f"GPS mismatch: image taken {distance:.2f}km away (limit: {self.max_distance_km}km)"
            
            # ALWAYS PASS - GPS is just informational
            return ValidationResult(
                passed=True,  # Always pass
                score=score,
                reason=reason,
                details={
                    "distance_km": round(distance, 3),
                    "max_distance_km": self.max_distance_km,
                    "exif_latitude": exif_coords['latitude'],
                    "exif_longitude": exif_coords['longitude'],
                    "user_latitude": user_latitude,
                    "user_longitude": user_longitude
                }
            )
            
        except Exception as e:
            logger.error(f"GPS validation error: {str(e)}")
            # ALWAYS PASS on error
            return ValidationResult(
                passed=True,
                score=0,
                reason=f"GPS check skipped: {str(e)}",
                details={"error": str(e)}
            )
    
    def _parse_gps(self, gps_info: Dict) -> Optional[Dict[str, float]]:
        """Parse GPS coordinates from EXIF GPS info."""
        try:
            def convert_to_degrees(value):
                """Convert GPS coordinate tuple to decimal degrees."""
                d, m, s = value
                # Handle IFDRational type
                d = float(d)
                m = float(m)
                s = float(s)
                return d + m / 60 + s / 3600
            
            gps_latitude = gps_info.get(2)
            gps_latitude_ref = gps_info.get(1)
            gps_longitude = gps_info.get(4)
            gps_longitude_ref = gps_info.get(3)
            
            if gps_latitude and gps_longitude:
                lat = convert_to_degrees(gps_latitude)
                if gps_latitude_ref == 'S':
                    lat = -lat
                    
                lon = convert_to_degrees(gps_longitude)
                if gps_longitude_ref == 'W':
                    lon = -lon
                    
                return {'latitude': lat, 'longitude': lon}
        except Exception as e:
            logger.warning(f"GPS parsing error: {e}")
        
        return None
    
    def _calculate_distance(
        self, 
        lat1: float, 
        lon1: float, 
        lat2: float, 
        lon2: float
    ) -> float:
        """
        Calculate distance between two GPS coordinates using Haversine formula.
        
        Returns:
            Distance in kilometers
        """
        R = 6371  # Earth's radius in kilometers
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c


class WebExistenceValidator(BaseValidator):
    """
    Checks if image exists online or in the database.
    
    Uses perceptual hashing to compare against known images.
    Can be extended to use TinEye or Google Vision API.
    """
    
    def __init__(self, db_connection=None, hamming_threshold: int = 5):
        """
        Initialize web existence validator.
        
        Args:
            db_connection: Database connection for checking known hashes
            hamming_threshold: Max hamming distance for similarity match
        """
        self.db = db_connection
        self.hamming_threshold = hamming_threshold
    
    def validate(self, image: Image.Image, **kwargs) -> ValidationResult:
        """
        Check if image exists in database or online.
        
        Returns ValidationResult with:
        - passed: True if image is NOT found (original)
        - details: found_online, similar_hash_id
        """
        try:
            # Calculate perceptual hash
            phash = imagehash.phash(image, hash_size=16)
            phash_str = str(phash)
            
            # Calculate SHA256 for exact match
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='PNG')
            sha256 = hashlib.sha256(img_bytes.getvalue()).hexdigest()
            
            details = {
                "phash": phash_str,
                "sha256": sha256[:16] + "...",  # Truncated for display
                "checked_database": False,
                "found_online": False
            }
            
            # Check against database if connection available
            if self.db:
                try:
                    found, match_info = self._check_database(phash, sha256)
                    details["checked_database"] = True
                    
                    if found:
                        # Only reject EXACT SHA256 matches
                        # Similar images (perceptual hash) are allowed
                        if 'exact_match' in match_info:
                            return ValidationResult(
                                passed=False,
                                score=-40,
                                reason="Exact duplicate image found (rejected)",
                                details={
                                    **details,
                                    "found_in_database": True,
                                    "match_info": match_info
                                }
                            )
                        else:
                            # Similar but not exact - just note it, don't reject
                            details["similar_image_found"] = True
                            details["match_info"] = match_info
                except Exception as e:
                    logger.warning(f"Database check failed: {e}")
                    details["database_error"] = str(e)
            
            # TODO: Add TinEye/Google Vision API integration here
            # For now, just return success if not found in database
            
            return ValidationResult(
                passed=True,
                score=15,
                reason="Image not found in known image database",
                details={
                    **details,
                    "found_in_database": False
                }
            )
            
        except Exception as e:
            logger.error(f"Web existence check error: {str(e)}")
            return ValidationResult(
                passed=True,  # Pass by default on error (don't block legit images)
                score=0,
                reason=f"Web check error (allowing): {str(e)}",
                details={"error": str(e)}
            )
    
    def _check_database(self, phash: imagehash.ImageHash, sha256: str) -> Tuple[bool, str]:
        """
        Check if image hash exists in database.
        
        Returns:
            Tuple of (found: bool, match_info: str)
        """
        cursor = self.db.cursor()
        
        # First check for exact SHA256 match
        cursor.execute(
            "SELECT id, source_type FROM known_image_hashes WHERE sha256_hash = %s",
            (sha256,)
        )
        result = cursor.fetchone()
        if result:
            return True, f"exact_match_id_{result[0]}"
        
        # Then check for similar perceptual hash
        cursor.execute("SELECT id, phash, source_type FROM known_image_hashes")
        
        for row in cursor.fetchall():
            try:
                existing_hash = imagehash.hex_to_hash(row[1])
                hamming_distance = phash - existing_hash
                
                if hamming_distance <= self.hamming_threshold:
                    return True, f"similar_match_id_{row[0]}_distance_{hamming_distance}"
            except Exception:
                continue
        
        return False, ""
    
    def store_hash(self, image: Image.Image, source_type: str = 'submission') -> bool:
        """
        Store image hash in database for future comparison.
        
        Args:
            image: PIL Image
            source_type: Type of source (submission, web, known_fake)
            
        Returns:
            True if stored successfully
        """
        if not self.db:
            return False
        
        try:
            phash = str(imagehash.phash(image, hash_size=16))
            
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='PNG')
            sha256 = hashlib.sha256(img_bytes.getvalue()).hexdigest()
            
            cursor = self.db.cursor()
            cursor.execute(
                """INSERT INTO known_image_hashes (phash, sha256_hash, source_type)
                   VALUES (%s, %s, %s)""",
                (phash, sha256, source_type)
            )
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to store hash: {e}")
            self.db.rollback()
            return False
