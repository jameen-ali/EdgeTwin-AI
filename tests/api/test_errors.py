"""Tests for error handling and CORS policies."""

import pytest
from fastapi.testclient import TestClient

from api.app.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


def test_404_not_found_problem_details(client):
    """Verify 404 responses conform to RFC 7807 problem details structure."""
    response = client.get("/non_existent_route")
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == 404
    assert data["title"] == "HTTP Error"
    assert "Not Found" in data["detail"]
    assert data["instance"] == "/non_existent_route"


def test_cors_headers(client):
    """Verify CORS middleware sets appropriate headers for allowed origins."""
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/health", headers=headers)
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "GET" in response.headers.get("access-control-allow-methods", "")
