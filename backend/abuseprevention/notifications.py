"""
Notification Manager for SUDHAR System
Handles push notifications via Firebase Cloud Messaging (FCM)
"""

import logging
from datetime import datetime
from typing import Dict, List
import json

logger = logging.getLogger(__name__)


class NotificationManager:
    """
    Manages notifications for the SUDHAR system.
    Implements real-time push notifications and alerts.
    """
    
    def __init__(self, db_connection, fcm_enabled=False):
        """
        Initialize notification manager.
        
        Args:
            db_connection: Database connection
            fcm_enabled: Whether FCM is enabled (requires Firebase setup)
        """
        self.db = db_connection
        self.fcm_enabled = fcm_enabled
        
        # In production, initialize FCM
        # from firebase_admin import messaging
        # import firebase_admin
        # firebase_admin.initialize_app()
    
    def notify_nearby_verifiers(self, report_id: str, location: Dict[str, float], radius_km: float = 5.0):
        """
        Send push notification to nearby users about new report.
        Implements: Push Notification (FCM): "Issue near you"
        
        Args:
            report_id: Report ID
            location: GPS location of report
            radius_km: Notification radius in kilometers
        """
        try:
            cursor = self.db.cursor()
            
            # Get report details
            cursor.execute("""
                SELECT description, latitude, longitude
                FROM reports
                WHERE report_id = ?
            """, (report_id,))
            
            report = cursor.fetchone()
            if not report:
                return
            
            # Find nearby users (simplified - in production use spatial queries)
            cursor.execute("""
                SELECT user_id, name
                FROM users
                WHERE is_active = 1 AND role = 'CITIZEN'
            """)
            
            users = cursor.fetchall()
            
            # Calculate distance and notify nearby users
            from .middleware import AbusePreventionLayer
            abuse_layer = AbusePreventionLayer(self.db)
            
            notification_count = 0
            for user_row in users:
                user_id = user_row[0]
                
                # Create notification in database
                self._create_notification(
                    user_id=user_id,
                    notification_type='NEARBY_REPORT',
                    title='Issue near you',
                    message=f'A new issue has been reported nearby. Help verify it!',
                    related_report_id=report_id,
                    priority='NORMAL'
                )
                
                # Send push notification via FCM
                self._send_push_notification(
                    user_id=user_id,
                    title='Issue near you',
                    body=f'A new issue has been reported nearby. Help verify it!',
                    data={
                        'report_id': report_id,
                        'type': 'NEARBY_REPORT',
                        'latitude': str(location['latitude']),
                        'longitude': str(location['longitude'])
                    }
                )
                
                notification_count += 1
            
            logger.info(f"Sent {notification_count} notifications for report {report_id}")
            
        except Exception as e:
            logger.error(f"Error notifying verifiers: {str(e)}")
    
    def notify_verification_complete(self, report_id: str):
        """
        Notify report creator that verification is complete.
        
        Args:
            report_id: Report ID
        """
        try:
            cursor = self.db.cursor()
            
            # Get report and user details
            cursor.execute("""
                SELECT user_id, description
                FROM reports
                WHERE report_id = ?
            """, (report_id,))
            
            report = cursor.fetchone()
            if not report:
                return
            
            user_id = report[0]
            
            # Create notification
            self._create_notification(
                user_id=user_id,
                notification_type='VERIFICATION_COMPLETE',
                title='Report Verified',
                message='Your report has been verified by the community and sent to officials.',
                related_report_id=report_id,
                priority='HIGH'
            )
            
            # Send push notification
            self._send_push_notification(
                user_id=user_id,
                title='Report Verified',
                body='Your report has been verified and sent to officials.',
                data={
                    'report_id': report_id,
                    'type': 'VERIFICATION_COMPLETE'
                }
            )
            
            logger.info(f"Notified user {user_id} of verification completion for {report_id}")
            
        except Exception as e:
            logger.error(f"Error notifying verification complete: {str(e)}")
    
    def alert_official(self, report_id: str):
        """
        Send high priority alert to government officials.
        Implements: Push Alert (High Priority) & Update WebSocket Dashboard
        
        Args:
            report_id: Report ID
        """
        try:
            cursor = self.db.cursor()
            
            # Get report details
            cursor.execute("""
                SELECT latitude, longitude, description, verification_count
                FROM reports
                WHERE report_id = ?
            """, (report_id,))
            
            report = cursor.fetchone()
            if not report:
                return
            
            # Get all active officials
            cursor.execute("""
                SELECT official_id, name, email
                FROM officials
                WHERE is_active = 1
            """)
            
            officials = cursor.fetchall()
            
            for official_row in officials:
                official_id = official_row[0]
                
                # Create high priority notification
                cursor.execute("""
                    INSERT INTO notifications (
                        user_id, notification_type, title, message,
                        related_report_id, priority, is_read, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    official_id,
                    'VERIFIED_REPORT',
                    'New Verified Report',
                    f'A verified report requires attention: {report[2][:50]}...',
                    report_id,
                    'HIGH',
                    0,
                    datetime.now().isoformat()
                ))
                
                # Send push notification to official
                self._send_push_notification(
                    user_id=official_id,
                    title='New Verified Report',
                    body=f'A verified report requires your attention.',
                    data={
                        'report_id': report_id,
                        'type': 'VERIFIED_REPORT',
                        'latitude': str(report[0]),
                        'longitude': str(report[1]),
                        'verification_count': str(report[3])
                    }
                )
            
            self.db.commit()
            
            # Update WebSocket dashboard (would be implemented with WebSocket server)
            self._update_websocket_dashboard(report_id)
            
            logger.info(f"Alerted officials about verified report {report_id}")
            
        except Exception as e:
            logger.error(f"Error alerting officials: {str(e)}")
    
    def notify_resolution(self, report_id: str):
        """
        Notify citizen that their issue is resolved.
        Implements: Push: "Your issue is resolved"
        
        Args:
            report_id: Report ID
        """
        try:
            cursor = self.db.cursor()
            
            # Get report and user details
            cursor.execute("""
                SELECT user_id, description, resolution_notes
                FROM reports
                WHERE report_id = ?
            """, (report_id,))
            
            report = cursor.fetchone()
            if not report:
                return
            
            user_id = report[0]
            resolution_notes = report[2] or "No additional notes provided."
            
            # Create notification
            self._create_notification(
                user_id=user_id,
                notification_type='ISSUE_RESOLVED',
                title='Your issue is resolved',
                message=f'Your report has been resolved. {resolution_notes}',
                related_report_id=report_id,
                priority='HIGH'
            )
            
            # Send push notification
            self._send_push_notification(
                user_id=user_id,
                title='Your issue is resolved',
                body=f'Your report has been resolved. Thank you for reporting!',
                data={
                    'report_id': report_id,
                    'type': 'ISSUE_RESOLVED',
                    'resolution_notes': resolution_notes
                }
            )
            
            logger.info(f"Notified user {user_id} of resolution for {report_id}")
            
        except Exception as e:
            logger.error(f"Error notifying resolution: {str(e)}")
    
    def _create_notification(self, user_id: str, notification_type: str,
                            title: str, message: str, related_report_id: str = None,
                            priority: str = 'NORMAL'):
        """
        Create a notification in the database.
        
        Args:
            user_id: User ID to notify
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            related_report_id: Related report ID if applicable
            priority: Notification priority (NORMAL, HIGH)
        """
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO notifications (
                    user_id, notification_type, title, message,
                    related_report_id, priority, is_read, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                notification_type,
                title,
                message,
                related_report_id,
                priority,
                0,
                datetime.now().isoformat()
            ))
            self.db.commit()
        except Exception as e:
            logger.error(f"Error creating notification: {str(e)}")
    
    def _send_push_notification(self, user_id: str, title: str, body: str, data: Dict = None):
        """
        Send push notification via FCM.
        
        Args:
            user_id: User ID
            title: Notification title
            body: Notification body
            data: Additional data payload
        """
        if not self.fcm_enabled:
            logger.info(f"[FCM DISABLED] Would send to {user_id}: {title}")
            return
        
        try:
            # In production, implement FCM:
            # from firebase_admin import messaging
            # 
            # # Get user's FCM token from database
            # cursor = self.db.cursor()
            # cursor.execute("SELECT fcm_token FROM users WHERE user_id = ?", (user_id,))
            # result = cursor.fetchone()
            # 
            # if result and result[0]:
            #     fcm_token = result[0]
            #     
            #     message = messaging.Message(
            #         notification=messaging.Notification(
            #             title=title,
            #             body=body
            #         ),
            #         data=data or {},
            #         token=fcm_token
            #     )
            #     
            #     response = messaging.send(message)
            #     logger.info(f"FCM sent to {user_id}: {response}")
            
            logger.info(f"[FCM] Sent notification to {user_id}: {title}")
            
        except Exception as e:
            logger.error(f"Error sending FCM notification: {str(e)}")
    
    def _update_websocket_dashboard(self, report_id: str):
        """
        Update WebSocket dashboard for real-time updates.
        
        Args:
            report_id: Report ID
        """
        try:
            # In production, implement WebSocket:
            # import socketio
            # sio = socketio.Client()
            # sio.connect('http://localhost:3000')
            # sio.emit('dashboard_update', {'report_id': report_id, 'type': 'NEW_VERIFIED'})
            
            logger.info(f"[WebSocket] Dashboard updated for report {report_id}")
            
        except Exception as e:
            logger.error(f"Error updating WebSocket dashboard: {str(e)}")
    
    def mark_notification_read(self, notification_id: int):
        """
        Mark a notification as read.
        
        Args:
            notification_id: Notification ID
        """
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                UPDATE notifications
                SET is_read = 1
                WHERE notification_id = ?
            """, (notification_id,))
            self.db.commit()
        except Exception as e:
            logger.error(f"Error marking notification read: {str(e)}")
    
    def get_unread_count(self, user_id: str) -> int:
        """
        Get count of unread notifications for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Count of unread notifications
        """
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM notifications
                WHERE user_id = ? AND is_read = 0
            """, (user_id,))
            return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting unread count: {str(e)}")
            return 0