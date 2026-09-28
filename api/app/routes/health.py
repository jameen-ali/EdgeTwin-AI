"""Health and readiness router."""

from datetime import UTC, datetime

from fastapi import APIRouter, Response, status

from api.app.config import get_settings
from api.app.db.session import check_db_connection
from api.app.schemas.health import HealthResponse, ReadyResponse

router = APIRouter(tags=["Health & Diagnostics"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Liveness Probe",
    description="Check whether the backend application process is running and alive.",
)
def get_health() -> HealthResponse:
    """Return backend process liveness status."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(UTC),
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
    )


@router.get(
    "/ready",
    response_model=ReadyResponse,
    responses={
        status.HTTP_200_OK: {
            "model": ReadyResponse,
            "description": "Service is ready to handle traffic.",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ReadyResponse,
            "description": "Service dependency (e.g. database) is unavailable.",
        },
    },
    summary="Service Readiness Probe",
    description="Verify active connectivity to dependent backing services (e.g. database).",
)
def get_readiness(response: Response) -> ReadyResponse:
    """Return backend readiness status and check database connectivity."""
    db_ok, err_msg = check_db_connection()

    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadyResponse(
            status="unready",
            database="disconnected",
            timestamp=datetime.now(UTC),
            detail=f"Database connection failed: {err_msg}",
        )

    return ReadyResponse(
        status="ready",
        database="connected",
        timestamp=datetime.now(UTC),
        detail=None,
    )
