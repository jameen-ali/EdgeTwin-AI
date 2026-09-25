"""
ml/data/engineering.py - EdgeTwin AI physics-derived feature engineering.

T-012: Adds three optional physics-derived columns to a prepared DataFrame.

Feature sets
------------
base10  (11 cols)  - the 10 numeric sensors + Machine_Type from T-011.
                     This is the default S03 contract; no new columns.
+physics (14 cols) - base10 + 3 physics-derived columns:
                       Delta_T_C       = Process_Temperature_C - Air_Temperature_C
                       Apparent_Power_VA = Voltage_V * Current_A
                       Mech_Power_W    = Torque_Nm * Rotational_Speed_RPM * 2*pi/60
+wear_rate (15 cols) - +physics + Wear_Rate (Tool_Wear_Min / Operating_Hours)

Engineering rules
-----------------
- All derivations are pure arithmetic on existing columns — zero information
  from the target or from external data.
- NaN in any input column propagates to NaN in the derived output.
- Divide-by-zero in Wear_Rate (Operating_Hours == 0) produces NaN, not inf.
- Derivations are applied AFTER the train/val/test split, to each partition
  independently — no cross-partition information is required.
- The function only ADDS columns; it never drops or modifies existing columns.

Formula documentation
---------------------
Delta_T_C:
    Temperature difference (Kelvin = Celsius difference).
    Rationale: elevated process-vs-ambient differential correlates with
    heat-dissipation failures.  Formula: Process_Temperature_C - Air_Temperature_C

Apparent_Power_VA:
    Approximate electrical apparent power.
    Rationale: power anomalies are a documented failure precursor in the dataset.
    Formula: Voltage_V * Current_A  (VA; not corrected for power factor)

Mech_Power_W:
    Approximate shaft mechanical power.
    Rationale: excessive torque at given RPM is a precursor to overstraining.
    Formula: Torque_Nm * (Rotational_Speed_RPM * 2*pi / 60)
    Units: Newton-metres * radians/second = Watts

Wear_Rate:
    Normalised tool-wear accumulation.
    Rationale: absolute Tool_Wear_Min is already a feature; this ratio adds
    information about wear relative to total runtime.  Guarded for zero
    Operating_Hours.
    Formula: Tool_Wear_Min / Operating_Hours  (min/hr; dimensionless ratio)

Leakage safety
--------------
Failure_Type, Machine_ID, Timestamp, Sensor_Batch_Code, Checksum_Flag are
NOT used and NOT read by this module.

Author: T-012 / S04
"""

from __future__ import annotations

import math

import pandas as pd

# ---------------------------------------------------------------------------
# Constants — engineered column names
# ---------------------------------------------------------------------------

DELTA_T_COL: str = "Delta_T_C"
APPARENT_POWER_COL: str = "Apparent_Power_VA"
MECH_POWER_COL: str = "Mech_Power_W"
WEAR_RATE_COL: str = "Wear_Rate"

#: Ordered list of physics-derived column names (not including Wear_Rate).
PHYSICS_COLS: list[str] = [DELTA_T_COL, APPARENT_POWER_COL, MECH_POWER_COL]

#: All engineered columns (physics + wear_rate).
ENGINEERED_COLS: list[str] = PHYSICS_COLS + [WEAR_RATE_COL]

# ---------------------------------------------------------------------------
# Feature-set definitions
# ---------------------------------------------------------------------------

#: The three supported feature-set identifiers.
FEATURE_SET_BASE = "base10"
FEATURE_SET_PHYSICS = "+physics"
FEATURE_SET_WEAR_RATE = "+wear_rate"

VALID_FEATURE_SETS: tuple[str, ...] = (
    FEATURE_SET_BASE,
    FEATURE_SET_PHYSICS,
    FEATURE_SET_WEAR_RATE,
)

# ---------------------------------------------------------------------------
# Engineered feature derivation
# ---------------------------------------------------------------------------

_TWO_PI_OVER_60: float = 2.0 * math.pi / 60.0  # constant for RPM -> rad/s


def add_physics_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add Delta_T_C, Apparent_Power_VA, and Mech_Power_W to *df*.

    NaN propagates from any missing input.  The original DataFrame is not
    modified; a copy is returned.

    Parameters
    ----------
    df:
        DataFrame containing at minimum:
        ``Process_Temperature_C``, ``Air_Temperature_C``,
        ``Voltage_V``, ``Current_A``,
        ``Torque_Nm``, ``Rotational_Speed_RPM``.

    Returns
    -------
    pd.DataFrame
        Copy of *df* with three additional columns appended.
    """
    df = df.copy()
    df[DELTA_T_COL] = df["Process_Temperature_C"] - df["Air_Temperature_C"]
    df[APPARENT_POWER_COL] = df["Voltage_V"] * df["Current_A"]
    df[MECH_POWER_COL] = df["Torque_Nm"] * (df["Rotational_Speed_RPM"] * _TWO_PI_OVER_60)
    return df


def add_wear_rate(df: pd.DataFrame) -> pd.DataFrame:
    """Add Wear_Rate = Tool_Wear_Min / Operating_Hours to *df*.

    Zero Operating_Hours produces NaN (not inf).
    NaN in either input column propagates to NaN in Wear_Rate.

    Parameters
    ----------
    df:
        DataFrame containing ``Tool_Wear_Min`` and ``Operating_Hours``.

    Returns
    -------
    pd.DataFrame
        Copy of *df* with ``Wear_Rate`` appended.
    """
    df = df.copy()
    # Safe division: where Operating_Hours == 0 or is NaN, produce NaN.
    operating_hours = df["Operating_Hours"].replace(0, float("nan"))
    df[WEAR_RATE_COL] = df["Tool_Wear_Min"] / operating_hours
    return df


def apply_feature_set(df: pd.DataFrame, feature_set: str) -> pd.DataFrame:
    """Apply the named feature-set transformation to *df*.

    Parameters
    ----------
    df:
        Prepared DataFrame (may include all 17 columns or a subset).
    feature_set:
        One of ``"base10"``, ``"+physics"``, or ``"+wear_rate"``.

    Returns
    -------
    pd.DataFrame
        Copy of *df* with any new engineered columns appended.
        Returns an unchanged copy for ``"base10"``.

    Raises
    ------
    ValueError
        If *feature_set* is not one of the valid identifiers.
    """
    if feature_set not in VALID_FEATURE_SETS:
        raise ValueError(
            f"Unknown feature_set '{feature_set}'. "
            f"Valid options: {VALID_FEATURE_SETS}"
        )
    if feature_set == FEATURE_SET_BASE:
        return df.copy()
    df = add_physics_features(df)
    if feature_set == FEATURE_SET_WEAR_RATE:
        df = add_wear_rate(df)
    return df


def get_feature_cols_for_set(
    base_feature_cols: list[str],
    feature_set: str,
) -> list[str]:
    """Return the ordered feature column list for a given feature set.

    Parameters
    ----------
    base_feature_cols:
        The 11 S03 base feature columns from ``get_feature_columns()``.
    feature_set:
        One of the valid feature-set identifiers.

    Returns
    -------
    list[str]
        Full ordered column list for that feature set.
    """
    if feature_set == FEATURE_SET_BASE:
        return list(base_feature_cols)
    cols = list(base_feature_cols) + PHYSICS_COLS
    if feature_set == FEATURE_SET_WEAR_RATE:
        cols = cols + [WEAR_RATE_COL]
    return cols
