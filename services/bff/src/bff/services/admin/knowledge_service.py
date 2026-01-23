"""Knowledge Management service for admin API (Story 9.9a).

Orchestrates AiModelClient calls for knowledge document management.
"""

from collections.abc import AsyncIterator

from bff.api.schemas.admin.knowledge_schemas import (
    ALLOWED_FILE_TYPES,
    MAX_FILE_SIZE_BYTES,
    ChunkListResponse,
    DeleteDocumentResponse,
    DocumentDetail,
    DocumentListResponse,
    DocumentSummary,
    ExtractionJobStatus,
    QueryResponse,
    QueryResultItem,
    VectorizationJobStatus,
)
from bff.api.schemas.responses import PaginationMeta
from bff.infrastructure.clients.ai_model_client import AiModelClient
from bff.services.base_service import BaseService
from bff.transformers.admin.knowledge_transformer import KnowledgeTransformer
from fastapi import HTTPException, UploadFile
from fp_proto.ai_model.v1 import ai_model_pb2


class AdminKnowledgeService(BaseService):
    """Service for admin knowledge management operations.

    Orchestrates AiModelClient calls and transforms to API schemas.
    """

    def __init__(
        self,
        ai_model_client: AiModelClient | None = None,
        transformer: KnowledgeTransformer | None = None,
    ) -> None:
        super().__init__()
        self._client = ai_model_client or AiModelClient()
        self._transformer = transformer or KnowledgeTransformer()

    # =========================================================================
    # Document CRUD (AC 9.9a.1)
    # =========================================================================

    async def list_documents(
        self,
        domain: str | None = None,
        status: str | None = None,
        author: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> DocumentListResponse:
        """List knowledge documents with filtering and pagination."""
        self._logger.info(
            "listing_knowledge_documents",
            domain=domain,
            status=status,
            author=author,
            page=page,
            page_size=page_size,
        )

        response = await self._client.list_documents(
            domain=domain,
            status=status,
            author=author,
            page=page,
            page_size=page_size,
        )

        summaries = [self._transformer.to_summary(doc) for doc in response.documents]
        pagination = PaginationMeta.from_client_response(
            total_count=response.total_count,
            page_size=response.page_size,
            page=response.page,
        )

        return DocumentListResponse(data=summaries, pagination=pagination)

    async def search_documents(
        self,
        query: str,
        domain: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> list[DocumentSummary]:
        """Search documents by title and content."""
        self._logger.info("searching_knowledge_documents", query=query, domain=domain)

        response = await self._client.search_documents(
            query=query,
            domain=domain,
            status=status,
            limit=limit,
        )

        return [self._transformer.to_summary(doc) for doc in response.documents]

    async def get_document(
        self,
        document_id: str,
        version: int = 0,
    ) -> DocumentDetail:
        """Get document detail by ID, optionally a specific version."""
        self._logger.info("getting_knowledge_document", document_id=document_id, version=version)

        doc = await self._client.get_document(document_id=document_id, version=version)
        return self._transformer.to_detail(doc)

    async def create_document(
        self,
        title: str,
        domain: str,
        content: str = "",
        author: str = "",
        source: str = "",
        region: str = "",
        tags: list[str] | None = None,
    ) -> DocumentDetail:
        """Create a new knowledge document."""
        self._logger.info("creating_knowledge_document", title=title, domain=domain)

        metadata = ai_model_pb2.RAGDocumentMetadata(
            author=author,
            source=source,
            region=region,
            tags=tags or [],
        )

        response = await self._client.create_document(
            title=title,
            domain=domain,
            content=content,
            metadata=metadata,
        )

        return self._transformer.to_detail(response.document)

    async def update_document(
        self,
        document_id: str,
        title: str = "",
        content: str = "",
        author: str = "",
        source: str = "",
        region: str = "",
        tags: list[str] | None = None,
        change_summary: str = "",
    ) -> DocumentDetail:
        """Update document (creates new version)."""
        self._logger.info("updating_knowledge_document", document_id=document_id)

        metadata = ai_model_pb2.RAGDocumentMetadata(
            author=author,
            source=source,
            region=region,
            tags=tags or [],
        )

        doc = await self._client.update_document(
            document_id=document_id,
            title=title,
            content=content,
            metadata=metadata,
            change_summary=change_summary,
        )

        return self._transformer.to_detail(doc)

    async def delete_document(self, document_id: str) -> DeleteDocumentResponse:
        """Delete (archive) a document and all versions."""
        self._logger.info("deleting_knowledge_document", document_id=document_id)

        response = await self._client.delete_document(document_id=document_id)
        return DeleteDocumentResponse(versions_archived=response.versions_archived)

    # =========================================================================
    # Document Lifecycle (AC 9.9a.2)
    # =========================================================================

    async def stage_document(self, document_id: str, version: int = 0) -> DocumentDetail:
        """Transition document from draft to staged."""
        self._logger.info("staging_document", document_id=document_id, version=version)
        doc = await self._client.stage_document(document_id=document_id, version=version)
        return self._transformer.to_detail(doc)

    async def activate_document(self, document_id: str, version: int = 0) -> DocumentDetail:
        """Transition document from staged to active."""
        self._logger.info("activating_document", document_id=document_id, version=version)
        doc = await self._client.activate_document(document_id=document_id, version=version)
        return self._transformer.to_detail(doc)

    async def archive_document(self, document_id: str, version: int = 0) -> DocumentDetail:
        """Transition document to archived state."""
        self._logger.info("archiving_document", document_id=document_id, version=version)
        doc = await self._client.archive_document(document_id=document_id, version=version)
        return self._transformer.to_detail(doc)

    async def rollback_document(self, document_id: str, target_version: int) -> DocumentDetail:
        """Create new draft version from a previous version."""
        self._logger.info("rolling_back_document", document_id=document_id, target_version=target_version)
        doc = await self._client.rollback_document(document_id=document_id, target_version=target_version)
        return self._transformer.to_detail(doc)

    # =========================================================================
    # File Upload & Extraction (AC 9.9a.3, 9.9a.4)
    # =========================================================================

    async def upload_document(
        self,
        file: UploadFile,
        title: str,
        domain: str,
        author: str = "",
        source: str = "",
        region: str = "",
    ) -> ExtractionJobStatus:
        """Upload file, create document, and trigger extraction."""
        self._logger.info("uploading_knowledge_document", title=title, filename=file.filename)

        # Validate file type
        file_ext = (file.filename or "").rsplit(".", 1)[-1].lower() if file.filename else ""
        if file_ext not in ALLOWED_FILE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: '{file_ext}'. Allowed: {', '.join(sorted(ALLOWED_FILE_TYPES))}",
            )

        # Read and validate file size
        content_bytes = await file.read()
        if len(content_bytes) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"File size {len(content_bytes)} bytes exceeds max {MAX_FILE_SIZE_BYTES} bytes (50MB)",
            )

        # For text-based files, decode content directly
        file_content = ""
        if file_ext in {"md", "txt"}:
            file_content = content_bytes.decode("utf-8", errors="replace")

        # Build source file metadata
        source_file = ai_model_pb2.SourceFile(
            filename=file.filename or "unknown",
            file_type=file_ext,
            file_size_bytes=len(content_bytes),
        )

        # Build document metadata
        metadata = ai_model_pb2.RAGDocumentMetadata(
            author=author,
            source=source,
            region=region,
        )

        # Step 1: Create document
        create_response = await self._client.create_document(
            title=title,
            domain=domain,
            content=file_content,
            metadata=metadata,
            source_file=source_file,
        )

        created_doc = create_response.document

        # Step 2: Trigger extraction
        extract_response = await self._client.extract_document(
            document_id=created_doc.document_id,
            version=created_doc.version,
        )

        # Step 3: Get initial job status
        job_response = await self._client.get_extraction_job(job_id=extract_response.job_id)
        return self._transformer.to_extraction_status(job_response)

    async def get_extraction_job(self, job_id: str) -> ExtractionJobStatus:
        """Get extraction job status for polling."""
        self._logger.info("getting_extraction_job", job_id=job_id)
        job = await self._client.get_extraction_job(job_id=job_id)
        return self._transformer.to_extraction_status(job)

    async def stream_extraction_progress(
        self,
        document_id: str,
        job_id: str,
    ) -> AsyncIterator:
        """Get gRPC stream for extraction progress (for SSE adapter)."""
        self._logger.info("streaming_extraction_progress", document_id=document_id, job_id=job_id)
        return await self._client.stream_extraction_progress(job_id=job_id)

    # =========================================================================
    # Chunking & Vectorization (AC 9.9a.5)
    # =========================================================================

    async def list_chunks(
        self,
        document_id: str,
        version: int = 0,
        page: int = 1,
        page_size: int = 50,
    ) -> ChunkListResponse:
        """List chunks for a document with pagination."""
        self._logger.info("listing_chunks", document_id=document_id, version=version, page=page)

        response = await self._client.list_chunks(
            document_id=document_id,
            version=version,
            page=page,
            page_size=page_size,
        )

        chunks = [self._transformer.to_chunk_summary(chunk) for chunk in response.chunks]
        pagination = PaginationMeta.from_client_response(
            total_count=response.total_count,
            page_size=response.page_size,
            page=response.page,
        )

        return ChunkListResponse(data=chunks, pagination=pagination)

    async def vectorize_document(
        self,
        document_id: str,
        version: int = 0,
    ) -> VectorizationJobStatus:
        """Trigger document vectorization."""
        self._logger.info("vectorizing_document", document_id=document_id, version=version)

        response = await self._client.vectorize_document(
            document_id=document_id,
            version=version,
        )

        # VectorizeDocumentResponse has similar fields to VectorizationJobResponse
        return VectorizationJobStatus(
            job_id=response.job_id,
            status=response.status or "pending",
            document_id=document_id,
            document_version=version,
            namespace=response.namespace,
            chunks_total=response.chunks_total,
            chunks_embedded=response.chunks_embedded,
            chunks_stored=response.chunks_stored,
            failed_count=response.failed_count,
            content_hash=response.content_hash,
            error_message=response.error_message,
        )

    async def get_vectorization_job(self, job_id: str) -> VectorizationJobStatus:
        """Get vectorization job status for polling."""
        self._logger.info("getting_vectorization_job", job_id=job_id)
        job = await self._client.get_vectorization_job(job_id=job_id)
        return self._transformer.to_vectorization_status(job)

    # =========================================================================
    # Knowledge Query (AC 9.9a.6)
    # =========================================================================

    async def query_knowledge(
        self,
        query: str,
        domains: list[str] | None = None,
        top_k: int = 5,
        confidence_threshold: float = 0.0,
    ) -> QueryResponse:
        """Query knowledge base using existing AiModelClient method."""
        self._logger.info("querying_knowledge", query_length=len(query), domains=domains)

        result = await self._client.query_knowledge(
            query=query,
            domains=domains,
            top_k=top_k,
            confidence_threshold=confidence_threshold,
        )

        # RetrievalResult is already Pydantic model from fp-common
        matches = [
            QueryResultItem(
                chunk_id=match.chunk_id,
                content=match.content,
                score=match.score,
                document_id=match.document_id,
                title=match.title,
                domain=match.domain,
            )
            for match in result.matches
        ]

        return QueryResponse(
            matches=matches,
            query=result.query,
            total_matches=result.total_matches,
        )
