"""
simulation/contract.py — EdgeTwin AI Telemetry Contract v1 and Boundary Validator.

Tasks: T-020 Telemetry Contract v1

Provides:
- TelemetryValidator: Validates JSON/dict messages against telemetry.v1.schema.json,
  enforces topic-payload consistency, flags out-of-range sensor values, sets missing-value
  quality flags, checks for forbidden leakage fields, and runs diagnostic comparisons.
- TelemetryValidationResult: Structured result reporting validity, errors, warnings,
  quality flags, and diagnostic discrepancies.
- telemetry_to_feature_df: Adapter converting validated wire telemetry payloads into the
  exact 11-column ML feature DataFrame (10 raw sensors + Machine_Type) required by the
  frozen champion model (models:/edgetwin-risk@champion).

Authoritative imports:
- MACHINE_ID_PREFIX_MAP and SENSOR_RANGES are imported directly from ml.data.schema.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import jsonschema
import numpy as np
import pandas as pd

from ml.data.features import validate_no_leakage
from ml.data.schema import (
    FEATURE_COLUMNS,
    MACHINE_ID_PREFIX_MAP,
    SENSOR_RANGES,
)

logger = logging.getLogger(__name__)

SCHEMA_ID: str = "edgetwin.telemetry.v1"
DEFAULT_SCHEMA_PATH: Path = (
    Path(__file__).resolve().parent.parent / "docs" / "api" / "telemetry.v1.schema.json"
)

#: Maps wire-format signal keys to canonical ML feature column names.
SIGNAL_TO_FEATURE_MAP: dict[str, str] = {
    "air_temp_c": "Air_Temperature_C",
    "process_temp_c": "Process_Temperature_C",
    "rotational_speed_rpm": "Rotational_Speed_RPM",
    "torque_nm": "Torque_Nm",
    "vibration_mm_s": "Vibration_mm_s",
    "pressure_bar": "Pressure_bar",
    "current_a": "Current_A",
    "voltage_v": "Voltage_V",
    "tool_wear_min": "Tool_Wear_Min",
    "operating_hours": "Operating_Hours",
}

#: Reverse map from canonical ML feature column names to wire-format signal keys.
FEATURE_TO_SIGNAL_MAP: dict[str, str] = {v: k for k, v in SIGNAL_TO_FEATURE_MAP.items()}

#: Fields that must NEVER be accepted in telemetry messages (leakage / dataset artifacts).
FORBIDDEN_TELEMETRY_FIELDS: set[str] = {
    "Failure_Type",
    "Machine_Failure",
    "Sensor_Batch_Code",
    "Checksum_Flag",
}

#: Diagnostic tolerances for comparing edge vs cloud derived physics.
DELTA_T_DIAGNOSTIC_TOLERANCE_C: float = 0.2
POWER_DIAGNOSTIC_TOLERANCE_VA: float = 5.0

_TOPIC_REGEX = re.compile(r"^edgetwin/v[0-9]+/([A-Z]{3}-[0-9]{4})/telemetry$")


def extract_machine_id_from_topic(topic: str) -> str | None:
    """Extract machine_id from an MQTT topic string, or return raw string if formatted as an ID."""
    match = _TOPIC_REGEX.match(topic)
    if match:
        return match.group(1)
    if re.match(r"^[A-Z]{3}-[0-9]{4}$", topic):
        return topic
    return None


@dataclass
class TelemetryValidationResult:
    """Structured result of boundary telemetry validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    quality_flags: dict[str, str] = field(default_factory=dict)
    diagnostic_discrepancies: dict[str, str] = field(default_factory=dict)


