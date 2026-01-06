### Epic 0.6: Infrastructure Hardening (ADR Implementation)

**Priority:** P0

**Dependencies:** Epic 0 (Infrastructure Foundation) - Complete

Cross-cutting infrastructure improvements implementing accepted Architecture Decision Records (ADRs). These stories establish shared patterns, type safety, resilience mechanisms, and DAPR SDK patterns that enable robust production deployments.

**Related ADRs:**
- ADR-004: Type Safety - Shared Pydantic Models
- ADR-005: gRPC Client Retry Strategy
- ADR-006: Event Delivery and Dead Letter Queue
- ADR-007: Source Config Cache with Change Streams
- ADR-008: Invalid Linkage Field Handling
- ADR-009: Logging Standards and Runtime Configuration
- ADR-010: DAPR Patterns and Configuration
- ADR-011: gRPC/FastAPI/DAPR Service Architecture

**Validated By:** PoC at `tests/e2e/poc-dapr-patterns/` (5/5 tests passing)

---

## Architecture Context

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  INFRASTRUCTURE HARDENING (Epic 0.6)                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  WAVE 1: FOUNDATION (Stories 0.6.1-0.6.4)                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │   fp-common     │  │   fp-common     │  │ collection-model│         │
│  │   /models/      │  │   /logging.py   │  │ /infrastructure │         │
│  │  Story 0.6.1    │  │  Story 0.6.2    │  │ Stories 0.6.3-4 │         │
│  │  Pydantic Models│  │  Logging Module │  │ gRPC Retry      │         │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘         │
│           │                    │                    │                   │
│           ▼                    ▼                    ▼                   │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  WAVE 2: DAPR SDK MIGRATION (Stories 0.6.5-0.6.8)                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │ plantation-model│  │ collection-model│  │  DAPR Config    │         │
│  │  /events/       │  │  /events/       │  │  /components/   │         │
│  │  Story 0.6.5    │  │  Story 0.6.6    │  │ Stories 0.6.7-8 │         │
│  │  Streaming Subs │  │  Streaming Subs │  │ Resiliency+DLQ  │         │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘         │
│           │                    │                    │                   │
│           ▼                    ▼                    ▼                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    DAPR MESH (Redis Pub/Sub)                    │   │
│  │          Events flow with DLQ, retry policies, metrics          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  WAVE 3: DOMAIN LOGIC (Stories 0.6.9-0.6.10)                           │
│  ┌─────────────────────────────────────────┐  ┌─────────────────────┐  │
│  │ collection-model/source_config_service  │  │ plantation-model    │  │
│  │  Story 0.6.9 - Cache + Change Streams   │  │ /quality_processor  │  │
│  │  Startup warming + real-time invalidate │  │  Story 0.6.10       │  │
│  │                                         │  │  Linkage validation │  │
│  └─────────────────────────────────────────┘  └─────────────────────┘  │
│                                                                         │
│  WAVE 1: Foundation (No dependencies between stories)                  │
│  WAVE 2: DAPR SDK Migration (Depends on Wave 1 logging)                │
│  WAVE 3: Domain Logic (Depends on Wave 2 DLQ for error handling)       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Wave 1 Stories

### Story 0.6.1: Shared Pydantic Models in fp-common

**[📄 Story File](../sprint-artifacts/0-6-1-shared-pydantic-models.md)** | Status: To Do

As a **developer consuming MCP server responses**,
I want typed Pydantic models shared via fp-common,
So that IDE autocomplete works and validation catches errors at MCP boundaries.

**ADR:** ADR-004 - Type Safety Architecture

**Acceptance Criteria:**

**Given** domain models exist in plantation-model
**When** I check `libs/fp-common/fp_common/models/`
**Then** I find:
  - `farmer.py` - Farmer, FarmerSummary models
  - `factory.py` - Factory, CollectionPoint models
  - `region.py` - Region, RegionalWeather models
  - `grading_model.py` - GradingModel, GradeRules models
  - `flush.py` - Flush model
  - `document.py` - Document, RawDocumentRef, SearchResult models
  - `source_summary.py` - SourceSummary model

