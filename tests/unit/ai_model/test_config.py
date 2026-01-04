"""Unit tests for AI Model configuration."""

import os
from unittest.mock import patch


class TestSettings:
    """Tests for AI Model Settings configuration."""

    def test_default_settings(self) -> None:
        """Settings should have correct default values."""
        # Import here to get fresh settings
        from ai_model.config import Settings

        settings = Settings()

        assert settings.service_name == "ai-model"
        assert settings.service_version == "0.1.0"
        assert settings.environment == "development"
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.grpc_port == 50051
        assert settings.mongodb_database == "ai_model"
        assert settings.dapr_pubsub_name == "pubsub"
        assert settings.otel_enabled is True

    def test_settings_from_environment(self) -> None:
        """Settings should be loadable from environment variables."""
        from ai_model.config import Settings

        env_vars = {
            "AI_MODEL_SERVICE_NAME": "test-ai-model",
            "AI_MODEL_SERVICE_VERSION": "1.0.0",
            "AI_MODEL_ENVIRONMENT": "production",
            "AI_MODEL_PORT": "9000",
            "AI_MODEL_GRPC_PORT": "50052",
            "AI_MODEL_MONGODB_URI": "mongodb://testhost:27017",
            "AI_MODEL_MONGODB_DATABASE": "test_ai_model",
            "AI_MODEL_OTEL_ENABLED": "false",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            settings = Settings()

            assert settings.service_name == "test-ai-model"
            assert settings.service_version == "1.0.0"
            assert settings.environment == "production"
            assert settings.port == 9000
            assert settings.grpc_port == 50052
            assert settings.mongodb_uri == "mongodb://testhost:27017"
            assert settings.mongodb_database == "test_ai_model"
            assert settings.otel_enabled is False

    def test_settings_env_prefix(self) -> None:
        """Settings should use AI_MODEL_ prefix for environment variables."""
        from ai_model.config import Settings

        # Verify the model config uses correct prefix
        assert Settings.model_config.get("env_prefix") == "AI_MODEL_"

    def test_mongodb_pool_settings(self) -> None:
        """MongoDB pool settings should have sensible defaults."""
        from ai_model.config import Settings

        settings = Settings()

        assert settings.mongodb_min_pool_size == 5
        assert settings.mongodb_max_pool_size == 50
        assert settings.mongodb_min_pool_size < settings.mongodb_max_pool_size

    def test_dapr_settings(self) -> None:
        """DAPR settings should have correct defaults."""
        from ai_model.config import Settings

        settings = Settings()

        assert settings.dapr_host == "localhost"
        assert settings.dapr_http_port == 3500
        assert settings.dapr_grpc_port == 50001

    def test_otel_settings(self) -> None:
        """OpenTelemetry settings should have correct defaults."""
        from ai_model.config import Settings

        settings = Settings()

        assert settings.otel_enabled is True
        assert settings.otel_exporter_endpoint == "http://localhost:4317"
        assert settings.otel_exporter_insecure is True
        assert settings.otel_service_namespace == "farmer-power"
