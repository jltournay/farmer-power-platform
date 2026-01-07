"""Tests for fp_knowledge.models module."""

import pytest
from fp_knowledge.models import (
    ChunkResult,
    DocumentMetadata,
    DocumentStatus,
    ExtractionJobResult,
    JobStatus,
    KnowledgeDomain,
    OperationResult,
    RagChunk,
    RagDocument,
    RagDocumentInput,
    SourceFileInfo,
)
from pydantic import ValidationError


class TestKnowledgeDomain:
    """Tests for KnowledgeDomain enum."""

    def test_valid_domains(self) -> None:
        """Test all valid domain values."""
        assert KnowledgeDomain.PLANT_DISEASES.value == "plant_diseases"
        assert KnowledgeDomain.TEA_CULTIVATION.value == "tea_cultivation"
        assert KnowledgeDomain.WEATHER_PATTERNS.value == "weather_patterns"
        assert KnowledgeDomain.QUALITY_STANDARDS.value == "quality_standards"
        assert KnowledgeDomain.REGIONAL_CONTEXT.value == "regional_context"

    def test_domain_count(self) -> None:
        """Test that we have expected number of domains."""
        assert len(KnowledgeDomain) == 5


class TestDocumentStatus:
    """Tests for DocumentStatus enum."""

    def test_valid_statuses(self) -> None:
        """Test all valid status values."""
        assert DocumentStatus.DRAFT.value == "draft"
        assert DocumentStatus.STAGED.value == "staged"
        assert DocumentStatus.ACTIVE.value == "active"
        assert DocumentStatus.ARCHIVED.value == "archived"

    def test_status_count(self) -> None:
        """Test that we have expected number of statuses."""
        assert len(DocumentStatus) == 4


class TestDocumentMetadata:
    """Tests for DocumentMetadata model."""

    def test_required_author(self) -> None:
        """Test that author is required."""
        with pytest.raises(ValidationError):
            DocumentMetadata()  # type: ignore

    def test_minimal_metadata(self) -> None:
        """Test creation with only required field."""
        metadata = DocumentMetadata(author="test-author")
        assert metadata.author == "test-author"
        assert metadata.source is None
        assert metadata.region is None
        assert metadata.season is None
        assert metadata.tags == []

    def test_full_metadata(self) -> None:
        """Test creation with all fields."""
        metadata = DocumentMetadata(
            author="dr-kimani",
            source="Tea Research Foundation",
            region="Kenya",
            season="dry_season",
            tags=["disease", "tea"],
        )
        assert metadata.author == "dr-kimani"
        assert metadata.source == "Tea Research Foundation"
        assert metadata.region == "Kenya"
        assert metadata.season == "dry_season"
        assert metadata.tags == ["disease", "tea"]


class TestRagDocumentInput:
    """Tests for RagDocumentInput model."""

    def test_with_content(self) -> None:
        """Test document input with inline content."""
        doc = RagDocumentInput(
            document_id="test-doc",
            title="Test Document",
            domain=KnowledgeDomain.PLANT_DISEASES,
            content="# Test Content",
        )
        assert doc.document_id == "test-doc"
        assert doc.title == "Test Document"
        assert doc.domain == KnowledgeDomain.PLANT_DISEASES
        assert doc.content == "# Test Content"
        assert doc.file is None
        assert doc.has_content_or_file()

    def test_with_file(self) -> None:
        """Test document input with file reference."""
        doc = RagDocumentInput(
            document_id="test-doc",
            title="Test Document",
            domain=KnowledgeDomain.TEA_CULTIVATION,
            file="documents/guide.pdf",
        )
        assert doc.file == "documents/guide.pdf"
        assert doc.content is None
        assert doc.has_content_or_file()

    def test_neither_content_nor_file(self) -> None:
        """Test document input with neither content nor file."""
        doc = RagDocumentInput(
            document_id="test-doc",
            title="Test Document",
            domain=KnowledgeDomain.WEATHER_PATTERNS,
        )
        assert not doc.has_content_or_file()


