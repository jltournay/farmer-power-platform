"""Integration tests for document extraction pipeline.

Story 0.75.10b: Basic PDF/Markdown Extraction

This module tests the full extraction pipeline from PDF bytes through
document extraction, job tracking, and content update. Uses mock MongoDB
but exercises real extraction logic with programmatically generated PDFs.
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pymupdf
import pytest
from ai_model.domain.extraction_job import ExtractionJob, ExtractionJobStatus
from ai_model.domain.rag_document import (
    FileType,
    RagDocument,
    RAGDocumentMetadata,
    RagDocumentStatus,
    SourceFile,
)
from ai_model.infrastructure.repositories.extraction_job_repository import (
    ExtractionJobRepository,
)
from ai_model.infrastructure.repositories.rag_document_repository import (
    RagDocumentRepository,
)
from ai_model.services.document_extractor import DocumentExtractor
from ai_model.services.extraction_workflow import ExtractionWorkflow


def create_test_pdf(text: str, pages: int = 1) -> bytes:
    """Create a minimal PDF for integration testing."""
    doc = pymupdf.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((50, 50), f"Page {i + 1}: {text}")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


class TestExtractionPipelineIntegration:
    """Integration tests for full extraction pipeline."""

    @pytest.fixture
    def mock_db(self):
        """Create mock MongoDB database."""
        db = MagicMock()
        # Mock extraction_jobs collection
        jobs_collection = MagicMock()
        db.__getitem__ = MagicMock(side_effect=lambda name: jobs_collection if name == "extraction_jobs" else MagicMock())
        return db

    @pytest.fixture
    def mock_blob_client(self):
        """Create mock blob storage client."""
        client = MagicMock()
        client.download_to_bytes = AsyncMock()
        return client

    @pytest.fixture
    def sample_document(self) -> RagDocument:
        """Create sample RAG document with source file."""
        return RagDocument(
            id="test-doc:v1",
            document_id="test-doc",
            version=1,
            title="Test Document",
            domain="plant_diseases",
            content="",
            status=RagDocumentStatus.DRAFT,
            metadata=RAGDocumentMetadata(author="Test Author"),
            source_file=SourceFile(
                filename="test.pdf",
                file_type=FileType.PDF,
                blob_path="documents/test.pdf",
                file_size_bytes=1024,
            ),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    @pytest.mark.asyncio
    async def test_full_pdf_extraction_pipeline(
        self,
        mock_db,
        mock_blob_client,
        sample_document,
    ):
        """Test full pipeline: PDF download → extraction → job completion."""
        # Arrange
        pdf_content = create_test_pdf("Integration test content", pages=5)
        mock_blob_client.download_to_bytes.return_value = pdf_content

        # Mock document repository
        doc_repo = MagicMock(spec=RagDocumentRepository)
        doc_repo.get_by_version = AsyncMock(return_value=sample_document)
        doc_repo.update = AsyncMock(return_value=sample_document)

        # Mock job repository with tracking
        created_jobs = []
        updated_jobs = []

        async def mock_create(job: ExtractionJob) -> ExtractionJob:
            created_jobs.append(job)
            return job

        async def mock_get_by_job_id(job_id: str) -> ExtractionJob | None:
            for job in created_jobs:
                if job.job_id == job_id:
                    return job
            return None

        async def mock_mark_completed(job_id: str, pages_processed: int, total_pages: int) -> ExtractionJob:
            for job in created_jobs:
                if job.job_id == job_id:
                    job.status = ExtractionJobStatus.COMPLETED
                    job.progress_percent = 100
                    job.pages_processed = pages_processed
                    job.total_pages = total_pages
                    updated_jobs.append(job)
                    return job
            return None

        job_repo = MagicMock(spec=ExtractionJobRepository)
        job_repo.create = AsyncMock(side_effect=mock_create)
        job_repo.get_by_job_id = AsyncMock(side_effect=mock_get_by_job_id)
        job_repo.mark_completed = AsyncMock(side_effect=mock_mark_completed)
        job_repo.mark_failed = AsyncMock()
        job_repo.update_progress = AsyncMock()

        # Create real extractor (no mocking - this is the integration point)
        extractor = DocumentExtractor()

        # Create workflow with mocked dependencies
        workflow = ExtractionWorkflow(
            document_repository=doc_repo,
            job_repository=job_repo,
            blob_client=mock_blob_client,
            extractor=extractor,
        )

        # Act
        job_id = await workflow.start_extraction("test-doc", version=1)

        # Wait for background task to complete
        await asyncio.sleep(0.5)

        # Assert
        assert job_id is not None
        assert len(created_jobs) == 1
        assert created_jobs[0].document_id == "test-doc"

        # Verify blob was downloaded
        mock_blob_client.download_to_bytes.assert_called_once_with("documents/test.pdf")

        # Verify document was updated with extraction results
        doc_repo.update.assert_called()
        update_call_args = doc_repo.update.call_args
        update_data = update_call_args[0][1]

        # Should have updated source_file with extraction metadata
        assert "source_file.extraction_method" in update_data or "content" in update_data

    @pytest.mark.asyncio
    async def test_extraction_pipeline_handles_corrupted_pdf(
        self,
        mock_db,
        mock_blob_client,
        sample_document,
    ):
        """Test pipeline handles corrupted PDF gracefully."""
        # Arrange - corrupted PDF content
        mock_blob_client.download_to_bytes.return_value = b"Not a valid PDF"

        doc_repo = MagicMock(spec=RagDocumentRepository)
        doc_repo.get_by_version = AsyncMock(return_value=sample_document)

        failed_jobs = []

        async def mock_create(job: ExtractionJob) -> ExtractionJob:
            return job

        async def mock_mark_failed(job_id: str, error_message: str) -> ExtractionJob:
            job = ExtractionJob(
                id=job_id,
                job_id=job_id,
                document_id="test-doc",
                status=ExtractionJobStatus.FAILED,
                error_message=error_message,
            )
            failed_jobs.append(job)
            return job

        job_repo = MagicMock(spec=ExtractionJobRepository)
        job_repo.create = AsyncMock(side_effect=mock_create)
        job_repo.mark_failed = AsyncMock(side_effect=mock_mark_failed)
        job_repo.update_progress = AsyncMock()

        extractor = DocumentExtractor()
        workflow = ExtractionWorkflow(
            document_repository=doc_repo,
            job_repository=job_repo,
            blob_client=mock_blob_client,
            extractor=extractor,
        )

        # Act
        job_id = await workflow.start_extraction("test-doc", version=1)

        # Wait for background task
        await asyncio.sleep(0.5)

        # Assert - job should be marked as failed
        assert len(failed_jobs) == 1
        assert "Corrupted" in failed_jobs[0].error_message or "parse" in failed_jobs[0].error_message.lower()

    @pytest.mark.asyncio
    async def test_extraction_pipeline_markdown_file(
        self,
        mock_db,
        mock_blob_client,
    ):
        """Test pipeline with Markdown file (no PDF extraction needed)."""
        # Arrange - Markdown content
        md_content = b"# Test Document\n\n## Section 1\n\nThis is test content.\n\n- Item 1\n- Item 2"
        mock_blob_client.download_to_bytes.return_value = md_content

        md_document = RagDocument(
            id="md-doc:v1",
            document_id="md-doc",
            version=1,
            title="Markdown Document",
            domain="plant_diseases",
            content="",
            status=RagDocumentStatus.DRAFT,
            metadata=RAGDocumentMetadata(author="Test Author"),
            source_file=SourceFile(
                filename="guide.md",
                file_type=FileType.MD,
                blob_path="documents/guide.md",
                file_size_bytes=len(md_content),
            ),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        doc_repo = MagicMock(spec=RagDocumentRepository)
        doc_repo.get_by_version = AsyncMock(return_value=md_document)
        doc_repo.update = AsyncMock(return_value=md_document)

        completed_jobs = []

        async def mock_create(job: ExtractionJob) -> ExtractionJob:
            return job

        async def mock_mark_completed(job_id: str, pages_processed: int, total_pages: int) -> ExtractionJob:
            job = ExtractionJob(
                id=job_id,
                job_id=job_id,
                document_id="md-doc",
                status=ExtractionJobStatus.COMPLETED,
                progress_percent=100,
                pages_processed=pages_processed,
                total_pages=total_pages,
            )
            completed_jobs.append(job)
            return job

        job_repo = MagicMock(spec=ExtractionJobRepository)
        job_repo.create = AsyncMock(side_effect=mock_create)
        job_repo.mark_completed = AsyncMock(side_effect=mock_mark_completed)
        job_repo.update_progress = AsyncMock()

        extractor = DocumentExtractor()
        workflow = ExtractionWorkflow(
            document_repository=doc_repo,
            job_repository=job_repo,
            blob_client=mock_blob_client,
            extractor=extractor,
        )

        # Act
        job_id = await workflow.start_extraction("md-doc", version=1)

        # Wait for background task
        await asyncio.sleep(0.5)

        # Assert - Markdown extraction should complete successfully
        assert len(completed_jobs) == 1
        assert completed_jobs[0].status == ExtractionJobStatus.COMPLETED

        # Verify content was extracted
        doc_repo.update.assert_called()
        update_call_args = doc_repo.update.call_args
        update_data = update_call_args[0][1]

        # Content should contain the markdown text
        if "content" in update_data:
            assert "Test Document" in update_data["content"]
