"""BFF service configuration.

Environment-based configuration loading per ADR-002.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """BFF service settings.

    All settings can be overridden via environment variables.
    Uses pydantic-settings for automatic environment variable parsing.
    """

    # Application settings
    app_env: str = "development"
    log_level: str = "INFO"

    # Authentication settings (Story 0.5.3)
    auth_provider: str = "mock"  # "mock" or "azure-ad-b2c"
    mock_jwt_secret: str = "dev-secret-for-local-development"

    # DAPR settings
    dapr_http_port: int = 3500
    dapr_grpc_port: int = 50001

    # OpenTelemetry settings
    otel_enabled: bool = True
    otel_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "bff"

    model_config = {
        "env_prefix": "",
        "case_sensitive": False,
    }


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Cached Settings instance.
    """
    return Settings()
