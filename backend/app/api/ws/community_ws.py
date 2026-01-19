from fastapi import APIRouter, WebSocket
from app.api.ws.connection_manager import manager
from app.api.ws.connection_manager import ConnectionManager

router = APIRouter()
manager = ConnectionManager()

@router.websocket("/ws/community/{uid}")
async def community_ws(websocket: WebSocket, uid: str):
    await manager.connect(uid, websocket)
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except Exception:
        manager.disconnect(uid)
