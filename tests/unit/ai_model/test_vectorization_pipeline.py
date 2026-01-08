"""Unit tests for Vectorization Pipeline.

Tests cover:
- Domain models (VectorizationJob, VectorizationProgress, VectorizationResult)
- Namespace generation strategy
- Content hash computation
- Vector metadata building
- Batch processing with embedding and storage
- Progress tracking
- Error handling and partial failures
- Async job support

Story 0.75.13b: RAG Vectorization Pipeline (Orchestration)
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from ai_model.config import Settings
from ai_model.domain.exceptions import (
    DocumentNotFoundError,
    InvalidDocumentStatusError,
)
from ai_model.domain.rag_document import (
    KnowledgeDomain,
    RagChunk,
    RagDocument,
    RAGDocumentMetadata,
    RagDocumentStatus,
)
from ai_model.domain.vectorization import (
    FailedChunk,
    VectorizationJob,
    VectorizationJobStatus,
    VectorizationProgress,
    VectorizationResult,
)
from ai_model.infrastructure.pinecone_vector_store import PineconeVectorStore
from ai_model.infrastructure.repositories.rag_chunk_repository import RagChunkRepository
from ai_model.infrastructure.repositories.rag_document_repository import RagDocumentRepository
from ai_model.services.embedding_service import EmbeddingService
from ai_model.services.vectorization_pipeline import VectorizationPipeline

# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_settings(monkeypatch) -> Settings:
    """Create settings for vectorization pipeline tests."""
    monkeypatch.setenv("PINECONE_API_KEY", "test-pinecone-api-key")
    monkeypatch.setenv("PINECONE_INDEX_NAME", "test-index")

    return Settings(
        _env_file=None,
        vectorization_batch_size=10,  # Small batch for testing
    )


@pytest.fixture
def mock_chunk_repository() -> AsyncMock:
    """Create mock RagChunkRepository."""
    repo = AsyncMock(spec=RagChunkRepository)
    return repo


@pytest.fixture
def mock_document_repository() -> AsyncMock:
    """Create mock RagDocumentRepository."""
    repo = AsyncMock(spec=RagDocumentRepository)
    return repo


@pytest.fixture
def mock_embedding_service() -> AsyncMock:
    """Create mock EmbeddingService."""
    service = AsyncMock(spec=EmbeddingService)
    return service


@pytest.fixture
def mock_vector_store() -> AsyncMock:
    """Create mock PineconeVectorStore."""
    store = AsyncMock(spec=PineconeVectorStore)
    return store


@pytest.fixture
def pipeline(
    mock_chunk_repository,
    mock_document_repository,
    mock_embedding_service,
    mock_vector_store,
    mock_settings,
) -> VectorizationPipeline:
    """Create VectorizationPipeline with mocked dependencies."""
    return VectorizationPipeline(
        chunk_repository=mock_chunk_repository,
        document_repository=mock_document_repository,
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,
        settings=mock_settings,
    )


@pytest.fixture
def sample_document() -> RagDocument:
    """Create sample RagDocument for testing."""
    return RagDocument(
        id="disease-guide:v1",
        document_id="disease-guide",
        version=1,
        title="Disease Diagnosis Guide",
        domain=KnowledgeDomain.PLANT_DISEASES,
        content="# Blister Blight\n\nCaused by fungus...",
        status=RagDocumentStatus.STAGED,
        metadata=RAGDocumentMetadata(
            author="Dr. Wanjiku",
            source="Kenya Tea Research",
            region="Kenya",
            season="monsoon",
            tags=["blister-blight", "fungal"],
        ),
    )


@pytest.fixture
def sample_chunks() -> list[RagChunk]:
    """Create sample RagChunks for testing."""
    return [
        RagChunk(
            chunk_id="disease-guide-v1-chunk-0",
            document_id="disease-guide",
            document_version=1,
            chunk_index=0,
            content="# Blister Blight\n\nBlister blight is caused by fungus.",
            section_title="Blister Blight",
            word_count=10,
            char_count=50,
        ),
        RagChunk(
            chunk_id="disease-guide-v1-chunk-1",
            document_id="disease-guide",
            document_version=1,
            chunk_index=1,
            content="## Treatment\n\nApply fungicide early in the season.",
            section_title="Treatment",
            word_count=8,
            char_count=45,
        ),
        RagChunk(
            chunk_id="disease-guide-v1-chunk-2",
            document_id="disease-guide",
            document_version=1,
            chunk_index=2,
            content="## Prevention\n\nMaintain good drainage and airflow.",
            section_title="Prevention",
            word_count=7,
            char_count=42,
        ),
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# DOMAIN MODEL TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestVectorizationProgress:
    """Tests for VectorizationProgress domain model."""

    def test_progress_percent_with_chunks(self):
        """Test progress percentage calculation."""
        progress = VectorizationProgress(
            chunks_total=100,
            chunks_embedded=50,
            chunks_stored=25,
            failed_count=0,
        )
        assert progress.progress_percent == 25.0

    def test_progress_percent_empty(self):
        """Test progress percentage when no chunks."""
        progress = VectorizationProgress(
            chunks_total=0,
            chunks_embedded=0,
            chunks_stored=0,
            failed_count=0,
        )
        assert progress.progress_percent == 100.0

    def test_progress_percent_complete(self):
        """Test progress percentage when complete."""
        progress = VectorizationProgress(
            chunks_total=50,
            chunks_embedded=50,
            chunks_stored=50,
            failed_count=0,
        )
        assert progress.progress_percent == 100.0


class TestVectorizationJob:
    """Tests for VectorizationJob domain model."""

    def test_job_creation(self):
        """Test VectorizationJob creation with defaults."""
        job = VectorizationJob(
            job_id="test-job-123",
            document_id="disease-guide",
            document_version=1,
        )
        assert job.job_id == "test-job-123"
        assert job.status == VectorizationJobStatus.PENDING
        assert job.namespace is None
        assert job.created_at is not None

    def test_job_status_values(self):
        """Test VectorizationJobStatus enum values."""
        assert VectorizationJobStatus.PENDING.value == "pending"
        assert VectorizationJobStatus.IN_PROGRESS.value == "in_progress"
        assert VectorizationJobStatus.COMPLETED.value == "completed"
        assert VectorizationJobStatus.FAILED.value == "failed"
        assert VectorizationJobStatus.PARTIAL.value == "partial"


class TestVectorizationResult:
    """Tests for VectorizationResult domain model."""

    def test_result_duration_calculation(self):
        """Test duration calculation when timestamps are set."""
        started = datetime(2026, 1, 7, 10, 0, 0, tzinfo=UTC)
        completed = datetime(2026, 1, 7, 10, 0, 30, tzinfo=UTC)

        result = VectorizationResult(
            job_id="test-job",
            status=VectorizationJobStatus.COMPLETED,
            document_id="test-doc",
            document_version=1,
            started_at=started,
            completed_at=completed,
        )
        assert result.duration_seconds == 30.0

    def test_result_duration_none_when_incomplete(self):
        """Test duration is None when timestamps not set."""
        result = VectorizationResult(
            job_id="test-job",
            status=VectorizationJobStatus.IN_PROGRESS,
            document_id="test-doc",
            document_version=1,
        )
        assert result.duration_seconds is None

    def test_result_with_failed_chunks(self):
        """Test result with failed chunks list."""
        result = VectorizationResult(
            job_id="test-job",
            status=VectorizationJobStatus.PARTIAL,
            document_id="test-doc",
            document_version=1,
            failed_chunks=[
                FailedChunk(
                    chunk_id="chunk-5",
                    chunk_index=5,
                    error_message="Embedding failed",
                )
            ],
        )
        assert len(result.failed_chunks) == 1
        assert result.failed_chunks[0].chunk_id == "chunk-5"


# ═══════════════════════════════════════════════════════════════════════════════
# NAMESPACE GENERATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestNamespaceGeneration:
    """Tests for namespace generation based on document status."""

    def test_namespace_active_document(self, pipeline, sample_document):
        """Test namespace for active document."""
        sample_document.status = RagDocumentStatus.ACTIVE
        sample_document.version = 5
        namespace = pipeline._generate_namespace(sample_document)
        assert namespace == "knowledge-v5"

    def test_namespace_staged_document(self, pipeline, sample_document):
        """Test namespace for staged document."""
        sample_document.status = RagDocumentStatus.STAGED
        sample_document.version = 3
        namespace = pipeline._generate_namespace(sample_document)
        assert namespace == "knowledge-v3-staged"

    def test_namespace_archived_document(self, pipeline, sample_document):
        """Test namespace for archived document."""
        sample_document.status = RagDocumentStatus.ARCHIVED
        sample_document.version = 2
        namespace = pipeline._generate_namespace(sample_document)
        assert namespace == "knowledge-v2-archived"

    def test_namespace_draft_document_raises_error(self, pipeline, sample_document):
        """Test that draft documents raise InvalidDocumentStatusError."""
        sample_document.status = RagDocumentStatus.DRAFT

        with pytest.raises(InvalidDocumentStatusError) as exc_info:
            pipeline._generate_namespace(sample_document)

        assert "draft" in str(exc_info.value).lower()


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT HASH TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestContentHash:
    """Tests for content hash computation."""

    def test_content_hash_computation(self, pipeline, sample_chunks):
        """Test SHA256 hash is computed correctly."""
        content_hash = pipeline._compute_content_hash(sample_chunks)

        # Verify format
        assert content_hash.startswith("sha256:")
        assert len(content_hash) == 71  # "sha256:" (7) + 64 hex chars

    def test_content_hash_deterministic(self, pipeline, sample_chunks):
        """Test same chunks produce same hash."""
        hash1 = pipeline._compute_content_hash(sample_chunks)
        hash2 = pipeline._compute_content_hash(sample_chunks)
        assert hash1 == hash2

    def test_content_hash_order_independent(self, pipeline, sample_chunks):
        """Test chunks are sorted by index before hashing."""
        # Reverse the order
        reversed_chunks = list(reversed(sample_chunks))
        hash_original = pipeline._compute_content_hash(sample_chunks)
        hash_reversed = pipeline._compute_content_hash(reversed_chunks)

        # Should produce same hash because chunks are sorted internally
        assert hash_original == hash_reversed

    def test_content_hash_changes_with_content(self, pipeline, sample_chunks):
        """Test hash changes when content changes."""
        hash1 = pipeline._compute_content_hash(sample_chunks)

        # Modify content
        modified_chunks = [
            RagChunk(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                document_version=c.document_version,
                chunk_index=c.chunk_index,
                content=c.content + " modified",
                word_count=c.word_count,
                char_count=c.char_count,
            )
            for c in sample_chunks
        ]
        hash2 = pipeline._compute_content_hash(modified_chunks)

        assert hash1 != hash2


# ═══════════════════════════════════════════════════════════════════════════════
# VECTOR METADATA TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestVectorMetadata:
    """Tests for vector metadata building."""

    def test_metadata_from_chunk_and_document(self, pipeline, sample_document, sample_chunks):
        """Test metadata is built correctly from chunk and document."""
        chunk = sample_chunks[0]
        metadata = pipeline._build_vector_metadata(chunk, sample_document)

        assert metadata.document_id == "disease-guide"
        assert metadata.chunk_id == "disease-guide-v1-chunk-0"
        assert metadata.chunk_index == 0
        assert metadata.domain == "plant_diseases"
        assert metadata.title == "Disease Diagnosis Guide"
        assert metadata.region == "Kenya"
        assert metadata.season == "monsoon"
        assert metadata.tags == ["blister-blight", "fungal"]

    def test_vector_id_generation(self, pipeline):
        """Test vector ID format."""
        vector_id = pipeline._generate_vector_id("disease-guide", 5)
        assert vector_id == "disease-guide-5"


# ═══════════════════════════════════════════════════════════════════════════════
# VECTORIZE DOCUMENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestVectorizeDocument:
    """Tests for the main vectorize_document method."""

    @pytest.mark.asyncio
    async def test_document_not_found_raises_error(
        self,
        pipeline,
        mock_document_repository,
    ):
        """Test DocumentNotFoundError when document doesn't exist."""
        mock_document_repository.get_by_version.return_value = None

        with pytest.raises(DocumentNotFoundError) as exc_info:
            await pipeline.vectorize_document("nonexistent", 1)

        assert "nonexistent" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_no_chunks_returns_completed(
        self,
        pipeline,
        mock_document_repository,
        mock_chunk_repository,
        sample_document,
    ):
        """Test immediate completion when no un-vectorized chunks."""
        mock_document_repository.get_by_version.return_value = sample_document
        mock_chunk_repository.get_chunks_without_vectors.return_value = []

        result = await pipeline.vectorize_document("disease-guide", 1)

        assert result.status == VectorizationJobStatus.COMPLETED
        assert result.progress.chunks_total == 0
        assert result.progress.chunks_stored == 0

    @pytest.mark.asyncio
    async def test_successful_vectorization(
        self,
        pipeline,
        mock_document_repository,
        mock_chunk_repository,
        mock_embedding_service,
        mock_vector_store,
        sample_document,
        sample_chunks,
    ):
        """Test successful full vectorization flow."""
        # Setup mocks
        mock_document_repository.get_by_version.return_value = sample_document
        mock_chunk_repository.get_chunks_without_vectors.return_value = sample_chunks
        mock_chunk_repository.update_pinecone_id.return_value = sample_chunks[0]
        mock_document_repository.replace.return_value = sample_document

        # Mock embedding service to return fake embeddings
        mock_embedding_service.embed_passages.return_value = [
            [0.1] * 1024,
            [0.2] * 1024,
            [0.3] * 1024,
        ]

        # Mock vector store
        mock_vector_store.upsert.return_value = MagicMock(upserted_count=3)

        # Execute
        result = await pipeline.vectorize_document("disease-guide", 1)

        # Verify
        assert result.status == VectorizationJobStatus.COMPLETED
        assert result.progress.chunks_total == 3
        assert result.progress.chunks_stored == 3
        assert result.progress.failed_count == 0
        assert result.namespace == "knowledge-v1-staged"
        assert len(result.pinecone_ids) == 3
        assert result.content_hash is not None

        # Verify embedding service was called
        mock_embedding_service.embed_passages.assert_called_once()

        # Verify vector store was called
        mock_vector_store.upsert.assert_called_once()

        # Verify document was updated
        mock_document_repository.replace.assert_called_once()

    @pytest.mark.asyncio
    async def test_partial_failure_continues_processing(
        self,
        pipeline,
        mock_document_repository,
        mock_chunk_repository,
        mock_embedding_service,
        mock_vector_store,
        sample_document,
        mock_settings,
    ):
        """Test that partial failures result in PARTIAL status."""
        # Create more chunks than batch size to test batching
        chunks = [
            RagChunk(
                chunk_id=f"chunk-{i}",
                document_id="disease-guide",
                document_version=1,
                chunk_index=i,
                content=f"Content {i}",
                word_count=2,
                char_count=10,
            )
            for i in range(15)  # More than batch_size of 10
        ]

        mock_document_repository.get_by_version.return_value = sample_document
        mock_chunk_repository.get_chunks_without_vectors.return_value = chunks
        mock_chunk_repository.update_pinecone_id.return_value = chunks[0]
        mock_document_repository.replace.return_value = sample_document

        # First batch succeeds, second batch fails
        mock_embedding_service.embed_passages.side_effect = [
            [[0.1] * 1024] * 10,  # First batch succeeds
            Exception("Embedding API error"),  # Second batch fails
        ]
        mock_vector_store.upsert.return_value = MagicMock(upserted_count=10)

        result = await pipeline.vectorize_document("disease-guide", 1)

        assert result.status == VectorizationJobStatus.PARTIAL
        assert result.progress.chunks_stored == 10
        assert result.progress.failed_count == 5
        assert len(result.failed_chunks) == 5

    @pytest.mark.asyncio
    async def test_all_batches_fail_returns_failed(
        self,
        pipeline,
        mock_document_repository,
        mock_chunk_repository,
        mock_embedding_service,
        mock_vector_store,
        sample_document,
        sample_chunks,
    ):
        """Test that complete failure results in FAILED status."""
        mock_document_repository.get_by_version.return_value = sample_document
        mock_chunk_repository.get_chunks_without_vectors.return_value = sample_chunks
        mock_document_repository.replace.return_value = sample_document

        # All embeddings fail
        mock_embedding_service.embed_passages.side_effect = Exception("API down")

        result = await pipeline.vectorize_document("disease-guide", 1)

        assert result.status == VectorizationJobStatus.FAILED
        assert result.progress.chunks_stored == 0
        assert result.progress.failed_count == 3


