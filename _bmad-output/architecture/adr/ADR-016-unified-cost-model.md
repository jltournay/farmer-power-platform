# ADR-016: Unified Cost Model and Platform Cost Service

**Status:** Accepted
**Date:** 2026-01-12
**Deciders:** Winston (Architect), Amelia (Dev), John (PM), Jeanlouistournay
**Related Stories:** Epic 9 (Admin Portal), Story 9.6 (LLM Cost Dashboard)

## Context

The platform incurs costs from multiple external services:

| Cost Source | Current State | Billing Model |
|-------------|---------------|---------------|
| **LLM (OpenRouter)** | Tracked in ai-model, persisted to MongoDB, exposed via gRPC CostService | Per token (input/output) |
| **Azure Document Intelligence** | `AzureDocIntelCostEvent` created but only logged, not persisted | Per page |
| **Pinecone Embedding** | `EmbeddingCostEvent` persisted but no USD cost calculated | Per token (included in index pricing) |
| **SMS (Africa's Talking)** | Not implemented yet | Per message |

### Problems

1. **Cost tracking is fragmented** - LLM costs in one place, document costs logged but not stored, embedding costs without USD values
2. **No unified view** - Platform Admin UI can only see LLM costs via ai-model gRPC
3. **Wrong service boundary** - Cost aggregation logic is in ai-model, which violates single responsibility
4. **Not extensible** - Adding SMS costs would require modifying ai-model

### Requirements

1. Platform Admin UI needs a **unified cost dashboard** showing all cost types
2. Dashboard design: **Hybrid approach** with summary view + expandable sections + detail links
3. Each service should be a **cost producer**, not a cost store
4. Solution must be **extensible** for future cost types (SMS, etc.)

## Decision

**Create a dedicated `platform-cost` service that aggregates costs from all services via DAPR pub/sub.**

### Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  ai-model   │     │ notification│     │  future-svc │
│ (LLM, Doc,  │     │   (SMS)     │     │             │
│  Embedding) │     │             │     │             │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       │ publish           │ publish           │ publish
       ▼                   ▼                   ▼
┌──────────────────────────────────────────────────────┐
│           DAPR Pub/Sub: "platform.cost.recorded"     │
└──────────────────────────────────────────────────────┘
       │
       │ subscribe
       ▼
┌─────────────────────────────────────────────────────┐
│  services/platform-cost/                            │
│                                                     │
│  - Subscribes to cost events                        │
│  - Persists to unified cost_events collection       │
│  - Exposes gRPC UnifiedCostService                  │
│  - Handles budget alerts across all cost types      │
└─────────────────────────────────────────────────────┘
       │
       │ gRPC
       ▼
┌─────────────────────────────────────────────────────┐
│  Platform Admin UI                                  │
└─────────────────────────────────────────────────────┘
```

### Key Principles

1. **ai-model becomes a pure cost PRODUCER** - publishes events, does not store or expose cost APIs
2. **platform-cost is the single source of truth** - stores all costs, exposes all cost APIs
3. **Event-driven decoupling** - services don't know about platform-cost, just publish to topic
4. **Unified schema** - all cost types use the same event envelope

---

## Detailed Changes

### Part 1: Shared Event Model (fp-common)

#### New File: `libs/fp-common/fp_common/events/cost_recorded.py`

```python
"""Unified cost event model for cross-service cost tracking.

All services that incur billable costs publish this event to the
'platform.cost.recorded' DAPR topic. The platform-cost service
subscribes and aggregates.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CostType(str, Enum):
    """Supported cost types across the platform."""
    LLM = "llm"
    DOCUMENT = "document"
    EMBEDDING = "embedding"
    SMS = "sms"


class CostUnit(str, Enum):
    """Units of measurement for cost quantities."""
    TOKENS = "tokens"
    PAGES = "pages"
    MESSAGES = "messages"
    QUERIES = "queries"


class CostRecordedEvent(BaseModel):
    """Unified cost event published by all services.

    This is the canonical event schema for cost tracking. All services
    that incur billable costs MUST publish this event to the
    'platform.cost.recorded' DAPR topic.

    Attributes:
        cost_type: Category of cost (llm, document, embedding, sms).
        amount_usd: Cost in USD as string (Decimal serialization for precision).
        quantity: Number of units consumed (tokens, pages, messages).
        unit: Unit of measurement for quantity.
        timestamp: When the cost was incurred (UTC).
        source_service: Service that incurred the cost (e.g., "ai-model").
        success: Whether the operation succeeded (failed ops may still incur cost).
        metadata: Type-specific additional data (model, agent_type, etc.).

    Example:
        ```python
        event = CostRecordedEvent(
            cost_type=CostType.LLM,
            amount_usd="0.0023",
            quantity=1500,
            unit=CostUnit.TOKENS,
            timestamp=datetime.now(UTC),
            source_service="ai-model",
            success=True,
            metadata={
                "model": "anthropic/claude-3-5-sonnet",
                "agent_type": "explorer",
                "tokens_in": 1000,
                "tokens_out": 500,
            }
        )
        ```
    """

    cost_type: CostType = Field(..., description="Category of cost")
    amount_usd: str = Field(..., description="Cost in USD (Decimal as string)")
    quantity: int = Field(..., ge=0, description="Number of units consumed")
    unit: CostUnit = Field(..., description="Unit of measurement")
    timestamp: datetime = Field(..., description="When cost was incurred (UTC)")
    source_service: str = Field(..., description="Service that incurred the cost")
    success: bool = Field(default=True, description="Whether operation succeeded")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Type-specific data")

    # Optional fields extracted from metadata for indexing
    factory_id: str | None = Field(default=None, description="Factory ID for attribution")
    request_id: str | None = Field(default=None, description="Correlation ID for tracing")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: str,
        }
```

#### Metadata by Cost Type

| Cost Type | Required Metadata Fields | Optional Fields |
|-----------|-------------------------|-----------------|
| `llm` | `model`, `agent_type`, `tokens_in`, `tokens_out` | `agent_id`, `factory_id`, `retry_count` |
| `document` | `model_id`, `page_count` | `document_id`, `job_id` |
| `embedding` | `model`, `texts_count` | `knowledge_domain`, `batch_count` |
| `sms` | `message_type`, `recipient_count` | `campaign_id` |

---

### Part 2: Changes in ai-model Service

#### 2.1 Files to DELETE

| File | Current Purpose | Why Delete |
|------|-----------------|------------|
| `src/ai_model/api/cost_service.py` | gRPC CostService implementation | Moves to platform-cost |
| `src/ai_model/infrastructure/repositories/cost_event_repository.py` | LLM cost MongoDB repository | Moves to platform-cost |
| `src/ai_model/infrastructure/repositories/embedding_cost_repository.py` | Embedding cost MongoDB repository | Moves to platform-cost |
| `src/ai_model/llm/budget_monitor.py` | Budget threshold alerting | Moves to platform-cost |

#### 2.2 Proto Changes: `proto/ai_model/v1/ai_model.proto`

**REMOVE the following from the proto file:**

```protobuf
// DELETE: CostService and all related messages

service CostService {
  rpc GetDailyCostSummary(DailyCostSummaryRequest) returns (DailyCostSummaryResponse);
  rpc GetCurrentDayCost(CurrentDayCostRequest) returns (CostSummaryResponse);
  rpc GetCostByAgentType(CostByAgentTypeRequest) returns (CostByAgentTypeResponse);
  rpc GetCostByModel(CostByModelRequest) returns (CostByModelResponse);
  rpc GetCostAlerts(CostAlertsRequest) returns (CostAlertsResponse);
  rpc ConfigureCostThreshold(ConfigureCostThresholdRequest) returns (ConfigureCostThresholdResponse);
}

// DELETE all these messages:
message DailyCostSummaryRequest { ... }
message DailyCostSummaryResponse { ... }
message DailyCost { ... }
message CurrentDayCostRequest { ... }
message CostSummaryResponse { ... }
message CostByAgentTypeRequest { ... }
message CostByAgentTypeResponse { ... }
message AgentTypeCostEntry { ... }
message CostByModelRequest { ... }
message CostByModelResponse { ... }
message ModelCostEntry { ... }
message CostAlertsRequest { ... }
message CostAlertsResponse { ... }
message CostAlert { ... }
message ConfigureCostThresholdRequest { ... }
message ConfigureCostThresholdResponse { ... }
```

#### 2.3 Config Changes: `src/ai_model/config.py`

**REMOVE these settings (move to platform-cost):**

```python
# DELETE: Lines 94-100
llm_cost_tracking_enabled: bool = True
llm_cost_alert_daily_usd: float = 10.0
llm_cost_alert_monthly_usd: float = 100.0
llm_cost_event_topic: str = "ai.cost.recorded"
llm_cost_alert_topic: str = "ai.cost.threshold_exceeded"
```

**ADD these settings:**

```python
# ========================================
# Unified Cost Publishing (ADR-016)
# ========================================

# DAPR topic for unified cost events (consumed by platform-cost service)
unified_cost_topic: str = "platform.cost.recorded"

# Pinecone embedding cost per 1K tokens (approximate)
# Source: Pinecone Inference API pricing ~$0.0001/1K tokens
embedding_cost_per_1k_tokens: float = 0.0001
```

#### 2.4 Main.py Changes: `src/ai_model/main.py`

**REMOVE from lifespan startup:**

```python
# DELETE: Cost repository initialization
cost_repository = LlmCostEventRepository(db)
await cost_repository.ensure_indexes()

# DELETE: Embedding cost repository initialization
embedding_cost_repository = EmbeddingCostEventRepository(db)
await embedding_cost_repository.ensure_indexes()

# DELETE: Budget monitor initialization
budget_monitor = BudgetMonitor(
    daily_threshold_usd=Decimal(str(settings.llm_cost_alert_daily_usd)),
    monthly_threshold_usd=Decimal(str(settings.llm_cost_alert_monthly_usd)),
)
```

**ADD to lifespan startup:**

```python
from dapr.aio.clients import DaprClient

# Create DAPR client for cost event publishing
dapr_client = DaprClient()
app.state.dapr_client = dapr_client
```

**MODIFY LLMGateway instantiation:**

```python
# BEFORE:
llm_gateway = LLMGateway(
    settings=settings,
    cost_repository=cost_repository,
    budget_monitor=budget_monitor,
    rate_limiter=rate_limiter,
)

# AFTER:
llm_gateway = LLMGateway(
    settings=settings,
    dapr_client=dapr_client,
    rate_limiter=rate_limiter,
)
```

**MODIFY EmbeddingService instantiation:**

```python
# BEFORE:
embedding_service = EmbeddingService(
    settings=settings,
    cost_repository=embedding_cost_repository,
)

# AFTER:
embedding_service = EmbeddingService(
    settings=settings,
    dapr_client=dapr_client,
)
```

#### 2.5 gRPC Server Changes: `src/ai_model/api/grpc_server.py`

**REMOVE CostService registration:**

```python
# DELETE: These lines
from ai_model.api.cost_service import CostServiceServicer
from farmer_power.ai_model.v1.ai_model_pb2_grpc import add_CostServiceServicer_to_server

# DELETE: In serve() function
cost_servicer = CostServiceServicer(cost_repository, budget_monitor)
add_CostServiceServicer_to_server(cost_servicer, server)
```

#### 2.6 LLM Gateway Changes: `src/ai_model/llm/gateway.py`

**MODIFY `__init__` method:**

```python
# BEFORE:
def __init__(
    self,
    settings: Settings,
    cost_repository: LlmCostEventRepository | None = None,
    budget_monitor: BudgetMonitor | None = None,
    rate_limiter: RateLimiter | None = None,
) -> None:
    self._settings = settings
    self._cost_repository = cost_repository
    self._budget_monitor = budget_monitor
    self._rate_limiter = rate_limiter

# AFTER:
def __init__(
    self,
    settings: Settings,
    dapr_client: DaprClient | None = None,
    rate_limiter: RateLimiter | None = None,
) -> None:
    self._settings = settings
    self._dapr_client = dapr_client
    self._rate_limiter = rate_limiter
```

**REPLACE cost persistence logic (lines ~557-577):**

```python
# DELETE: Lines 557-577
# Persist cost event to MongoDB (AC8)
if self._cost_repository:
    try:
        await self._cost_repository.insert(cost_event)
    except Exception as e:
        logger.warning(
            "Failed to persist cost event",
            event_id=cost_event.id,
            error=str(e),
        )

# Check budget thresholds (AC12)
if self._budget_monitor:
    alert = await self._budget_monitor.record_cost(cost_event)
    if alert:
        logger.warning(
            "Cost threshold alert triggered",
            threshold_type=alert.threshold_type.value,
            threshold_usd=str(alert.threshold_usd),
            current_cost_usd=str(alert.current_cost_usd),
        )

# REPLACE WITH:
# Publish cost event to unified topic (ADR-016)
if self._dapr_client:
    try:
        from fp_common.events.cost_recorded import CostRecordedEvent, CostType, CostUnit

        event = CostRecordedEvent(
            cost_type=CostType.LLM,
            amount_usd=str(cost_event.cost_usd),
            quantity=cost_event.tokens_in + cost_event.tokens_out,
            unit=CostUnit.TOKENS,
            timestamp=cost_event.timestamp,
            source_service="ai-model",
            success=cost_event.success,
            factory_id=cost_event.factory_id,
            request_id=cost_event.request_id,
            metadata={
                "model": cost_event.model,
                "agent_type": cost_event.agent_type,
                "agent_id": cost_event.agent_id,
                "tokens_in": cost_event.tokens_in,
                "tokens_out": cost_event.tokens_out,
                "retry_count": cost_event.retry_count,
            },
        )

        await self._dapr_client.publish_event(
            pubsub_name=self._settings.dapr_pubsub_name,
            topic_name=self._settings.unified_cost_topic,
            data=event.model_dump_json(),
            data_content_type="application/json",
        )

        logger.debug(
            "Published LLM cost event",
            cost_usd=str(cost_event.cost_usd),
            model=cost_event.model,
        )
    except Exception as e:
        logger.warning(
            "Failed to publish cost event",
            error=str(e),
        )
```

**REMOVE imports:**

```python
# DELETE:
from ai_model.infrastructure.repositories.cost_event_repository import LlmCostEventRepository
from ai_model.llm.budget_monitor import BudgetMonitor
```

**ADD imports:**

```python
from dapr.aio.clients import DaprClient
```

#### 2.7 Embedding Service Changes: `src/ai_model/services/embedding_service.py`

**MODIFY `__init__` method:**

```python
# BEFORE:
def __init__(
    self,
    settings: Settings,
    cost_repository: EmbeddingCostEventRepository | None = None,
) -> None:
    self._settings = settings
    self._cost_repository = cost_repository

# AFTER:
def __init__(
    self,
    settings: Settings,
    dapr_client: DaprClient | None = None,
) -> None:
    self._settings = settings
    self._dapr_client = dapr_client
```

**REPLACE `_record_cost_event` method (lines 352-402):**

```python
# DELETE: Entire _record_cost_event method

# REPLACE WITH:
async def _publish_cost_event(
    self,
    request_id: str,
    texts_count: int,
    tokens_total: int,
    knowledge_domain: str | None,
    success: bool,
    batch_count: int,
    retry_count: int,
) -> None:
    """Publish embedding cost event to unified topic (ADR-016)."""
    if self._dapr_client is None:
        logger.debug("DAPR client not configured, skipping cost event")
        return

    from decimal import Decimal
    from fp_common.events.cost_recorded import CostRecordedEvent, CostType, CostUnit

    # Calculate USD cost
    cost_usd = (Decimal(tokens_total) / 1000) * Decimal(
        str(self._settings.embedding_cost_per_1k_tokens)
    )

    try:
        event = CostRecordedEvent(
            cost_type=CostType.EMBEDDING,
            amount_usd=str(cost_usd),
            quantity=tokens_total,
            unit=CostUnit.TOKENS,
            timestamp=datetime.now(UTC),
            source_service="ai-model",
            success=success,
            request_id=request_id,
            metadata={
                "model": self._settings.pinecone_embedding_model,
                "knowledge_domain": knowledge_domain,
                "texts_count": texts_count,
                "batch_count": batch_count,
                "retry_count": retry_count,
            },
        )

        await self._dapr_client.publish_event(
            pubsub_name=self._settings.dapr_pubsub_name,
            topic_name=self._settings.unified_cost_topic,
            data=event.model_dump_json(),
            data_content_type="application/json",
        )

        logger.debug(
            "Published embedding cost event",
            cost_usd=str(cost_usd),
            tokens=tokens_total,
        )
    except Exception as e:
        logger.warning(
            "Failed to publish embedding cost event",
            request_id=request_id,
            error=str(e),
        )
```

**UPDATE method calls:**
- Replace `await self._record_cost_event(...)` with `await self._publish_cost_event(...)`

**REMOVE imports:**

```python
# DELETE:
from ai_model.infrastructure.repositories.embedding_cost_repository import EmbeddingCostEventRepository
```

**ADD imports:**

```python
from datetime import UTC, datetime
from dapr.aio.clients import DaprClient
```

#### 2.8 Azure Document Intelligence Changes: `src/ai_model/infrastructure/azure_doc_intel_client.py`

**MODIFY `__init__` to accept cost callback:**

```python
# BEFORE:
def __init__(self, settings: Settings) -> None:

# AFTER:
from collections.abc import Awaitable, Callable

def __init__(
    self,
    settings: Settings,
    on_cost_event: Callable[[AzureDocIntelCostEvent], Awaitable[None]] | None = None,
) -> None:
    ...
    self._on_cost_event = on_cost_event
```

**ADD cost callback invocation after creating cost_event (after line ~288):**

```python
# After logger.info("Azure DI cost event", ...)

# Invoke cost callback if provided (ADR-016)
if self._on_cost_event:
    try:
        await self._on_cost_event(cost_event)
    except Exception as e:
        logger.warning(
            "Failed to invoke cost event callback",
            error=str(e),
        )
```

**In the caller (wherever AzureDocumentIntelligenceClient is instantiated):**

```python
from fp_common.events.cost_recorded import CostRecordedEvent, CostType, CostUnit

async def publish_document_cost(event: AzureDocIntelCostEvent) -> None:
    """Publish Azure Document Intelligence cost to unified topic."""
    cost_event = CostRecordedEvent(
        cost_type=CostType.DOCUMENT,
        amount_usd=str(event.estimated_cost_usd),
        quantity=event.page_count,
        unit=CostUnit.PAGES,
        timestamp=event.timestamp,
        source_service="ai-model",
        success=event.success,
        metadata={
            "model_id": event.model_id,
            "document_id": event.document_id,
            "job_id": event.job_id,
            "error_message": event.error_message,
        },
    )

    await dapr_client.publish_event(
        pubsub_name=settings.dapr_pubsub_name,
        topic_name=settings.unified_cost_topic,
        data=cost_event.model_dump_json(),
        data_content_type="application/json",
    )

# Instantiate with callback
azure_client = AzureDocumentIntelligenceClient(
    settings=settings,
    on_cost_event=publish_document_cost,
)
```

---

### Part 3: New platform-cost Service

#### 3.1 Service Structure

```
services/platform-cost/
├── src/
│   └── platform_cost/
│       ├── __init__.py
│       ├── main.py                         # FastAPI + DAPR + gRPC
│       ├── config.py                       # Service configuration
│       │
│       ├── domain/
│       │   ├── __init__.py
│       │   └── cost_event.py               # UnifiedCostEvent domain model
│       │
│       ├── infrastructure/
│       │   ├── __init__.py
│       │   └── repositories/
│       │       ├── __init__.py
│       │       └── cost_repository.py      # Unified MongoDB repository
│       │
│       ├── services/
│       │   ├── __init__.py
│       │   └── budget_monitor.py           # Migrated from ai-model + extended
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── grpc_server.py              # gRPC server setup
│       │   └── unified_cost_service.py     # UnifiedCostService implementation
│       │
│       └── handlers/
│           ├── __init__.py
│           └── cost_event_handler.py       # DAPR subscription handler
│
├── tests/
│   └── unit/
│       └── platform_cost/
│           ├── __init__.py
│           ├── test_cost_repository.py
│           ├── test_budget_monitor.py
│           └── test_cost_service.py
│
├── dapr/
│   ├── config.yaml
│   └── subscription.yaml                   # Subscribe to platform.cost.recorded
│
├── Dockerfile
├── pyproject.toml
└── README.md
```

#### 3.2 Proto Definition: `proto/platform_cost/v1/platform_cost.proto`

```protobuf
syntax = "proto3";

package farmer_power.platform_cost.v1;

option python_package = "farmer_power.platform_cost.v1";

// UnifiedCostService provides cost aggregation and reporting
// across all billable services in the platform.
service UnifiedCostService {
  // Get summary of all costs with breakdown by type
  rpc GetCostSummary(CostSummaryRequest) returns (CostSummaryResponse);

  // Get daily cost trend (for stacked area chart)
  rpc GetDailyCostTrend(DailyTrendRequest) returns (DailyTrendResponse);

  // Get current day's running total
  rpc GetCurrentDayCost(CurrentDayCostRequest) returns (CurrentDayCostResponse);

  // === Type-specific breakdowns ===

  // LLM costs by agent type (migrated from ai-model)
  rpc GetLlmCostByAgentType(LlmCostByAgentTypeRequest) returns (LlmCostByAgentTypeResponse);

  // LLM costs by model (migrated from ai-model)
  rpc GetLlmCostByModel(LlmCostByModelRequest) returns (LlmCostByModelResponse);

  // Document costs summary
  rpc GetDocumentCostSummary(DocumentCostRequest) returns (DocumentCostResponse);

  // Embedding costs by knowledge domain
  rpc GetEmbeddingCostByDomain(EmbeddingCostByDomainRequest) returns (EmbeddingCostByDomainResponse);

  // === Budget Management ===

  // Get current budget status and alerts
  rpc GetBudgetStatus(BudgetStatusRequest) returns (BudgetStatusResponse);

  // Configure budget thresholds
  rpc ConfigureBudgetThreshold(ConfigureThresholdRequest) returns (ConfigureThresholdResponse);
}

// === Common Messages ===

message CostSummaryRequest {
  string start_date = 1;  // ISO format YYYY-MM-DD
  string end_date = 2;    // ISO format YYYY-MM-DD
  optional string factory_id = 3;  // Optional factory filter
}

message CostSummaryResponse {
  string total_cost_usd = 1;
  repeated CostTypeBreakdown by_type = 2;
  string period_start = 3;
  string period_end = 4;
  string trend_vs_previous_period = 5;  // e.g., "+8.5%"
  int64 total_requests = 6;
}

message CostTypeBreakdown {
  string cost_type = 1;      // "llm", "document", "embedding", "sms"
  string amount_usd = 2;     // Decimal as string
  int64 quantity = 3;
  string unit = 4;           // "tokens", "pages", "messages"
  double percentage = 5;     // Percentage of total
  int64 request_count = 6;
}

// === Daily Trend ===

message DailyTrendRequest {
  string start_date = 1;
  string end_date = 2;
  optional string factory_id = 3;
}

message DailyTrendResponse {
  repeated DailyCostEntry entries = 1;
  string data_available_from = 2;  // ISO date (YYYY-MM-DD) - earliest date with available data (based on TTL retention)
}

message DailyCostEntry {
  string date = 1;               // YYYY-MM-DD
  string total_cost_usd = 2;
  string llm_cost_usd = 3;
  string document_cost_usd = 4;
  string embedding_cost_usd = 5;
  string sms_cost_usd = 6;
}

// === Current Day ===

message CurrentDayCostRequest {
  optional string factory_id = 1;
}

message CurrentDayCostResponse {
  string date = 1;
  string total_cost_usd = 2;
  repeated CostTypeBreakdown by_type = 3;
  string updated_at = 4;  // ISO timestamp
}

// === LLM-Specific (migrated from ai-model) ===

message LlmCostByAgentTypeRequest {
  string start_date = 1;
  string end_date = 2;
  optional string factory_id = 3;
}

message LlmCostByAgentTypeResponse {
  repeated AgentTypeCostEntry entries = 1;
  string total_cost_usd = 2;
}

message AgentTypeCostEntry {
  string agent_type = 1;    // "explorer", "generator", "extractor", etc.
  string cost_usd = 2;
  int64 request_count = 3;
  int64 tokens_in = 4;
  int64 tokens_out = 5;
  double percentage = 6;
}

message LlmCostByModelRequest {
  string start_date = 1;
  string end_date = 2;
  optional string factory_id = 3;
}

message LlmCostByModelResponse {
  repeated ModelCostEntry entries = 1;
  string total_cost_usd = 2;
}

message ModelCostEntry {
  string model = 1;          // "anthropic/claude-3-5-sonnet", etc.
  string cost_usd = 2;
  int64 request_count = 3;
  int64 tokens_in = 4;
  int64 tokens_out = 5;
  double percentage = 6;
}

// === Document-Specific ===

message DocumentCostRequest {
  string start_date = 1;
  string end_date = 2;
}

message DocumentCostResponse {
  string total_cost_usd = 1;
  int64 total_pages = 2;
  int64 total_documents = 3;
  string average_cost_per_document = 4;
}

// === Embedding-Specific ===

message EmbeddingCostByDomainRequest {
  string start_date = 1;
  string end_date = 2;
}

message EmbeddingCostByDomainResponse {
  repeated DomainCostEntry entries = 1;
  string total_cost_usd = 2;
}

message DomainCostEntry {
  string knowledge_domain = 1;
  string cost_usd = 2;
  int64 tokens_total = 3;
  int64 texts_count = 4;
}

// === Budget Management ===

message BudgetStatusRequest {}

message BudgetStatusResponse {
  string daily_threshold_usd = 1;
  string monthly_threshold_usd = 2;
  string current_daily_cost_usd = 3;
  string current_monthly_cost_usd = 4;
  bool daily_alert_triggered = 5;
  bool monthly_alert_triggered = 6;
  string daily_remaining_usd = 7;
  string monthly_remaining_usd = 8;
  repeated CostAlert active_alerts = 9;
}

message CostAlert {
  string alert_type = 1;       // "daily_threshold", "monthly_threshold"
  string threshold_usd = 2;
  string current_cost_usd = 3;
  string triggered_at = 4;     // ISO timestamp
}

message ConfigureThresholdRequest {
  optional string daily_threshold_usd = 1;   // Decimal as string, empty to keep current
  optional string monthly_threshold_usd = 2;
}

message ConfigureThresholdResponse {
  string daily_threshold_usd = 1;
  string monthly_threshold_usd = 2;
  string message = 3;
}
```

#### 3.3 Domain Models: `platform_cost/domain/cost_event.py`

```python
"""Domain models for unified cost tracking.

Migrated from ai-model and extended for all cost types.
Includes both storage models and repository response models.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class CostType(str, Enum):
    """Supported cost types."""
    LLM = "llm"
    DOCUMENT = "document"
    EMBEDDING = "embedding"
    SMS = "sms"


# =============================================================================
# Storage Model
# =============================================================================

class UnifiedCostEvent(BaseModel):
    """Unified cost event stored in MongoDB.

    This is the internal storage model. Events are received via DAPR
    subscription and converted to this model for persistence.
    """

    id: str = Field(..., description="Unique event ID")
    cost_type: CostType
    amount_usd: Decimal = Field(..., description="Cost in USD")
    quantity: int = Field(..., ge=0)
    unit: str
    timestamp: datetime
    source_service: str
    success: bool = True
    metadata: dict = Field(default_factory=dict)

    # Indexed fields for efficient querying
    factory_id: str | None = None
    request_id: str | None = None

    # Type-specific indexed fields (extracted from metadata)
    agent_type: str | None = None      # LLM
    model: str | None = None           # LLM, Embedding
    knowledge_domain: str | None = None  # Embedding

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: str,
        }

    @classmethod
    def from_event(cls, event_id: str, event: CostRecordedEvent) -> "UnifiedCostEvent":
        """Create a UnifiedCostEvent from a CostRecordedEvent.

        Extracts indexed fields from metadata for efficient querying:
        - agent_type: from LLM metadata
        - model: from LLM or Embedding metadata
        - knowledge_domain: from Embedding metadata

        Args:
            event_id: Unique identifier for this event (typically UUID)
            event: The CostRecordedEvent from DAPR pub/sub

        Returns:
            UnifiedCostEvent ready for MongoDB storage
        """
        # Extract indexed fields from metadata
        agent_type = event.metadata.get("agent_type") if event.cost_type == CostType.LLM else None
        model = event.metadata.get("model")  # Present in both LLM and Embedding
        knowledge_domain = event.metadata.get("knowledge_domain") if event.cost_type == CostType.EMBEDDING else None

        return cls(
            id=event_id,
            cost_type=event.cost_type if isinstance(event.cost_type, str) else event.cost_type.value,
            amount_usd=event.amount_usd,
            quantity=event.quantity,
            unit=event.unit if isinstance(event.unit, str) else event.unit.value,
            timestamp=event.timestamp,
            source_service=event.source_service,
            success=event.success,
            metadata=event.metadata,
            factory_id=event.factory_id,
            request_id=event.request_id,
            agent_type=agent_type,
            model=model,
            knowledge_domain=knowledge_domain,
        )