**Given** models are moved to fp-common
**When** plantation-model imports from fp-common
**Then** `from fp_common.models import Farmer, Factory, Region` works
**And** existing plantation-model code continues to work unchanged

**Given** MCP servers return typed models
**When** I call `get_farmer()` in plantation-mcp
**Then** the return type is `Farmer` (not `dict[str, Any]`)
**And** Pydantic validation runs on response construction

**Unit Tests Required:**
- `tests/unit/fp_common/models/test_farmer.py` - Farmer model validation
- `tests/unit/fp_common/models/test_factory.py` - Factory model validation
- `tests/unit/fp_common/models/test_region.py` - Region model validation
- `tests/unit/fp_common/models/test_document.py` - Document model validation

**E2E Test Impact:**
- Existing E2E tests should pass unchanged (models are backward compatible)
- After completion, run full E2E suite to verify no regressions

**Story Points:** 5

---

### Story 0.6.2: Shared Logging Module with Runtime Configuration

**[📄 Story File](../sprint-artifacts/0-6-2-shared-logging-module.md)** | Status: To Do

As a **developer debugging production issues**,
I want consistent structured logging with runtime log level control,
So that I can enable DEBUG for specific packages without pod restart.

**ADR:** ADR-009 - Logging Standards and Runtime Configuration

**Acceptance Criteria:**

**Given** logging needs to be configured
**When** I import from fp-common
**Then** `from fp_common.logging import configure_logging` is available
**And** `configure_logging("plantation-model")` sets up structlog with JSON output

**Given** logging is configured
**When** I call `structlog.get_logger("plantation_model.domain.services")`
**Then** logs include: service name, timestamp (ISO), log level, trace_id, span_id

**Given** a service is running
**When** I POST to `/admin/logging/plantation_model.domain?level=DEBUG`
**Then** that logger and children are set to DEBUG
**And** other loggers remain at INFO

**Given** debug logging was enabled
**When** I DELETE `/admin/logging/plantation_model.domain`
**Then** that logger resets to default level

**Unit Tests Required:**
- `tests/unit/fp_common/logging/test_configure_logging.py` - Configuration tests
- `tests/unit/fp_common/logging/test_trace_context.py` - OpenTelemetry injection
- `tests/unit/fp_common/logging/test_runtime_level.py` - Level change via API

**E2E Test Impact:**
- E2E tests may see more structured log output (no breaking changes)
- New `/admin/logging` endpoint available for debugging E2E failures

**Story Points:** 3

---

### Story 0.6.3: gRPC Client Retry - AiModelClient

**[📄 Story File](../sprint-artifacts/0-6-3-grpc-retry-ai-model-client.md)** | Status: To Do

As a **platform engineer**,
I want AiModelClient to auto-recover from gRPC connection failures,
So that transient network issues don't require pod restarts.

**ADR:** ADR-005 - gRPC Client Retry and Reconnection Strategy

**Acceptance Criteria:**

**Given** AiModelClient has no retry logic
**When** I review `services/collection-model/src/collection_model/infrastructure/ai_model_client.py`
**Then** it uses per-request channel creation (anti-pattern)

**Given** AiModelClient is refactored
**When** I check the updated implementation
**Then** it uses singleton channel pattern with lazy initialization
**And** all RPC methods have `@retry` decorator from Tenacity
**And** retry config is: 3 attempts, exponential backoff (1-10s)

**Given** the gRPC connection is lost
**When** the next RPC method is called
**Then** the retry decorator catches the error
**And** reconnection is attempted automatically
**And** the call succeeds after reconnection (within retry limit)

**Given** all retries are exhausted
**When** the connection still fails
**Then** a clear error is raised with context (app_id, method, attempt count)

**Unit Tests Required:**
- `tests/unit/collection_model/infrastructure/test_ai_model_client.py`
  - `test_singleton_channel_reused` - Same channel across multiple calls
  - `test_retry_on_unavailable` - Retry triggers on UNAVAILABLE status
  - `test_retry_exhausted_raises` - Error after max retries
  - `test_channel_recreation_on_error` - Channel reset on connection error

**E2E Test Impact:**
- PoC test `tests/e2e/poc-dapr-patterns/` validates this pattern
- Extend with integration test: restart AI model service during call

**Story Points:** 2

---

### Story 0.6.4: gRPC Client Retry - IterationResolver

**[📄 Story File](../sprint-artifacts/0-6-4-grpc-retry-iteration-resolver.md)** | Status: To Do

As a **platform engineer**,
I want IterationResolver to auto-recover from gRPC connection failures,
So that transient network issues don't require pod restarts.

**ADR:** ADR-005 - gRPC Client Retry and Reconnection Strategy

**Acceptance Criteria:**

**Given** IterationResolver has no retry logic
**When** I review `services/collection-model/src/collection_model/infrastructure/iteration_resolver.py`
**Then** it uses per-request channel creation (anti-pattern)

**Given** IterationResolver is refactored
**When** I check the updated implementation
**Then** it uses singleton channel pattern with lazy initialization
**And** all RPC methods have `@retry` decorator from Tenacity
**And** retry config matches AiModelClient (3 attempts, exponential 1-10s)

**Given** the gRPC connection is lost
**When** the next RPC method is called
**Then** the retry decorator catches the error
**And** reconnection is attempted automatically

**Unit Tests Required:**
- `tests/unit/collection_model/infrastructure/test_iteration_resolver.py`
  - `test_singleton_channel_reused` - Same channel across multiple calls
  - `test_retry_on_unavailable` - Retry triggers on UNAVAILABLE status
  - `test_retry_exhausted_raises` - Error after max retries

**E2E Test Impact:**
- Same pattern as Story 0.6.3
- Extend PoC resilience test to cover IterationResolver

**Story Points:** 2

---

## Wave 2 Stories (DAPR SDK Migration)

> **Prerequisite:** Wave 1 Story 0.6.2 (Logging) should be complete before Wave 2.
> Wave 2 stories use the shared logging module for observability.

### Story 0.6.5: Plantation Model Streaming Subscriptions

**[📄 Story File](../sprint-artifacts/0-6-5-plantation-streaming-subscriptions.md)** | Status: To Do

As a **platform engineer**,
I want Plantation Model to use DAPR SDK streaming subscriptions,
So that event handling is simplified and no extra incoming port is needed.

**ADRs:** ADR-010, ADR-011 - DAPR Patterns and Service Architecture

**Acceptance Criteria:**

**Given** Plantation Model currently uses FastAPI HTTP handlers for events
**When** I check the event handling implementation
**Then** it uses `@app.post("/events/...")` pattern (anti-pattern)

**Given** the migration is complete
**When** I check the updated implementation
**Then** it uses `client.subscribe_with_handler()` from DAPR SDK
**And** handlers return `TopicEventResponse("success"|"retry"|"drop")`
**And** `dead_letter_topic="events.dlq"` is configured in code
**And** no extra incoming port is needed for event handling

**Given** a quality result event is published
**When** Plantation Model receives it via streaming subscription
**Then** `QualityEventProcessor` processes the event correctly
**And** farmer performance is updated
**And** metrics are emitted for observability

**Unit Tests Required:**
- `tests/unit/plantation_model/events/test_subscriber.py`
  - `test_quality_result_handler_returns_success`
  - `test_quality_result_handler_returns_retry_on_transient_error`
  - `test_quality_result_handler_returns_drop_on_validation_error`
  - `test_message_data_returns_dict_not_string`

**E2E Test Impact:**
- Story 0.4.7 (Cross-Model Events) validates this flow
- Must pass after migration

**Story Points:** 5

---

### Story 0.6.6: Collection Model Streaming Subscriptions

**[📄 Story File](../sprint-artifacts/0-6-6-collection-streaming-subscriptions.md)** | Status: To Do

As a **platform engineer**,
I want Collection Model to use DAPR SDK streaming subscriptions,
So that event handling is simplified and consistent with Plantation Model.

