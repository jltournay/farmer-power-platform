"""Domain event topic definitions.

This module provides a central registry of valid DAPR Pub/Sub topic names
for domain events. All event topics must be defined here to ensure
consistency and enable validation.

Topic Naming Convention:
    {domain}.{entity}.{action}

Examples:
    - collection.quality_result.received
    - collection.weather.updated
    - plantation.farmer.registered
"""

from enum import StrEnum


class CollectionEventTopic(StrEnum):
    """Valid DAPR Pub/Sub topics for Collection Model domain events.

    These topics are used for config-driven event emission from
    the content processing pipeline.
    """

    # Quality Results (QC Analyzer - Bag Result)
    QUALITY_RESULT_RECEIVED = "collection.quality_result.received"
    QUALITY_RESULT_FAILED = "collection.quality_result.failed"

    # Exception Images (QC Analyzer - Exceptions)
    EXCEPTION_IMAGES_RECEIVED = "collection.exception_images.received"
    EXCEPTION_IMAGES_FAILED = "collection.exception_images.failed"

    # Weather Data
    WEATHER_UPDATED = "collection.weather.updated"
    WEATHER_FAILED = "collection.weather.failed"

    # Market Prices
    MARKET_PRICES_UPDATED = "collection.market_prices.updated"
    MARKET_PRICES_FAILED = "collection.market_prices.failed"


class PlantationEventTopic(StrEnum):
    """Valid DAPR Pub/Sub topics for Plantation Model domain events."""

    # Farmer events
    FARMER_REGISTERED = "plantation.farmer.registered"

    # Plot events
    PLOT_CREATED = "plantation.plot.created"
    PLOT_UPDATED = "plantation.plot.updated"

    # Quality events (Story 1.7)
    QUALITY_GRADED = "plantation.quality.graded"
    PERFORMANCE_UPDATED = "plantation.performance_updated"


def get_all_valid_topics() -> list[str]:
    """Get all valid domain event topic names.

    Returns:
        List of all valid topic strings from all domain enums.
    """
    topics: list[str] = []
    topics.extend([t.value for t in CollectionEventTopic])
    topics.extend([t.value for t in PlantationEventTopic])
    return topics


def is_valid_topic(topic: str) -> bool:
    """Check if a topic name is valid.

    Args:
        topic: The topic name to validate.

    Returns:
        True if the topic is defined in one of the domain enums.
    """
    return topic in get_all_valid_topics()
