"""Tests for fp_knowledge.settings module."""

from fp_knowledge.settings import Environment, Settings, get_settings


class TestSettings:
    """Tests for Settings class."""

    def test_default_values(self) -> None:
        """Test default setting values."""
        settings = Settings()

        assert settings.grpc_endpoint_dev == "localhost:50001"
        assert settings.grpc_endpoint_staging == "localhost:50001"
        assert settings.grpc_endpoint_prod == "localhost:50001"
        assert settings.dapr_app_id == "ai-model"
        assert settings.grpc_timeout == 30.0
        assert settings.max_retries == 3
        assert settings.retry_delay == 1.0
        assert settings.poll_interval == 2.0

    def test_get_grpc_endpoint_dev(self) -> None:
        """Test getting gRPC endpoint for dev environment."""
        settings = Settings(grpc_endpoint_dev="dev.example.com:50001")
        endpoint = settings.get_grpc_endpoint("dev")
        assert endpoint == "dev.example.com:50001"

    def test_get_grpc_endpoint_staging(self) -> None:
        """Test getting gRPC endpoint for staging environment."""
        settings = Settings(grpc_endpoint_staging="staging.example.com:50001")
        endpoint = settings.get_grpc_endpoint("staging")
        assert endpoint == "staging.example.com:50001"

    def test_get_grpc_endpoint_prod(self) -> None:
        """Test getting gRPC endpoint for prod environment."""
        settings = Settings(grpc_endpoint_prod="prod.example.com:50001")
        endpoint = settings.get_grpc_endpoint("prod")
        assert endpoint == "prod.example.com:50001"

    def test_custom_dapr_app_id(self) -> None:
        """Test custom DAPR app ID."""
        settings = Settings(dapr_app_id="custom-ai-model")
        assert settings.dapr_app_id == "custom-ai-model"

    def test_custom_timeout(self) -> None:
        """Test custom timeout values."""
        settings = Settings(grpc_timeout=60.0, poll_interval=5.0)
        assert settings.grpc_timeout == 60.0
        assert settings.poll_interval == 5.0


class TestGetSettings:
    """Tests for get_settings function."""

    def test_returns_settings(self) -> None:
        """Test that get_settings returns a Settings instance."""
        # Clear cache to ensure fresh instance
        get_settings.cache_clear()

        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_caches_result(self) -> None:
        """Test that get_settings caches the result."""
        get_settings.cache_clear()

        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2


class TestEnvironmentType:
    """Tests for Environment type."""

    def test_valid_environments(self) -> None:
        """Test that valid environment values are accepted."""
        valid_envs: list[Environment] = ["dev", "staging", "prod"]
        for env in valid_envs:
            # This should not raise any errors
            settings = Settings()
            endpoint = settings.get_grpc_endpoint(env)
            assert endpoint is not None
