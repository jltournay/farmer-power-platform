"""DAPR streaming subscription handler for cost events.

Story 13.5: DAPR Cost Event Subscription

Receives cost events from all services via pub/sub and persists them to MongoDB.
Alerting is handled via OTEL metrics (BudgetMonitor), NOT via pub/sub events.

Key Pattern (per ADR-010/ADR-011):
- Handlers receive message via `subscribe_with_handler()`
- `message.data()` returns dict directly (NOT JSON string)
- Return `TopicEventResponse("success"|"retry"|"drop")`
- Use `asyncio.run_coroutine_threadsafe()` for async operations on main event loop

Event Flow:
1. Parse `message.data()` (handles dict, str, bytes formats)
2. Validate as `CostRecordedEvent` using Pydantic
3. Generate UUID for event ID
4. Convert to `UnifiedCostEvent.from_event()`
5. Insert via `UnifiedCostRepository.insert()`
6. Record cost via `BudgetMonitor.record_cost()`
7. Return appropriate `TopicEventResponse`

Error Handling Strategy:
- ValidationError → "drop" (malformed event, won't fix on retry)
- Repository insert error → "retry" (transient DB issue)
- Budget monitor error → "retry" (transient, should succeed on retry)
- Parse error → "drop" (malformed payload)
- Services not initialized → "retry" (startup timing, will resolve)
"""

import asyncio
import json
import time
import uuid
from typing import TYPE_CHECKING, Any

import structlog
from dapr.clients import DaprClient
from dapr.clients.grpc._response import TopicEventResponse
from fp_common.events.cost_recorded import CostRecordedEvent
from opentelemetry import metrics, trace
from pydantic import ValidationError

from platform_cost.domain.cost_event import UnifiedCostEvent

if TYPE_CHECKING:
    from platform_cost.infrastructure.repositories.cost_repository import (
        UnifiedCostRepository,
    )
    from platform_cost.services.budget_monitor import BudgetMonitor

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter("platform_cost.cost_event_handler")

# Metrics for event processing
event_processing_counter = meter.create_counter(
    name="platform_cost_event_processing_total",
    description="Total cost events processed by subscription handler",
    unit="1",
)


# =============================================================================
# Module-level service references (set during startup)
# =============================================================================

_cost_repository: "UnifiedCostRepository | None" = None
_budget_monitor: "BudgetMonitor | None" = None
_main_event_loop: asyncio.AbstractEventLoop | None = None


def set_handler_dependencies(
    cost_repository: "UnifiedCostRepository",
    budget_monitor: "BudgetMonitor",
) -> None:
    """Set the cost handler dependencies (called during service startup).

    Args:
        cost_repository: Repository for persisting cost events.
        budget_monitor: Monitor for budget threshold tracking.
    """
    global _cost_repository, _budget_monitor
    _cost_repository = cost_repository
    _budget_monitor = budget_monitor
    logger.info("Cost event handler dependencies set")


