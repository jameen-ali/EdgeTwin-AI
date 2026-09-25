"""
tests/contract/test_telemetry_ml_compat.py - Telemetry to ML compatibility tests.

Tasks: T-020 Telemetry Contract v1 & S06 Champion Compatibility
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import mlflow
import numpy as np
import pandas as pd
import pytest

from ml.data.features import validate_no_leakage
from ml.data.schema import FEATURE_COLUMNS, MACHINE_ID_PREFIX_MAP
from simulation.contract import (
    telemetry_to_feature_df,
)


@pytest.fixture
def valid_telemetry_payload() -> dict[str, Any]:
    """Return a canonical valid Telemetry v1 payload."""
    return {
        "schema": "edgetwin.telemetry.v1",
        "machine_id": "MOT-1001",
        "seq": 1842,
        "ts": "2026-09-24T10:15:03Z",
        "provenance": "SIMULATED",
        "fw": "0.2.0",
        "signals": {
            "air_temp_c": 25.4,
            "process_temp_c": 35.6,
            "rotational_speed_rpm": 1540.0,
            "torque_nm": 41.2,
            "vibration_mm_s": 2.6,
            "pressure_bar": 5.5,
            "current_a": 12.1,
            "voltage_v": 415.2,
            "tool_wear_min": 131.0,
            "operating_hours": 10021.5,
        },
        "quality": {
            "vibration_mm_s": "OK",
            "pressure_bar": "OK",
        },
        "edge": {
            "delta_t_c": 10.2,
            "power_va": 5023.92,
            "trip": None,
            "buffered": 0,
        },
    }


@pytest.fixture(scope="module")
def champion_model() -> Any:
    """Load the registered champion model."""
    project_db = Path(__file__).resolve().parents[2] / "mlflow.db"
    mlflow.set_tracking_uri(f"sqlite:///{project_db.as_posix()}")
    return mlflow.pyfunc.load_model("models:/edgetwin-risk@champion")


@pytest.mark.parametrize(
    ("prefix", "expected_type"),
    list(MACHINE_ID_PREFIX_MAP.items()),
)
def test_all_five_known_machine_prefixes(
    valid_telemetry_payload: dict[str, Any],
    prefix: str,
    expected_type: str,
) -> None:
    """Test 16: All five known prefixes map to the expected Machine_Type."""
    payload = copy.deepcopy(valid_telemetry_payload)
    payload["machine_id"] = f"{prefix}-9999"

    df = telemetry_to_feature_df(payload)
    assert len(df) == 1
    assert df["Machine_Type"].iloc[0] == expected_type


def test_unknown_machine_prefix(
    valid_telemetry_payload: dict[str, Any],
    champion_model: Any,
) -> None:
    """Test 17: Unknown machine prefix maps to 'Unknown' and is scored without error."""
    payload = copy.deepcopy(valid_telemetry_payload)
    payload["machine_id"] = "XYZ-9999"

    df = telemetry_to_feature_df(payload)
    assert df["Machine_Type"].iloc[0] == "Unknown"

    # Score with champion model
    pred_df = champion_model.predict(df)
    assert len(pred_df) == 1
    assert "calibrated_probability" in pred_df.columns


def test_adapter_output_columns_and_names(
    valid_telemetry_payload: dict[str, Any],
) -> None:
    """Test 18 & 19: Adapter output has exactly 11 columns matching FEATURE_COLUMNS."""
    df = telemetry_to_feature_df(valid_telemetry_payload)
    assert list(df.columns) == FEATURE_COLUMNS
    assert len(df.columns) == 11
    # Verify PascalCase and underscores
    assert "Air_Temperature_C" in df.columns
    assert "Rotational_Speed_RPM" in df.columns
    assert "Machine_Type" in df.columns


def test_adapter_output_passes_leakage_guard(
    valid_telemetry_payload: dict[str, Any],
) -> None:
    """Test 20: validate_no_leakage passes on adapter output."""
    df = telemetry_to_feature_df(valid_telemetry_payload)
    # Must not raise ValueError
    validate_no_leakage(df, context="test")


def test_champion_model_accepts_adapter_output(
    valid_telemetry_payload: dict[str, Any],
    champion_model: Any,
) -> None:
    """Test 21 & 25: Champion model accepts adapter output and produces expected schema."""
    df = telemetry_to_feature_df(valid_telemetry_payload)
    pred_df = champion_model.predict(df)

    assert isinstance(pred_df, pd.DataFrame)
    expected_cols = ["calibrated_probability", "failure_prediction", "risk_band"]
    assert list(pred_df.columns) == expected_cols

    prob = float(pred_df["calibrated_probability"].iloc[0])
    pred = int(pred_df["failure_prediction"].iloc[0])
    band = str(pred_df["risk_band"].iloc[0])

    assert 0.0 <= prob <= 1.0
    assert pred in {0, 1}
    assert band in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def test_champion_model_derives_physics_features(
    valid_telemetry_payload: dict[str, Any],
    champion_model: Any,
) -> None:
    """Test 22: Champion model independently derives physics features without caller needing to."""
    df = telemetry_to_feature_df(valid_telemetry_payload)
    # Assert physics columns are not in raw adapter output
    assert "Delta_T_C" not in df.columns
    assert "Apparent_Power_VA" not in df.columns
    assert "Mech_Power_W" not in df.columns

    # Champion model runs and auto-derives them internally
    pred_df = champion_model.predict(df)
    assert len(pred_df) == 1


def test_modifying_edge_diagnostics_does_not_change_ml_prediction(
    valid_telemetry_payload: dict[str, Any],
    champion_model: Any,
) -> None:
    """Test 23: Changing edge diagnostics has ZERO effect on ML predictions."""
    payload1 = copy.deepcopy(valid_telemetry_payload)
    payload1["edge"]["delta_t_c"] = 10.2
    payload1["edge"]["power_va"] = 5000.0

    payload2 = copy.deepcopy(valid_telemetry_payload)
    payload2["edge"]["delta_t_c"] = 999.0  # Bogus edge diagnostic
    payload2["edge"]["power_va"] = 99999.0  # Bogus edge diagnostic

    df1 = telemetry_to_feature_df(payload1)
    df2 = telemetry_to_feature_df(payload2)

    pred1 = champion_model.predict(df1)
    pred2 = champion_model.predict(df2)

    assert float(pred1["calibrated_probability"].iloc[0]) == float(
        pred2["calibrated_probability"].iloc[0]
    )
    assert str(pred1["risk_band"].iloc[0]) == str(pred2["risk_band"].iloc[0])


def test_null_sensor_values_handled_by_model(
    valid_telemetry_payload: dict[str, Any],
    champion_model: Any,
) -> None:
    """Test 24: Null sensor values pass through to model imputation without failing."""
    payload = copy.deepcopy(valid_telemetry_payload)
    payload["signals"]["vibration_mm_s"] = None
    payload["signals"]["pressure_bar"] = None

    df = telemetry_to_feature_df(payload)
    assert np.isnan(df["Vibration_mm_s"].iloc[0])
    assert np.isnan(df["Pressure_bar"].iloc[0])

    pred_df = champion_model.predict(df)
    assert len(pred_df) == 1
    assert 0.0 <= float(pred_df["calibrated_probability"].iloc[0]) <= 1.0
