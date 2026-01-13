"""DAPR event handlers for platform cost service.

Story 13.5: DAPR Cost Event Subscription
- CostEventHandler: Subscribes to platform.cost.recorded events
"""

from platform_cost.handlers.cost_event_handler import (
    handle_cost_event,
    run_cost_subscription,
    set_handler_dependencies,
    set_main_event_loop,
)

__all__ = [
    "handle_cost_event",
    "run_cost_subscription",
    "set_handler_dependencies",
    "set_main_event_loop",
]
