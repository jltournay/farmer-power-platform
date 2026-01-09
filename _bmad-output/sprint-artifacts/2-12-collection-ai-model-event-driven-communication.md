  # Story 2-12: Collection → AI Model Event-Driven Communication

**Epic:** Epic 2 - Quality Data Ingestion
**Status:** ready-for-dev
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

### AC-1: Import Shared Event Models from fp-common
- [ ] Import event models from `fp_common.events.ai_model_events`:
  - `AgentRequestEvent` - for publishing requests
  - `AgentCompletedEvent` - for handling successful results
  - `AgentFailedEvent` - for handling failures
  - `EntityLinkage` - for linking to Plantation Model entities (farmer, region, etc.)
- [ ] Import topic helpers from `fp_common.models.domain_events`:
  - `AIModelEventTopic` - for topic name helpers (StrEnum with static methods)
- [ ] NO duplicate event model definitions in Collection Model

### AC-2: Conditional AI Extraction Based on Source Config
- [ ] **Check source config for AI extraction requirement:**
  ```python
  if source_config.ai_extraction.enabled and source_config.ai_extraction.agent_id:
      # Path A: AI extraction required
  else:
      # Path B: Direct storage (no AI)
  ```

- [ ] **Path A: AI Extraction Required**
  - Store document with `extraction.status = "pending"`
  - `extracted_fields = {}` (empty, will be filled by AI)
  - Publish `AgentRequestEvent` to topic `ai.agent.requested`
  - Event includes all required fields:
    - `request_id`: Use `document_id` as correlation key
    - `agent_id`: From `source_config.ai_extraction.agent_id`
    - `linkage`: `EntityLinkage` with plantation entities (`farmer_id`, `region_id`, etc.)
    - `input_data`: Data for the agent (e.g., `{"text": "...", "image_url": "..."}`)
    - `source`: `"collection-model"` (observability)
  - Event published via DAPR pub/sub component

- [ ] **Path B: Direct Storage (No AI Extraction)**
  - Store document with `extraction.status = "complete"`
  - `extracted_fields` populated from input data directly (or transformation rules)
  - `extraction.ai_agent_id = "none"` or `null`
  - `extraction.confidence = 1.0` (no AI uncertainty)
  - Publish success event if configured in `source_config.events.on_success`
  - **NO AgentRequestEvent published**

### AC-3: Event Subscription for AI Results (Path A only)
- [ ] Collection Model subscribes to `ai.agent.{agent_id}.completed` for each agent it uses
- [ ] Collection Model subscribes to `ai.agent.{agent_id}.failed` for error handling
- [ ] Use `AIModelEventTopic.agent_completed_topic(agent_id)` helper for topic names
- [ ] **Correlation via request_id = document_id:**
  - `request_id` IS the `document_id` (no separate mapping needed)
  - Lookup document directly: `document_repo.get_by_id(event.request_id)`
- [ ] **Success handler (`AgentCompletedEvent`):**
  - Find document: `document = document_repo.get_by_id(event.request_id)`
  - Update extraction status: `extraction.status = "complete"`
  - Copy extracted fields: `extracted_fields = event.result.extracted_fields`
  - Update metadata: `extraction.ai_agent_id = event.agent_id`
  - Update metadata: `extraction.validation_passed = len(event.result.validation_errors) == 0`
  - Update metadata: `extraction.validation_warnings = event.result.validation_warnings`
  - Save document
  - **Publish success event (same as Path B):** `_emit_success_event(document, source_config)`
    - Uses existing `publish_success()` → config-driven topic (e.g., `collection.quality.ready`)
- [ ] **Failure handler (`AgentFailedEvent`):**
  - Find document: `document = document_repo.get_by_id(event.request_id)`
  - Update extraction status: `extraction.status = "failed"`
  - Store error: `extraction.error_message = event.error_message`
  - Store error type: `extraction.error_type = event.error_type`
  - Save document
  - Log for alerting/monitoring
- [ ] Handler follows dead letter queue pattern (ADR-006)

### AC-4: Publish Document Ready Event (Both Paths)
- [ ] **After document is fully processed, publish domain event:**
  - Path A: After receiving `AgentCompletedEvent` and updating document
  - Path B: After storing document directly
- [ ] **Topic from source config:** `source_config.events.on_success.topic`
  - Example topics: `collection.quality.ready`, `collection.weather.ready`
- [ ] **Event payload includes:**
  - `document_id`: The completed document ID
  - `source_id`: Source configuration ID
  - `farmer_id`, `region_id`, etc.: From linkage fields
  - `extracted_fields`: Key fields for downstream routing
  - Custom fields from `source_config.events.on_success.payload_fields`
- [ ] **Existing `DaprEventPublisher.publish_success()` already supports this** - reuse it
- [ ] This enables downstream services to react:
  - Quality documents → Quality Model for aggregation
  - Weather documents → Farm Model for alerts

### AC-5: Remove Synchronous gRPC Extraction
- [ ] `AiModelClient.extract()` method removed or deprecated
- [ ] No synchronous gRPC calls for extraction workflow
- [ ] MCP query methods retained if needed for other use cases

### AC-6: Unit Tests Updated
- [ ] **Path A tests (AI extraction):**
  - Test: source config with `ai_extraction.enabled=true` triggers AgentRequestEvent
  - Test: document stored with `status="pending"` before publishing
  - Test: `AgentCompletedEvent` handler updates document with extracted_fields
  - Test: `AgentFailedEvent` handler marks document as failed
  - Test: `request_id` equals `document_id` for correlation
- [ ] **Path B tests (direct storage):**
  - Test: source config with `ai_extraction.enabled=false` stores directly
  - Test: document stored with `status="complete"` immediately
  - Test: NO `AgentRequestEvent` published
  - Test: success event published if configured
- [ ] Mock event bus used for unit testing

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
_Last Updated: 2026-01-09_ (Fixed: status, AC numbering, EntityLinkage fields, correlation strategy, AIModelEventTopic import path, removed AC-7)