**ADRs:** ADR-010, ADR-011 - DAPR Patterns and Service Architecture

**Acceptance Criteria:**

**Given** Collection Model currently uses FastAPI HTTP handlers for events
**When** I check the event handling implementation
**Then** it uses `@app.post("/events/...")` pattern

**Given** the migration is complete
**When** I check the updated implementation
**Then** it uses `client.subscribe_with_handler()` from DAPR SDK
**And** blob events are processed via streaming subscription
**And** `dead_letter_topic="events.dlq"` is configured

**Given** a blob event is received
**When** Collection Model processes it via streaming subscription
**Then** the document is ingested correctly
**And** quality result event is published to downstream services

**Unit Tests Required:**
- `tests/unit/collection_model/events/test_subscriber.py`
  - `test_blob_event_handler_returns_success`
  - `test_blob_event_handler_returns_retry_on_transient_error`
  - `test_blob_event_handler_returns_drop_on_permanent_error`

**E2E Test Impact:**
- Stories 0.4.5, 0.4.6 (Blob Ingestion) validate this flow
- Must pass after migration

**Story Points:** 5

---

### Story 0.6.7: DAPR Resiliency Configuration

**[📄 Story File](../sprint-artifacts/0-6-7-dapr-resiliency-config.md)** | Status: To Do

As a **platform engineer**,
I want DAPR resiliency policies configured for pub/sub,
So that events are retried with exponential backoff before dead-lettering.

**ADR:** ADR-006 - Event Delivery and Dead Letter Queue

**Acceptance Criteria:**

**Given** no resiliency policy exists
**When** I check `deploy/dapr/components/`
**Then** there is no `resiliency.yaml` file

**Given** the resiliency policy is created
**When** I check the configuration
**Then** `resiliency.yaml` defines:
  - `maxRetries: 3`
  - `policy: exponential`
  - `duration: 1s`
  - `maxInterval: 30s`
**And** it targets the `pubsub` component

**Given** an event handler returns `TopicEventResponse("retry")`
**When** DAPR processes the retry
**Then** it follows the exponential backoff policy
**And** after 3 failures, the event goes to DLQ

**Unit Tests Required:**
- N/A (YAML configuration, validated by E2E)

**E2E Test Impact:**
- PoC at `tests/e2e/poc-dapr-patterns/` validates retry behavior
- Extend PoC to verify retry count and timing

**Story Points:** 2

---

### Story 0.6.8: Dead Letter Queue Handler

**[📄 Story File](../sprint-artifacts/0-6-8-dead-letter-queue-handler.md)** | Status: To Do

As a **platform engineer**,
I want a DLQ handler that stores failed events in MongoDB,
So that failed events are visible and can be replayed after fixes.

**ADR:** ADR-006 - Event Delivery and Dead Letter Queue

**Acceptance Criteria:**

**Given** events may fail permanently
**When** an event is sent to `events.dlq` topic
**Then** the DLQ handler receives it via streaming subscription

**Given** the DLQ handler receives a failed event
**When** it processes the event
**Then** it stores the event in MongoDB `event_dead_letter` collection
**And** includes: original topic, event data, received_at, status
**And** increments `event_dead_letter_total` metric for alerting

**Given** failed events are stored
**When** I query the `event_dead_letter` collection
**Then** I can see all failed events with their original context
**And** status is initially "pending_review"

**Unit Tests Required:**
- `tests/unit/fp_common/events/test_dlq_handler.py`
  - `test_dlq_handler_stores_event_in_mongodb`
  - `test_dlq_handler_increments_metric`
  - `test_dlq_handler_extracts_original_topic`

**E2E Test Impact:**
- PoC at `tests/e2e/poc-dapr-patterns/` validates DLQ flow
- Extend to verify MongoDB storage

**Story Points:** 3

---

## Wave 3 Stories (Domain Logic)

