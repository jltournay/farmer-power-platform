"""BFF service configuration.

Environment-based configuration loading per ADR-002.
"""

from functools import lru_cache
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """BFF service settings.

    All settings can be overridden via environment variables.
    Uses pydantic-settings for automatic environment variable parsing.
    """

    # Application settings
    app_env: str = "development"
    log_level: str = "INFO"

    # Authentication settings (Story 0.5.3)
    auth_provider: str = "mock"  # "mock" or "azure-b2c"
    mock_jwt_secret: str = "dev-secret-for-local-development"

    # Azure B2C settings (Story 0.5.8 - stub for now)
    b2c_tenant: str = ""
    b2c_client_id: str = ""

    # DAPR settings
    dapr_http_port: int = 3500
    dapr_grpc_port: int = 50001

    # OpenTelemetry settings
    otel_enabled: bool = True
    otel_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "bff"

    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
    )

    @model_validator(mode="after")
    def validate_no_mock_in_production(self) -> Self:
        """Security guardrail: prevent mock auth in production.

        This validator ensures that the mock authentication provider
        cannot be used in production environments. This is a critical
        security measure to prevent accidental misconfigurations.

        Returns:
            The validated Settings instance.

        Raises:
            ValueError: If mock auth is configured in production.
        """
        if self.auth_provider == "mock" and self.app_env == "production":
            raise ValueError(
                "SECURITY ERROR: Mock auth provider cannot be used in production. "
                "Set AUTH_PROVIDER=azure-b2c for production deployments."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Cached Settings instance.
    """
    return Settings()
