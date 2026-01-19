from typing import Dict
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_users: dict[str, WebSocket] = {}

    async def connect(self, uid: str, websocket: WebSocket):
        await websocket.accept()
        self.active_users[uid] = websocket

    def disconnect(self, uid: str):
        self.active_users.pop(uid, None)

    async def send_to_user(self, uid: str, message: dict):
        if uid in self.active_users:
            await self.active_users[uid].send_json(message)

    async def broadcast(self, uids: list[str], message: dict):
        """
        Send message to multiple users safely
        """
        for uid in uids:
            if uid in self.active_users:
                try:
                    await self.active_users[uid].send_json(message)
                except Exception:
                    self.disconnect(uid)


# ✅ SINGLE shared instance (VERY IMPORTANT)
manager = ConnectionManager()
