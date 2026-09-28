"""
tests/api/test_health_engine.py — Unit tests for Health Engine (Layers 1-6) and Recommendation Engine.

Tests cover:
- Layer 1 Sensor Condition & Clamped Penalty [0, 15]
- Layer 2 ML Risk Bands & Thresholds
- Layer 3 Anomaly Normalization [0, 1] & Flag
- Layer 4 Composite Health Score & Deterministic State Precedence
- Layer 5 Alert Severity Assignment & Hysteresis Transitions
- Layer 6 Recommendation Generator & Domain Action Codes
"""

from __future__ import annotations

import pytest

from api.app.inference.health_engine import HealthEngine
from api.app.inference.recommendations import (
    ACTION_CALIBRATE_SENSORS,
    ACTION_CHECK_CONNECTIVITY,
    ACTION_CHECK_ELECTRICAL,
    ACTION_CHECK_MECHANICAL_OVERLOAD,
    ACTION_CHECK_PRESSURE_SEALS,
    ACTION_DIAGNOSTIC_AUDIT,
    ACTION_EMERGENCY_INSPECT,
    ACTION_INSPECT_BEARINGS_VIBRATION,
    ACTION_INSPECT_COOLING,
    ACTION_REPLACE_TOOL,
    ACTION_ROUTINE_MONITOR,
    generate_recommendation,
)


@pytest.fixture
def nominal_payload() -> dict:
    """Nominal healthy telemetry payload."""
    return {
        "version": "1.0",
        "machine_id": "MOT-1001",
        "ts": "2026-09-28T12:00:00Z",
        "seq": 101,
        "signals": {
            "air_temperature_c": 25.0,
            "process_temperature_c": 35.0,
            "rotational_speed_rpm": 1500.0,
            "torque_nm": 40.0,
            "vibration_mm_s": 1.5,
            "pressure_bar": 2.0,
            "current_a": 8.0,
            "voltage_v": 230.0,
            "tool_wear_min": 50.0,
            "operating_hours": 120.0,
        },
        "quality": {
            "air_temperature_c": "OK",
            "process_temperature_c": "OK",
            "rotational_speed_rpm": "OK",
            "torque_nm": "OK",
            "vibration_mm_s": "OK",
            "pressure_bar": "OK",
            "current_a": "OK",
            "voltage_v": "OK",
            "tool_wear_min": "OK",
            "operating_hours": "OK",
        },
        "edge": {"trip": False, "delta_t_c": 10.0, "power_va": 1840.0},
    }


