"""
tests/mlops/test_register.py - Unit tests for model packaging, promotion gate, and registry (T-016).

Test Groups:
- R1: EdgeTwinRiskModel raw telemetry inference & physics feature auto-generation
- R2: Imputation & encoding resilience (NaNs and unseen Machine_Type values)
- R3: Leakage guard enforcement (rejection of all 6 forbidden columns)
- R4: Output contract conformance (schema, bounds, threshold 0.16 consistency, risk bands)
- R5: Technical promotion gate validation & rejection triggers
- R6: End-to-end MLflow registration, alias assignment ('challenger' -> 'champion'),
      and URI resolution ('models:/edgetwin-risk@champion') in isolated test store.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import mlflow
import numpy as np
import pandas as pd
import pytest
from mlflow.tracking import MlflowClient

from ml.data.engineering import get_feature_cols_for_set
from ml.data.schema import FORBIDDEN_FEATURE_COLUMNS
from ml.models.calibrate import fit_calibrator
from ml.models.train import BASE_FEATURE_COLS, build_pipeline, train_model
from mlops.register import (
    MODEL_NAME,
    OPERATIONAL_THRESHOLD,
    EdgeTwinRiskModel,
    verify_promotion_gate,
)


@pytest.fixture
def feature_cols_14() -> list[str]:
    """14 features for the +physics model."""
    return get_feature_cols_for_set(BASE_FEATURE_COLS, "+physics")


@pytest.fixture
def raw_telemetry_cols() -> list[str]:
    """Raw telemetry columns: 10 sensors + Machine_Type."""
    return [
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
        "Machine_Type",
    ]


@pytest.fixture
def synthetic_training_data(feature_cols_14: list[str]) -> tuple[pd.DataFrame, pd.Series]:
    """Synthetic dataset with 14 features for fast model fitting."""
    np.random.seed(42)
    n = 100
    data: dict[str, Any] = {
        "Air_Temperature_C": np.random.uniform(20, 30, n),
        "Process_Temperature_C": np.random.uniform(30, 45, n),
        "Rotational_Speed_RPM": np.random.uniform(1200, 2000, n),
        "Torque_Nm": np.random.uniform(20, 80, n),
        "Vibration_mm_s": np.random.uniform(0.5, 3.5, n),
        "Pressure_bar": np.random.uniform(1, 10, n),
        "Current_A": np.random.uniform(5, 25, n),
        "Voltage_V": np.random.uniform(200, 240, n),
        "Tool_Wear_Min": np.random.uniform(0, 250, n),
        "Operating_Hours": np.random.uniform(10, 500, n),
        "Machine_Type": np.random.choice(["L", "M", "H"], n),
        "Delta_T_C": np.random.uniform(8, 15, n),
        "Apparent_Power_VA": np.random.uniform(2000, 5000, n),
        "Mech_Power_W": np.random.uniform(3000, 8000, n),
    }
    df = pd.DataFrame(data)[feature_cols_14]
    y_raw = (df["Tool_Wear_Min"] > 180) | (df["Vibration_mm_s"] > 2.8)
    y = pd.Series(y_raw.astype(int), name="Machine_Failure")
    return df, y


@pytest.fixture
def calibrated_risk_model(
    synthetic_training_data: tuple[pd.DataFrame, pd.Series],
    feature_cols_14: list[str],
) -> EdgeTwinRiskModel:
    """Instantiated EdgeTwinRiskModel wrapping calibrated pipeline."""
    X, y = synthetic_training_data
    pipe = build_pipeline("xgboost", feature_cols_14, seed=42)
    fitted_pipe = train_model(pipe, X, y)
    cal_model = fit_calibrator(fitted_pipe, X, y, method="sigmoid")

    metadata = {
        "model_family": "xgboost",
        "feature_set": "+physics",
        "calibration_method": "sigmoid",
        "operational_threshold": OPERATIONAL_THRESHOLD,
        "n_features": 14,
        "git_commit": "testcommit",
    }
    return EdgeTwinRiskModel(
        calibrated_model=cal_model,
        feature_cols=feature_cols_14,
        operational_threshold=OPERATIONAL_THRESHOLD,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# R1 & R2: Raw Telemetry, Missing Values & Unseen Machine Types
# ---------------------------------------------------------------------------


class TestInferenceContracts:
    def test_predict_raw_telemetry_auto_generates_physics(
        self,
        calibrated_risk_model: EdgeTwinRiskModel,
        raw_telemetry_cols: list[str],
    ) -> None:
        raw_df = pd.DataFrame(
            {
                "Air_Temperature_C": [25.0, 26.0],
                "Process_Temperature_C": [35.0, 38.0],
                "Rotational_Speed_RPM": [1500.0, 1600.0],
                "Torque_Nm": [40.0, 50.0],
                "Vibration_mm_s": [1.2, 2.5],
                "Pressure_bar": [4.0, 5.0],
                "Current_A": [12.0, 15.0],
                "Voltage_V": [220.0, 230.0],
                "Tool_Wear_Min": [50.0, 210.0],
                "Operating_Hours": [100.0, 400.0],
                "Machine_Type": ["L", "M"],
            }
        )[raw_telemetry_cols]

        pred = calibrated_risk_model.predict(raw_df)
        assert isinstance(pred, pd.DataFrame)
        assert len(pred) == 2
        assert list(pred.columns) == ["calibrated_probability", "failure_prediction", "risk_band"]

    def test_predict_handles_nan_sensor_values(
        self,
        calibrated_risk_model: EdgeTwinRiskModel,
        raw_telemetry_cols: list[str],
    ) -> None:
        raw_df = pd.DataFrame(
            {
                "Air_Temperature_C": [np.nan, 25.0],
                "Process_Temperature_C": [35.0, np.nan],
                "Rotational_Speed_RPM": [1500.0, 1500.0],
                "Torque_Nm": [np.nan, 45.0],
                "Vibration_mm_s": [1.5, np.nan],
                "Pressure_bar": [4.0, 4.0],
                "Current_A": [12.0, 12.0],
                "Voltage_V": [220.0, 220.0],
                "Tool_Wear_Min": [100.0, 100.0],
                "Operating_Hours": [200.0, 200.0],
                "Machine_Type": ["L", "H"],
            }
        )[raw_telemetry_cols]

        pred = calibrated_risk_model.predict(raw_df)
        assert len(pred) == 2
        assert not pred["calibrated_probability"].isna().any()

    def test_predict_handles_unseen_machine_type(
        self,
        calibrated_risk_model: EdgeTwinRiskModel,
        raw_telemetry_cols: list[str],
    ) -> None:
        raw_df = pd.DataFrame(
            {
                "Air_Temperature_C": [25.0, 25.0],
                "Process_Temperature_C": [35.0, 35.0],
                "Rotational_Speed_RPM": [1500.0, 1500.0],
                "Torque_Nm": [40.0, 40.0],
                "Vibration_mm_s": [1.2, 1.2],
                "Pressure_bar": [4.0, 4.0],
                "Current_A": [12.0, 12.0],
                "Voltage_V": [220.0, 220.0],
                "Tool_Wear_Min": [50.0, 50.0],
                "Operating_Hours": [100.0, 100.0],
                "Machine_Type": ["UNSEEN_TYPE_99", "CUSTOM_V"],
            }
        )[raw_telemetry_cols]

        pred = calibrated_risk_model.predict(raw_df)
        assert len(pred) == 2
        assert not pred["calibrated_probability"].isna().any()


# ---------------------------------------------------------------------------
# R3: Leakage Guard
# ---------------------------------------------------------------------------


class TestModelLeakage:
    @pytest.mark.parametrize("forbidden_col", FORBIDDEN_FEATURE_COLUMNS)
    def test_predict_rejects_forbidden_columns(
        self,
        calibrated_risk_model: EdgeTwinRiskModel,
        raw_telemetry_cols: list[str],
        forbidden_col: str,
    ) -> None:
        raw_df = pd.DataFrame(
            {
                "Air_Temperature_C": [25.0],
                "Process_Temperature_C": [35.0],
                "Rotational_Speed_RPM": [1500.0],
                "Torque_Nm": [40.0],
                "Vibration_mm_s": [1.2],
                "Pressure_bar": [4.0],
                "Current_A": [12.0],
                "Voltage_V": [220.0],
                "Tool_Wear_Min": [50.0],
                "Operating_Hours": [100.0],
                "Machine_Type": ["L"],
                forbidden_col: [123],
            }
        )
        with pytest.raises(ValueError, match="Leakage guard violation"):
            calibrated_risk_model.predict(raw_df)


# ---------------------------------------------------------------------------
# R4: Output Contract, Threshold Consistency & Risk Bands
# ---------------------------------------------------------------------------


class TestOutputContract:
    def test_schema_and_probability_bounds(
        self,
        calibrated_risk_model: EdgeTwinRiskModel,
        synthetic_training_data: tuple[pd.DataFrame, pd.Series],
    ) -> None:
        X, _ = synthetic_training_data
        pred = calibrated_risk_model.predict(X)

        assert list(pred.columns) == ["calibrated_probability", "failure_prediction", "risk_band"]
        assert len(pred) == len(X)

        probs = pred["calibrated_probability"].to_numpy()
        assert np.all(probs >= 0.0)
        assert np.all(probs <= 1.0)
        assert not np.isnan(probs).any()

    def test_threshold_consistency(
        self,
        calibrated_risk_model: EdgeTwinRiskModel,
        synthetic_training_data: tuple[pd.DataFrame, pd.Series],
    ) -> None:
        X, _ = synthetic_training_data
        pred = calibrated_risk_model.predict(X)

        probs = pred["calibrated_probability"].to_numpy()
        preds = pred["failure_prediction"].to_numpy()

        assert np.all(np.isin(preds, [0, 1]))
        expected_preds = (probs >= OPERATIONAL_THRESHOLD).astype(int)
        np.testing.assert_array_equal(preds, expected_preds)

    def test_risk_band_mapping_and_boundaries(
        self,
        calibrated_risk_model: EdgeTwinRiskModel,
        synthetic_training_data: tuple[pd.DataFrame, pd.Series],
    ) -> None:
        X, _ = synthetic_training_data
        pred = calibrated_risk_model.predict(X)

        valid_bands = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        assert set(pred["risk_band"].unique()).issubset(valid_bands)

        for _, row in pred.iterrows():
            p = row["calibrated_probability"]
            b = row["risk_band"]
            if p < 0.15:
                assert b == "LOW"
            elif 0.15 <= p < 0.16:
                assert b == "MEDIUM"
            elif 0.16 <= p < 0.80:
                assert b == "HIGH"
            else:
                assert b == "CRITICAL"


# ---------------------------------------------------------------------------
# R5: Promotion Gate Verification
# ---------------------------------------------------------------------------


class TestPromotionGate:
    def test_promotion_gate_success(
        self,
        calibrated_risk_model: EdgeTwinRiskModel,
    ) -> None:
        metadata = {
            "calibration_method": "sigmoid",
            "operational_threshold": 0.16,
            "n_features": 14,
        }
        res = verify_promotion_gate(calibrated_risk_model, metadata=metadata)
        assert res["status"] == "PASSED"
        assert len(res["checks_passed"]) >= 9

    def test_promotion_gate_rejects_wrong_calibration_method(
        self,
        calibrated_risk_model: EdgeTwinRiskModel,
    ) -> None:
        bad_meta = {
            "calibration_method": "isotonic",
            "operational_threshold": 0.16,
            "n_features": 14,
        }
        with pytest.raises(ValueError, match="calibration_method must be 'sigmoid'"):
            verify_promotion_gate(calibrated_risk_model, metadata=bad_meta)

    def test_promotion_gate_rejects_wrong_threshold(
        self,
        calibrated_risk_model: EdgeTwinRiskModel,
    ) -> None:
        bad_meta = {
            "calibration_method": "sigmoid",
            "operational_threshold": 0.50,
            "n_features": 14,
        }
        with pytest.raises(ValueError, match="operational_threshold must be 0.16"):
            verify_promotion_gate(calibrated_risk_model, metadata=bad_meta)

    def test_promotion_gate_rejects_wrong_feature_count(
        self,
        calibrated_risk_model: EdgeTwinRiskModel,
    ) -> None:
        bad_meta = {
            "calibration_method": "sigmoid",
            "operational_threshold": 0.16,
            "n_features": 11,
        }
        with pytest.raises(ValueError, match="n_features must be 14"):
            verify_promotion_gate(calibrated_risk_model, metadata=bad_meta)


# ---------------------------------------------------------------------------
# R6: End-to-End Registration & Alias Resolution in Isolated Store
# ---------------------------------------------------------------------------


class TestRegistryLifecycle:
    def test_e2e_registration_and_champion_alias(
        self,
        calibrated_risk_model: EdgeTwinRiskModel,
        feature_cols_14: list[str],
        tmp_path: Path,
    ) -> None:
        orig_tracking_uri = mlflow.get_tracking_uri()
        db_path = tmp_path / "test_mlflow.db"
        tracking_uri = f"sqlite:///{db_path}"
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment("test-registry")

        # Save artifacts locally in tmp_path
        joblib_path = tmp_path / "calibrated_model.joblib"
        joblib.dump(calibrated_risk_model.calibrated_model, joblib_path)
        feat_path = tmp_path / "champion_features.json"
        with open(feat_path, "w", encoding="utf-8") as f:
            json.dump(feature_cols_14, f)

        metadata = {
            "model_family": "xgboost",
            "feature_set": "+physics",
            "calibration_method": "sigmoid",
            "operational_threshold": OPERATIONAL_THRESHOLD,
            "n_features": 14,
            "git_commit": "testcommit",
        }

        try:
            with mlflow.start_run(run_name="test-run"):
                for k, v in metadata.items():
                    mlflow.log_param(k, v)

                mlflow.pyfunc.log_model(
                    artifact_path="model",
                    python_model=calibrated_risk_model,
                    artifacts={
                        "calibrated_model": str(joblib_path),
                        "feature_cols": str(feat_path),
                    },
                    code_paths=["ml", "mlops"],
                    registered_model_name=MODEL_NAME,
                )

            client = MlflowClient()
            versions = client.search_model_versions(f"name='{MODEL_NAME}'")
            assert len(versions) >= 1
            v = str(max(int(x.version) for x in versions))

            # 1. Assign challenger
            client.set_registered_model_alias(MODEL_NAME, "challenger", v)
            challenger_model = client.get_model_version_by_alias(MODEL_NAME, "challenger")
            assert str(challenger_model.version) == str(v)

            # 2. Run promotion gate on challenger
            gate_res = verify_promotion_gate(f"models:/{MODEL_NAME}@challenger", metadata=metadata)
            assert gate_res["status"] == "PASSED"

            # 3. Assign champion
            client.set_registered_model_alias(MODEL_NAME, "champion", v)
            champion_model = client.get_model_version_by_alias(MODEL_NAME, "champion")
            assert str(champion_model.version) == str(v)

            # 4. Load-and-predict round trip via models:/edgetwin-risk@champion
            loaded = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}@champion")
            sample_raw = pd.DataFrame(
                {
                    "Air_Temperature_C": [25.0],
                    "Process_Temperature_C": [35.0],
                    "Rotational_Speed_RPM": [1500.0],
                    "Torque_Nm": [40.0],
                    "Vibration_mm_s": [1.2],
                    "Pressure_bar": [4.0],
                    "Current_A": [12.0],
                    "Voltage_V": [220.0],
                    "Tool_Wear_Min": [50.0],
                    "Operating_Hours": [100.0],
                    "Machine_Type": ["L"],
                }
            )
            res = loaded.predict(sample_raw)
            assert len(res) == 1
            assert list(res.columns) == [
                "calibrated_probability",
                "failure_prediction",
                "risk_band",
            ]
            assert 0.0 <= res["calibrated_probability"].iloc[0] <= 1.0
        finally:
            mlflow.set_tracking_uri(orig_tracking_uri)
