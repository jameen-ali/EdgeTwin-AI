"""Tests for SQLAlchemy domain models, relationships, and constraints."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from api.app.db.base import Base
from api.app.models import (
    AlertRecord,
    FeedbackRecord,
    MachineRecord,
    MaintenanceRecord,
    ModelVersionRecord,
    PredictionRecord,
    TelemetryRecord,
    TwinSnapshotRecord,
)


@pytest.fixture
def db_session():
    """Create in-memory SQLite database session fixture."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_machine_crud(db_session: Session):
    """Test machine model creation and retrieval."""
    machine = MachineRecord(
        machine_id="MOT-1001",
        machine_type="Motor",
        location="Shop Floor Bay 3",
        status="RUNNING",
    )
    db_session.add(machine)
    db_session.commit()

    retrieved = db_session.get(MachineRecord, "MOT-1001")
    assert retrieved is not None
    assert retrieved.machine_type == "Motor"
    assert retrieved.status == "RUNNING"


def test_telemetry_crud_and_uniqueness(db_session: Session):
    """Test telemetry record creation, relationships, and unique constraint."""
    machine = MachineRecord(machine_id="PMP-2001", machine_type="Pump", status="RUNNING")
    db_session.add(machine)
    db_session.commit()

    now = datetime.now(UTC)
    telemetry = TelemetryRecord(
        machine_id="PMP-2001",
        seq=1,
        ts=now,
        provenance="SIMULATED",
        fw="0.2.0",
        air_temp_c=25.4,
        process_temp_c=35.3,
        rotational_speed_rpm=1548.0,
        torque_nm=40.1,
        vibration_mm_s=2.5,
        pressure_bar=5.5,
        current_a=12.0,
        voltage_v=415.0,
        tool_wear_min=50.0,
        operating_hours=10000.0,
        quality={"vibration_mm_s": "OK"},
        delta_t_c=9.9,
        power_va=4980.0,
        trip=None,
        buffered=0,
    )
    db_session.add(telemetry)
    db_session.commit()

    assert telemetry.id is not None
    assert len(machine.telemetry_records) == 1

    # Test unique constraint on (machine_id, seq)
    dup_telemetry = TelemetryRecord(
        machine_id="PMP-2001",
        seq=1,  # Duplicate seq
        ts=now,
        provenance="SIMULATED",
        fw="0.2.0",
    )
    db_session.add(dup_telemetry)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_prediction_crud_and_relationships(db_session: Session):
    """Test prediction record linked to machine and telemetry."""
    machine = MachineRecord(machine_id="CMP-3001", machine_type="Compressor", status="RUNNING")
    db_session.add(machine)
    db_session.commit()

    now = datetime.now(UTC)
    telemetry = TelemetryRecord(
        machine_id="CMP-3001",
        seq=10,
        ts=now,
        provenance="SIMULATED",
        fw="0.2.0",
    )
    db_session.add(telemetry)
    db_session.commit()

    pred = PredictionRecord(
        machine_id="CMP-3001",
        telemetry_id=telemetry.id,
        ts=now,
        failure_probability=0.042,
        failure_prediction=0,
        risk_band="LOW",
        anomaly_score=0.12,
        anomaly_flag=False,
        health_score=97.5,
        health_state="HEALTHY",
        top_factors=[{"feature": "Vibration_mm_s", "shap_value": 0.05}],
        model_version="edgetwin-risk:v2",
        inference_latency_ms=18.5,
    )
    db_session.add(pred)
    db_session.commit()

    assert pred.id is not None
    assert pred.machine.machine_id == "CMP-3001"
    assert pred.telemetry.seq == 10


def test_twin_snapshot_crud(db_session: Session):
    """Test twin snapshot persistence."""
    machine = MachineRecord(machine_id="CNC-4001", machine_type="CNC_Machine", status="RUNNING")
    db_session.add(machine)
    db_session.commit()

    snapshot = TwinSnapshotRecord(
        machine_id="CNC-4001",
        ts=datetime.now(UTC),
        sync_status="LIVE",
        operating_state="RUNNING",
        health_state="HEALTHY",
        health_score=95.0,
        risk_band="LOW",
        failure_probability=0.02,
        anomaly_flag=False,
        snapshot_payload={"state": "RUNNING", "sync": "LIVE"},
    )
    db_session.add(snapshot)
    db_session.commit()
    assert snapshot.id is not None


def test_alert_and_feedback_crud(db_session: Session):
    """Test alert creation and feedback linking."""
    machine = MachineRecord(machine_id="CNV-5001", machine_type="Conveyor", status="RUNNING")
    db_session.add(machine)
    db_session.commit()

    alert = AlertRecord(
        machine_id="CNV-5001",
        alert_type="HIGH_RISK_WARNING",
        severity="WARNING",
        status="OPEN",
        message="Elevated vibration and temperature detected",
        triggered_at=datetime.now(UTC),
    )
    db_session.add(alert)
    db_session.commit()

    feedback = FeedbackRecord(
        machine_id="CNV-5001",
        alert_id=alert.id,
        feedback_type="CONFIRMED",
        notes="Bearing defect confirmed by technician.",
        user_id="tech_01",
    )
    db_session.add(feedback)
    db_session.commit()

    assert feedback.id is not None
    assert len(alert.feedbacks) == 1
    assert alert.feedbacks[0].feedback_type == "CONFIRMED"


def test_maintenance_event_crud(db_session: Session):
    """Test maintenance event logging."""
    machine = MachineRecord(
        machine_id="MOT-1002", machine_type="Motor", status="MAINTENANCE_REQUIRED"
    )
    db_session.add(machine)
    db_session.commit()

    event = MaintenanceRecord(
        machine_id="MOT-1002",
        event_type="PART_REPLACEMENT",
        description="Replaced worn bearing housing",
        status="COMPLETED",
        technician="Sarah Connor",
    )
    db_session.add(event)
    db_session.commit()
    assert event.id is not None
    assert event.status == "COMPLETED"


def test_model_version_crud(db_session: Session):
    """Test model version registration and uniqueness constraint."""
    mv = ModelVersionRecord(
        model_name="edgetwin-risk",
        version="2",
        alias="champion",
        metrics={"pr_auc": 0.8969, "recall": 0.8195},
    )
    db_session.add(mv)
    db_session.commit()

    assert mv.id is not None

    dup_mv = ModelVersionRecord(
        model_name="edgetwin-risk",
        version="2",  # Duplicate version
        alias="challenger",
    )
    db_session.add(dup_mv)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
