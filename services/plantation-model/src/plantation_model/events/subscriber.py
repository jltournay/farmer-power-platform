"""DAPR streaming subscription handlers for Plantation Model.

Story 0.6.5: Plantation Model Streaming Subscriptions

This module implements DAPR SDK streaming subscriptions per ADR-010/ADR-011.
Replaces the FastAPI HTTP callback handlers with outbound streaming.

Key Pattern:
- Handlers receive message via `subscribe_with_handler()`
- `message.data()` returns dict directly (NOT JSON string)
- Return `TopicEventResponse("success"|"retry"|"drop")`
- DLQ configured via `dead_letter_topic` parameter in code
"""

import asyncio
import json
import time
from datetime import date, datetime
from typing import TYPE_CHECKING

import structlog
from dapr.clients import DaprClient
from dapr.clients.grpc._response import TopicEventResponse
from opentelemetry import metrics, trace
from pydantic import BaseModel, Field, ValidationError

if TYPE_CHECKING:
    from plantation_model.domain.services.quality_event_processor import (
        QualityEventProcessor,
    )
    from plantation_model.infrastructure.repositories.regional_weather_repository import (
        RegionalWeatherRepository,
    )

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter("plantation-model")

# Metrics for event processing
event_processing_counter = meter.create_counter(
    name="plantation_event_processing_total",
    description="Total events processed by Plantation Model",
    unit="1",
)


# =============================================================================
# Event Payload Models
# =============================================================================


class QualityResultEvent(BaseModel):
    """Event payload for collection.quality_result.received."""

    document_id: str = Field(description="Collection Model document ID")
    farmer_id: str = Field(description="Farmer ID from quality document")


class WeatherObservationData(BaseModel):
    """Weather observation data from Collection Model."""

    temp_min: float = Field(description="Minimum temperature in Celsius")
    temp_max: float = Field(description="Maximum temperature in Celsius")
    precipitation_mm: float = Field(ge=0, description="Total precipitation in mm")
    humidity_avg: float = Field(ge=0, le=100, description="Average humidity %")


class WeatherUpdatedEvent(BaseModel):
    """Event payload for collection.weather.updated."""

    region_id: str = Field(description="Region ID (e.g., nyeri-highland)")
    date: str = Field(description="Observation date in YYYY-MM-DD format")
    observations: WeatherObservationData = Field(description="Weather observations")
    source: str = Field(default="open-meteo", description="Weather data source")
    collected_at: datetime | None = Field(default=None, description="When data was collected")


# =============================================================================
# Module-level service references (set during startup)
# =============================================================================

_quality_event_processor: "QualityEventProcessor | None" = None
_regional_weather_repo: "RegionalWeatherRepository | None" = None


def set_quality_event_processor(processor: "QualityEventProcessor") -> None:
    """Set the quality event processor (called during service startup)."""
    global _quality_event_processor
    _quality_event_processor = processor
    logger.info("Quality event processor set for streaming subscriptions")


def set_regional_weather_repo(repo: "RegionalWeatherRepository") -> None:
    """Set the regional weather repository (called during service startup)."""
    global _regional_weather_repo
    _regional_weather_repo = repo
    logger.info("Regional weather repository set for streaming subscriptions")


# =============================================================================
# Event Handlers
# =============================================================================


