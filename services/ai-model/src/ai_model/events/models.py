"""Event payload models for AI Model DAPR pub/sub.

Story 0.75.8: Event Flow, Subscriber, and Publisher (AC: #3)
Story 0.75.16b: Models moved to fp_common.events.ai_model_events for cross-service sharing.

This module re-exports models from fp_common for backwards compatibility.
All new code should import directly from fp_common.events:
    from fp_common.events import AgentRequestEvent, AgentCompletedEvent, ...
"""

# Re-export all models from fp_common for backwards compatibility
# New code should import directly from fp_common.events
from fp_common.events.ai_model_events import (
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

__all__ = [
    "AgentCompletedEvent",
    "AgentFailedEvent",
    "AgentRequestEvent",
    "AgentResult",
    "ConversationalAgentResult",
    "CostRecordedEvent",
    "EntityLinkage",
    "ExplorerAgentResult",
    "ExtractorAgentResult",
    "GeneratorAgentResult",
    "TieredVisionAgentResult",
]
