"""tests/api/test_auth.py — Comprehensive tests for T-038 Authentication, RBAC, and Security Hardening.

Test suite covers:
- PASSWORDS: hash difference, correct validation, wrong password failure, empty password
- AUTH: valid login, invalid password, unknown user, inactive user, token format, password absence,
        /me profile, missing token, expired token, malformed token, invalid signature
- RBAC: admin allowed, maintenance engineer allowed, operator allowed on reads, operator forbidden on
        privileged operations (403), unauthenticated rejected (401)
- COMMAND GUARD & SCENARIOS: valid role + valid command, operator forbidden (403), invalid scenario (422),
        invalid machine (404), unsafe code/command injection blocked (422)
- WEBSOCKET: unauthenticated rejected (1008 close), valid token accepted, invalid token rejected,
        expired token rejected, inactive user rejected
- SECURITY: CORS disallows wildcard, security headers present, passwords/JWTs not logged
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import jwt
import pytest
import starlette.websockets
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.app.config import get_settings
from api.app.db.base import Base
from api.app.db.session import get_db
from api.app.main import app
from api.app.models.alert import AlertRecord
from api.app.models.machine import MachineRecord
from api.app.models.user import UserRecord
from api.app.security.jwt import create_access_token
from api.app.security.passwords import hash_password, verify_password
from api.app.security.roles import UserRole

# ---------------------------------------------------------------------------
# Database & Test Setup Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session():
    """In-memory SQLite database session with seeded users and test assets."""
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

    # Seed users for each role
    admin = UserRecord(
        username="admin_user",
        password_hash=hash_password("AdminPass123!"),
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    engineer = UserRecord(
        username="engineer_user",
        password_hash=hash_password("EngineerPass123!"),
        role=UserRole.MAINTENANCE_ENGINEER.value,
        is_active=True,
    )
    operator = UserRecord(
        username="operator_user",
        password_hash=hash_password("OperatorPass123!"),
        role=UserRole.OPERATOR.value,
        is_active=True,
    )
    inactive = UserRecord(
        username="inactive_user",
        password_hash=hash_password("InactivePass123!"),
        role=UserRole.OPERATOR.value,
        is_active=False,
    )
    session.add_all([admin, engineer, operator, inactive])

    # Seed base machine asset
    machine = MachineRecord(
        machine_id="MOT-1001",
        machine_type="Motor",
        location="Cell-A",
        status="ACTIVE",
    )
    session.add(machine)
    session.flush()

    # Seed alert for MOT-1001
    alert = AlertRecord(
        machine_id="MOT-1001",
        alert_type="HIGH_TEMPERATURE",
        severity="WARNING",
        status="OPEN",
        message="Process temperature exceeded nominal warning limit",
        triggered_at=datetime.now(UTC),
    )
    session.add(alert)
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    """TestClient with database session override and mocked MQTT background client."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with (
        patch("api.app.ingest.mqtt_client.MQTTIngestionClient.start"),
        patch("api.app.ingest.mqtt_client.MQTTIngestionClient.stop"),
        TestClient(app) as test_client,
    ):
        yield test_client
    app.dependency_overrides.clear()


def make_auth_headers(token: str) -> dict[str, str]:
    """Helper to build standard Bearer Authorization header."""
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Password Hashing Tests
# ---------------------------------------------------------------------------


class TestPasswordHashing:
    def test_password_hash_differs_from_plaintext(self) -> None:
        raw_pw = "SuperSecurePassword99!"
        pw_hash = hash_password(raw_pw)
        assert pw_hash != raw_pw
        assert pw_hash.startswith(("$2b$", "$2a$"))

    def test_correct_password_validates(self) -> None:
        raw_pw = "IndustrialKey#2026"
        pw_hash = hash_password(raw_pw)
        assert verify_password(raw_pw, pw_hash) is True

    def test_wrong_password_fails(self) -> None:
        raw_pw = "IndustrialKey#2026"
        pw_hash = hash_password(raw_pw)
        assert verify_password("WrongPassword!", pw_hash) is False

    def test_empty_password_rejected(self) -> None:
        with pytest.raises(ValueError, match="Password must be a non-empty string"):
            hash_password("")


# ---------------------------------------------------------------------------
# 2. Authentication & Token Lifecycle Tests
# ---------------------------------------------------------------------------


