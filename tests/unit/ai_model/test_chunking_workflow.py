"""Unit tests for ChunkingWorkflow.

Story 0.75.10d: Semantic Chunking
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from ai_model.domain.rag_document import (
    KnowledgeDomain,
    RagDocument,
    RAGDocumentMetadata,
    RagDocumentStatus,
)
from ai_model.services.chunking_workflow import (
    ChunkingError,
    ChunkingWorkflow,
    TooManyChunksError,
)


@pytest.fixture
def mock_chunk_repo():
    """Create a mock RagChunkRepository."""
    repo = MagicMock()
    repo.delete_by_document = AsyncMock(return_value=0)
    repo.bulk_create = AsyncMock(side_effect=lambda chunks: chunks)
    repo.get_by_document = AsyncMock(return_value=[])
    repo.count_by_document = AsyncMock(return_value=0)
    return repo


@pytest.fixture
def mock_settings():
    """Create mock settings with chunking configuration."""
    settings = MagicMock()
    settings.chunk_size = 1000
    settings.chunk_overlap = 200
    settings.min_chunk_size = 100
    settings.max_chunks_per_document = 500
    return settings


@pytest.fixture
def workflow(mock_chunk_repo, mock_settings):
    """Create a ChunkingWorkflow with mocks."""
    return ChunkingWorkflow(mock_chunk_repo, mock_settings)


@pytest.fixture
def sample_document():
    """Create a sample RagDocument for testing."""
    # Create content that will produce chunks even with default min_chunk_size of 100
    return RagDocument(
        id="test-doc:v1",
        document_id="test-doc",
        version=1,
        title="Test Document",
        domain=KnowledgeDomain.PLANT_DISEASES,
        content="""# Introduction

This is the introduction section with meaningful content about tea cultivation and plant diseases. The content needs to be long enough to exceed the minimum chunk size of 100 characters when combined with the heading.

## Symptoms

The symptoms section describes various symptoms that can be observed in tea plants affected by blister blight disease. These symptoms include visible blisters on leaves, discoloration, and eventual leaf drop. Early detection is crucial for effective treatment.

## Treatment

Treatment involves several steps that should be followed carefully including cultural control methods, proper pruning schedule maintenance, chemical fungicide application, and ongoing monitoring for disease recurrence. Always follow recommended application rates.""",
        status=RagDocumentStatus.DRAFT,
        metadata=RAGDocumentMetadata(author="Test Author"),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestChunkingWorkflowInit:
    """Tests for ChunkingWorkflow initialization."""

    def test_workflow_initializes_with_settings(self, mock_chunk_repo, mock_settings):
        """Test workflow initializes chunker with settings."""
        workflow = ChunkingWorkflow(mock_chunk_repo, mock_settings)

        assert workflow._chunker.chunk_size == 1000
        assert workflow._chunker.chunk_overlap == 200
        assert workflow._chunker.min_chunk_size == 100

    def test_workflow_initializes_without_settings(self, mock_chunk_repo):
        """Test workflow uses defaults when no settings provided."""
        with patch("ai_model.services.chunking_workflow.Settings") as MockSettings:
            mock_default = MagicMock()
            mock_default.chunk_size = 1000
            mock_default.chunk_overlap = 200
            mock_default.min_chunk_size = 100
            mock_default.max_chunks_per_document = 500
            MockSettings.return_value = mock_default

            workflow = ChunkingWorkflow(mock_chunk_repo)

            assert workflow._chunker is not None


class TestChunkingWorkflowChunkDocument:
    """Tests for chunk_document method."""

    @pytest.mark.asyncio
    async def test_chunk_document_creates_chunks(self, workflow, mock_chunk_repo, sample_document):
        """Test chunk_document creates and stores chunks."""
        chunks = await workflow.chunk_document(sample_document)

        # Should have created chunks
        assert len(chunks) > 0
        mock_chunk_repo.bulk_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_chunk_document_deletes_existing_chunks(self, workflow, mock_chunk_repo, sample_document):
        """Test chunk_document deletes existing chunks first."""
        mock_chunk_repo.delete_by_document = AsyncMock(return_value=3)

        await workflow.chunk_document(sample_document)

        mock_chunk_repo.delete_by_document.assert_called_once_with("test-doc", 1)

    @pytest.mark.asyncio
    async def test_chunk_document_empty_content_returns_empty(self, workflow, mock_chunk_repo):
        """Test chunk_document returns empty list for empty content."""
        doc = RagDocument(
            id="empty:v1",
            document_id="empty",
            version=1,
            title="Empty",
            domain=KnowledgeDomain.PLANT_DISEASES,
            content="",
            status=RagDocumentStatus.DRAFT,
            metadata=RAGDocumentMetadata(author="Test"),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        chunks = await workflow.chunk_document(doc)

        assert chunks == []
        mock_chunk_repo.bulk_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_chunk_document_whitespace_only_returns_empty(self, workflow, mock_chunk_repo):
        """Test chunk_document returns empty for whitespace-only content."""
        doc = RagDocument(
            id="whitespace:v1",
            document_id="whitespace",
            version=1,
            title="Whitespace",
            domain=KnowledgeDomain.PLANT_DISEASES,
            content="   \n\n   ",
            status=RagDocumentStatus.DRAFT,
            metadata=RAGDocumentMetadata(author="Test"),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        chunks = await workflow.chunk_document(doc)

        assert chunks == []

    @pytest.mark.asyncio
    async def test_chunk_document_generates_correct_chunk_ids(self, workflow, mock_chunk_repo, sample_document):
        """Test chunk IDs follow expected format."""
        chunks = await workflow.chunk_document(sample_document)

        for i, chunk in enumerate(chunks):
            expected_id = f"test-doc-v1-chunk-{i}"
            assert chunk.chunk_id == expected_id

    @pytest.mark.asyncio
    async def test_chunk_document_preserves_document_metadata(self, workflow, mock_chunk_repo, sample_document):
        """Test chunks reference parent document correctly."""
        chunks = await workflow.chunk_document(sample_document)

        for chunk in chunks:
            assert chunk.document_id == "test-doc"
            assert chunk.document_version == 1

    @pytest.mark.asyncio
    async def test_chunk_document_calls_progress_callback(self, workflow, mock_chunk_repo, sample_document):
        """Test progress callback is called."""
        progress_calls = []

        def progress_callback(created, total):
            progress_calls.append((created, total))

        await workflow.chunk_document(sample_document, progress_callback=progress_callback)

        # Should have at least 2 calls: initial (0, total) and final (n, n)
        assert len(progress_calls) >= 2
        assert progress_calls[0][0] == 0  # Initial call with 0 created
        assert progress_calls[-1][0] == progress_calls[-1][1]  # Final call where created == total

    @pytest.mark.asyncio
    async def test_chunk_document_too_many_chunks_raises_error(self, mock_chunk_repo, mock_settings):
        """Test TooManyChunksError raised when chunk limit exceeded."""
        mock_settings.max_chunks_per_document = 2
        mock_settings.min_chunk_size = 50  # Lower minimum to ensure chunks are created

        # Create document with content that will produce more than 2 chunks
        # Each section needs to be > 50 chars to meet min_chunk_size
        sections = []
        for i in range(10):
            # Each section is about 150+ characters
            sections.append(f"""# Section {i}

