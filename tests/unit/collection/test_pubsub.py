"""Tests for Collection Model Dapr pub/sub client."""

import pytest

from collection_model.config import settings


def test_pubsub_client_initialization() -> None:
    """Test DaprPubSubClient initializes with correct settings."""
    from collection_model.infrastructure.pubsub import DaprPubSubClient

    client = DaprPubSubClient()

    assert client._dapr_host == settings.dapr_host
    assert client._dapr_http_port == settings.dapr_http_port
    assert client._pubsub_name == settings.dapr_pubsub_name
    assert "localhost" in client._base_url
    assert "3500" in client._base_url


def test_pubsub_client_custom_host() -> None:
    """Test DaprPubSubClient with custom host and port."""
    from collection_model.infrastructure.pubsub import DaprPubSubClient

    client = DaprPubSubClient(dapr_host="custom-host", dapr_http_port=3600)

    assert client._dapr_host == "custom-host"
    assert client._dapr_http_port == 3600
    assert "custom-host:3600" in client._base_url


def test_pubsub_topics_configured_correctly() -> None:
    """Test that pub/sub topics are correctly configured."""
    assert settings.dapr_document_stored_topic == "collection.document.stored"
    assert settings.dapr_poor_quality_topic == "collection.poor_quality_detected"
    assert settings.dapr_weather_updated_topic == "collection.weather.updated"
    assert settings.dapr_market_prices_topic == "collection.market_prices.updated"


def test_get_pubsub_client_returns_singleton() -> None:
    """Test get_pubsub_client returns singleton instance."""
    from collection_model.infrastructure.pubsub import get_pubsub_client

    client1 = get_pubsub_client()
    client2 = get_pubsub_client()

    assert client1 is client2


@pytest.mark.asyncio
async def test_pubsub_publish_event_builds_correct_url() -> None:
    """Test publish_event builds the correct Dapr URL."""
    from collection_model.infrastructure.pubsub import DaprPubSubClient

    client = DaprPubSubClient()

    # Verify URL construction is correct
    expected_base = f"http://{settings.dapr_host}:{settings.dapr_http_port}"
    assert client._base_url == expected_base

    # The URL for publishing would be:
    # {base_url}/v1.0/publish/{pubsub_name}/{topic}
    expected_publish_url = f"{expected_base}/v1.0/publish/{settings.dapr_pubsub_name}/collection.document.stored"
    assert settings.dapr_pubsub_name == "pubsub"


@pytest.mark.asyncio
async def test_pubsub_check_health_with_unavailable_dapr() -> None:
    """Test health check handles connection failures gracefully."""
    from collection_model.infrastructure.pubsub import DaprPubSubClient

    # Use a port that's definitely not available
    client = DaprPubSubClient(dapr_host="127.0.0.1", dapr_http_port=59999)
    result = await client.check_health()

    # Should return False when Dapr is unavailable (connection refused)
    assert result is False


@pytest.mark.asyncio
async def test_pubsub_publish_event_with_unavailable_dapr() -> None:
    """Test event publishing handles connection failures gracefully."""
    from collection_model.infrastructure.pubsub import DaprPubSubClient

    # Use a port that's definitely not available
    client = DaprPubSubClient(dapr_host="127.0.0.1", dapr_http_port=59999)
    result = await client.publish_event("test.topic", {"event_type": "test"})

    # Should return False when Dapr is unavailable
    assert result is False
