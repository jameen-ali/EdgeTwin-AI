"""
ml/models/thresholds.py - EdgeTwin AI threshold analysis and risk bands module.

T-013: Sweeps candidate decision thresholds (0.10 to 0.90, step 0.02) on
validation data, evaluates cost-sensitive operating points, checks the PRD
target, and assigns discrete risk bands.

Formulas & Definitions
----------------------
Precision:   TP / (TP + FP)
Recall:      TP / (TP + FN)
F1 score:    2 * P * R / (P + R)
F2 score:    5 * P * R / (4 * P + R)   (weights recall twice as heavily as precision)
Cost(t; r):  r * FN(t) + FP(t)         (r = cost ratio C_FN / C_FP)
Pred Rate:   (TP + FP) / N

Risk Bands (Project Operating Rules)
------------------------------------
- LOW:      p < 0.15
- MEDIUM:   0.15 <= p < t*
- HIGH:     t* <= p < 0.80
- CRITICAL: p >= 0.80

Author: T-013 / S05
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

# Default sweep settings
DEFAULT_THRESHOLDS: np.ndarray = np.round(np.arange(0.10, 0.91, 0.02), 2)
DEFAULT_COST_RATIOS: tuple[int, ...] = (1, 3, 5, 10)

# Risk Band Names
BAND_LOW: str = "LOW"
BAND_MEDIUM: str = "MEDIUM"
BAND_HIGH: str = "HIGH"
BAND_CRITICAL: str = "CRITICAL"
RISK_BANDS: tuple[str, ...] = (BAND_LOW, BAND_MEDIUM, BAND_HIGH, BAND_CRITICAL)


def sweep_thresholds(
    y_true: pd.Series | np.ndarray,
    y_proba: np.ndarray,
    thresholds: np.ndarray | None = None,
    cost_ratios: tuple[int, ...] = DEFAULT_COST_RATIOS,
) -> list[dict[str, Any]]:
    """Evaluate classification and cost metrics across a range of decision thresholds.

    Parameters
    ----------
    y_true:
        Ground truth binary labels (0/1).
    y_proba:
        Predicted positive-class probabilities.
    thresholds:
        Array of threshold values in [0.0, 1.0]. Defaults to 0.10..0.90 (step 0.02).
    cost_ratios:
        Tuple of integer cost ratios r = C_FN / C_FP.

    Returns
    -------
    list[dict[str, Any]]
        List of dicts containing threshold metrics for each point in thresholds.
    """
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS

    y_true_arr = np.asarray(y_true, dtype=int)
    y_proba_arr = np.asarray(y_proba, dtype=float)
    n_samples = len(y_true_arr)

    results: list[dict[str, Any]] = []

    for t in thresholds:
        t_val = float(t)
        y_pred = (y_proba_arr >= t_val).astype(int)

        tp = int(np.sum((y_pred == 1) & (y_true_arr == 1)))
        tn = int(np.sum((y_pred == 0) & (y_true_arr == 0)))
        fp = int(np.sum((y_pred == 1) & (y_true_arr == 0)))
        fn = int(np.sum((y_pred == 0) & (y_true_arr == 1)))

        prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = float(2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        f2 = float(5 * prec * rec / (4 * prec + rec)) if (4 * prec + rec) > 0 else 0.0
        pred_rate = float((tp + fp) / n_samples) if n_samples > 0 else 0.0

        item: dict[str, Any] = {
            "threshold": t_val,
            "tp": tp,
            "tn": tn,
            "fp": fp,
            "fn": fn,
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "f2": f2,
            "predicted_positive_rate": pred_rate,
        }

        # Compute cost for each ratio: Cost = r * FN + FP
        for r in cost_ratios:
            item[f"cost_r{r}"] = int(r * fn + fp)

        results.append(item)

    return results


def find_f1_optimal_threshold(sweep_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Find the threshold record maximizing the F1 score.

    Ties broken by higher recall, then lower threshold.
    """
    if not sweep_results:
        raise ValueError("sweep_results cannot be empty")
    return max(sweep_results, key=lambda x: (x["f1"], x["recall"], -x["threshold"]))


def find_cost_optimal_threshold(
    sweep_results: list[dict[str, Any]],
    cost_ratio: int = 5,
) -> dict[str, Any]:
    """Find the threshold record minimizing Cost = r * FN + FP.

    Ties broken by higher recall, then lower false positives.
    """
    if not sweep_results:
        raise ValueError("sweep_results cannot be empty")
    key = f"cost_r{cost_ratio}"
    if key not in sweep_results[0]:
        raise KeyError(f"Cost ratio r={cost_ratio} was not evaluated in sweep_results")
    return min(sweep_results, key=lambda x: (x[key], -x["recall"], x["fp"]))


def find_prd_target_thresholds(
    sweep_results: list[dict[str, Any]],
    min_recall: float = 0.85,
    min_precision: float = 0.70,
) -> list[dict[str, Any]]:
    """Find all threshold points satisfying the PRD target (Recall >= min_recall and Precision >= min_precision).

    Parameters
    ----------
    sweep_results:
        Results from sweep_thresholds().
    min_recall:
        Minimum target recall (default: 0.85 per PRD §13.3).
    min_precision:
        Minimum target precision (default: 0.70 per PRD §13.3).

    Returns
    -------
    list[dict[str, Any]]
        List of qualifying threshold records (may be empty if target is unachievable).
    """
    qualifying = [
        item
        for item in sweep_results
        if item["recall"] >= min_recall and item["precision"] >= min_precision
    ]
    # Sort qualifying points by highest F1 score
    return sorted(qualifying, key=lambda x: x["f1"], reverse=True)


def classify_risk_band(
    proba: float | np.ndarray,
    t_star: float,
) -> str | np.ndarray:
    """Map a continuous probability value or array to a discrete risk band.

    Bands:
    - LOW:      p < 0.15
    - MEDIUM:   0.15 <= p < t*
    - HIGH:     t* <= p < 0.80
    - CRITICAL: p >= 0.80

    Parameters
    ----------
    proba:
        Probability value (float in [0, 1]) or NumPy array of probabilities.
    t_star:
        The selected operational decision threshold (must satisfy 0.15 <= t_star < 0.80).

    Returns
    -------
    str | np.ndarray
        Risk band string (or string array).
    """
    if isinstance(proba, (float, int, np.floating)):
        p = float(proba)
        if p >= 0.80:
            return BAND_CRITICAL
        if p >= t_star:
            return BAND_HIGH
        if p >= 0.15:
            return BAND_MEDIUM
        return BAND_LOW

    # Vectorized for numpy arrays
    p_arr = np.asarray(proba, dtype=float)
    conditions = [
        p_arr >= 0.80,
        p_arr >= t_star,
        p_arr >= 0.15,
    ]
    choices = [BAND_CRITICAL, BAND_HIGH, BAND_MEDIUM]
    return np.select(conditions, choices, default=BAND_LOW)
