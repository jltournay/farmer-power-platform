"""Event handling for AI Model service.

Story 0.75.8: Event Flow, Subscriber, and Publisher

This package provides DAPR pub/sub integration for:
- Agent request event subscription (inbound)
- Agent result/failure event publishing (outbound)
- Dead Letter Queue handling via fp-common

Architecture (ADR-010, ADR-011):
- Streaming subscriptions via `subscribe_with_handler()`
- Publishers use `DaprClient.publish_event()`
- DLQ handler reused from fp-common
"""

from ai_model.events.models import (
    AgentCompletedEvent,
    AgentFailedEvent,
    AgentRequestEvent,
    AgentResult,
    ConversationalAgentResult,
    CostRecordedEvent,
    EntityLinkage,
    ExplorerAgentResult,
    ExtractorAgentResult,
    GeneratorAgentResult,
    TieredVisionAgentResult,
)
from ai_model.events.publisher import EventPublisher
from ai_model.events.subscriber import (
    run_streaming_subscriptions,
    set_agent_config_cache,
    set_main_event_loop,
)

__all__ = [
    "AgentCompletedEvent",
    "AgentFailedEvent",
    "AgentRequestEvent",
    "AgentResult",
    "ConversationalAgentResult",
    "CostRecordedEvent",
    "EntityLinkage",
    "EventPublisher",
    "ExplorerAgentResult",
    "ExtractorAgentResult",
    "GeneratorAgentResult",
    "TieredVisionAgentResult",
    "run_streaming_subscriptions",
    "set_agent_config_cache",
    "set_main_event_loop",
]
