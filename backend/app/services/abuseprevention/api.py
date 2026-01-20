"""
Flask API for Image Validation.

Provides a single endpoint for validating images through the abuse prevention system.
"""

import os
import logging
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

from .config import Config, get_config
from .service import ImageValidationService, get_db_connection
from .models import create_tables

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Load configuration
config = get_config()
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def get_validation_service() -> ImageValidationService:
    """Get an instance of the validation service with database connection."""
    try:
        db_conn = get_db_connection(config)
        # Ensure tables exist
        create_tables(db_conn)
        return ImageValidationService(db_connection=db_conn, config=config)
    except Exception as e:
        logger.warning(f"Could not connect to database: {e}. Running without DB.")
        return ImageValidationService(db_connection=None, config=config)


@app.route('/api/v1/validate-image', methods=['POST'])
def validate_image():
    """
    Validate an image through the abuse prevention system.
    
    Request:
        - image: file upload (multipart/form-data)
        - latitude: float (user's current latitude)
        - longitude: float (user's current longitude)
    
    Response:
        {
            "success": true/false,
            "data": {
                "is_valid": true/false,
                "overall_score": 0-100,
                "checks": {
                    "ai_detection": {...},
                    "exif_freshness": {...},
                    "gps_match": {...},
                    "web_existence": {...}
                },
                "reasons": [...],
                "image_hash": "...",
                "phash": "..."
            },
            "error": null or "error message"
        }
    """
    try:
        # Validate request has image
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'data': None,
                'error': 'No image file provided. Use form field "image".'
            }), 400
        
        image_file = request.files['image']
        
        if image_file.filename == '':
            return jsonify({
                'success': False,
                'data': None,
                'error': 'No image file selected.'
            }), 400
        
        # Validate file extension
        if not Config.is_allowed_file(image_file.filename):
            return jsonify({
                'success': False,
                'data': None,
                'error': f'Invalid file type. Allowed: {", ".join(Config.ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Get user location
        try:
            latitude = float(request.form.get('latitude'))
            longitude = float(request.form.get('longitude'))
        except (TypeError, ValueError):
            return jsonify({
                'success': False,
                'data': None,
                'error': 'Invalid or missing latitude/longitude. Both must be valid floats.'
            }), 400
        
        # Validate coordinate ranges
        if not (-90 <= latitude <= 90):
            return jsonify({
                'success': False,
                'data': None,
                'error': 'Latitude must be between -90 and 90.'
            }), 400
        
        if not (-180 <= longitude <= 180):
            return jsonify({
                'success': False,
                'data': None,
                'error': 'Longitude must be between -180 and 180.'
            }), 400
        
        # Read image data
        image_data = image_file.read()
        
        # Get validation service and validate
        service = get_validation_service()
        result = service.validate_image(
            image_data=image_data,
            user_latitude=latitude,
            user_longitude=longitude,
            store_hash=True
        )
        
        # Return result
        return jsonify({
            'success': True,
            'data': result.to_dict(),
            'error': None
        }), 200 if result.is_valid else 422
        
    except Exception as e:
        logger.error(f"Validation endpoint error: {str(e)}")
        return jsonify({
            'success': False,
            'data': None,
            'error': f'Internal server error: {str(e)}'
        }), 500


@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    db_status = "unknown"
    
    try:
        db_conn = get_db_connection(config)
        cursor = db_conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        db_conn.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return jsonify({
        'status': 'healthy',
        'service': 'abuse-prevention',
        'database': db_status,
        'version': '2.0.0'
    })


@app.route('/api/v1/info', methods=['GET'])
def api_info():
    """Get API information and configuration."""
    return jsonify({
        'name': 'SUDHAR Abuse Prevention API',
        'version': '2.0.0',
        'description': 'Image validation service with AI detection, EXIF validation, GPS matching, and web existence checks.',
        'endpoints': {
            'POST /api/v1/validate-image': 'Validate an image',
            'GET /api/v1/health': 'Health check',
            'GET /api/v1/info': 'API information'
        },
        'configuration': {
            'max_photo_age_hours': config.MAX_PHOTO_AGE_HOURS,
            'gps_max_distance_km': config.GPS_MAX_DISTANCE_KM,
            'ai_detection_threshold': config.AI_DETECTION_THRESHOLD,
            'allowed_extensions': list(config.ALLOWED_EXTENSIONS)
        }
    })


# Initialize database tables on startup
def init_db():
    """Initialize database tables."""
    try:
        db_conn = get_db_connection(config)
        create_tables(db_conn)
        db_conn.close()
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.warning(f"Could not initialize database: {e}")


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)