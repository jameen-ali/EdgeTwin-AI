"""
tests/api/test_retrain_api.py — Integration and RBAC tests for T-061 retraining endpoints.

Covers:
- Authentication: unauthenticated requests rejected with 401.
- RBAC: correct role enforcement on all 6 endpoints.
  - POST /retrain/run → ADMIN + MAINTENANCE_ENGINEER (OPERATOR rejected)
  - GET  /retrain/gate → ADMIN + MAINTENANCE_ENGINEER (OPERATOR rejected)
  - POST /retrain/promote → ADMIN only (MAINTENANCE_ENGINEER + OPERATOR rejected)
  - POST /retrain/rollback → ADMIN only (MAINTENANCE_ENGINEER + OPERATOR rejected)
  - GET  /retrain/registry → ADMIN + MAINTENANCE_ENGINEER (OPERATOR rejected)
  - GET  /retrain/audit-log → ADMIN only (all others rejected)
- Retrain endpoint: success returns 202 with ChallengerResultDTO.
- Gate endpoint: returns PromotionGateDTO.
- Promote endpoint: success returns PromotionResultDTO; gate failure returns 409.
- Rollback endpoint: success returns RollbackResultDTO; invalid version returns 422.
- Registry endpoint: returns ModelRegistryDTO.
- Audit log: returns AuditLogDTO with correct entries.
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
from api.app.models.user import UserRecord
from api.app.security.deps import get_current_user
from api.app.security.roles import UserRole

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session():
    """In-memory SQLite session isolated per test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_connection, connection_record):
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


