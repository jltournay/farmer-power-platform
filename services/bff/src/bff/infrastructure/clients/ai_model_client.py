"""AI Model gRPC client for BFF.

Story 0.75.23: RAG Query Service with BFF Integration
Story 9.9a: Knowledge Management BFF API - RAG Document CRUD, Lifecycle, Extraction, Chunking, Vectorization

This client provides typed access to the AI Model service via DAPR gRPC
service invocation. All methods return fp-common Pydantic domain models (NOT dicts)
or proto responses for the transformer layer.

Pattern follows:
- ADR-002 §"Service Invocation Pattern" (native gRPC with dapr-app-id metadata)
- ADR-005 for retry logic (3 attempts, exponential backoff 1-10s)

CRITICAL: Uses fp-common domain models for type safety. Never returns dict[str, Any].
"""

from collections.abc import AsyncIterator

import grpc
import grpc.aio
import structlog
from bff.infrastructure.clients.base import (
    BaseGrpcClient,
    grpc_retry,
)
from fp_common.converters import (
    retrieval_query_to_proto,
    retrieval_result_from_proto,
)
from fp_common.models import (
    RetrievalQuery,
    RetrievalResult,
)
from fp_proto.ai_model.v1 import ai_model_pb2, ai_model_pb2_grpc

logger = structlog.get_logger(__name__)


