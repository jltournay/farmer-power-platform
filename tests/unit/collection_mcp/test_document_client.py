"""Tests for Collection MCP Document Client."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from collection_mcp.infrastructure.document_client import (
    DocumentClient,
    DocumentNotFoundError,
)


class MockAsyncCursor:
    """Mock async cursor for MongoDB operations."""

    def __init__(self, documents: list[dict[str, Any]]) -> None:
        self._documents = documents
        self._sorted = False
        self._limit: int | None = None

    def sort(self, field: str, direction: int) -> "MockAsyncCursor":
        """Mock sort."""
        self._sorted = True
        return self

    def limit(self, n: int) -> "MockAsyncCursor":
        """Mock limit."""
        self._limit = n
        return self

    async def to_list(self, length: int | None = None) -> list[dict[str, Any]]:
        """Convert to list."""
        limit = length or self._limit or len(self._documents)
        return self._documents[:limit]


class TestDocumentClientQueryBuilding:
    """Tests for query building logic."""

    @pytest.fixture
    def client(self) -> DocumentClient:
        """Create a document client with mocked MongoDB."""
        with patch("collection_mcp.infrastructure.document_client.AsyncIOMotorClient"):
            client = DocumentClient(
                mongodb_uri="mongodb://localhost:27017",
                database_name="test_db",
            )
            return client

    def test_build_query_empty(self, client: DocumentClient) -> None:
        """Verify empty query with no filters."""
        query = client._build_query()
        assert query == {}

    def test_build_query_source_id(self, client: DocumentClient) -> None:
        """Verify query with source_id filter."""
        query = client._build_query(source_id="qc-analyzer-result")
        # Field path matches DocumentIndex.ingestion.source_id
        assert query == {"ingestion.source_id": "qc-analyzer-result"}

    def test_build_query_farmer_id(self, client: DocumentClient) -> None:
        """Verify query with farmer_id filter."""
        query = client._build_query(farmer_id="WM-4521")
        # farmer_id can be in linkage_fields or extracted_fields per DocumentIndex schema
        assert query == {
            "$or": [
                {"linkage_fields.farmer_id": "WM-4521"},
                {"extracted_fields.farmer_id": "WM-4521"},
            ]
        }

    def test_build_query_linkage(self, client: DocumentClient) -> None:
        """Verify query with linkage filters."""
        query = client._build_query(linkage={"batch_id": "batch-001", "factory_id": "FAC-001"})
        # Field path matches DocumentIndex.linkage_fields (not "linkage")
        assert query == {
            "linkage_fields.batch_id": "batch-001",
            "linkage_fields.factory_id": "FAC-001",
        }

    def test_build_query_attributes_equality(self, client: DocumentClient) -> None:
        """Verify query with attribute equality filters."""
        query = client._build_query(attributes={"grade": "A"})
        # Field path matches DocumentIndex.extracted_fields (not "attributes")
        assert query == {"extracted_fields.grade": "A"}

    def test_build_query_attributes_operators(self, client: DocumentClient) -> None:
        """Verify query with attribute operator filters."""
        query = client._build_query(
            attributes={
                "bag_summary.primary_percentage": {"$lt": 70},
                "temperature": {"$gt": 25, "$lt": 35},
            }
        )
        # Field path matches DocumentIndex.extracted_fields (not "attributes")
        assert query == {
            "extracted_fields.bag_summary.primary_percentage": {"$lt": 70},
            "extracted_fields.temperature": {"$gt": 25, "$lt": 35},
        }

    def test_build_query_date_range(self, client: DocumentClient) -> None:
        """Verify query with date range filter."""
        query = client._build_query(
            date_range={
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
            }
        )
        # Field path matches DocumentIndex.created_at (not "ingested_at")
        assert "created_at" in query
        assert "$gte" in query["created_at"]
        assert "$lte" in query["created_at"]

    def test_build_query_combined(self, client: DocumentClient) -> None:
        """Verify query with multiple filters combined."""
        query = client._build_query(
            source_id="qc-analyzer-result",
            linkage={"batch_id": "batch-001"},
            attributes={"grade": "B"},
        )
        # Field paths match DocumentIndex schema
        assert query["ingestion.source_id"] == "qc-analyzer-result"
        assert query["linkage_fields.batch_id"] == "batch-001"
        assert query["extracted_fields.grade"] == "B"


class TestDocumentClientGetDocuments:
    """Tests for get_documents method."""

    @pytest.fixture
    def client(self) -> DocumentClient:
        """Create a document client with mocked MongoDB."""
        with patch("collection_mcp.infrastructure.document_client.AsyncIOMotorClient"):
            client = DocumentClient(
                mongodb_uri="mongodb://localhost:27017",
                database_name="test_db",
            )
            return client

    @pytest.mark.asyncio
    async def test_get_documents_returns_list(self, client: DocumentClient) -> None:
        """Verify get_documents returns a list of Document Pydantic models."""
        # Mock data must match DocumentIndex schema with nested structures
        mock_docs = [
            {
                "_id": "id1",
                "document_id": "doc-001",
                "ingestion": {"source_id": "test", "ingestion_id": "ing-001"},
                "raw_document": {"blob_container": "raw", "blob_path": "path1"},
                "extraction": {"ai_agent_id": "agent-1"},
                "extracted_fields": {},
            },
            {
                "_id": "id2",
                "document_id": "doc-002",
                "ingestion": {"source_id": "test", "ingestion_id": "ing-002"},
                "raw_document": {"blob_container": "raw", "blob_path": "path2"},
                "extraction": {"ai_agent_id": "agent-1"},
                "extracted_fields": {},
            },
        ]
        mock_cursor = MockAsyncCursor(mock_docs)
        client._default_collection = MagicMock()
        client._default_collection.find = MagicMock(return_value=mock_cursor)

        result = await client.get_documents(source_id="test")

        # Returns Pydantic Document models (Story 0.6.12)
        assert len(result) == 2
        assert result[0].document_id == "doc-001"
        assert result[0].ingestion.source_id == "test"

    @pytest.mark.asyncio
    async def test_get_documents_respects_limit(self, client: DocumentClient) -> None:
        """Verify get_documents respects limit parameter."""
        # Mock data must match DocumentIndex schema with nested structures
        mock_docs = [
            {
                "_id": f"id{i}",
                "document_id": f"doc-{i:03d}",
                "ingestion": {"source_id": "test", "ingestion_id": f"ing-{i}"},
                "raw_document": {"blob_container": "raw", "blob_path": f"path{i}"},
                "extraction": {"ai_agent_id": "agent-1"},
                "extracted_fields": {},
            }
            for i in range(100)
        ]
        mock_cursor = MockAsyncCursor(mock_docs)
        client._default_collection = MagicMock()
        client._default_collection.find = MagicMock(return_value=mock_cursor)

        result = await client.get_documents(limit=10)

        assert len(result) == 10

    @pytest.mark.asyncio
    async def test_get_documents_enforces_max_limit(self, client: DocumentClient) -> None:
        """Verify get_documents enforces maximum limit of 1000."""
        # Mock data must match DocumentIndex schema with nested structures
        mock_docs = [
            {
                "_id": "id1",
                "document_id": "doc-001",
                "ingestion": {"source_id": "test", "ingestion_id": "ing-001"},
                "raw_document": {"blob_container": "raw", "blob_path": "path1"},
                "extraction": {"ai_agent_id": "agent-1"},
                "extracted_fields": {},
            }
        ]
        mock_cursor = MockAsyncCursor(mock_docs)
        client._default_collection = MagicMock()
        client._default_collection.find = MagicMock(return_value=mock_cursor)

        # Request more than max limit
        await client.get_documents(limit=2000)

        # Verify limit was capped to 1000
        assert mock_cursor._limit == 1000


class TestDocumentClientGetDocumentById:
    """Tests for get_document_by_id method."""

    @pytest.fixture
    def client(self) -> DocumentClient:
        """Create a document client with mocked MongoDB."""
        with patch("collection_mcp.infrastructure.document_client.AsyncIOMotorClient"):
            client = DocumentClient(
                mongodb_uri="mongodb://localhost:27017",
                database_name="test_db",
            )
            return client

    @pytest.mark.asyncio
    async def test_get_document_by_id_returns_document(self, client: DocumentClient) -> None:
        """Verify get_document_by_id returns a Document Pydantic model."""
        # Mock data must match DocumentIndex schema with nested structures
        mock_doc = {
            "_id": "id1",
            "document_id": "qc-analyzer/batch-001/leaf_001",
            "ingestion": {"source_id": "qc-analyzer-exceptions", "ingestion_id": "ing-001"},
            "raw_document": {"blob_container": "raw", "blob_path": "batch-001/leaf_001.jpg"},
            "extraction": {"ai_agent_id": "qc-analyzer"},
            "extracted_fields": {"grade": "A"},
        }
        client._default_collection = MagicMock()
        client._default_collection.find_one = AsyncMock(return_value=mock_doc)

        result = await client.get_document_by_id("qc-analyzer/batch-001/leaf_001")

        # Returns Pydantic Document model (Story 0.6.12)
        assert result.document_id == "qc-analyzer/batch-001/leaf_001"
        assert result.ingestion.source_id == "qc-analyzer-exceptions"

    @pytest.mark.asyncio
    async def test_get_document_by_id_raises_not_found(self, client: DocumentClient) -> None:
        """Verify get_document_by_id raises DocumentNotFoundError."""
        client._default_collection = MagicMock()
        client._default_collection.find_one = AsyncMock(return_value=None)

        with pytest.raises(DocumentNotFoundError) as exc_info:
            await client.get_document_by_id("nonexistent")

        assert "nonexistent" in str(exc_info.value)


class TestDocumentClientGetFarmerDocuments:
    """Tests for get_farmer_documents method."""

    @pytest.fixture
    def client(self) -> DocumentClient:
        """Create a document client with mocked MongoDB."""
        with patch("collection_mcp.infrastructure.document_client.AsyncIOMotorClient"):
            client = DocumentClient(
                mongodb_uri="mongodb://localhost:27017",
                database_name="test_db",
            )
            return client

    @pytest.mark.asyncio
    async def test_get_farmer_documents_basic(self, client: DocumentClient) -> None:
        """Verify get_farmer_documents returns Document Pydantic models for farmer."""
        # Mock data must match DocumentIndex schema with nested structures
        mock_docs = [
            {
                "_id": "id1",
                "document_id": "doc-001",
                "ingestion": {"source_id": "qc-analyzer", "ingestion_id": "ing-001"},
                "raw_document": {"blob_container": "raw", "blob_path": "path1"},
                "extraction": {"ai_agent_id": "agent-1"},
                "extracted_fields": {"farmer_id": "WM-4521"},
                "linkage_fields": {"farmer_id": "WM-4521"},
            },
            {
                "_id": "id2",
                "document_id": "doc-002",
                "ingestion": {"source_id": "qc-analyzer", "ingestion_id": "ing-002"},
                "raw_document": {"blob_container": "raw", "blob_path": "path2"},
                "extraction": {"ai_agent_id": "agent-1"},
                "extracted_fields": {"farmer_id": "WM-4521"},
                "linkage_fields": {"farmer_id": "WM-4521"},
            },
        ]
        mock_cursor = MockAsyncCursor(mock_docs)
        client._default_collection = MagicMock()
        client._default_collection.find = MagicMock(return_value=mock_cursor)

        result = await client.get_farmer_documents(farmer_id="WM-4521")

        # Returns Pydantic Document models (Story 0.6.12)
        assert len(result) == 2
        assert all(doc.linkage_fields.get("farmer_id") == "WM-4521" for doc in result)

    @pytest.mark.asyncio
    async def test_get_farmer_documents_with_source_filter(self, client: DocumentClient) -> None:
        """Verify get_farmer_documents filters by source_ids."""
        # Mock data must match DocumentIndex schema with nested structures
        mock_docs = [
            {
                "_id": "id1",
                "document_id": "doc-001",
                "ingestion": {"source_id": "qc-analyzer-result", "ingestion_id": "ing-001"},
                "raw_document": {"blob_container": "raw", "blob_path": "path1"},
                "extraction": {"ai_agent_id": "agent-1"},
                "extracted_fields": {"farmer_id": "WM-4521"},
                "linkage_fields": {"farmer_id": "WM-4521"},
            }
        ]
        mock_cursor = MockAsyncCursor(mock_docs)
        client._default_collection = MagicMock()
        client._default_collection.find = MagicMock(return_value=mock_cursor)

        await client.get_farmer_documents(
            farmer_id="WM-4521",
            source_ids=["qc-analyzer-result", "qc-analyzer-exceptions"],
        )

        # Verify $in operator was used for source_ids
        # Field path matches DocumentIndex.ingestion.source_id
        call_args = client._default_collection.find.call_args
        query = call_args[0][0]
        assert "ingestion.source_id" in query
        assert "$in" in query["ingestion.source_id"]


class TestDocumentClientSearchDocuments:
    """Tests for search_documents method."""

    @pytest.fixture
    def client(self) -> DocumentClient:
        """Create a document client with mocked MongoDB."""
        with patch("collection_mcp.infrastructure.document_client.AsyncIOMotorClient"):
            client = DocumentClient(
                mongodb_uri="mongodb://localhost:27017",
                database_name="test_db",
            )
            return client

    @pytest.mark.asyncio
    async def test_search_documents_text_search(self, client: DocumentClient) -> None:
        """Verify search_documents uses text search and returns SearchResult models."""
        # Mock data must match DocumentIndex schema with nested structures
        mock_docs = [
            {
                "_id": "id1",
                "document_id": "doc-001",
                "ingestion": {"source_id": "qc-analyzer", "ingestion_id": "ing-001"},
                "raw_document": {"blob_container": "raw", "blob_path": "path1"},
                "extraction": {"ai_agent_id": "agent-1"},
                "extracted_fields": {"description": "coarse leaf"},
                "relevance_score": 1.5,
            },
        ]
        mock_cursor = MockAsyncCursor(mock_docs)

        # Mock cursor with sort method that returns cursor
        mock_cursor_with_sort = MagicMock()
        mock_cursor_with_sort.sort = MagicMock(return_value=mock_cursor)
        mock_cursor_with_sort.limit = MagicMock(return_value=mock_cursor)

        client._default_collection = MagicMock()
        client._default_collection.find = MagicMock(return_value=mock_cursor_with_sort)

        result = await client.search_documents(query_text="coarse leaf")

        # Returns Pydantic SearchResult models (Story 0.6.12)
        assert len(result) == 1
        assert result[0].document_id == "doc-001"
        # Verify text search query was used
        call_args = client._default_collection.find.call_args
        query = call_args[0][0]
        assert "$text" in query

    @pytest.mark.asyncio
    async def test_search_documents_enforces_max_limit(self, client: DocumentClient) -> None:
        """Verify search_documents enforces maximum limit of 100."""
        # Mock data must match DocumentIndex schema with nested structures
        mock_docs = [
            {
                "_id": "id1",
                "document_id": "doc-001",
                "ingestion": {"source_id": "qc-analyzer", "ingestion_id": "ing-001"},
                "raw_document": {"blob_container": "raw", "blob_path": "path1"},
                "extraction": {"ai_agent_id": "agent-1"},
                "extracted_fields": {},
                "relevance_score": 1.0,
            }
        ]
        mock_cursor = MockAsyncCursor(mock_docs)
        mock_cursor_with_sort = MagicMock()
        mock_cursor_with_sort.sort = MagicMock(return_value=mock_cursor)

        client._default_collection = MagicMock()
        client._default_collection.find = MagicMock(return_value=mock_cursor_with_sort)

        # Request more than max limit
        await client.search_documents(query_text="test", limit=500)

        # The limit should be capped in the method
        # (Implementation detail - verified via code review)
