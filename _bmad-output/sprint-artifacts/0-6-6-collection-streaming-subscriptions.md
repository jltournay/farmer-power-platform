# Story 0.6.6: Collection Model Streaming Subscriptions

**Status:** To Do
**GitHub Issue:** TBD
**Epic:** [Epic 0.6: Infrastructure Hardening](../epics/epic-0-6-infrastructure-hardening.md)
**ADRs:** [ADR-010](../architecture/adr/ADR-010-dapr-patterns-configuration.md), [ADR-011](../architecture/adr/ADR-011-grpc-fastapi-dapr-architecture.md)
**Story Points:** 5
**Wave:** 2 (DAPR SDK Migration)
**Prerequisite:** Story 0.6.2 (Shared Logging), Story 0.6.5 (Plantation Streaming - for pattern reference)

---

## CRITICAL REQUIREMENTS FOR DEV AGENT

> **READ THIS FIRST - Apply same pattern as Story 0.6.5!**

### 1. Same Pattern as Story 0.6.5

This story applies the EXACT same streaming subscription pattern to Collection Model. Reference Story 0.6.5 implementation.

### 2. This is HIGH RISK

Collection Model handles blob events which trigger the entire ingestion pipeline. Test thoroughly:
1. Run PoC tests first
2. Run local E2E tests (Stories 0.4.5, 0.4.6)
3. Verify CI passes

### 3. Definition of Done Checklist

- [ ] **FastAPI handlers removed** - No more `@app.post("/events/...")`
- [ ] **Streaming subscriptions work** - Blob events received via SDK
- [ ] **TopicEventResponse used** - All handlers return proper responses
- [ ] **DLQ configured in code** - `dead_letter_topic="events.dlq"`
- [ ] **Unit tests pass** - New tests in `tests/unit/collection_model/events/`
- [ ] **E2E tests pass** - Stories 0.4.5, 0.4.6 still work
- [ ] **Lint passes** - `ruff check . && ruff format --check .`

---

## Story

As a **platform engineer**,
I want Collection Model to use DAPR SDK streaming subscriptions,
So that event handling is simplified and consistent with Plantation Model.

## Acceptance Criteria

1. **AC1: Current State** - Given Collection Model currently uses FastAPI HTTP handlers for events, When I check the event handling implementation, Then it uses `@app.post("/events/...")` pattern

2. **AC2: Streaming Subscriptions Implemented** - Given the migration is complete, When I check the updated implementation, Then it uses `client.subscribe_with_handler()` from DAPR SDK And blob events are processed via streaming subscription And `dead_letter_topic="events.dlq"` is configured

3. **AC3: Blob Events Processed** - Given a blob event is received, When Collection Model processes it via streaming subscription, Then the document is ingested correctly And quality result event is published to downstream services

4. **AC4: Error Handling Works** - Given an event processing fails, When the handler catches the error, Then transient errors return `TopicEventResponse("retry")` And permanent errors (corrupt blob, validation) return `TopicEventResponse("drop")`

## Tasks / Subtasks

- [ ] **Task 1: Analyze Current Implementation** (AC: 1)
  - [ ] Find all FastAPI event handlers in collection-model
  - [ ] Document which topics are currently subscribed
  - [ ] Identify blob event handling logic to preserve

- [ ] **Task 2: Create Subscriber Module** (AC: 2)
  - [ ] Create `services/collection-model/src/collection_model/events/__init__.py`
  - [ ] Create `services/collection-model/src/collection_model/events/subscriber.py`
  - [ ] Import `DaprClient` and `TopicEventResponse`

- [ ] **Task 3: Implement Blob Event Handler** (AC: 3, 4)
  - [ ] Create `handle_blob_event(message) -> TopicEventResponse`
  - [ ] Extract data using `message.data()` (returns dict)
  - [ ] Call existing blob processing logic
  - [ ] Return appropriate `TopicEventResponse`
  - [ ] Add OpenTelemetry metrics

- [ ] **Task 4: Create Subscription Startup** (AC: 2)
  - [ ] Create `async def start_subscriptions()` function
  - [ ] Subscribe to blob events topic
  - [ ] Configure `dead_letter_topic="events.dlq"`