This is detailed content for section number {i}. It describes important information about tea cultivation, plant diseases, and agricultural practices that farmers should follow. This needs to be long enough.""")

        large_content = "\n\n".join(sections)

        doc = RagDocument(
            id="large:v1",
            document_id="large",
            version=1,
            title="Large",
            domain=KnowledgeDomain.PLANT_DISEASES,
            content=large_content,
            status=RagDocumentStatus.DRAFT,
            metadata=RAGDocumentMetadata(author="Test"),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        workflow = ChunkingWorkflow(mock_chunk_repo, mock_settings)

        with pytest.raises(TooManyChunksError) as exc_info:
            await workflow.chunk_document(doc)

        assert "exceeds maximum of 2" in str(exc_info.value)


class TestChunkingWorkflowGetChunkById:
    """Tests for get_chunk_by_id method."""

    @pytest.mark.asyncio
    async def test_get_chunk_by_id_returns_chunk(self, workflow, mock_chunk_repo):
        """Test get_chunk_by_id returns chunk when found."""
        expected_chunk = MagicMock()
        mock_chunk_repo.get_by_id = AsyncMock(return_value=expected_chunk)

        result = await workflow.get_chunk_by_id("test-doc-v1-chunk-0")

        assert result == expected_chunk
        mock_chunk_repo.get_by_id.assert_called_once_with("test-doc-v1-chunk-0")

    @pytest.mark.asyncio
    async def test_get_chunk_by_id_returns_none_when_not_found(self, workflow, mock_chunk_repo):
        """Test get_chunk_by_id returns None when chunk not found."""
        mock_chunk_repo.get_by_id = AsyncMock(return_value=None)

        result = await workflow.get_chunk_by_id("nonexistent-chunk")

        assert result is None
        mock_chunk_repo.get_by_id.assert_called_once_with("nonexistent-chunk")


class TestChunkingWorkflowGetChunks:
    """Tests for get_chunks method."""

    @pytest.mark.asyncio
    async def test_get_chunks_delegates_to_repository(self, workflow, mock_chunk_repo):
        """Test get_chunks calls repository."""
        expected_chunks = [MagicMock()]
        mock_chunk_repo.get_by_document = AsyncMock(return_value=expected_chunks)

        result = await workflow.get_chunks("doc-id", 2)

        assert result == expected_chunks
        mock_chunk_repo.get_by_document.assert_called_once_with("doc-id", 2)


class TestChunkingWorkflowGetChunkCount:
    """Tests for get_chunk_count method."""

    @pytest.mark.asyncio
    async def test_get_chunk_count_delegates_to_repository(self, workflow, mock_chunk_repo):
        """Test get_chunk_count calls repository."""
        mock_chunk_repo.count_by_document = AsyncMock(return_value=15)

        result = await workflow.get_chunk_count("doc-id", 1)

        assert result == 15
        mock_chunk_repo.count_by_document.assert_called_once_with("doc-id", 1)


class TestChunkingWorkflowDeleteChunks:
    """Tests for delete_chunks method."""

    @pytest.mark.asyncio
    async def test_delete_chunks_delegates_to_repository(self, workflow, mock_chunk_repo):
        """Test delete_chunks calls repository."""
        mock_chunk_repo.delete_by_document = AsyncMock(return_value=10)

        result = await workflow.delete_chunks("doc-id", 1)

        assert result == 10
        mock_chunk_repo.delete_by_document.assert_called_once_with("doc-id", 1)


class TestChunkingExceptions:
    """Tests for chunking exception classes."""

    def test_chunking_error_is_exception(self):
        """Test ChunkingError is an Exception."""
        assert issubclass(ChunkingError, Exception)

    def test_too_many_chunks_error_is_chunking_error(self):
        """Test TooManyChunksError inherits from ChunkingError."""
        assert issubclass(TooManyChunksError, ChunkingError)

    def test_too_many_chunks_error_message(self):
        """Test TooManyChunksError can have custom message."""
        error = TooManyChunksError("Document has 1000 chunks")
        assert "1000 chunks" in str(error)
