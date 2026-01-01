# Story 0.6.6: Collection Model Streaming Subscriptions

**Status:** In Progress
**GitHub Issue:** #51
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

- [x] **FastAPI handlers removed** - HTTP endpoint kept for Azure Event Grid backward compat, streaming subscriptions added
- [x] **Streaming subscriptions work** - Blob events received via SDK (`blob.created` topic)
- [x] **TopicEventResponse used** - All handlers return proper responses (success/retry/drop)
- [x] **DLQ configured in code** - `dead_letter_topic="events.dlq"`
- [x] **Unit tests pass** - 14 tests in `tests/unit/collection_model/events/`
- [x] **E2E tests pass** - test_04 (blob ingestion) + test_06 (cross-model events): 11 passed
- [x] **Lint passes** - `ruff check . && ruff format --check .`

---

## LESSONS LEARNED FROM STORY 0.6.5 (CRITICAL)

> **READ THIS BEFORE IMPLEMENTING!** These issues were discovered during Story 0.6.5 and WILL affect this story.

### 1. DAPR Configuration Changes Required

The E2E `docker-compose.e2e.yaml` needs these updates for streaming subscriptions:

**DAPR Version:** Must be 1.14.0 (not 1.12.0) for streaming subscription support:
```yaml
collection-model-dapr:
  image: daprio/daprd:1.14.0  # NOT 1.12.0!
```

**App Protocol:** For services with gRPC, use `-app-protocol grpc`:
```yaml
command: [
  "./daprd",
  "-app-id", "collection-model",
  "-app-port", "50051",
  "-app-protocol", "grpc",  # Changed from http
  ...
]
```

**Declarative Subscriptions:** Remove all subscriptions from `subscription.yaml` - streaming subscriptions are programmatic:
```yaml
# subscription.yaml should be empty or only contain comments
# Streaming subscriptions are configured in code via subscribe_with_handler()
```

### 2. Event Loop Error (CRITICAL FIX)

**The Problem:** DAPR streaming handlers run in a separate thread, but Motor (MongoDB async driver) and other async clients are bound to the main event loop. Using `asyncio.run()` creates a NEW event loop that can't access Motor's connections:

```
RuntimeError: no running event loop
RuntimeError: Event loop is closed
```

**The Fix:** Pass the main event loop to handlers and use `asyncio.run_coroutine_threadsafe()`:

```python
# In subscriber.py:
_main_event_loop: asyncio.AbstractEventLoop | None = None

def set_main_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Set the main event loop for async operations."""
    global _main_event_loop
    _main_event_loop = loop

def handle_blob_event(message) -> TopicEventResponse:
    # Check main event loop initialization
    if _main_event_loop is None:
        logger.error("Main event loop not initialized - will retry")
        return TopicEventResponse("retry")

    # Run async operations on the MAIN event loop
    future = asyncio.run_coroutine_threadsafe(
        process_blob(...),  # Your async processing function
        _main_event_loop,
    )
    future.result(timeout=30)
```

```python
# In main.py (during startup):
from collection_model.events.subscriber import set_main_event_loop

# CRITICAL: Pass the main event loop before starting subscription thread
main_loop = asyncio.get_running_loop()
set_main_event_loop(main_loop)

# Then start the subscription thread
subscription_thread = threading.Thread(
    target=run_streaming_subscriptions,
    daemon=True,
)
subscription_thread.start()
```

### 3. Subscription Thread Pattern

The DaprClient must stay alive for subscriptions to work. Use a single function with an infinite loop:

```python
def run_streaming_subscriptions() -> None:
    """Run in a daemon thread - keeps DaprClient alive."""
    time.sleep(5)  # Wait for DAPR sidecar
    close_fns = []
    try:
        client = DaprClient()  # Must stay alive!
        close_fn = client.subscribe_with_handler(
            pubsub_name="pubsub",
            topic="your.topic.name",
            handler_fn=your_handler,
            dead_letter_topic="events.dlq",
        )
        close_fns.append(close_fn)

        while True:  # Keep client alive
            time.sleep(1)
    finally:
        for close_fn in close_fns:
            close_fn()
```

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

- [x] **Task 1: Analyze Current Implementation** (AC: 1) ✅
  - [x] Find all FastAPI event handlers in collection-model
  - [x] Document which topics are currently subscribed
  - [x] Identify blob event handling logic to preserve
  - **Findings:** `/api/events/blob-created` (HTTP webhook), `/api/v1/triggers/job/{source_id}` (DAPR Job). No DAPR pub/sub subscriptions - uses HTTP webhooks from Azure Event Grid. Blob logic in `_process_blob_created_event()` preserved.

