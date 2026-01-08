"""gRPC RAGDocumentService implementation.

This module implements the RAGDocumentService gRPC API for RAG document management.
Documents are versioned with lifecycle status: draft → staged → active → archived.

Story 0.75.10: gRPC Model for RAG Document
Story 0.75.13c: Added VectorizeDocument and GetVectorizationJob RPCs
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import grpc
import structlog
from ai_model.domain.exceptions import (
    DocumentNotFoundError,
    InvalidDocumentStatusError,
)
from ai_model.domain.rag_document import (
    ExtractionMethod,
    FileType,
    KnowledgeDomain,
    RagDocument,
    RAGDocumentMetadata,
    RagDocumentStatus,
    SourceFile,
)
from ai_model.infrastructure.repositories import RagDocumentRepository
from fp_proto.ai_model.v1 import ai_model_pb2, ai_model_pb2_grpc
from google.protobuf import timestamp_pb2

# Lazy import type for VectorizationPipeline to avoid circular imports
if TYPE_CHECKING:
    from ai_model.services.vectorization_pipeline import VectorizationPipeline

logger = structlog.get_logger(__name__)

# Pagination defaults
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def _datetime_to_timestamp(dt: datetime) -> timestamp_pb2.Timestamp:
    """Convert datetime to protobuf Timestamp."""
    ts = timestamp_pb2.Timestamp()
    ts.FromDatetime(dt)
    return ts


def _pydantic_to_proto(doc: RagDocument) -> ai_model_pb2.RAGDocument:
    """Convert Pydantic RagDocument to Proto RAGDocument."""
    proto_doc = ai_model_pb2.RAGDocument(
        id=doc.id,
        document_id=doc.document_id,
        version=doc.version,
        title=doc.title,
        domain=doc.domain.value,
        content=doc.content,
        status=doc.status.value,
        change_summary=doc.change_summary or "",
        pinecone_namespace=doc.pinecone_namespace or "",
        pinecone_ids=list(doc.pinecone_ids),
        content_hash=doc.content_hash or "",
    )

    # Set timestamps
    proto_doc.created_at.FromDatetime(doc.created_at)
    proto_doc.updated_at.FromDatetime(doc.updated_at)

    # Set metadata
    proto_doc.metadata.CopyFrom(
        ai_model_pb2.RAGDocumentMetadata(
            author=doc.metadata.author,
            source=doc.metadata.source or "",
            region=doc.metadata.region or "",
            season=doc.metadata.season or "",
            tags=list(doc.metadata.tags),
        )
    )

    # Set source file if present
    if doc.source_file:
        proto_doc.source_file.CopyFrom(
            ai_model_pb2.SourceFile(
                filename=doc.source_file.filename,
                file_type=doc.source_file.file_type.value,
                blob_path=doc.source_file.blob_path,
                file_size_bytes=doc.source_file.file_size_bytes,
                extraction_method=doc.source_file.extraction_method.value if doc.source_file.extraction_method else "",
                extraction_confidence=doc.source_file.extraction_confidence or 0.0,
                page_count=doc.source_file.page_count or 0,
            )
        )

    return proto_doc


def _proto_metadata_to_pydantic(
    metadata: ai_model_pb2.RAGDocumentMetadata,
) -> RAGDocumentMetadata:
    """Convert Proto RAGDocumentMetadata to Pydantic."""
    return RAGDocumentMetadata(
        author=metadata.author,
        source=metadata.source if metadata.source else None,
        region=metadata.region if metadata.region else None,
        season=metadata.season if metadata.season else None,
        tags=list(metadata.tags),
    )


def _proto_source_file_to_pydantic(
    source_file: ai_model_pb2.SourceFile,
) -> SourceFile | None:
    """Convert Proto SourceFile to Pydantic."""
    if not source_file.filename:
        return None
    return SourceFile(
        filename=source_file.filename,
        file_type=FileType(source_file.file_type),
        blob_path=source_file.blob_path,
        file_size_bytes=source_file.file_size_bytes,
        extraction_method=ExtractionMethod(source_file.extraction_method) if source_file.extraction_method else None,
        extraction_confidence=source_file.extraction_confidence if source_file.extraction_confidence else None,
        page_count=source_file.page_count if source_file.page_count else None,
    )


class RAGDocumentServiceServicer(ai_model_pb2_grpc.RAGDocumentServiceServicer):
    """gRPC RAGDocumentService implementation.

    Provides RAG document management APIs:
    - CRUD operations (CreateDocument, GetDocument, UpdateDocument, DeleteDocument)
    - Listing and search (ListDocuments, SearchDocuments)
    - Lifecycle management (StageDocument, ActivateDocument, ArchiveDocument, RollbackDocument)
    - Vectorization operations (VectorizeDocument, GetVectorizationJob) - Story 0.75.13c
    """

    def __init__(
        self,
        repository: RagDocumentRepository,
        vectorization_pipeline: "VectorizationPipeline | None" = None,
    ) -> None:
        """Initialize the RAGDocumentService.

        Args:
            repository: Repository for RAG document persistence.
            vectorization_pipeline: Optional pipeline for vectorization operations.
                                    Story 0.75.13c: Added for VectorizeDocument/GetVectorizationJob.
        """
        self._repository = repository
        self._vectorization_pipeline = vectorization_pipeline
        logger.info("RAGDocumentService initialized")

    async def CreateDocument(
        self,
        request: ai_model_pb2.CreateDocumentRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.CreateDocumentResponse:
        """Create a new RAG document.

        Creates a new document with version=1 and status=draft.
        Auto-generates document_id (UUID4) if not provided.

        Args:
            request: CreateDocumentRequest with document details.
            context: gRPC context.

        Returns:
            CreateDocumentResponse with the created document.
        """
        try:
            # Validate required fields
            if not request.title:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "title is required",
                )
                return ai_model_pb2.CreateDocumentResponse()

            if not request.domain:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "domain is required",
                )
                return ai_model_pb2.CreateDocumentResponse()

            if not request.metadata.author:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "metadata.author is required",
                )
                return ai_model_pb2.CreateDocumentResponse()

            # Validate domain enum
            try:
                domain = KnowledgeDomain(request.domain)
            except ValueError:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"Invalid domain: {request.domain}. Must be one of: {[d.value for d in KnowledgeDomain]}",
                )
                return ai_model_pb2.CreateDocumentResponse()

            # Auto-generate document_id if not provided
            document_id = request.document_id or str(uuid.uuid4())
            version = 1

            # Create the document
            now = datetime.now(UTC)
            doc = RagDocument(
                id=f"{document_id}:v{version}",
                document_id=document_id,
                version=version,
                title=request.title,
                domain=domain,
                content=request.content,
                status=RagDocumentStatus.DRAFT,
                metadata=_proto_metadata_to_pydantic(request.metadata),
                source_file=_proto_source_file_to_pydantic(request.source_file),
                created_at=now,
                updated_at=now,
            )

            created_doc = await self._repository.create(doc)

            logger.info(
                "Document created",
                document_id=document_id,
                version=version,
                title=request.title,
            )

            return ai_model_pb2.CreateDocumentResponse(document=_pydantic_to_proto(created_doc))

        except Exception as e:
            logger.error("CreateDocument failed", error=str(e))
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            raise

    async def GetDocument(
        self,
        request: ai_model_pb2.GetDocumentRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.RAGDocument:
        """Get document by ID or latest version.

        If version is specified (>0), returns that specific version.
        Otherwise, returns the active version (status=active).

        Args:
            request: GetDocumentRequest with document_id and optional version.
            context: gRPC context.

        Returns:
            RAGDocument.
        """
        try:
            if not request.document_id:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "document_id is required",
                )
                return ai_model_pb2.RAGDocument()

            # Get specific version or active version
            if request.version > 0:
                doc = await self._repository.get_by_version(request.document_id, request.version)
            else:
                doc = await self._repository.get_active(request.document_id)

            if doc is None:
                await context.abort(
                    grpc.StatusCode.NOT_FOUND,
                    f"Document not found: {request.document_id}"
                    + (f" version {request.version}" if request.version > 0 else ""),
                )
                return ai_model_pb2.RAGDocument()

            logger.debug(
                "GetDocument completed",
                document_id=request.document_id,
                version=doc.version,
            )

            return _pydantic_to_proto(doc)

        except Exception as e:
            logger.error("GetDocument failed", error=str(e), document_id=request.document_id)
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            raise

    async def UpdateDocument(
        self,
        request: ai_model_pb2.UpdateDocumentRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.RAGDocument:
        """Update a document by creating a new version.

        Creates a new version (version = max_version + 1) with status=draft.
        Copies document_id and metadata from the previous version unless overridden.

        Args:
            request: UpdateDocumentRequest with document_id and updates.
            context: gRPC context.

        Returns:
            RAGDocument (the new version).
        """
        try:
            if not request.document_id:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "document_id is required",
                )
                return ai_model_pb2.RAGDocument()

            # Get all versions to find the latest
            versions = await self._repository.list_versions(request.document_id)
            if not versions:
                await context.abort(
                    grpc.StatusCode.NOT_FOUND,
                    f"Document not found: {request.document_id}",
                )
                return ai_model_pb2.RAGDocument()

            # Find the latest version (list is sorted descending)
            latest_doc = versions[0]
            new_version = latest_doc.version + 1

            # Create new version, copying from latest and applying updates
            now = datetime.now(UTC)
            new_doc = RagDocument(
                id=f"{request.document_id}:v{new_version}",
                document_id=request.document_id,
                version=new_version,
                title=request.title if request.title else latest_doc.title,
                domain=latest_doc.domain,
                content=request.content if request.content else latest_doc.content,
                status=RagDocumentStatus.DRAFT,
                metadata=_proto_metadata_to_pydantic(request.metadata)
                if request.metadata.author
                else latest_doc.metadata,
                source_file=latest_doc.source_file,
                change_summary=request.change_summary,
                created_at=now,
                updated_at=now,
                pinecone_namespace=None,  # Reset for new version
                pinecone_ids=[],
                content_hash=None,
            )

            created_doc = await self._repository.create(new_doc)

            logger.info(
                "Document updated (new version)",
                document_id=request.document_id,
                old_version=latest_doc.version,
                new_version=new_version,
            )

            return _pydantic_to_proto(created_doc)

        except Exception as e:
            logger.error("UpdateDocument failed", error=str(e), document_id=request.document_id)
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            raise

    async def DeleteDocument(
        self,
        request: ai_model_pb2.DeleteDocumentRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.DeleteDocumentResponse:
        """Delete a document by archiving all versions.

        Soft delete - archives all versions via status update.

        Args:
            request: DeleteDocumentRequest with document_id.
            context: gRPC context.

        Returns:
            DeleteDocumentResponse with count of archived versions.
        """
        try:
            if not request.document_id:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "document_id is required",
                )
                return ai_model_pb2.DeleteDocumentResponse()

            # Get all versions
            versions = await self._repository.list_versions(request.document_id)
            if not versions:
                await context.abort(
                    grpc.StatusCode.NOT_FOUND,
                    f"Document not found: {request.document_id}",
                )
                return ai_model_pb2.DeleteDocumentResponse()

            # Archive all non-archived versions
            archived_count = 0
            for doc in versions:
                if doc.status != RagDocumentStatus.ARCHIVED:
                    await self._repository.update(
                        doc.id,
                        {
                            "status": RagDocumentStatus.ARCHIVED.value,
                            "updated_at": datetime.now(UTC),
                        },
                    )
                    archived_count += 1

            logger.info(
                "Document deleted (archived)",
                document_id=request.document_id,
                versions_archived=archived_count,
            )

            return ai_model_pb2.DeleteDocumentResponse(versions_archived=archived_count)

        except Exception as e:
            logger.error("DeleteDocument failed", error=str(e), document_id=request.document_id)
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            raise

    async def ListDocuments(
        self,
        request: ai_model_pb2.ListDocumentsRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.ListDocumentsResponse:
        """List documents with pagination and filtering.

        Args:
            request: ListDocumentsRequest with pagination and filter params.
            context: gRPC context.

        Returns:
            ListDocumentsResponse with documents and pagination info.
        """
        try:
            # Pagination validation
            page = max(1, request.page or 1)
            page_size = min(MAX_PAGE_SIZE, request.page_size or DEFAULT_PAGE_SIZE)
            skip = (page - 1) * page_size

            # Build query filter
            query: dict = {}
            if request.domain:
                query["domain"] = request.domain
            if request.status:
                query["status"] = request.status
            if request.author:
                query["metadata.author"] = request.author

            # Execute query with pagination (using repository method)
            documents, total_count = await self._repository.list_with_pagination(
                filters=query,
                skip=skip,
                limit=page_size,
            )

            # Convert to proto
            proto_docs = [_pydantic_to_proto(doc) for doc in documents]

            logger.debug(
                "ListDocuments completed",
                page=page,
                page_size=page_size,
                returned=len(proto_docs),
                total_count=total_count,
            )

            return ai_model_pb2.ListDocumentsResponse(
                documents=proto_docs,
                total_count=total_count,
                page=page,
                page_size=page_size,
            )

        except Exception as e:
            logger.error("ListDocuments failed", error=str(e))
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            raise

    async def SearchDocuments(
        self,
        request: ai_model_pb2.SearchDocumentsRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.SearchDocumentsResponse:
        """Search documents by title and content.

        Uses MongoDB $regex for MVP (no text index required).

        Args:
            request: SearchDocumentsRequest with search query and filters.
            context: gRPC context.

        Returns:
            SearchDocumentsResponse with matching documents.
        """
        try:
            if not request.query:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "query is required",
                )
                return ai_model_pb2.SearchDocumentsResponse()

            # Build additional filters
            filters: dict = {}
            if request.domain:
                filters["domain"] = request.domain
            if request.status:
                filters["status"] = request.status

            limit = min(MAX_PAGE_SIZE, request.limit or DEFAULT_PAGE_SIZE)

            # Execute search (using repository method)
            documents = await self._repository.search(
                query_text=request.query,
                filters=filters if filters else None,
                limit=limit,
            )

            # Convert to proto
            proto_docs = [_pydantic_to_proto(doc) for doc in documents]

            logger.debug(
                "SearchDocuments completed",
                query=request.query,
                returned=len(proto_docs),
            )

            return ai_model_pb2.SearchDocumentsResponse(documents=proto_docs)

        except Exception as e:
            logger.error("SearchDocuments failed", error=str(e), query=request.query)
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            raise

    async def StageDocument(
        self,
        request: ai_model_pb2.StageDocumentRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.RAGDocument:
        """Transition document from draft to staged.

        Args:
            request: StageDocumentRequest with document_id and version.
            context: gRPC context.

        Returns:
            RAGDocument with updated status.
        """
        try:
            if not request.document_id:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "document_id is required",
                )
                return ai_model_pb2.RAGDocument()

            if request.version <= 0:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "version is required (must be > 0)",
                )
                return ai_model_pb2.RAGDocument()

            # Get the document
            doc = await self._repository.get_by_version(request.document_id, request.version)
            if doc is None:
                await context.abort(
                    grpc.StatusCode.NOT_FOUND,
                    f"Document not found: {request.document_id} version {request.version}",
                )
                return ai_model_pb2.RAGDocument()

            # Validate current status
            if doc.status != RagDocumentStatus.DRAFT:
                await context.abort(
                    grpc.StatusCode.FAILED_PRECONDITION,
                    f"Cannot stage document: current status is '{doc.status.value}', expected 'draft'",
                )
                return ai_model_pb2.RAGDocument()

            # Update status
            updated_doc = await self._repository.update(
                doc.id,
                {
                    "status": RagDocumentStatus.STAGED.value,
                    "updated_at": datetime.now(UTC),
                },
            )

            logger.info(
                "Document staged",
                document_id=request.document_id,
                version=request.version,
            )

            return _pydantic_to_proto(updated_doc)

        except Exception as e:
            logger.error(
                "StageDocument failed",
                error=str(e),
                document_id=request.document_id,
            )
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            raise

    async def ActivateDocument(
        self,
        request: ai_model_pb2.ActivateDocumentRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.RAGDocument:
        """Transition document from staged to active.

        Archives the current active version first.

        Args:
            request: ActivateDocumentRequest with document_id and version.
            context: gRPC context.

        Returns:
            RAGDocument with updated status.
        """
        try:
            if not request.document_id:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "document_id is required",
                )
                return ai_model_pb2.RAGDocument()

            if request.version <= 0:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "version is required (must be > 0)",
                )
                return ai_model_pb2.RAGDocument()

            # Get the document to activate
            doc = await self._repository.get_by_version(request.document_id, request.version)
            if doc is None:
                await context.abort(
                    grpc.StatusCode.NOT_FOUND,
                    f"Document not found: {request.document_id} version {request.version}",
                )
                return ai_model_pb2.RAGDocument()

            # Validate current status
            if doc.status != RagDocumentStatus.STAGED:
                await context.abort(
                    grpc.StatusCode.FAILED_PRECONDITION,
                    f"Cannot activate document: current status is '{doc.status.value}', expected 'staged'",
                )
                return ai_model_pb2.RAGDocument()

            # Archive current active version (if exists)
            current_active = await self._repository.get_active(request.document_id)
            if current_active:
                await self._repository.update(
                    current_active.id,
                    {
                        "status": RagDocumentStatus.ARCHIVED.value,
                        "updated_at": datetime.now(UTC),
                    },
                )
                logger.debug(
                    "Previous active version archived",
                    document_id=request.document_id,
                    archived_version=current_active.version,
                )

            # Activate the new version
            updated_doc = await self._repository.update(
                doc.id,
                {
                    "status": RagDocumentStatus.ACTIVE.value,
                    "updated_at": datetime.now(UTC),
                },
            )

            logger.info(
                "Document activated",
                document_id=request.document_id,
                version=request.version,
            )

            return _pydantic_to_proto(updated_doc)

        except Exception as e:
            logger.error(
                "ActivateDocument failed",
                error=str(e),
                document_id=request.document_id,
            )
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            raise

    async def ArchiveDocument(
        self,
        request: ai_model_pb2.ArchiveDocumentRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.RAGDocument:
        """Archive a document version or all versions.

        If version is specified, archives only that version.
        If version is 0, archives all non-archived versions.

        Args:
            request: ArchiveDocumentRequest with document_id and optional version.
            context: gRPC context.

        Returns:
            RAGDocument (the last archived document).
        """
        try:
            if not request.document_id:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "document_id is required",
                )
                return ai_model_pb2.RAGDocument()

            if request.version > 0:
                # Archive specific version
                doc = await self._repository.get_by_version(request.document_id, request.version)
                if doc is None:
                    await context.abort(
                        grpc.StatusCode.NOT_FOUND,
                        f"Document not found: {request.document_id} version {request.version}",
                    )
                    return ai_model_pb2.RAGDocument()

                updated_doc = await self._repository.update(
                    doc.id,
                    {
                        "status": RagDocumentStatus.ARCHIVED.value,
                        "updated_at": datetime.now(UTC),
                    },
                )

                logger.info(
                    "Document version archived",
                    document_id=request.document_id,
                    version=request.version,
                )

                return _pydantic_to_proto(updated_doc)
            else:
                # Archive all versions
                versions = await self._repository.list_versions(request.document_id)
                if not versions:
                    await context.abort(
                        grpc.StatusCode.NOT_FOUND,
                        f"Document not found: {request.document_id}",
                    )
                    return ai_model_pb2.RAGDocument()

                last_archived = None
                for doc in versions:
                    if doc.status != RagDocumentStatus.ARCHIVED:
                        last_archived = await self._repository.update(
                            doc.id,
                            {
                                "status": RagDocumentStatus.ARCHIVED.value,
                                "updated_at": datetime.now(UTC),
                            },
                        )

                logger.info(
                    "All document versions archived",
                    document_id=request.document_id,
                    total_versions=len(versions),
                )

                # Return the first version (highest version number)
                return _pydantic_to_proto(last_archived or versions[0])

        except Exception as e:
            logger.error(
                "ArchiveDocument failed",
                error=str(e),
                document_id=request.document_id,
            )
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            raise

    async def RollbackDocument(
        self,
        request: ai_model_pb2.RollbackDocumentRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.RAGDocument:
        """Create new draft version copying content from specified old version.

        Creates a new version with status=draft containing the content
        from the target version.

        Args:
            request: RollbackDocumentRequest with document_id and target_version.
            context: gRPC context.

        Returns:
            RAGDocument (the new draft version).
        """
        try:
            if not request.document_id:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "document_id is required",
                )
                return ai_model_pb2.RAGDocument()

            if request.target_version <= 0:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "target_version is required (must be > 0)",
                )
                return ai_model_pb2.RAGDocument()

            # Get the target version to rollback to
            target_doc = await self._repository.get_by_version(request.document_id, request.target_version)
            if target_doc is None:
                await context.abort(
                    grpc.StatusCode.NOT_FOUND,
                    f"Document not found: {request.document_id} version {request.target_version}",
                )
                return ai_model_pb2.RAGDocument()

            # Get all versions to determine new version number
            versions = await self._repository.list_versions(request.document_id)
            new_version = versions[0].version + 1

            # Create new draft version with content from target
            now = datetime.now(UTC)
            new_doc = RagDocument(
                id=f"{request.document_id}:v{new_version}",
                document_id=request.document_id,
                version=new_version,
                title=target_doc.title,
                domain=target_doc.domain,
                content=target_doc.content,
                status=RagDocumentStatus.DRAFT,
                metadata=target_doc.metadata,
                source_file=target_doc.source_file,
                change_summary=f"Rollback to version {request.target_version}",
                created_at=now,
                updated_at=now,
                pinecone_namespace=None,
                pinecone_ids=[],
                content_hash=None,
            )

            created_doc = await self._repository.create(new_doc)

            logger.info(
                "Document rolled back",
                document_id=request.document_id,
                target_version=request.target_version,
                new_version=new_version,
            )

            return _pydantic_to_proto(created_doc)

        except Exception as e:
            logger.error(
                "RollbackDocument failed",
                error=str(e),
                document_id=request.document_id,
            )
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            raise

    # ========================================
    # Extraction Operations (Story 0.75.10b)
    # ========================================

    async def ExtractDocument(
        self,
        request: ai_model_pb2.ExtractDocumentRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.ExtractDocumentResponse:
        """Start async extraction for a document.

        Downloads source file from blob storage and extracts text content.
        Returns immediately with a job_id for tracking progress.

        Args:
            request: ExtractDocumentRequest with document_id and optional version.
            context: gRPC context.

        Returns:
            ExtractDocumentResponse with job_id.
        """
        try:
            if not request.document_id:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "document_id is required",
                )
                return ai_model_pb2.ExtractDocumentResponse()

            # Import here to avoid circular import
            from ai_model.services import (
                DocumentNotFoundError,
                NoSourceFileError,
            )

            # Check if workflow is available
            if not hasattr(self, "_extraction_workflow") or self._extraction_workflow is None:
                await context.abort(
                    grpc.StatusCode.UNAVAILABLE,
                    "Extraction service not configured",
                )
                return ai_model_pb2.ExtractDocumentResponse()

            # Start extraction
            job_id = await self._extraction_workflow.start_extraction(
                request.document_id,
                version=request.version if request.version > 0 else None,
            )

            logger.info(
                "Extraction started",
                document_id=request.document_id,
                version=request.version,
                job_id=job_id,
            )

            return ai_model_pb2.ExtractDocumentResponse(job_id=job_id)

        except DocumentNotFoundError as e:
            await context.abort(grpc.StatusCode.NOT_FOUND, str(e))
            raise
        except NoSourceFileError as e:
            await context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))
            raise
        except Exception as e:
            logger.error(
                "ExtractDocument failed",
                error=str(e),
                document_id=request.document_id,
            )
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            raise

    async def GetExtractionJob(
        self,
        request: ai_model_pb2.GetExtractionJobRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.ExtractionJobResponse:
        """Get extraction job status.

        One-shot status check for an extraction job.

        Args:
            request: GetExtractionJobRequest with job_id.
            context: gRPC context.

        Returns:
            ExtractionJobResponse with job details.
        """
        try:
            if not request.job_id:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "job_id is required",
                )
                return ai_model_pb2.ExtractionJobResponse()

            # Check if workflow is available
            if not hasattr(self, "_extraction_workflow") or self._extraction_workflow is None:
                await context.abort(
                    grpc.StatusCode.UNAVAILABLE,
                    "Extraction service not configured",
                )
                return ai_model_pb2.ExtractionJobResponse()

            job = await self._extraction_workflow.get_job(request.job_id)

            if job is None:
                await context.abort(
                    grpc.StatusCode.NOT_FOUND,
                    f"Extraction job not found: {request.job_id}",
                )
                return ai_model_pb2.ExtractionJobResponse()

            response = ai_model_pb2.ExtractionJobResponse(
                job_id=job.job_id,
                document_id=job.document_id,
                status=job.status.value,
                progress_percent=job.progress_percent,
                pages_processed=job.pages_processed,
                total_pages=job.total_pages,
                error_message=job.error_message or "",
            )

            # Set timestamps
            response.started_at.FromDatetime(job.started_at)
            if job.completed_at:
                response.completed_at.FromDatetime(job.completed_at)

            return response

        except Exception as e:
            logger.error(
                "GetExtractionJob failed",
                error=str(e),
                job_id=request.job_id,
            )
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            raise

    async def StreamExtractionProgress(
        self,
        request: ai_model_pb2.StreamExtractionProgressRequest,
        context: grpc.aio.ServicerContext,
    ):
        """Stream extraction progress events.

        Server-streaming RPC that yields progress events until job completes.

        Args:
            request: StreamExtractionProgressRequest with job_id.
            context: gRPC context.

        Yields:
            ExtractionProgressEvent with current progress.
        """
        import asyncio

        from ai_model.domain.extraction_job import ExtractionJobStatus

        if not request.job_id:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "job_id is required",
            )
            return

        # Check if workflow is available
        if not hasattr(self, "_extraction_workflow") or self._extraction_workflow is None:
            await context.abort(
                grpc.StatusCode.UNAVAILABLE,
                "Extraction service not configured",
            )
            return

        job_id = request.job_id
        poll_interval = 0.5  # seconds

        while not context.cancelled():
            job = await self._extraction_workflow.get_job(job_id)

            if job is None:
                await context.abort(
                    grpc.StatusCode.NOT_FOUND,
                    f"Extraction job not found: {job_id}",
                )
                return

            # Yield progress event
            yield ai_model_pb2.ExtractionProgressEvent(
                job_id=job.job_id,
                status=job.status.value,
                progress_percent=job.progress_percent,
                pages_processed=job.pages_processed,
                total_pages=job.total_pages,
                error_message=job.error_message or "",
            )

            # Check if job is complete
            if job.status in (ExtractionJobStatus.COMPLETED, ExtractionJobStatus.FAILED):
                return

            # Wait before next poll
            await asyncio.sleep(poll_interval)

    def set_extraction_workflow(self, workflow) -> None:
        """Set the extraction workflow service.

        Called during service initialization to inject the workflow.

        Args:
            workflow: ExtractionWorkflow instance.
        """
        self._extraction_workflow = workflow

    def set_chunking_workflow(self, workflow) -> None:
        """Set the chunking workflow service.

        Called during service initialization to inject the workflow.

        Args:
            workflow: ChunkingWorkflow instance.
        """
        self._chunking_workflow = workflow

    async def _require_chunking_workflow(self, context: grpc.aio.ServicerContext) -> bool:
        """Check if chunking workflow is available.

        Args:
            context: gRPC context for error reporting.

        Returns:
            True if workflow is available, False if aborted.
        """
        if not hasattr(self, "_chunking_workflow") or self._chunking_workflow is None:
            await context.abort(
                grpc.StatusCode.UNAVAILABLE,
                "Chunking service not configured",
            )
            return False
        return True

    # ========================================
    # Chunking Operations (Story 0.75.10d)
    # ========================================

    async def ChunkDocument(
        self,
        request: ai_model_pb2.ChunkDocumentRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.ChunkDocumentResponse:
        """Chunk a document's content into semantic chunks.

        Creates chunks from extracted document content, splitting on
        headings and paragraphs for optimal vectorization.

        Args:
            request: ChunkDocumentRequest with document_id and optional version.
            context: gRPC context.

        Returns:
            ChunkDocumentResponse with chunking statistics.
        """
        try:
            if not request.document_id:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "document_id is required",
                )
                return ai_model_pb2.ChunkDocumentResponse()

            # Check if chunking workflow is available
            if not await self._require_chunking_workflow(context):
                return ai_model_pb2.ChunkDocumentResponse()

            # Get the document
            if request.version > 0:
                doc = await self._repository.get_by_version(request.document_id, request.version)
            else:
                # Get latest non-archived version
                versions = await self._repository.list_versions(request.document_id, include_archived=False)
                doc = versions[0] if versions else None

            if doc is None:
                await context.abort(
                    grpc.StatusCode.NOT_FOUND,
                    f"Document not found: {request.document_id}"
                    + (f" version {request.version}" if request.version > 0 else ""),
                )
                return ai_model_pb2.ChunkDocumentResponse()

            # Check if document has content
            if not doc.content or not doc.content.strip():
                await context.abort(
                    grpc.StatusCode.FAILED_PRECONDITION,
                    "Document has no content to chunk. Run ExtractDocument first.",
                )
                return ai_model_pb2.ChunkDocumentResponse()

            # Import chunking errors
            from ai_model.services import TooManyChunksError

            # Perform chunking
            try:
                chunks = await self._chunking_workflow.chunk_document(doc)
            except TooManyChunksError as e:
                await context.abort(grpc.StatusCode.RESOURCE_EXHAUSTED, str(e))
                raise

            # Calculate statistics
            total_char_count = sum(c.char_count for c in chunks)
            total_word_count = sum(c.word_count for c in chunks)

            logger.info(
                "Document chunked",
                document_id=request.document_id,
                version=doc.version,
                chunks_created=len(chunks),
                total_char_count=total_char_count,
                total_word_count=total_word_count,
            )

            return ai_model_pb2.ChunkDocumentResponse(
                chunks_created=len(chunks),
                total_char_count=total_char_count,
                total_word_count=total_word_count,
            )

        except Exception as e:
            logger.error(
                "ChunkDocument failed",
                error=str(e),
                document_id=request.document_id,
            )
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            raise

    async def ListChunks(
        self,
        request: ai_model_pb2.ListChunksRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.ListChunksResponse:
        """List chunks for a document version with pagination.

        Args:
            request: ListChunksRequest with document_id, version, and pagination params.
            context: gRPC context.

        Returns:
            ListChunksResponse with chunks and pagination info.
        """
        try:
            if not request.document_id:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "document_id is required",
                )
                return ai_model_pb2.ListChunksResponse()

            if request.version <= 0:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "version is required (must be > 0)",
                )
                return ai_model_pb2.ListChunksResponse()

            # Check if chunking workflow is available
            if not await self._require_chunking_workflow(context):
                return ai_model_pb2.ListChunksResponse()

            # Pagination
            page = max(1, request.page or 1)
            page_size = min(100, request.page_size or 50)

            # Get all chunks (workflow handles ordering)
            all_chunks = await self._chunking_workflow.get_chunks(
                request.document_id,
                request.version,
            )

            # Apply pagination
            total_count = len(all_chunks)
            start = (page - 1) * page_size
            end = start + page_size
            page_chunks = all_chunks[start:end]

            # Convert to proto
            proto_chunks = []
            for chunk in page_chunks:
                proto_chunk = ai_model_pb2.RagChunk(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    document_version=chunk.document_version,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    section_title=chunk.section_title or "",
                    word_count=chunk.word_count,
                    char_count=chunk.char_count,
                    pinecone_id=chunk.pinecone_id or "",
                )
                proto_chunk.created_at.FromDatetime(chunk.created_at)
                proto_chunks.append(proto_chunk)

            logger.debug(
                "ListChunks completed",
                document_id=request.document_id,
                version=request.version,
                page=page,
                page_size=page_size,
                returned=len(proto_chunks),
                total_count=total_count,
            )

            return ai_model_pb2.ListChunksResponse(
                chunks=proto_chunks,
                total_count=total_count,
                page=page,
                page_size=page_size,
            )

        except Exception as e:
            logger.error(
                "ListChunks failed",
                error=str(e),
                document_id=request.document_id,
            )
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            raise

    async def GetChunk(
        self,
        request: ai_model_pb2.GetChunkRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.RagChunk:
        """Get a specific chunk by ID.

        Args:
            request: GetChunkRequest with chunk_id.
            context: gRPC context.

        Returns:
            RagChunk.
        """
        try:
            if not request.chunk_id:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "chunk_id is required",
                )
                return ai_model_pb2.RagChunk()

            # Check if chunking workflow is available
            if not await self._require_chunking_workflow(context):
                return ai_model_pb2.RagChunk()

            # Get chunk via workflow (proper encapsulation)
            chunk = await self._chunking_workflow.get_chunk_by_id(request.chunk_id)

            if chunk is None:
                await context.abort(
                    grpc.StatusCode.NOT_FOUND,
                    f"Chunk not found: {request.chunk_id}",
                )
                return ai_model_pb2.RagChunk()

            # Convert to proto
            proto_chunk = ai_model_pb2.RagChunk(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                document_version=chunk.document_version,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                section_title=chunk.section_title or "",
                word_count=chunk.word_count,
                char_count=chunk.char_count,
                pinecone_id=chunk.pinecone_id or "",
            )
            proto_chunk.created_at.FromDatetime(chunk.created_at)

            return proto_chunk

        except Exception as e:
            logger.error(
                "GetChunk failed",
                error=str(e),
                chunk_id=request.chunk_id,
            )
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            raise

    async def DeleteChunks(
        self,
        request: ai_model_pb2.DeleteChunksRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.DeleteChunksResponse:
        """Delete all chunks for a document version.

        Args:
            request: DeleteChunksRequest with document_id and version.
            context: gRPC context.

        Returns:
            DeleteChunksResponse with count of deleted chunks.
        """
        try:
            if not request.document_id:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "document_id is required",
                )
                return ai_model_pb2.DeleteChunksResponse()

            if request.version <= 0:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "version is required (must be > 0)",
                )
                return ai_model_pb2.DeleteChunksResponse()

            # Check if chunking workflow is available
            if not await self._require_chunking_workflow(context):
                return ai_model_pb2.DeleteChunksResponse()

            # Delete chunks
            deleted_count = await self._chunking_workflow.delete_chunks(
                request.document_id,
                request.version,
            )

            logger.info(
                "Chunks deleted",
                document_id=request.document_id,
                version=request.version,
                chunks_deleted=deleted_count,
            )

            return ai_model_pb2.DeleteChunksResponse(chunks_deleted=deleted_count)

        except Exception as e:
            logger.error(
                "DeleteChunks failed",
                error=str(e),
                document_id=request.document_id,
            )
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            raise

    # ========================================
    # Vectorization Operations (Story 0.75.13c)
    # ========================================

    def set_vectorization_pipeline(self, pipeline: "VectorizationPipeline") -> None:
        """Set the vectorization pipeline service.

        Called during service initialization to inject the pipeline.

        Args:
            pipeline: VectorizationPipeline instance.
        """
        self._vectorization_pipeline = pipeline

    async def _require_vectorization_pipeline(self, context: grpc.aio.ServicerContext) -> bool:
        """Check if vectorization pipeline is available.

        Args:
            context: gRPC context for error reporting.

        Returns:
            True if pipeline is available, False if aborted.
        """
        if self._vectorization_pipeline is None:
            await context.abort(
                grpc.StatusCode.UNAVAILABLE,
                "Vectorization service not configured",
            )
            return False
        return True

    async def VectorizeDocument(
        self,
        request: ai_model_pb2.VectorizeDocumentRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.VectorizeDocumentResponse:
        """Vectorize a document by generating embeddings and storing in Pinecone.

        In sync mode (async=False), blocks until vectorization completes.
        In async mode (async=True), returns immediately with job_id for polling.

        Args:
            request: VectorizeDocumentRequest with document_id, version, and async flag.
            context: gRPC context.

        Returns:
            VectorizeDocumentResponse with job_id and (in sync mode) vectorization results.
        """
        try:
            if not request.document_id:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "document_id is required",
                )
                return ai_model_pb2.VectorizeDocumentResponse()

            # Check if vectorization pipeline is available
            if not await self._require_vectorization_pipeline(context):
                return ai_model_pb2.VectorizeDocumentResponse()

            # Determine version to vectorize (0 = get latest active or staged)
            version = request.version
            if version <= 0:
                # Get the active version, or if none, the latest staged version
                doc = await self._repository.get_active(request.document_id)
                if doc is None:
                    # Try latest staged version
                    versions = await self._repository.list_versions(request.document_id, include_archived=False)
                    staged_versions = [v for v in versions if v.status == RagDocumentStatus.STAGED]
                    if staged_versions:
                        doc = staged_versions[0]  # Highest version first

                if doc is None:
                    await context.abort(
                        grpc.StatusCode.NOT_FOUND,
                        f"No active or staged version found for document: {request.document_id}",
                    )
                    return ai_model_pb2.VectorizeDocumentResponse()
                version = doc.version

            # Async mode: create job and return immediately
            # Note: 'async' is a Python reserved word, access via getattr
            is_async = getattr(request, "async", False)
            if is_async:
                job = self._vectorization_pipeline.create_job(
                    document_id=request.document_id,
                    document_version=version,
                )

                logger.info(
                    "Vectorization job created (async mode)",
                    job_id=job.job_id,
                    document_id=request.document_id,
                    version=version,
                )

                # Schedule async execution (fire-and-forget via asyncio.create_task)
                import asyncio

                # Store task reference to prevent garbage collection
                # In production, consider a task manager for proper lifecycle management
                task = asyncio.create_task(
                    self._vectorization_pipeline.vectorize_document(
                        document_id=request.document_id,
                        document_version=version,
                        request_id=job.job_id,
                    )
                )
                # Log if task fails (fire-and-forget pattern)
                task.add_done_callback(
                    lambda t: logger.error("Background vectorization failed", error=str(t.exception()))
                    if t.exception()
                    else None
                )

                return ai_model_pb2.VectorizeDocumentResponse(
                    job_id=job.job_id,
                    status=job.status.value,
                )

            # Sync mode: block until complete
            try:
                result = await self._vectorization_pipeline.vectorize_document(
                    document_id=request.document_id,
                    document_version=version,
                )
            except DocumentNotFoundError as e:
                await context.abort(grpc.StatusCode.NOT_FOUND, str(e))
                raise
            except InvalidDocumentStatusError as e:
                await context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))
                raise

            logger.info(
                "Vectorization completed (sync mode)",
                job_id=result.job_id,
                document_id=request.document_id,
                version=version,
                status=result.status.value,
                chunks_stored=result.progress.chunks_stored,
            )

            # Build error message from failed chunks if any
            error_message = ""
            if result.failed_chunks:
                errors = [f"chunk {fc.chunk_index}: {fc.error_message}" for fc in result.failed_chunks[:3]]
                error_message = "; ".join(errors)
                if len(result.failed_chunks) > 3:
                    error_message += f" ... and {len(result.failed_chunks) - 3} more"

            return ai_model_pb2.VectorizeDocumentResponse(
                job_id=result.job_id,
                status=result.status.value,
                namespace=result.namespace or "",
                chunks_total=result.progress.chunks_total,
                chunks_embedded=result.progress.chunks_embedded,
                chunks_stored=result.progress.chunks_stored,
                failed_count=result.progress.failed_count,
                content_hash=result.content_hash or "",
                error_message=error_message,
            )

        except Exception as e:
            logger.error(
                "VectorizeDocument failed",
                error=str(e),
                document_id=request.document_id,
            )
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            raise

    async def GetVectorizationJob(
        self,
        request: ai_model_pb2.GetVectorizationJobRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.VectorizationJobResponse:
        """Get vectorization job status.

        Used to poll for job completion in async mode.

        Args:
            request: GetVectorizationJobRequest with job_id.
            context: gRPC context.

        Returns:
            VectorizationJobResponse with job details.
        """
        try:
            if not request.job_id:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "job_id is required",
                )
                return ai_model_pb2.VectorizationJobResponse()

            # Check if vectorization pipeline is available
            if not await self._require_vectorization_pipeline(context):
                return ai_model_pb2.VectorizationJobResponse()

            # Get job status
            result = await self._vectorization_pipeline.get_job_status(request.job_id)

            if result is None:
                await context.abort(
                    grpc.StatusCode.NOT_FOUND,
                    f"Vectorization job not found: {request.job_id}",
                )
                return ai_model_pb2.VectorizationJobResponse()

            # Build error message from failed chunks if any
            error_message = ""
            if result.failed_chunks:
                errors = [f"chunk {fc.chunk_index}: {fc.error_message}" for fc in result.failed_chunks[:3]]
                error_message = "; ".join(errors)
                if len(result.failed_chunks) > 3:
                    error_message += f" ... and {len(result.failed_chunks) - 3} more"

            response = ai_model_pb2.VectorizationJobResponse(
                job_id=result.job_id,
                status=result.status.value,
                document_id=result.document_id,
                document_version=result.document_version,
                namespace=result.namespace or "",
                chunks_total=result.progress.chunks_total,
                chunks_embedded=result.progress.chunks_embedded,
                chunks_stored=result.progress.chunks_stored,
                failed_count=result.progress.failed_count,
                content_hash=result.content_hash or "",
                error_message=error_message,
            )

            # Set timestamps
            response.started_at.FromDatetime(result.started_at)
            if result.completed_at:
                response.completed_at.FromDatetime(result.completed_at)

            return response

        except Exception as e:
            logger.error(
                "GetVectorizationJob failed",
                error=str(e),
                job_id=request.job_id,
            )
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            raise
