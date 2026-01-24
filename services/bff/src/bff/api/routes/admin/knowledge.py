"""Knowledge Management admin API routes (Story 9.9a).

Implements REST endpoints for knowledge document management:
- CRUD: list, search, get, create, update, delete
- Lifecycle: stage, activate, archive, rollback
- Upload & Extraction: upload file, poll extraction, SSE progress
- Chunking: list chunks
- Vectorization: trigger, poll status
- Query: knowledge base query
"""

import os

from bff.api.middleware.auth import require_platform_admin
from bff.api.schemas import ApiError, TokenClaims
from bff.api.schemas.admin.knowledge_schemas import (
    ChunkListResponse,
    CreateDocumentRequest,
    DeleteDocumentResponse,
    DocumentDetail,
    DocumentListResponse,
    DocumentStatus,
    DocumentSummary,
    ExtractionJobStatus,
    KnowledgeDomain,
    QueryKnowledgeRequest,
    QueryResponse,
    RollbackDocumentRequest,
    UpdateDocumentRequest,
    VectorizationJobStatus,
    VectorizeDocumentRequest,
)
from bff.infrastructure.clients import NotFoundError, ServiceUnavailableError
from bff.infrastructure.clients.ai_model_client import AiModelClient
from bff.infrastructure.sse import SSEManager, grpc_stream_to_sse
from bff.services.admin.knowledge_service import AdminKnowledgeService
from bff.transformers.admin.knowledge_transformer import KnowledgeTransformer
from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, UploadFile
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/knowledge", tags=["admin-knowledge"])


def get_knowledge_service() -> AdminKnowledgeService:
    """Dependency for AdminKnowledgeService."""
    direct_host = os.environ.get("AI_MODEL_GRPC_HOST")
    return AdminKnowledgeService(
        ai_model_client=AiModelClient(direct_host=direct_host),
        transformer=KnowledgeTransformer(),
    )


# =========================================================================
# CRUD Routes (AC 9.9a.1)
# =========================================================================


