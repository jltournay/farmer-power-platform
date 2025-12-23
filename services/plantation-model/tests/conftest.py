"""Pytest fixtures for Plantation Model service tests."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from plantation_model.config import Settings


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings with safe defaults."""
    return Settings(
        service_name="plantation-model-test",
        environment="test",
        mongodb_uri="mongodb://localhost:27017",
        mongodb_database="plantation_test",
        otel_enabled=False,  # Disable tracing in tests
    )


@pytest.fixture
def mock_mongodb_client() -> MagicMock:
    """Create a mock MongoDB client."""
    mock_client = MagicMock()
    mock_client.admin.command = AsyncMock(return_value={"ok": 1})
    mock_client.close = MagicMock()
    return mock_client


@pytest.fixture
def mock_mongodb_database(mock_mongodb_client: MagicMock) -> MagicMock:
    """Create a mock MongoDB database."""
    mock_db = MagicMock()
    mock_mongodb_client.__getitem__.return_value = mock_db
    return mock_db


@pytest.fixture
def app_with_mocks(
    test_settings: Settings,
    mock_mongodb_client: MagicMock,
) -> Generator:
    """Create FastAPI app with mocked dependencies."""
    with patch("plantation_model.config.settings", test_settings):
        with patch(
            "plantation_model.infrastructure.mongodb._client",
            mock_mongodb_client,
        ):
            with patch(
                "plantation_model.infrastructure.tracing.setup_tracing",
                return_value=None,
            ):
                with patch(
                    "plantation_model.api.grpc_server.start_grpc_server",
                    new_callable=AsyncMock,
                ):
                    from plantation_model.main import app

                    yield app


@pytest.fixture
def sync_client(app_with_mocks) -> Generator[TestClient, None, None]:
    """Create synchronous test client."""
    with TestClient(app_with_mocks) as client:
        yield client


@pytest.fixture
async def async_client(app_with_mocks) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    transport = ASGITransport(app=app_with_mocks)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
