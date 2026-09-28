"""Maintenance event request and response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MaintenanceDTO(BaseModel):
    """Maintenance event entity DTO."""

    id: int = Field(..., description="Unique maintenance event sequence ID")
    machine_id: str = Field(..., description="Target machine identifier")
    event_type: str = Field(
        ...,
        description="Event classification: INSPECTION, PART_REPLACEMENT, OVERHAUL, LUBRICATION, CALIBRATION",
    )
    description: str = Field(..., description="Description of maintenance performed or scheduled")
    status: str = Field(
        ...,
        description="Maintenance lifecycle status: SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED",
    )
    technician: str | None = Field(None, description="Assigned technician name or ID")
    started_at: datetime | None = Field(None, description="Service start timestamp")
    completed_at: datetime | None = Field(None, description="Service completion timestamp")
    created_at: datetime = Field(..., description="Event logged timestamp")

    model_config = ConfigDict(from_attributes=True)


class MaintenanceListResponse(BaseModel):
    """Bounded paginated list of maintenance events."""

    items: list[MaintenanceDTO] = Field(..., description="List of maintenance events")
    total: int = Field(..., description="Total matching maintenance records")
    limit: int = Field(..., description="Applied pagination limit")
    offset: int = Field(..., description="Applied pagination offset")
