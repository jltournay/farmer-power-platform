"""Unit tests for IngestionQueue."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from collection_model.domain.ingestion_job import IngestionJob
from collection_model.infrastructure.ingestion_queue import IngestionQueue
from pymongo.errors import DuplicateKeyError


class TestIngestionQueueJobQueuing:
    """Tests for job queuing functionality."""

    @pytest.mark.asyncio
    async def test_queue_job_success(self, mock_mongodb_client) -> None:
        """Test successful job queuing."""
        db = mock_mongodb_client["collection_model"]
        queue = IngestionQueue(db)

        job = IngestionJob(
            blob_path="results/WM-4521/tea/batch-001.json",
            blob_etag="0x8DB12345",
            container="qc-analyzer-landing",
            source_id="qc-analyzer",
            content_length=1024,
            metadata={"plantation_id": "WM-4521"},
        )

        result = await queue.queue_job(job)

        assert result is True

        # Verify job was stored
        stored = await db["ingestion_queue"].find_one({"blob_path": job.blob_path})
        assert stored is not None
        assert stored["source_id"] == "qc-analyzer"
        assert stored["status"] == "queued"

    @pytest.mark.asyncio
    async def test_queue_job_duplicate_returns_false(self) -> None:
        """Test that duplicate job returns False (idempotency)."""
        # Create a mock that raises DuplicateKeyError
        mock_collection = MagicMock()
        mock_collection.insert_one = AsyncMock(side_effect=DuplicateKeyError("duplicate key error"))

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        queue = IngestionQueue(mock_db)

        job = IngestionJob(
            blob_path="results/WM-4521/tea/batch-001.json",
            blob_etag="0x8DB12345",
            container="qc-analyzer-landing",
            source_id="qc-analyzer",
            content_length=1024,
        )

        result = await queue.queue_job(job)

        assert result is False

    @pytest.mark.asyncio
    async def test_queued_job_has_ingestion_id(self, mock_mongodb_client) -> None:
        """Test that queued jobs have unique ingestion_id."""
        db = mock_mongodb_client["collection_model"]
        queue = IngestionQueue(db)

        job = IngestionJob(
            blob_path="results/WM-4521/tea/batch-001.json",
            blob_etag="0x8DB12345",
            container="qc-analyzer-landing",
            source_id="qc-analyzer",
            content_length=1024,
        )

        await queue.queue_job(job)

        stored = await db["ingestion_queue"].find_one({"blob_path": job.blob_path})
        assert stored is not None
        assert "ingestion_id" in stored
        assert len(stored["ingestion_id"]) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_queued_job_preserves_trace_id(self, mock_mongodb_client) -> None:
        """Test that trace_id is preserved in queued job."""
        db = mock_mongodb_client["collection_model"]
        queue = IngestionQueue(db)

        job = IngestionJob(
            blob_path="results/WM-4521/tea/batch-001.json",
            blob_etag="0x8DB12345",
            container="qc-analyzer-landing",
            source_id="qc-analyzer",
            content_length=1024,
            trace_id="00-abc123-def456-01",
        )

        await queue.queue_job(job)

        stored = await db["ingestion_queue"].find_one({"blob_path": job.blob_path})
        assert stored is not None
        assert stored["trace_id"] == "00-abc123-def456-01"


class TestIngestionQueueRetrieval:
    """Tests for job retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_pending_jobs_returns_queued(self, mock_mongodb_client) -> None:
        """Test that get_pending_jobs returns jobs with queued status."""
        db = mock_mongodb_client["collection_model"]
        queue = IngestionQueue(db)

        # Insert jobs with different statuses
        await db["ingestion_queue"].insert_one(
            {
                "ingestion_id": "job-1",
                "blob_path": "path1.json",
                "blob_etag": "etag1",
                "container": "test",
                "source_id": "test",
                "content_length": 100,
                "status": "queued",
                "created_at": datetime.now(UTC),
                "metadata": {},
            }
        )
        await db["ingestion_queue"].insert_one(
            {
                "ingestion_id": "job-2",
                "blob_path": "path2.json",
                "blob_etag": "etag2",
                "container": "test",
                "source_id": "test",
                "content_length": 100,
                "status": "processing",
                "created_at": datetime.now(UTC),
                "metadata": {},
            }
        )
        await db["ingestion_queue"].insert_one(
            {
                "ingestion_id": "job-3",
                "blob_path": "path3.json",
                "blob_etag": "etag3",
                "container": "test",
                "source_id": "test",
                "content_length": 100,
                "status": "queued",
                "created_at": datetime.now(UTC),
                "metadata": {},
            }
        )

        jobs = await queue.get_pending_jobs()

        assert len(jobs) == 2
        assert all(job.status == "queued" for job in jobs)

    @pytest.mark.asyncio
    async def test_get_pending_jobs_respects_limit(self, mock_mongodb_client) -> None:
        """Test that get_pending_jobs respects the limit parameter."""
        db = mock_mongodb_client["collection_model"]
        queue = IngestionQueue(db)

        # Insert multiple jobs
        for i in range(5):
            await db["ingestion_queue"].insert_one(
                {
                    "ingestion_id": f"job-{i}",
                    "blob_path": f"path{i}.json",
                    "blob_etag": f"etag{i}",
                    "container": "test",
                    "source_id": "test",
                    "content_length": 100,
                    "status": "queued",
                    "created_at": datetime.now(UTC),
                    "metadata": {},
                }
            )

        jobs = await queue.get_pending_jobs(limit=3)

        assert len(jobs) == 3

    @pytest.mark.asyncio
    async def test_get_job_by_id(self, mock_mongodb_client) -> None:
        """Test retrieving job by ingestion_id."""
        db = mock_mongodb_client["collection_model"]
        queue = IngestionQueue(db)

        await db["ingestion_queue"].insert_one(
            {
                "ingestion_id": "test-job-123",
                "blob_path": "path.json",
                "blob_etag": "etag",
                "container": "test",
                "source_id": "test",
                "content_length": 100,
                "status": "queued",
                "created_at": datetime.now(UTC),
                "metadata": {},
            }
        )

        job = await queue.get_job_by_id("test-job-123")

        assert job is not None
        assert job.ingestion_id == "test-job-123"

    @pytest.mark.asyncio
    async def test_get_job_by_id_returns_none_for_missing(self, mock_mongodb_client) -> None:
        """Test that get_job_by_id returns None for non-existent job."""
        db = mock_mongodb_client["collection_model"]
        queue = IngestionQueue(db)

        job = await queue.get_job_by_id("non-existent-job")

        assert job is None


