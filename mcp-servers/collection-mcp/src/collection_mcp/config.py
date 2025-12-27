"""Service configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Collection MCP Server settings."""

    model_config = SettingsConfigDict(env_prefix="COLLECTION_MCP_")

    # gRPC Server
    grpc_port: int = 50051
    grpc_max_workers: int = 10

    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "collection_model"

    # Azure Blob Storage
    azure_storage_connection_string: str = ""
    azure_storage_account_name: str = ""
    azure_storage_account_key: str = ""
    sas_token_validity_hours: int = 1

    # OpenTelemetry
    otel_service_name: str = "collection-mcp"
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"

    # Logging
    log_level: str = "INFO"


settings = Settings()
