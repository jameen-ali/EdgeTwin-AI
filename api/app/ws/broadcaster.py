"""
api/app/ws/broadcaster.py — Multi-client WebSocket connection manager (T-037).

Design:
- ConnectionManager maintains a set of active WebSocket connections, optionally
  filtered by machine_id subscription.
- broadcast() sends a JSON message to all qualifying connections; disconnected
  clients are silently removed without crashing the caller.
- Each connection can optionally subscribe to a specific machine_id.
  If machine_id is None the connection receives updates for ALL machines.
- thread-safe via asyncio.Lock (all access from the FastAPI event loop thread).

Fan-out path (triggered by TwinService):
    MQTT thread → TwinService._set_state()
                → ConnectionManager.broadcast_twin_update() scheduled on event loop
                → each active WebSocket.send_json()
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts twin-state updates.

    Usage
    -----
    manager = ConnectionManager()

    # In WebSocket endpoint:
    await manager.connect(websocket, machine_id="MOT-1001")  # or None = all
    try:
        while True:
            await websocket.receive_text()  # keepalive
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    """

    def __init__(self) -> None:
        # Maps WebSocket → optional machine_id filter (None = all machines)
        self._connections: dict[WebSocket, str | None] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(
        self,
        websocket: WebSocket,
        machine_id: str | None = None,
    ) -> None:
        """Accept and register a new WebSocket connection.

        Parameters
        ----------
        websocket:
            The FastAPI WebSocket instance.
        machine_id:
            Optional subscription filter — only updates for this machine are sent.
            Pass None to receive updates for all machines.
        """
        await websocket.accept()
        async with self._lock:
            self._connections[websocket] = machine_id
        logger.info(f"WebSocket connected (filter={machine_id!r}, total={len(self._connections)})")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a connection (safe to call even if not present)."""
        self._connections.pop(websocket, None)
        logger.info(f"WebSocket disconnected (total={len(self._connections)})")

    @property
    def active_count(self) -> int:
        """Number of currently active connections."""
        return len(self._connections)

    # ------------------------------------------------------------------
    # Broadcast
    # ------------------------------------------------------------------

    async def broadcast_twin_update(
        self,
        machine_id: str,
        state_dict: dict[str, Any],
    ) -> None:
        """Send a twin-state update to all subscribed WebSocket clients.

        Parameters
        ----------
        machine_id:
            The machine whose state changed.
        state_dict:
            JSON-serialisable twin state dict (from TwinState.to_dict()).
        """
        if not self._connections:
            return

        message = json.dumps({"event": "twin_update", "data": state_dict})

        # Snapshot connection list to avoid mutation during iteration
        async with self._lock:
            targets = {
                ws: filter_id
                for ws, filter_id in self._connections.items()
                if filter_id is None or filter_id == machine_id
            }

        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_text(message)
            except (WebSocketDisconnect, RuntimeError, Exception) as exc:  # noqa: BLE001
                logger.debug(f"WebSocket send failed ({exc!s}); marking for removal")
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.pop(ws, None)
            logger.info(
                f"Removed {len(dead)} dead WebSocket connection(s) "
                f"(remaining={len(self._connections)})"
            )

    async def broadcast_raw(self, message: dict[str, Any]) -> None:
        """Broadcast an arbitrary JSON message to ALL connected clients."""
        if not self._connections:
            return

        text = json.dumps(message)
        async with self._lock:
            all_ws = list(self._connections.keys())

        dead: list[WebSocket] = []
        for ws in all_ws:
            try:
                await ws.send_text(text)
            except Exception as exc:  # noqa: BLE001
                logger.debug(f"WebSocket broadcast_raw failed: {exc!s}")
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.pop(ws, None)


# ---------------------------------------------------------------------------
# Module-level singleton (wired into app.state in main.py)
# ---------------------------------------------------------------------------

_manager: ConnectionManager | None = None


def get_connection_manager() -> ConnectionManager:
    """Return the global ConnectionManager singleton."""
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager
