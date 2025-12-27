"""JSON extraction processor for processing JSON blobs.

This module provides the JsonExtractionProcessor class which handles
JSON file ingestion. It is FULLY GENERIC - no hardcoded collection names,
event topics, or business logic.
"""

from datetime import UTC, datetime
from typing import Any

import structlog
from collection_model.domain.document_index import (
    DocumentIndex,
    ExtractionMetadata,
    IngestionMetadata,
    RawDocumentRef,
)
from collection_model.domain.exceptions import (
    ConfigurationError,
    DuplicateDocumentError,
    ExtractionError,
    StorageError,
    ValidationError,
)
from collection_model.domain.ingestion_job import IngestionJob
from collection_model.infrastructure.ai_model_client import (
    AiModelClient,
    ExtractionRequest,
)
from collection_model.infrastructure.blob_storage import BlobStorageClient
from collection_model.infrastructure.dapr_event_publisher import DaprEventPublisher
from collection_model.infrastructure.document_repository import DocumentRepository
from collection_model.infrastructure.raw_document_store import RawDocumentStore
from collection_model.processors.base import ContentProcessor, ProcessorResult

logger = structlog.get_logger(__name__)


class JsonExtractionProcessor(ContentProcessor):
    """Processor for JSON file extraction.

    This processor is FULLY GENERIC:
    - NO hardcoded collection names (uses source_config.storage.index_collection)
    - NO hardcoded event topics (uses source_config.events.on_success.topic)
    - NO business logic (stores extracted_fields AS-IS from AI Model)

    Processing pipeline:
    1. Download blob from Azure Blob Storage
    2. Store raw document with content hash
    3. Call AI Model via DAPR Service Invocation for extraction
    4. Store extracted data to collection from config
    5. Emit domain event to topic from config
    """

    def __init__(
        self,
        blob_client: BlobStorageClient | None = None,
        raw_document_store: RawDocumentStore | None = None,
        ai_model_client: AiModelClient | None = None,
        document_repository: DocumentRepository | None = None,
        event_publisher: DaprEventPublisher | None = None,
    ) -> None:
        """Initialize the processor.

        Args:
            blob_client: Azure Blob Storage client.
            raw_document_store: Raw document storage.
            ai_model_client: AI Model DAPR client.
            document_repository: Generic document repository.
            event_publisher: DAPR event publisher.
        """
        self._blob_client = blob_client
        self._raw_store = raw_document_store
        self._ai_client = ai_model_client
        self._doc_repo = document_repository
        self._event_publisher = event_publisher

    def set_dependencies(
        self,
        blob_client: BlobStorageClient,
        raw_document_store: RawDocumentStore,
        ai_model_client: AiModelClient,
        document_repository: DocumentRepository,
        event_publisher: DaprEventPublisher,
    ) -> None:
        """Set dependencies after construction.

        Used when processor is instantiated by registry.

        Args:
            blob_client: Azure Blob Storage client.
            raw_document_store: Raw document storage.
            ai_model_client: AI Model DAPR client.
            document_repository: Generic document repository.
            event_publisher: DAPR event publisher.
        """
        self._blob_client = blob_client
        self._raw_store = raw_document_store
        self._ai_client = ai_model_client
        self._doc_repo = document_repository
        self._event_publisher = event_publisher

    async def process(
        self,
        job: IngestionJob,
        source_config: dict[str, Any],
    ) -> ProcessorResult:
        """Process a JSON ingestion job.

        Fully config-driven pipeline - all storage and event settings
        are read from source_config.

        Args:
            job: The queued ingestion job.
            source_config: Full source configuration from MongoDB.

        Returns:
            ProcessorResult with success status and extracted data.
        """
        source_id = source_config.get("source_id", job.source_id)

        logger.info(
            "Processing JSON blob",
            ingestion_id=job.ingestion_id,
            source_id=source_id,
            blob_path=job.blob_path,
        )

        try:
            # Step 1: Download blob
            content = await self._download_blob(job)

            # Step 2: Validate JSON
            raw_json = self._validate_json(content)

            # Step 3: Store raw document
            raw_doc = await self._store_raw_document(
                content=content,
                source_config=source_config,
                job=job,
            )

            # Step 4: Call AI Model for extraction
            extraction_result = await self._call_ai_model(
                raw_content=raw_json,
                source_config=source_config,
            )

            # Step 5: Create document index
            document = self._create_document_index(
                raw_doc=raw_doc,
                extraction_result=extraction_result,
                job=job,
                source_config=source_config,
            )

            # Step 6: Store to config-driven collection
            await self._store_document(document, source_config)

            # Step 7: Emit config-driven event
            await self._emit_success_event(document, source_config)

            logger.info(
                "JSON processing completed",
                ingestion_id=job.ingestion_id,
                document_id=document.document_id,
                source_id=source_id,
            )

            return ProcessorResult(
                success=True,
                document_id=document.document_id,
                extracted_data=extraction_result.get("extracted_fields", {}),
            )

        except DuplicateDocumentError as e:
            # Duplicate is actually a success case - we skip processing
            logger.info(
                "Duplicate document detected, skipping",
                ingestion_id=job.ingestion_id,
                source_id=source_id,
                error=str(e),
            )
            return ProcessorResult(
                success=True,
                error_message=str(e),
            )

        except ValidationError as e:
            logger.warning(
                "JSON validation failed",
                ingestion_id=job.ingestion_id,
                source_id=source_id,
                error=str(e),
            )
            return ProcessorResult(
                success=False,
                error_message=str(e),
                error_type="validation",
            )

        except ConfigurationError as e:
            logger.error(
                "Configuration error",
                ingestion_id=job.ingestion_id,
                source_id=source_id,
                error=str(e),
            )
            return ProcessorResult(
                success=False,
                error_message=str(e),
                error_type="config",
            )

        except ExtractionError as e:
            logger.error(
                "AI Model extraction failed",
                ingestion_id=job.ingestion_id,
                source_id=source_id,
                error=str(e),
            )
            return ProcessorResult(
                success=False,
                error_message=str(e),
                error_type="extraction",
            )

        except StorageError as e:
            logger.error(
                "Storage operation failed",
                ingestion_id=job.ingestion_id,
                source_id=source_id,
                error=str(e),
            )
            return ProcessorResult(
                success=False,
                error_message=str(e),
                error_type="storage",
            )

        except Exception as e:
            logger.exception(
                "Unexpected error during JSON processing",
                ingestion_id=job.ingestion_id,
                source_id=source_id,
                error=str(e),
            )
            return ProcessorResult(
                success=False,
                error_message=str(e),
                error_type="unknown",
            )

    def supports_content_type(self, content_type: str) -> bool:
        """Check if processor supports the given content type.

        Args:
            content_type: MIME type.

        Returns:
            True for application/json.
        """
        return content_type in ("application/json", "text/json")

    async def _download_blob(self, job: IngestionJob) -> bytes:
        """Download blob content from Azure Blob Storage."""
        if not self._blob_client:
            raise ConfigurationError("Blob client not configured")

        return await self._blob_client.download_blob(
            container=job.container,
            blob_path=job.blob_path,
        )

    def _validate_json(self, content: bytes) -> str:
        """Validate that content is valid JSON."""
        import json

        try:
            decoded = content.decode("utf-8")
            json.loads(decoded)  # Validate JSON syntax
            return decoded
        except UnicodeDecodeError as e:
            raise ValidationError(f"Invalid UTF-8 encoding: {e}") from e
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {e}") from e

    async def _store_raw_document(
        self,
        content: bytes,
        source_config: dict[str, Any],
        job: IngestionJob,
    ) -> dict[str, Any]:
        """Store raw document in blob storage with content hash."""
        if not self._raw_store:
            raise ConfigurationError("Raw document store not configured")

        raw_doc = await self._raw_store.store_raw_document(
            content=content,
            source_config=source_config,
            ingestion_id=job.ingestion_id,
            metadata=job.metadata,
        )

        return {
            "blob_container": raw_doc.blob_container,
            "blob_path": raw_doc.blob_path,
            "content_hash": raw_doc.content_hash,
            "size_bytes": raw_doc.size_bytes,
            "stored_at": raw_doc.stored_at,
        }

    async def _call_ai_model(
        self,
        raw_content: str,
        source_config: dict[str, Any],
    ) -> dict[str, Any]:
        """Call AI Model for structured extraction."""
        if not self._ai_client:
            raise ConfigurationError("AI Model client not configured")

        # Get AI agent ID from config
        transformation = source_config.get("config", {}).get("transformation", {})
        ai_agent_id = transformation.get("ai_agent_id") or transformation.get("agent")

        if not ai_agent_id:
            raise ConfigurationError("No ai_agent_id in transformation config")

        request = ExtractionRequest(
            raw_content=raw_content,
            ai_agent_id=ai_agent_id,
            source_config=source_config,
            content_type="application/json",
        )

        response = await self._ai_client.extract(request)

        return {
            "extracted_fields": response.extracted_fields,
            "confidence": response.confidence,
            "validation_passed": response.validation_passed,
            "validation_warnings": response.validation_warnings,
        }

    def _create_document_index(
        self,
        raw_doc: dict[str, Any],
        extraction_result: dict[str, Any],
        job: IngestionJob,
        source_config: dict[str, Any],
    ) -> DocumentIndex:
        """Create a document index from extraction results."""
        transformation = source_config.get("config", {}).get("transformation", {})
        ai_agent_id = transformation.get("ai_agent_id") or transformation.get("agent", "unknown")

        raw_ref = RawDocumentRef(
            blob_container=raw_doc["blob_container"],
            blob_path=raw_doc["blob_path"],
            content_hash=raw_doc["content_hash"],
            size_bytes=raw_doc["size_bytes"],
            stored_at=raw_doc["stored_at"],
        )

        extraction = ExtractionMetadata(
            ai_agent_id=ai_agent_id,
            extraction_timestamp=datetime.now(UTC),
            confidence=extraction_result.get("confidence", 1.0),
            validation_passed=extraction_result.get("validation_passed", True),
            validation_warnings=extraction_result.get("validation_warnings", []),
        )

        ingestion = IngestionMetadata(
            ingestion_id=job.ingestion_id,
            source_id=job.source_id,
            received_at=job.created_at,
            processed_at=datetime.now(UTC),
        )

        return DocumentIndex.from_extraction(
            raw_document=raw_ref,
            extraction=extraction,
            ingestion=ingestion,
            extracted_fields=extraction_result.get("extracted_fields", {}),
            source_config=source_config,
        )

    async def _store_document(
        self,
        document: DocumentIndex,
        source_config: dict[str, Any],
    ) -> None:
        """Store document to config-driven collection."""
        if not self._doc_repo:
            raise ConfigurationError("Document repository not configured")

        # Get collection name FROM CONFIG - not hardcoded!
        storage = source_config.get("config", {}).get("storage", {})
        collection_name = storage.get("index_collection")

        if not collection_name:
            raise ConfigurationError("No index_collection in storage config")

        # Get link field for indexing
        transformation = source_config.get("config", {}).get("transformation", {})
        link_field = transformation.get("link_field", "")

        # Ensure indexes exist
        await self._doc_repo.ensure_indexes(collection_name, link_field)

        # Save document
        await self._doc_repo.save(document, collection_name)

    async def _emit_success_event(
        self,
        document: DocumentIndex,
        source_config: dict[str, Any],
    ) -> None:
        """Emit success event to config-driven topic."""
        if not self._event_publisher:
            logger.debug("Event publisher not configured, skipping event emission")
            return

        await self._event_publisher.publish_success(source_config, document)
