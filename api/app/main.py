"""FastAPI application entry point and lifecycle configuration."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.app.config import get_settings
from api.app.ingest.mqtt_client import MQTTIngestionClient
from api.app.logging import get_logger, setup_logging
from api.app.routes.health import router as health_router
from api.app.schemas.common import ProblemDetails

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan management for initialization and graceful shutdown.

    Startup:
    - Configure structured logging.
    - Start the MQTT ingestion client (background paho thread).

    Shutdown:
    - Disconnect MQTT client gracefully before process exits.
    """
    setup_logging()
    settings = get_settings()
    logger.info(
        f"Starting {settings.PROJECT_NAME} (v{settings.VERSION}) in [{settings.ENVIRONMENT}] mode"
    )

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
            f"MQTT ingestion client failed to initiate connection: {exc}; "
            "will retry automatically"
        )

    yield

    # Graceful shutdown
    logger.info(f"Shutting down {settings.PROJECT_NAME}")
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
            errors=exc.errors(),
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

    return app


app = create_app()
