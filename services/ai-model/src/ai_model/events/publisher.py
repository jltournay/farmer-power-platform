"""Event publishing utilities for AI Model.

Story 0.75.8: Event Flow, Subscriber, and Publisher (AC: #2, #5)

This module provides async event publishing via DAPR pub/sub:
- AgentCompletedEvent → `ai.agent.{agent_id}.completed`
- AgentFailedEvent → `ai.agent.{agent_id}.failed`
- CostRecordedEvent → `ai.cost.recorded`
"""

import structlog
from ai_model.events.models import (
    AgentCompletedEvent,
    AgentFailedEvent,
    CostRecordedEvent,
)
from dapr.clients import DaprClient
from opentelemetry import trace

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)


class EventPublisher:
    """Async event publisher for AI Model events.

    Publishes events to DAPR pub/sub component following the topic
    naming convention from architecture documentation:
    - ai.agent.{agent_id}.completed - Successful results
    - ai.agent.{agent_id}.failed - Failed executions
    - ai.cost.recorded - Cost tracking telemetry
    """

    def __init__(self, pubsub_name: str = "pubsub"):
        """Initialize the event publisher.

        Args:
            pubsub_name: Name of the DAPR pub/sub component.
        """
        self._pubsub_name = pubsub_name

    async def publish_agent_completed(self, event: AgentCompletedEvent) -> None:
        """Publish successful agent execution result.

        Topic: ai.agent.{agent_id}.completed

        Args:
            event: The completed event to publish.
        """
        topic = f"ai.agent.{event.agent_id}.completed"
        await self._publish(topic, event)

        logger.info(
            "Published agent completed event",
            topic=topic,
            request_id=event.request_id,
            agent_id=event.agent_id,
            result_type=event.result.result_type,
        )

    async def publish_agent_failed(self, event: AgentFailedEvent) -> None:
        """Publish failed agent execution.

        Topic: ai.agent.{agent_id}.failed

        Args:
            event: The failed event to publish.
        """
        topic = f"ai.agent.{event.agent_id}.failed"
        await self._publish(topic, event)

        logger.warning(
            "Published agent failed event",
            topic=topic,
            request_id=event.request_id,
            agent_id=event.agent_id,
            error_type=event.error_type,
        )

    async def publish_cost_recorded(self, event: CostRecordedEvent) -> None:
        """Publish LLM cost tracking event.

        Topic: ai.cost.recorded

        Args:
            event: The cost event to publish.
        """
        topic = "ai.cost.recorded"
        await self._publish(topic, event)

        logger.debug(
            "Published cost recorded event",
            topic=topic,
            request_id=event.request_id,
            agent_id=event.agent_id,
            model=event.model,
            cost_usd=str(event.cost_usd),
        )

    async def _publish(self, topic: str, event) -> None:
        """Internal method to publish an event to DAPR pub/sub.

        Args:
            topic: Topic name to publish to.
            event: Pydantic model to serialize and publish.
        """
        with tracer.start_as_current_span(f"publish_event_{topic}") as span:
            span.set_attribute("pubsub.topic", topic)
            span.set_attribute("pubsub.name", self._pubsub_name)

            try:
                # DaprClient is thread-safe and can be created per-call
                # for async context to avoid blocking
                with DaprClient() as client:
                    client.publish_event(
                        pubsub_name=self._pubsub_name,
                        topic_name=topic,
                        data=event.model_dump_json(),
                        data_content_type="application/json",
                    )

                span.set_attribute("publish.success", True)

            except Exception as e:
                span.set_attribute("publish.success", False)
                span.set_attribute("error", str(e))
                logger.exception(
                    "Failed to publish event",
                    topic=topic,
                    error=str(e),
                )
                raise
