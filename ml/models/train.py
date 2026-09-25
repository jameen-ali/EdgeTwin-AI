"""
ml/models/train.py - EdgeTwin AI model pipeline construction and training.

T-012: Builds sklearn Pipelines for each candidate model with correct
preprocessing for the feature set.

Preprocessing rules
-------------------
- SimpleImputer(strategy='median') on all numeric features.
  HistGradientBoostingClassifier and XGBClassifier handle NaN natively, but
  they are still wrapped in a uniform Pipeline for API consistency.
- OrdinalEncoder on Machine_Type with handle_unknown='use_encoded_value'
  so unseen categories at inference time produce -1 (not an error).
- StandardScaler applied ONLY to Logistic Regression (numeric features).
- class_weight='balanced' for LR, DT, RF (native sklearn support).
  XGBoost uses scale_pos_weight. HistGBT uses class_weight='balanced'.
- All Pipeline steps are fitted ONLY on training data.

Candidate models
----------------
- logistic_regression
- decision_tree
- random_forest
- hist_gradient_boosting
- xgboost

Feature sets (from ml/data/engineering.py)
------------------------------------------
- base10      : 11 cols (10 numeric sensors + Machine_Type)
- +physics    : 14 cols (base10 + Delta_T_C + Apparent_Power_VA + Mech_Power_W)
- +wear_rate  : 15 cols (  +physics + Wear_Rate)

Author: T-012 / S04
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

from ml.data.engineering import apply_feature_set, get_feature_cols_for_set
from ml.data.features import (
    get_feature_columns,
    get_target_column,
    validate_no_leakage,
)
from ml.data.schema import CATEGORICAL_COLUMNS

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SEED: int = 42
TARGET: str = get_target_column()
BASE_FEATURE_COLS: list[str] = get_feature_columns()

#: All candidate model names supported by this module.
CANDIDATE_MODELS: tuple[str, ...] = (
    "logistic_regression",
    "decision_tree",
    "random_forest",
    "hist_gradient_boosting",
    "xgboost",
)


# ---------------------------------------------------------------------------
# Preprocessing helpers
# ---------------------------------------------------------------------------


def _numeric_cols(feature_cols: list[str]) -> list[str]:
    """Return numeric feature columns (all features except Machine_Type)."""
    return [c for c in feature_cols if c not in CATEGORICAL_COLUMNS]


def _build_numeric_transformer(*, scale: bool) -> Pipeline:
    """Build the numeric preprocessing sub-pipeline.

    Parameters
    ----------
    scale:
        If True, appends StandardScaler after imputation.
    """
    steps: list[tuple[str, Any]] = [
        ("imputer", SimpleImputer(strategy="median")),
    ]
    if scale:
        steps.append(("scaler", StandardScaler()))
    return Pipeline(steps)


def _build_preprocessor(feature_cols: list[str], *, scale: bool) -> ColumnTransformer:
    """Build a ColumnTransformer for the given feature column list.

    Parameters
    ----------
    feature_cols:
        Ordered list of all feature columns for this run.
    scale:
        Whether to apply StandardScaler to numeric columns.

    Returns
    -------
    ColumnTransformer
        Remainder='drop' so any unexpected columns are discarded.
    """
    num_cols = _numeric_cols(feature_cols)
    cat_cols = [c for c in CATEGORICAL_COLUMNS if c in feature_cols]

    transformers: list[tuple[str, Any, list[str]]] = [
        ("num", _build_numeric_transformer(scale=scale), num_cols),
    ]
    if cat_cols:
        cat_transformer = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="most_frequent")),
                (
                    "encoder",
                    OrdinalEncoder(
                        handle_unknown="use_encoded_value",
                        unknown_value=-1,
                    ),
                ),
            ]
        )
        transformers.append(("cat", cat_transformer, cat_cols))

    return ColumnTransformer(transformers=transformers, remainder="drop")


# ---------------------------------------------------------------------------
# Pipeline builders per model
# ---------------------------------------------------------------------------


def build_pipeline(
    model_name: str,
    feature_cols: list[str],
    *,
    class_weight: str | None = "balanced",
    seed: int = SEED,
) -> Pipeline:
    """Build a ready-to-fit sklearn Pipeline for *model_name*.

    The pipeline is:
        preprocessor (ColumnTransformer) -> classifier

    Parameters
    ----------
    model_name:
        One of the CANDIDATE_MODELS identifiers.
    feature_cols:
        Ordered list of feature columns for this pipeline.
        Must not contain any forbidden columns.
    class_weight:
        Class weighting strategy.  ``'balanced'`` is default.
        Pass ``None`` to disable.
    seed:
        Random state for all stochastic components.

    Returns
    -------
    sklearn.pipeline.Pipeline
        Unfitted pipeline ready for ``.fit(X_train, y_train)``.

    Raises
    ------
    ValueError
        If *model_name* is not in CANDIDATE_MODELS.
    """
    if model_name not in CANDIDATE_MODELS:
        raise ValueError(f"Unknown model '{model_name}'. Valid options: {CANDIDATE_MODELS}")

    if model_name == "logistic_regression":
        preprocessor = _build_preprocessor(feature_cols, scale=True)
        clf = LogisticRegression(
            class_weight=class_weight,
            max_iter=2000,
            solver="lbfgs",
            random_state=seed,
        )

    elif model_name == "decision_tree":
        preprocessor = _build_preprocessor(feature_cols, scale=False)
        clf = DecisionTreeClassifier(
            class_weight=class_weight,
            random_state=seed,
        )

    elif model_name == "random_forest":
        preprocessor = _build_preprocessor(feature_cols, scale=False)
        clf = RandomForestClassifier(
            n_estimators=200,
            class_weight=class_weight,
            random_state=seed,
            n_jobs=-1,
        )

    elif model_name == "hist_gradient_boosting":
        # HGBT handles NaN natively; still use the preprocessor for
        # categorical encoding consistency.
        preprocessor = _build_preprocessor(feature_cols, scale=False)
        clf = HistGradientBoostingClassifier(
            class_weight=class_weight,
            random_state=seed,
            max_iter=300,
            learning_rate=0.05,
            max_leaf_nodes=31,
            l2_regularization=1.0,
        )

    else:  # xgboost
        preprocessor = _build_preprocessor(feature_cols, scale=False)
        # XGBoost handles NaN natively.
        # Compute scale_pos_weight from class_weight='balanced' logic:
        # will be set dynamically at fit time via the wrapper below.
        clf = XGBClassifier(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=6,
            min_child_weight=5,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="logloss",
            random_state=seed,
            # scale_pos_weight set in train_model() for the actual ratio
        )

    return Pipeline([("preprocessor", preprocessor), ("classifier", clf)])


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def train_model(
    pipeline: Pipeline,
    X_train: pd.DataFrame,
    y_train: pd.Series,
) -> Pipeline:
    """Fit *pipeline* on (X_train, y_train).

    For XGBClassifier, scale_pos_weight is computed from the actual training
    label distribution before fitting.

    Parameters
    ----------
    pipeline:
        Unfitted sklearn Pipeline from build_pipeline().
    X_train:
        Training feature DataFrame.
    y_train:
        Training target Series (binary 0/1).

    Returns
    -------
    Pipeline
        Fitted pipeline.
    """
    clf = pipeline.named_steps["classifier"]
    if isinstance(clf, XGBClassifier):
        neg = int((y_train == 0).sum())
        pos = int((y_train == 1).sum())
        if pos > 0:
            clf.set_params(scale_pos_weight=neg / pos)

    pipeline.fit(X_train, y_train)
    return pipeline


# ---------------------------------------------------------------------------
# Cross-validation run
# ---------------------------------------------------------------------------


def cross_val_run(
    model_name: str,
    feature_set: str,
    X_full: pd.DataFrame,
    y_full: pd.Series,
    *,
    n_splits: int = 5,
    seed: int = SEED,
) -> dict[str, Any]:
    """Run stratified k-fold cross-validation on *X_full* / *y_full*.

    The *full* data passed in must be the train partition only (not val or
    test).  The function returns mean ± std for each metric.

    Parameters
    ----------
    model_name:
        Candidate model identifier.
    feature_set:
        Feature-set identifier for engineering.
    X_full:
        Training partition DataFrame (all 17 columns OK; forbidden cols
        will raise if present as feature cols).
    y_full:
        Training partition target Series.
    n_splits:
        Number of stratified folds.
    seed:
        Random seed.

    Returns
    -------
    dict
        Keys: model_name, feature_set, fold_metrics (list of dicts),
        plus mean_<metric> and std_<metric> for each metric.
    """
    from sklearn.model_selection import StratifiedKFold

    from ml.models.evaluate import compute_metrics

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    feature_cols = get_feature_cols_for_set(BASE_FEATURE_COLS, feature_set)

    fold_metrics: list[dict[str, float]] = []

    for fold_idx, (train_idx, val_idx) in enumerate(skf.split(X_full, y_full)):
        X_tr = X_full.iloc[train_idx].reset_index(drop=True)
        X_va = X_full.iloc[val_idx].reset_index(drop=True)
        y_tr = y_full.iloc[train_idx].reset_index(drop=True)
        y_va = y_full.iloc[val_idx].reset_index(drop=True)

        # Apply feature engineering AFTER split (no leakage)
        X_tr_eng = apply_feature_set(X_tr, feature_set)[feature_cols]
        X_va_eng = apply_feature_set(X_va, feature_set)[feature_cols]

        pipe = build_pipeline(model_name, feature_cols, seed=seed)
        pipe = train_model(pipe, X_tr_eng, y_tr)

        y_proba = pipe.predict_proba(X_va_eng)[:, 1]
        y_pred = pipe.predict(X_va_eng)

        metrics = compute_metrics(y_va, y_pred, y_proba)
        metrics["fold"] = fold_idx
        fold_metrics.append(metrics)

    # Aggregate
    metric_keys = [k for k in fold_metrics[0] if k != "fold"]
    result: dict[str, Any] = {
        "model_name": model_name,
        "feature_set": feature_set,
        "fold_metrics": fold_metrics,
    }
    for key in metric_keys:
        vals = np.array([fm[key] for fm in fold_metrics])
        result[f"mean_{key}"] = float(vals.mean())
        result[f"std_{key}"] = float(vals.std())

    return result


# ---------------------------------------------------------------------------
# Leakage guard for feature columns
# ---------------------------------------------------------------------------


def assert_no_forbidden_features(feature_cols: list[str]) -> None:
    """Raise ValueError if any forbidden column is in *feature_cols*.

    Uses the shared leakage guard from ml/data/features.py.
    Constructs a minimal DataFrame with those columns to trigger the guard.

    Parameters
    ----------
    feature_cols:
        List of column names to check.

    Raises
    ------
    ValueError
        If any FORBIDDEN_FEATURE_COLUMNS member is in *feature_cols*.
    """
    dummy = pd.DataFrame(columns=feature_cols)
    validate_no_leakage(dummy, context="T-012 feature column check")
