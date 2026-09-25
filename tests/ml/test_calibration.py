"""
tests/ml/test_calibration.py - Unit tests for probability calibration (T-013).

Test Groups:
- C1: Calibration metrics & curve data (Brier, ECE, bounds)
- C2: Fit & predict calibrator (sigmoid and isotonic via FrozenEstimator)
- C3: Leakage guards (forbidden columns rejected)
- C4: Monotonicity and probability bounds [0, 1]
- C5: Calibration comparison & selection logic on synthetic/real data
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.data.schema import FORBIDDEN_FEATURE_COLUMNS
from ml.models.calibrate import (
    CALIBRATION_METHODS,
    compare_calibration_methods,
    compute_calibration_metrics,
    fit_calibrator,
    get_calibration_curve_data,
    predict_calibrated_proba,
)


@pytest.fixture
def synthetic_binary_data() -> tuple[pd.DataFrame, pd.Series]:
    """Deterministic synthetic data with 5 features and 200 samples."""
    np.random.seed(42)
    n = 200
    X = pd.DataFrame(
        {
            "feat_1": np.random.randn(n),
            "feat_2": np.random.randn(n) * 2.0,
            "feat_3": np.random.uniform(10, 50, n),
        }
    )
    # Log-odds dependent on feat_1 and feat_2
    logits = X["feat_1"] * 1.5 - X["feat_2"] * 0.5
    proba = 1.0 / (1.0 + np.exp(-logits))
    y = pd.Series((proba >= 0.5).astype(int), name="Machine_Failure")
    return X, y


@pytest.fixture
def simple_fitted_pipeline(synthetic_binary_data: tuple[pd.DataFrame, pd.Series]) -> Pipeline:
    """Pre-fitted sklearn Pipeline for calibration wrapping."""
    X, y = synthetic_binary_data
    pipe = Pipeline([("scaler", StandardScaler()), ("clf", LogisticRegression(random_state=42))])
    pipe.fit(X, y)
    return pipe


# ---------------------------------------------------------------------------
# C1: Calibration metrics & curve data
# ---------------------------------------------------------------------------


class TestCalibrationMetrics:
    """C1: Metrics computation (Brier score, ECE, ROC-AUC, PR-AUC)."""

    def test_perfect_predictions_brier_zero(self) -> None:
        y_true = np.array([0, 1, 0, 1])
        y_proba = np.array([0.0, 1.0, 0.0, 1.0])
        metrics = compute_calibration_metrics(y_true, y_proba)
        assert metrics["brier_score"] == pytest.approx(0.0, abs=1e-6)
        assert metrics["ece"] == pytest.approx(0.0, abs=1e-6)
        assert metrics["roc_auc"] == pytest.approx(1.0, abs=1e-6)
        assert metrics["pr_auc"] == pytest.approx(1.0, abs=1e-6)

    def test_worst_predictions_brier_one(self) -> None:
        y_true = np.array([0, 1])
        y_proba = np.array([1.0, 0.0])
        metrics = compute_calibration_metrics(y_true, y_proba)
        assert metrics["brier_score"] == pytest.approx(1.0, abs=1e-6)

    def test_metrics_keys_and_ranges(self) -> None:
        y_true = np.array([0, 0, 1, 1, 0, 1])
        y_proba = np.array([0.1, 0.2, 0.8, 0.9, 0.3, 0.7])
        metrics = compute_calibration_metrics(y_true, y_proba)
        assert set(metrics.keys()) == {"brier_score", "ece", "roc_auc", "pr_auc"}
        for k, v in metrics.items():
            assert 0.0 <= v <= 1.0, f"Metric {k} = {v} is outside [0, 1]"

    def test_calibration_curve_data_structure(self) -> None:
        y_true = np.array([0, 0, 0, 1, 1, 1, 1, 0])
        y_proba = np.array([0.1, 0.2, 0.3, 0.7, 0.8, 0.85, 0.9, 0.15])
        curve = get_calibration_curve_data(y_true, y_proba, n_bins=5)
        assert "prob_true" in curve
        assert "prob_pred" in curve
        assert len(curve["prob_true"]) == len(curve["prob_pred"])
        assert len(curve["prob_true"]) > 0


# ---------------------------------------------------------------------------
# C2: Fit & predict calibrator
# ---------------------------------------------------------------------------


class TestCalibratorFitting:
    """C2: Calibrator fitting using FrozenEstimator."""

    @pytest.mark.parametrize("method", CALIBRATION_METHODS)
    def test_fit_and_predict_probabilities(
        self,
        simple_fitted_pipeline: Pipeline,
        synthetic_binary_data: tuple[pd.DataFrame, pd.Series],
        method: str,
    ) -> None:
        X, y = synthetic_binary_data
        calibrator = fit_calibrator(simple_fitted_pipeline, X, y, method=method)
        proba = predict_calibrated_proba(calibrator, X)

        assert isinstance(proba, np.ndarray)
        assert len(proba) == len(X)
        assert np.all(proba >= 0.0)
        assert np.all(proba <= 1.0)

    def test_invalid_method_raises(
        self,
        simple_fitted_pipeline: Pipeline,
        synthetic_binary_data: tuple[pd.DataFrame, pd.Series],
    ) -> None:
        X, y = synthetic_binary_data
        with pytest.raises(ValueError, match="Unknown calibration method"):
            fit_calibrator(simple_fitted_pipeline, X, y, method="unsupported_method")


# ---------------------------------------------------------------------------
# C3: Leakage guards
# ---------------------------------------------------------------------------


class TestCalibrationLeakageGuards:
    """C3: Forbidden columns must trigger ValueError."""

    @pytest.mark.parametrize("forbidden_col", FORBIDDEN_FEATURE_COLUMNS)
    def test_fit_calibrator_rejects_forbidden_columns(
        self,
        simple_fitted_pipeline: Pipeline,
        synthetic_binary_data: tuple[pd.DataFrame, pd.Series],
        forbidden_col: str,
    ) -> None:
        X, y = synthetic_binary_data
        X_leaked = X.copy()
        X_leaked[forbidden_col] = 1

        with pytest.raises(ValueError, match="Leakage guard violation"):
            fit_calibrator(simple_fitted_pipeline, X_leaked, y, method="sigmoid")

    @pytest.mark.parametrize("forbidden_col", FORBIDDEN_FEATURE_COLUMNS)
    def test_predict_calibrated_rejects_forbidden_columns(
        self,
        simple_fitted_pipeline: Pipeline,
        synthetic_binary_data: tuple[pd.DataFrame, pd.Series],
        forbidden_col: str,
    ) -> None:
        X, y = synthetic_binary_data
        cal = fit_calibrator(simple_fitted_pipeline, X, y, method="sigmoid")
        X_leaked = X.copy()
        X_leaked[forbidden_col] = 1

        with pytest.raises(ValueError, match="Leakage guard violation"):
            predict_calibrated_proba(cal, X_leaked)


# ---------------------------------------------------------------------------
# C4: Comparison & method selection
# ---------------------------------------------------------------------------


class TestCalibrationComparison:
    """C4: Method comparison logic."""

    def test_compare_calibration_methods_returns_all_keys(
        self,
        simple_fitted_pipeline: Pipeline,
        synthetic_binary_data: tuple[pd.DataFrame, pd.Series],
    ) -> None:
        X, y = synthetic_binary_data
        feature_cols = list(X.columns)
        res = compare_calibration_methods(simple_fitted_pipeline, X, y, feature_cols)

        assert "uncalibrated" in res
        assert "sigmoid" in res
        assert "isotonic" in res
        assert "selected_method" in res
        assert res["selected_method"] in {"uncalibrated", "sigmoid", "isotonic"}

        for m in ("uncalibrated", "sigmoid", "isotonic"):
            metrics = res[m]["metrics"]
            assert "brier_score" in metrics
            assert "ece" in metrics
            assert "pr_auc" in metrics
            assert "roc_auc" in metrics
            proba = res[m]["probabilities"]
            assert np.all(proba >= 0.0) and np.all(proba <= 1.0)
