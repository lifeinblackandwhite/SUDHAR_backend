"""
Test suite for SUDHAR Abuse Prevention System
"""

import unittest
import psycopg2
import sys, pathlib
# Ensure project root is on sys.path for absolute imports
ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
from psycopg2.extras import RealDictCursor
import importlib
abp = importlib.import_module('backend.abuseprevention')
sys.modules['abuseprevention'] = abp
from backend.abuseprevention.database import get_pg_connection, create_abuse_prevention_tables_pg
import io
import os
from datetime import datetime
from PIL import Image
import imagehash

from backend.abuseprevention.middleware import AbusePreventionLayer, ReportVerificationManager
from backend.abuseprevention.notifications import NotificationManager
from backend.abuseprevention.database import initialize_database


class TestAbusePreventionLayer(unittest.TestCase):
    """Test cases for AbusePreventionLayer."""
    
    def setUp(self):
        """Set up test database."""
        self.db = get_pg_connection()
        create_abuse_prevention_tables_pg(self.db)
        self.abuse_layer = AbusePreventionLayer(self.db)
    
    def tearDown(self):
        """Clean up."""
        self.db.close()
    
    def create_test_image(self, size=(800, 600), color=(255, 0, 0)):
        """Create a test image."""
        img = Image.new('RGB', size, color=color)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        return img_bytes.getvalue()
    
    def test_calculate_phash(self):
        """Test perceptual hash calculation."""
        image_data = self.create_test_image()
        image = Image.open(io.BytesIO(image_data))
        phash = self.abuse_layer._calculate_phash(image)
        
        self.assertIsInstance(phash, imagehash.ImageHash)
        self.assertEqual(len(str(phash)), 64)  # 16x16 hash = 256 bits = 64 hex chars
    
    def test_calculate_distance(self):
        """Test GPS distance calculation."""
        # New Delhi to Mumbai (approximately 1150 km)
        distance = self.abuse_layer._calculate_distance(
            28.6139, 77.2090,  # New Delhi
            19.0760, 72.8777   # Mumbai
        )
        
        self.assertGreater(distance, 1100)
        self.assertLess(distance, 1200)
    
    def test_duplicate_detection(self):
        """Test duplicate image detection."""
        # Create first report
        cursor = self.db.cursor()
        test_phash = "0123456789abcdef" * 4
        
        cursor.execute("""
            INSERT INTO reports (
                report_id, user_id, phash, validation_score,
                classification, latitude, longitude, description,
                status, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, ('report1', 'user1', test_phash, 100, 'REAL',
              28.6139, 77.2090, 'Test', 'PENDING', datetime.now().isoformat()))
        self.db.commit()
        
        # Check for duplicate
        phash = imagehash.hex_to_hash(test_phash)
        result = self.abuse_layer._check_duplicates(phash)
        
        self.assertTrue(result['is_duplicate'])
        self.assertLess(result['score'], 0)
    
    def test_photo_comparison(self):
        """Test verification photo comparison."""
        # Create two similar hashes
        hash1 = "0123456789abcdef" * 4
        hash2 = "0123456789abcdef" * 4  # Identical
        
        result = self.abuse_layer.compare_verification_photos(hash1, hash2)
        
        self.assertFalse(result['is_similar'])  # Too similar (identical)
        self.assertEqual(result['hamming_distance'], 0)


class TestReportVerificationManager(unittest.TestCase):
    """Test cases for ReportVerificationManager."""
    
    def setUp(self):
        """Set up test database."""
        self.db = get_pg_connection()
        create_abuse_prevention_tables_pg(self.db)
        self.manager = ReportVerificationManager(self.db)
    
    def tearDown(self):
        """Clean up."""
        self.db.close()
    
    def test_create_report(self):
        """Test report creation."""
        validation_result = {
            'is_valid': True,
            'phash': '0123456789abcdef' * 4,
            'score': 80,
            'classification': 'REAL'
        }
        
        location = {'latitude': 28.6139, 'longitude': 77.2090}
        
        report_id = self.manager.create_report(
            user_id='test_user',
            image_validation=validation_result,
            location=location,
            description='Test report'
        )
        
        self.assertIsNotNone(report_id)
        self.assertEqual(len(report_id), 16)
        
        # Verify in database
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM reports WHERE report_id = %s", (report_id,))
        report = cursor.fetchone()
        
        self.assertIsNotNone(report)
    
    def test_verification_threshold(self):
        """Test verification threshold logic."""
        # Create a report first
        validation_result = {
            'is_valid': True,
            'phash': '0123456789abcdef' * 4,
            'score': 80,
            'classification': 'REAL'
        }
        
        location = {'latitude': 28.6139, 'longitude': 77.2090}
        report_id = self.manager.create_report(
            'test_user', validation_result, location, 'Test'
        )
        
        # Submit 3 verifications
        for i in range(3):
            result = self.manager.submit_verification(
                report_id=report_id,
                verifier_id=f'verifier_{i}',
                verification_photo_hash='fedcba9876543210' * 4,
                comment=f'Verification {i+1}'
            )
            
            if i < 2:
                self.assertFalse(result.get('threshold_reached', False))
            else:
                self.assertTrue(result.get('threshold_reached', False))


class TestNotificationManager(unittest.TestCase):
    """Test cases for NotificationManager."""
    
    def setUp(self):
        """Set up test database."""
        self.db = get_pg_connection()
        create_abuse_prevention_tables_pg(self.db)
        self.notification_manager = NotificationManager(self.db, fcm_enabled=False)
    
    def tearDown(self):
        """Clean up."""
        self.db.close()
    
    def test_create_notification(self):
        """Test notification creation."""
        # Create a test user
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, phone_number, name, role, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, ('test_user', '1234567890', 'Test User', 'CITIZEN', datetime.now().isoformat()))
        self.db.commit()
        
        # Create notification
        self.notification_manager._create_notification(
            user_id='test_user',
            notification_type='TEST',
            title='Test Notification',
            message='This is a test',
            priority='NORMAL'
        )
        
        # Verify
        cursor.execute("SELECT * FROM notifications WHERE user_id = %s", ('test_user',))
        notification = cursor.fetchone()
        
        self.assertIsNotNone(notification)
    
    def test_unread_count(self):
        """Test unread notification count."""
        # Create test user
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, phone_number, name, role, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, ('test_user', '1234567890', 'Test User', 'CITIZEN', datetime.now().isoformat()))
        
        # Create notifications
        for i in range(3):
            self.notification_manager._create_notification(
                user_id='test_user',
                notification_type='TEST',
                title=f'Notification {i}',
                message='Test',
                priority='NORMAL'
            )
        
        count = self.notification_manager.get_unread_count('test_user')
        self.assertEqual(count, 3)
        
        # Mark one as read
        cursor.execute("SELECT notification_id FROM notifications LIMIT 1")
        notif_id = cursor.fetchone()[0]
        self.notification_manager.mark_notification_read(notif_id)
        
        count = self.notification_manager.get_unread_count('test_user')
        self.assertEqual(count, 2)


class TestDatabaseSchema(unittest.TestCase):
    """Test database schema."""
    
    def test_tables_created(self):
        """Test that all tables are created."""
        db = get_pg_connection()
        create_abuse_prevention_tables_pg(db)
        
        cursor = db.cursor()
        cursor.execute("SELECT name FROM pg_tables WHERE schemaname='public'")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = [
            'reports', 'verifications', 'image_metadata',
            'users', 'officials', 'notifications', 'abuse_logs'
        ]
        
        for table in required_tables:
            self.assertIn(table, tables)
        
        db.close()
    
    def test_indexes_created(self):
        """Test that indexes are created."""
        db = get_pg_connection()
        create_abuse_prevention_tables_pg(db)
        required_tables = ('reports','verifications','image_metadata','users','officials','notifications','abuse_logs')
        cursor = db.cursor()
        cursor.execute("SELECT indexname FROM pg_indexes WHERE tablename IN %s", (required_tables,))
        indexes = [row[0] for row in cursor.fetchall()]
        
        self.assertIn('idx_reports_phash', indexes)
        self.assertIn('idx_reports_status', indexes)
        
        db.close()


class TestIntegration(unittest.TestCase):
    """Integration tests."""
    
    def setUp(self):
        """Set up test environment."""
        self.db = get_pg_connection()
        create_abuse_prevention_tables_pg(self.db)
        
        # Create test user
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO users (user_id, phone_number, name, role, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, ('test_user', '1234567890', 'Test User', 'CITIZEN', datetime.now().isoformat()))
        self.db.commit()
    
    def tearDown(self):
        """Clean up."""
        self.db.close()
    
    def test_full_workflow(self):
        """Test complete workflow from report to verification."""
        abuse_layer = AbusePreventionLayer(self.db)
        verification_manager = ReportVerificationManager(self.db)
        
        # Create report
        validation_result = {
            'is_valid': True,
            'phash': '0123456789abcdef' * 4,
            'score': 80,
            'classification': 'REAL'
        }
        
        location = {'latitude': 28.6139, 'longitude': 77.2090}
        report_id = verification_manager.create_report(
            'test_user', validation_result, location, 'Integration test'
        )
        
        self.assertIsNotNone(report_id)
        
        # Get nearby reports
        nearby = verification_manager.get_nearby_reports(28.6140, 77.2091, 1.0)
        self.assertEqual(len(nearby), 1)
        self.assertEqual(nearby[0]['report_id'], report_id)


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestAbusePreventionLayer))
    suite.addTests(loader.loadTestsFromTestCase(TestReportVerificationManager))
    suite.addTests(loader.loadTestsFromTestCase(TestNotificationManager))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseSchema))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)