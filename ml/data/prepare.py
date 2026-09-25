"""
ml/data/prepare.py - EdgeTwin AI reproducible data preparation pipeline.

T-003: Replace notebook-only cleaning logic with a tested, reproducible
Python data-preparation pipeline that fixes defects identified in the
data audit.

Pipeline order (deterministic):
    1. load_raw_data()       - read immutable raw CSV
    2. validate_schema()     - check columns, types, target values
    3. derive_machine_type() - recover Machine_Type from Machine_ID prefix
    4. remove_duplicates()   - drop exact duplicates ignoring batch/checksum cols
    5. validate_ranges()     - flag & nullify impossible sensor values (no clipping)
    6. build_quality_report()- compile all change counts
    7. save_outputs()        - write interim CSV + JSON quality report

What this pipeline does NOT do (belongs to later tasks):
    - Imputation (no mean/median/mode/ffill/bfill/0-fill)
    - Train/test splitting
    - Feature engineering
    - Fitted preprocessing of any kind

Usage:
    python -m ml.data.prepare
    python -m ml.data.prepare --raw PATH --interim DIR
    python -m ml.data.prepare --deterministic   (used by DVC; fixes timestamp)

Author: T-003 / S02; --deterministic added S03 / T-010
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from ml.data.schema import (
    DUPLICATE_IGNORE_COLUMNS,
    MACHINE_ID_PREFIX_MAP,
    SENSOR_RANGES,
    validate_schema,
)

# ---------------------------------------------------------------------------
# Repository-relative path helpers
# ---------------------------------------------------------------------------

#: Absolute path to the repository root (two levels above this file).
_REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent

#: Default path to the immutable raw dataset.
DEFAULT_RAW_PATH: Path = _REPO_ROOT / "data" / "raw" / "predictive_maintenance_dataset.csv"

#: Default output directory for prepared data and quality report.
DEFAULT_INTERIM_DIR: Path = _REPO_ROOT / "data" / "interim"

#: Pipeline identifier for the quality report.
PIPELINE_VERSION: str = "T-003/v1"


# ---------------------------------------------------------------------------
# Step 1 — Load
# ---------------------------------------------------------------------------


def load_raw_data(path: Path) -> pd.DataFrame:
    """Load the raw dataset from *path*.

    The raw file is treated as immutable; this function never writes to it.

    Parameters
    ----------
    path:
        Absolute or relative path to the raw CSV file.

    Returns
    -------
    pd.DataFrame
        DataFrame with the original dtypes inferred by pandas.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Raw dataset not found: {path}")
    return pd.read_csv(path)


# ---------------------------------------------------------------------------
# Step 3 — Derive Machine_Type
# ---------------------------------------------------------------------------


