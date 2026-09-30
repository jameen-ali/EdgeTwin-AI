"""
tests/ml/test_prepare.py — Unit and regression tests for T-003 data pipeline.

Tests:
    T1  test_prefix_mapping           — All 5 Machine_ID prefix→type mappings
    T2  test_missing_machine_type_recovery — NaN Machine_Type filled from Machine_ID
    T3  test_conflicting_machine_type_detected — Mismatch flagged in report
    T4  test_duplicate_removal_ignores_batch_checksum — Batch/checksum cols ignored
    T5  test_missing_sensor_values_preserved — NaN in → NaN out
    T6  test_range_violation_detected_and_nullified — OOB value flagged, nullified
    T7  test_no_imputation_performed  — All input NaNs remain NaN
    T8  test_regression_on_raw_dataset — Full pipeline on actual raw file

Notes on T8 row-count calculation:
    10,000 raw rows
    Machine_Type is derived BEFORE duplicate removal (spec-mandated order).
    After derivation, 9 rows that previously had Machine_Type=NaN become
    semantically identical to existing non-null rows → detected as duplicates.
    Total duplicates detected: 106 (with NaN Machine_Type) + 9 (semantic) = 115.
    Output rows: 10,000 − 115 = 9,885.

    Historical note: the previously recorded value of 9,894 was calculated
    with a dedup-first order (raw NaN ≠ non-null), which detected only 106
    duplicates.  The spec-mandated derive-first order is semantically correct
    because duplicate identity should be evaluated on recovered values.
    This discrepancy is documented in the data preparation specification.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

from ml.data.prepare import (
    derive_machine_type,
    prepare_dataset,
    remove_duplicates,
    validate_ranges,
)
from ml.data.schema import (
    DUPLICATE_IGNORE_COLUMNS,
    MACHINE_ID_PREFIX_MAP,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_RAW_PATH = _REPO_ROOT / "data" / "raw" / "predictive_maintenance_dataset.csv"


def _make_df(**kwargs: list) -> pd.DataFrame:
    """Build a minimal DataFrame from column→value-list kwargs."""
    return pd.DataFrame(kwargs)


def _is_missing(val: object) -> bool:
    """Return True if *val* is NaN or None (missing in either representation).

    When a single-row DataFrame is constructed from a dict with ``None``
    for float columns, pandas may keep dtype as ``object``, in which case
    ``df.loc[0, col]`` returns Python ``None`` rather than ``float('nan')``.
    This helper treats both as missing so tests are not brittle to dtype.
    """
    if val is None:
        return True
    try:
        return math.isnan(val)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False


def _minimal_row(
    machine_id: str = "CMP-1001",
    machine_type: str | None = "Compressor",
    air_temp: float | None = 25.0,
    voltage: float | None = 410.0,
    sensor_batch: str | None = "SB001",
    checksum: str | None = "OK",
    machine_failure: int = 0,
) -> dict:
    """Return a single-row dict suitable for DataFrame construction."""
    return {
        "Machine_ID": machine_id,
        "Timestamp": "2024-01-01T00:00:00Z",
        "Machine_Type": machine_type,
        "Air_Temperature_C": air_temp,
        "Process_Temperature_C": 35.0,
        "Rotational_Speed_RPM": 1500.0,
        "Torque_Nm": 40.0,
        "Vibration_mm_s": 2.5,
        "Pressure_bar": 5.5,
        "Current_A": 12.0,
        "Voltage_V": voltage,
        "Tool_Wear_Min": 130.0,
        "Operating_Hours": 10000.0,
        "Failure_Type": "No Failure",
        "Machine_Failure": machine_failure,
        "Sensor_Batch_Code": sensor_batch,
        "Checksum_Flag": checksum,
    }


# ---------------------------------------------------------------------------
# T1 — Prefix mapping
# ---------------------------------------------------------------------------


class TestPrefixMapping:
    """T1: Verify all 5 Machine_ID prefix → Machine_Type mappings."""

    @pytest.mark.parametrize(
        "prefix, expected_type",
        [
            ("CMP", "Compressor"),
            ("PMP", "Pump"),
            ("CNC", "CNC_Machine"),
            ("CNV", "Conveyor"),
            ("MOT", "Motor"),
        ],
    )
    def test_all_five_prefixes_in_map(self, prefix: str, expected_type: str) -> None:
        assert MACHINE_ID_PREFIX_MAP[prefix] == expected_type

    def test_map_has_exactly_five_entries(self) -> None:
        assert len(MACHINE_ID_PREFIX_MAP) == 5


# ---------------------------------------------------------------------------
# T2 — Missing Machine_Type recovery
# ---------------------------------------------------------------------------


class TestMissingMachineTypeRecovery:
    """T2: NaN Machine_Type is recovered from the Machine_ID prefix."""

    def test_null_machine_type_filled_from_id(self) -> None:
        rows = [
            _minimal_row("CMP-1001", machine_type=None),
            _minimal_row("PMP-1002", machine_type=None),
            _minimal_row("CNC-1003", machine_type=None),
            _minimal_row("CNV-1004", machine_type=None),
            _minimal_row("MOT-1005", machine_type=None),
        ]
        df = pd.DataFrame(rows)
        assert df["Machine_Type"].isna().all(), "Pre-condition: all NaN"

        df_out, _report = derive_machine_type(df)

        assert df_out["Machine_Type"].isna().sum() == 0, "No remaining NaN"
        assert df_out.loc[0, "Machine_Type"] == "Compressor"
        assert df_out.loc[1, "Machine_Type"] == "Pump"
        assert df_out.loc[2, "Machine_Type"] == "CNC_Machine"
        assert df_out.loc[3, "Machine_Type"] == "Conveyor"
        assert df_out.loc[4, "Machine_Type"] == "Motor"

    def test_report_counts_recovered(self) -> None:
        rows = [_minimal_row("PMP-9999", machine_type=None) for _ in range(5)]
        df = pd.DataFrame(rows)
        _, report = derive_machine_type(df)
        assert report["missing_before"] == 5
        assert report["recovered"] == 5

    def test_non_null_machine_type_preserved_when_consistent(self) -> None:
        row = _minimal_row("CMP-1001", machine_type="Compressor")
        df = pd.DataFrame([row])
        df_out, report = derive_machine_type(df)
        assert df_out.loc[0, "Machine_Type"] == "Compressor"
        assert report["conflicts_detected"] == 0


# ---------------------------------------------------------------------------
# T3 — Conflicting Machine_Type detection
# ---------------------------------------------------------------------------


class TestConflictingMachineTypeDetection:
    """T3: Non-null Machine_Type that conflicts with prefix is flagged."""

    def test_conflict_detected_and_reported(self) -> None:
        # CMP prefix should yield Compressor, but we provide Pump
        row = _minimal_row("CMP-1001", machine_type="Pump")
        df = pd.DataFrame([row])
        _df_out, report = derive_machine_type(df)

        assert report["conflicts_detected"] == 1
        assert report["conflicts_overridden"] == 1

    def test_conflict_value_overridden_with_derived(self) -> None:
        row = _minimal_row("MOT-1001", machine_type="Compressor")
        df = pd.DataFrame([row])
        df_out, _report = derive_machine_type(df)
        # After override, Machine_Type should be Motor (derived)
        assert df_out.loc[0, "Machine_Type"] == "Motor"

    def test_zero_conflicts_in_consistent_data(self) -> None:
        rows = [
            _minimal_row("CMP-1001", machine_type="Compressor"),
            _minimal_row("MOT-1002", machine_type="Motor"),
        ]
        df = pd.DataFrame(rows)
        _, report = derive_machine_type(df)
        assert report["conflicts_detected"] == 0


# ---------------------------------------------------------------------------
# T4 — Duplicate removal ignores Sensor_Batch_Code and Checksum_Flag
# ---------------------------------------------------------------------------


class TestDuplicateRemoval:
    """T4: Rows identical except Sensor_Batch_Code/Checksum_Flag are duplicates."""

    def test_rows_differing_only_in_batch_code_removed(self) -> None:
        # Two rows: same everything, different Sensor_Batch_Code
        row_a = _minimal_row("CMP-1001", sensor_batch="SB001")
        row_b = _minimal_row("CMP-1001", sensor_batch="SB999")  # different batch
        df = pd.DataFrame([row_a, row_b])

        df_out, report = remove_duplicates(df)

        assert len(df_out) == 1, "Only 1 row kept"
        assert report["duplicates_detected"] == 1
        assert report["rows_removed"] == 1

    def test_rows_differing_only_in_checksum_removed(self) -> None:
        row_a = _minimal_row("PMP-1001", checksum="OK")
        row_b = _minimal_row("PMP-1001", checksum="FAIL")
        df = pd.DataFrame([row_a, row_b])

        df_out, report = remove_duplicates(df)

        assert len(df_out) == 1
        assert report["duplicates_detected"] == 1

    def test_rows_differing_in_sensor_value_kept(self) -> None:
        row_a = _minimal_row("CMP-1001", air_temp=25.0)
        row_b = _minimal_row("CMP-1001", air_temp=30.0)  # different temperature
        df = pd.DataFrame([row_a, row_b])

        df_out, report = remove_duplicates(df)

        assert len(df_out) == 2, "Both rows kept — they are genuinely different"
        assert report["duplicates_detected"] == 0

    def test_ignore_columns_defined_correctly(self) -> None:
        assert "Sensor_Batch_Code" in DUPLICATE_IGNORE_COLUMNS
        assert "Checksum_Flag" in DUPLICATE_IGNORE_COLUMNS
        assert len(DUPLICATE_IGNORE_COLUMNS) == 2

    def test_first_occurrence_kept(self) -> None:
        row_a = _minimal_row("CMP-1001", air_temp=25.0, sensor_batch="FIRST")
        row_b = _minimal_row("CMP-1001", air_temp=25.0, sensor_batch="SECOND")
        df = pd.DataFrame([row_a, row_b])

        df_out, _ = remove_duplicates(df)

        assert df_out.iloc[0]["Sensor_Batch_Code"] == "FIRST"


# ---------------------------------------------------------------------------
# T5 — Missing sensor values preserved
# ---------------------------------------------------------------------------


class TestMissingValuesPreserved:
    """T5: NaN sensor values pass through the pipeline unchanged."""

    def test_nan_sensor_preserved_through_derive(self) -> None:
        row = _minimal_row("CMP-1001", air_temp=None)
        df = pd.DataFrame([row])
        df_out, _ = derive_machine_type(df)
        assert _is_missing(df_out.loc[0, "Air_Temperature_C"])

    def test_nan_sensor_preserved_through_dedup(self) -> None:
        row_a = _minimal_row("CMP-1001", air_temp=None, sensor_batch="SB1")
        row_b = _minimal_row("CMP-1002", air_temp=None, sensor_batch="SB2")
        df = pd.DataFrame([row_a, row_b])
        df_out, _ = remove_duplicates(df)
        # Different Machine_IDs → not duplicates; NaN preserved
        assert df_out["Air_Temperature_C"].isna().all()

    def test_nan_within_range_not_touched_by_range_validator(self) -> None:
        row = _minimal_row("CMP-1001", voltage=None)
        df = pd.DataFrame([row])
        df_out, report = validate_ranges(df)
        assert _is_missing(df_out.loc[0, "Voltage_V"])
        assert report["violations_per_column"]["Voltage_V"] == 0

    def test_multiple_nan_columns_preserved(self) -> None:
        row = _minimal_row("MOT-1001", air_temp=None, voltage=None)
        df = pd.DataFrame([row])
        df_out, _ = validate_ranges(df)
        assert _is_missing(df_out.loc[0, "Air_Temperature_C"])
        assert _is_missing(df_out.loc[0, "Voltage_V"])


# ---------------------------------------------------------------------------
# T6 — Range violation detected and nullified (not clipped)
# ---------------------------------------------------------------------------


class TestRangeViolation:
    """T6: Out-of-range values are detected, reported, and nullified to NaN."""

    def test_voltage_above_500_detected(self) -> None:
        row = _minimal_row("CMP-1001", voltage=525.0)  # > 500 V upper bound
        df = pd.DataFrame([row])
        _df_out, report = validate_ranges(df)

        assert report["violations_per_column"]["Voltage_V"] == 1
        assert report["values_nullified_per_column"]["Voltage_V"] == 1

    def test_voltage_above_500_nullified_not_clipped(self) -> None:
        """Verify the value becomes NaN, NOT 500.0 (the bound)."""
        row = _minimal_row("CMP-1001", voltage=525.0)
        df = pd.DataFrame([row])
        df_out, _ = validate_ranges(df)

        result = df_out.loc[0, "Voltage_V"]
        assert math.isnan(result), f"Expected NaN, got {result}"
        # Explicitly confirm it was NOT clipped to the bound value
        assert result != 500.0, "Value must not be clipped to boundary"

    def test_valid_voltage_at_boundary_not_flagged(self) -> None:
        """Values exactly at the bounds (300.0 and 500.0) are valid."""
        for v in (300.0, 500.0, 400.0):
            row = _minimal_row("CMP-1001", voltage=v)
            df = pd.DataFrame([row])
            df_out, report = validate_ranges(df)
            assert report["violations_per_column"]["Voltage_V"] == 0, f"Voltage {v} should be valid"
            assert df_out.loc[0, "Voltage_V"] == v

    def test_total_violation_count_reported(self) -> None:
        rows = [_minimal_row("CMP-1001", voltage=510.0) for _ in range(3)]
        df = pd.DataFrame(rows)
        _, report = validate_ranges(df)
        assert report["total_violations"] == 3
        assert report["total_nullified"] == 3

    def test_range_bounds_present_in_report(self) -> None:
        df = pd.DataFrame([_minimal_row("CMP-1001")])
        _, report = validate_ranges(df)
        assert "Voltage_V" in report["range_bounds"]
        bounds = report["range_bounds"]["Voltage_V"]
        assert bounds["lo"] == 300.0
        assert bounds["hi"] == 500.0


# ---------------------------------------------------------------------------
# T7 — Forbidden preprocessing: no imputation performed
# ---------------------------------------------------------------------------


class TestNoImputationPerformed:
    """T7: The preparation pipeline must not impute any missing values."""

    def test_pipeline_does_not_fill_nan_with_mean_or_median(self) -> None:
        """Multiple NaN rows for the same column: none should be filled."""
        rows = [
            _minimal_row("CMP-1001", air_temp=None),
            _minimal_row("PMP-1002", air_temp=None),
            _minimal_row("CNC-1003", air_temp=25.0),
        ]
        df = pd.DataFrame(rows)

        # Run through the full pipeline steps
        df_after_mt, _ = derive_machine_type(df)
        df_after_dedup, _ = remove_duplicates(df_after_mt)
        df_after_range, _ = validate_ranges(df_after_dedup)

        nan_count = df_after_range["Air_Temperature_C"].isna().sum()
        assert nan_count == 2, f"Expected 2 NaN values to remain (no imputation), got {nan_count}"

    def test_pipeline_does_not_fill_nan_with_zero(self) -> None:
        row = _minimal_row("CMP-1001", air_temp=None)
        df = pd.DataFrame([row])
        df_after_mt, _ = derive_machine_type(df)
        df_after_dedup, _ = remove_duplicates(df_after_mt)
        df_after_range, _ = validate_ranges(df_after_dedup)

        val = df_after_range.loc[0, "Air_Temperature_C"]
        assert _is_missing(val), "NaN must not be replaced with 0"

    def test_pipeline_does_not_forward_fill(self) -> None:
        rows = [
            _minimal_row("CMP-1001", air_temp=30.0),
            _minimal_row("PMP-1002", air_temp=None),
        ]
        df = pd.DataFrame(rows)
        df_after_mt, _ = derive_machine_type(df)
        df_after_dedup, _ = remove_duplicates(df_after_mt)
        df_after_range, _ = validate_ranges(df_after_dedup)

        # Second row must still be NaN (no forward fill from first row)
        assert math.isnan(
            df_after_range.iloc[1]["Air_Temperature_C"]
        ), "NaN must not be forward-filled"


# ---------------------------------------------------------------------------
# T8 — Regression test on the actual raw dataset
# ---------------------------------------------------------------------------


class TestRegressionOnRawDataset:
    """T8: Run the full pipeline against the actual raw dataset.

    Row-count calculation (derive-first, spec-mandated order):
        Input rows              : 10,000
        Machine_Type derived    : 490 rows recovered from Machine_ID prefix
        Duplicates before dedup : 115
          - 106 duplicates detectable with raw NaN Machine_Type preserved
          -   9 additional semantic duplicates exposed after derivation
              (rows with NaN Machine_Type that match an existing row with
               the same derived Machine_Type and identical sensor values)
        Output rows             : 10,000 − 115 = 9,885

    Historical discrepancy:
        The value 9,894 was calculated with a dedup-FIRST order, which
        treats NaN Machine_Type as distinct from non-null Machine_Type and
        therefore detects only 106 duplicates.  The derive-first order is
        semantically correct per the T-003 spec.
    """

    @pytest.mark.skipif(
        not _RAW_PATH.exists(),
        reason=f"Raw dataset not found at {_RAW_PATH}",
    )
    def test_output_row_count(self, tmp_path: Path) -> None:
        report = prepare_dataset(raw_path=_RAW_PATH, interim_dir=tmp_path)

        src_rows = report["source"]["row_count"]
        out_rows = report["output"]["row_count"]
        dup_removed = report["duplicate_removal"]["rows_removed"]

        assert src_rows == 10_000, f"Expected 10,000 source rows, got {src_rows}"

        # Derive-first removes 115 duplicates: 106 raw + 9 semantic
        assert dup_removed == 115, (
            f"Expected 115 duplicates removed (derive-first order), got {dup_removed}. "
            f"Historical dedup-first value was 106 → 9,894 rows; "
            f"derive-first is semantically correct per T-003 spec."
        )
        assert out_rows == 9_885, (
            f"Expected 9,885 output rows (10,000 − 115), got {out_rows}. "
            f"See class docstring for full calculation."
        )

    @pytest.mark.skipif(
        not _RAW_PATH.exists(),
        reason=f"Raw dataset not found at {_RAW_PATH}",
    )
    def test_machine_type_fully_recovered(self, tmp_path: Path) -> None:
        report = prepare_dataset(raw_path=_RAW_PATH, interim_dir=tmp_path)
        mt = report["machine_type_recovery"]
        assert mt["missing_before"] == 490
        assert mt["recovered"] == 490
        assert mt["conflicts_detected"] == 0

    @pytest.mark.skipif(
        not _RAW_PATH.exists(),
        reason=f"Raw dataset not found at {_RAW_PATH}",
    )
    def test_voltage_violations_nullified(self, tmp_path: Path) -> None:
        report = prepare_dataset(raw_path=_RAW_PATH, interim_dir=tmp_path)
        rng = report["range_validation"]
        assert rng["violations_per_column"]["Voltage_V"] == 22
        assert rng["values_nullified_per_column"]["Voltage_V"] == 22

    @pytest.mark.skipif(
        not _RAW_PATH.exists(),
        reason=f"Raw dataset not found at {_RAW_PATH}",
    )
    def test_no_other_range_violations(self, tmp_path: Path) -> None:
        report = prepare_dataset(raw_path=_RAW_PATH, interim_dir=tmp_path)
        rng = report["range_validation"]
        for col, count in rng["violations_per_column"].items():
            if col != "Voltage_V":
                assert count == 0, f"Unexpected range violation in {col}: {count}"

    @pytest.mark.skipif(
        not _RAW_PATH.exists(),
        reason=f"Raw dataset not found at {_RAW_PATH}",
    )
    def test_no_machine_type_null_in_output(self, tmp_path: Path) -> None:
        """Prepared CSV must have zero NaN Machine_Type values."""
        report = prepare_dataset(raw_path=_RAW_PATH, interim_dir=tmp_path)
        csv_path = Path(report["_output_files"]["prepared_csv"])
        df_out = pd.read_csv(csv_path)
        assert df_out["Machine_Type"].isna().sum() == 0

    @pytest.mark.skipif(
        not _RAW_PATH.exists(),
        reason=f"Raw dataset not found at {_RAW_PATH}",
    )
    def test_raw_dataset_unchanged(self, tmp_path: Path) -> None:
        """Running the pipeline must not modify the raw file."""
        import hashlib

        with open(_RAW_PATH, "rb") as fh:
            before_hash = hashlib.sha256(fh.read()).hexdigest()

        prepare_dataset(raw_path=_RAW_PATH, interim_dir=tmp_path)

        with open(_RAW_PATH, "rb") as fh:
            after_hash = hashlib.sha256(fh.read()).hexdigest()

        assert before_hash == after_hash, "Raw dataset was modified by the pipeline"

    @pytest.mark.skipif(
        not _RAW_PATH.exists(),
        reason=f"Raw dataset not found at {_RAW_PATH}",
    )
    def test_pipeline_deterministic(self, tmp_path: Path) -> None:
        """Two runs on the same input must produce identical output CSVs."""
        import hashlib

        run1_dir = tmp_path / "run1"
        run2_dir = tmp_path / "run2"

        prepare_dataset(raw_path=_RAW_PATH, interim_dir=run1_dir)
        prepare_dataset(raw_path=_RAW_PATH, interim_dir=run2_dir)

        csv1 = run1_dir / "predictive_maintenance_prepared.csv"
        csv2 = run2_dir / "predictive_maintenance_prepared.csv"

        with open(csv1, "rb") as fh:
            h1 = hashlib.sha256(fh.read()).hexdigest()
        with open(csv2, "rb") as fh:
            h2 = hashlib.sha256(fh.read()).hexdigest()

        assert h1 == h2, "Pipeline is not deterministic: two runs produced different CSVs"
