"""Unit tests for platform-cost health endpoints.

Story 13.2: Platform Cost Service scaffold.
"""

import warnings
from unittest import mock

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test cases for health endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        # Import inside fixture to avoid side effects
        from platform_cost.main import app

        # Suppress httpx deprecation warning about 'app' shortcut
        # This is a known issue with Starlette TestClient
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*app.*shortcut.*")
            return TestClient(app)

    def test_health_endpoint_returns_healthy(self, client: TestClient):
        """Test /health endpoint returns healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_root_endpoint_returns_service_info(self, client: TestClient):
        """Test root endpoint returns service information."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "platform-cost"
        assert data["version"] == "0.1.0"
        assert data["status"] == "running"

    def test_ready_endpoint_without_mongodb_check(self, client: TestClient):
        """Test /ready endpoint when MongoDB check is not configured."""
        # Reset MongoDB check function
        from platform_cost.api import health

        health._mongodb_check_fn = None

        response = client.get("/ready")

        # Should return 503 when MongoDB is not configured - service not ready
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["mongodb"] == "not_configured"

    @pytest.mark.asyncio
    async def test_ready_endpoint_with_mongodb_connected(self, client: TestClient):
        """Test /ready endpoint when MongoDB is connected."""
        from platform_cost.api import health

        # Mock MongoDB check to return True
        async def mock_check():
            return True

        health.set_mongodb_check(mock_check)

        response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["checks"]["mongodb"] == "connected"

    @pytest.mark.asyncio
    async def test_ready_endpoint_with_mongodb_disconnected(self, client: TestClient):
        """Test /ready endpoint when MongoDB is disconnected."""
        from platform_cost.api import health

        # Mock MongoDB check to return False
        async def mock_check():
            return False

        health.set_mongodb_check(mock_check)

        response = client.get("/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["mongodb"] == "disconnected"

    @pytest.mark.asyncio
    async def test_ready_endpoint_with_mongodb_error(self, client: TestClient):
        """Test /ready endpoint when MongoDB check throws error."""
        from platform_cost.api import health

        # Mock MongoDB check to raise exception
        async def mock_check():
            raise ConnectionError("MongoDB unavailable")

        health.set_mongodb_check(mock_check)

        response = client.get("/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["mongodb"] == "error"


class TestDaprHealthCheck:
    """Test cases for DAPR sidecar health check."""

    @pytest.mark.asyncio
    async def test_check_dapr_sidecar_healthy(self):
        """Test DAPR health check returns True when sidecar is healthy."""
        from platform_cost.api.health import check_dapr_sidecar

        with mock.patch("platform_cost.api.health.httpx.AsyncClient") as mock_client:
            mock_response = mock.MagicMock()
            mock_response.status_code = 204
            mock_client.return_value.__aenter__.return_value.get = mock.AsyncMock(return_value=mock_response)

            result = await check_dapr_sidecar()
            assert result is True

    @pytest.mark.asyncio
    async def test_check_dapr_sidecar_unhealthy(self):
        """Test DAPR health check returns False when sidecar is unavailable."""
        from platform_cost.api.health import check_dapr_sidecar

        with mock.patch("platform_cost.api.health.httpx.AsyncClient") as mock_client:
            import httpx

            mock_client.return_value.__aenter__.return_value.get = mock.AsyncMock(
                side_effect=httpx.RequestError("Connection refused")
            )

            result = await check_dapr_sidecar()
            assert result is False

    @pytest.mark.asyncio
    async def test_check_dapr_sidecar_unexpected_error(self):
        """Test DAPR health check handles unexpected errors."""
        from platform_cost.api.health import check_dapr_sidecar

        with mock.patch("platform_cost.api.health.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = mock.AsyncMock(side_effect=Exception("Unexpected"))

            result = await check_dapr_sidecar()
            assert result is False