# ═══════════════════════════════════════════════════════════════════════════════
# BATCH PROCESSING TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestBatchProcessing:
    """Tests for batch processing logic."""

    @pytest.mark.asyncio
    async def test_chunks_split_into_batches(
        self,
        pipeline,
        mock_document_repository,
        mock_chunk_repository,
        mock_embedding_service,
        mock_vector_store,
        sample_document,
        mock_settings,
    ):
        """Test chunks are correctly split into batches."""
        # Create 25 chunks (batch size is 10)
        chunks = [
            RagChunk(
                chunk_id=f"chunk-{i}",
                document_id="disease-guide",
                document_version=1,
                chunk_index=i,
                content=f"Content {i}",
                word_count=2,
                char_count=10,
            )
            for i in range(25)
        ]

        mock_document_repository.get_by_version.return_value = sample_document
        mock_chunk_repository.get_chunks_without_vectors.return_value = chunks
        mock_chunk_repository.update_pinecone_id.return_value = chunks[0]
        mock_document_repository.replace.return_value = sample_document

        # Return embeddings for each batch
        mock_embedding_service.embed_passages.side_effect = [
            [[0.1] * 1024] * 10,  # Batch 1: 10 chunks
            [[0.2] * 1024] * 10,  # Batch 2: 10 chunks
            [[0.3] * 1024] * 5,  # Batch 3: 5 chunks
        ]
        mock_vector_store.upsert.return_value = MagicMock(upserted_count=10)

        result = await pipeline.vectorize_document("disease-guide", 1)

        # Verify 3 batches were processed
        assert mock_embedding_service.embed_passages.call_count == 3
        assert mock_vector_store.upsert.call_count == 3
        assert result.progress.chunks_stored == 25


