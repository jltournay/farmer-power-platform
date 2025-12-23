"""Unit tests for Plantation Model service configuration."""

import os
from unittest.mock import patch

import pytest

from plantation_model.config import Settings


@pytest.mark.unit
class TestSettings:
    """Tests for Settings configuration class."""

    def test_default_values(self) -> None:
        """Test that default settings are properly set."""
        settings = Settings()

        assert settings.service_name == "plantation-model"
        assert settings.service_version == "0.1.0"
        assert settings.environment == "development"
        assert settings.port == 8000
        assert settings.grpc_port == 50051

    def test_mongodb_defaults(self) -> None:
        """Test MongoDB default configuration."""
        settings = Settings()

        assert settings.mongodb_uri == "mongodb://localhost:27017"
        assert settings.mongodb_database == "plantation"
        assert settings.mongodb_min_pool_size == 5
        assert settings.mongodb_max_pool_size == 50

    def test_dapr_defaults(self) -> None:
        """Test DAPR default configuration."""
        settings = Settings()

        assert settings.dapr_http_port == 3500
        assert settings.dapr_grpc_port == 50001

    def test_otel_defaults(self) -> None:
        """Test OpenTelemetry default configuration."""
        settings = Settings()

        assert settings.otel_enabled is True
        assert settings.otel_exporter_endpoint == "http://localhost:4317"
        assert settings.otel_service_namespace == "farmer-power"

    def test_env_prefix(self) -> None:
        """Test that environment variables use PLANTATION_ prefix."""
        with patch.dict(os.environ, {"PLANTATION_ENVIRONMENT": "production"}):
            settings = Settings()
            assert settings.environment == "production"

    def test_mongodb_uri_from_env(self) -> None:
        """Test MongoDB URI from environment variable."""
        test_uri = "mongodb://user:pass@mongodb:27017"
        with patch.dict(os.environ, {"PLANTATION_MONGODB_URI": test_uri}):
            settings = Settings()
            assert settings.mongodb_uri == test_uri

    def test_otel_disabled_from_env(self) -> None:
        """Test disabling OpenTelemetry via environment."""
        with patch.dict(os.environ, {"PLANTATION_OTEL_ENABLED": "false"}):
            settings = Settings()
            assert settings.otel_enabled is False
