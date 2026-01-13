# Epic 13: Unified Platform Cost Service

**Priority:** P1 (Required for Story 9.6 - LLM Cost Dashboard)

**Dependencies:** Epic 0.75 (AI Model - for cost event publishing)

Centralized cost aggregation service that collects costs from all billable services (LLM, Document Intelligence, Embeddings, SMS) via DAPR pub/sub and exposes a unified gRPC API for the Platform Admin Cost Dashboard.

**Related ADRs:** ADR-016 (Unified Cost Model and Platform Cost Service)

**Scope:**
- New `platform-cost` microservice
- Shared cost event model in fp-common
- DAPR pub/sub subscription for cost events
- gRPC UnifiedCostService with cost queries and budget management
- Refactor ai-model from cost store to cost producer
- 90-day TTL data retention (configurable)
- OpenTelemetry metrics for Prometheus/Grafana alerting

---

## Story 13.1: Shared Cost Event Model

As a **platform developer**,
I want a shared cost event model in fp-common,
So that all services can publish cost events with a consistent schema.

**Acceptance Criteria:**

**Given** I need to publish a cost event from any service
**When** I import from fp-common
**Then** `CostRecordedEvent` model is available with fields:
  - `cost_type`: enum (llm, document, embedding, sms)
  - `amount_usd`: Decimal as string for precision
  - `quantity`: int (tokens, pages, messages)
  - `unit`: enum (tokens, pages, messages, queries)
  - `timestamp`: datetime UTC
  - `source_service`: string
  - `success`: bool
  - `metadata`: dict for type-specific data
  - `factory_id`: optional string
  - `request_id`: optional string

**Given** I publish a cost event
**When** I serialize it for DAPR
**Then** `model_dump_json()` produces valid JSON
**And** Decimal values are serialized as strings

**Technical Notes:**
- Location: `libs/fp-common/fp_common/events/cost_recorded.py`
- Enums: `CostType`, `CostUnit`
- Reference: ADR-016 section "Part 1: Shared Event Model"

**Dependencies:** None

**Story Points:** 2

---

## Story 13.2: Platform Cost Service Scaffold

As a **platform developer**,
I want the platform-cost service scaffolded with FastAPI + DAPR + gRPC,
So that cost aggregation logic has a home.

**Acceptance Criteria:**

**Given** I create the service structure
**When** I scaffold `services/platform-cost/`
**Then** Standard service layout exists:
  - `src/platform_cost/main.py` (FastAPI lifespan)
  - `src/platform_cost/config.py` (Pydantic Settings)
  - `src/platform_cost/domain/` (domain models)
  - `src/platform_cost/infrastructure/` (repositories)
  - `src/platform_cost/services/` (business logic)
  - `src/platform_cost/api/` (gRPC servicers)
  - `src/platform_cost/handlers/` (DAPR handlers)

**Given** the service is running
**When** I call `/health`
**Then** Health check returns 200 with service info
**And** MongoDB connection is verified
**And** DAPR sidecar connection is verified

**Given** I configure the service
**When** I set environment variables
**Then** Settings are loaded for:
  - MongoDB connection
  - DAPR pubsub name and topic
  - Budget thresholds (daily/monthly)
  - Cost event retention days (TTL)
  - gRPC port

**Technical Notes:**
- Location: `services/platform-cost/`
- Dockerfile follows existing service patterns
- DAPR config in `services/platform-cost/dapr/`
- Reference: ADR-016 section 3.6 (Config)

**Dependencies:**
- Story 13.1: Shared Cost Event Model

**Story Points:** 3

---

## Story 13.3: Cost Repository and Budget Monitor

As a **platform developer**,
I want a unified cost repository with TTL and a budget monitor with warm-up,
So that costs are persisted efficiently and metrics survive restarts.

**Acceptance Criteria:**

**Given** the repository is initialized
**When** `ensure_indexes()` is called
**Then** Indexes are created for:
  - `timestamp` (descending, for recent queries)
  - `cost_type` (for type filtering)
  - `cost_type + timestamp` (compound)
  - `factory_id` (sparse, for attribution)
  - `agent_type`, `model` (sparse, for LLM breakdowns)
  - `knowledge_domain` (sparse, for embedding breakdowns)
  - TTL index on `timestamp` (90 days default, configurable)

