"""Health and readiness endpoint response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Liveness probe response model."""

    status: str = Field(default="ok", description="Liveness status of the backend service")
    timestamp: datetime = Field(..., description="Current server UTC timestamp")
    version: str = Field(..., description="Backend application version")
    environment: str = Field(..., description="Operational environment name")

    model_config = ConfigDict(
        protected_namespaces=(),
        json_schema_extra={
            "example": {
                "status": "ok",
                "timestamp": "2026-09-26T12:00:00Z",
                "version": "0.1.0",
                "environment": "development",
            }
        },
    )


class ReadyResponse(BaseModel):
    """Readiness probe response model verifying operational dependencies."""

    status: str = Field(..., description="Readiness status ('ready' or 'unready')")
    database: str = Field(
        ..., description="Database connection status ('connected' or 'disconnected')"
    )
    timestamp: datetime = Field(..., description="Current server UTC timestamp")
    detail: str | None = Field(None, description="Optional diagnostic details or error message")

    model_config = ConfigDict(
        protected_namespaces=(),
        json_schema_extra={
            "example": {
                "status": "ready",
                "database": "connected",
                "timestamp": "2026-09-26T12:00:00Z",
                "detail": None,
            }
        },
    )
