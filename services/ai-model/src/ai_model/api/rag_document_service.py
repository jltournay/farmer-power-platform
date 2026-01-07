"""gRPC RAGDocumentService implementation.

This module implements the RAGDocumentService gRPC API for RAG document management.
Documents are versioned with lifecycle status: draft → staged → active → archived.

Story 0.75.10: gRPC Model for RAG Document
"""

import uuid
from datetime import UTC, datetime

import grpc
import structlog
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
    """

    def __init__(self, repository: RagDocumentRepository) -> None:
        """Initialize the RAGDocumentService.

        Args:
            repository: Repository for RAG document persistence.
        """
        self._repository = repository
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

            # Execute query with pagination
            cursor = self._repository._collection.find(query).skip(skip).limit(page_size)
            docs = await cursor.to_list(length=page_size)
            total_count = await self._repository._collection.count_documents(query)

            # Convert to proto
            proto_docs = []
            for doc in docs:
                doc.pop("_id", None)
                pydantic_doc = RagDocument.model_validate(doc)
                proto_docs.append(_pydantic_to_proto(pydantic_doc))

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

            # Build search filter using $regex
            filter_query: dict = {
                "$or": [
                    {"title": {"$regex": request.query, "$options": "i"}},
                    {"content": {"$regex": request.query, "$options": "i"}},
                ]
            }
            if request.domain:
                filter_query["domain"] = request.domain
            if request.status:
                filter_query["status"] = request.status

            limit = min(MAX_PAGE_SIZE, request.limit or DEFAULT_PAGE_SIZE)

            # Execute search
            cursor = self._repository._collection.find(filter_query).limit(limit)
            docs = await cursor.to_list(length=limit)

            # Convert to proto
            proto_docs = []
            for doc in docs:
                doc.pop("_id", None)
                pydantic_doc = RagDocument.model_validate(doc)
                proto_docs.append(_pydantic_to_proto(pydantic_doc))

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