**Given** I query costs
**When** I call repository methods
**Then** `get_summary_by_type()` returns typed `CostTypeSummary` models
**And** `get_daily_trend()` returns typed `DailyCostEntry` models
**And** `get_current_day_cost()` returns typed `CurrentDayCost` model
**And** `get_llm_cost_by_agent_type()` returns typed `AgentTypeCost` models
**And** `get_llm_cost_by_model()` returns typed `ModelCost` models

**Given** the service restarts mid-day
**When** BudgetMonitor initializes
**Then** `warm_up_from_repository()` is called
**And** Daily and monthly totals are restored from MongoDB
**And** Alert states are correctly set based on restored totals
**And** Startup fails if warm-up query fails (fail-fast)

**Given** BudgetMonitor is running
**When** costs are recorded
**Then** OpenTelemetry gauges are updated:
  - `platform_cost_daily_total_usd`
  - `platform_cost_monthly_total_usd`
  - `platform_cost_daily_utilization_percent`
  - `platform_cost_monthly_utilization_percent`
  - `platform_cost_by_type_usd` (with cost_type label)

**Technical Notes:**
- Repository: `platform_cost/infrastructure/repositories/cost_repository.py`
- BudgetMonitor: `platform_cost/services/budget_monitor.py`
- Domain models: `platform_cost/domain/cost_event.py`
- Reference: ADR-016 sections 3.4, 3.5

**Dependencies:**
- Story 13.2: Platform Cost Service Scaffold

**Story Points:** 5

---

## Story 13.4: gRPC UnifiedCostService

As a **platform developer**,
I want a gRPC UnifiedCostService exposing all cost query and budget APIs,
So that the Platform Admin UI can consume cost data.

**Acceptance Criteria:**

**Given** the proto is defined
**When** I generate Python code
**Then** `proto/platform_cost/v1/platform_cost.proto` defines:
  - `GetCostSummary` - total costs with type breakdown
  - `GetDailyCostTrend` - daily costs for stacked chart (includes `data_available_from`)
  - `GetCurrentDayCost` - real-time today's cost
  - `GetLlmCostByAgentType` - LLM breakdown by agent
  - `GetLlmCostByModel` - LLM breakdown by model
  - `GetDocumentCostSummary` - document processing costs
  - `GetEmbeddingCostByDomain` - embedding costs by knowledge domain
  - `GetBudgetStatus` - current thresholds and utilization
  - `ConfigureBudgetThreshold` - update thresholds (persisted to MongoDB)

**Given** I call `GetDailyCostTrend`
**When** the response is returned
**Then** `data_available_from` field indicates earliest available date
**And** Requests for dates before TTL cutoff return empty entries (not errors)

**Given** I call `ConfigureBudgetThreshold`
**When** thresholds are updated
**Then** New values are persisted to MongoDB `budget_config` collection
**And** BudgetMonitor in-memory state is updated immediately
**And** Next restart loads persisted values

**Technical Notes:**
- Proto: `proto/platform_cost/v1/platform_cost.proto`
- Servicer: `platform_cost/api/unified_cost_service.py`
- gRPC server: `platform_cost/api/grpc_server.py`
- Reference: ADR-016 section 3.2 (Proto), 3.6 (Threshold Config)

**Dependencies:**
- Story 13.3: Cost Repository and Budget Monitor

**Story Points:** 5

---

## Story 13.5: DAPR Cost Event Subscription

As a **platform developer**,
I want platform-cost to subscribe to cost events via DAPR pub/sub,
So that costs from all services are aggregated automatically.

**Acceptance Criteria:**

**Given** the DAPR subscription is configured
**When** the service starts
**Then** It subscribes to topic `platform.cost.recorded`
**And** Subscription is defined in `dapr/subscription.yaml`

**Given** a cost event is published
**When** platform-cost receives it
**Then** Event is parsed into `UnifiedCostEvent` domain model
**And** Event is persisted to MongoDB `cost_events` collection
**And** BudgetMonitor is updated (metrics reflect new cost)
**And** `TopicEventResponse("success")` is returned

