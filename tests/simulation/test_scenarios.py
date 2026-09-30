"""
tests/simulation/test_scenarios.py - Tests for process model and scenario specifications.

Tasks: T-021 Scenario Specification & Process Model
Evaluates scenarios against models:/edgetwin-risk@champion, IsolationForest, and HealthEngine.
Reports actual measured probabilities honestly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import mlflow
import numpy as np
import pytest

from ml.data.engineering import apply_feature_set
from ml.models.explain import EdgeTwinExplainer
from ml.models.health import compute_health_score, determine_health_state
from mlops.register import EdgeTwinRiskModel
from simulation.contract import TelemetryValidator, telemetry_to_feature_df
from simulation.process_model import MachineOperatingState, SimulatedMachine

SCENARIOS_DIR = Path(__file__).resolve().parent.parent.parent / "simulation" / "scenarios"


@pytest.fixture(scope="module")
def champion_model() -> Any:
    """Load the registered champion model (with local artifact fallback)."""
    project_db = Path(__file__).resolve().parents[2] / "mlflow.db"
    if project_db.exists():
        try:
            mlflow.set_tracking_uri(f"sqlite:///{project_db.as_posix()}")
            return mlflow.pyfunc.load_model("models:/edgetwin-risk@champion")
        except Exception:  # noqa: BLE001, S110
            pass

    artifacts_dir = Path(__file__).resolve().parents[2] / "artifacts"
    calibrated = joblib.load(artifacts_dir / "calibrated_classifier_sigmoid.joblib")
    with open(artifacts_dir / "champion_features.json", "r", encoding="utf-8") as f:
        features = json.load(f)
    return EdgeTwinRiskModel(
        calibrated_model=calibrated,
        feature_cols=features,
        operational_threshold=0.160,
    )


@pytest.fixture(scope="module")
def validator() -> TelemetryValidator:
    """Return initialized TelemetryValidator."""
    return TelemetryValidator()


# ---------------------------------------------------------------------------
# Test 1 & 2: Determinism and Fixed Replay Timestamps
# ---------------------------------------------------------------------------


def test_scenario_seed_determinism() -> None:
    """Test 1: Identical seeds produce byte-identical telemetry streams."""
    sim1 = SimulatedMachine.from_scenario_file(SCENARIOS_DIR / "healthy_nominal.yaml", seed=42)
    sim2 = SimulatedMachine.from_scenario_file(SCENARIOS_DIR / "healthy_nominal.yaml", seed=42)

    msgs1 = sim1.run_scenario(steps=50)
    msgs2 = sim2.run_scenario(steps=50)

    assert len(msgs1) == 50
    assert len(msgs2) == 50
    assert msgs1 == msgs2, "Telemetry streams diverged with identical seed=42"


def test_scenario_timestamps_advance_deterministically() -> None:
    """Test 2: Replay timestamps start at fixed epoch and increment strictly by tick_interval."""
    sim = SimulatedMachine.from_scenario_file(
        SCENARIOS_DIR / "healthy_nominal.yaml",
        seed=42,
    )
    msgs = sim.run_scenario(steps=10)

    assert msgs[0]["ts"] == "2026-01-01T00:00:00Z"
    assert msgs[1]["ts"] == "2026-01-01T00:00:01Z"
    assert msgs[9]["ts"] == "2026-01-01T00:00:09Z"


# ---------------------------------------------------------------------------
# Test 3 & 4: Healthy Baseline Distribution & Model Response
# ---------------------------------------------------------------------------


def test_healthy_nominal_distribution_matches_empirical_means() -> None:
    """Test 3: SCN-01 sensor distribution matches empirical non-failure training means."""
    sim = SimulatedMachine.from_scenario_file(SCENARIOS_DIR / "healthy_nominal.yaml", seed=42)
    msgs = sim.run_scenario(steps=100)

    # Compute means of generated telemetry
    air_temps = [m["signals"]["air_temp_c"] for m in msgs]
    proc_temps = [m["signals"]["process_temp_c"] for m in msgs]
    rpms = [m["signals"]["rotational_speed_rpm"] for m in msgs]
    torques = [m["signals"]["torque_nm"] for m in msgs]
    currents = [m["signals"]["current_a"] for m in msgs]

    # Verify within engineering tolerance of empirical means
    assert abs(np.mean(air_temps) - 25.4) < 1.0, f"Air temp mean {np.mean(air_temps)} deviated"
    assert abs(np.mean(proc_temps) - 35.3) < 1.5, f"Proc temp mean {np.mean(proc_temps)} deviated"
    assert abs(np.mean(rpms) - 1548.0) < 50.0, f"RPM mean {np.mean(rpms)} deviated"
    assert abs(np.mean(torques) - 40.1) < 3.0, f"Torque mean {np.mean(torques)} deviated"
    assert abs(np.mean(currents) - 12.0) < 1.0, f"Current mean {np.mean(currents)} deviated"


def test_healthy_nominal_model_behavior(
    champion_model: Any,
    validator: TelemetryValidator,
) -> None:
    """Test 4: SCN-01 healthy nominal produces low risk and zero failure classifications."""
    sim = SimulatedMachine.from_scenario_file(SCENARIOS_DIR / "healthy_nominal.yaml", seed=42)
    msgs = sim.run_scenario(steps=60)

    # Validate all messages against Telemetry Contract v1
    for m in msgs:
        val_res = validator.validate(m)
        assert (
            val_res.valid is True
        ), f"Contract validation failed on healthy message: {val_res.errors}"

    # Convert to ML feature DataFrame and score with champion model
    df = telemetry_to_feature_df(msgs)
    pred_df = champion_model.predict(df)

    mean_prob = float(pred_df["calibrated_probability"].mean())
    max_prob = float(pred_df["calibrated_probability"].max())
    failure_preds = int(pred_df["failure_prediction"].sum())

    print(
        f"\n[SCN-01 Measured] mean_p={mean_prob:.4f}, max_p={max_prob:.4f}, failure_preds={failure_preds}/60"
    )

    # Acceptance criterion: mean p < 0.15 (LOW risk band) and zero failure predictions (p >= 0.16)
    assert mean_prob < 0.15, f"Healthy mean probability {mean_prob:.4f} >= 0.15"
    assert (
        failure_preds == 0
    ), f"Healthy baseline triggered {failure_preds} false positive failure alerts"


# ---------------------------------------------------------------------------
# Test 5 & 6: Fault Scenarios Measured Model Results
# ---------------------------------------------------------------------------


def test_heat_dissipation_scenario(
    champion_model: Any,
    validator: TelemetryValidator,
) -> None:
    """Test SCN-02: Heat Dissipation Failure measured model results."""
    sim = SimulatedMachine.from_scenario_file(SCENARIOS_DIR / "heat_dissipation.yaml", seed=42)
    msgs = sim.run_scenario(steps=120)

    for m in msgs:
        assert validator.validate(m).valid is True

    df = telemetry_to_feature_df(msgs)
    pred_df = champion_model.predict(df)

    # Steps 0-30: baseline healthy
    baseline_p = float(pred_df["calibrated_probability"].iloc[10:30].mean())
    # Steps 80-120: fully degraded
    degraded_p = float(pred_df["calibrated_probability"].iloc[80:120].mean())
    max_p = float(pred_df["calibrated_probability"].max())

    print(
        f"\n[SCN-02 Measured] baseline_p={baseline_p:.4f}, degraded_p={degraded_p:.4f}, max_p={max_p:.4f}"
    )

    # Honest acceptance target check: degraded risk must cross operational threshold 0.16
    assert baseline_p < 0.15, f"SCN-02 baseline was not healthy: {baseline_p:.4f}"
    assert (
        degraded_p >= 0.16
    ), f"SCN-02 degraded risk {degraded_p:.4f} failed to reach threshold 0.16"


def test_overstrain_scenario(
    champion_model: Any,
    validator: TelemetryValidator,
) -> None:
    """Test SCN-03: Overstrain Failure measured model results."""
    sim = SimulatedMachine.from_scenario_file(SCENARIOS_DIR / "overstrain.yaml", seed=42)
    msgs = sim.run_scenario(steps=100)

    for m in msgs:
        assert validator.validate(m).valid is True

    df = telemetry_to_feature_df(msgs)
    pred_df = champion_model.predict(df)

    baseline_p = float(pred_df["calibrated_probability"].iloc[10:30].mean())
    degraded_p = float(pred_df["calibrated_probability"].iloc[70:100].mean())
    max_p = float(pred_df["calibrated_probability"].max())

    print(
        f"\n[SCN-03 Measured] baseline_p={baseline_p:.4f}, degraded_p={degraded_p:.4f}, max_p={max_p:.4f}"
    )

    assert (
        degraded_p >= 0.16
    ), f"SCN-03 degraded risk {degraded_p:.4f} failed to cross threshold 0.16"


def test_power_failure_scenario(
    champion_model: Any,
    validator: TelemetryValidator,
) -> None:
    """Test SCN-04: Power Failure measured model results and edge safety trip."""
    sim = SimulatedMachine.from_scenario_file(SCENARIOS_DIR / "power_failure.yaml", seed=42)
    msgs = sim.run_scenario(steps=90)

    for m in msgs:
        assert validator.validate(m).valid is True

    df = telemetry_to_feature_df(msgs)
    pred_df = champion_model.predict(df)

    # During fault injection (steps 31..39 before edge trip at step 40)
    active_fault_p = float(pred_df["calibrated_probability"].iloc[31:39].mean())
    max_p = float(pred_df["calibrated_probability"].max())

    # Check edge trip flag in post-trip telemetry (step 45+)
    post_trip_msgs = msgs[45:70]
    trip_codes = [m["edge"]["trip"] for m in post_trip_msgs]

    print(
        f"\n[SCN-04 Measured] active_fault_p={active_fault_p:.4f}, max_p={max_p:.4f}, post_trip={trip_codes[0]}"
    )

    assert (
        active_fault_p >= 0.16
    ), f"SCN-04 active fault risk {active_fault_p:.4f} failed to cross threshold 0.16"
    assert "TRIP_OVERLOAD" in trip_codes


def test_tool_wear_scenario_and_operational_override(
    champion_model: Any,
    validator: TelemetryValidator,
) -> None:
    """Test SCN-05: Tool Wear Failure & T-014 operational override to MAINTENANCE_REQUIRED."""
    sim = SimulatedMachine.from_scenario_file(SCENARIOS_DIR / "tool_wear.yaml", seed=42)
    msgs = sim.run_scenario(steps=120)

    for m in msgs:
        assert validator.validate(m).valid is True

    df = telemetry_to_feature_df(msgs)
    pred_df = champion_model.predict(df)

    # Check tool wear accumulation
    wear_values = [m["signals"]["tool_wear_min"] for m in msgs]
    initial_wear = wear_values[0]
    final_wear = wear_values[-1]

    # Verify wear crosses 240 min
    assert initial_wear == 225.0
    assert final_wear > 240.0

    # Evaluate health state with health model precedence
    # Tool_Wear_Min >= 240 must yield MAINTENANCE_REQUIRED
    late_msg = msgs[-1]
    late_prob = float(pred_df["calibrated_probability"].iloc[-1])
    score = compute_health_score(late_prob)
    health_state = determine_health_state(
        health_score=score,
        calibrated_p_fail=late_prob,
        tool_wear_min=late_msg["signals"]["tool_wear_min"],
    )

    print(
        f"\n[SCN-05 Measured] final_wear={final_wear:.1f} min, late_p={late_prob:.4f}, health_state={health_state}"
    )
    assert (
        health_state == "MAINTENANCE_REQUIRED"
    ), f"Expected MAINTENANCE_REQUIRED, got {health_state}"


def test_random_vibration_scenario(
    champion_model: Any,
    validator: TelemetryValidator,
) -> None:
    """Test SCN-06: Sudden High-Vibration empirical cluster failure."""
    sim = SimulatedMachine.from_scenario_file(SCENARIOS_DIR / "random_vibration.yaml", seed=42)
    msgs = sim.run_scenario(steps=80)

    for m in msgs:
        assert validator.validate(m).valid is True

    df = telemetry_to_feature_df(msgs)
    pred_df = champion_model.predict(df)

    fault_p = float(pred_df["calibrated_probability"].iloc[35:80].mean())
    max_p = float(pred_df["calibrated_probability"].max())
    bands = list(pred_df["risk_band"].iloc[35:80].unique())

    print(f"\n[SCN-06 Measured] fault_p={fault_p:.4f}, max_p={max_p:.4f}, bands={bands}")

    # Empirical signature in dataset has 100% recall and extreme risk
    assert fault_p >= 0.80, f"SCN-06 probability {fault_p:.4f} < 0.80"
    assert "CRITICAL" in bands


def test_sensor_dropout_scenario(
    champion_model: Any,
    validator: TelemetryValidator,
) -> None:
    """Test SCN-07: Sensor dropout handling and MISSING quality assignment."""
    sim = SimulatedMachine.from_scenario_file(SCENARIOS_DIR / "sensor_dropout.yaml", seed=42)
    msgs = sim.run_scenario(steps=90)

    # Check validator flags
    step25 = msgs[25]
    step50 = msgs[50]
    step80 = msgs[80]

    val25 = validator.validate(step25)
    assert val25.valid is True
    assert val25.quality_flags["vibration_mm_s"] == "MISSING"

    val50 = validator.validate(step50)
    assert val50.valid is True
    assert val50.quality_flags["pressure_bar"] == "MISSING"

    val80 = validator.validate(step80)
    assert val80.valid is True
    assert val80.quality_flags["vibration_mm_s"] == "OK"
    assert val80.quality_flags["pressure_bar"] == "OK"

    # Model scores all rows without exception via median imputer
    df = telemetry_to_feature_df(msgs)
    pred_df = champion_model.predict(df)
    assert len(pred_df) == 90
    assert pred_df["calibrated_probability"].isna().sum() == 0


def test_machine_offline_scenario() -> None:
    """Test SCN-08: Communication disconnect halts telemetry emission."""
    sim = SimulatedMachine.from_scenario_file(SCENARIOS_DIR / "machine_offline.yaml", seed=42)
    msgs = sim.run_scenario(steps=40)

    # Disconnect at step 10 -> only 10 messages should be emitted
    assert len(msgs) == 10
    assert msgs[-1]["seq"] == 9


# ---------------------------------------------------------------------------
# Test 7: Top SHAP Factors for Fault Scenarios
# ---------------------------------------------------------------------------


def test_fault_scenarios_top_shap_factors(champion_model: Any) -> None:
    """Test 7: Top SHAP feature attributions correspond to physical scenario drivers."""
    python_model = getattr(champion_model._model_impl, "python_model", champion_model._model_impl)
    explainer = EdgeTwinExplainer(
        model=python_model.calibrated_model,
        feature_cols=python_model.feature_cols,
    )

    # 1. Evaluate SCN-02 (HDF) top SHAP factor
    sim_hdf = SimulatedMachine.from_scenario_file(SCENARIOS_DIR / "heat_dissipation.yaml", seed=42)
    msgs_hdf = sim_hdf.run_scenario(steps=100)
    df_hdf = apply_feature_set(telemetry_to_feature_df(msgs_hdf[-1]), "+physics")

    expl_hdf = explainer.explain_instance(df_hdf, top_k=3)
    top_factors_hdf = [f["feature_name"] for f in expl_hdf["top_factors"]]
    print(f"\n[SCN-02 SHAP] top factors: {top_factors_hdf}")
    assert any(feat in top_factors_hdf for feat in ("Process_Temperature_C", "Delta_T_C"))

    # 2. Evaluate SCN-06 (RNF) top SHAP factor
    sim_rnf = SimulatedMachine.from_scenario_file(SCENARIOS_DIR / "random_vibration.yaml", seed=42)
    msgs_rnf = sim_rnf.run_scenario(steps=60)
    df_rnf = apply_feature_set(telemetry_to_feature_df(msgs_rnf[-1]), "+physics")

    expl_rnf = explainer.explain_instance(df_rnf, top_k=3)
    top_factors_rnf = [f["feature_name"] for f in expl_rnf["top_factors"]]
    print(f"[SCN-06 SHAP] top factors: {top_factors_rnf}")
    assert "Vibration_mm_s" in top_factors_rnf


# ---------------------------------------------------------------------------
# Test 8: FSM State Transitions
# ---------------------------------------------------------------------------


def test_fsm_state_transitions() -> None:
    """Test 8: Full FSM lifecycle across STOPPED -> STARTING -> RUNNING -> DEGRADING -> TRIPPED -> STOPPED."""
    sim = SimulatedMachine(machine_id="MOT-1001", seed=42, auto_start=False)
    assert sim.state == MachineOperatingState.STOPPED

    sim.start()
    assert sim.state == MachineOperatingState.STARTING

    # Step until speed reaches running threshold
    for _ in range(10):
        sim.step()
        if sim.state == MachineOperatingState.RUNNING:
            break
    assert sim.state == MachineOperatingState.RUNNING

    # Trip the machine
    sim.trigger_trip("TRIP_OVERLOAD")
    assert sim.state == MachineOperatingState.TRIPPED
    assert sim.active_trip == "TRIP_OVERLOAD"
    assert sim.rpm == 0.0

    # Reset
    sim.reset()
    assert sim.state == MachineOperatingState.STOPPED
    assert sim.active_trip is None