# ═══════════════════════════════════════════════════════════════════════════════
# JOB STATUS TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestJobStatus:
    """Tests for async job tracking."""

    @pytest.mark.asyncio
    async def test_get_job_status_returns_result(
        self,
        pipeline,
        mock_document_repository,
        mock_chunk_repository,
        mock_embedding_service,
        mock_vector_store,
        sample_document,
        sample_chunks,
    ):
        """Test job status can be retrieved after vectorization."""
        mock_document_repository.get_by_version.return_value = sample_document
        mock_chunk_repository.get_chunks_without_vectors.return_value = sample_chunks
        mock_chunk_repository.update_pinecone_id.return_value = sample_chunks[0]
        mock_document_repository.replace.return_value = sample_document
        mock_embedding_service.embed_passages.return_value = [[0.1] * 1024] * 3
        mock_vector_store.upsert.return_value = MagicMock(upserted_count=3)

        result = await pipeline.vectorize_document("disease-guide", 1, request_id="test-job-id")

        # Retrieve job status
        job_status = await pipeline.get_job_status("test-job-id")

        assert job_status is not None
        assert job_status.job_id == "test-job-id"
        assert job_status.status == VectorizationJobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_get_job_status_unknown_job(self, pipeline):
        """Test None returned for unknown job ID."""
        result = await pipeline.get_job_status("unknown-job")
        assert result is None

    @pytest.mark.asyncio
    async def test_create_job(self, pipeline):
        """Test creating a new job for tracking."""
        job = await pipeline.create_job("disease-guide", 2)

        assert job.document_id == "disease-guide"
        assert job.document_version == 2
        assert job.status == VectorizationJobStatus.PENDING
        assert job.job_id is not None


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestConfiguration:
    """Tests for configuration handling."""

    def test_vectorization_batch_size_setting(self, mock_settings):
        """Test vectorization_batch_size is configurable."""
        assert mock_settings.vectorization_batch_size == 10

    def test_default_batch_size(self, monkeypatch):
        """Test default batch size is 50."""
        monkeypatch.setenv("PINECONE_API_KEY", "test-key")
        settings = Settings(_env_file=None)
        assert settings.vectorization_batch_size == 50
