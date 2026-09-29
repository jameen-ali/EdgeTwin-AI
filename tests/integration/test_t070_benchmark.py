"""tests/integration/test_t070_benchmark.py — Automated tests for T-070 Benchmark Harness.

Verifies:
1. SCN-01 Healthy scenario produces no false alert in steady-state.
2. SCN-02 Heat dissipation scenario produces expected alert behavior.
3. SCN-03 Overstrain scenario produces expected alert behavior.
4. SCN-04 Power failure scenario produces expected alert and trip behavior.
5. SCN-05 Tool wear scenario produces expected degradation and maintenance override.
6. SCN-06 Vibration spike scenario produces expected alert behavior.
7. SCN-07 Sensor dropout scenario produces expected data-quality behavior.
8. SCN-08 Machine offline scenario produces expected offline behavior.
9. Detection latency calculation logic.
10. Missing timestamp handling.
11. Duplicate event handling.
12. Benchmark result serialization and export.
13. Full harness execution across all 8 canonical scenarios.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.app.db.base import Base
from api.app.ingest.handler import handle_message
from api.app.models.machine import MachineRecord
from api.app.models.telemetry import TelemetryRecord
from scripts.benchmark_t070 import (
    BenchmarkSuiteSummary,
    LatencyStats,
    T070BenchmarkHarness,
)
from simulation.process_model import SimulatedMachine


@pytest.fixture
def isolated_db_factory():
    """Create isolated in-memory SQLite DB session factory with test machine."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine)

    with factory() as session:
        session.add(
            MachineRecord(
                machine_id="MOT-1001",
                machine_type="L",
                location="Test-Bay-1",
            )
        )
        session.commit()

    return factory


@pytest.fixture
def harness():
    """Return initialized T070BenchmarkHarness with seed=42."""
    return T070BenchmarkHarness(seed=42)


# ---------------------------------------------------------------------------
# Test 1: SCN-01 Healthy Nominal produces zero false alarms in steady-state
# ---------------------------------------------------------------------------


def test_benchmark_healthy_nominal_no_false_alarm(harness: T070BenchmarkHarness):
    """Test 1: SCN-01 maintains healthy state with zero failure alerts or critical alarms."""
    spec = next(s for s in harness.SCENARIO_SPECS if s["id"] == "SCN-01")
    result = harness.execute_scenario(spec)

    assert result.detected is True
    assert result.false_alarm is False
    assert result.final_health_state == "HEALTHY"
    assert result.final_risk_band == "LOW"
    assert result.final_failure_probability is not None
    assert result.final_failure_probability < 0.160
    assert result.final_health_score is not None
    assert result.final_health_score >= 80.0

    # Ensure no CRITICAL alerts raised
    crit_alerts = [a for a in result.actual_alerts if a["severity"] == "CRITICAL"]
    assert len(crit_alerts) == 0


# ---------------------------------------------------------------------------
# Test 2: SCN-02 Heat Dissipation Failure Detection
# ---------------------------------------------------------------------------


def test_benchmark_heat_dissipation_detection(harness: T070BenchmarkHarness):
    """Test 2: SCN-02 triggers thermal alert and transitions to CRITICAL state."""
    spec = next(s for s in harness.SCENARIO_SPECS if s["id"] == "SCN-02")
    result = harness.execute_scenario(spec)

    assert result.detected is True
    assert result.false_alarm is False
    assert result.activation_step == 30
    assert result.detection_step_lag > 0
    assert result.final_health_state == "CRITICAL"
    assert result.final_risk_band == "CRITICAL"
    assert result.final_failure_probability is not None
    assert result.final_failure_probability >= 0.160

    # Verify critical health alert was raised
    has_crit_alert = any(
        a["alert_type"] == "CRITICAL_MACHINE_HEALTH" and a["severity"] == "CRITICAL"
        for a in result.actual_alerts
    )
    assert has_crit_alert is True


# ---------------------------------------------------------------------------
# Test 3: SCN-03 Overstrain Failure Detection
# ---------------------------------------------------------------------------