> **Prerequisite:** Wave 2 complete. Wave 3 stories depend on:
> - Story 0.6.8 (DLQ Handler) - For handling validation failures
> - Story 0.6.5/0.6.6 (Streaming Subscriptions) - For event processing

### Story 0.6.9: Source Config Cache with MongoDB Change Streams

**[📄 Story File](../sprint-artifacts/0-6-9-source-config-cache-change-streams.md)** | Status: To Do

As a **platform engineer**,
I want source config cache to use MongoDB Change Streams for real-time invalidation,
So that new configs are immediately available without 5-minute stale windows.

**ADR:** ADR-007 - Source Config Cache with Change Streams

**Acceptance Criteria:**

**Given** the service is starting up
**When** the service reaches ready state
**Then** the source config cache is warmed with all configs from MongoDB
**And** a metric `source_config_cache_size` shows the count

**Given** the cache is warm
**When** an operator creates/updates/deletes a source config
**Then** MongoDB Change Stream fires within milliseconds
**And** the cache is invalidated immediately
**And** a metric `source_config_cache_invalidations_total` is incremented

**Given** a blob event arrives
**When** the source config is looked up
**Then** it's found in the warm cache (cache hit)
**Or** loaded fresh if cache was just invalidated (cache miss)
**And** metrics track cache hit/miss ratio

**Given** the Change Stream connection is lost
**When** the watcher reconnects
**Then** it resumes from the last resume token
**And** no invalidations are missed

**Unit Tests Required:**
- `tests/unit/collection_model/services/test_source_config_service.py`
  - `test_cache_warmed_on_startup`
  - `test_change_stream_invalidates_on_insert`
  - `test_change_stream_invalidates_on_update`
  - `test_change_stream_invalidates_on_delete`
  - `test_cache_metrics_tracked`

**E2E Test Impact:**
- Add cache verification to existing E2E tests
- Verify no silent event drops due to stale cache

**Story Points:** 5

---

### Story 0.6.10: Linkage Field Validation with Metrics

**[📄 Story File](../sprint-artifacts/0-6-10-linkage-field-validation.md)** | Status: To Do

As a **platform engineer**,
I want all linkage field validation failures to raise exceptions with metrics,
So that invalid events go to DLQ and trigger alerts instead of silent data loss.

**ADR:** ADR-008 - Invalid Linkage Field Handling

**Acceptance Criteria:**

**Given** a quality event has an invalid `farmer_id`
**When** `QualityEventProcessor.process()` is called
**Then** an exception is raised with type `farmer_not_found`
**And** metric `event_linkage_validation_failures_total{field=farmer_id}` is incremented
**And** the event is retried then sent to DLQ

**Given** a quality event has an invalid `factory_id`
**When** `QualityEventProcessor.process()` is called
**Then** an exception is raised with type `factory_not_found`
**And** metric `event_linkage_validation_failures_total{field=factory_id}` is incremented

**Given** a quality event has an invalid `grading_model_id`
**When** `QualityEventProcessor.process()` is called
**Then** an exception is raised with type `grading_model_not_found`
**And** metric `event_linkage_validation_failures_total{field=grading_model_id}` is incremented

**Given** a quality event has an invalid `region_id` (via farmer)
**When** `QualityEventProcessor.process()` is called
**Then** an exception is raised with type `region_not_found`
**And** metric `event_linkage_validation_failures_total{field=region_id}` is incremented

**Given** all linkage fields are valid
**When** `QualityEventProcessor.process()` is called
**Then** the event is processed successfully
**And** no validation failure metrics are incremented

**Unit Tests Required:**
- `tests/unit/plantation_model/services/test_quality_event_processor.py`
  - `test_invalid_farmer_id_raises_and_increments_metric`
  - `test_invalid_factory_id_raises_and_increments_metric`
  - `test_invalid_grading_model_id_raises_and_increments_metric`
  - `test_invalid_region_id_raises_and_increments_metric`
  - `test_valid_linkage_fields_no_metric`

**E2E Test Impact:**
- Events with invalid linkage should appear in DLQ
- Metrics should be queryable for alerting tests

**Story Points:** 3

---

