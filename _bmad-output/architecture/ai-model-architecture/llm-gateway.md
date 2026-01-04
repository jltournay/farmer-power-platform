# LLM Gateway

[OpenRouter.ai](https://openrouter.ai) serves as the unified LLM gateway:

| Benefit | Description |
|---------|-------------|
| **Multi-Provider** | Access OpenAI, Anthropic, Google, Meta, Mistral through single API |
| **Model Flexibility** | Switch models per agent without code changes |
| **Fallback** | Automatic failover if one provider is down |
| **Unified Billing** | Single invoice, per-model cost breakdown |
| **No Vendor Lock-in** | Can switch providers without changing integration |

**Model Configuration Strategy:**

Models are configured **explicitly per agent** (not via centralized task-type routing). This provides:

- **Clarity:** Agent config shows exactly what model it uses
- **Flexibility:** Each agent can use any model without override patterns
- **Self-contained:** No need to check gateway config to understand agent behavior

**Recommended Models by Use Case:**

| Use Case | Recommended Model | Rationale |
|----------|-------------------|-----------|
| **Extraction** | Claude Haiku / GPT-4o-mini | Fast, cheap, structured output |
| **Diagnosis** | Claude Sonnet / GPT-4o | Complex reasoning, accuracy critical |
| **Generation** | Claude Sonnet | Translation, simplification, cultural context |
| **Market Analysis** | GPT-4o | Data synthesis, pattern recognition |
| **Intent Classification** | Claude Haiku | Fast, low-latency classification |

**Gateway Configuration:**

The gateway handles **resilience and operational concerns**, not model selection.

Configuration follows the **established project pattern**: Pydantic Settings loaded from environment variables.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    LLM GATEWAY CONFIGURATION FLOW                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  SOURCE OF TRUTH: Environment Variables                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  # .env (local) or K8s ConfigMap/Secrets (deployed)            │   │
│  │  AI_MODEL_OPENROUTER_API_KEY=sk-or-...                          │   │
│  │  AI_MODEL_OPENROUTER_BASE_URL=https://openrouter.ai/api/v1      │   │
│  │  AI_MODEL_LLM_FALLBACK_MODELS=claude-3-5-sonnet,gpt-4o,gemini   │   │
│  │  AI_MODEL_LLM_RETRY_MAX_ATTEMPTS=3                              │   │
│  │  AI_MODEL_LLM_RATE_LIMIT_RPM=100                                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              │ Loaded at startup                        │
│                              ▼                                          │
│  PYDANTIC SETTINGS: services/ai-model/src/ai_model/config.py           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Validated, typed, with defaults                                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              │ Dependency injection                     │
│                              ▼                                          │
│  LLM GATEWAY CLASS: Retry, fallback, rate limiting, cost tracking      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Pydantic Settings (config.py):**

```python
# services/ai-model/src/ai_model/config.py
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """AI Model service configuration.

    Follows project pattern: env vars with AI_MODEL_ prefix.
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

    # Server configuration (ADR-011: Two-port pattern)
    host: str = "0.0.0.0"
    port: int = 8000
    grpc_port: int = 50051

    # MongoDB configuration
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "ai_model"

    # ═══════════════════════════════════════════════════════════════════
    # LLM GATEWAY CONFIGURATION
    # ═══════════════════════════════════════════════════════════════════

    # OpenRouter connection
    openrouter_api_key: SecretStr  # Required, no default
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Fallback chain (comma-separated in env var)
    llm_fallback_models: list[str] = [
        "anthropic/claude-3-5-sonnet",
        "openai/gpt-4o",
        "google/gemini-pro",
    ]

    # Retry configuration
    llm_retry_max_attempts: int = 3
    llm_retry_backoff_ms: list[int] = [100, 500, 2000]

    # Rate limiting
    llm_rate_limit_rpm: int = 100      # Requests per minute
    llm_rate_limit_tpm: int = 100000   # Tokens per minute

    # Cost tracking
    llm_cost_tracking_enabled: bool = True
    llm_cost_log_per_call: bool = True
    llm_cost_alert_daily_usd: float = 100.0

    # ═══════════════════════════════════════════════════════════════════
    # PINECONE (RAG)
    # ═══════════════════════════════════════════════════════════════════

    pinecone_api_key: SecretStr  # Required, no default
    pinecone_environment: str = "us-east-1"
    pinecone_index_name: str = "farmer-power-knowledge"

    # ═══════════════════════════════════════════════════════════════════
    # DAPR
    # ═══════════════════════════════════════════════════════════════════

    dapr_host: str = "localhost"
    dapr_http_port: int = 3500
    dapr_pubsub_name: str = "pubsub"

    # ═══════════════════════════════════════════════════════════════════
    # OBSERVABILITY
    # ═══════════════════════════════════════════════════════════════════

    log_level: str = "INFO"
    otel_enabled: bool = True
    otel_exporter_endpoint: str = "http://localhost:4317"


# Global settings instance
settings = Settings()
```

**LLM Gateway Class:**

```python
# services/ai-model/src/ai_model/llm/gateway.py
from ai_model.config import Settings


class LLMGateway:
    """Unified LLM access via OpenRouter with resilience.

    Handles: retry, fallback, rate limiting, cost tracking.
    Does NOT handle: model selection (per-agent config).
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = self._create_client()
        self.rate_limiter = RateLimiter(
            rpm=settings.llm_rate_limit_rpm,
            tpm=settings.llm_rate_limit_tpm,
        )

    async def complete(
        self,
        model: str,  # Explicit model from agent config
        messages: list[dict],
        **kwargs,
    ) -> LLMResponse:
        """Execute LLM completion with resilience."""

        await self.rate_limiter.acquire()

        # Try primary model, then fallback chain
        models_to_try = [model] + self.settings.llm_fallback_models

        for attempt_model in models_to_try:
            try:
                response = await self._call_with_retry(
                    attempt_model, messages, **kwargs
                )
                self._track_cost(response)
                return response
            except ModelUnavailableError:
                continue  # Try next in fallback chain

        raise AllModelsUnavailableError(models_to_try)
```

**Why This Pattern:**

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **No YAML file** | Env vars only | Aligns with project pattern (collection, plantation, etc.) |
| **Pydantic Settings** | Type-safe config | Validated at startup, IDE support, clear defaults |
| **SecretStr for keys** | API key protection | Never logged, K8s secrets integration |
| **Flat structure** | Simple env vars | Easy to override per environment |
| **Global instance** | `settings = Settings()` | Consistent with other services |

**Agent-Level Model Configuration:**

Each agent explicitly declares its model in its configuration:

```yaml
# Example: disease-diagnosis agent
agent:
  id: "disease-diagnosis"
  llm:
    model: "anthropic/claude-3-5-sonnet"   # Explicit, no indirection
    temperature: 0.3
    max_tokens: 2000
```
