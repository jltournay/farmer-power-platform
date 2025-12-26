"""Azure Event Grid webhook handler for blob-created events.

This module handles incoming Event Grid events when blobs are created
in Azure Blob Storage containers (qc-analyzer-results, qc-analyzer-exceptions).
Events are validated, matched against source configurations, and queued
for processing.
"""

from typing import Any

import structlog
from collection_model.domain.ingestion_job import IngestionJob
from collection_model.infrastructure.ingestion_queue import IngestionQueue
from collection_model.services.source_config_service import SourceConfigService
from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/events", tags=["events"])

# Metrics counters (simple in-memory for now, can be replaced with proper metrics)
_metrics: dict[str, int] = {
    "events_received": 0,
    "events_queued": 0,
    "events_duplicate": 0,
    "events_unmatched": 0,
    "events_disabled": 0,
}


def get_metrics() -> dict[str, int]:
    """Get current event processing metrics."""
    return _metrics.copy()


def reset_metrics() -> None:
    """Reset metrics counters (for testing)."""
    for key in _metrics:
        _metrics[key] = 0


class BlobCreatedData(BaseModel):
    """Data payload for Microsoft.Storage.BlobCreated event."""

    api: str = Field(description="API that triggered the event")
    client_request_id: str = Field(default="", alias="clientRequestId", description="Client request ID")
    request_id: str = Field(default="", alias="requestId", description="Request ID")
    e_tag: str = Field(default="", alias="eTag", description="Blob ETag")
    content_type: str = Field(default="", alias="contentType", description="Blob content type")
    content_length: int = Field(default=0, alias="contentLength", description="Blob size in bytes")
    blob_type: str = Field(default="", alias="blobType", description="Type of blob")
    url: str = Field(description="Full URL to the blob")
    sequencer: str = Field(default="", description="Event sequencer")
    storage_diagnostics: dict[str, Any] = Field(
        default_factory=dict,
        alias="storageDiagnostics",
        description="Storage diagnostics",
    )


class EventGridEvent(BaseModel):
    """Azure Event Grid event schema."""

    id: str = Field(description="Unique event ID")
    topic: str = Field(default="", description="Event topic")
    subject: str = Field(description="Event subject (blob path)")
    event_type: str = Field(alias="eventType", description="Event type")
    event_time: str = Field(alias="eventTime", description="Event timestamp")
    data: dict[str, Any] = Field(description="Event data payload")
    data_version: str = Field(default="", alias="dataVersion", description="Data schema version")
    metadata_version: str = Field(default="", alias="metadataVersion", description="Metadata version")


class SubscriptionValidationData(BaseModel):
    """Data payload for subscription validation event."""

    validation_code: str = Field(alias="validationCode", description="Validation code to echo back")
    validation_url: str | None = Field(
        default=None,
        alias="validationUrl",
        description="Alternative validation URL",
    )


@router.post("/blob-created")
async def handle_blob_created(request: Request) -> Response:
    """Handle Azure Event Grid blob-created events.

    This endpoint handles two types of requests:
    1. Subscription validation handshake - Event Grid sends this when
       creating a new subscription to verify the endpoint.
    2. Blob-created events - Sent when a new blob is created in the
       monitored storage containers.

    Processing flow for blob-created events:
    1. Parse event and extract container/blob_path
    2. Look up source config by container
    3. If no match or disabled, log and skip
    4. Extract metadata from path using path_pattern
    5. Queue IngestionJob with idempotency check

    Args:
        request: The incoming HTTP request from Event Grid.

    Returns:
        Response with validation response or 202 Accepted for events.

    """
    try:
        body = await request.json()
    except Exception as e:
        logger.error("Failed to parse Event Grid request body", error=str(e))
        return Response(status_code=400, content="Invalid JSON body")

    # Event Grid sends events as an array
    if not isinstance(body, list):
        logger.warning("Expected array of events", body_type=type(body).__name__)
        return Response(status_code=400, content="Expected array of events")

    if len(body) == 0:
        return Response(status_code=202)

    # Check first event for subscription validation
    first_event = body[0]
    event_type = first_event.get("eventType", "")

    # Handle subscription validation handshake
    if event_type == "Microsoft.EventGrid.SubscriptionValidationEvent":
        return _handle_subscription_validation(first_event)

    # Get services from app state
    source_config_service: SourceConfigService | None = getattr(request.app.state, "source_config_service", None)
    ingestion_queue: IngestionQueue | None = getattr(request.app.state, "ingestion_queue", None)

    if source_config_service is None or ingestion_queue is None:
        logger.error("Services not initialized in app state")
        return Response(status_code=503, content="Service not ready")

    # Extract trace_id from headers for distributed tracing
    trace_id = request.headers.get("traceparent") or request.headers.get("x-trace-id")

    # Process blob-created events
    queued_count = 0
    for event in body:
        if event.get("eventType") == "Microsoft.Storage.BlobCreated":
            _metrics["events_received"] += 1
            result = await _process_blob_created_event(
                event=event,
                source_config_service=source_config_service,
                ingestion_queue=ingestion_queue,
                trace_id=trace_id,
            )
            if result:
                queued_count += 1

    logger.info(
        "Processed Event Grid batch",
        total_events=len(body),
        queued_count=queued_count,
    )

    return Response(status_code=202)


