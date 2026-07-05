from fastapi import WebSocket
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Maps user_id to a list of active websocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Could also maintain a mapping of role -> List[WebSocket] for role-based broadcasts

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"User {user_id} connected via WebSocket. Total connections for user: {len(self.active_connections[user_id])}")

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"User {user_id} disconnected via WebSocket.")

    async def send_personal_message(self, message: Dict[str, Any], user_id: str):
        """Send a JSON message to a specific user's active connections."""
        if user_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to {user_id}: {e}")
                    dead_connections.append(connection)
            
            # Clean up dead connections
            for dead in dead_connections:
                self.disconnect(dead, user_id)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a JSON message to all connected clients."""
        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, user_id)

manager = ConnectionManager()