# =============================================================================
# Repository Response Models (Type-safe return types)
# =============================================================================

class CostTypeSummary(BaseModel):
    """Summary for a single cost type (used in breakdown responses)."""
    cost_type: CostType
    total_cost_usd: Decimal
    total_quantity: int
    request_count: int
    unit: str = ""
    percentage: float = 0.0


class DailyCostEntry(BaseModel):
    """Single day's cost breakdown (for stacked area chart)."""
    date: date
    total_cost_usd: Decimal
    llm_cost_usd: Decimal = Decimal("0")
    document_cost_usd: Decimal = Decimal("0")
    embedding_cost_usd: Decimal = Decimal("0")
    sms_cost_usd: Decimal = Decimal("0")


class CurrentDayCost(BaseModel):
    """Current day's running total."""
    date: date
    total_cost_usd: Decimal
    by_type: list[CostTypeSummary]
    updated_at: datetime


class AgentTypeCost(BaseModel):
    """LLM cost breakdown by agent type."""
    agent_type: str
    cost_usd: Decimal
    request_count: int
    tokens_in: int
    tokens_out: int
    percentage: float = 0.0


class ModelCost(BaseModel):
    """LLM cost breakdown by model."""
    model: str
    cost_usd: Decimal
    request_count: int
    tokens_in: int
    tokens_out: int
    percentage: float = 0.0


