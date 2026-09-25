"""
tests/ml/test_health.py - Unit tests for Layer 4 health score and state engine (T-014).

Test Groups:
- H1: Sensor penalty computation & clamping [0, 15]
- H2: Health score range [0, 100], component penalties, offline None output
- H3: State precedence 1: OFFLINE overrides all other states
- H4: State precedence 2: MAINTENANCE_REQUIRED operational override
- H5: State precedence 3: CRITICAL conditions
- H6: State precedence 4 & 5: WARNING and HEALTHY conditions
- H7: evaluate_machine_health bundle and degraded telemetry flags
"""

from __future__ import annotations

from ml.models.health import (
    STATE_CRITICAL,
    STATE_HEALTHY,
    STATE_MAINTENANCE_REQUIRED,
    STATE_OFFLINE,
    STATE_WARNING,
    compute_health_score,
    compute_sensor_penalty,
    determine_health_state,
    evaluate_machine_health,
)

# ---------------------------------------------------------------------------
# H1: Sensor penalty clamping
# ---------------------------------------------------------------------------


class TestSensorPenalty:
    """H1: Sensor penalty is strictly bounded in [0, 15]."""

    def test_zero_faults_gives_zero_penalty(self) -> None:
        assert compute_sensor_penalty(0, 0) == 0.0

    def test_single_fault_penalty(self) -> None:
        assert compute_sensor_penalty(out_of_range_count=1, missing_count=0) == 5.0
        assert compute_sensor_penalty(out_of_range_count=0, missing_count=1) == 5.0

    def test_two_faults_penalty(self) -> None:
        assert compute_sensor_penalty(out_of_range_count=1, missing_count=1) == 10.0

    def test_three_faults_max_cap(self) -> None:
        assert compute_sensor_penalty(out_of_range_count=2, missing_count=1) == 15.0

    def test_many_faults_strictly_clamped_to_15(self) -> None:
        # Multiple faults must never produce an unbounded penalty > 15
        assert compute_sensor_penalty(out_of_range_count=10, missing_count=10) == 15.0

    def test_negative_fault_counts_handled_safely(self) -> None:
        assert compute_sensor_penalty(out_of_range_count=-1, missing_count=-5) == 0.0


# ---------------------------------------------------------------------------
# H2: Health score formula & bounds
# ---------------------------------------------------------------------------


class TestHealthScoreComputation:
    """H2: Score calculation, bounds [0, 100], and offline None behavior."""

    def test_perfect_healthy_conditions(self) -> None:
        score = compute_health_score(calibrated_p_fail=0.0, anomaly_score=0.0, delta_sensor=0.0)
        assert score == 100.0

    def test_max_failure_penalty(self) -> None:
        # p=1.0 subtracts 60 points -> 40.0
        score = compute_health_score(calibrated_p_fail=1.0, anomaly_score=0.0, delta_sensor=0.0)
        assert score == 40.0

    def test_max_anomaly_penalty(self) -> None:
        # a=1.0 subtracts 25 points -> 75.0
        score = compute_health_score(calibrated_p_fail=0.0, anomaly_score=1.0, delta_sensor=0.0)
        assert score == 75.0

    def test_max_combined_deductions_clamped_at_zero(self) -> None:
        # 100 - (60 + 25 + 15) = 0.0
        score = compute_health_score(calibrated_p_fail=1.0, anomaly_score=1.0, delta_sensor=15.0)
        assert score == 0.0

    def test_offline_returns_none(self) -> None:
        assert compute_health_score(calibrated_p_fail=0.05, is_offline=True) is None

    def test_none_probability_returns_none(self) -> None:
        assert compute_health_score(calibrated_p_fail=None) is None


# ---------------------------------------------------------------------------
# H3 - H6: Deterministic Precedence Hierarchy
# ---------------------------------------------------------------------------


