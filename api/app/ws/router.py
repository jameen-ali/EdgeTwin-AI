"""
api/app/ws/router.py — WebSocket endpoint for live twin-state streaming (T-037).

Endpoint:  GET /ws/live
           GET /ws/live/{machine_id}   (single-machine subscription)

Protocol:
- Client connects via WS upgrade.
- Server immediately sends the current twin state(s) as a "snapshot" event.
- Server then pushes "twin_update" events whenever any subscribed machine
  twin state changes.
- Client can send any text frame (e.g. "ping") as a keepalive; server echoes "pong".
- On disconnect the connection is removed from the ConnectionManager.

Message schema:
  {
    "event": "twin_update" | "snapshot" | "pong" | "error",
    "data":  <TwinState.to_dict()>  |  <list[TwinState.to_dict()]>  |  <str>
  }
"""

from __future__ import annotations

import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from api.app.models.user import UserRecord
from api.app.security.deps import get_current_ws_user
from api.app.twin.service import get_twin_service
from api.app.ws.broadcaster import get_connection_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/live")
async def ws_live_all(
    websocket: WebSocket,
    current_user: Annotated[UserRecord, Depends(get_current_ws_user)],
) -> None:
    """Subscribe to live twin-state updates for ALL machines."""
    manager = get_connection_manager()
    twin_svc = get_twin_service()

    await manager.connect(websocket, machine_id=None)

    # Send immediate snapshot of all known twins
    try:
        all_states: list[dict[str, Any]] = [
            state.to_dict() for state in twin_svc.get_all_states().values()
        ]
        await websocket.send_text(json.dumps({"event": "snapshot", "data": all_states}))
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Failed to send initial snapshot to WS client: {exc}")

    try:
        while True:
            # Keep-alive: accept any frame from client; echo "pong"
            text = await websocket.receive_text()
            if text.strip().lower() in ("ping", ""):
                await websocket.send_text(json.dumps({"event": "pong", "data": "pong"}))
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"WebSocket /ws/live error: {exc}")
    finally:
        manager.disconnect(websocket)


@router.websocket("/ws/live/{machine_id}")
async def ws_live_machine(
    websocket: WebSocket,
    machine_id: str,
    current_user: Annotated[UserRecord, Depends(get_current_ws_user)],
) -> None:
    """Subscribe to live twin-state updates for a single machine.

    Parameters
    ----------
    machine_id:
        The machine to subscribe to (e.g. MOT-1001).  Pattern: [A-Z]{3}-[0-9]{4}.
    """
    manager = get_connection_manager()
    twin_svc = get_twin_service()

    await manager.connect(websocket, machine_id=machine_id)

    # Send current state as an immediate snapshot
    try:
        state = twin_svc.get_state(machine_id)
        if state is not None:
            await websocket.send_text(json.dumps({"event": "snapshot", "data": state.to_dict()}))
        else:
            await websocket.send_text(
                json.dumps(
                    {
                        "event": "snapshot",
                        "data": None,
                        "message": f"Machine {machine_id} not yet tracked",
                    }
                )
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Failed to send initial snapshot for {machine_id}: {exc}")

    try:
        while True:
            text = await websocket.receive_text()
            if text.strip().lower() in ("ping", ""):
                await websocket.send_text(json.dumps({"event": "pong", "data": "pong"}))
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"WebSocket /ws/live/{machine_id} error: {exc}")
    finally:
        manager.disconnect(websocket)
