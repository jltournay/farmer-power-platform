  # Story 2-12: Collection → AI Model Event-Driven Communication

**Epic:** Epic 2 - Quality Data Ingestion
**Status:** in-progress
**Blocks:** Story 0.75.18 (E2E Weather Observation Extraction Flow)
**GitHub Issue:** #81
**Story Points:** 5

---

## User Story

As a **platform developer**,
I want Collection Model to communicate with AI Model via async events instead of synchronous gRPC,
So that the system follows the architecture specification and scales properly.

---

## Context

The current Collection Model implementation uses **synchronous gRPC calls** to AI Model via `AiModelClient`, but the architecture specifies **event-driven async communication** via DAPR Pub/Sub.

**Architecture Reference:** `_bmad-output/architecture/ai-model-architecture.md` § *Event Flow Example - Quality Document Processing*

### Scope: json_extraction.py Only

| Processor | AI Extraction? | Changes Needed |
|-----------|----------------|----------------|
| `json_extraction.py` | ✅ Yes (when `ai_agent_id` configured) | **This story** - change sync gRPC to async events |
| `zip_extraction.py` | ❌ No (always direct extraction) | No changes - already "Path B" |

**Current implementation in `json_extraction.py` (line 314):**
```python
ai_agent_id = transformation.get_ai_agent_id()

if not ai_agent_id:
    # Path B: Direct extraction (no AI) - NO CHANGES NEEDED
    extracted = {field: json_data[field] for field in extract_fields}
else:
    # Path A: Sync gRPC call - THIS CHANGES TO ASYNC EVENTS
    response = await self._ai_client.extract(request)  # ← Remove this
```

### Event Flow (Path A - AI Extraction)
```
1. Collection stores document with status="pending" → document_id
2. Collection publishes: "ai.agent.requested" with request_id=document_id
3. AI Model subscribes, executes workflow via AgentExecutor
4. AI Model publishes: "ai.agent.{agent_id}.completed" or "ai.agent.{agent_id}.failed"
5. Collection subscribes, updates document, then publishes success event
```

**Key Design Decisions:**
- **Shared Event Models:** Event models are in `fp_common.events.ai_model_events` (Story 0.75.16b)
- **Dynamic Topic Names:** AI Model publishes to `ai.agent.{agent_id}.completed` - Collection subscribes using the `agent_id` it sent
- **Correlation Strategy (Option A):** `request_id` = `document_id` - Collection stores document first, then uses document ID as request_id. When AI Model responds, Collection looks up document by `event.request_id`
- **EntityLinkage:** Contains Plantation Model entities (`farmer_id`, `region_id`, etc.) for result routing - NOT `document_id`
- **Source Field:** `source="collection-model"` is REQUIRED in AgentRequestEvent

---

## Acceptance Criteria

1. **AC1: Shared Event Models** - Collection Model imports all event models (`AgentRequestEvent`, `AgentCompletedEvent`, `AgentFailedEvent`, `EntityLinkage`) from `fp_common.events.ai_model_events` and topic helpers from `fp_common.models.domain_events`. No duplicate event model definitions exist in Collection Model.

2. **AC2: Conditional AI Extraction** - When `source_config.ai_extraction.enabled=true`, document is stored with `status="pending"` and `AgentRequestEvent` is published (Path A). When disabled, document is stored with `status="complete"` immediately with no event published (Path B).

3. **AC3: Event Subscription for AI Results** - Collection Model subscribes to `ai.agent.{agent_id}.completed` and `ai.agent.{agent_id}.failed` topics. Success handler updates document with extracted fields and publishes success event. Failure handler marks document as failed with error details. Correlation uses `request_id = document_id`.

4. **AC4: Document Ready Event** - After document is fully processed (Path A: after AI completion, Path B: after direct storage), a success event is published to the topic configured in `source_config.events.on_success.topic` using existing `DaprEventPublisher.publish_success()`.

5. **AC5: Remove Synchronous gRPC** - `AiModelClient.extract()` method is removed or deprecated. No synchronous gRPC calls remain for extraction workflow. MCP query methods retained if needed.