**Given** a malformed event is received
**When** parsing fails (missing required field)
**Then** Event is logged with error details
**And** `TopicEventResponse("drop")` is returned (no retry)

**Given** a transient error occurs (MongoDB unavailable)
**When** persistence fails
**Then** `TopicEventResponse("retry")` is returned
**And** DAPR will retry delivery

**Technical Notes:**
- Handler: `platform_cost/handlers/cost_event_handler.py`
- DAPR subscription: `services/platform-cost/dapr/subscription.yaml`
- Topic: `platform.cost.recorded`
- Reference: ADR-016 section 3.7

**Dependencies:**
- Story 13.3: Cost Repository and Budget Monitor

**Story Points:** 3

---

## Story 13.6: BFF Integration Layer

As a **platform developer**,
I want shared cost models in fp-common with converters and BFF client,
So that Platform Admin UI can consume cost data with type safety (not dict).

**Acceptance Criteria:**

**Given** I need to return cost data from BFF
**When** I import from fp-common
**Then** Shared response models are available in `fp_common/models/cost.py`:
  - `CostType`: enum (llm, document, embedding, sms)
  - `CostTypeSummary`: breakdown per type
  - `CostSummary`: total with type breakdown
  - `DailyCostEntry`: daily breakdown for charts
  - `DailyCostTrend`: trend with data availability date
  - `CurrentDayCost`: today's running total
  - `AgentTypeCost`: LLM cost by agent type
  - `ModelCost`: LLM cost by model
  - `DomainCost`: embedding cost by knowledge domain
  - `DocumentCostSummary`: document processing costs
  - `BudgetStatus`: thresholds and alert states

**Given** BFF receives gRPC responses from platform-cost
**When** I need to convert proto to Pydantic
**Then** Converters are available in `fp_common/converters/cost_converters.py`:
  - `cost_summary_from_proto()`
  - `daily_cost_entry_from_proto()`
  - `daily_cost_trend_from_proto()`
  - `current_day_cost_from_proto()`
  - `agent_type_cost_from_proto()`
  - `model_cost_from_proto()`
  - `domain_cost_from_proto()`
  - `document_cost_summary_from_proto()`
  - `budget_status_from_proto()`

**Given** BFF needs to call platform-cost service
**When** I use PlatformCostClient
**Then** Client exists at `bff/infrastructure/clients/platform_cost_client.py`:
  - Follows PlantationClient/CollectionClient pattern
  - Uses DAPR gRPC service invocation (dapr-app-id metadata)
  - Returns typed Pydantic models (NOT dict[str, Any])
  - Implements retry decorator per ADR-005
  - Methods: `get_cost_summary()`, `get_daily_trend()`, `get_current_day_cost()`,
    `get_llm_cost_by_agent_type()`, `get_llm_cost_by_model()`,
    `get_document_cost_summary()`, `get_embedding_cost_by_domain()`,
    `get_budget_status()`, `configure_budget_threshold()`

**Given** platform-cost service has internal models
**When** I review the codebase
**Then** Service imports response models from fp-common (not duplicated)
**And** Only `UnifiedCostEvent` storage model remains in `platform_cost/domain/cost_event.py`

**Technical Notes:**
- fp-common models: `libs/fp-common/fp_common/models/cost.py`
- fp-common converters: `libs/fp-common/fp_common/converters/cost_converters.py`
- BFF client: `services/bff/src/bff/infrastructure/clients/platform_cost_client.py`
- Pattern reference: PlantationClient, CollectionClient
- Reference: ADR-016 Parts 4, 5, 6

**Dependencies:**
- Story 13.4: gRPC UnifiedCostService (proto must exist)

**Story Points:** 5

---

## Story 13.7: AI Model Refactor - Publish Costs via DAPR

As a **platform developer**,
I want ai-model to publish cost events instead of persisting them,
So that platform-cost becomes the single source of truth for costs.

**Acceptance Criteria:**

**Given** LLM Gateway processes a request
**When** cost is calculated
**Then** `CostRecordedEvent` is published to `platform.cost.recorded` topic
**And** Event includes: cost_type=llm, model, agent_type, tokens_in, tokens_out
**And** No local persistence to MongoDB occurs