## Wave 4 Stories (Type Safety at MCP Boundary)

> **Context:** MCP server infrastructure clients currently return `dict[str, Any]` with manual `_to_dict()`
> conversion methods. This creates field mapping drift between Proto definitions, Pydantic models,
> and MCP responses. These stories centralize Proto-to-Pydantic conversion in fp-common and refactor
> MCP clients to return typed Pydantic models.

### Story 0.6.11: Proto-to-Pydantic Converters in fp-common

**[📄 Story File](../sprint-artifacts/0-6-11-proto-to-pydantic-converters.md)** | Status: To Do

As a **developer maintaining MCP servers**,
I want Proto-to-Pydantic conversion functions centralized in fp-common,
So that field mappings are defined once and reused by both services and MCP clients.

**ADR:** ADR-004 - Type Safety Architecture (extension)

**Acceptance Criteria:**

**Given** Plantation proto messages exist
**When** I check `libs/fp-common/fp_common/converters/`
**Then** I find `plantation_converters.py` with:
  - `farmer_from_proto(proto: plantation_pb2.Farmer) -> Farmer`
  - `factory_from_proto(proto: plantation_pb2.Factory) -> Factory`
  - `region_from_proto(proto: plantation_pb2.Region) -> Region`
  - `farmer_summary_from_proto(proto: plantation_pb2.FarmerSummary) -> FarmerSummary`
  - `collection_point_from_proto(proto: plantation_pb2.CollectionPoint) -> CollectionPoint`

**Given** converters are in fp-common
**When** MCP client imports them
**Then** `from fp_common.converters import farmer_from_proto` works
**And** conversion logic is identical to what's currently in `_farmer_to_dict()`

**Unit Tests Required:**
- `tests/unit/fp_common/converters/test_plantation_converters.py`
  - Round-trip: proto → pydantic → model_dump() produces expected dict
  - Edge cases: optional fields, nested messages, enums

**Story Points:** 3

---

### Story 0.6.12: MCP Clients Return Pydantic Models (Option B)

**[📄 Story File](../sprint-artifacts/0-6-12-mcp-clients-pydantic-models.md)** | Status: To Do

As a **developer consuming MCP server responses**,
I want MCP infrastructure clients to return Pydantic models instead of dicts,
So that I have type safety and IDE autocomplete throughout the call chain.

**ADR:** ADR-004 - Type Safety Architecture (extension)

**Acceptance Criteria:**

**Given** `PlantationClient` currently returns `dict[str, Any]`
**When** I refactor `mcp-servers/plantation-mcp/src/plantation_mcp/infrastructure/plantation_client.py`
**Then** methods return Pydantic models:
  - `get_farmer() -> Farmer`
  - `get_factory() -> Factory`
  - `get_region() -> Region`
  - `get_farmer_summary() -> FarmerSummary`
  - `get_collection_points() -> list[CollectionPoint]`
**And** manual `_*_to_dict()` methods are removed
**And** converters from `fp_common.converters` are used instead

**Given** MCP tool handlers receive Pydantic models
**When** they serialize for JSON response
**Then** they call `model.model_dump()` at the boundary
**And** field names match Proto/Pydantic definitions (no drift)

**Given** collection-mcp infrastructure clients exist
**When** I check `source_config_client.py` and `document_client.py`
**Then** they return Pydantic models where applicable
**Or** remain dict-based for dynamic MongoDB documents (acceptable)

**Unit Tests Required:**
- `tests/unit/plantation_mcp/infrastructure/test_plantation_client.py`
  - Verify return types are Pydantic models
  - Verify model_dump() produces expected JSON structure

**E2E Test Impact:**
- Existing E2E tests should pass unchanged (JSON output identical)
- Type safety is internal improvement, no API changes

**Story Points:** 5

---

### Story 0.6.13: Replace CollectionClient Direct DB Access with gRPC

**[📄 Story File](../sprint-artifacts/0-6-13-collection-client-grpc.md)** | Status: To Do