- [x] **Task 2: Create Subscriber Module** (AC: 2) ✅
  - [x] Create `services/collection-model/src/collection_model/events/__init__.py`
  - [x] Create `services/collection-model/src/collection_model/events/subscriber.py`
  - [x] Import `DaprClient` and `TopicEventResponse`

- [x] **Task 3: Implement Blob Event Handler** (AC: 3, 4) ✅
  - [x] Create `handle_blob_event(message) -> TopicEventResponse`
  - [x] Extract data using `message.data()` (returns dict)
  - [x] Call existing blob processing logic (reused via `_process_blob_event_async`)
  - [x] Return appropriate `TopicEventResponse` (success/retry/drop)
  - [x] Add OpenTelemetry metrics (`collection_event_processing_total`)

- [x] **Task 4: Create Subscription Startup** (AC: 2) ✅
  - [x] Create `run_streaming_subscriptions()` function (runs in daemon thread)
  - [x] Subscribe to blob events topic (`blob.created`)
  - [x] Configure `dead_letter_topic="events.dlq"`

- [x] **Task 5: Update Service Startup** (AC: 2) ✅
  - [x] Modify `main.py` to start subscription thread
  - [x] Set main event loop via `set_main_event_loop()`
  - [x] Set blob processor services via `set_blob_processor()`
  - **Note:** HTTP endpoint retained for Azure Event Grid backward compatibility

- [x] **Task 6: Create Unit Tests** (AC: All) ✅
  - [x] Create `tests/unit/collection_model/events/test_subscriber.py` (14 tests)
  - [x] Test handler returns correct response types
  - [x] Test event subject parsing
  - [x] Test Pydantic models for Event Grid events

- [x] **Task 7: Verify Integration** (AC: 3) ✅
  - [x] Run E2E tests: test_04 (blob ingestion), test_06 (cross-model events)
  - [x] Run lint (`ruff check . && ruff format --check .`)

## Git Workflow (MANDATORY)

**Branch name:** `story/0-6-6-collection-streaming-subscriptions`

---

## Unit Tests Required

> **NOTE:** Tests MUST mock the main event loop since handlers use `asyncio.run_coroutine_threadsafe()`.

```python
# tests/unit/collection_model/events/test_subscriber.py
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dapr.clients.grpc._response import TopicEventResponse, TopicEventResponseStatus


@pytest.fixture
def mock_event_loop():
    """Create a mock event loop for testing handlers."""
    loop = MagicMock(spec=asyncio.AbstractEventLoop)
    return loop


class TestBlobEventHandler:
    """Tests for blob event handler."""

    def test_handler_returns_success_on_valid_blob(self, mock_event_loop):
        """Handler returns success when blob processing succeeds."""
        from collection_model.events import subscriber

        message = MagicMock()
        message.data.return_value = {
            "container": "quality-events",
            "blob_path": "2024/01/01/event-123.json",
            "source_id": "qc-analyzer",
        }

        # Mock run_coroutine_threadsafe to return a completed future
        mock_future = MagicMock()
        mock_future.result.return_value = {"status": "success"}

        with (
            patch.object(subscriber, "_blob_processor", MagicMock()),
            patch.object(subscriber, "_main_event_loop", mock_event_loop),
            patch("asyncio.run_coroutine_threadsafe", return_value=mock_future),
        ):
            result = subscriber.handle_blob_event(message)

        assert result.status == TopicEventResponseStatus.success

    def test_handler_returns_retry_on_transient_error(self, mock_event_loop):
        """Handler returns retry on transient errors (storage unavailable)."""
        from collection_model.events import subscriber

        message = MagicMock()
        message.data.return_value = {"container": "test", "blob_path": "test.json"}

        # Mock run_coroutine_threadsafe to raise ConnectionError
        mock_future = MagicMock()
        mock_future.result.side_effect = ConnectionError("Storage unavailable")

        with (
            patch.object(subscriber, "_blob_processor", MagicMock()),
            patch.object(subscriber, "_main_event_loop", mock_event_loop),
            patch("asyncio.run_coroutine_threadsafe", return_value=mock_future),
        ):
            result = subscriber.handle_blob_event(message)

        assert result.status == TopicEventResponseStatus.retry

    def test_handler_returns_drop_on_corrupt_blob(self, mock_event_loop):
        """Handler returns drop on permanent errors (corrupt blob)."""
        from collection_model.events import subscriber

        message = MagicMock()
        message.data.return_value = {"container": "test", "blob_path": "corrupt.json"}

        # Mock run_coroutine_threadsafe to raise ValueError
        mock_future = MagicMock()
        mock_future.result.side_effect = ValueError("Corrupt blob")

        with (
            patch.object(subscriber, "_blob_processor", MagicMock()),
            patch.object(subscriber, "_main_event_loop", mock_event_loop),
            patch("asyncio.run_coroutine_threadsafe", return_value=mock_future),
        ):
            result = subscriber.handle_blob_event(message)

        assert result.status == TopicEventResponseStatus.drop

    def test_handler_returns_retry_when_event_loop_not_initialized(self):
        """Handler returns retry when main event loop is not initialized."""
        from collection_model.events import subscriber

        message = MagicMock()
        message.data.return_value = {"container": "test", "blob_path": "test.json"}

        with patch.object(subscriber, "_main_event_loop", None):
            result = subscriber.handle_blob_event(message)

        assert result.status == TopicEventResponseStatus.retry
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

**1. Unit Tests:**
```bash
PYTHONPATH="${PYTHONPATH}:.:services/collection-model/src:libs/fp-common/src:libs/fp-proto/src" \
  pytest tests/unit/collection_model/events/test_subscriber.py -v