@router.get(
    "",
    response_model=DocumentListResponse,
    responses={
        200: {"description": "Paginated list of knowledge documents"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="List knowledge documents",
    description="List knowledge documents with optional filters. Requires platform_admin role.",
)
async def list_documents(
    domain: KnowledgeDomain | None = Query(default=None, description="Filter by knowledge domain"),
    status: DocumentStatus | None = Query(default=None, description="Filter by status"),
    author: str | None = Query(default=None, description="Filter by author"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    user: TokenClaims = require_platform_admin(),
    service: AdminKnowledgeService = Depends(get_knowledge_service),
) -> DocumentListResponse:
    """List knowledge documents with filtering and pagination."""
    try:
        return await service.list_documents(
            domain=domain.value if domain else None,
            status=status.value if status else None,
            author=author,
            page=page,
            page_size=page_size,
        )
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("AI Model").model_dump(),
        ) from e


@router.get(
    "/search",
    response_model=list[DocumentSummary],
    responses={
        200: {"description": "Search results"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Search knowledge documents",
    description="Search documents by title/content. Requires platform_admin role.",
)
async def search_documents(
    q: str = Query(description="Search query text", min_length=1),
    domain: KnowledgeDomain | None = Query(default=None, description="Filter by domain"),
    status: DocumentStatus | None = Query(default=None, description="Filter by status"),
    limit: int = Query(default=20, ge=1, le=100, description="Max results"),
    user: TokenClaims = require_platform_admin(),
    service: AdminKnowledgeService = Depends(get_knowledge_service),
) -> list[DocumentSummary]:
    """Search knowledge documents by title and content."""
    try:
        return await service.search_documents(
            query=q,
            domain=domain.value if domain else None,
            status=status.value if status else None,
            limit=limit,
        )
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("AI Model").model_dump(),
        ) from e


@router.get(
    "/{document_id}",
    response_model=DocumentDetail,
    responses={
        200: {"description": "Document detail"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        404: {"description": "Document not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Get knowledge document",
    description="Get document detail with optional version. Requires platform_admin role.",
)
async def get_document(
    document_id: str = Path(description="Document ID"),
    version: int = Query(default=0, ge=0, description="Specific version (0 = active)"),
    user: TokenClaims = require_platform_admin(),
    service: AdminKnowledgeService = Depends(get_knowledge_service),
) -> DocumentDetail:
    """Get knowledge document by ID."""
    try:
        return await service.get_document(document_id=document_id, version=version)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError.not_found("Document", document_id).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("AI Model").model_dump(),
        ) from e


@router.post(
    "",
    response_model=DocumentDetail,
    status_code=201,
    responses={
        201: {"description": "Document created"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Create knowledge document",
    description="Create a new knowledge document. Requires platform_admin role.",
)
async def create_document(
    request: CreateDocumentRequest,
    user: TokenClaims = require_platform_admin(),
    service: AdminKnowledgeService = Depends(get_knowledge_service),
) -> DocumentDetail:
    """Create a new knowledge document."""
    try:
        return await service.create_document(
            title=request.title,
            domain=request.domain.value,
            content=request.content,
            author=request.author,
            source=request.source,
            region=request.region,
            tags=request.tags,
        )
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("AI Model").model_dump(),
        ) from e


@router.put(
    "/{document_id}",
    response_model=DocumentDetail,
    responses={
        200: {"description": "Document updated (new version created)"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        404: {"description": "Document not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Update knowledge document",
    description="Update document (creates new version). Requires platform_admin role.",
)
async def update_document(
    request: UpdateDocumentRequest,
    document_id: str = Path(description="Document ID to update"),
    user: TokenClaims = require_platform_admin(),
    service: AdminKnowledgeService = Depends(get_knowledge_service),
) -> DocumentDetail:
    """Update a knowledge document (creates new version)."""
    try:
        return await service.update_document(
            document_id=document_id,
            title=request.title,
            content=request.content,
            author=request.author,
            source=request.source,
            region=request.region,
            tags=request.tags,
            change_summary=request.change_summary,
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError.not_found("Document", document_id).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("AI Model").model_dump(),
        ) from e


@router.delete(
    "/{document_id}",
    response_model=DeleteDocumentResponse,
    responses={
        200: {"description": "Document deleted (archived)"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        404: {"description": "Document not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Delete knowledge document",
    description="Delete (archive) document and all versions. Requires platform_admin role.",
)
async def delete_document(
    document_id: str = Path(description="Document ID to delete"),
    user: TokenClaims = require_platform_admin(),
    service: AdminKnowledgeService = Depends(get_knowledge_service),
) -> DeleteDocumentResponse:
    """Delete (archive) a knowledge document."""
    try:
        return await service.delete_document(document_id=document_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError.not_found("Document", document_id).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("AI Model").model_dump(),
        ) from e


# =========================================================================
# Lifecycle Routes (AC 9.9a.2)
# =========================================================================


@router.post(
    "/{document_id}/stage",
    response_model=DocumentDetail,
    responses={
        200: {"description": "Document staged"},
        400: {"description": "Invalid state transition", "model": ApiError},
        404: {"description": "Document not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Stage document",
    description="Transition document from draft to staged. Requires platform_admin role.",
)
async def stage_document(
    document_id: str = Path(description="Document ID"),
    version: int = Query(default=0, ge=0, description="Version to stage"),
    user: TokenClaims = require_platform_admin(),
    service: AdminKnowledgeService = Depends(get_knowledge_service),
) -> DocumentDetail:
    """Stage a knowledge document."""
    try:
        return await service.stage_document(document_id=document_id, version=version)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError.not_found("Document", document_id).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("AI Model").model_dump(),
        ) from e


@router.post(
    "/{document_id}/activate",
    response_model=DocumentDetail,
    responses={
        200: {"description": "Document activated"},
        400: {"description": "Invalid state transition", "model": ApiError},
        404: {"description": "Document not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Activate document",
    description="Transition document from staged to active. Requires platform_admin role.",
)
async def activate_document(
    document_id: str = Path(description="Document ID"),
    version: int = Query(default=0, ge=0, description="Version to activate"),
    user: TokenClaims = require_platform_admin(),
    service: AdminKnowledgeService = Depends(get_knowledge_service),
) -> DocumentDetail:
    """Activate a knowledge document."""
    try:
        return await service.activate_document(document_id=document_id, version=version)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError.not_found("Document", document_id).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("AI Model").model_dump(),
        ) from e


@router.post(
    "/{document_id}/archive",
    response_model=DocumentDetail,
    responses={
        200: {"description": "Document archived"},
        404: {"description": "Document not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Archive document",
    description="Archive a document (any state). Requires platform_admin role.",
)
async def archive_document(
    document_id: str = Path(description="Document ID"),
    version: int = Query(default=0, ge=0, description="Version to archive (0 = all)"),
    user: TokenClaims = require_platform_admin(),
    service: AdminKnowledgeService = Depends(get_knowledge_service),
) -> DocumentDetail:
    """Archive a knowledge document."""
    try:
        return await service.archive_document(document_id=document_id, version=version)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError.not_found("Document", document_id).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("AI Model").model_dump(),
        ) from e


@router.post(
    "/{document_id}/rollback",
    response_model=DocumentDetail,
    responses={
        200: {"description": "Document rolled back (new draft created)"},
        404: {"description": "Document not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Rollback document",
    description="Create new draft from a previous version. Requires platform_admin role.",
)
async def rollback_document(
    request: RollbackDocumentRequest,
    document_id: str = Path(description="Document ID"),
    user: TokenClaims = require_platform_admin(),
    service: AdminKnowledgeService = Depends(get_knowledge_service),
) -> DocumentDetail:
    """Rollback a knowledge document to a previous version."""
    try:
        return await service.rollback_document(
            document_id=document_id,
            target_version=request.target_version,
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError.not_found("Document", document_id).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("AI Model").model_dump(),
        ) from e


# =========================================================================
# Upload & Extraction Routes (AC 9.9a.3, 9.9a.4)
# =========================================================================


@router.post(
    "/upload",
    response_model=ExtractionJobStatus,
    status_code=201,
    responses={
        201: {"description": "Document uploaded and extraction triggered"},
        400: {"description": "Invalid file type or size", "model": ApiError},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Upload document file",
    description="Upload file with metadata, triggers extraction. Requires platform_admin role.",
)
async def upload_document(
    file: UploadFile = File(..., description="Document file (pdf, docx, md, txt)"),
    title: str = Form(..., description="Document title"),
    domain: KnowledgeDomain = Form(..., description="Knowledge domain"),
    author: str = Form(default="", description="Document author"),
    source: str = Form(default="", description="Original source"),
    region: str = Form(default="", description="Geographic relevance"),
    user: TokenClaims = require_platform_admin(),
    service: AdminKnowledgeService = Depends(get_knowledge_service),
) -> ExtractionJobStatus:
    """Upload document file, create document, and trigger extraction."""
    try:
        return await service.upload_document(
            file=file,
            title=title,
            domain=domain.value,
            author=author,
            source=source,
            region=region,
        )
    except HTTPException:
        raise
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("AI Model").model_dump(),
        ) from e


@router.get(
    "/{document_id}/extraction/progress",
    responses={
        200: {"description": "SSE stream of extraction progress events", "content": {"text/event-stream": {}}},
        404: {"description": "Job not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Stream extraction progress (SSE)",
    description="Real-time extraction progress via Server-Sent Events. Requires platform_admin role.",
)
async def stream_extraction_progress(
    document_id: str = Path(description="Document ID"),
    job_id: str = Query(..., description="Extraction job ID"),
    user: TokenClaims = require_platform_admin(),
    service: AdminKnowledgeService = Depends(get_knowledge_service),
) -> StreamingResponse:
    """SSE stream for extraction progress."""
    try:
        grpc_stream = await service.stream_extraction_progress(document_id, job_id)

        def _transform_progress(msg):
            message = msg.error_message if msg.status == "failed" and msg.error_message else f"Pages {msg.pages_processed}/{msg.total_pages}"
            return {
                "percent": msg.progress_percent,
                "status": msg.status,
                "message": message,
                "pages_processed": msg.pages_processed,
                "total_pages": msg.total_pages,
            }

        sse_events = grpc_stream_to_sse(
            grpc_stream,
            transform=_transform_progress,
        )

        return SSEManager.create_response(sse_events, event_type="progress")
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError.not_found("Extraction job", job_id).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("AI Model").model_dump(),
        ) from e


@router.get(
    "/{document_id}/extraction/{job_id}",
    response_model=ExtractionJobStatus,
    responses={
        200: {"description": "Extraction job status"},
        404: {"description": "Job not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Get extraction job status",
    description="Poll extraction job status. Requires platform_admin role.",
)
async def get_extraction_job(
    document_id: str = Path(description="Document ID"),
    job_id: str = Path(description="Extraction job ID"),
    user: TokenClaims = require_platform_admin(),
    service: AdminKnowledgeService = Depends(get_knowledge_service),
) -> ExtractionJobStatus:
    """Get extraction job status."""
    try:
        return await service.get_extraction_job(job_id=job_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError.not_found("Extraction job", job_id).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("AI Model").model_dump(),
        ) from e


# =========================================================================
# Chunking Routes (AC 9.9a.5)
# =========================================================================


@router.get(
    "/{document_id}/chunks",
    response_model=ChunkListResponse,
    responses={
        200: {"description": "Paginated list of chunks"},
        404: {"description": "Document not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="List document chunks",
    description="List chunks for a document version. Requires platform_admin role.",
)
async def list_chunks(
    document_id: str = Path(description="Document ID"),
    version: int = Query(default=0, ge=0, description="Document version (0 = latest)"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=100, description="Items per page"),
    user: TokenClaims = require_platform_admin(),
    service: AdminKnowledgeService = Depends(get_knowledge_service),
) -> ChunkListResponse:
    """List document chunks with pagination."""
    try:
        return await service.list_chunks(
            document_id=document_id,
            version=version,
            page=page,
            page_size=page_size,
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError.not_found("Document", document_id).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("AI Model").model_dump(),
        ) from e


# =========================================================================
# Vectorization Routes (AC 9.9a.5)
# =========================================================================


@router.post(
    "/{document_id}/vectorize",
    response_model=VectorizationJobStatus,
    responses={
        200: {"description": "Vectorization triggered"},
        404: {"description": "Document not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Trigger vectorization",
    description="Trigger document vectorization. Requires platform_admin role.",
)
async def vectorize_document(
    document_id: str = Path(description="Document ID"),
    request: VectorizeDocumentRequest | None = None,
    user: TokenClaims = require_platform_admin(),
    service: AdminKnowledgeService = Depends(get_knowledge_service),
) -> VectorizationJobStatus:
    """Trigger document vectorization."""
    version = request.version if request else 0
    try:
        return await service.vectorize_document(document_id=document_id, version=version)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError.not_found("Document", document_id).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("AI Model").model_dump(),
        ) from e


@router.get(
    "/{document_id}/vectorization/{job_id}",
    response_model=VectorizationJobStatus,
    responses={
        200: {"description": "Vectorization job status"},
        404: {"description": "Job not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Get vectorization job status",
    description="Poll vectorization job status. Requires platform_admin role.",
)
async def get_vectorization_job(
    document_id: str = Path(description="Document ID"),
    job_id: str = Path(description="Vectorization job ID"),
    user: TokenClaims = require_platform_admin(),
    service: AdminKnowledgeService = Depends(get_knowledge_service),
) -> VectorizationJobStatus:
    """Get vectorization job status."""
    try:
        return await service.get_vectorization_job(job_id=job_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError.not_found("Vectorization job", job_id).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("AI Model").model_dump(),
        ) from e


# =========================================================================
# Query Route (AC 9.9a.6)
# =========================================================================


@router.post(
    "/query",
    response_model=QueryResponse,
    responses={
        200: {"description": "Knowledge query results"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Query knowledge base",
    description="Query knowledge base for 'Test with AI' feature. Requires platform_admin role.",
)
async def query_knowledge(
    request: QueryKnowledgeRequest,
    user: TokenClaims = require_platform_admin(),
    service: AdminKnowledgeService = Depends(get_knowledge_service),
) -> QueryResponse:
    """Query the knowledge base."""
    try:
        return await service.query_knowledge(
            query=request.query,
            domains=[d.value for d in request.domains] if request.domains else None,
            top_k=request.top_k,
            confidence_threshold=request.confidence_threshold,
            namespace=request.namespace or None,
        )
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("AI Model").model_dump(),
        ) from e
