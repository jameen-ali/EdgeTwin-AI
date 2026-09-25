"""
ml/models/health.py - EdgeTwin AI Layer 4 health score and state engine.

T-014: Calculates the explainable, deterministic L4 machine health score [0, 100]
and implements deterministic health-state precedence per architecture.md §4.

Health Score Formula
--------------------
Health Score = clip(100 - (Delta_risk + Delta_anomaly + Delta_sensor), 0.0, 100.0)

Where:
- Delta_risk = 60.0 * calibrated_failure_probability (0 <= p <= 1)
- Delta_anomaly = 25.0 * anomaly_score (0 <= a <= 1)
- Delta_sensor = min(15.0, max(0.0, 5 * N_out_of_range + 5 * N_missing))
  (Strictly enforced: 0 <= Delta_sensor <= 15)

Deterministic State Precedence Hierarchy
-----------------------------------------
1. OFFLINE:
   Telemetry loss, stale > 3x sampling period, broker disconnected, or missing reading.
   Output: health_score = None, state = OFFLINE.

2. MAINTENANCE_REQUIRED:
   Operational rule override (NOT an ML target):
   Tool_Wear_Min >= 240.0 min OR technician confirmed overhaul.
   Output: state = MAINTENANCE_REQUIRED.

3. CRITICAL:
   Health Score < 50.0 OR calibrated_p_fail >= 0.80 OR hardware trip.
   Output: state = CRITICAL.

4. WARNING:
   50.0 <= Health Score < 80.0 OR calibrated_p_fail >= 0.15 OR anomaly_flag == True
   OR Delta_sensor > 0.0 OR missing_sensor_count >= 3.
   Output: state = WARNING.

5. HEALTHY:
   Health Score >= 80.0 AND calibrated_p_fail < 0.15 AND anomaly_flag == False
   AND Delta_sensor == 0.0 AND missing_sensor_count < 3.
   Output: state = HEALTHY.

Author: T-014 / S05
"""

from __future__ import annotations

from typing import Any

# Health States per architecture.md §4
STATE_HEALTHY: str = "HEALTHY"
STATE_WARNING: str = "WARNING"
STATE_CRITICAL: str = "CRITICAL"
STATE_MAINTENANCE_REQUIRED: str = "MAINTENANCE_REQUIRED"
STATE_OFFLINE: str = "OFFLINE"

HEALTH_STATES: tuple[str, ...] = (
    STATE_HEALTHY,
    STATE_WARNING,
    STATE_CRITICAL,
    STATE_MAINTENANCE_REQUIRED,
    STATE_OFFLINE,
)

# Threshold Constants
TOOL_WEAR_MAINTENANCE_LIMIT_MIN: float = 240.0
PROB_WARNING_THRESHOLD: float = 0.15
PROB_CRITICAL_THRESHOLD: float = 0.80
HEALTH_WARNING_THRESHOLD: float = 80.0
HEALTH_CRITICAL_THRESHOLD: float = 50.0
MAX_SENSOR_PENALTY: float = 15.0


def compute_sensor_penalty(
    out_of_range_count: int = 0,
    missing_count: int = 0,
) -> float:
    """Calculate clamped sensor-quality penalty (0 <= Delta_sensor <= 15).

    Parameters
    ----------
    out_of_range_count:
        Number of sensor channels violating physical bounds.
    missing_count:
        Number of unpopulated / null sensor channels.

    Returns
    -------
    float
        Clamped penalty in [0.0, 15.0].
    """
    raw_penalty = 5.0 * max(0, out_of_range_count) + 5.0 * max(0, missing_count)
    return float(min(MAX_SENSOR_PENALTY, max(0.0, raw_penalty)))


def compute_health_score(
    calibrated_p_fail: float | None,
    anomaly_score: float | None = None,
    delta_sensor: float = 0.0,
    *,
    is_offline: bool = False,
) -> float | None:
    """Compute deterministic composite health score in [0.0, 100.0].

    Returns None if machine is OFFLINE or calibrated probability is unavailable.

    Parameters
    ----------
    calibrated_p_fail:
        Calibrated failure probability in [0.0, 1.0]. None if telemetry absent.
    anomaly_score:
        Normalized anomaly score in [0.0, 1.0]. Defaults to 0.0 if not computed.
    delta_sensor:
        Sensor quality penalty in [0.0, 15.0].
    is_offline:
        True if telemetry is lost or stale > 3x period.

    Returns
    -------
    float | None
        Composite score in [0.0, 100.0], or None if OFFLINE.
    """
    if is_offline or calibrated_p_fail is None:
        return None

    # Guard bounds
    p = float(min(1.0, max(0.0, calibrated_p_fail)))
    a = float(min(1.0, max(0.0, anomaly_score if anomaly_score is not None else 0.0)))
    s = (
        compute_sensor_penalty(out_of_range_count=0, missing_count=0)
        if delta_sensor <= 0
        else min(MAX_SENSOR_PENALTY, max(0.0, float(delta_sensor)))
    )

    delta_risk = 60.0 * p
    delta_anomaly = 25.0 * a

    score = 100.0 - (delta_risk + delta_anomaly + s)
    return float(min(100.0, max(0.0, score)))


