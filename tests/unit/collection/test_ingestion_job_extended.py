"""Unit tests for extended IngestionJob model (Story 2.4, 2.7).

Tests cover:
- Story 2.4: extracting status, retry_count, error_type
- Story 2.7: content, linkage, is_pull_mode, is_blob_mode, validation
"""

import pytest
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


class TestIngestionJobPullMode:
    """Tests for IngestionJob pull mode extensions from Story 2.7."""

    def test_pull_mode_with_content(self) -> None:
        """Test creating pull mode job with inline content."""
        job = IngestionJob(
            source_id="weather-api",
            content=b'{"temperature": 22.5}',
        )
        assert job.content == b'{"temperature": 22.5}'
        assert job.blob_path is None

    def test_pull_mode_with_linkage(self) -> None:
        """Test pull mode job with linkage from iteration."""
        job = IngestionJob(
            source_id="weather-api",
            content=b'{"temperature": 22.5}',
            linkage={"region_id": "nyeri", "name": "Nyeri"},
        )
        assert job.linkage == {"region_id": "nyeri", "name": "Nyeri"}

    def test_linkage_defaults_to_none(self) -> None:
        """Test linkage defaults to None."""
        job = IngestionJob(
            source_id="weather-api",
            content=b'{"temperature": 22.5}',
        )
        assert job.linkage is None

    def test_is_pull_mode_true_when_content_set(self) -> None:
        """Test is_pull_mode returns True when content is set."""
        job = IngestionJob(
            source_id="weather-api",
            content=b'{"data": "test"}',
        )
        assert job.is_pull_mode is True

    def test_is_pull_mode_false_when_blob_path_set(self) -> None:
        """Test is_pull_mode returns False for blob mode."""
        job = IngestionJob(
            blob_path="test/path.json",
            blob_etag='"etag-123"',
            container="test-container",
            source_id="test-source",
            content_length=100,
        )
        assert job.is_pull_mode is False

    def test_is_blob_mode_true_when_blob_path_set(self) -> None:
        """Test is_blob_mode returns True when blob_path is set."""
        job = IngestionJob(
            blob_path="test/path.json",
            blob_etag='"etag-123"',
            container="test-container",
            source_id="test-source",
            content_length=100,
        )
        assert job.is_blob_mode is True

    def test_is_blob_mode_false_when_content_set(self) -> None:
        """Test is_blob_mode returns False for pull mode."""
        job = IngestionJob(
            source_id="weather-api",
            content=b'{"data": "test"}',
        )
        assert job.is_blob_mode is False

    def test_validation_requires_blob_path_or_content(self) -> None:
        """Test validation fails when neither blob_path nor content is set."""
        with pytest.raises(ValueError, match=r"Either blob_path.*or content.*must be set"):
            IngestionJob(
                source_id="test-source",
            )

    def test_both_blob_path_and_content_allowed(self) -> None:
        """Test job can have both blob_path and content (edge case)."""
        job = IngestionJob(
            blob_path="test/path.json",
            blob_etag='"etag-123"',
            container="test-container",
            source_id="test-source",
            content_length=100,
            content=b'{"data": "test"}',
        )
        # Both modes return True when both are set
        assert job.is_pull_mode is True
        assert job.is_blob_mode is True

    def test_model_dump_includes_pull_mode_fields(self) -> None:
        """Test model_dump includes content and linkage fields."""
        job = IngestionJob(
            source_id="weather-api",
            content=b'{"temperature": 22.5}',
            linkage={"region_id": "nyeri"},
        )

        data = job.model_dump()

        assert "content" in data
        assert data["content"] == b'{"temperature": 22.5}'
        assert "linkage" in data
        assert data["linkage"] == {"region_id": "nyeri"}
