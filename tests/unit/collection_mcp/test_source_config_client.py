"""Tests for Collection MCP Source Config Client."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from collection_mcp.infrastructure.source_config_client import SourceConfigClient


class MockAsyncCursor:
    """Mock async cursor for MongoDB operations."""

    def __init__(self, documents: list[dict[str, Any]]) -> None:
        self._documents = documents

    def sort(self, field: str, direction: int) -> "MockAsyncCursor":
        """Mock sort."""
        return self

    async def to_list(self, length: int | None = None) -> list[dict[str, Any]]:
        """Convert to list."""
        limit = length or len(self._documents)
        return self._documents[:limit]


class TestListSources:
    """Tests for list_sources method."""

    @pytest.fixture
    def client(self) -> SourceConfigClient:
        """Create a source config client with mocked MongoDB."""
        with patch("collection_mcp.infrastructure.source_config_client.AsyncIOMotorClient"):
            client = SourceConfigClient(
                mongodb_uri="mongodb://localhost:27017",
                database_name="test_db",
            )
            return client

    @pytest.mark.asyncio
    async def test_list_sources_returns_all_enabled(self, client: SourceConfigClient) -> None:
        """Verify list_sources returns enabled sources by default."""
        mock_sources = [
            {
                "source_id": "qc-analyzer-result",
                "display_name": "QC Analyzer Results",
                "description": "Quality control results",
                "enabled": True,
                "ingestion": {"mode": "BLOB_TRIGGER", "schedule": None},
            },
            {
                "source_id": "weather-api",
                "display_name": "Weather Data",
                "description": "Weather information",
                "enabled": True,
                "ingestion": {"mode": "PULL", "schedule": "0 */6 * * *"},
            },
        ]
        mock_cursor = MockAsyncCursor(mock_sources)
        client._collection = MagicMock()
        client._collection.find = MagicMock(return_value=mock_cursor)

        result = await client.list_sources(enabled_only=True)

        assert len(result) == 2
        assert result[0]["source_id"] == "qc-analyzer-result"
        assert result[0]["display_name"] == "QC Analyzer Results"
        assert result[0]["ingestion_mode"] == "BLOB_TRIGGER"
        assert result[1]["source_id"] == "weather-api"
        assert result[1]["ingestion_schedule"] == "0 */6 * * *"

        # Verify query included enabled filter
        call_args = client._collection.find.call_args
        query = call_args[0][0]
        assert query["enabled"] is True

    @pytest.mark.asyncio
    async def test_list_sources_returns_all_when_not_enabled_only(self, client: SourceConfigClient) -> None:
        """Verify list_sources returns all sources when enabled_only=False."""
        mock_sources = [
            {
                "source_id": "disabled-source",
                "display_name": "Disabled Source",
                "enabled": False,
                "ingestion": {"mode": "PULL"},
            },
        ]
        mock_cursor = MockAsyncCursor(mock_sources)
        client._collection = MagicMock()
        client._collection.find = MagicMock(return_value=mock_cursor)

        result = await client.list_sources(enabled_only=False)

        assert len(result) == 1
        assert result[0]["enabled"] is False

        # Verify query did NOT include enabled filter
        call_args = client._collection.find.call_args
        query = call_args[0][0]
        assert "enabled" not in query

    @pytest.mark.asyncio
    async def test_list_sources_handles_missing_fields(self, client: SourceConfigClient) -> None:
        """Verify list_sources handles sources with missing optional fields."""
        mock_sources = [
            {
                "source_id": "minimal-source",
                # No display_name, description, or ingestion
            },
        ]
        mock_cursor = MockAsyncCursor(mock_sources)
        client._collection = MagicMock()
        client._collection.find = MagicMock(return_value=mock_cursor)

        result = await client.list_sources(enabled_only=False)

        assert len(result) == 1
        assert result[0]["source_id"] == "minimal-source"
        assert result[0]["display_name"] == "minimal-source"  # Falls back to source_id
        assert result[0]["description"] == ""
        assert result[0]["enabled"] is True  # Default
        assert result[0]["ingestion_mode"] == "unknown"
        assert result[0]["ingestion_schedule"] is None

    @pytest.mark.asyncio
    async def test_list_sources_empty_result(self, client: SourceConfigClient) -> None:
        """Verify list_sources returns empty list when no sources found."""
        mock_cursor = MockAsyncCursor([])
        client._collection = MagicMock()
        client._collection.find = MagicMock(return_value=mock_cursor)

        result = await client.list_sources()

        assert result == []


class TestGetSource:
    """Tests for get_source method."""

    @pytest.fixture
    def client(self) -> SourceConfigClient:
        """Create a source config client with mocked MongoDB."""
        with patch("collection_mcp.infrastructure.source_config_client.AsyncIOMotorClient"):
            client = SourceConfigClient(
                mongodb_uri="mongodb://localhost:27017",
                database_name="test_db",
            )
            return client

    @pytest.mark.asyncio
    async def test_get_source_returns_source(self, client: SourceConfigClient) -> None:
        """Verify get_source returns source configuration."""
        mock_source = {
            "_id": "objectid123",
            "source_id": "qc-analyzer-result",
            "display_name": "QC Analyzer Results",
            "description": "Quality control analysis results",
            "enabled": True,
            "ingestion": {
                "mode": "BLOB_TRIGGER",
                "container": "qc-data",
            },
        }
        client._collection = MagicMock()
        client._collection.find_one = AsyncMock(return_value=mock_source)

        result = await client.get_source("qc-analyzer-result")

        assert result is not None
        assert result["source_id"] == "qc-analyzer-result"
        assert result["_id"] == "objectid123"  # Converted to string
        client._collection.find_one.assert_called_once_with({"source_id": "qc-analyzer-result"})

    @pytest.mark.asyncio
    async def test_get_source_returns_none_when_not_found(self, client: SourceConfigClient) -> None:
        """Verify get_source returns None when source not found."""
        client._collection = MagicMock()
        client._collection.find_one = AsyncMock(return_value=None)

        result = await client.get_source("nonexistent-source")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_source_converts_objectid(self, client: SourceConfigClient) -> None:
        """Verify get_source converts ObjectId to string."""
        from bson import ObjectId

        mock_source = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "source_id": "test-source",
        }
        client._collection = MagicMock()
        client._collection.find_one = AsyncMock(return_value=mock_source)

        result = await client.get_source("test-source")

        assert result is not None
        assert isinstance(result["_id"], str)
        assert result["_id"] == "507f1f77bcf86cd799439011"
