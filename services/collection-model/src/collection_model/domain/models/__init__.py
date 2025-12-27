"""Domain models for Collection Model service.

This module previously contained hardcoded event classes.
Events are now config-driven via source_config.events.on_success.topic.

See: DaprEventPublisher.publish_success() for event emission.
"""

# No hardcoded event models - all events are config-driven
__all__: list[str] = []
