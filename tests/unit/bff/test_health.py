"""Unit tests for BFF health endpoints.

Tests health and readiness endpoints per AC2 requirements.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def bff_client():
    """Create a test client for the BFF application."""
    from bff.main import create_app

    app = create_app()
    return TestClient(app)


def test_health_endpoint_returns_200(bff_client: TestClient) -> None:
    """Test that /health returns 200 OK."""
    response = bff_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_health_endpoint_returns_service_name(bff_client: TestClient) -> None:
    """Test that /health returns service information."""
    response = bff_client.get("/health")
    data = response.json()
    assert "service" in data
    assert data["service"] == "bff"


def test_ready_endpoint_returns_200(bff_client: TestClient) -> None:
    """Test that /ready returns 200 OK when all dependencies are available."""
    response = bff_client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"


def test_ready_endpoint_includes_dependencies(bff_client: TestClient) -> None:
    """Test that /ready includes dependency status."""
    response = bff_client.get("/ready")
    data = response.json()
    assert "dependencies" in data