def determine_health_state(
    health_score: float | None,
    calibrated_p_fail: float | None,
    *,
    anomaly_score: float | None = None,
    anomaly_threshold: float = 0.50,
    delta_sensor: float = 0.0,
    tool_wear_min: float | None = None,
    technician_confirmed_maintenance: bool = False,
    is_offline: bool = False,
    hardware_trip: bool = False,
    missing_sensor_count: int = 0,
) -> str:
    """Determine machine health state using strict deterministic precedence hierarchy.

    Precedence:
    1. OFFLINE
    2. MAINTENANCE_REQUIRED
    3. CRITICAL
    4. WARNING
    5. HEALTHY

    Parameters
    ----------
    health_score:
        Computed health score (None if offline).
    calibrated_p_fail:
        Calibrated failure probability.
    anomaly_score:
        Normalized anomaly score.
    anomaly_threshold:
        Anomaly decision threshold (default: 0.50).
    delta_sensor:
        Clamped sensor penalty.
    tool_wear_min:
        Current accumulated tool wear in minutes.
    technician_confirmed_maintenance:
        Operational override flag set by maintenance engineer.
    is_offline:
        True if communication lost or stale.
    hardware_trip:
        True if edge firmware safety limit tripped.
    missing_sensor_count:
        Count of missing telemetry channels.

    Returns
    -------
    str
        One of the 5 HEALTH_STATES.
    """
    # 1. OFFLINE precedence
    if is_offline or health_score is None:
        return STATE_OFFLINE

    # 2. MAINTENANCE_REQUIRED precedence (operational override)
    wear_exceeded = tool_wear_min is not None and tool_wear_min >= TOOL_WEAR_MAINTENANCE_LIMIT_MIN
    if wear_exceeded or technician_confirmed_maintenance:
        return STATE_MAINTENANCE_REQUIRED

    # 3. CRITICAL precedence
    p = calibrated_p_fail if calibrated_p_fail is not None else 0.0
    if health_score < HEALTH_CRITICAL_THRESHOLD or p >= PROB_CRITICAL_THRESHOLD or hardware_trip:
        return STATE_CRITICAL

    # 4. WARNING precedence
    anomaly_flag = anomaly_score is not None and anomaly_score >= anomaly_threshold
    if (
        health_score < HEALTH_WARNING_THRESHOLD
        or p >= PROB_WARNING_THRESHOLD
        or anomaly_flag
        or delta_sensor > 0.0
        or missing_sensor_count >= 3
    ):
        return STATE_WARNING

    # 5. HEALTHY precedence
    return STATE_HEALTHY


def evaluate_machine_health(
    calibrated_p_fail: float | None,
    anomaly_score: float | None = None,
    *,
    out_of_range_count: int = 0,
    missing_count: int = 0,
    tool_wear_min: float | None = None,
    technician_confirmed_maintenance: bool = False,
    is_offline: bool = False,
    hardware_trip: bool = False,
    anomaly_threshold: float = 0.50,
) -> dict[str, Any]:
    """Comprehensive health assessment bundle for Digital Twin state ingestion.

    Parameters
    ----------
    calibrated_p_fail:
        Calibrated positive failure probability.
    anomaly_score:
        Normalized anomaly score.
    out_of_range_count:
        Number of sensor range violations.
    missing_count:
        Number of missing sensor fields.
    tool_wear_min:
        Tool wear in minutes.
    technician_confirmed_maintenance:
        Technician override flag.
    is_offline:
        Communication loss flag.
    hardware_trip:
        Edge safety trip flag.
    anomaly_threshold:
        Threshold for anomaly flag.

    Returns
    -------
    dict[str, Any]
        Health assessment dict including score, state, breakdown penalties, and degraded status.
    """
    delta_sensor = compute_sensor_penalty(out_of_range_count, missing_count)
    score = compute_health_score(
        calibrated_p_fail=calibrated_p_fail,
        anomaly_score=anomaly_score,
        delta_sensor=delta_sensor,
        is_offline=is_offline,
    )
    state = determine_health_state(
        health_score=score,
        calibrated_p_fail=calibrated_p_fail,
        anomaly_score=anomaly_score,
        anomaly_threshold=anomaly_threshold,
        delta_sensor=delta_sensor,
        tool_wear_min=tool_wear_min,
        technician_confirmed_maintenance=technician_confirmed_maintenance,
        is_offline=is_offline,
        hardware_trip=hardware_trip,
        missing_sensor_count=missing_count,
    )

    delta_risk = (
        60.0 * min(1.0, max(0.0, calibrated_p_fail)) if calibrated_p_fail is not None else None
    )
    delta_anomaly = 25.0 * min(1.0, max(0.0, anomaly_score)) if anomaly_score is not None else None

    is_degraded = missing_count >= 3 or delta_sensor > 0.0

    return {
        "health_score": score,
        "health_state": state,
        "calibrated_p_fail": calibrated_p_fail,
        "anomaly_score": anomaly_score,
        "anomaly_flag": (
            (anomaly_score >= anomaly_threshold) if anomaly_score is not None else False
        ),
        "delta_risk": delta_risk,
        "delta_anomaly": delta_anomaly,
        "delta_sensor": delta_sensor,
        "is_degraded": is_degraded,
        "is_offline": is_offline,
    }
