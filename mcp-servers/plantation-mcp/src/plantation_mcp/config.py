"""Service configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Plantation MCP Server settings."""

    model_config = SettingsConfigDict(env_prefix="PLANTATION_MCP_")

    # gRPC Server
    grpc_port: int = 50051
    grpc_max_workers: int = 10

    # Plantation Model Service
    plantation_app_id: str = "plantation-model"

    # OpenTelemetry
    otel_service_name: str = "plantation-mcp"
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"

    # Logging
    log_level: str = "INFO"


settings = Settings()
