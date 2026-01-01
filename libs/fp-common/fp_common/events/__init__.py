"""Event handling utilities for Farmer Power Platform services.

Provides shared components for DAPR event subscriptions including:
- Dead Letter Queue (DLQ) handler for failed events
- DLQ Repository for MongoDB storage
- DLQ subscription startup utilities

Story 0.6.8: Dead Letter Queue Handler (ADR-006)
"""

from fp_common.events.dlq_handler import (
    DLQHandler,
    handle_dead_letter,
    set_dlq_event_loop,
    set_dlq_repository,
    start_dlq_subscription,
)
from fp_common.events.dlq_repository import DLQRecord, DLQRepository

__all__ = [
    "DLQHandler",
    "DLQRecord",
    "DLQRepository",
    "handle_dead_letter",
    "set_dlq_event_loop",
    "set_dlq_repository",
    "start_dlq_subscription",
]
