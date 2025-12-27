"""Unit tests for extended IngestionJob model (Story 2.4).

Tests cover:
- New extracting status
- retry_count field
- error_type field
"""

from collection_model.domain.ingestion_job import IngestionJob


class TestIngestionJobExtended:
    """Tests for IngestionJob extensions from Story 2.4."""

    def test_extracting_status(self) -> None:
        """Test that extracting status is valid."""
        job = IngestionJob(
            blob_path="test/path.json",
            blob_etag='"etag-123"',
            container="test-container",
            source_id="test-source",
            content_length=100,
            status="extracting",
        )
        assert job.status == "extracting"

    def test_all_statuses(self) -> None:
        """Test all valid status values."""
        valid_statuses = ["queued", "processing", "extracting", "completed", "failed"]

        for status in valid_statuses:
            job = IngestionJob(
                blob_path="test/path.json",
                blob_etag='"etag-123"',
                container="test-container",
                source_id="test-source",
                content_length=100,
                status=status,
            )
            assert job.status == status

    def test_retry_count_default(self) -> None:
        """Test retry_count defaults to 0."""
        job = IngestionJob(
            blob_path="test/path.json",
            blob_etag='"etag-123"',
            container="test-container",
            source_id="test-source",
            content_length=100,
        )
        assert job.retry_count == 0

    def test_retry_count_explicit(self) -> None:
        """Test setting retry_count explicitly."""
        job = IngestionJob(
            blob_path="test/path.json",
            blob_etag='"etag-123"',
            container="test-container",
            source_id="test-source",
            content_length=100,
            retry_count=3,
        )
        assert job.retry_count == 3

    def test_error_type_default(self) -> None:
        """Test error_type defaults to None."""
        job = IngestionJob(
            blob_path="test/path.json",
            blob_etag='"etag-123"',
            container="test-container",
            source_id="test-source",
            content_length=100,
        )
        assert job.error_type is None

    def test_error_type_values(self) -> None:
        """Test valid error_type values."""
        valid_types = ["extraction", "storage", "validation", "config"]

        for error_type in valid_types:
            job = IngestionJob(
                blob_path="test/path.json",
                blob_etag='"etag-123"',
                container="test-container",
                source_id="test-source",
                content_length=100,
                status="failed",
                error_type=error_type,
            )
            assert job.error_type == error_type

    def test_model_dump_includes_new_fields(self) -> None:
        """Test that model_dump includes all new fields."""
        job = IngestionJob(
            blob_path="test/path.json",
            blob_etag='"etag-123"',
            container="test-container",
            source_id="test-source",
            content_length=100,
            status="failed",
            retry_count=2,
            error_type="extraction",
        )

        data = job.model_dump()

        assert "status" in data
        assert data["status"] == "failed"
        assert "retry_count" in data
        assert data["retry_count"] == 2
        assert "error_type" in data
        assert data["error_type"] == "extraction"
