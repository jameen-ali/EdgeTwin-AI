"""
api/app/ws/__init__.py — WebSocket package.

Exposes:
    router         — FastAPI APIRouter with the /ws/live endpoint.
    ConnectionManager — multi-client WebSocket fan-out manager.
"""

from api.app.ws.broadcaster import ConnectionManager
from api.app.ws.router import router

__all__ = ["ConnectionManager", "router"]
