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


def test_ready_endpoint_returns_503_when_mongodb_fails() -> None:
    """Test /ready endpoint returns 503 when MongoDB connection fails."""
    # Mock MongoDB to fail - must patch in main.py where it's imported
    with (
        patch("collection_model.infrastructure.mongodb.get_mongodb_client") as mock_mongo,
        patch("collection_model.main.check_mongodb_connection") as mock_check,
        patch("collection_model.infrastructure.tracing.setup_tracing"),
        patch("collection_model.infrastructure.tracing.shutdown_tracing"),
        patch("collection_model.infrastructure.tracing.instrument_fastapi"),
    ):
        mock_mongo.return_value = AsyncMock()

        # Create an async function that raises an exception
        async def failing_check() -> bool:
            raise Exception("Connection refused")

        mock_check.side_effect = failing_check

        from collection_model.main import app

        with TestClient(app) as test_client:
            response = test_client.get("/ready")

            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert data["status"] == "not_ready"
            assert data["checks"]["mongodb"] == "error"


def test_ready_endpoint_returns_200_when_healthy() -> None:
    """Test /ready endpoint returns 200 when all checks pass."""
    with (
        patch("collection_model.infrastructure.mongodb.get_mongodb_client") as mock_mongo,
        patch("collection_model.infrastructure.mongodb.check_mongodb_connection") as mock_check,
        patch("collection_model.infrastructure.pubsub.check_pubsub_health") as mock_pubsub,
        patch("collection_model.infrastructure.tracing.setup_tracing"),
        patch("collection_model.infrastructure.tracing.shutdown_tracing"),
        patch("collection_model.infrastructure.tracing.instrument_fastapi"),
    ):
        mock_mongo.return_value = AsyncMock()
        mock_check.return_value = True
        mock_pubsub.return_value = True

        from collection_model.main import app

        with TestClient(app) as test_client:
            response = test_client.get("/ready")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "ready"
            assert data["checks"]["mongodb"] == "connected"
