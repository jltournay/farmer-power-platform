"""Service configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Plantation Model service configuration.

    Configuration values are loaded from environment variables.
    All I/O-related settings support async operations.
    """

    model_config = SettingsConfigDict(
        env_prefix="PLANTATION_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Service identification
    service_name: str = "plantation-model"
    service_version: str = "0.1.0"
    environment: str = "development"

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    grpc_port: int = 50051

    # MongoDB configuration
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "plantation"
    mongodb_min_pool_size: int = 5
    mongodb_max_pool_size: int = 50

    # DAPR configuration
    dapr_host: str = "localhost"
    dapr_http_port: int = 3500
    dapr_grpc_port: int = 50001
    dapr_pubsub_name: str = "pubsub"
    dapr_farmer_events_topic: str = "farmer-events"

    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "json"

    # OpenTelemetry configuration
    otel_enabled: bool = True
    otel_exporter_endpoint: str = "http://localhost:4317"
    otel_exporter_insecure: bool = True  # Set False in production for TLS
    otel_service_namespace: str = "farmer-power"

    # Google APIs configuration
    google_elevation_api_key: str = ""  # Required for altitude auto-population

    # Collection Model configuration (Story 0.6.13)
    # Used to fetch quality documents for event processing via gRPC
    # Replaces direct MongoDB access per ADR-010/011
    collection_app_id: str = "collection-model"  # DAPR app ID for service invocation
    collection_grpc_host: str = ""  # Direct gRPC host (empty = use DAPR sidecar)


# Global settings instance
settings = Settings()
