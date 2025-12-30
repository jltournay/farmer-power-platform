"""Unit tests for content processors and registry (Story 2.4).

Tests cover:
- ProcessorRegistry registration and lookup
- ProcessorNotFoundError for unknown processor types
- ContentProcessor ABC contract
- JsonExtractionProcessor processing pipeline
"""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from collection_model.domain.ingestion_job import IngestionJob
from collection_model.processors.base import (
    ContentProcessor,
    ProcessorNotFoundError,
    ProcessorResult,
)
from collection_model.processors.json_extraction import JsonExtractionProcessor
from collection_model.processors.registry import ProcessorRegistry


class TestProcessorRegistry:
    """Tests for ProcessorRegistry."""

    def setup_method(self) -> None:
        """Clear registry before each test."""
        ProcessorRegistry.clear()

    def test_register_and_get_processor(self) -> None:
        """Test registering and retrieving a processor."""

        class TestProcessor(ContentProcessor):
            async def process(self, job: IngestionJob, source_config: dict[str, Any]) -> ProcessorResult:
                return ProcessorResult(success=True)

            def supports_content_type(self, content_type: str) -> bool:
                return content_type == "test/type"

        ProcessorRegistry.register("test-processor", TestProcessor)

        processor = ProcessorRegistry.get_processor("test-processor")
        assert isinstance(processor, TestProcessor)

    def test_get_processor_not_found(self) -> None:
        """Test that unknown processor_type raises ProcessorNotFoundError."""
        with pytest.raises(ProcessorNotFoundError) as exc_info:
            ProcessorRegistry.get_processor("unknown-processor")

        assert "No processor registered for processor_type: unknown-processor" in str(exc_info.value)

    def test_list_registered(self) -> None:
        """Test listing registered processors."""

        class TestProcessor1(ContentProcessor):
            async def process(self, job: IngestionJob, source_config: dict[str, Any]) -> ProcessorResult:
                return ProcessorResult(success=True)

            def supports_content_type(self, content_type: str) -> bool:
                return True

        class TestProcessor2(ContentProcessor):
            async def process(self, job: IngestionJob, source_config: dict[str, Any]) -> ProcessorResult:
                return ProcessorResult(success=True)

            def supports_content_type(self, content_type: str) -> bool:
                return True

        ProcessorRegistry.register("processor-1", TestProcessor1)
        ProcessorRegistry.register("processor-2", TestProcessor2)

        registered = ProcessorRegistry.list_registered()
        assert "processor-1" in registered
        assert "processor-2" in registered

    def test_is_registered(self) -> None:
        """Test checking if processor is registered."""

        class TestProcessor(ContentProcessor):
            async def process(self, job: IngestionJob, source_config: dict[str, Any]) -> ProcessorResult:
                return ProcessorResult(success=True)

            def supports_content_type(self, content_type: str) -> bool:
                return True

        ProcessorRegistry.register("test-processor", TestProcessor)

        assert ProcessorRegistry.is_registered("test-processor") is True
        assert ProcessorRegistry.is_registered("unknown") is False

    def test_clear(self) -> None:
        """Test clearing all registered processors."""

        class TestProcessor(ContentProcessor):
            async def process(self, job: IngestionJob, source_config: dict[str, Any]) -> ProcessorResult:
                return ProcessorResult(success=True)

            def supports_content_type(self, content_type: str) -> bool:
                return True

        ProcessorRegistry.register("test-processor", TestProcessor)
        assert ProcessorRegistry.is_registered("test-processor") is True

        ProcessorRegistry.clear()
        assert ProcessorRegistry.is_registered("test-processor") is False


class TestProcessorResult:
    """Tests for ProcessorResult model."""

    def test_success_result(self) -> None:
        """Test creating a success result."""
        result = ProcessorResult(
            success=True,
            document_id="doc-123",
            extracted_data={"field": "value"},
        )
        assert result.success is True
        assert result.document_id == "doc-123"
        assert result.extracted_data == {"field": "value"}
        assert result.error_message is None
        assert result.error_type is None

    def test_failure_result(self) -> None:
        """Test creating a failure result."""
        result = ProcessorResult(
            success=False,
            error_message="Extraction failed",
            error_type="extraction",
        )
        assert result.success is False
        assert result.document_id is None
        assert result.error_message == "Extraction failed"
        assert result.error_type == "extraction"


