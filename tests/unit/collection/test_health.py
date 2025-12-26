"""Tests for Collection Model health endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    """Create test client with mocked dependencies."""
    # Mock MongoDB before importing app
    with (
        patch("collection_model.infrastructure.mongodb.get_mongodb_client") as mock_mongo,
        patch("collection_model.infrastructure.mongodb.check_mongodb_connection") as mock_check,
        patch("collection_model.infrastructure.tracing.setup_tracing"),
        patch("collection_model.infrastructure.tracing.shutdown_tracing"),
        patch("collection_model.infrastructure.tracing.instrument_fastapi"),
    ):
        mock_mongo.return_value = AsyncMock()
        mock_check.return_value = True

        from collection_model.main import app

        with TestClient(app) as test_client:
            yield test_client


def test_health_endpoint_returns_200(client: TestClient) -> None:
    """Test /health endpoint returns 200 when service is running."""
    response = client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "healthy"}


def test_root_endpoint_returns_service_info(client: TestClient) -> None:
    """Test root endpoint returns service information."""
    response = client.get("/")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["service"] == "collection-model"
    assert data["status"] == "running"
    assert "version" in data
