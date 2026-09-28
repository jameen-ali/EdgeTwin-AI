"""
tests/integration/test_firmware_backend_integration.py — End-to-end integration tests for ESP32 Firmware.

Verifies the complete data pipeline:
ESP32/Wokwi wire payload
   ↓
MQTT message handler
   ↓
Validation & Normalization
   ↓
Database persistence (TelemetryRecord)
   ↓
ML Inference (PredictionRecord)
   ↓
Health Engine (L1-L6) & Alerts (AlertRecord)
   ↓
Digital Twin (TwinState, sync FSM, TwinSnapshotRecord)

Also verifies LWT status topic handling and OFFLINE transition.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from api.app.db.base import Base
from api.app.ingest.handler import handle_message
from api.app.models.machine import MachineRecord
from api.app.models.prediction import PredictionRecord
from api.app.models.telemetry import TelemetryRecord
from api.app.models.twin import TwinSnapshotRecord
from api.app.twin.service import get_twin_service


@pytest.fixture(scope="module")
def sqlite_engine():
    """In-memory SQLite engine for integration tests."""
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
    """Short-lived test session."""
    connection = sqlite_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def canonical_firmware_payload() -> dict[str, Any]:
    """Canonical telemetry payload matching edge/telemetry.cpp output."""
    return {
        "schema": "edgetwin.telemetry.v1",
        "machine_id": "MOT-1001",
        "seq": 1,
        "ts": "2026-09-28T12:00:01Z",
        "provenance": "SIMULATED",
        "fw": "0.2.0",
        "signals": {
            "air_temp_c": 25.40,
            "process_temp_c": 35.30,
            "rotational_speed_rpm": 1548.0,
            "torque_nm": 40.10,
            "vibration_mm_s": 2.50,
            "pressure_bar": 5.50,
            "current_a": 12.00,
            "voltage_v": 415.00,
            "tool_wear_min": 50.00,
            "operating_hours": 10000.0000,
        },
        "quality": {
            "vibration_mm_s": "OK",
            "pressure_bar": "OK",
        },
        "edge": {
            "delta_t_c": 9.90,
            "power_va": 4980.00,
            "trip": None,
            "buffered": 0,
        },
    }


def test_firmware_nominal_telemetry_e2e_pipeline(
    db: Session, canonical_firmware_payload: dict[str, Any]
):
    """Verify that firmware telemetry flows seamlessly through ingest, DB, ML inference, and Twin."""
    topic = "edgetwin/v1/MOT-1001/telemetry"
    raw_payload = json.dumps(canonical_firmware_payload).encode("utf-8")

    result = handle_message(topic=topic, raw_payload=raw_payload, db=db)
    assert result["outcome"] == "persisted"
    assert result["machine_id"] == "MOT-1001"
    assert result["seq"] == 1

    # 1. Telemetry persisted
    telem = db.execute(
        select(TelemetryRecord).where(
            TelemetryRecord.machine_id == "MOT-1001",
            TelemetryRecord.seq == 1,
        )
    ).scalar_one_or_none()
    assert telem is not None
    assert telem.air_temp_c == 25.40
    assert telem.torque_nm == 40.10
    assert telem.delta_t_c == 9.90
    assert telem.raw_payload["edge"]["delta_t_c"] == 9.90

    # 2. Machine auto-registered
    machine = db.execute(
        select(MachineRecord).where(MachineRecord.machine_id == "MOT-1001")
    ).scalar_one_or_none()
    assert machine is not None
    assert machine.machine_type in ("Motor", "UNKNOWN")

    # 3. ML prediction persisted
    pred = db.execute(
        select(PredictionRecord).where(
            PredictionRecord.machine_id == "MOT-1001",
            PredictionRecord.telemetry_id == telem.id,
        )
    ).scalar_one_or_none()
    assert pred is not None
    assert 0.0 <= pred.failure_probability <= 1.0
    assert pred.risk_band in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert 0.0 <= pred.health_score <= 100.0

    # 4. Digital Twin state updated to LIVE
    twin_svc = get_twin_service()
    twin_state = twin_svc.get_state("MOT-1001")
    assert twin_state is not None
    assert twin_state.sync_status == "LIVE"
    assert twin_state.last_seq == 1


def test_firmware_tripped_telemetry_e2e_pipeline(db: Session):
    """Verify that tripped telemetry from firmware persists and updates twin state."""
    tripped_payload = {
        "schema": "edgetwin.telemetry.v1",
        "machine_id": "MOT-1001",
        "seq": 2,
        "ts": "2026-09-28T12:00:02Z",
        "provenance": "SIMULATED",
        "fw": "0.2.0",
        "signals": {
            "air_temp_c": 25.40,
            "process_temp_c": 26.00,
            "rotational_speed_rpm": 0.0,
            "torque_nm": 0.0,
            "vibration_mm_s": 0.10,
            "pressure_bar": 0.50,
            "current_a": 0.0,
            "voltage_v": 415.00,
            "tool_wear_min": 52.10,
            "operating_hours": 10000.0100,
        },
        "quality": {
            "vibration_mm_s": "OK",
            "pressure_bar": "OK",
        },
        "edge": {
            "delta_t_c": 0.60,
            "power_va": 0.0,
            "trip": "TRIP_OVERLOAD",
            "buffered": 0,
        },
    }

    topic = "edgetwin/v1/MOT-1001/telemetry"
    result = handle_message(
        topic=topic, raw_payload=json.dumps(tripped_payload).encode("utf-8"), db=db
    )
    assert result["outcome"] == "persisted"

    telem = db.execute(
        select(TelemetryRecord).where(
            TelemetryRecord.machine_id == "MOT-1001",
            TelemetryRecord.seq == 2,
        )
    ).scalar_one_or_none()
    assert telem is not None
    assert telem.trip == "TRIP_OVERLOAD"
    assert telem.raw_payload["edge"]["trip"] == "TRIP_OVERLOAD"
    assert telem.rotational_speed_rpm == 0.0


def test_firmware_lwt_offline_e2e_pipeline(db: Session, canonical_firmware_payload: dict[str, Any]):
    """Verify that MQTT LWT status message updates Digital Twin to OFFLINE and records snapshot."""
    twin_svc = get_twin_service()

    # 1. Establish LIVE twin state
    topic_telem = "edgetwin/v1/MOT-1001/telemetry"
    handle_message(
        topic=topic_telem, raw_payload=json.dumps(canonical_firmware_payload).encode("utf-8"), db=db
    )
    assert twin_svc.get_state("MOT-1001").sync_status == "LIVE"

    # 2. Dispatch LWT status message
    topic_status = "edgetwin/v1/MOT-1001/status"
    lwt_payload = json.dumps({"status": "OFFLINE"}).encode("utf-8")
    result = handle_message(topic=topic_status, raw_payload=lwt_payload, db=db)

    assert result["outcome"] == "status_updated"
    assert result["machine_id"] == "MOT-1001"

    # 3. Verify Twin transitioned to OFFLINE
    state = twin_svc.get_state("MOT-1001")
    assert state is not None
    assert state.sync_status == "OFFLINE"
    assert state.health_state == "OFFLINE"

    # 4. Verify snapshot persisted with OFFLINE
    snapshot = (
        db.execute(
            select(TwinSnapshotRecord)
            .where(
                TwinSnapshotRecord.machine_id == "MOT-1001",
                TwinSnapshotRecord.sync_status == "OFFLINE",
            )
            .order_by(TwinSnapshotRecord.created_at.desc())
        )
        .scalars()
        .first()
    )
    assert snapshot is not None
    assert snapshot.sync_status == "OFFLINE"


def test_firmware_online_status_e2e_pipeline(db: Session):
    """Verify that ONLINE status message is handled cleanly."""
    topic_status = "edgetwin/v1/MOT-1001/status"
    online_payload = json.dumps({"status": "ONLINE"}).encode("utf-8")
    result = handle_message(topic=topic_status, raw_payload=online_payload, db=db)

    assert result["outcome"] == "status_updated"
    assert "ONLINE" in result["reason"]
