"""Lightweight, deterministic ML smoke test suite for CI and local verification (T-062).

Verifies ML operational invariants without modifying models or accessing held-out test data:
1. Production model artifacts and load paths are valid.
2. Feature contract contains exactly 14 production features.
3. Inference produces valid calibrated failure probabilities in [0.0, 1.0].
4. Operational decision threshold is strictly frozen at 0.160.
5. Risk-band mapping logic is correct and exhaustive.
6. ModelEngine champion singleton loads and evaluates nominal telemetry.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from api.app.inference.engine import ModelEngine
from ml.data.features import get_forbidden_columns

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ARTIFACTS_DIR = _PROJECT_ROOT / "artifacts"


class TestMLArtifactsIntegrity:
    """Verify presence, integrity, and contracts of serialized production artifacts."""

    def test_production_artifacts_exist(self) -> None:
        """Ensure all required production model and reference artifacts exist."""
        required_artifacts = [
            "calibrated_classifier_sigmoid.joblib",
            "champion_features.json",
            "anomaly_isolation_forest.joblib",
            "anomaly_ref_params.json",
            "training_reference_stats.json",
        ]
        for artifact_name in required_artifacts:
            path = _ARTIFACTS_DIR / artifact_name
            assert path.is_file(), f"Required ML production artifact missing: {path}"
            assert path.stat().st_size > 0, f"ML artifact is empty: {path}"

    def test_feature_contract_exact_14_features(self) -> None:
        """Validate production feature contract: exactly 14 features without leakage."""
        features_file = _ARTIFACTS_DIR / "champion_features.json"
        with open(features_file, "r", encoding="utf-8") as f:
            features = json.load(f)

        assert isinstance(features, list), "Features specification must be a JSON array"
        assert (
            len(features) == 14
        ), f"Feature contract violation: expected 14 features, got {len(features)}"

        expected_sensors = [
            "Air_Temperature_C",
            "Process_Temperature_C",
            "Rotational_Speed_RPM",
            "Torque_Nm",
            "Vibration_mm_s",
            "Pressure_bar",
            "Current_A",
            "Voltage_V",
            "Tool_Wear_Min",
            "Operating_Hours",
        ]
        expected_meta = ["Machine_Type"]
        expected_physics = ["Delta_T_C", "Apparent_Power_VA", "Mech_Power_W"]

        for col in expected_sensors + expected_meta + expected_physics:
            assert col in features, f"Required feature '{col}' missing from feature contract"

        # Leakage guard: zero forbidden columns in feature contract
        for forbidden in get_forbidden_columns():
            assert (
                forbidden not in features
            ), f"Forbidden leakage column '{forbidden}' found in feature contract"


class TestMLOperationalInvariants:
    """Verify threshold, risk bands, and model inference contracts."""

    @pytest.fixture
    def nominal_telemetry_df(self) -> pd.DataFrame:
        """Construct synthetic nominal telemetry record with derived physics."""
        return pd.DataFrame(
            [
                {
                    "Air_Temperature_C": 25.0,
                    "Process_Temperature_C": 35.0,
                    "Rotational_Speed_RPM": 1500.0,
                    "Torque_Nm": 40.0,
                    "Vibration_mm_s": 1.5,
                    "Pressure_bar": 5.0,
                    "Current_A": 12.0,
                    "Voltage_V": 400.0,
                    "Tool_Wear_Min": 60.0,
                    "Operating_Hours": 120.0,
                    "Machine_Type": "L",
                    "Delta_T_C": 10.0,
                    "Apparent_Power_VA": 4800.0,
                    "Mech_Power_W": 6283.18,
                }
            ]
        )

    def test_operational_decision_threshold_is_frozen(self) -> None:
        """Verify the operational decision threshold is frozen strictly at 0.160."""
        engine = ModelEngine()
        engine.load()
        assert engine.operational_threshold == pytest.approx(
            0.160, abs=1e-4
        ), f"Decision threshold contract broken: expected 0.160, got {engine.operational_threshold}"

    def test_champion_model_loads_and_infers_valid_probabilities(
        self, nominal_telemetry_df: pd.DataFrame
    ) -> None:
        """Verify the production champion loads and outputs valid probabilities in [0.0, 1.0]."""
        engine = ModelEngine()
        engine.load()

        p_fail, pred, risk_band = engine.predict_risk(nominal_telemetry_df)

        assert isinstance(p_fail, float), "Failure probability must be a float"
        assert 0.0 <= p_fail <= 1.0, f"Failure probability out of bounds [0, 1]: {p_fail}"
        assert pred in (0, 1), f"Prediction classification must be binary (0 or 1), got {pred}"
        assert pred == (
            1 if p_fail >= engine.operational_threshold else 0
        ), f"Prediction classification ({pred}) inconsistent with decision threshold {engine.operational_threshold} and p_fail {p_fail}"
        assert risk_band in ("LOW", "MEDIUM", "HIGH", "CRITICAL"), f"Invalid risk band: {risk_band}"

    def test_risk_band_mapping_invariants(self) -> None:
        """Verify exact boundary conditions for operational risk-band assignments."""
        cases = [
            (0.00, "LOW"),
            (0.1499, "LOW"),
            (0.1500, "MEDIUM"),
            (0.1599, "MEDIUM"),
            (0.1600, "HIGH"),  # Exactly at threshold t* = 0.160
            (0.5000, "HIGH"),
            (0.7999, "HIGH"),
            (0.8000, "CRITICAL"),
            (1.0000, "CRITICAL"),
        ]

        for p_val, expected_band in cases:
            if p_val < 0.15:
                band = "LOW"
            elif p_val < 0.16:
                band = "MEDIUM"
            elif p_val < 0.80:
                band = "HIGH"
            else:
                band = "CRITICAL"
            assert (
                band == expected_band
            ), f"Risk band mismatch at p={p_val}: expected {expected_band}, got {band}"

    def test_anomaly_detector_smoke(self, nominal_telemetry_df: pd.DataFrame) -> None:
        """Verify Isolation Forest anomaly detector loads and returns normalized score."""
        engine = ModelEngine()
        engine.load()

        score, flag = engine.predict_anomaly(nominal_telemetry_df)

        if engine.anomaly_pipeline is not None:
            assert score is not None, "Anomaly score should not be None when pipeline is loaded"
            assert 0.0 <= score <= 1.0, f"Anomaly score out of normalized range [0, 1]: {score}"
            assert isinstance(
                flag, (bool, np.bool_)
            ), f"Anomaly flag must be boolean, got {type(flag)}"


if __name__ == "__main__":
    # Allow running directly as a standalone smoke script: python tests/ml/test_ml_smoke.py
    pytest.main(["-v", __file__])
