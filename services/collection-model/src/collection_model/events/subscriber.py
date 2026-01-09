"""DAPR streaming subscription handlers for Collection Model.

Story 0.6.6: Collection Model Streaming Subscriptions
Story 2-12: AI Model Event-Driven Communication

This module implements DAPR SDK streaming subscriptions per ADR-010/ADR-011.
Replaces the FastAPI HTTP callback handlers with outbound streaming.

Key Pattern:
- Handlers receive message via `subscribe_with_handler()`
- `message.data()` returns dict directly (NOT JSON string)
- Return `TopicEventResponse("success"|"retry"|"drop")`
- DLQ configured via `dead_letter_topic` parameter in code

CRITICAL: Event Loop Handling
- DAPR streaming handlers run in a separate thread
- Motor (MongoDB async driver) is bound to the main event loop
- Use `asyncio.run_coroutine_threadsafe()` to schedule on main loop

Story 2-12 Additions:
- handle_agent_completed_event: Handles AgentCompletedEvent from AI Model
- handle_agent_failed_event: Handles AgentFailedEvent from AI Model
- set_ai_event_handlers: Sets up document repository and event publisher for AI events
"""

import asyncio
import json
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog
from dapr.clients import DaprClient
from dapr.clients.grpc._response import TopicEventResponse
from fp_common.events.ai_model_events import (
    AgentCompletedEvent,
    AgentFailedEvent,
    ExtractorAgentResult,
)
from fp_common.models.domain_events import AIModelEventTopic
from opentelemetry import metrics, trace
from pydantic import BaseModel, Field, ValidationError

if TYPE_CHECKING:
    from collection_model.infrastructure.dapr_event_publisher import DaprEventPublisher
    from collection_model.infrastructure.document_repository import DocumentRepository
    from collection_model.infrastructure.ingestion_queue import IngestionQueue
    from collection_model.infrastructure.metrics import EventMetrics
    from collection_model.services.source_config_service import SourceConfigService

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter("collection-model")

# Metrics for event processing
event_processing_counter = meter.create_counter(
    name="collection_event_processing_total",
    description="Total events processed by Collection Model streaming subscriptions",
    unit="1",
)


# =============================================================================
# Event Payload Models
# =============================================================================


class BlobEventData(BaseModel):
    """Data payload for blob-created events (Azure Event Grid format)."""

    content_length: int = Field(alias="contentLength", default=0)
    etag: str = Field(alias="eTag", default="")
    content_type: str = Field(alias="contentType", default="application/octet-stream")
    blob_type: str = Field(alias="blobType", default="BlockBlob")
    url: str = Field(default="")


class BlobCreatedEvent(BaseModel):
    """Azure Event Grid blob-created event structure."""

    id: str = Field(default="")
    event_type: str = Field(alias="eventType", default="")
    subject: str = Field(default="")
    event_time: str = Field(alias="eventTime", default="")
    data: BlobEventData = Field(default_factory=BlobEventData)


# =============================================================================
# Module-level service references (set during startup)
# =============================================================================

_source_config_service: "SourceConfigService | None" = None
_ingestion_queue: "IngestionQueue | None" = None
_event_metrics: "EventMetrics | None" = None
_main_event_loop: asyncio.AbstractEventLoop | None = None

# Story 2-12: AI Model event handler dependencies
_document_repository: "DocumentRepository | None" = None
_event_publisher: "DaprEventPublisher | None" = None
_registered_agent_ids: set[str] = set()  # Track which agent topics we've subscribed to


def set_blob_processor(
    source_config_service: "SourceConfigService",
    ingestion_queue: "IngestionQueue",
    event_metrics: "EventMetrics | None" = None,
) -> None:
    """Set the blob processing services (called during service startup).

    Args:
        source_config_service: Service for looking up source configs.
        ingestion_queue: Queue for storing ingestion jobs.
        event_metrics: Optional metrics for recording event stats.
    """
    global _source_config_service, _ingestion_queue, _event_metrics
    _source_config_service = source_config_service
    _ingestion_queue = ingestion_queue
    _event_metrics = event_metrics
    logger.info("Blob processing services set for streaming subscriptions")


