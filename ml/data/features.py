"""
ml/data/features.py - EdgeTwin AI shared feature contract.

T-011: Defines the canonical feature selection API consumed by both the
ML training pipeline and the API serving path.

The feature contract separates:
    - Which columns are predictive inputs (FEATURE_COLUMNS)
    - Which column is the prediction target (TARGET_COLUMN)
    - Which columns are absolutely forbidden as model inputs

No feature engineering is performed here.
No imputation is performed here.
No scaling or encoding is performed here.

Those transformations belong inside a fitted sklearn Pipeline
applied only to training data (T-012).

Functions
---------
get_feature_columns()
    Return the ordered list of feature column names.
get_target_column()
    Return the target column name.
get_forbidden_columns()
    Return columns that must never appear as model inputs.
select_features(df)
    Extract feature columns from a DataFrame with validation.
select_target(df)
    Extract the target column from a DataFrame with validation.
validate_no_leakage(df, context)
    Raise ValueError if any forbidden column is present in df.columns.

Author: T-011 / S03
"""

from __future__ import annotations

import pandas as pd

from ml.data.schema import (
    FEATURE_COLUMNS,
    FORBIDDEN_FEATURE_COLUMNS,
    TARGET_COLUMN,
)

# ---------------------------------------------------------------------------
# Public accessors (stable API for downstream tasks)
# ---------------------------------------------------------------------------


def get_feature_columns() -> list[str]:
    """Return the ordered list of feature columns for model input.

    Feature columns: 10 numeric sensor/operating columns + Machine_Type.
    No engineered features are included at this stage.

    Returns
    -------
    list[str]
        A new list (copy) so callers cannot mutate the schema constant.
    """
    return list(FEATURE_COLUMNS)


def get_target_column() -> str:
    """Return the name of the supervised prediction target.

    The target is Machine_Failure (binary: 0 = healthy, 1 = failure).

    Returns
    -------
    str
        ``"Machine_Failure"``
    """
    return TARGET_COLUMN


def get_forbidden_columns() -> list[str]:
    """Return columns that must never appear as ML model inputs.

    Forbidden columns:
        - Failure_Type     : post-outcome label (direct target leakage)
        - Machine_ID       : opaque identifier (identifier leakage)
        - Timestamp        : ordering metadata (ordering leakage)
        - Sensor_Batch_Code: administrative
        - Checksum_Flag    : administrative

    These columns are retained in the prepared dataset for traceability
    but must be excluded at feature-construction time.

    Returns
    -------
    list[str]
        A new list (copy) of forbidden column names.
    """
    return list(FORBIDDEN_FEATURE_COLUMNS)


# ---------------------------------------------------------------------------
# Feature / target extraction
# ---------------------------------------------------------------------------


def select_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract the feature columns from *df*.

    Validates that:
    - All expected feature columns are present in *df*.
    - No forbidden (leakage) columns are present in the selection.

    Parameters
    ----------
    df:
        Prepared DataFrame containing at least the feature columns.

    Returns
    -------
    pd.DataFrame
        A view/copy containing only the feature columns, in the canonical
        order defined by FEATURE_COLUMNS.

    Raises
    ------
    ValueError
        If any required feature column is missing from *df*, or if
        forbidden columns are found in *df* that would be silently
        included by a careless caller.
    """
    validate_no_leakage(df, context="select_features()")
    _assert_columns_present(df, FEATURE_COLUMNS, context="select_features()")
    return df[FEATURE_COLUMNS].copy()


def select_target(df: pd.DataFrame) -> pd.Series:
    """Extract the target column from *df*.

    Parameters
    ----------
    df:
        Prepared DataFrame containing the target column.

    Returns
    -------
    pd.Series
        The Machine_Failure series.

    Raises
    ------
    ValueError
        If the target column is absent from *df*.
    """
    if TARGET_COLUMN not in df.columns:
        raise ValueError(
            f"Target column '{TARGET_COLUMN}' is missing from the DataFrame. "
            f"Available columns: {sorted(df.columns.tolist())}"
        )
    return df[TARGET_COLUMN].copy()


# ---------------------------------------------------------------------------
# Leakage guard
# ---------------------------------------------------------------------------


def validate_no_leakage(df: pd.DataFrame, context: str = "") -> None:
    """Raise ValueError if any forbidden column is present in *df*.

    This is a safety check to prevent accidental inclusion of post-outcome
    labels, identifiers, or administrative columns in model inputs.

    Parameters
    ----------
    df:
        DataFrame to inspect.
    context:
        Optional description of the call site (for clearer error messages).

    Raises
    ------
    ValueError
        If one or more forbidden columns are found in ``df.columns``.
    """
    found = [col for col in FORBIDDEN_FEATURE_COLUMNS if col in df.columns]
    if found:
        prefix = f"[{context}] " if context else ""
        raise ValueError(
            f"{prefix}Leakage guard violation: forbidden column(s) present in "
            f"the DataFrame that would be included as model inputs: {found}. "
            f"Remove these columns before calling feature selection."
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _assert_columns_present(
    df: pd.DataFrame,
    required: list[str],
    context: str = "",
) -> None:
    """Raise ValueError if any required column is absent from *df*."""
    missing = [col for col in required if col not in df.columns]
    if missing:
        prefix = f"[{context}] " if context else ""
        raise ValueError(
            f"{prefix}Required column(s) missing from the DataFrame: {missing}. "
            f"Ensure the prepared dataset has been loaded correctly."
        )
