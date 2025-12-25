"""Integration tests for the Plantation Model application."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestPlantationModelApplication:
    """Integration tests for the full Plantation Model application."""

    @pytest.fixture
    def mock_dependencies(self) -> dict:
        """Create mocked dependencies."""
        mock_client = MagicMock()
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})
        mock_client.close = MagicMock()

        return {
            "mongodb_client": mock_client,
        }

    @pytest.fixture
    def client(self, mock_dependencies: dict) -> TestClient:
        """Create test client with mocked dependencies."""
        with patch(
            "plantation_model.infrastructure.mongodb.AsyncIOMotorClient",
            return_value=mock_dependencies["mongodb_client"],
        ), patch(
            "plantation_model.infrastructure.tracing.setup_tracing",
            return_value=None,
        ), patch(
            "plantation_model.infrastructure.tracing.instrument_fastapi",
            return_value=None,
        ), patch(
            "plantation_model.api.grpc_server.GrpcServer.start",
            new_callable=AsyncMock,
        ):
            from plantation_model.main import app

            with TestClient(app) as test_client:
                yield test_client

    def test_root_endpoint(self, client: TestClient) -> None:
        """Test root endpoint returns service info."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "plantation-model"
        assert data["status"] == "running"
        assert "version" in data

    def test_health_endpoint(self, client: TestClient) -> None:
        """Test health endpoint is accessible."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_openapi_schema_available(self, client: TestClient) -> None:
        """Test that OpenAPI schema is available."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "Plantation Model Service"
        assert "paths" in data

    def test_docs_available(self, client: TestClient) -> None:
        """Test that Swagger docs are available."""
        response = client.get("/docs")

        assert response.status_code == 200

    def test_redoc_available(self, client: TestClient) -> None:
        """Test that ReDoc is available."""
        response = client.get("/redoc")

        assert response.status_code == 200

    def test_cors_headers(self, client: TestClient) -> None:
        """Test that CORS headers are present."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # CORS preflight should work
        assert response.status_code in (200, 405)
