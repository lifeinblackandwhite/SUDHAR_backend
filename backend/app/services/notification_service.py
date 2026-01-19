from app.db.models import Issue
from app.api.integrations.firebase_client import (
    get_users_by_location,
    send_push_notification,
    notify_users,
)

from app.api.ws.community_ws import manager

from app.api.ws.connection_manager import manager
from app.api.integrations.firebase_client import get_users_by_location, notify_users

class NotificationService:
    async def notify_community(self, issue):
        users = get_users_by_location(
            city=issue.city,
            pincode=issue.pincode,
            state=issue.state
        )

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
        await manager.broadcast(uids, message)

        # 🔹 Push notifications (offline users)
        notify_users(
            users,
            title="New issue near you",
            body=issue.title,
            data={"issue_id": str(issue.id)}
        )



# Create instance for module-level access
_service = NotificationService()

# Export for convenience
notify_community = _service.notify_community