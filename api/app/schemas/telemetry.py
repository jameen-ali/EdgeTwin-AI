"""Telemetry request and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TelemetryDTO(BaseModel):
    """Telemetry observation data transfer object."""

    id: int = Field(..., description="Unique telemetry record sequence ID")
    machine_id: str = Field(..., description="Target machine identifier")
    seq: int = Field(..., description="Edge monotonic packet sequence number")
    ts: datetime = Field(..., description="ISO-8601 UTC observation timestamp")
    provenance: str = Field(..., description="Data origin: SIMULATED, REPLAY, REAL")
    fw: str = Field(..., description="Edge firmware version (e.g. 0.2.0)")

    # 10 Raw Sensor Signals
    air_temp_c: float | None = Field(None, description="Ambient air temperature in Celsius")
    process_temp_c: float | None = Field(None, description="Process contact temperature in Celsius")
    rotational_speed_rpm: float | None = Field(None, description="Rotational speed in RPM")
    torque_nm: float | None = Field(None, description="Shaft torque in Newton-meters")
    vibration_mm_s: float | None = Field(
        None, description="Windowed vibration velocity in mm/s RMS"
    )
    pressure_bar: float | None = Field(None, description="Hydraulic/pneumatic pressure in bar")
    current_a: float | None = Field(None, description="Electrical current in Amperes")
    voltage_v: float | None = Field(None, description="Supply voltage in Volts")
    tool_wear_min: float | None = Field(None, description="Cumulative tool wear in minutes")
    operating_hours: float | None = Field(None, description="Total machine operating hours")

    # Diagnostics and Quality
    quality: dict[str, Any] | None = Field(None, description="Per-sensor quality flags")
    delta_t_c: float | None = Field(None, description="Process minus ambient temperature delta")
    power_va: float | None = Field(None, description="Apparent power in Volt-Amperes")
    trip: str | None = Field(None, description="Hardware safety trip code if activated")
    buffered: int = Field(0, description="Count of buffered messages sent on reconnect")
    received_at: datetime = Field(..., description="Ingestion timestamp at broker/backend")

    model_config = ConfigDict(from_attributes=True)


class TelemetryListResponse(BaseModel):
    """Bounded paginated list of telemetry records."""

    items: list[TelemetryDTO] = Field(..., description="List of telemetry observations")
    total: int = Field(..., description="Total matching telemetry records")
    limit: int = Field(..., description="Applied pagination limit")
    offset: int = Field(..., description="Applied pagination offset")
