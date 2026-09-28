"""
api/app/inference/health_engine.py — Comprehensive Health Engine implementing Layers 1 through 6.

Evaluates:
- Layer 1: Sensor Condition & Quality Penalties [0, 15]
- Layer 2: Supervised ML Failure Risk & Risk Bands
- Layer 3: Unsupervised Anomaly Detection [0, 1]
- Layer 4: Composite Machine Health Score [0, 100] & State Precedence
- Layer 5: Alert Severity with State Hysteresis
- Layer 6: Actionable Maintenance Recommendations
"""

from __future__ import annotations

import logging
from typing import Any

from api.app.inference.recommendations import generate_recommendation
from api.app.inference.schemas import HealthAssessment
from ml.models.health import (
    STATE_CRITICAL,
    STATE_MAINTENANCE_REQUIRED,
    STATE_OFFLINE,
    STATE_WARNING,
    TOOL_WEAR_MAINTENANCE_LIMIT_MIN,
    compute_health_score,
    compute_sensor_penalty,
    determine_health_state,
)

logger = logging.getLogger(__name__)


class HealthEngine:
    """Multi-layer health evaluation and alert engine with state tracking."""

    def __init__(self) -> None:
        # Per-machine state memory for hysteresis and transition tracking
        self._machine_history: dict[str, dict[str, Any]] = {}

    def reset_machine_history(self, machine_id: str | None = None) -> None:
        """Reset hysteresis tracking for a single machine or all machines."""
        if machine_id is not None:
            self._machine_history.pop(machine_id, None)
        else:
            self._machine_history.clear()

    def evaluate_payload(
        self,
        payload: dict[str, Any],
        *,
        failure_probability: float | None = None,
        anomaly_score: float | None = None,
        top_factors: list[dict[str, Any]] | None = None,
        technician_confirmed_maintenance: bool = False,
        is_offline: bool = False,
    ) -> HealthAssessment:
        """Evaluate full L1–L6 health assessment for a single telemetry message.

        Parameters
        ----------
        payload:
            Canonical validated telemetry dictionary conforming to edgetwin.telemetry.v1.
        failure_probability:
            Calibrated failure probability from Layer 2 model.
        anomaly_score:
            Normalized anomaly score from Layer 3 detector.
        top_factors:
            Top SHAP features from explainability module.
        technician_confirmed_maintenance:
            Technician manual work-order flag.
        is_offline:
            Offline / disconnected / stale stream flag.

        Returns
        -------
        HealthAssessment
            Structured multi-layer evaluation payload.
        """
        machine_id = str(payload.get("machine_id", "UNKNOWN"))
        signals = payload.get("signals", {})
        quality_block = payload.get("quality", {})
        edge_block = payload.get("edge", {})

        # -------------------------------------------------------------------
        # Layer 1: Sensor Condition & Penalties
        # -------------------------------------------------------------------
        out_of_range_count = 0
        missing_count = 0
        sensor_status: dict[str, str] = {}

        # Canonical sensor channel keys
        wire_to_canonical = {
            "air_temp_c": ("air_temp_c", "air_temperature_c"),
            "process_temp_c": ("process_temp_c", "process_temperature_c"),
            "rotational_speed_rpm": ("rotational_speed_rpm",),
            "torque_nm": ("torque_nm",),
            "vibration_mm_s": ("vibration_mm_s",),
            "pressure_bar": ("pressure_bar",),
            "current_a": ("current_a",),
            "voltage_v": ("voltage_v",),
            "tool_wear_min": ("tool_wear_min",),
            "operating_hours": ("operating_hours",),
        }

        for canonical_key, aliases in wire_to_canonical.items():
            val = None
            q_flag = "OK"
            for alias in aliases:
                if alias in signals and signals[alias] is not None:
                    val = signals[alias]
                if quality_block and alias in quality_block:
                    q_flag = quality_block[alias]

            if val is None:
                missing_count += 1
                sensor_status[canonical_key] = "MISSING"
            elif q_flag == "OUT_OF_RANGE":
                out_of_range_count += 1
                sensor_status[canonical_key] = "OUT_OF_RANGE"
            else:
                sensor_status[canonical_key] = q_flag

        delta_sensor = compute_sensor_penalty(
            out_of_range_count=out_of_range_count,
            missing_count=missing_count,
        )
        is_degraded = missing_count >= 3 or delta_sensor > 0.0

        # Extract tool wear and hardware safety trip flag
        tool_wear_val = signals.get("tool_wear_min")
        tool_wear_min = float(tool_wear_val) if tool_wear_val is not None else None
        hardware_trip = bool(edge_block.get("trip", False))

        # -------------------------------------------------------------------
        # Layer 2: Supervised ML Failure Risk
        # -------------------------------------------------------------------
        p_cal = float(failure_probability) if failure_probability is not None else None
        failure_prediction = int(p_cal >= 0.16) if p_cal is not None else None
        risk_band: str | None = None
        if p_cal is not None:
            if p_cal < 0.15:
                risk_band = "LOW"
            elif p_cal < 0.16:
                risk_band = "MEDIUM"
            elif p_cal < 0.80:
                risk_band = "HIGH"
            else:
                risk_band = "CRITICAL"

        # -------------------------------------------------------------------
        # Layer 3: Unsupervised Anomaly Detection
        # -------------------------------------------------------------------
        a_score = float(anomaly_score) if anomaly_score is not None else None
        anomaly_flag = (a_score >= 0.50) if a_score is not None else None

        # -------------------------------------------------------------------
        # Layer 4: Composite Machine Health Score & State Precedence
        # -------------------------------------------------------------------
        health_score = compute_health_score(
            calibrated_p_fail=p_cal,
            anomaly_score=a_score,
            delta_sensor=delta_sensor,
            is_offline=is_offline,
        )

        health_state = determine_health_state(
            health_score=health_score,
            calibrated_p_fail=p_cal,
            anomaly_score=a_score,
            anomaly_threshold=0.50,
            delta_sensor=delta_sensor,
            tool_wear_min=tool_wear_min,
            technician_confirmed_maintenance=technician_confirmed_maintenance,
            is_offline=is_offline,
            hardware_trip=hardware_trip,
            missing_sensor_count=missing_count,
        )

        delta_risk = 60.0 * min(1.0, max(0.0, p_cal)) if p_cal is not None else None
        delta_anomaly = 25.0 * min(1.0, max(0.0, a_score)) if a_score is not None else None

        # -------------------------------------------------------------------
        # Layer 5: Alert Severity with Hysteresis
        # -------------------------------------------------------------------
        alert_severity: str | None = None
        alert_type: str | None = None
        trigger_conditions: dict[str, Any] = {}

        if hardware_trip:
            alert_severity = "CRITICAL"
            alert_type = "HARDWARE_SAFETY_TRIP"
            trigger_conditions["reason"] = "Edge controller hardware trip active"
            trigger_conditions["trip"] = True
        elif health_state == STATE_CRITICAL:
            alert_severity = "CRITICAL"
            alert_type = "CRITICAL_MACHINE_HEALTH"
            trigger_conditions["health_score"] = health_score
            trigger_conditions["p_fail"] = p_cal
            trigger_conditions["threshold"] = "health_score < 50 or p_fail >= 0.80"
        elif health_state == STATE_MAINTENANCE_REQUIRED:
            alert_severity = "WARNING"
            alert_type = "MAINTENANCE_REQUIRED"
            trigger_conditions["tool_wear_min"] = tool_wear_min
            trigger_conditions["limit"] = TOOL_WEAR_MAINTENANCE_LIMIT_MIN
        elif health_state == STATE_WARNING:
            alert_severity = "WARNING"
            alert_type = "WARNING_ELEVATED_RISK"
            trigger_conditions["health_score"] = health_score
            trigger_conditions["p_fail"] = p_cal
            trigger_conditions["anomaly_score"] = a_score
            trigger_conditions["delta_sensor"] = delta_sensor
        elif health_state == STATE_OFFLINE:
            alert_severity = "INFO"
            alert_type = "MACHINE_OFFLINE"
            trigger_conditions["is_offline"] = True
        else:
            # STATE_HEALTHY: Check if recovering from previous warning/critical
            prev_record = self._machine_history.get(machine_id)
            if prev_record and prev_record.get("alert_severity") in ("WARNING", "CRITICAL"):
                alert_severity = "INFO"
                alert_type = "RECOVERED_TO_HEALTHY"
                trigger_conditions["message"] = "Machine health returned to nominal parameters"

        # Update machine history
        self._machine_history[machine_id] = {
            "health_state": health_state,
            "health_score": health_score,
            "alert_severity": alert_severity,
            "p_fail": p_cal,
        }

        # -------------------------------------------------------------------
        # Layer 6: Actionable Maintenance Recommendation
        # -------------------------------------------------------------------
        recommendation = generate_recommendation(
            health_state=health_state,
            top_factors=top_factors,
            hardware_trip=hardware_trip,
            tool_wear_min=tool_wear_min,
            out_of_range_count=out_of_range_count,
            missing_count=missing_count,
            failure_probability=p_cal,
            anomaly_flag=anomaly_flag,
        )

        return HealthAssessment(
            out_of_range_count=out_of_range_count,
            missing_count=missing_count,
            sensor_penalty=delta_sensor,
            sensor_status=sensor_status,
            is_degraded=is_degraded,
            failure_probability=p_cal,
            failure_prediction=failure_prediction,
            risk_band=risk_band,
            anomaly_score=a_score,
            anomaly_flag=anomaly_flag,
            health_score=health_score,
            health_state=health_state,
            delta_risk=delta_risk,
            delta_anomaly=delta_anomaly,
            alert_severity=alert_severity,
            alert_type=alert_type,
            trigger_conditions=trigger_conditions,
            recommendation=recommendation,
        )