**Given** EmbeddingService processes embeddings
**When** cost is calculated (using `embedding_cost_per_1k_tokens` setting)
**Then** `CostRecordedEvent` is published with cost_type=embedding
**And** Event includes: model, knowledge_domain, texts_count, batch_count

**Given** AzureDocumentIntelligenceClient processes a document
**When** cost is calculated
**Then** `CostRecordedEvent` is published with cost_type=document
**And** Event includes: model_id, page_count, document_id

**Given** the refactor is complete
**When** I review ai-model codebase
**Then** These files are DELETED:
  - `src/ai_model/api/cost_service.py`
  - `src/ai_model/infrastructure/repositories/cost_event_repository.py`
  - `src/ai_model/infrastructure/repositories/embedding_cost_repository.py`
  - `src/ai_model/llm/budget_monitor.py`
**And** CostService is removed from `proto/ai_model/v1/ai_model.proto`
**And** Cost-related settings are removed from `ai_model/config.py`
**And** `unified_cost_topic` setting is added to config

**Given** DAPR publish fails
**When** exception is caught
**Then** Warning is logged (cost tracking is best-effort)
**And** LLM/embedding/document operation still succeeds

**Technical Notes:**
- LLM Gateway: `src/ai_model/llm/gateway.py` lines ~557-577
- EmbeddingService: `src/ai_model/services/embedding_service.py`
- Azure DI Client: `src/ai_model/infrastructure/azure_doc_intel_client.py`
- Reference: ADR-016 sections 2.1-2.8

**Dependencies:**
- Story 13.1: Shared Cost Event Model
- Story 13.5: DAPR Cost Event Subscription (for receiving events)

**Story Points:** 5

---

## Story 13.8: E2E Integration Tests

As a **platform developer**,
I want E2E tests validating the full cost tracking flow,
So that I have confidence the pub/sub integration works correctly.

**Acceptance Criteria:**

**Given** ai-model publishes a cost event
**When** I make an LLM request via gRPC
**Then** Cost event appears in platform-cost MongoDB within 5 seconds
**And** BudgetMonitor metrics reflect the new cost

**Given** I query costs via gRPC
**When** I call `GetCostSummary` after publishing events
**Then** Response includes the published costs
**And** Type breakdown is accurate

**Given** I configure budget thresholds
**When** costs exceed the threshold
**Then** `GetBudgetStatus` shows `daily_alert_triggered: true`
**And** OTEL metric `platform_cost_daily_utilization_percent` >= 100

**Given** platform-cost restarts
**When** I query `GetCurrentDayCost`
**Then** Response includes costs from before restart
**And** No data loss occurred

**Given** TTL is configured
**When** I query for dates beyond retention
**Then** `data_available_from` field indicates the cutoff
**And** Empty results are returned (not errors)

**Technical Notes:**
- Location: `tests/e2e/scenarios/test_platform_cost.py`
- Requires: ai-model + platform-cost + MongoDB + DAPR running
- Seed data: None required (tests publish their own events)
- Reference: ADR-016 "Integration testing with E2E scenarios"

**Dependencies:**
- Story 13.5: DAPR Cost Event Subscription
- Story 13.7: AI Model Refactor

**Story Points:** 5

---

## Notes

**Total Story Points:** 33

**Implementation Order:**
1. Story 13.1 (shared event model) - no dependencies ✅
2. Story 13.2 (scaffold) - depends on 13.1 ✅
3. Story 13.3 (repository + monitor) - depends on 13.2 ✅
4. Story 13.4 (proto + gRPC service) - depends on 13.3
5. Story 13.5 (DAPR subscription) - depends on 13.3
6. Story 13.6 (BFF integration: fp-common models + converters + client) - depends on 13.4
7. Story 13.7 (ai-model refactor) - depends on 13.1, 13.5
8. Story 13.8 (E2E tests) - depends on 13.5, 13.7

**Post-Epic:** Update Story 9.6 (LLM Cost Dashboard) to consume `platform-cost` gRPC instead of `ai-model` CostService.
