"""
ml/models/evaluate.py - EdgeTwin AI model evaluation utilities.

T-012: Compute classification metrics for binary failure prediction.

Metrics reported
----------------
- accuracy
- precision        (positive class; zero_division=0)
- recall           (positive class; zero_division=0)
- f1               (positive class; zero_division=0)
- roc_auc          (area under ROC curve)
- pr_auc           (average precision = area under PR curve)
- confusion_matrix (2x2 as nested list for JSON serialisability)

All metrics are computed on the positive class (Machine_Failure == 1)
which is the minority class at ~10.97%.

Per-failure-type recall
-----------------------
per_failure_type_recall() uses the Failure_Type column (present in the
prepared dataset but NOT a model feature) to compute recall separately
for each failure mode.  This is a post-hoc diagnostic, not a training
objective.

Tool Wear Failure is expected to be the hardest class based on the S02
data audit (172 occurrences, the smallest failure sub-type).

Author: T-012 / S04
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

# ---------------------------------------------------------------------------
# Core metric computation
# ---------------------------------------------------------------------------


def compute_metrics(
    y_true: pd.Series | np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray,
) -> dict[str, float]:
    """Compute all T-012 binary classification metrics.

    Parameters
    ----------
    y_true:
        Ground-truth binary labels (0/1).
    y_pred:
        Predicted binary labels (0/1).
    y_proba:
        Predicted probabilities for the positive class.

    Returns
    -------
    dict[str, float]
        Keys: accuracy, precision, recall, f1, roc_auc, pr_auc.
        All values are floats in [0, 1].
    """
    y_true_arr = np.asarray(y_true)
    return {
        "accuracy": float(accuracy_score(y_true_arr, y_pred)),
        "precision": float(precision_score(y_true_arr, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true_arr, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true_arr, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true_arr, y_proba)),
        "pr_auc": float(average_precision_score(y_true_arr, y_proba)),
    }


def compute_confusion_matrix(
    y_true: pd.Series | np.ndarray,
    y_pred: np.ndarray,
) -> list[list[int]]:
    """Return confusion matrix as a JSON-serialisable nested list.

    Layout: [[TN, FP], [FN, TP]]

    Parameters
    ----------
    y_true:
        Ground-truth binary labels.
    y_pred:
        Predicted binary labels.

    Returns
    -------
    list[list[int]]
        2x2 confusion matrix.
    """
    cm = confusion_matrix(np.asarray(y_true), y_pred, labels=[0, 1])
    return cm.tolist()


# ---------------------------------------------------------------------------
# Per-failure-type recall
# ---------------------------------------------------------------------------


def per_failure_type_recall(
    y_true: pd.Series | np.ndarray,
    y_pred: np.ndarray,
    failure_types: pd.Series,
) -> dict[str, dict[str, Any]]:
    """Compute recall per Failure_Type sub-class.

    This is a post-hoc diagnostic.  Failure_Type is NOT a model feature;
    it is used here only to analyse where failures are missed.

    Parameters
    ----------
    y_true:
        Ground-truth binary Machine_Failure labels (0/1).
    y_pred:
        Predicted binary labels.
    failure_types:
        Failure_Type string column from the prepared dataset.
        Must be aligned (same index) as y_true and y_pred.

    Returns
    -------
    dict[str, dict]
        Keys are Failure_Type strings; values are dicts with:
        - count: total rows with that failure type
        - failures: rows where Machine_Failure == 1
        - detected: TP for that failure type
        - recall: float in [0, 1] (0 if no positive labels)
    """
    y_true_arr = np.asarray(y_true)
    y_pred_arr = np.asarray(y_pred)
    result: dict[str, dict[str, Any]] = {}

    for ft in sorted(failure_types.unique()):
        mask = (failure_types == ft).values
        yt = y_true_arr[mask]
        yp = y_pred_arr[mask]
        total = int(mask.sum())
        n_failures = int(yt.sum())
        detected = int(((yt == 1) & (yp == 1)).sum())
        rec = float(detected / n_failures) if n_failures > 0 else 0.0
        result[ft] = {
            "count": total,
            "failures": n_failures,
            "detected": detected,
            "recall": rec,
        }

    return result


# ---------------------------------------------------------------------------
# Confusion matrix artifact helpers
# ---------------------------------------------------------------------------


def confusion_matrix_to_dict(cm: list[list[int]]) -> dict[str, int]:
    """Flatten a 2×2 confusion matrix to a labelled dict.

    Parameters
    ----------
    cm:
        [[TN, FP], [FN, TP]] from compute_confusion_matrix().

    Returns
    -------
    dict
        Keys: tn, fp, fn, tp.
    """
    return {
        "tn": cm[0][0],
        "fp": cm[0][1],
        "fn": cm[1][0],
        "tp": cm[1][1],
    }


def save_confusion_matrix_png(
    cm: list[list[int]],
    output_path: str,
    title: str = "Confusion Matrix",
) -> None:
    """Save a heatmap of the confusion matrix to *output_path*.

    Parameters
    ----------
    cm:
        [[TN, FP], [FN, TP]].
    output_path:
        Absolute path to write the PNG to.
    title:
        Plot title.
    """
    import matplotlib
    import matplotlib.pyplot as plt

    matplotlib.use("Agg")  # non-interactive backend

    fig, ax = plt.subplots(figsize=(4, 3))
    arr = [[cm[0][0], cm[0][1]], [cm[1][0], cm[1][1]]]
    im = ax.imshow(arr, interpolation="nearest", cmap="Blues")
    fig.colorbar(im, ax=ax)

    labels = ["No Failure (0)", "Failure (1)"]
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=8)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Predicted", fontsize=9)
    ax.set_ylabel("Actual", fontsize=9)
    ax.set_title(title, fontsize=10)

    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(arr[i][j]), ha="center", va="center", fontsize=11)

    fig.tight_layout()
    fig.savefig(output_path, dpi=100)
    plt.close(fig)