def handle_quality_result(message) -> TopicEventResponse:
    """Handle quality result events from Collection Model.

    CRITICAL:
    - message.data() returns a dict, NOT a JSON string
    - Must return TopicEventResponse, not None

    Args:
        message: DAPR subscription message.

    Returns:
        TopicEventResponse indicating success, retry, or drop.
    """
    with tracer.start_as_current_span("handle_quality_result_streaming") as span:
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

            # Extract payload from CloudEvent wrapper if present
            if "data" in data and isinstance(data.get("data"), dict):
                payload = data["data"].get("payload", data["data"])
            elif "payload" in data:
                payload = data["payload"]
            else:
                payload = data

        except Exception as e:
            logger.error("Failed to parse message data", error=str(e))
            span.set_attribute("error", "parse_failed")
            event_processing_counter.add(1, {"topic": "quality_result", "status": "drop"})
            return TopicEventResponse("drop")

        # Validate payload
        try:
            event_data = QualityResultEvent.model_validate(payload)
            span.set_attribute("event.document_id", event_data.document_id)
            span.set_attribute("event.farmer_id", event_data.farmer_id)

            logger.info(
                "Processing quality result event via streaming",
                document_id=event_data.document_id,
                farmer_id=event_data.farmer_id,
            )

        except ValidationError as e:
            logger.error("Invalid event payload", error=str(e), payload=payload)
            span.set_attribute("error", "validation_failed")
            event_processing_counter.add(1, {"topic": "quality_result", "status": "drop"})
            return TopicEventResponse("drop")

        # Check processor initialization
        if _quality_event_processor is None:
            logger.error("Quality event processor not initialized - will retry")
            span.set_attribute("error", "processor_not_initialized")
            event_processing_counter.add(1, {"topic": "quality_result", "status": "retry"})
            return TopicEventResponse("retry")

        # Process the event (runs in event loop)
        try:
            # Run async processor - create new event loop for this thread
            # DAPR handlers run in a separate thread, not the main event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're in an event loop, schedule the coroutine
                future = asyncio.run_coroutine_threadsafe(
                    _quality_event_processor.process(
                        document_id=event_data.document_id,
                        farmer_id=event_data.farmer_id,
                    ),
                    loop,
                )
                future.result(timeout=30)  # 30 second timeout
            except RuntimeError:
                # No running event loop - use asyncio.run() for new loop
                asyncio.run(
                    _quality_event_processor.process(
                        document_id=event_data.document_id,
                        farmer_id=event_data.farmer_id,
                    )
                )

            logger.info(
                "Quality result event processed successfully",
                document_id=event_data.document_id,
                farmer_id=event_data.farmer_id,
            )
            span.set_attribute("processing.success", True)
            event_processing_counter.add(1, {"topic": "quality_result", "status": "success"})
            return TopicEventResponse("success")

        except (ConnectionError, TimeoutError) as e:
            # Transient errors - retry
            logger.warning(
                "Transient error processing quality event, will retry",
                error=str(e),
                document_id=event_data.document_id,
            )
            span.set_attribute("error", str(e))
            event_processing_counter.add(1, {"topic": "quality_result", "status": "retry"})
            return TopicEventResponse("retry")

        except Exception as e:
            # Check if it's a validation/data error (permanent) vs transient
            error_str = str(e).lower()
            if any(term in error_str for term in ["validation", "invalid", "not found", "missing"]):
                # Permanent error - drop to DLQ
                logger.error(
                    "Permanent error processing quality event - sending to DLQ",
                    error=str(e),
                    document_id=event_data.document_id,
                )
                span.set_attribute("error", str(e))
                event_processing_counter.add(1, {"topic": "quality_result", "status": "drop"})
                return TopicEventResponse("drop")

            # Unknown error - retry (might be transient)
            logger.exception(
                "Unexpected error processing quality event",
                document_id=event_data.document_id,
            )
            span.set_attribute("error", str(e))
            event_processing_counter.add(1, {"topic": "quality_result", "status": "retry"})
            return TopicEventResponse("retry")


