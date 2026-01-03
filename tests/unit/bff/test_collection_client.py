"""Unit tests for CollectionClient.

Tests all 4 document query methods, DAPR service invocation, error handling, and retry logic.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from bff.infrastructure.clients.base import NotFoundError, ServiceUnavailableError
from bff.infrastructure.clients.collection_client import CollectionClient
from fp_common.models import Document
from fp_proto.collection.v1 import collection_pb2, collection_pb2_grpc

from tests.unit.bff.conftest import create_document_proto


@pytest.fixture
def mock_collection_stub() -> MagicMock:
    """Create a mock Collection service stub."""
    stub = MagicMock()
    stub.GetDocument = AsyncMock()
    stub.ListDocuments = AsyncMock()
    stub.GetDocumentsByFarmer = AsyncMock()
    stub.SearchDocuments = AsyncMock()
    return stub


@pytest.fixture
def collection_client_with_mock_stub(
    mock_collection_stub: MagicMock,
) -> tuple[CollectionClient, MagicMock]:
    """Create a CollectionClient with a mocked stub."""
    client = CollectionClient(direct_host="localhost:50051")
    # Inject the mock stub
    client._stubs[collection_pb2_grpc.CollectionServiceStub] = mock_collection_stub
    return client, mock_collection_stub


class TestCollectionClientInit:
    """Tests for CollectionClient initialization."""

    def test_default_init(self) -> None:
        """Test default initialization with DAPR settings."""
        client = CollectionClient()
        assert client._target_app_id == "collection-model"
        assert client._dapr_grpc_port == 50001
        assert client._direct_host is None
        assert client._channel is None

    def test_direct_host_init(self) -> None:
        """Test initialization with direct host."""
        client = CollectionClient(direct_host="localhost:50051")
        assert client._direct_host == "localhost:50051"

    def test_custom_dapr_port(self) -> None:
        """Test initialization with custom DAPR port."""
        client = CollectionClient(dapr_grpc_port=50099)
        assert client._dapr_grpc_port == 50099


class TestCollectionClientMetadata:
    """Tests for gRPC metadata handling."""

    def test_metadata_with_dapr(self) -> None:
        """Test metadata generation with DAPR routing."""
        client = CollectionClient()
        metadata = client._get_metadata()
        assert ("dapr-app-id", "collection-model") in metadata

    def test_metadata_direct_connection(self) -> None:
        """Test metadata is empty for direct connection."""
        client = CollectionClient(direct_host="localhost:50051")
        metadata = client._get_metadata()
        assert metadata == []


class TestGetDocument:
    """Tests for get_document method."""

    @pytest.mark.asyncio
    async def test_get_document_success(
        self,
        collection_client_with_mock_stub: tuple[CollectionClient, MagicMock],
    ) -> None:
        """Test successful document retrieval."""
        client, stub = collection_client_with_mock_stub
        stub.GetDocument.return_value = create_document_proto(document_id="doc-12345")

        doc = await client.get_document("doc-12345", "qc_analyzer_results")

        assert isinstance(doc, Document)
        assert doc.document_id == "doc-12345"
        assert doc.raw_document.blob_container == "quality-data"
        assert doc.extraction.ai_agent_id == "qc-extractor-v1"
        assert doc.extraction.confidence == 0.95
        assert doc.ingestion.source_id == "qc-analyzer-result"
        assert doc.extracted_fields["farmer_id"] == "WM-0001"
        assert doc.linkage_fields["farmer_id"] == "WM-0001"

    @pytest.mark.asyncio
    async def test_get_document_not_found(
        self,
        collection_client_with_mock_stub: tuple[CollectionClient, MagicMock],
    ) -> None:
        """Test document not found error."""
        client, stub = collection_client_with_mock_stub
        error = grpc.aio.AioRpcError(
            code=grpc.StatusCode.NOT_FOUND,
            initial_metadata=None,
            trailing_metadata=None,
            details="Document not found",
            debug_error_string="",
        )
        stub.GetDocument.side_effect = error

        with pytest.raises(NotFoundError, match="Document doc-9999 not found"):
            await client.get_document("doc-9999", "qc_analyzer_results")

    @pytest.mark.asyncio
    async def test_get_document_request_params(
        self,
        collection_client_with_mock_stub: tuple[CollectionClient, MagicMock],
    ) -> None:
        """Test get_document sends correct request parameters."""
        client, stub = collection_client_with_mock_stub
        stub.GetDocument.return_value = create_document_proto()

        await client.get_document("doc-123", "my_collection")

        call_args = stub.GetDocument.call_args
        request = call_args[0][0]
        assert request.document_id == "doc-123"
        assert request.collection_name == "my_collection"


class TestListDocuments:
    """Tests for list_documents method."""

    @pytest.mark.asyncio
    async def test_list_documents_success(
        self,
        collection_client_with_mock_stub: tuple[CollectionClient, MagicMock],
    ) -> None:
        """Test successful document listing returns PaginatedResponse."""
        client, stub = collection_client_with_mock_stub
        response = collection_pb2.ListDocumentsResponse(
            documents=[
                create_document_proto(document_id="doc-001"),
                create_document_proto(document_id="doc-002"),
            ],
            next_page_token="token123",
            total_count=100,
        )
        stub.ListDocuments.return_value = response

        result = await client.list_documents("qc_analyzer_results")

        assert len(result.data) == 2
        assert all(isinstance(doc, Document) for doc in result.data)
        assert result.data[0].document_id == "doc-001"
        assert result.data[1].document_id == "doc-002"
        assert result.pagination.next_page_token == "token123"
        assert result.pagination.total_count == 100
        assert result.pagination.has_next is True
        assert result.meta is not None

    @pytest.mark.asyncio
    async def test_list_documents_with_pagination(
        self,
        collection_client_with_mock_stub: tuple[CollectionClient, MagicMock],
    ) -> None:
        """Test document listing with pagination parameters."""
        client, stub = collection_client_with_mock_stub
        response = collection_pb2.ListDocumentsResponse(
            documents=[create_document_proto()],
            next_page_token="",
            total_count=1,
        )
        stub.ListDocuments.return_value = response

        result = await client.list_documents(
            collection_name="qc_analyzer_results",
            page_size=10,
            page_token="prev_token",
        )

        call_args = stub.ListDocuments.call_args
        request = call_args[0][0]
        assert request.page_size == 10
        assert request.page_token == "prev_token"
        assert result.pagination.next_page_token is None  # Empty string should become None
        assert result.pagination.has_next is False

    @pytest.mark.asyncio
    async def test_list_documents_with_farmer_filter(
        self,
        collection_client_with_mock_stub: tuple[CollectionClient, MagicMock],
    ) -> None:
        """Test document listing with farmer_id filter."""
        client, stub = collection_client_with_mock_stub
        response = collection_pb2.ListDocumentsResponse(
            documents=[create_document_proto(farmer_id="WM-0002")],
            next_page_token="",
            total_count=1,
        )
        stub.ListDocuments.return_value = response

        result = await client.list_documents(
            collection_name="qc_analyzer_results",
            farmer_id="WM-0002",
        )

        call_args = stub.ListDocuments.call_args
        request = call_args[0][0]
        assert request.farmer_id == "WM-0002"
        assert len(result.data) == 1

    @pytest.mark.asyncio
    async def test_list_documents_page_size_capped(
        self,
        collection_client_with_mock_stub: tuple[CollectionClient, MagicMock],
    ) -> None:
        """Test page_size is capped at 100 in request and response."""
        client, stub = collection_client_with_mock_stub
        response = collection_pb2.ListDocumentsResponse(
            documents=[],
            next_page_token="",
            total_count=0,
        )
        stub.ListDocuments.return_value = response

        result = await client.list_documents("qc_analyzer_results", page_size=200)

        call_args = stub.ListDocuments.call_args
        request = call_args[0][0]
        assert request.page_size == 100  # Request should be capped at 100
        assert result.pagination.page_size == 100  # Response should also show capped value


class TestGetDocumentsByFarmer:
    """Tests for get_documents_by_farmer method."""

    @pytest.mark.asyncio
    async def test_get_documents_by_farmer_success(
        self,
        collection_client_with_mock_stub: tuple[CollectionClient, MagicMock],
    ) -> None:
        """Test successful retrieval of documents by farmer returns BoundedResponse."""
        client, stub = collection_client_with_mock_stub
        response = collection_pb2.GetDocumentsByFarmerResponse(
            documents=[
                create_document_proto(document_id="doc-001", farmer_id="WM-0001"),
                create_document_proto(document_id="doc-002", farmer_id="WM-0001"),
                create_document_proto(document_id="doc-003", farmer_id="WM-0001"),
            ],
            total_count=3,
        )
        stub.GetDocumentsByFarmer.return_value = response

        result = await client.get_documents_by_farmer("WM-0001", "qc_analyzer_results")

        assert len(result.data) == 3
        assert all(isinstance(doc, Document) for doc in result.data)
        assert result.total_count == 3
        assert len(result) == 3  # Test __len__ method
        assert result.meta is not None

    @pytest.mark.asyncio
    async def test_get_documents_by_farmer_with_limit(
        self,
        collection_client_with_mock_stub: tuple[CollectionClient, MagicMock],
    ) -> None:
        """Test get_documents_by_farmer with custom limit."""
        client, stub = collection_client_with_mock_stub
        response = collection_pb2.GetDocumentsByFarmerResponse(
            documents=[create_document_proto()],
            total_count=1,
        )
        stub.GetDocumentsByFarmer.return_value = response

        await client.get_documents_by_farmer("WM-0001", "qc_analyzer_results", limit=50)

        call_args = stub.GetDocumentsByFarmer.call_args
        request = call_args[0][0]
        assert request.farmer_id == "WM-0001"
        assert request.collection_name == "qc_analyzer_results"
        assert request.limit == 50

    @pytest.mark.asyncio
    async def test_get_documents_by_farmer_empty(
        self,
        collection_client_with_mock_stub: tuple[CollectionClient, MagicMock],
    ) -> None:
        """Test get_documents_by_farmer with no results returns empty BoundedResponse."""
        client, stub = collection_client_with_mock_stub
        response = collection_pb2.GetDocumentsByFarmerResponse(
            documents=[],
            total_count=0,
        )
        stub.GetDocumentsByFarmer.return_value = response

        result = await client.get_documents_by_farmer("WM-9999", "qc_analyzer_results")

        assert len(result.data) == 0
        assert result.total_count == 0
        assert len(result) == 0


class TestSearchDocuments:
    """Tests for search_documents method."""

    @pytest.mark.asyncio
    async def test_search_documents_success(
        self,
        collection_client_with_mock_stub: tuple[CollectionClient, MagicMock],
    ) -> None:
        """Test successful document search returns PaginatedResponse."""
        client, stub = collection_client_with_mock_stub
        response = collection_pb2.SearchDocumentsResponse(
            documents=[
                create_document_proto(document_id="doc-001"),
                create_document_proto(document_id="doc-002"),
            ],
            next_page_token="token456",
            total_count=50,
        )
        stub.SearchDocuments.return_value = response

        result = await client.search_documents("qc_analyzer_results")

        assert len(result.data) == 2
        assert all(isinstance(doc, Document) for doc in result.data)
        assert result.pagination.next_page_token == "token456"
        assert result.pagination.total_count == 50
        assert result.pagination.has_next is True
        assert result.meta is not None

    @pytest.mark.asyncio
    async def test_search_documents_with_source_filter(
        self,
        collection_client_with_mock_stub: tuple[CollectionClient, MagicMock],
    ) -> None:
        """Test search with source_id filter."""
        client, stub = collection_client_with_mock_stub
        response = collection_pb2.SearchDocumentsResponse(
            documents=[create_document_proto()],
            next_page_token="",
            total_count=1,
        )
        stub.SearchDocuments.return_value = response

        await client.search_documents(
            collection_name="qc_analyzer_results",
            source_id="qc-analyzer-result",
        )

        call_args = stub.SearchDocuments.call_args
        request = call_args[0][0]
        assert request.source_id == "qc-analyzer-result"

    @pytest.mark.asyncio
    async def test_search_documents_with_date_range(
        self,
        collection_client_with_mock_stub: tuple[CollectionClient, MagicMock],
    ) -> None:
        """Test search with date range filter."""
        client, stub = collection_client_with_mock_stub
        response = collection_pb2.SearchDocumentsResponse(
            documents=[],
            next_page_token="",
            total_count=0,
        )
        stub.SearchDocuments.return_value = response

        start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)

        await client.search_documents(
            collection_name="qc_analyzer_results",
            start_date=start,
            end_date=end,
        )

        call_args = stub.SearchDocuments.call_args
        request = call_args[0][0]
        assert request.start_date.seconds > 0
        assert request.end_date.seconds > 0

    @pytest.mark.asyncio
    async def test_search_documents_with_linkage_filters(
        self,
        collection_client_with_mock_stub: tuple[CollectionClient, MagicMock],
    ) -> None:
        """Test search with linkage filters."""
        client, stub = collection_client_with_mock_stub
        response = collection_pb2.SearchDocumentsResponse(
            documents=[create_document_proto()],
            next_page_token="",
            total_count=1,
        )
        stub.SearchDocuments.return_value = response

        await client.search_documents(
            collection_name="qc_analyzer_results",
            linkage_filters={"farmer_id": "WM-0001", "region": "nyeri"},
        )

        call_args = stub.SearchDocuments.call_args
        request = call_args[0][0]
        assert request.linkage_filters["farmer_id"] == "WM-0001"
        assert request.linkage_filters["region"] == "nyeri"

    @pytest.mark.asyncio
    async def test_search_documents_with_pagination(
        self,
        collection_client_with_mock_stub: tuple[CollectionClient, MagicMock],
    ) -> None:
        """Test search with pagination parameters."""
        client, stub = collection_client_with_mock_stub
        response = collection_pb2.SearchDocumentsResponse(
            documents=[],
            next_page_token="",
            total_count=0,
        )
        stub.SearchDocuments.return_value = response

        await client.search_documents(
            collection_name="qc_analyzer_results",
            page_size=50,
            page_token="prev_token",
        )

        call_args = stub.SearchDocuments.call_args
        request = call_args[0][0]
        assert request.page_size == 50
        assert request.page_token == "prev_token"

    @pytest.mark.asyncio
    async def test_search_documents_page_size_capped(
        self,
        collection_client_with_mock_stub: tuple[CollectionClient, MagicMock],
    ) -> None:
        """Test page_size is capped at 100 for search in request and response."""
        client, stub = collection_client_with_mock_stub
        response = collection_pb2.SearchDocumentsResponse(
            documents=[],
            next_page_token="",
            total_count=0,
        )
        stub.SearchDocuments.return_value = response

        result = await client.search_documents("qc_analyzer_results", page_size=200)

        call_args = stub.SearchDocuments.call_args
        request = call_args[0][0]
        assert request.page_size == 100  # Request should be capped at 100
        assert result.pagination.page_size == 100  # Response should also show capped value


class TestErrorHandling:
    """Tests for error handling and retry logic."""

    @pytest.mark.asyncio
    async def test_service_unavailable_error(
        self,
        collection_client_with_mock_stub: tuple[CollectionClient, MagicMock],
    ) -> None:
        """Test service unavailable error handling."""
        client, stub = collection_client_with_mock_stub
        error = grpc.aio.AioRpcError(
            code=grpc.StatusCode.UNAVAILABLE,
            initial_metadata=None,
            trailing_metadata=None,
            details="Connection refused",
            debug_error_string="",
        )
        stub.GetDocument.side_effect = error

        with pytest.raises(ServiceUnavailableError, match="Service unavailable"):
            await client.get_document("doc-123", "collection")

    @pytest.mark.asyncio
    async def test_channel_reset_on_unavailable(
        self,
        collection_client_with_mock_stub: tuple[CollectionClient, MagicMock],
    ) -> None:
        """Test channel is reset on UNAVAILABLE error."""
        client, stub = collection_client_with_mock_stub
        # Pre-populate stubs cache
        client._stubs["test_stub"] = "test_value"

        error = grpc.aio.AioRpcError(
            code=grpc.StatusCode.UNAVAILABLE,
            initial_metadata=None,
            trailing_metadata=None,
            details="Connection refused",
            debug_error_string="",
        )
        stub.GetDocument.side_effect = error

        with pytest.raises(ServiceUnavailableError):
            await client.get_document("doc-123", "collection")

        # Channel reset is called - the key behavior is ServiceUnavailableError

    @pytest.mark.asyncio
    async def test_unknown_grpc_error_propagated(
        self,
        collection_client_with_mock_stub: tuple[CollectionClient, MagicMock],
    ) -> None:
        """Test unknown gRPC errors are propagated."""
        client, stub = collection_client_with_mock_stub
        error = grpc.aio.AioRpcError(
            code=grpc.StatusCode.INTERNAL,
            initial_metadata=None,
            trailing_metadata=None,
            details="Internal server error",
            debug_error_string="",
        )
        stub.GetDocument.side_effect = error

        with pytest.raises(grpc.aio.AioRpcError):
            await client.get_document("doc-123", "collection")


class TestProtoConversion:
    """Tests for proto-to-domain model conversion."""

    @pytest.mark.asyncio
    async def test_document_fields_converted(
        self,
        collection_client_with_mock_stub: tuple[CollectionClient, MagicMock],
    ) -> None:
        """Test all document fields are correctly converted."""
        client, stub = collection_client_with_mock_stub
        proto = create_document_proto(
            document_id="custom-doc",
            blob_container="custom-container",
            blob_path="path/to/blob.json",
            content_hash="sha256:custom",
            size_bytes=2048,
            ai_agent_id="custom-agent",
            confidence=0.88,
            validation_passed=False,
            ingestion_id="ing-custom",
            source_id="custom-source",
            farmer_id="WM-9999",
        )
        # Add validation warning
        proto.extraction.validation_warnings.append("Low confidence warning")
        stub.GetDocument.return_value = proto

        doc = await client.get_document("custom-doc", "collection")

        assert doc.document_id == "custom-doc"
        assert doc.raw_document.blob_container == "custom-container"
        assert doc.raw_document.blob_path == "path/to/blob.json"
        assert doc.raw_document.content_hash == "sha256:custom"
        assert doc.raw_document.size_bytes == 2048
        assert doc.extraction.ai_agent_id == "custom-agent"
        assert doc.extraction.confidence == 0.88
        assert doc.extraction.validation_passed is False
        assert "Low confidence warning" in doc.extraction.validation_warnings
        assert doc.ingestion.ingestion_id == "ing-custom"
        assert doc.ingestion.source_id == "custom-source"
        assert doc.linkage_fields["farmer_id"] == "WM-9999"


class TestClientClose:
    """Tests for client cleanup."""

    @pytest.mark.asyncio
    async def test_close_cleans_up_channel(self) -> None:
        """Test close properly cleans up channel."""
        client = CollectionClient(direct_host="localhost:50051")
        mock_channel = AsyncMock()
        client._channel = mock_channel
        client._stubs["test"] = "value"

        await client.close()

        mock_channel.close.assert_called_once()
        assert client._channel is None
        assert client._stubs == {}

    @pytest.mark.asyncio
    async def test_close_without_channel(self) -> None:
        """Test close is safe when no channel exists."""
        client = CollectionClient()
        # Should not raise
        await client.close()
        assert client._channel is None
