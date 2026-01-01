"""Dead Letter Queue Handler for DAPR streaming subscriptions.

Story 0.6.8: Dead Letter Queue Handler (ADR-006)

This module provides:
- DLQHandler class for processing dead-lettered events
- handle_dead_letter() function for DAPR streaming subscription
- start_dlq_subscription() for initiating DLQ subscription during startup

Key Pattern:
- Handler receives message via `subscribe_with_handler()`
- `message.data()` returns dict directly (NOT JSON string)
- Returns `TopicEventResponse("success"|"retry"|"drop")`

CRITICAL: Event Loop Handling
- DAPR streaming handlers run in a separate thread
- Motor (MongoDB async driver) is bound to the main event loop
- Use `asyncio.run_coroutine_threadsafe()` to schedule on main loop
"""

import asyncio
import json
import time
from typing import TYPE_CHECKING

import structlog
from dapr.clients import DaprClient
from dapr.clients.grpc._response import TopicEventResponse
from opentelemetry import metrics, trace

if TYPE_CHECKING:
    from fp_common.events.dlq_repository import DLQRepository

logger = structlog.get_logger("fp_common.events.dlq")
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter("fp-common")

# OpenTelemetry counter for DLQ events (for alerting)
dlq_counter = meter.create_counter(
    name="event_dead_letter_total",
    description="Total events sent to dead letter queue",
    unit="1",
)


# =============================================================================
# Module-level state (set during startup)
# =============================================================================

_dlq_repository: "DLQRepository | None" = None
_main_event_loop: asyncio.AbstractEventLoop | None = None


def set_dlq_repository(repository: "DLQRepository") -> None:
    """Set the DLQ repository (called during service startup).

    Args:
        repository: DLQRepository instance for storing failed events.
    """
    global _dlq_repository
    _dlq_repository = repository
    logger.info("DLQ repository set for streaming subscriptions")


def set_dlq_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Set the main event loop for async operations (called during service startup).

    CRITICAL: The DAPR streaming handlers run in a separate thread, but Motor
    (MongoDB async driver) and other async clients are bound to the main event loop.
    We must schedule async operations on the main loop, not create new loops.

    Args:
        loop: The main asyncio event loop.
    """
    global _main_event_loop
    _main_event_loop = loop
    logger.info("Main event loop set for DLQ subscriptions")


# =============================================================================
# DLQ Handler Class (for dependency injection in tests)
# =============================================================================


class DLQHandler:
    """Dead Letter Queue handler with dependency injection.

    This class provides the DLQ handling logic and can be instantiated
    with explicit dependencies for easier testing.

    Usage:
        handler = DLQHandler(
            repository=dlq_repository,
            event_loop=asyncio.get_event_loop(),
        )
        response = handler.handle(message)
    """

    def __init__(
        self,
        repository: "DLQRepository",
        event_loop: asyncio.AbstractEventLoop,
    ):
        """Initialize the DLQ handler.

        Args:
            repository: DLQRepository for storing failed events.
            event_loop: Main event loop for async operations.
        """
        self._repository = repository
        self._event_loop = event_loop

    def handle(self, message) -> TopicEventResponse:
        """Handle a dead-lettered event.

        Args:
            message: DAPR subscription message.

        Returns:
            TopicEventResponse indicating success.
        """
        with tracer.start_as_current_span("handle_dead_letter") as span:
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

            except Exception as e:
                logger.error("Failed to parse DLQ message data", error=str(e))
                span.set_attribute("error", "parse_failed")
                # Still try to store what we can
                data = {"raw_error": str(e), "raw_type": str(type(raw_data))}

            # Extract original topic from message
            # Note: The exact API depends on DAPR SDK version
            try:
                original_topic = message.topic() if callable(getattr(message, "topic", None)) else "unknown"
            except Exception:
                original_topic = "unknown"

            span.set_attribute("dlq.original_topic", original_topic)

            # Increment counter for alerting
            dlq_counter.add(1, {"topic": original_topic})

            # Store in MongoDB via async repository on main event loop
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self._repository.store_failed_event(
                        event_data=data,
                        original_topic=original_topic,
                    ),
                    self._event_loop,
                )
                doc_id = future.result(timeout=30)

                logger.error(
                    "Event dead-lettered and stored",
                    topic=original_topic,
                    document_id=doc_id,
                    event_keys=list(data.keys()) if isinstance(data, dict) else None,
                )
                span.set_attribute("dlq.document_id", doc_id)
                span.set_attribute("processing.success", True)

            except Exception as e:
                # If we can't store, log but still return success
                # (we don't want to retry DLQ processing forever)
                logger.exception(
                    "Failed to store dead-lettered event in MongoDB",
                    error=str(e),
                    topic=original_topic,
                )
                span.set_attribute("error", f"storage_failed: {e}")

            return TopicEventResponse("success")


# =============================================================================
# Module-level handler function (for DAPR subscription)
# =============================================================================


def handle_dead_letter(message) -> TopicEventResponse:
    """Handle dead-lettered events via DAPR streaming subscription.

    This function is the handler passed to `subscribe_with_handler()`.

    CRITICAL:
    - message.data() returns a dict, NOT a JSON string
    - Must return TopicEventResponse, not None
    - Runs in DAPR subscription thread, NOT main thread

    Args:
        message: DAPR subscription message.

    Returns:
        TopicEventResponse indicating success.
    """
    # Check initialization
    if _dlq_repository is None:
        logger.error("DLQ repository not initialized - will retry")
        dlq_counter.add(1, {"topic": "unknown", "error": "not_initialized"})
        return TopicEventResponse("retry")

    if _main_event_loop is None:
        logger.error("Main event loop not initialized - will retry")
        dlq_counter.add(1, {"topic": "unknown", "error": "loop_not_initialized"})
        return TopicEventResponse("retry")

    # Use the handler class for actual processing
    handler = DLQHandler(
        repository=_dlq_repository,
        event_loop=_main_event_loop,
    )
    return handler.handle(message)


# =============================================================================
# Subscription Startup (ADR-010 Pattern)
# =============================================================================


def start_dlq_subscription(
    dapr_sidecar_wait_seconds: int = 5,
) -> None:
    """Start DLQ subscription in a background thread.

    This function matches the PoC pattern from ADR-010:
    - DaprClient created and kept alive in this function
    - Subscription established
    - Infinite loop keeps client alive until shutdown

    Called from a daemon thread during service startup.

    Args:
        dapr_sidecar_wait_seconds: Seconds to wait for DAPR sidecar to be ready.
    """
    logger.info("Starting DLQ subscription...")

    # Wait for DAPR sidecar to be ready
    time.sleep(dapr_sidecar_wait_seconds)

    close_fn = None

    try:
        # Create client - must stay alive for subscriptions to work
        client = DaprClient()

        # Subscribe to DLQ topic
        # IMPORTANT: DLQ handler has NO dead_letter_topic (no DLQ for DLQ)
        close_fn = client.subscribe_with_handler(
            pubsub_name="pubsub",
            topic="events.dlq",
            handler_fn=handle_dead_letter,
            # No dead_letter_topic - DLQ handler must not fail permanently
        )

        logger.info(
            "DLQ subscription established",
            topic="events.dlq",
            pubsub="pubsub",
        )

        # Keep subscription alive - client must not be garbage collected
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("DLQ subscription loop interrupted")
    except Exception as e:
        logger.exception("DLQ subscription error", error=str(e))
    finally:
        # Clean up subscription
        if close_fn:
            try:
                close_fn()
            except Exception as e:
                logger.warning("Error closing DLQ subscription", error=str(e))
        logger.info("DLQ subscription closed")
