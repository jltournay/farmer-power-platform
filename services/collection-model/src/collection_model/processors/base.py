"""Base classes for content processors.

This module defines the ContentProcessor ABC and ProcessorResult model
that all content processors must implement. This enables the Open/Closed
Principle - new processors can be added without modifying core pipeline code.
"""

from abc import ABC, abstractmethod
from typing import Any

from collection_model.domain.ingestion_job import IngestionJob
from pydantic import BaseModel, Field


class ProcessorResult(BaseModel):
    """Result of content processing.

    Attributes:
        success: Whether processing completed successfully.
        document_id: ID of the created document if successful.
        extracted_data: Data extracted by AI Model.
        error_message: Error description if processing failed.
        error_type: Classification of the error for retry logic.
    """

    success: bool
    document_id: str | None = None
    extracted_data: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    error_type: str | None = None  # "extraction", "storage", "validation", "config"


class ProcessorNotFoundError(Exception):
    """Raised when no processor is registered for the given processor_type.

    This is a configuration error that should NOT trigger retries.
    """

    pass


class ContentProcessor(ABC):
    """Base class for all content processors.

    Extend this class to add new source type support.
    Register with ProcessorRegistry using ingestion.processor_type key.

    The processing pipeline is generic and config-driven:
    1. Download blob from Azure Blob Storage
    2. Store raw document with content hash
    3. Call AI Model via DAPR Service Invocation for extraction
    4. Store extracted data to collection from source_config.storage.index_collection
    5. Emit domain event to topic from source_config.events.on_success.topic
    """

    @abstractmethod
    async def process(
        self,
        job: IngestionJob,
        source_config: dict[str, Any],
    ) -> ProcessorResult:
        """Process the ingestion job according to source config.

        This method implements the full processing pipeline for the content type.
        All storage locations and event topics are read from source_config -
        NO hardcoded collection names or event topics.

        Args:
            job: The queued ingestion job with blob path and metadata.
            source_config: Full source configuration from MongoDB.

        Returns:
            ProcessorResult with success status and extracted data.
        """
        pass

    @abstractmethod
    def supports_content_type(self, content_type: str) -> bool:
        """Check if processor supports the given content type.

        Args:
            content_type: MIME type (e.g., "application/json", "application/zip").

        Returns:
            True if this processor can handle the content type.
        """
        pass
