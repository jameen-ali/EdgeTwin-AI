"""tests/api/test_history.py — Tests for historical analytics endpoints (T-057)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
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
from api.app.models.machine import MachineRecord
from api.app.models.maintenance import MaintenanceRecord
from api.app.models.prediction import PredictionRecord
from api.app.models.telemetry import TelemetryRecord
from api.app.models.twin import TwinSnapshotRecord
from api.app.models.user import UserRecord
from api.app.security.deps import get_current_user


@pytest.fixture()
def sqlite_db():
    """In-memory SQLite database session with seeded machine and historical events."""
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

    # Seed machines
    m1 = MachineRecord(
        machine_id="MOT-1001",
        machine_type="Motor",
        location="Cell-A",
        status="RUNNING",
    )
    m2 = MachineRecord(
        machine_id="PMP-2001",
        machine_type="Pump",
        location="Cell-B",
        status="DEGRADING",
    )
    m_empty = MachineRecord(
        machine_id="GEN-3001",
        machine_type="Generator",
        location="Cell-C",
        status="OFFLINE",
    )
    session.add_all([m1, m2, m_empty])
    session.commit()

    now = datetime.now(UTC)

    # Seed 30 telemetry points across the last 30 minutes for MOT-1001
    telemetry_records = []
    for i in range(30):
        t_ts = now - timedelta(minutes=(30 - i))
        t = TelemetryRecord(
            machine_id="MOT-1001",
            seq=1000 + i,
            ts=t_ts,
            provenance="SIMULATED",
            fw="0.2.0",
            air_temp_c=25.0 + (i * 0.1),
            process_temp_c=45.0 + (i * 0.2),
            rotational_speed_rpm=1500.0 - (i * 2.0),
            torque_nm=40.0 + (i * 0.1),
            vibration_mm_s=2.0 + (i * 0.05),
            pressure_bar=5.0,
            current_a=12.0,
            voltage_v=400.0,
            tool_wear_min=100.0 + i,
            operating_hours=350.0 + (i * 0.01),
            delta_t_c=20.0 + (i * 0.1),
            power_va=4800.0,
            trip=None,
            buffered=0,
        )
        telemetry_records.append(t)
    session.add_all(telemetry_records)

    # Seed twin snapshots for MOT-1001
    snapshots = []
    for i in range(10):
        s_ts = now - timedelta(minutes=(30 - i * 3))
        h_score = 90.0 - (i * 1.5)
        h_state = "HEALTHY" if h_score >= 80 else "WARNING"
        snap = TwinSnapshotRecord(
            machine_id="MOT-1001",
            ts=s_ts,
            sync_status="LIVE",
            operating_state="RUNNING",
            health_state=h_state,
            health_score=h_score,
            risk_band="LOW" if h_score >= 80 else "MEDIUM",
            failure_probability=0.02 + (i * 0.01),
            anomaly_flag=False,
            snapshot_payload={
                "machine_id": "MOT-1001",
                "sync_status": "LIVE",
                "health_state": h_state,
                "health_score": h_score,
                "operating_state": "RUNNING",
                "risk_band": "LOW" if h_score >= 80 else "MEDIUM",
                "failure_probability": 0.02 + (i * 0.01),
                "last_telemetry_ts": s_ts.isoformat(),
            },
        )
        snapshots.append(snap)
    session.add_all(snapshots)

    # Seed 2 predictions for MOT-1001
    p1 = PredictionRecord(
        machine_id="MOT-1001",
        ts=now - timedelta(minutes=15),
        failure_probability=0.12,
        failure_prediction=0,
        risk_band="MEDIUM",
        anomaly_score=0.15,
        anomaly_flag=False,
        health_score=82.0,
        health_state="HEALTHY",
        top_factors=[{"feature": "Process_Temperature_C", "shap_value": 0.22}],
        model_version="v1.2-xgb",
        inference_latency_ms=12.5,
    )
    p2 = PredictionRecord(
        machine_id="MOT-1001",
        ts=now - timedelta(minutes=5),
        failure_probability=0.17,
        failure_prediction=1,
        risk_band="HIGH",
        anomaly_score=0.45,
        anomaly_flag=True,
        health_score=75.0,
        health_state="WARNING",
        top_factors=[{"feature": "Vibration_mm_s", "shap_value": 0.38}],
        model_version="v1.2-xgb",
        inference_latency_ms=14.1,
    )
    session.add_all([p1, p2])

    # Seed Alerts for MOT-1001 and PMP-2001
    a1 = AlertRecord(
        machine_id="MOT-1001",
        alert_type="PREDICTIVE_FAILURE_WARNING",
        severity="WARNING",
        status="OPEN",
        message="Failure risk elevated above threshold",
        trigger_conditions={"failure_probability": 0.17},
        top_factors=[{"feature": "Vibration_mm_s", "shap_value": 0.38}],
        triggered_at=now - timedelta(minutes=10),
    )
    a2 = AlertRecord(
        machine_id="MOT-1001",
        alert_type="PREDICTIVE_FAILURE_WARNING",
        severity="INFO",
        status="RESOLVED",
        message="Temporary temperature excursion resolved",
        trigger_conditions={},
        top_factors=[],
        triggered_at=now - timedelta(minutes=25),
        resolved_at=now - timedelta(minutes=20),
        resolved_by="admin_tester",
    )
    a3 = AlertRecord(
        machine_id="PMP-2001",
        alert_type="SAFETY_TRIP",
        severity="CRITICAL",
        status="OPEN",
        message="Critical cavitation trip",
        trigger_conditions={"trip": "CAVITATION"},
        top_factors=[],
        triggered_at=now - timedelta(minutes=5),
    )
    session.add_all([a1, a2, a3])

    # Seed Maintenance for MOT-1001
    maint1 = MaintenanceRecord(
        machine_id="MOT-1001",
        alert_id=a1.id,
        event_type="INSPECTION",
        description="Inspect vibration sensor mounting and bearing wear",
        status="SCHEDULED",
        technician="TECH-007",
        created_at=now - timedelta(minutes=8),
    )
    session.add(maint1)

    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def client(sqlite_db: Session) -> TestClient:
    """FastAPI TestClient with overridden get_db and mocked admin credentials."""
    mock_user = UserRecord(
        id=1,
        username="operator_tester",
        role="OPERATOR",
        is_active=True,
    )

    def _override_get_db():
        yield sqlite_db

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: mock_user
    with (
        patch("api.app.ingest.mqtt_client.MQTTIngestionClient.start"),
        patch("api.app.ingest.mqtt_client.MQTTIngestionClient.stop"),
        TestClient(app) as test_client,
    ):
        yield test_client
    app.dependency_overrides.clear()


class TestHistoryEndpoints:
    """Test suite for /api/v1/history/machines/{id} and /api/v1/history/fleet."""

    def test_get_machine_history_authenticated_200(self, client: TestClient):
        res = client.get("/api/v1/history/machines/MOT-1001?window=24h")
        assert res.status_code == 200
        data = res.json()

        assert data["machine_id"] == "MOT-1001"
        assert data["machine_type"] == "Motor"
        assert data["window"] == "24h"
        assert "from_ts" in data
        assert "to_ts" in data

        # Summary
        summary = data["summary"]
        assert summary["avg_health_score"] is not None
        assert summary["alert_count"] == 2
        assert summary["resolved_alert_count"] == 1
        assert summary["maintenance_count"] == 1
        assert summary["sample_count"] > 0

        # Trends
        assert len(data["health_trend"]) == 10
        assert len(data["sensor_trend"]) == 30
        assert len(data["prediction_history"]) == 2
        assert len(data["alerts"]) == 2
        assert len(data["maintenance"]) == 1

    def test_get_machine_history_unauthenticated_401(self, sqlite_db: Session):
        def _override_get_db():
            yield sqlite_db

        app.dependency_overrides[get_db] = _override_get_db
        # Remove get_current_user override so real auth runs and rejects unauthenticated request
        if get_current_user in app.dependency_overrides:
            del app.dependency_overrides[get_current_user]

        with TestClient(app) as unauth_client:
            res = unauth_client.get("/api/v1/history/machines/MOT-1001")
            assert res.status_code == 401
            assert res.headers["content-type"] == "application/problem+json"

        app.dependency_overrides.clear()

    def test_get_machine_history_not_found_404(self, client: TestClient):
        res = client.get("/api/v1/history/machines/UNKNOWN-999")
        assert res.status_code == 404
        assert res.headers["content-type"] == "application/problem+json"
        data = res.json()
        assert "not found" in data["detail"].lower()

    def test_get_machine_history_invalid_window_422(self, client: TestClient):
        res = client.get("/api/v1/history/machines/MOT-1001?window=99years")
        assert res.status_code == 422
        data = res.json()
        assert "invalid time window" in data["detail"].lower()

    def test_get_machine_history_empty_machine(self, client: TestClient):
        res = client.get("/api/v1/history/machines/GEN-3001?window=24h")
        assert res.status_code == 200
        data = res.json()

        assert data["machine_id"] == "GEN-3001"
        assert data["summary"]["avg_health_score"] is None
        assert data["summary"]["alert_count"] == 0
        assert data["summary"]["sample_count"] == 0
        assert data["health_trend"] == []
        assert data["sensor_trend"] == []
        assert data["alerts"] == []
        assert data["maintenance"] == []

    def test_get_machine_history_downsampling_enforced(self, client: TestClient):
        # We seeded 30 telemetry points. Request max_points=10.
        res = client.get("/api/v1/history/machines/MOT-1001?window=24h&max_points=10")
        assert res.status_code == 200
        data = res.json()

        assert data["is_downsampled"] is True
        assert data["downsample_interval_s"] is not None
        assert len(data["sensor_trend"]) <= 10

    def test_get_machine_history_defensible_durations(self, client: TestClient):
        res = client.get("/api/v1/history/machines/MOT-1001?window=24h")
        assert res.status_code == 200
        data = res.json()
        # Some points in MOT-1001 snapshot had health < 80 (WARNING)
        summary = data["summary"]
        assert summary["time_in_warning_s"] >= 0
        assert summary["time_in_critical_s"] >= 0

    def test_get_fleet_history_200(self, client: TestClient):
        res = client.get("/api/v1/history/fleet?window=24h")
        assert res.status_code == 200
        data = res.json()

        assert data["total_machines"] == 3
        assert "health_distribution" in data
        assert "risk_distribution" in data
        assert len(data["alerts_by_machine"]) == 3
        assert len(data["machine_summaries"]) == 3

        # MOT-1001 had 2 alerts, PMP-2001 had 1 alert (critical)
        alert_map = {a["machine_id"]: a for a in data["alerts_by_machine"]}
        assert alert_map["MOT-1001"]["alert_count"] == 2
        assert alert_map["PMP-2001"]["critical_count"] == 1

    def test_get_fleet_history_invalid_window_422(self, client: TestClient):
        res = client.get("/api/v1/history/fleet?window=bad_window")
        assert res.status_code == 422

    def test_get_history_no_mutation_side_effects(self, client: TestClient, sqlite_db: Session):
        count_alerts_before = sqlite_db.execute(select(AlertRecord)).scalars().all()
        count_telemetry_before = sqlite_db.execute(select(TelemetryRecord)).scalars().all()

        client.get("/api/v1/history/machines/MOT-1001?window=24h")
        client.get("/api/v1/history/fleet?window=24h")

        count_alerts_after = sqlite_db.execute(select(AlertRecord)).scalars().all()
        count_telemetry_after = sqlite_db.execute(select(TelemetryRecord)).scalars().all()

        assert len(count_alerts_before) == len(count_alerts_after)
        assert len(count_telemetry_before) == len(count_telemetry_after)

    def test_get_machine_history_explicit_bounds(self, client: TestClient):
        now = datetime.now(UTC)
        after_ts = (now - timedelta(hours=2)).isoformat()
        before_ts = now.isoformat()
        res = client.get(
            "/api/v1/history/machines/MOT-1001", params={"after": after_ts, "before": before_ts}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["machine_id"] == "MOT-1001"

    def test_get_machine_history_invalid_bounds_order_422(self, client: TestClient):
        now = datetime.now(UTC)
        after_ts = now.isoformat()
        before_ts = (now - timedelta(hours=2)).isoformat()
        res = client.get(
            "/api/v1/history/machines/MOT-1001", params={"after": after_ts, "before": before_ts}
        )
        assert res.status_code == 422
        data = res.json()
        assert "earlier than" in data["detail"].lower()

    def test_get_machine_history_predictions_content(self, client: TestClient):
        res = client.get("/api/v1/history/machines/MOT-1001?window=24h")
        assert res.status_code == 200
        preds = res.json()["prediction_history"]
        assert len(preds) == 2
        high_pred = next(p for p in preds if p["risk_band"] == "HIGH")
        assert high_pred["failure_prediction"] == 1
        assert high_pred["anomaly_flag"] is True
        assert high_pred["model_version"] == "v1.2-xgb"

    def test_get_machine_history_alerts_and_maintenance_content(self, client: TestClient):
        res = client.get("/api/v1/history/machines/MOT-1001?window=24h")
        assert res.status_code == 200
        data = res.json()
        alerts = data["alerts"]
        assert any(a["severity"] == "WARNING" and a["status"] == "OPEN" for a in alerts)
        assert any(a["status"] == "RESOLVED" and a["resolved_by"] == "admin_tester" for a in alerts)
        maint = data["maintenance"]
        assert len(maint) == 1
        assert maint[0]["event_type"] == "INSPECTION"
        assert maint[0]["status"] == "SCHEDULED"

    def test_history_openapi_docs(self, client: TestClient):
        res = client.get("/openapi.json")
        assert res.status_code == 200
        paths = res.json()["paths"]
        assert "/api/v1/history/machines/{machine_id}" in paths
        assert "/api/v1/history/fleet" in paths
