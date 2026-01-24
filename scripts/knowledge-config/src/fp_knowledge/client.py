"""gRPC client for RAG Document operations.

This module provides the KnowledgeClient class for managing RAG documents
via the AI Model's RAGDocumentService gRPC API.

Uses DAPR sidecar for service discovery with dapr-app-id metadata header.
Implements retry logic per ADR-005 for resilient gRPC communication.
"""

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from pathlib import Path

import grpc
from fp_proto.ai_model.v1 import ai_model_pb2, ai_model_pb2_grpc
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from fp_knowledge.models import (
    ChunkResult,
    DocumentMetadata,
    DocumentStatus,
    ExtractionJobResult,
    JobStatus,
    RagChunk,
    RagDocument,
    RagDocumentInput,
    SourceFileInfo,
    VectorizationJobResult,
    VectorizationJobStatus,
    VectorizationResult,
)
from fp_knowledge.settings import Environment, Settings


def _grpc_retry():
    """Create retry decorator for gRPC operations per ADR-005.

    Retries on transient gRPC errors with exponential backoff.
    """
    return retry(
        retry=retry_if_exception_type(grpc.aio.AioRpcError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )


class KnowledgeClient:
    """Async gRPC client for RAG document operations.

    Provides thin wrapper calling RagDocumentService RPCs including:
    - CRUD operations (create, get, list, update)
    - Lifecycle management (stage, activate, archive, rollback)
    - Extraction and chunking operations with progress streaming

    Implements retry logic per ADR-005 for resilient gRPC communication.
    """

    def __init__(self, settings: Settings, env: Environment) -> None:
        """Initialize the knowledge client.

        Args:
            settings: Application settings.
            env: Target environment (dev, staging, prod).
        """
        self._settings = settings
        self._env = env
        self._channel: grpc.aio.Channel | None = None
        self._stub: ai_model_pb2_grpc.RAGDocumentServiceStub | None = None

    async def connect(self) -> None:
        """Connect to the gRPC service via DAPR sidecar.

        Configures channel with keepalive per ADR-005:
        - Keepalive interval: 30 seconds
        - Keepalive timeout: 10 seconds
        """
        endpoint = self._settings.get_grpc_endpoint(self._env)

        # Channel options with keepalive per ADR-005 and message size for file uploads
        options = [
            ("grpc.max_send_message_length", 50 * 1024 * 1024),  # 50MB
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),  # 50MB
            ("grpc.keepalive_time_ms", 30000),  # 30 second interval
            ("grpc.keepalive_timeout_ms", 10000),  # 10 second timeout
            ("grpc.keepalive_permit_without_calls", True),
            ("grpc.http2.min_time_between_pings_ms", 30000),
        ]

        self._channel = grpc.aio.insecure_channel(endpoint, options=options)
        self._stub = ai_model_pb2_grpc.RAGDocumentServiceStub(self._channel)

    async def disconnect(self) -> None:
        """Disconnect from the gRPC service."""
        if self._channel:
            await self._channel.close()
            self._channel = None
            self._stub = None

    async def _reset_on_error(self) -> None:
        """Reset channel and stub on error to force reconnection per ADR-005."""
        if self._channel:
            try:
                await self._channel.close()
            except Exception:
                pass  # Ignore errors during cleanup
        self._channel = None
        self._stub = None

    def _get_metadata(self) -> list[tuple[str, str]]:
        """Get gRPC metadata including DAPR app-id header."""
        return [("dapr-app-id", self._settings.dapr_app_id)]

    def _ensure_connected(self) -> ai_model_pb2_grpc.RAGDocumentServiceStub:
        """Ensure client is connected and return stub."""
        if self._stub is None:
            raise RuntimeError("Client not connected. Call connect() first.")
        return self._stub

    def _proto_to_document(self, proto: ai_model_pb2.RAGDocument) -> RagDocument:
        """Convert protobuf RAGDocument to Pydantic RagDocument model."""
        # Convert metadata
        metadata = DocumentMetadata(
            author=proto.metadata.author,
            source=proto.metadata.source or None,
            region=proto.metadata.region or None,
            season=proto.metadata.season or None,
            tags=list(proto.metadata.tags),
        )

        # Convert source file if present
        source_file = None
        if proto.source_file.filename:
            source_file = SourceFileInfo(
                filename=proto.source_file.filename,
                file_type=proto.source_file.file_type,
                blob_path=proto.source_file.blob_path or None,
                file_size_bytes=proto.source_file.file_size_bytes or None,
                extraction_method=proto.source_file.extraction_method or None,
                extraction_confidence=proto.source_file.extraction_confidence or None,
                page_count=proto.source_file.page_count or None,
            )

        # Convert timestamps
        created_at = None
        if proto.created_at.seconds:
            created_at = datetime.fromtimestamp(
                proto.created_at.seconds + proto.created_at.nanos / 1e9,
                tz=timezone.utc,
            )

        updated_at = None
        if proto.updated_at.seconds:
            updated_at = datetime.fromtimestamp(
                proto.updated_at.seconds + proto.updated_at.nanos / 1e9,
                tz=timezone.utc,
            )

        return RagDocument(
            id=proto.id,
            document_id=proto.document_id,
            version=proto.version,
            title=proto.title,
            domain=proto.domain,
            content=proto.content,
            status=DocumentStatus(proto.status),
            metadata=metadata,
            source_file=source_file,
            change_summary=proto.change_summary or None,
            created_at=created_at,
            updated_at=updated_at,
            content_hash=proto.content_hash or None,
        )

    def _input_to_proto_request(
        self, doc_input: RagDocumentInput, base_dir: Path | None = None
    ) -> ai_model_pb2.CreateDocumentRequest:
        """Convert RagDocumentInput to CreateDocumentRequest protobuf."""
        # Build metadata proto
        metadata = ai_model_pb2.RAGDocumentMetadata(
            author=doc_input.metadata.author,
            source=doc_input.metadata.source or "",
            region=doc_input.metadata.region or "",
            season=doc_input.metadata.season or "",
            tags=doc_input.metadata.tags,
        )

        # Read file bytes and build source_file if file path is specified
        file_content = b""
        source_file = None
        if doc_input.file:
            resolve_dir = base_dir or Path.cwd()
            file_path = resolve_dir / doc_input.file
            file_content = file_path.read_bytes()
            file_ext = file_path.suffix.lstrip(".").lower()
            source_file = ai_model_pb2.SourceFile(
                filename=file_path.name,
                file_type=file_ext,
                file_size_bytes=len(file_content),
            )

        request = ai_model_pb2.CreateDocumentRequest(
            document_id=doc_input.document_id,
            title=doc_input.title,
            domain=doc_input.domain.value,
            content=doc_input.content or "",
            metadata=metadata,
            file_content=file_content,
        )
        if source_file:
            request.source_file.CopyFrom(source_file)
        return request

    @_grpc_retry()
    async def create(
        self, doc_input: RagDocumentInput, base_dir: Path | None = None
    ) -> RagDocument:
        """Create a new RAG document.

        Args:
            doc_input: Document input from YAML validation.
            base_dir: Base directory for resolving relative file paths.

        Returns:
            The created RagDocument.
        """
        stub = self._ensure_connected()
        request = self._input_to_proto_request(doc_input, base_dir=base_dir)

        response = await stub.CreateDocument(
            request,
            metadata=self._get_metadata(),
            timeout=self._settings.grpc_timeout,
        )
        return self._proto_to_document(response.document)

    @_grpc_retry()
    async def get_by_id(self, document_id: str) -> RagDocument | None:
        """Get active version of a document by document_id.

        Args:
            document_id: The logical document identifier.

        Returns:
            The active document if found, None otherwise.
        """
        stub = self._ensure_connected()
        request = ai_model_pb2.GetDocumentRequest(
            document_id=document_id,
            version=0,  # 0 = active version
        )

        try:
            response = await stub.GetDocument(
                request,
                metadata=self._get_metadata(),
                timeout=self._settings.grpc_timeout,
            )
            return self._proto_to_document(response)
        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                return None
            raise

    @_grpc_retry()
    async def get_by_version(
        self, document_id: str, version: int
    ) -> RagDocument | None:
        """Get a specific version of a document.

        Args:
            document_id: The logical document identifier.
            version: The version number.

        Returns:
            The document if found, None otherwise.
        """
        stub = self._ensure_connected()
        request = ai_model_pb2.GetDocumentRequest(
            document_id=document_id,
            version=version,
        )

        try:
            response = await stub.GetDocument(
                request,
                metadata=self._get_metadata(),
                timeout=self._settings.grpc_timeout,
            )
            return self._proto_to_document(response)
        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                return None
            raise

    @_grpc_retry()
    async def list_documents(
        self,
        domain: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[RagDocument], int]:
        """List documents with optional filtering.

        Args:
            domain: Optional domain filter.
            status: Optional status filter.
            page: Page number (1-indexed).
            page_size: Number of results per page.

        Returns:
            Tuple of (documents list, total count).
        """
        stub = self._ensure_connected()
        request = ai_model_pb2.ListDocumentsRequest(
            page=page,
            page_size=page_size,
            domain=domain or "",
            status=status or "",
        )

        response = await stub.ListDocuments(
            request,
            metadata=self._get_metadata(),
            timeout=self._settings.grpc_timeout,
        )

        documents = [self._proto_to_document(doc) for doc in response.documents]
        return documents, response.total_count

    @_grpc_retry()
    async def list_versions(self, document_id: str) -> list[RagDocument]:
        """List all versions of a document.

        Args:
            document_id: The logical document identifier.

        Returns:
            List of document versions, sorted by version descending.
        """
        # Use list with document_id filter to get all versions
        stub = self._ensure_connected()
        request = ai_model_pb2.ListDocumentsRequest(
            page=1,
            page_size=100,  # Get all versions
        )

        response = await stub.ListDocuments(
            request,
            metadata=self._get_metadata(),
            timeout=self._settings.grpc_timeout,
        )

        # Filter by document_id and sort by version descending
        versions = [
            self._proto_to_document(doc)
            for doc in response.documents
            if doc.document_id == document_id
        ]
        versions.sort(key=lambda d: d.version, reverse=True)
        return versions

    @_grpc_retry()
    async def stage(self, document_id: str, version: int) -> RagDocument:
        """Stage a document version for review.

        Args:
            document_id: The document identifier.
            version: The version to stage.

        Returns:
            The staged document.
        """
        stub = self._ensure_connected()
        request = ai_model_pb2.StageDocumentRequest(
            document_id=document_id,
            version=version,
        )

        response = await stub.StageDocument(
            request,
            metadata=self._get_metadata(),
            timeout=self._settings.grpc_timeout,
        )
        return self._proto_to_document(response)

    @_grpc_retry()
    async def activate(self, document_id: str, version: int) -> RagDocument:
        """Activate (promote) a staged document version.

        Args:
            document_id: The document identifier.
            version: The version to activate.

        Returns:
            The activated document.
        """
        stub = self._ensure_connected()
        request = ai_model_pb2.ActivateDocumentRequest(
            document_id=document_id,
            version=version,
        )

        response = await stub.ActivateDocument(
            request,
            metadata=self._get_metadata(),
            timeout=self._settings.grpc_timeout,
        )
        return self._proto_to_document(response)

    @_grpc_retry()
    async def archive(
        self, document_id: str, version: int | None = None
    ) -> RagDocument:
        """Archive a document version.

        Args:
            document_id: The document identifier.
            version: The version to archive (0 = all versions).

        Returns:
            The archived document.
        """
        stub = self._ensure_connected()
        request = ai_model_pb2.ArchiveDocumentRequest(
            document_id=document_id,
            version=version or 0,
        )

        response = await stub.ArchiveDocument(
            request,
            metadata=self._get_metadata(),
            timeout=self._settings.grpc_timeout,
        )
        return self._proto_to_document(response)

    @_grpc_retry()
    async def rollback(self, document_id: str, target_version: int) -> RagDocument:
        """Rollback to a previous document version.

        Creates a new draft version with content from target_version.

        Args:
            document_id: The document identifier.
            target_version: The version to rollback to.

        Returns:
            The new draft document created from rollback.
        """
        stub = self._ensure_connected()
        request = ai_model_pb2.RollbackDocumentRequest(
            document_id=document_id,
            target_version=target_version,
        )

        response = await stub.RollbackDocument(
            request,
            metadata=self._get_metadata(),
            timeout=self._settings.grpc_timeout,
        )
        return self._proto_to_document(response)

    @_grpc_retry()
    async def extract(self, document_id: str, version: int = 0) -> str:
        """Start content extraction for a document.

        Triggers async extraction job for PDF/document processing.

        Args:
            document_id: The document identifier.
            version: The version to extract (0 = latest).

        Returns:
            The extraction job ID.
        """
        stub = self._ensure_connected()
        request = ai_model_pb2.ExtractDocumentRequest(
            document_id=document_id,
            version=version,
        )

        response = await stub.ExtractDocument(
            request,
            metadata=self._get_metadata(),
            timeout=self._settings.grpc_timeout,
        )
        return response.job_id

    @_grpc_retry()
    async def get_job_status(self, job_id: str) -> ExtractionJobResult:
        """Get extraction job status (polling mode).

        Args:
            job_id: The job identifier.

        Returns:
            ExtractionJobResult with current status.
        """
        stub = self._ensure_connected()
        request = ai_model_pb2.GetExtractionJobRequest(job_id=job_id)

        response = await stub.GetExtractionJob(
            request,
            metadata=self._get_metadata(),
            timeout=self._settings.grpc_timeout,
        )

        # Convert timestamps
        started_at = None
        if response.started_at.seconds:
            started_at = datetime.fromtimestamp(
                response.started_at.seconds + response.started_at.nanos / 1e9,
                tz=timezone.utc,
            )

        completed_at = None
        if response.completed_at.seconds:
            completed_at = datetime.fromtimestamp(
                response.completed_at.seconds + response.completed_at.nanos / 1e9,
                tz=timezone.utc,
            )

        return ExtractionJobResult(
            job_id=response.job_id,
            document_id=response.document_id,
            status=JobStatus(response.status),
            progress_percent=response.progress_percent,
            pages_processed=response.pages_processed,
            total_pages=response.total_pages,
            error_message=response.error_message or None,
            started_at=started_at,
            completed_at=completed_at,
        )

    async def stream_progress(
        self, job_id: str
    ) -> AsyncGenerator[ExtractionJobResult, None]:
        """Stream extraction progress events (streaming mode).

        Yields progress events until job completes or fails.

        Args:
            job_id: The job identifier.

        Yields:
            ExtractionJobResult with current progress.
        """
        stub = self._ensure_connected()
        request = ai_model_pb2.StreamExtractionProgressRequest(job_id=job_id)

        async for event in stub.StreamExtractionProgress(
            request,
            metadata=self._get_metadata(),
        ):
            result = ExtractionJobResult(
                job_id=event.job_id,
                document_id="",  # Not in streaming event
                status=JobStatus(event.status),
                progress_percent=event.progress_percent,
                pages_processed=event.pages_processed,
                total_pages=event.total_pages,
                error_message=event.error_message or None,
            )
            yield result

            # Stop on terminal states
            if event.status in ("completed", "failed"):
                break

    @_grpc_retry()
    async def chunk(self, document_id: str, version: int = 0) -> ChunkResult:
        """Chunk a document for vectorization (synchronous).

        Args:
            document_id: The document identifier.
            version: The version to chunk (0 = latest).

        Returns:
            ChunkResult with chunking statistics.
        """
        stub = self._ensure_connected()
        request = ai_model_pb2.ChunkDocumentRequest(
            document_id=document_id,
            version=version,
        )

        response = await stub.ChunkDocument(
            request,
            metadata=self._get_metadata(),
            timeout=self._settings.grpc_timeout,
        )

        return ChunkResult(
            chunks_created=response.chunks_created,
            total_char_count=response.total_char_count,
            total_word_count=response.total_word_count,
        )

    @_grpc_retry()
    async def list_chunks(
        self,
        document_id: str,
        version: int,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[RagChunk], int]:
        """List chunks for a document version.

        Args:
            document_id: The document identifier.
            version: The document version.
            page: Page number (1-indexed).
            page_size: Number of results per page.

        Returns:
            Tuple of (chunks list, total count).
        """
        stub = self._ensure_connected()
        request = ai_model_pb2.ListChunksRequest(
            document_id=document_id,
            version=version,
            page=page,
            page_size=page_size,
        )

        response = await stub.ListChunks(
            request,
            metadata=self._get_metadata(),
            timeout=self._settings.grpc_timeout,
        )

        chunks = []
        for chunk_proto in response.chunks:
            created_at = None
            if chunk_proto.created_at.seconds:
                created_at = datetime.fromtimestamp(
                    chunk_proto.created_at.seconds + chunk_proto.created_at.nanos / 1e9,
                    tz=timezone.utc,
                )

            chunks.append(
                RagChunk(
                    chunk_id=chunk_proto.chunk_id,
                    document_id=chunk_proto.document_id,
                    document_version=chunk_proto.document_version,
                    chunk_index=chunk_proto.chunk_index,
                    content=chunk_proto.content,
                    section_title=chunk_proto.section_title or None,
                    word_count=chunk_proto.word_count,
                    char_count=chunk_proto.char_count,
                    created_at=created_at,
                    pinecone_id=chunk_proto.pinecone_id or None,
                )
            )

        return chunks, response.total_count

    @_grpc_retry()
    async def get_chunk(self, chunk_id: str) -> RagChunk | None:
        """Get a specific chunk by ID.

        Args:
            chunk_id: The chunk identifier.

        Returns:
            The chunk if found, None otherwise.
        """
        stub = self._ensure_connected()
        request = ai_model_pb2.GetChunkRequest(chunk_id=chunk_id)

        try:
            chunk_proto = await stub.GetChunk(
                request,
                metadata=self._get_metadata(),
                timeout=self._settings.grpc_timeout,
            )

            created_at = None
            if chunk_proto.created_at.seconds:
                created_at = datetime.fromtimestamp(
                    chunk_proto.created_at.seconds + chunk_proto.created_at.nanos / 1e9,
                    tz=timezone.utc,
                )

            return RagChunk(
                chunk_id=chunk_proto.chunk_id,
                document_id=chunk_proto.document_id,
                document_version=chunk_proto.document_version,
                chunk_index=chunk_proto.chunk_index,
                content=chunk_proto.content,
                section_title=chunk_proto.section_title or None,
                word_count=chunk_proto.word_count,
                char_count=chunk_proto.char_count,
                created_at=created_at,
                pinecone_id=chunk_proto.pinecone_id or None,
            )
        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                return None
            raise

    @_grpc_retry()
    async def delete_chunks(self, document_id: str, version: int) -> int:
        """Delete all chunks for a document version.

        Args:
            document_id: The document identifier.
            version: The document version.

        Returns:
            Number of chunks deleted.
        """
        stub = self._ensure_connected()
        request = ai_model_pb2.DeleteChunksRequest(
            document_id=document_id,
            version=version,
        )

        response = await stub.DeleteChunks(
            request,
            metadata=self._get_metadata(),
            timeout=self._settings.grpc_timeout,
        )
        return response.chunks_deleted

    # ========================================
    # Vectorization Operations (Story 0.75.13c)
    # ========================================

    @_grpc_retry()
    async def vectorize(
        self,
        document_id: str,
        version: int = 0,
        async_mode: bool = False,
    ) -> VectorizationResult:
        """Vectorize a document by generating embeddings and storing in Pinecone.

        Args:
            document_id: The document identifier.
            version: The version to vectorize (0 = latest active/staged).
            async_mode: If True, returns immediately with job_id for polling.

        Returns:
            VectorizationResult with job status and statistics.
        """
        stub = self._ensure_connected()
        # Note: async_ is a reserved word in protobuf Python generation
        # The field is accessed via async_ in the generated code
        request = ai_model_pb2.VectorizeDocumentRequest(
            document_id=document_id,
            version=version,
        )
        # Set async field via setattr to handle reserved word
        setattr(request, "async", async_mode)

        response = await stub.VectorizeDocument(
            request,
            metadata=self._get_metadata(),
            timeout=self._settings.grpc_timeout * 3,  # Longer timeout for vectorization
        )

        return VectorizationResult(
            job_id=response.job_id,
            status=VectorizationJobStatus(response.status),
            namespace=response.namespace or None,
            chunks_total=response.chunks_total,
            chunks_embedded=response.chunks_embedded,
            chunks_stored=response.chunks_stored,
            failed_count=response.failed_count,
            content_hash=response.content_hash or None,
            error_message=response.error_message or None,
        )

    @_grpc_retry()
    async def get_vectorization_job_status(
        self, job_id: str
    ) -> VectorizationJobResult | None:
        """Get vectorization job status.

        Args:
            job_id: The job identifier.

        Returns:
            VectorizationJobResult with current status, or None if not found.
        """
        stub = self._ensure_connected()
        request = ai_model_pb2.GetVectorizationJobRequest(job_id=job_id)

        try:
            response = await stub.GetVectorizationJob(
                request,
                metadata=self._get_metadata(),
                timeout=self._settings.grpc_timeout,
            )
        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                return None
            raise

        # Convert timestamps
        started_at = None
        if response.started_at.seconds:
            started_at = datetime.fromtimestamp(
                response.started_at.seconds + response.started_at.nanos / 1e9,
                tz=timezone.utc,
            )

        completed_at = None
        if response.completed_at.seconds:
            completed_at = datetime.fromtimestamp(
                response.completed_at.seconds + response.completed_at.nanos / 1e9,
                tz=timezone.utc,
            )

        return VectorizationJobResult(
            job_id=response.job_id,
            status=VectorizationJobStatus(response.status),
            document_id=response.document_id,
            document_version=response.document_version,
            namespace=response.namespace or None,
            chunks_total=response.chunks_total,
            chunks_embedded=response.chunks_embedded,
            chunks_stored=response.chunks_stored,
            failed_count=response.failed_count,
            content_hash=response.content_hash or None,
            error_message=response.error_message or None,
            started_at=started_at,
            completed_at=completed_at,
        )
