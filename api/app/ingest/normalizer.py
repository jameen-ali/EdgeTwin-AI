"""
api/app/ingest/normalizer.py — Telemetry payload normalizer.

Converts a validated wire-format telemetry dict into a TelemetryRecord-ready
dict, ready for insertion into the database.  This module is a pure function
layer with no database or MQTT dependencies.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def normalize_telemetry(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert a validated telemetry v1 dict to a TelemetryRecord field dict.

    Parameters
    ----------
    payload:
        A validated telemetry v1 dict (from simulation.contract.TelemetryValidator).

    Returns
    -------
    dict[str, Any]
        Keyword arguments for constructing TelemetryRecord (minus relationships).
        Sensor values that are ``null``/None remain None; they are NOT replaced with 0.
    """
    signals: dict[str, Any] = payload.get("signals") or {}
    edge: dict[str, Any] = payload.get("edge") or {}

    # Parse timestamp; fromisoformat handles Z suffix on Python 3.11+
    ts_raw: str = payload["ts"]
    try:
        ts: datetime = datetime.fromisoformat(ts_raw)
        if ts.tzinfo is None:
            # Treat naive timestamps as UTC
            ts = ts.replace(tzinfo=UTC)
    except ValueError:
        # Contract already validated the timestamp; raise clearly if somehow wrong
        raise ValueError(f"normalizer: unparseable timestamp '{ts_raw}'")

    fw_raw = payload.get("fw", "0.0.0")
    # fw may be a dict (firmware info block) or a plain semver string
    if isinstance(fw_raw, dict):
        fw: str = fw_raw.get("version", "0.0.0")
    else:
        fw = str(fw_raw)

    return {
        "machine_id": payload["machine_id"],
        "seq": int(payload["seq"]),
        "ts": ts,
        "provenance": payload["provenance"],
        "fw": fw,
        # 10 raw sensor signals — None allowed (never replace with 0)
        "air_temp_c": _optional_float(signals.get("air_temp_c")),
        "process_temp_c": _optional_float(signals.get("process_temp_c")),
        "rotational_speed_rpm": _optional_float(signals.get("rotational_speed_rpm")),
        "torque_nm": _optional_float(signals.get("torque_nm")),
        "vibration_mm_s": _optional_float(signals.get("vibration_mm_s")),
        "pressure_bar": _optional_float(signals.get("pressure_bar")),
        "current_a": _optional_float(signals.get("current_a")),
        "voltage_v": _optional_float(signals.get("voltage_v")),
        "tool_wear_min": _optional_float(signals.get("tool_wear_min")),
        "operating_hours": _optional_float(signals.get("operating_hours")),
        # Quality flags (JSON blob)
        "quality": payload.get("quality"),
        # Edge diagnostics (for audit; NOT used as ML source of truth)
        "delta_t_c": _optional_float(edge.get("delta_t_c")),
        "power_va": _optional_float(edge.get("power_va")),
        "trip": edge.get("trip"),
        "buffered": int(edge.get("buffered") or 0),
        # Full raw payload stored for auditability
        "raw_payload": payload,
    }


def _optional_float(value: Any) -> float | None:
    """Return float(value) or None, never coercing missing/null to 0."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
