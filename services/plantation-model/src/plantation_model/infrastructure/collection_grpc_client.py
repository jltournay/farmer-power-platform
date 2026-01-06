"""Collection Model gRPC client for fetching documents.

Story 0.6.13: Replaces direct MongoDB access with gRPC via DAPR.
ADR-010/011: Inter-service communication via DAPR service invocation.

Uses same patterns as PlantationClient in plantation-mcp:
- Singleton channel pattern (lazy init, reuse, reset on error)
- Tenacity retry with exponential backoff
- Returns Pydantic models, not dicts
"""

import grpc
import structlog
from fp_common.converters import document_from_proto
from fp_common.models import Document
from fp_proto.collection.v1 import collection_pb2, collection_pb2_grpc
from plantation_model.config import settings
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)


class DocumentNotFoundError(Exception):
    """Raised when a document is not found in Collection Model."""

    def __init__(self, document_id: str) -> None:
        self.document_id = document_id
        super().__init__(f"Document not found: {document_id}")


class CollectionClientError(Exception):
    """Raised when a Collection Model client operation fails."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        self.cause = cause
        super().__init__(message)


class CollectionGrpcClient:
    """Client for Collection Model service via gRPC.

    Uses DAPR sidecar for service discovery when deployed.
    Follows singleton channel pattern (ADR-005) for connection reuse.

    Note:
        Returns Pydantic Document model, not dict.
        Call model.model_dump() at serialization boundary if needed.

    Example:
        client = CollectionGrpcClient()
        doc = await client.get_document("doc-123", "quality_documents")
        await client.close()
    """

    def __init__(self, channel: grpc.aio.Channel | None = None) -> None:
        """Initialize the client.

        Args:
            channel: Optional gRPC channel. If not provided, creates one to DAPR sidecar.
        """
        self._channel = channel
        self._stub: collection_pb2_grpc.CollectionServiceStub | None = None

    async def _get_stub(self) -> collection_pb2_grpc.CollectionServiceStub:
        """Get or create the gRPC stub (singleton pattern)."""
        if self._stub is None:
            if self._channel is None:
                if settings.collection_grpc_host:
                    # Direct connection to Collection Model gRPC server
                    target = settings.collection_grpc_host
                    logger.info("Connecting directly to Collection Model gRPC", target=target)
                else:
                    # Connect via DAPR sidecar (localhost:50001 is DAPR's gRPC port)
                    dapr_grpc_port = 50001
                    target = f"localhost:{dapr_grpc_port}"
                    logger.info(
                        "Connecting via DAPR service invocation",
                        target=target,
                        app_id=settings.collection_app_id,
                    )
                self._channel = grpc.aio.insecure_channel(target)
            self._stub = collection_pb2_grpc.CollectionServiceStub(self._channel)
        return self._stub

    def _get_metadata(self) -> list[tuple[str, str]]:
        """Get gRPC call metadata for DAPR service invocation."""
        if settings.collection_grpc_host:
            # Direct connection - no DAPR metadata needed
            return []
        # DAPR service invocation - add app-id metadata
        return [("dapr-app-id", settings.collection_app_id)]

    @retry(
        retry=retry_if_exception_type(grpc.aio.AioRpcError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def get_document(self, document_id: str, collection_name: str = "quality_documents") -> Document:
        """Get a document by ID from Collection Model.

        Args:
            document_id: The document's unique identifier.
            collection_name: Collection to search in (default: quality_documents).

        Returns:
            Document Pydantic model.

        Raises:
            DocumentNotFoundError: If document not found.
            CollectionClientError: If gRPC call fails after retries.
        """
        try:
            stub = await self._get_stub()
            request = collection_pb2.GetDocumentRequest(
                document_id=document_id,
                collection_name=collection_name,
            )

            logger.debug(
                "Fetching document from Collection Model via gRPC",
                document_id=document_id,
                collection_name=collection_name,
            )

            response = await stub.GetDocument(request, metadata=self._get_metadata())

            logger.info(
                "Document retrieved from Collection Model",
                document_id=document_id,
                source_id=response.ingestion.source_id,
            )

            return document_from_proto(response)

        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                logger.warning("Document not found in Collection Model", document_id=document_id)
                raise DocumentNotFoundError(document_id) from e
            logger.error(
                "gRPC call to Collection Model failed",
                document_id=document_id,
                status_code=e.code().name,
                details=e.details(),
            )
            # Reset stub to force reconnection on next call (ADR-005)
            self._stub = None
            self._channel = None
            raise CollectionClientError(f"Failed to fetch document {document_id}", cause=e) from e

    async def close(self) -> None:
        """Close the gRPC channel."""
        if self._channel:
            await self._channel.close()
            self._channel = None
            self._stub = None
            logger.info("Collection gRPC client connection closed")