class AiModelClient(BaseGrpcClient):
    """Client for AI Model gRPC service via DAPR.

    Provides access to RAG query operations:

    Query Operations:
    - query_knowledge: Query knowledge base with natural language

    All methods return typed Pydantic models from fp-common.

    Example:
        >>> client = AiModelClient()
        >>> result = await client.query_knowledge(
        ...     query="What causes blister blight in tea?",
        ...     domains=["plant_diseases"],
        ...     top_k=5
        ... )
        >>> for match in result.matches:
        ...     print(f"{match.title}: {match.score:.2f}")
        Blister Blight Treatment Guide: 0.92
    """

    def __init__(
        self,
        dapr_grpc_port: int = 50001,
        direct_host: str | None = None,
        channel: grpc.aio.Channel | None = None,
    ) -> None:
        """Initialize the AI Model client.

        Args:
            dapr_grpc_port: Port for DAPR sidecar gRPC endpoint (default: 50001).
            direct_host: Optional direct host for testing (bypasses DAPR).
            channel: Optional pre-configured channel for testing.
        """
        super().__init__(
            target_app_id="ai-model",
            dapr_grpc_port=dapr_grpc_port,
            direct_host=direct_host,
            channel=channel,
        )

    async def _get_rag_stub(self) -> ai_model_pb2_grpc.RAGDocumentServiceStub:
        """Get the RAG Document service stub."""
        return await self._get_stub(ai_model_pb2_grpc.RAGDocumentServiceStub)

    # =========================================================================
    # Query Operations (Story 0.75.23)
    # =========================================================================

    @grpc_retry
    async def query_knowledge(
        self,
        query: str,
        domains: list[str] | None = None,
        top_k: int = 5,
        confidence_threshold: float = 0.0,
        namespace: str | None = None,
    ) -> RetrievalResult:
        """Query the RAG knowledge base with natural language.

        Performs semantic search against vectorized document chunks
        using Pinecone similarity search and returns ranked results.

        Args:
            query: Natural language query text.
            domains: Optional list of knowledge domains to filter.
                     Valid domains: plant_diseases, tea_cultivation,
                     weather_patterns, quality_standards, regional_context.
            top_k: Maximum number of results to return (default: 5, max: 100).
            confidence_threshold: Minimum similarity score (0-1) to include.
            namespace: Optional Pinecone namespace for version isolation.

        Returns:
            RetrievalResult with matches and metadata.

        Raises:
            ServiceUnavailableError: If service is unavailable.
            ValueError: If query is empty.

        Example:
            >>> result = await client.query_knowledge(
            ...     query="How to treat blister blight?",
            ...     domains=["plant_diseases"],
            ...     top_k=5,
            ...     confidence_threshold=0.7
            ... )
            >>> print(f"Found {result.count} matches")
            Found 3 matches
        """
        if not query or not query.strip():
            raise ValueError("query is required")

        try:
            stub = await self._get_rag_stub()

            # Build request using converter
            retrieval_query = RetrievalQuery(
                query=query,
                domains=domains or [],
                top_k=top_k,
                confidence_threshold=confidence_threshold,
                namespace=namespace,
            )
            request = retrieval_query_to_proto(retrieval_query)

            logger.debug(
                "Querying knowledge base",
                query_length=len(query),
                domains=domains,
                top_k=top_k,
                confidence_threshold=confidence_threshold,
                namespace=namespace,
            )

            response = await stub.QueryKnowledge(request, metadata=self._get_metadata())

            result = retrieval_result_from_proto(response)

            logger.debug(
                "Knowledge query completed",
                query_length=len(query),
                total_matches=result.total_matches,
                returned_matches=len(result.matches),
            )

            return result

        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Knowledge query")
            raise

    @grpc_retry
    async def query_knowledge_from_query(
        self,
        retrieval_query: RetrievalQuery,
    ) -> RetrievalResult:
        """Query knowledge base using a RetrievalQuery object.

        Convenience method that accepts a RetrievalQuery Pydantic model directly.

        Args:
            retrieval_query: RetrievalQuery with query parameters.

        Returns:
            RetrievalResult with matches and metadata.

        Raises:
            ServiceUnavailableError: If service is unavailable.
        """
        return await self.query_knowledge(
            query=retrieval_query.query,
            domains=retrieval_query.domains,
            top_k=retrieval_query.top_k,
            confidence_threshold=retrieval_query.confidence_threshold,
            namespace=retrieval_query.namespace,
        )

    # =========================================================================
    # Document CRUD Operations (Story 9.9a - Task 1.1)
    # =========================================================================

    @grpc_retry
    async def list_documents(
        self,
        domain: str | None = None,
        status: str | None = None,
        author: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> ai_model_pb2.ListDocumentsResponse:
        """List RAG documents with filtering and pagination."""
        try:
            stub = await self._get_rag_stub()
            request = ai_model_pb2.ListDocumentsRequest(
                page=page,
                page_size=page_size,
                domain=domain or "",
                status=status or "",
                author=author or "",
            )
            return await stub.ListDocuments(request, metadata=self._get_metadata())
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "List documents")
            raise

    @grpc_retry
    async def search_documents(
        self,
        query: str,
        domain: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> ai_model_pb2.SearchDocumentsResponse:
        """Search RAG documents by title and content."""
        try:
            stub = await self._get_rag_stub()
            request = ai_model_pb2.SearchDocumentsRequest(
                query=query,
                domain=domain or "",
                status=status or "",
                limit=limit,
            )
            return await stub.SearchDocuments(request, metadata=self._get_metadata())
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Search documents")
            raise

    @grpc_retry
    async def get_document(
        self,
        document_id: str,
        version: int = 0,
    ) -> ai_model_pb2.RAGDocument:
        """Get a RAG document by ID, optionally a specific version."""
        try:
            stub = await self._get_rag_stub()
            request = ai_model_pb2.GetDocumentRequest(
                document_id=document_id,
                version=version,
            )
            return await stub.GetDocument(request, metadata=self._get_metadata())
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Document {document_id}")
            raise

    @grpc_retry
    async def create_document(
        self,
        title: str,
        domain: str,
        content: str = "",
        metadata: ai_model_pb2.RAGDocumentMetadata | None = None,
        source_file: ai_model_pb2.SourceFile | None = None,
        document_id: str = "",
        file_content: bytes = b"",
    ) -> ai_model_pb2.CreateDocumentResponse:
        """Create a new RAG document."""
        try:
            stub = await self._get_rag_stub()
            request = ai_model_pb2.CreateDocumentRequest(
                document_id=document_id,
                title=title,
                domain=domain,
                content=content,
                file_content=file_content,
            )
            if metadata:
                request.metadata.CopyFrom(metadata)
            if source_file:
                request.source_file.CopyFrom(source_file)
            return await stub.CreateDocument(request, metadata=self._get_metadata())
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Create document")
            raise

    @grpc_retry
    async def update_document(
        self,
        document_id: str,
        title: str = "",
        content: str = "",
        metadata: ai_model_pb2.RAGDocumentMetadata | None = None,
        change_summary: str = "",
    ) -> ai_model_pb2.RAGDocument:
        """Update a RAG document (creates new version)."""
        try:
            stub = await self._get_rag_stub()
            request = ai_model_pb2.UpdateDocumentRequest(
                document_id=document_id,
                title=title,
                content=content,
                change_summary=change_summary,
            )
            if metadata:
                request.metadata.CopyFrom(metadata)
            return await stub.UpdateDocument(request, metadata=self._get_metadata())
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Update document {document_id}")
            raise

    @grpc_retry
    async def delete_document(
        self,
        document_id: str,
    ) -> ai_model_pb2.DeleteDocumentResponse:
        """Delete (archive) a RAG document and all versions."""
        try:
            stub = await self._get_rag_stub()
            request = ai_model_pb2.DeleteDocumentRequest(document_id=document_id)
            return await stub.DeleteDocument(request, metadata=self._get_metadata())
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Delete document {document_id}")
            raise

    # =========================================================================
    # Document Lifecycle Operations (Story 9.9a - Task 1.2)
    # =========================================================================

    @grpc_retry
    async def stage_document(
        self,
        document_id: str,
        version: int = 0,
    ) -> ai_model_pb2.RAGDocument:
        """Transition document from draft to staged."""
        try:
            stub = await self._get_rag_stub()
            request = ai_model_pb2.StageDocumentRequest(
                document_id=document_id,
                version=version,
            )
            return await stub.StageDocument(request, metadata=self._get_metadata())
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Stage document {document_id}")
            raise

    @grpc_retry
    async def activate_document(
        self,
        document_id: str,
        version: int = 0,
    ) -> ai_model_pb2.RAGDocument:
        """Transition document from staged to active."""
        try:
            stub = await self._get_rag_stub()
            request = ai_model_pb2.ActivateDocumentRequest(
                document_id=document_id,
                version=version,
            )
            return await stub.ActivateDocument(request, metadata=self._get_metadata())
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Activate document {document_id}")
            raise

    @grpc_retry
    async def archive_document(
        self,
        document_id: str,
        version: int = 0,
    ) -> ai_model_pb2.RAGDocument:
        """Transition document to archived state."""
        try:
            stub = await self._get_rag_stub()
            request = ai_model_pb2.ArchiveDocumentRequest(
                document_id=document_id,
                version=version,
            )
            return await stub.ArchiveDocument(request, metadata=self._get_metadata())
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Archive document {document_id}")
            raise

    @grpc_retry
    async def rollback_document(
        self,
        document_id: str,
        target_version: int,
    ) -> ai_model_pb2.RAGDocument:
        """Create new draft version from a previous version."""
        try:
            stub = await self._get_rag_stub()
            request = ai_model_pb2.RollbackDocumentRequest(
                document_id=document_id,
                target_version=target_version,
            )
            return await stub.RollbackDocument(request, metadata=self._get_metadata())
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Rollback document {document_id}")
            raise

    # =========================================================================
    # Extraction Operations (Story 9.9a - Task 1.3)
    # =========================================================================

    @grpc_retry
    async def extract_document(
        self,
        document_id: str,
        version: int = 0,
    ) -> ai_model_pb2.ExtractDocumentResponse:
        """Trigger document content extraction."""
        try:
            stub = await self._get_rag_stub()
            request = ai_model_pb2.ExtractDocumentRequest(
                document_id=document_id,
                version=version,
            )
            return await stub.ExtractDocument(request, metadata=self._get_metadata())
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Extract document {document_id}")
            raise

    @grpc_retry
    async def get_extraction_job(
        self,
        job_id: str,
    ) -> ai_model_pb2.ExtractionJobResponse:
        """Get extraction job status."""
        try:
            stub = await self._get_rag_stub()
            request = ai_model_pb2.GetExtractionJobRequest(job_id=job_id)
            return await stub.GetExtractionJob(request, metadata=self._get_metadata())
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Extraction job {job_id}")
            raise

    async def stream_extraction_progress(
        self,
        job_id: str,
    ) -> AsyncIterator[ai_model_pb2.ExtractionProgressEvent]:
        """Stream extraction progress events (server-streaming RPC).

        Note: No @grpc_retry - streaming RPCs handle their own lifecycle.
        """
        try:
            stub = await self._get_rag_stub()
            request = ai_model_pb2.StreamExtractionProgressRequest(job_id=job_id)
            return stub.StreamExtractionProgress(request, metadata=self._get_metadata())
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Stream extraction progress {job_id}")
            raise

    # =========================================================================
    # Chunking Operations (Story 9.9a - Task 1.4)
    # =========================================================================

    @grpc_retry
    async def list_chunks(
        self,
        document_id: str,
        version: int = 0,
        page: int = 1,
        page_size: int = 50,
    ) -> ai_model_pb2.ListChunksResponse:
        """List chunks for a document version with pagination."""
        try:
            stub = await self._get_rag_stub()
            request = ai_model_pb2.ListChunksRequest(
                document_id=document_id,
                version=version,
                page=page,
                page_size=page_size,
            )
            return await stub.ListChunks(request, metadata=self._get_metadata())
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"List chunks for {document_id}")
            raise

    # =========================================================================
    # Chunking Operations
    # =========================================================================

    @grpc_retry
    async def chunk_document(
        self,
        document_id: str,
        version: int = 0,
    ) -> ai_model_pb2.ChunkDocumentResponse:
        """Trigger document chunking (synchronous)."""
        try:
            stub = await self._get_rag_stub()
            request = ai_model_pb2.ChunkDocumentRequest(
                document_id=document_id,
                version=version,
            )
            return await stub.ChunkDocument(request, metadata=self._get_metadata())
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Chunk document {document_id}")
            raise

    # =========================================================================
    # Vectorization Operations (Story 9.9a - Task 1.5)
    # =========================================================================

    @grpc_retry
    async def vectorize_document(
        self,
        document_id: str,
        version: int = 0,
    ) -> ai_model_pb2.VectorizeDocumentResponse:
        """Trigger document vectorization (async mode)."""
        try:
            stub = await self._get_rag_stub()
            request = ai_model_pb2.VectorizeDocumentRequest(
                document_id=document_id,
                version=version,
            )
            # Field name is 'async' in proto but Python reserved word
            # Set via setattr
            setattr(request, "async", True)
            return await stub.VectorizeDocument(request, metadata=self._get_metadata())
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Vectorize document {document_id}")
            raise

    @grpc_retry
    async def get_vectorization_job(
        self,
        job_id: str,
    ) -> ai_model_pb2.VectorizationJobResponse:
        """Get vectorization job status."""
        try:
            stub = await self._get_rag_stub()
            request = ai_model_pb2.GetVectorizationJobRequest(job_id=job_id)
            return await stub.GetVectorizationJob(request, metadata=self._get_metadata())
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Vectorization job {job_id}")
            raise
