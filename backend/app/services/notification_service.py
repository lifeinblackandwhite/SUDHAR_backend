from app.db.models import Issue
from app.api.integrations.firebase_client import (
    get_users_by_location,
    send_push_notification,
    notify_users,
)

from app.api.ws.community_ws import manager

from app.api.ws.connection_manager import manager
from app.api.integrations.firebase_client import get_users_by_location, notify_users
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    async def notify_community(self, issue):
        print("=" * 50)
        print("🔔 NOTIFICATION SERVICE - notify_community()")
        print(f"Issue ID: {issue.id}")
        print(f"City: {issue.city}, State: {issue.state}, Pincode: {issue.pincode}")
        
        users = get_users_by_location(
            city=issue.city,
            pincode=issue.pincode,
            state=issue.state
        )

        print(f"📋 Found {len(users)} users matching location")
        for u in users:
            print(f"  - UID: {u['uid']}, Name: {u.get('name')}, FCM: {'Yes' if u.get('fcm_token') else 'No'}")

        uids = [u["uid"] for u in users]

        message = {
            "type": "NEW_ISSUE",
            "issue_id": issue.id,
            "title": issue.title,
            "category": issue.category,
            "city": issue.city,
            "pincode": issue.pincode
        }

        # 🔹 WebSocket (online users)
        print(f"📡 Broadcasting WebSocket to {len(uids)} UIDs")
        await manager.broadcast(uids, message)

        # 🔹 Push notifications (offline users)
        tokens_count = len([u for u in users if u.get('fcm_token')])
        print(f"📲 Sending FCM push to {tokens_count} devices with tokens")
        notify_users(
            users,
            title="New issue near you",
            body=issue.title,
            data={"issue_id": str(issue.id)}
        )
        print("=" * 50)

    async def notify_reporter(self, issue, message: str):
        """Notify the reporter about issue status."""
        pass

    async def notify_department(self, issue):
        """Notify relevant government department."""
        pass

    async def notify_rejection(self, issue, reason: str = ""):
        """Notify reporter that issue was rejected."""
        pass

    async def notify_resolution(self, issue):
        """Notify reporter that issue was resolved."""
        pass


# Create instance for module-level access
_service = NotificationService()

# Export for convenience
notify_community = _service.notify_community