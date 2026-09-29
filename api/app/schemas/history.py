"""History and operational analytics schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

HistoryWindow = Literal["1h", "6h", "24h", "7d", "30d"]


class HistoricalHealthPoint(BaseModel):
    """Historical machine health and operating state point."""

    ts: datetime = Field(..., description="Observation timestamp (UTC)")
    health_score: float = Field(..., description="Overall health score (0-100)")
    health_state: str = Field(
        ..., description="Categorical health state: HEALTHY, WARNING, CRITICAL, OFFLINE"
    )
    operating_state: str = Field(
        ...,
        description="Machine operational state: STOPPED, STARTING, RUNNING, DEGRADING, TRIPPED, UNKNOWN",
    )
    failure_probability: float | None = Field(
        None, description="Calibrated failure risk probability (0.0 to 1.0)"
    )

    model_config = ConfigDict(from_attributes=True)


class HistoricalSensorPoint(BaseModel):
    """Historical sensor observation point with downsampled or raw readings."""

    ts: datetime = Field(..., description="Observation timestamp (UTC)")
    process_temp_c: float | None = Field(None, description="Process contact temperature (°C)")
    air_temp_c: float | None = Field(None, description="Ambient air temperature (°C)")
    rotational_speed_rpm: float | None = Field(None, description="Rotational speed (RPM)")
    torque_nm: float | None = Field(None, description="Torque (Nm)")
    vibration_mm_s: float | None = Field(None, description="Vibration velocity RMS (mm/s)")
    pressure_bar: float | None = Field(None, description="Pressure (bar)")
    current_a: float | None = Field(None, description="Current (A)")
    voltage_v: float | None = Field(None, description="Voltage (V)")
    power_va: float | None = Field(None, description="Apparent power (VA)")
    tool_wear_min: float | None = Field(None, description="Tool wear (min)")

    model_config = ConfigDict(from_attributes=True)


class HistoricalPredictionPoint(BaseModel):
    """Historical ML model inference assessment."""

    id: int = Field(..., description="Prediction sequence identifier")
    ts: datetime = Field(..., description="Inference timestamp (UTC)")
    failure_probability: float = Field(
        ..., description="Calibrated failure probability (0.0 - 1.0)"
    )
    failure_prediction: int = Field(
        ..., description="Binary prediction classification at decision threshold"
    )
    risk_band: str = Field(..., description="Risk categorization: LOW, MEDIUM, HIGH, CRITICAL")
    anomaly_score: float | None = Field(
        None, description="Isolation forest unsupervised anomaly score"
    )
    anomaly_flag: bool | None = Field(None, description="Unsupervised anomaly indicator")
    model_version: str = Field(..., description="Governance model version key")
    top_factors: list[dict[str, Any]] | None = Field(None, description="SHAP feature attributions")

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class HistoricalAlertItem(BaseModel):
    """Historical alert record raised during the analysis window."""

    id: int = Field(..., description="Alert record identifier")
    alert_type: str = Field(..., description="Alert classification type")
    severity: str = Field(..., description="Severity level: INFO, WARNING, CRITICAL")
    status: str = Field(..., description="Lifecycle status: OPEN, ACKNOWLEDGED, RESOLVED")
    message: str = Field(..., description="Human-readable incident description")
    triggered_at: datetime = Field(..., description="Trigger timestamp (UTC)")
    acknowledged_at: datetime | None = Field(None, description="Acknowledgment timestamp (UTC)")
    resolved_at: datetime | None = Field(None, description="Resolution timestamp (UTC)")
    resolved_by: str | None = Field(None, description="User or technician who marked resolved")

    model_config = ConfigDict(from_attributes=True)


class HistoricalMaintenanceItem(BaseModel):
    """Historical maintenance event, inspection, or repair."""

    id: int = Field(..., description="Maintenance work order identifier")
    alert_id: int | None = Field(None, description="Linked incident alert ID")
    event_type: str = Field(
        ..., description="Activity type: INSPECTION, PART_REPLACEMENT, OVERHAUL, etc."
    )
    description: str = Field(..., description="Action notes and technician observations")
    status: str = Field(
        ..., description="Work order lifecycle: SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED"
    )
    technician: str | None = Field(None, description="Assigned technician or engineer")
    started_at: datetime | None = Field(None, description="Execution start timestamp (UTC)")
    completed_at: datetime | None = Field(None, description="Completion timestamp (UTC)")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")

    model_config = ConfigDict(from_attributes=True)


class MachineHistorySummary(BaseModel):
    """Defensible summary metrics calculated across the selected time horizon."""

    avg_health_score: float | None = Field(
        None, description="Mean health score across observed points"
    )
    min_health_score: float | None = Field(
        None, description="Lowest observed health score in window"
    )
    max_health_score: float | None = Field(
        None, description="Highest observed health score in window"
    )
    time_in_warning_s: int = Field(
        0, description="Defensible duration spent in WARNING state (seconds)"
    )
    time_in_critical_s: int = Field(
        0, description="Defensible duration spent in CRITICAL state (seconds)"
    )
    alert_count: int = Field(0, description="Total alerts triggered in window")
    resolved_alert_count: int = Field(0, description="Alerts resolved in window")
    maintenance_count: int = Field(0, description="Maintenance events logged in window")
    avg_failure_probability: float | None = Field(
        None, description="Mean failure risk probability in window"
    )
    sample_count: int = Field(0, description="Total discrete observations in window")


class MachineHistoryResponse(BaseModel):
    """Comprehensive bounded machine historical analytics payload."""

    machine_id: str = Field(..., description="Target industrial asset ID")
    machine_type: str = Field(..., description="Equipment classification")
    current_operating_state: str = Field(..., description="Current operational state")
    window: str = Field(..., description="Selected time horizon (e.g. 24h)")
    from_ts: datetime = Field(..., description="Window start timestamp (UTC)")
    to_ts: datetime = Field(..., description="Window end timestamp (UTC)")
    summary: MachineHistorySummary = Field(..., description="Window aggregate metrics")
    health_trend: list[HistoricalHealthPoint] = Field(
        ..., description="Time-series health progression"
    )
    sensor_trend: list[HistoricalSensorPoint] = Field(
        ..., description="Time-series telemetry observations"
    )
    prediction_history: list[HistoricalPredictionPoint] = Field(
        ..., description="Model inferences in window"
    )
    alerts: list[HistoricalAlertItem] = Field(..., description="Incident alert events in window")
    maintenance: list[HistoricalMaintenanceItem] = Field(
        ..., description="Maintenance actions in window"
    )
    is_downsampled: bool = Field(
        False, description="Flag indicating if time-series was downsampled"
    )
    downsample_interval_s: int | None = Field(None, description="Downsample bin width in seconds")


class FleetHealthDistribution(BaseModel):
    """Fleet-wide machine distribution by health state."""

    healthy: int = Field(0, description="Count of healthy machines (health >= 80)")
    warning: int = Field(0, description="Count of warning machines (60 <= health < 80)")
    critical: int = Field(0, description="Count of critical machines (health < 60)")
    offline: int = Field(0, description="Count of offline / uncommunicative machines")


class FleetRiskDistribution(BaseModel):
    """Fleet-wide machine distribution by ML failure risk band."""

    low: int = Field(0, description="Count of machines with LOW risk")
    medium: int = Field(0, description="Count of machines with MEDIUM risk")
    high: int = Field(0, description="Count of machines with HIGH risk")
    critical: int = Field(0, description="Count of machines with CRITICAL risk")


class FleetMachineSummary(BaseModel):
    """Per-machine high-level statistics for fleet analytics table."""

    machine_id: str = Field(..., description="Machine asset ID")
    machine_type: str = Field(..., description="Equipment classification")
    location: str | None = Field(None, description="Plant bay or location")
    operating_state: str = Field(..., description="Current operating state")
    health_state: str = Field(..., description="Current health classification")
    health_score: float | None = Field(None, description="Current or window-average health score")
    failure_probability: float | None = Field(
        None, description="Current or window-average failure probability"
    )
    alert_count: int = Field(0, description="Total alerts triggered in window")
    maintenance_count: int = Field(0, description="Maintenance events in window")


class FleetAlertCount(BaseModel):
    """Per-machine alert frequency for fleet triage."""

    machine_id: str = Field(..., description="Machine asset ID")
    alert_count: int = Field(0, description="Total alerts in window")
    critical_count: int = Field(0, description="Critical alerts in window")


class FleetHistoryResponse(BaseModel):
    """Aggregated fleet-level historical analytics payload."""

    window: str = Field(..., description="Selected time horizon (e.g. 24h)")
    from_ts: datetime = Field(..., description="Window start timestamp (UTC)")
    to_ts: datetime = Field(..., description="Window end timestamp (UTC)")
    total_machines: int = Field(0, description="Total registered industrial assets")
    avg_fleet_health: float | None = Field(None, description="Fleet-wide mean health score")
    health_distribution: FleetHealthDistribution = Field(
        ..., description="Machine counts by health status"
    )
    risk_distribution: FleetRiskDistribution = Field(..., description="Machine counts by risk band")
    alerts_by_machine: list[FleetAlertCount] = Field(..., description="Alert frequency per asset")
    machine_summaries: list[FleetMachineSummary] = Field(
        ..., description="Per-machine analytics summaries"
    )
