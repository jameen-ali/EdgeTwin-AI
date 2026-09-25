"""
tests/ml/test_features.py - Unit tests for the T-011 shared feature contract.

Tests:
    F1  test_get_feature_columns_returns_list
    F2  test_feature_columns_count
    F3  test_feature_columns_include_numeric_sensors
    F4  test_feature_columns_include_machine_type
    F5  test_feature_columns_exclude_forbidden
    F6  test_feature_columns_exclude_target
    F7  test_get_target_column
    F8  test_get_forbidden_columns_returns_all_five
    F9  test_select_features_returns_correct_columns
    F10 test_select_features_raises_on_missing_column
    F11 test_select_features_raises_on_leakage_column_in_df
    F12 test_select_target_returns_series
    F13 test_select_target_raises_on_missing_target
    F14 test_validate_no_leakage_raises_for_forbidden_col
    F15 test_validate_no_leakage_passes_for_clean_df
    F16 test_select_features_returns_copy_not_view
    F17 test_get_feature_columns_returns_new_list
    F18 test_regression_on_prepared_dataset
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ml.data.features import (
    get_feature_columns,
    get_forbidden_columns,
    get_target_column,
    select_features,
    select_target,
    validate_no_leakage,
)
from ml.data.schema import (
    CATEGORICAL_COLUMNS,
    FEATURE_COLUMNS,
    FORBIDDEN_FEATURE_COLUMNS,
    NUMERIC_SENSOR_COLUMNS,
    TARGET_COLUMN,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PREPARED_PATH = _REPO_ROOT / "data" / "interim" / "predictive_maintenance_prepared.csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_clean_df(n: int = 3) -> pd.DataFrame:
    """Build a minimal clean DataFrame with all feature and target columns."""
    base = {
        "Machine_ID": [f"CMP-100{i}" for i in range(n)],
        "Timestamp": ["2024-01-01"] * n,
        "Machine_Type": ["Compressor"] * n,
        "Air_Temperature_C": [25.0] * n,
        "Process_Temperature_C": [35.0] * n,
        "Rotational_Speed_RPM": [1500.0] * n,
        "Torque_Nm": [40.0] * n,
        "Vibration_mm_s": [2.5] * n,
        "Pressure_bar": [5.5] * n,
        "Current_A": [12.0] * n,
        "Voltage_V": [415.0] * n,
        "Tool_Wear_Min": [130.0] * n,
        "Operating_Hours": [10000.0] * n,
        "Failure_Type": ["No Failure"] * n,
        "Machine_Failure": [0] * n,
        "Sensor_Batch_Code": ["SB001"] * n,
        "Checksum_Flag": ["OK"] * n,
    }
    return pd.DataFrame(base)


def _make_feature_only_df(n: int = 3) -> pd.DataFrame:
    """Build a DataFrame containing ONLY the feature columns (no forbidden/target)."""
    df = _make_clean_df(n)
    return df[FEATURE_COLUMNS].copy()


# ---------------------------------------------------------------------------
# F1 — get_feature_columns returns list
# ---------------------------------------------------------------------------


class TestGetFeatureColumns:
    """F1-F4: Basic contract of get_feature_columns()."""

    def test_returns_list(self) -> None:
        result = get_feature_columns()
        assert isinstance(result, list)

    def test_feature_columns_count(self) -> None:
        """11 feature columns: 10 numeric sensors + Machine_Type."""
        cols = get_feature_columns()
        assert len(cols) == 11, f"Expected 11 feature columns, got {len(cols)}: {cols}"

    def test_includes_all_numeric_sensors(self) -> None:
        cols = get_feature_columns()
        for sensor in NUMERIC_SENSOR_COLUMNS:
            assert sensor in cols, f"Numeric sensor '{sensor}' missing from feature columns"

    def test_includes_machine_type(self) -> None:
        cols = get_feature_columns()
        for cat_col in CATEGORICAL_COLUMNS:
            assert cat_col in cols, f"Categorical column '{cat_col}' missing from feature columns"

    def test_feature_columns_exclude_all_forbidden(self) -> None:
        """F5: No forbidden column must appear in the feature list."""
        cols = set(get_feature_columns())
        for forbidden in FORBIDDEN_FEATURE_COLUMNS:
            assert forbidden not in cols, f"Forbidden column '{forbidden}' found in FEATURE_COLUMNS"

    def test_feature_columns_exclude_target(self) -> None:
        """F6: Target column must not appear in the feature list."""
        assert TARGET_COLUMN not in get_feature_columns()

    def test_returns_new_list_not_mutation(self) -> None:
        """F17: Mutating the returned list must not affect the schema constant."""
        cols1 = get_feature_columns()
        cols1.append("HACKED")
        cols2 = get_feature_columns()
        assert "HACKED" not in cols2, "get_feature_columns() returned the original list"


# ---------------------------------------------------------------------------
# F7 — get_target_column
# ---------------------------------------------------------------------------


class TestGetTargetColumn:
    """F7: Target column accessor."""

    def test_returns_machine_failure(self) -> None:
        assert get_target_column() == "Machine_Failure"

    def test_returns_string(self) -> None:
        assert isinstance(get_target_column(), str)


# ---------------------------------------------------------------------------
# F8 — get_forbidden_columns
# ---------------------------------------------------------------------------


class TestGetForbiddenColumns:
    """F8: Forbidden columns accessor."""

    def test_returns_all_five(self) -> None:
        forbidden = get_forbidden_columns()
        assert len(forbidden) == 5, f"Expected 5 forbidden columns, got {len(forbidden)}"

    def test_contains_failure_type(self) -> None:
        assert "Failure_Type" in get_forbidden_columns()

    def test_contains_machine_id(self) -> None:
        assert "Machine_ID" in get_forbidden_columns()

    def test_contains_timestamp(self) -> None:
        assert "Timestamp" in get_forbidden_columns()

    def test_contains_sensor_batch_code(self) -> None:
        assert "Sensor_Batch_Code" in get_forbidden_columns()

    def test_contains_checksum_flag(self) -> None:
        assert "Checksum_Flag" in get_forbidden_columns()

    def test_returns_new_list(self) -> None:
        forbidden1 = get_forbidden_columns()
        forbidden1.append("HACKED")
        assert "HACKED" not in get_forbidden_columns()


# ---------------------------------------------------------------------------
# F9-F11 — select_features
# ---------------------------------------------------------------------------


class TestSelectFeatures:
    """F9-F11, F16: Feature selection from DataFrame."""

    def test_returns_correct_columns_when_full_df(self) -> None:
        """F9: select_features on a full prepared row extracts feature cols only."""
        df = _make_clean_df()
        # Full df has forbidden cols; need to remove them for select_features to pass
        # Actually validate_no_leakage checks the INPUT df — full df contains forbidden cols
        # select_features must raise here since forbidden cols are present
        with pytest.raises(ValueError, match="Leakage guard violation"):
            select_features(df)

    def test_returns_correct_columns_from_clean_feature_df(self) -> None:
        """F9: select_features on a feature-only DataFrame returns feature columns."""
        df = _make_feature_only_df()
        result = select_features(df)
        assert list(result.columns) == FEATURE_COLUMNS

    def test_raises_on_missing_feature_column(self) -> None:
        """F10: Missing required column raises ValueError."""
        df = _make_feature_only_df()
        df = df.drop(columns=["Voltage_V"])
        with pytest.raises(ValueError, match="Required column.*missing"):
            select_features(df)

    def test_raises_on_leakage_column_present(self) -> None:
        """F11: Forbidden column in DataFrame raises ValueError."""
        df = _make_feature_only_df()
        df["Failure_Type"] = "No Failure"  # inject leakage
        with pytest.raises(ValueError, match="Leakage guard violation"):
            select_features(df)

    def test_returns_copy_not_view(self) -> None:
        """F16: Modifying returned DataFrame does not affect original."""
        df = _make_feature_only_df()
        result = select_features(df)
        original_val = df.loc[0, "Voltage_V"]
        result.loc[0, "Voltage_V"] = 999.0
        assert df.loc[0, "Voltage_V"] == original_val


# ---------------------------------------------------------------------------
# F12-F13 — select_target
# ---------------------------------------------------------------------------


class TestSelectTarget:
    """F12-F13: Target extraction."""

    def test_returns_series(self) -> None:
        """F12: select_target returns a pandas Series."""
        df = _make_clean_df()
        result = select_target(df)
        assert isinstance(result, pd.Series)

    def test_returns_machine_failure_values(self) -> None:
        df = _make_clean_df()
        result = select_target(df)
        assert result.name == "Machine_Failure"
        assert set(result.unique()).issubset({0, 1})

    def test_raises_on_missing_target(self) -> None:
        """F13: Missing target column raises ValueError."""
        df = _make_clean_df().drop(columns=["Machine_Failure"])
        with pytest.raises(ValueError, match="Target column.*missing"):
            select_target(df)


# ---------------------------------------------------------------------------
# F14-F15 — validate_no_leakage
# ---------------------------------------------------------------------------


class TestValidateNoLeakage:
    """F14-F15: Leakage guard."""

    def test_raises_for_forbidden_col(self) -> None:
        """F14: DataFrame with a forbidden column raises ValueError."""
        df = _make_feature_only_df()
        df["Machine_ID"] = "CMP-1001"
        with pytest.raises(ValueError, match="Leakage guard violation"):
            validate_no_leakage(df)

    def test_passes_for_clean_df(self) -> None:
        """F15: DataFrame without forbidden columns passes silently."""
        df = _make_feature_only_df()
        validate_no_leakage(df)  # must not raise

    def test_error_message_lists_found_columns(self) -> None:
        df = _make_feature_only_df()
        df["Failure_Type"] = "No Failure"
        df["Machine_ID"] = "CMP-1001"
        with pytest.raises(ValueError) as exc_info:
            validate_no_leakage(df, context="test")
        msg = str(exc_info.value)
        assert "Failure_Type" in msg or "Machine_ID" in msg

    def test_context_appears_in_error(self) -> None:
        df = _make_feature_only_df()
        df["Failure_Type"] = "leak"
        with pytest.raises(ValueError) as exc_info:
            validate_no_leakage(df, context="training_pipeline")
        assert "training_pipeline" in str(exc_info.value)


# ---------------------------------------------------------------------------
# F18 — Regression on actual prepared dataset
# ---------------------------------------------------------------------------


class TestRegressionOnPreparedDataset:
    """F18: Run feature contract against the actual prepared dataset."""

    @pytest.mark.skipif(
        not _PREPARED_PATH.exists(),
        reason=f"Prepared dataset not found at {_PREPARED_PATH}",
    )
    def test_all_feature_columns_present(self) -> None:
        df = pd.read_csv(_PREPARED_PATH)
        for col in get_feature_columns():
            assert col in df.columns, f"Feature column '{col}' missing from prepared dataset"

    @pytest.mark.skipif(
        not _PREPARED_PATH.exists(),
        reason=f"Prepared dataset not found at {_PREPARED_PATH}",
    )
    def test_target_column_present_and_binary(self) -> None:
        df = pd.read_csv(_PREPARED_PATH)
        target = get_target_column()
        assert target in df.columns
        assert set(df[target].dropna().unique()).issubset({0, 1})

    @pytest.mark.skipif(
        not _PREPARED_PATH.exists(),
        reason=f"Prepared dataset not found at {_PREPARED_PATH}",
    )
    def test_select_target_on_prepared_dataset(self) -> None:
        df = pd.read_csv(_PREPARED_PATH)
        target = select_target(df)
        assert len(target) == 9885
        assert target.sum() == 1084  # verified failure count from S02 audit
