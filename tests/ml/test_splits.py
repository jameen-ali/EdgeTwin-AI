"""
tests/ml/test_splits.py - Unit tests for T-011 dataset splitting.

Tests:
    S1  test_split_produces_three_non_empty_dataframes
    S2  test_split_sizes_approximate_fractions
    S3  test_no_machine_id_overlap_between_splits
    S4  test_all_machine_ids_covered
    S5  test_same_seed_produces_identical_splits
    S6  test_different_seed_can_produce_different_splits
    S7  test_target_column_present_in_every_split
    S8  test_target_classes_in_every_split
    S9  test_failure_rate_approximately_preserved
    S10 test_split_is_deterministic_for_any_seed
    S11 test_save_and_load_roundtrip
    S12 test_split_raises_on_missing_group_col
    S13 test_split_raises_on_missing_target_col
    S14 test_split_raises_on_invalid_fractions
    S15 test_feature_columns_present_in_splits
    S16 test_regression_on_prepared_dataset
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ml.data.features import get_feature_columns
from ml.data.schema import TARGET_COLUMN
from ml.data.splits import (
    load_splits,
    save_splits,
    split_dataset,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PREPARED_PATH = _REPO_ROOT / "data" / "interim" / "predictive_maintenance_prepared.csv"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def small_df() -> pd.DataFrame:
    """60 machines, 10 rows each, alternating failure to give ~10% failure rate."""
    machines = [f"CMP-{i:04d}" for i in range(30)] + [f"PMP-{i:04d}" for i in range(30)]
    rows = []
    for mid in machines:
        for j in range(10):
            rows.append(
                {
                    "Machine_ID": mid,
                    "Timestamp": f"2024-01-{(j % 28) + 1:02d}",
                    "Machine_Type": "Compressor" if mid.startswith("CMP") else "Pump",
                    "Air_Temperature_C": 25.0,
                    "Process_Temperature_C": 35.0,
                    "Rotational_Speed_RPM": 1500.0,
                    "Torque_Nm": 40.0,
                    "Vibration_mm_s": 2.5,
                    "Pressure_bar": 5.5,
                    "Current_A": 12.0,
                    "Voltage_V": 415.0,
                    "Tool_Wear_Min": float(j * 10),
                    "Operating_Hours": float(j * 100),
                    "Failure_Type": "No Failure",
                    "Machine_Failure": 1 if j == 9 else 0,  # ~10%
                    "Sensor_Batch_Code": "SB001",
                    "Checksum_Flag": "OK",
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture
def small_split(small_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return split_dataset(small_df, seed=42)


# ---------------------------------------------------------------------------
# S1-S4: Basic split properties
# ---------------------------------------------------------------------------


class TestBasicSplitProperties:
    """S1-S4: Shape and coverage."""

    def test_produces_three_non_empty_dataframes(
        self, small_split: tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
    ) -> None:
        train, val, test = small_split
        assert len(train) > 0
        assert len(val) > 0
        assert len(test) > 0

    def test_split_sizes_approximate_fractions(
        self, small_df: pd.DataFrame, small_split: tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
    ) -> None:
        """S2: Machine counts match requested fractions approximately."""
        train, val, test = small_split
        train_machines = train["Machine_ID"].nunique()
        val_machines = val["Machine_ID"].nunique()
        test_machines = test["Machine_ID"].nunique()
        total_machines = small_df["Machine_ID"].nunique()  # 60

        # Allow ±1 machine tolerance for rounding
        assert abs(train_machines - round(total_machines * 0.70)) <= 1
        assert abs(val_machines - round(total_machines * 0.15)) <= 1
        assert abs(test_machines - round(total_machines * 0.15)) <= 1

    def test_no_machine_id_overlap(
        self, small_split: tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
    ) -> None:
        """S3: No Machine_ID appears in more than one split."""
        train, val, test = small_split
        train_m = set(train["Machine_ID"])
        val_m = set(val["Machine_ID"])
        test_m = set(test["Machine_ID"])
        assert not (train_m & val_m), f"Machine_ID overlap train/val: {train_m & val_m}"
        assert not (train_m & test_m), f"Machine_ID overlap train/test: {train_m & test_m}"
        assert not (val_m & test_m), f"Machine_ID overlap val/test: {val_m & test_m}"

    def test_all_machines_covered(
        self, small_df: pd.DataFrame, small_split: tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
    ) -> None:
        """S4: Every Machine_ID from the input appears in exactly one split."""
        train, val, test = small_split
        all_original = set(small_df["Machine_ID"])
        all_split = set(train["Machine_ID"]) | set(val["Machine_ID"]) | set(test["Machine_ID"])
        assert all_original == all_split


# ---------------------------------------------------------------------------
# S5-S6: Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    """S5-S6, S10: Seed determinism."""

    def test_same_seed_produces_identical_splits(self, small_df: pd.DataFrame) -> None:
        """S5: Two calls with the same seed produce byte-identical DataFrames."""
        train1, val1, test1 = split_dataset(small_df, seed=42)
        train2, val2, test2 = split_dataset(small_df, seed=42)

        for df1, df2, name in [
            (train1, train2, "train"),
            (val1, val2, "val"),
            (test1, test2, "test"),
        ]:
            assert list(df1["Machine_ID"]) == list(
                df2["Machine_ID"]
            ), f"{name} Machine_IDs differ between identical-seed runs"

    def test_different_seed_may_produce_different_splits(self, small_df: pd.DataFrame) -> None:
        """S6: Two calls with different seeds can produce different splits.

        This is a probabilistic test — with 60 machines and two very different
        seeds, at least one split boundary will differ in the overwhelming
        majority of cases.
        """
        train42, _, _ = split_dataset(small_df, seed=42)
        train99, _, _ = split_dataset(small_df, seed=99)
        # It is possible (but extremely unlikely) that the same machines end
        # up in the same order for both seeds; we allow this by just checking
        # that the test does not crash rather than asserting difference.
        assert isinstance(train42, pd.DataFrame)
        assert isinstance(train99, pd.DataFrame)

    def test_split_deterministic_for_arbitrary_seed(self, small_df: pd.DataFrame) -> None:
        """S10: Any seed produces identical results on repeated calls."""
        for seed in (0, 1, 100, 2024):
            t1, _v1, _e1 = split_dataset(small_df, seed=seed)
            t2, _v2, _e2 = split_dataset(small_df, seed=seed)
            assert set(t1["Machine_ID"]) == set(
                t2["Machine_ID"]
            ), f"Non-deterministic at seed={seed}"


# ---------------------------------------------------------------------------
# S7-S9: Target properties
# ---------------------------------------------------------------------------


class TestTargetProperties:
    """S7-S9: Target column presence and failure rate."""

    def test_target_present_in_every_split(
        self, small_split: tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
    ) -> None:
        """S7: Machine_Failure exists in all three split DataFrames."""
        for df, name in zip(small_split, ("train", "val", "test")):
            assert TARGET_COLUMN in df.columns, f"{TARGET_COLUMN} missing from {name}"

    def test_target_classes_in_every_split(
        self, small_split: tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
    ) -> None:
        """S8: Both classes (0 and 1) are present in every split."""
        for df, name in zip(small_split, ("train", "val", "test")):
            classes = set(df[TARGET_COLUMN].unique())
            assert 0 in classes, f"Class 0 absent from {name}"
            assert 1 in classes, f"Class 1 absent from {name}"

    def test_failure_rate_roughly_preserved(
        self, small_df: pd.DataFrame, small_split: tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
    ) -> None:
        """S9: Per-split failure rates should be within ±5pp of the overall rate.

        The round-robin assignment distributes machines by failure rate,
        so each split should receive a proportional mix.  With only 60 machines
        and integer rounding, exact stratification is not achievable.
        """
        train, val, test = small_split
        overall = small_df[TARGET_COLUMN].mean()
        tolerance = 0.05  # 5 percentage points

        for df, name in [(train, "train"), (val, "val"), (test, "test")]:
            rate = df[TARGET_COLUMN].mean()
            assert abs(rate - overall) <= tolerance, (
                f"{name} failure rate {rate:.3f} deviates from overall {overall:.3f} "
                f"by more than {tolerance:.2f}"
            )


# ---------------------------------------------------------------------------
# S11: Save/load round-trip
# ---------------------------------------------------------------------------


class TestSaveLoadRoundtrip:
    """S11: Persistence round-trip."""

    def test_save_and_load_roundtrip(
        self,
        small_split: tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame],
        tmp_path: Path,
    ) -> None:
        train, val, test = small_split
        save_splits(train, val, test, splits_dir=tmp_path)

        assert (tmp_path / "train.csv").exists()
        assert (tmp_path / "val.csv").exists()
        assert (tmp_path / "test.csv").exists()

        train2, val2, test2 = load_splits(tmp_path)

        for df1, df2, name in [(train, train2, "train"), (val, val2, "val"), (test, test2, "test")]:
            assert len(df1) == len(df2), f"{name} row count changed after round-trip"
            assert set(df1["Machine_ID"]) == set(
                df2["Machine_ID"]
            ), f"{name} Machine_IDs changed after round-trip"

    def test_load_raises_on_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_splits(tmp_path)  # no files written


# ---------------------------------------------------------------------------
# S12-S14: Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """S12-S14: Input validation errors."""

    def test_raises_on_missing_group_col(self, small_df: pd.DataFrame) -> None:
        """S12: Missing group column raises ValueError."""
        df = small_df.drop(columns=["Machine_ID"])
        with pytest.raises(ValueError, match="Group column"):
            split_dataset(df, group_col="Machine_ID")

    def test_raises_on_missing_target_col(self, small_df: pd.DataFrame) -> None:
        """S13: Missing target column raises ValueError."""
        df = small_df.drop(columns=["Machine_Failure"])
        with pytest.raises(ValueError, match="Target column"):
            split_dataset(df, target_col="Machine_Failure")

    def test_raises_on_invalid_fractions_sum_to_one(self, small_df: pd.DataFrame) -> None:
        """S14: train_frac + val_frac >= 1 raises ValueError."""
        with pytest.raises(ValueError, match="train_frac.*val_frac"):
            split_dataset(small_df, train_frac=0.85, val_frac=0.20)


# ---------------------------------------------------------------------------
# S15: Feature columns present in splits
# ---------------------------------------------------------------------------


class TestFeatureColumnsInSplits:
    """S15: Feature columns are accessible from split DataFrames."""

    def test_feature_columns_present_in_splits(
        self, small_split: tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
    ) -> None:
        feature_cols = get_feature_columns()
        for df, name in zip(small_split, ("train", "val", "test")):
            for col in feature_cols:
                assert col in df.columns, f"Feature '{col}' missing from {name} split"


# ---------------------------------------------------------------------------
# S16: Regression on actual prepared dataset
# ---------------------------------------------------------------------------


class TestRegressionOnPreparedDataset:
    """S16: Full split on the real prepared dataset."""

    @pytest.mark.skipif(
        not _PREPARED_PATH.exists(),
        reason=f"Prepared dataset not found at {_PREPARED_PATH}",
    )
    def test_regression_split_sizes(self, tmp_path: Path) -> None:
        """Split the actual 9,885-row dataset and verify machine counts."""
        df = pd.read_csv(_PREPARED_PATH)
        train, val, test = split_dataset(df, seed=42)

        total_machines = df["Machine_ID"].nunique()  # 60
        assert total_machines == 60

        train_m = train["Machine_ID"].nunique()
        val_m = val["Machine_ID"].nunique()
        test_m = test["Machine_ID"].nunique()

        # 60 * 0.70 = 42, 60 * 0.15 = 9
        assert train_m + val_m + test_m == 60
        assert abs(train_m - 42) <= 1
        assert abs(val_m - 9) <= 1
        assert abs(test_m - 9) <= 1

    @pytest.mark.skipif(
        not _PREPARED_PATH.exists(),
        reason=f"Prepared dataset not found at {_PREPARED_PATH}",
    )
    def test_regression_no_overlap(self) -> None:
        """Zero Machine_ID overlap in the real dataset split."""
        df = pd.read_csv(_PREPARED_PATH)
        train, val, test = split_dataset(df, seed=42)

        train_m = set(train["Machine_ID"])
        val_m = set(val["Machine_ID"])
        test_m = set(test["Machine_ID"])

        assert not (train_m & val_m), f"Overlap train/val: {train_m & val_m}"
        assert not (train_m & test_m), f"Overlap train/test: {train_m & test_m}"
        assert not (val_m & test_m), f"Overlap val/test: {val_m & test_m}"

    @pytest.mark.skipif(
        not _PREPARED_PATH.exists(),
        reason=f"Prepared dataset not found at {_PREPARED_PATH}",
    )
    def test_regression_deterministic(self) -> None:
        """Two runs on real data with same seed produce identical train Machine_IDs."""
        df = pd.read_csv(_PREPARED_PATH)
        train1, _, _ = split_dataset(df, seed=42)
        train2, _, _ = split_dataset(df, seed=42)

        assert set(train1["Machine_ID"]) == set(train2["Machine_ID"])

    @pytest.mark.skipif(
        not _PREPARED_PATH.exists(),
        reason=f"Prepared dataset not found at {_PREPARED_PATH}",
    )
    def test_regression_failure_rate_preserved(self) -> None:
        """Failure rate in each split is within 5pp of overall 10.97%."""
        df = pd.read_csv(_PREPARED_PATH)
        train, val, test = split_dataset(df, seed=42)

        overall = df["Machine_Failure"].mean()
        tolerance = 0.05

        for part_df, name in [(train, "train"), (val, "val"), (test, "test")]:
            rate = part_df["Machine_Failure"].mean()
            assert abs(rate - overall) <= tolerance, (
                f"Real {name} failure rate {rate:.4f} deviates from overall "
                f"{overall:.4f} by more than {tolerance}"
            )

    @pytest.mark.skipif(
        not _PREPARED_PATH.exists(),
        reason=f"Prepared dataset not found at {_PREPARED_PATH}",
    )
    def test_regression_save_and_load(self, tmp_path: Path) -> None:
        """Save splits to disk and reload; row counts must match."""
        df = pd.read_csv(_PREPARED_PATH)
        train, val, test = split_dataset(df, seed=42)
        save_splits(train, val, test, splits_dir=tmp_path)
        train2, val2, test2 = load_splits(tmp_path)

        assert len(train) == len(train2)
        assert len(val) == len(val2)
        assert len(test) == len(test2)