def test_benchmark_overstrain_detection(harness: T070BenchmarkHarness):
    """Test 3: SCN-03 triggers mechanical overload alert and transitions to CRITICAL state."""
    spec = next(s for s in harness.SCENARIO_SPECS if s["id"] == "SCN-03")
    result = harness.execute_scenario(spec)

    assert result.detected is True
    assert result.false_alarm is False
    assert result.activation_step == 30
    assert result.detection_step_lag > 0
    assert result.final_health_state == "CRITICAL"
    assert result.final_risk_band == "CRITICAL"
    assert result.final_failure_probability is not None
    assert result.final_failure_probability >= 0.160

    has_overstrain_alert = any(
        a["alert_type"] == "CRITICAL_MACHINE_HEALTH" and a["severity"] == "CRITICAL"
        for a in result.actual_alerts
    )
    assert has_overstrain_alert is True


# ---------------------------------------------------------------------------
# Test 4: SCN-04 Power Failure and Safety Trip Detection
# ---------------------------------------------------------------------------


def test_benchmark_power_failure_detection_and_trip(harness: T070BenchmarkHarness):
    """Test 4: SCN-04 triggers power surge alert and hardware safety trip."""
    spec = next(s for s in harness.SCENARIO_SPECS if s["id"] == "SCN-04")
    result = harness.execute_scenario(spec)

    assert result.detected is True
    assert result.false_alarm is False
    assert result.activation_step == 30
    assert result.final_health_state == "CRITICAL"

    # Verify hardware trip alert
    has_trip_alert = any(
        a["alert_type"] == "HARDWARE_SAFETY_TRIP" and a["severity"] == "CRITICAL"
        for a in result.actual_alerts
    )
    assert has_trip_alert is True


# ---------------------------------------------------------------------------
# Test 5: SCN-05 Tool Wear Degradation & Operational Override
# ---------------------------------------------------------------------------


def test_benchmark_tool_wear_degradation_and_override(harness: T070BenchmarkHarness):
    """Test 5: SCN-05 triggers MAINTENANCE_REQUIRED override when tool wear exceeds 240 min."""
    spec = next(s for s in harness.SCENARIO_SPECS if s["id"] == "SCN-05")
    result = harness.execute_scenario(spec)

    assert result.detected is True
    assert result.false_alarm is False
    assert result.activation_step == 20
    assert result.final_health_state == "MAINTENANCE_REQUIRED"

    # Verify maintenance required alert
    has_maint_alert = any(
        a["alert_type"] == "MAINTENANCE_REQUIRED" and a["severity"] == "WARNING"
        for a in result.actual_alerts
    )
    assert has_maint_alert is True


# ---------------------------------------------------------------------------
# Test 6: SCN-06 Sudden High-Vibration Cluster Detection
# ---------------------------------------------------------------------------


def test_benchmark_vibration_spike_detection(harness: T070BenchmarkHarness):
    """Test 6: SCN-06 detects sudden vibration/pressure shock immediately."""
    spec = next(s for s in harness.SCENARIO_SPECS if s["id"] == "SCN-06")
    result = harness.execute_scenario(spec)

    assert result.detected is True
    assert result.false_alarm is False
    assert result.activation_step == 30
    assert result.detection_step_lag == 0  # Step fault detected at trigger step
    assert result.final_health_state == "CRITICAL"
    assert result.final_risk_band == "CRITICAL"


# ---------------------------------------------------------------------------
# Test 7: SCN-07 Sensor Dropout and Quality Marking
# ---------------------------------------------------------------------------


def test_benchmark_sensor_dropout_resilience_and_quality(harness: T070BenchmarkHarness):
    """Test 7: SCN-07 handles missing sensor channels without crash, applying quality penalties."""
    spec = next(s for s in harness.SCENARIO_SPECS if s["id"] == "SCN-07")
    result = harness.execute_scenario(spec)

    assert result.detected is True
    assert result.false_alarm is False
    assert result.activation_step == 20
    assert result.final_risk_band == "LOW"
    assert result.final_failure_probability is not None
    assert result.final_failure_probability < 0.160


# ---------------------------------------------------------------------------
# Test 8: SCN-08 Machine Offline and LWT Detection
# ---------------------------------------------------------------------------


def test_benchmark_machine_offline_lwt_detection(harness: T070BenchmarkHarness):
    """Test 8: SCN-08 transitions Digital Twin sync status to OFFLINE."""
    spec = next(s for s in harness.SCENARIO_SPECS if s["id"] == "SCN-08")
    result = harness.execute_scenario(spec)

    assert result.detected is True
    assert result.false_alarm is False
    assert result.activation_step == 10
    assert result.final_sync_status == "OFFLINE"
    assert result.final_health_state == "OFFLINE"


