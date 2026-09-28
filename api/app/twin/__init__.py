"""
api/app/twin/__init__.py — Digital Twin service package.

Exposes:
    TwinService        — stateful service managing per-machine Digital Twin state.
    get_twin_service   — singleton accessor.
    TwinState          — immutable snapshot dataclass.
"""

from api.app.twin.service import TwinService, get_twin_service
from api.app.twin.state import TwinState

__all__ = ["TwinService", "TwinState", "get_twin_service"]
