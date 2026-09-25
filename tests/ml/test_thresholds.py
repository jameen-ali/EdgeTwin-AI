"""
tests/ml/test_thresholds.py - Unit tests for threshold sweep and risk bands (T-013).

Test Groups:
- T1: Sweep table completeness and confusion matrix balance
- T2: Metric monotonicity (recall non-increasing with threshold)
- T3: Cost function calculations and cost-optimal selection
- T4: F1-optimal selection
- T5: PRD target filtering (Recall >= 0.85, Precision >= 0.70)
- T6: Risk bands partition & boundary correctness
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.models.thresholds import (
    BAND_CRITICAL,
    BAND_HIGH,
    BAND_LOW,
    BAND_MEDIUM,
    DEFAULT_THRESHOLDS,
    RISK_BANDS,
    classify_risk_band,
    find_cost_optimal_threshold,
    find_f1_optimal_threshold,
    find_prd_target_thresholds,
    sweep_thresholds,
)


@pytest.fixture
def synthetic_predictions() -> tuple[np.ndarray, np.ndarray]:
    """Synthetic true labels and predicted probabilities with moderate separation."""
    np.random.seed(42)
    n = 500
    y_true = np.random.binomial(1, 0.10, n)  # ~10% positive class
    # Add noise to proba
    y_proba = np.clip(
        y_true * 0.7 + np.random.beta(2, 5, n) * 0.4,
        0.0,
        1.0,
    )
    return y_true, y_proba


# ---------------------------------------------------------------------------
# T1: Sweep table completeness
# ---------------------------------------------------------------------------


class TestThresholdSweep:
    """T1 & T2: Sweep generation and metric consistency."""

    def test_default_sweep_length_and_range(
        self, synthetic_predictions: tuple[np.ndarray, np.ndarray]
    ) -> None:
        y_true, y_proba = synthetic_predictions
        res = sweep_thresholds(y_true, y_proba)
        assert len(res) == len(DEFAULT_THRESHOLDS)
        assert res[0]["threshold"] == pytest.approx(0.10, abs=1e-3)
        assert res[-1]["threshold"] == pytest.approx(0.90, abs=1e-3)

    def test_confusion_matrix_sum_equals_sample_count(
        self, synthetic_predictions: tuple[np.ndarray, np.ndarray]
    ) -> None:
        y_true, y_proba = synthetic_predictions
        n_samples = len(y_true)
        res = sweep_thresholds(y_true, y_proba)

        for row in res:
            total = row["tp"] + row["tn"] + row["fp"] + row["fn"]
            assert total == n_samples
            assert 0.0 <= row["precision"] <= 1.0
            assert 0.0 <= row["recall"] <= 1.0
            assert 0.0 <= row["f1"] <= 1.0
            assert 0.0 <= row["f2"] <= 1.0
            assert 0.0 <= row["predicted_positive_rate"] <= 1.0

    def test_recall_is_monotonically_non_increasing(
        self, synthetic_predictions: tuple[np.ndarray, np.ndarray]
    ) -> None:
        y_true, y_proba = synthetic_predictions
        res = sweep_thresholds(y_true, y_proba)

        recalls = [r["recall"] for r in res]
        for i in range(len(recalls) - 1):
            assert (
                recalls[i] >= recalls[i + 1] - 1e-6
            ), f"Recall increased from {recalls[i]} to {recalls[i+1]} at step {i}"


# ---------------------------------------------------------------------------
# T3: Cost optimization
# ---------------------------------------------------------------------------


class TestCostOptimization:
    """T3: Cost calculation and cost-optimal threshold selection."""

    def test_cost_calculation_matches_formula(
        self, synthetic_predictions: tuple[np.ndarray, np.ndarray]
    ) -> None:
        y_true, y_proba = synthetic_predictions
        cost_ratios = (1, 3, 5, 10)
        res = sweep_thresholds(y_true, y_proba, cost_ratios=cost_ratios)

        for r in cost_ratios:
            for row in res:
                expected_cost = r * row["fn"] + row["fp"]
                assert row[f"cost_r{r}"] == expected_cost

    def test_cost_optimal_minimizes_cost(
        self, synthetic_predictions: tuple[np.ndarray, np.ndarray]
    ) -> None:
        y_true, y_proba = synthetic_predictions
        res = sweep_thresholds(y_true, y_proba, cost_ratios=(1, 5))

        best_r5 = find_cost_optimal_threshold(res, cost_ratio=5)
        for row in res:
            assert best_r5["cost_r5"] <= row["cost_r5"]

    def test_invalid_cost_ratio_raises_key_error(
        self, synthetic_predictions: tuple[np.ndarray, np.ndarray]
    ) -> None:
        y_true, y_proba = synthetic_predictions
        res = sweep_thresholds(y_true, y_proba, cost_ratios=(1, 5))
        with pytest.raises(KeyError, match="Cost ratio r=99"):
            find_cost_optimal_threshold(res, cost_ratio=99)


# ---------------------------------------------------------------------------
# T4 & T5: F1 and PRD Target
# ---------------------------------------------------------------------------


class TestF1AndPrdSelection:
    """T4 & T5: F1 maximization and PRD criteria."""

    def test_find_f1_optimal_maximizes_f1(
        self, synthetic_predictions: tuple[np.ndarray, np.ndarray]
    ) -> None:
        y_true, y_proba = synthetic_predictions
        res = sweep_thresholds(y_true, y_proba)
        best_f1 = find_f1_optimal_threshold(res)

        for row in res:
            assert best_f1["f1"] >= row["f1"] - 1e-6

    def test_prd_target_filters_correctly(self) -> None:
        # Mock sweep results with known values
        mock_results = [
            {"threshold": 0.30, "recall": 0.90, "precision": 0.65, "f1": 0.75},
            {"threshold": 0.40, "recall": 0.86, "precision": 0.72, "f1": 0.78},
            {"threshold": 0.50, "recall": 0.80, "precision": 0.85, "f1": 0.82},
        ]
        qualifying = find_prd_target_thresholds(mock_results, min_recall=0.85, min_precision=0.70)
        assert len(qualifying) == 1
        assert qualifying[0]["threshold"] == 0.40

    def test_prd_target_returns_empty_when_no_match(self) -> None:
        mock_results = [
            {"threshold": 0.30, "recall": 0.50, "precision": 0.50, "f1": 0.50},
        ]
        qualifying = find_prd_target_thresholds(mock_results, min_recall=0.85, min_precision=0.70)
        assert qualifying == []


# ---------------------------------------------------------------------------
# T6: Risk bands
# ---------------------------------------------------------------------------


class TestRiskBands:
    """T6: Risk band partitions and boundaries."""

    @pytest.mark.parametrize(
        "proba,t_star,expected_band",
        [
            (0.00, 0.40, BAND_LOW),
            (0.149, 0.40, BAND_LOW),
            (0.15, 0.40, BAND_MEDIUM),
            (0.399, 0.40, BAND_MEDIUM),
            (0.40, 0.40, BAND_HIGH),
            (0.799, 0.40, BAND_HIGH),
            (0.80, 0.40, BAND_CRITICAL),
            (1.00, 0.40, BAND_CRITICAL),
        ],
    )
    def test_scalar_risk_band_boundaries(
        self, proba: float, t_star: float, expected_band: str
    ) -> None:
        assert classify_risk_band(proba, t_star) == expected_band

    def test_vectorized_risk_bands_match_scalar(self) -> None:
        t_star = 0.42
        test_probas = np.array([0.05, 0.15, 0.30, 0.42, 0.60, 0.80, 0.95])
        vector_res = classify_risk_band(test_probas, t_star)

        for p, v_band in zip(test_probas, vector_res):
            s_band = classify_risk_band(float(p), t_star)
            assert v_band == s_band
            assert v_band in RISK_BANDS
