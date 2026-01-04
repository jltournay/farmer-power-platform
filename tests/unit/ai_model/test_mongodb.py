"""Unit tests for AI Model MongoDB infrastructure."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pymongo.errors import ConnectionFailure


class TestMongoDBClient:
    """Tests for MongoDB client functions."""

    @pytest.mark.asyncio
    async def test_get_mongodb_client_creates_singleton(self) -> None:
        """get_mongodb_client should return same instance on multiple calls."""
        from ai_model.infrastructure import mongodb

        # Reset global state
        mongodb._client = None
        mongodb._database = None

        mock_client = MagicMock()
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})

        with patch(
            "ai_model.infrastructure.mongodb.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            client1 = await mongodb.get_mongodb_client()
            client2 = await mongodb.get_mongodb_client()

            assert client1 is client2
            assert client1 is mock_client

        # Cleanup
        mongodb._client = None
        mongodb._database = None

    @pytest.mark.asyncio
    async def test_get_database_returns_database(self) -> None:
        """get_database should return the configured database."""
        from ai_model.infrastructure import mongodb

        # Reset global state
        mongodb._client = None
        mongodb._database = None

        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})
        mock_client.__getitem__ = MagicMock(return_value=mock_db)

        with patch(
            "ai_model.infrastructure.mongodb.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            db = await mongodb.get_database()

            assert db is mock_db
            mock_client.__getitem__.assert_called_with("ai_model")

        # Cleanup
        mongodb._client = None
        mongodb._database = None

    @pytest.mark.asyncio
    async def test_check_mongodb_connection_returns_true_when_healthy(self) -> None:
        """check_mongodb_connection should return True when ping succeeds."""
        from ai_model.infrastructure import mongodb

        # Reset global state
        mongodb._client = None
        mongodb._database = None

        mock_client = MagicMock()
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})

        with patch(
            "ai_model.infrastructure.mongodb.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            result = await mongodb.check_mongodb_connection()

            assert result is True

        # Cleanup
        mongodb._client = None
        mongodb._database = None

    @pytest.mark.asyncio
    async def test_check_mongodb_connection_raises_on_failure(self) -> None:
        """check_mongodb_connection should raise on connection failure."""
        from ai_model.infrastructure import mongodb

        # Reset global state
        mongodb._client = None
        mongodb._database = None

        mock_client = MagicMock()
        mock_client.admin.command = AsyncMock(side_effect=ConnectionFailure("Connection refused"))

        with (
            patch(
                "ai_model.infrastructure.mongodb.AsyncIOMotorClient",
                return_value=mock_client,
            ),
            pytest.raises(ConnectionFailure),
        ):
            await mongodb.check_mongodb_connection()

        # Cleanup
        mongodb._client = None
        mongodb._database = None

    @pytest.mark.asyncio
    async def test_close_mongodb_connection_closes_client(self) -> None:
        """close_mongodb_connection should close and reset client."""
        from ai_model.infrastructure import mongodb

        mock_client = MagicMock()
        mongodb._client = mock_client
        mongodb._database = MagicMock()

        await mongodb.close_mongodb_connection()

        mock_client.close.assert_called_once()
        assert mongodb._client is None
        assert mongodb._database is None

    @pytest.mark.asyncio
    async def test_close_mongodb_connection_does_nothing_when_none(self) -> None:
        """close_mongodb_connection should handle case when no client."""
        from ai_model.infrastructure import mongodb

        mongodb._client = None
        mongodb._database = None

        # Should not raise any exception
        await mongodb.close_mongodb_connection()
