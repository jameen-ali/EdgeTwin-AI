"""FastAPI application entry point and lifecycle configuration."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.app.config import get_settings
from api.app.ingest.mqtt_client import MQTTIngestionClient
from api.app.logging import get_logger, setup_logging
from api.app.routes.alerts import router as alerts_router
from api.app.routes.auth import router as auth_router
from api.app.routes.health import router as health_router
from api.app.routes.machines import router as machines_router
from api.app.routes.maintenance import router as maintenance_router
from api.app.routes.mlops import router as mlops_router
from api.app.routes.retrain import router as retrain_router
from api.app.routes.scenarios import router as scenarios_router
from api.app.schemas.common import ProblemDetails
from api.app.ws.broadcaster import get_connection_manager
from api.app.ws.router import router as ws_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan management for initialization and graceful shutdown.

    Startup:
    - Configure structured logging.
    - Register WebSocket broadcast callback with TwinService (T-037).
    - Start the MQTT ingestion client (background paho thread).

    Shutdown:
    - Unregister WS callback.
    - Disconnect MQTT client gracefully before process exits.
    """
    setup_logging()
    settings = get_settings()
    logger.info(
        f"Starting {settings.PROJECT_NAME} (v{settings.VERSION}) in [{settings.ENVIRONMENT}] mode"
    )

    # Register the WebSocket broadcaster as a TwinService callback so every
    # twin state update fires a broadcast to connected clients (T-037).
    manager = get_connection_manager()
    app.state.ws_manager = manager

    from api.app.twin.service import get_twin_service

    twin_svc = get_twin_service()
    app.state.twin_service = twin_svc

    async def _ws_broadcast_callback(machine_id: str, state_dict: dict[str, Any]) -> None:
        await manager.broadcast_twin_update(machine_id, state_dict)

    twin_svc.register_ws_callback(_ws_broadcast_callback)

    # Start MQTT ingestion client (T-032)
    mqtt_client = MQTTIngestionClient(settings=settings)
    app.state.mqtt_client = mqtt_client
    try:
        mqtt_client.start()
        logger.info("MQTT ingestion client started")
    except Exception as exc:  # noqa: BLE001
        # If the broker is unavailable at startup, log but do NOT block the API.
        # paho will continue retrying in the background thread.
        logger.warning(
            f"MQTT ingestion client failed to initiate connection: {exc}; will retry automatically"
        )

    # Bootstrap initial admin account if configured in environment (T-038)
    if settings.ADMIN_PASSWORD:
        try:
            from sqlalchemy import select

            from api.app.db.session import SessionLocal
            from api.app.models.user import UserRecord
            from api.app.security.passwords import hash_password
            from api.app.security.roles import UserRole

            with SessionLocal() as db_session:
                admin_user = db_session.execute(
                    select(UserRecord).where(UserRecord.username == settings.ADMIN_USERNAME)
                ).scalar_one_or_none()
                if admin_user is None:
                    admin_user = UserRecord(
                        username=settings.ADMIN_USERNAME,
                        password_hash=hash_password(settings.ADMIN_PASSWORD),
                        role=UserRole.ADMIN.value,
                        is_active=True,
                    )
                    db_session.add(admin_user)
                    db_session.commit()
                    logger.info(f"Initialized administrative account: {settings.ADMIN_USERNAME}")
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Failed to bootstrap admin user during startup: {exc}")

    yield

    # Graceful shutdown
    logger.info(f"Shutting down {settings.PROJECT_NAME}")
    twin_svc.unregister_ws_callback(_ws_broadcast_callback)
    try:
        mqtt_client.stop()
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Error stopping MQTT client during shutdown: {exc}")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="EdgeTwin AI Predictive Maintenance Platform REST and Ingestion API",
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # 1. Configure CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
    )

    # 2. Security Headers Middleware (T-038)
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next: Any) -> Any:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

    # 2. Register Global Exception Handlers (RFC 7807 Problem Details)
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warning(
            f"Request validation failed on {request.method} {request.url.path}: {exc.errors()}"
        )
        problem = ProblemDetails(
            type="https://edgetwin.ai/errors/validation-error",
            title="Validation Error",
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="One or more request parameters or payload fields failed validation.",
            instance=str(request.url.path),
            errors=jsonable_encoder(exc.errors()),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=problem.model_dump(),
            headers={"Content-Type": "application/problem+json"},
        )

    @app.exception_handler(HTTPException)
    @app.exception_handler(404)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        status_code = getattr(exc, "status_code", 404)
        detail = getattr(exc, "detail", "Not Found")
        logger.info(f"HTTP {status_code} on {request.method} {request.url.path}: {detail}")
        problem = ProblemDetails(
            type="https://edgetwin.ai/errors/http-error",
            title="HTTP Error",
            status=status_code,
            detail=str(detail),
            instance=str(request.url.path),
        )
        return JSONResponse(
            status_code=status_code,
            content=problem.model_dump(),
            headers={"Content-Type": "application/problem+json"},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            f"Unhandled internal exception on {request.method} {request.url.path}: {exc!s}"
        )
        problem = ProblemDetails(
            type="https://edgetwin.ai/errors/internal-server-error",
            title="Internal Server Error",
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the request.",
            instance=str(request.url.path),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=problem.model_dump(),
            headers={"Content-Type": "application/problem+json"},
        )

    # 3. Mount Routers
    # Direct root probes
    app.include_router(health_router)
    # API v1 prefix probes
    app.include_router(health_router, prefix=settings.API_V1_PREFIX)
    # REST API v1 routes (T-036, T-038)
    app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
    app.include_router(machines_router, prefix=settings.API_V1_PREFIX)
    app.include_router(alerts_router, prefix=settings.API_V1_PREFIX)
    app.include_router(maintenance_router, prefix=settings.API_V1_PREFIX)
    app.include_router(mlops_router, prefix=settings.API_V1_PREFIX)
    app.include_router(retrain_router, prefix=settings.API_V1_PREFIX)
    app.include_router(scenarios_router, prefix=settings.API_V1_PREFIX)
    # WebSocket live stream (T-037, T-038) — /ws/live and /ws/live/{machine_id}
    app.include_router(ws_router)

    return app


app = create_app()