class DomainCost(BaseModel):
    """Embedding cost breakdown by knowledge domain."""
    knowledge_domain: str
    cost_usd: Decimal
    tokens_total: int
    texts_count: int
    percentage: float = 0.0


class DocumentCostSummary(BaseModel):
    """Document processing cost summary."""
    total_cost_usd: Decimal
    total_pages: int
    total_documents: int
    average_cost_per_document: Decimal
```

#### 3.4 Repository: `platform_cost/infrastructure/repositories/cost_repository.py`

```python
"""Unified cost repository for all cost types.

Migrated from ai-model LlmCostEventRepository and extended.
Returns typed Pydantic models instead of raw dicts for type safety.
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase
from platform_cost.domain.cost_event import (
    AgentTypeCost,
    CostType,
    CostTypeSummary,
    CurrentDayCost,
    DailyCostEntry,
    ModelCost,
    UnifiedCostEvent,
)

logger = structlog.get_logger(__name__)


class UnifiedCostRepository:
    """Repository for all cost types in a single collection.

    All query methods return typed Pydantic models for type safety
    and IDE autocompletion support.
    """

    COLLECTION = "cost_events"

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        retention_days: int = 90,
    ) -> None:
        self._db = db
        self._collection = db[self.COLLECTION]
        self._retention_days = retention_days

    @property
    def data_available_from(self) -> date:
        """Earliest date for which data may exist (based on TTL retention)."""
        if self._retention_days <= 0:
            # No TTL - data available from beginning of time (use a reasonable default)
            return date(2024, 1, 1)
        return datetime.now(UTC).date() - timedelta(days=self._retention_days)

    async def ensure_indexes(self) -> None:
        """Create indexes for efficient queries."""
        indexes = [
            # Primary query patterns
            ([("timestamp", -1)], {"name": "idx_timestamp"}),
            ([("cost_type", 1)], {"name": "idx_cost_type"}),
            ([("cost_type", 1), ("timestamp", -1)], {"name": "idx_cost_type_timestamp"}),

            # Factory attribution
            ([("factory_id", 1)], {"name": "idx_factory_id", "sparse": True}),

            # LLM-specific
            ([("agent_type", 1)], {"name": "idx_agent_type", "sparse": True}),
            ([("model", 1)], {"name": "idx_model", "sparse": True}),
            ([("cost_type", 1), ("agent_type", 1), ("timestamp", -1)],
             {"name": "idx_llm_agent_type", "sparse": True}),
            ([("cost_type", 1), ("model", 1), ("timestamp", -1)],
             {"name": "idx_llm_model", "sparse": True}),

            # Embedding-specific
            ([("knowledge_domain", 1)], {"name": "idx_knowledge_domain", "sparse": True}),

            # Tracing
            ([("request_id", 1)], {"name": "idx_request_id", "sparse": True}),
        ]

        for keys, options in indexes:
            await self._collection.create_index(keys, **options)

        # TTL index for automatic data retention (if enabled)
        if self._retention_days > 0:
            await self._collection.create_index(
                [("timestamp", 1)],
                expireAfterSeconds=self._retention_days * 86400,  # days to seconds
                name="idx_ttl",
            )
            logger.info(
                "TTL index created",
                retention_days=self._retention_days,
                collection=self.COLLECTION,
            )

        logger.info("Cost repository indexes ensured", collection=self.COLLECTION)

    async def insert(self, event: UnifiedCostEvent) -> None:
        """Insert a cost event."""
        doc = event.model_dump()
        doc["amount_usd"] = str(event.amount_usd)  # Store as string for precision
        await self._collection.insert_one(doc)

    async def get_summary_by_type(
        self,
        start_date: date,
        end_date: date,
        factory_id: str | None = None,
    ) -> list[CostTypeSummary]:
        """Get cost breakdown by type for date range.

        Returns:
            List of CostTypeSummary models sorted by cost descending.
        """
        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
        end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=UTC)

        match_stage: dict = {"timestamp": {"$gte": start_dt, "$lt": end_dt}}
        if factory_id:
            match_stage["factory_id"] = factory_id

        pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": "$cost_type",
                "total_cost_usd": {"$sum": {"$toDecimal": "$amount_usd"}},
                "total_quantity": {"$sum": "$quantity"},
                "request_count": {"$sum": 1},
            }},
            {"$sort": {"total_cost_usd": -1}},
        ]

        results: list[CostTypeSummary] = []
        total_cost = Decimal("0")

        # First pass: collect results and calculate total
        raw_results = []
        async for doc in self._collection.aggregate(pipeline):
            cost = Decimal(str(doc["total_cost_usd"]))
            total_cost += cost
            raw_results.append({
                "cost_type": CostType(doc["_id"]),
                "total_cost_usd": cost,
                "total_quantity": doc["total_quantity"],
                "request_count": doc["request_count"],
            })

        # Second pass: calculate percentages and create models
        for raw in raw_results:
            percentage = float(raw["total_cost_usd"] / total_cost * 100) if total_cost > 0 else 0.0
            results.append(CostTypeSummary(
                cost_type=raw["cost_type"],
                total_cost_usd=raw["total_cost_usd"],
                total_quantity=raw["total_quantity"],
                request_count=raw["request_count"],
                percentage=round(percentage, 2),
            ))

        return results

    async def get_daily_trend(
        self,
        start_date: date,
        end_date: date,
        factory_id: str | None = None,
    ) -> list[DailyCostEntry]:
        """Get daily costs broken down by type (for stacked chart).

        Returns:
            List of DailyCostEntry models sorted by date ascending.
        """
        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
        end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=UTC)

        match_stage: dict = {"timestamp": {"$gte": start_dt, "$lt": end_dt}}
        if factory_id:
            match_stage["factory_id"] = factory_id

        pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": {
                    "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                    "cost_type": "$cost_type",
                },
                "total_cost_usd": {"$sum": {"$toDecimal": "$amount_usd"}},
            }},
            {"$sort": {"_id.date": 1}},
        ]

        # Pivot results by date
        daily_data: dict[str, DailyCostEntry] = {}
        async for doc in self._collection.aggregate(pipeline):
            date_str = doc["_id"]["date"]
            cost_type = doc["_id"]["cost_type"]
            cost = Decimal(str(doc["total_cost_usd"]))

            if date_str not in daily_data:
                daily_data[date_str] = DailyCostEntry(
                    date=date.fromisoformat(date_str),
                    total_cost_usd=Decimal("0"),
                )

            # Update total and type-specific cost
            daily_data[date_str].total_cost_usd += cost

            if cost_type == CostType.LLM.value:
                daily_data[date_str].llm_cost_usd = cost
            elif cost_type == CostType.DOCUMENT.value:
                daily_data[date_str].document_cost_usd = cost
            elif cost_type == CostType.EMBEDDING.value:
                daily_data[date_str].embedding_cost_usd = cost
            elif cost_type == CostType.SMS.value:
                daily_data[date_str].sms_cost_usd = cost

        return list(daily_data.values())

    async def get_current_day_cost(
        self,
        factory_id: str | None = None,
    ) -> CurrentDayCost:
        """Get running total for current day.

        Returns:
            CurrentDayCost model with breakdown by type.
        """
        today = datetime.now(UTC).date()
        start_dt = datetime.combine(today, datetime.min.time(), tzinfo=UTC)

        match_stage: dict = {"timestamp": {"$gte": start_dt}}
        if factory_id:
            match_stage["factory_id"] = factory_id

        pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": "$cost_type",
                "total_cost_usd": {"$sum": {"$toDecimal": "$amount_usd"}},
                "total_quantity": {"$sum": "$quantity"},
                "request_count": {"$sum": 1},
            }},
        ]

        by_type: list[CostTypeSummary] = []
        total_cost = Decimal("0")

        async for doc in self._collection.aggregate(pipeline):
            cost = Decimal(str(doc["total_cost_usd"]))
            total_cost += cost
            by_type.append(CostTypeSummary(
                cost_type=CostType(doc["_id"]),
                total_cost_usd=cost,
                total_quantity=doc["total_quantity"],
                request_count=doc["request_count"],
            ))

        # Calculate percentages
        for entry in by_type:
            if total_cost > 0:
                entry.percentage = round(float(entry.total_cost_usd / total_cost * 100), 2)

        return CurrentDayCost(
            date=today,
            total_cost_usd=total_cost,
            by_type=by_type,
            updated_at=datetime.now(UTC),
        )

    async def get_current_month_cost(self) -> Decimal:
        """Get running total for current month (for budget monitoring).

        Returns:
            Total cost for current month as Decimal.
        """
        now = datetime.now(UTC)
        start_of_month = datetime(now.year, now.month, 1, tzinfo=UTC)

        pipeline = [
            {"$match": {"timestamp": {"$gte": start_of_month}}},
            {"$group": {
                "_id": None,
                "total_cost_usd": {"$sum": {"$toDecimal": "$amount_usd"}},
            }},
        ]

        async for doc in self._collection.aggregate(pipeline):
            return Decimal(str(doc["total_cost_usd"]))

        return Decimal("0")

    # === LLM-Specific Queries (migrated from ai-model) ===

    async def get_llm_cost_by_agent_type(
        self,
        start_date: date,
        end_date: date,
        factory_id: str | None = None,
    ) -> list[AgentTypeCost]:
        """Get LLM costs grouped by agent type.

        Returns:
            List of AgentTypeCost models sorted by cost descending.
        """
        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
        end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=UTC)

        match_stage: dict = {
            "timestamp": {"$gte": start_dt, "$lt": end_dt},
            "cost_type": CostType.LLM.value,
        }
        if factory_id:
            match_stage["factory_id"] = factory_id

        pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": "$agent_type",
                "total_cost_usd": {"$sum": {"$toDecimal": "$amount_usd"}},
                "request_count": {"$sum": 1},
                "tokens_in": {"$sum": {"$ifNull": ["$metadata.tokens_in", 0]}},
                "tokens_out": {"$sum": {"$ifNull": ["$metadata.tokens_out", 0]}},
            }},
            {"$sort": {"total_cost_usd": -1}},
        ]

        results: list[AgentTypeCost] = []
        total_cost = Decimal("0")

        # First pass: collect and sum
        raw_results = []
        async for doc in self._collection.aggregate(pipeline):
            cost = Decimal(str(doc["total_cost_usd"]))
            total_cost += cost
            raw_results.append({
                "agent_type": doc["_id"] or "unknown",
                "cost_usd": cost,
                "request_count": doc["request_count"],
                "tokens_in": doc["tokens_in"],
                "tokens_out": doc["tokens_out"],
            })

        # Second pass: create models with percentages
        for raw in raw_results:
            percentage = float(raw["cost_usd"] / total_cost * 100) if total_cost > 0 else 0.0
            results.append(AgentTypeCost(
                agent_type=raw["agent_type"],
                cost_usd=raw["cost_usd"],
                request_count=raw["request_count"],
                tokens_in=raw["tokens_in"],
                tokens_out=raw["tokens_out"],
                percentage=round(percentage, 2),
            ))

        return results

    async def get_llm_cost_by_model(
        self,
        start_date: date,
        end_date: date,
        factory_id: str | None = None,
    ) -> list[ModelCost]:
        """Get LLM costs grouped by model.

        Returns:
            List of ModelCost models sorted by cost descending.
        """
        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
        end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=UTC)

        match_stage: dict = {
            "timestamp": {"$gte": start_dt, "$lt": end_dt},
            "cost_type": CostType.LLM.value,
        }
        if factory_id:
            match_stage["factory_id"] = factory_id

        pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": "$model",
                "total_cost_usd": {"$sum": {"$toDecimal": "$amount_usd"}},
                "request_count": {"$sum": 1},
                "tokens_in": {"$sum": {"$ifNull": ["$metadata.tokens_in", 0]}},
                "tokens_out": {"$sum": {"$ifNull": ["$metadata.tokens_out", 0]}},
            }},
            {"$sort": {"total_cost_usd": -1}},
        ]

        results: list[ModelCost] = []
        total_cost = Decimal("0")

        # First pass: collect and sum
        raw_results = []
        async for doc in self._collection.aggregate(pipeline):
            cost = Decimal(str(doc["total_cost_usd"]))
            total_cost += cost
            raw_results.append({
                "model": doc["_id"] or "unknown",
                "cost_usd": cost,
                "request_count": doc["request_count"],
                "tokens_in": doc["tokens_in"],
                "tokens_out": doc["tokens_out"],
            })

        # Second pass: create models with percentages
        for raw in raw_results:
            percentage = float(raw["cost_usd"] / total_cost * 100) if total_cost > 0 else 0.0
            results.append(ModelCost(
                model=raw["model"],
                cost_usd=raw["cost_usd"],
                request_count=raw["request_count"],
                tokens_in=raw["tokens_in"],
                tokens_out=raw["tokens_out"],
                percentage=round(percentage, 2),
            ))

        return results
```

#### 3.5 Budget Monitor: `platform_cost/services/budget_monitor.py`

```python
"""Budget monitoring service for all cost types.

