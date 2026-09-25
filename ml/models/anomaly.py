"""
ml/models/anomaly.py - EdgeTwin AI unsupervised anomaly detection module.

T-014: Unsupervised anomaly detector trained exclusively on healthy training
observations (Machine_Failure == 0).

Model Architecture
------------------
- Model: sklearn IsolationForest
- Preprocessing: SimpleImputer(strategy='median') + OrdinalEncoder on Machine_Type
- Training data: Healthy training rows only (train_df[Machine_Failure == 0])
- Features: 14 +physics features (10 raw sensors + Machine_Type + 3 physics derivations)
- Hyperparameters: n_estimators=150, contamination=0.02, random_state=42

Anomaly Score Contract & Semantics
-----------------------------------
- Raw Isolation Forest score: score_samples() produces values typically in [-0.7, -0.3]
  (where more negative = more anomalous).
- Normalized score: strictly in [0.0, 1.0]
  - 0.0 = completely nominal / healthy
  - 1.0 = highly anomalous
- Normalization parameters derived from healthy training reference scores:
  - s_nominal = 95th percentile of healthy training scores
  - s_extreme = 1st percentile of healthy training scores
  - delta = s_nominal - s_extreme
  - Safeguard: if delta <= 1e-9 or score is NaN, returns 0.5 fallback
  - score = clip((s_nominal - raw_score) / delta, 0.0, 1.0)

Leakage Guards
--------------
- Machine_Failure, Failure_Type, Machine_ID, Timestamp, Sensor_Batch_Code,
  and Checksum_Flag are FORBIDDEN from feature inputs.
- Test set is NEVER used during detector fitting or threshold selection.

Author: T-014 / S05
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

from ml.data.features import validate_no_leakage
from ml.data.schema import CATEGORICAL_COLUMNS

# Default hyperparameters
DEFAULT_CONTAMINATION: float = 0.02
DEFAULT_N_ESTIMATORS: int = 150
DEFAULT_SEED: int = 42
DEFAULT_ANOMALY_THRESHOLD: float = 0.50


def build_anomaly_pipeline(
    feature_cols: list[str],
    *,
    contamination: float = DEFAULT_CONTAMINATION,
    n_estimators: int = DEFAULT_N_ESTIMATORS,
    seed: int = DEFAULT_SEED,
) -> Pipeline:
    """Construct an unfitted anomaly detection Pipeline with preprocessing.

    Parameters
    ----------
    feature_cols:
        List of feature column names.
    contamination:
        Expected proportion of outliers in the data.
    n_estimators:
        Number of trees in IsolationForest.
    seed:
        Random state seed.

    Returns
    -------
    Pipeline
        Unfitted Pipeline with steps ('preprocessor', 'detector').
    """
    validate_no_leakage(pd.DataFrame(columns=feature_cols))

    num_cols = [c for c in feature_cols if c not in CATEGORICAL_COLUMNS]
    cat_cols = [c for c in feature_cols if c in CATEGORICAL_COLUMNS]

    transformers = [
        ("num", SimpleImputer(strategy="median"), num_cols),
    ]
    if cat_cols:
        transformers.append(
            (
                "cat",
                OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1),
                cat_cols,
            )
        )

    preprocessor = ColumnTransformer(transformers=transformers)
    detector = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=seed,
        n_jobs=-1,
    )
    return Pipeline([("preprocessor", preprocessor), ("detector", detector)])


def fit_anomaly_detector(
    train_df: pd.DataFrame,
    feature_cols: list[str],
    *,
    target_col: str = "Machine_Failure",
    contamination: float = DEFAULT_CONTAMINATION,
    n_estimators: int = DEFAULT_N_ESTIMATORS,
    seed: int = DEFAULT_SEED,
) -> tuple[Pipeline, dict[str, float]]:
    """Fit IsolationForest on healthy training rows only and compute reference calibration.

    Parameters
    ----------
    train_df:
        Training DataFrame containing feature_cols and target_col.
    feature_cols:
        Feature columns to train on (must not contain forbidden columns).
    target_col:
        Supervised failure column used ONLY to filter healthy rows (Machine_Failure == 0).
    contamination:
        IsolationForest contamination parameter.
    n_estimators:
        Number of trees.
    seed:
        Random seed.

    Returns
    -------
    tuple[Pipeline, dict[str, float]]
        Fitted Pipeline and reference normalization dictionary.
    """
    # 1. Filter healthy rows only
    if target_col not in train_df.columns:
        raise ValueError(f"target_col '{target_col}' not found in train_df")

    healthy_mask = train_df[target_col] == 0
    healthy_train = train_df.loc[healthy_mask]

    # 2. Extract feature matrix and validate leakage
    X_train = healthy_train[feature_cols]
    validate_no_leakage(X_train)

    # 3. Build and fit pipeline
    pipeline = build_anomaly_pipeline(
        feature_cols,
        contamination=contamination,
        n_estimators=n_estimators,
        seed=seed,
    )
    pipeline.fit(X_train)

    # 4. Compute reference percentiles on healthy training data
    # Transform through preprocessor first to get exact features passed to detector
    preprocessor = pipeline.named_steps["preprocessor"]
    detector = pipeline.named_steps["detector"]
    X_trans = preprocessor.transform(X_train)
    raw_scores = detector.score_samples(X_trans)

    s_nominal = float(np.percentile(raw_scores, 95))
    s_extreme = float(np.percentile(raw_scores, 1))
    delta = float(s_nominal - s_extreme)

    ref_params = {
        "s_nominal": s_nominal,
        "s_extreme": s_extreme,
        "delta": delta,
        "contamination": contamination,
        "n_healthy_train": float(len(healthy_train)),
    }
    return pipeline, ref_params


def predict_anomaly_score(
    pipeline: Pipeline,
    ref_params: dict[str, float],
    X: pd.DataFrame,
) -> np.ndarray:
    """Compute normalized anomaly scores in [0.0, 1.0].

    Semantics:
    - 0.0 = completely nominal / healthy
    - 1.0 = highly anomalous

    Guards:
    - Zero denominator / constant scores -> 0.5 fallback
    - NaN values in input or output -> 0.5 fallback
    - Bounded explicitly with np.clip(..., 0.0, 1.0)

    Parameters
    ----------
    pipeline:
        Fitted anomaly Pipeline.
    ref_params:
        Reference parameters dictionary from fit_anomaly_detector().
    X:
        Feature DataFrame. Forbidden columns will raise an error.

    Returns
    -------
    np.ndarray
        Array of normalized anomaly scores in [0.0, 1.0].
    """
    validate_no_leakage(X)

    s_nominal = ref_params.get("s_nominal", 0.0)
    delta = ref_params.get("delta", 0.0)

    # Guard: degenerate reference distribution
    if delta <= 1e-9 or np.isnan(delta):
        return np.full(len(X), 0.5, dtype=float)

    preprocessor = pipeline.named_steps["preprocessor"]
    detector = pipeline.named_steps["detector"]

    X_trans = preprocessor.transform(X)
    raw_scores = detector.score_samples(X_trans)

    # Transform raw score so that higher raw score (more normal) -> 0, lower raw score -> 1
    # raw_scores typically in [-0.7, -0.3]
    normalized = (s_nominal - raw_scores) / delta

    # Guard against NaN / inf in output
    normalized = np.nan_to_num(normalized, nan=0.5, posinf=1.0, neginf=0.0)
    return np.clip(normalized, 0.0, 1.0)


def evaluate_anomaly_detector(
    pipeline: Pipeline,
    ref_params: dict[str, float],
    val_df: pd.DataFrame,
    feature_cols: list[str],
    *,
    target_col: str = "Machine_Failure",
    provisional_threshold: float = DEFAULT_ANOMALY_THRESHOLD,
) -> dict[str, Any]:
    """Evaluate anomaly detector on validation data and compute empirical threshold.

    Parameters
    ----------
    pipeline:
        Fitted anomaly pipeline.
    ref_params:
        Reference parameters from fit_anomaly_detector().
    val_df:
        Validation DataFrame containing feature_cols and target_col.
    feature_cols:
        Feature column names.
    target_col:
        Target column for discrimination evaluation.
    provisional_threshold:
        Default operational threshold (default: 0.50).

    Returns
    -------
    dict[str, Any]
        Metrics, empirical threshold, and detection rates.
    """
    X_val = val_df[feature_cols]
    validate_no_leakage(X_val)

    y_val = np.asarray(val_df[target_col], dtype=int)
    scores = predict_anomaly_score(pipeline, ref_params, X_val)

    # 1. Discrimination metrics against ground-truth failure
    roc_auc = float(roc_auc_score(y_val, scores))
    pr_auc = float(average_precision_score(y_val, scores))

    # 2. Empirical threshold on healthy validation observations
    # At alpha = contamination (e.g. 0.02), find the 98th percentile of healthy validation scores
    contamination = ref_params.get("contamination", DEFAULT_CONTAMINATION)
    healthy_val_scores = scores[y_val == 0]

    empirical_percentile = 100.0 * (1.0 - contamination)
    empirical_threshold = float(np.percentile(healthy_val_scores, empirical_percentile))

    # 3. Detection rates at both thresholds
    def _metrics_at_t(t: float) -> dict[str, float]:
        preds = (scores >= t).astype(int)
        tp = int(np.sum((preds == 1) & (y_val == 1)))
        fp = int(np.sum((preds == 1) & (y_val == 0)))
        fn = int(np.sum((preds == 0) & (y_val == 1)))
        rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        fpr = float(fp / len(healthy_val_scores)) if len(healthy_val_scores) > 0 else 0.0
        return {
            "threshold": t,
            "recall": rec,
            "precision": prec,
            "false_positive_rate": fpr,
        }

    provisional_metrics = _metrics_at_t(provisional_threshold)
    empirical_metrics = _metrics_at_t(empirical_threshold)

    return {
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "provisional_threshold": provisional_threshold,
        "provisional_metrics": provisional_metrics,
        "empirical_threshold": empirical_threshold,
        "empirical_metrics": empirical_metrics,
        "ref_params": ref_params,
    }
