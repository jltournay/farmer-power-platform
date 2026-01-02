"""Unit tests for Collection Model gRPC Service.

Story 0.5.1a: Tests for CollectionServiceServicer gRPC handlers.
Tests all 4 document query methods: GetDocument, ListDocuments,
GetDocumentsByFarmer, SearchDocuments.
"""

import copy
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from collection_model.api.grpc_service import CollectionServiceServicer
from fp_proto.collection.v1 import collection_pb2

# ═══════════════════════════════════════════════════════════════════════════════
# MOCK ENHANCEMENTS FOR NESTED FIELD QUERIES
# ═══════════════════════════════════════════════════════════════════════════════


def _get_nested_value(doc: dict[str, Any], key: str) -> Any:
    """Get nested value from document using dot notation.

    Args:
        doc: Document dictionary.
        key: Key with dot notation (e.g., 'linkage_fields.farmer_id').

    Returns:
        Value at the nested path, or None if not found.
    """
    parts = key.split(".")
    current = doc
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _matches_filter(doc: dict[str, Any], filter: dict[str, Any]) -> bool:
    """Check if document matches all filter criteria.

    Supports dot notation for nested fields and comparison operators.

    Args:
        doc: Document to check.
        filter: MongoDB-style filter.

    Returns:
        True if document matches all filter criteria.
    """
    for key, expected in filter.items():
        # Handle operators
        if isinstance(expected, dict):
            actual = _get_nested_value(doc, key)
            for op, val in expected.items():
                if op == "$gte" and (actual is None or actual < val):
                    return False
                if op == "$lte" and (actual is None or actual > val):
                    return False
                if op == "$gt" and (actual is None or actual <= val):
                    return False
                if op == "$lt" and (actual is None or actual >= val):
                    return False
        else:
            actual = _get_nested_value(doc, key)
            if actual != expected:
                return False
    return True


class MockMongoCursorWithNestedFields:
    """Mock MongoDB cursor that supports nested field filtering."""

    def __init__(self, documents: list[dict[str, Any]]) -> None:
        self._documents = documents
        self._skip = 0
        self._limit_val: int | None = None
        self._sort_key: str | None = None
        self._sort_direction: int = 1

    def __aiter__(self) -> "MockMongoCursorWithNestedFields":
        return self

    async def __anext__(self) -> dict[str, Any]:
        docs = self._get_sorted_docs()
        docs = docs[self._skip :]
        if self._limit_val:
            docs = docs[: self._limit_val]
        if not hasattr(self, "_iter_index"):
            self._iter_index = 0
        if self._iter_index >= len(docs):
            raise StopAsyncIteration
        doc = docs[self._iter_index]
        self._iter_index += 1
        return doc

    def _get_sorted_docs(self) -> list[dict[str, Any]]:
        """Get documents with sorting applied."""
        docs = self._documents.copy()
        if self._sort_key:
            docs.sort(
                key=lambda d: _get_nested_value(d, self._sort_key) or "",
                reverse=self._sort_direction == -1,
            )
        return docs

    async def to_list(self, length: int | None = None) -> list[dict[str, Any]]:
        """Convert cursor to list."""
        docs = self._get_sorted_docs()
        docs = docs[self._skip :]
        if self._limit_val:
            docs = docs[: self._limit_val]
        if length:
            docs = docs[:length]
        return docs

    def skip(self, n: int) -> "MockMongoCursorWithNestedFields":
        """Skip n documents."""
        self._skip = n
        return self

    def limit(self, n: int) -> "MockMongoCursorWithNestedFields":
        """Limit to n documents."""
        self._limit_val = n
        return self

    def sort(self, key_or_list: Any, direction: int = 1) -> "MockMongoCursorWithNestedFields":
        """Sort documents."""
        if isinstance(key_or_list, str):
            self._sort_key = key_or_list
            self._sort_direction = direction
        return self


