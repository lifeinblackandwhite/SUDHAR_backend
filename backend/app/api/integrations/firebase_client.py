"""
Firebase client utilities
-------------------------
Responsibilities:
- Initialize Firebase Admin SDK
- Fetch users by location (state + city + pincode)
- Fetch single user profile
- Store / retrieve FCM tokens
- Send push notifications (single + bulk)

SAFE to import anywhere in backend.
"""

import firebase_admin
from firebase_admin import credentials, firestore, messaging
from typing import List, Dict, Optional
import os

# -------------------------------------------------------------------
# Firebase Initialization
# -------------------------------------------------------------------

if not firebase_admin._apps:
    cred = credentials.Certificate(
        os.getenv(
            "FIREBASE_SERVICE_ACCOUNT_PATH",
            "firebase_service_account.json"
        )
    )
    firebase_admin.initialize_app(cred)

db = firestore.client()

# -------------------------------------------------------------------
# User Profile Queries
# -------------------------------------------------------------------

def get_user_profile(uid: str) -> Optional[Dict]:
    """Fetch a single user's profile from Firebase."""
    doc = db.collection("users").document(uid).get()
    if not doc.exists:
        return None
    return doc.to_dict()


def get_users_by_location(
    city: str,
    pincode: str,
    state: Optional[str] = None
) -> List[Dict]:
    """
    Fetch citizens eligible for community verification
    based on location.
    """

    users_ref = db.collection("users")

    query = users_ref.where("city", "==", city).where("pincode", "==", pincode)

    if state:
        query = query.where("state", "==", state)

    users: List[Dict] = []

    for doc in query.stream():
        data = doc.to_dict()

        # Only citizens participate in community verification
        if data.get("role", "citizen") != "citizen":
            continue

        users.append({
            "uid": doc.id,
            "name": data.get("name"),
            "city": data.get("city"),
            "state": data.get("state"),
            "pincode": data.get("pincode"),
            "fcm_token": data.get("fcmToken"),  # normalized here
        })

    return users

# -------------------------------------------------------------------
# FCM Token Management
# -------------------------------------------------------------------

def save_fcm_token(uid: str, token: str):
    """Store or update FCM token for a user."""
    db.collection("users").document(uid).set(
        {"fcmToken": token},
        merge=True
    )


def remove_fcm_token(uid: str):
    """Remove FCM token (logout / uninstall)."""
    db.collection("users").document(uid).update(
        {"fcmToken": firestore.DELETE_FIELD}
    )

# -------------------------------------------------------------------
# Push Notifications
# -------------------------------------------------------------------

def send_push_notification(
    token: str,
    title: str,
    body: str,
    data: Dict[str, str] | None = None
):
    """Send push notification to a single device."""
    if not token:
        return

    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=data or {},
        token=token,
    )

    try:
        messaging.send(message)
    except Exception as e:
        print(f"[FCM ERROR] {e}")


def notify_users(
    users: List[Dict],
    title: str,
    body: str,
    data: Dict[str, str] | None = None
):
    """
    Send push notifications to many users.
    Uses FCM multicast for efficiency.
    """

    tokens = [
        u["fcm_token"]
        for u in users
        if u.get("fcm_token")
    ]

    if not tokens:
        return

    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=data or {},
        tokens=tokens,
    )

    try:
        messaging.send_multicast(message)
    except Exception as e:
        print(f"[FCM MULTICAST ERROR] {e}")
