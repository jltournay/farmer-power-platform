"""DAPR subscription handler for Collection Model quality result events.

This module handles `collection.quality_result.received` events emitted by
the Collection Model when a QC Analyzer result is processed.

Event Flow:
1. Collection Model processes QC result blob
2. Collection Model emits `collection.quality_result.received` event
3. DAPR routes to this handler via Pub/Sub subscription
4. Handler retrieves full document from Collection MCP
5. Handler updates FarmerPerformance metrics
6. Handler emits `plantation.quality.graded` event for downstream consumers
7. Handler emits `plantation.performance_updated` event for Engagement Model
"""

from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Request, Response
from opentelemetry import trace
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)

router = APIRouter(prefix="/api/v1/events", tags=["events"])


class QualityResultEvent(BaseModel):
    """Event payload for collection.quality_result.received.

    This matches the payload defined in source config's payload_fields:
    - document_id: The stored document ID in Collection Model
    - farmer_id: The farmer ID from the quality document
    """

    document_id: str = Field(description="Collection Model document ID")
    farmer_id: str = Field(description="Farmer ID from quality document")


class CloudEventWrapper(BaseModel):
    """DAPR CloudEvents 1.0 wrapper.

    DAPR delivers Pub/Sub messages as CloudEvents.
    See: https://docs.dapr.io/developing-applications/building-blocks/pubsub/howto-publish-subscribe/
    """

    id: str = Field(description="Event ID")
    source: str = Field(description="Event source")
    type: str = Field(description="Event type")
    specversion: str = Field(default="1.0", description="CloudEvents version")
    datacontenttype: str = Field(default="application/json", description="Content type")
    data: dict[str, Any] = Field(description="Event payload")
    time: datetime | None = Field(default=None, description="Event timestamp")
    traceparent: str | None = Field(default=None, description="W3C trace context")


class DaprSubscriptionResponse(BaseModel):
    """DAPR Pub/Sub subscription status response."""

    success: bool
    message: str | None = None


@router.get("/subscriptions")
async def get_subscriptions() -> list[dict[str, Any]]:
    """Return DAPR Pub/Sub subscriptions for this service.

    DAPR calls this endpoint at startup to discover subscriptions.
    See: https://docs.dapr.io/developing-applications/building-blocks/pubsub/subscription-methods/

    Returns:
        List of subscription configurations.
    """
    return [
        {
            "pubsubname": "pubsub",
            "topic": "collection.quality_result.received",
            "route": "/api/v1/events/quality-result",
            "metadata": {
                "rawPayload": "true",  # Receive CloudEvents format
            },
        }
    ]


@router.post("/quality-result")
async def handle_quality_result(request: Request) -> Response:
    """Handle quality result events from Collection Model.

    This endpoint is called by DAPR when a `collection.quality_result.received`
    event is published. The handler:

    1. Parses the CloudEvent payload
    2. Retrieves the full document from Collection MCP (Task 3)
    3. Loads the GradingModel for grade label lookup (Task 2)
    4. Updates FarmerPerformance metrics (Task 4)
    5. Emits `plantation.quality.graded` event (Task 5)
    6. Emits `plantation.performance_updated` event (Task 5c)

    Args:
        request: FastAPI request with CloudEvent payload.

    Returns:
        Response with DAPR acknowledgment status:
        - 200 SUCCESS: Event processed successfully
        - 400 DROP: Invalid event, don't retry
        - 500 RETRY: Temporary failure, retry later
    """
    with tracer.start_as_current_span("handle_quality_result") as span:
        try:
            body = await request.json()
        except Exception as e:
            logger.error("Failed to parse event body", error=str(e))
            span.set_attribute("error", "parse_failed")
            return Response(status_code=400, content='{"status": "DROP"}')

        # Parse CloudEvent wrapper
        try:
            cloud_event = CloudEventWrapper.model_validate(body)
            event_id = cloud_event.id
            trace_parent = cloud_event.traceparent

            span.set_attribute("event.id", event_id)
            span.set_attribute("event.type", cloud_event.type)
            if trace_parent:
                span.set_attribute("event.traceparent", trace_parent)

        except Exception as e:
            logger.error("Invalid CloudEvent format", error=str(e), body=body)
            span.set_attribute("error", "invalid_cloud_event")
            return Response(status_code=400, content='{"status": "DROP"}')

        # Parse event data
        try:
            event_data = QualityResultEvent.model_validate(cloud_event.data.get("payload", cloud_event.data))
            span.set_attribute("event.document_id", event_data.document_id)
            span.set_attribute("event.farmer_id", event_data.farmer_id)

            logger.info(
                "Processing quality result event",
                event_id=event_id,
                document_id=event_data.document_id,
                farmer_id=event_data.farmer_id,
            )

        except Exception as e:
            logger.error(
                "Invalid event payload",
                error=str(e),
                data=cloud_event.data,
            )
            span.set_attribute("error", "invalid_payload")
            return Response(status_code=400, content='{"status": "DROP"}')

        # Get services from app state
        quality_event_processor = getattr(request.app.state, "quality_event_processor", None)

        if quality_event_processor is None:
            logger.warning(
                "Quality event processor not initialized - event will be skipped",
                event_id=event_id,
                document_id=event_data.document_id,
            )
            # Return success to avoid infinite retries in development
            # In production, this should be a 500 RETRY
            return Response(
                status_code=200,
                content='{"status": "SUCCESS", "message": "Processor not initialized"}',
            )

        # Process the event (Tasks 2-6 will be implemented here)
        try:
            await quality_event_processor.process(
                document_id=event_data.document_id,
                farmer_id=event_data.farmer_id,
            )

            logger.info(
                "Quality result event processed successfully",
                event_id=event_id,
                document_id=event_data.document_id,
                farmer_id=event_data.farmer_id,
            )
            span.set_attribute("processing.success", True)

            return Response(status_code=200, content='{"status": "SUCCESS"}')

        except Exception as e:
            logger.exception(
                "Failed to process quality result event",
                event_id=event_id,
                document_id=event_data.document_id,
                error=str(e),
            )
            span.set_attribute("error", str(e))
            span.record_exception(e)

            # Return RETRY to let DAPR retry later
            return Response(status_code=500, content='{"status": "RETRY"}')
