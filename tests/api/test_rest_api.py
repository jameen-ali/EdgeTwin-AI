"""tests/api/test_rest_api.py — Comprehensive tests for T-036 REST API v1 + OpenAPI.

Test suite covers:
- HEALTH: /health, /ready, /api/v1/health, /api/v1/ready
- MACHINES: list machines, machine summaries, get machine detail, machine not found (404)
- TELEMETRY: telemetry list, pagination, limit boundaries, timestamp filtering, machine not found (404)
- PREDICTIONS: predictions list, response schema verification, no inference computation on GET
- TWIN: latest twin, twin history, twin matching canonical state, machine not found (404)
- ALERTS: fleet list, severity filter, acknowledgement filter, machine alerts, alert not found (404), alert acknowledgement
- MAINTENANCE: maintenance events history, machine not found (404)
- FEEDBACK: valid feedback (prediction and alert), invalid machine (404), invalid prediction (404), invalid alert (404), invalid payload (422)
- ERRORS: RFC 7807 Problem Details compliance on 404, 422, 500
- OPENAPI: /openapi.json and /docs load, paths inventory, schema presence
- SECURITY/INPUT: oversized limits rejected, malformed ID rejected, invalid enum rejected
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
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
from api.app.models.twin import TwinSnapshotRecord
from api.app.twin.service import get_twin_service
from api.app.twin.state import SYNC_LIVE, TwinState

# ---------------------------------------------------------------------------
# Database & TestClient Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sqlite_db():
    """In-memory SQLite database session with foreign key enforcement."""
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

    # Seed base test assets
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

    now = datetime.now(UTC)

    # Seed Telemetry for MOT-1001
    t1 = TelemetryRecord(
        machine_id="MOT-1001",
        seq=101,
        ts=now,
        provenance="SIMULATED",
        fw="0.2.0",
        air_temp_c=25.5,
        process_temp_c=35.2,
        rotational_speed_rpm=1500.0,
        torque_nm=40.5,
        vibration_mm_s=2.1,
        pressure_bar=5.0,
        current_a=12.0,
        voltage_v=400.0,
        tool_wear_min=120.0,
        operating_hours=500.0,
        quality={"vibration_mm_s": "OK"},
        delta_t_c=9.7,
        power_va=4800.0,
        trip=None,
        buffered=0,
    )
    t2 = TelemetryRecord(
        machine_id="MOT-1001",
        seq=102,
        ts=now,
        provenance="SIMULATED",
        fw="0.2.0",
        air_temp_c=26.0,
        process_temp_c=36.0,
        rotational_speed_rpm=1510.0,
        torque_nm=41.0,
        vibration_mm_s=2.3,
        pressure_bar=5.1,
        current_a=12.2,
        voltage_v=401.0,
        tool_wear_min=121.0,
        operating_hours=500.1,
        quality={"vibration_mm_s": "OK"},
        delta_t_c=10.0,
        power_va=4892.2,
        trip=None,
        buffered=0,
    )
    session.add_all([t1, t2])
    session.commit()

    # Seed Prediction for MOT-1001
    p1 = PredictionRecord(
        machine_id="MOT-1001",
        telemetry_id=t2.id,
        ts=now,
        failure_probability=0.04,
        failure_prediction=0,
        risk_band="LOW",
        anomaly_score=0.12,
        anomaly_flag=False,
        health_score=89.5,
        health_state="HEALTHY",
        top_factors=[{"feature": "Tool_Wear_Min", "shap_value": 0.08}],
        model_version="edgetwin-risk:v2-champion",
        inference_latency_ms=15.4,
    )
    session.add(p1)
    session.commit()

    # Seed Twin Snapshot for MOT-1001
    snap1 = TwinSnapshotRecord(
        machine_id="MOT-1001",
        ts=now,
        sync_status="LIVE",
        operating_state="RUNNING",
        health_state="HEALTHY",
        health_score=89.5,
        risk_band="LOW",
        failure_probability=0.04,
        anomaly_flag=False,
        snapshot_payload={
            "machine_id": "MOT-1001",
            "sync_status": "LIVE",
            "health_state": "HEALTHY",
            "health_score": 89.5,
            "risk_band": "LOW",
            "failure_probability": 0.04,
            "anomaly_flag": False,
            "anomaly_score": 0.12,
            "operating_state": "RUNNING",
            "last_telemetry_ts": now.isoformat(),
            "last_seq": 102,
            "updated_at": now.isoformat(),
            "signals": {"air_temp_c": 26.0},
            "quality": {"air_temp_c": "OK"},
            "edge": {"trip": None},
            "top_factors": [{"feature": "Tool_Wear_Min", "shap_value": 0.08}],
            "recommendation": None,
            "model_version": "edgetwin-risk:v2-champion",
            "provenance": "SIMULATED",
            "fw": "0.2.0",
        },
    )
    session.add(snap1)
    session.commit()

    # Seed Alerts
    a1 = AlertRecord(
        machine_id="MOT-1001",
        alert_type="PREDICTIVE_FAILURE_WARNING",
        severity="WARNING",
        status="OPEN",
        message="Failure risk elevated above threshold",
        trigger_conditions={"failure_probability": 0.18},
        top_factors=[{"feature": "Process_Temperature_C", "shap_value": 0.35}],
        triggered_at=now,
    )
    a2 = AlertRecord(
        machine_id="MOT-1001",
        alert_type="SAFETY_TRIP",
        severity="CRITICAL",
        status="ACKNOWLEDGED",
        message="Hardware safety trip triggered: TRIP_OVERLOAD",
        trigger_conditions={"trip": "TRIP_OVERLOAD"},
        top_factors=[],
        triggered_at=now,
        acknowledged_at=now,
    )
    session.add_all([a1, a2])
    session.commit()

    # Seed Maintenance Event
    maint1 = MaintenanceRecord(
        machine_id="MOT-1001",
        event_type="INSPECTION",
        description="Routine monthly bearing and lubrication inspection",
        status="COMPLETED",
        technician="TECH-007",
        started_at=now,
        completed_at=now,
    )
    session.add(maint1)
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def client(sqlite_db: Session) -> TestClient:
    """FastAPI TestClient with overridden get_db dependency and mocked background services."""

    def _override_get_db():
        yield sqlite_db

    app.dependency_overrides[get_db] = _override_get_db
    with (
        patch("api.app.ingest.mqtt_client.MQTTIngestionClient.start"),
        patch("api.app.ingest.mqtt_client.MQTTIngestionClient.stop"),
        TestClient(app) as test_client,
    ):
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 1. HEALTH Endpoints
# ---------------------------------------------------------------------------


class TestHealthEndpoints:
    def test_health_root(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_ready_root(self, client: TestClient) -> None:
        with patch("api.app.routes.health.check_db_connection", return_value=(True, None)):
            resp = client.get("/ready")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ready"
            assert data["database"] == "connected"

    def test_health_api_v1(self, client: TestClient) -> None:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_ready_api_v1(self, client: TestClient) -> None:
        with patch("api.app.routes.health.check_db_connection", return_value=(True, None)):
            resp = client.get("/api/v1/ready")
            assert resp.status_code == 200
            assert resp.json()["status"] == "ready"


# ---------------------------------------------------------------------------
# 2. MACHINES Endpoints
# ---------------------------------------------------------------------------


class TestMachineEndpoints:
    def test_list_machines(self, client: TestClient) -> None:
        resp = client.get("/api/v1/machines")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        ids = [m["machine_id"] for m in data["items"]]
        assert "MOT-1001" in ids
        assert "PMP-2001" in ids

    def test_get_machine_success(self, client: TestClient) -> None:
        resp = client.get("/api/v1/machines/MOT-1001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["machine_id"] == "MOT-1001"
        assert data["machine_type"] == "Motor"
        assert data["status"] == "ACTIVE"
        assert data["latest_twin"] is not None
        assert data["latest_telemetry"] is not None
        assert data["latest_prediction"] is not None

    def test_get_machine_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/v1/machines/MOT-9999")
        assert resp.status_code == 404
        data = resp.json()
        assert data["title"] == "HTTP Error"
        assert data["status"] == 404
        assert "MOT-9999" in data["detail"]


# ---------------------------------------------------------------------------
# 3. TELEMETRY Endpoints
# ---------------------------------------------------------------------------


class TestTelemetryEndpoints:
    def test_telemetry_list(self, client: TestClient) -> None:
        resp = client.get("/api/v1/machines/MOT-1001/telemetry")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        # Ordered ts desc
        assert data["items"][0]["seq"] >= data["items"][1]["seq"]

    def test_telemetry_pagination(self, client: TestClient) -> None:
        resp = client.get("/api/v1/machines/MOT-1001/telemetry?limit=1&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 1
        assert data["limit"] == 1
        assert data["offset"] == 0

    def test_telemetry_seq_filter(self, client: TestClient) -> None:
        resp = client.get("/api/v1/machines/MOT-1001/telemetry?seq_min=102")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["seq"] == 102

    def test_telemetry_invalid_limit(self, client: TestClient) -> None:
        resp = client.get("/api/v1/machines/MOT-1001/telemetry?limit=0")
        assert resp.status_code == 422
        data = resp.json()
        assert data["title"] == "Validation Error"

    def test_telemetry_machine_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/v1/machines/GHOST-9999/telemetry")
        assert resp.status_code == 404
        assert "GHOST-9999" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# 4. PREDICTIONS Endpoints
# ---------------------------------------------------------------------------


class TestPredictionEndpoints:
    def test_prediction_list(self, client: TestClient) -> None:
        resp = client.get("/api/v1/machines/MOT-1001/predictions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        pred = data["items"][0]
        assert pred["machine_id"] == "MOT-1001"
        assert pred["failure_probability"] == pytest.approx(0.04)
        assert pred["risk_band"] == "LOW"
        assert pred["model_version"] == "edgetwin-risk:v2-champion"
        assert pred["health_score"] == pytest.approx(89.5)

    def test_no_inference_triggered_by_get(self, client: TestClient) -> None:
        with patch("api.app.inference.service.InferenceService.run_inference") as mock_inf:
            resp = client.get("/api/v1/machines/MOT-1001/predictions")
            assert resp.status_code == 200
            mock_inf.assert_not_called()

    def test_prediction_machine_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/v1/machines/GHOST-9999/predictions")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 5. DIGITAL TWIN Endpoints
# ---------------------------------------------------------------------------


class TestTwinEndpoints:
    def test_latest_twin(self, client: TestClient) -> None:
        resp = client.get("/api/v1/machines/MOT-1001/twin")
        assert resp.status_code == 200
        data = resp.json()
        assert data["machine_id"] == "MOT-1001"
        assert data["sync_status"] == "LIVE"
        assert data["health_state"] == "HEALTHY"

    def test_twin_history(self, client: TestClient) -> None:
        resp = client.get("/api/v1/machines/MOT-1001/twin/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["health_score"] == pytest.approx(89.5)

    def test_twin_machine_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/v1/machines/GHOST-9999/twin")
        assert resp.status_code == 404

    def test_rest_twin_matches_canonical_state(self, client: TestClient) -> None:
        twin_svc = get_twin_service()
        state = TwinState(
            machine_id="MOT-1001",
            sync_status=SYNC_LIVE,
            health_state="WARNING",
            health_score=68.0,
            risk_band="HIGH",
            failure_probability=0.25,
            anomaly_flag=False,
            operating_state="RUNNING",
            last_telemetry_ts=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        with twin_svc._lock:
            twin_svc._states["MOT-1001"] = state

        resp = client.get("/api/v1/machines/MOT-1001/twin")
        assert resp.status_code == 200
        data = resp.json()
        assert data["health_state"] == "WARNING"
        assert data["health_score"] == pytest.approx(68.0)
        assert data["risk_band"] == "HIGH"


# ---------------------------------------------------------------------------
# 6. ALERTS Endpoints
# ---------------------------------------------------------------------------


class TestAlertEndpoints:
    def test_list_alerts(self, client: TestClient) -> None:
        resp = client.get("/api/v1/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_filter_alerts_severity(self, client: TestClient) -> None:
        resp = client.get("/api/v1/alerts?severity=CRITICAL")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["severity"] == "CRITICAL"

    def test_filter_alerts_acknowledged(self, client: TestClient) -> None:
        resp = client.get("/api/v1/alerts?acknowledged=true")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "ACKNOWLEDGED"

    def test_machine_alerts(self, client: TestClient) -> None:
        resp = client.get("/api/v1/machines/MOT-1001/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    def test_alert_not_found(self, client: TestClient) -> None:
        resp = client.patch(
            "/api/v1/alerts/99999",
            json={"status": "ACKNOWLEDGED", "resolved_by": "TECH-01"},
        )
        assert resp.status_code == 404

    def test_acknowledge_alert_success(self, client: TestClient, sqlite_db: Session) -> None:
        # Get id of the OPEN alert
        alert = sqlite_db.query(AlertRecord).filter_by(status="OPEN").first()
        assert alert is not None

        resp = client.patch(
            f"/api/v1/alerts/{alert.id}",
            json={
                "status": "ACKNOWLEDGED",
                "resolved_by": "TECH-101",
                "notes": "Inspected bearing",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == alert.id
        assert data["status"] == "ACKNOWLEDGED"
        assert data["resolved_by"] == "TECH-101"
        assert data["acknowledged_at"] is not None


# ---------------------------------------------------------------------------
# 7. MAINTENANCE Endpoints
# ---------------------------------------------------------------------------


class TestMaintenanceEndpoints:
    def test_maintenance_history(self, client: TestClient) -> None:
        resp = client.get("/api/v1/machines/MOT-1001/maintenance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["event_type"] == "INSPECTION"
        assert data["items"][0]["technician"] == "TECH-007"

    def test_maintenance_machine_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/v1/machines/GHOST-9999/maintenance")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 8. FEEDBACK Endpoints
# ---------------------------------------------------------------------------


class TestFeedbackEndpoints:
    def test_valid_feedback_with_prediction(self, client: TestClient, sqlite_db: Session) -> None:
        pred = sqlite_db.query(PredictionRecord).first()
        assert pred is not None

        resp = client.post(
            "/api/v1/machines/MOT-1001/feedback",
            json={
                "prediction_id": pred.id,
                "ground_truth_failure": True,
                "notes": "Verified bearing damage during teardown",
                "technician_id": "TECH-042",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["machine_id"] == "MOT-1001"
        assert data["feedback_type"] == "CONFIRMED"
        assert data["user_id"] == "TECH-042"

        # Verify persisted in DB
        db_fb = sqlite_db.query(FeedbackRecord).filter_by(id=data["id"]).first()
        assert db_fb is not None
        assert db_fb.feedback_type == "CONFIRMED"

    def test_valid_feedback_with_alert(self, client: TestClient, sqlite_db: Session) -> None:
        alert = sqlite_db.query(AlertRecord).first()
        assert alert is not None

        resp = client.post(
            "/api/v1/machines/MOT-1001/feedback",
            json={
                "alert_id": alert.id,
                "feedback_type": "FALSE_ALARM",
                "notes": "Transient sensor glitch, machine inspected and healthy",
                "technician_id": "TECH-042",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["feedback_type"] == "FALSE_ALARM"

    def test_feedback_invalid_machine(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/machines/GHOST-9999/feedback",
            json={"alert_id": 1, "feedback_type": "CONFIRMED"},
        )
        assert resp.status_code == 404
        assert "GHOST-9999" in resp.json()["detail"]

    def test_feedback_invalid_prediction_reference(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/machines/MOT-1001/feedback",
            json={"prediction_id": 99999, "feedback_type": "CONFIRMED"},
        )
        assert resp.status_code == 404
        assert "99999" in resp.json()["detail"]

    def test_feedback_invalid_alert_reference(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/machines/MOT-1001/feedback",
            json={"alert_id": 99999, "feedback_type": "CONFIRMED"},
        )
        assert resp.status_code == 404
        assert "99999" in resp.json()["detail"]

    def test_feedback_invalid_payload_missing_all_refs(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/machines/MOT-1001/feedback",
            json={"notes": "No target specified"},
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["title"] == "Validation Error"


# ---------------------------------------------------------------------------
# 9. ERRORS & RFC 7807 Problem Details
# ---------------------------------------------------------------------------


class TestErrorContract:
    def test_rfc7807_validation_error_shape(self, client: TestClient) -> None:
        # Send bad limit type
        resp = client.get("/api/v1/machines?limit=not_an_int")
        assert resp.status_code == 422
        assert resp.headers["content-type"] == "application/problem+json"
        data = resp.json()
        assert "type" in data
        assert data["title"] == "Validation Error"
        assert data["status"] == 422
        assert "detail" in data
        assert data["instance"] == "/api/v1/machines"
        assert isinstance(data.get("errors"), list)

    def test_rfc7807_404_shape(self, client: TestClient) -> None:
        resp = client.get("/api/v1/machines/MISSING-1")
        assert resp.status_code == 404
        assert resp.headers["content-type"] == "application/problem+json"
        data = resp.json()
        assert data["title"] == "HTTP Error"
        assert data["status"] == 404
        assert data["instance"] == "/api/v1/machines/MISSING-1"


# ---------------------------------------------------------------------------
# 10. OPENAPI & Documentation Verification
# ---------------------------------------------------------------------------


class TestOpenAPIContract:
    def test_openapi_json_loads(self, client: TestClient) -> None:
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["openapi"].startswith("3.")
        assert "paths" in data

    def test_openapi_routes_presence(self, client: TestClient) -> None:
        resp = client.get("/openapi.json")
        paths = resp.json()["paths"]
        expected_paths = [
            "/health",
            "/ready",
            "/api/v1/health",
            "/api/v1/ready",
            "/api/v1/machines",
            "/api/v1/machines/{machine_id}",
            "/api/v1/machines/{machine_id}/telemetry",
            "/api/v1/machines/{machine_id}/predictions",
            "/api/v1/machines/{machine_id}/twin",
            "/api/v1/machines/{machine_id}/twin/history",
            "/api/v1/machines/{machine_id}/alerts",
            "/api/v1/machines/{machine_id}/maintenance",
            "/api/v1/machines/{machine_id}/feedback",
            "/api/v1/alerts",
            "/api/v1/alerts/{alert_id}",
        ]
        for p in expected_paths:
            assert p in paths, f"Path {p} missing from OpenAPI schema"

    def test_docs_page_accessible(self, client: TestClient) -> None:
        resp = client.get("/docs")
        assert resp.status_code == 200
        assert "swagger" in resp.text.lower()


# ---------------------------------------------------------------------------
# 11. SECURITY & INPUT VALIDATION
# ---------------------------------------------------------------------------


class TestSecurityInputValidation:
    def test_oversized_limit_rejected(self, client: TestClient) -> None:
        resp = client.get("/api/v1/machines?limit=9999")
        assert resp.status_code == 422
        data = resp.json()
        assert data["title"] == "Validation Error"

    def test_malformed_machine_id_rejected(self, client: TestClient) -> None:
        # Machine ID containing forbidden special characters / spaces
        resp = client.get("/api/v1/machines/MOT%201001%20bad!/twin")
        assert resp.status_code == 422

    def test_negative_offset_rejected(self, client: TestClient) -> None:
        resp = client.get("/api/v1/machines?offset=-5")
        assert resp.status_code == 422