class TestAuthentication:
    def test_valid_login_returns_jwt_token(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_user", "password": "AdminPass123!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == "ADMIN"
        assert data["username"] == "admin_user"
        assert data["expires_in"] == 3600

    def test_invalid_password_returns_401(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_user", "password": "WrongPassword!"},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert data["title"] == "HTTP Error" or data["status"] == 401
        assert "Invalid username or password" in data["detail"]

    def test_unknown_user_returns_401(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent_user", "password": "SomePassword123!"},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert "Invalid username or password" in data["detail"]

    def test_inactive_user_returns_401(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "inactive_user", "password": "InactivePass123!"},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert "deactivated" in data["detail"].lower()

    def test_login_never_returns_password_or_hash(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_user", "password": "AdminPass123!"},
        )
        assert resp.status_code == 200
        body_text = resp.text.lower()
        assert "adminpass123!" not in body_text
        assert "password_hash" not in body_text

    def test_get_me_returns_authenticated_user_profile(self, client: TestClient) -> None:
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"username": "engineer_user", "password": "EngineerPass123!"},
        )
        token = login_resp.json()["access_token"]

        resp = client.get("/api/v1/auth/me", headers=make_auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "engineer_user"
        assert data["role"] == "MAINTENANCE_ENGINEER"
        assert data["is_active"] is True
        assert "id" in data
        assert "password" not in data

    def test_missing_token_returns_401(self, client: TestClient) -> None:
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401
        data = resp.json()
        assert "Authentication required" in data["detail"]

    def test_expired_jwt_returns_401(self, client: TestClient) -> None:
        # Create expired token (-10 minutes)
        expired_token = create_access_token(
            subject="admin_user",
            role="ADMIN",
            expires_delta=timedelta(minutes=-10),
        )
        resp = client.get("/api/v1/auth/me", headers=make_auth_headers(expired_token))
        assert resp.status_code == 401
        data = resp.json()
        assert "expired" in data["detail"].lower()

    def test_malformed_jwt_returns_401(self, client: TestClient) -> None:
        resp = client.get(
            "/api/v1/auth/me",
            headers=make_auth_headers("not.a.valid.jwt.token"),
        )
        assert resp.status_code == 401
        data = resp.json()
        assert "invalid" in data["detail"].lower()

    def test_invalid_signature_returns_401(self, client: TestClient) -> None:
        settings = get_settings()
        # Sign with different secret
        bogus_token = jwt.encode(
            {
                "sub": "admin_user",
                "role": "ADMIN",
                "iat": int(datetime.now(UTC).timestamp()),
                "exp": int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
            },
            "attacker-crafted-secret-key-that-does-not-match",
            algorithm=settings.JWT_ALGORITHM,
        )
        resp = client.get("/api/v1/auth/me", headers=make_auth_headers(bogus_token))
        assert resp.status_code == 401
        data = resp.json()
        assert "invalid" in data["detail"].lower()


# ---------------------------------------------------------------------------
# 3. Role-Based Access Control (RBAC) Tests
# ---------------------------------------------------------------------------


class TestRBAC:
    @pytest.fixture()
    def tokens(self, client: TestClient) -> dict[str, str]:
        """Obtain valid tokens for all 3 roles."""
        admin_tok = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_user", "password": "AdminPass123!"},
        ).json()["access_token"]

        engineer_tok = client.post(
            "/api/v1/auth/login",
            json={"username": "engineer_user", "password": "EngineerPass123!"},
        ).json()["access_token"]

        operator_tok = client.post(
            "/api/v1/auth/login",
            json={"username": "operator_user", "password": "OperatorPass123!"},
        ).json()["access_token"]

        return {"ADMIN": admin_tok, "ENGINEER": engineer_tok, "OPERATOR": operator_tok}

    def test_admin_allowed_on_privileged_alert_patch(
        self, client: TestClient, tokens: dict[str, str]
    ) -> None:
        resp = client.patch(
            "/api/v1/alerts/1",
            json={"status": "ACKNOWLEDGED", "notes": "Admin reviewing thermal telemetry"},
            headers=make_auth_headers(tokens["ADMIN"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ACKNOWLEDGED"
        assert data["resolved_by"] == "admin_user"

    def test_maintenance_engineer_allowed_on_alert_patch(
        self, client: TestClient, tokens: dict[str, str]
    ) -> None:
        resp = client.patch(
            "/api/v1/alerts/1",
            json={"status": "RESOLVED", "notes": "Thermal sensor recalibrated"},
            headers=make_auth_headers(tokens["ENGINEER"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "RESOLVED"
        assert data["resolved_by"] == "engineer_user"

    def test_operator_forbidden_from_alert_patch_403(
        self, client: TestClient, tokens: dict[str, str]
    ) -> None:
        resp = client.patch(
            "/api/v1/alerts/1",
            json={"status": "ACKNOWLEDGED"},
            headers=make_auth_headers(tokens["OPERATOR"]),
        )
        assert resp.status_code == 403
        data = resp.json()
        assert "lacks permission" in data["detail"]

    def test_operator_allowed_on_read_endpoints(
        self, client: TestClient, tokens: dict[str, str]
    ) -> None:
        headers = make_auth_headers(tokens["OPERATOR"])
        # Machine fleet
        r1 = client.get("/api/v1/machines", headers=headers)
        assert r1.status_code == 200

        # Machine detail
        r2 = client.get("/api/v1/machines/MOT-1001", headers=headers)
        assert r2.status_code == 200

        # Fleet alerts
        r3 = client.get("/api/v1/alerts", headers=headers)
        assert r3.status_code == 200

    def test_operator_allowed_to_submit_feedback(
        self, client: TestClient, tokens: dict[str, str]
    ) -> None:
        headers = make_auth_headers(tokens["OPERATOR"])
        resp = client.post(
            "/api/v1/machines/MOT-1001/feedback",
            json={"feedback_type": "FALSE_ALARM", "alert_id": 1, "notes": "Routine load spike"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["feedback_type"] == "FALSE_ALARM"
        assert data["user_id"] == "operator_user"

    def test_unauthenticated_request_to_machines_returns_401(self, client: TestClient) -> None:
        resp = client.get("/api/v1/machines")
        assert resp.status_code == 401
        data = resp.json()
        assert "Authentication required" in data["detail"]


# ---------------------------------------------------------------------------
# 4. Command Guard & Scenario Control Tests
# ---------------------------------------------------------------------------


class TestCommandGuardAndScenarios:
    @pytest.fixture()
    def tokens(self, client: TestClient) -> dict[str, str]:
        admin_tok = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_user", "password": "AdminPass123!"},
        ).json()["access_token"]

        engineer_tok = client.post(
            "/api/v1/auth/login",
            json={"username": "engineer_user", "password": "EngineerPass123!"},
        ).json()["access_token"]

        operator_tok = client.post(
            "/api/v1/auth/login",
            json={"username": "operator_user", "password": "OperatorPass123!"},
        ).json()["access_token"]

        return {"ADMIN": admin_tok, "ENGINEER": engineer_tok, "OPERATOR": operator_tok}

    def test_list_scenarios_authenticated(self, client: TestClient, tokens: dict[str, str]) -> None:
        resp = client.get("/api/v1/scenarios", headers=make_auth_headers(tokens["OPERATOR"]))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 8
        scenario_ids = [s["scenario_id"] for s in data["scenarios"]]
        assert "SCN-01" in scenario_ids
        assert "SCN-02" in scenario_ids
        assert "SCN-08" in scenario_ids

    def test_inject_scenario_admin_success(
        self, client: TestClient, tokens: dict[str, str]
    ) -> None:
        resp = client.post(
            "/api/v1/scenarios/inject",
            json={"machine_id": "MOT-1001", "scenario_id": "SCN-02", "parameters": {}},
            headers=make_auth_headers(tokens["ADMIN"]),
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "ACCEPTED"
        assert data["scenario_id"] == "SCN-02"
        assert data["machine_id"] == "MOT-1001"
        assert data["injected_by"] == "admin_user"
        assert "command_id" in data

    def test_inject_scenario_engineer_success(
        self, client: TestClient, tokens: dict[str, str]
    ) -> None:
        resp = client.post(
            "/api/v1/scenarios/inject",
            json={"machine_id": "MOT-1001", "scenario_id": "SCN-04", "parameters": {}},
            headers=make_auth_headers(tokens["ENGINEER"]),
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "ACCEPTED"
        assert data["scenario_id"] == "SCN-04"
        assert data["injected_by"] == "engineer_user"

    def test_inject_scenario_operator_forbidden_403(
        self, client: TestClient, tokens: dict[str, str]
    ) -> None:
        resp = client.post(
            "/api/v1/scenarios/inject",
            json={"machine_id": "MOT-1001", "scenario_id": "SCN-02"},
            headers=make_auth_headers(tokens["OPERATOR"]),
        )
        assert resp.status_code == 403
        data = resp.json()
        assert "lacks permission" in data["detail"]

    def test_inject_scenario_invalid_machine_404(
        self, client: TestClient, tokens: dict[str, str]
    ) -> None:
        resp = client.post(
            "/api/v1/scenarios/inject",
            json={"machine_id": "MOT-9999", "scenario_id": "SCN-02"},
            headers=make_auth_headers(tokens["ADMIN"]),
        )
        assert resp.status_code == 404
        data = resp.json()
        assert "MOT-9999" in data["detail"]

    def test_inject_scenario_invalid_scenario_id_422(
        self, client: TestClient, tokens: dict[str, str]
    ) -> None:
        resp = client.post(
            "/api/v1/scenarios/inject",
            json={"machine_id": "MOT-1001", "scenario_id": "SCN-INVALID-99"},
            headers=make_auth_headers(tokens["ADMIN"]),
        )
        assert resp.status_code == 422

    def test_inject_scenario_arbitrary_code_command_rejected_422(
        self, client: TestClient, tokens: dict[str, str]
    ) -> None:
        resp = client.post(
            "/api/v1/scenarios/inject",
            json={
                "machine_id": "MOT-1001",
                "scenario_id": "SCN-01",
                "parameters": {"eval": "import os; os.system('whoami')"},
            },
            headers=make_auth_headers(tokens["ADMIN"]),
        )
        assert resp.status_code == 422
        data = resp.json()
        assert "Unsafe execution parameter" in data["detail"]


# ---------------------------------------------------------------------------
# 5. WebSocket Authentication Tests
# ---------------------------------------------------------------------------


class TestWebSocketAuthentication:
    def test_ws_unauthenticated_connection_rejected(self, client: TestClient) -> None:
        with (
            pytest.raises(starlette.websockets.WebSocketDisconnect) as exc_info,
            client.websocket_connect("/ws/live"),
        ):
            pass
        assert exc_info.value.code == 1008

    def test_ws_valid_token_accepted(self, client: TestClient) -> None:
        token = create_access_token(subject="operator_user", role="OPERATOR")
        with client.websocket_connect(f"/ws/live?token={token}") as ws:
            msg = ws.receive_json()
            assert msg["event"] == "snapshot"

    def test_ws_valid_token_single_machine_accepted(self, client: TestClient) -> None:
        token = create_access_token(subject="engineer_user", role="MAINTENANCE_ENGINEER")
        with client.websocket_connect(f"/ws/live/MOT-1001?token={token}") as ws:
            msg = ws.receive_json()
            assert msg["event"] == "snapshot"

    def test_ws_invalid_token_rejected(self, client: TestClient) -> None:
        with (
            pytest.raises(starlette.websockets.WebSocketDisconnect) as exc_info,
            client.websocket_connect("/ws/live?token=invalid.jwt.token"),
        ):
            pass
        assert exc_info.value.code == 1008

    def test_ws_expired_token_rejected(self, client: TestClient) -> None:
        expired_token = create_access_token(
            subject="operator_user",
            role="OPERATOR",
            expires_delta=timedelta(minutes=-5),
        )
        with (
            pytest.raises(starlette.websockets.WebSocketDisconnect) as exc_info,
            client.websocket_connect(f"/ws/live?token={expired_token}"),
        ):
            pass
        assert exc_info.value.code == 1008

    def test_ws_inactive_user_rejected(self, client: TestClient) -> None:
        inactive_token = create_access_token(
            subject="inactive_user",
            role="OPERATOR",
        )
        with (
            pytest.raises(starlette.websockets.WebSocketDisconnect) as exc_info,
            client.websocket_connect(f"/ws/live?token={inactive_token}"),
        ):
            pass
        assert exc_info.value.code == 1008


# ---------------------------------------------------------------------------
# 6. Security Hardening & Headers Tests
# ---------------------------------------------------------------------------


class TestSecurityHardening:
    def test_security_headers_present(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        headers = resp.headers
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert headers.get("X-XSS-Protection") == "1; mode=block"

    def test_cors_disallows_wildcard_with_credentials(self) -> None:
        from api.app.config import Settings

        with pytest.raises(ValueError, match="Wildcard CORS origin"):
            Settings(CORS_ORIGINS=["*"])

        with pytest.raises(ValueError, match="Wildcard CORS origin"):
            Settings(CORS_ORIGINS="*")

    def test_password_and_jwt_not_in_audit_logs(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.INFO)
        raw_password = "AdminPass123!"

        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_user", "password": raw_password},
        )
        assert resp.status_code == 200
        jwt_token = resp.json()["access_token"]

        # Check logs captured during login
        captured_text = caplog.text
        assert raw_password not in captured_text
        assert jwt_token not in captured_text