class TelemetryValidator:
    """Boundary validator for EdgeTwin AI Telemetry Contract v1."""

    def __init__(self, schema_path: Path | str | None = None) -> None:
        self.schema_path = Path(schema_path or DEFAULT_SCHEMA_PATH)
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Telemetry schema not found at {self.schema_path}")

        with open(self.schema_path, "r", encoding="utf-8") as f:
            self.schema_doc = json.load(f)

        format_checker = getattr(jsonschema.Draft202012Validator, "FORMAT_CHECKER", None)
        self.validator = jsonschema.Draft202012Validator(
            self.schema_doc,
            format_checker=format_checker,
        )

    def validate(
        self,
        payload: Any,
        topic: str | None = None,
    ) -> TelemetryValidationResult:
        """Validate a telemetry payload against the contract.

        Parameters
        ----------
        payload:
            Dictionary or JSON string containing the telemetry message.
        topic:
            Optional MQTT topic string (e.g. 'edgetwin/v1/MOT-1001/telemetry').

        Returns
        -------
        TelemetryValidationResult
            Detailed validation result with errors, warnings, quality flags, and diagnostic info.
        """
        errors: list[str] = []
        warnings: list[str] = []
        quality_flags: dict[str, str] = {}
        diagnostic_discrepancies: dict[str, str] = {}

        # 1. Decode string if raw JSON string passed
        data: dict[str, Any]
        if isinstance(payload, str):
            try:
                data = json.loads(payload)
            except (json.JSONDecodeError, TypeError) as exc:
                return TelemetryValidationResult(
                    valid=False,
                    errors=[f"Malformed JSON payload: {exc}"],
                )
        elif isinstance(payload, dict):
            data = payload
        else:
            return TelemetryValidationResult(
                valid=False,
                errors=[f"Expected dict or JSON string, got {type(payload).__name__}"],
            )

        # 2. Check forbidden leakage fields anywhere in the payload
        for forbidden in FORBIDDEN_TELEMETRY_FIELDS:
            if forbidden in data:
                errors.append(
                    f"Forbidden leakage field '{forbidden}' found in telemetry payload root"
                )
            if (
                "signals" in data
                and isinstance(data["signals"], dict)
                and forbidden in data["signals"]
            ):
                errors.append(f"Forbidden leakage field '{forbidden}' found in telemetry signals")

        # 3. Explicit ISO-8601 timestamp check
        ts_val = data.get("ts")
        if ts_val is not None:
            if not isinstance(ts_val, str):
                errors.append(f"Timestamp 'ts' must be a string, got {type(ts_val).__name__}")
            else:
                try:
                    _ = datetime.fromisoformat(ts_val)
                except ValueError:
                    errors.append(f"Invalid timestamp format '{ts_val}'; must be ISO-8601 UTC")

        # 4. JSON Schema structural validation
        schema_errors = list(self.validator.iter_errors(data))
        if schema_errors:
            for err in schema_errors:
                field_path = ".".join(str(p) for p in err.absolute_path) or "root"
                errors.append(f"Schema violation at '{field_path}': {err.message}")

        # If fatal schema errors exist, return early before deep inspections
        if errors:
            return TelemetryValidationResult(
                valid=False,
                errors=errors,
                warnings=warnings,
                quality_flags=quality_flags,
                diagnostic_discrepancies=diagnostic_discrepancies,
            )

        # 4. Topic-payload machine_id consistency check
        payload_machine_id = data.get("machine_id", "")
        if topic is not None:
            topic_machine_id = extract_machine_id_from_topic(topic)
            if topic_machine_id and topic_machine_id != payload_machine_id:
                errors.append(
                    f"Machine ID mismatch: topic '{topic_machine_id}' != payload '{payload_machine_id}'"
                )

        # 5. Machine_ID prefix check
        prefix = payload_machine_id[:3] if len(payload_machine_id) >= 3 else ""
        if prefix not in MACHINE_ID_PREFIX_MAP:
            warnings.append(
                f"Unknown Machine_ID prefix '{prefix}' for '{payload_machine_id}'; will map to 'Unknown'"
            )

        # 6. Sensor range checks and quality flag determination
        signals = data.get("signals", {})
        existing_quality = data.get("quality", {})

        for signal_key, feature_col in SIGNAL_TO_FEATURE_MAP.items():
            val = signals.get(signal_key)
            if val is None:
                quality_flags[signal_key] = "MISSING"
            else:
                lo, hi = SENSOR_RANGES[feature_col]
                num_val = float(val)
                if not (lo <= num_val <= hi):
                    quality_flags[signal_key] = "OUT_OF_RANGE"
                    warnings.append(
                        f"Signal '{signal_key}' value {num_val} is out of authoritative range [{lo}, {hi}]"
                    )
                else:
                    # Retain edge flag if already non-OK, otherwise mark OK
                    quality_flags[signal_key] = existing_quality.get(signal_key, "OK")

        # 7. Edge vs Cloud Physics Diagnostic Comparison
        edge_block = data.get("edge", {})
        air_temp = signals.get("air_temp_c")
        proc_temp = signals.get("process_temp_c")
        voltage = signals.get("voltage_v")
        current = signals.get("current_a")

        # Delta T comparison
        if air_temp is not None and proc_temp is not None:
            cloud_delta_t = float(proc_temp) - float(air_temp)
            edge_delta_t = edge_block.get("delta_t_c")
            if edge_delta_t is not None:
                diff_dt = abs(cloud_delta_t - float(edge_delta_t))
                if diff_dt > DELTA_T_DIAGNOSTIC_TOLERANCE_C:
                    msg = (
                        f"Delta_T discrepancy: cloud={cloud_delta_t:.2f} °C, "
                        f"edge={edge_delta_t:.2f} °C (diff={diff_dt:.2f} °C > {DELTA_T_DIAGNOSTIC_TOLERANCE_C} °C)"
                    )
                    diagnostic_discrepancies["delta_t_c"] = msg
                    warnings.append(msg)

        # Apparent Power comparison
        if voltage is not None and current is not None:
            cloud_power = float(voltage) * float(current)
            edge_power = edge_block.get("power_va")
            if edge_power is not None:
                diff_power = abs(cloud_power - float(edge_power))
                if diff_power > POWER_DIAGNOSTIC_TOLERANCE_VA:
                    msg = (
                        f"Power_VA discrepancy: cloud={cloud_power:.2f} VA, "
                        f"edge={edge_power:.2f} VA (diff={diff_power:.2f} VA > {POWER_DIAGNOSTIC_TOLERANCE_VA} VA)"
                    )
                    diagnostic_discrepancies["power_va"] = msg
                    warnings.append(msg)

        return TelemetryValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            quality_flags=quality_flags,
            diagnostic_discrepancies=diagnostic_discrepancies,
        )