Migrated from ai-model and extended for unified cost tracking.
Exposes OpenTelemetry metrics for alerting via OTEL backend (Grafana/Prometheus).
"""

from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum

import structlog
from opentelemetry import metrics
from platform_cost.domain.cost_event import CostType, UnifiedCostEvent
from pydantic import BaseModel

logger = structlog.get_logger(__name__)
meter = metrics.get_meter("platform_cost")


class ThresholdType(str, Enum):
    DAILY = "daily"
    MONTHLY = "monthly"


class BudgetStatus(BaseModel):
    """Current budget status for gRPC response."""
    daily_threshold_usd: Decimal
    monthly_threshold_usd: Decimal
    current_daily_cost_usd: Decimal
    current_monthly_cost_usd: Decimal
    daily_alert_triggered: bool
    monthly_alert_triggered: bool
    daily_remaining_usd: Decimal
    monthly_remaining_usd: Decimal


class BudgetMonitor:
    """Monitors costs against configurable thresholds.

    Tracks running totals and exposes OpenTelemetry metrics for alerting.
    Alerting is handled by the OTEL backend (Grafana/Prometheus), NOT via
    pub/sub events. This allows flexible, infrastructure-as-code alerting.

    OpenTelemetry Metrics Exposed:
        - platform_cost_daily_total_usd: Running daily cost (gauge)
        - platform_cost_monthly_total_usd: Running monthly cost (gauge)
        - platform_cost_daily_threshold_usd: Configured daily threshold (gauge)
        - platform_cost_monthly_threshold_usd: Configured monthly threshold (gauge)
        - platform_cost_daily_utilization_percent: Daily cost as % of threshold (gauge)
        - platform_cost_monthly_utilization_percent: Monthly cost as % of threshold (gauge)
        - platform_cost_by_type_usd: Cost breakdown by type (gauge with labels)
        - platform_cost_events_total: Total cost events processed (counter)
    """

    def __init__(
        self,
        daily_threshold_usd: Decimal = Decimal("0"),
        monthly_threshold_usd: Decimal = Decimal("0"),
    ) -> None:
        self._daily_threshold = daily_threshold_usd
        self._monthly_threshold = monthly_threshold_usd

        # Running totals
        self._daily_total = Decimal("0")
        self._monthly_total = Decimal("0")
        self._daily_by_type: dict[CostType, Decimal] = {}
        self._last_daily_reset = datetime.now(UTC).date()
        self._last_monthly_reset = (datetime.now(UTC).year, datetime.now(UTC).month)

        # Alert state (for gRPC status response)
        self._daily_alert_triggered = False
        self._monthly_alert_triggered = False

        # =====================================================================
        # OpenTelemetry Metrics (for Grafana/Prometheus alerting)
        # =====================================================================

        # Cost totals (gauges)
        self._daily_cost_gauge = meter.create_observable_gauge(
            name="platform_cost_daily_total_usd",
            description="Running daily cost across all services in USD",
            callbacks=[lambda options: [(float(self._daily_total), {})]],
            unit="usd",
        )
        self._monthly_cost_gauge = meter.create_observable_gauge(
            name="platform_cost_monthly_total_usd",
            description="Running monthly cost across all services in USD",
            callbacks=[lambda options: [(float(self._monthly_total), {})]],
            unit="usd",
        )

        # Thresholds (gauges - for dashboard display)
        self._daily_threshold_gauge = meter.create_observable_gauge(
            name="platform_cost_daily_threshold_usd",
            description="Configured daily cost threshold in USD",
            callbacks=[lambda options: [(float(self._daily_threshold), {})]],
            unit="usd",
        )
        self._monthly_threshold_gauge = meter.create_observable_gauge(
            name="platform_cost_monthly_threshold_usd",
            description="Configured monthly cost threshold in USD",
            callbacks=[lambda options: [(float(self._monthly_threshold), {})]],
            unit="usd",
        )

        # Utilization percentages (for threshold-based alerting)
        self._daily_utilization_gauge = meter.create_observable_gauge(
            name="platform_cost_daily_utilization_percent",
            description="Daily cost as percentage of threshold (100 = at threshold)",
            callbacks=[lambda options: [(self._calculate_daily_utilization(), {})]],
            unit="percent",
        )
        self._monthly_utilization_gauge = meter.create_observable_gauge(
            name="platform_cost_monthly_utilization_percent",
            description="Monthly cost as percentage of threshold (100 = at threshold)",
            callbacks=[lambda options: [(self._calculate_monthly_utilization(), {})]],
            unit="percent",
        )

        # Cost by type (for breakdown dashboards)
        self._cost_by_type_gauge = meter.create_observable_gauge(
            name="platform_cost_by_type_usd",
            description="Daily cost breakdown by cost type",
            callbacks=[self._get_cost_by_type_metrics],
            unit="usd",
        )

        # Event counter
        self._events_counter = meter.create_counter(
            name="platform_cost_events_total",
            description="Total number of cost events processed",
            unit="events",
        )

    def _calculate_daily_utilization(self) -> float:
        """Calculate daily cost as percentage of threshold."""
        if self._daily_threshold <= 0:
            return 0.0
        return float(self._daily_total / self._daily_threshold * 100)

    def _calculate_monthly_utilization(self) -> float:
        """Calculate monthly cost as percentage of threshold."""
        if self._monthly_threshold <= 0:
            return 0.0
        return float(self._monthly_total / self._monthly_threshold * 100)

    def _get_cost_by_type_metrics(self, options) -> list[tuple[float, dict]]:
        """Return cost breakdown by type for OTEL gauge."""
        return [
            (float(cost), {"cost_type": cost_type.value})
            for cost_type, cost in self._daily_by_type.items()
        ]

    def _check_reset(self) -> None:
        """Reset totals if day/month has changed."""
        now = datetime.now(UTC)
        today = now.date()
        current_month = (now.year, now.month)

        if today != self._last_daily_reset:
            self._daily_total = Decimal("0")
            self._daily_by_type = {}
            self._daily_alert_triggered = False
            self._last_daily_reset = today
            logger.info("Daily cost total reset")

        if current_month != self._last_monthly_reset:
            self._monthly_total = Decimal("0")
            self._monthly_alert_triggered = False
            self._last_monthly_reset = current_month
            logger.info("Monthly cost total reset")

    async def record_cost(self, event: UnifiedCostEvent) -> None:
        """Record a cost event and update metrics.

        Note: Alerting is handled by OTEL backend (Grafana/Prometheus),
        not by returning alert objects. The metrics exposed above can be
        used to configure alert rules in the observability stack.
        """
        self._check_reset()

        # Update totals
        self._daily_total += event.amount_usd
        self._monthly_total += event.amount_usd

        # Update by-type breakdown
        if event.cost_type not in self._daily_by_type:
            self._daily_by_type[event.cost_type] = Decimal("0")
        self._daily_by_type[event.cost_type] += event.amount_usd

        # Increment event counter
        self._events_counter.add(1, {"cost_type": event.cost_type.value})

        # Update alert state (for gRPC status, not for pub/sub)
        if (
            self._daily_threshold > 0
            and not self._daily_alert_triggered
            and self._daily_total >= self._daily_threshold
        ):
            self._daily_alert_triggered = True
            logger.warning(
                "Daily cost threshold exceeded",
                threshold_usd=str(self._daily_threshold),
                current_usd=str(self._daily_total),
            )

        if (
            self._monthly_threshold > 0
            and not self._monthly_alert_triggered
            and self._monthly_total >= self._monthly_threshold
        ):
            self._monthly_alert_triggered = True
            logger.warning(
                "Monthly cost threshold exceeded",
                threshold_usd=str(self._monthly_threshold),
                current_usd=str(self._monthly_total),
            )

    def get_status(self) -> BudgetStatus:
        """Get current budget status for gRPC response."""
        self._check_reset()

        return BudgetStatus(
            daily_threshold_usd=self._daily_threshold,
            monthly_threshold_usd=self._monthly_threshold,
            current_daily_cost_usd=self._daily_total,
            current_monthly_cost_usd=self._monthly_total,
            daily_alert_triggered=self._daily_alert_triggered,
            monthly_alert_triggered=self._monthly_alert_triggered,
            daily_remaining_usd=max(Decimal("0"), self._daily_threshold - self._daily_total),
            monthly_remaining_usd=max(Decimal("0"), self._monthly_threshold - self._monthly_total),
        )

    async def warm_up_from_repository(
        self,
        repository: "UnifiedCostRepository",
    ) -> None:
        """Re-calculate running totals from MongoDB on startup.

        CRITICAL: This method MUST be called during service startup to ensure
        accurate metrics after a restart. Without this, a mid-day restart would
        reset totals to zero, causing missed budget alerts.

        Args:
            repository: The cost repository to query for current totals.

        Raises:
            Exception: If MongoDB query fails. Caller should fail startup.
        """
        from platform_cost.domain.cost_event import CostType

        # Get current day totals (includes breakdown by type)
        current_day = await repository.get_current_day_cost()
        self._daily_total = current_day.total_cost_usd

        # Rebuild by-type breakdown
        for type_summary in current_day.by_type:
            self._daily_by_type[type_summary.cost_type] = type_summary.total_cost_usd

        # Get current month total
        self._monthly_total = await repository.get_current_month_cost()

        # Check if we should already be in alert state
        if self._daily_threshold > 0 and self._daily_total >= self._daily_threshold:
            self._daily_alert_triggered = True
        if self._monthly_threshold > 0 and self._monthly_total >= self._monthly_threshold:
            self._monthly_alert_triggered = True

        logger.info(
            "BudgetMonitor warmed up from repository",
            daily_total_usd=str(self._daily_total),
            monthly_total_usd=str(self._monthly_total),
            daily_alert_triggered=self._daily_alert_triggered,
            monthly_alert_triggered=self._monthly_alert_triggered,
        )

    def update_thresholds(
        self,
        daily_threshold_usd: Decimal | None = None,
        monthly_threshold_usd: Decimal | None = None,
    ) -> None:
        """Update threshold configuration."""
        if daily_threshold_usd is not None:
            self._daily_threshold = daily_threshold_usd
            if self._daily_total < self._daily_threshold:
                self._daily_alert_triggered = False

        if monthly_threshold_usd is not None:
            self._monthly_threshold = monthly_threshold_usd
            if self._monthly_total < self._monthly_threshold:
                self._monthly_alert_triggered = False

        logger.info(
            "Budget thresholds updated",
            daily=str(self._daily_threshold),
            monthly=str(self._monthly_threshold),
        )
```

#### 3.5.1 Recommended Prometheus Alert Rules

Configure these alerts in your Grafana/Prometheus stack:

```yaml
# prometheus-alerts.yaml
groups:
  - name: platform-cost-alerts
    rules:
      # Alert when daily cost reaches 80% of threshold
      - alert: PlatformCostDailyWarning
        expr: platform_cost_daily_utilization_percent > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Daily cost approaching threshold"
          description: "Platform daily cost is at {{ $value }}% of threshold"

      # Alert when daily cost exceeds threshold
      - alert: PlatformCostDailyExceeded
        expr: platform_cost_daily_utilization_percent >= 100
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Daily cost threshold exceeded"
          description: "Platform daily cost has exceeded the configured threshold"

      # Alert when monthly cost reaches 80% of threshold
      - alert: PlatformCostMonthlyWarning
        expr: platform_cost_monthly_utilization_percent > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Monthly cost approaching threshold"
          description: "Platform monthly cost is at {{ $value }}% of threshold"

      # Alert when monthly cost exceeds threshold
      - alert: PlatformCostMonthlyExceeded
        expr: platform_cost_monthly_utilization_percent >= 100
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Monthly cost threshold exceeded"
          description: "Platform monthly cost has exceeded the configured threshold"

      # Alert on cost spike (daily cost increased >50% in 1 hour)
      - alert: PlatformCostSpike
        expr: |
          (platform_cost_daily_total_usd - platform_cost_daily_total_usd offset 1h)
          / platform_cost_daily_total_usd offset 1h > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Unusual cost spike detected"
          description: "Platform cost increased by >50% in the last hour"
```

#### 3.5.2 Budget Alert Latency SLA

**Expected Latency:** 30 seconds to 2 minutes between threshold breach and alert firing.

**Latency Breakdown:**

| Stage | Typical Latency |
|-------|-----------------|
| ai-model → DAPR pub/sub → platform-cost | 10-50ms |
| MongoDB persistence + BudgetMonitor update | 5-20ms |
| Prometheus scrape interval | 15-60s (configurable) |
| Alert rule evaluation interval | 15-60s (configurable) |
| **Total** | **30s - 2m** |

**Implications:**

- High-velocity batch operations (e.g., 100 LLM calls in 30s) may exceed threshold by 50-100% before alert fires
- This is **accepted behavior** for this architecture

**Recommendations:**

1. **Set thresholds with 10-20% safety buffer** - If your hard limit is $100/day, set threshold at $80-90
2. **For tighter control:** Reduce Prometheus scrape interval to 5-10 seconds (increases monitoring load)
3. **For critical environments:** Consider rate limiting at the source (ai-model) rather than relying solely on alerts

**Decision:** Alert latency of 30s-2m is acceptable for Farmer Power Platform. Threshold buffers provide adequate protection for expected usage patterns.

#### 3.5.3 Grafana Dashboard Metrics

| Metric | Type | Description | Use Case |
|--------|------|-------------|----------|
| `platform_cost_daily_total_usd` | Gauge | Running daily cost | Time series chart |
| `platform_cost_monthly_total_usd` | Gauge | Running monthly cost | Stat panel |
| `platform_cost_daily_threshold_usd` | Gauge | Daily threshold | Threshold line on chart |
| `platform_cost_daily_utilization_percent` | Gauge | % of daily threshold | Gauge panel, alerting |
| `platform_cost_monthly_utilization_percent` | Gauge | % of monthly threshold | Gauge panel, alerting |
| `platform_cost_by_type_usd{cost_type="llm\|document\|..."}` | Gauge | Cost by type | Pie chart, stacked chart |
| `platform_cost_events_total{cost_type="..."}` | Counter | Events processed | Rate chart |

#### 3.6 Threshold Configuration

Thresholds are managed through a layered configuration approach:

**1. Default Values (Service Configuration)**

`platform_cost/config.py`:
```python
"""Service configuration using Pydantic Settings."""

from decimal import Decimal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Platform Cost service configuration."""

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

    # DAPR configuration
    dapr_host: str = "localhost"
    dapr_http_port: int = 3500
    dapr_grpc_port: int = 50001
    dapr_pubsub_name: str = "pubsub"

    # OpenTelemetry configuration
    otel_enabled: bool = True
    otel_exporter_endpoint: str = "http://localhost:4317"
    otel_service_namespace: str = "farmer-power"

    # ========================================
    # Budget Threshold Defaults
    # ========================================
    # These are default values. Runtime updates via gRPC are persisted
    # to MongoDB and take precedence over these defaults.

    # Daily cost threshold in USD (0 = disabled)
    budget_daily_threshold_usd: float = 10.0

    # Monthly cost threshold in USD (0 = disabled)
    budget_monthly_threshold_usd: float = 100.0

    # DAPR topic for cost events (subscribes to this topic)
    cost_event_topic: str = "platform.cost.recorded"

    # ========================================
    # Data Retention (TTL)
    # ========================================
    # Cost events older than this are automatically deleted by MongoDB TTL index.
    # Set to 0 to disable TTL (keep data forever).
    # Note: Queries for dates beyond retention window will return empty results.
    cost_event_retention_days: int = 90


