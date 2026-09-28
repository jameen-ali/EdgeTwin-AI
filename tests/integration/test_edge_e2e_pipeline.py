"""tests/integration/test_edge_e2e_pipeline.py — Comprehensive end-to-end edge-to-backend integration tests.

Verifies the complete automated pipeline:
ESP32 / Wokwi telemetry -> MQTT Ingest -> Schema Validation -> DB Persistence
-> ML Inference -> Health Engine -> Digital Twin -> Alerts & Maintenance.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.app.db.base import Base
from api.app.ingest.handler import handle_message
from api.app.models.machine import MachineRecord
from api.app.models.telemetry import TelemetryRecord
from api.app.twin.service import get_twin_service
from simulation.contract import TelemetryValidator
from simulation.process_model import SimulatedMachine


@pytest.fixture
def sqlite_session_factory():
    """Create fresh isolated in-memory SQLite database session factory."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine)

    # Pre-register test machines
    with factory() as session:
        session.add(MachineRecord(machine_id="MOT-1001", machine_type="Motor", location="Bay-A"))
        session.add(
            MachineRecord(machine_id="CMP-2001", machine_type="Compressor", location="Bay-B")
        )
        session.commit()

    return factory


def test_e2e_nominal_telemetry_flow(sqlite_session_factory):
    """Test full nominal pipeline: 15 ticks of healthy nominal telemetry -> DB -> ML -> Twin."""
    from pathlib import Path

    scenarios_dir = Path(__file__).resolve().parents[2] / "simulation" / "scenarios"
    sim = SimulatedMachine.from_scenario_file(scenarios_dir / "healthy_nominal.yaml", seed=42)

    msgs = sim.run_scenario(steps=15)

    with sqlite_session_factory() as session:
        for msg in msgs:
            payload_bytes = json.dumps(msg).encode("utf-8")
            res = handle_message("edgetwin/v1/MOT-1001/telemetry", payload_bytes, session)
            assert res["outcome"] in ("persisted", "duplicate")

        # Verify DB records
        count = session.query(TelemetryRecord).filter_by(machine_id="MOT-1001").count()
        assert count == 15

    # Verify Twin state
    twin = get_twin_service()
    state = twin.get_state("MOT-1001")
    assert state is not None
    assert state.sync_status == "LIVE"
    assert state.operating_state in ("RUNNING", "STARTING")
    assert state.health_state == "HEALTHY"
    assert state.failure_probability is not None
    assert state.failure_probability < 0.16


@pytest.mark.parametrize(
    "trip_code,signal_override",
    [
        ("TRIP_THERMAL", {"air_temp_c": 25.0, "process_temp_c": 72.0}),  # DeltaT = 47 > 45
        ("TRIP_OVERCURRENT", {"current_a": 48.0}),  # Current > 45
        ("TRIP_VIBRATION", {"vibration_mm_s": 16.5}),  # Vibration > 15
        ("TRIP_OVERLOAD", {"current_a": 34.0}),  # Sustained overload
    ],
)
def test_e2e_all_four_safety_trips_flow(
    sqlite_session_factory, trip_code: str, signal_override: dict[str, Any]
):
    """Test all 4 hardware safety trip conditions through backend ingestion and alerting."""
    validator = TelemetryValidator()

    sim = SimulatedMachine(machine_id="MOT-1001", seed=42)
    nominal = sim.step()

    # Form tripped payload
    tripped_msg = dict(nominal)
    tripped_msg["seq"] = 100
    tripped_msg["signals"] = dict(nominal["signals"])
    tripped_msg["signals"].update(signal_override)
    tripped_msg["edge"] = dict(nominal["edge"])
    tripped_msg["edge"]["trip"] = trip_code
    tripped_msg["edge"]["buffered"] = 0

    assert validator.validate(tripped_msg).valid is True

    with sqlite_session_factory() as session:
        payload_bytes = json.dumps(tripped_msg).encode("utf-8")
        res = handle_message("edgetwin/v1/MOT-1001/telemetry", payload_bytes, session)
        assert res["outcome"] == "persisted"

        rec = session.query(TelemetryRecord).filter_by(machine_id="MOT-1001", seq=100).one_or_none()
        assert rec is not None
        assert rec.trip == trip_code

    twin = get_twin_service()
    state = twin.get_state("MOT-1001")
    assert state is not None
    assert state.operating_state == "TRIPPED"


def test_e2e_offline_buffering_and_reconnect_flush(sqlite_session_factory):
    """Test offline buffer accumulation, LWT OFFLINE mark, and reconnect batch flush."""
    twin = get_twin_service()
    validator = TelemetryValidator()
    sim = SimulatedMachine(machine_id="MOT-1001", seed=42)

    # 1. First establish online connection with message 1
    msg1 = sim.step()
    msg1["seq"] = 1
    with sqlite_session_factory() as session:
        handle_message("edgetwin/v1/MOT-1001/telemetry", json.dumps(msg1).encode("utf-8"), session)
    assert twin.get_state("MOT-1001").sync_status == "LIVE"

    # 2. Broker receives LWT OFFLINE (e.g. WiFi cut)
    lwt_status = json.dumps({"status": "OFFLINE"}).encode("utf-8")
    with sqlite_session_factory() as session:
        res = handle_message("edgetwin/v1/MOT-1001/status", lwt_status, session)
        assert res["outcome"] == "status_updated"
    assert twin.get_state("MOT-1001").sync_status == "OFFLINE"

    # 3. Edge buffers 10 messages locally while offline
    buffered_msgs = []
    for seq in range(2, 12):
        m = sim.step()
        m["seq"] = seq
        m["edge"]["buffered"] = seq - 1  # 1, 2, 3...
        assert validator.validate(m).valid is True
        buffered_msgs.append(m)

    # 4. Connection restored -> Edge flushes buffer
    with sqlite_session_factory() as session:
        for m in buffered_msgs:
            res = handle_message(
                "edgetwin/v1/MOT-1001/telemetry", json.dumps(m).encode("utf-8"), session
            )
            assert res["outcome"] == "persisted"

        # All 11 messages are now in the DB
        total = session.query(TelemetryRecord).filter_by(machine_id="MOT-1001").count()
        assert total == 11

    # Twin returns to LIVE
    final_state = twin.get_state("MOT-1001")
    assert final_state.sync_status == "LIVE"
    assert final_state.last_seq == 11


def test_e2e_sensor_dropout_resilience(sqlite_session_factory):
    """Test that missing sensor values are ingested, imputed, and processed cleanly without crash."""
    sim = SimulatedMachine(machine_id="MOT-1001", seed=42)
    msg = sim.step()
    msg["seq"] = 200

    # Simulate dropout of pressure and vibration
    msg["signals"]["pressure_bar"] = None
    msg["signals"]["vibration_mm_s"] = None
    msg["quality"]["pressure_bar"] = "MISSING"
    msg["quality"]["vibration_mm_s"] = "MISSING"

    validator = TelemetryValidator()
    assert validator.validate(msg).valid is True

    with sqlite_session_factory() as session:
        res = handle_message(
            "edgetwin/v1/MOT-1001/telemetry", json.dumps(msg).encode("utf-8"), session
        )
        assert res["outcome"] == "persisted"

        rec = session.query(TelemetryRecord).filter_by(machine_id="MOT-1001", seq=200).one()
        assert rec.pressure_bar is None
        assert rec.vibration_mm_s is None

    twin = get_twin_service()
    state = twin.get_state("MOT-1001")
    assert state is not None
    assert state.sync_status == "LIVE"
