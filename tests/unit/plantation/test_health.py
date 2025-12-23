"""Unit tests for Plantation Model health endpoints."""

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import will be updated once plantation-model is installable
import sys
sys.path.insert(0, str(__file__).replace("tests/unit/plantation/test_health.py", "services/plantation-model/src"))

from plantation_model.api.health import router, set_mongodb_check


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with health router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.mark.unit
class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_ok(self, client: TestClient) -> None:
        """Test that health endpoint returns healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["service"] == "plantation-model"

    def test_health_includes_version(self, client: TestClient) -> None:
        """Test that health endpoint includes version."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data


@pytest.mark.unit
class TestReadyEndpoint:
    """Tests for /ready endpoint."""

    def test_ready_without_mongodb_check_returns_not_ready(
        self, client: TestClient
    ) -> None:
        """Test that ready returns not ready when MongoDB check not set."""
        # Reset the check function
        set_mongodb_check(None)

        response = client.get("/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["mongodb"] is False

    def test_ready_with_healthy_mongodb(self, client: TestClient) -> None:
        """Test that ready returns ready when MongoDB is healthy."""
        mock_check = AsyncMock(return_value=True)
        set_mongodb_check(mock_check)

        response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["checks"]["mongodb"] is True

    def test_ready_with_unhealthy_mongodb(self, client: TestClient) -> None:
        """Test that ready returns not ready when MongoDB is unhealthy."""
        mock_check = AsyncMock(return_value=False)
        set_mongodb_check(mock_check)

        response = client.get("/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["mongodb"] is False

    def test_ready_with_mongodb_exception(self, client: TestClient) -> None:
        """Test that ready handles MongoDB check exceptions."""
        mock_check = AsyncMock(side_effect=Exception("Connection failed"))
        set_mongodb_check(mock_check)

        response = client.get("/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["mongodb"] is False
