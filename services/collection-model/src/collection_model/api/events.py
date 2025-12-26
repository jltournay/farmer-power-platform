"""Azure Event Grid webhook handler for blob-created events.

This module handles incoming Event Grid events when blobs are created
in Azure Blob Storage containers (qc-analyzer-results, qc-analyzer-exceptions).
"""

from typing import Any

import structlog
from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/events", tags=["events"])


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

    # Process blob-created events
    processed_count = 0
    for event in body:
        if event.get("eventType") == "Microsoft.Storage.BlobCreated":
            _log_blob_created_event(event)
            processed_count += 1

    logger.info(
        "Processed Event Grid batch",
        total_events=len(body),
        blob_created_events=processed_count,
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
            validation_code=validation_code[:8] + "...",  # Log partial code for security
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


def _log_blob_created_event(event: dict[str, Any]) -> None:
    """Log a blob-created event for later processing.

    In Story 2.1, we only log the events. Actual processing
    (downloading, parsing, storing) is implemented in Story 2.3.

    Args:
        event: The blob-created event from Event Grid.

    """
    subject = event.get("subject", "")
    data = event.get("data", {})

    # Extract container and blob path from subject
    # Subject format: /blobServices/default/containers/{container}/blobs/{blob_path}
    parts = subject.split("/containers/")
    container = ""
    blob_path = ""
    if len(parts) > 1:
        container_and_blob = parts[1]
        if "/blobs/" in container_and_blob:
            container, blob_path = container_and_blob.split("/blobs/", 1)

    logger.info(
        "Blob created event received",
        event_id=event.get("id"),
        event_time=event.get("eventTime"),
        container=container,
        blob_path=blob_path,
        content_type=data.get("contentType", ""),
        content_length=data.get("contentLength", 0),
        blob_url=data.get("url", ""),
        # TODO: Queue for processing in Story 2.3
    )
