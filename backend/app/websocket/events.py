from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional
from app.websocket.manager import manager
from jose import jwt, JWTError
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
ws_router = APIRouter()

@ws_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """WebSocket endpoint for real-time EdgeTwin AI events."""
    try:
        # Validate token
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            await websocket.close(code=1008)
            return
            
    except JWTError as e:
        logger.error(f"WebSocket auth failed: {e}")
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, user_id)
    try:
        while True:
            # Receive heartbeat or specific events from client
            data = await websocket.receive_text()
            # For now, just echo or handle heartbeat
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