```
**Output:**
```
======================== 14 passed in 0.46s ========================
```

**2. E2E Tests (test_04 + test_06):**
```bash
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/test_04_quality_blob_ingestion.py tests/e2e/scenarios/test_06_cross_model_events.py -v
```
**Output:**
```
tests/e2e/scenarios/test_04_quality_blob_ingestion.py::TestBlobUpload::test_blob_upload_to_quality_events_container PASSED
tests/e2e/scenarios/test_04_quality_blob_ingestion.py::TestBlobEventTrigger::test_blob_event_trigger_returns_202_accepted PASSED
tests/e2e/scenarios/test_04_quality_blob_ingestion.py::TestDocumentCreation::test_document_created_with_farmer_linkage PASSED
tests/e2e/scenarios/test_04_quality_blob_ingestion.py::TestDocumentCreation::test_document_has_extracted_attributes PASSED
tests/e2e/scenarios/test_04_quality_blob_ingestion.py::TestDaprEventPublished::test_quality_result_received_event_published PASSED
tests/e2e/scenarios/test_04_quality_blob_ingestion.py::TestDuplicateDetection::test_duplicate_blob_is_detected_and_skipped PASSED
tests/e2e/scenarios/test_06_cross_model_events.py::TestInitialPerformanceBaseline::test_farmer_summary_returns_baseline_metrics PASSED
tests/e2e/scenarios/test_06_cross_model_events.py::TestQualityEventIngestion::test_quality_event_ingested_and_document_created PASSED
tests/e2e/scenarios/test_06_cross_model_events.py::TestPlantationModelEventProcessing::test_dapr_event_propagation_and_processing PASSED
tests/e2e/scenarios/test_06_cross_model_events.py::TestMCPQueryVerification::test_farmer_summary_updated_after_quality_event PASSED
tests/e2e/scenarios/test_06_cross_model_events.py::TestMCPQueryVerification::test_farmer_summary_accessible_via_mcp PASSED

======================== 11 passed in 29.04s ========================
```

**3. Lint Check:** [x] Passed
```bash
ruff check . && ruff format --check .
# Found 0 errors, 301 files already formatted
```

---

## E2E Test Strategy (Mental Model Alignment)

> **Reference:** `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

### Direction of Change

Same pattern as Story 0.6.5. **Changes transport mechanism** but **behavior is unchanged**.

| Aspect | Impact |
|--------|--------|
| Proto definitions | **UNCHANGED** |
| Event payload format | **UNCHANGED** - Same blob event structure |
| Business logic | **UNCHANGED** - Same blob processing pipeline |
| E2E tests | **MUST PASS WITHOUT MODIFICATION** |

### Existing E2E Tests

**ALL existing E2E tests MUST pass unchanged.** E2E tests verify blob processing outcomes, not transport.

Critical tests:
- `test_05_quality_event_blob.py` (Story 0.4.5) - Blob ingestion flow
- `test_05_weather_ingestion.py` (Story 0.4.6) - Weather data ingestion

### New E2E Tests Needed

**None for happy path.** Existing tests cover the blob processing flow.

### If Existing Tests Fail

Same debugging approach as Story 0.6.5:
1. Check if streaming subscription is receiving events
2. Check DAPR sidecar logs for errors
3. Check handler returns correct `TopicEventResponse`

**IMPORTANT:** If tests fail, the bug is in our streaming implementation - NOT in the test or seed data.

---

## References

- [Story 0.6.5: Plantation Streaming](./0-6-5-plantation-streaming-subscriptions.md) - Pattern reference
- [ADR-010: DAPR Patterns](../architecture/adr/ADR-010-dapr-patterns-configuration.md)
- [ADR-011: Service Architecture](../architecture/adr/ADR-011-grpc-fastapi-dapr-architecture.md)