settings = Settings()
```

**2. Threshold Persistence (MongoDB)**

`platform_cost/infrastructure/repositories/threshold_repository.py`:
```python
"""Repository for persisting budget threshold configuration.

Thresholds are stored as a single document with _id="budget_thresholds".
This allows runtime updates via gRPC to survive service restarts.
"""

from decimal import Decimal
from datetime import datetime, UTC

import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class ThresholdConfig(BaseModel):
    """Budget threshold configuration document."""
    daily_threshold_usd: Decimal
    monthly_threshold_usd: Decimal
    updated_at: datetime
    updated_by: str = "system"  # "system" for defaults, "admin" for gRPC updates


class ThresholdRepository:
    """Repository for budget threshold configuration."""

    COLLECTION = "budget_config"
    DOC_ID = "budget_thresholds"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db
        self._collection = db[self.COLLECTION]

    async def get_thresholds(self) -> ThresholdConfig | None:
        """Get current threshold configuration.

        Returns:
            ThresholdConfig if exists, None otherwise.
        """
        doc = await self._collection.find_one({"_id": self.DOC_ID})
        if doc:
            return ThresholdConfig(
                daily_threshold_usd=Decimal(str(doc["daily_threshold_usd"])),
                monthly_threshold_usd=Decimal(str(doc["monthly_threshold_usd"])),
                updated_at=doc["updated_at"],
                updated_by=doc.get("updated_by", "system"),
            )
        return None

    async def set_thresholds(
        self,
        daily_threshold_usd: Decimal | None = None,
        monthly_threshold_usd: Decimal | None = None,
        updated_by: str = "admin",
    ) -> ThresholdConfig:
        """Update threshold configuration.

        Args:
            daily_threshold_usd: New daily threshold (None to keep current).
            monthly_threshold_usd: New monthly threshold (None to keep current).
            updated_by: Who made the update (for audit trail).

        Returns:
            Updated ThresholdConfig.
        """
        # Get current values
        current = await self.get_thresholds()
        if current:
            daily = daily_threshold_usd if daily_threshold_usd is not None else current.daily_threshold_usd
            monthly = monthly_threshold_usd if monthly_threshold_usd is not None else current.monthly_threshold_usd
        else:
            daily = daily_threshold_usd or Decimal("0")
            monthly = monthly_threshold_usd or Decimal("0")

        # Upsert
        now = datetime.now(UTC)
        await self._collection.update_one(
            {"_id": self.DOC_ID},
            {"$set": {
                "daily_threshold_usd": str(daily),
                "monthly_threshold_usd": str(monthly),
                "updated_at": now,
                "updated_by": updated_by,
            }},
            upsert=True,
        )

        logger.info(
            "Budget thresholds updated",
            daily_usd=str(daily),
            monthly_usd=str(monthly),
            updated_by=updated_by,
        )

        return ThresholdConfig(
            daily_threshold_usd=daily,
            monthly_threshold_usd=monthly,
            updated_at=now,
            updated_by=updated_by,
        )
