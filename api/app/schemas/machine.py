"""Machine entity request and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MachineSummary(BaseModel):
    """Summary of a machine's current status and identity."""

    machine_id: str = Field(..., description="Unique machine identifier (e.g. MOT-1001)")
    machine_type: str = Field(..., description="Machine type / equipment class (e.g. Motor, Pump)")
    location: str | None = Field(None, description="Physical plant location or workcell")
    status: str = Field(..., description="Registration status: ACTIVE, OFFLINE, DECOMMISSIONED")
    sync_status: str | None = Field(
        None, description="Real-time Digital Twin sync status: LIVE, STALE, OFFLINE"
    )
    health_state: str | None = Field(
        None, description="Health state: HEALTHY, WARNING, CRITICAL, MAINTENANCE_REQUIRED, OFFLINE"
    )
    health_score: float | None = Field(
        None, ge=0.0, le=100.0, description="Health index between 0.0 and 100.0"
    )
    risk_band: str | None = Field(
        None, description="Operational risk band: LOW, MEDIUM, HIGH, CRITICAL"
    )
    operating_state: str | None = Field(
        None,
        description="Operating state from edge: RUNNING, STOPPED, STARTING, DEGRADING, TRIPPED",
    )
    last_telemetry_ts: datetime | None = Field(
        None, description="ISO-8601 UTC timestamp of most recent telemetry"
    )
    updated_at: datetime | None = Field(None, description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class MachineListResponse(BaseModel):
    """Bounded paginated list of machines."""

    items: list[MachineSummary] = Field(
        ..., description="List of machines matching filter criteria"
    )
    total: int = Field(..., description="Total number of machines")
    limit: int = Field(..., description="Applied pagination limit")
    offset: int = Field(..., description="Applied pagination offset")


class MachineDetailResponse(BaseModel):
    """Detailed view of a machine including latest telemetry, prediction, and twin state."""

    machine_id: str = Field(..., description="Unique machine identifier")
    machine_type: str = Field(..., description="Equipment class")
    location: str | None = Field(None, description="Plant location")
    status: str = Field(..., description="Registration status")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record last update timestamp")
    latest_twin: dict[str, Any] | None = Field(
        None, description="Canonical Digital Twin state object"
    )
    latest_telemetry: dict[str, Any] | None = Field(
        None, description="Summary of latest telemetry observation"
    )
    latest_prediction: dict[str, Any] | None = Field(
        None, description="Summary of latest ML failure risk prediction"
    )

    model_config = ConfigDict(from_attributes=True)