class TestHealthEngineLayers:
    """Test suite for Layers 1 through 5 in HealthEngine."""

    def test_layer1_sensor_conditions_nominal(self, nominal_payload: dict):
        engine = HealthEngine()
        assessment = engine.evaluate_payload(
            nominal_payload, failure_probability=0.01, anomaly_score=0.05
        )

        assert assessment.out_of_range_count == 0
        assert assessment.missing_count == 0
        assert assessment.sensor_penalty == 0.0
        assert not assessment.is_degraded
        assert assessment.health_state == "HEALTHY"
        assert assessment.health_score is not None and assessment.health_score >= 95.0

    def test_layer1_sensor_penalty_clamping(self, nominal_payload: dict):
        engine = HealthEngine()
        # Create a payload with 4 missing and 2 out_of_range sensors -> raw = 5*2 + 5*4 = 30 -> clamped to 15.0
        bad_payload = dict(nominal_payload)
        bad_payload["signals"] = {
            "air_temperature_c": 25.0,
            "process_temperature_c": 35.0,
            # missing 8 sensors
        }
        bad_payload["quality"] = {
            "air_temperature_c": "OUT_OF_RANGE",
            "process_temperature_c": "OUT_OF_RANGE",
        }

        assessment = engine.evaluate_payload(
            bad_payload, failure_probability=0.02, anomaly_score=0.1
        )
        assert assessment.out_of_range_count == 2
        assert assessment.missing_count == 8
        assert assessment.sensor_penalty == 15.0  # strictly clamped at 15
        assert assessment.is_degraded is True
        assert assessment.health_state == "WARNING"

    def test_layer2_risk_bands(self, nominal_payload: dict):
        engine = HealthEngine()

        # LOW: < 0.15
        a1 = engine.evaluate_payload(nominal_payload, failure_probability=0.05)
        assert a1.risk_band == "LOW"
        assert a1.failure_prediction == 0

        # MEDIUM: 0.15 <= p < 0.16
        a2 = engine.evaluate_payload(nominal_payload, failure_probability=0.155)
        assert a2.risk_band == "MEDIUM"
        assert a2.failure_prediction == 0

        # HIGH: 0.16 <= p < 0.80
        a3 = engine.evaluate_payload(nominal_payload, failure_probability=0.50)
        assert a3.risk_band == "HIGH"
        assert a3.failure_prediction == 1

        # CRITICAL: >= 0.80
        a4 = engine.evaluate_payload(nominal_payload, failure_probability=0.85)
        assert a4.risk_band == "CRITICAL"
        assert a4.failure_prediction == 1

    def test_layer4_deterministic_state_precedence_offline(self, nominal_payload: dict):
        engine = HealthEngine()
        # OFFLINE takes precedence over everything
        assessment = engine.evaluate_payload(
            nominal_payload,
            failure_probability=0.99,
            anomaly_score=0.99,
            is_offline=True,
        )
        assert assessment.health_state == "OFFLINE"
        assert assessment.health_score is None

    def test_layer4_deterministic_state_precedence_maintenance_required(
        self, nominal_payload: dict
    ):
        engine = HealthEngine()
        # Tool wear >= 240 takes precedence over CRITICAL/WARNING
        payload = dict(nominal_payload)
        payload["signals"] = dict(nominal_payload["signals"])
        payload["signals"]["tool_wear_min"] = 245.0

        assessment = engine.evaluate_payload(payload, failure_probability=0.05)
        assert assessment.health_state == "MAINTENANCE_REQUIRED"

        # Technician confirmation also forces MAINTENANCE_REQUIRED
        assessment_tech = engine.evaluate_payload(
            nominal_payload,
            failure_probability=0.05,
            technician_confirmed_maintenance=True,
        )
        assert assessment_tech.health_state == "MAINTENANCE_REQUIRED"

    def test_layer4_deterministic_state_precedence_critical(self, nominal_payload: dict):
        engine = HealthEngine()

        # High failure probability (>= 0.80) -> CRITICAL
        a1 = engine.evaluate_payload(nominal_payload, failure_probability=0.85)
        assert a1.health_state == "CRITICAL"

        # Hardware safety trip -> CRITICAL
        trip_payload = dict(nominal_payload)
        trip_payload["edge"] = {"trip": True}
        a2 = engine.evaluate_payload(trip_payload, failure_probability=0.02)
        assert a2.health_state == "CRITICAL"

        # Low health score (< 50) -> CRITICAL
        # Delta_risk = 60 * 0.70 = 42, Delta_anomaly = 25 * 0.60 = 15 -> score = 100 - 57 = 43 < 50
        a3 = engine.evaluate_payload(nominal_payload, failure_probability=0.70, anomaly_score=0.60)
        assert a3.health_score is not None and a3.health_score < 50.0
        assert a3.health_state == "CRITICAL"

    def test_layer4_deterministic_state_precedence_warning(self, nominal_payload: dict):
        engine = HealthEngine()

        # Moderate failure probability (>= 0.15) -> WARNING
        a1 = engine.evaluate_payload(nominal_payload, failure_probability=0.20)
        assert a1.health_state == "WARNING"

        # Anomaly flag triggered (score >= 0.50) -> WARNING
        a2 = engine.evaluate_payload(nominal_payload, failure_probability=0.02, anomaly_score=0.65)
        assert a2.health_state == "WARNING"

    def test_layer5_alert_severity_and_hysteresis(self, nominal_payload: dict):
        engine = HealthEngine()

        # 1. Step 1: Nominal Healthy -> No alert
        a1 = engine.evaluate_payload(nominal_payload, failure_probability=0.02)
        assert a1.alert_severity is None

        # 2. Step 2: Warning condition -> WARNING alert
        a2 = engine.evaluate_payload(nominal_payload, failure_probability=0.25)
        assert a2.alert_severity == "WARNING"
        assert a2.alert_type == "WARNING_ELEVATED_RISK"

        # 3. Step 3: Critical condition -> CRITICAL alert
        a3 = engine.evaluate_payload(nominal_payload, failure_probability=0.90)
        assert a3.alert_severity == "CRITICAL"
        assert a3.alert_type == "CRITICAL_MACHINE_HEALTH"

        # 4. Step 4: Machine recovers back to Healthy -> INFO recovery alert
        a4 = engine.evaluate_payload(nominal_payload, failure_probability=0.02)
        assert a4.alert_severity == "INFO"
        assert a4.alert_type == "RECOVERED_TO_HEALTHY"

        # 5. Step 5: Second healthy reading -> None
        a5 = engine.evaluate_payload(nominal_payload, failure_probability=0.02)
        assert a5.alert_severity is None


