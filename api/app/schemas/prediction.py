"""Prediction request and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PredictionDTO(BaseModel):
    """ML prediction and health assessment record DTO."""

    id: int = Field(..., description="Unique prediction record sequence ID")
    machine_id: str = Field(..., description="Machine identifier")
    telemetry_id: int | None = Field(None, description="Linked raw telemetry record ID")
    ts: datetime = Field(..., description="ISO-8601 UTC timestamp of assessed state")

    # Layer 2: Supervised Failure Risk
    failure_probability: float = Field(
        ..., ge=0.0, le=1.0, description="Calibrated positive failure probability"
    )
    failure_prediction: int = Field(
        ..., description="Binary decision (0 = Normal, 1 = Failure Risk)"
    )
    risk_band: str = Field(..., description="Operational risk band: LOW, MEDIUM, HIGH, CRITICAL")

    # Layer 3: Unsupervised Anomaly Detection
    anomaly_score: float | None = Field(
        None, ge=0.0, le=1.0, description="Normalized Isolation Forest anomaly score"
    )
    anomaly_flag: bool | None = Field(None, description="True if anomaly threshold crossed")

    # Layer 4: Composite Machine Health
    health_score: float | None = Field(
        None, ge=0.0, le=100.0, description="Health score index (0-100)"
    )
    health_state: str | None = Field(
        None,
        description="Hierarchical health state (HEALTHY, WARNING, CRITICAL, MAINTENANCE_REQUIRED, OFFLINE)",
    )

    # Layer 5: Explainability
    top_factors: list[dict[str, Any]] | None = Field(
        None, description="Top contributing SHAP feature attributions in model margin space"
    )

    # Governance
    model_version: str = Field(..., description="Registered ML model version tag")
    inference_latency_ms: float | None = Field(
        None, description="End-to-end model inference compute latency in milliseconds"
    )
    created_at: datetime = Field(..., description="Record insertion timestamp")

    model_config = ConfigDict(from_attributes=True)


class PredictionListResponse(BaseModel):
    """Bounded paginated list of prediction records."""

    items: list[PredictionDTO] = Field(..., description="List of persisted predictions")
    total: int = Field(..., description="Total matching predictions")
    limit: int = Field(..., description="Applied pagination limit")
    offset: int = Field(..., description="Applied pagination offset")
