"""Digital Twin request and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TwinStateDTO(BaseModel):
    """Canonical real-time Digital Twin state."""

    machine_id: str = Field(..., description="Unique machine identifier")
    sync_status: str = Field(..., description="Sync status: LIVE, STALE, OFFLINE")
    health_state: str = Field(
        ..., description="Health state: HEALTHY, WARNING, CRITICAL, MAINTENANCE_REQUIRED, OFFLINE"
    )
    health_score: float | None = Field(
        None, ge=0.0, le=100.0, description="Health score (0.0 to 100.0)"
    )
    risk_band: str | None = Field(None, description="Risk band: LOW, MEDIUM, HIGH, CRITICAL")
    failure_probability: float | None = Field(
        None, ge=0.0, le=1.0, description="Calibrated failure probability"
    )
    anomaly_flag: bool | None = Field(None, description="Unsupervised anomaly flag")
    anomaly_score: float | None = Field(
        None, ge=0.0, le=1.0, description="Unsupervised anomaly score"
    )
    operating_state: str = Field(
        "UNKNOWN",
        description="Operating state from edge: RUNNING, STOPPED, STARTING, DEGRADING, TRIPPED",
    )
    last_telemetry_ts: datetime | None = Field(
        None, description="Timestamp of most recent telemetry"
    )
    last_seq: int | None = Field(None, description="Last packet sequence number")
    updated_at: datetime | None = Field(None, description="Twin state update timestamp")

    signals: dict[str, Any] = Field(default_factory=dict, description="Latest raw sensor signals")
    quality: dict[str, str] = Field(default_factory=dict, description="Latest sensor quality flags")
    edge: dict[str, Any] = Field(
        default_factory=dict, description="Edge computed metrics and trips"
    )
    top_factors: list[dict[str, Any]] | None = Field(None, description="Top SHAP attributions")
    recommendation: dict[str, Any] | None = Field(
        None, description="Actionable maintenance recommendation"
    )
    model_version: str = Field("unknown", description="Model version used for inference")
    provenance: str = Field("SIMULATED", description="Data provenance: SIMULATED, REPLAY, REAL")
    fw: str | None = Field(None, description="Firmware version")

    model_config = ConfigDict(from_attributes=True)


class TwinSnapshotDTO(BaseModel):
    """Persisted snapshot record of a machine's Digital Twin."""

    id: int = Field(..., description="Snapshot record sequence ID")
    machine_id: str = Field(..., description="Machine identifier")
    ts: datetime = Field(..., description="ISO-8601 UTC timestamp of snapshot")
    sync_status: str = Field(..., description="Sync status at snapshot time")
    operating_state: str = Field(..., description="Operating state")
    health_state: str = Field(..., description="Health state")
    health_score: float = Field(..., description="Health score")
    risk_band: str = Field(..., description="Risk band")
    failure_probability: float = Field(..., description="Failure probability")
    anomaly_flag: bool = Field(..., description="Anomaly flag")
    snapshot_payload: dict[str, Any] = Field(..., description="Full state JSON payload")
    created_at: datetime = Field(..., description="Persistence timestamp")

    model_config = ConfigDict(from_attributes=True)


class TwinHistoryResponse(BaseModel):
    """Bounded paginated list of historical Digital Twin snapshots."""

    items: list[TwinSnapshotDTO] = Field(..., description="List of historical twin snapshots")
    total: int = Field(..., description="Total matching snapshots")
    limit: int = Field(..., description="Applied pagination limit")
    offset: int = Field(..., description="Applied pagination offset")
