"""Unit tests for domain_events module.

Tests cover:
- CollectionEventTopic enum values
- PlantationEventTopic enum values
- get_all_valid_topics helper function
- is_valid_topic validation function
"""

from fp_common.models.domain_events import (
    CollectionEventTopic,
    PlantationEventTopic,
    get_all_valid_topics,
    is_valid_topic,
)


class TestCollectionEventTopic:
    """Tests for CollectionEventTopic enum."""

    def test_quality_result_topics(self) -> None:
        """Test quality result event topics."""
        assert CollectionEventTopic.QUALITY_RESULT_RECEIVED == "collection.quality_result.received"
        assert CollectionEventTopic.QUALITY_RESULT_FAILED == "collection.quality_result.failed"

    def test_exception_images_topics(self) -> None:
        """Test exception images event topics."""
        assert CollectionEventTopic.EXCEPTION_IMAGES_RECEIVED == "collection.exception_images.received"
        assert CollectionEventTopic.EXCEPTION_IMAGES_FAILED == "collection.exception_images.failed"

    def test_weather_topics(self) -> None:
        """Test weather event topics."""
        assert CollectionEventTopic.WEATHER_UPDATED == "collection.weather.updated"
        assert CollectionEventTopic.WEATHER_FAILED == "collection.weather.failed"

    def test_market_prices_topics(self) -> None:
        """Test market prices event topics."""
        assert CollectionEventTopic.MARKET_PRICES_UPDATED == "collection.market_prices.updated"
        assert CollectionEventTopic.MARKET_PRICES_FAILED == "collection.market_prices.failed"


class TestPlantationEventTopic:
    """Tests for PlantationEventTopic enum."""

    def test_farmer_topics(self) -> None:
        """Test farmer event topics."""
        assert PlantationEventTopic.FARMER_REGISTERED == "plantation.farmer.registered"
        assert PlantationEventTopic.FARMER_UPDATED == "plantation.farmer.updated"
        assert PlantationEventTopic.FARMER_DEACTIVATED == "plantation.farmer.deactivated"

    def test_plot_topics(self) -> None:
        """Test plot event topics."""
        assert PlantationEventTopic.PLOT_CREATED == "plantation.plot.created"
        assert PlantationEventTopic.PLOT_UPDATED == "plantation.plot.updated"

    def test_quality_topics(self) -> None:
        """Test quality event topics."""
        assert PlantationEventTopic.QUALITY_GRADED == "plantation.quality.graded"

    def test_performance_topics(self) -> None:
        """Test performance event topics."""
        assert PlantationEventTopic.PERFORMANCE_UPDATED == "plantation.performance_updated"


class TestGetAllValidTopics:
    """Tests for get_all_valid_topics function."""

    def test_returns_list(self) -> None:
        """Test that function returns a list."""
        topics = get_all_valid_topics()
        assert isinstance(topics, list)

    def test_contains_collection_topics(self) -> None:
        """Test that list contains all Collection topics."""
        topics = get_all_valid_topics()
        assert "collection.quality_result.received" in topics
        assert "collection.quality_result.failed" in topics
        assert "collection.exception_images.received" in topics
        assert "collection.weather.updated" in topics
        assert "collection.market_prices.updated" in topics

    def test_contains_plantation_topics(self) -> None:
        """Test that list contains all Plantation topics."""
        topics = get_all_valid_topics()
        assert "plantation.farmer.registered" in topics
        assert "plantation.farmer.updated" in topics
        assert "plantation.plot.created" in topics
        assert "plantation.quality.graded" in topics
        assert "plantation.performance_updated" in topics

    def test_total_count(self) -> None:
        """Test total count of valid topics."""
        topics = get_all_valid_topics()
        # 8 Collection + 7 Plantation = 15 total
        assert len(topics) == 15


class TestIsValidTopic:
    """Tests for is_valid_topic function."""

    def test_valid_collection_topic(self) -> None:
        """Test valid Collection topic returns True."""
        assert is_valid_topic("collection.quality_result.received") is True
        assert is_valid_topic("collection.weather.updated") is True

    def test_valid_plantation_topic(self) -> None:
        """Test valid Plantation topic returns True."""
        assert is_valid_topic("plantation.farmer.registered") is True
        assert is_valid_topic("plantation.plot.created") is True

    def test_invalid_topic_returns_false(self) -> None:
        """Test invalid topic returns False."""
        assert is_valid_topic("invalid.topic") is False
        assert is_valid_topic("collection.invalid.topic") is False
        assert is_valid_topic("") is False
        assert is_valid_topic("random-string") is False

    def test_case_sensitive(self) -> None:
        """Test that topic matching is case-sensitive."""
        assert is_valid_topic("COLLECTION.QUALITY_RESULT.RECEIVED") is False
        assert is_valid_topic("Collection.Quality_Result.Received") is False
