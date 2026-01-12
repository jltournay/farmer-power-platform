"""Event handling utilities for Farmer Power Platform services.

Provides shared components for DAPR event subscriptions including:
- Dead Letter Queue (DLQ) handler for failed events
- DLQ Repository for MongoDB storage
- DLQ subscription startup utilities
- AI Model event models (shared across services)
- Unified Cost Event Model (ADR-016)

Story 0.6.8: Dead Letter Queue Handler (ADR-006)
Story 0.75.16b: AI Model event models moved to fp-common
Story 13.1: Unified Cost Event Model (ADR-016)
"""

from fp_common.events.ai_model_events import (
    AgentCompletedEvent,
    AgentFailedEvent,
    AgentRequestEvent,
    AgentResult,
    ConversationalAgentResult,
    EntityLinkage,
    ExplorerAgentResult,
    ExtractorAgentResult,
    GeneratorAgentResult,
    TieredVisionAgentResult,
)

# Story 13.1: Unified Cost Event Model (ADR-016)
# Import from new location - replaces LLM-only CostRecordedEvent
from fp_common.events.cost_recorded import (
    CostRecordedEvent,
    CostType,
    CostUnit,
)
from fp_common.events.dlq_handler import (
    DLQHandler,
    handle_dead_letter,
    set_dlq_event_loop,
    set_dlq_repository,
    start_dlq_subscription,
)
from fp_common.events.dlq_repository import DLQRecord, DLQRepository

__all__ = [
    "AgentCompletedEvent",
    "AgentFailedEvent",
    "AgentRequestEvent",
    "AgentResult",
    "ConversationalAgentResult",
    "CostRecordedEvent",
    "CostType",
    "CostUnit",
    "DLQHandler",
    "DLQRecord",
    "DLQRepository",
    "EntityLinkage",
    "ExplorerAgentResult",
    "ExtractorAgentResult",
    "GeneratorAgentResult",
    "TieredVisionAgentResult",
    "handle_dead_letter",
    "set_dlq_event_loop",
    "set_dlq_repository",
    "start_dlq_subscription",
]
