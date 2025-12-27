"""Unit tests for extended IngestionQueue methods (Story 2.4).

Tests cover:
- update_job_status with new parameters
- increment_retry_count method
"""

import pytest

from collection_model.domain.ingestion_job import IngestionJob
from collection_model.infrastructure.ingestion_queue import IngestionQueue


class TestIngestionQueueExtended:
    """Tests for IngestionQueue extensions from Story 2.4."""

    @pytest.fixture
    def mock_db(self, mock_mongodb_client):
        """Create mock database."""
        return mock_mongodb_client["collection"]

    @pytest.fixture
    def ingestion_queue(self, mock_db):
        """Create ingestion queue with mock database."""
        return IngestionQueue(mock_db)

    @pytest.fixture
    def sample_job(self) -> IngestionJob:
        """Create sample ingestion job."""
        return IngestionJob(
            ingestion_id="test-ing-123",
            blob_path="test/path.json",
            blob_etag='"etag-123"',
            container="test-container",
            source_id="test-source",
            content_length=100,
            status="queued",
        )

    @pytest.mark.asyncio
    async def test_update_job_status_with_error_type(
        self,
        ingestion_queue: IngestionQueue,
        sample_job: IngestionJob,
    ) -> None:
        """Test updating job status with error_type."""
        # Queue the job first
        await ingestion_queue.queue_job(sample_job)

        # Update with error_type
        result = await ingestion_queue.update_job_status(
            ingestion_id=sample_job.ingestion_id,
            status="failed",
            error_message="Extraction failed",
            error_type="extraction",
        )

        assert result is True

        # Verify the update
        updated_job = await ingestion_queue.get_job_by_id(sample_job.ingestion_id)
        assert updated_job.status == "failed"
        assert updated_job.error_message == "Extraction failed"

    @pytest.mark.asyncio
    async def test_update_job_status_with_document_id(
        self,
        ingestion_queue: IngestionQueue,
        sample_job: IngestionJob,
    ) -> None:
        """Test updating job status with document_id on success."""
        # Queue the job first
        await ingestion_queue.queue_job(sample_job)

        # Update with document_id
        result = await ingestion_queue.update_job_status(
            ingestion_id=sample_job.ingestion_id,
            status="completed",
            document_id="doc-456",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_update_job_status_sets_processed_at(
        self,
        ingestion_queue: IngestionQueue,
        sample_job: IngestionJob,
    ) -> None:
        """Test that completed/failed status sets processed_at."""
        # Queue the job first
        await ingestion_queue.queue_job(sample_job)

        # Update to completed
        await ingestion_queue.update_job_status(
            ingestion_id=sample_job.ingestion_id,
            status="completed",
        )

        # Verify processed_at is set
        updated_job = await ingestion_queue.get_job_by_id(sample_job.ingestion_id)
        assert updated_job.processed_at is not None

    @pytest.mark.asyncio
    async def test_update_job_status_not_found(
        self,
        ingestion_queue: IngestionQueue,
    ) -> None:
        """Test updating non-existent job returns False."""
        result = await ingestion_queue.update_job_status(
            ingestion_id="nonexistent-id",
            status="completed",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_increment_retry_count(
        self,
        ingestion_queue: IngestionQueue,
        sample_job: IngestionJob,
        mock_db,
    ) -> None:
        """Test incrementing retry count."""
        # Queue the job first
        await ingestion_queue.queue_job(sample_job)

        # Mock find_one_and_update to return updated document
        async def mock_find_one_and_update(filter, update, return_document):
            # Simulate the increment
            doc = await mock_db["ingestion_queue"].find_one(filter)
            if doc:
                doc["retry_count"] = doc.get("retry_count", 0) + 1
                return doc
            return None

        mock_db["ingestion_queue"].find_one_and_update = mock_find_one_and_update

        # Increment retry count
        new_count = await ingestion_queue.increment_retry_count(sample_job.ingestion_id)

        assert new_count == 1

    @pytest.mark.asyncio
    async def test_increment_retry_count_not_found(
        self,
        ingestion_queue: IngestionQueue,
        mock_db,
    ) -> None:
        """Test incrementing retry count for non-existent job returns 0."""

        # Mock find_one_and_update to return None asynchronously
        async def mock_find_one_and_update(*args, **kwargs):
            return None

        mock_db["ingestion_queue"].find_one_and_update = mock_find_one_and_update

        new_count = await ingestion_queue.increment_retry_count("nonexistent-id")

        assert new_count == 0

    @pytest.mark.asyncio
    async def test_extracting_status_transition(
        self,
        ingestion_queue: IngestionQueue,
        sample_job: IngestionJob,
    ) -> None:
        """Test status transition to extracting."""
        # Queue the job first
        await ingestion_queue.queue_job(sample_job)

        # Update to processing
        await ingestion_queue.update_job_status(
            sample_job.ingestion_id,
            "processing",
        )

        # Update to extracting
        await ingestion_queue.update_job_status(
            sample_job.ingestion_id,
            "extracting",
        )

        updated_job = await ingestion_queue.get_job_by_id(sample_job.ingestion_id)
        assert updated_job.status == "extracting"