6. **AC6: Unit Tests** - Path A tests verify pending storage, event publishing, and result handling. Path B tests verify direct storage with no event published. All tests use mocked event bus.

7. **AC7: E2E Regression** - All existing E2E tests continue to pass with `--build` flag.

8. **AC8: CI Passes** - All lint checks and tests pass in CI.

---

## Tasks / Subtasks

- [ ] **Task 1: Import Shared Event Models** (AC: #1)
  - [ ] Add imports from `fp_common.events.ai_model_events`: `AgentRequestEvent`, `AgentCompletedEvent`, `AgentFailedEvent`, `EntityLinkage`
  - [ ] Add imports from `fp_common.models.domain_events`: `AIModelEventTopic`
  - [ ] Remove any duplicate event model definitions in Collection Model

- [ ] **Task 2: Implement Path A - AI Extraction Flow** (AC: #2)
  - [ ] Update `json_extraction.py` to check `source_config.ai_extraction.enabled` and `agent_id`
  - [ ] Store document with `extraction.status = "pending"` and empty `extracted_fields`
  - [ ] Build `AgentRequestEvent` with `request_id` = `document_id` (correlation key)
  - [ ] Set `agent_id` from source config
  - [ ] Set `linkage` with `EntityLinkage` (farmer_id, region_id, etc.)
  - [ ] Set `input_data` with document content
  - [ ] Set `source` = `"collection-model"`
  - [ ] Publish event to `ai.agent.requested` topic via DAPR pub/sub

- [ ] **Task 3: Implement Path B - Direct Storage Flow** (AC: #2)
  - [ ] Store document with `extraction.status = "complete"` immediately
  - [ ] Populate `extracted_fields` from input data or transformation rules
  - [ ] Set `extraction.ai_agent_id = null` and `extraction.confidence = 1.0`
  - [ ] Publish success event if configured in `source_config.events.on_success`
  - [ ] Ensure NO `AgentRequestEvent` is published

- [ ] **Task 4: Implement Event Subscription Handlers** (AC: #3)
  - [ ] Register subscriptions for `ai.agent.{agent_id}.completed` and `.failed` topics
  - [ ] Use `AIModelEventTopic.agent_completed_topic(agent_id)` helper for topic names
  - [ ] Implement `_handle_extraction_completed()`:
    - [ ] Find document by `event.request_id` (= document_id)
    - [ ] Update `extraction.status = "complete"`
    - [ ] Copy `extracted_fields` from `event.result`
    - [ ] Set `ai_agent_id`, `validation_passed`, `validation_warnings`
    - [ ] Save document
    - [ ] Call `_emit_success_event(document, source_config)`
  - [ ] Implement `_handle_extraction_failed()`:
    - [ ] Find document by `event.request_id`
    - [ ] Update `extraction.status = "failed"`
    - [ ] Store `error_message` and `error_type`
    - [ ] Save document and log for monitoring
  - [ ] Follow dead letter queue pattern (ADR-006)

- [ ] **Task 5: Publish Document Ready Event** (AC: #4)
  - [ ] Ensure success event published after Path A completion (in handler)
  - [ ] Ensure success event published after Path B direct storage
  - [ ] Use topic from `source_config.events.on_success.topic`
  - [ ] Include payload: `document_id`, `source_id`, `farmer_id`, `region_id`, `extracted_fields`
  - [ ] Reuse existing `DaprEventPublisher.publish_success()` method

- [ ] **Task 6: Remove Synchronous gRPC Extraction** (AC: #5)
  - [ ] Remove or deprecate `AiModelClient.extract()` method
  - [ ] Remove sync gRPC call in `json_extraction.py` (line ~314)
  - [ ] Retain MCP query methods if needed for other use cases
  - [ ] Update any imports/references

- [ ] **Task 7: Unit Tests** (AC: #6)
  - [ ] Test Path A: `ai_extraction.enabled=true` triggers `AgentRequestEvent`
  - [ ] Test Path A: document stored with `status="pending"` before publishing
  - [ ] Test Path A: `AgentCompletedEvent` handler updates document correctly
  - [ ] Test Path A: `AgentFailedEvent` handler marks document as failed
  - [ ] Test Path A: `request_id` equals `document_id` for correlation
  - [ ] Test Path B: `ai_extraction.enabled=false` stores directly
  - [ ] Test Path B: document stored with `status="complete"` immediately
  - [ ] Test Path B: NO `AgentRequestEvent` published
  - [ ] Test Path B: success event published if configured
  - [ ] Use mock event bus for all tests

- [ ] **Task 8: E2E Regression Testing (MANDATORY)** (AC: #7)
  - [ ] Rebuild and start E2E infrastructure with `--build` flag
  - [ ] Verify Docker images were rebuilt (NOT cached)
  - [ ] Run full E2E test suite
  - [ ] Capture output in "Local Test Run Evidence" section
  - [ ] Tear down infrastructure

- [ ] **Task 9: CI Verification** (AC: #8)
  - [ ] Run lint: `ruff check . && ruff format --check .`
  - [ ] Run unit tests locally
  - [ ] Push and verify CI passes
  - [ ] Trigger E2E CI workflow: `gh workflow run e2e.yaml --ref <branch>`
  - [ ] Verify E2E CI passes before code review

---

## Technical Notes

### Event Models (from fp_common - Story 0.75.16b)

All event models are shared via `fp_common`. **DO NOT duplicate these in Collection Model.**

```python
# Event payload models
from fp_common.events.ai_model_events import (
    AgentRequestEvent,
    AgentCompletedEvent,
    AgentFailedEvent,
    EntityLinkage,
)

# Topic name helpers (StrEnum)
from fp_common.models.domain_events import AIModelEventTopic
```

**EntityLinkage** - Links to Plantation Model entities (NOT Collection entities):
```python
class EntityLinkage(BaseModel):
    """Linkage to Plantation Model entities - at least one field required."""
    farmer_id: str | None = None        # Link to specific farmer (most common)
    region_id: str | None = None        # Link to region (weather, trends)
    group_id: str | None = None         # Link to farmer group (broadcasts)
    collection_point_id: str | None = None  # Link to collection point
    factory_id: str | None = None       # Link to processing factory
```

**IMPORTANT:** `EntityLinkage` does NOT include `document_id`. Collection Model uses `request_id` to correlate responses back to documents.

### Correlation Strategy (Option A: request_id = document_id)

```
1. Collection stores document → gets document_id
2. Collection publishes AgentRequestEvent with request_id = document_id
3. AI Model processes and responds with same request_id
4. Collection receives response, looks up document: document_repo.get_by_id(event.request_id)
```

**Why this works:**
- No separate correlation table needed
- Direct document lookup by ID (fast)
- EntityLinkage carries Plantation entities for result routing (farmer_id, region_id, etc.)
- request_id carries the document correlation

**AgentRequestEvent** - Published by Collection to request AI processing:
```python
class AgentRequestEvent(BaseModel):
    """Event for requesting agent execution."""
    request_id: str                      # Use document_id as correlation key
    agent_id: str                        # e.g., "qc-event-extractor"
    linkage: EntityLinkage               # Links to Plantation Model entities
    input_data: dict[str, Any]           # Data for the agent
    source: str                          # REQUIRED: "collection-model"
    source_service: str | None = None    # Optional: explicit service name
```

**AgentCompletedEvent** - Received by Collection on success:
```python
class AgentCompletedEvent(BaseModel):
    """Event published when agent execution succeeds."""
    request_id: str                      # Correlates to original request (= document_id)
    agent_id: str
    linkage: EntityLinkage               # SAME linkage from request (passthrough)
    result: AgentResult                  # Discriminated union of typed results
    execution_time_ms: int
    model_used: str
    cost_usd: Decimal | None = None      # Total cost in USD
```

**AgentFailedEvent** - Received by Collection on failure:
```python
class AgentFailedEvent(BaseModel):
    """Event published when agent execution fails."""
    request_id: str                      # Correlates to original request (= document_id)
    agent_id: str
    linkage: EntityLinkage               # SAME linkage from request (passthrough)
    error_type: str                      # Error category (validation, llm_error, timeout, etc.)
    error_message: str
    retry_count: int = 0
```

### Topic Names

| Direction | Topic | Helper |
|-----------|-------|--------|
| Collection → AI Model | `ai.agent.requested` | `AIModelEventTopic.AGENT_REQUESTED` |
| AI Model → Collection (success) | `ai.agent.{agent_id}.completed` | `AIModelEventTopic.agent_completed_topic(agent_id)` |
| AI Model → Collection (failure) | `ai.agent.{agent_id}.failed` | `AIModelEventTopic.agent_failed_topic(agent_id)` |

**Example:** If Collection uses `agent_id = "qc-event-extractor"`:
- Publishes to: `ai.agent.requested`
- Subscribes to: `ai.agent.qc-event-extractor.completed`
- Subscribes to: `ai.agent.qc-event-extractor.failed`

### Publishing Example (Collection Model)

```python
from fp_common.events.ai_model_events import (
    AgentRequestEvent,
    EntityLinkage,
)
from fp_common.models.domain_events import AIModelEventTopic

async def request_extraction(document: Document, source_config: SourceConfig) -> None:
    """Publish agent request after document storage.

    IMPORTANT: request_id = document_id for correlation (Option A).
    When AI Model responds, Collection uses request_id to find the document.
    """
    event = AgentRequestEvent(
        request_id=str(document.id),  # Use document_id as correlation key
        agent_id=source_config.ai_extraction.agent_id,
        linkage=EntityLinkage(
            farmer_id=document.farmer_id,      # From document metadata
            region_id=document.region_id,      # Optional: for weather data
        ),
        input_data={
            "text": document.raw_text,
            "image_url": document.thumbnail_url,
        },
        source="collection-model",  # REQUIRED field
    )

    await dapr_client.publish_event(
        pubsub_name="pubsub",
        topic_name=AIModelEventTopic.AGENT_REQUESTED,
        data=event.model_dump_json(),
    )
```

### Subscription Example (Collection Model)

**Note:** The `agent_id` comes from source config. Collection Model subscribes to result topics
for each agent_id used across all source configs.

```python
from fp_common.events.ai_model_events import (
    AgentCompletedEvent,
    AgentFailedEvent,
)
from fp_common.models.domain_events import AIModelEventTopic

# Dynamic subscription based on source configs
# Each source_config.ai_extraction.agent_id needs subscriptions
# Example: if source configs use "weather-extractor" and "qc-event-extractor",
# subscribe to both: ai.agent.weather-extractor.completed, ai.agent.qc-event-extractor.completed

def register_agent_subscriptions(app, source_config_cache: SourceConfigCache):
    """Register subscriptions for all agent_ids in source configs."""
    agent_ids = source_config_cache.get_all_agent_ids()  # e.g., ["weather-extractor"]

    for agent_id in agent_ids:
        # Register completed handler
        @app.subscribe(
            pubsub="pubsub",
            topic=AIModelEventTopic.agent_completed_topic(agent_id),
        )
        async def handle_completed(event_data: dict) -> None:
            await _handle_extraction_completed(event_data)

        # Register failed handler
        @app.subscribe(
            pubsub="pubsub",
            topic=AIModelEventTopic.agent_failed_topic(agent_id),
        )
        async def handle_failed(event_data: dict) -> None:
            await _handle_extraction_failed(event_data)


async def _handle_extraction_completed(event_data: dict) -> None:
    """Handle successful extraction result.

    IMPORTANT: request_id = document_id (Option A correlation).
    """
    event = AgentCompletedEvent.model_validate(event_data)

    # Use request_id to find document (request_id = document_id)
    document = await document_repo.get_by_id(event.request_id)

    # Update document with extracted fields
    document.extraction.status = "complete"
    document.extraction.extracted_fields = event.result.extracted_fields
    document.extraction.ai_agent_id = event.agent_id
    document.extraction.validation_passed = len(event.result.validation_errors) == 0
    await document_repo.save(document)

    # Publish success event for downstream services
    await _emit_success_event(document)


async def _handle_extraction_failed(event_data: dict) -> None:
    """Handle extraction failure.

    IMPORTANT: request_id = document_id (Option A correlation).
    """
    event = AgentFailedEvent.model_validate(event_data)

    # Use request_id to find document (request_id = document_id)
    document = await document_repo.get_by_id(event.request_id)
    document.extraction.status = "failed"
    document.extraction.error_message = event.error_message
    document.extraction.error_type = event.error_type
    await document_repo.save(document)
```

### Files to Modify

| File | Change |
|------|--------|
| `processors/json_extraction.py` | **Main change:** Replace sync `_call_ai_model()` with async event flow for Path A |
| `processors/json_extraction.py` | Split processing: store pending → publish event → (later) receive result |
| `infrastructure/ai_model_client.py` | Remove/deprecate `extract()` method |
| `infrastructure/dapr_event_publisher.py` | Add `publish_agent_request()` method for `AgentRequestEvent` |
| `application/event_handlers.py` | **NEW:** Add `handle_extraction_completed/failed()` handlers |
| `dapr/subscriptions.py` | Register subscriptions for `ai.agent.{agent_id}.completed/failed` topics |

### Files NOT Modified

| File | Reason |
|------|--------|
| `processors/zip_extraction.py` | No AI extraction - always direct (Path B) |
| `infrastructure/dapr_event_publisher.py` `publish_success()` | Already exists and works correctly |

---

## Dependencies

| Depends On | Reason |
|------------|--------|
| Story 0.75.16b | Event models moved to fp-common, AgentExecutor wired |
| Story 0.75.17 | Sample Extractor agent deployed and tested |
| Story 0.75.8 | DAPR pub/sub infrastructure in AI Model |

| Blocks | Reason |
|--------|--------|
| Story 0.75.18 | E2E validation requires async event flow |

---

## Sequence Diagram

```
┌─────────────┐       ┌──────────────┐       ┌──────────────┐
│  Collection │       │    DAPR      │       │   AI Model   │
│    Model    │       │   Pub/Sub    │       │              │
└──────┬──────┘       └──────┬───────┘       └──────┬───────┘
       │                     │                      │
       │ 1. Store document   │                      │
       │─────────────────────│                      │
       │                     │                      │
       │ 2. Publish AgentRequestEvent               │
       │   topic: ai.agent.requested                │
       │   {request_id, agent_id, linkage, input}   │
       │────────────────────>│                      │
       │                     │                      │
       │                     │ 3. Deliver to subscriber
       │                     │─────────────────────>│
       │                     │                      │
       │                     │      4. AgentExecutor.execute()
       │                     │      - Load config & prompt
       │                     │      - Run workflow
       │                     │      - LLM extraction
       │                     │                      │
       │                     │ 5. Publish AgentCompletedEvent
       │                     │   topic: ai.agent.{agent_id}.completed
       │                     │   {request_id, linkage, result}
       │                     │<─────────────────────│
       │                     │                      │
       │ 6. Deliver to handler                      │
       │<────────────────────│                      │
       │                     │                      │
       │ 7. Update document  │                      │
       │   using request_id (= document_id)         │
       │─────────────────────│                      │
       │                     │                      │
```

---

## Out of Scope

- Thumbnail generation (see Story 2-13)
- AI Model implementation (Epic 0.75)
- E2E testing (Story 0.75.18)

---

## Anti-Patterns to AVOID

1. **DO NOT duplicate event models** - Import from `fp_common.events.ai_model_events`
2. **DO NOT hardcode topic names** - Use `AIModelEventTopic` from `fp_common.models.domain_events`
3. **DO NOT use random UUIDs for request_id** - Use `document_id` as `request_id` for correlation
4. **DO NOT use synchronous waits** - Event-driven means fire-and-forget publishing
5. **DO NOT forget failure handling** - Subscribe to both `.completed` AND `.failed` topics

---

_Created: 2026-01-05_
_Last Updated: 2026-01-09_ (Restructured: ACs as testable statements, added Tasks/Subtasks section with AC references, flattened nested lists to checkboxes)
