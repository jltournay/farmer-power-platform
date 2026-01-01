"""Collection Model event handling via DAPR streaming subscriptions.

Story 0.6.6: Collection Model Streaming Subscriptions

This package implements DAPR SDK streaming subscriptions per ADR-010/ADR-011.
Replaces the FastAPI HTTP callback handlers with outbound streaming.
"""

from collection_model.events.subscriber import (
    handle_blob_event,
    run_streaming_subscriptions,
    set_blob_processor,
    set_main_event_loop,
)

__all__ = [
    "handle_blob_event",
    "run_streaming_subscriptions",
    "set_blob_processor",
    "set_main_event_loop",
]