class TestIngestionQueueStatusUpdate:
    """Tests for job status updates."""

    @pytest.mark.asyncio
    async def test_update_job_status_success(self, mock_mongodb_client) -> None:
        """Test successful status update."""
        db = mock_mongodb_client["collection_model"]
        queue = IngestionQueue(db)

        await db["ingestion_queue"].insert_one(
            {
                "ingestion_id": "test-job",
                "blob_path": "path.json",
                "blob_etag": "etag",
                "container": "test",
                "source_id": "test",
                "content_length": 100,
                "status": "queued",
                "created_at": datetime.now(UTC),
                "metadata": {},
            }
        )

        result = await queue.update_job_status("test-job", "processing")

        assert result is True

        updated = await db["ingestion_queue"].find_one({"ingestion_id": "test-job"})
        assert updated["status"] == "processing"

    @pytest.mark.asyncio
    async def test_update_job_status_sets_processed_at(self, mock_mongodb_client) -> None:
        """Test that completed/failed status sets processed_at."""
        db = mock_mongodb_client["collection_model"]
        queue = IngestionQueue(db)

        await db["ingestion_queue"].insert_one(
            {
                "ingestion_id": "test-job",
                "blob_path": "path.json",
                "blob_etag": "etag",
                "container": "test",
                "source_id": "test",
                "content_length": 100,
                "status": "processing",
                "created_at": datetime.now(UTC),
                "metadata": {},
            }
        )

        await queue.update_job_status("test-job", "completed")

        updated = await db["ingestion_queue"].find_one({"ingestion_id": "test-job"})
        assert updated["status"] == "completed"
        assert "processed_at" in updated

    @pytest.mark.asyncio
    async def test_update_job_status_sets_error_message(self, mock_mongodb_client) -> None:
        """Test that failed status can include error message."""
        db = mock_mongodb_client["collection_model"]
        queue = IngestionQueue(db)

        await db["ingestion_queue"].insert_one(
            {
                "ingestion_id": "test-job",
                "blob_path": "path.json",
                "blob_etag": "etag",
                "container": "test",
                "source_id": "test",
                "content_length": 100,
                "status": "processing",
                "created_at": datetime.now(UTC),
                "metadata": {},
            }
        )

        await queue.update_job_status("test-job", "failed", error_message="Validation failed")

        updated = await db["ingestion_queue"].find_one({"ingestion_id": "test-job"})
        assert updated["status"] == "failed"
        assert updated["error_message"] == "Validation failed"

    @pytest.mark.asyncio
    async def test_update_job_status_returns_false_for_missing(self, mock_mongodb_client) -> None:
        """Test that updating non-existent job returns False."""
        db = mock_mongodb_client["collection_model"]
        queue = IngestionQueue(db)

        result = await queue.update_job_status("non-existent", "processing")

        assert result is False


class TestIngestionJobModel:
    """Tests for IngestionJob Pydantic model."""

    def test_ingestion_job_default_values(self) -> None:
        """Test IngestionJob default values."""
        job = IngestionJob(
            blob_path="test.json",
            blob_etag="0x123",
            container="test-container",
            source_id="test-source",
            content_length=100,
        )

        assert job.status == "queued"
        assert job.metadata == {}
        assert job.error_message is None
        assert job.processed_at is None
        assert job.trace_id is None
        assert len(job.ingestion_id) == 36  # UUID format

    def test_ingestion_job_with_all_fields(self) -> None:
        """Test IngestionJob with all fields specified."""
        now = datetime.now(UTC)
        job = IngestionJob(
            ingestion_id="custom-id",
            trace_id="trace-123",
            blob_path="test.json",
            blob_etag="0x123",
            container="test-container",
            source_id="test-source",
            content_length=100,
            status="processing",
            created_at=now,
            metadata={"key": "value"},
            error_message="test error",
            processed_at=now,
        )

        assert job.ingestion_id == "custom-id"
        assert job.trace_id == "trace-123"
        assert job.metadata == {"key": "value"}
        assert job.error_message == "test error"

    def test_ingestion_job_serialization(self) -> None:
        """Test IngestionJob model_dump for MongoDB storage."""
        job = IngestionJob(
            blob_path="test.json",
            blob_etag="0x123",
            container="test-container",
            source_id="test-source",
            content_length=100,
        )

        data = job.model_dump()

        assert "ingestion_id" in data
        assert "blob_path" in data
        assert "status" in data
        assert "created_at" in data