def telemetry_to_feature_df(
    payload: dict[str, Any] | list[dict[str, Any]],
) -> pd.DataFrame:
    """Convert validated telemetry payload(s) into the 11-column base ML feature DataFrame.

    Extracts exactly the 10 raw sensors + Machine_Type.
    Converts null sensor values to np.nan.
    Excludes machine_id, ts, seq, provenance, fw, quality, and edge diagnostics.
    Enforces validate_no_leakage().

    Parameters
    ----------
    payload:
        Single telemetry dictionary or list of telemetry dictionaries.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns matching FEATURE_COLUMNS from ml.data.schema:
        ['Air_Temperature_C', 'Process_Temperature_C', 'Rotational_Speed_RPM',
         'Torque_Nm', 'Vibration_mm_s', 'Pressure_bar', 'Current_A', 'Voltage_V',
         'Tool_Wear_Min', 'Operating_Hours', 'Machine_Type']
    """
    messages = [payload] if isinstance(payload, dict) else payload

    rows: list[dict[str, Any]] = []
    for msg in messages:
        signals = msg.get("signals", {})
        machine_id = str(msg.get("machine_id", ""))
        prefix = machine_id[:3]
        machine_type = MACHINE_ID_PREFIX_MAP.get(prefix, "Unknown")

        row: dict[str, Any] = {}
        for sig_key, feat_col in SIGNAL_TO_FEATURE_MAP.items():
            val = signals.get(sig_key)
            row[feat_col] = float(val) if val is not None else np.nan

        row["Machine_Type"] = machine_type
        rows.append(row)

    df = pd.DataFrame(rows)

    # Reorder columns strictly to match canonical FEATURE_COLUMNS
    ordered_cols = [c for c in FEATURE_COLUMNS if c in df.columns]
    df = df[ordered_cols]

    # Enforce strict leakage guard: no forbidden columns
    validate_no_leakage(df, context="telemetry_to_feature_df")

    return df
