"""
ml/models/calibrate.py - EdgeTwin AI probability calibration module.

T-013: Fits and evaluates probability calibration models for the frozen
S04 XGBoost champion model.

Supported Methods
-----------------
1. Uncalibrated baseline: raw model probabilities
2. Sigmoid (Platt) calibration: logistic regression on model logits/probabilities
3. Isotonic calibration: non-parametric piece-wise constant monotonic mapping

Protocol & Leakage Guards
-------------------------
- Base model is trained strictly on train_df.
- Calibration models are fitted on val_df using FrozenEstimator(pipeline).
- test_df is NEVER accessed during calibration fitting or method selection.
- All input feature matrices are validated against FORBIDDEN_FEATURE_COLUMNS.

Author: T-013 / S05
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline

from ml.data.features import validate_no_leakage

# Supported calibration methods
CALIBRATION_METHODS: tuple[str, ...] = ("sigmoid", "isotonic")


def compute_calibration_metrics(
    y_true: pd.Series | np.ndarray,
    y_proba: np.ndarray,
    n_bins: int = 10,
) -> dict[str, float]:
    """Compute calibration metrics: Brier score, ECE, ROC-AUC, and PR-AUC.

    Parameters
    ----------
    y_true:
        Ground truth binary labels (0/1).
    y_proba:
        Predicted probabilities for positive class (Machine_Failure == 1).
    n_bins:
        Number of bins for Expected Calibration Error (ECE) calculation.

    Returns
    -------
    dict[str, float]
        Keys: brier_score, ece, roc_auc, pr_auc.
    """
    y_true_arr = np.asarray(y_true, dtype=int)
    y_proba_arr = np.asarray(y_proba, dtype=float)

    # 1. Brier score
    brier = float(brier_score_loss(y_true_arr, y_proba_arr))

    # 2. Expected Calibration Error (ECE)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n_total = len(y_true_arr)

    for i in range(n_bins):
        low, high = bins[i], bins[i + 1]
        # In upper bin, include right edge
        if i == n_bins - 1:
            mask = (y_proba_arr >= low) & (y_proba_arr <= high)
        else:
            mask = (y_proba_arr >= low) & (y_proba_arr < high)

        bin_count = int(np.sum(mask))
        if bin_count > 0:
            bin_acc = float(np.mean(y_true_arr[mask]))
            bin_conf = float(np.mean(y_proba_arr[mask]))
            ece += (bin_count / n_total) * abs(bin_acc - bin_conf)

    # 3. Discrimination metrics
    roc_auc = float(roc_auc_score(y_true_arr, y_proba_arr))
    pr_auc = float(average_precision_score(y_true_arr, y_proba_arr))

    return {
        "brier_score": brier,
        "ece": float(ece),
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
    }


def get_calibration_curve_data(
    y_true: pd.Series | np.ndarray,
    y_proba: np.ndarray,
    n_bins: int = 10,
) -> dict[str, list[float]]:
    """Compute empirical calibration curve coordinates.

    Parameters
    ----------
    y_true:
        Ground truth binary labels.
    y_proba:
        Predicted positive-class probabilities.
    n_bins:
        Number of quantile/uniform bins.

    Returns
    -------
    dict[str, list[float]]
        Dict with keys "prob_true" and "prob_pred".
    """
    y_true_arr = np.asarray(y_true, dtype=int)
    y_proba_arr = np.asarray(y_proba, dtype=float)

    prob_true, prob_pred = calibration_curve(
        y_true_arr,
        y_proba_arr,
        n_bins=n_bins,
        strategy="uniform",
    )
    return {
        "prob_true": [float(v) for v in prob_true],
        "prob_pred": [float(v) for v in prob_pred],
    }


def fit_calibrator(
    pipeline: Pipeline,
    X_val: pd.DataFrame,
    y_val: pd.Series | np.ndarray,
    method: str = "sigmoid",
) -> CalibratedClassifierCV:
    """Fit a post-hoc probability calibrator on validation data using FrozenEstimator.

    Parameters
    ----------
    pipeline:
        Pre-fitted scikit-learn Pipeline (base champion model).
    X_val:
        Validation feature DataFrame. Forbidden columns will raise an error.
    y_val:
        Validation target Series.
    method:
        Calibration method: "sigmoid" (Platt scaling) or "isotonic".

    Returns
    -------
    CalibratedClassifierCV
        Fitted calibrator instance.

    Raises
    ------
    ValueError
        If method is invalid or forbidden columns are present in X_val.
    """
    if method not in CALIBRATION_METHODS:
        raise ValueError(
            f"Unknown calibration method '{method}'. Valid options: {CALIBRATION_METHODS}"
        )

    validate_no_leakage(X_val)

    # Wrap the pre-fitted pipeline in FrozenEstimator to prevent retraining base model
    frozen_model = FrozenEstimator(pipeline)
    calibrator = CalibratedClassifierCV(frozen_model, method=method)
    calibrator.fit(X_val, y_val)
    return calibrator


def predict_calibrated_proba(
    calibrator: CalibratedClassifierCV | Pipeline,
    X: pd.DataFrame,
) -> np.ndarray:
    """Predict positive-class probabilities using fitted pipeline or calibrator.

    Parameters
    ----------
    calibrator:
        Fitted CalibratedClassifierCV or Pipeline instance.
    X:
        Feature DataFrame. Forbidden columns will raise an error.

    Returns
    -------
    np.ndarray
        1D array of probabilities in [0.0, 1.0].
    """
    validate_no_leakage(X)
    proba = calibrator.predict_proba(X)[:, 1]
    # Bound explicitly to [0.0, 1.0] to guard against floating-point anomalies
    return np.clip(np.asarray(proba, dtype=float), 0.0, 1.0)


def compare_calibration_methods(
    pipeline: Pipeline,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    feature_cols: list[str],
) -> dict[str, Any]:
    """Compare uncalibrated, sigmoid, and isotonic calibration on validation data.

    Parameters
    ----------
    pipeline:
        Fitted base champion pipeline.
    X_val:
        Validation DataFrame containing feature_cols.
    y_val:
        Validation target Series.
    feature_cols:
        List of feature column names.

    Returns
    -------
    dict[str, Any]
        Dictionary of results per method, curves, and selected production method.
    """
    validate_no_leakage(X_val[feature_cols])

    # 1. Uncalibrated baseline
    p_uncal = predict_calibrated_proba(pipeline, X_val[feature_cols])
    metrics_uncal = compute_calibration_metrics(y_val, p_uncal)
    curve_uncal = get_calibration_curve_data(y_val, p_uncal)

    # 2. Sigmoid calibration
    cal_sig = fit_calibrator(pipeline, X_val[feature_cols], y_val, method="sigmoid")
    p_sig = predict_calibrated_proba(cal_sig, X_val[feature_cols])
    metrics_sig = compute_calibration_metrics(y_val, p_sig)
    curve_sig = get_calibration_curve_data(y_val, p_sig)

    # 3. Isotonic calibration
    cal_iso = fit_calibrator(pipeline, X_val[feature_cols], y_val, method="isotonic")
    p_iso = predict_calibrated_proba(cal_iso, X_val[feature_cols])
    metrics_iso = compute_calibration_metrics(y_val, p_iso)
    curve_iso = get_calibration_curve_data(y_val, p_iso)

    results = {
        "uncalibrated": {
            "metrics": metrics_uncal,
            "curve": curve_uncal,
            "probabilities": p_uncal,
        },
        "sigmoid": {
            "metrics": metrics_sig,
            "curve": curve_sig,
            "probabilities": p_sig,
            "calibrator": cal_sig,
        },
        "isotonic": {
            "metrics": metrics_iso,
            "curve": curve_iso,
            "probabilities": p_iso,
            "calibrator": cal_iso,
        },
    }

    # Selection logic:
    # 1. Sigmoid is evaluated first: requires >= 2% Brier improvement without PR-AUC degradation.
    # 2. Isotonic is non-parametric and prone to step-function binning artifacts on smaller validation
    #    sets (133 events). Per approved design, sigmoid is preferred unless isotonic materially beats
    #    sigmoid (>= 20% further Brier reduction) AND does not degrade PR-AUC ranking.
    brier_base = metrics_uncal["brier_score"]
    brier_sig = metrics_sig["brier_score"]
    brier_iso = metrics_iso["brier_score"]

    selected_method = "uncalibrated"
    best_brier = brier_base

    # Check sigmoid
    if brier_sig <= brier_base * 0.98 and metrics_sig["pr_auc"] >= metrics_uncal["pr_auc"] - 0.005:
        selected_method = "sigmoid"
        best_brier = brier_sig

    # Check isotonic (requires materially beating sigmoid by >= 20% AND preserving PR-AUC)
    if brier_iso <= best_brier * 0.80 and metrics_iso["pr_auc"] >= metrics_uncal["pr_auc"]:
        selected_method = "isotonic"
        best_brier = brier_iso

    results["selected_method"] = selected_method
    return results
