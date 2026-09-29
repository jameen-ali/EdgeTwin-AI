"""tests/api/test_alerts_maintenance_feedback.py — Integration and RBAC tests for S22 (T-056).

Covers:
- Alerts: List, get by id, acknowledge, resolve, invalid state transitions, 404s, RBAC (Operator vs Admin/Engineer)
- Maintenance: List, get by id, create for machine and fleet-wide, alert linking, invalid machine (404),
  mismatched alert (400), status update lifecycle, RBAC
- Feedback: Valid submission, duplicate submission rejection (409), relationship validation, history retrieval, RBAC
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.app.db.base import Base
from api.app.db.session import get_db
from api.app.main import app
from api.app.models.alert import AlertRecord
from api.app.models.feedback import FeedbackRecord
from api.app.models.machine import MachineRecord
from api.app.models.maintenance import MaintenanceRecord
from api.app.models.prediction import PredictionRecord
from api.app.models.telemetry import TelemetryRecord
from api.app.models.user import UserRecord
from api.app.security.deps import get_current_user


@pytest.fixture()
def db_session():
    """In-memory SQLite session with foreign key enforcement."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_conn, _conn_record):
        dbapi_conn.execute("PRAGMA foreign_keys = ON")

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()

    now = datetime.now(UTC)

    # Seed machines
    m1 = MachineRecord(
        machine_id="MOT-1001",
        machine_type="Motor",
        location="Cell-A",
        status="ACTIVE",
    )
    m2 = MachineRecord(
        machine_id="PMP-2001",
        machine_type="Pump",
        location="Cell-B",
        status="ACTIVE",
    )
    session.add_all([m1, m2])
    session.commit()

    # Seed telemetry & prediction
    t1 = TelemetryRecord(
        machine_id="MOT-1001",
        seq=1,
        ts=now,
        provenance="SIMULATED",
        fw="0.2.0",
        air_temp_c=25.0,
        process_temp_c=35.0,
        rotational_speed_rpm=1500.0,
        torque_nm=40.0,
        vibration_mm_s=2.0,
        pressure_bar=5.0,
        current_a=12.0,
        voltage_v=400.0,
        tool_wear_min=100.0,
        operating_hours=400.0,
        quality={},
        delta_t_c=10.0,
        power_va=4800.0,
        buffered=0,
    )
    session.add(t1)
    session.commit()

    p1 = PredictionRecord(
        machine_id="MOT-1001",
        telemetry_id=t1.id,
        ts=now,
        failure_probability=0.22,
        failure_prediction=1,
        risk_band="CRITICAL",
        anomaly_score=0.85,
        anomaly_flag=True,
        health_score=42.0,
        health_state="CRITICAL",
        top_factors=[{"feature": "Process_Temperature_C", "shap_value": 0.45}],
        model_version="edgetwin-risk:v2-champion",
        inference_latency_ms=12.0,
    )
    session.add(p1)
    session.commit()

    # Seed Alerts
    a1 = AlertRecord(
        machine_id="MOT-1001",
        alert_type="PREDICTIVE_FAILURE_WARNING",
        severity="CRITICAL",
        status="OPEN",
        message="Critical failure risk elevated (22%)",
        trigger_conditions={"failure_probability": 0.22},
        top_factors=[{"feature": "Process_Temperature_C", "shap_value": 0.45}],
        triggered_at=now,
    )
    a2 = AlertRecord(
        machine_id="PMP-2001",
        alert_type="VIBRATION_SPIKE",
        severity="WARNING",
        status="ACKNOWLEDGED",
        message="Vibration spike on pump impeller",
        trigger_conditions={"vibration_mm_s": 4.8},
        top_factors=[],
        triggered_at=now,
        acknowledged_at=now,
        resolved_by="tech_alex",
    )
    a3 = AlertRecord(
        machine_id="MOT-1001",
        alert_type="HIGH_TEMP",
        severity="INFO",
        status="RESOLVED",
        message="Motor temperature normalized",
        trigger_conditions={"process_temp_c": 35.0},
        top_factors=[],
        triggered_at=now,
        acknowledged_at=now,
        resolved_at=now,
        resolved_by="lead_eng",
    )
    session.add_all([a1, a2, a3])
    session.commit()

    # Seed Maintenance
    maint1 = MaintenanceRecord(
        machine_id="MOT-1001",
        alert_id=a1.id,
        event_type="INSPECTION",
        description="Initial diagnostic check of motor bearing",
        status="SCHEDULED",
        technician="tech_alex",
    )
    session.add(maint1)
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def create_test_client(session: Session, role: str = "ADMIN", username: str = "test_user"):
    user = UserRecord(id=10, username=username, role=role, is_active=True)

    def _get_db_override():
        yield session

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_current_user] = lambda: user

    with (
        patch("api.app.ingest.mqtt_client.MQTTIngestionClient.start"),
        patch("api.app.ingest.mqtt_client.MQTTIngestionClient.stop"),
    ):
        client = TestClient(app)
        yield client

    app.dependency_overrides.clear()