```

**3. Service Startup (main.py)**

```python
# In lifespan startup:

# Initialize threshold repository
threshold_repo = ThresholdRepository(db)

# Load thresholds: MongoDB first, then fall back to config defaults
saved_thresholds = await threshold_repo.get_thresholds()
if saved_thresholds:
    daily_threshold = saved_thresholds.daily_threshold_usd
    monthly_threshold = saved_thresholds.monthly_threshold_usd
    logger.info(
        "Loaded thresholds from MongoDB",
        daily=str(daily_threshold),
        monthly=str(monthly_threshold),
    )
else:
    daily_threshold = Decimal(str(settings.budget_daily_threshold_usd))
    monthly_threshold = Decimal(str(settings.budget_monthly_threshold_usd))
    logger.info(
        "Using default thresholds from config",
        daily=str(daily_threshold),
        monthly=str(monthly_threshold),
    )

# Initialize budget monitor with loaded thresholds
budget_monitor = BudgetMonitor(
    daily_threshold_usd=daily_threshold,
    monthly_threshold_usd=monthly_threshold,
)

# CRITICAL: Warm up from MongoDB to restore accurate totals after restart
# This blocks startup until complete - health check won't pass with stale data
try:
    await budget_monitor.warm_up_from_repository(cost_repository)
except Exception as e:
    logger.error("Failed to warm up BudgetMonitor - cannot start with inaccurate metrics", error=str(e))
    raise  # Fail startup - better to be down than report wrong alerts
```

**4. gRPC ConfigureBudgetThreshold Implementation**

In `unified_cost_service.py`:
```python
async def ConfigureBudgetThreshold(
    self,
    request: ConfigureThresholdRequest,
    context: grpc.aio.ServicerContext,
) -> ConfigureThresholdResponse:
    """Update budget thresholds via gRPC.

    Updates are persisted to MongoDB and immediately applied to BudgetMonitor.
    """
    daily = Decimal(request.daily_threshold_usd) if request.daily_threshold_usd else None
    monthly = Decimal(request.monthly_threshold_usd) if request.monthly_threshold_usd else None

    # Persist to MongoDB
    updated = await self._threshold_repo.set_thresholds(
        daily_threshold_usd=daily,
        monthly_threshold_usd=monthly,
        updated_by="admin",  # Could extract from auth context
    )

    # Apply to in-memory budget monitor
    self._budget_monitor.update_thresholds(
        daily_threshold_usd=updated.daily_threshold_usd,
        monthly_threshold_usd=updated.monthly_threshold_usd,
    )

    return ConfigureThresholdResponse(
        daily_threshold_usd=str(updated.daily_threshold_usd),
        monthly_threshold_usd=str(updated.monthly_threshold_usd),
        message="Budget thresholds updated successfully",
    )
```

**Configuration Flow Summary**

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Configuration Flow                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. STARTUP                                                         │
│     ┌────────────────┐    exists?    ┌────────────────────────┐    │
│     │ MongoDB        │──────────────▶│ Use MongoDB values     │    │
│     │ budget_config  │      yes      └────────────────────────┘    │
│     └────────────────┘                                              │
│            │ no                                                     │
│            ▼                                                        │
│     ┌────────────────────────────┐                                  │
│     │ Use config.py defaults     │                                  │
│     │ (env vars / .env file)     │                                  │
│     └────────────────────────────┘                                  │
│                                                                     │
│  2. RUNTIME UPDATE                                                  │
│     ┌────────────────────────┐    ┌────────────────────────────┐   │
│     │ Platform Admin UI      │───▶│ gRPC ConfigureBudgetThreshold│  │
│     └────────────────────────┘    └────────────────────────────┘   │
│                                              │                      │
│                                              ▼                      │
│                               ┌──────────────────────────┐          │
│                               │ 1. Persist to MongoDB    │          │
│                               │ 2. Update BudgetMonitor  │          │
│                               │ 3. OTEL metrics update   │          │
│                               └──────────────────────────┘          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Environment Variables**

| Variable | Default | Description |
|----------|---------|-------------|
| `PLATFORM_COST_BUDGET_DAILY_THRESHOLD_USD` | 10.0 | Initial daily threshold |
| `PLATFORM_COST_BUDGET_MONTHLY_THRESHOLD_USD` | 100.0 | Initial monthly threshold |
| `PLATFORM_COST_COST_EVENT_RETENTION_DAYS` | 90 | Days to retain cost events (0 = forever) |

---

#### 3.7 DAPR Subscription Handler: `platform_cost/handlers/cost_event_handler.py`

```python
"""DAPR subscription handler for cost events.

Receives cost events from all services via pub/sub and persists them.
Alerting is handled via OTEL metrics, NOT via pub/sub events.
"""

import structlog
from dapr.clients.grpc._response import TopicEventResponse
from platform_cost.domain.cost_event import UnifiedCostEvent
from platform_cost.infrastructure.repositories.cost_repository import UnifiedCostRepository
from platform_cost.services.budget_monitor import BudgetMonitor

logger = structlog.get_logger(__name__)


class CostEventHandler:
    """Handler for incoming cost events via DAPR subscription.

    Responsibilities:
    1. Receive cost events from DAPR pub/sub
    2. Persist to MongoDB for querying
    3. Update BudgetMonitor (which exposes OTEL metrics for alerting)

    Note: Alerting is NOT done via pub/sub events. The BudgetMonitor
    exposes OpenTelemetry metrics that Prometheus/Grafana use for
    alerting rules. See section 3.5.1 for alert rule configuration.
    """

    def __init__(
        self,
        repository: UnifiedCostRepository,
        budget_monitor: BudgetMonitor,
    ) -> None:
        self._repository = repository
        self._budget_monitor = budget_monitor

    async def handle(self, message) -> TopicEventResponse:
        """Handle incoming cost event.

        Args:
            message: DAPR message with cost event data.

        Returns:
            TopicEventResponse indicating success, retry, or drop.
        """
        try:
            data = message.data()

            # Parse event
            event = UnifiedCostEvent.from_event(data)

            logger.info(
                "Received cost event",
                cost_type=event.cost_type.value,
                amount_usd=str(event.amount_usd),
                source=event.source_service,
            )

            # Persist to MongoDB
            await self._repository.insert(event)

            # Update budget monitor (updates OTEL metrics for Prometheus alerting)
            await self._budget_monitor.record_cost(event)

            return TopicEventResponse("success")

        except KeyError as e:
            logger.error("Invalid cost event - missing field", field=str(e))
            return TopicEventResponse("drop")  # Don't retry malformed events

        except Exception as e:
            logger.exception("Failed to process cost event", error=str(e))
            return TopicEventResponse("retry")
