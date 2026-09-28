"""Tests for Telemetry persistence from canonical edgetwin.telemetry.v1 payloads."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from api.app.db.base import Base
from api.app.models import MachineRecord, TelemetryRecord
from simulation.contract import TelemetryValidator


@pytest.fixture
def db_session():
    """Create in-memory database fixture."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_persist_valid_telemetry_payload(db_session: Session):
    """Verify persisting a valid telemetry message conforming to edgetwin.telemetry.v1."""
    # Ensure machine exists
    machine = MachineRecord(machine_id="MOT-1001", machine_type="Motor", status="RUNNING")
    db_session.add(machine)
    db_session.commit()

    payload = {
        "schema": "edgetwin.telemetry.v1",
        "machine_id": "MOT-1001",
        "seq": 42,
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

    # Validate using authoritative TelemetryValidator
    validator = TelemetryValidator()
    result = validator.validate(payload, topic="edgetwin/v1/MOT-1001/telemetry")
    assert result.valid is True

    # Map validated payload to database entity
    signals = payload["signals"]
    edge = payload["edge"]
    telemetry_rec = TelemetryRecord(
        machine_id=payload["machine_id"],
        seq=payload["seq"],
        ts=datetime.fromisoformat(payload["ts"]),
        provenance=payload["provenance"],
        fw=payload["fw"],
        air_temp_c=signals["air_temp_c"],
        process_temp_c=signals["process_temp_c"],
        rotational_speed_rpm=signals["rotational_speed_rpm"],
        torque_nm=signals["torque_nm"],
        vibration_mm_s=signals["vibration_mm_s"],
        pressure_bar=signals["pressure_bar"],
        current_a=signals["current_a"],
        voltage_v=signals["voltage_v"],
        tool_wear_min=signals["tool_wear_min"],
        operating_hours=signals["operating_hours"],
        quality=payload["quality"],
        delta_t_c=edge["delta_t_c"],
        power_va=edge["power_va"],
        trip=edge["trip"],
        buffered=edge["buffered"],
        raw_payload=payload,
    )

    db_session.add(telemetry_rec)
    db_session.commit()

    saved = db_session.get(TelemetryRecord, telemetry_rec.id)
    assert saved is not None
    assert saved.machine_id == "MOT-1001"
    assert saved.seq == 42
    assert saved.air_temp_c == 25.4
    assert saved.quality == {"vibration_mm_s": "OK", "pressure_bar": "OK"}
    assert saved.delta_t_c == 9.9


def test_persist_telemetry_with_null_sensors(db_session: Session):
    """Verify storing telemetry when sensor channels are null (missing sensors)."""
    machine = MachineRecord(machine_id="PMP-1002", machine_type="Pump", status="RUNNING")
    db_session.add(machine)
    db_session.commit()

    telemetry_rec = TelemetryRecord(
        machine_id="PMP-1002",
        seq=1,
        ts=datetime.now(UTC),
        provenance="SIMULATED",
        fw="0.2.0",
        air_temp_c=25.0,
        process_temp_c=None,  # Missing sensor
        rotational_speed_rpm=1500.0,
        torque_nm=None,  # Missing sensor
        vibration_mm_s=2.5,
        pressure_bar=5.0,
        current_a=None,
        voltage_v=415.0,
        tool_wear_min=10.0,
        operating_hours=100.0,
        quality={"process_temp_c": "MISSING", "torque_nm": "MISSING"},
        delta_t_c=None,
        power_va=None,
        trip=None,
        buffered=0,
    )

    db_session.add(telemetry_rec)
    db_session.commit()

    saved = db_session.get(TelemetryRecord, telemetry_rec.id)
    assert saved is not None
    assert saved.process_temp_c is None
    assert saved.torque_nm is None
    assert saved.quality["process_temp_c"] == "MISSING"


def test_forbidden_leakage_fields_rejected():
    """Verify that forbidden ML target and leakage fields are rejected by validator."""
    forbidden_payload = {
        "schema": "edgetwin.telemetry.v1",
        "machine_id": "MOT-1001",
        "seq": 1,
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
        "quality": {},
        "edge": {"delta_t_c": 9.9, "power_va": 4980.0, "trip": None, "buffered": 0},
        "Failure_Type": "Heat Dissipation Failure",  # FORBIDDEN LEAKAGE
    }

    validator = TelemetryValidator()
    result = validator.validate(forbidden_payload, topic="edgetwin/v1/MOT-1001/telemetry")
    assert result.valid is False
    assert any(
        "forbidden" in str(err).lower() or "additional" in str(err).lower() for err in result.errors
    )
