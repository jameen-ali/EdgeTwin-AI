"""
ml/data/schema.py — EdgeTwin AI raw dataset schema definition and validation.

Defines:
- Expected raw column list
- Numeric sensor columns
- Per-column engineering range bounds (project data-quality bounds;
  NOT claimed ISO or industry safety standards)
- Machine_ID prefix → Machine_Type mapping
- FORBIDDEN_FEATURE_COLUMNS constant (leakage/identifier guard for ML tasks)
- DUPLICATE_IGNORE_COLUMNS constant
- validate_schema() function

No ML preprocessing is performed here.
"""

from __future__ import annotations

import pandas as pd

# ---------------------------------------------------------------------------
# Column definitions
# ---------------------------------------------------------------------------

#: All 17 columns expected in the raw dataset, in their original order.
EXPECTED_COLUMNS: list[str] = [
    "Machine_ID",
    "Timestamp",
    "Machine_Type",
    "Air_Temperature_C",
    "Process_Temperature_C",
    "Rotational_Speed_RPM",
    "Torque_Nm",
    "Vibration_mm_s",
    "Pressure_bar",
    "Current_A",
    "Voltage_V",
    "Tool_Wear_Min",
    "Operating_Hours",
    "Failure_Type",
    "Machine_Failure",
    "Sensor_Batch_Code",
    "Checksum_Flag",
]

#: Numeric sensor measurement columns (continuous float-valued).
NUMERIC_SENSOR_COLUMNS: list[str] = [
    "Air_Temperature_C",
    "Process_Temperature_C",
    "Rotational_Speed_RPM",
    "Torque_Nm",
    "Vibration_mm_s",
    "Pressure_bar",
    "Current_A",
    "Voltage_V",
    "Tool_Wear_Min",
    "Operating_Hours",
]

# ---------------------------------------------------------------------------
# Engineering range bounds
# ---------------------------------------------------------------------------

#: Per-column inclusive (lo, hi) bounds used for range validation.
#:
#: These are project data-quality bounds derived from EDA of the training
#: dataset.  They are NOT claimed industry safety standards or ISO limits.
#: Values outside these bounds are flagged and nullified; they are NOT
#: clipped silently.
SENSOR_RANGES: dict[str, tuple[float, float]] = {
    "Air_Temperature_C": (0.0, 60.0),
    "Process_Temperature_C": (0.0, 80.0),
    "Rotational_Speed_RPM": (0.0, 5000.0),
    "Torque_Nm": (0.0, 150.0),
    "Vibration_mm_s": (0.0, 20.0),
    "Pressure_bar": (0.0, 20.0),
    "Current_A": (0.0, 50.0),
    "Voltage_V": (300.0, 500.0),
    "Tool_Wear_Min": (0.0, 300.0),
    "Operating_Hours": (0.0, 25000.0),
}

# ---------------------------------------------------------------------------
# Machine_ID prefix → Machine_Type mapping
# ---------------------------------------------------------------------------

#: Deterministic mapping from the 3-character Machine_ID prefix to the
#: expected Machine_Type string.  Used to recover missing Machine_Type
#: values and to detect conflicts in non-null values.
MACHINE_ID_PREFIX_MAP: dict[str, str] = {
    "CMP": "Compressor",
    "PMP": "Pump",
    "CNC": "CNC_Machine",
    "CNV": "Conveyor",
    "MOT": "Motor",
}

# ---------------------------------------------------------------------------
# Forbidden feature columns
# ---------------------------------------------------------------------------

#: Columns that must NEVER be used as ML model inputs.
#:
#: - Failure_Type: post-outcome label — direct target leakage.
#: - Machine_ID: opaque identifier — identifier leakage.
#: - Timestamp: order/time leakage in an i.i.d.-snapshot dataset.
#: - Sensor_Batch_Code: administrative metadata.
#: - Checksum_Flag: administrative metadata.
#:
#: This constant is established in T-003 and enforced by a leakage-guard
#: test in future ML tasks (T-012, etc.).  The raw and interim datasets
#: RETAIN these columns for traceability; they are excluded at feature
#: construction time.
FORBIDDEN_FEATURE_COLUMNS: list[str] = [
    "Failure_Type",
    "Machine_ID",
    "Timestamp",
    "Sensor_Batch_Code",
    "Checksum_Flag",
]

# ---------------------------------------------------------------------------
# Duplicate detection exclusions
# ---------------------------------------------------------------------------

#: Administrative columns excluded from duplicate identity comparison.
#: Two rows are considered duplicates when they are identical across all
#: columns EXCEPT these two.
DUPLICATE_IGNORE_COLUMNS: list[str] = [
    "Sensor_Batch_Code",
    "Checksum_Flag",
]

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

#: Valid values for the binary target column.
VALID_MACHINE_FAILURE_VALUES: set[int] = {0, 1}


def validate_schema(df: pd.DataFrame) -> dict:
    """Validate that *df* conforms to the expected raw dataset schema.

    Checks performed:
    - All expected columns are present.
    - No unexpected critical columns are missing.
    - Machine_ID is present and non-null.
    - Timestamp is present and non-null.
    - Numeric sensor columns are numeric-compatible (float or int).
    - Machine_Failure contains only valid target values {0, 1}.

    Parameters
    ----------
    df:
        DataFrame loaded from the raw dataset.

    Returns
    -------
    dict
        ``{"valid": bool, "errors": list[str], "warnings": list[str]}``
    """
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Required columns present
    missing_cols = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing_cols:
        errors.append(f"Missing required columns: {missing_cols}")

    # 2. Unexpected extra columns (warning, not error)
    extra_cols = [c for c in df.columns if c not in EXPECTED_COLUMNS]
    if extra_cols:
        warnings.append(f"Unexpected extra columns (ignored): {extra_cols}")

    # 3. Machine_ID non-null
    if "Machine_ID" in df.columns and df["Machine_ID"].isna().any():
        errors.append("Machine_ID contains null values — cannot derive Machine_Type")

    # 4. Timestamp non-null
    if "Timestamp" in df.columns and df["Timestamp"].isna().any():
        warnings.append("Timestamp contains null values")

    # 5. Numeric sensor columns are numeric-compatible
    for col in NUMERIC_SENSOR_COLUMNS:
        if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
            errors.append(f"{col} is not numeric (dtype={df[col].dtype})")

    # 6. Machine_Failure target values
    if "Machine_Failure" in df.columns:
        unique_vals = set(df["Machine_Failure"].dropna().unique())
        invalid_target = unique_vals - VALID_MACHINE_FAILURE_VALUES
        if invalid_target:
            errors.append(f"Machine_Failure contains unexpected values: {invalid_target}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