# ===========================================================================
# 1. ALERTS TESTS
# ===========================================================================


def test_alerts_list_and_filters(db_session: Session):
    for client in create_test_client(db_session, role="ADMIN"):
        # Fleet-wide
        res = client.get("/api/v1/alerts")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

        # Filter by severity
        res_crit = client.get("/api/v1/alerts?severity=CRITICAL")
        assert res_crit.status_code == 200
        crit_data = res_crit.json()
        assert crit_data["total"] == 1
        assert crit_data["items"][0]["severity"] == "CRITICAL"

        # Filter by status
        res_open = client.get("/api/v1/alerts?status=OPEN")
        assert res_open.status_code == 200
        assert res_open.json()["total"] == 1
        assert res_open.json()["items"][0]["status"] == "OPEN"

        # Filter by machine
        res_mot = client.get("/api/v1/alerts?machine_id=MOT-1001")
        assert res_mot.status_code == 200
        assert res_mot.json()["total"] == 2


def test_alert_get_by_id(db_session: Session):
    for client in create_test_client(db_session, role="OPERATOR"):
        # Get existing alert
        res = client.get("/api/v1/alerts/1")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == 1
        assert data["machine_id"] == "MOT-1001"
        assert data["severity"] == "CRITICAL"

        # 404 for non-existent alert
        res_404 = client.get("/api/v1/alerts/9999")
        assert res_404.status_code == 404
        assert "not found" in res_404.json()["detail"].lower()


