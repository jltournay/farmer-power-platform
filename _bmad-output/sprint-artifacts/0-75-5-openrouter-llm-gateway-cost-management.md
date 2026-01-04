# Story 0.75.5: OpenRouter LLM Gateway with Cost Observability

**Status:** review
**GitHub Issue:** #97

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer implementing AI agents**,
I want a unified LLM gateway with cost tracking, observability, and resilience,
So that agents can reliably call LLMs with automatic retry, fallback, and full cost visibility.

## Acceptance Criteria

1. **AC1: LLM Gateway Class** - `LLMGateway` class created in `services/ai-model/src/ai_model/llm/gateway.py` with OpenRouter integration
2. **AC2: OpenRouter Client** - Async HTTP client (httpx) calling OpenRouter API with proper headers (api-key, site-url, site-name)
3. **AC3: Retry with Backoff** - Tenacity retry decorator with exponential backoff (100ms, 500ms, 2000ms) for transient errors (429, 500, 502, 503, 504)
4. **AC4: Fallback Chain** - Execute fallback models when primary fails (ModelUnavailableError triggers next model in chain)
5. **AC5: Model Validation** - Validate model availability via OpenRouter `/models` API endpoint on startup
6. **AC6: Rate Limiting** - Token bucket rate limiter for requests per minute (RPM) and tokens per minute (TPM)
7. **AC7: Cost Event Pydantic Model** - `LlmCostEvent` Pydantic model with all fields per epic specification
8. **AC8: Cost Persistence** - Cost events stored in MongoDB collection `ai_model.llm_cost_events`
9. **AC9: Cost Repository** - `LlmCostEventRepository` with insert and query methods
10. **AC10: Cost Event Emission** - DAPR pub/sub event `ai.cost.recorded` published after each LLM call
11. **AC11: gRPC CostService** - Proto definition and gRPC service implementing cost query APIs (contract for Epic 9 dashboard)
12. **AC12: Budget Alerting** - Configurable daily/monthly cost thresholds with alert events when exceeded
13. **AC13: OpenTelemetry Metrics** - All 4 metrics specified in epic: `llm_request_cost_usd`, `llm_tokens_total`, `llm_daily_cost_usd`, `llm_cost_alert_triggered`
14. **AC14: Settings Integration** - All config values from Pydantic Settings (`AI_MODEL_` prefix) per LLM Gateway architecture doc
15. **AC15: Gateway Lifespan** - Gateway initialized in app lifespan, validates model availability before accepting requests
16. **AC16: Unit Tests** - Unit tests for retry logic, fallback chain, rate limiting, cost tracking (minimum 40 tests)
17. **AC17: E2E Tests Pass** - All existing E2E tests pass (no regressions)
18. **AC18: CI Passes** - All lint checks and unit tests pass in CI

## Tasks / Subtasks