```

---

### Part 4: Shared Response Models (fp-common)

The platform-cost service has internal domain models in `platform_cost/domain/cost_event.py`.
However, following the established pattern for Collection and Plantation models, the **BFF
must use shared models from fp-common** to avoid direct dependency on service code.

#### New File: `libs/fp-common/fp_common/models/cost.py`

```python
"""Cost domain models for BFF consumption.

These models are returned by the PlatformCostClient to the BFF,
following the same pattern as Farmer, Factory, Document, etc.

The CostRecordedEvent (events/cost_recorded.py) is for PUBLISHING.
These models are for QUERYING via gRPC responses.

Reference:
- Proto definition: proto/platform_cost/v1/platform_cost.proto
- Service models: services/platform-cost/src/platform_cost/domain/cost_event.py
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, PlainSerializer

# Custom type for Decimal that serializes as string to preserve precision
DecimalStr = Annotated[Decimal, PlainSerializer(str, return_type=str)]


class CostType(str, Enum):
    """Cost type enum (mirrors events/cost_recorded.py)."""

    LLM = "llm"
    DOCUMENT = "document"
    EMBEDDING = "embedding"
    SMS = "sms"


class CostTypeSummary(BaseModel):
    """Summary for a single cost type in breakdown responses.

    Maps to: CostTypeBreakdown proto message.
    """

    cost_type: CostType
    amount_usd: DecimalStr
    quantity: int
    unit: str
    request_count: int
    percentage: float


class CostSummary(BaseModel):
    """Overall cost summary with breakdown by type.

    Maps to: CostSummaryResponse proto message.
    """

    total_cost_usd: DecimalStr
    by_type: list[CostTypeSummary]
    period_start: date
    period_end: date
    trend_vs_previous_period: str  # e.g., "+8.5%"
    total_requests: int


class DailyCostEntry(BaseModel):
    """Single day cost breakdown for trend charts.

    Maps to: DailyCostEntry proto message.
    """

    date: date
    total_cost_usd: DecimalStr
    llm_cost_usd: DecimalStr = Field(default=Decimal("0"))
    document_cost_usd: DecimalStr = Field(default=Decimal("0"))
    embedding_cost_usd: DecimalStr = Field(default=Decimal("0"))
    sms_cost_usd: DecimalStr = Field(default=Decimal("0"))


class DailyCostTrend(BaseModel):
    """Daily trend response with data availability info.

    Maps to: DailyTrendResponse proto message.
    """

    entries: list[DailyCostEntry]
    data_available_from: date  # Earliest date based on TTL retention


class CurrentDayCost(BaseModel):
    """Current day running total.

    Maps to: CurrentDayCostResponse proto message.
    """

    date: date
    total_cost_usd: DecimalStr
    by_type: list[CostTypeSummary]
    updated_at: datetime


class AgentTypeCost(BaseModel):
    """LLM cost breakdown by agent type.

    Maps to: AgentTypeCostEntry proto message.
    """

    agent_type: str
    cost_usd: DecimalStr
    request_count: int
    tokens_in: int
    tokens_out: int
    percentage: float


class ModelCost(BaseModel):
    """LLM cost breakdown by model.

    Maps to: ModelCostEntry proto message.
    """

    model: str
    cost_usd: DecimalStr
    request_count: int
    tokens_in: int
    tokens_out: int
    percentage: float


class DomainCost(BaseModel):
    """Embedding cost breakdown by knowledge domain.

    Maps to: DomainCostEntry proto message.
    """

    knowledge_domain: str
    cost_usd: DecimalStr
    tokens_total: int
    texts_count: int
    percentage: float


class DocumentCostSummary(BaseModel):
    """Document processing cost summary.

    Maps to: DocumentCostResponse proto message.
    """

    total_cost_usd: DecimalStr
    total_pages: int
    total_documents: int
    average_cost_per_document: DecimalStr


class BudgetStatus(BaseModel):
    """Current budget status with thresholds and alerts.

    Maps to: BudgetStatusResponse proto message.
    """

    daily_threshold_usd: DecimalStr
    monthly_threshold_usd: DecimalStr
    current_daily_cost_usd: DecimalStr
    current_monthly_cost_usd: DecimalStr
    daily_alert_triggered: bool
    monthly_alert_triggered: bool
    daily_remaining_usd: DecimalStr
    monthly_remaining_usd: DecimalStr
```

#### Update `libs/fp-common/fp_common/models/__init__.py`

Add exports for cost models:

```python
from fp_common.models.cost import (
    AgentTypeCost,
    BudgetStatus,
    CostSummary,
    CostType,
    CostTypeSummary,
    CurrentDayCost,
    DailyCostEntry,
    DailyCostTrend,
    DocumentCostSummary,
    DomainCost,
    ModelCost,
)
```

---

### Part 5: gRPC Converters (fp-common)

Following the pattern in `collection_converters.py` and `plantation_converters.py`.

#### New File: `libs/fp-common/fp_common/converters/cost_converters.py`

```python
"""Proto-to-Pydantic converters for Platform Cost domain.

Following the same pattern as plantation_converters.py and collection_converters.py.

Usage:
    from fp_common.converters import cost_summary_from_proto, daily_cost_entry_from_proto

    # In BFF client
    summary = cost_summary_from_proto(grpc_response)

Reference:
- Pydantic models: fp_common/models/cost.py
- Proto definition: proto/platform_cost/v1/platform_cost.proto
"""

from datetime import date, datetime
from decimal import Decimal

from fp_proto.platform_cost.v1 import platform_cost_pb2

from fp_common.models.cost import (
    AgentTypeCost,
    BudgetStatus,
    CostSummary,
    CostType,
    CostTypeSummary,
    CurrentDayCost,
    DailyCostEntry,
    DailyCostTrend,
    DocumentCostSummary,
    DomainCost,
    ModelCost,
)


def _proto_cost_type_to_enum(proto_str: str) -> CostType:
    """Convert proto cost_type string to CostType enum."""
    mapping = {
        "llm": CostType.LLM,
        "document": CostType.DOCUMENT,
        "embedding": CostType.EMBEDDING,
        "sms": CostType.SMS,
    }
    return mapping.get(proto_str.lower(), CostType.LLM)


def cost_type_summary_from_proto(
    proto: platform_cost_pb2.CostTypeBreakdown,
) -> CostTypeSummary:
    """Convert CostTypeBreakdown proto to Pydantic model."""
    return CostTypeSummary(
        cost_type=_proto_cost_type_to_enum(proto.cost_type),
        amount_usd=Decimal(proto.amount_usd),
        quantity=proto.quantity,
        unit=proto.unit,
        request_count=proto.request_count,
        percentage=proto.percentage,
    )


def cost_summary_from_proto(
    proto: platform_cost_pb2.CostSummaryResponse,
) -> CostSummary:
    """Convert CostSummaryResponse proto to Pydantic model."""
    return CostSummary(
        total_cost_usd=Decimal(proto.total_cost_usd),
        by_type=[cost_type_summary_from_proto(bt) for bt in proto.by_type],
        period_start=date.fromisoformat(proto.period_start),
        period_end=date.fromisoformat(proto.period_end),
        trend_vs_previous_period=proto.trend_vs_previous_period,
        total_requests=proto.total_requests,
    )


def daily_cost_entry_from_proto(
    proto: platform_cost_pb2.DailyCostEntry,
) -> DailyCostEntry:
    """Convert DailyCostEntry proto to Pydantic model."""
    return DailyCostEntry(
        date=date.fromisoformat(proto.date),
        total_cost_usd=Decimal(proto.total_cost_usd),
        llm_cost_usd=Decimal(proto.llm_cost_usd),
        document_cost_usd=Decimal(proto.document_cost_usd),
        embedding_cost_usd=Decimal(proto.embedding_cost_usd),
        sms_cost_usd=Decimal(proto.sms_cost_usd),
    )


def daily_cost_trend_from_proto(
    proto: platform_cost_pb2.DailyTrendResponse,
) -> DailyCostTrend:
    """Convert DailyTrendResponse proto to Pydantic model."""
    return DailyCostTrend(
        entries=[daily_cost_entry_from_proto(e) for e in proto.entries],
        data_available_from=date.fromisoformat(proto.data_available_from),
    )


def current_day_cost_from_proto(
    proto: platform_cost_pb2.CurrentDayCostResponse,
) -> CurrentDayCost:
    """Convert CurrentDayCostResponse proto to Pydantic model."""
    return CurrentDayCost(
        date=date.fromisoformat(proto.date),
        total_cost_usd=Decimal(proto.total_cost_usd),
        by_type=[cost_type_summary_from_proto(bt) for bt in proto.by_type],
        updated_at=datetime.fromisoformat(proto.updated_at),
    )


def agent_type_cost_from_proto(
    proto: platform_cost_pb2.AgentTypeCostEntry,
) -> AgentTypeCost:
    """Convert AgentTypeCostEntry proto to Pydantic model."""
    return AgentTypeCost(
        agent_type=proto.agent_type,
        cost_usd=Decimal(proto.cost_usd),
        request_count=proto.request_count,
        tokens_in=proto.tokens_in,
        tokens_out=proto.tokens_out,
        percentage=proto.percentage,
    )


def model_cost_from_proto(
    proto: platform_cost_pb2.ModelCostEntry,
) -> ModelCost:
    """Convert ModelCostEntry proto to Pydantic model."""
    return ModelCost(
        model=proto.model,
        cost_usd=Decimal(proto.cost_usd),
        request_count=proto.request_count,
        tokens_in=proto.tokens_in,
        tokens_out=proto.tokens_out,
        percentage=proto.percentage,
    )


def domain_cost_from_proto(
    proto: platform_cost_pb2.DomainCostEntry,
) -> DomainCost:
    """Convert DomainCostEntry proto to Pydantic model."""
    return DomainCost(
        knowledge_domain=proto.knowledge_domain,
        cost_usd=Decimal(proto.cost_usd),
        tokens_total=proto.tokens_total,
        texts_count=proto.texts_count,
        percentage=proto.percentage if hasattr(proto, "percentage") else 0.0,
    )


def document_cost_summary_from_proto(
    proto: platform_cost_pb2.DocumentCostResponse,
) -> DocumentCostSummary:
    """Convert DocumentCostResponse proto to Pydantic model."""
    return DocumentCostSummary(
        total_cost_usd=Decimal(proto.total_cost_usd),
        total_pages=proto.total_pages,
        total_documents=proto.total_documents,
        average_cost_per_document=Decimal(proto.average_cost_per_document),
    )


def budget_status_from_proto(
    proto: platform_cost_pb2.BudgetStatusResponse,
) -> BudgetStatus:
    """Convert BudgetStatusResponse proto to Pydantic model."""
    return BudgetStatus(
        daily_threshold_usd=Decimal(proto.daily_threshold_usd),
        monthly_threshold_usd=Decimal(proto.monthly_threshold_usd),
        current_daily_cost_usd=Decimal(proto.current_daily_cost_usd),
        current_monthly_cost_usd=Decimal(proto.current_monthly_cost_usd),
        daily_alert_triggered=proto.daily_alert_triggered,
        monthly_alert_triggered=proto.monthly_alert_triggered,
        daily_remaining_usd=Decimal(proto.daily_remaining_usd),
        monthly_remaining_usd=Decimal(proto.monthly_remaining_usd),
    )
```

#### Update `libs/fp-common/fp_common/converters/__init__.py`

Add exports for cost converters:

```python
from fp_common.converters.cost_converters import (
    agent_type_cost_from_proto,
    budget_status_from_proto,
    cost_summary_from_proto,
    cost_type_summary_from_proto,
    current_day_cost_from_proto,
    daily_cost_entry_from_proto,
    daily_cost_trend_from_proto,
    document_cost_summary_from_proto,
    domain_cost_from_proto,
    model_cost_from_proto,
)
```

---

### Part 6: BFF Client

Following the pattern in `plantation_client.py` and `collection_client.py`.

#### New File: `services/bff/src/bff/infrastructure/clients/platform_cost_client.py`

```python
"""Platform Cost gRPC client for BFF.

Provides typed access to Platform Cost service via DAPR gRPC.
All methods return fp-common Pydantic domain models (NOT dicts).

