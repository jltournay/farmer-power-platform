"""Unit tests for Document, SearchResult, and related models.

Story 0.6.1: Shared Pydantic Models in fp-common
"""

from datetime import UTC, datetime

import pytest
from fp_common.models import (
    Document,
    ExtractionMetadata,
    IngestionMetadata,
    RawDocumentRef,
    SearchResult,
)
from pydantic import ValidationError


class TestRawDocumentRef:
    """Tests for RawDocumentRef model."""

    def test_create_valid_raw_document_ref(self) -> None:
        """Test creating a valid RawDocumentRef."""
        ref = RawDocumentRef(
            blob_container="quality-data",
            blob_path="factory-001/2025-12-28/batch-001.json",
            content_hash="sha256:abc123",
            size_bytes=1024,
            stored_at=datetime.now(UTC),
        )

        assert ref.blob_container == "quality-data"
        assert ref.blob_path == "factory-001/2025-12-28/batch-001.json"
        assert ref.content_hash == "sha256:abc123"
        assert ref.size_bytes == 1024
        assert ref.stored_at is not None

    def test_size_bytes_must_be_non_negative(self) -> None:
        """Test that size_bytes must be >= 0."""
        with pytest.raises(ValidationError):
            RawDocumentRef(
                blob_container="test",
                blob_path="test/path",
                content_hash="sha256:test",
                size_bytes=-1,  # Invalid
                stored_at=datetime.now(UTC),
            )


class TestExtractionMetadata:
    """Tests for ExtractionMetadata model."""

    def test_create_valid_extraction_metadata(self) -> None:
        """Test creating valid ExtractionMetadata."""
        metadata = ExtractionMetadata(
            ai_agent_id="qc-extractor-v1",
            extraction_timestamp=datetime.now(UTC),
            confidence=0.95,
            validation_passed=True,
            validation_warnings=[],
        )

        assert metadata.ai_agent_id == "qc-extractor-v1"
        assert metadata.confidence == 0.95
        assert metadata.validation_passed is True
        assert metadata.validation_warnings == []

    def test_confidence_must_be_between_0_and_1(self) -> None:
        """Test that confidence must be between 0 and 1."""
        with pytest.raises(ValidationError):
            ExtractionMetadata(
                ai_agent_id="test",
                extraction_timestamp=datetime.now(UTC),
                confidence=1.5,  # Invalid - > 1
            )

        with pytest.raises(ValidationError):
            ExtractionMetadata(
                ai_agent_id="test",
                extraction_timestamp=datetime.now(UTC),
                confidence=-0.1,  # Invalid - < 0
            )


class TestIngestionMetadata:
    """Tests for IngestionMetadata model."""

    def test_create_valid_ingestion_metadata(self) -> None:
        """Test creating valid IngestionMetadata."""
        now = datetime.now(UTC)
        metadata = IngestionMetadata(
            ingestion_id="ing-001",
            source_id="qc-analyzer-result",
            received_at=now,
            processed_at=now,
        )

        assert metadata.ingestion_id == "ing-001"
        assert metadata.source_id == "qc-analyzer-result"
        assert metadata.received_at == now
        assert metadata.processed_at == now


class TestDocument:
    """Tests for Document model."""

    def test_create_valid_document(self) -> None:
        """Test creating a valid Document with all fields."""
        now = datetime.now(UTC)

        doc = Document(
            document_id="doc-12345",
            raw_document=RawDocumentRef(
                blob_container="quality-data",
                blob_path="factory-001/batch.json",
                content_hash="sha256:abc",
                size_bytes=1024,
                stored_at=now,
            ),
            extraction=ExtractionMetadata(
                ai_agent_id="qc-extractor",
                extraction_timestamp=now,
                confidence=0.9,
            ),
            ingestion=IngestionMetadata(
                ingestion_id="ing-001",
                source_id="qc-analyzer",
                received_at=now,
                processed_at=now,
            ),
            extracted_fields={"farmer_id": "WM-0001", "grade": "Primary"},
            linkage_fields={"farmer_id": "WM-0001"},
        )

        assert doc.document_id == "doc-12345"
        assert doc.extracted_fields["farmer_id"] == "WM-0001"
        assert doc.linkage_fields["farmer_id"] == "WM-0001"

    def test_document_id_auto_generated(self) -> None:
        """Test that document_id is auto-generated if not provided."""
        now = datetime.now(UTC)

        doc = Document(
            raw_document=RawDocumentRef(
                blob_container="test",
                blob_path="test/path",
                content_hash="sha256:test",
                size_bytes=100,
                stored_at=now,
            ),
            extraction=ExtractionMetadata(
                ai_agent_id="test",
                extraction_timestamp=now,
                confidence=0.8,
            ),
            ingestion=IngestionMetadata(
                ingestion_id="ing-002",
                source_id="test-source",
                received_at=now,
                processed_at=now,
            ),
        )

        assert doc.document_id is not None
        assert len(doc.document_id) > 0  # UUID format


class TestSearchResult:
    """Tests for SearchResult model."""

    def test_create_valid_search_result(self) -> None:
        """Test creating a valid SearchResult."""
        now = datetime.now(UTC)

        result = SearchResult(
            document_id="doc-12345",
            raw_document=RawDocumentRef(
                blob_container="quality-data",
                blob_path="factory-001/batch.json",
                content_hash="sha256:abc",
                size_bytes=1024,
                stored_at=now,
            ),
            extraction=ExtractionMetadata(
                ai_agent_id="qc-extractor",
                extraction_timestamp=now,
                confidence=0.9,
            ),
            ingestion=IngestionMetadata(
                ingestion_id="ing-001",
                source_id="qc-analyzer",
                received_at=now,
                processed_at=now,
            ),
            created_at=now,
            relevance_score=0.85,
        )

        assert result.document_id == "doc-12345"
        assert result.relevance_score == 0.85

    def test_relevance_score_default(self) -> None:
        """Test that relevance_score defaults to 1.0."""
        now = datetime.now(UTC)

        result = SearchResult(
            document_id="doc-123",
            raw_document=RawDocumentRef(
                blob_container="test",
                blob_path="test/path",
                content_hash="sha256:test",
                size_bytes=100,
                stored_at=now,
            ),
            extraction=ExtractionMetadata(
                ai_agent_id="test",
                extraction_timestamp=now,
                confidence=0.8,
            ),
            ingestion=IngestionMetadata(
                ingestion_id="ing-002",
                source_id="test-source",
                received_at=now,
                processed_at=now,
            ),
            created_at=now,
        )

        assert result.relevance_score == 1.0

    def test_relevance_score_must_be_between_0_and_1(self) -> None:
        """Test that relevance_score must be between 0 and 1."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError):
            SearchResult(
                document_id="doc-123",
                raw_document=RawDocumentRef(
                    blob_container="test",
                    blob_path="test/path",
                    content_hash="sha256:test",
                    size_bytes=100,
                    stored_at=now,
                ),
                extraction=ExtractionMetadata(
                    ai_agent_id="test",
                    extraction_timestamp=now,
                    confidence=0.8,
                ),
                ingestion=IngestionMetadata(
                    ingestion_id="ing-002",
                    source_id="test-source",
                    received_at=now,
                    processed_at=now,
                ),
                created_at=now,
                relevance_score=1.5,  # Invalid
            )
