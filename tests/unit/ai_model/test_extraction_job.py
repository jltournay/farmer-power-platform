"""Unit tests for ExtractionJob model and repository.

Story 0.75.10b: Basic PDF/Markdown Extraction

Tests cover:
- ExtractionJob model creation and validation
- ExtractionJobRepository CRUD operations
- Job status updates and progress tracking
- Error handling scenarios
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from ai_model.domain.extraction_job import ExtractionJob, ExtractionJobStatus
from ai_model.infrastructure.repositories.extraction_job_repository import (
    ExtractionJobRepository,
)

# ============================================
# ExtractionJob Model Tests
# ============================================


class TestExtractionJobModel:
    """Tests for ExtractionJob Pydantic model."""

    def test_create_job_with_defaults(self):
        """Job created with default values."""
        job = ExtractionJob(
            id="job-123",
            job_id="job-123",
            document_id="doc-456",
        )

        assert job.job_id == "job-123"
        assert job.document_id == "doc-456"
        assert job.status == ExtractionJobStatus.PENDING
        assert job.progress_percent == 0
        assert job.pages_processed == 0
        assert job.total_pages == 0
        assert job.error_message is None
        assert job.completed_at is None

    def test_create_job_with_all_fields(self):
        """Job created with all fields specified."""
        now = datetime.now(UTC)
        job = ExtractionJob(
            id="job-123",
            job_id="job-123",
            document_id="doc-456",
            status=ExtractionJobStatus.IN_PROGRESS,
            progress_percent=50,
            pages_processed=5,
            total_pages=10,
            error_message=None,
            started_at=now,
            completed_at=None,
        )

        assert job.status == ExtractionJobStatus.IN_PROGRESS
        assert job.progress_percent == 50
        assert job.pages_processed == 5
        assert job.total_pages == 10

    def test_job_progress_validation(self):
        """Progress percent must be between 0 and 100."""
        # Valid at boundaries
        job_min = ExtractionJob(
            id="job-1",
            job_id="job-1",
            document_id="doc-1",
            progress_percent=0,
        )
        assert job_min.progress_percent == 0

        job_max = ExtractionJob(
            id="job-2",
            job_id="job-2",
            document_id="doc-2",
            progress_percent=100,
        )
        assert job_max.progress_percent == 100

        # Invalid values raise validation error
        with pytest.raises(ValueError):
            ExtractionJob(
                id="job-3",
                job_id="job-3",
                document_id="doc-3",
                progress_percent=101,
            )

        with pytest.raises(ValueError):
            ExtractionJob(
                id="job-4",
                job_id="job-4",
                document_id="doc-4",
                progress_percent=-1,
            )

    def test_job_status_enum_values(self):
        """ExtractionJobStatus enum has expected values."""
        assert ExtractionJobStatus.PENDING.value == "pending"
        assert ExtractionJobStatus.IN_PROGRESS.value == "in_progress"
        assert ExtractionJobStatus.COMPLETED.value == "completed"
        assert ExtractionJobStatus.FAILED.value == "failed"

    def test_job_serialization(self):
        """Job can be serialized to dict."""
        job = ExtractionJob(
            id="job-123",
            job_id="job-123",
            document_id="doc-456",
            status=ExtractionJobStatus.COMPLETED,
        )

        data = job.model_dump()

        assert data["job_id"] == "job-123"
        assert data["document_id"] == "doc-456"
        assert data["status"] == "completed"


# ============================================
# ExtractionJobRepository Tests
# ============================================


class TestExtractionJobRepository:
    """Tests for ExtractionJobRepository MongoDB operations."""

    @pytest.fixture
    def mock_db(self):
        """Create mock MongoDB database."""
        db = MagicMock()
        collection = MagicMock()
        db.__getitem__ = MagicMock(return_value=collection)
        return db

    @pytest.fixture
    def repository(self, mock_db):
        """Create repository with mock database."""
        return ExtractionJobRepository(mock_db)

    @pytest.mark.asyncio
    async def test_create_job(self, repository, mock_db):
        """Create job inserts into MongoDB."""
        mock_db["extraction_jobs"].insert_one = AsyncMock()

        job = ExtractionJob(
            id="job-123",
            job_id="job-123",
            document_id="doc-456",
        )

        result = await repository.create(job)

        assert result == job
        mock_db["extraction_jobs"].insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_job_id_found(self, repository, mock_db):
        """Get job by job_id returns job when found."""
        mock_db["extraction_jobs"].find_one = AsyncMock(
            return_value={
                "id": "job-123",
                "job_id": "job-123",
                "document_id": "doc-456",
                "status": "in_progress",
                "progress_percent": 50,
                "pages_processed": 5,
                "total_pages": 10,
                "error_message": None,
                "started_at": datetime.now(UTC),
                "completed_at": None,
            }
        )

        result = await repository.get_by_job_id("job-123")

        assert result is not None
        assert result.job_id == "job-123"
        assert result.status == ExtractionJobStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_get_by_job_id_not_found(self, repository, mock_db):
        """Get job by job_id returns None when not found."""
        mock_db["extraction_jobs"].find_one = AsyncMock(return_value=None)

        result = await repository.get_by_job_id("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_progress(self, repository, mock_db):
        """Update progress updates job status and counts."""
        mock_db["extraction_jobs"].find_one_and_update = AsyncMock(
            return_value={
                "id": "job-123",
                "job_id": "job-123",
                "document_id": "doc-456",
                "status": "in_progress",
                "progress_percent": 50,
                "pages_processed": 5,
                "total_pages": 10,
                "error_message": None,
                "started_at": datetime.now(UTC),
                "completed_at": None,
            }
        )

        result = await repository.update_progress(
            job_id="job-123",
            progress_percent=50,
            pages_processed=5,
            total_pages=10,
        )

        assert result is not None
        assert result.progress_percent == 50
        mock_db["extraction_jobs"].find_one_and_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_completed(self, repository, mock_db):
        """Mark completed updates status and sets completed_at."""
        now = datetime.now(UTC)
        mock_db["extraction_jobs"].find_one_and_update = AsyncMock(
            return_value={
                "id": "job-123",
                "job_id": "job-123",
                "document_id": "doc-456",
                "status": "completed",
                "progress_percent": 100,
                "pages_processed": 10,
                "total_pages": 10,
                "error_message": None,
                "started_at": now,
                "completed_at": now,
            }
        )

        result = await repository.mark_completed(
            job_id="job-123",
            pages_processed=10,
            total_pages=10,
        )

        assert result is not None
        assert result.status == ExtractionJobStatus.COMPLETED
        assert result.progress_percent == 100

    @pytest.mark.asyncio
    async def test_mark_failed(self, repository, mock_db):
        """Mark failed updates status and sets error message."""
        now = datetime.now(UTC)
        mock_db["extraction_jobs"].find_one_and_update = AsyncMock(
            return_value={
                "id": "job-123",
                "job_id": "job-123",
                "document_id": "doc-456",
                "status": "failed",
                "progress_percent": 25,
                "pages_processed": 2,
                "total_pages": 8,
                "error_message": "PDF is password-protected",
                "started_at": now,
                "completed_at": now,
            }
        )

        result = await repository.mark_failed(
            job_id="job-123",
            error_message="PDF is password-protected",
        )

        assert result is not None
        assert result.status == ExtractionJobStatus.FAILED
        assert result.error_message == "PDF is password-protected"


# ============================================
# Error Scenario Tests
# ============================================


class TestExtractionJobErrors:
    """Tests for error handling in extraction jobs."""

    def test_failed_job_has_error_message(self):
        """Failed job should have error message."""
        job = ExtractionJob(
            id="job-123",
            job_id="job-123",
            document_id="doc-456",
            status=ExtractionJobStatus.FAILED,
            error_message="Corrupted PDF: invalid header",
        )

        assert job.status == ExtractionJobStatus.FAILED
        assert "Corrupted PDF" in job.error_message

    def test_failed_job_has_completed_at(self):
        """Failed job should have completed_at timestamp."""
        now = datetime.now(UTC)
        job = ExtractionJob(
            id="job-123",
            job_id="job-123",
            document_id="doc-456",
            status=ExtractionJobStatus.FAILED,
            error_message="Password-protected",
            completed_at=now,
        )

        assert job.completed_at is not None
        assert job.completed_at == now