class TestRagDocument:
    """Tests for RagDocument model."""

    def test_minimal_document(self) -> None:
        """Test creation with required fields only."""
        doc = RagDocument(
            id="test:v1",
            document_id="test",
            version=1,
            title="Test Document",
            domain="plant_diseases",
            content="Content",
            status=DocumentStatus.DRAFT,
            metadata=DocumentMetadata(author="test"),
        )
        assert doc.id == "test:v1"
        assert doc.version == 1
        assert doc.status == DocumentStatus.DRAFT

    def test_full_document(self, sample_document: RagDocument) -> None:
        """Test document with all fields."""
        assert sample_document.document_id == "blister-blight-guide"
        assert sample_document.metadata.author == "dr-kimani"
        assert sample_document.source_file is None


class TestSourceFileInfo:
    """Tests for SourceFileInfo model."""

    def test_minimal_source_file(self) -> None:
        """Test creation with required fields."""
        info = SourceFileInfo(
            filename="guide.pdf",
            file_type="pdf",
        )
        assert info.filename == "guide.pdf"
        assert info.file_type == "pdf"
        assert info.blob_path is None

    def test_full_source_file(self) -> None:
        """Test creation with all fields."""
        info = SourceFileInfo(
            filename="guide.pdf",
            file_type="pdf",
            blob_path="docs/guide.pdf",
            file_size_bytes=1024,
            extraction_method="azure_doc_intel",
            extraction_confidence=0.95,
            page_count=10,
        )
        assert info.file_size_bytes == 1024
        assert info.extraction_confidence == 0.95
        assert info.page_count == 10


class TestJobStatus:
    """Tests for JobStatus enum."""

    def test_valid_statuses(self) -> None:
        """Test all valid job status values."""
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.IN_PROGRESS.value == "in_progress"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"


class TestExtractionJobResult:
    """Tests for ExtractionJobResult model."""

    def test_minimal_result(self) -> None:
        """Test creation with required fields."""
        result = ExtractionJobResult(
            job_id="job-123",
            document_id="test-doc",
            status=JobStatus.PENDING,
        )
        assert result.job_id == "job-123"
        assert result.status == JobStatus.PENDING
        assert result.progress_percent == 0

    def test_in_progress_result(self, sample_extraction_job: ExtractionJobResult) -> None:
        """Test in-progress extraction job."""
        assert sample_extraction_job.status == JobStatus.IN_PROGRESS
        assert sample_extraction_job.progress_percent == 50
        assert sample_extraction_job.pages_processed == 5
        assert sample_extraction_job.total_pages == 10


class TestChunkResult:
    """Tests for ChunkResult model."""

    def test_chunk_result(self) -> None:
        """Test chunk result creation."""
        result = ChunkResult(
            chunks_created=10,
            total_char_count=5000,
            total_word_count=1000,
        )
        assert result.chunks_created == 10
        assert result.total_char_count == 5000
        assert result.total_word_count == 1000


class TestRagChunk:
    """Tests for RagChunk model."""

    def test_minimal_chunk(self) -> None:
        """Test creation with required fields."""
        chunk = RagChunk(
            chunk_id="doc-v1-chunk-0",
            document_id="doc",
            document_version=1,
            chunk_index=0,
            content="Chunk content",
            word_count=2,
            char_count=13,
        )
        assert chunk.chunk_id == "doc-v1-chunk-0"
        assert chunk.chunk_index == 0
        assert chunk.section_title is None


class TestOperationResult:
    """Tests for OperationResult model."""

    def test_success_result(self) -> None:
        """Test successful operation result."""
        result = OperationResult(
            success=True,
            message="Operation completed",
        )
        assert result.success is True
        assert result.error is None

    def test_failure_result(self) -> None:
        """Test failed operation result."""
        result = OperationResult(
            success=False,
            error="Something went wrong",
        )
        assert result.success is False
        assert result.error == "Something went wrong"