- [ ] **Task 5: Update Service Startup** (AC: 2)
  - [ ] Modify `main.py` to call `start_subscriptions()`
  - [ ] Remove old FastAPI event handlers

- [ ] **Task 6: Create Unit Tests** (AC: All)
  - [ ] Create `tests/unit/collection_model/events/test_subscriber.py`
  - [ ] Test handler returns correct response types
  - [ ] Mock blob processor for isolation

- [ ] **Task 7: Verify Integration** (AC: 3)
  - [ ] Run PoC tests
  - [ ] Run E2E tests: Stories 0.4.5, 0.4.6
  - [ ] Run lint

## Git Workflow (MANDATORY)

**Branch name:** `story/0-6-6-collection-streaming-subscriptions`

---

## Unit Tests Required

```python
# tests/unit/collection_model/events/test_subscriber.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dapr.clients.grpc._response import TopicEventResponse

from collection_model.events.subscriber import handle_blob_event


class TestBlobEventHandler:
    """Tests for blob event handler."""

    @pytest.mark.asyncio
    async def test_handler_returns_success_on_valid_blob(self):
        """Handler returns success when blob processing succeeds."""
        message = MagicMock()
        message.data.return_value = {
            "container": "quality-events",
            "blob_path": "2024/01/01/event-123.json",
            "source_id": "qc-analyzer",
        }

        with patch("collection_model.events.subscriber.blob_processor") as mock_processor:
            mock_processor.process = AsyncMock()

            result = handle_blob_event(message)

            assert result.status == "success"

    @pytest.mark.asyncio
    async def test_handler_returns_retry_on_transient_error(self):
        """Handler returns retry on transient errors (storage unavailable)."""
        message = MagicMock()
        message.data.return_value = {"container": "test", "blob_path": "test.json"}

        with patch("collection_model.events.subscriber.blob_processor") as mock_processor:
            mock_processor.process = AsyncMock(side_effect=ConnectionError("Storage unavailable"))

            result = handle_blob_event(message)

            assert result.status == "retry"

    @pytest.mark.asyncio
    async def test_handler_returns_drop_on_corrupt_blob(self):
        """Handler returns drop on permanent errors (corrupt blob)."""
        message = MagicMock()
        message.data.return_value = {"container": "test", "blob_path": "corrupt.json"}

        with patch("collection_model.events.subscriber.blob_processor") as mock_processor:
            mock_processor.process = AsyncMock(side_effect=ValueError("Corrupt blob"))

            result = handle_blob_event(message)

            assert result.status == "drop"
```

---

## E2E Test Impact

### Critical Tests

| Test | File | Must Pass |
|------|------|-----------|
| Story 0.4.5 | `test_05_quality_event_blob.py` | Blob ingestion flow |
| Story 0.4.6 | `test_05_weather_ingestion.py` | Weather data ingestion |

### Verification Steps

```bash
# Run E2E suite for blob ingestion
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/test_05*.py -v
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```

---

## Implementation Reference

Same pattern as Story 0.6.5. Key differences:
- Topic: `azure.blobstorage.events` (or equivalent blob event topic)
- Handler: Processes blob events, not quality results
- Downstream: Publishes `collection.quality_result.received` after processing

---

## Local Test Run Evidence (MANDATORY)

**1. PoC Tests:**
```bash
cd tests/e2e/poc-dapr-patterns && python run_tests.py
```
**Output:** (paste here)

**2. Unit Tests:**
```bash
pytest tests/unit/collection_model/events/ -v
```
**Output:** (paste here)

**3. E2E Blob Ingestion:**
```bash
pytest tests/e2e/scenarios/test_05*.py -v
```
**Output:** (paste here)

**4. Lint Check:** [ ] Passed

---

## References

- [Story 0.6.5: Plantation Streaming](./0-6-5-plantation-streaming-subscriptions.md) - Pattern reference
- [ADR-010: DAPR Patterns](../architecture/adr/ADR-010-dapr-patterns-configuration.md)
- [ADR-011: Service Architecture](../architecture/adr/ADR-011-grpc-fastapi-dapr-architecture.md)
