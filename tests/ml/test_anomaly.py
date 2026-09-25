"""
tests/ml/test_anomaly.py - Unit tests for unsupervised anomaly detector (T-014).

Test Groups:
- A1: Fitting on healthy training data only
- A2: Leakage rejection (forbidden columns raise ValueError)
- A3: Score normalization, semantics, and range [0, 1]
- A4: Safeguards: zero denominator, degenerate data, NaN/inf guards
- A5: Determinism with fixed seed
- A6: Validation evaluation and empirical threshold calculation
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml.data.schema import FORBIDDEN_FEATURE_COLUMNS
from ml.models.anomaly import (
    evaluate_anomaly_detector,
    fit_anomaly_detector,
    predict_anomaly_score,
)


@pytest.fixture
def synthetic_health_data() -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Synthetic train and validation sets with healthy and anomalous observations."""
    np.random.seed(42)
    feature_cols = ["sensor_1", "sensor_2", "sensor_3", "Machine_Type"]

    # 300 train rows: 260 healthy, 40 failures
    n_train = 300
    train_healthy = 260
    train_fail = 40

    train_data = {
        "sensor_1": np.concatenate(
            [np.random.normal(50, 5, train_healthy), np.random.normal(90, 10, train_fail)]
        ),
        "sensor_2": np.concatenate(
            [np.random.normal(100, 10, train_healthy), np.random.normal(20, 5, train_fail)]
        ),
        "sensor_3": np.concatenate(
            [np.random.normal(10, 2, train_healthy), np.random.normal(50, 15, train_fail)]
        ),
        "Machine_Type": np.random.choice(["Pump", "Motor", "Compressor"], n_train),
        "Machine_Failure": np.concatenate([np.zeros(train_healthy), np.ones(train_fail)]).astype(
            int
        ),
    }
    train_df = pd.DataFrame(train_data)

    # 100 val rows
    n_val = 100
    val_healthy = 85
    val_fail = 15
    val_data = {
        "sensor_1": np.concatenate(
            [np.random.normal(50, 5, val_healthy), np.random.normal(90, 10, val_fail)]
        ),
        "sensor_2": np.concatenate(
            [np.random.normal(100, 10, val_healthy), np.random.normal(20, 5, val_fail)]
        ),
        "sensor_3": np.concatenate(
            [np.random.normal(10, 2, val_healthy), np.random.normal(50, 15, val_fail)]
        ),
        "Machine_Type": np.random.choice(["Pump", "Motor", "Compressor"], n_val),
        "Machine_Failure": np.concatenate([np.zeros(val_healthy), np.ones(val_fail)]).astype(int),
    }
    val_df = pd.DataFrame(val_data)

    return train_df, val_df, feature_cols


# ---------------------------------------------------------------------------
# A1: Healthy training data
# ---------------------------------------------------------------------------


class TestAnomalyFitting:
    """A1: IsolationForest fits only on Machine_Failure == 0 rows."""

    def test_fit_uses_only_healthy_rows(
        self, synthetic_health_data: tuple[pd.DataFrame, pd.DataFrame, list[str]]
    ) -> None:
        train_df, _, feature_cols = synthetic_health_data
        _pipe, ref = fit_anomaly_detector(train_df, feature_cols, target_col="Machine_Failure")

        expected_healthy = int((train_df["Machine_Failure"] == 0).sum())
        assert ref["n_healthy_train"] == expected_healthy
        assert ref["delta"] > 0.0

    def test_missing_target_col_raises(
        self, synthetic_health_data: tuple[pd.DataFrame, pd.DataFrame, list[str]]
    ) -> None:
        train_df, _, feature_cols = synthetic_health_data
        with pytest.raises(ValueError, match="target_col 'Missing_Col' not found"):
            fit_anomaly_detector(train_df, feature_cols, target_col="Missing_Col")


# ---------------------------------------------------------------------------
# A2: Leakage guards
# ---------------------------------------------------------------------------