class TestHealthStatePrecedence:
    """H3-H6: Strict precedence: OFFLINE > MAINTENANCE_REQUIRED > CRITICAL > WARNING > HEALTHY."""

    def test_precedence_1_offline_overrides_all(self) -> None:
        # Even with high tool wear, critical probability, hardware trip: OFFLINE wins
        state = determine_health_state(
            health_score=None,
            calibrated_p_fail=0.99,
            tool_wear_min=300.0,
            hardware_trip=True,
            is_offline=True,
        )
        assert state == STATE_OFFLINE

    def test_precedence_2_maintenance_required_override(self) -> None:
        # Tool wear >= 240 overrides CRITICAL, WARNING, HEALTHY
        state = determine_health_state(
            health_score=30.0,
            calibrated_p_fail=0.85,
            tool_wear_min=240.0,
            is_offline=False,
        )
        assert state == STATE_MAINTENANCE_REQUIRED

        # Technician confirmation also triggers MAINTENANCE_REQUIRED
        state_tech = determine_health_state(
            health_score=95.0,
            calibrated_p_fail=0.02,
            technician_confirmed_maintenance=True,
            is_offline=False,
        )
        assert state_tech == STATE_MAINTENANCE_REQUIRED

    def test_precedence_3_critical_conditions(self) -> None:
        # Low health score < 50
        state1 = determine_health_state(
            health_score=49.0,
            calibrated_p_fail=0.50,
            tool_wear_min=100.0,
        )
        assert state1 == STATE_CRITICAL

        # High probability >= 0.80
        state2 = determine_health_state(
            health_score=60.0,
            calibrated_p_fail=0.80,
            tool_wear_min=100.0,
        )
        assert state2 == STATE_CRITICAL

        # Hardware safety trip
        state3 = determine_health_state(
            health_score=90.0,
            calibrated_p_fail=0.05,
            hardware_trip=True,
        )
        assert state3 == STATE_CRITICAL

    def test_precedence_4_warning_conditions(self) -> None:
        # Score in [50, 80)
        state1 = determine_health_state(
            health_score=75.0,
            calibrated_p_fail=0.10,
            tool_wear_min=50.0,
        )
        assert state1 == STATE_WARNING

        # Probability in [0.15, 0.80)
        state2 = determine_health_state(
            health_score=85.0,
            calibrated_p_fail=0.15,
            tool_wear_min=50.0,
        )
        assert state2 == STATE_WARNING

        # Anomaly flag triggered
        state3 = determine_health_state(
            health_score=90.0,
            calibrated_p_fail=0.05,
            anomaly_score=0.60,
            anomaly_threshold=0.50,
        )
        assert state3 == STATE_WARNING

        # Sensor penalty > 0
        state4 = determine_health_state(
            health_score=95.0,
            calibrated_p_fail=0.02,
            delta_sensor=5.0,
        )
        assert state4 == STATE_WARNING

        # 3 or more missing sensors
        state5 = determine_health_state(
            health_score=85.0,
            calibrated_p_fail=0.02,
            missing_sensor_count=3,
        )
        assert state5 == STATE_WARNING

    def test_precedence_5_healthy_condition(self) -> None:
        state = determine_health_state(
            health_score=92.0,
            calibrated_p_fail=0.05,
            anomaly_score=0.10,
            anomaly_threshold=0.50,
            delta_sensor=0.0,
            tool_wear_min=60.0,
            missing_sensor_count=0,
        )
        assert state == STATE_HEALTHY


# ---------------------------------------------------------------------------
# H7: evaluate_machine_health bundle
# ---------------------------------------------------------------------------


class TestEvaluateMachineHealthBundle:
    """H7: Comprehensive dictionary bundle output."""

    def test_bundle_structure_and_degraded_flag(self) -> None:
        bundle = evaluate_machine_health(
            calibrated_p_fail=0.05,
            anomaly_score=0.20,
            out_of_range_count=1,
            missing_count=2,
            tool_wear_min=80.0,
        )
        assert bundle["health_score"] is not None
        assert 0.0 <= bundle["health_score"] <= 100.0
        assert bundle["health_state"] == STATE_WARNING
        assert bundle["delta_sensor"] == 15.0  # (1 + 2) * 5 = 15
        assert bundle["is_degraded"] is True
        assert bundle["is_offline"] is False
