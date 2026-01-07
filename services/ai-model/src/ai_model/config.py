"""Service configuration using Pydantic Settings.

Story 0.75.5: Added LLM Gateway configuration.
"""

from pydantic import Field, SecretStr
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
        extra="ignore",
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

    # ========================================
    # MCP Integration Configuration (Story 0.75.8b)
    # ========================================

    # TTL for discovered MCP tools cache (seconds)
    # After this duration, tools are re-discovered from MCP servers
    mcp_tool_cache_ttl_seconds: int = 300  # 5 minutes

    # ========================================
    # Azure Blob Storage Configuration (Story 0.75.10b)
    # ========================================

    # Azure Blob Storage connection string for RAG document source files
    azure_storage_connection_string: str = ""

    # Container name for RAG document files
    azure_storage_container: str = "rag-documents"

    # ========================================
    # Extraction Configuration (Story 0.75.10b)
    # ========================================

    # Thread pool size for PDF extraction (PyMuPDF is synchronous)
    extraction_max_workers: int = 4

    # ========================================
    # Azure Document Intelligence (Story 0.75.10c)
    # ========================================

    # Azure Document Intelligence endpoint URL
    # Format: https://<resource-name>.cognitiveservices.azure.com/
    azure_doc_intel_endpoint: str = ""

    # Azure Document Intelligence API key
    azure_doc_intel_key: SecretStr | None = None

    # Azure DI model ID for layout analysis (default: prebuilt-layout)
    # Options: prebuilt-layout (best for general docs), prebuilt-read (text only)
    azure_doc_intel_model: str = "prebuilt-layout"

    # Timeout in seconds for Azure DI operations (async polling)
    azure_doc_intel_timeout: int = 300

    # Cost tracking: estimated cost per page in USD
    azure_doc_intel_cost_per_page: float = 0.01

    # ========================================
    # Semantic Chunking Configuration (Story 0.75.10d)
    # ========================================

    # Target chunk size in characters for semantic splitting
    # Chunks may be smaller at section boundaries, but won't exceed this
    chunk_size: int = 1000

    # Overlap between consecutive chunks to maintain context
    # Applied when splitting large sections at paragraph boundaries
    chunk_overlap: int = 200

    # Minimum viable chunk size - chunks smaller than this are merged
    # or skipped to avoid low-quality fragments
    min_chunk_size: int = 100

    # Maximum chunks per document (safety limit to prevent runaway chunking)
    # If exceeded, chunking fails with an error
    max_chunks_per_document: int = 500

    # ========================================
    # Pinecone Configuration (Story 0.75.12)
    # ========================================
    # Note: validation_alias allows reading from PINECONE_* (without prefix)
    # for consistency with other external service credentials (OpenRouter, Azure)

    # Pinecone API key (required for embedding and vector operations)
    pinecone_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="PINECONE_API_KEY",
    )

    # Pinecone environment/region (e.g., "us-east-1")
    pinecone_environment: str = Field(
        default="us-east-1",
        validation_alias="PINECONE_ENVIRONMENT",
    )

    # Pinecone index name for RAG vectors
    pinecone_index_name: str = Field(
        default="farmer-power-rag",
        validation_alias="PINECONE_INDEX_NAME",
    )

    # Embedding model to use via Pinecone Inference API
    # Default: multilingual-e5-large (1024 dimensions, 100+ languages)
    pinecone_embedding_model: str = Field(
        default="multilingual-e5-large",
        validation_alias="PINECONE_EMBEDDING_MODEL",
    )

    # ========================================
    # Embedding Batch Configuration (Story 0.75.12)
    # ========================================

    # Maximum texts per batch for Pinecone Inference API
    # Pinecone limit is 96 texts per request
    embedding_batch_size: int = 96

    # Maximum tokens per text for embedding
    # Texts exceeding this will be truncated at END
    embedding_max_tokens: int = 1024

    # Retry configuration for embedding API calls
    # Uses exponential backoff (1s min, 10s max) with tenacity
    embedding_retry_max_attempts: int = 3

    # ========================================
    # Vectorization Pipeline Configuration (Story 0.75.13b)
    # ========================================

    # Number of chunks to process per batch in vectorization pipeline
    # Balances memory usage with throughput
    vectorization_batch_size: int = 50

    @property
    def pinecone_enabled(self) -> bool:
        """Check if Pinecone is configured and available.

        Pinecone is enabled only when API key is provided.
        Used to determine whether embedding operations can proceed.
        """
        return bool(self.pinecone_api_key and self.pinecone_api_key.get_secret_value())

    @property
    def azure_doc_intel_enabled(self) -> bool:
        """Check if Azure Document Intelligence is configured and available.

        Azure DI is enabled only when both endpoint and key are provided.
        Used to determine whether to route scanned PDFs to Azure DI or
        fall back to PyMuPDF with a warning.
        """
        return bool(
            self.azure_doc_intel_endpoint and self.azure_doc_intel_key and self.azure_doc_intel_key.get_secret_value()
        )


# Global settings instance
settings = Settings()
