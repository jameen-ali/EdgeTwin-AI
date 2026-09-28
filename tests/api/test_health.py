"""Tests for health and readiness endpoints."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.app.main import create_app


@pytest.fixture
def client():
    """Create test client fixture."""
    app = create_app()
    return TestClient(app)


def test_health_endpoint_root(client):
    """Verify GET /health returns 200 OK with proper payload."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data
    assert "version" in data
    assert "environment" in data


def test_health_endpoint_v1(client):
    """Verify GET /api/v1/health returns 200 OK."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_ready_endpoint_success(client):
    """Verify GET /ready returns 200 when database connection succeeds."""
    with patch("api.app.routes.health.check_db_connection", return_value=(True, None)):
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"
        assert data["detail"] is None


def test_ready_endpoint_failure(client):
    """Verify GET /ready returns 503 Service Unavailable when database connection fails."""
    with patch(
        "api.app.routes.health.check_db_connection", return_value=(False, "Connection refused")
    ):
        response = client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unready"
        assert data["database"] == "disconnected"
        assert "Connection refused" in data["detail"]
