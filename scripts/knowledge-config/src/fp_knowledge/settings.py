"""Environment settings for the Knowledge CLI.

Handles configuration for different deployment environments (dev, staging, prod).
Connects to AI Model gRPC service via DAPR sidecar or direct connection.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings

Environment = Literal["dev", "staging", "prod"]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # gRPC endpoints per environment (via DAPR sidecar)
    grpc_endpoint_dev: str = Field(
        default="localhost:50001",
        alias="AI_MODEL_GRPC_ENDPOINT_DEV",
    )
    grpc_endpoint_staging: str = Field(
        default="localhost:50001",
        alias="AI_MODEL_GRPC_ENDPOINT_STAGING",
    )
    grpc_endpoint_prod: str = Field(
        default="localhost:50001",
        alias="AI_MODEL_GRPC_ENDPOINT_PROD",
    )

    # DAPR app-id for the AI Model service
    dapr_app_id: str = Field(
        default="ai-model",
        alias="AI_MODEL_DAPR_APP_ID",
    )

    # gRPC timeout in seconds
    grpc_timeout: float = Field(
        default=30.0,
        alias="AI_MODEL_GRPC_TIMEOUT",
    )

    # Retry configuration
    max_retries: int = Field(
        default=3,
        alias="AI_MODEL_MAX_RETRIES",
    )
    retry_delay: float = Field(
        default=1.0,
        alias="AI_MODEL_RETRY_DELAY",
    )

    # Stream progress polling interval (seconds) when using --poll mode
    poll_interval: float = Field(
        default=2.0,
        alias="AI_MODEL_POLL_INTERVAL",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,  # Allow both alias and field name in constructor
    }

    def get_grpc_endpoint(self, env: Environment) -> str:
        """Get gRPC endpoint for the specified environment."""
        endpoint_map = {
            "dev": self.grpc_endpoint_dev,
            "staging": self.grpc_endpoint_staging,
            "prod": self.grpc_endpoint_prod,
        }
        return endpoint_map[env]


@lru_cache
def get_settings() -> Settings:
    """Get application settings singleton."""
    return Settings()