class MockMongoCollectionWithNestedFields:
    """Mock MongoDB collection that supports nested field queries."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._documents: dict[str, dict[str, Any]] = {}
        self._id_counter: int = 0

    async def insert_one(self, document: dict[str, Any]) -> MagicMock:
        """Mock insert_one operation."""
        if "_id" not in document:
            self._id_counter += 1
            document["_id"] = f"mock_id_{self._id_counter}"
        self._documents[str(document["_id"])] = document.copy()
        result = MagicMock()
        result.inserted_id = document["_id"]
        return result

    async def find_one(self, filter: dict[str, Any]) -> dict[str, Any] | None:
        """Mock find_one operation with nested field support."""
        for doc in self._documents.values():
            if _matches_filter(doc, filter):
                return doc.copy()
        return None

    def find(self, filter: dict[str, Any]) -> MockMongoCursorWithNestedFields:
        """Mock find operation with nested field support."""
        matching = [doc.copy() for doc in self._documents.values() if _matches_filter(doc, filter)]
        return MockMongoCursorWithNestedFields(matching)

    async def count_documents(self, filter: dict[str, Any]) -> int:
        """Mock count_documents operation with nested field support."""
        return sum(1 for doc in self._documents.values() if _matches_filter(doc, filter))


class MockMongoDatabaseWithNestedFields:
    """Mock MongoDB database with nested field support."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._collections: dict[str, MockMongoCollectionWithNestedFields] = {}

    def __getitem__(self, collection_name: str) -> MockMongoCollectionWithNestedFields:
        """Get collection by name."""
        if collection_name not in self._collections:
            self._collections[collection_name] = MockMongoCollectionWithNestedFields(collection_name)
        return self._collections[collection_name]


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_db() -> MockMongoDatabaseWithNestedFields:
    """Provide a mock MongoDB database with nested field support."""
    return MockMongoDatabaseWithNestedFields("collection")


@pytest.fixture
def sample_document_data() -> dict:
    """Sample document data matching DocumentIndex structure."""
    return {
        "document_id": "doc-001",
        "raw_document": {
            "blob_container": "quality-data",
            "blob_path": "factory-001/2025-12-28/batch-001.json",
            "content_hash": "sha256:abc123",
            "size_bytes": 1024,
            "stored_at": datetime(2025, 12, 28, 10, 0, 0, tzinfo=UTC),
        },
        "extraction": {
            "ai_agent_id": "qc-extractor-v1",
            "extraction_timestamp": datetime(2025, 12, 28, 10, 0, 5, tzinfo=UTC),
            "confidence": 0.95,
            "validation_passed": True,
            "validation_warnings": [],
        },
        "ingestion": {
            "ingestion_id": "ing-001",
            "source_id": "qc-analyzer-result",
            "received_at": datetime(2025, 12, 28, 10, 0, 0, tzinfo=UTC),
            "processed_at": datetime(2025, 12, 28, 10, 0, 5, tzinfo=UTC),
        },
        "extracted_fields": {
            "farmer_id": "WM-0001",
            "grade": "Primary",
            "weight_kg": 25.5,
        },
        "linkage_fields": {
            "farmer_id": "WM-0001",
        },
        "created_at": datetime(2025, 12, 28, 10, 0, 5, tzinfo=UTC),
    }


@pytest.fixture
def grpc_context() -> MagicMock:
    """Mock gRPC context for testing."""
    context = MagicMock(spec=grpc.aio.ServicerContext)
    context.abort = AsyncMock()
    return context


# ═══════════════════════════════════════════════════════════════════════════════
# GETDOCUMENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_document_success(
    mock_db: MockMongoDatabaseWithNestedFields,
    grpc_context: MagicMock,
    sample_document_data: dict,
) -> None:
    """Test GetDocument returns document when found."""
    await mock_db["qc_documents"].insert_one(sample_document_data)

    servicer = CollectionServiceServicer(mock_db)
    request = collection_pb2.GetDocumentRequest(
        document_id="doc-001",
        collection_name="qc_documents",
    )

    result = await servicer.GetDocument(request, grpc_context)

    assert result.document_id == "doc-001"
    assert result.raw_document.blob_container == "quality-data"
    assert result.extraction.ai_agent_id == "qc-extractor-v1"
    assert result.ingestion.source_id == "qc-analyzer-result"
    assert result.linkage_fields["farmer_id"] == "WM-0001"