def test_alert_acknowledgment_workflow(db_session: Session):
    # Admin can acknowledge
    for client in create_test_client(db_session, role="ADMIN", username="admin_ops"):
        payload = {"status": "ACKNOWLEDGED", "notes": "Investigating high bearing vibration"}
        res = client.patch("/api/v1/alerts/1", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ACKNOWLEDGED"
        assert data["acknowledged_at"] is not None
        assert data["resolved_by"] == "admin_ops"


def test_alert_resolution_workflow(db_session: Session):
    # Maintenance Engineer can resolve
    for client in create_test_client(db_session, role="MAINTENANCE_ENGINEER", username="eng_sarah"):
        payload = {
            "status": "RESOLVED",
            "notes": "Bearing lubricated, vibration returned to normal",
        }
        res = client.patch("/api/v1/alerts/1", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "RESOLVED"
        assert data["acknowledged_at"] is not None
        assert data["resolved_at"] is not None
        assert data["resolved_by"] == "eng_sarah"


def test_alert_invalid_status_transition(db_session: Session):
    for client in create_test_client(db_session, role="ADMIN"):
        # Alert 3 is already RESOLVED in fixture. Attempting to transition it should fail.
        res = client.patch("/api/v1/alerts/3", json={"status": "ACKNOWLEDGED"})
        assert res.status_code == 400
        assert "already resolved" in res.json()["detail"].lower()

        # Invalid status enum
        res_bad_status = client.patch("/api/v1/alerts/1", json={"status": "INVALID_STATE"})
        assert res_bad_status.status_code == 400
        assert "must be 'acknowledged' or 'resolved'" in res_bad_status.json()["detail"].lower()


def test_alert_rbac_operator_forbidden(db_session: Session):
    for client in create_test_client(db_session, role="OPERATOR", username="op_bob"):
        res = client.patch("/api/v1/alerts/1", json={"status": "ACKNOWLEDGED"})
        assert res.status_code == 403
        assert "forbidden" in res.json()["detail"].lower() or "role" in res.json()["detail"].lower()


# ===========================================================================
# 2. MAINTENANCE TESTS
# ===========================================================================


def test_maintenance_list_and_get(db_session: Session):
    for client in create_test_client(db_session, role="OPERATOR"):
        # Fleet-wide
        res = client.get("/api/v1/maintenance")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["items"][0]["machine_id"] == "MOT-1001"
        assert data["items"][0]["alert_id"] == 1

        # Per machine
        res_m = client.get("/api/v1/machines/MOT-1001/maintenance")
        assert res_m.status_code == 200
        assert res_m.json()["total"] == 1

        # Get by id
        res_id = client.get("/api/v1/maintenance/1")
        assert res_id.status_code == 200
        assert res_id.json()["id"] == 1
        assert res_id.json()["event_type"] == "INSPECTION"

        # 404 for missing
        assert client.get("/api/v1/maintenance/9999").status_code == 404


def test_maintenance_create_and_alert_link(db_session: Session):
    for client in create_test_client(db_session, role="MAINTENANCE_ENGINEER", username="eng_mark"):
        payload = {
            "machine_id": "MOT-1001",
            "event_type": "PART_REPLACEMENT",
            "description": "Replace worn drive belt and inspect motor mountings",
            "status": "SCHEDULED",
            "alert_id": 1,
            "technician": "eng_mark",
        }
        res = client.post("/api/v1/maintenance", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["id"] is not None
        assert data["machine_id"] == "MOT-1001"
        assert data["alert_id"] == 1
        assert data["event_type"] == "PART_REPLACEMENT"
        assert data["status"] == "SCHEDULED"

        # Verify per-machine creation endpoint
        payload_machine = {
            "event_type": "LUBRICATION",
            "description": "Grease bearings",
            "status": "SCHEDULED",
            "alert_id": None,
        }
        res2 = client.post("/api/v1/machines/PMP-2001/maintenance", json=payload_machine)
        assert res2.status_code == 201
        assert res2.json()["machine_id"] == "PMP-2001"
        assert res2.json()["event_type"] == "LUBRICATION"


def test_maintenance_create_validations(db_session: Session):
    for client in create_test_client(db_session, role="ADMIN"):
        # Invalid machine
        res_bad_mach = client.post(
            "/api/v1/maintenance",
            json={
                "machine_id": "NON_EXISTENT",
                "event_type": "INSPECTION",
                "description": "Test bad machine",
            },
        )
        assert res_bad_mach.status_code == 404

        # Invalid alert id
        res_bad_alert = client.post(
            "/api/v1/maintenance",
            json={
                "machine_id": "MOT-1001",
                "event_type": "INSPECTION",
                "description": "Test non existent alert",
                "alert_id": 9999,
            },
        )
        assert res_bad_alert.status_code == 404

        # Mismatched alert (Alert 2 belongs to PMP-2001, not MOT-1001)
        res_mismatch = client.post(
            "/api/v1/maintenance",
            json={
                "machine_id": "MOT-1001",
                "event_type": "INSPECTION",
                "description": "Test mismatched alert machine",
                "alert_id": 2,
            },
        )
        assert res_mismatch.status_code == 400
        assert "belongs to machine" in res_mismatch.json()["detail"].lower()


def test_maintenance_update_lifecycle(db_session: Session):
    for client in create_test_client(db_session, role="MAINTENANCE_ENGINEER"):
        # Transition to IN_PROGRESS
        res1 = client.patch(
            "/api/v1/maintenance/1",
            json={"status": "IN_PROGRESS", "technician": "lead_tech"},
        )
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["status"] == "IN_PROGRESS"
        assert data1["started_at"] is not None
        assert data1["technician"] == "lead_tech"

        # Transition to COMPLETED
        res2 = client.patch(
            "/api/v1/maintenance/1",
            json={
                "status": "COMPLETED",
                "description": "Inspection finished with no anomalous wear found",
            },
        )
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["status"] == "COMPLETED"
        assert data2["completed_at"] is not None

        # Invalid status transition
        res_bad = client.patch("/api/v1/maintenance/1", json={"status": "BOGUS_STATUS"})
        assert res_bad.status_code == 400


def test_maintenance_rbac(db_session: Session):
    for client in create_test_client(db_session, role="OPERATOR"):
        # Operator cannot create maintenance
        res_post = client.post(
            "/api/v1/maintenance",
            json={
                "machine_id": "MOT-1001",
                "event_type": "INSPECTION",
                "description": "Operator attempting work order creation",
            },
        )
        assert res_post.status_code == 403

        # Operator cannot patch maintenance
        res_patch = client.patch("/api/v1/maintenance/1", json={"status": "IN_PROGRESS"})
        assert res_patch.status_code == 403


# ===========================================================================
# 3. FEEDBACK TESTS
# ===========================================================================


def test_feedback_submit_and_persistence(db_session: Session):
    for client in create_test_client(db_session, role="OPERATOR", username="op_charlie"):
        payload = {
            "alert_id": 1,
            "feedback_type": "CONFIRMED",
            "notes": "Verified bearing overheating and high friction on teardown",
        }
        res = client.post("/api/v1/machines/MOT-1001/feedback", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["id"] is not None
        assert data["machine_id"] == "MOT-1001"
        assert data["alert_id"] == 1
        assert data["feedback_type"] == "CONFIRMED"
        assert data["user_id"] == "op_charlie"

        # Verify DB persistence directly
        rec = db_session.execute(
            select(FeedbackRecord).where(FeedbackRecord.id == data["id"])
        ).scalar_one_or_none()
        assert rec is not None
        assert rec.notes == "Verified bearing overheating and high friction on teardown"

        # Verify feedback history list
        hist_res = client.get("/api/v1/machines/MOT-1001/feedback")
        assert hist_res.status_code == 200
        hist_data = hist_res.json()
        assert hist_data["total"] >= 1
        assert hist_data["items"][0]["id"] == data["id"]


def test_feedback_duplicate_rejection(db_session: Session):
    for client in create_test_client(db_session, role="OPERATOR", username="op_charlie"):
        payload = {
            "alert_id": 2,
            "feedback_type": "FALSE_ALARM",
            "notes": "Transient sensor interference, no mechanical issue",
        }
        # First submission succeeds
        res1 = client.post("/api/v1/machines/PMP-2001/feedback", json=payload)
        assert res1.status_code == 201

        # Duplicate submission on same alert fails with 409 Conflict
        res2 = client.post("/api/v1/machines/PMP-2001/feedback", json=payload)
        assert res2.status_code == 409
        assert "already been submitted" in res2.json()["detail"].lower()


def test_feedback_validations(db_session: Session):
    for client in create_test_client(db_session, role="ADMIN"):
        # Machine not found
        res_m = client.post(
            "/api/v1/machines/NON_EXISTENT/feedback",
            json={"alert_id": 1, "feedback_type": "CONFIRMED"},
        )
        assert res_m.status_code == 404

        # Alert not found for this machine
        res_a = client.post(
            "/api/v1/machines/MOT-1001/feedback",
            json={"alert_id": 9999, "feedback_type": "CONFIRMED"},
        )
        assert res_a.status_code == 404

        # Missing both prediction_id and alert_id
        res_empty = client.post(
            "/api/v1/machines/MOT-1001/feedback",
            json={"feedback_type": "CONFIRMED"},
        )
        assert res_empty.status_code == 422
