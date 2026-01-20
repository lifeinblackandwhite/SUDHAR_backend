"""
WebSocket endpoint for real-time ranking updates.

Government officials can connect to receive real-time updates when:
- New issues are created
- Issues are verified
- Issue status changes
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional
import asyncio

from .ws_manager import manager
from .service import DynamicRankingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("/ranking")
async def ranking_websocket(
    websocket: WebSocket,
    state: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    category: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time ranking updates.
    
    Connect to receive live ranking updates.
    
    Query params for filtering:
    - state: Filter by state
    - city: Filter by city
    - category: Filter by category
    
    Messages sent:
    - On connect: Full current ranking
    - On updates: New ranking data
    
    Example:
        ws://localhost:8000/ws/ranking?state=Karnataka&city=Bengaluru
    """
    await manager.connect(websocket, "ranking")
    
    # Store filters for this connection
    filters = {
        "state": state,
        "city": city, 
        "category": category
    }
    await manager.set_filters(websocket, filters)
    
    try:
        # Send initial ranking on connect
        await send_current_ranking(websocket, filters)
        
        # Keep connection alive and handle messages
        while True:
            # Wait for client messages (e.g., filter updates)
            data = await websocket.receive_json()
            
            # Handle filter update requests
            if data.get("type") == "update_filters":
                new_filters = data.get("filters", {})
                filters.update(new_filters)
                await manager.set_filters(websocket, filters)
                await send_current_ranking(websocket, filters)
            
            # Handle ping/keepalive
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        await manager.disconnect(websocket, "ranking")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket, "ranking")


async def send_current_ranking(websocket: WebSocket, filters: dict):
    """Send current ranking to a specific websocket."""
    try:
        # Note: In production, inject db session properly
        service = DynamicRankingService()
        
        # For now, send a structure that frontend can use
        # In production, this would fetch from DB
        await websocket.send_json({
            "type": "ranking_update",
            "data": {
                "message": "Connected to ranking updates",
                "filters": filters,
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }
        })
    except Exception as e:
        logger.error(f"Error sending ranking: {e}")


async def broadcast_ranking_update(
    event_type: str,
    issue_id: int = None,
    issue_data: dict = None
):
    """
    Broadcast a ranking update to all connected officials.
    
    Call this when:
    - New issue is created
    - Issue is verified
    - Issue status changes
    
    Args:
        event_type: Type of event (new_issue, verification, status_change)
        issue_id: ID of affected issue
        issue_data: Additional issue data
    """
    message = {
        "type": "ranking_update",
        "event": event_type,
        "issue_id": issue_id,
        "data": issue_data,
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }
    
    await manager.broadcast_to_channel("ranking", message)
    logger.info(f"Broadcast ranking update: {event_type} for issue {issue_id}")