@pytest.mark.asyncio
async def test_get_document_not_found(
    mock_db: MockMongoDatabaseWithNestedFields,
    grpc_context: MagicMock,
) -> None:
    """Test GetDocument returns NOT_FOUND when document doesn't exist."""
    servicer = CollectionServiceServicer(mock_db)
    request = collection_pb2.GetDocumentRequest(
        document_id="nonexistent",
        collection_name="qc_documents",
    )

    await servicer.GetDocument(request, grpc_context)

    grpc_context.abort.assert_called_once()
    call_args = grpc_context.abort.call_args
    assert call_args[0][0] == grpc.StatusCode.NOT_FOUND


@pytest.mark.asyncio
async def test_get_document_missing_document_id(
    mock_db: MockMongoDatabaseWithNestedFields,
    grpc_context: MagicMock,
) -> None:
    """Test GetDocument returns INVALID_ARGUMENT when document_id missing."""
    servicer = CollectionServiceServicer(mock_db)
    request = collection_pb2.GetDocumentRequest(
        document_id="",
        collection_name="qc_documents",
    )

    await servicer.GetDocument(request, grpc_context)

    grpc_context.abort.assert_called_once()
    call_args = grpc_context.abort.call_args
    assert call_args[0][0] == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_get_document_missing_collection_name(
    mock_db: MockMongoDatabaseWithNestedFields,
    grpc_context: MagicMock,
) -> None:
    """Test GetDocument returns INVALID_ARGUMENT when collection_name missing."""
    servicer = CollectionServiceServicer(mock_db)
    request = collection_pb2.GetDocumentRequest(
        document_id="doc-001",
        collection_name="",
    )

    await servicer.GetDocument(request, grpc_context)

    grpc_context.abort.assert_called_once()
    call_args = grpc_context.abort.call_args
    assert call_args[0][0] == grpc.StatusCode.INVALID_ARGUMENT


# ═══════════════════════════════════════════════════════════════════════════════
# LISTDOCUMENTS TESTS
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_documents_success(
    mock_db: MockMongoDatabaseWithNestedFields,
    grpc_context: MagicMock,
    sample_document_data: dict,
) -> None:
    """Test ListDocuments returns all documents."""
    # Insert multiple documents
    await mock_db["qc_documents"].insert_one(copy.deepcopy(sample_document_data))
    doc2 = copy.deepcopy(sample_document_data)
    doc2["document_id"] = "doc-002"
    await mock_db["qc_documents"].insert_one(doc2)

    servicer = CollectionServiceServicer(mock_db)
    request = collection_pb2.ListDocumentsRequest(
        collection_name="qc_documents",
        page_size=10,
    )

    result = await servicer.ListDocuments(request, grpc_context)

    assert len(result.documents) == 2
    assert result.total_count == 2


@pytest.mark.asyncio
async def test_list_documents_with_farmer_id_filter(
    mock_db: MockMongoDatabaseWithNestedFields,
    grpc_context: MagicMock,
    sample_document_data: dict,
) -> None:
    """Test ListDocuments filters by farmer_id."""
    # Insert document for WM-0001
    await mock_db["qc_documents"].insert_one(copy.deepcopy(sample_document_data))
    # Insert document for different farmer
    doc2 = copy.deepcopy(sample_document_data)
    doc2["document_id"] = "doc-002"
    doc2["linkage_fields"] = {"farmer_id": "WM-0002"}
    await mock_db["qc_documents"].insert_one(doc2)

    servicer = CollectionServiceServicer(mock_db)
    request = collection_pb2.ListDocumentsRequest(
        collection_name="qc_documents",
        farmer_id="WM-0001",
        page_size=10,
    )

    result = await servicer.ListDocuments(request, grpc_context)

    assert len(result.documents) == 1
    assert result.documents[0].linkage_fields["farmer_id"] == "WM-0001"


@pytest.mark.asyncio
async def test_list_documents_pagination(
    mock_db: MockMongoDatabaseWithNestedFields,
    grpc_context: MagicMock,
    sample_document_data: dict,
) -> None:
    """Test ListDocuments pagination works correctly."""
    # Insert 5 documents
    for i in range(5):
        doc = sample_document_data.copy()
        doc["document_id"] = f"doc-{i:03d}"
        await mock_db["qc_documents"].insert_one(doc)

    servicer = CollectionServiceServicer(mock_db)

    # First page
    request = collection_pb2.ListDocumentsRequest(
        collection_name="qc_documents",
        page_size=2,
    )
    result = await servicer.ListDocuments(request, grpc_context)

    assert len(result.documents) == 2
    assert result.total_count == 5
    assert result.next_page_token != ""

    # Second page
    request2 = collection_pb2.ListDocumentsRequest(
        collection_name="qc_documents",
        page_size=2,
        page_token=result.next_page_token,
    )
    result2 = await servicer.ListDocuments(request2, grpc_context)

    assert len(result2.documents) == 2


