"""Tests for Collection Model configuration."""

import os
from unittest.mock import patch


def test_config_defaults() -> None:
    """Test configuration default values."""
    # Clear any existing env vars
    with patch.dict(os.environ, {}, clear=True):
        # Import fresh settings
        from collection_model.config import Settings

        settings = Settings()

        assert settings.service_name == "collection-model"
        assert settings.service_version == "0.1.0"
        assert settings.environment == "development"
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.mongodb_database == "collection"
        assert settings.dapr_pubsub_name == "pubsub"
        assert settings.dapr_document_stored_topic == "collection.document.stored"
        assert settings.dapr_poor_quality_topic == "collection.poor_quality_detected"


def test_config_from_env() -> None:
    """Test configuration from environment variables."""
    env_vars = {
        "COLLECTION_ENVIRONMENT": "production",
        "COLLECTION_MONGODB_URI": "mongodb://prod:27017",
        "COLLECTION_OTEL_ENABLED": "false",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        from collection_model.config import Settings

        settings = Settings()

        assert settings.environment == "production"
        assert settings.mongodb_uri == "mongodb://prod:27017"
        assert settings.otel_enabled is False


def test_config_event_grid_topics() -> None:
    """Test Event Grid related topics are configured."""
    from collection_model.config import settings

    assert settings.dapr_document_stored_topic == "collection.document.stored"
    assert settings.dapr_weather_updated_topic == "collection.weather.updated"
    assert settings.dapr_market_prices_topic == "collection.market_prices.updated"
