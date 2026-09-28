"""Alert request and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AlertDTO(BaseModel):
    """Machine or system alert record."""

    id: int = Field(..., description="Unique alert ID")
    machine_id: str = Field(..., description="Machine identifier")
    alert_type: str = Field(..., description="Type classification of alert")
    severity: str = Field(..., description="Alert severity: INFO, WARNING, CRITICAL")
    status: str = Field(..., description="Lifecycle status: OPEN, ACKNOWLEDGED, RESOLVED")
    message: str = Field(..., description="Human-readable alert summary")
    trigger_conditions: dict[str, Any] | None = Field(
        None, description="Triggering signal conditions"
    )
    top_factors: list[dict[str, Any]] | None = Field(
        None, description="Top SHAP attributions at trigger time"
    )
    triggered_at: datetime = Field(..., description="Timestamp alert condition was raised")
    acknowledged_at: datetime | None = Field(None, description="Timestamp alert was acknowledged")
    resolved_at: datetime | None = Field(None, description="Timestamp alert was resolved")
    resolved_by: str | None = Field(
        None, description="Technician or operator who resolved the alert"
    )

    model_config = ConfigDict(from_attributes=True)


class AlertListResponse(BaseModel):
    """Bounded paginated list of alerts."""

    items: list[AlertDTO] = Field(..., description="List of alerts")
    total: int = Field(..., description="Total matching alerts")
    limit: int = Field(..., description="Applied pagination limit")
    offset: int = Field(..., description="Applied pagination offset")


class AlertAcknowledgeRequest(BaseModel):
    """Request payload for acknowledging or resolving an alert."""

    status: str = Field(
        default="ACKNOWLEDGED",
        description="Target status (ACKNOWLEDGED or RESOLVED)",
    )
    resolved_by: str | None = Field(None, description="Operator or technician identifier")
    notes: str | None = Field(None, description="Acknowledgement or resolution notes")
