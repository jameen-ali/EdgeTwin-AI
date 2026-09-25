"""
tests/contract/test_telemetry_contract.py - Tests for Telemetry Contract v1 and TelemetryValidator.

Tasks: T-020 Telemetry Contract v1
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from simulation.contract import (
    FORBIDDEN_TELEMETRY_FIELDS,
    TelemetryValidator,
)


@pytest.fixture
def valid_telemetry_payload() -> dict[str, Any]:
    """Return a canonical valid Telemetry v1 payload."""
    return {
        "schema": "edgetwin.telemetry.v1",
        "machine_id": "MOT-1001",
        "seq": 1842,
        "ts": "2026-09-24T10:15:03Z",
        "provenance": "SIMULATED",
        "fw": "0.2.0",
        "signals": {
            "air_temp_c": 25.4,
            "process_temp_c": 35.6,
            "rotational_speed_rpm": 1540.0,
            "torque_nm": 41.2,
            "vibration_mm_s": 2.6,
            "pressure_bar": 5.5,
            "current_a": 12.1,
            "voltage_v": 415.2,
            "tool_wear_min": 131.0,
            "operating_hours": 10021.5,
        },
        "quality": {
            "vibration_mm_s": "OK",
            "pressure_bar": "OK",
        },
        "edge": {
            "delta_t_c": 10.2,
            "power_va": 5023.92,
            "trip": None,
            "buffered": 0,
        },
    }


@pytest.fixture
def validator() -> TelemetryValidator:
    """Return initialized TelemetryValidator instance."""
    return TelemetryValidator()


def test_valid_telemetry_payload_passes(
    validator: TelemetryValidator,
    valid_telemetry_payload: dict[str, Any],
) -> None:
    """Test 1: Valid schema passes without error."""
    res = validator.validate(valid_telemetry_payload, topic="edgetwin/v1/MOT-1001/telemetry")
    assert res.valid is True
    assert len(res.errors) == 0


@pytest.mark.parametrize(
    "missing_field",
    ["schema", "machine_id", "seq", "ts", "provenance", "fw", "signals", "quality", "edge"],
)
def test_missing_required_fields_rejected(
    validator: TelemetryValidator,
    valid_telemetry_payload: dict[str, Any],
    missing_field: str,
) -> None:
    """Test 2: Missing required envelope fields fail validation."""
    payload = copy.deepcopy(valid_telemetry_payload)
    del payload[missing_field]
    res = validator.validate(payload)
    assert res.valid is False
    assert any("required" in err.lower() or missing_field in err for err in res.errors)


def test_invalid_schema_identifier_rejected(
    validator: TelemetryValidator,
    valid_telemetry_payload: dict[str, Any],
) -> None:
    """Test 3: Incorrect schema identifier is rejected."""
    payload = copy.deepcopy(valid_telemetry_payload)
    payload["schema"] = "edgetwin.telemetry.v2"
    res = validator.validate(payload)
    assert res.valid is False
    assert any("schema" in err.lower() for err in res.errors)


@pytest.mark.parametrize("invalid_id", ["mot-1001", "MOT1001", "TOOL-12", "123-4567", "MOTOR-1001"])
def test_invalid_machine_id_rejected(
    validator: TelemetryValidator,
    valid_telemetry_payload: dict[str, Any],
    invalid_id: str,
) -> None:
    """Test 4: Invalid machine_id pattern is rejected."""
    payload = copy.deepcopy(valid_telemetry_payload)
    payload["machine_id"] = invalid_id
    res = validator.validate(payload)
    assert res.valid is False
    assert any("machine_id" in err.lower() for err in res.errors)


@pytest.mark.parametrize(
    "invalid_ts", ["2026/09/24 10:15:03", "yesterday", "not-a-timestamp", "1609459200"]
)
def test_invalid_timestamp_rejected(
    validator: TelemetryValidator,
    valid_telemetry_payload: dict[str, Any],
    invalid_ts: str,
) -> None:
    """Test 5: Non-ISO-8601 timestamp string is rejected."""
    payload = copy.deepcopy(valid_telemetry_payload)
    payload["ts"] = invalid_ts
    res = validator.validate(payload)
    assert res.valid is False
    assert any("ts" in err.lower() for err in res.errors)


@pytest.mark.parametrize("invalid_prov", ["SYNTHETIC", "TEST", "PROD", "unknown"])
def test_invalid_provenance_rejected(
    validator: TelemetryValidator,
    valid_telemetry_payload: dict[str, Any],
    invalid_prov: str,
) -> None:
    """Test 6: Invalid provenance enum is rejected."""
    payload = copy.deepcopy(valid_telemetry_payload)
    payload["provenance"] = invalid_prov
    res = validator.validate(payload)
    assert res.valid is False
    assert any("provenance" in err.lower() for err in res.errors)


@pytest.mark.parametrize("prov", ["SIMULATED", "REPLAY", "REAL"])
def test_all_valid_provenance_accepted(
    validator: TelemetryValidator,
    valid_telemetry_payload: dict[str, Any],
    prov: str,
) -> None:
    """Test 6b: All three supported provenance types pass."""
    payload = copy.deepcopy(valid_telemetry_payload)
    payload["provenance"] = prov
    res = validator.validate(payload)
    assert res.valid is True


def test_invalid_types_rejected(
    validator: TelemetryValidator,
    valid_telemetry_payload: dict[str, Any],
) -> None:
    """Test 7: Type mismatches (e.g. string for numeric sensor) are rejected."""
    payload = copy.deepcopy(valid_telemetry_payload)
    payload["signals"]["air_temp_c"] = "hot"
    res = validator.validate(payload)
    assert res.valid is False
    assert any("air_temp_c" in err for err in res.errors)


def test_negative_sequence_rejected(
    validator: TelemetryValidator,
    valid_telemetry_payload: dict[str, Any],
) -> None:
    """Test 8: Negative sequence counter is rejected."""
    payload = copy.deepcopy(valid_telemetry_payload)
    payload["seq"] = -1
    res = validator.validate(payload)
    assert res.valid is False
    assert any("seq" in err for err in res.errors)


def test_null_sensor_values_allowed_and_flagged_missing(
    validator: TelemetryValidator,
    valid_telemetry_payload: dict[str, Any],
) -> None:
    """Test 9 & 10: Null sensor values are valid JSON and assigned MISSING quality."""
    payload = copy.deepcopy(valid_telemetry_payload)
    payload["signals"]["vibration_mm_s"] = None
    payload["signals"]["pressure_bar"] = None

    res = validator.validate(payload)
    assert res.valid is True
    assert res.quality_flags["vibration_mm_s"] == "MISSING"
    assert res.quality_flags["pressure_bar"] == "MISSING"
    assert res.quality_flags["air_temp_c"] == "OK"


def test_out_of_range_values_flagged_and_not_clipped(
    validator: TelemetryValidator,
    valid_telemetry_payload: dict[str, Any],
) -> None:
    """Test 11 & 12: Out-of-range sensor values flagged OUT_OF_RANGE and NOT clipped."""
    payload = copy.deepcopy(valid_telemetry_payload)
    # Voltage range is [300.0, 500.0]; test 520.0 V
    payload["signals"]["voltage_v"] = 520.0
    # Vibration range is [0.0, 20.0]; test 25.5 mm/s
    payload["signals"]["vibration_mm_s"] = 25.5

    res = validator.validate(payload)
    assert res.valid is True  # Ingestible with warnings
    assert res.quality_flags["voltage_v"] == "OUT_OF_RANGE"
    assert res.quality_flags["vibration_mm_s"] == "OUT_OF_RANGE"
    # Verify raw values remained unchanged (not clipped)
    assert payload["signals"]["voltage_v"] == 520.0
    assert payload["signals"]["vibration_mm_s"] == 25.5
    assert len(res.warnings) >= 2


@pytest.mark.parametrize("forbidden", list(FORBIDDEN_TELEMETRY_FIELDS))
def test_forbidden_leakage_fields_rejected(
    validator: TelemetryValidator,
    valid_telemetry_payload: dict[str, Any],
    forbidden: str,
) -> None:
    """Test 13: Target and administrative leakage fields are rejected."""
    # Test at payload root
    payload1 = copy.deepcopy(valid_telemetry_payload)
    payload1[forbidden] = "leakage"
    res1 = validator.validate(payload1)
    assert res1.valid is False
    assert any(forbidden in err for err in res1.errors)

    # Test in signals block
    payload2 = copy.deepcopy(valid_telemetry_payload)
    payload2["signals"][forbidden] = 1
    res2 = validator.validate(payload2)
    assert res2.valid is False
    assert any(forbidden in err for err in res2.errors)


def test_mqtt_topic_machine_id_mismatch_rejected(
    validator: TelemetryValidator,
    valid_telemetry_payload: dict[str, Any],
) -> None:
    """Test 14: MQTT topic machine ID mismatch is rejected."""
    res = validator.validate(valid_telemetry_payload, topic="edgetwin/v1/CNC-2002/telemetry")
    assert res.valid is False
    assert any("Machine ID mismatch" in err for err in res.errors)


@pytest.mark.parametrize(
    "malformed_input",
    ["{invalid json", "", 12345, None, "plain string", '{"schema": }'],
)
def test_malformed_input_does_not_crash(
    validator: TelemetryValidator,
    malformed_input: Any,
) -> None:
    """Test 15: Malformed payloads return valid=False without crashing."""
    res = validator.validate(malformed_input)
    assert res.valid is False
    assert len(res.errors) > 0


def test_diagnostic_discrepancy_detection(
    validator: TelemetryValidator,
    valid_telemetry_payload: dict[str, Any],
) -> None:
    """Test edge vs cloud physics diagnostic discrepancy detection."""
    payload = copy.deepcopy(valid_telemetry_payload)
    # process=35.6, air=25.4 -> cloud delta_t = 10.2
    # simulate edge bug where edge delta_t is 15.0 (diff = 4.8 > 0.2 tolerance)
    payload["edge"]["delta_t_c"] = 15.0

    res = validator.validate(payload)
    assert res.valid is True  # Still valid for ingestion
    assert "delta_t_c" in res.diagnostic_discrepancies
    assert any("Delta_T discrepancy" in w for w in res.warnings)