def set_main_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Set the main event loop for async operations (called during service startup).

    CRITICAL: The DAPR streaming handlers run in a separate thread, but Motor
    (MongoDB async driver) and other async clients are bound to the main event loop.
    We must schedule async operations on the main loop, not create new loops.
    """
    global _main_event_loop
    _main_event_loop = loop
    logger.info("Main event loop set for streaming subscriptions")


def set_ai_event_handlers(
    document_repository: "DocumentRepository",
    event_publisher: "DaprEventPublisher",
    source_config_service: "SourceConfigService",
) -> None:
    """Set AI Model event handler dependencies (called during service startup).

    Story 2-12: These dependencies are used by the AgentCompleted/Failed handlers
    to update documents and emit success events.

    Args:
        document_repository: Repository for updating documents.
        event_publisher: Publisher for emitting success events.
        source_config_service: Service for looking up source configs.
    """
    global _document_repository, _event_publisher, _source_config_service
    _document_repository = document_repository
    _event_publisher = event_publisher
    _source_config_service = source_config_service
    logger.info("AI Model event handler dependencies set")


def register_agent_id(agent_id: str) -> None:
    """Register an agent_id for subscription.

    Story 2-12: Called during startup to register which agent topics to subscribe to.

    Args:
        agent_id: The agent configuration ID.
    """
    global _registered_agent_ids
    _registered_agent_ids.add(agent_id)
    logger.info("Registered agent for subscription", agent_id=agent_id)


# =============================================================================
# Helper Functions
# =============================================================================


def _parse_event_subject(subject: str) -> tuple[str, str]:
    """Parse container and blob path from Event Grid subject.

    Subject format: /blobServices/default/containers/{container}/blobs/{blob_path}

    Args:
        subject: The event subject string.

    Returns:
        Tuple of (container, blob_path), or ("", "") if parsing fails.
    """
    parts = subject.split("/containers/")
    if len(parts) < 2:
        return "", ""

    container_and_blob = parts[1]
    if "/blobs/" not in container_and_blob:
        return "", ""

    container, blob_path = container_and_blob.split("/blobs/", 1)
    return container, blob_path


async def _process_blob_event_async(
    container: str,
    blob_path: str,
    content_length: int,
    etag: str,
    event_id: str,
    trace_id: str | None,
) -> bool:
    """Process a blob event asynchronously.

    This function contains the actual blob processing logic, reused from
    the original api/events.py implementation.

    Args:
        container: Blob container name.
        blob_path: Path to blob within container.
        content_length: Blob size in bytes.
        etag: Blob ETag for idempotency.
        event_id: Event ID for logging.
        trace_id: Optional trace ID for distributed tracing.

    Returns:
        True if job was queued successfully, False otherwise.

    Raises:
        ConnectionError: On transient database errors.
        ValueError: On validation errors (permanent).
    """
    from collection_model.domain.ingestion_job import IngestionJob

    if _source_config_service is None or _ingestion_queue is None:
        raise ConnectionError("Services not initialized")

    logger.info(
        "Processing blob event",
        event_id=event_id,
        container=container,
        blob_path=blob_path,
        content_length=content_length,
    )

    # Look up source config by container
    config = await _source_config_service.get_config_by_container(container)
    if config is None:
        logger.warning(
            "No matching source config for container",
            container=container,
            blob_path=blob_path,
        )
        if _event_metrics:
            _event_metrics.increment_unmatched(container)
        # No config = permanent error (drop)
        raise ValueError(f"No source config for container: {container}")

    source_id = config.source_id or ""

    # Check if source is enabled
    if not config.enabled:
        logger.info(
            "Source config is disabled",
            source_id=source_id,
            container=container,
        )
        if _event_metrics:
            _event_metrics.increment_disabled(source_id)
        # Disabled = permanent state (drop)
        raise ValueError(f"Source config disabled: {source_id}")

    # Extract metadata from blob path using path_pattern
    metadata = _source_config_service.extract_path_metadata(blob_path, config)

    # Create and queue ingestion job
    job = IngestionJob(
        blob_path=blob_path,
        blob_etag=etag,
        container=container,
        source_id=source_id,
        content_length=content_length,
        metadata=metadata,
        trace_id=trace_id,
    )

    queued = await _ingestion_queue.queue_job(job)
    if queued:
        logger.info(
            "Ingestion job queued",
            ingestion_id=job.ingestion_id,
            source_id=source_id,
            blob_path=blob_path,
            metadata=metadata,
        )
        if _event_metrics:
            _event_metrics.increment_queued(source_id)
        return True

    logger.info(
        "Duplicate event skipped (already processed)",
        blob_path=blob_path,
        etag=etag,
    )
    if _event_metrics:
        _event_metrics.increment_duplicate(source_id)
    # Duplicate = success (already processed)
    return True


# =============================================================================
# Event Handler
# =============================================================================


def handle_blob_event(message) -> TopicEventResponse:
    """Handle blob-created events via DAPR streaming subscription.

    CRITICAL:
    - message.data() returns a dict, NOT a JSON string
    - Must return TopicEventResponse, not None
    - Runs in DAPR subscription thread, NOT main thread

    Args:
        message: DAPR subscription message.

    Returns:
        TopicEventResponse indicating success, retry, or drop.
    """
    with tracer.start_as_current_span("handle_blob_event_streaming") as span:
        # Extract message data - DAPR SDK returns dict, NOT JSON string
        try:
            raw_data = message.data()
            # Handle both dict and string formats for safety
            if isinstance(raw_data, str):
                data = json.loads(raw_data)
            elif isinstance(raw_data, bytes):
                data = json.loads(raw_data.decode("utf-8"))
            else:
                data = raw_data

            # Support both single event and array of events
            # Azure Event Grid sends arrays; DAPR may deliver individually
            events = data if isinstance(data, list) else [data]

        except Exception as e:
            logger.error("Failed to parse message data", error=str(e))
            span.set_attribute("error", "parse_failed")
            event_processing_counter.add(1, {"topic": "blob_created", "status": "drop"})
            return TopicEventResponse("drop")

        # Check service initialization
        if _source_config_service is None or _ingestion_queue is None:
            logger.error("Blob processing services not initialized - will retry")
            span.set_attribute("error", "services_not_initialized")
            event_processing_counter.add(1, {"topic": "blob_created", "status": "retry"})
            return TopicEventResponse("retry")

        # Check main event loop initialization
        if _main_event_loop is None:
            logger.error("Main event loop not initialized - will retry")
            span.set_attribute("error", "event_loop_not_initialized")
            event_processing_counter.add(1, {"topic": "blob_created", "status": "retry"})
            return TopicEventResponse("retry")

        # Process each event
        processed_count = 0
        for event_data in events:
            try:
                # Handle CloudEvent wrapper or direct Event Grid format
                if "data" in event_data and "subject" not in event_data:
                    # CloudEvent wrapper - extract inner data
                    inner = event_data.get("data", {})
                    event_data = inner.get("payload", inner)

                # Parse event
                event = BlobCreatedEvent.model_validate(event_data)

                # Only process BlobCreated events
                if event.event_type != "Microsoft.Storage.BlobCreated":
                    logger.debug(
                        "Skipping non-blob-created event",
                        event_type=event.event_type,
                    )
                    continue

                # Parse container and blob path from subject
                container, blob_path = _parse_event_subject(event.subject)
                if not container or not blob_path:
                    logger.warning("Invalid event subject format", subject=event.subject)
                    continue

                span.set_attribute("event.container", container)
                span.set_attribute("event.blob_path", blob_path)

                # Process on MAIN event loop using run_coroutine_threadsafe
                future = asyncio.run_coroutine_threadsafe(
                    _process_blob_event_async(
                        container=container,
                        blob_path=blob_path,
                        content_length=event.data.content_length,
                        etag=event.data.etag,
                        event_id=event.id,
                        trace_id=None,  # Could extract from message headers
                    ),
                    _main_event_loop,
                )
                future.result(timeout=30)  # 30 second timeout
                processed_count += 1

            except ValidationError as e:
                logger.error("Invalid blob event payload", error=str(e))
                # Validation error on single event - continue processing others
                continue

            except ValueError as e:
                # Permanent errors (no config, disabled) - drop this event
                logger.warning(
                    "Permanent error processing blob event",
                    error=str(e),
                )
                event_processing_counter.add(1, {"topic": "blob_created", "status": "drop"})
                return TopicEventResponse("drop")

            except (ConnectionError, TimeoutError) as e:
                # Transient errors - retry the whole message
                logger.warning(
                    "Transient error processing blob event, will retry",
                    error=str(e),
                )
                span.set_attribute("error", str(e))
                event_processing_counter.add(1, {"topic": "blob_created", "status": "retry"})
                return TopicEventResponse("retry")

            except Exception as e:
                # Unknown error - check if permanent or transient
                error_str = str(e).lower()
                if any(term in error_str for term in ["validation", "invalid", "not found", "disabled"]):
                    logger.error(
                        "Permanent error processing blob event - sending to DLQ",
                        error=str(e),
                    )
                    span.set_attribute("error", str(e))
                    event_processing_counter.add(1, {"topic": "blob_created", "status": "drop"})
                    return TopicEventResponse("drop")

                # Assume transient - retry
                logger.exception("Unexpected error processing blob event")
                span.set_attribute("error", str(e))
                event_processing_counter.add(1, {"topic": "blob_created", "status": "retry"})
                return TopicEventResponse("retry")

        # All events processed successfully
        if processed_count > 0:
            logger.info(
                "Blob events processed successfully",
                processed_count=processed_count,
            )
            span.set_attribute("processing.success", True)
            span.set_attribute("processing.count", processed_count)
            event_processing_counter.add(1, {"topic": "blob_created", "status": "success"})
            return TopicEventResponse("success")

        # No events matched criteria - still success (nothing to process)
        logger.debug("No blob-created events in message")
        event_processing_counter.add(1, {"topic": "blob_created", "status": "success"})
        return TopicEventResponse("success")


# =============================================================================
# Story 2-12: AI Model Event Handlers
# =============================================================================


async def _process_agent_completed_async(event: AgentCompletedEvent) -> bool:
    """Process AgentCompletedEvent asynchronously.

    Story 2-12: Updates the pending document with extraction results
    and emits the success event.

    Args:
        event: The AgentCompletedEvent from AI Model.

    Returns:
        True if processed successfully, False otherwise.

    Raises:
        ConnectionError: On transient database errors.
        ValueError: On permanent errors (document not found, etc.).
    """
    if _document_repository is None or _event_publisher is None or _source_config_service is None:
        raise ConnectionError("AI event handler services not initialized")

    logger.info(
        "Processing AgentCompletedEvent",
        request_id=event.request_id,
        agent_id=event.agent_id,
        result_type=event.result.result_type,
    )

    # Look up source config by agent_id to get collection name
    config = await _source_config_service.get_config_by_agent_id(event.agent_id)
    if config is None:
        logger.error(
            "No source config found for agent_id",
            agent_id=event.agent_id,
            request_id=event.request_id,
        )
        raise ValueError(f"No source config for agent_id: {event.agent_id}")

    collection_name = config.storage.index_collection
    if not collection_name:
        raise ValueError(f"No index_collection in source config for agent: {event.agent_id}")

    # Find the pending document by request_id (which equals document_id)
    document = await _document_repository.find_pending_by_request_id(
        request_id=event.request_id,
        collection_name=collection_name,
    )

    if document is None:
        logger.warning(
            "Pending document not found for request_id - may already be processed",
            request_id=event.request_id,
            collection_name=collection_name,
        )
        # Not an error - document may have already been processed (idempotency)
        return True

    # Update document with extraction results
    if isinstance(event.result, ExtractorAgentResult):
        document.extracted_fields = event.result.extracted_fields
        document.extraction.confidence = 1.0  # AI extraction confidence
        document.extraction.validation_passed = len(event.result.validation_errors) == 0
        document.extraction.validation_warnings = event.result.validation_warnings

        # Update linkage_fields based on extracted_fields
        transformation = config.transformation
        extract_field_names = transformation.extract_fields or []
        field_mappings = transformation.field_mappings or {}
        for field_name in extract_field_names:
            if field_name in document.extracted_fields:
                mapped_name = field_mappings.get(field_name, field_name)
                document.linkage_fields[mapped_name] = document.extracted_fields[field_name]

    document.extraction.status = "complete"
    document.extraction.extraction_timestamp = datetime.now(UTC)

    # Save updated document
    updated = await _document_repository.update(document, collection_name)
    if not updated:
        logger.error(
            "Failed to update document",
            document_id=document.document_id,
            collection_name=collection_name,
        )
        raise ConnectionError(f"Failed to update document: {document.document_id}")

    logger.info(
        "Document updated with extraction results",
        document_id=document.document_id,
        status="complete",
        field_count=len(document.extracted_fields),
    )

    # Emit success event (Story 2-12 AC5)
    result = await _event_publisher.publish_success(config, document)
    logger.info(
        "Success event published",
        document_id=document.document_id,
        published=result,
    )

    return True


async def _process_agent_failed_async(event: AgentFailedEvent) -> bool:
    """Process AgentFailedEvent asynchronously.

    Story 2-12: Updates the pending document with failure status.

    Args:
        event: The AgentFailedEvent from AI Model.

    Returns:
        True if processed successfully, False otherwise.

    Raises:
        ConnectionError: On transient database errors.
        ValueError: On permanent errors.
    """
    if _document_repository is None or _source_config_service is None:
        raise ConnectionError("AI event handler services not initialized")

    logger.info(
        "Processing AgentFailedEvent",
        request_id=event.request_id,
        agent_id=event.agent_id,
        error_type=event.error_type,
        error_message=event.error_message,
    )

    # Look up source config by agent_id to get collection name
    config = await _source_config_service.get_config_by_agent_id(event.agent_id)
    if config is None:
        logger.error(
            "No source config found for agent_id",
            agent_id=event.agent_id,
            request_id=event.request_id,
        )
        raise ValueError(f"No source config for agent_id: {event.agent_id}")

    collection_name = config.storage.index_collection
    if not collection_name:
        raise ValueError(f"No index_collection in source config for agent: {event.agent_id}")

    # Find the pending document by request_id
    document = await _document_repository.find_pending_by_request_id(
        request_id=event.request_id,
        collection_name=collection_name,
    )

    if document is None:
        logger.warning(
            "Pending document not found for request_id",
            request_id=event.request_id,
            collection_name=collection_name,
        )
        return True

    # Update document with failure status
    document.extraction.status = "failed"
    document.extraction.error_type = event.error_type
    document.extraction.error_message = event.error_message
    document.extraction.extraction_timestamp = datetime.now(UTC)

    # Save updated document
    updated = await _document_repository.update(document, collection_name)
    if not updated:
        logger.error(
            "Failed to update document with failure status",
            document_id=document.document_id,
            collection_name=collection_name,
        )
        raise ConnectionError(f"Failed to update document: {document.document_id}")

    logger.warning(
        "Document marked as failed",
        document_id=document.document_id,
        error_type=event.error_type,
        error_message=event.error_message,
    )

    return True


def handle_agent_completed_event(message) -> TopicEventResponse:
    """Handle AgentCompletedEvent via DAPR streaming subscription.

    Story 2-12: Receives extraction results from AI Model and updates
    the pending document.

    Args:
        message: DAPR subscription message.

    Returns:
        TopicEventResponse indicating success, retry, or drop.
    """
    with tracer.start_as_current_span("handle_agent_completed_event") as span:
        try:
            raw_data = message.data()
            if isinstance(raw_data, str):
                data = json.loads(raw_data)
            elif isinstance(raw_data, bytes):
                data = json.loads(raw_data.decode("utf-8"))
            else:
                data = raw_data

            # Parse the event
            event = AgentCompletedEvent.model_validate(data)
            span.set_attribute("event.request_id", event.request_id)
            span.set_attribute("event.agent_id", event.agent_id)

        except Exception as e:
            logger.error("Failed to parse AgentCompletedEvent", error=str(e))
            span.set_attribute("error", "parse_failed")
            event_processing_counter.add(1, {"topic": "agent_completed", "status": "drop"})
            return TopicEventResponse("drop")

        # Check service initialization
        if _document_repository is None or _main_event_loop is None:
            logger.error("AI event handler services not initialized - will retry")
            span.set_attribute("error", "services_not_initialized")
            event_processing_counter.add(1, {"topic": "agent_completed", "status": "retry"})
            return TopicEventResponse("retry")

        try:
            # Process on MAIN event loop
            future = asyncio.run_coroutine_threadsafe(
                _process_agent_completed_async(event),
                _main_event_loop,
            )
            future.result(timeout=60)  # 60 second timeout for AI result processing

            logger.info(
                "AgentCompletedEvent processed successfully",
                request_id=event.request_id,
                agent_id=event.agent_id,
            )
            span.set_attribute("processing.success", True)
            event_processing_counter.add(1, {"topic": "agent_completed", "status": "success"})
            return TopicEventResponse("success")

        except ValueError as e:
            logger.warning(
                "Permanent error processing AgentCompletedEvent",
                error=str(e),
                request_id=event.request_id,
            )
            event_processing_counter.add(1, {"topic": "agent_completed", "status": "drop"})
            return TopicEventResponse("drop")

        except (ConnectionError, TimeoutError) as e:
            logger.warning(
                "Transient error processing AgentCompletedEvent, will retry",
                error=str(e),
                request_id=event.request_id,
            )
            span.set_attribute("error", str(e))
            event_processing_counter.add(1, {"topic": "agent_completed", "status": "retry"})
            return TopicEventResponse("retry")

        except Exception as e:
            logger.exception(
                "Unexpected error processing AgentCompletedEvent",
                request_id=event.request_id,
            )
            span.set_attribute("error", str(e))
            event_processing_counter.add(1, {"topic": "agent_completed", "status": "retry"})
            return TopicEventResponse("retry")


def handle_agent_failed_event(message) -> TopicEventResponse:
    """Handle AgentFailedEvent via DAPR streaming subscription.

    Story 2-12: Receives failure notification from AI Model and updates
    the pending document.

    Args:
        message: DAPR subscription message.

    Returns:
        TopicEventResponse indicating success, retry, or drop.
    """
    with tracer.start_as_current_span("handle_agent_failed_event") as span:
        try:
            raw_data = message.data()
            if isinstance(raw_data, str):
                data = json.loads(raw_data)
            elif isinstance(raw_data, bytes):
                data = json.loads(raw_data.decode("utf-8"))
            else:
                data = raw_data

            # Parse the event
            event = AgentFailedEvent.model_validate(data)
            span.set_attribute("event.request_id", event.request_id)
            span.set_attribute("event.agent_id", event.agent_id)
            span.set_attribute("event.error_type", event.error_type)

        except Exception as e:
            logger.error("Failed to parse AgentFailedEvent", error=str(e))
            span.set_attribute("error", "parse_failed")
            event_processing_counter.add(1, {"topic": "agent_failed", "status": "drop"})
            return TopicEventResponse("drop")

        # Check service initialization
        if _document_repository is None or _main_event_loop is None:
            logger.error("AI event handler services not initialized - will retry")
            span.set_attribute("error", "services_not_initialized")
            event_processing_counter.add(1, {"topic": "agent_failed", "status": "retry"})
            return TopicEventResponse("retry")

        try:
            # Process on MAIN event loop
            future = asyncio.run_coroutine_threadsafe(
                _process_agent_failed_async(event),
                _main_event_loop,
            )
            future.result(timeout=30)

            logger.info(
                "AgentFailedEvent processed successfully",
                request_id=event.request_id,
                agent_id=event.agent_id,
            )
            span.set_attribute("processing.success", True)
            event_processing_counter.add(1, {"topic": "agent_failed", "status": "success"})
            return TopicEventResponse("success")

        except ValueError as e:
            logger.warning(
                "Permanent error processing AgentFailedEvent",
                error=str(e),
                request_id=event.request_id,
            )
            event_processing_counter.add(1, {"topic": "agent_failed", "status": "drop"})
            return TopicEventResponse("drop")

        except (ConnectionError, TimeoutError) as e:
            logger.warning(
                "Transient error processing AgentFailedEvent, will retry",
                error=str(e),
                request_id=event.request_id,
            )
            span.set_attribute("error", str(e))
            event_processing_counter.add(1, {"topic": "agent_failed", "status": "retry"})
            return TopicEventResponse("retry")

        except Exception as e:
            logger.exception(
                "Unexpected error processing AgentFailedEvent",
                request_id=event.request_id,
            )
            span.set_attribute("error", str(e))
            event_processing_counter.add(1, {"topic": "agent_failed", "status": "retry"})
            return TopicEventResponse("retry")


# =============================================================================
# Subscription Startup (ADR-010 Pattern)
# =============================================================================


def run_streaming_subscriptions() -> None:
    """Run streaming subscriptions in a background thread.

    This function matches the PoC pattern from ADR-010:
    - DaprClient created and kept alive in this function
    - Subscriptions established
    - Infinite loop keeps client alive until shutdown

    Called from a daemon thread in main.py.

    Story 2-12: Also subscribes to AI Model completion/failure topics
    for each registered agent_id.
    """
    from collection_model.config import settings

    logger.info("Starting DAPR streaming subscriptions for Collection Model...")

    # Wait for DAPR sidecar to be ready (configurable via COLLECTION_DAPR_SIDECAR_WAIT_SECONDS)
    time.sleep(settings.dapr_sidecar_wait_seconds)

    close_fns: list = []

    try:
        # Create client - must stay alive for subscriptions to work
        client = DaprClient()

        # Subscribe to blob-created events with DLQ
        # Topic name matches Azure Event Grid binding convention
        blob_close = client.subscribe_with_handler(
            pubsub_name="pubsub",
            topic="blob.created",
            handler_fn=handle_blob_event,
            dead_letter_topic="events.dlq",
        )
        close_fns.append(blob_close)
        logger.info(
            "Subscription established",
            topic="blob.created",
            dlq="events.dlq",
        )

        # Story 2-12: Subscribe to AI Model completion/failure topics for each registered agent
        for agent_id in _registered_agent_ids:
            completed_topic = AIModelEventTopic.agent_completed_topic(agent_id)
            failed_topic = AIModelEventTopic.agent_failed_topic(agent_id)

            # Subscribe to completed events
            completed_close = client.subscribe_with_handler(
                pubsub_name="pubsub",
                topic=completed_topic,
                handler_fn=handle_agent_completed_event,
                dead_letter_topic="events.dlq",
            )
            close_fns.append(completed_close)
            logger.info(
                "AI Agent completion subscription established",
                topic=completed_topic,
                agent_id=agent_id,
            )

            # Subscribe to failed events
            failed_close = client.subscribe_with_handler(
                pubsub_name="pubsub",
                topic=failed_topic,
                handler_fn=handle_agent_failed_event,
                dead_letter_topic="events.dlq",
            )
            close_fns.append(failed_close)
            logger.info(
                "AI Agent failure subscription established",
                topic=failed_topic,
                agent_id=agent_id,
            )

        logger.info(
            "All subscriptions started - keeping alive",
            subscription_count=len(close_fns),
            registered_agents=len(_registered_agent_ids),
        )

        # Keep subscriptions alive - client must not be garbage collected
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Subscription loop interrupted")
    except Exception as e:
        logger.exception("Subscription error", error=str(e))
    finally:
        # Clean up subscriptions
        for close_fn in close_fns:
            try:
                close_fn()
            except Exception as e:
                logger.warning("Error closing subscription", error=str(e))
        logger.info("All subscriptions closed")
