"""gRPC client for RAG Document operations.

This module provides the KnowledgeClient class for managing RAG documents
via the AI Model's RAGDocumentService gRPC API.

Uses DAPR sidecar for service discovery with dapr-app-id metadata header.
"""

from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import grpc
from fp_proto.ai_model.v1 import ai_model_pb2, ai_model_pb2_grpc

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
)
from fp_knowledge.settings import Environment, Settings


class KnowledgeClient:
    """Async gRPC client for RAG document operations.

    Provides thin wrapper calling RagDocumentService RPCs including:
    - CRUD operations (create, get, list, update)
    - Lifecycle management (stage, activate, archive, rollback)
    - Extraction and chunking operations with progress streaming
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
        """Connect to the gRPC service via DAPR sidecar."""
        endpoint = self._settings.get_grpc_endpoint(self._env)
        self._channel = grpc.aio.insecure_channel(endpoint)
        self._stub = ai_model_pb2_grpc.RAGDocumentServiceStub(self._channel)

    async def disconnect(self) -> None:
        """Disconnect from the gRPC service."""
        if self._channel:
            await self._channel.close()
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
        self, doc_input: RagDocumentInput
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

        return ai_model_pb2.CreateDocumentRequest(
            document_id=doc_input.document_id,
            title=doc_input.title,
            domain=doc_input.domain.value,
            content=doc_input.content or "",
            metadata=metadata,
        )

    async def create(self, doc_input: RagDocumentInput) -> RagDocument:
        """Create a new RAG document.

        Args:
            doc_input: Document input from YAML validation.

        Returns:
            The created RagDocument.
        """
        stub = self._ensure_connected()
        request = self._input_to_proto_request(doc_input)

        response = await stub.CreateDocument(
            request,
            metadata=self._get_metadata(),
            timeout=self._settings.grpc_timeout,
        )
        return self._proto_to_document(response.document)

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
