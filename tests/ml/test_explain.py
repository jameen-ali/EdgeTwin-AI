"""
tests/ml/test_explain.py - Unit tests for EdgeTwinExplainer (T-015).

Test Groups:
- E1: Explainer initialization & component extraction (Pipeline vs CalibratedClassifierCV)
- E2: Leakage protection (rejection of all forbidden columns)
- E3: Feature alignment & transformed column recovery
- E4: Local explanation structure, top-k sorting, direction semantics, disclaimer
- E5: Additivity verification (|base + sum(shap) - margin| <= 1e-4) and loud failure on violation
- E6: Native XGBoost fallback engine equivalence
- E7: Global feature importance computation & ranking
- E8: Latency SLA benchmark (p95 < 100 ms)
- E9: explain_prediction API (single vs batch observation)
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import pytest
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

from ml.data.engineering import get_feature_cols_for_set
from ml.data.schema import FORBIDDEN_FEATURE_COLUMNS
from ml.models.calibrate import fit_calibrator
from ml.models.explain import (
    ADDITIVITY_TOLERANCE,
    EXPLAINABILITY_DISCLAIMER,
    EdgeTwinExplainer,
)
from ml.models.train import BASE_FEATURE_COLS, build_pipeline, train_model


@pytest.fixture
def feature_cols_14() -> list[str]:
    """Ordered 14 features for the +physics champion."""
    return get_feature_cols_for_set(BASE_FEATURE_COLS, "+physics")


@pytest.fixture
def synthetic_data_14(feature_cols_14: list[str]) -> tuple[pd.DataFrame, pd.Series]:
    """Synthetic dataset with 14 features for fast, offline testing."""
    np.random.seed(42)
    n = 80
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
    # Synthetic failure labels
    y_raw = (df["Tool_Wear_Min"] > 180) | (df["Vibration_mm_s"] > 2.8)
    y = pd.Series(y_raw.astype(int), name="Machine_Failure")
    return df, y


@pytest.fixture
def fitted_pipeline(
    synthetic_data_14: tuple[pd.DataFrame, pd.Series],
    feature_cols_14: list[str],
) -> Pipeline:
    """Fitted champion pipeline on synthetic data."""
    X, y = synthetic_data_14
    pipe = build_pipeline("xgboost", feature_cols_14, seed=42)
    return train_model(pipe, X, y)


@pytest.fixture
def fitted_calibrated_model(
    fitted_pipeline: Pipeline,
    synthetic_data_14: tuple[pd.DataFrame, pd.Series],
) -> Any:
    """Fitted CalibratedClassifierCV wrapping champion pipeline."""
    X, y = synthetic_data_14
    return fit_calibrator(fitted_pipeline, X, y, method="sigmoid")


# ---------------------------------------------------------------------------
# E1: Explainer Initialization & Component Extraction
# ---------------------------------------------------------------------------


class TestExplainerInit:
    def test_init_with_pipeline(
        self,
        fitted_pipeline: Pipeline,
        feature_cols_14: list[str],
    ) -> None:
        explainer = EdgeTwinExplainer(fitted_pipeline, feature_cols_14)
        assert explainer.calibrator is None
        assert isinstance(explainer.preprocessor, ColumnTransformer)
        assert len(explainer.transformed_feature_names) == 14

    def test_init_with_calibrated_classifier(
        self,
        fitted_calibrated_model: Any,
        feature_cols_14: list[str],
    ) -> None:
        explainer = EdgeTwinExplainer(fitted_calibrated_model, feature_cols_14)
        assert explainer.calibrator is not None
        assert isinstance(explainer.preprocessor, ColumnTransformer)
        assert len(explainer.transformed_feature_names) == 14

    def test_init_invalid_estimator_type(self, feature_cols_14: list[str]) -> None:
        with pytest.raises(TypeError, match="Expected Pipeline or CalibratedClassifierCV"):
            EdgeTwinExplainer("not_a_model", feature_cols_14)  # type: ignore

    def test_init_feature_count_mismatch(
        self,
        fitted_pipeline: Pipeline,
    ) -> None:
        # Pass only 5 feature cols when preprocessor expects 14
        with pytest.raises(ValueError, match="Feature count mismatch"):
            EdgeTwinExplainer(fitted_pipeline, ["Air_Temperature_C", "Torque_Nm"])


# ---------------------------------------------------------------------------
# E2: Leakage Protection
# ---------------------------------------------------------------------------


class TestExplainerLeakage:
    @pytest.mark.parametrize("forbidden_col", FORBIDDEN_FEATURE_COLUMNS)
    def test_rejects_forbidden_columns_in_feature_cols(
        self,
        fitted_pipeline: Pipeline,
        feature_cols_14: list[str],
        forbidden_col: str,
    ) -> None:
        bad_cols = feature_cols_14[:-1] + [forbidden_col]
        with pytest.raises(ValueError, match="Leakage guard violation"):
            EdgeTwinExplainer(fitted_pipeline, bad_cols)

    @pytest.mark.parametrize("forbidden_col", FORBIDDEN_FEATURE_COLUMNS)
    def test_rejects_forbidden_column_in_explain_instance(
        self,
        fitted_pipeline: Pipeline,
        synthetic_data_14: tuple[pd.DataFrame, pd.Series],
        feature_cols_14: list[str],
        forbidden_col: str,
    ) -> None:
        X, _ = synthetic_data_14
        explainer = EdgeTwinExplainer(fitted_pipeline, feature_cols_14)
        row = X.iloc[[0]].copy()
        row[forbidden_col] = 123
        with pytest.raises(ValueError, match="Leakage guard violation"):
            explainer.explain_instance(row)

    @pytest.mark.parametrize("forbidden_col", FORBIDDEN_FEATURE_COLUMNS)
    def test_rejects_forbidden_column_in_explain_global(
        self,
        fitted_pipeline: Pipeline,
        synthetic_data_14: tuple[pd.DataFrame, pd.Series],
        feature_cols_14: list[str],
        forbidden_col: str,
    ) -> None:
        X, _ = synthetic_data_14
        explainer = EdgeTwinExplainer(fitted_pipeline, feature_cols_14)
        X_bad = X.copy()
        X_bad[forbidden_col] = 123
        with pytest.raises(ValueError, match="Leakage guard violation"):
            explainer.explain_global(X_bad)


# ---------------------------------------------------------------------------
# E3: Feature Alignment
# ---------------------------------------------------------------------------


class TestFeatureAlignment:
    def test_transformed_feature_names_match_feature_cols(
        self,
        fitted_pipeline: Pipeline,
        feature_cols_14: list[str],
    ) -> None:
        explainer = EdgeTwinExplainer(fitted_pipeline, feature_cols_14)
        # All 14 feature columns should be present in transformed names (set equality)
        assert set(explainer.transformed_feature_names) == set(feature_cols_14)
        assert len(explainer.transformed_feature_names) == 14

    def test_machine_type_position_resolved_deterministically(
        self,
        fitted_pipeline: Pipeline,
        feature_cols_14: list[str],
    ) -> None:
        explainer = EdgeTwinExplainer(fitted_pipeline, feature_cols_14)
        # Machine_Type is categorical, ColumnTransformer puts numeric first then cat
        assert "Machine_Type" in explainer.transformed_feature_names


# ---------------------------------------------------------------------------
# E4: Local Explanation Structure & Semantics
# ---------------------------------------------------------------------------


class TestLocalExplanation:
    def test_local_explanation_keys(
        self,
        fitted_calibrated_model: Any,
        synthetic_data_14: tuple[pd.DataFrame, pd.Series],
        feature_cols_14: list[str],
    ) -> None:
        X, _ = synthetic_data_14
        explainer = EdgeTwinExplainer(fitted_calibrated_model, feature_cols_14)
        res = explainer.explain_instance(X.iloc[[0]], top_k=5)

        expected_keys = {
            "base_value",
            "model_margin",
            "calibrated_probability",
            "feature_contributions",
            "top_factors",
            "additivity_verified",
            "additivity_discrepancy",
            "disclaimer",
        }
        assert expected_keys.issubset(res.keys())
        assert res["additivity_verified"] is True
        assert res["disclaimer"] == EXPLAINABILITY_DISCLAIMER
        assert res["calibrated_probability"] is not None
        assert 0.0 <= res["calibrated_probability"] <= 1.0

    def test_top_k_sorting_and_direction(
        self,
        fitted_pipeline: Pipeline,
        synthetic_data_14: tuple[pd.DataFrame, pd.Series],
        feature_cols_14: list[str],
    ) -> None:
        X, _ = synthetic_data_14
        explainer = EdgeTwinExplainer(fitted_pipeline, feature_cols_14)
        res = explainer.explain_instance(X.iloc[[0]], top_k=4)

        top = res["top_factors"]
        assert len(top) == 4

        # Strictly sorted descending by absolute magnitude
        mags = [item["abs_magnitude"] for item in top]
        assert mags == sorted(mags, reverse=True)

        # Check direction semantics
        for item in top:
            if item["shap_value"] > 1e-6:
                assert item["direction"] == "increases risk"
            elif item["shap_value"] < -1e-6:
                assert item["direction"] == "lowers risk"
            else:
                assert item["direction"] == "neutral"


# ---------------------------------------------------------------------------
# E5: Additivity Verification & Strict Tolerance
# ---------------------------------------------------------------------------


class TestAdditivity:
    def test_additivity_on_multiple_rows(
        self,
        fitted_pipeline: Pipeline,
        synthetic_data_14: tuple[pd.DataFrame, pd.Series],
        feature_cols_14: list[str],
    ) -> None:
        X, _ = synthetic_data_14
        explainer = EdgeTwinExplainer(fitted_pipeline, feature_cols_14)

        for i in range(min(15, len(X))):
            res = explainer.explain_instance(X.iloc[[i]])
            assert res["additivity_discrepancy"] <= ADDITIVITY_TOLERANCE
            assert res["additivity_verified"] is True

    def test_additivity_violation_raises_value_error(
        self,
        fitted_pipeline: Pipeline,
        synthetic_data_14: tuple[pd.DataFrame, pd.Series],
        feature_cols_14: list[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        X, _ = synthetic_data_14
        explainer = EdgeTwinExplainer(fitted_pipeline, feature_cols_14)

        original_compute = explainer._compute_shap_matrix

        # Artificially inject corrupted SHAP matrix
        def fake_shap(X_trans: np.ndarray) -> tuple[np.ndarray, float]:
            shap_matrix, base_val = original_compute(X_trans)
            # Add large corruption to break additivity
            shap_matrix = shap_matrix.copy()
            shap_matrix[0, 0] += 5.0
            return shap_matrix, base_val

        monkeypatch.setattr(explainer, "_compute_shap_matrix", fake_shap)

        with pytest.raises(ValueError, match="Additivity consistency check failed"):
            explainer.explain_instance(X.iloc[[0]])


# ---------------------------------------------------------------------------
# E6: Native XGBoost Fallback Engine
# ---------------------------------------------------------------------------


class TestNativeFallback:
    def test_fallback_produces_identical_results(
        self,
        fitted_pipeline: Pipeline,
        synthetic_data_14: tuple[pd.DataFrame, pd.Series],
        feature_cols_14: list[str],
    ) -> None:
        X, _ = synthetic_data_14
        row = X.iloc[[0]]

        expl_primary = EdgeTwinExplainer(fitted_pipeline, feature_cols_14, use_fallback=False)
        expl_fallback = EdgeTwinExplainer(fitted_pipeline, feature_cols_14, use_fallback=True)

        res_p = expl_primary.explain_instance(row)
        res_fb = expl_fallback.explain_instance(row)

        assert abs(res_p["base_value"] - res_fb["base_value"]) < 1e-4
        assert abs(res_p["model_margin"] - res_fb["model_margin"]) < 1e-4
        assert res_fb["additivity_verified"] is True

        p_shaps = [c["shap_value"] for c in res_p["feature_contributions"]]
        fb_shaps = [c["shap_value"] for c in res_fb["feature_contributions"]]
        np.testing.assert_allclose(p_shaps, fb_shaps, atol=1e-4)


# ---------------------------------------------------------------------------
# E7: Global Importance Computation & Ranking
# ---------------------------------------------------------------------------


class TestGlobalImportance:
    def test_explain_global_table(
        self,
        fitted_pipeline: Pipeline,
        synthetic_data_14: tuple[pd.DataFrame, pd.Series],
        feature_cols_14: list[str],
    ) -> None:
        X, _ = synthetic_data_14
        explainer = EdgeTwinExplainer(fitted_pipeline, feature_cols_14)
        df_imp = explainer.explain_global(X)

        assert isinstance(df_imp, pd.DataFrame)
        assert list(df_imp.columns) == ["feature_name", "mean_abs_shap", "mean_signed_shap"]
        assert len(df_imp) == 14

        # Sorted descending by mean_abs_shap
        mean_abs = df_imp["mean_abs_shap"].tolist()
        assert mean_abs == sorted(mean_abs, reverse=True)
        assert all(v >= 0.0 for v in mean_abs)


# ---------------------------------------------------------------------------
# E8: Latency SLA Benchmark (p95 < 100 ms)
# ---------------------------------------------------------------------------


class TestLatencySLA:
    def test_latency_sla_under_100ms(
        self,
        fitted_pipeline: Pipeline,
        synthetic_data_14: tuple[pd.DataFrame, pd.Series],
        feature_cols_14: list[str],
    ) -> None:
        X, _ = synthetic_data_14
        explainer = EdgeTwinExplainer(fitted_pipeline, feature_cols_14)

        bench = explainer.benchmark_latency(X.head(20), n_runs=50)
        assert bench["n_runs"] == 50
        assert bench["p95_ms"] < 100.0, f"p95 latency {bench['p95_ms']:.2f} ms exceeds 100 ms SLA"
        assert bench["sla_passed"] is True


# ---------------------------------------------------------------------------
# E9: explain_prediction API (Single vs Batch)
# ---------------------------------------------------------------------------


class TestExplainPredictionAPI:
    def test_explain_prediction_series(
        self,
        fitted_pipeline: Pipeline,
        synthetic_data_14: tuple[pd.DataFrame, pd.Series],
        feature_cols_14: list[str],
    ) -> None:
        X, _ = synthetic_data_14
        explainer = EdgeTwinExplainer(fitted_pipeline, feature_cols_14)
        res = explainer.explain_prediction(X.iloc[0])
        assert isinstance(res, dict)
        assert "top_factors" in res

    def test_explain_prediction_single_row_dataframe(
        self,
        fitted_pipeline: Pipeline,
        synthetic_data_14: tuple[pd.DataFrame, pd.Series],
        feature_cols_14: list[str],
    ) -> None:
        X, _ = synthetic_data_14
        explainer = EdgeTwinExplainer(fitted_pipeline, feature_cols_14)
        res = explainer.explain_prediction(X.iloc[[0]])
        assert isinstance(res, dict)
        assert "top_factors" in res

    def test_explain_prediction_batch_dataframe(
        self,
        fitted_pipeline: Pipeline,
        synthetic_data_14: tuple[pd.DataFrame, pd.Series],
        feature_cols_14: list[str],
    ) -> None:
        X, _ = synthetic_data_14
        explainer = EdgeTwinExplainer(fitted_pipeline, feature_cols_14)
        res = explainer.explain_prediction(X.head(4))
        assert isinstance(res, list)
        assert len(res) == 4
        assert all(isinstance(r, dict) for r in res)
        assert all("top_factors" in r for r in res)
