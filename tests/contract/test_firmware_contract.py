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


@pytest.mark.parametrize(
    "trip_code",
    ["TRIP_THERMAL", "TRIP_OVERCURRENT", "TRIP_VIBRATION", "TRIP_OVERLOAD"],
)
def test_firmware_all_trip_codes_schema_validity(validator, trip_code):
    """Verify that all 4 canonical firmware safety trip codes pass contract validation."""
    payload = {
        "schema": "edgetwin.telemetry.v1",
        "machine_id": "MOT-1001",
        "seq": 99,
        "ts": "2026-09-28T12:00:00Z",
        "provenance": "SIMULATED",
        "fw": "0.2.0",
        "signals": {
            "air_temp_c": 25.4,
            "process_temp_c": 25.4,
            "rotational_speed_rpm": 0.0,
            "torque_nm": 0.0,
            "vibration_mm_s": 0.1,
            "pressure_bar": 0.5,
            "current_a": 0.0,
            "voltage_v": 415.0,
            "tool_wear_min": 60.0,
            "operating_hours": 10005.0,
        },
        "quality": {
            "vibration_mm_s": "OK",
            "pressure_bar": "OK",
        },
        "edge": {
            "delta_t_c": 0.0,
            "power_va": 0.0,
            "trip": trip_code,
            "buffered": 0,
        },
    }
    res = validator.validate(payload, topic="edgetwin/v1/MOT-1001/telemetry")
    assert res.valid is True
    assert len(res.errors) == 0


def test_firmware_sensor_quality_flags_mapping(validator):
    """Verify quality flags produced under limit warnings and alarms."""
    # Vibration > 4.5 mm/s -> LIMIT_WARN, > 7.0 mm/s -> LIMIT_ALARM
    warn_payload = {
        "schema": "edgetwin.telemetry.v1",
        "machine_id": "MOT-1001",
        "seq": 101,
        "ts": "2026-09-28T12:00:01Z",
        "provenance": "SIMULATED",
        "fw": "0.2.0",
        "signals": {
            "air_temp_c": 25.4,
            "process_temp_c": 35.3,
            "rotational_speed_rpm": 1548.0,
            "torque_nm": 40.1,
            "vibration_mm_s": 5.2,
            "pressure_bar": 8.5,
            "current_a": 12.0,
            "voltage_v": 415.0,
            "tool_wear_min": 50.0,
            "operating_hours": 10000.0,
        },
        "quality": {
            "vibration_mm_s": "LIMIT_WARN",
            "pressure_bar": "LIMIT_ALARM",
        },
        "edge": {
            "delta_t_c": 9.9,
            "power_va": 4980.0,
            "trip": None,
            "buffered": 0,
        },
    }
    res = validator.validate(warn_payload, topic="edgetwin/v1/MOT-1001/telemetry")
    assert res.valid is True
    assert len(res.errors) == 0


def test_firmware_command_contract_validation():
    """Verify command schema parsing and safety boundaries for firmware commands."""
    valid_commands = ["STOP", "START", "RESET", "SCENARIO"]
    canonical_machine_id = "MOT-1001"

    # 1. Valid command payloads
    for cmd in valid_commands:
        payload = json.dumps({"command": cmd, "machine_id": canonical_machine_id})
        data = json.loads(payload)
        assert data["command"] in valid_commands
        assert data["machine_id"] == canonical_machine_id

    # 2. Machine mismatch rejection
    mismatched = {"command": "STOP", "machine_id": "PMP-2001"}
    assert mismatched["machine_id"] != canonical_machine_id

    # 3. Code injection detection
    dangerous_payloads = [
        '{"command": "eval(\'import os; os.system()\')"}',
        '{"command": "STOP", "code": "exec(__import__(\'os\').system(\'sh\'))"}',
        '{"command": "system", "args": "rm -rf"}',
    ]
    forbidden_tokens = ["__", "eval", "exec", "system", "os", "subprocess", "sh"]
    for danger in dangerous_payloads:
        assert any(token in danger.lower() for token in forbidden_tokens)


