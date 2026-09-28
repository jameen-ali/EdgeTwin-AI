"""Routes package exporting API routers."""

from api.app.routes.alerts import router as alerts_router
from api.app.routes.health import router as health_router
from api.app.routes.machines import router as machines_router

__all__ = ["alerts_router", "health_router", "machines_router"]
