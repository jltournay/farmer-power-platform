"""DAPR streaming subscription handlers for AI Model.

Story 0.75.8: Event Flow, Subscriber, and Publisher (AC: #1, #4, #10)
Story 0.75.16b: Wired to AgentExecutor for actual workflow execution

This module implements DAPR SDK streaming subscriptions per ADR-010/ADR-011.
Key Pattern:
- Handlers receive message via `subscribe_with_handler()`
- `message.data()` returns dict directly (NOT JSON string)
- Return `TopicEventResponse("success"|"retry"|"drop")`
- DLQ configured via `dead_letter_topic` parameter in code

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
from ai_model.config import settings
from dapr.clients import DaprClient
from dapr.clients.grpc._response import TopicEventResponse
from fp_common.events import AgentRequestEvent
from opentelemetry import metrics, trace
from pydantic import ValidationError

if TYPE_CHECKING:
    from ai_model.services import AgentConfigCache, AgentExecutor

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter("ai-model")

# =============================================================================
# OpenTelemetry Metrics (AC: #9)
# =============================================================================

event_processing_counter = meter.create_counter(
    name="ai_event_processing_total",
    description="Total events processed by AI Model",
    unit="1",
)

processing_failures_counter = meter.create_counter(
    name="ai_event_processing_failures_total",
    description="Total events that failed processing",
    unit="1",
)

dlq_counter = meter.create_counter(
    name="ai_event_dead_letter_total",
    description="Total events sent to dead letter queue",
    unit="1",
)


# =============================================================================
# Module-level service references (set during startup)
# =============================================================================

_agent_config_cache: "AgentConfigCache | None" = None
_agent_executor: "AgentExecutor | None" = None
_main_event_loop: asyncio.AbstractEventLoop | None = None


def set_agent_config_cache(cache: "AgentConfigCache") -> None:
    """Set the agent config cache (called during service startup)."""
    global _agent_config_cache
    _agent_config_cache = cache
    logger.info("Agent config cache set for streaming subscriptions")


def set_agent_executor(executor: "AgentExecutor") -> None:
    """Set the agent executor (called during service startup).

    Story 0.75.16b: Wire subscriber to AgentExecutor.
    """
    global _agent_executor
    _agent_executor = executor
    logger.info("Agent executor set for streaming subscriptions")


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
# CloudEvent Payload Extraction
# =============================================================================


def extract_payload(raw_data) -> dict:
    """Extract payload from raw message data.

    Handles both CloudEvent wrapped and direct payloads.

    Args:
        raw_data: Raw data from message.data()

    Returns:
        Extracted payload dict
    """
    # Handle string/bytes format for safety
    if isinstance(raw_data, str):
        data = json.loads(raw_data)
    elif isinstance(raw_data, bytes):
        data = json.loads(raw_data.decode("utf-8"))
    else:
        data = raw_data

    # Extract from CloudEvent wrapper if present
    if "data" in data and isinstance(data.get("data"), dict):
        return data["data"].get("payload", data["data"])
    elif "payload" in data:
        return data["payload"]
    return data


# =============================================================================
# Agent Execution (Story 0.75.16b - wired to AgentExecutor)
# =============================================================================


async def execute_agent(event: AgentRequestEvent) -> None:
    """Execute agent workflow via AgentExecutor.

    Story 0.75.16b: Replaced placeholder with actual AgentExecutor call.

    Args:
        event: The validated agent request event.

    Raises:
        RuntimeError: If AgentExecutor is not initialized.
    """
    if _agent_executor is None:
        raise RuntimeError("AgentExecutor not initialized - call set_agent_executor() first")

    logger.info(
        "Executing agent workflow",
        request_id=event.request_id,
        agent_id=event.agent_id,
        source=event.source,
    )

    # Execute and publish result (AgentExecutor handles publishing)
    await _agent_executor.execute_and_publish(event)


# =============================================================================
# Event Handlers
# =============================================================================


def handle_agent_request(message) -> TopicEventResponse:
    """Handle agent request events from domain models.

    CRITICAL:
    - message.data() returns a dict, NOT a JSON string
    - Must return TopicEventResponse, not None
    - Handler runs in separate thread - use run_coroutine_threadsafe()

    Args:
        message: DAPR subscription message.

    Returns:
        TopicEventResponse indicating success, retry, or drop.
    """
    with tracer.start_as_current_span("handle_agent_request") as span:
        # Extract message data
        try:
            raw_data = message.data()
            payload = extract_payload(raw_data)

        except Exception as e:
            logger.error("Failed to parse message data", error=str(e))
            span.set_attribute("error", "parse_failed")
            event_processing_counter.add(1, {"topic": "agent_request", "status": "drop"})
            dlq_counter.add(1, {"topic": "agent_request"})
            return TopicEventResponse("drop")

        # Validate payload
        try:
            event_data = AgentRequestEvent.model_validate(payload)
            span.set_attribute("event.request_id", event_data.request_id)
            span.set_attribute("event.agent_id", event_data.agent_id)
            span.set_attribute("event.source", event_data.source)

            logger.info(
                "Processing agent request event",
                request_id=event_data.request_id,
                agent_id=event_data.agent_id,
                source=event_data.source,
            )

        except ValidationError as e:
            logger.error("Invalid event payload", error=str(e), payload=payload)
            span.set_attribute("error", "validation_failed")
            event_processing_counter.add(1, {"topic": "agent_request", "status": "drop"})
            processing_failures_counter.add(1, {"topic": "agent_request", "error_type": "validation"})
            dlq_counter.add(1, {"topic": "agent_request"})
            return TopicEventResponse("drop")

        # Check agent config cache initialization
        if _agent_config_cache is None:
            logger.error("Agent config cache not initialized - will retry")
            span.set_attribute("error", "cache_not_initialized")
            event_processing_counter.add(1, {"topic": "agent_request", "status": "retry"})
            return TopicEventResponse("retry")

        # Check main event loop initialization
        if _main_event_loop is None:
            logger.error("Main event loop not initialized - will retry")
            span.set_attribute("error", "event_loop_not_initialized")
            event_processing_counter.add(1, {"topic": "agent_request", "status": "retry"})
            return TopicEventResponse("retry")

        # Check agent executor initialization (Story 0.75.16b)
        if _agent_executor is None:
            logger.error("Agent executor not initialized - will retry")
            span.set_attribute("error", "executor_not_initialized")
            event_processing_counter.add(1, {"topic": "agent_request", "status": "retry"})
            return TopicEventResponse("retry")

        # Verify agent_id exists in cache
        try:
            future = asyncio.run_coroutine_threadsafe(
                _agent_config_cache.get(event_data.agent_id),
                _main_event_loop,
            )
            agent_config = future.result(timeout=settings.event_handler_config_timeout_s)

            if agent_config is None:
                logger.warning(
                    "Unknown agent_id - dropping event",
                    agent_id=event_data.agent_id,
                    request_id=event_data.request_id,
                )
                span.set_attribute("error", "agent_not_found")
                event_processing_counter.add(1, {"topic": "agent_request", "status": "drop"})
                processing_failures_counter.add(1, {"topic": "agent_request", "error_type": "config_not_found"})
                dlq_counter.add(1, {"topic": "agent_request"})
                return TopicEventResponse("drop")

        except TimeoutError:
            logger.warning("Timeout checking agent config - will retry")
            span.set_attribute("error", "cache_timeout")
            event_processing_counter.add(1, {"topic": "agent_request", "status": "retry"})
            return TopicEventResponse("retry")

        except Exception as e:
            logger.warning("Error checking agent config - will retry", error=str(e))
            span.set_attribute("error", str(e))
            event_processing_counter.add(1, {"topic": "agent_request", "status": "retry"})
            return TopicEventResponse("retry")

        # Execute agent workflow (Story 0.75.16b - wired to AgentExecutor)
        try:
            future = asyncio.run_coroutine_threadsafe(
                execute_agent(event_data),
                _main_event_loop,
            )
            future.result(timeout=settings.event_handler_execution_timeout_s)

            logger.info(
                "Agent request processed successfully",
                request_id=event_data.request_id,
                agent_id=event_data.agent_id,
            )
            span.set_attribute("processing.success", True)
            event_processing_counter.add(1, {"topic": "agent_request", "status": "success"})
            return TopicEventResponse("success")

        except (ConnectionError, TimeoutError) as e:
            # Transient errors - retry
            logger.warning(
                "Transient error processing agent request, will retry",
                error=str(e),
                request_id=event_data.request_id,
            )
            span.set_attribute("error", str(e))
            event_processing_counter.add(1, {"topic": "agent_request", "status": "retry"})
            return TopicEventResponse("retry")

        except Exception as e:
            # Unknown error - retry (might be transient)
            logger.exception(
                "Unexpected error processing agent request",
                request_id=event_data.request_id,
            )
            span.set_attribute("error", str(e))
            event_processing_counter.add(1, {"topic": "agent_request", "status": "retry"})
            processing_failures_counter.add(1, {"topic": "agent_request", "error_type": "unknown"})
            return TopicEventResponse("retry")


# =============================================================================
# Subscription Startup (ADR-010 Pattern)
# =============================================================================

# Module-level flag for signaling subscription readiness
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

    logger.info("Starting DAPR streaming subscriptions for AI Model...")

    # Wait for DAPR sidecar to be ready
    time.sleep(5)

    close_fns: list = []

    try:
        # Create client - must stay alive for subscriptions to work
        client = DaprClient()

        # Subscribe to agent requests with DLQ
        # NOTE: Using specific topic, not wildcard (DAPR doesn't support wildcards)
        agent_close = client.subscribe_with_handler(
            pubsub_name="pubsub",
            topic="ai.agent.requested",
            handler_fn=handle_agent_request,
            dead_letter_topic="events.dlq",
        )
        close_fns.append(agent_close)
        logger.info(
            "Subscription established",
            topic="ai.agent.requested",
            dlq="events.dlq",
        )

        subscription_ready = True
        logger.info(
            "All AI Model subscriptions started - keeping alive",
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
        logger.info("All AI Model subscriptions closed")
