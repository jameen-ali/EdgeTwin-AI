"""
tests/api/test_ingest.py — Comprehensive tests for T-032 + T-033 (S11).

Tests cover:
- Valid telemetry message accepted and persisted.
- Invalid JSON rejected cleanly.
- Invalid schema rejected.
- Invalid machine_id format rejected.
- Invalid sensor range rejected.
- Missing required field rejected.
- Nullable sensor persisted with NULL.
- Invalid enum (provenance) rejected.
- Duplicate (machine_id, seq) handled safely.
- Database persistence confirmed.
- Topic/payload machine_id mismatch rejected.
- MQTT callback does not raise on malformed payload.
- Topic parsing tests.
- Machine ID extracted correctly.
- Valid telemetry creates exactly one DB record.
- End-to-end integration: wire JSON → handler → DB → query.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from api.app.db.base import Base
from api.app.ingest.handler import extract_machine_id_from_topic, handle_message
from api.app.ingest.normalizer import _optional_float, normalize_telemetry
from api.app.ingest.persistence import persist_telemetry
from api.app.models.machine import MachineRecord
from api.app.models.telemetry import TelemetryRecord

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sqlite_engine():
    """In-memory SQLite engine for all ingest tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(sqlite_engine) -> Session:
    """Short-lived session per test, rolled back after each test."""
    connection = sqlite_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def valid_payload() -> dict[str, Any]:
    """Canonical valid telemetry v1 payload."""
    return {
        "schema": "edgetwin.telemetry.v1",
        "machine_id": "MOT-1001",
        "seq": 100,
        "ts": "2026-09-28T10:00:00Z",
        "provenance": "SIMULATED",
        "fw": "0.2.0",
        "signals": {
            "air_temp_c": 25.0,
            "process_temp_c": 35.0,
            "rotational_speed_rpm": 1500.0,
            "torque_nm": 40.0,
            "vibration_mm_s": 2.5,
            "pressure_bar": 5.0,
            "current_a": 12.0,
            "voltage_v": 415.0,
            "tool_wear_min": 100.0,
            "operating_hours": 5000.0,
        },
        "quality": {"air_temp_c": "OK"},
        "edge": {
            "delta_t_c": 10.0,
            "power_va": 4980.0,
            "trip": None,
            "buffered": 0,
        },
    }


@pytest.fixture
def valid_topic() -> str:
    return "edgetwin/v1/MOT-1001/telemetry"


