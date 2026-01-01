"""Service configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Collection Model service configuration.

    Configuration values are loaded from environment variables.
    All I/O-related settings support async operations.
    """

    model_config = SettingsConfigDict(
        env_prefix="COLLECTION_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Service identification
    service_name: str = "collection-model"
    service_version: str = "0.1.0"
    environment: str = "development"

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000

    # MongoDB configuration
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "collection"
    mongodb_min_pool_size: int = 5
    mongodb_max_pool_size: int = 50
    mongodb_retry_attempts: int = 3
    mongodb_retry_min_wait: int = 1
    mongodb_retry_max_wait: int = 10

    # Azure Blob Storage configuration
    azure_storage_connection_string: str = "DefaultEndpointsProtocol=https;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1"

    # Content Processor Worker configuration
    worker_poll_interval: float = 5.0
    worker_batch_size: int = 10
    worker_max_retries: int = 3

    # AI Model DAPR configuration
    ai_model_app_id: str = "ai-model"

    # CORS configuration
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8080"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # DAPR configuration
    # Note: Event topics are config-driven from source_config, not hardcoded here
    dapr_host: str = "localhost"
    dapr_http_port: int = 3500
    dapr_pubsub_name: str = "pubsub"
    dapr_sidecar_wait_seconds: int = 5  # Wait time for DAPR sidecar readiness

    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "json"

    # OpenTelemetry configuration
    otel_enabled: bool = True
    otel_exporter_endpoint: str = "http://localhost:4317"
    otel_exporter_insecure: bool = True
    otel_service_namespace: str = "farmer-power"


# Global settings instance
settings = Settings()