def _handle_subscription_validation(event: dict[str, Any]) -> Response:
    """Handle Event Grid subscription validation handshake.

    When creating an Event Grid subscription with webhook endpoint,
    Event Grid sends a validation request. We must respond with
    the validationCode to confirm we control the endpoint.

    Args:
        event: The validation event from Event Grid.

    Returns:
        Response with validationResponse JSON.

    """
    try:
        validation_data = SubscriptionValidationData.model_validate(event.get("data", {}))
        validation_code = validation_data.validation_code

        logger.info(
            "Event Grid subscription validation request received",
            validation_code=validation_code[:8] + "...",
        )

        return Response(
            content=f'{{"validationResponse": "{validation_code}"}}',
            media_type="application/json",
            status_code=200,
        )
    except Exception as e:
        logger.error(
            "Failed to handle subscription validation",
            error=str(e),
        )
        return Response(status_code=400, content="Invalid validation request")


async def _process_blob_created_event(
    event: dict[str, Any],
    source_config_service: SourceConfigService,
    ingestion_queue: IngestionQueue,
    trace_id: str | None,
) -> bool:
    """Process a single blob-created event.

    Args:
        event: The blob-created event from Event Grid.
        source_config_service: Service for looking up source configs.
        ingestion_queue: Queue for storing ingestion jobs.
        trace_id: Distributed tracing ID from request headers.

    Returns:
        True if job was queued successfully, False otherwise.

    """
    subject = event.get("subject", "")
    data = event.get("data", {})

    # Extract container and blob path from subject
    # Subject format: /blobServices/default/containers/{container}/blobs/{blob_path}
    container, blob_path = _parse_event_subject(subject)
    if not container or not blob_path:
        logger.warning("Invalid event subject format", subject=subject)
        return False

    content_length = data.get("contentLength", 0)
    etag = data.get("eTag", "")

    logger.info(
        "Processing blob-created event",
        event_id=event.get("id"),
        container=container,
        blob_path=blob_path,
        content_length=content_length,
    )

    # Look up source config by container
    config = await source_config_service.get_config_by_container(container)
    if config is None:
        logger.warning(
            "No matching source config for container",
            container=container,
            blob_path=blob_path,
        )
        _metrics["events_unmatched"] += 1
        return False

    source_id = config.get("source_id", "")

    # Check if source is enabled
    if not config.get("enabled", True):
        logger.info(
            "Source config is disabled",
            source_id=source_id,
            container=container,
        )
        _metrics["events_disabled"] += 1
        return False

    # Extract metadata from blob path using path_pattern
    metadata = source_config_service.extract_path_metadata(blob_path, config)

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

    queued = await ingestion_queue.queue_job(job)
    if queued:
        logger.info(
            "Ingestion job queued",
            ingestion_id=job.ingestion_id,
            source_id=source_id,
            blob_path=blob_path,
            metadata=metadata,
        )
        _metrics["events_queued"] += 1
        return True

    logger.info(
        "Duplicate event skipped (already processed)",
        blob_path=blob_path,
        etag=etag,
    )
    _metrics["events_duplicate"] += 1
    return False


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
        return ("", "")

    container_and_blob = parts[1]
    if "/blobs/" not in container_and_blob:
        return ("", "")

    container, blob_path = container_and_blob.split("/blobs/", 1)
    return (container, blob_path)
