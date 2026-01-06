"""Unit tests for CollectionGrpcClient.

Story 0.6.13: Tests for gRPC client that replaces direct MongoDB access.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import pytest
from fp_common.models import Document
from fp_proto.collection.v1 import collection_pb2
from google.protobuf.timestamp_pb2 import Timestamp
from plantation_model.infrastructure.collection_grpc_client import (
    CollectionClientError,
    CollectionGrpcClient,
    DocumentNotFoundError,
)


def _datetime_to_timestamp(dt: datetime) -> Timestamp:
    """Helper to convert datetime to protobuf Timestamp."""
    ts = Timestamp()
    ts.FromDatetime(dt)
    return ts


@pytest.fixture
def mock_channel():
    """Create a mock gRPC channel."""
    channel = MagicMock(spec=grpc.aio.Channel)
    channel.close = AsyncMock()
    return channel


@pytest.fixture
def sample_proto_document() -> collection_pb2.Document:
    """Sample proto Document for testing."""
    now = datetime(2026, 1, 6, 10, 0, 0, tzinfo=UTC)
    return collection_pb2.Document(
        document_id="doc-grpc-001",
        raw_document=collection_pb2.RawDocumentRef(
            blob_container="quality-data",
            blob_path="factory-001/batch.json",
            content_hash="sha256:test",
            size_bytes=1024,
            stored_at=_datetime_to_timestamp(now),
        ),
        extraction=collection_pb2.ExtractionMetadata(
            ai_agent_id="extractor-v1",
            extraction_timestamp=_datetime_to_timestamp(now),
            confidence=0.95,
            validation_passed=True,
            validation_warnings=[],
        ),
        ingestion=collection_pb2.IngestionMetadata(
            ingestion_id="ing-001",
            source_id="qc-analyzer-result",
            received_at=_datetime_to_timestamp(now),
            processed_at=_datetime_to_timestamp(now),
        ),
        extracted_fields={
            "farmer_id": "WM-0001",
            "grading_model_id": "tbk-kenya-v1",
        },
        linkage_fields={"farmer_id": "WM-0001"},
        created_at=_datetime_to_timestamp(now),
    )


class TestCollectionGrpcClient:
    """Tests for CollectionGrpcClient."""

    @pytest.mark.asyncio
    async def test_get_document_returns_pydantic_model(self, mock_channel, sample_proto_document):
        """get_document returns a Pydantic Document model."""
        # Arrange
        mock_stub = MagicMock()
        mock_stub.GetDocument = AsyncMock(return_value=sample_proto_document)

        with patch(
            "plantation_model.infrastructure.collection_grpc_client.collection_pb2_grpc.CollectionServiceStub"
        ) as mock_stub_class:
            mock_stub_class.return_value = mock_stub

            client = CollectionGrpcClient(channel=mock_channel)

            # Act
            result = await client.get_document("doc-grpc-001")

            # Assert
            assert isinstance(result, Document)
            assert result.document_id == "doc-grpc-001"
            assert result.raw_document.blob_container == "quality-data"
            assert result.extraction.confidence == 0.95
            assert result.ingestion.source_id == "qc-analyzer-result"
            assert result.extracted_fields["farmer_id"] == "WM-0001"

    @pytest.mark.asyncio
    async def test_get_document_uses_correct_request(self, mock_channel, sample_proto_document):
        """get_document passes correct parameters to gRPC request."""
        mock_stub = MagicMock()
        mock_stub.GetDocument = AsyncMock(return_value=sample_proto_document)

        with patch(
            "plantation_model.infrastructure.collection_grpc_client.collection_pb2_grpc.CollectionServiceStub"
        ) as mock_stub_class:
            mock_stub_class.return_value = mock_stub

            client = CollectionGrpcClient(channel=mock_channel)

            await client.get_document("doc-123", collection_name="custom_collection")

            # Verify the request was made with correct parameters
            call_args = mock_stub.GetDocument.call_args
            request = call_args[0][0]
            assert request.document_id == "doc-123"
            assert request.collection_name == "custom_collection"

    @pytest.mark.asyncio
    async def test_get_document_not_found_raises_error(self, mock_channel):
        """get_document raises DocumentNotFoundError for NOT_FOUND status."""
        mock_stub = MagicMock()
        mock_rpc_error = grpc.aio.AioRpcError(
            code=grpc.StatusCode.NOT_FOUND,
            initial_metadata=grpc.aio.Metadata(),
            trailing_metadata=grpc.aio.Metadata(),
            details="Document not found",
            debug_error_string="",
        )
        mock_stub.GetDocument = AsyncMock(side_effect=mock_rpc_error)

        with patch(
            "plantation_model.infrastructure.collection_grpc_client.collection_pb2_grpc.CollectionServiceStub"
        ) as mock_stub_class:
            mock_stub_class.return_value = mock_stub

            client = CollectionGrpcClient(channel=mock_channel)

            with pytest.raises(DocumentNotFoundError) as exc_info:
                await client.get_document("nonexistent-doc")

            assert exc_info.value.document_id == "nonexistent-doc"

    @pytest.mark.asyncio
    async def test_get_document_unavailable_raises_client_error(self, mock_channel):
        """get_document raises CollectionClientError for UNAVAILABLE status."""
        mock_stub = MagicMock()
        mock_rpc_error = grpc.aio.AioRpcError(
            code=grpc.StatusCode.UNAVAILABLE,
            initial_metadata=grpc.aio.Metadata(),
            trailing_metadata=grpc.aio.Metadata(),
            details="Service unavailable",
            debug_error_string="",
        )
        mock_stub.GetDocument = AsyncMock(side_effect=mock_rpc_error)

        with patch(
            "plantation_model.infrastructure.collection_grpc_client.collection_pb2_grpc.CollectionServiceStub"
        ) as mock_stub_class:
            mock_stub_class.return_value = mock_stub
            # Disable retry for faster test
            with patch.object(CollectionGrpcClient, "get_document", new=CollectionGrpcClient.get_document.__wrapped__):
                client = CollectionGrpcClient(channel=mock_channel)

                with pytest.raises(CollectionClientError) as exc_info:
                    await client.get_document("doc-123")

                assert "doc-123" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_close_closes_channel(self, mock_channel):
        """close() properly closes the gRPC channel."""
        client = CollectionGrpcClient(channel=mock_channel)

        await client.close()

        mock_channel.close.assert_called_once()
        assert client._channel is None
        assert client._stub is None

    @pytest.mark.asyncio
    async def test_singleton_pattern_reuses_stub(self, mock_channel, sample_proto_document):
        """Stub is reused across multiple calls (singleton pattern)."""
        mock_stub = MagicMock()
        mock_stub.GetDocument = AsyncMock(return_value=sample_proto_document)

        with patch(
            "plantation_model.infrastructure.collection_grpc_client.collection_pb2_grpc.CollectionServiceStub"
        ) as mock_stub_class:
            mock_stub_class.return_value = mock_stub

            client = CollectionGrpcClient(channel=mock_channel)

            # Make multiple calls
            await client.get_document("doc-1")
            await client.get_document("doc-2")
            await client.get_document("doc-3")

            # Stub should only be created once
            assert mock_stub_class.call_count == 1


class TestDocumentNotFoundError:
    """Tests for DocumentNotFoundError exception."""

    def test_stores_document_id(self):
        """Exception stores the document_id."""
        error = DocumentNotFoundError("doc-abc-123")
        assert error.document_id == "doc-abc-123"
        assert "doc-abc-123" in str(error)


class TestCollectionClientError:
    """Tests for CollectionClientError exception."""

    def test_stores_cause(self):
        """Exception stores the cause."""
        cause = ValueError("original error")
        error = CollectionClientError("Failed operation", cause=cause)
        assert error.cause is cause
        assert "Failed operation" in str(error)
