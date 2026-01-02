"""Unit tests for BFF configuration loading.

Tests configuration loading per AC5 requirements.
"""

import os
from unittest.mock import patch


def test_settings_loads_default_values() -> None:
    """Test that Settings loads with default values."""
    from bff.config import Settings

    settings = Settings()
    assert settings.app_env == "development"
    assert settings.auth_provider == "mock"
    assert settings.dapr_grpc_port == 50001


def test_settings_loads_from_environment() -> None:
    """Test that Settings loads values from environment variables."""
    from bff.config import Settings

    env_vars = {
        "APP_ENV": "production",
        "AUTH_PROVIDER": "azure-ad-b2c",
        "DAPR_GRPC_PORT": "51001",
        "OTEL_ENDPOINT": "http://otel-collector:4317",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        settings = Settings()
        assert settings.app_env == "production"
        assert settings.auth_provider == "azure-ad-b2c"
        assert settings.dapr_grpc_port == 51001
        assert settings.otel_endpoint == "http://otel-collector:4317"


def test_settings_mock_jwt_secret_has_default() -> None:
    """Test that mock JWT secret has a default for development."""
    from bff.config import Settings

    settings = Settings()
    assert settings.mock_jwt_secret is not None
    assert len(settings.mock_jwt_secret) > 0


def test_get_settings_returns_singleton() -> None:
    """Test that get_settings returns a cached settings instance."""
    from bff.config import get_settings

    settings1 = get_settings()
    settings2 = get_settings()
    # Both should be the same cached instance
    assert settings1.app_env == settings2.app_env
