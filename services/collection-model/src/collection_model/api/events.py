"""Event handlers for blob-created events and DAPR Job triggers.

This module handles:
1. Azure Event Grid events when blobs are created in storage containers
2. DAPR Job callbacks for scheduled pull ingestion (Story 2.7)

Events are validated, matched against source configurations, and queued
for processing.
"""

from typing import TYPE_CHECKING, Any

import structlog
from collection_model.domain.ingestion_job import IngestionJob
from collection_model.infrastructure.ingestion_queue import IngestionQueue
from collection_model.infrastructure.metrics import EventMetrics
from collection_model.services.source_config_service import SourceConfigService
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from collection_model.services.pull_job_handler import PullJobHandler

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api", tags=["events"])


class SubscriptionValidationData(BaseModel):
    """Data payload for subscription validation event."""

    validation_code: str = Field(alias="validationCode", description="Validation code to echo back")
    validation_url: str | None = Field(
        default=None,
        alias="validationUrl",
        description="Alternative validation URL",
    )


@router.post("/events/blob-created")
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
    event_metrics: EventMetrics | None = getattr(request.app.state, "event_metrics", None)

    if source_config_service is None or ingestion_queue is None:
        logger.error("Services not initialized in app state")
        return Response(status_code=503, content="Service not ready")

    # Extract trace_id from headers for distributed tracing
    trace_id = request.headers.get("traceparent") or request.headers.get("x-trace-id")

    # Process blob-created events
    queued_count = 0
    for event in body:
        if event.get("eventType") == "Microsoft.Storage.BlobCreated":
            if event_metrics:
                event_metrics.increment_received()
            result = await _process_blob_created_event(
                event=event,
                source_config_service=source_config_service,
                ingestion_queue=ingestion_queue,
                trace_id=trace_id,
                event_metrics=event_metrics,
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
    event_metrics: EventMetrics | None = None,
) -> bool:
    """Process a single blob-created event.

    Args:
        event: The blob-created event from Event Grid.
        source_config_service: Service for looking up source configs.
        ingestion_queue: Queue for storing ingestion jobs.
        trace_id: Distributed tracing ID from request headers.
        event_metrics: Optional metrics for recording event stats.

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
        if event_metrics:
            event_metrics.increment_unmatched(container)
        return False

    # Use typed attribute access from SourceConfig Pydantic model
    source_id = config.source_id or ""

    # Check if source is enabled
    if not config.enabled:
        logger.info(
            "Source config is disabled",
            source_id=source_id,
            container=container,
        )
        if event_metrics:
            event_metrics.increment_disabled(source_id)
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
        if event_metrics:
            event_metrics.increment_queued(source_id)
        return True

    logger.info(
        "Duplicate event skipped (already processed)",
        blob_path=blob_path,
        etag=etag,
    )
    if event_metrics:
        event_metrics.increment_duplicate(source_id)
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
        return "", ""

    container_and_blob = parts[1]
    if "/blobs/" not in container_and_blob:
        return "", ""

    container, blob_path = container_and_blob.split("/blobs/", 1)
    return container, blob_path


# =============================================================================
# DAPR Job Trigger Endpoint (Story 2.7)
# =============================================================================


class JobTriggerResponse(BaseModel):
    """Response for job trigger endpoint."""

    success: bool = Field(description="Whether the job completed successfully")
    source_id: str = Field(description="Source identifier")
    fetched: int = Field(default=0, description="Number of successful fetches")
    failed: int = Field(default=0, description="Number of failed fetches")
    duplicates: int = Field(default=0, description="Number of duplicate documents")
    error: str | None = Field(default=None, description="Error message if failed")


@router.post(
    "/v1/triggers/job/{source_id}",
    response_model=JobTriggerResponse,
    tags=["triggers"],
)
async def handle_job_trigger(
    source_id: str,
    request: Request,
) -> JobTriggerResponse:
    """Handle DAPR Job trigger callback for scheduled pull ingestion.

    This endpoint is called by DAPR Jobs at the configured schedule.
    It triggers data fetching from the configured external API and
    processes the response through the ingestion pipeline.

    Args:
        source_id: Source configuration identifier from job callback.
        request: FastAPI request object.

    Returns:
        JobTriggerResponse with fetch results summary.

    Raises:
        HTTPException: 503 if services not initialized.
        HTTPException: 500 on processing error.
    """
    logger.info("DAPR Job trigger received", source_id=source_id)

    # Get pull job handler from app state
    pull_job_handler: PullJobHandler | None = getattr(request.app.state, "pull_job_handler", None)

    if pull_job_handler is None:
        logger.error("PullJobHandler not initialized in app state")
        raise HTTPException(
            status_code=503,
            detail="Pull job handler not available",
        )

    try:
        result = await pull_job_handler.handle_job_trigger(source_id=source_id)

        logger.info(
            "Job trigger completed",
            source_id=source_id,
            success=result["success"],
            fetched=result.get("fetched", 0),
            failed=result.get("failed", 0),
        )

        return JobTriggerResponse(**result)

    except Exception as e:
        logger.exception(
            "Job trigger failed",
            source_id=source_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Job trigger failed: {e}",
        ) from e