# ---------------------------------------------------------------------------
# Test 9: Detection Latency Calculation Math & Stats
# ---------------------------------------------------------------------------


def test_benchmark_detection_latency_calculation():
    """Test 9: LatencyStats correctly computes min, median, mean, max, and count."""
    samples = [10.0, 20.0, 30.0, 40.0, 50.0]
    stats = LatencyStats.from_samples(samples)

    assert stats.min_ms == 10.0
    assert stats.median_ms == 30.0
    assert stats.mean_ms == 30.0
    assert stats.max_ms == 50.0
    assert stats.sample_count == 5

    empty_stats = LatencyStats.from_samples([])
    assert empty_stats.sample_count == 0
    assert empty_stats.mean_ms == 0.0


# ---------------------------------------------------------------------------
# Test 10: Missing Timestamp Fallback Handling
# ---------------------------------------------------------------------------


def test_benchmark_missing_timestamp_handling(isolated_db_factory):
    """Test 10: Ingest handler safely processes payload with missing ts field."""
    sim = SimulatedMachine(machine_id="MOT-1001", seed=42)
    msg = sim.step()
    del msg["ts"]  # remove timestamp

    with isolated_db_factory() as session:
        res = handle_message(
            "edgetwin/v1/MOT-1001/telemetry", json.dumps(msg).encode("utf-8"), session
        )
        # Missing required field fails schema validation gracefully
        assert res["outcome"] in ("persisted", "rejected")


# ---------------------------------------------------------------------------
# Test 11: Duplicate Event Ingestion Handling
# ---------------------------------------------------------------------------


def test_benchmark_duplicate_event_handling(isolated_db_factory):
    """Test 11: Ingestion handler drops duplicate sequence numbers without corrupting DB."""
    sim = SimulatedMachine(machine_id="MOT-1001", seed=42)
    msg = sim.step()
    msg["seq"] = 555
    payload_bytes = json.dumps(msg).encode("utf-8")

    with isolated_db_factory() as session:
        # First attempt: persisted
        res1 = handle_message("edgetwin/v1/MOT-1001/telemetry", payload_bytes, session)
        assert res1["outcome"] == "persisted"

        # Duplicate attempt: dropped
        res2 = handle_message("edgetwin/v1/MOT-1001/telemetry", payload_bytes, session)
        assert res2["outcome"] == "duplicate"

        # Verify only 1 record in DB
        count = session.query(TelemetryRecord).filter_by(machine_id="MOT-1001", seq=555).count()
        assert count == 1


# ---------------------------------------------------------------------------
# Test 12: Benchmark Result Serialization & Export
# ---------------------------------------------------------------------------


def test_benchmark_result_serialization_and_export(tmp_path: Path, harness: T070BenchmarkHarness):
    """Test 12: BenchmarkSuiteSummary serializes to valid JSON matching schema."""
    spec = next(s for s in harness.SCENARIO_SPECS if s["id"] == "SCN-01")
    sc_res = harness.execute_scenario(spec)

    summary = BenchmarkSuiteSummary(
        total_scenarios=1,
        passed_scenarios=1,
        failed_scenarios=0,
        overall_detection_rate=1.0,
        overall_false_alarm_rate=0.0,
        scenarios=[sc_res],
    )

    out_file = tmp_path / "test_benchmark.json"
    exported_path = harness.export_results(summary, output_path=out_file)

    assert exported_path.exists()
    with open(exported_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)

    assert loaded["benchmark_name"] == summary.benchmark_name
    assert loaded["total_scenarios"] == 1
    assert loaded["passed_scenarios"] == 1
    assert len(loaded["scenarios"]) == 1
    assert loaded["scenarios"][0]["scenario_id"] == "SCN-01"


# ---------------------------------------------------------------------------
# Test 13: Full Harness Run All Verification
# ---------------------------------------------------------------------------


def test_benchmark_harness_full_run_all(harness: T070BenchmarkHarness):
    """Test 13: Execute full suite of 8 canonical scenarios and verify 100% pass rate."""
    summary = harness.run_all()

    assert summary.total_scenarios == 8
    assert summary.passed_scenarios == 8
    assert summary.failed_scenarios == 0
    assert summary.overall_detection_rate == 1.0
    assert summary.overall_false_alarm_rate == 0.0
    assert len(summary.scenarios) == 8
