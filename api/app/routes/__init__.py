"""Routes package exporting API routers."""

from api.app.routes.alerts import router as alerts_router
from api.app.routes.health import router as health_router
from api.app.routes.machines import router as machines_router
from api.app.routes.maintenance import router as maintenance_router
from api.app.routes.mlops import router as mlops_router

__all__ = [
    "alerts_router",
    "health_router",
    "machines_router",
    "maintenance_router",
    "mlops_router",
]
