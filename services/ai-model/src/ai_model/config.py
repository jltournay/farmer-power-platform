"""Service configuration using Pydantic Settings.

Story 0.75.5: Added LLM Gateway configuration.
"""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """AI Model service configuration.

    Configuration values are loaded from environment variables.
    All I/O-related settings support async operations.
    """

    model_config = SettingsConfigDict(
        env_prefix="AI_MODEL_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Service identification
    service_name: str = "ai-model"
    service_version: str = "0.1.0"
    environment: str = "development"

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    grpc_port: int = 50051

    # MongoDB configuration
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "ai_model"
    mongodb_min_pool_size: int = 5
    mongodb_max_pool_size: int = 50

    # DAPR configuration
    dapr_host: str = "localhost"
    dapr_http_port: int = 3500
    dapr_grpc_port: int = 50001
    dapr_pubsub_name: str = "pubsub"

    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "json"

    # OpenTelemetry configuration
    otel_enabled: bool = True
    otel_exporter_endpoint: str = "http://localhost:4317"
    otel_exporter_insecure: bool = True  # Set False in production for TLS
    otel_service_namespace: str = "farmer-power"

    # ========================================
    # LLM Gateway Configuration (Story 0.75.5)
    # ========================================

    # OpenRouter API key (required for LLM operations)
    # Can also be set via OPENROUTER_API_KEY environment variable
    openrouter_api_key: SecretStr | None = None

    # OpenRouter base URL (default should not be changed)
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Site identification for OpenRouter
    openrouter_site_url: str = "https://farmer-power.com"
    openrouter_site_name: str = "Farmer Power Platform"

    # Default model for LLM requests
    llm_default_model: str = "anthropic/claude-3-5-sonnet"

    # Fallback models to try if primary model fails
    # Order matters - tried in sequence
    llm_fallback_models: list[str] = [
        "openai/gpt-4o",
        "google/gemini-pro",
    ]

    # Retry configuration for transient errors (429, 5xx)
    llm_retry_max_attempts: int = 3
    llm_retry_backoff_ms: list[int] = [100, 500, 2000]

    # Rate limiting (per minute)
    llm_rate_limit_rpm: int = 60  # Requests per minute
    llm_rate_limit_tpm: int = 100000  # Tokens per minute

    # Cost tracking and alerting
    llm_cost_tracking_enabled: bool = True
    llm_cost_alert_daily_usd: float = 10.0  # Daily threshold in USD (0 = disabled)
    llm_cost_alert_monthly_usd: float = 100.0  # Monthly threshold in USD (0 = disabled)

    # DAPR topics for cost events
    llm_cost_event_topic: str = "ai.cost.recorded"
    llm_cost_alert_topic: str = "ai.cost.threshold_exceeded"

    # ========================================
    # Event Handler Configuration (Story 0.75.8)
    # ========================================

    # Timeout for agent config cache lookups in event handlers (seconds)
    event_handler_config_timeout_s: int = 10

    # Timeout for agent execution in event handlers (seconds)
    event_handler_execution_timeout_s: int = 30


# Global settings instance
settings = Settings()