def handle_weather_updated(message) -> TopicEventResponse:
    """Handle weather updated events from Collection Model.

    Args:
        message: DAPR subscription message.

    Returns:
        TopicEventResponse indicating success, retry, or drop.
    """
    with tracer.start_as_current_span("handle_weather_updated_streaming") as span:
        # Extract message data
        try:
            raw_data = message.data()
            if isinstance(raw_data, str):
                data = json.loads(raw_data)
            elif isinstance(raw_data, bytes):
                data = json.loads(raw_data.decode("utf-8"))
            else:
                data = raw_data

            # Extract payload from CloudEvent wrapper if present
            if "data" in data and isinstance(data.get("data"), dict):
                payload = data["data"].get("payload", data["data"])
            elif "payload" in data:
                payload = data["payload"]
            else:
                payload = data

        except Exception as e:
            logger.error("Failed to parse weather event data", error=str(e))
            span.set_attribute("error", "parse_failed")
            event_processing_counter.add(1, {"topic": "weather_updated", "status": "drop"})
            return TopicEventResponse("drop")

        # Validate payload
        try:
            event_data = WeatherUpdatedEvent.model_validate(payload)
            span.set_attribute("event.region_id", event_data.region_id)
            span.set_attribute("event.date", event_data.date)

            logger.info(
                "Processing weather updated event via streaming",
                region_id=event_data.region_id,
                date=event_data.date,
            )

        except ValidationError as e:
            logger.error("Invalid weather event payload", error=str(e), payload=payload)
            span.set_attribute("error", "validation_failed")
            event_processing_counter.add(1, {"topic": "weather_updated", "status": "drop"})
            return TopicEventResponse("drop")

        # Parse observation date
        try:
            observation_date = date.fromisoformat(event_data.date)
        except ValueError as e:
            logger.error("Invalid date format", error=str(e), date=event_data.date)
            span.set_attribute("error", "invalid_date")
            event_processing_counter.add(1, {"topic": "weather_updated", "status": "drop"})
            return TopicEventResponse("drop")

        # Check repository initialization
        if _regional_weather_repo is None:
            logger.error("Regional weather repository not initialized - will retry")
            span.set_attribute("error", "repo_not_initialized")
            event_processing_counter.add(1, {"topic": "weather_updated", "status": "retry"})
            return TopicEventResponse("retry")

        # Upsert weather observation
        try:
            from plantation_model.domain.models import WeatherObservation

            observation = WeatherObservation(
                temp_min=event_data.observations.temp_min,
                temp_max=event_data.observations.temp_max,
                precipitation_mm=event_data.observations.precipitation_mm,
                humidity_avg=event_data.observations.humidity_avg,
            )

            # Run async operation - create new event loop for this thread
            try:
                loop = asyncio.get_running_loop()
                future = asyncio.run_coroutine_threadsafe(
                    _regional_weather_repo.upsert_observation(
                        region_id=event_data.region_id,
                        observation_date=observation_date,
                        observation=observation,
                        source=event_data.source,
                    ),
                    loop,
                )
                future.result(timeout=30)
            except RuntimeError:
                # No running event loop - use asyncio.run() for new loop
                asyncio.run(
                    _regional_weather_repo.upsert_observation(
                        region_id=event_data.region_id,
                        observation_date=observation_date,
                        observation=observation,
                        source=event_data.source,
                    )
                )

            logger.info(
                "Weather observation upserted successfully",
                region_id=event_data.region_id,
                date=event_data.date,
            )
            span.set_attribute("processing.success", True)
            event_processing_counter.add(1, {"topic": "weather_updated", "status": "success"})
            return TopicEventResponse("success")

        except (ConnectionError, TimeoutError) as e:
            logger.warning(
                "Transient error upserting weather, will retry",
                error=str(e),
                region_id=event_data.region_id,
            )
            span.set_attribute("error", str(e))
            event_processing_counter.add(1, {"topic": "weather_updated", "status": "retry"})
            return TopicEventResponse("retry")

        except Exception as e:
            logger.exception(
                "Failed to upsert weather observation",
                region_id=event_data.region_id,
            )
            span.set_attribute("error", str(e))
            event_processing_counter.add(1, {"topic": "weather_updated", "status": "retry"})
            return TopicEventResponse("retry")


# =============================================================================
# Subscription Startup (ADR-010 Pattern)
# =============================================================================

# Module-level event for signaling subscription readiness
subscription_ready = False


def run_streaming_subscriptions() -> None:
    """Run streaming subscriptions in a background thread.

    This function matches the PoC pattern from ADR-010:
    - DaprClient created and kept alive in this function
    - Subscriptions established
    - Infinite loop keeps client alive until shutdown

    Called from a daemon thread in main.py.
    """
    global subscription_ready

    logger.info("Starting DAPR streaming subscriptions...")

    # Wait for DAPR sidecar to be ready
    time.sleep(5)

    close_fns: list = []  # list[Callable[[], None]]

    try:
        # Create client - must stay alive for subscriptions to work
        client = DaprClient()

        # Subscribe to quality results with DLQ
        quality_close = client.subscribe_with_handler(
            pubsub_name="pubsub",
            topic="collection.quality_result.received",
            handler_fn=handle_quality_result,
            dead_letter_topic="events.dlq",
        )
        close_fns.append(quality_close)
        logger.info(
            "Subscription established",
            topic="collection.quality_result.received",
            dlq="events.dlq",
        )

        # Subscribe to weather updates with DLQ
        weather_close = client.subscribe_with_handler(
            pubsub_name="pubsub",
            topic="weather.observation.updated",
            handler_fn=handle_weather_updated,
            dead_letter_topic="events.dlq",
        )
        close_fns.append(weather_close)
        logger.info(
            "Subscription established",
            topic="weather.observation.updated",
            dlq="events.dlq",
        )

        subscription_ready = True
        logger.info(
            "All subscriptions started - keeping alive",
            subscription_count=len(close_fns),
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
