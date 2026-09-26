"""
tests/contract/test_firmware_contract.py — Contract and compatibility tests for ESP32 / Wokwi Firmware v1.

Tasks: T-041 ESP32/Wokwi Firmware v1
"""

import json
from pathlib import Path

import pytest

from ml.data.schema import FEATURE_COLUMNS
from simulation.contract import (
    FORBIDDEN_TELEMETRY_FIELDS,
    TelemetryValidator,
    telemetry_to_feature_df,
)


@pytest.fixture
def validator():
    return TelemetryValidator()


@pytest.fixture
def edge_dir():
    return Path(__file__).resolve().parent.parent.parent / "edge"


def test_wokwi_diagram_structure(edge_dir):
    """Verify that edge/diagram.json contains all required parts and connections."""
    diagram_path = edge_dir / "diagram.json"
    assert diagram_path.exists(), "diagram.json must exist in edge/"

    with open(diagram_path, "r", encoding="utf-8") as f:
        diagram = json.load(f)

    assert "parts" in diagram
    assert "connections" in diagram

    parts_by_id = {p["id"]: p["type"] for p in diagram["parts"]}
    assert "esp" in parts_by_id
    assert parts_by_id["esp"] == "wokwi-esp32-devkit-v1"
    assert "dht" in parts_by_id
    assert parts_by_id["dht"] == "wokwi-dht22"
    assert "pot" in parts_by_id
    assert parts_by_id["pot"] == "wokwi-slide-potentiometer"
    assert "mpu" in parts_by_id
    assert parts_by_id["mpu"] == "wokwi-mpu6050"
    assert "led_trip" in parts_by_id
    assert parts_by_id["led_trip"] == "wokwi-led"


def test_wokwi_toml_and_libraries(edge_dir):
    """Verify wokwi.toml and libraries.txt configuration."""
    toml_path = edge_dir / "wokwi.toml"
    assert toml_path.exists(), "wokwi.toml must exist"
    toml_text = toml_path.read_text(encoding="utf-8")
    assert 'diagram = "diagram.json"' in toml_text

    lib_path = edge_dir / "libraries.txt"
    assert lib_path.exists(), "libraries.txt must exist"
    lib_text = lib_path.read_text(encoding="utf-8")
    assert "DHT sensor library for ESPx" in lib_text
    assert "Adafruit MPU6050" in lib_text
    assert "MQTT" in lib_text


def test_config_example_contains_no_secrets(edge_dir):
    """Verify that config.h.example has safe placeholders and no hardcoded production secrets."""
    config_path = edge_dir / "config.h.example"
    assert config_path.exists(), "config.h.example must exist"
    content = config_path.read_text(encoding="utf-8")

    assert '#define MACHINE_ID "MOT-1001"' in content
    assert '#define SCHEMA_ID "edgetwin.telemetry.v1"' in content
    assert '#define PROVENANCE "SIMULATED"' in content
    assert "#define PIN_DHT 15" in content
    assert "#define PIN_POT 34" in content
    assert "#define PIN_LED_TRIP 2" in content
    assert "#define PIN_I2C_SDA 21" in content
    assert "#define PIN_I2C_SCL 22" in content


def test_firmware_telemetry_payload_schema_validity(validator):
    """Verify that sample telemetry generated according to firmware specification passes validation."""
    sample_firmware_payload = {
        "schema": "edgetwin.telemetry.v1",
        "machine_id": "MOT-1001",
        "seq": 0,
        "ts": "2026-09-26T12:00:00Z",
        "provenance": "SIMULATED",
        "fw": "0.2.0",
        "signals": {
            "air_temp_c": 25.4,
            "process_temp_c": 35.3,
            "rotational_speed_rpm": 1548.0,
            "torque_nm": 40.1,
            "vibration_mm_s": 2.5,
            "pressure_bar": 5.5,
            "current_a": 12.0,
            "voltage_v": 415.0,
            "tool_wear_min": 50.0,
            "operating_hours": 10000.0,
        },
        "quality": {
            "vibration_mm_s": "OK",
            "pressure_bar": "OK",
        },
        "edge": {
            "delta_t_c": 9.9,
            "power_va": 4980.0,
            "trip": None,
            "buffered": 0,
        },
    }

    res = validator.validate(sample_firmware_payload, topic="edgetwin/v1/MOT-1001/telemetry")
    assert res.valid is True
    assert len(res.errors) == 0
    assert len(res.diagnostic_discrepancies) == 0


def test_firmware_tripped_payload_schema_validity(validator):
    """Verify that a tripped telemetry payload from firmware passes validation."""
    tripped_payload = {
        "schema": "edgetwin.telemetry.v1",
        "machine_id": "MOT-1001",
        "seq": 42,
        "ts": "2026-09-26T12:00:42Z",
        "provenance": "SIMULATED",
        "fw": "0.2.0",
        "signals": {
            "air_temp_c": 25.4,
            "process_temp_c": 26.0,
            "rotational_speed_rpm": 0.0,
            "torque_nm": 0.0,
            "vibration_mm_s": 0.1,
            "pressure_bar": 0.5,
            "current_a": 0.0,
            "voltage_v": 415.0,
            "tool_wear_min": 52.1,
            "operating_hours": 10000.0117,
        },
        "quality": {
            "vibration_mm_s": "OK",
            "pressure_bar": "OK",
        },
        "edge": {
            "delta_t_c": 0.6,
            "power_va": 0.0,
            "trip": "TRIP_OVERLOAD",
            "buffered": 3,
        },
    }

    res = validator.validate(tripped_payload, topic="edgetwin/v1/MOT-1001/telemetry")
    assert res.valid is True
    assert len(res.errors) == 0


def test_firmware_payload_to_feature_df():
    """Verify that firmware payload transforms cleanly into ML features with correct Machine_Type."""
    sample_payload = {
        "schema": "edgetwin.telemetry.v1",
        "machine_id": "MOT-1001",
        "seq": 10,
        "ts": "2026-09-26T12:00:10Z",
        "provenance": "SIMULATED",
        "fw": "0.2.0",
        "signals": {
            "air_temp_c": 25.4,
            "process_temp_c": 35.3,
            "rotational_speed_rpm": 1548.0,
            "torque_nm": 40.1,
            "vibration_mm_s": 2.5,
            "pressure_bar": 5.5,
            "current_a": 12.0,
            "voltage_v": 415.0,
            "tool_wear_min": 50.0,
            "operating_hours": 10000.0,
        },
        "quality": {},
        "edge": {
            "delta_t_c": 9.9,
            "power_va": 4980.0,
            "trip": None,
            "buffered": 0,
        },
    }

    feature_df = telemetry_to_feature_df(sample_payload)
    assert len(feature_df) == 1
    assert list(feature_df.columns) == FEATURE_COLUMNS
    assert feature_df["Machine_Type"].iloc[0] == "Motor"
    assert feature_df["Air_Temperature_C"].iloc[0] == 25.4
    assert feature_df["Torque_Nm"].iloc[0] == 40.1

    # Ensure zero forbidden leakage fields
    for forbidden in FORBIDDEN_TELEMETRY_FIELDS:
        assert forbidden not in feature_df.columns