def derive_machine_type(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Recover and validate Machine_Type from the Machine_ID prefix.

    For rows where Machine_Type is **missing (NaN)**:
        The value is derived from the first 3 characters of Machine_ID
        using MACHINE_ID_PREFIX_MAP.

    For rows where Machine_Type is **already present**:
        The existing value is compared against the prefix-derived value.
        If they differ, the row is flagged as a data-quality conflict
        (the derived value takes precedence so the output has zero
        mismatches against the deterministic prefix mapping).

    Parameters
    ----------
    df:
        DataFrame after schema validation.  Must contain ``Machine_ID``
        and ``Machine_Type`` columns.  Input is not mutated.

    Returns
    -------
    df_out : pd.DataFrame
        Copy of *df* with Machine_Type fully populated from prefix map.
    report : dict
        ``{
            "missing_before": int,
            "recovered": int,
            "conflicts_detected": int,
            "conflicts_overridden": int,
            "unknown_prefixes": list[str],
        }``
    """
    df_out = df.copy()

    # Derive expected type for every row from Machine_ID prefix
    df_out["_derived_type"] = df_out["Machine_ID"].apply(
        lambda mid: MACHINE_ID_PREFIX_MAP.get(str(mid)[:3])
    )

    missing_mask = df_out["Machine_Type"].isna()
    non_null_mask = ~missing_mask

    # Detect conflicts in non-null rows
    conflict_mask = non_null_mask & (df_out["Machine_Type"] != df_out["_derived_type"])
    conflicts_detected = int(conflict_mask.sum())

    # Unknown prefixes (Machine_ID prefix not in map)
    unknown_prefix_mask = df_out["_derived_type"].isna()
    unknown_prefixes: list[str] = list(
        df_out.loc[unknown_prefix_mask, "Machine_ID"]
        .apply(lambda mid: str(mid)[:3])
        .unique()
    )

    # Apply: fill missing from derived; override conflicts with derived
    df_out["Machine_Type"] = df_out["_derived_type"]
    df_out = df_out.drop(columns=["_derived_type"])

    missing_before = int(missing_mask.sum())
    recovered = missing_before  # all missing rows get a derived value

    report: dict[str, Any] = {
        "missing_before": missing_before,
        "recovered": recovered,
        "conflicts_detected": conflicts_detected,
        "conflicts_overridden": conflicts_detected,
        "unknown_prefixes": unknown_prefixes,
    }
    return df_out, report


# ---------------------------------------------------------------------------
# Step 4 — Remove duplicates
# ---------------------------------------------------------------------------


def remove_duplicates(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Remove exact-duplicate rows, ignoring administrative columns.

    Duplicate identity is determined by comparing all columns EXCEPT
    ``Sensor_Batch_Code`` and ``Checksum_Flag``.  This is intentional:
    two observations that are identical in every sensor reading and
    metadata field but differ only in batch code or checksum are
    considered the same observation.

    The first occurrence is kept; subsequent duplicates are dropped.
    The comparison is deterministic (no randomness).

    Parameters
    ----------
    df:
        DataFrame after Machine_Type derivation.  Input is not mutated.

    Returns
    -------
    df_out : pd.DataFrame
        DataFrame with duplicates removed.
    report : dict
        ``{
            "comparison_columns": list[str],
            "rows_before": int,
            "duplicates_detected": int,
            "rows_removed": int,
            "rows_after": int,
        }``
    """
    comparison_columns = [c for c in df.columns if c not in DUPLICATE_IGNORE_COLUMNS]
    rows_before = len(df)

    duplicate_mask = df.duplicated(subset=comparison_columns, keep="first")
    df_out = df[~duplicate_mask].copy()

    duplicates_removed = int(duplicate_mask.sum())

    report: dict[str, Any] = {
        "comparison_columns": comparison_columns,
        "rows_before": rows_before,
        "duplicates_detected": duplicates_removed,
        "rows_removed": duplicates_removed,
        "rows_after": len(df_out),
    }
    return df_out, report


# ---------------------------------------------------------------------------
# Step 5 — Range validation
# ---------------------------------------------------------------------------


def validate_ranges(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Flag and nullify sensor values that fall outside project range bounds.

    For each numeric sensor column defined in SENSOR_RANGES:
        - Non-null values outside [lo, hi] are flagged.
        - The out-of-range value is replaced with NaN (nullified).
        - The value is NOT clipped; silent alteration of measurements is
          never acceptable in this pipeline.

    These bounds are project data-quality bounds derived from EDA.
    They are NOT claimed ISO limits or industry safety standards.

    Parameters
    ----------
    df:
        DataFrame after duplicate removal.  Input is not mutated.

    Returns
    -------
    df_out : pd.DataFrame
        Copy of *df* with out-of-range values replaced by NaN.
    report : dict
        ``{
            "range_bounds": dict,
            "violations_per_column": dict[str, int],
            "values_nullified_per_column": dict[str, int],
            "total_violations": int,
            "total_nullified": int,
        }``
    """
    df_out = df.copy()

    violations_per_column: dict[str, int] = {}
    values_nullified_per_column: dict[str, int] = {}
    total_violations = 0

    for col, (lo, hi) in SENSOR_RANGES.items():
        if col not in df_out.columns:
            continue
        non_null_mask = df_out[col].notna()
        out_of_range = non_null_mask & ((df_out[col] < lo) | (df_out[col] > hi))
        count = int(out_of_range.sum())
        violations_per_column[col] = count
        values_nullified_per_column[col] = count
        total_violations += count
        if count > 0:
            df_out.loc[out_of_range, col] = float("nan")

    report: dict[str, Any] = {
        "range_bounds": {col: {"lo": lo, "hi": hi} for col, (lo, hi) in SENSOR_RANGES.items()},
        "violations_per_column": violations_per_column,
        "values_nullified_per_column": values_nullified_per_column,
        "total_violations": total_violations,
        "total_nullified": total_violations,
    }
    return df_out, report


# ---------------------------------------------------------------------------
# Step 6 — Build quality report
# ---------------------------------------------------------------------------


def build_quality_report(
    raw_path: Path,
    raw_shape: tuple[int, int],
    output_shape: tuple[int, int],
    schema_result: dict[str, Any],
    mt_report: dict[str, Any],
    dup_report: dict[str, Any],
    range_report: dict[str, Any],
    missing_before: dict[str, int],
    missing_after: dict[str, int],
    *,
    deterministic: bool = False,
) -> dict[str, Any]:
    """Compile all preparation statistics into a single quality report dict.

    Parameters
    ----------
    raw_path:
        Path to the source raw file (stored as a string for serialisability).
    raw_shape:
        (rows, cols) of the raw dataset.
    output_shape:
        (rows, cols) of the prepared output dataset.
    schema_result:
        Result from validate_schema().
    mt_report:
        Result from derive_machine_type().
    dup_report:
        Result from remove_duplicates().
    range_report:
        Result from validate_ranges().
    missing_before:
        Per-column null counts before preparation.
    missing_after:
        Per-column null counts after preparation.
    deterministic:
        If True, replace the live UTC timestamp with a fixed sentinel string
        so that the JSON output is byte-identical across runs (required for
        stable DVC output hashing).  Defaults to False so that interactive
        CLI runs still record a real timestamp.

    Returns
    -------
    dict
        A JSON-serialisable quality report.
    """
    timestamp_value = "deterministic" if deterministic else datetime.now(UTC).isoformat()
    return {
        "pipeline_version": PIPELINE_VERSION,
        "pipeline_timestamp_utc": timestamp_value,
        "source": {
            "file": str(raw_path),
            "row_count": raw_shape[0],
            "column_count": raw_shape[1],
        },
        "output": {
            "row_count": output_shape[0],
            "column_count": output_shape[1],
        },
        "schema_validation": schema_result,
        "machine_type_recovery": mt_report,
        "duplicate_removal": dup_report,
        "range_validation": range_report,
        "missing_values": {
            "before_preparation": missing_before,
            "after_preparation": missing_after,
        },
    }


# ---------------------------------------------------------------------------
# Step 7 — Save outputs
# ---------------------------------------------------------------------------


def save_outputs(
    df: pd.DataFrame,
    report: dict[str, Any],
    interim_dir: Path,
) -> tuple[Path, Path]:
    """Write the prepared dataset and quality report to *interim_dir*.

    Files written:
    - ``predictive_maintenance_prepared.csv``  — prepared dataset
    - ``data_quality_report.json``             — machine-readable report

    Parameters
    ----------
    df:
        Prepared DataFrame.
    report:
        Quality report dict from build_quality_report().
    interim_dir:
        Directory to write outputs into.  Created if it does not exist.

    Returns
    -------
    (csv_path, json_path) : tuple[Path, Path]
        Absolute paths to the written files.
    """
    interim_dir = Path(interim_dir)
    interim_dir.mkdir(parents=True, exist_ok=True)

    csv_path = interim_dir / "predictive_maintenance_prepared.csv"
    json_path = interim_dir / "data_quality_report.json"

    df.to_csv(csv_path, index=False)

    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    return csv_path, json_path


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def prepare_dataset(
    raw_path: Path = DEFAULT_RAW_PATH,
    interim_dir: Path = DEFAULT_INTERIM_DIR,
    *,
    deterministic: bool = False,
) -> dict[str, Any]:
    """Run the full data preparation pipeline end-to-end.

    Pipeline order:
        load -> validate_schema -> derive_machine_type ->
        remove_duplicates -> validate_ranges -> build_quality_report ->
        save_outputs

    No imputation, no clipping, no splitting, no feature engineering.
    Missing sensor values remain NaN throughout.

    Parameters
    ----------
    raw_path:
        Path to the immutable raw CSV.
    interim_dir:
        Directory for prepared CSV and quality report.
    deterministic:
        If True, the quality report JSON uses a fixed timestamp sentinel
        instead of the real UTC time.  Set by the ``--deterministic`` CLI
        flag and by the DVC stage so that output hashes are stable.

    Returns
    -------
    dict
        The quality report plus output file paths.
    """
    raw_path = Path(raw_path)
    interim_dir = Path(interim_dir)

    # 1. Load
    df_raw = load_raw_data(raw_path)
    raw_shape = df_raw.shape
    missing_before = {col: int(df_raw[col].isna().sum()) for col in df_raw.columns}

    # 2. Schema validation (non-fatal: pipeline continues on warnings)
    schema_result = validate_schema(df_raw)
    if not schema_result["valid"]:
        print(
            f"[WARN] Schema validation errors: {schema_result['errors']}",
            file=sys.stderr,
        )

    # 3. Derive Machine_Type (before dedup so duplicate comparison uses
    #    the semantically correct Machine_Type)
    df, mt_report = derive_machine_type(df_raw)

    # 4. Remove duplicates (on all columns except Sensor_Batch_Code/Checksum_Flag)
    df, dup_report = remove_duplicates(df)

    # 5. Range validation — flag & nullify; no clipping
    df, range_report = validate_ranges(df)

    # Capture missing-value counts in the prepared output
    missing_after = {col: int(df[col].isna().sum()) for col in df.columns}

    # 6. Build quality report
    report = build_quality_report(
        raw_path=raw_path,
        raw_shape=raw_shape,
        output_shape=df.shape,
        schema_result=schema_result,
        mt_report=mt_report,
        dup_report=dup_report,
        range_report=range_report,
        missing_before=missing_before,
        missing_after=missing_after,
        deterministic=deterministic,
    )

    # 7. Save outputs
    csv_path, json_path = save_outputs(df, report, interim_dir)

    report["_output_files"] = {
        "prepared_csv": str(csv_path),
        "quality_report_json": str(json_path),
    }

    return report


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m ml.data.prepare",
        description="EdgeTwin AI - T-003 Data Preparation Pipeline",
    )
    parser.add_argument(
        "--raw",
        type=Path,
        default=DEFAULT_RAW_PATH,
        metavar="PATH",
        help=f"Path to the immutable raw CSV (default: {DEFAULT_RAW_PATH})",
    )
    parser.add_argument(
        "--interim",
        type=Path,
        default=DEFAULT_INTERIM_DIR,
        metavar="DIR",
        help=f"Output directory for prepared data (default: {DEFAULT_INTERIM_DIR})",
    )
    parser.add_argument(
        "--deterministic",
        action="store_true",
        default=False,
        help=(
            "Replace the live UTC timestamp in the quality report with a fixed "
            "sentinel string so that JSON output is byte-identical across runs. "
            "Used by the DVC stage to produce stable output hashes."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for the data preparation pipeline."""
    args = _parse_args(argv)
    print(f"[T-003] Loading raw data from: {args.raw}")
    report = prepare_dataset(
        raw_path=args.raw,
        interim_dir=args.interim,
        deterministic=args.deterministic,
    )

    src = report["source"]
    out = report["output"]
    mt = report["machine_type_recovery"]
    dup = report["duplicate_removal"]
    rng = report["range_validation"]
    mv_before = report["missing_values"]["before_preparation"]
    mv_after = report["missing_values"]["after_preparation"]

    print()
    print("=== EdgeTwin AI - Data Preparation Summary ===")
    print(f"  Source rows      : {src['row_count']}")
    print(f"  Source columns   : {src['column_count']}")
    print()
    print(f"  Machine_Type missing before : {mt['missing_before']}")
    print(f"  Machine_Type recovered      : {mt['recovered']}")
    print(f"  Machine_Type conflicts      : {mt['conflicts_detected']}")
    print()
    print(f"  Duplicates detected : {dup['duplicates_detected']}")
    print(f"  Rows after dedup    : {dup['rows_after']}")
    print()
    print(f"  Range violations total : {rng['total_violations']}")
    print(f"  Values nullified total : {rng['total_nullified']}")
    for col, count in rng["violations_per_column"].items():
        if count > 0:
            print(f"    {col}: {count} violation(s) nullified")
    print()
    print(f"  Output rows    : {out['row_count']}")
    print(f"  Output columns : {out['column_count']}")
    print()

    # Summarise missing-value change for sensor columns
    from ml.data.schema import NUMERIC_SENSOR_COLUMNS

    print("  Missing sensor values (before -> after):")
    for col in NUMERIC_SENSOR_COLUMNS:
        before = mv_before.get(col, 0)
        after = mv_after.get(col, 0)
        change = after - before
        change_str = f" (+{change} nullified)" if change > 0 else ""
        print(f"    {col}: {before} -> {after}{change_str}")

    print()
    schema_ok = report["schema_validation"]["valid"]
    print(f"  Schema valid: {schema_ok}")
    if not schema_ok:
        print(f"  Schema errors: {report['schema_validation']['errors']}")

    print()
    print(f"  Output CSV   : {report['_output_files']['prepared_csv']}")
    print(f"  Quality JSON : {report['_output_files']['quality_report_json']}")
    print("==============================================")


if __name__ == "__main__":
    main()
