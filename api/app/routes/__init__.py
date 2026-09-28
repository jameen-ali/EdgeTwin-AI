"""Routes package exporting all API endpoint routers."""

from api.app.routes.health import router as health_router

__all__ = ["health_router"]
