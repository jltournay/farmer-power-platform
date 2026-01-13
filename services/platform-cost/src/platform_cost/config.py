"""Service configuration using Pydantic Settings.

Story 13.2: Platform Cost Service scaffold configuration.
Per ADR-016 section 3.6, includes settings for:
- MongoDB connection
- DAPR pub/sub configuration
- Budget thresholds (daily/monthly)
- Cost event retention (TTL)
- gRPC port
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Platform Cost service configuration.

    Configuration values are loaded from environment variables.
    All I/O-related settings support async operations.
    """

    model_config = SettingsConfigDict(
        env_prefix="PLATFORM_COST_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Service identification
    service_name: str = "platform-cost"
    service_version: str = "0.1.0"
    environment: str = "development"

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    grpc_port: int = 50054

    # MongoDB configuration
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "platform_cost"
    mongodb_min_pool_size: int = 5
    mongodb_max_pool_size: int = 50

    # DAPR configuration
    dapr_host: str = "localhost"
    dapr_http_port: int = 3500
    dapr_grpc_port: int = 50001
    dapr_pubsub_name: str = "pubsub"

    # Cost event topic (per ADR-016)
    cost_event_topic: str = "platform.cost.recorded"

    # DAPR sidecar wait time (seconds before starting subscriptions)
    # Story 13.5: Allow time for sidecar readiness before establishing subscription
    dapr_sidecar_wait_seconds: int = 5

    # Budget thresholds (per ADR-016)
    budget_daily_threshold_usd: float = 10.0
    budget_monthly_threshold_usd: float = 100.0

    # Cost event retention (TTL in days)
    # After this period, cost events are automatically deleted via MongoDB TTL index
    cost_event_retention_days: int = 90

    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "json"

    # OpenTelemetry configuration
    otel_enabled: bool = True
    otel_exporter_endpoint: str = "http://localhost:4317"
    otel_exporter_insecure: bool = True  # Set False in production for TLS
    otel_service_namespace: str = "farmer-power"


# Global settings instance
settings = Settings()
