"""Unit tests for Collection Model AI event subscriber handlers (Story 2-12).

Tests cover:
- _process_agent_completed_async(): Updates document with extraction results
- _process_agent_failed_async(): Marks document as failed
- Correlation via request_id = document_id
- Success event publishing after completion
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from collection_model.domain.document_index import (
    DocumentIndex,
    ExtractionMetadata,
    IngestionMetadata,
    RawDocumentRef,
)
from collection_model.events.subscriber import (
    _process_agent_completed_async,
    _process_agent_failed_async,
)
from fp_common.events.ai_model_events import (
    AgentCompletedEvent,
    AgentFailedEvent,
    EntityLinkage,
    ExtractorAgentResult,
)
from fp_common.models.source_config import SourceConfig


class TestAgentCompletedHandler:
    """Tests for _process_agent_completed_async handler."""

    @pytest.fixture
    def mock_document_repository(self) -> MagicMock:
        """Create mock document repository."""
        repo = MagicMock()
        repo.find_pending_by_request_id = AsyncMock()
        repo.update = AsyncMock(return_value=True)
        return repo

    @pytest.fixture
    def mock_event_publisher(self) -> MagicMock:
        """Create mock event publisher."""
        publisher = MagicMock()
        publisher.publish_success = AsyncMock(return_value=True)
        return publisher

    @pytest.fixture
    def mock_source_config_service(self) -> MagicMock:
        """Create mock source config service."""
        service = MagicMock()
        service.get_config_by_agent_id = AsyncMock()
        return service

    @pytest.fixture
    def sample_source_config(self) -> SourceConfig:
        """Create sample source configuration."""
        return SourceConfig.model_validate(
            {
                "source_id": "test-source",
                "display_name": "Test Source",
                "description": "Test source for unit tests",
                "enabled": True,
                "ingestion": {
                    "mode": "blob_trigger",
                    "landing_container": "test-landing",
                    "file_format": "json",
                    "processor_type": "json-extraction",
                },
                "transformation": {
                    "ai_agent_id": "test-extractor",
                    "extract_fields": ["field1", "field2"],
                    "link_field": "field1",
                },
                "storage": {
                    "raw_container": "raw",
                    "index_collection": "test_documents",
                },
            }
        )

    @pytest.fixture
    def sample_pending_document(self) -> DocumentIndex:
        """Create sample pending document."""
        return DocumentIndex(
            document_id="doc-123",
            raw_document=RawDocumentRef(
                blob_container="raw",
                blob_path="test/path",
                content_hash="abc123",
                size_bytes=100,
                stored_at=datetime.now(UTC),
            ),
            extraction=ExtractionMetadata(
                ai_agent_id="test-extractor",
                extraction_timestamp=datetime.now(UTC),
                status="pending",
                confidence=0.0,
            ),
            ingestion=IngestionMetadata(
                ingestion_id="ing-123",
                source_id="test-source",
                received_at=datetime.now(UTC),
                processed_at=datetime.now(UTC),
            ),
            extracted_fields={},
            linkage_fields={},
        )

    @pytest.fixture
    def sample_completed_event(self) -> AgentCompletedEvent:
        """Create sample AgentCompletedEvent."""
        return AgentCompletedEvent(
            request_id="doc-123",
            agent_id="test-extractor",
            linkage=EntityLinkage(farmer_id="farmer-001"),
            result=ExtractorAgentResult(
                extracted_fields={"field1": "value1", "field2": "value2"},
                validation_errors=[],
                validation_warnings=["Minor warning"],
            ),
            execution_time_ms=1500,
            model_used="claude-3-haiku",
        )

    @pytest.mark.asyncio
    async def test_completed_handler_updates_document(
        self,
        mock_document_repository: MagicMock,
        mock_event_publisher: MagicMock,
        mock_source_config_service: MagicMock,
        sample_source_config: SourceConfig,
        sample_pending_document: DocumentIndex,
        sample_completed_event: AgentCompletedEvent,
    ) -> None:
        """Test that completed handler updates document with extraction results."""
        # Setup mocks
        mock_source_config_service.get_config_by_agent_id.return_value = sample_source_config
        mock_document_repository.find_pending_by_request_id.return_value = sample_pending_document

        # Set up module-level dependencies
        with (
            patch("collection_model.events.subscriber._document_repository", mock_document_repository),
            patch("collection_model.events.subscriber._event_publisher", mock_event_publisher),
            patch("collection_model.events.subscriber._source_config_service", mock_source_config_service),
        ):
            result = await _process_agent_completed_async(sample_completed_event)

        assert result is True

        # Verify document was looked up by request_id
        mock_document_repository.find_pending_by_request_id.assert_called_once_with(
            request_id="doc-123",
            collection_name="test_documents",
        )

        # Verify document was updated
        mock_document_repository.update.assert_called_once()
        updated_doc = mock_document_repository.update.call_args[0][0]
        assert updated_doc.extraction.status == "complete"
        assert updated_doc.extracted_fields == {"field1": "value1", "field2": "value2"}

        # Verify success event was published
        mock_event_publisher.publish_success.assert_called_once()

    @pytest.mark.asyncio
    async def test_completed_handler_idempotent_when_document_not_found(
        self,
        mock_document_repository: MagicMock,
        mock_event_publisher: MagicMock,
        mock_source_config_service: MagicMock,
        sample_source_config: SourceConfig,
        sample_completed_event: AgentCompletedEvent,
    ) -> None:
        """Test that completed handler is idempotent when document already processed."""
        mock_source_config_service.get_config_by_agent_id.return_value = sample_source_config
        mock_document_repository.find_pending_by_request_id.return_value = None  # Already processed

        with (
            patch("collection_model.events.subscriber._document_repository", mock_document_repository),
            patch("collection_model.events.subscriber._event_publisher", mock_event_publisher),
            patch("collection_model.events.subscriber._source_config_service", mock_source_config_service),
        ):
            result = await _process_agent_completed_async(sample_completed_event)

        # Should return True (success) even though document not found
        assert result is True

        # Document should not be updated
        mock_document_repository.update.assert_not_called()


class TestAgentFailedHandler:
    """Tests for _process_agent_failed_async handler."""

    @pytest.fixture
    def mock_document_repository(self) -> MagicMock:
        """Create mock document repository."""
        repo = MagicMock()
        repo.find_pending_by_request_id = AsyncMock()
        repo.update = AsyncMock(return_value=True)
        return repo

    @pytest.fixture
    def mock_source_config_service(self) -> MagicMock:
        """Create mock source config service."""
        service = MagicMock()
        service.get_config_by_agent_id = AsyncMock()
        return service

    @pytest.fixture
    def sample_source_config(self) -> SourceConfig:
        """Create sample source configuration."""
        return SourceConfig.model_validate(
            {
                "source_id": "test-source",
                "display_name": "Test Source",
                "description": "Test source for unit tests",
                "enabled": True,
                "ingestion": {
                    "mode": "blob_trigger",
                    "landing_container": "test-landing",
                    "file_format": "json",
                    "processor_type": "json-extraction",
                },
                "transformation": {
                    "ai_agent_id": "test-extractor",
                    "extract_fields": ["field1"],
                    "link_field": "field1",
                },
                "storage": {
                    "raw_container": "raw",
                    "index_collection": "test_documents",
                },
            }
        )

    @pytest.fixture
    def sample_pending_document(self) -> DocumentIndex:
        """Create sample pending document."""
        return DocumentIndex(
            document_id="doc-456",
            raw_document=RawDocumentRef(
                blob_container="raw",
                blob_path="test/path",
                content_hash="def456",
                size_bytes=200,
                stored_at=datetime.now(UTC),
            ),
            extraction=ExtractionMetadata(
                ai_agent_id="test-extractor",
                extraction_timestamp=datetime.now(UTC),
                status="pending",
                confidence=0.0,
            ),
            ingestion=IngestionMetadata(
                ingestion_id="ing-456",
                source_id="test-source",
                received_at=datetime.now(UTC),
                processed_at=datetime.now(UTC),
            ),
            extracted_fields={},
            linkage_fields={},
        )

    @pytest.fixture
    def sample_failed_event(self) -> AgentFailedEvent:
        """Create sample AgentFailedEvent."""
        return AgentFailedEvent(
            request_id="doc-456",
            agent_id="test-extractor",
            linkage=EntityLinkage(farmer_id="farmer-002"),
            error_type="validation",
            error_message="Required field 'field1' missing from input",
            retry_count=2,
        )

    @pytest.mark.asyncio
    async def test_failed_handler_marks_document_as_failed(
        self,
        mock_document_repository: MagicMock,
        mock_source_config_service: MagicMock,
        sample_source_config: SourceConfig,
        sample_pending_document: DocumentIndex,
        sample_failed_event: AgentFailedEvent,
    ) -> None:
        """Test that failed handler marks document with failure status."""
        mock_source_config_service.get_config_by_agent_id.return_value = sample_source_config
        mock_document_repository.find_pending_by_request_id.return_value = sample_pending_document

        with (
            patch("collection_model.events.subscriber._document_repository", mock_document_repository),
            patch("collection_model.events.subscriber._source_config_service", mock_source_config_service),
        ):
            result = await _process_agent_failed_async(sample_failed_event)

        assert result is True

        # Verify document was looked up by request_id
        mock_document_repository.find_pending_by_request_id.assert_called_once_with(
            request_id="doc-456",
            collection_name="test_documents",
        )

        # Verify document was updated with failure info
        mock_document_repository.update.assert_called_once()
        updated_doc = mock_document_repository.update.call_args[0][0]
        assert updated_doc.extraction.status == "failed"
        assert updated_doc.extraction.error_type == "validation"
        assert updated_doc.extraction.error_message == "Required field 'field1' missing from input"

    @pytest.mark.asyncio
    async def test_failed_handler_raises_on_no_config(
        self,
        mock_document_repository: MagicMock,
        mock_source_config_service: MagicMock,
        sample_failed_event: AgentFailedEvent,
    ) -> None:
        """Test that failed handler raises ValueError when config not found."""
        mock_source_config_service.get_config_by_agent_id.return_value = None

        with (
            patch("collection_model.events.subscriber._document_repository", mock_document_repository),
            patch("collection_model.events.subscriber._source_config_service", mock_source_config_service),
            pytest.raises(ValueError) as exc_info,
        ):
            await _process_agent_failed_async(sample_failed_event)

        assert "No source config for agent_id" in str(exc_info.value)
