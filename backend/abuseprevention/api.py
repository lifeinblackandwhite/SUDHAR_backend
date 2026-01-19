"""
Flask API Routes for SUDHAR Abuse Prevention System
Implements the API endpoints as per the architecture flowchart
"""

from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import psycopg2
from psycopg2.extras import RealDictCursor
from app.core.config import DATABASE_URL
import os
import logging
from datetime import datetime
from typing import Dict
import io

from .middleware import AbusePreventionLayer, ReportVerificationManager
from .notifications import NotificationManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DATABASE_URL'] = DATABASE_URL

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def get_db():
    """Get Postgres database connection."""
    conn = psycopg2.connect(app.config['DATABASE_URL'], cursor_factory=RealDictCursor)
    return conn


@app.route('/api/report/create', methods=['POST'])
def create_report():
    """
    POST /report/create
    Create a new issue report with photo, GPS, and description.
    Implements the ABUSE PREVENTION LAYER.
    """
    try:
        # Validate request
        if 'photo' not in request.files:
            return jsonify({'error': 'No photo provided'}), 400
        
        photo = request.files['photo']
        if photo.filename == '':
            return jsonify({'error': 'No photo selected'}), 400
        
        # Get form data
        user_id = request.form.get('user_id')
        latitude = float(request.form.get('latitude'))
        longitude = float(request.form.get('longitude'))
        description = request.form.get('description', '')
        
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400
        
        # Read image data
        image_data = photo.read()
        
        # Initialize abuse prevention layer
        db = get_db()
        abuse_layer = AbusePreventionLayer(db)
        
        # Validate EXIF and calculate pHash
        gps_location = {'latitude': latitude, 'longitude': longitude}
        validation_result = abuse_layer.validate_image(image_data, gps_location)
        
        # Store validation result
        logger.info(f"Image validation: {validation_result['classification']} "
                   f"(score: {validation_result['score']})")
        
        # Create report if valid
        if validation_result['is_valid']:
            verification_manager = ReportVerificationManager(db)
            report_id = verification_manager.create_report(
                user_id=user_id,
                image_validation=validation_result,
                location=gps_location,
                description=description
            )
            
            # Save image file
            filename = f"{report_id}_original.jpg"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            # Store image metadata
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO image_metadata (
                    report_id, image_type, exif_datetime, exif_make, exif_model,
                    gps_latitude, gps_longitude, file_hash, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                report_id,
                'ORIGINAL',
                validation_result['exif_data'].get('DateTime'),
                validation_result['exif_data'].get('Make'),
                validation_result['exif_data'].get('Model'),
                gps_location.get('latitude'),
                gps_location.get('longitude'),
                validation_result['phash'],
                datetime.now().isoformat()
            ))
            db.commit()
            
            # Send real-time notification to nearby verifiers
            notification_manager = NotificationManager(db)
            notification_manager.notify_nearby_verifiers(report_id, gps_location)
            
            db.close()
            
            return jsonify({
                'success': True,
                'report_id': report_id,
                'status': 'PENDING',
                'validation': {
                    'score': validation_result['score'],
                    'classification': validation_result['classification'],
                    'reasons': validation_result['reasons']
                }
            }), 201
        else:
            # Report rejected due to abuse detection
            db.close()
            
            return jsonify({
                'success': False,
                'error': 'Report rejected',
                'classification': validation_result['classification'],
                'reasons': validation_result['reasons'],
                'score': validation_result['score']
            }), 400
            
    except Exception as e:
        logger.error(f"Error creating report: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500


@app.route('/api/report/verify', methods=['POST'])
def verify_report():
    """
    POST /report/verify
    Submit verification photo and comment for a report.
    Compares C1 vs C2 photos (Similarity Check).
    """
    try:
        # Validate request
        if 'photo' not in request.files:
            return jsonify({'error': 'No verification photo provided'}), 400
        
        photo = request.files['photo']
        report_id = request.form.get('report_id')
        verifier_id = request.form.get('verifier_id')
        comment = request.form.get('comment', '')
        
        if not report_id or not verifier_id:
            return jsonify({'error': 'Report ID and Verifier ID required'}), 400
        
        # Read image data
        image_data = photo.read()
        
        # Calculate perceptual hash
        from PIL import Image
        import imagehash
        image = Image.open(io.BytesIO(image_data))
        verification_phash = str(imagehash.phash(image, hash_size=16))
        
        # Submit verification
        db = get_db()
        verification_manager = ReportVerificationManager(db)
        result = verification_manager.submit_verification(
            report_id=report_id,
            verifier_id=verifier_id,
            verification_photo_hash=verification_phash,
            comment=comment
        )
        
        if result['success']:
            # Save verification photo
            filename = f"{report_id}_verify_{verifier_id}.jpg"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            # Update user statistics
            cursor = db.cursor()
            cursor.execute("""
                UPDATE users 
                SET verifications_completed = verifications_completed + 1
                WHERE user_id = %s
            """, (verifier_id,))
            db.commit()
            
            # Check if verification threshold reached
            if result['threshold_reached']:
                # Update status to VERIFIED
                notification_manager = NotificationManager(db)
                notification_manager.notify_verification_complete(report_id)
                notification_manager.alert_official(report_id)
        
        db.close()
        
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        logger.error(f"Error verifying report: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500


@app.route('/api/reports/nearby', methods=['GET'])
def get_nearby_reports():
    """
    GET /reports/nearby
    Get unverified reports near user's location for verification.
    Used for "View Request & Navigate to Location" flow.
    """
    try:
        latitude = float(request.args.get('latitude'))
        longitude = float(request.args.get('longitude'))
        radius = float(request.args.get('radius', 5.0))
        
        db = get_db()
        verification_manager = ReportVerificationManager(db)
        nearby_reports = verification_manager.get_nearby_reports(
            latitude, longitude, radius
        )
        db.close()
        
        return jsonify({
            'success': True,
            'count': len(nearby_reports),
            'reports': nearby_reports
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching nearby reports: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500


@app.route('/api/report/<report_id>', methods=['GET'])
def get_report_details(report_id):
    """
    GET /report/<report_id>
    Get details of a specific report.
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            SELECT r.*, u.name as reporter_name, u.phone_number
            FROM reports r
            JOIN users u ON r.user_id = u.user_id
            WHERE r.report_id = %s
        """, (report_id,))
        
        report = cursor.fetchone()
        
        if not report:
            db.close()
            return jsonify({'error': 'Report not found'}), 404
        
        # Get verifications
        cursor.execute("""
            SELECT v.*, u.name as verifier_name
            FROM verifications v
            JOIN users u ON v.verifier_id = u.user_id
            WHERE v.report_id = %s
            ORDER BY v.created_at DESC
        """, (report_id,))
        
        verifications = cursor.fetchall()
        
        db.close()
        
        return jsonify({
            'success': True,
            'report': dict(report),
            'verifications': [dict(v) for v in verifications]
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching report details: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500


@app.route('/api/official/dashboard', methods=['GET'])
def official_dashboard():
    """
    GET /official/dashboard
    Get verified reports for official action.
    Filtered by verified status.
    """
    try:
        official_id = request.args.get('official_id')
        status_filter = request.args.get('status', 'VERIFIED')
        
        db = get_db()
        cursor = db.cursor()
        
        query = """
            SELECT r.*, u.name as reporter_name, u.phone_number,
                   COUNT(v.verification_id) as verification_count
            FROM reports r
            JOIN users u ON r.user_id = u.user_id
            LEFT JOIN verifications v ON r.report_id = v.report_id
            WHERE r.status = %s
        """
        params = [status_filter]
        
        if official_id:
            query += " AND (r.assigned_official_id = %s OR r.assigned_official_id IS NULL)"
            params.append(official_id)
        
        query += " GROUP BY r.report_id ORDER BY r.created_at DESC"
        
        cursor.execute(query, params)
        reports = cursor.fetchall()
        
        db.close()
        
        return jsonify({
            'success': True,
            'count': len(reports),
            'reports': [dict(r) for r in reports]
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching dashboard: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500


@app.route('/api/official/update-status', methods=['POST'])
def update_report_status():
    """
    POST /official/update-status
    Official updates report status (In Progress/Resolved).
    """
    try:
        data = request.get_json()
        report_id = data.get('report_id')
        official_id = data.get('official_id')
        new_status = data.get('status')
        notes = data.get('notes', '')
        
        if not all([report_id, official_id, new_status]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        if new_status not in ['IN_PROGRESS', 'RESOLVED', 'REJECTED']:
            return jsonify({'error': 'Invalid status'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            UPDATE reports
            SET status = %s, assigned_official_id = %s, 
                resolution_notes = %s, updated_at = %s
            WHERE report_id = %s
        """, (new_status, official_id, notes, datetime.now().isoformat(), report_id))
        
        db.commit()
        
        # Notify citizen
        if new_status == 'RESOLVED':
            notification_manager = NotificationManager(db)
            notification_manager.notify_resolution(report_id)
        
        db.close()
        
        return jsonify({
            'success': True,
            'report_id': report_id,
            'status': new_status
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating status: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500


@app.route('/api/user/notifications', methods=['GET'])
def get_notifications():
    """
    GET /user/notifications
    Get notifications for a user.
    """
    try:
        user_id = request.args.get('user_id')
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        query = "SELECT * FROM notifications WHERE user_id = %s"
        params = [user_id]
        
        if unread_only:
            query += " AND is_read = 0"
        
        query += " ORDER BY created_at DESC LIMIT 50"
        
        cursor.execute(query, params)
        notifications = cursor.fetchall()
        
        db.close()
        
        return jsonify({
            'success': True,
            'count': len(notifications),
            'notifications': [dict(n) for n in notifications]
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching notifications: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500


@app.route('/api/user/register', methods=['POST'])
def register_user():
    """
    POST /user/register
    Register a new user (Citizen OTP Login).
    """
    try:
        data = request.get_json()
        phone_number = data.get('phone_number')
        name = data.get('name', '')
        email = data.get('email', '')
        
        if not phone_number:
            return jsonify({'error': 'Phone number required'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # Generate user ID
        import hashlib
        user_id = hashlib.sha256(
            f"{phone_number}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        cursor.execute("""
            INSERT INTO users (user_id, phone_number, name, email, created_at, last_login)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, phone_number, name, email, 
              datetime.now().isoformat(), datetime.now().isoformat()))
        
        db.commit()
        db.close()
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'phone_number': phone_number
        }), 201
        
    except psycopg2.IntegrityError:
        return jsonify({'error': 'Phone number already registered'}), 400
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    }), 200


if __name__ == '__main__':
    # Initialize Postgres tables on first run
    from .database import get_pg_connection, create_abuse_prevention_tables_pg
    conn = get_pg_connection()
    create_abuse_prevention_tables_pg(conn)
    conn.close()
    
    # Run Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)