def _make_user(user_id: int, username: str, role: str, db_session: Session) -> UserRecord:
    user = UserRecord(
        id=user_id,
        username=username,
        password_hash="fakehash",
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def admin_user(db_session: Session) -> UserRecord:
    return _make_user(1, "admin_test", UserRole.ADMIN.value, db_session)


@pytest.fixture()
def engineer_user(db_session: Session) -> UserRecord:
    return _make_user(2, "engineer_test", UserRole.MAINTENANCE_ENGINEER.value, db_session)


@pytest.fixture()
def operator_user(db_session: Session) -> UserRecord:
    return _make_user(3, "operator_test", UserRole.OPERATOR.value, db_session)


# ---------------------------------------------------------------------------
# Dummy DTOs for mocking service layer
# ---------------------------------------------------------------------------


def _dummy_challenger_result_dto() -> dict:
    return {
        "run_id": "test-run-001",
        "challenger_version": "3",
        "challenger_uri": "models:/edgetwin-risk@challenger",
        "val_recall": 0.85,
        "val_precision": 0.70,
        "val_pr_auc": 0.80,
        "val_roc_auc": 0.90,
        "val_f1": 0.77,
        "feature_cols": [f"feat_{i}" for i in range(14)],
        "artifacts_dir": "/tmp/artifacts",
        "authorized_train_version": "v1.0-train-split",
        "train_sha256": "a" * 64,
        "val_sha256": "b" * 64,
        "retrain_timestamp": datetime.now(UTC).isoformat(),
    }


def _dummy_gate_dto(gate_passed: bool = True) -> dict:
    return {
        "gate_passed": gate_passed,
        "challenger_version": "3",
        "champion_version": "2",
        "challenger_val_recall": 0.85,
        "challenger_val_precision": 0.70,
        "challenger_val_pr_auc": 0.80,
        "champion_val_recall": 0.80,
        "champion_val_precision": 0.65,
        "champion_val_pr_auc": 0.75,
        "recall_delta": 0.05,
        "precision_delta": 0.05,
        "pr_auc_delta": 0.05,
        "checks_passed": ["recall_protection", "precision_floor"],
        "checks_failed": [],
        "gate_reason": "All checks passed",
        "technical_gate": {"status": "PASSED"},
        "evaluated_at": datetime.now(UTC).isoformat(),
    }


def _dummy_promote_dto() -> dict:
    return {
        "promoted": True,
        "new_champion_version": "3",
        "previous_champion_version": "2",
        "actor": "admin_test",
        "gate_result": _dummy_gate_dto(gate_passed=True),
        "promoted_at": datetime.now(UTC).isoformat(),
        "notes": "",
    }


def _dummy_rollback_dto() -> dict:
    return {
        "rolled_back": True,
        "restored_champion_version": "1",
        "demoted_version": "3",
        "actor": "admin_test",
        "reason": "Production incident INC-0001",
        "rolled_back_at": datetime.now(UTC).isoformat(),
    }


def _dummy_registry_dto() -> dict:
    return {
        "model_name": "edgetwin-risk",
        "total_versions": 2,
        "champion_version": "2",
        "challenger_version": "3",
        "versions": [
            {
                "version": "2",
                "status": "READY",
                "aliases": ["champion"],
                "run_id": "run-002",
                "created_at": 1700000000000,
                "val_recall_at_t_star": 0.80,
                "val_precision_at_t_star": 0.65,
                "val_pr_auc": 0.75,
                "val_roc_auc": 0.88,
            }
        ],
        "generated_at": datetime.now(UTC).isoformat(),
    }


def _dummy_audit_log_dto() -> dict:
    return {
        "total_entries": 2,
        "entries": [
            {
                "event": "retrain_started",
                "actor": "engineer_test",
                "timestamp": datetime.now(UTC).isoformat(),
                "git_commit": "abc123",
                "authorized_train_version": "v1.0-train-split",
                "train_sha256": "a" * 64,
                "val_sha256": "b" * 64,
                "mlflow_run_id": "",
                "challenger_version": "",
                "val_recall": None,
                "val_precision": None,
                "val_pr_auc": None,
                "notes": "",
                "error": "",
            }
        ],
        "generated_at": datetime.now(UTC).isoformat(),
    }


# ---------------------------------------------------------------------------
# T-061-API-01: Authentication enforcement
# ---------------------------------------------------------------------------


class TestRetrainAPIAuthentication:
    """All endpoints must reject unauthenticated requests with 401."""

    def test_all_endpoints_require_auth(self, client: TestClient) -> None:
        """Unauthenticated requests to all retrain endpoints must return 401."""
        endpoints = [
            ("POST", "/api/v1/retrain/run", {}),
            ("GET", "/api/v1/retrain/gate", None),
            ("POST", "/api/v1/retrain/promote", {}),
            ("POST", "/api/v1/retrain/rollback", {"target_version": "1", "reason": "x" * 10}),
            ("GET", "/api/v1/retrain/registry", None),
            ("GET", "/api/v1/retrain/audit-log", None),
        ]
        for method, url, body in endpoints:
            if method == "POST":
                response = client.post(url, json=body)
            else:
                response = client.get(url)
            assert (
                response.status_code == 401
            ), f"Expected 401 for {method} {url}, got {response.status_code}"


# ---------------------------------------------------------------------------
# T-061-API-02: RBAC enforcement
# ---------------------------------------------------------------------------


class TestRetrainAPIRBAC:
    """Verify RBAC enforcement on all retrain endpoints."""

    # ---- Retrain: ADMIN + ENGINEER can, OPERATOR cannot ----

    def test_operator_cannot_initiate_retrain(
        self, client: TestClient, operator_user: UserRecord
    ) -> None:
        """OPERATOR must be rejected from POST /retrain/run (403)."""
        app.dependency_overrides[get_current_user] = lambda: operator_user
        response = client.post("/api/v1/retrain/run", json={"run_name": "test"})
        assert response.status_code == 403

    def test_engineer_can_view_gate(self, client: TestClient, engineer_user: UserRecord) -> None:
        """MAINTENANCE_ENGINEER can access GET /retrain/gate."""
        app.dependency_overrides[get_current_user] = lambda: engineer_user

        from api.app.schemas.retrain import PromotionGateDTO

        gate_data = _dummy_gate_dto()
        mock_gate = PromotionGateDTO(**gate_data)

        with patch(
            "api.app.services.retrain_service.RetrainService.get_promotion_gate",
            return_value=mock_gate,
        ):
            response = client.get("/api/v1/retrain/gate")

        assert response.status_code == 200

    def test_operator_cannot_view_gate(self, client: TestClient, operator_user: UserRecord) -> None:
        """OPERATOR must be rejected from GET /retrain/gate (403)."""
        app.dependency_overrides[get_current_user] = lambda: operator_user
        response = client.get("/api/v1/retrain/gate")
        assert response.status_code == 403

    # ---- Promote: ADMIN only ----

    def test_engineer_cannot_promote(self, client: TestClient, engineer_user: UserRecord) -> None:
        """MAINTENANCE_ENGINEER must be rejected from POST /retrain/promote (403)."""
        app.dependency_overrides[get_current_user] = lambda: engineer_user
        response = client.post("/api/v1/retrain/promote")
        assert response.status_code == 403

    def test_operator_cannot_promote(self, client: TestClient, operator_user: UserRecord) -> None:
        """OPERATOR must be rejected from POST /retrain/promote (403)."""
        app.dependency_overrides[get_current_user] = lambda: operator_user
        response = client.post("/api/v1/retrain/promote")
        assert response.status_code == 403

    # ---- Rollback: ADMIN only ----

    def test_engineer_cannot_rollback(self, client: TestClient, engineer_user: UserRecord) -> None:
        """MAINTENANCE_ENGINEER must be rejected from POST /retrain/rollback (403)."""
        app.dependency_overrides[get_current_user] = lambda: engineer_user
        response = client.post(
            "/api/v1/retrain/rollback",
            json={"target_version": "1", "reason": "test reason here"},
        )
        assert response.status_code == 403

    def test_operator_cannot_rollback(self, client: TestClient, operator_user: UserRecord) -> None:
        """OPERATOR must be rejected from POST /retrain/rollback (403)."""
        app.dependency_overrides[get_current_user] = lambda: operator_user
        response = client.post(
            "/api/v1/retrain/rollback",
            json={"target_version": "1", "reason": "test reason here"},
        )
        assert response.status_code == 403

    # ---- Audit log: ADMIN only ----

    def test_engineer_cannot_access_audit_log(
        self, client: TestClient, engineer_user: UserRecord
    ) -> None:
        """MAINTENANCE_ENGINEER must be rejected from GET /retrain/audit-log (403)."""
        app.dependency_overrides[get_current_user] = lambda: engineer_user
        response = client.get("/api/v1/retrain/audit-log")
        assert response.status_code == 403

    def test_operator_cannot_access_audit_log(
        self, client: TestClient, operator_user: UserRecord
    ) -> None:
        """OPERATOR must be rejected from GET /retrain/audit-log (403)."""
        app.dependency_overrides[get_current_user] = lambda: operator_user
        response = client.get("/api/v1/retrain/audit-log")
        assert response.status_code == 403

    # ---- Registry: ADMIN + ENGINEER can ----

    def test_operator_cannot_view_registry(
        self, client: TestClient, operator_user: UserRecord
    ) -> None:
        """OPERATOR must be rejected from GET /retrain/registry (403)."""
        app.dependency_overrides[get_current_user] = lambda: operator_user
        response = client.get("/api/v1/retrain/registry")
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# T-061-API-03: Endpoint response schemas
# ---------------------------------------------------------------------------


class TestRetrainAPIResponses:
    """Verify endpoint response schemas for admin users."""

    def test_retrain_run_returns_202_with_dto(
        self, client: TestClient, admin_user: UserRecord
    ) -> None:
        """POST /retrain/run must return 202 with ChallengerResultDTO schema."""
        app.dependency_overrides[get_current_user] = lambda: admin_user

        from api.app.schemas.retrain import ChallengerResultDTO

        result_data = _dummy_challenger_result_dto()
        mock_result = ChallengerResultDTO(**result_data)

        with patch(
            "api.app.services.retrain_service.RetrainService.run_retrain",
            return_value=mock_result,
        ):
            response = client.post(
                "/api/v1/retrain/run",
                json={"run_name": "test-run", "seed": 42, "notes": ""},
            )

        assert response.status_code == 202
        data = response.json()
        assert "run_id" in data
        assert "challenger_version" in data
        assert "val_recall" in data
        assert "val_precision" in data
        assert "feature_cols" in data
        assert len(data["feature_cols"]) == 14

    def test_gate_endpoint_returns_gate_dto(
        self, client: TestClient, admin_user: UserRecord
    ) -> None:
        """GET /retrain/gate must return PromotionGateDTO schema."""
        app.dependency_overrides[get_current_user] = lambda: admin_user

        from api.app.schemas.retrain import PromotionGateDTO

        gate_data = _dummy_gate_dto()
        mock_gate = PromotionGateDTO(**gate_data)

        with patch(
            "api.app.services.retrain_service.RetrainService.get_promotion_gate",
            return_value=mock_gate,
        ):
            response = client.get("/api/v1/retrain/gate")

        assert response.status_code == 200
        data = response.json()
        assert "gate_passed" in data
        assert "checks_passed" in data
        assert "checks_failed" in data
        assert "recall_delta" in data

    def test_promote_endpoint_success_returns_200(
        self, client: TestClient, admin_user: UserRecord
    ) -> None:
        """POST /retrain/promote with passing gate must return 200 PromotionResultDTO."""
        app.dependency_overrides[get_current_user] = lambda: admin_user

        from api.app.schemas.retrain import PromotionResultDTO

        promote_data = _dummy_promote_dto()
        mock_result = PromotionResultDTO(**promote_data)

        with patch(
            "api.app.services.retrain_service.RetrainService.promote",
            return_value=mock_result,
        ):
            response = client.post("/api/v1/retrain/promote")

        assert response.status_code == 200
        data = response.json()
        assert data["promoted"] is True
        assert "new_champion_version" in data
        assert "previous_champion_version" in data
        assert "gate_result" in data

    def test_promote_endpoint_returns_409_on_gate_failure(
        self, client: TestClient, admin_user: UserRecord
    ) -> None:
        """POST /retrain/promote must return 409 when gate fails."""
        app.dependency_overrides[get_current_user] = lambda: admin_user

        with patch(
            "api.app.services.retrain_service.RetrainService.promote",
            side_effect=ValueError("Promotion gate FAILED: recall regression"),
        ):
            response = client.post("/api/v1/retrain/promote")

        assert response.status_code == 409
        data = response.json()
        assert "gate" in data.get("detail", "").lower() or "Promotion" in data.get("detail", "")

    def test_rollback_endpoint_success_returns_200(
        self, client: TestClient, admin_user: UserRecord
    ) -> None:
        """POST /retrain/rollback with valid version must return 200 RollbackResultDTO."""
        app.dependency_overrides[get_current_user] = lambda: admin_user

        from api.app.schemas.retrain import RollbackResultDTO

        rollback_data = _dummy_rollback_dto()
        mock_result = RollbackResultDTO(**rollback_data)

        with patch(
            "api.app.services.retrain_service.RetrainService.rollback",
            return_value=mock_result,
        ):
            response = client.post(
                "/api/v1/retrain/rollback",
                json={
                    "target_version": "1",
                    "reason": "Production incident INC-0001: false alarm storm",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["rolled_back"] is True
        assert data["restored_champion_version"] == "1"

    def test_rollback_endpoint_returns_422_on_invalid_version(
        self, client: TestClient, admin_user: UserRecord
    ) -> None:
        """POST /retrain/rollback with non-existent version must return 422."""
        app.dependency_overrides[get_current_user] = lambda: admin_user

        with patch(
            "api.app.services.retrain_service.RetrainService.rollback",
            side_effect=ValueError("Target version '999' does not exist"),
        ):
            response = client.post(
                "/api/v1/retrain/rollback",
                json={
                    "target_version": "999",
                    "reason": "Testing nonexistent version behavior",
                },
            )

        assert response.status_code == 422

    def test_rollback_endpoint_rejects_short_reason(
        self, client: TestClient, admin_user: UserRecord
    ) -> None:
        """POST /retrain/rollback with reason < 10 chars must return 422 (validation)."""
        app.dependency_overrides[get_current_user] = lambda: admin_user

        response = client.post(
            "/api/v1/retrain/rollback",
            json={"target_version": "1", "reason": "short"},  # only 5 chars
        )
        assert response.status_code == 422

    def test_registry_endpoint_returns_model_registry_dto(
        self, client: TestClient, admin_user: UserRecord
    ) -> None:
        """GET /retrain/registry must return ModelRegistryDTO schema."""
        app.dependency_overrides[get_current_user] = lambda: admin_user

        from api.app.schemas.retrain import ModelRegistryDTO

        registry_data = _dummy_registry_dto()
        mock_registry = ModelRegistryDTO(**registry_data)

        with patch(
            "api.app.services.retrain_service.RetrainService.get_model_registry",
            return_value=mock_registry,
        ):
            response = client.get("/api/v1/retrain/registry")

        assert response.status_code == 200
        data = response.json()
        assert "model_name" in data
        assert "versions" in data
        assert "champion_version" in data
        assert "total_versions" in data

    def test_audit_log_endpoint_returns_audit_log_dto(
        self, client: TestClient, admin_user: UserRecord
    ) -> None:
        """GET /retrain/audit-log must return AuditLogDTO schema."""
        app.dependency_overrides[get_current_user] = lambda: admin_user

        from api.app.schemas.retrain import AuditLogDTO

        audit_data = _dummy_audit_log_dto()
        mock_audit = AuditLogDTO(**audit_data)

        with patch(
            "api.app.services.retrain_service.RetrainService.get_audit_log",
            return_value=mock_audit,
        ):
            response = client.get("/api/v1/retrain/audit-log")

        assert response.status_code == 200
        data = response.json()
        assert "total_entries" in data
        assert "entries" in data
        assert "generated_at" in data

    def test_audit_log_limit_parameter_accepted(
        self, client: TestClient, admin_user: UserRecord
    ) -> None:
        """GET /retrain/audit-log?limit=5 must be accepted (valid query param)."""
        app.dependency_overrides[get_current_user] = lambda: admin_user

        from api.app.schemas.retrain import AuditLogDTO

        audit_data = _dummy_audit_log_dto()
        mock_audit = AuditLogDTO(**audit_data)

        with patch(
            "api.app.services.retrain_service.RetrainService.get_audit_log",
            return_value=mock_audit,
        ) as mock_svc:
            response = client.get("/api/v1/retrain/audit-log?limit=5")

        assert response.status_code == 200
        mock_svc.assert_called_once_with(limit=5)
