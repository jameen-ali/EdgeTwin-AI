"""
tests/api/test_mlops_api.py — Integration and RBAC tests for MLOps endpoints (T-060).

Covers:
- Authentication requirement (401 for unauthenticated requests).
- MLOps overview endpoint (/api/v1/mlops/overview).
- Feature drift endpoint (/api/v1/mlops/drift).
- Feedback performance endpoint (/api/v1/mlops/performance).
- Insufficient data handling on empty database.
- Telemetry evaluation and drift detection.
- Operator feedback metric calculation.
- RBAC validation: all authenticated roles (Admin, Maintenance Engineer, Operator) have read access.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

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
from api.app.models.telemetry import TelemetryRecord
from api.app.models.user import UserRecord
from api.app.security.deps import get_current_user


@pytest.fixture()
def db_session():
    """In-memory SQLite database isolated per test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session: Session):
    """FastAPI TestClient with overridden database session."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_user(db_session: Session) -> UserRecord:
    """Create and return an active ADMIN user."""
    user = UserRecord(
        id=1,
        username="admin_test",
        password_hash="fakehash",
        role="ADMIN",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def operator_user(db_session: Session) -> UserRecord:
    """Create and return an active OPERATOR user."""
    user = UserRecord(
        id=2,
        username="operator_test",
        password_hash="fakehash",
        role="OPERATOR",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def sample_machine(db_session: Session) -> MachineRecord:
    """Create a sample monitored machine."""
    machine = MachineRecord(
        machine_id="CNC-1001",
        machine_type="CNC_Machine",
        location="Shop Floor 1",
        status="RUNNING",
    )
    db_session.add(machine)
    db_session.commit()
    db_session.refresh(machine)
    return machine


# ===========================================================================
# Tests
# ===========================================================================


class TestMLOpsAPI:
    """Test suite for MLOps REST endpoints."""

    def test_unauthenticated_request_rejected(self, client: TestClient) -> None:
        """Unauthenticated requests must be rejected with 401 Unauthorized."""
        response = client.get("/api/v1/mlops/overview")
        assert response.status_code == 401

        response = client.get("/api/v1/mlops/drift")
        assert response.status_code == 401

        response = client.get("/api/v1/mlops/performance")
        assert response.status_code == 401

    def test_get_mlops_overview_empty_db(self, client: TestClient, admin_user: UserRecord) -> None:
        """Overview endpoint on empty database returns INSUFFICIENT_DATA gracefully."""
        app.dependency_overrides[get_current_user] = lambda: admin_user

        response = client.get("/api/v1/mlops/overview")
        assert response.status_code == 200
        data = response.json()

        assert "model_version" in data
        assert "drift" in data
        assert "performance" in data
        assert data["drift"]["overall_status"] == "INSUFFICIENT_DATA"
        assert data["performance"]["status"] == "INSUFFICIENT_DATA"
        assert data["performance"]["precision"] is None

    def test_get_drift_report_with_telemetry_data(
        self,
        client: TestClient,
        admin_user: UserRecord,
        sample_machine: MachineRecord,
        db_session: Session,
    ) -> None:
        """Drift endpoint evaluates all 14 features when sufficient telemetry rows exist."""
        app.dependency_overrides[get_current_user] = lambda: admin_user

        # Seed 40 telemetry observations (> MIN_SAMPLE_SIZE = 30)
        base_time = datetime.now(UTC) - timedelta(hours=1)
        for i in range(40):
            tel = TelemetryRecord(
                machine_id=sample_machine.machine_id,
                seq=i + 1,
                ts=base_time + timedelta(seconds=i * 5),
                provenance="SIMULATED",
                fw="v1.0.0",
                air_temp_c=25.0 + (i % 3),
                process_temp_c=35.0 + (i % 4),
                rotational_speed_rpm=1500.0 + (i % 20),
                torque_nm=40.0 + (i % 5),
                vibration_mm_s=2.5 + (i % 2) * 0.1,
                pressure_bar=5.0,
                current_a=15.0,
                voltage_v=400.0,
                tool_wear_min=50.0 + i,
                operating_hours=100.0 + i,
            )
            db_session.add(tel)
        db_session.commit()

        response = client.get("/api/v1/mlops/drift")
        assert response.status_code == 200
        data = response.json()

        assert data["current_sample_count"] == 40
        assert data["reference_version"] == "v1.0-train-split"
        assert len(data["features"]) == 14

        # Verify numeric feature has both PSI and KS computed
        vibration_feat = next(
            (f for f in data["features"] if f["feature_name"] == "Vibration_mm_s"), None
        )
        assert vibration_feat is not None
        assert vibration_feat["feature_type"] == "numeric"
        assert vibration_feat["psi"] is not None
        assert vibration_feat["ks_statistic"] is not None
        assert vibration_feat["status"] in ("STABLE", "WATCH", "DRIFT")

        # Verify categorical feature has PSI but KS is None
        type_feat = next((f for f in data["features"] if f["feature_name"] == "Machine_Type"), None)
        assert type_feat is not None
        assert type_feat["feature_type"] == "categorical"
        assert type_feat["psi"] is not None
        assert type_feat["ks_statistic"] is None

    def test_get_performance_metrics_with_feedback(
        self,
        client: TestClient,
        admin_user: UserRecord,
        sample_machine: MachineRecord,
        db_session: Session,
    ) -> None:
        """Performance endpoint calculates precision and false alarm rate from operator feedback."""
        app.dependency_overrides[get_current_user] = lambda: admin_user

        # Create alert
        alert = AlertRecord(
            machine_id=sample_machine.machine_id,
            alert_type="PREDICTIVE_FAILURE",
            severity="CRITICAL",
            status="RESOLVED",
            message="High failure risk detected",
            triggered_at=datetime.now(UTC) - timedelta(hours=2),
        )
        db_session.add(alert)
        db_session.commit()
        db_session.refresh(alert)

        # Seed 6 feedback records: 4 CONFIRMED, 2 FALSE_ALARM (Precision = 4/6 = 0.6667)
        for i in range(4):
            fb = FeedbackRecord(
                machine_id=sample_machine.machine_id,
                alert_id=alert.id,
                feedback_type="CONFIRMED",
                notes=f"Confirmed wear finding {i}",
                user_id="tech_1",
            )
            db_session.add(fb)
        for i in range(2):
            fb = FeedbackRecord(
                machine_id=sample_machine.machine_id,
                alert_id=alert.id,
                feedback_type="FALSE_ALARM",
                notes=f"False alarm finding {i}",
                user_id="tech_2",
            )
            db_session.add(fb)
        db_session.commit()

        response = client.get("/api/v1/mlops/performance")
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "SUFFICIENT"
        assert data["total_feedback"] == 6
        assert data["confirmed_count"] == 4
        assert data["false_alarm_count"] == 2
        assert data["precision"] == 0.6667
        assert data["false_alarm_rate"] == 0.3333

    def test_operator_role_has_read_access(
        self, client: TestClient, operator_user: UserRecord
    ) -> None:
        """Operator role must be authorized to view MLOps monitoring data (read-only)."""
        app.dependency_overrides[get_current_user] = lambda: operator_user

        response = client.get("/api/v1/mlops/overview")
        assert response.status_code == 200

        response = client.get("/api/v1/mlops/drift")
        assert response.status_code == 200

        response = client.get("/api/v1/mlops/performance")
        assert response.status_code == 200