class TestAnomalyLeakageGuards:
    """A2: Forbidden columns must trigger ValueError."""

    @pytest.mark.parametrize("forbidden_col", FORBIDDEN_FEATURE_COLUMNS)
    def test_fit_detector_rejects_forbidden_columns(
        self,
        synthetic_health_data: tuple[pd.DataFrame, pd.DataFrame, list[str]],
        forbidden_col: str,
    ) -> None:
        train_df, _, feature_cols = synthetic_health_data
        leaked_cols = feature_cols + [forbidden_col]
        train_leaked = train_df.copy()
        train_leaked[forbidden_col] = 0

        with pytest.raises(ValueError, match="Leakage guard violation"):
            fit_anomaly_detector(train_leaked, leaked_cols)

    @pytest.mark.parametrize("forbidden_col", FORBIDDEN_FEATURE_COLUMNS)
    def test_predict_score_rejects_forbidden_columns(
        self,
        synthetic_health_data: tuple[pd.DataFrame, pd.DataFrame, list[str]],
        forbidden_col: str,
    ) -> None:
        train_df, _, feature_cols = synthetic_health_data
        pipe, ref = fit_anomaly_detector(train_df, feature_cols)

        X_leaked = train_df[feature_cols].copy()
        X_leaked[forbidden_col] = 0

        with pytest.raises(ValueError, match="Leakage guard violation"):
            predict_anomaly_score(pipe, ref, X_leaked)


# ---------------------------------------------------------------------------
# A3 & A4: Score semantics & safeguards
# ---------------------------------------------------------------------------


class TestAnomalyScoreSemantics:
    """A3 & A4: Score ranges, directionality, and robustness guards."""

    def test_score_range_and_directionality(
        self, synthetic_health_data: tuple[pd.DataFrame, pd.DataFrame, list[str]]
    ) -> None:
        train_df, val_df, feature_cols = synthetic_health_data
        pipe, ref = fit_anomaly_detector(train_df, feature_cols)

        scores = predict_anomaly_score(pipe, ref, val_df[feature_cols])
        assert np.all(scores >= 0.0)
        assert np.all(scores <= 1.0)

        # Failures should have significantly higher anomaly score than healthy on average
        mean_healthy = float(np.mean(scores[val_df["Machine_Failure"] == 0]))
        mean_failure = float(np.mean(scores[val_df["Machine_Failure"] == 1]))
        assert (
            mean_failure > mean_healthy
        ), f"Expected failure mean ({mean_failure}) > healthy mean ({mean_healthy})"

    def test_zero_denominator_guard(
        self, synthetic_health_data: tuple[pd.DataFrame, pd.DataFrame, list[str]]
    ) -> None:
        train_df, val_df, feature_cols = synthetic_health_data
        pipe, ref = fit_anomaly_detector(train_df, feature_cols)

        # Force degenerate delta
        degenerate_ref = dict(ref)
        degenerate_ref["delta"] = 0.0

        scores = predict_anomaly_score(pipe, degenerate_ref, val_df[feature_cols])
        # Safe fallback: all 0.5
        assert np.all(scores == 0.5)

    def test_nan_features_handle_gracefully(
        self, synthetic_health_data: tuple[pd.DataFrame, pd.DataFrame, list[str]]
    ) -> None:
        train_df, val_df, feature_cols = synthetic_health_data
        pipe, ref = fit_anomaly_detector(train_df, feature_cols)

        X_nan = val_df[feature_cols].copy()
        X_nan.loc[0, "sensor_1"] = np.nan

        scores = predict_anomaly_score(pipe, ref, X_nan)
        assert not np.isnan(scores[0])
        assert 0.0 <= scores[0] <= 1.0


# ---------------------------------------------------------------------------
# A5 & A6: Determinism & Validation Evaluation
# ---------------------------------------------------------------------------


class TestAnomalyDeterminismAndEval:
    """A5 & A6: Reproducibility and evaluation reporting."""

    def test_same_seed_produces_identical_scores(
        self, synthetic_health_data: tuple[pd.DataFrame, pd.DataFrame, list[str]]
    ) -> None:
        train_df, val_df, feature_cols = synthetic_health_data
        pipe1, ref1 = fit_anomaly_detector(train_df, feature_cols, seed=42)
        pipe2, ref2 = fit_anomaly_detector(train_df, feature_cols, seed=42)

        scores1 = predict_anomaly_score(pipe1, ref1, val_df[feature_cols])
        scores2 = predict_anomaly_score(pipe2, ref2, val_df[feature_cols])
        np.testing.assert_allclose(scores1, scores2, rtol=1e-5)

    def test_evaluate_anomaly_detector_structure(
        self, synthetic_health_data: tuple[pd.DataFrame, pd.DataFrame, list[str]]
    ) -> None:
        train_df, val_df, feature_cols = synthetic_health_data
        pipe, ref = fit_anomaly_detector(train_df, feature_cols)

        eval_res = evaluate_anomaly_detector(pipe, ref, val_df, feature_cols)
        assert "roc_auc" in eval_res
        assert "pr_auc" in eval_res
        assert "provisional_threshold" in eval_res
        assert "empirical_threshold" in eval_res
        assert 0.0 <= eval_res["empirical_threshold"] <= 1.0
        assert eval_res["provisional_threshold"] == 0.50