Pattern follows PlantationClient and CollectionClient per:
- ADR-002 §"Service Invocation Pattern" (native gRPC with dapr-app-id metadata)
- ADR-005 for retry logic (3 attempts, exponential backoff 1-10s)
- ADR-016 for unified cost model

CRITICAL: Uses fp-common domain models for type safety. Never returns dict[str, Any].
"""

from datetime import date

import grpc.aio
from bff.infrastructure.clients.base import BaseGrpcClient, grpc_retry
from fp_common.converters.cost_converters import (
    agent_type_cost_from_proto,
    budget_status_from_proto,
    cost_summary_from_proto,
    current_day_cost_from_proto,
    daily_cost_trend_from_proto,
    document_cost_summary_from_proto,
    domain_cost_from_proto,
    model_cost_from_proto,
)
from fp_common.models.cost import (
    AgentTypeCost,
    BudgetStatus,
    CostSummary,
    CurrentDayCost,
    DailyCostTrend,
    DocumentCostSummary,
    DomainCost,
    ModelCost,
)
from fp_proto.platform_cost.v1 import platform_cost_pb2, platform_cost_pb2_grpc


class PlatformCostClient(BaseGrpcClient):
    """gRPC client for Platform Cost service.

    Provides typed access to unified cost reporting via DAPR.
    All methods return Pydantic domain models from fp_common.models.cost.

    Example:
        >>> client = PlatformCostClient()
        >>> summary = await client.get_cost_summary(
        ...     start_date=date(2026, 1, 1),
        ...     end_date=date(2026, 1, 31),
        ... )
        >>> assert isinstance(summary, CostSummary)
        >>> print(summary.total_cost_usd)
    """

    def __init__(
        self,
        dapr_grpc_port: int = 50001,
        direct_host: str | None = None,
        channel: grpc.aio.Channel | None = None,
    ) -> None:
        super().__init__(
            target_app_id="platform-cost",
            dapr_grpc_port=dapr_grpc_port,
            direct_host=direct_host,
            channel=channel,
        )

    async def _get_cost_stub(self) -> platform_cost_pb2_grpc.UnifiedCostServiceStub:
        return await self._get_stub(platform_cost_pb2_grpc.UnifiedCostServiceStub)

    # =========================================================================
    # Summary & Trend Queries
    # =========================================================================

    @grpc_retry
    async def get_cost_summary(
        self,
        start_date: date,
        end_date: date,
        factory_id: str | None = None,
    ) -> CostSummary:
        """Get cost summary with breakdown by type.

        Args:
            start_date: Start of date range (inclusive).
            end_date: End of date range (inclusive).
            factory_id: Optional filter by factory.

        Returns:
            CostSummary with total, breakdown by type, and trend.

        Raises:
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_cost_stub()
            request = platform_cost_pb2.CostSummaryRequest(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                factory_id=factory_id or "",
            )
            response = await stub.GetCostSummary(request, metadata=self._get_metadata())
            return cost_summary_from_proto(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Cost summary")
            raise

    @grpc_retry
    async def get_daily_trend(
        self,
        start_date: date,
        end_date: date,
        factory_id: str | None = None,
    ) -> DailyCostTrend:
        """Get daily cost trend for stacked area chart.

        Args:
            start_date: Start of date range (inclusive).
            end_date: End of date range (inclusive).
            factory_id: Optional filter by factory.

        Returns:
            DailyCostTrend with entries and data availability date.

        Raises:
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_cost_stub()
            request = platform_cost_pb2.DailyTrendRequest(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                factory_id=factory_id or "",
            )
            response = await stub.GetDailyCostTrend(request, metadata=self._get_metadata())
            return daily_cost_trend_from_proto(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Daily trend")
            raise

    @grpc_retry
    async def get_current_day_cost(
        self,
        factory_id: str | None = None,
    ) -> CurrentDayCost:
        """Get current day running total.

        Args:
            factory_id: Optional filter by factory.

        Returns:
            CurrentDayCost with today's running total and breakdown.

        Raises:
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_cost_stub()
            request = platform_cost_pb2.CurrentDayCostRequest(
                factory_id=factory_id or "",
            )
            response = await stub.GetCurrentDayCost(request, metadata=self._get_metadata())
            return current_day_cost_from_proto(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Current day cost")
            raise

    # =========================================================================
    # LLM-Specific Queries
    # =========================================================================

    @grpc_retry
    async def get_llm_cost_by_agent_type(
        self,
        start_date: date,
        end_date: date,
        factory_id: str | None = None,
    ) -> tuple[list[AgentTypeCost], str]:
        """Get LLM costs grouped by agent type.

        Args:
            start_date: Start of date range (inclusive).
            end_date: End of date range (inclusive).
            factory_id: Optional filter by factory.

        Returns:
            Tuple of (list of AgentTypeCost, total_cost_usd string).

        Raises:
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_cost_stub()
            request = platform_cost_pb2.LlmCostByAgentTypeRequest(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                factory_id=factory_id or "",
            )
            response = await stub.GetLlmCostByAgentType(request, metadata=self._get_metadata())
            entries = [agent_type_cost_from_proto(e) for e in response.entries]
            return entries, response.total_cost_usd
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "LLM cost by agent type")
            raise

    @grpc_retry
    async def get_llm_cost_by_model(
        self,
        start_date: date,
        end_date: date,
        factory_id: str | None = None,
    ) -> tuple[list[ModelCost], str]:
        """Get LLM costs grouped by model.

        Args:
            start_date: Start of date range (inclusive).
            end_date: End of date range (inclusive).
            factory_id: Optional filter by factory.

        Returns:
            Tuple of (list of ModelCost, total_cost_usd string).

        Raises:
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_cost_stub()
            request = platform_cost_pb2.LlmCostByModelRequest(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                factory_id=factory_id or "",
            )
            response = await stub.GetLlmCostByModel(request, metadata=self._get_metadata())
            entries = [model_cost_from_proto(e) for e in response.entries]
            return entries, response.total_cost_usd
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "LLM cost by model")
            raise

    # =========================================================================
    # Type-Specific Queries
    # =========================================================================

    @grpc_retry
    async def get_document_cost_summary(
        self,
        start_date: date,
        end_date: date,
    ) -> DocumentCostSummary:
        """Get document processing cost summary.

        Args:
            start_date: Start of date range (inclusive).
            end_date: End of date range (inclusive).

        Returns:
            DocumentCostSummary with total, pages, and averages.

        Raises:
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_cost_stub()
            request = platform_cost_pb2.DocumentCostRequest(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
            response = await stub.GetDocumentCostSummary(request, metadata=self._get_metadata())
            return document_cost_summary_from_proto(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Document cost summary")
            raise

    @grpc_retry
    async def get_embedding_cost_by_domain(
        self,
        start_date: date,
        end_date: date,
    ) -> tuple[list[DomainCost], str]:
        """Get embedding costs grouped by knowledge domain.

        Args:
            start_date: Start of date range (inclusive).
            end_date: End of date range (inclusive).

        Returns:
            Tuple of (list of DomainCost, total_cost_usd string).

        Raises:
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_cost_stub()
            request = platform_cost_pb2.EmbeddingCostByDomainRequest(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
            response = await stub.GetEmbeddingCostByDomain(request, metadata=self._get_metadata())
            entries = [domain_cost_from_proto(e) for e in response.entries]
            return entries, response.total_cost_usd
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Embedding cost by domain")
            raise

    # =========================================================================
    # Budget Management
    # =========================================================================

    @grpc_retry
    async def get_budget_status(self) -> BudgetStatus:
        """Get current budget status with thresholds and alerts.

        Returns:
            BudgetStatus with thresholds, current costs, and alert states.

        Raises:
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_cost_stub()
            request = platform_cost_pb2.BudgetStatusRequest()
            response = await stub.GetBudgetStatus(request, metadata=self._get_metadata())
            return budget_status_from_proto(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Budget status")
            raise

    @grpc_retry
    async def configure_budget_threshold(
        self,
        daily_threshold_usd: str | None = None,
        monthly_threshold_usd: str | None = None,
    ) -> tuple[str, str, str]:
        """Configure budget thresholds.

        Args:
            daily_threshold_usd: New daily threshold (Decimal as string), or None to keep.
            monthly_threshold_usd: New monthly threshold (Decimal as string), or None to keep.

        Returns:
            Tuple of (daily_threshold_usd, monthly_threshold_usd, message).

        Raises:
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_cost_stub()
            request = platform_cost_pb2.ConfigureThresholdRequest(
                daily_threshold_usd=daily_threshold_usd or "",
                monthly_threshold_usd=monthly_threshold_usd or "",
            )
            response = await stub.ConfigureBudgetThreshold(request, metadata=self._get_metadata())
            return response.daily_threshold_usd, response.monthly_threshold_usd, response.message
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Configure budget threshold")
            raise
```

---

## Consequences

### Positive

1. **Clean separation of concerns** - ai-model handles AI operations, platform-cost handles cost aggregation
2. **Single source of truth** - All costs in one service, one collection, one API
3. **Extensible** - Adding SMS costs just requires publishing to the topic
4. **Platform Admin UI simplicity** - Single gRPC endpoint for all cost data
5. **No backward compatibility burden** - Platform Admin UI doesn't exist yet

### Negative

1. **New service to maintain** - platform-cost adds operational overhead
2. **Migration effort** - Moving code from ai-model to platform-cost
3. **Eventual consistency** - Small delay between cost incurred and cost visible (pub/sub latency)
4. **DAPR dependency** - Cost tracking requires DAPR pub/sub to be healthy

### Risks

| Risk | Mitigation |
|------|------------|
| Lost cost events (DAPR failure) | Dead letter queue + reconciliation job (future) |
| Budget alerts delayed | Accept 30s-2m latency as acceptable (see section 3.5.2) |
| MongoDB storage growth | 90-day TTL index auto-deletes old events (configurable) |
| Inaccurate metrics after restart | BudgetMonitor warm-up from MongoDB on startup (see section 3.5) |

---

## Implementation Order

| # | Task | Story | Status |
|---|------|-------|--------|
| 1 | Create fp-common event model (`CostRecordedEvent`) | 13.1 | ✅ Done |
| 2 | Create platform-cost service scaffold | 13.2 | ✅ Done |
| 3 | Create repository + budget monitor in platform-cost | 13.3 | ✅ Done |
| 4 | **Create proto definition** (`proto/platform_cost/v1/platform_cost.proto`) | 13.4 | Pending |
| 5 | **Add gRPC UnifiedCostService** to platform-cost | 13.4 | Pending |
| 6 | **Add DAPR subscription handler** to platform-cost | 13.5 | Pending |
| 7 | **Create fp-common shared models** (`fp_common/models/cost.py`) | 13.6 | Pending |
| 8 | **Create fp-common converters** (`fp_common/converters/cost_converters.py`) | 13.6 | Pending |
| 9 | **Create BFF client** (`bff/.../platform_cost_client.py`) | 13.6 | Pending |
| 10 | Modify ai-model to publish instead of persist | 13.7 | Pending |
| 11 | Remove deleted files from ai-model | 13.7 | Pending |
| 12 | Integration testing with E2E scenarios | 13.8 | Pending |

**Notes:**
- Steps 7-9 (BFF Integration) follow the established pattern from Collection/Plantation models
- The fp-common models mirror the service-internal models but live in the shared library
- Converters convert proto messages → fp-common Pydantic models for type-safe BFF consumption

---

## References

- Story 9.6: LLM Cost Dashboard (original UI spec)
- Story 0.75.5: OpenRouter LLM Gateway with Cost Observability
- ADR-010: DAPR Patterns and Configuration Standards
- ADR-011: gRPC + FastAPI + DAPR Architecture
