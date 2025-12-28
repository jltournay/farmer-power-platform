"""Unit tests for CollectionClient.

Story 1.7: Quality Grading Event Subscription
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from plantation_model.infrastructure.collection_client import (
    CollectionClient,
    CollectionClientError,
    DocumentNotFoundError,
)


@pytest.fixture
def mock_motor_client():
    """Create a mock Motor client."""
    mock = MagicMock()
    return mock


@pytest.fixture
def collection_client() -> CollectionClient:
    """Create a CollectionClient with test config."""
    return CollectionClient(
        mongodb_uri="mongodb://localhost:27017",
        database_name="collection_test",
    )


class TestCollectionClient:
    """Tests for CollectionClient."""

    @pytest.mark.asyncio
    async def test_get_document_success(
        self,
        collection_client: CollectionClient,
    ) -> None:
        """Test successful document retrieval."""
        # Arrange
        mock_doc = {
            "_id": "test-id",
            "document_id": "doc-123",
            "source_id": "qc-analyzer-result",
            "farmer_id": "WM-0001",
            "attributes": {"grading_model_id": "tbk_kenya_tea_v1"},
        }

        mock_collection = AsyncMock()
        mock_collection.find_one = AsyncMock(return_value=mock_doc)

        # Patch the _get_collection method
        collection_client._get_collection = AsyncMock(return_value=mock_collection)

        # Act
        result = await collection_client.get_document("doc-123")

        # Assert
        assert result["document_id"] == "doc-123"
        assert result["source_id"] == "qc-analyzer-result"
        assert result["_id"] == "test-id"  # ObjectId converted to string
        mock_collection.find_one.assert_called_once_with({"document_id": "doc-123"})

    @pytest.mark.asyncio
    async def test_get_document_not_found(
        self,
        collection_client: CollectionClient,
    ) -> None:
        """Test DocumentNotFoundError when document doesn't exist."""
        # Arrange
        mock_collection = AsyncMock()
        mock_collection.find_one = AsyncMock(return_value=None)
        collection_client._get_collection = AsyncMock(return_value=mock_collection)

        # Act & Assert
        with pytest.raises(DocumentNotFoundError) as exc_info:
            await collection_client.get_document("nonexistent-doc")

        assert exc_info.value.document_id == "nonexistent-doc"
        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_document_database_error(
        self,
        collection_client: CollectionClient,
    ) -> None:
        """Test CollectionClientError on database errors."""
        # Arrange
        mock_collection = AsyncMock()
        mock_collection.find_one = AsyncMock(side_effect=Exception("Connection failed"))
        collection_client._get_collection = AsyncMock(return_value=mock_collection)

        # Act & Assert
        with pytest.raises(CollectionClientError) as exc_info:
            await collection_client.get_document("doc-123")

        assert "Failed to fetch document" in str(exc_info.value)
        assert exc_info.value.cause is not None

    @pytest.mark.asyncio
    async def test_close_connection(
        self,
        collection_client: CollectionClient,
    ) -> None:
        """Test closing the MongoDB connection."""
        # Arrange - initialize a mock client
        mock_client = MagicMock()
        collection_client._client = mock_client

        # Act
        await collection_client.close()

        # Assert
        mock_client.close.assert_called_once()
        assert collection_client._client is None
        assert collection_client._db is None


class TestDocumentNotFoundError:
    """Tests for DocumentNotFoundError exception."""

    def test_error_message(self) -> None:
        """Test error message format."""
        error = DocumentNotFoundError("doc-456")

        assert error.document_id == "doc-456"
        assert "doc-456" in str(error)
        assert "not found" in str(error).lower()


class TestCollectionClientError:
    """Tests for CollectionClientError exception."""

    def test_error_with_cause(self) -> None:
        """Test error with cause exception."""
        cause = ValueError("Original error")
        error = CollectionClientError("Failed operation", cause=cause)

        assert error.cause == cause
        assert "Failed operation" in str(error)

    def test_error_without_cause(self) -> None:
        """Test error without cause."""
        error = CollectionClientError("Failed operation")

        assert error.cause is None
        assert "Failed operation" in str(error)
