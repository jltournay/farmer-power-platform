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
_main_event_loop: asyncio.AbstractEventLoop | None = None


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


def set_main_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Set the main event loop for async operations (called during service startup).

    CRITICAL: The DAPR streaming handlers run in a separate thread, but Motor
    (MongoDB async driver) and other async clients are bound to the main event loop.
    We must schedule async operations on the main loop, not create new loops.
    """
    global _main_event_loop
    _main_event_loop = loop
    logger.info("Main event loop set for streaming subscriptions")


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

        # Check main event loop initialization
        if _main_event_loop is None:
            logger.error("Main event loop not initialized - will retry")
            span.set_attribute("error", "event_loop_not_initialized")
            event_processing_counter.add(1, {"topic": "quality_result", "status": "retry"})
            return TopicEventResponse("retry")

        # Process the event on the MAIN event loop
        # CRITICAL: DAPR handlers run in a separate thread, but Motor (MongoDB)
        # and other async clients are bound to the main event loop. We MUST use
        # run_coroutine_threadsafe() to schedule on the main loop.
        try:
            future = asyncio.run_coroutine_threadsafe(
                _quality_event_processor.process(
                    document_id=event_data.document_id,
                    farmer_id=event_data.farmer_id,
                ),
                _main_event_loop,
            )
            future.result(timeout=30)  # 30 second timeout

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
            # Story 0.6.10: Check for QualityEventProcessingError (linkage validation failures)
            # These errors should RETRY so they go to DLQ after max retries (ADR-006)
            from plantation_model.domain.services.quality_event_processor import (
                QualityEventProcessingError,
            )

            if isinstance(e, QualityEventProcessingError):
                # Linkage validation failure - return retry to trigger DLQ flow
                logger.warning(
                    "Linkage validation failed - will retry then DLQ",
                    error_type=e.error_type,
                    field=e.field_name,
                    value=e.field_value,
                    document_id=e.document_id,
                )
                span.set_attribute("error", str(e))
                span.set_attribute("error_type", e.error_type)
                if e.field_name:
                    span.set_attribute("error_field", e.field_name)
                event_processing_counter.add(1, {"topic": "quality_result", "status": "retry"})
                return TopicEventResponse("retry")

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

        # Check main event loop initialization
        if _main_event_loop is None:
            logger.error("Main event loop not initialized - will retry")
            span.set_attribute("error", "event_loop_not_initialized")
            event_processing_counter.add(1, {"topic": "weather_updated", "status": "retry"})
            return TopicEventResponse("retry")

        # Upsert weather observation on the MAIN event loop
        try:
            from plantation_model.domain.models import WeatherObservation

            observation = WeatherObservation(
                temp_min=event_data.observations.temp_min,
                temp_max=event_data.observations.temp_max,
                precipitation_mm=event_data.observations.precipitation_mm,
                humidity_avg=event_data.observations.humidity_avg,
            )

            # Run async operation on the MAIN event loop
            # CRITICAL: Motor is bound to the main loop, so we must use
            # run_coroutine_threadsafe() to schedule on that loop.
            future = asyncio.run_coroutine_threadsafe(
                _regional_weather_repo.upsert_observation(
                    region_id=event_data.region_id,
                    observation_date=observation_date,
                    observation=observation,
                    source=event_data.source,
                ),
                _main_event_loop,
            )
            future.result(timeout=30)

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