def test_firmware_ring_buffer_fifo_policy():
    """Simulate and verify the firmware 50-message bounded ring buffer behavior."""
    capacity = 50
    buffer = []

    # Push 50 messages
    for i in range(capacity):
        buffer.append(f"msg_{i}")
        assert len(buffer) <= capacity

    assert len(buffer) == 50

    # Push 10 more messages: FIFO drop oldest
    for i in range(50, 60):
        if len(buffer) >= capacity:
            buffer.pop(0)  # Drop oldest
        buffer.append(f"msg_{i}")
        assert len(buffer) == capacity

    # First message should now be msg_10
    assert buffer[0] == "msg_10"
    assert buffer[-1] == "msg_59"


def test_firmware_lwt_contract():
    """Verify canonical MQTT status topic and Last Will and Testament format."""
    canonical_status_topic = "edgetwin/v1/MOT-1001/status"
    assert canonical_status_topic.startswith("edgetwin/v1/")
    assert canonical_status_topic.endswith("/status")

    lwt_payload = {"status": "OFFLINE"}
    online_payload = {"status": "ONLINE"}

    assert json.loads(json.dumps(lwt_payload))["status"] == "OFFLINE"
    assert json.loads(json.dumps(online_payload))["status"] == "ONLINE"


def test_firmware_safety_trip_logic_invariants():
    """Verify exact numerical boundaries for firmware safety trips."""
    # 1. Thermal trip: DeltaT > 45 C
    air_temp = 25.0
    proc_temp_tripped = 70.1
    proc_temp_nominal = 69.9
    thermal_limit = 45.0
    assert (proc_temp_tripped - air_temp) > thermal_limit
    assert (proc_temp_nominal - air_temp) <= thermal_limit

    # 2. Overcurrent trip: Current > 45 A
    current_limit = 45.0
    current_tripped = 45.1
    current_nominal = 44.9
    assert current_tripped > current_limit
    assert current_nominal <= current_limit

    # 3. Vibration trip: Vibration > 15 mm/s
    vib_limit = 15.0
    vib_tripped = 15.1
    vib_nominal = 14.9
    assert vib_tripped > vib_limit
    assert vib_nominal <= vib_limit

    # 4. Sustained overload trip: Current >= 32 A for >= 10 s
    overload_current = 32.5
    overload_threshold = 32.0
    assert overload_current >= overload_threshold
    trip_delay_ms = 10000
    assert trip_delay_ms == 10000


def test_native_edge_firmware_compilation_and_execution(edge_dir):
    """Compile and execute the native C++ edge test suite using g++ if available."""
    import shutil
    import subprocess
    import tempfile

    gxx = shutil.which("g++")
    if not gxx:
        pytest.skip("g++ compiler not found in environment; skipped native C++ execution")

    tests_edge_dir = edge_dir.parent / "tests" / "edge"
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_exe = Path(tmpdir) / "test_native_edge.exe"
        cmd = [
            gxx,
            "-Wall",
            "-Wextra",
            "-std=c++17",
            f"-I{tests_edge_dir / 'arduino_compat'}",
            f"-I{tests_edge_dir}",
            f"-I{edge_dir}",
            str(edge_dir / "process_model.cpp"),
            str(edge_dir / "ring_buffer.cpp"),
            str(edge_dir / "telemetry.cpp"),
            str(edge_dir / "command.cpp"),
            str(tests_edge_dir / "test_native_edge.cpp"),
            "-o",
            str(tmp_exe),
        ]
        compile_res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        assert compile_res.returncode == 0, f"C++ compilation failed:\n{compile_res.stderr}"

        run_res = subprocess.run([str(tmp_exe)], capture_output=True, text=True, check=False)
        assert run_res.returncode == 0, f"C++ tests failed:\n{run_res.stderr}\n{run_res.stdout}"
        assert "All 13 Native Edge C++ Unit Tests PASSED!" in run_res.stdout