As a **platform engineer**,
I want Plantation Model to fetch documents from Collection Model via gRPC instead of direct MongoDB access,
So that domain boundaries are respected and services communicate through proper DAPR channels.

**ADR:** ADR-010/011 - DAPR Patterns and Service Architecture

**Context:**
`plantation_model/infrastructure/collection_client.py` currently connects directly to Collection Model's MongoDB
to fetch quality documents during event processing. This violates the "ALL inter-service communication via DAPR"
rule and creates tight coupling to Collection Model's internal schema.

Collection Model already exposes `GetDocument` via gRPC (proto/collection/v1/collection.proto:22).

**Acceptance Criteria:**

**Given** `CollectionClient` accesses MongoDB directly
**When** I check `services/plantation-model/src/plantation_model/infrastructure/collection_client.py`
**Then** it uses `AsyncIOMotorClient` to connect to `collection_mongodb_uri`

**Given** the migration is complete
**When** I check the updated implementation
**Then** a new `CollectionGrpcClient` exists that:
  - Calls Collection Model's `GetDocument` RPC via DAPR service invocation
  - Uses singleton channel pattern with retry (matching Story 0.6.3/0.6.4 pattern)
  - Returns Pydantic model (consistent with Story 0.6.12)

**Given** `QualityEventProcessor` needs a document
**When** it calls `get_document(document_id)`
**Then** the request flows: Plantation Model → DAPR → Collection Model gRPC → MongoDB
**And** no direct MongoDB connection exists from Plantation Model to Collection Model DB

**Given** the old client is removed
**When** I check plantation-model settings
**Then** `collection_mongodb_uri` and `collection_mongodb_database` are removed
**And** `collection_app_id` (DAPR app ID) is used instead

**Unit Tests Required:**
- `tests/unit/plantation_model/infrastructure/test_collection_grpc_client.py`
  - `test_get_document_calls_grpc` - Verify gRPC call, not MongoDB
  - `test_retry_on_unavailable` - Retry triggers on UNAVAILABLE status
  - `test_document_not_found_raises` - Proper error propagation

**E2E Test Impact:**
- E2E tests should pass unchanged (behavior identical, only transport changes)
- Remove `COLLECTION_MONGODB_URI` from plantation-model E2E config

**Story Points:** 3

---

## Summary

### Wave 1: Foundation (12 points)

| Story | Description | ADR | Points | Status |
|-------|-------------|-----|--------|--------|
| 0.6.1 | Shared Pydantic Models | ADR-004 | 5 | To Do |
| 0.6.2 | Shared Logging Module | ADR-009 | 3 | To Do |
| 0.6.3 | AiModelClient Retry | ADR-005 | 2 | To Do |
| 0.6.4 | IterationResolver Retry | ADR-005 | 2 | To Do |
| **Wave 1 Total** | | | **12** | |

### Wave 2: DAPR SDK Migration (15 points)

| Story | Description | ADR | Points | Status |
|-------|-------------|-----|--------|--------|
| 0.6.5 | Plantation Streaming Subs | ADR-010/011 | 5 | To Do |
| 0.6.6 | Collection Streaming Subs | ADR-010/011 | 5 | To Do |
| 0.6.7 | DAPR Resiliency Config | ADR-006 | 2 | To Do |
| 0.6.8 | Dead Letter Queue Handler | ADR-006 | 3 | To Do |
| **Wave 2 Total** | | | **15** | |

### Wave 3: Domain Logic (8 points)

| Story | Description | ADR | Points | Status |
|-------|-------------|-----|--------|--------|
| 0.6.9 | Source Config Cache + Change Streams | ADR-007 | 5 | To Do |
| 0.6.10 | Linkage Field Validation + Metrics | ADR-008 | 3 | To Do |
| **Wave 3 Total** | | | **8** | |

### Wave 4: Type Safety & Service Boundaries (11 points)

