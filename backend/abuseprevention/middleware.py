"""
SUDHAR Abuse Prevention Middleware
Validates images for authenticity and prevents abuse through EXIF validation,
perceptual hashing, and duplicate detection.
"""

import hashlib
import imagehash
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime
from typing import Dict, Tuple, Optional
import io
import logging

logger = logging.getLogger(__name__)


class AbusePreventionLayer:
    """
    Abuse prevention layer for SUDHAR system.
    Validates images based on EXIF data and perceptual hashing.
    """
    
    def __init__(self, db_connection):
        """
        Initialize abuse prevention layer.
        
        Args:
            db_connection: Database connection object
        """
        self.db = db_connection
        self.verification_threshold = 3  # Number of verifications needed
        
    def validate_image(self, image_data: bytes, gps_location: Dict[str, float]) -> Dict:
        """
        Validate image for abuse prevention.
        
        Args:
            image_data: Raw image bytes
            gps_location: Expected GPS location {'latitude': float, 'longitude': float}
            
        Returns:
            Dict with validation results
        """
        result = {
            'is_valid': True,
            'score': 0,
            'reasons': [],
            'exif_data': {},
            'phash': None
        }
        
        try:
            # Open image
            image = Image.open(io.BytesIO(image_data))
            
            # Extract and validate EXIF data
            exif_validation = self._validate_exif(image, gps_location)
            result['exif_data'] = exif_validation['exif_data']
            result['score'] += exif_validation['score']
            result['reasons'].extend(exif_validation['reasons'])
            
            # Calculate perceptual hash
            phash = self._calculate_phash(image)
            result['phash'] = str(phash)
            
            # Check for duplicates
            duplicate_check = self._check_duplicates(phash)
            result['score'] += duplicate_check['score']
            result['reasons'].extend(duplicate_check['reasons'])
            
            # Determine if image is valid (score >= 0 means valid)
            if result['score'] < -50:
                result['is_valid'] = False
                result['classification'] = 'FAKE'
            elif duplicate_check['is_duplicate']:
                result['is_valid'] = False
                result['classification'] = 'DUPLICATE'
            else:
                result['classification'] = 'REAL'
                
        except Exception as e:
            logger.error(f"Error validating image: {str(e)}")
            result['is_valid'] = False
            result['score'] = -100
            result['reasons'].append(f"Validation error: {str(e)}")
            result['classification'] = 'ERROR'
            
        return result
    
    def _validate_exif(self, image: Image, expected_gps: Dict[str, float]) -> Dict:
        """
        Validate EXIF data against expected GPS location.
        
        Args:
            image: PIL Image object
            expected_gps: Expected GPS coordinates
            
        Returns:
            Dict with EXIF validation results
        """
        result = {
            'score': 0,
            'reasons': [],
            'exif_data': {}
        }
        
        try:
            exif_data = image._getexif()
            
            if not exif_data:
                result['score'] -= 30
                result['reasons'].append("No EXIF data found")
                return result
            
            # Parse EXIF data
            exif = {
                TAGS.get(tag, tag): value
                for tag, value in exif_data.items()
            }
            
            result['exif_data'] = {
                'DateTime': exif.get('DateTime'),
                'Make': exif.get('Make'),
                'Model': exif.get('Model'),
                'Software': exif.get('Software')
            }
            
            # Check for GPS data
            gps_info = exif.get('GPSInfo')
            if gps_info:
                gps_coords = self._parse_gps(gps_info)
                result['exif_data']['GPS'] = gps_coords
                
                # Validate GPS proximity (within ~100 meters)
                if gps_coords and expected_gps:
                    distance = self._calculate_distance(
                        gps_coords['latitude'],
                        gps_coords['longitude'],
                        expected_gps['latitude'],
                        expected_gps['longitude']
                    )
                    
                    if distance < 0.1:  # Within 100 meters
                        result['score'] += 50
                        result['reasons'].append("GPS location matches")
                    else:
                        result['score'] -= 40
                        result['reasons'].append(f"GPS mismatch: {distance:.2f}km away")
            else:
                result['score'] -= 20
                result['reasons'].append("No GPS data in EXIF")
            
            # Check timestamp
            if 'DateTime' in exif:
                try:
                    photo_time = datetime.strptime(exif['DateTime'], '%Y:%m:%d %H:%M:%S')
                    time_diff = abs((datetime.now() - photo_time).total_seconds())
                    
                    # Photo should be recent (within 1 hour)
                    if time_diff < 3600:
                        result['score'] += 30
                        result['reasons'].append("Recent photo timestamp")
                    elif time_diff < 86400:  # Within 24 hours
                        result['score'] += 10
                        result['reasons'].append("Photo taken within 24 hours")
                    else:
                        result['score'] -= 20
                        result['reasons'].append("Old photo timestamp")
                except:
                    pass
            
            # Check for camera make/model
            if 'Make' in exif and 'Model' in exif:
                result['score'] += 10
                result['reasons'].append("Camera metadata present")
                
        except Exception as e:
            logger.error(f"EXIF validation error: {str(e)}")
            result['score'] -= 25
            result['reasons'].append("EXIF parsing error")
            
        return result
    
    def _parse_gps(self, gps_info: Dict) -> Optional[Dict[str, float]]:
        """Parse GPS coordinates from EXIF GPS info."""
        try:
            def convert_to_degrees(value):
                d, m, s = value
                return float(d) + float(m) / 60 + float(s) / 3600
            
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
        except:
            pass
        return None
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two GPS coordinates using Haversine formula.
        Returns distance in kilometers.
        """
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # Earth's radius in kilometers
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    def _calculate_phash(self, image: Image) -> imagehash.ImageHash:
        """
        Calculate perceptual hash of image.
        
        Args:
            image: PIL Image object
            
        Returns:
            Perceptual hash
        """
        return imagehash.phash(image, hash_size=16)
    
    def _check_duplicates(self, phash: imagehash.ImageHash) -> Dict:
        """
        Check if image is a duplicate based on perceptual hash.
        
        Args:
            phash: Perceptual hash of image
            
        Returns:
            Dict with duplicate check results
        """
        result = {
            'score': 0,
            'reasons': [],
            'is_duplicate': False
        }
        
        try:
            # Query database for similar hashes
            # Using hamming distance threshold of 5 for similarity
            cursor = self.db.cursor()
            cursor.execute("""
                SELECT phash, report_id FROM reports 
                WHERE status != 'REJECTED'
            """)
            
            for row in cursor.fetchall():
                existing_hash = imagehash.hex_to_hash(row[0])
                hamming_distance = phash - existing_hash
                
                if hamming_distance <= 5:
                    result['is_duplicate'] = True
                    result['score'] -= 60
                    result['reasons'].append(f"Duplicate image detected (similarity: {100 - hamming_distance * 10}%)")
                    result['duplicate_report_id'] = row[1]
                    break
                    
        except Exception as e:
            logger.error(f"Duplicate check error: {str(e)}")
            
        return result
    
    def compare_verification_photos(self, original_phash: str, verification_phash: str) -> Dict:
        """
        Compare original report photo with verification photo.
        
        Args:
            original_phash: Perceptual hash of original photo
            verification_phash: Perceptual hash of verification photo
            
        Returns:
            Dict with similarity results
        """
        try:
            hash1 = imagehash.hex_to_hash(original_phash)
            hash2 = imagehash.hex_to_hash(verification_phash)
            
            hamming_distance = hash1 - hash2
            similarity_percentage = 100 - (hamming_distance * 5)
            
            # Images should be similar (same location) but not identical
            is_similar = 10 <= hamming_distance <= 25
            
            return {
                'is_similar': is_similar,
                'similarity_percentage': max(0, similarity_percentage),
                'hamming_distance': hamming_distance,
                'valid_verification': is_similar
            }
        except Exception as e:
            logger.error(f"Photo comparison error: {str(e)}")
            return {
                'is_similar': False,
                'similarity_percentage': 0,
                'hamming_distance': 100,
                'valid_verification': False
            }


class ReportVerificationManager:
    """
    Manages the verification workflow for reports.
    """
    
    def __init__(self, db_connection):
        """
        Initialize verification manager.
        
        Args:
            db_connection: Database connection object
        """
        self.db = db_connection
        self.verification_threshold = 3
        
    def create_report(self, user_id: str, image_validation: Dict, 
                     location: Dict, description: str) -> str:
        """
        Create a new report with validation data.
        
        Args:
            user_id: User ID creating the report
            image_validation: Validation results from AbusePreventionLayer
            location: GPS location
            description: Report description
            
        Returns:
            Report ID
        """
        try:
            cursor = self.db.cursor()
            
            report_id = hashlib.sha256(
                f"{user_id}{datetime.now().isoformat()}".encode()
            ).hexdigest()[:16]
            
            cursor.execute("""
                INSERT INTO reports (
                    report_id, user_id, phash, validation_score,
                    classification, latitude, longitude, description,
                    status, verification_count, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                report_id,
                user_id,
                image_validation['phash'],
                image_validation['score'],
                image_validation['classification'],
                location['latitude'],
                location['longitude'],
                description,
                'PENDING' if image_validation['is_valid'] else 'REJECTED',
                0,
                datetime.now().isoformat()
            ))
            
            self.db.commit()
            return report_id
            
        except Exception as e:
            logger.error(f"Error creating report: {str(e)}")
            self.db.rollback()
            raise
    
    def submit_verification(self, report_id: str, verifier_id: str,
                           verification_photo_hash: str, comment: str) -> Dict:
        """
        Submit a verification for a report.
        
        Args:
            report_id: Report ID being verified
            verifier_id: User ID of verifier
            verification_photo_hash: Perceptual hash of verification photo
            comment: Verifier's comment
            
        Returns:
            Dict with verification results
        """
        try:
            cursor = self.db.cursor()
            
            # Get original report
            cursor.execute("""
                SELECT phash, verification_count FROM reports
                WHERE report_id = %s
            """, (report_id,))
            
            result = cursor.fetchone()
            if not result:
                return {'success': False, 'error': 'Report not found'}
            
            original_phash, verification_count = result
            
            # Compare photos
            abuse_layer = AbusePreventionLayer(self.db)
            comparison = abuse_layer.compare_verification_photos(
                original_phash, verification_photo_hash
            )
            
            # Record verification
            cursor.execute("""
                INSERT INTO verifications (
                    report_id, verifier_id, verification_phash,
                    similarity_score, comment, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                report_id,
                verifier_id,
                verification_photo_hash,
                comparison['similarity_percentage'],
                comment,
                datetime.now().isoformat()
            ))
            
            # Update verification count if valid
            if comparison['valid_verification']:
                new_count = verification_count + 1
                cursor.execute("""
                    UPDATE reports
                    SET verification_count = %s
                    WHERE report_id = %s
                """, (new_count, report_id))
                
                # Check if threshold reached
                if new_count >= self.verification_threshold:
                    cursor.execute("""
                        UPDATE reports
                        SET status = 'VERIFIED'
                        WHERE report_id = %s
                    """, (report_id,))
            
            self.db.commit()
            
            return {
                'success': True,
                'verification_count': verification_count + 1 if comparison['valid_verification'] else verification_count,
                'similarity': comparison['similarity_percentage'],
                'valid': comparison['valid_verification'],
                'threshold_reached': verification_count + 1 >= self.verification_threshold
            }
            
        except Exception as e:
            logger.error(f"Error submitting verification: {str(e)}")
            self.db.rollback()
            return {'success': False, 'error': str(e)}
    
    def get_nearby_reports(self, latitude: float, longitude: float, 
                          radius_km: float = 5.0) -> list:
        """
        Get unverified reports near a location.
        
        Args:
            latitude: User's latitude
            longitude: User's longitude
            radius_km: Search radius in kilometers
            
        Returns:
            List of nearby reports needing verification
        """
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                SELECT report_id, latitude, longitude, description,
                       verification_count, created_at
                FROM reports
                WHERE status = 'PENDING'
                AND verification_count < ?
            """, (self.verification_threshold,))
            
            nearby_reports = []
            abuse_layer = AbusePreventionLayer(self.db)
            
            for row in cursor.fetchall():
                distance = abuse_layer._calculate_distance(
                    latitude, longitude, row[1], row[2]
                )
                
                if distance <= radius_km:
                    nearby_reports.append({
                        'report_id': row[0],
                        'latitude': row[1],
                        'longitude': row[2],
                        'description': row[3],
                        'verification_count': row[4],
                        'created_at': row[5],
                        'distance_km': round(distance, 2)
                    })
            
            # Sort by distance
            nearby_reports.sort(key=lambda x: x['distance_km'])
            
            return nearby_reports
            
        except Exception as e:
            logger.error(f"Error fetching nearby reports: {str(e)}")
            return []