class TestLayer6Recommendations:
    """Test suite for Layer 6 actionable recommendations."""

    def test_emergency_hardware_trip_recommendation(self):
        rec = generate_recommendation(
            health_state="CRITICAL",
            hardware_trip=True,
        )
        assert rec.action_code == ACTION_EMERGENCY_INSPECT
        assert rec.urgency == "IMMEDIATE"
        assert rec.target_component == "SAFETY_SYSTEM"

    def test_tool_wear_recommendation(self):
        rec = generate_recommendation(
            health_state="MAINTENANCE_REQUIRED",
            tool_wear_min=242.5,
        )
        assert rec.action_code == ACTION_REPLACE_TOOL
        assert "242.5 min" in rec.recommendation_text
        assert rec.target_component == "TOOLING"

    def test_thermal_cooling_recommendation(self):
        top_factors = [
            {
                "feature_name": "Process_Temperature_C",
                "shap_value": 0.85,
                "abs_magnitude": 0.85,
            },
            {"feature_name": "Delta_T_C", "shap_value": 0.40, "abs_magnitude": 0.40},
        ]
        rec = generate_recommendation(
            health_state="WARNING",
            top_factors=top_factors,
            failure_probability=0.30,
        )
        assert rec.action_code == ACTION_INSPECT_COOLING
        assert rec.target_component == "THERMAL_COOLING"

    def test_electrical_recommendation(self):
        top_factors = [{"feature_name": "Current_A", "shap_value": 1.10, "abs_magnitude": 1.10}]
        rec = generate_recommendation(
            health_state="CRITICAL",
            top_factors=top_factors,
            failure_probability=0.85,
        )
        assert rec.action_code == ACTION_CHECK_ELECTRICAL
        assert rec.urgency == "HIGH"
        assert rec.target_component == "ELECTRICAL_SUPPLY"

    def test_mechanical_overload_recommendation(self):
        top_factors = [{"feature_name": "Torque_Nm", "shap_value": 0.75, "abs_magnitude": 0.75}]
        rec = generate_recommendation(
            health_state="WARNING",
            top_factors=top_factors,
            failure_probability=0.45,
        )
        assert rec.action_code == ACTION_CHECK_MECHANICAL_OVERLOAD
        assert rec.target_component == "DRIVE_TRAIN"

    def test_vibration_recommendation(self):
        top_factors = [
            {
                "feature_name": "Vibration_mm_s",
                "shap_value": 0.95,
                "abs_magnitude": 0.95,
            }
        ]
        rec = generate_recommendation(
            health_state="WARNING",
            top_factors=top_factors,
            failure_probability=0.40,
        )
        assert rec.action_code == ACTION_INSPECT_BEARINGS_VIBRATION
        assert rec.target_component == "BEARINGS_ROTORS"

    def test_pressure_recommendation(self):
        top_factors = [{"feature_name": "Pressure_bar", "shap_value": 0.60, "abs_magnitude": 0.60}]
        rec = generate_recommendation(
            health_state="WARNING",
            top_factors=top_factors,
            failure_probability=0.25,
        )
        assert rec.action_code == ACTION_CHECK_PRESSURE_SEALS
        assert rec.target_component == "PRESSURE_HYDRAULICS"

    def test_sensor_calibration_recommendation(self):
        rec = generate_recommendation(
            health_state="WARNING",
            out_of_range_count=2,
            missing_count=1,
        )
        assert rec.action_code == ACTION_CALIBRATE_SENSORS
        assert rec.target_component == "SENSORS_TELEM"

    def test_unsupervised_anomaly_recommendation(self):
        rec = generate_recommendation(
            health_state="WARNING",
            anomaly_flag=True,
            top_factors=[],
        )
        assert rec.action_code == ACTION_DIAGNOSTIC_AUDIT
        assert rec.target_component == "GENERAL_SYSTEM"

    def test_nominal_routine_recommendation(self):
        rec = generate_recommendation(health_state="HEALTHY")
        assert rec.action_code == ACTION_ROUTINE_MONITOR
        assert rec.urgency == "ROUTINE"

    def test_offline_recommendation(self):
        rec = generate_recommendation(health_state="OFFLINE")
        assert rec.action_code == ACTION_CHECK_CONNECTIVITY
        assert rec.urgency == "LOW"