@pytest.mark.asyncio
async def test_list_documents_missing_collection_name(
    mock_db: MockMongoDatabaseWithNestedFields,
    grpc_context: MagicMock,
) -> None:
    """Test ListDocuments returns INVALID_ARGUMENT when collection_name missing."""
    servicer = CollectionServiceServicer(mock_db)
    request = collection_pb2.ListDocumentsRequest(
        collection_name="",
        page_size=10,
    )

    await servicer.ListDocuments(request, grpc_context)

    grpc_context.abort.assert_called_once()
    call_args = grpc_context.abort.call_args
    assert call_args[0][0] == grpc.StatusCode.INVALID_ARGUMENT


# ═══════════════════════════════════════════════════════════════════════════════
# GETDOCUMENTSBYFARMER TESTS
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_documents_by_farmer_success(
    mock_db: MockMongoDatabaseWithNestedFields,
    grpc_context: MagicMock,
    sample_document_data: dict,
) -> None:
    """Test GetDocumentsByFarmer returns all documents for a farmer."""
    # Insert 3 documents for WM-0001
    for i in range(3):
        doc = sample_document_data.copy()
        doc["document_id"] = f"doc-{i:03d}"
        await mock_db["qc_documents"].insert_one(doc)

    servicer = CollectionServiceServicer(mock_db)
    request = collection_pb2.GetDocumentsByFarmerRequest(
        farmer_id="WM-0001",
        collection_name="qc_documents",
    )

    result = await servicer.GetDocumentsByFarmer(request, grpc_context)

    assert len(result.documents) == 3
    assert result.total_count == 3


@pytest.mark.asyncio
async def test_get_documents_by_farmer_with_limit(
    mock_db: MockMongoDatabaseWithNestedFields,
    grpc_context: MagicMock,
    sample_document_data: dict,
) -> None:
    """Test GetDocumentsByFarmer respects limit parameter."""
    # Insert 5 documents
    for i in range(5):
        doc = sample_document_data.copy()
        doc["document_id"] = f"doc-{i:03d}"
        await mock_db["qc_documents"].insert_one(doc)

    servicer = CollectionServiceServicer(mock_db)
    request = collection_pb2.GetDocumentsByFarmerRequest(
        farmer_id="WM-0001",
        collection_name="qc_documents",
        limit=3,
    )

    result = await servicer.GetDocumentsByFarmer(request, grpc_context)

    assert len(result.documents) == 3


@pytest.mark.asyncio
async def test_get_documents_by_farmer_missing_farmer_id(
    mock_db: MockMongoDatabaseWithNestedFields,
    grpc_context: MagicMock,
) -> None:
    """Test GetDocumentsByFarmer returns INVALID_ARGUMENT when farmer_id missing."""
    servicer = CollectionServiceServicer(mock_db)
    request = collection_pb2.GetDocumentsByFarmerRequest(
        farmer_id="",
        collection_name="qc_documents",
    )

    await servicer.GetDocumentsByFarmer(request, grpc_context)

    grpc_context.abort.assert_called_once()
    call_args = grpc_context.abort.call_args
    assert call_args[0][0] == grpc.StatusCode.INVALID_ARGUMENT


# ═══════════════════════════════════════════════════════════════════════════════
# SEARCHDOCUMENTS TESTS
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_search_documents_by_source_id(
    mock_db: MockMongoDatabaseWithNestedFields,
    grpc_context: MagicMock,
    sample_document_data: dict,
) -> None:
    """Test SearchDocuments filters by source_id."""
    # Insert document with source_id
    await mock_db["qc_documents"].insert_one(copy.deepcopy(sample_document_data))
    # Insert document with different source_id
    doc2 = copy.deepcopy(sample_document_data)
    doc2["document_id"] = "doc-002"
    doc2["ingestion"]["source_id"] = "weather-data"
    await mock_db["qc_documents"].insert_one(doc2)

    servicer = CollectionServiceServicer(mock_db)
    request = collection_pb2.SearchDocumentsRequest(
        collection_name="qc_documents",
        source_id="qc-analyzer-result",
    )

    result = await servicer.SearchDocuments(request, grpc_context)

    assert len(result.documents) == 1
    assert result.documents[0].ingestion.source_id == "qc-analyzer-result"


