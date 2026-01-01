"""Plantation Model event subscriptions via DAPR streaming.

This module implements DAPR SDK streaming subscriptions per ADR-010/ADR-011.
Events are received via outbound streaming (no extra HTTP port needed).

Event handlers:
- handle_quality_result: Processes quality events from Collection Model
- handle_weather_updated: Processes weather events from Collection Model
"""

from plantation_model.events.subscriber import (
    handle_quality_result,
    handle_weather_updated,
    start_subscriptions,
)

__all__ = [
    "handle_quality_result",
    "handle_weather_updated",
    "start_subscriptions",
]
