"""Collection Model gRPC client for BFF.

Provides typed access to Collection Model service via DAPR service invocation.
Implements 4 document query methods following the pattern from PlantationClient.

Per ADR-002 §"Service Invocation Pattern" and ADR-005 for retry logic.
"""

from datetime import datetime

import grpc
import grpc.aio
import structlog
from bff.infrastructure.clients.base import (
    BaseGrpcClient,
    grpc_retry,
)
from fp_common.models import (
    Document,
    ExtractionMetadata,
    IngestionMetadata,
    RawDocumentRef,
)
from fp_proto.collection.v1 import collection_pb2, collection_pb2_grpc
from google.protobuf.timestamp_pb2 import Timestamp

logger = structlog.get_logger(__name__)


class CollectionClient(BaseGrpcClient):
    """gRPC client for Collection Model service.

    Provides typed access to document query operations via DAPR service invocation.
    All methods return Pydantic domain models (NOT dict[str, Any]).

    Example:
        >>> client = CollectionClient()
        >>> doc = await client.get_document("doc-123", "qc_analyzer_results")
        >>> assert isinstance(doc, Document)

        >>> # With direct connection for testing
        >>> client = CollectionClient(direct_host="localhost:50051")
    """

    def __init__(
        self,
        dapr_grpc_port: int = 50001,
        direct_host: str | None = None,
        channel: grpc.aio.Channel | None = None,
    ) -> None:
        """Initialize the CollectionClient.

        Args:
            dapr_grpc_port: Port for DAPR sidecar gRPC endpoint (default: 50001).
            direct_host: Optional direct host for testing (e.g., "localhost:50051").
                        If provided, DAPR routing is bypassed.
            channel: Optional pre-configured channel for testing.
        """
        super().__init__(
            target_app_id="collection-model",
            dapr_grpc_port=dapr_grpc_port,
            direct_host=direct_host,
            channel=channel,
        )

    # =========================================================================
    # Helper Methods for Proto-to-Domain Conversion
    # =========================================================================

    def _proto_to_document(self, proto: collection_pb2.Document) -> Document:
        """Convert proto Document to Pydantic Document model.

        Args:
            proto: The proto Document message.

        Returns:
            A Pydantic Document model.
        """
        # Convert proto Timestamp to datetime
        raw_stored_at = (
            proto.raw_document.stored_at.ToDatetime() if proto.raw_document.HasField("stored_at") else datetime.now()
        )
        extraction_timestamp = (
            proto.extraction.extraction_timestamp.ToDatetime()
            if proto.extraction.HasField("extraction_timestamp")
            else datetime.now()
        )
        received_at = (
            proto.ingestion.received_at.ToDatetime() if proto.ingestion.HasField("received_at") else datetime.now()
        )
        processed_at = (
            proto.ingestion.processed_at.ToDatetime() if proto.ingestion.HasField("processed_at") else datetime.now()
        )
        created_at = proto.created_at.ToDatetime() if proto.HasField("created_at") else datetime.now()

        return Document(
            document_id=proto.document_id,
            raw_document=RawDocumentRef(
                blob_container=proto.raw_document.blob_container,
                blob_path=proto.raw_document.blob_path,
                content_hash=proto.raw_document.content_hash,
                size_bytes=proto.raw_document.size_bytes,
                stored_at=raw_stored_at,
            ),
            extraction=ExtractionMetadata(
                ai_agent_id=proto.extraction.ai_agent_id,
                extraction_timestamp=extraction_timestamp,
                confidence=proto.extraction.confidence,
                validation_passed=proto.extraction.validation_passed,
                validation_warnings=list(proto.extraction.validation_warnings),
            ),
            ingestion=IngestionMetadata(
                ingestion_id=proto.ingestion.ingestion_id,
                source_id=proto.ingestion.source_id,
                received_at=received_at,
                processed_at=processed_at,
            ),
            extracted_fields=dict(proto.extracted_fields),
            linkage_fields=dict(proto.linkage_fields),
            created_at=created_at,
        )

    def _datetime_to_proto_timestamp(self, dt: datetime) -> Timestamp:
        """Convert datetime to proto Timestamp.

        Args:
            dt: The datetime to convert.

        Returns:
            A proto Timestamp.
        """
        ts = Timestamp()
        ts.FromDatetime(dt)
        return ts

    # =========================================================================
    # Document Query Methods (4 methods)
    # =========================================================================

    @grpc_retry
    async def get_document(self, document_id: str, collection_name: str) -> Document:
        """Get a single document by ID.

        Args:
            document_id: The document ID.
            collection_name: The collection to search in.

        Returns:
            The Document domain model.

        Raises:
            NotFoundError: If the document is not found.
            ServiceUnavailableError: If the service is unavailable.
        """
        stub = await self._get_stub(collection_pb2_grpc.CollectionServiceStub)
        request = collection_pb2.GetDocumentRequest(
            document_id=document_id,
            collection_name=collection_name,
        )

        try:
            response = await stub.GetDocument(request, metadata=self._get_metadata())
            return self._proto_to_document(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Document {document_id}")

    @grpc_retry
    async def list_documents(
        self,
        collection_name: str,
        page_size: int = 20,
        page_token: str | None = None,
        farmer_id: str | None = None,
    ) -> tuple[list[Document], str | None, int]:
        """List documents with pagination and optional farmer_id filter.

        Args:
            collection_name: The collection to search in.
            page_size: Maximum number of documents to return (max 100, default 20).
            page_token: Pagination cursor from previous response.
            farmer_id: Optional filter by farmer_id in linkage_fields.

        Returns:
            Tuple of (documents, next_page_token, total_count).
            next_page_token is None if no more pages.

        Raises:
            ServiceUnavailableError: If the service is unavailable.
        """
        stub = await self._get_stub(collection_pb2_grpc.CollectionServiceStub)
        request = collection_pb2.ListDocumentsRequest(
            collection_name=collection_name,
            page_size=min(page_size, 100),
            page_token=page_token or "",
            farmer_id=farmer_id or "",
        )

        try:
            response = await stub.ListDocuments(request, metadata=self._get_metadata())
            documents = [self._proto_to_document(doc) for doc in response.documents]
            next_token = response.next_page_token if response.next_page_token else None
            return documents, next_token, response.total_count
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "List documents")

    @grpc_retry
    async def get_documents_by_farmer(
        self,
        farmer_id: str,
        collection_name: str,
        limit: int = 100,
    ) -> tuple[list[Document], int]:
        """Get all documents for a specific farmer.

        Convenience method that returns all documents linked to a farmer.

        Args:
            farmer_id: The farmer ID to filter by.
            collection_name: The collection to search in.
            limit: Maximum number of documents to return (default 100).

        Returns:
            Tuple of (documents, total_count).

        Raises:
            ServiceUnavailableError: If the service is unavailable.
        """
        stub = await self._get_stub(collection_pb2_grpc.CollectionServiceStub)
        request = collection_pb2.GetDocumentsByFarmerRequest(
            farmer_id=farmer_id,
            collection_name=collection_name,
            limit=limit,
        )

        try:
            response = await stub.GetDocumentsByFarmer(request, metadata=self._get_metadata())
            documents = [self._proto_to_document(doc) for doc in response.documents]
            return documents, response.total_count
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Documents for farmer {farmer_id}")

    @grpc_retry
    async def search_documents(
        self,
        collection_name: str,
        source_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        linkage_filters: dict[str, str] | None = None,
        page_size: int = 20,
        page_token: str | None = None,
    ) -> tuple[list[Document], str | None, int]:
        """Search documents with filters.

        Args:
            collection_name: The collection to search in.
            source_id: Filter by source configuration ID.
            start_date: Filter by created_at >= start_date.
            end_date: Filter by created_at <= end_date.
            linkage_filters: Filter by linkage_fields (e.g., {"farmer_id": "WM-0001"}).
            page_size: Maximum number of documents to return (default 20).
            page_token: Pagination cursor from previous response.

        Returns:
            Tuple of (documents, next_page_token, total_count).
            next_page_token is None if no more pages.

        Raises:
            ServiceUnavailableError: If the service is unavailable.
        """
        stub = await self._get_stub(collection_pb2_grpc.CollectionServiceStub)

        request = collection_pb2.SearchDocumentsRequest(
            collection_name=collection_name,
            source_id=source_id or "",
            page_size=page_size,
            page_token=page_token or "",
        )

        # Set date filters if provided
        if start_date:
            request.start_date.CopyFrom(self._datetime_to_proto_timestamp(start_date))
        if end_date:
            request.end_date.CopyFrom(self._datetime_to_proto_timestamp(end_date))

        # Set linkage filters if provided
        if linkage_filters:
            for key, value in linkage_filters.items():
                request.linkage_filters[key] = value

        try:
            response = await stub.SearchDocuments(request, metadata=self._get_metadata())
            documents = [self._proto_to_document(doc) for doc in response.documents]
            next_token = response.next_page_token if response.next_page_token else None
            return documents, next_token, response.total_count
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Search documents")