| Story | Description | ADR | Points | Status |
|-------|-------------|-----|--------|--------|
| 0.6.11 | Proto-to-Pydantic Converters | ADR-004 | 3 | To Do |
| 0.6.12 | MCP Clients Return Pydantic Models | ADR-004 | 5 | To Do |
| 0.6.13 | Replace CollectionClient Direct DB with gRPC | ADR-010/011 | 3 | To Do |
| **Wave 4 Total** | | | **11** | |

### Epic Total: 46 Story Points (Wave 1: 12 + Wave 2: 15 + Wave 3: 8 + Wave 4: 11)

## Testing Strategy

### Unit Tests (Per Story)
Each story includes specific unit test requirements. Tests must:
- Be placed in `tests/unit/{package}/` matching source structure
- Use fixtures from `tests/conftest.py` (DO NOT override)
- Run with `pytest tests/unit/ -v`

### E2E Test Verification
After each story:
```bash
# Run full E2E suite to verify no regressions
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```

### PoC Validation
Wave 1 (Stories 0.6.3-0.6.4) and Wave 2 (all stories) are validated by existing PoC:
```bash
cd tests/e2e/poc-dapr-patterns
docker compose up --build -d
python run_tests.py  # All 5 tests should pass
docker compose down -v
```

**PoC Test Coverage:**

| Test | Stories Validated |
|------|-------------------|
| gRPC Echo | 0.6.3, 0.6.4 |
| gRPC Calculator | 0.6.3, 0.6.4 |
| Pub/Sub Success | 0.6.5, 0.6.6 |
| Pub/Sub Retry | 0.6.5, 0.6.6, 0.6.7 |
| Pub/Sub DLQ | 0.6.7, 0.6.8 |

## CI Requirements

All stories must pass CI before merge:
1. `ruff check . && ruff format --check .`
2. `pytest tests/unit/ -v` (unit tests)
3. GitHub Actions CI workflow (on feature branch)

## Definition of Done

### Wave 1
- [ ] Stories 0.6.1-0.6.4 implemented and merged
- [ ] All unit tests pass
- [ ] E2E test suite passes (no regressions)
- [ ] CI pipelines green on all PRs
- [ ] ADR-004, ADR-005, ADR-009 marked as "Implemented"

### Wave 2
- [ ] Stories 0.6.5-0.6.8 implemented and merged
- [ ] All unit tests pass
- [ ] E2E test suite passes (no regressions)
- [ ] PoC tests all pass (5/5)
- [ ] CI pipelines green on all PRs
- [ ] ADR-006, ADR-010, ADR-011 marked as "Implemented"

### Wave 3
- [ ] Stories 0.6.9-0.6.10 implemented and merged
- [ ] All unit tests pass
- [ ] E2E test suite passes (no regressions)
- [ ] Cache metrics visible in observability stack
- [ ] Linkage validation metrics visible in observability stack
- [ ] CI pipelines green on all PRs
- [ ] ADR-007, ADR-008 marked as "Implemented"

### Wave 4
- [ ] Stories 0.6.11-0.6.13 implemented and merged
- [ ] All unit tests pass
- [ ] E2E test suite passes (no regressions)
- [ ] MCP clients return Pydantic models (type-safe)
- [ ] Manual `_to_dict()` methods removed from plantation_client.py
- [ ] Proto-to-Pydantic converters centralized in fp-common
- [ ] Plantation Model fetches documents via gRPC, not direct MongoDB
- [ ] `collection_mongodb_uri` removed from plantation-model settings
- [ ] CI pipelines green on all PRs

---

## Retrospective

**[📄 Epic 0.6 Retrospective (2026-01-02)](../sprint-artifacts/epic-0-6-retro-2026-01-02.md)**

**Key Outcomes:**
- All 10 stories completed (35/35 story points)
- 8 ADRs implemented (ADR-004 through ADR-011)
- ~180 unit tests added
- Key learning: DAPR streaming handlers run in separate threads - use `asyncio.run_coroutine_threadsafe()` for async operations

---

**Total Story Points:** 46 (Wave 1: 12 + Wave 2: 15 + Wave 3: 8 + Wave 4: 11)

**Estimated Duration:** 4 sprints (1 sprint per wave)