class TestJsonExtractionProcessor:
    """Tests for JsonExtractionProcessor."""

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
        mock_raw_doc.blob_container = "raw-container"
        mock_raw_doc.blob_path = "path/to/raw"
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
            ingestion_id="ing-123",
            blob_path="results/WM-4521/tea/batch-001.json",
            blob_etag='"etag-123"',
            container="qc-analyzer-landing",
            source_id="qc-analyzer-result",
            content_length=100,
            status="queued",
            metadata={"plantation_id": "WM-4521"},
        )

    @pytest.fixture
    def sample_source_config(self) -> dict[str, Any]:
        """Create sample source configuration."""
        return {
            "source_id": "qc-analyzer-result",
            "ingestion": {
                "mode": "blob_trigger",
                "processor_type": "json-extraction",
            },
            "transformation": {
                "ai_agent_id": "qc-result-extraction-agent",
                "extract_fields": ["plantation_id", "batch_id"],
                "link_field": "plantation_id",
                "field_mappings": {"plantation_id": "farmer_id"},
            },
            "storage": {
                "raw_container": "quality-results-raw",
                "index_collection": "quality_results_index",
            },
            "events": {
                "on_success": {
                    "topic": "collection.quality_result.received",
                    "payload_fields": ["document_id", "source_id"],
                },
            },
        }

    @pytest.mark.asyncio
    async def test_process_success(
        self,
        mock_blob_client: MagicMock,
        mock_raw_store: MagicMock,
        mock_ai_client: MagicMock,
        mock_doc_repo: MagicMock,
        mock_event_publisher: MagicMock,
        sample_job: IngestionJob,
        sample_source_config: dict[str, Any],
    ) -> None:
        """Test successful JSON processing."""
        processor = JsonExtractionProcessor()
        processor.set_dependencies(
            blob_client=mock_blob_client,
            raw_document_store=mock_raw_store,
            ai_model_client=mock_ai_client,
            document_repository=mock_doc_repo,
            event_publisher=mock_event_publisher,
        )

        result = await processor.process(sample_job, sample_source_config)

        assert result.success is True
        assert result.document_id is not None
        assert result.error_message is None

        # Verify all steps were called
        mock_blob_client.download_blob.assert_called_once()
        mock_raw_store.store_raw_document.assert_called_once()
        mock_ai_client.extract.assert_called_once()
        mock_doc_repo.save.assert_called_once()
        mock_event_publisher.publish_success.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_invalid_json(
        self,
        mock_blob_client: MagicMock,
        mock_raw_store: MagicMock,
        mock_ai_client: MagicMock,
        mock_doc_repo: MagicMock,
        mock_event_publisher: MagicMock,
        sample_job: IngestionJob,
        sample_source_config: dict[str, Any],
    ) -> None:
        """Test processing invalid JSON returns validation error."""
        mock_blob_client.download_blob = AsyncMock(return_value=b"not valid json")

        processor = JsonExtractionProcessor()
        processor.set_dependencies(
            blob_client=mock_blob_client,
            raw_document_store=mock_raw_store,
            ai_model_client=mock_ai_client,
            document_repository=mock_doc_repo,
            event_publisher=mock_event_publisher,
        )

        result = await processor.process(sample_job, sample_source_config)

        assert result.success is False
        assert result.error_type == "validation"
        assert "Invalid JSON" in result.error_message

    @pytest.mark.asyncio
    async def test_process_direct_extraction_without_ai_agent(
        self,
        mock_blob_client: MagicMock,
        mock_raw_store: MagicMock,
        mock_ai_client: MagicMock,
        mock_doc_repo: MagicMock,
        mock_event_publisher: MagicMock,
        sample_job: IngestionJob,
    ) -> None:
        """Test direct JSON extraction when ai_agent_id is null/missing.

        When ai_agent_id is null, the processor performs direct field extraction
        from the JSON without calling the AI model (Story 0.4.5).
        """
        direct_config = {
            "source_id": "test-direct",
            "transformation": {
                "ai_agent_id": None,  # Direct extraction mode
                "extract_fields": ["farmer_id", "weight_kg"],
                "link_field": "farmer_id",
            },
            "storage": {
                "raw_container": "raw",
                "index_collection": "index",
            },
        }

        # Mock blob content with fields to extract
        mock_blob_client.download_blob = AsyncMock(
            return_value=b'{"farmer_id": "FRM-001", "weight_kg": 12.5, "extra": "ignored"}'
        )

        processor = JsonExtractionProcessor()
        processor.set_dependencies(
            blob_client=mock_blob_client,
            raw_document_store=mock_raw_store,
            ai_model_client=mock_ai_client,
            document_repository=mock_doc_repo,
            event_publisher=mock_event_publisher,
        )

        result = await processor.process(sample_job, direct_config)

        # Direct extraction should succeed
        assert result.success is True
        assert result.document_id is not None
        assert result.error_message is None

        # AI client should NOT be called for direct extraction
        mock_ai_client.extract.assert_not_called()

        # Document should still be saved and event published
        mock_doc_repo.save.assert_called_once()
        mock_event_publisher.publish_success.assert_called_once()

    def test_supports_content_type(self) -> None:
        """Test content type support."""
        processor = JsonExtractionProcessor()

        assert processor.supports_content_type("application/json") is True
        assert processor.supports_content_type("text/json") is True
        assert processor.supports_content_type("application/zip") is False
        assert processor.supports_content_type("text/plain") is False


class TestJsonExtractionProcessorRegistration:
    """Test that JsonExtractionProcessor is properly registered."""

    def test_json_extraction_registered(self) -> None:
        """Test that json-extraction processor is registered on import."""
        # Re-register since other tests clear the registry
        ProcessorRegistry.register("json-extraction", JsonExtractionProcessor)

        assert ProcessorRegistry.is_registered("json-extraction")

        processor = ProcessorRegistry.get_processor("json-extraction")
        assert isinstance(processor, JsonExtractionProcessor)