@pytest.mark.asyncio
async def test_search_documents_by_linkage_filter(
    mock_db: MockMongoDatabaseWithNestedFields,
    grpc_context: MagicMock,
    sample_document_data: dict,
) -> None:
    """Test SearchDocuments filters by linkage_fields."""
    await mock_db["qc_documents"].insert_one(copy.deepcopy(sample_document_data))
    # Insert document with different farmer
    doc2 = copy.deepcopy(sample_document_data)
    doc2["document_id"] = "doc-002"
    doc2["linkage_fields"] = {"farmer_id": "WM-0002"}
    await mock_db["qc_documents"].insert_one(doc2)

    servicer = CollectionServiceServicer(mock_db)
    request = collection_pb2.SearchDocumentsRequest(
        collection_name="qc_documents",
        linkage_filters={"farmer_id": "WM-0001"},
    )

    result = await servicer.SearchDocuments(request, grpc_context)

    assert len(result.documents) == 1
    assert result.documents[0].linkage_fields["farmer_id"] == "WM-0001"


@pytest.mark.asyncio
async def test_search_documents_empty_results(
    mock_db: MockMongoDatabaseWithNestedFields,
    grpc_context: MagicMock,
) -> None:
    """Test SearchDocuments returns empty results when no match."""
    servicer = CollectionServiceServicer(mock_db)
    request = collection_pb2.SearchDocumentsRequest(
        collection_name="qc_documents",
        source_id="nonexistent-source",
    )

    result = await servicer.SearchDocuments(request, grpc_context)

    assert len(result.documents) == 0
    assert result.total_count == 0


@pytest.mark.asyncio
async def test_search_documents_missing_collection_name(
    mock_db: MockMongoDatabaseWithNestedFields,
    grpc_context: MagicMock,
) -> None:
    """Test SearchDocuments returns INVALID_ARGUMENT when collection_name missing."""
    servicer = CollectionServiceServicer(mock_db)
    request = collection_pb2.SearchDocumentsRequest(
        collection_name="",
    )

    await servicer.SearchDocuments(request, grpc_context)

    grpc_context.abort.assert_called_once()
    call_args = grpc_context.abort.call_args
    assert call_args[0][0] == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_search_documents_pagination(
    mock_db: MockMongoDatabaseWithNestedFields,
    grpc_context: MagicMock,
    sample_document_data: dict,
) -> None:
    """Test SearchDocuments pagination works correctly."""
    # Insert 5 documents
    for i in range(5):
        doc = sample_document_data.copy()
        doc["document_id"] = f"doc-{i:03d}"
        await mock_db["qc_documents"].insert_one(doc)

    servicer = CollectionServiceServicer(mock_db)

    # First page
    request = collection_pb2.SearchDocumentsRequest(
        collection_name="qc_documents",
        page_size=2,
    )
    result = await servicer.SearchDocuments(request, grpc_context)

    assert len(result.documents) == 2
    assert result.total_count == 5
    assert result.next_page_token != ""


# ═══════════════════════════════════════════════════════════════════════════════
# CONVERSION HELPER TESTS
# ═══════════════════════════════════════════════════════════════════════════════


def test_document_index_to_proto_conversion(sample_document_data: dict) -> None:
    """Test that DocumentIndex is correctly converted to proto."""
    from collection_model.api.grpc_service import _document_index_to_proto
    from collection_model.domain.document_index import DocumentIndex

    doc = DocumentIndex.model_validate(sample_document_data)
    proto_doc = _document_index_to_proto(doc)

    assert proto_doc.document_id == "doc-001"
    assert proto_doc.raw_document.blob_container == "quality-data"
    assert proto_doc.extraction.confidence == 0.95
    assert proto_doc.ingestion.source_id == "qc-analyzer-result"
    assert proto_doc.extracted_fields["farmer_id"] == "WM-0001"
    assert proto_doc.linkage_fields["farmer_id"] == "WM-0001"
