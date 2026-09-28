"""Pydantic schemas for scenario control and command guard."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ScenarioID(str, Enum):
    """Canonical test and fault scenarios defined in simulation/scenarios/."""

    SCN_01 = "SCN-01"  # Healthy Nominal
    SCN_02 = "SCN-02"  # Heat Dissipation Failure
    SCN_03 = "SCN-03"  # Overstrain Failure
    SCN_04 = "SCN-04"  # Power Failure
    SCN_05 = "SCN-05"  # Tool Wear Failure
    SCN_06 = "SCN-06"  # Random Vibration Failure
    SCN_07 = "SCN-07"  # Sensor Dropout
    SCN_08 = "SCN-08"  # Machine Offline


CANONICAL_SCENARIOS: dict[str, dict[str, str]] = {
    "SCN-01": {
        "name": "Healthy Nominal Operation",
        "description": "Baseline healthy multi-sensor process telemetry within nominal envelopes.",
        "target_fault": "NONE",
        "file": "healthy_nominal.yaml",
    },
    "SCN-02": {
        "name": "Heat Dissipation Failure",
        "description": "Progressive thermal breakdown with reduced RPM and elevated process temperature.",
        "target_fault": "Heat Dissipation Failure",
        "file": "heat_dissipation.yaml",
    },
    "SCN-03": {
        "name": "Overstrain Failure",
        "description": "Elevated torque combined with excessive tool wear driving mechanical overstrain.",
        "target_fault": "Overstrain Failure",
        "file": "overstrain.yaml",
    },
    "SCN-04": {
        "name": "Power Failure and Safety Trip",
        "description": "Current surge exceeding power limits, triggering edge hardware safety trip.",
        "target_fault": "Power Failure",
        "file": "power_failure.yaml",
    },
    "SCN-05": {
        "name": "Tool Wear Degradation",
        "description": "Tool wear exceeding 240 minutes, triggering Layer 4 maintenance override.",
        "target_fault": "Tool Wear Failure",
        "file": "tool_wear.yaml",
    },
    "SCN-06": {
        "name": "Random Vibration Cluster",
        "description": "Sudden abnormal vibration spike without thermal precursors.",
        "target_fault": "Random Failures",
        "file": "random_vibration.yaml",
    },
    "SCN-07": {
        "name": "Sensor Dropout and Quality Marking",
        "description": "Transient missing sensor observations correctly assigned MISSING flags.",
        "target_fault": "Sensor Dropout",
        "file": "sensor_dropout.yaml",
    },
    "SCN-08": {
        "name": "Machine Offline and LWT",
        "description": "Abrupt communication stoppage verifying OFFLINE transition and last-will message.",
        "target_fault": "Offline State",
        "file": "machine_offline.yaml",
    },
}


class ScenarioSummary(BaseModel):
    """Metadata for an available simulation scenario."""

    scenario_id: str = Field(..., description="Canonical identifier (e.g. SCN-01)")
    name: str = Field(..., description="Human-readable scenario name")
    description: str = Field(..., description="Scenario description and physical dynamics")
    target_fault: str = Field(..., description="Target failure mode or operational state")


class ScenarioListResponse(BaseModel):
    """List of available simulation scenarios."""

    scenarios: list[ScenarioSummary]
    total: int


class ScenarioInjectRequest(BaseModel):
    """Request payload for scenario injection on a simulated asset."""

    machine_id: str = Field(
        ...,
        pattern=r"^[A-Z0-9_-]{1,32}$",
        description="Target machine identifier (e.g. MOT-1001)",
    )
    scenario_id: ScenarioID = Field(
        ..., description="Canonical scenario identifier (SCN-01 to SCN-08)"
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional bounded parameters for scenario execution (no code execution allowed)",
    )


class ScenarioInjectResponse(BaseModel):
    """Confirmation payload returned upon successful command validation and dispatch."""

    command_id: str = Field(..., description="Unique UUID tracking the command execution")
    machine_id: str = Field(..., description="Target machine identifier")
    scenario_id: str = Field(..., description="Injected scenario identifier")
    status: str = Field(..., description="Command dispatch status (e.g. ACCEPTED, DISPATCHED)")
    message: str = Field(..., description="Descriptive status message")
    injected_by: str = Field(
        ..., description="Username of the authorizing engineer or administrator"
    )
    injected_at: datetime = Field(..., description="Timestamp when command was authorized")
