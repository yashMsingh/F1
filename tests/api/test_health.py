"""Tests for API health check endpoint."""

from fastapi.testclient import TestClient

from app.api.app import app


def test_health_check():
    """Verify GET /api/health returns 200 with status ok."""
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
