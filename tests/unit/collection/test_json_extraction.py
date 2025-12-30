"""Unit tests for JsonExtractionProcessor deduplication (Story 2.6).

Tests cover duplicate detection behavior for JSON processor:
- ProcessorResult.is_duplicate=True on DuplicateDocumentError
- No event emission on duplicate
- No document storage on duplicate
- StorageMetrics called correctly
"""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from collection_model.domain.ingestion_job import IngestionJob
from collection_model.processors.json_extraction import JsonExtractionProcessor


class TestJsonExtractionProcessorDeduplication:
    """Tests for JSON processor duplicate detection (Story 2.6)."""

    @pytest.fixture
    def mock_blob_client(self) -> MagicMock:
        """Create mock blob client."""
        client = MagicMock()
        client.download_blob = AsyncMock(return_value=b'{"test": "data"}')
        return client

    @pytest.fixture
    def mock_raw_store(self) -> MagicMock:
        """Create mock raw document store."""
        store = MagicMock()
        mock_raw_doc = MagicMock()
        mock_raw_doc.blob_container = "raw-json"
        mock_raw_doc.blob_path = "test-source/ing-123/abc123"
        mock_raw_doc.content_hash = "abc123"
        mock_raw_doc.size_bytes = 100
        mock_raw_doc.stored_at = datetime.now(UTC)
        store.store_raw_document = AsyncMock(return_value=mock_raw_doc)
        return store

    @pytest.fixture
    def mock_ai_client(self) -> MagicMock:
        """Create mock AI model client."""
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.extracted_fields = {"field1": "value1"}
        mock_response.confidence = 0.95
        mock_response.validation_passed = True
        mock_response.validation_warnings = []
        client.extract = AsyncMock(return_value=mock_response)
        return client

    @pytest.fixture
    def mock_doc_repo(self) -> MagicMock:
        """Create mock document repository."""
        repo = MagicMock()
        repo.ensure_indexes = AsyncMock()
        repo.save = AsyncMock(return_value="doc-123")
        return repo

    @pytest.fixture
    def mock_event_publisher(self) -> MagicMock:
        """Create mock event publisher."""
        publisher = MagicMock()
        publisher.publish_success = AsyncMock(return_value=True)
        return publisher

    @pytest.fixture
    def sample_job(self) -> IngestionJob:
        """Create sample ingestion job."""
        return IngestionJob(
            ingestion_id="ing-456",
            blob_path="data/test-file.json",
            blob_etag='"etag-456"',
            container="json-landing",
            source_id="test-json-source",
            content_length=100,
            status="queued",
            metadata={"batch_id": "batch-001"},
        )

    @pytest.fixture
    def sample_source_config(self) -> dict[str, Any]:
        """Create sample source configuration."""
        return {
            "source_id": "test-json-source",
            "ingestion": {
                "mode": "blob_trigger",
                "processor_type": "json-extraction",
            },
            "transformation": {
                "ai_agent_id": "test-agent",
                "link_field": "batch_id",
            },
            "storage": {
                "raw_container": "raw-json",
                "index_collection": "json_documents",
            },
            "events": {
                "on_success": {
                    "topic": "collection.json.received",
                    "payload_fields": ["batch_id"],
                },
            },
        }

    @pytest.mark.asyncio
    async def test_duplicate_json_returns_is_duplicate_true(
        self,
        mock_blob_client: MagicMock,
        mock_raw_store: MagicMock,
        mock_ai_client: MagicMock,
        mock_doc_repo: MagicMock,
        mock_event_publisher: MagicMock,
        sample_job: IngestionJob,
        sample_source_config: dict[str, Any],
    ) -> None:
        """Test that duplicate JSON returns ProcessorResult with is_duplicate=True."""
        from collection_model.domain.exceptions import DuplicateDocumentError

        # Make raw_store raise DuplicateDocumentError
        mock_raw_store.store_raw_document = AsyncMock(side_effect=DuplicateDocumentError("abc123def456"))

        processor = JsonExtractionProcessor()
        processor.set_dependencies(
            blob_client=mock_blob_client,
            raw_document_store=mock_raw_store,
            ai_model_client=mock_ai_client,
            document_repository=mock_doc_repo,
            event_publisher=mock_event_publisher,
        )

        result = await processor.process(sample_job, sample_source_config)

        # Verify duplicate handling
        assert result.success is True, "Duplicate should be a success case"
        assert result.is_duplicate is True, "is_duplicate should be True"
        assert result.error_message is None
        assert result.document_id is None

    @pytest.mark.asyncio
    async def test_duplicate_json_does_not_call_ai_model(
        self,
        mock_blob_client: MagicMock,
        mock_raw_store: MagicMock,
        mock_ai_client: MagicMock,
        mock_doc_repo: MagicMock,
        mock_event_publisher: MagicMock,
        sample_job: IngestionJob,
        sample_source_config: dict[str, Any],
    ) -> None:
        """Test that duplicate JSON does not call AI model (saves LLM costs)."""
        from collection_model.domain.exceptions import DuplicateDocumentError

        mock_raw_store.store_raw_document = AsyncMock(side_effect=DuplicateDocumentError("abc123"))

        processor = JsonExtractionProcessor()
        processor.set_dependencies(
            blob_client=mock_blob_client,
            raw_document_store=mock_raw_store,
            ai_model_client=mock_ai_client,
            document_repository=mock_doc_repo,
            event_publisher=mock_event_publisher,
        )

        await processor.process(sample_job, sample_source_config)

        # AI model should NOT be called for duplicates (cost saving!)
        mock_ai_client.extract.assert_not_called()

    @pytest.mark.asyncio
    async def test_duplicate_json_does_not_emit_event(
        self,
        mock_blob_client: MagicMock,
        mock_raw_store: MagicMock,
        mock_ai_client: MagicMock,
        mock_doc_repo: MagicMock,
        mock_event_publisher: MagicMock,
        sample_job: IngestionJob,
        sample_source_config: dict[str, Any],
    ) -> None:
        """Test that duplicate JSON does not emit domain event."""
        from collection_model.domain.exceptions import DuplicateDocumentError

        mock_raw_store.store_raw_document = AsyncMock(side_effect=DuplicateDocumentError("abc123"))

        processor = JsonExtractionProcessor()
        processor.set_dependencies(
            blob_client=mock_blob_client,
            raw_document_store=mock_raw_store,
            ai_model_client=mock_ai_client,
            document_repository=mock_doc_repo,
            event_publisher=mock_event_publisher,
        )

        await processor.process(sample_job, sample_source_config)

        # Event should NOT be emitted for duplicates
        mock_event_publisher.publish_success.assert_not_called()

    @pytest.mark.asyncio
    async def test_duplicate_json_does_not_store_document(
        self,
        mock_blob_client: MagicMock,
        mock_raw_store: MagicMock,
        mock_ai_client: MagicMock,
        mock_doc_repo: MagicMock,
        mock_event_publisher: MagicMock,
        sample_job: IngestionJob,
        sample_source_config: dict[str, Any],
    ) -> None:
        """Test that duplicate JSON does not store document to index collection."""
        from collection_model.domain.exceptions import DuplicateDocumentError

        mock_raw_store.store_raw_document = AsyncMock(side_effect=DuplicateDocumentError("abc123"))

        processor = JsonExtractionProcessor()
        processor.set_dependencies(
            blob_client=mock_blob_client,
            raw_document_store=mock_raw_store,
            ai_model_client=mock_ai_client,
            document_repository=mock_doc_repo,
            event_publisher=mock_event_publisher,
        )

        await processor.process(sample_job, sample_source_config)

        # Document repository save should NOT be called for duplicates
        mock_doc_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_duplicate_json_calls_storage_metrics(
        self,
        mock_blob_client: MagicMock,
        mock_raw_store: MagicMock,
        mock_ai_client: MagicMock,
        mock_doc_repo: MagicMock,
        mock_event_publisher: MagicMock,
        sample_job: IngestionJob,
        sample_source_config: dict[str, Any],
    ) -> None:
        """Test that duplicate JSON increments StorageMetrics.record_duplicate()."""
        from collection_model.domain.exceptions import DuplicateDocumentError

        mock_raw_store.store_raw_document = AsyncMock(side_effect=DuplicateDocumentError("abc123"))

        processor = JsonExtractionProcessor()
        processor.set_dependencies(
            blob_client=mock_blob_client,
            raw_document_store=mock_raw_store,
            ai_model_client=mock_ai_client,
            document_repository=mock_doc_repo,
            event_publisher=mock_event_publisher,
        )

        with patch("collection_model.processors.json_extraction.StorageMetrics") as mock_metrics:
            await processor.process(sample_job, sample_source_config)

            # Verify record_duplicate was called with correct source_id
            mock_metrics.record_duplicate.assert_called_once_with("test-json-source")
            mock_metrics.record_stored.assert_not_called()

    @pytest.mark.asyncio
    async def test_successful_json_calls_storage_metrics_stored(
        self,
        mock_blob_client: MagicMock,
        mock_raw_store: MagicMock,
        mock_ai_client: MagicMock,
        mock_doc_repo: MagicMock,
        mock_event_publisher: MagicMock,
        sample_job: IngestionJob,
        sample_source_config: dict[str, Any],
    ) -> None:
        """Test that successful JSON processing calls StorageMetrics.record_stored()."""
        json_content = b'{"test": "data"}'
        mock_blob_client.download_blob = AsyncMock(return_value=json_content)

        processor = JsonExtractionProcessor()
        processor.set_dependencies(
            blob_client=mock_blob_client,
            raw_document_store=mock_raw_store,
            ai_model_client=mock_ai_client,
            document_repository=mock_doc_repo,
            event_publisher=mock_event_publisher,
        )

        with patch("collection_model.processors.json_extraction.StorageMetrics") as mock_metrics:
            result = await processor.process(sample_job, sample_source_config)

            assert result.success is True
            # Verify record_stored was called with correct args
            mock_metrics.record_stored.assert_called_once_with("test-json-source", len(json_content))
            mock_metrics.record_duplicate.assert_not_called()
