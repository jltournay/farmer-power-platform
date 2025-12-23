"""Unit tests for Plantation Model MongoDB infrastructure."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# Import will be updated once plantation-model is installable
import sys
sys.path.insert(0, str(__file__).replace("tests/unit/plantation/test_mongodb.py", "services/plantation-model/src"))

from plantation_model.infrastructure.mongodb import (
    check_mongodb_connection,
    close_mongodb_connection,
    get_database,
    get_mongodb_client,
)


@pytest.mark.unit
class TestGetMongoDBClient:
    """Tests for get_mongodb_client function."""

    @pytest.fixture(autouse=True)
    def reset_globals(self) -> None:
        """Reset global state before each test."""
        import plantation_model.infrastructure.mongodb as mongodb_module

        mongodb_module._client = None
        mongodb_module._database = None

    @pytest.mark.asyncio
    async def test_creates_client_on_first_call(self) -> None:
        """Test that client is created on first call."""
        mock_client = MagicMock()
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})

        with patch(
            "plantation_model.infrastructure.mongodb.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            client = await get_mongodb_client()

            assert client is mock_client
            mock_client.admin.command.assert_called_once_with("ping")

    @pytest.mark.asyncio
    async def test_returns_existing_client_on_subsequent_calls(self) -> None:
        """Test that same client is returned on subsequent calls."""
        mock_client = MagicMock()
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})

        with patch(
            "plantation_model.infrastructure.mongodb.AsyncIOMotorClient",
            return_value=mock_client,
        ) as mock_constructor:
            client1 = await get_mongodb_client()
            client2 = await get_mongodb_client()

            assert client1 is client2
            # Constructor should only be called once
            assert mock_constructor.call_count == 1


@pytest.mark.unit
class TestGetDatabase:
    """Tests for get_database function."""

    @pytest.fixture(autouse=True)
    def reset_globals(self) -> None:
        """Reset global state before each test."""
        import plantation_model.infrastructure.mongodb as mongodb_module

        mongodb_module._client = None
        mongodb_module._database = None

    @pytest.mark.asyncio
    async def test_returns_database(self) -> None:
        """Test that database is returned."""
        mock_client = MagicMock()
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db

        with patch(
            "plantation_model.infrastructure.mongodb.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            db = await get_database()

            assert db is mock_db


@pytest.mark.unit
class TestCheckMongoDBConnection:
    """Tests for check_mongodb_connection function."""

    @pytest.fixture(autouse=True)
    def reset_globals(self) -> None:
        """Reset global state before each test."""
        import plantation_model.infrastructure.mongodb as mongodb_module

        mongodb_module._client = None
        mongodb_module._database = None

    @pytest.mark.asyncio
    async def test_returns_true_when_healthy(self) -> None:
        """Test that True is returned when connection is healthy."""
        mock_client = MagicMock()
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})

        with patch(
            "plantation_model.infrastructure.mongodb.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            result = await check_mongodb_connection()

            assert result is True

    @pytest.mark.asyncio
    async def test_raises_on_connection_failure(self) -> None:
        """Test that ConnectionFailure is raised on connection failure."""
        mock_client = MagicMock()
        mock_client.admin.command = AsyncMock(
            side_effect=ConnectionFailure("Connection refused")
        )

        with patch(
            "plantation_model.infrastructure.mongodb.AsyncIOMotorClient",
            return_value=mock_client,
        ):
            with pytest.raises(ConnectionFailure):
                await check_mongodb_connection()


@pytest.mark.unit
class TestCloseMongoDBConnection:
    """Tests for close_mongodb_connection function."""

    @pytest.mark.asyncio
    async def test_closes_existing_connection(self) -> None:
        """Test that existing connection is closed."""
        import plantation_model.infrastructure.mongodb as mongodb_module

        mock_client = MagicMock()
        mongodb_module._client = mock_client
        mongodb_module._database = MagicMock()

        await close_mongodb_connection()

        mock_client.close.assert_called_once()
        assert mongodb_module._client is None
        assert mongodb_module._database is None

    @pytest.mark.asyncio
    async def test_handles_no_existing_connection(self) -> None:
        """Test that no error when no connection exists."""
        import plantation_model.infrastructure.mongodb as mongodb_module

        mongodb_module._client = None
        mongodb_module._database = None

        # Should not raise
        await close_mongodb_connection()

        assert mongodb_module._client is None
        assert mongodb_module._database is None
