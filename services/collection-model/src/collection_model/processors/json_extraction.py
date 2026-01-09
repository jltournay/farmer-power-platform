"""JSON extraction processor for processing JSON blobs.

This module provides the JsonExtractionProcessor class which handles
JSON file ingestion. It is FULLY GENERIC - no hardcoded collection names,
event topics, or business logic.

Story 2-12: Collection → AI Model Event-Driven Communication
-------------------------------------------------------------
This processor now supports TWO extraction paths:
- Path A (AI Extraction): When source_config.transformation.ai_agent_id is set,
  document is stored with status="pending" and an AgentRequestEvent is published.
  The result arrives asynchronously via AgentCompletedEvent/AgentFailedEvent.
- Path B (Direct Extraction): When ai_agent_id is not set, extraction is done
  synchronously from JSON fields, stored with status="complete".
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
    StorageError,
    ValidationError,
)
from collection_model.domain.ingestion_job import IngestionJob
from collection_model.infrastructure.blob_storage import BlobStorageClient
from collection_model.infrastructure.dapr_event_publisher import DaprEventPublisher
from collection_model.infrastructure.document_repository import DocumentRepository
from collection_model.infrastructure.raw_document_store import RawDocumentStore
from collection_model.infrastructure.storage_metrics import StorageMetrics
from collection_model.processors.base import ContentProcessor, ProcessorResult
from fp_common.events.ai_model_events import (
    AgentRequestEvent,
    EntityLinkage,
)
from fp_common.models.domain_events import AIModelEventTopic
from fp_common.models.source_config import SourceConfig

logger = structlog.get_logger(__name__)


class JsonExtractionProcessor(ContentProcessor):
    """Processor for JSON file extraction.

    This processor is FULLY GENERIC:
    - NO hardcoded collection names (uses source_config.storage.index_collection)
    - NO hardcoded event topics (uses source_config.events.on_success.topic)
    - NO business logic (stores extracted_fields AS-IS from AI Model)

    Story 2-12: Event-Driven Processing Pipeline
    ---------------------------------------------
    Path A (AI Extraction - when ai_agent_id is set):
    1. Download blob from Azure Blob Storage
    2. Store raw document with content hash
    3. Store document index with status="pending" and empty extracted_fields
    4. Publish AgentRequestEvent to ai.agent.requested topic
    5. (Async) Receive AgentCompletedEvent/AgentFailedEvent via subscriber
    6. (Async) Update document with result, emit success event

    Path B (Direct Extraction - when ai_agent_id is NOT set):
    1. Download blob from Azure Blob Storage
    2. Store raw document with content hash
    3. Extract fields directly from JSON
    4. Store document index with status="complete"
    5. Emit success event to topic from config
    """

    def __init__(
        self,
        blob_client: BlobStorageClient | None = None,
        raw_document_store: RawDocumentStore | None = None,
        document_repository: DocumentRepository | None = None,
        event_publisher: DaprEventPublisher | None = None,
    ) -> None:
        """Initialize the processor.

        Args:
            blob_client: Azure Blob Storage client.
            raw_document_store: Raw document storage.
            document_repository: Generic document repository.
            event_publisher: DAPR event publisher.
        """
        self._blob_client = blob_client
        self._raw_store = raw_document_store
        self._doc_repo = document_repository
        self._event_publisher = event_publisher

    # set_dependencies inherited from ContentProcessor ABC

    async def process(
        self,
        job: IngestionJob,
        source_config: SourceConfig,
    ) -> ProcessorResult:
        """Process a JSON ingestion job.

        Story 2-12: Implements two extraction paths:
        - Path A (AI): Store pending → publish event → async result
        - Path B (Direct): Extract from JSON → store complete → emit event

        Args:
            job: The queued ingestion job.
            source_config: Typed SourceConfig from MongoDB.

        Returns:
            ProcessorResult with success status and extracted data.
        """
        source_id = source_config.source_id or job.source_id
        is_pull_mode = job.is_pull_mode
        transformation = source_config.transformation
        ai_agent_id = transformation.get_ai_agent_id()

        logger.info(
            "Processing JSON content",
            ingestion_id=job.ingestion_id,
            source_id=source_id,
            blob_path=job.blob_path if not is_pull_mode else None,
            is_pull_mode=is_pull_mode,
            ai_agent_id=ai_agent_id,
            extraction_path="A" if ai_agent_id else "B",
        )

        try:
            # Step 1: Get content (inline for pull mode, download for blob mode)
            if is_pull_mode:
                content = job.content  # type: ignore[assignment]
            else:
                content = await self._download_blob(job)

            # Step 2: Validate JSON
            raw_json = self._validate_json(content)

            # Step 3: Store raw document
            raw_doc = await self._store_raw_document(
                content=content,
                source_config=source_config,
                job=job,
            )

            # Step 4: Extract based on path
            if ai_agent_id:
                # Path A: AI Extraction (async event-driven)
                return await self._process_path_a(
                    raw_doc=raw_doc,
                    raw_json=raw_json,
                    job=job,
                    source_config=source_config,
                    ai_agent_id=ai_agent_id,
                    content_length=len(content),
                )
            else:
                # Path B: Direct Extraction (synchronous)
                return await self._process_path_b(
                    raw_doc=raw_doc,
                    raw_json=raw_json,
                    job=job,
                    source_config=source_config,
                    content_length=len(content),
                )

        except DuplicateDocumentError as e:
            # Duplicate is actually a success case - we skip processing
            logger.info(
                "Duplicate document detected, skipping",
                ingestion_id=job.ingestion_id,
                source_id=source_id,
                content_hash=str(e),
            )
            # Record duplicate metrics
            StorageMetrics.record_duplicate(source_id)
            return ProcessorResult(
                success=True,
                is_duplicate=True,
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

    async def _process_path_a(
        self,
        raw_doc: dict[str, Any],
        raw_json: str,
        job: IngestionJob,
        source_config: SourceConfig,
        ai_agent_id: str,
        content_length: int,
    ) -> ProcessorResult:
        """Path A: AI Extraction via async events.

        Story 2-12: Stores document with status="pending", publishes
        AgentRequestEvent, and returns. Result arrives via subscriber.

        Args:
            raw_doc: Raw document reference.
            raw_json: Validated JSON content string.
            job: Ingestion job.
            source_config: Source configuration.
            ai_agent_id: AI agent to use for extraction.
            content_length: Size of content for metrics.

        Returns:
            ProcessorResult indicating async processing initiated.
        """
        import json

        source_id = source_config.source_id or job.source_id

        # Parse JSON to get extracted_fields for linkage (empty for now)
        json_data = json.loads(raw_json)

        # Create document with status="pending" and empty extracted_fields
        extraction_result = {
            "extracted_fields": {},  # Will be filled by AI Model
            "confidence": 0.0,
            "validation_passed": False,
            "validation_warnings": [],
            "status": "pending",
        }

        document = self._create_document_index(
            raw_doc=raw_doc,
            extraction_result=extraction_result,
            job=job,
            source_config=source_config,
        )

        # Store document to get document_id for correlation
        await self._store_document(document, source_config)

        logger.info(
            "Document stored with pending status",
            document_id=document.document_id,
            source_id=source_id,
            ai_agent_id=ai_agent_id,
        )

        # Build EntityLinkage from job linkage or extracted fields
        linkage_data = job.linkage or {}
        # Merge any linkage fields from JSON itself
        for field in source_config.transformation.extract_fields or []:
            if field in json_data and field not in linkage_data:
                linkage_data[field] = json_data[field]

        # Create EntityLinkage with available fields
        # EntityLinkage requires at least one field - use source_id as region_id fallback
        # when no explicit entity linkage is available
        has_linkage = any(
            [
                linkage_data.get("farmer_id"),
                linkage_data.get("region_id"),
                linkage_data.get("group_id"),
                linkage_data.get("collection_point_id"),
                linkage_data.get("factory_id"),
            ]
        )

        if not has_linkage:
            # Use source_id as region_id for routing when no explicit linkage exists
            linkage_data["region_id"] = source_id

        entity_linkage = EntityLinkage(
            farmer_id=linkage_data.get("farmer_id"),
            region_id=linkage_data.get("region_id"),
            group_id=linkage_data.get("group_id"),
            collection_point_id=linkage_data.get("collection_point_id"),
            factory_id=linkage_data.get("factory_id"),
        )

        # Build AgentRequestEvent with request_id = document_id
        agent_request = AgentRequestEvent(
            request_id=document.document_id,  # Use document_id for correlation
            agent_id=ai_agent_id,
            linkage=entity_linkage,
            input_data={
                "raw_content": raw_json,
                "content_type": "application/json",
                "source_id": source_id,
            },
            source="collection-model",
        )

        # Publish AgentRequestEvent to ai.agent.requested topic
        published = await self._publish_agent_request(agent_request)

        if not published:
            logger.error(
                "Failed to publish AgentRequestEvent",
                document_id=document.document_id,
                agent_id=ai_agent_id,
            )
            # Update document status to failed
            document.extraction.status = "failed"
            document.extraction.error_type = "event_publish"
            document.extraction.error_message = "Failed to publish agent request event"
            await self._update_document(document, source_config)
            return ProcessorResult(
                success=False,
                document_id=document.document_id,
                error_message="Failed to publish agent request event",
                error_type="event_publish",
            )

        logger.info(
            "AgentRequestEvent published - awaiting async result",
            document_id=document.document_id,
            agent_id=ai_agent_id,
            request_id=document.document_id,
        )

        # Record storage metrics
        StorageMetrics.record_stored(source_id, content_length)

        # Return success - extraction will complete asynchronously
        return ProcessorResult(
            success=True,
            document_id=document.document_id,
            extracted_data={},  # Empty until AI completes
            pending_extraction=True,  # Indicate async processing
        )

    async def _process_path_b(
        self,
        raw_doc: dict[str, Any],
        raw_json: str,
        job: IngestionJob,
        source_config: SourceConfig,
        content_length: int,
    ) -> ProcessorResult:
        """Path B: Direct extraction without AI.

        Extracts fields directly from JSON, stores with status="complete",
        and emits success event synchronously.

        Args:
            raw_doc: Raw document reference.
            raw_json: Validated JSON content string.
            job: Ingestion job.
            source_config: Source configuration.
            content_length: Size of content for metrics.

        Returns:
            ProcessorResult with extracted data.
        """
        source_id = source_config.source_id or job.source_id

        # Direct extraction from JSON
        extraction_result = await self._extract_direct(
            raw_content=raw_json,
            source_config=source_config,
        )

        # Create document index with status="complete"
        document = self._create_document_index(
            raw_doc=raw_doc,
            extraction_result=extraction_result,
            job=job,
            source_config=source_config,
        )

        # Store to config-driven collection
        await self._store_document(document, source_config)

        # Emit success event
        await self._emit_success_event(document, source_config)

        logger.info(
            "JSON processing completed (Path B - direct extraction)",
            ingestion_id=job.ingestion_id,
            document_id=document.document_id,
            source_id=source_id,
        )

        # Record storage metrics
        StorageMetrics.record_stored(source_id, content_length)

        return ProcessorResult(
            success=True,
            document_id=document.document_id,
            extracted_data=extraction_result.get("extracted_fields", {}),
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
        source_config: SourceConfig,
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

    async def _extract_direct(
        self,
        raw_content: str,
        source_config: SourceConfig,
    ) -> dict[str, Any]:
        """Path B: Direct JSON extraction without AI.

        Story 2-12: This is the synchronous extraction path used when
        ai_agent_id is not set in source config.

        Args:
            raw_content: Validated JSON content string.
            source_config: Source configuration with extract_fields.

        Returns:
            Extraction result dict with status="complete".
        """
        import json

        transformation = source_config.transformation

        try:
            json_data = json.loads(raw_content)
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Failed to parse JSON for direct extraction: {e}") from e

        extract_fields = transformation.extract_fields
        extracted = {}
        missing_fields = []
        for field in extract_fields:
            if field in json_data:
                extracted[field] = json_data[field]
            else:
                missing_fields.append(field)

        # Log warning for missing fields (observability)
        if missing_fields:
            logger.warning(
                "Direct extraction: configured fields not found in JSON",
                missing_fields=missing_fields,
                available_fields=list(json_data.keys()),
                source_id=source_config.source_id,
            )

        return {
            "extracted_fields": extracted,
            # Confidence is 1.0 because direct extraction is deterministic -
            # the field either exists and is extracted exactly, or it doesn't.
            "confidence": 1.0,
            "validation_passed": True,
            "validation_warnings": [f"Missing field: {f}" for f in missing_fields],
            "status": "complete",  # Direct extraction is synchronous
        }

    def _create_document_index(
        self,
        raw_doc: dict[str, Any],
        extraction_result: dict[str, Any],
        job: IngestionJob,
        source_config: SourceConfig,
    ) -> DocumentIndex:
        """Create a document index from extraction results.

        Story 2-12: Now handles status field for async extraction tracking.
        - status="pending": Awaiting AI Model result (Path A)
        - status="complete": Extraction finished (Path B or after AI completes)
        - status="failed": Extraction failed

        For pull mode jobs with linkage, the linkage fields from iteration
        are merged into the extracted_fields before building linkage_fields.
        """
        transformation = source_config.transformation
        ai_agent_id = transformation.get_ai_agent_id() or "direct-extraction"

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
            status=extraction_result.get("status", "complete"),
            confidence=extraction_result.get("confidence", 1.0),
            validation_passed=extraction_result.get("validation_passed", True),
            validation_warnings=extraction_result.get("validation_warnings", []),
            error_type=extraction_result.get("error_type"),
            error_message=extraction_result.get("error_message"),
        )

        ingestion = IngestionMetadata(
            ingestion_id=job.ingestion_id,
            source_id=job.source_id,
            received_at=job.created_at,
            processed_at=datetime.now(UTC),
        )

        # Merge linkage from pull mode iteration into extracted fields
        extracted_fields = extraction_result.get("extracted_fields", {}).copy()
        if job.linkage:
            extracted_fields.update(job.linkage)

        return DocumentIndex.from_extraction(
            raw_document=raw_ref,
            extraction=extraction,
            ingestion=ingestion,
            extracted_fields=extracted_fields,
            source_config=source_config,
        )

    async def _store_document(
        self,
        document: DocumentIndex,
        source_config: SourceConfig,
    ) -> None:
        """Store document to config-driven collection."""
        if not self._doc_repo:
            raise ConfigurationError("Document repository not configured")

        # Get collection name FROM CONFIG - not hardcoded!
        collection_name = source_config.storage.index_collection

        if not collection_name:
            raise ConfigurationError("No index_collection in storage config")

        # Get link field for indexing
        link_field = source_config.transformation.link_field

        # Ensure indexes exist
        await self._doc_repo.ensure_indexes(collection_name, link_field)

        # Save document
        await self._doc_repo.save(document, collection_name)

    async def _emit_success_event(
        self,
        document: DocumentIndex,
        source_config: SourceConfig,
    ) -> None:
        """Emit success event to config-driven topic."""
        logger.info(
            "Attempting to emit success event",
            document_id=document.document_id,
            source_id=source_config.source_id,
            has_event_publisher=self._event_publisher is not None,
        )
        if not self._event_publisher:
            logger.warning("Event publisher not configured, skipping event emission")
            return

        result = await self._event_publisher.publish_success(source_config, document)
        logger.info(
            "Event publish result",
            document_id=document.document_id,
            success=result,
        )

    async def _publish_agent_request(
        self,
        agent_request: AgentRequestEvent,
    ) -> bool:
        """Publish AgentRequestEvent to ai.agent.requested topic.

        Story 2-12: Used in Path A to trigger AI Model extraction asynchronously.

        Args:
            agent_request: The agent request event to publish.

        Returns:
            True if published successfully, False otherwise.
        """
        if not self._event_publisher:
            logger.warning(
                "Event publisher not configured, cannot publish agent request",
                request_id=agent_request.request_id,
                agent_id=agent_request.agent_id,
            )
            return False

        topic = AIModelEventTopic.AGENT_REQUESTED

        # Convert Pydantic model to dict for publishing
        payload = agent_request.model_dump(mode="json")

        logger.debug(
            "Publishing AgentRequestEvent",
            topic=topic,
            request_id=agent_request.request_id,
            agent_id=agent_request.agent_id,
        )

        return await self._event_publisher.publish(
            topic=topic,
            payload=payload,
            source_id=agent_request.input_data.get("source_id", "collection-model"),
        )

    async def _update_document(
        self,
        document: DocumentIndex,
        source_config: SourceConfig,
    ) -> None:
        """Update an existing document in the collection.

        Story 2-12: Used to update document status after AI Model responds.

        Args:
            document: The document to update.
            source_config: Source configuration with collection name.
        """
        if not self._doc_repo:
            raise ConfigurationError("Document repository not configured")

        collection_name = source_config.storage.index_collection
        if not collection_name:
            raise ConfigurationError("No index_collection in storage config")

        await self._doc_repo.update(document, collection_name)
