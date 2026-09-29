"""Maintenance event request and response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MaintenanceDTO(BaseModel):
    """Maintenance event entity DTO."""

    id: int = Field(..., description="Unique maintenance event sequence ID")
    machine_id: str = Field(..., description="Target machine identifier")
    alert_id: int | None = Field(None, description="Linked alert ID")
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


class MaintenanceCreateRequest(BaseModel):
    """Payload to create or schedule a maintenance event / work order."""

    event_type: str = Field(
        ...,
        description="Event classification: INSPECTION, PART_REPLACEMENT, OVERHAUL, LUBRICATION, CALIBRATION",
    )
    description: str = Field(..., description="Description of work order or maintenance actions")
    status: str = Field(
        default="SCHEDULED",
        description="Lifecycle status: SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED",
    )
    technician: str | None = Field(None, description="Assigned technician name or ID")
    alert_id: int | None = Field(None, description="Optional linked alert sequence ID")
    started_at: datetime | None = Field(None, description="Service start timestamp")
    completed_at: datetime | None = Field(None, description="Service completion timestamp")


class MaintenanceCreateWithMachineRequest(MaintenanceCreateRequest):
    """Payload to create a maintenance event with machine_id in request body."""

    machine_id: str = Field(..., description="Target machine identifier")


class MaintenanceUpdateRequest(BaseModel):
    """Payload to update maintenance event lifecycle or work order notes."""

    status: str | None = Field(
        None,
        description="Updated lifecycle status: SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED",
    )
    description: str | None = Field(
        None, description="Updated work order notes or resolution details"
    )
    technician: str | None = Field(None, description="Assigned technician name or ID")
    started_at: datetime | None = Field(None, description="Service start timestamp")
    completed_at: datetime | None = Field(None, description="Service completion timestamp")


class MaintenanceListResponse(BaseModel):
    """Bounded paginated list of maintenance events."""

    items: list[MaintenanceDTO] = Field(..., description="List of maintenance events")
    total: int = Field(..., description="Total matching maintenance records")
    limit: int = Field(..., description="Applied pagination limit")
    offset: int = Field(..., description="Applied pagination offset")