- [ ] **Task 1: Create LLM Directory Structure** (AC: #1)
  - [ ] Create `services/ai-model/src/ai_model/llm/__init__.py`
  - [ ] Create `services/ai-model/src/ai_model/llm/gateway.py`
  - [ ] Create `services/ai-model/src/ai_model/llm/rate_limiter.py`
  - [ ] Create `services/ai-model/src/ai_model/llm/exceptions.py`
  - [ ] Export classes from `ai_model.llm`

- [ ] **Task 2: Implement LLM Exceptions** (AC: #3, #4)
  - [ ] Define `LLMError` base exception
  - [ ] Define `ModelUnavailableError` for model failures (triggers fallback)
  - [ ] Define `AllModelsUnavailableError` when entire fallback chain fails
  - [ ] Define `RateLimitExceededError` for rate limit breaches
  - [ ] Define `TransientError` for retryable errors (429, 5xx)

- [ ] **Task 3: Implement Token Bucket Rate Limiter** (AC: #6)
  - [ ] Create `RateLimiter` class with async `acquire()` method
  - [ ] Implement token bucket algorithm for RPM limiting
  - [ ] Implement separate token bucket for TPM limiting
  - [ ] Add `RateLimitExceededError` when limits exceeded
  - [ ] Add OpenTelemetry metrics for rate limit events

- [ ] **Task 4: Implement ChatOpenRouter (LangChain-compatible)** (AC: #1, #2, #3, #4, #5)
  - [ ] Create `ChatOpenRouter` class extending `langchain_openai.ChatOpenAI`
  - [ ] Override `__init__` to set `base_url="https://openrouter.ai/api/v1"`
  - [ ] Configure `openai_api_key` from Settings or `OPENROUTER_API_KEY` env var
  - [ ] Override `lc_secrets` property to map to `OPENROUTER_API_KEY`
  - [ ] Add optional headers (`HTTP-Referer`, `X-Title`) via `default_headers`
  - [ ] Create `LLMGateway` wrapper class for application-level concerns:
    - [ ] Inject `ChatOpenRouter` instance
    - [ ] Apply Tenacity retry decorator with exponential backoff
    - [ ] Implement fallback chain logic: try primary, then each fallback in order
    - [ ] Implement `validate_models()` async method calling `/models` API
  - [ ] **Benefit:** Native LangChain/LangGraph compatibility for agent workflows

- [ ] **Task 5: Define LlmCostEvent Pydantic Model** (AC: #7)
  - [ ] Create `services/ai-model/src/ai_model/domain/cost_event.py`
  - [ ] Define `LlmCostEvent` model with all fields per epic:
    - `timestamp: datetime`
    - `request_id: str`
    - `agent_type: str`
    - `agent_id: str`
    - `model: str`
    - `tokens_in: int`
    - `tokens_out: int`
    - `cost_usd: Decimal`
    - `factory_id: Optional[str]`
    - `success: bool`
    - `retry_count: int`
  - [ ] Add `model_config` for MongoDB serialization
  - [ ] Export from `ai_model.domain`

- [ ] **Task 6: Implement LlmCostEventRepository** (AC: #8, #9)
  - [ ] Create `services/ai-model/src/ai_model/infrastructure/repositories/cost_event_repository.py`
  - [ ] Extend base repository pattern from Story 0.75.2/0.75.3
  - [ ] Implement `insert(event: LlmCostEvent) -> str` method
  - [ ] Implement `get_daily_summary(date: date) -> DailyCostSummary` method
  - [ ] Implement `get_cost_by_agent_type(start: date, end: date) -> list[AgentTypeCost]` method
  - [ ] Implement `get_cost_by_model(start: date, end: date) -> list[ModelCost]` method
  - [ ] Implement `get_current_day_cost() -> CostSummary` method
  - [ ] Add MongoDB indexes for efficient querying (timestamp, agent_type, model)
  - [ ] Export from `ai_model.infrastructure.repositories`

- [ ] **Task 7: Implement Cost Tracking in Gateway** (AC: #10)
  - [ ] Add `_get_generation_stats(generation_id: str) -> GenerationStats` method
  - [ ] Call `GET /generation?id={generation_id}` to get **native** token counts and **actual cost**
  - [ ] **Implement retry with backoff for generation stats** - generation ID may not be immediately available after chat completion (100ms, 200ms, 500ms delays)
  - [ ] Handle 404 response by retrying (generation not yet indexed)
  - [ ] Add `_track_cost(generation_id, agent_id, agent_type, request_id, retry_count)` method
  - [ ] Create `LlmCostEvent` from generation stats (NOT from chat response `usage`)
  - [ ] Call repository to persist cost event
  - [ ] Publish `ai.cost.recorded` event via DAPR pub/sub
  - [ ] Update OpenTelemetry metrics
  - [ ] **CRITICAL:** Do NOT use `usage` from chat response - it's normalized, not billing tokens

- [ ] **Task 8: Define CostService Proto** (AC: #11)
  - [ ] Add to `proto/ai_model/v1/ai_model.proto`:
    - `CostService` service definition
    - `GetDailyCostSummary` RPC
    - `GetCurrentDayCost` RPC
    - `GetCostByAgentType` RPC
    - `GetCostByModel` RPC
    - `GetCostAlerts` RPC
    - `ConfigureCostThreshold` RPC
  - [ ] Define request/response messages for each RPC
  - [ ] Run `make proto` to generate Python stubs

- [ ] **Task 9: Implement gRPC CostService** (AC: #11)
  - [ ] Create `services/ai-model/src/ai_model/api/cost_service.py`
  - [ ] Implement `CostServiceServicer` class
  - [ ] Implement `GetDailyCostSummary` using repository
  - [ ] Implement `GetCurrentDayCost` using repository
  - [ ] Implement `GetCostByAgentType` using repository
  - [ ] Implement `GetCostByModel` using repository
  - [ ] Implement `GetCostAlerts` returning current threshold breaches
  - [ ] Implement `ConfigureCostThreshold` to update runtime thresholds
  - [ ] Register servicer in gRPC server

- [ ] **Task 10: Implement Budget Alerting** (AC: #12)
  - [ ] Add daily/monthly threshold fields to Settings
  - [ ] Create `services/ai-model/src/ai_model/llm/budget_monitor.py`
  - [ ] Implement `BudgetMonitor` class tracking running totals
  - [ ] Check thresholds after each cost event
  - [ ] Emit `ai.cost.threshold_exceeded` event when breached
  - [ ] Add `llm_cost_alert_triggered` counter metric
  - [ ] Store alert state to prevent duplicate alerts

- [ ] **Task 11: Implement OpenTelemetry Metrics** (AC: #13)
  - [ ] Create histogram: `llm_request_cost_usd` (cost per request)
  - [ ] Create counter: `llm_tokens_total` with labels: model, direction (in/out)
  - [ ] Create gauge: `llm_daily_cost_usd` (running daily total)
  - [ ] Create counter: `llm_cost_alert_triggered` with label: threshold_type
  - [ ] Add metric recording in `_track_cost()` method

- [ ] **Task 12: Update Settings** (AC: #14)
  - [ ] Verify/add `openrouter_api_key: SecretStr`
  - [ ] Verify/add `openrouter_base_url: str`
  - [ ] Verify/add `llm_fallback_models: list[str]`
  - [ ] Verify/add `llm_retry_max_attempts: int`
  - [ ] Verify/add `llm_retry_backoff_ms: list[int]`
  - [ ] Verify/add `llm_rate_limit_rpm: int`
  - [ ] Verify/add `llm_rate_limit_tpm: int`
  - [ ] Verify/add `llm_cost_tracking_enabled: bool`
  - [ ] Verify/add `llm_cost_alert_daily_usd: float`
  - [ ] Verify/add `llm_cost_alert_monthly_usd: float`

- [ ] **Task 13: Gateway Lifespan Integration** (AC: #15)
  - [ ] Modify `services/ai-model/src/ai_model/main.py` lifespan
  - [ ] Instantiate `LLMGateway` with settings
  - [ ] Call `gateway.validate_models()` during startup
  - [ ] Store gateway in `app.state.llm_gateway`
  - [ ] Instantiate `BudgetMonitor` and store in `app.state`
  - [ ] Add gateway cleanup in shutdown

- [ ] **Task 14: Unit Tests - Exceptions** (AC: #16)
  - [ ] Create `tests/unit/ai_model/llm/test_exceptions.py`
  - [ ] Test exception inheritance hierarchy
  - [ ] Test exception messages and attributes

- [ ] **Task 15: Unit Tests - Rate Limiter** (AC: #16)
  - [ ] Create `tests/unit/ai_model/llm/test_rate_limiter.py`
  - [ ] Test `acquire()` succeeds when under limit
  - [ ] Test `acquire()` blocks when at limit
  - [ ] Test `acquire()` raises when exceeded with timeout
  - [ ] Test token refill over time
  - [ ] Test RPM and TPM independent tracking

- [ ] **Task 16: Unit Tests - Gateway Core** (AC: #16)
  - [ ] Create `tests/unit/ai_model/llm/test_gateway.py`
  - [ ] Mock httpx client for all tests
  - [ ] Test `complete()` returns response on success
  - [ ] Test retry on 429 status code
  - [ ] Test retry on 503 status code
  - [ ] Test exponential backoff timing (verify delays)
  - [ ] Test fallback chain triggered on ModelUnavailableError
  - [ ] Test fallback succeeds with second model
  - [ ] Test AllModelsUnavailableError when all fail
  - [ ] Test `validate_models()` calls OpenRouter API
  - [ ] Test cost tracking called after successful completion

- [ ] **Task 17: Unit Tests - Cost Event** (AC: #16)
  - [ ] Create `tests/unit/ai_model/domain/test_cost_event.py`
  - [ ] Test `LlmCostEvent` validation
  - [ ] Test Decimal cost serialization
  - [ ] Test timestamp handling

- [ ] **Task 18: Unit Tests - Cost Repository** (AC: #16)
  - [ ] Create `tests/unit/ai_model/infrastructure/repositories/test_cost_event_repository.py`
  - [ ] Test `insert()` persists to MongoDB
  - [ ] Test `get_daily_summary()` aggregation
  - [ ] Test `get_cost_by_agent_type()` grouping
  - [ ] Test `get_cost_by_model()` grouping
  - [ ] Test `get_current_day_cost()` calculation

- [ ] **Task 19: Unit Tests - Budget Monitor** (AC: #16)
  - [ ] Create `tests/unit/ai_model/llm/test_budget_monitor.py`
  - [ ] Test alert triggered when daily threshold exceeded
  - [ ] Test alert triggered when monthly threshold exceeded
  - [ ] Test no duplicate alerts for same threshold
  - [ ] Test alert reset at day/month boundary

- [ ] **Task 20: E2E Verification** (AC: #17)
  - [ ] Run full E2E test suite with `--build` flag
  - [ ] Verify no regressions
  - [ ] Capture test output in story file

- [ ] **Task 21: CI Verification** (AC: #18)
  - [ ] Run `ruff check .` - lint passes
  - [ ] Run `ruff format --check .` - format passes
  - [ ] Push and verify CI passes
  - [ ] Trigger E2E CI workflow and verify passes

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.75.5: OpenRouter LLM Gateway with Cost Observability"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-75-5-openrouter-llm-gateway-cost-management
  ```

**Branch name:** `story/0-75-5-openrouter-llm-gateway-cost-management`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/...`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.75.5: OpenRouter LLM Gateway with Cost Observability" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/...`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
# LLM module tests
PYTHONPATH="${PYTHONPATH}:.:services/ai-model/src:libs/fp-common:libs/fp-proto/src" pytest tests/unit/ai_model/llm/ -v

# Cost domain and repository tests
PYTHONPATH="${PYTHONPATH}:.:services/ai-model/src:libs/fp-common:libs/fp-proto/src" pytest tests/unit/ai_model/domain/test_cost_event.py tests/unit/ai_model/infrastructure/repositories/test_cost_event_repository.py -v
```
**Output:**
```
======================== 82 passed, 8 warnings in 3.38s ========================

Test breakdown:
- test_exceptions.py: 15 tests
- test_rate_limiter.py: 18 tests
- test_budget_monitor.py: 12 tests
- test_cost_event.py: 13 tests
- test_cost_event_repository.py: 12 tests
- test_gateway.py: 12 tests
```
**Unit tests passed:** [x] Yes / [ ] No

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure (--build is MANDATORY)
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build

# Wait for services, then run tests
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v

# Tear down
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```
**Output:**
```
================== 102 passed, 1 skipped in 125.05s (0:02:05) ==================

All E2E tests passed:
- test_00_infrastructure_verification.py: 22 tests
- test_01_plantation_mcp_contracts.py: 14 tests
- test_02_collection_mcp_contracts.py: 12 tests
- test_03_factory_farmer_flow.py: 5 tests
- test_04_quality_blob_ingestion.py: 6 tests
- test_05_weather_ingestion.py: 7 tests
- test_06_cross_model_events.py: 5 tests
- test_07_grading_validation.py: 6 tests
- test_08_zip_ingestion.py: 9 tests (1 skipped)
- test_30_bff_farmer_api.py: 17 tests
```
**E2E passed:** [x] Yes / [ ] No

### 3. Lint Check
```bash
ruff check . && ruff format --check .
```
**Output:**
```
All checks passed!
404 files already formatted
```
**Lint passed:** [x] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin story/0-75-5-openrouter-llm-gateway-cost-management

# Wait ~30s, then check CI status
gh run list --branch story/0-75-5-openrouter-llm-gateway-cost-management --limit 3
```
**Quality CI Run ID:** 20699502592
**Quality CI Status:** [x] Passed / [ ] Failed
**E2E CI Run ID:** 20699540419
**E2E CI Status:** [x] Passed / [ ] Failed
**Verification Date:** 2026-01-04

---

## Dev Notes

### Architecture Reference

**Primary Sources:**
- LLM Gateway: `_bmad-output/architecture/ai-model-architecture/llm-gateway.md`
- Agent Configuration: `_bmad-output/architecture/ai-model-architecture/agent-configuration-schema.md`
- Epic 0.75: `_bmad-output/epics/epic-0-75-ai-model.md`

**Pattern Sources:**
- Repository pattern: Story 0.75.2 (Prompt Repository)
- Cache pattern: Story 0.75.4 (MongoChangeStreamCache)
- gRPC service: Story 0.75.1 (AI Model Setup)

### Key Design Decisions

#### 1. OpenRouter as Single Gateway

> **Decision:** ALL LLM calls go through OpenRouter - no direct provider calls.

Benefits:
- Multi-provider access (OpenAI, Anthropic, Google, Meta, Mistral)
- Single API key, unified billing
- Automatic failover between providers
- No vendor lock-in

#### 2. Model Selection Per-Agent (Not Centralized)

> **Decision:** Each agent config explicitly declares its model - no task-type routing table.

```yaml
# Each agent knows its model
agent:
  id: "disease-diagnosis"
  llm:
    model: "anthropic/claude-3-5-sonnet"  # Explicit
```

Benefits:
- Self-contained agent configs
- No indirection to understand behavior
- Each agent can use any model without override patterns

#### 3. Fallback Chain Order

> **Decision:** Fallback chain is global (from Settings), tried in order after primary fails.

```python
models_to_try = [agent_model] + settings.llm_fallback_models
# e.g., ["anthropic/claude-3-5-sonnet", "openai/gpt-4o", "google/gemini-pro"]
```

The agent's configured model is always tried first, then the global fallback chain.

#### 4. Cost Event Schema

```python
class LlmCostEvent(BaseModel):
    timestamp: datetime          # When the call completed
    request_id: str              # Correlation ID for tracing
    agent_type: str              # "extractor", "explorer", etc.
    agent_id: str                # Specific agent config ID
    model: str                   # Actual model used (may differ from requested)
    tokens_in: int               # Input tokens
    tokens_out: int              # Output tokens
    cost_usd: Decimal            # Total cost (Decimal for precision)
    factory_id: Optional[str]    # For future per-factory attribution
    success: bool                # Whether the request succeeded
    retry_count: int             # Number of retries before success/failure
```

#### 5. Retry Strategy

| Error Code | Action | Rationale |
|------------|--------|-----------|
| 429 | Retry with backoff | Rate limited, wait and retry |
| 500 | Retry with backoff | Server error, may be transient |
| 502, 503, 504 | Retry with backoff | Gateway/proxy errors |
| 400, 401, 403 | Fail immediately | Client errors, retry won't help |
| Model unavailable | Try fallback | Move to next model in chain |

Backoff schedule: 100ms → 500ms → 2000ms (configurable via Settings)

### ChatOpenRouter Implementation Pattern

> **Key Decision:** Subclass `langchain_openai.ChatOpenAI` for native LangChain/LangGraph compatibility.

```python
# services/ai-model/src/ai_model/llm/chat_openrouter.py
from typing import Optional
import os

from langchain_openai import ChatOpenAI
from pydantic import Field, SecretStr
from pydantic.functional_validators import secret_from_env


class ChatOpenRouter(ChatOpenAI):
    """OpenRouter LLM client compatible with LangChain/LangGraph.

    Subclasses ChatOpenAI since OpenRouter uses OpenAI-compatible API.
    """

    openai_api_key: Optional[SecretStr] = Field(
        alias="api_key",
        default_factory=secret_from_env("OPENROUTER_API_KEY", default=None),
    )

    @property
    def lc_secrets(self) -> dict[str, str]:
        return {"openai_api_key": "OPENROUTER_API_KEY"}

    def __init__(
        self,
        model: str = "anthropic/claude-3-5-sonnet",
        openai_api_key: Optional[str] = None,
        **kwargs,
    ):
        openai_api_key = openai_api_key or os.environ.get("OPENROUTER_API_KEY")
        super().__init__(
            model=model,
            base_url="https://openrouter.ai/api/v1",
            openai_api_key=openai_api_key,
            default_headers={
                "HTTP-Referer": "https://farmer-power.com",
                "X-Title": "Farmer Power Platform",
            },
            **kwargs,
        )
```

**Usage in LangGraph workflows (Stories 0.75.17+):**
```python
from ai_model.llm import ChatOpenRouter

# Direct usage - works with all LangChain/LangGraph patterns
llm = ChatOpenRouter(model="anthropic/claude-3-5-sonnet", temperature=0.3)
response = await llm.ainvoke(messages)

# In LangGraph agent
from langgraph.prebuilt import create_react_agent
agent = create_react_agent(llm, tools=[...])
```

### OpenRouter API Integration

> **Source:** [OpenRouter API Reference](https://openrouter.ai/docs/api/reference/overview)

**Base URL:** `https://openrouter.ai/api/v1`

#### Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/chat/completions` | POST | Primary LLM request endpoint |
| `/generation?id={ID}` | GET | Get native token counts and **actual cost** |
| `/models` | GET | List available models with pricing |

#### Required Headers
```python
headers = {
    "Authorization": f"Bearer {settings.openrouter_api_key.get_secret_value()}",
    "Content-Type": "application/json",
    # Optional - for OpenRouter leaderboard rankings
    "HTTP-Referer": "https://farmer-power.com",
    "X-Title": "Farmer Power Platform",
}
```

#### Chat Completion Request
```python
{
    "model": "anthropic/claude-3-5-sonnet",
    "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."}
    ],
    "max_tokens": 2000,
    "temperature": 0.3,
}
```

#### Chat Completion Response
```python
{
    "id": "gen-abc123...",  # SAVE THIS for /generation lookup
    "model": "anthropic/claude-3-5-sonnet",
    "choices": [...],
    "usage": {
        "prompt_tokens": 150,       # ⚠️ Normalized (GPT-4o tokenizer)
        "completion_tokens": 200,   # ⚠️ NOT billing tokens
        "total_tokens": 350
    }
}
```

> **⚠️ CRITICAL:** The `usage` in the response uses **normalized GPT-4o tokenizer counts**, but **billing uses native model tokenizer counts**. To get accurate cost, you MUST call the Generation Stats endpoint.

#### Generation Stats Endpoint (for accurate cost)
```python
# GET /generation?id=gen-abc123...
{
    "id": "gen-abc123...",
    "native_tokens_prompt": 145,      # Actual billing tokens
    "native_tokens_completion": 198,
    "total_cost": 0.00175,            # Actual USD cost
    "model": "anthropic/claude-3-5-sonnet"
}
```

> **⚠️ TIMING:** The generation stats are NOT immediately available after chat completion. The generation ID may return 404 for a short period (~100-500ms) after the request completes. **Implement retry with backoff** (e.g., 100ms, 200ms, 500ms) when fetching generation stats.

#### Models List Response (for pricing data)
```python
# GET /models
{
    "data": [
        {
            "id": "anthropic/claude-3-5-sonnet",
            "name": "Claude 3.5 Sonnet",
            "pricing": {
                "prompt": "0.000003",      # USD per token (string)
                "completion": "0.000015"   # USD per token (string)
            },
            "context_length": 200000
        }
    ]
}
```

### Rate Limiter Design

Token bucket algorithm with two independent buckets:

1. **RPM Bucket** - Requests per minute
   - Capacity: `settings.llm_rate_limit_rpm`
   - Refill rate: 1 token per (60 / rpm) seconds

2. **TPM Bucket** - Tokens per minute
   - Capacity: `settings.llm_rate_limit_tpm`
   - Refill rate: 1 token per (60 / tpm) seconds
   - Consume `tokens_in + tokens_out` after request

```python
class RateLimiter:
    async def acquire(self, tokens: int = 1) -> None:
        """Acquire rate limit tokens. Blocks if at limit."""
        await self._rpm_bucket.acquire(1)
        await self._tpm_bucket.acquire(tokens)
```

### gRPC CostService API Contract

This API is consumed by Epic 9 (Platform Admin Dashboard) Story 9.6.

```protobuf
service CostService {
    // Summary queries
    rpc GetDailyCostSummary(DateRangeRequest) returns (DailyCostSummaryResponse);
    rpc GetCurrentDayCost(Empty) returns (CostSummary);

    // Breakdown queries
    rpc GetCostByAgentType(DateRangeRequest) returns (CostByAgentTypeResponse);
    rpc GetCostByModel(DateRangeRequest) returns (CostByModelResponse);

    // Alerts
    rpc GetCostAlerts(Empty) returns (CostAlertsResponse);
    rpc ConfigureCostThreshold(ThresholdConfig) returns (Empty);
}

message DateRangeRequest {
    google.protobuf.Timestamp start_date = 1;
    google.protobuf.Timestamp end_date = 2;
}

message CostSummary {
    string total_cost_usd = 1;  // String for Decimal precision
    int64 total_requests = 2;
    int64 total_tokens_in = 3;
    int64 total_tokens_out = 4;
}

message DailyCostSummaryResponse {
    repeated DailyCost daily_costs = 1;
}

message DailyCost {
    google.protobuf.Timestamp date = 1;
    CostSummary summary = 2;
}
```

### Previous Story (0.75.4) Learnings

1. **TypeAdapter for discriminated unions** - Already used in AgentConfigCache
2. **Change stream pattern** - MongoChangeStreamCache base class available
3. **52 unit tests** - Set high bar for test coverage
4. **E2E verification** - All 102 tests passed
5. **Lifespan hooks pattern** - Established in main.py

### Recent Git Commits

```
705fc66 Story 0.75.4: Source Cache for Agent Types and Prompt Config (#96)
2b970a2 Story 0.75.3: Pydantic Model for Agent Configuration + Mongo Repository (#94)
463488e docs(story): Mark Story 0.75.2 as done
6da2c90 Story 0.75.2: Pydantic Model for Prompt + Mongo Repository (#92)
```

**Patterns from recent stories:**
- File naming: `services/ai-model/src/ai_model/llm/gateway.py`
- Test naming: `tests/unit/ai_model/llm/test_gateway.py`
- Export pattern: Update `__init__.py` files
- Commit format: Include issue reference

### File Structure After Story

```
services/ai-model/src/ai_model/
├── llm/                                    # NEW MODULE
│   ├── __init__.py                         # NEW: Export ChatOpenRouter, LLMGateway, RateLimiter
│   ├── chat_openrouter.py                  # NEW: ChatOpenRouter(ChatOpenAI) - LangChain compatible
│   ├── gateway.py                          # NEW: LLMGateway wrapper (retry, fallback, cost tracking)
│   ├── rate_limiter.py                     # NEW: Token bucket rate limiter
│   ├── budget_monitor.py                   # NEW: Cost threshold monitoring
│   └── exceptions.py                       # NEW: LLM-specific exceptions
├── domain/
│   ├── cost_event.py                       # NEW: LlmCostEvent model
│   └── ...
├── infrastructure/repositories/
│   ├── cost_event_repository.py            # NEW: Cost event persistence
│   └── ...
├── api/
│   ├── cost_service.py                     # NEW: gRPC CostService
│   └── ...
├── config.py                               # MODIFIED: Add LLM settings
└── main.py                                 # MODIFIED: Add gateway lifespan

proto/ai_model/v1/
└── ai_model.proto                          # MODIFIED: Add CostService

tests/unit/ai_model/
├── llm/                                    # NEW TEST DIRECTORY
│   ├── test_gateway.py                     # NEW: Gateway unit tests
│   ├── test_rate_limiter.py                # NEW: Rate limiter tests
│   ├── test_budget_monitor.py              # NEW: Budget alerting tests
│   └── test_exceptions.py                  # NEW: Exception tests
├── domain/
│   └── test_cost_event.py                  # NEW: Cost event model tests
└── infrastructure/repositories/
    └── test_cost_event_repository.py       # NEW: Repository tests
```

### Testing Strategy

**Unit Tests Required (minimum 40 tests):**

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_exceptions.py` | 5+ | Exception hierarchy, messages |
| `test_rate_limiter.py` | 8+ | Token bucket algorithm, RPM/TPM |
| `test_gateway.py` | 15+ | Retry, fallback, validation, cost tracking |
| `test_cost_event.py` | 5+ | Pydantic validation, serialization |
| `test_cost_event_repository.py` | 8+ | CRUD, aggregations |
| `test_budget_monitor.py` | 5+ | Threshold detection, alerts |

**E2E Verification:**
- All existing E2E tests must pass
- No new E2E tests needed (LLM gateway tested in Story 0.75.18 with real AI)
- Gateway is mocked in E2E until Story 0.75.18

### Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| `langchain-openai` | ^0.3 | ChatOpenAI base class for LangChain/LangGraph compatibility |
| `httpx` | ^0.27 | Async HTTP client for generation stats endpoint |
| `tenacity` | ^8.2 | Retry with backoff |
| `opentelemetry-api` | ^1.21 | Metrics |

Check if already in `pyproject.toml`, add if missing.

> **Why langchain-openai?** OpenRouter uses the OpenAI-compatible API. By subclassing `ChatOpenAI`, we get native LangChain/LangGraph compatibility for agent workflows (Stories 0.75.17+) without additional integration work.

### What This Story Does NOT Include

| Not in Scope | Implemented In |
|--------------|----------------|
| Agent workflow execution | Stories 0.75.17+ |
| RAG integration | Stories 0.75.9+ |
| CLI tooling | Stories 0.75.6, 0.75.7 |
| E2E tests with real LLM | Story 0.75.18 |
| Platform Admin Dashboard UI | Epic 9 (Story 9.6) |

### Anti-Patterns to AVOID

| Anti-Pattern | Correct Approach |
|--------------|------------------|
| Direct provider calls | ALL calls via OpenRouter gateway |
| Custom httpx client for LLM | Extend `ChatOpenAI` for LangChain/LangGraph compatibility |
| Synchronous I/O | ALL HTTP calls must be async |
| Hardcoded retry delays | Use configurable backoff_ms from Settings |
| Swallowing exceptions | Log errors, track in metrics, re-raise |
| Float for currency | Use Decimal for cost_usd |
| Missing correlation ID | Always include request_id in cost events |
| **Using `usage` from chat response for cost** | **Call `/generation?id=` endpoint for native tokens and actual cost** |

### OpenRouter Pricing Reference (2024)

| Model | Input ($/1K tokens) | Output ($/1K tokens) |
|-------|---------------------|----------------------|
| claude-3-5-sonnet | $0.003 | $0.015 |
| claude-3-haiku | $0.00025 | $0.00125 |
| gpt-4o | $0.005 | $0.015 |
| gpt-4o-mini | $0.00015 | $0.0006 |

**Cost Optimization Rules (from project-context.md):**
- Use Haiku for triage/classification (~$0.001/call)
- Use Sonnet for analysis requiring reasoning
- ALWAYS set `max_tokens` to prevent runaway costs

### References

- [Source: `_bmad-output/architecture/ai-model-architecture/llm-gateway.md`] - LLM Gateway architecture
- [Source: `_bmad-output/architecture/ai-model-architecture/agent-configuration-schema.md`] - Agent config schema
- [Source: `_bmad-output/epics/epic-0-75-ai-model.md`] - Story requirements (Story 0.75.5 section)
- [Source: `_bmad-output/project-context.md`] - Critical rules, cost optimization
- [Source: `_bmad-output/sprint-artifacts/0-75-4-source-cache-agent-types-prompt-config.md`] - Previous story patterns
- [OpenRouter API Docs](https://openrouter.ai/docs) - API reference

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

**Created:**
- (list new files)

**Modified:**
- (list modified files with brief description)
