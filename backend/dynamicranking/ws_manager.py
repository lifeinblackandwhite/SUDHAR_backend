"""
WebSocket Connection Manager for real-time updates.

Manages WebSocket connections for:
- Government officials receiving ranking updates
- Citizens receiving issue status updates
"""

import logging
from typing import Dict, List, Set
from fastapi import WebSocket
import json

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.
    
    Supports multiple channels:
    - ranking: Updates for government officials
    - issues: Updates for citizen issue tracking
    """
    
    def __init__(self):
        # Active connections by channel
        self.active_connections: Dict[str, List[WebSocket]] = {
            "ranking": [],
            "issues": [],
        }
        # Track which officials are subscribed to which filters
        self.official_filters: Dict[WebSocket, Dict] = {}
    
    async def connect(self, websocket: WebSocket, channel: str = "ranking"):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = []
        self.active_connections[channel].append(websocket)
        logger.info(f"New WebSocket connection on channel: {channel}")
    
    async def disconnect(self, websocket: WebSocket, channel: str = "ranking"):
        """Remove a WebSocket connection."""
        if channel in self.active_connections:
            if websocket in self.active_connections[channel]:
                self.active_connections[channel].remove(websocket)
        if websocket in self.official_filters:
            del self.official_filters[websocket]
        logger.info(f"WebSocket disconnected from channel: {channel}")
    
    async def set_filters(self, websocket: WebSocket, filters: Dict):
        """Set filters for an official's ranking subscription."""
        self.official_filters[websocket] = filters
    
    async def broadcast_to_channel(self, channel: str, message: dict):
        """Broadcast a message to all connections on a channel."""
        if channel not in self.active_connections:
            return
        
        disconnected = []
        for connection in self.active_connections[channel]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            await self.disconnect(conn, channel)
    
    async def send_to_connection(self, websocket: WebSocket, message: dict):
        """Send a message to a specific connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending to WebSocket: {e}")
    
    def get_connection_count(self, channel: str = None) -> int:
        """Get number of active connections."""
        if channel:
            return len(self.active_connections.get(channel, []))
        return sum(len(conns) for conns in self.active_connections.values())


# Global connection manager instance
manager = ConnectionManager()