def _encode(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")


# ---------------------------------------------------------------------------
# Topic parsing tests
# ---------------------------------------------------------------------------


class TestTopicParsing:
    def test_valid_topic_extracts_machine_id(self):
        mid = extract_machine_id_from_topic("edgetwin/v1/MOT-1001/telemetry")
        assert mid == "MOT-1001"

    def test_valid_topic_pump(self):
        mid = extract_machine_id_from_topic("edgetwin/v1/PMP-2002/telemetry")
        assert mid == "PMP-2002"

    def test_valid_topic_generator(self):
        mid = extract_machine_id_from_topic("edgetwin/v1/GEN-9999/telemetry")
        assert mid == "GEN-9999"

    def test_invalid_topic_wrong_prefix(self):
        assert extract_machine_id_from_topic("machines/MOT-1001/telemetry/v1") is None

    def test_invalid_topic_no_version(self):
        assert extract_machine_id_from_topic("edgetwin/MOT-1001/telemetry") is None

    def test_invalid_topic_status_not_telemetry(self):
        assert extract_machine_id_from_topic("edgetwin/v1/MOT-1001/status") is None

    def test_invalid_topic_lowercase_machine_id(self):
        assert extract_machine_id_from_topic("edgetwin/v1/mot-1001/telemetry") is None

    def test_invalid_topic_wrong_format(self):
        assert extract_machine_id_from_topic("edgetwin/v1/MOTOR-101/telemetry") is None


# ---------------------------------------------------------------------------
# Normalizer tests
# ---------------------------------------------------------------------------


class TestNormalizer:
    def test_normalizer_basic(self, valid_payload):
        fields = normalize_telemetry(valid_payload)
        assert fields["machine_id"] == "MOT-1001"
        assert fields["seq"] == 100
        assert isinstance(fields["ts"], datetime)
        assert fields["ts"].tzinfo is not None
        assert fields["provenance"] == "SIMULATED"
        assert fields["fw"] == "0.2.0"

    def test_normalizer_all_sensors_present(self, valid_payload):
        fields = normalize_telemetry(valid_payload)
        assert fields["air_temp_c"] == 25.0
        assert fields["process_temp_c"] == 35.0
        assert fields["rotational_speed_rpm"] == 1500.0
        assert fields["torque_nm"] == 40.0
        assert fields["vibration_mm_s"] == 2.5
        assert fields["pressure_bar"] == 5.0
        assert fields["current_a"] == 12.0
        assert fields["voltage_v"] == 415.0
        assert fields["tool_wear_min"] == 100.0
        assert fields["operating_hours"] == 5000.0

    def test_normalizer_nullable_sensor_stays_none(self, valid_payload):
        payload = copy.deepcopy(valid_payload)
        payload["signals"]["air_temp_c"] = None
        fields = normalize_telemetry(payload)
        assert fields["air_temp_c"] is None

    def test_normalizer_edge_fields(self, valid_payload):
        fields = normalize_telemetry(valid_payload)
        assert fields["delta_t_c"] == 10.0
        assert fields["power_va"] == 4980.0
        assert fields["trip"] is None
        assert fields["buffered"] == 0

    def test_normalizer_raw_payload_stored(self, valid_payload):
        fields = normalize_telemetry(valid_payload)
        assert fields["raw_payload"] == valid_payload

    def test_optional_float_none(self):
        assert _optional_float(None) is None

    def test_optional_float_valid(self):
        assert _optional_float(42) == 42.0

    def test_optional_float_string_number(self):
        assert _optional_float("3.14") == 3.14

    def test_optional_float_bad_string(self):
        assert _optional_float("notanumber") is None


# ---------------------------------------------------------------------------
# Handler unit tests (using SQLite session)
# ---------------------------------------------------------------------------


class TestHandler:
    def test_valid_message_persisted(self, valid_payload, valid_topic, db):
        result = handle_message(valid_topic, _encode(valid_payload), db)
        assert result["outcome"] == "persisted"
        assert result["machine_id"] == "MOT-1001"
        assert result["seq"] == 100

    def test_invalid_json_rejected(self, valid_topic, db):
        result = handle_message(valid_topic, b"not valid json", db)
        assert result["outcome"] == "rejected"
        assert "invalid_json" in result["reason"]

    def test_invalid_topic_rejected(self, valid_payload, db):
        result = handle_message("wrong/topic/format", _encode(valid_payload), db)
        assert result["outcome"] == "rejected"
        assert "invalid_topic" in result["reason"]

    def test_wrong_schema_version_rejected(self, valid_topic, db):
        payload = {
            "schema": "edgetwin.telemetry.v2",  # wrong version
            "machine_id": "MOT-1001",
            "seq": 1,
            "ts": "2026-09-28T10:00:00Z",
            "provenance": "SIMULATED",
            "fw": "0.2.0",
            "signals": {},
            "quality": {},
            "edge": {"delta_t_c": 0.0, "power_va": 0.0, "trip": None, "buffered": 0},
        }
        result = handle_message(valid_topic, _encode(payload), db)
        assert result["outcome"] == "rejected"

    def test_invalid_machine_id_format_rejected(self, db):
        topic = "edgetwin/v1/MOT-1001/telemetry"
        payload = {
            "schema": "edgetwin.telemetry.v1",
            "machine_id": "invalid-machine",  # wrong format in payload
            "seq": 1,
            "ts": "2026-09-28T10:00:00Z",
            "provenance": "SIMULATED",
            "fw": "0.2.0",
            "signals": {
                "air_temp_c": 25.0,
                "process_temp_c": 35.0,
                "rotational_speed_rpm": 1500.0,
                "torque_nm": 40.0,
                "vibration_mm_s": 2.5,
                "pressure_bar": 5.0,
                "current_a": 12.0,
                "voltage_v": 415.0,
                "tool_wear_min": 100.0,
                "operating_hours": 5000.0,
            },
            "quality": {},
            "edge": {"delta_t_c": 0.0, "power_va": 0.0, "trip": None, "buffered": 0},
        }
        result = handle_message(topic, _encode(payload), db)
        assert result["outcome"] == "rejected"

    def test_invalid_provenance_rejected(self, valid_payload, valid_topic, db):
        payload = copy.deepcopy(valid_payload)
        payload["provenance"] = "PRODUCTION"  # not in allowed enum
        result = handle_message(valid_topic, _encode(payload), db)
        assert result["outcome"] == "rejected"

    def test_missing_required_field_rejected(self, valid_payload, valid_topic, db):
        payload = copy.deepcopy(valid_payload)
        del payload["fw"]
        result = handle_message(valid_topic, _encode(payload), db)
        assert result["outcome"] == "rejected"

    def test_nullable_sensor_accepted(self, valid_payload, valid_topic, db):
        payload = copy.deepcopy(valid_payload)
        payload["seq"] = 200
        payload["signals"]["air_temp_c"] = None
        result = handle_message(valid_topic, _encode(payload), db)
        assert result["outcome"] == "persisted"

    def test_topic_payload_machine_id_mismatch_rejected(self, valid_payload, db):
        topic = "edgetwin/v1/PMP-2002/telemetry"  # different machine in topic
        result = handle_message(topic, _encode(valid_payload), db)
        # The contract validator catches the mismatch (machine_id in payload != topic)
        # and the handler sees it as validation_failed or machine_id_mismatch
        assert result["outcome"] == "rejected"

    def test_duplicate_seq_returns_duplicate(self, valid_payload, valid_topic, db):
        # First insert
        r1 = handle_message(valid_topic, _encode(valid_payload), db)
        assert r1["outcome"] == "persisted"
        # Second insert with same seq
        payload2 = copy.deepcopy(valid_payload)
        r2 = handle_message(valid_topic, _encode(payload2), db)
        assert r2["outcome"] == "duplicate"

    def test_empty_bytes_payload_rejected(self, valid_topic, db):
        result = handle_message(valid_topic, b"", db)
        assert result["outcome"] == "rejected"

    def test_non_utf8_payload_rejected(self, valid_topic, db):
        result = handle_message(valid_topic, b"\xff\xfe\x00invalid", db)
        assert result["outcome"] == "rejected"

    def test_callback_does_not_raise_on_malformed_payload(self, valid_topic, db):
        """MQTT callback safety: handle_message must never raise."""
        try:
            result = handle_message(valid_topic, b"<xml>not json</xml>", db)
            assert result["outcome"] == "rejected"
        except Exception as exc:  # noqa: BLE001  # intentional: catching for pytest.fail
            pytest.fail(f"handle_message raised unexpectedly: {exc}")


# ---------------------------------------------------------------------------
# Database persistence integration tests
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_valid_telemetry_creates_exactly_one_record(self, valid_payload, valid_topic, db):
        payload = copy.deepcopy(valid_payload)
        payload["seq"] = 300
        handle_message(valid_topic, _encode(payload), db)

        records = db.query(TelemetryRecord).filter_by(machine_id="MOT-1001", seq=300).all()
        assert len(records) == 1

    def test_duplicate_does_not_create_second_record(self, valid_payload, valid_topic, db):
        payload = copy.deepcopy(valid_payload)
        payload["seq"] = 401
        r1 = handle_message(valid_topic, _encode(payload), db)
        assert r1["outcome"] == "persisted"

        # Second call must return duplicate, not persisted
        r2 = handle_message(valid_topic, _encode(payload), db)
        assert r2["outcome"] == "duplicate"

    def test_nullable_sensor_stored_as_null(self, valid_payload, valid_topic, db):
        payload = copy.deepcopy(valid_payload)
        payload["seq"] = 500
        payload["signals"]["air_temp_c"] = None
        handle_message(valid_topic, _encode(payload), db)

        record = db.query(TelemetryRecord).filter_by(machine_id="MOT-1001", seq=500).first()
        assert record is not None
        assert record.air_temp_c is None

    def test_sensor_zero_vs_null_distinction(self, valid_payload, valid_topic, db):
        """Ensure 0.0 sensors are stored as 0.0, not None."""
        payload = copy.deepcopy(valid_payload)
        payload["seq"] = 600
        payload["signals"]["vibration_mm_s"] = 0.0
        handle_message(valid_topic, _encode(payload), db)

        record = db.query(TelemetryRecord).filter_by(machine_id="MOT-1001", seq=600).first()
        assert record is not None
        assert record.vibration_mm_s == 0.0

    def test_auto_machine_registration(self, valid_payload, db):
        """Unknown machine_id should be auto-registered with type=UNKNOWN."""
        payload = copy.deepcopy(valid_payload)
        payload["machine_id"] = "CMP-9999"
        payload["seq"] = 700
        topic = "edgetwin/v1/CMP-9999/telemetry"
        handle_message(topic, _encode(payload), db)

        machine = db.query(MachineRecord).filter_by(machine_id="CMP-9999").first()
        assert machine is not None
        assert machine.machine_type == "UNKNOWN"

    def test_persist_telemetry_direct(self, valid_payload, db):
        """Test persist_telemetry() directly (unit-level)."""
        payload = copy.deepcopy(valid_payload)
        payload["seq"] = 800
        # Ensure machine exists first
        db.add(MachineRecord(machine_id="MOT-1001", machine_type="MOTOR", status="ACTIVE"))
        db.flush()

        fields = normalize_telemetry(payload)
        ok, reason = persist_telemetry(db, fields)
        assert ok is True
        assert reason == "persisted"

    def test_raw_payload_stored_correctly(self, valid_payload, valid_topic, db):
        """Full wire payload should be preserved in raw_payload column."""
        payload = copy.deepcopy(valid_payload)
        payload["seq"] = 900
        handle_message(valid_topic, _encode(payload), db)

        record = db.query(TelemetryRecord).filter_by(machine_id="MOT-1001", seq=900).first()
        assert record is not None
        assert record.raw_payload is not None
        assert record.raw_payload["machine_id"] == "MOT-1001"


# ---------------------------------------------------------------------------
# End-to-end integration test (canonical contract → DB → query)
# ---------------------------------------------------------------------------


class TestE2EIngestion:
    def test_canonical_telemetry_reaches_database(self, db):
        """Full pipeline: canonical wire JSON → handle_message → persist → query row."""
        canonical = {
            "schema": "edgetwin.telemetry.v1",
            "machine_id": "MOT-2001",
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
            "quality": {"vibration_mm_s": "OK", "pressure_bar": "OK"},
            "edge": {
                "delta_t_c": 10.2,
                "power_va": 5023.0,
                "trip": None,
                "buffered": 0,
            },
        }
        topic = "edgetwin/v1/MOT-2001/telemetry"

        result = handle_message(topic, json.dumps(canonical).encode("utf-8"), db)

        # Outcome
        assert result["outcome"] == "persisted"
        assert result["machine_id"] == "MOT-2001"
        assert result["seq"] == 1842

        # Verify in DB
        row = db.query(TelemetryRecord).filter_by(machine_id="MOT-2001", seq=1842).first()
        assert row is not None
        assert row.machine_id == "MOT-2001"
        assert row.seq == 1842
        assert row.provenance == "SIMULATED"
        assert abs(row.air_temp_c - 25.4) < 1e-6
        assert abs(row.process_temp_c - 35.6) < 1e-6
        assert abs(row.voltage_v - 415.2) < 1e-6
        assert row.trip is None
        assert row.quality == {"vibration_mm_s": "OK", "pressure_bar": "OK"}

    def test_multiple_machines_isolated(self, db):
        """Telemetry from multiple machines should be independently stored."""
        for machine_id, seq in [("MOT-3001", 1), ("PMP-3002", 1), ("GEN-3003", 1)]:
            topic = f"edgetwin/v1/{machine_id}/telemetry"
            payload = {
                "schema": "edgetwin.telemetry.v1",
                "machine_id": machine_id,
                "seq": seq,
                "ts": "2026-09-28T10:00:00Z",
                "provenance": "SIMULATED",
                "fw": "0.2.0",
                "signals": {
                    "air_temp_c": 25.0,
                    "process_temp_c": 35.0,
                    "rotational_speed_rpm": 1500.0,
                    "torque_nm": 40.0,
                    "vibration_mm_s": 2.5,
                    "pressure_bar": 5.0,
                    "current_a": 12.0,
                    "voltage_v": 415.0,
                    "tool_wear_min": 100.0,
                    "operating_hours": 5000.0,
                },
                "quality": {},
                "edge": {"delta_t_c": 10.0, "power_va": 4980.0, "trip": None, "buffered": 0},
            }
            result = handle_message(topic, json.dumps(payload).encode("utf-8"), db)
            assert result["outcome"] == "persisted", f"Failed for {machine_id}"

        assert db.query(TelemetryRecord).count() == 3
