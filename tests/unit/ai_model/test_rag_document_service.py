"""Unit tests for RAGDocumentServiceServicer.

Story 0.75.10: gRPC Model for RAG Document
Story 0.75.13c: VectorizeDocument and GetVectorizationJob RPCs

Tests cover:
- CRUD operations (CreateDocument, GetDocument, UpdateDocument, DeleteDocument)
- Listing and search (ListDocuments, SearchDocuments)
- Lifecycle management (StageDocument, ActivateDocument, ArchiveDocument, RollbackDocument)
- Vectorization operations (VectorizeDocument, GetVectorizationJob)
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from ai_model.api.rag_document_service import RAGDocumentServiceServicer
from ai_model.domain.rag_document import (
    KnowledgeDomain,
    RagDocument,
    RAGDocumentMetadata,
    RagDocumentStatus,
)
from ai_model.infrastructure.repositories import RagDocumentRepository
from fp_proto.ai_model.v1 import ai_model_pb2


@pytest.fixture
def mock_repository(mock_mongodb_client):
    """Create a mock RagDocumentRepository with MockMongoClient."""
    db = mock_mongodb_client["ai_model"]
    return RagDocumentRepository(db)


@pytest.fixture
def mock_context():
    """Create a mock gRPC context."""
    context = MagicMock(spec=grpc.aio.ServicerContext)
    context.abort = AsyncMock()
    return context


@pytest.fixture
def service(mock_repository):
    """Create RAGDocumentServiceServicer with mock repository."""
    return RAGDocumentServiceServicer(mock_repository)


@pytest.fixture
def sample_document():
    """Create a sample RagDocument for testing."""
    return RagDocument(
        id="disease-guide:v1",
        document_id="disease-guide",
        version=1,
        title="Tea Disease Guide",
        domain=KnowledgeDomain.PLANT_DISEASES,
        content="# Tea Diseases\n\nThis guide covers common tea diseases...",
        status=RagDocumentStatus.DRAFT,
        metadata=RAGDocumentMetadata(
            author="Dr. Wanjiku",
            source="Kenya Tea Research Foundation",
            region="Kenya",
            tags=["tea", "diseases", "diagnosis"],
        ),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


# ============================================
# CreateDocument Tests (2 tests)
# ============================================


@pytest.mark.asyncio
async def test_create_document_success(service, mock_context):
    """Test successful document creation."""
    request = ai_model_pb2.CreateDocumentRequest(
        document_id="disease-guide",
        title="Tea Disease Guide",
        domain="plant_diseases",
        content="# Tea Diseases\n\nThis guide covers common tea diseases...",
        metadata=ai_model_pb2.RAGDocumentMetadata(
            author="Dr. Wanjiku",
            source="Kenya Tea Research Foundation",
            region="Kenya",
            tags=["tea", "diseases"],
        ),
    )

    response = await service.CreateDocument(request, mock_context)

    assert response.document.document_id == "disease-guide"
    assert response.document.version == 1
    assert response.document.status == "draft"
    assert response.document.title == "Tea Disease Guide"
    assert response.document.domain == "plant_diseases"
    assert response.document.metadata.author == "Dr. Wanjiku"
    mock_context.abort.assert_not_called()


@pytest.mark.asyncio
async def test_create_document_missing_required_fields(service, mock_context):
    """Test document creation with missing required fields."""
    request = ai_model_pb2.CreateDocumentRequest(
        title="",  # Empty title should fail
        domain="plant_diseases",
        metadata=ai_model_pb2.RAGDocumentMetadata(
            author="Dr. Wanjiku",
        ),
    )

    await service.CreateDocument(request, mock_context)

    mock_context.abort.assert_called_once()
    call_args = mock_context.abort.call_args
    assert call_args[0][0] == grpc.StatusCode.INVALID_ARGUMENT
    assert "title is required" in call_args[0][1]


# ============================================
# GetDocument Tests (2 tests)
# ============================================


@pytest.mark.asyncio
async def test_get_document_by_id_returns_active_version(service, mock_repository, mock_context, sample_document):
    """Test getting document by ID returns active version."""
    # Create draft document
    await mock_repository.create(sample_document)

    # Update to active status
    active_doc = RagDocument(
        id="disease-guide:v2",
        document_id="disease-guide",
        version=2,
        title="Tea Disease Guide v2",
        domain=KnowledgeDomain.PLANT_DISEASES,
        content="# Tea Diseases v2\n\nUpdated content...",
        status=RagDocumentStatus.ACTIVE,
        metadata=sample_document.metadata,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await mock_repository.create(active_doc)

    request = ai_model_pb2.GetDocumentRequest(document_id="disease-guide")
    response = await service.GetDocument(request, mock_context)

    assert response.document_id == "disease-guide"
    assert response.version == 2
    assert response.status == "active"
    mock_context.abort.assert_not_called()


@pytest.mark.asyncio
async def test_get_document_by_version(service, mock_repository, mock_context, sample_document):
    """Test getting specific document version."""
    # Create document
    await mock_repository.create(sample_document)

    request = ai_model_pb2.GetDocumentRequest(document_id="disease-guide", version=1)
    response = await service.GetDocument(request, mock_context)

    assert response.document_id == "disease-guide"
    assert response.version == 1
    assert response.title == "Tea Disease Guide"
    mock_context.abort.assert_not_called()


# ============================================
# UpdateDocument Tests (2 tests)
# ============================================


@pytest.mark.asyncio
async def test_update_document_creates_new_version(service, mock_repository, mock_context, sample_document):
    """Test updating document creates a new version."""
    # Create original document
    await mock_repository.create(sample_document)

    request = ai_model_pb2.UpdateDocumentRequest(
        document_id="disease-guide",
        title="Tea Disease Guide - Updated",
        content="# Updated Content\n\nNew information...",
        change_summary="Added new disease information",
    )

    response = await service.UpdateDocument(request, mock_context)

    assert response.document_id == "disease-guide"
    assert response.version == 2  # New version created
    assert response.status == "draft"  # New version starts as draft
    assert response.title == "Tea Disease Guide - Updated"
    assert response.change_summary == "Added new disease information"
    mock_context.abort.assert_not_called()


@pytest.mark.asyncio
async def test_update_document_preserves_metadata_if_not_provided(
    service, mock_repository, mock_context, sample_document
):
    """Test that updating document preserves metadata from previous version."""
    await mock_repository.create(sample_document)

    request = ai_model_pb2.UpdateDocumentRequest(
        document_id="disease-guide",
        content="# New Content",
        # No metadata provided - should copy from original
    )

    response = await service.UpdateDocument(request, mock_context)

    assert response.metadata.author == "Dr. Wanjiku"
    assert response.metadata.source == "Kenya Tea Research Foundation"
    mock_context.abort.assert_not_called()


# ============================================
# DeleteDocument Tests (1 test)
# ============================================


@pytest.mark.asyncio
async def test_delete_document_archives_all_versions(service, mock_repository, mock_context, sample_document):
    """Test deleting document archives all versions."""
    # Create multiple versions
    await mock_repository.create(sample_document)

    v2 = RagDocument(
        id="disease-guide:v2",
        document_id="disease-guide",
        version=2,
        title="Tea Disease Guide v2",
        domain=KnowledgeDomain.PLANT_DISEASES,
        content="# Version 2",
        status=RagDocumentStatus.ACTIVE,
        metadata=sample_document.metadata,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await mock_repository.create(v2)

    request = ai_model_pb2.DeleteDocumentRequest(document_id="disease-guide")
    response = await service.DeleteDocument(request, mock_context)

    assert response.versions_archived == 2  # Both versions archived
    mock_context.abort.assert_not_called()

    # Verify versions are archived
    versions = await mock_repository.list_versions("disease-guide")
    for v in versions:
        assert v.status == RagDocumentStatus.ARCHIVED


# ============================================
# ListDocuments Tests (3 tests)
# ============================================


@pytest.mark.asyncio
async def test_list_documents_with_pagination(service, mock_repository, mock_context):
    """Test listing documents with pagination."""
    # Create multiple documents
    for i in range(5):
        doc = RagDocument(
            id=f"doc-{i}:v1",
            document_id=f"doc-{i}",
            version=1,
            title=f"Document {i}",
            domain=KnowledgeDomain.PLANT_DISEASES,
            content=f"Content {i}",
            status=RagDocumentStatus.DRAFT,
            metadata=RAGDocumentMetadata(author="Test Author"),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await mock_repository.create(doc)

    request = ai_model_pb2.ListDocumentsRequest(page=1, page_size=2)
    response = await service.ListDocuments(request, mock_context)

    assert len(response.documents) == 2
    assert response.total_count == 5
    assert response.page == 1
    assert response.page_size == 2
    mock_context.abort.assert_not_called()


@pytest.mark.asyncio
async def test_list_documents_filter_by_domain(service, mock_repository, mock_context):
    """Test listing documents filtered by domain."""
    # Create documents with different domains
    for domain in [KnowledgeDomain.PLANT_DISEASES, KnowledgeDomain.TEA_CULTIVATION]:
        doc = RagDocument(
            id=f"{domain.value}:v1",
            document_id=domain.value,
            version=1,
            title=f"Document for {domain.value}",
            domain=domain,
            content="Content",
            status=RagDocumentStatus.DRAFT,
            metadata=RAGDocumentMetadata(author="Test Author"),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await mock_repository.create(doc)

    request = ai_model_pb2.ListDocumentsRequest(domain="plant_diseases")
    response = await service.ListDocuments(request, mock_context)

    assert len(response.documents) == 1
    assert response.documents[0].domain == "plant_diseases"
    mock_context.abort.assert_not_called()


@pytest.mark.asyncio
async def test_list_documents_filter_by_status(service, mock_repository, mock_context):
    """Test listing documents filtered by status."""
    # Create documents with different statuses
    for i, status in enumerate([RagDocumentStatus.DRAFT, RagDocumentStatus.ACTIVE]):
        doc = RagDocument(
            id=f"doc-{i}:v1",
            document_id=f"doc-{i}",
            version=1,
            title=f"Document {i}",
            domain=KnowledgeDomain.PLANT_DISEASES,
            content="Content",
            status=status,
            metadata=RAGDocumentMetadata(author="Test Author"),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await mock_repository.create(doc)

    request = ai_model_pb2.ListDocumentsRequest(status="active")
    response = await service.ListDocuments(request, mock_context)

    assert len(response.documents) == 1
    assert response.documents[0].status == "active"
    mock_context.abort.assert_not_called()


# ============================================
# SearchDocuments Tests (2 tests)
# ============================================


@pytest.mark.asyncio
async def test_search_documents_by_title(service, mock_repository, mock_context, sample_document):
    """Test searching documents by title."""
    await mock_repository.create(sample_document)

    # Create another document
    other_doc = RagDocument(
        id="weather-guide:v1",
        document_id="weather-guide",
        version=1,
        title="Weather Patterns Guide",
        domain=KnowledgeDomain.WEATHER_PATTERNS,
        content="Weather information...",
        status=RagDocumentStatus.DRAFT,
        metadata=RAGDocumentMetadata(author="Test Author"),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await mock_repository.create(other_doc)

    request = ai_model_pb2.SearchDocumentsRequest(query="Disease")
    response = await service.SearchDocuments(request, mock_context)

    assert len(response.documents) == 1
    assert response.documents[0].document_id == "disease-guide"
    mock_context.abort.assert_not_called()


@pytest.mark.asyncio
async def test_search_documents_by_content(service, mock_repository, mock_context, sample_document):
    """Test searching documents by content."""
    await mock_repository.create(sample_document)

    request = ai_model_pb2.SearchDocumentsRequest(query="common tea diseases")
    response = await service.SearchDocuments(request, mock_context)

    assert len(response.documents) == 1
    assert response.documents[0].document_id == "disease-guide"
    mock_context.abort.assert_not_called()


# ============================================
# Lifecycle Transition Tests (3 tests)
# ============================================


@pytest.mark.asyncio
async def test_stage_document_from_draft(service, mock_repository, mock_context, sample_document):
    """Test staging a document from draft status."""
    await mock_repository.create(sample_document)

    request = ai_model_pb2.StageDocumentRequest(document_id="disease-guide", version=1)
    response = await service.StageDocument(request, mock_context)

    assert response.document_id == "disease-guide"
    assert response.status == "staged"
    mock_context.abort.assert_not_called()


@pytest.mark.asyncio
async def test_activate_document_archives_current_active(service, mock_repository, mock_context):
    """Test that activating a document archives the current active version."""
    # Create an active document
    active_doc = RagDocument(
        id="disease-guide:v1",
        document_id="disease-guide",
        version=1,
        title="Disease Guide v1",
        domain=KnowledgeDomain.PLANT_DISEASES,
        content="Original content",
        status=RagDocumentStatus.ACTIVE,
        metadata=RAGDocumentMetadata(author="Test Author"),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await mock_repository.create(active_doc)

    # Create a staged document
    staged_doc = RagDocument(
        id="disease-guide:v2",
        document_id="disease-guide",
        version=2,
        title="Disease Guide v2",
        domain=KnowledgeDomain.PLANT_DISEASES,
        content="New content",
        status=RagDocumentStatus.STAGED,
        metadata=RAGDocumentMetadata(author="Test Author"),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await mock_repository.create(staged_doc)

    # Activate v2
    request = ai_model_pb2.ActivateDocumentRequest(document_id="disease-guide", version=2)
    response = await service.ActivateDocument(request, mock_context)

    assert response.version == 2
    assert response.status == "active"
    mock_context.abort.assert_not_called()

    # Verify v1 is now archived
    v1 = await mock_repository.get_by_version("disease-guide", 1)
    assert v1.status == RagDocumentStatus.ARCHIVED


@pytest.mark.asyncio
async def test_rollback_document_creates_new_draft(service, mock_repository, mock_context, sample_document):
    """Test rolling back to a previous version creates a new draft."""
    # Create original document
    await mock_repository.create(sample_document)

    # Create v2
    v2 = RagDocument(
        id="disease-guide:v2",
        document_id="disease-guide",
        version=2,
        title="Disease Guide v2 - Wrong Changes",
        domain=KnowledgeDomain.PLANT_DISEASES,
        content="Wrong content",
        status=RagDocumentStatus.ACTIVE,
        metadata=sample_document.metadata,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await mock_repository.create(v2)

    # Rollback to v1
    request = ai_model_pb2.RollbackDocumentRequest(document_id="disease-guide", target_version=1)
    response = await service.RollbackDocument(request, mock_context)

    assert response.version == 3  # New version created
    assert response.status == "draft"
    assert response.title == "Tea Disease Guide"  # Content from v1
    assert "Rollback to version 1" in response.change_summary
    mock_context.abort.assert_not_called()


# ============================================
# Error Handling Tests (2 additional tests)
# ============================================


@pytest.mark.asyncio
async def test_stage_document_invalid_transition(service, mock_repository, mock_context):
    """Test staging a document that is not in draft status fails."""
    # Create an already staged document
    staged_doc = RagDocument(
        id="disease-guide:v1",
        document_id="disease-guide",
        version=1,
        title="Disease Guide",
        domain=KnowledgeDomain.PLANT_DISEASES,
        content="Content",
        status=RagDocumentStatus.STAGED,  # Already staged
        metadata=RAGDocumentMetadata(author="Test Author"),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await mock_repository.create(staged_doc)

    request = ai_model_pb2.StageDocumentRequest(document_id="disease-guide", version=1)
    await service.StageDocument(request, mock_context)

    mock_context.abort.assert_called_once()
    call_args = mock_context.abort.call_args
    assert call_args[0][0] == grpc.StatusCode.FAILED_PRECONDITION
    assert "expected 'draft'" in call_args[0][1]


@pytest.mark.asyncio
async def test_get_document_not_found(service, mock_context):
    """Test getting a non-existent document returns NOT_FOUND."""
    request = ai_model_pb2.GetDocumentRequest(document_id="non-existent-doc", version=1)
    await service.GetDocument(request, mock_context)

    mock_context.abort.assert_called_once()
    call_args = mock_context.abort.call_args
    assert call_args[0][0] == grpc.StatusCode.NOT_FOUND


# ============================================
# Vectorization Tests (Story 0.75.13c) - 10 tests
# ============================================


@pytest.fixture
def mock_vectorization_pipeline():
    """Create a mock VectorizationPipeline.

    Uses mock objects that mirror the VectorizationJobResult structure
    to avoid import issues with the ai_model.services module.
    """
    from dataclasses import dataclass
    from enum import Enum

    # Local mock of VectorizationJobStatus to avoid importing from services
    class MockJobStatus(str, Enum):
        PENDING = "pending"
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"
        FAILED = "failed"
        PARTIAL = "partial"

    @dataclass
    class MockProgress:
        chunks_total: int = 0
        chunks_embedded: int = 0
        chunks_stored: int = 0
        failed_count: int = 0

    @dataclass
    class MockJobResult:
        job_id: str
        document_id: str
        document_version: int
        status: MockJobStatus
        progress: MockProgress
        namespace: str | None
        content_hash: str | None
        started_at: datetime
        completed_at: datetime | None
        failed_chunks: list

    pipeline = MagicMock()

    # Default result for successful vectorization
    pipeline.vectorize_document = AsyncMock(
        return_value=MockJobResult(
            job_id="job-123",
            document_id="disease-guide",
            document_version=1,
            status=MockJobStatus.COMPLETED,
            progress=MockProgress(
                chunks_total=10,
                chunks_embedded=10,
                chunks_stored=10,
                failed_count=0,
            ),
            namespace="disease-guide-v1",
            content_hash="abc123",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            failed_chunks=[],
        )
    )

    pipeline.create_job = AsyncMock(
        return_value=MockJobResult(
            job_id="job-456",
            document_id="disease-guide",
            document_version=1,
            status=MockJobStatus.PENDING,
            progress=MockProgress(),
            namespace=None,
            content_hash=None,
            started_at=datetime.now(UTC),
            completed_at=None,
            failed_chunks=[],
        )
    )

    pipeline.get_job_status = AsyncMock(return_value=None)

    return pipeline


@pytest.fixture
def service_with_pipeline(mock_repository, mock_vectorization_pipeline):
    """Create RAGDocumentServiceServicer with vectorization pipeline."""
    return RAGDocumentServiceServicer(mock_repository, mock_vectorization_pipeline)


@pytest.mark.asyncio
async def test_vectorize_document_sync_mode_success(
    service_with_pipeline, mock_repository, mock_context, sample_document
):
    """Test successful document vectorization in sync mode."""
    # Setup: Create active document
    sample_document.status = RagDocumentStatus.ACTIVE
    await mock_repository.create(sample_document)

    request = ai_model_pb2.VectorizeDocumentRequest(
        document_id="disease-guide",
        version=1,
    )
    # async_ field defaults to False (sync mode)

    response = await service_with_pipeline.VectorizeDocument(request, mock_context)

    assert response.job_id == "job-123"
    assert response.status == "completed"
    assert response.namespace == "disease-guide-v1"
    assert response.chunks_total == 10
    assert response.chunks_embedded == 10
    assert response.chunks_stored == 10
    assert response.failed_count == 0
    mock_context.abort.assert_not_called()


@pytest.mark.asyncio
async def test_vectorize_document_async_mode(service_with_pipeline, mock_repository, mock_context, sample_document):
    """Test document vectorization in async mode returns immediately."""
    # Setup: Create active document
    sample_document.status = RagDocumentStatus.ACTIVE
    await mock_repository.create(sample_document)

    request = ai_model_pb2.VectorizeDocumentRequest(
        document_id="disease-guide",
        version=1,
    )
    # Set async mode via setattr (protobuf reserved word handling)
    setattr(request, "async", True)

    response = await service_with_pipeline.VectorizeDocument(request, mock_context)

    assert response.job_id == "job-456"
    assert response.status == "pending"
    # Async mode doesn't include full results
    mock_context.abort.assert_not_called()


@pytest.mark.asyncio
async def test_vectorize_document_missing_document_id(service_with_pipeline, mock_context):
    """Test vectorization fails with missing document_id."""
    request = ai_model_pb2.VectorizeDocumentRequest(document_id="")

    await service_with_pipeline.VectorizeDocument(request, mock_context)

    mock_context.abort.assert_called_once()
    call_args = mock_context.abort.call_args
    assert call_args[0][0] == grpc.StatusCode.INVALID_ARGUMENT
    assert "document_id is required" in call_args[0][1]


@pytest.mark.asyncio
async def test_vectorize_document_no_pipeline_configured(service, mock_repository, mock_context, sample_document):
    """Test vectorization fails when pipeline not configured."""
    # service has no vectorization pipeline
    # Story 0.75.13c: Document must exist first (checked before pipeline availability)
    sample_document.status = RagDocumentStatus.STAGED
    await mock_repository.create(sample_document)

    request = ai_model_pb2.VectorizeDocumentRequest(document_id="disease-guide", version=1)

    await service.VectorizeDocument(request, mock_context)

    mock_context.abort.assert_called_once()
    call_args = mock_context.abort.call_args
    assert call_args[0][0] == grpc.StatusCode.UNAVAILABLE
    assert "Vectorization service not configured" in call_args[0][1]


@pytest.mark.asyncio
async def test_vectorize_document_version_0_finds_active(
    service_with_pipeline, mock_repository, mock_context, sample_document
):
    """Test vectorization with version=0 finds active document."""
    # Setup: Create active document
    sample_document.status = RagDocumentStatus.ACTIVE
    await mock_repository.create(sample_document)

    request = ai_model_pb2.VectorizeDocumentRequest(
        document_id="disease-guide",
        version=0,  # Should find active version
    )

    response = await service_with_pipeline.VectorizeDocument(request, mock_context)

    assert response.job_id == "job-123"
    mock_context.abort.assert_not_called()


@pytest.mark.asyncio
async def test_get_vectorization_job_success(service_with_pipeline, mock_context, mock_vectorization_pipeline):
    """Test getting vectorization job status."""
    from dataclasses import dataclass
    from enum import Enum

    # Local mock classes to avoid importing from services
    class MockJobStatus(str, Enum):
        COMPLETED = "completed"

    @dataclass
    class MockProgress:
        chunks_total: int = 0
        chunks_embedded: int = 0
        chunks_stored: int = 0
        failed_count: int = 0

    @dataclass
    class MockJobResult:
        job_id: str
        document_id: str
        document_version: int
        status: MockJobStatus
        progress: MockProgress
        namespace: str | None
        content_hash: str | None
        started_at: datetime
        completed_at: datetime | None
        failed_chunks: list

    # Setup mock to return job status
    mock_vectorization_pipeline.get_job_status = AsyncMock(
        return_value=MockJobResult(
            job_id="job-123",
            document_id="disease-guide",
            document_version=1,
            status=MockJobStatus.COMPLETED,
            progress=MockProgress(
                chunks_total=10,
                chunks_embedded=10,
                chunks_stored=10,
                failed_count=0,
            ),
            namespace="disease-guide-v1",
            content_hash="abc123",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            failed_chunks=[],
        )
    )

    request = ai_model_pb2.GetVectorizationJobRequest(job_id="job-123")

    response = await service_with_pipeline.GetVectorizationJob(request, mock_context)

    assert response.job_id == "job-123"
    assert response.status == "completed"
    assert response.document_id == "disease-guide"
    assert response.document_version == 1
    assert response.namespace == "disease-guide-v1"
    mock_context.abort.assert_not_called()


@pytest.mark.asyncio
async def test_get_vectorization_job_missing_job_id(service_with_pipeline, mock_context):
    """Test get vectorization job fails with missing job_id."""
    request = ai_model_pb2.GetVectorizationJobRequest(job_id="")

    await service_with_pipeline.GetVectorizationJob(request, mock_context)

    mock_context.abort.assert_called_once()
    call_args = mock_context.abort.call_args
    assert call_args[0][0] == grpc.StatusCode.INVALID_ARGUMENT
    assert "job_id is required" in call_args[0][1]


@pytest.mark.asyncio
async def test_get_vectorization_job_not_found(service_with_pipeline, mock_context, mock_vectorization_pipeline):
    """Test get vectorization job returns NOT_FOUND for unknown job."""
    mock_vectorization_pipeline.get_job_status = AsyncMock(return_value=None)

    request = ai_model_pb2.GetVectorizationJobRequest(job_id="non-existent-job")

    await service_with_pipeline.GetVectorizationJob(request, mock_context)

    mock_context.abort.assert_called_once()
    call_args = mock_context.abort.call_args
    assert call_args[0][0] == grpc.StatusCode.NOT_FOUND
    assert "not found" in call_args[0][1]


@pytest.mark.asyncio
async def test_get_vectorization_job_no_pipeline_configured(service, mock_context):
    """Test get vectorization job returns NOT_FOUND when pipeline not configured.

    Story 0.75.13c: If pipeline is not configured, no jobs can exist.
    Return NOT_FOUND rather than UNAVAILABLE (job cannot exist without pipeline).
    """
    request = ai_model_pb2.GetVectorizationJobRequest(job_id="job-123")

    await service.GetVectorizationJob(request, mock_context)

    mock_context.abort.assert_called_once()
    call_args = mock_context.abort.call_args
    assert call_args[0][0] == grpc.StatusCode.NOT_FOUND
    assert "not found" in call_args[0][1].lower()


@pytest.mark.asyncio
async def test_set_vectorization_pipeline(service, mock_vectorization_pipeline):
    """Test that vectorization pipeline can be set via setter method."""
    assert service._vectorization_pipeline is None

    service.set_vectorization_pipeline(mock_vectorization_pipeline)

    assert service._vectorization_pipeline is mock_vectorization_pipeline
