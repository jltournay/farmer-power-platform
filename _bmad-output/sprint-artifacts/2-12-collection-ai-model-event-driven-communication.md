# Story 2-12: Collection → AI Model Event-Driven Communication

**Epic:** Epic 2 - Quality Data Ingestion
**Status:** Blocked
**Blocked By:** Story 0.75.17 (Extractor Agent Implementation)
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

```
1. Collection stores document → doc_id
2. Collection publishes: "collection.document.received"
3. AI Model subscribes, processes
4. AI Model publishes: "ai.extraction.complete"
5. Collection subscribes, updates document
```

---

## Acceptance Criteria

### AC-1: Event Publishing After Document Storage
- [ ] After storing a document, Collection Model publishes `collection.document.received` event
- [ ] Event payload includes: `doc_id`, `source_id`, `event_type`, `has_thumbnail`
- [ ] Event published via DAPR pub/sub component

### AC-2: Event Subscription for AI Results
- [ ] Collection Model subscribes to `ai.extraction.complete` events
- [ ] Subscription handler updates document with extracted fields
- [ ] Handler follows dead letter queue pattern (ADR-006)

### AC-3: Remove Synchronous gRPC Extraction
- [ ] `AiModelClient.extract()` method removed or deprecated
- [ ] No synchronous gRPC calls for extraction workflow
- [ ] MCP query methods retained if needed for other use cases

### AC-4: Unit Tests Updated
- [ ] Unit tests cover event publishing after document storage
- [ ] Unit tests cover subscription handler for extraction results
- [ ] Mock event bus used for unit testing

### AC-5: E2E Test Marked as xfail
- [ ] `tests/e2e/scenarios/test_05_weather_ingestion.py` marked with `@pytest.mark.xfail(reason="Replaced by Story 0.75.18 real AI integration")`
- [ ] xfail reason clearly documents the planned replacement
- [ ] Test remains in codebase for reference until 0.75.18 rewrites it

---

## Technical Notes

### Event Schemas (from Story 0.75.17)

**collection.document.received:**
```python
{
    "doc_id": str,
    "source_id": str,
    "event_type": str,  # "quality_image", "weather_data", etc.
    "has_thumbnail": bool,
    "timestamp": datetime
}
```

**ai.extraction.complete:**
```python
{
    "doc_id": str,
    "agent_id": str,
    "success": bool,
    "result": dict,  # Extracted fields
    "error": Optional[str],
    "timestamp": datetime
}
```

### Files to Modify

- `services/collection-model/src/collection_model/infrastructure/ai_model_client.py` - Remove/deprecate extract()
- `services/collection-model/src/collection_model/application/event_publisher.py` - Add document.received publishing
- `services/collection-model/src/collection_model/application/event_handlers.py` - Add extraction.complete handler
- `services/collection-model/src/collection_model/dapr/subscriptions.py` - Register new subscription

---

## Dependencies

| Depends On | Reason |
|------------|--------|
| Story 0.75.17 | Defines event schemas and Extractor agent interface |
| Story 0.75.8 | DAPR pub/sub infrastructure in AI Model |

| Blocks | Reason |
|--------|--------|
| Story 0.75.18 | E2E validation requires async event flow |

---

## Out of Scope

- Thumbnail generation (see Story 2-13)
- AI Model implementation (Epic 0.75)
- E2E testing (Story 0.75.18)

---

_Created: 2026-01-05_
_Last Updated: 2026-01-05_
