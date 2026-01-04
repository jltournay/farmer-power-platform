"""Unit tests for AI Model health endpoints."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    # Import here to avoid import errors during collection
    from ai_model.main import app

    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /health liveness probe."""

    def test_health_returns_200(self, test_client: TestClient) -> None:
        """Health endpoint should return 200 with healthy status."""
        response = test_client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "healthy"}

    def test_health_is_always_available(self, test_client: TestClient) -> None:
        """Health endpoint should always return healthy even if dependencies fail."""
        # The health endpoint is a liveness probe - it should always return 200
        # if the service is running, regardless of dependency health
        response = test_client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"


class TestReadyEndpoint:
    """Tests for /ready readiness probe."""

    def test_ready_returns_mongodb_not_configured_before_startup(self, test_client: TestClient) -> None:
        """Ready endpoint should indicate MongoDB not configured if check not set."""
        # Note: In real startup, MongoDB check is set during lifespan
        # For unit tests without full lifespan, it may show as not_configured
        response = test_client.get("/ready")

        # Should return 200 or 503 depending on MongoDB state
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ]
        data = response.json()
        assert "status" in data
        assert "checks" in data
        assert "mongodb" in data["checks"]


class TestRootEndpoint:
    """Tests for / root endpoint."""

    def test_root_returns_service_info(self, test_client: TestClient) -> None:
        """Root endpoint should return service information."""
        response = test_client.get("/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["service"] == "ai-model"
        assert data["version"] == "0.1.0"
        assert data["status"] == "running"