def set_main_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Set the main event loop for async operations (called during service startup).

    CRITICAL: The DAPR streaming handlers run in a separate thread, but Motor
    (MongoDB async driver) and other async clients are bound to the main event loop.
    We must schedule async operations on the main loop, not create new loops.
    """
    global _main_event_loop
    _main_event_loop = loop
    logger.info("Main event loop set for cost event handler")


# =============================================================================
# Async Processing Logic
# =============================================================================


async def _process_cost_event_async(event: CostRecordedEvent) -> str:
    """Process a cost event asynchronously.

    This function contains the actual cost event processing logic:
    1. Generate UUID for event ID
    2. Convert to UnifiedCostEvent
    3. Insert via repository
    4. Update budget monitor

    Args:
        event: The validated CostRecordedEvent from DAPR pub/sub.

    Returns:
        The event ID of the persisted event.

    Raises:
        ConnectionError: On transient database errors.
        ValueError: On validation/processing errors.
    """
    if _cost_repository is None or _budget_monitor is None:
        raise ConnectionError("Cost event handler services not initialized")

    # Generate UUID for event ID
    event_id = str(uuid.uuid4())

    # Convert to storage model
    unified_event = UnifiedCostEvent.from_event(event_id, event)

    logger.debug(
        "Processing cost event",
        event_id=event_id,
        cost_type=unified_event.cost_type,
        amount_usd=str(unified_event.amount_usd),
        source_service=unified_event.source_service,
    )

    # Insert into MongoDB
    await _cost_repository.insert(unified_event)

    # Update budget monitor (synchronous operation)
    _budget_monitor.record_cost(
        cost_type=unified_event.cost_type,
        amount_usd=unified_event.amount_usd,
        timestamp=unified_event.timestamp,
    )

    logger.info(
        "Cost event processed successfully",
        event_id=event_id,
        cost_type=unified_event.cost_type,
        amount_usd=str(unified_event.amount_usd),
    )

    return event_id


# =============================================================================
# Event Handler
# =============================================================================


def handle_cost_event(message: Any) -> TopicEventResponse:
    """Handle cost events via DAPR streaming subscription.

    CRITICAL:
    - message.data() returns a dict, NOT a JSON string (usually)
    - Must return TopicEventResponse, not None
    - Runs in DAPR subscription thread, NOT main thread

    Args:
        message: DAPR subscription message.

    Returns:
        TopicEventResponse indicating success, retry, or drop.
    """
    with tracer.start_as_current_span("handle_cost_event") as span:
        # Extract message data - handle dict, string, and bytes formats
        try:
            raw_data = message.data()
            if isinstance(raw_data, str):
                data = json.loads(raw_data)
            elif isinstance(raw_data, bytes):
                data = json.loads(raw_data.decode("utf-8"))
            else:
                data = raw_data

        except Exception as e:
            logger.error("Failed to parse message data", error=str(e))
            span.set_attribute("error", "parse_failed")
            event_processing_counter.add(1, {"topic": "platform.cost.recorded", "status": "drop"})
            return TopicEventResponse("drop")

        # Check service initialization
        if _cost_repository is None or _budget_monitor is None:
            logger.error("Cost event handler services not initialized - will retry")
            span.set_attribute("error", "services_not_initialized")
            event_processing_counter.add(1, {"topic": "platform.cost.recorded", "status": "retry"})
            return TopicEventResponse("retry")

        # Check main event loop initialization
        if _main_event_loop is None:
            logger.error("Main event loop not initialized - will retry")
            span.set_attribute("error", "event_loop_not_initialized")
            event_processing_counter.add(1, {"topic": "platform.cost.recorded", "status": "retry"})
            return TopicEventResponse("retry")

        # Validate event payload
        try:
            event = CostRecordedEvent.model_validate(data)
            span.set_attribute("event.cost_type", event.cost_type)
            span.set_attribute("event.source_service", event.source_service)
            span.set_attribute("event.amount_usd", str(event.amount_usd))

        except ValidationError as e:
            logger.error(
                "Invalid cost event payload - dropping to DLQ",
                error=str(e),
                data=data,
            )
            span.set_attribute("error", "validation_failed")
            event_processing_counter.add(1, {"topic": "platform.cost.recorded", "status": "drop"})
            return TopicEventResponse("drop")

        # Process event on MAIN event loop using run_coroutine_threadsafe
        try:
            future = asyncio.run_coroutine_threadsafe(
                _process_cost_event_async(event),
                _main_event_loop,
            )
            event_id = future.result(timeout=30)  # 30 second timeout

            logger.info(
                "Cost event handled successfully",
                event_id=event_id,
                cost_type=event.cost_type,
            )
            span.set_attribute("processing.success", True)
            span.set_attribute("event.id", event_id)
            event_processing_counter.add(1, {"topic": "platform.cost.recorded", "status": "success"})
            return TopicEventResponse("success")

        except ConnectionError as e:
            # Transient database error - retry
            logger.warning(
                "Transient error processing cost event, will retry",
                error=str(e),
            )
            span.set_attribute("error", str(e))
            event_processing_counter.add(1, {"topic": "platform.cost.recorded", "status": "retry"})
            return TopicEventResponse("retry")

        except TimeoutError as e:
            # Timeout - retry
            logger.warning(
                "Timeout processing cost event, will retry",
                error=str(e),
            )
            span.set_attribute("error", "timeout")
            event_processing_counter.add(1, {"topic": "platform.cost.recorded", "status": "retry"})
            return TopicEventResponse("retry")

        except Exception as e:
            # Unknown error - check if permanent or transient
            error_str = str(e).lower()
            if any(term in error_str for term in ["validation", "invalid", "malformed"]):
                logger.error(
                    "Permanent error processing cost event - sending to DLQ",
                    error=str(e),
                )
                span.set_attribute("error", str(e))
                event_processing_counter.add(1, {"topic": "platform.cost.recorded", "status": "drop"})
                return TopicEventResponse("drop")

            # Assume transient - retry
            logger.exception("Unexpected error processing cost event")
            span.set_attribute("error", str(e))
            event_processing_counter.add(1, {"topic": "platform.cost.recorded", "status": "retry"})
            return TopicEventResponse("retry")


# =============================================================================
# Subscription Startup (ADR-010 Pattern)
# =============================================================================


def run_cost_subscription() -> None:
    """Run the cost event subscription in a background thread.

    This function matches the PoC pattern from ADR-010:
    - DaprClient created and kept alive in this function
    - Subscription established
    - Infinite loop keeps client alive until shutdown

    Called from a daemon thread in main.py.
    """
    from platform_cost.config import settings

    logger.info("Starting DAPR cost event subscription...")

    # Wait for DAPR sidecar to be ready (configurable via settings)
    time.sleep(settings.dapr_sidecar_wait_seconds)

    close_fn = None

    try:
        # Create client - must stay alive for subscription to work
        client = DaprClient()

        # Subscribe to cost events with DLQ
        close_fn = client.subscribe_with_handler(
            pubsub_name=settings.dapr_pubsub_name,
            topic=settings.cost_event_topic,
            handler_fn=handle_cost_event,
            dead_letter_topic="events.dlq",
        )

        logger.info(
            "Cost event subscription established",
            pubsub=settings.dapr_pubsub_name,
            topic=settings.cost_event_topic,
            dlq="events.dlq",
        )

        # Keep subscription alive - client must not be garbage collected
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Cost subscription loop interrupted")
    except Exception as e:
        logger.exception("Cost subscription error", error=str(e))
    finally:
        # Clean up subscription
        if close_fn is not None:
            try:
                close_fn()
            except Exception as e:
                logger.warning("Error closing cost subscription", error=str(e))
        logger.info("Cost event subscription closed")
