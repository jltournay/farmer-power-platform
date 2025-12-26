"""Tests for Collection Model MongoDB connection."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pymongo.errors import ConnectionFailure


@pytest.fixture
def mock_motor_client() -> MagicMock:
    """Create mock Motor client."""
    client = MagicMock()
    client.admin.command = AsyncMock(return_value={"ok": 1})
    client.__getitem__ = MagicMock(return_value=MagicMock())
    client.close = MagicMock()
    return client


@pytest.mark.asyncio
async def test_get_mongodb_client_creates_connection(mock_motor_client: MagicMock) -> None:
    """Test MongoDB client is created and connection verified."""
    with patch("collection_model.infrastructure.mongodb.AsyncIOMotorClient", return_value=mock_motor_client):
        # Reset module state
        import collection_model.infrastructure.mongodb as mongodb_module

        mongodb_module._client = None
        mongodb_module._database = None

        client = await mongodb_module.get_mongodb_client()

        assert client is mock_motor_client
        mock_motor_client.admin.command.assert_called_once_with("ping")


@pytest.mark.asyncio
async def test_get_database_returns_database() -> None:
    """Test get_database returns the configured database."""
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_client.__getitem__ = MagicMock(return_value=mock_db)

    with patch("collection_model.infrastructure.mongodb.get_mongodb_client", return_value=mock_client):
        import collection_model.infrastructure.mongodb as mongodb_module

        mongodb_module._database = None

        db = await mongodb_module.get_database()

        assert db is mock_db


@pytest.mark.asyncio
async def test_check_mongodb_connection_returns_true_when_healthy() -> None:
    """Test connection check returns True when MongoDB responds."""
    mock_client = MagicMock()
    mock_client.admin.command = AsyncMock(return_value={"ok": 1})

    with patch("collection_model.infrastructure.mongodb.get_mongodb_client", return_value=mock_client):
        from collection_model.infrastructure.mongodb import check_mongodb_connection

        result = await check_mongodb_connection()

        assert result is True


@pytest.mark.asyncio
async def test_close_mongodb_connection() -> None:
    """Test MongoDB connection is properly closed."""
    mock_client = MagicMock()

    import collection_model.infrastructure.mongodb as mongodb_module

    mongodb_module._client = mock_client
    mongodb_module._database = MagicMock()

    await mongodb_module.close_mongodb_connection()

    mock_client.close.assert_called_once()
    assert mongodb_module._client is None
    assert mongodb_module._database is None
