# Story 0.6.8: Dead Letter Queue Handler

**Status:** To Do
**GitHub Issue:** TBD
**Epic:** [Epic 0.6: Infrastructure Hardening](../epics/epic-0-6-infrastructure-hardening.md)
**ADR:** [ADR-006: Event Delivery and Dead Letter Queue](../architecture/adr/ADR-006-event-delivery-dead-letter-queue.md)
**Story Points:** 3
**Wave:** 2 (DAPR SDK Migration)
**Prerequisite:** Story 0.6.5 or 0.6.6 (need streaming subscription pattern)

---

## CRITICAL REQUIREMENTS FOR DEV AGENT

> **READ THIS FIRST - DLQ is critical for production observability!**

### 1. Shared Module in fp-common

The DLQ handler should be reusable across services. Create in fp-common.

### 2. MongoDB Storage

Failed events are stored in MongoDB for:
- Investigation (what went wrong?)
- Replay (after fix is deployed)
- Alerting (metrics trigger alerts)

### 3. Definition of Done Checklist

- [ ] **DLQ handler module created** - `fp_common/events/dlq_handler.py`
- [ ] **MongoDB storage works** - Events stored in `event_dead_letter` collection
- [ ] **Metrics emitted** - `event_dead_letter_total` counter incremented
- [ ] **Unit tests pass** - Tests in `tests/unit/fp_common/events/`
- [ ] **PoC DLQ test passes** - Events reach DLQ and are stored
- [ ] **Lint passes**

---

## Story

As a **platform engineer**,
I want a DLQ handler that stores failed events in MongoDB,
So that failed events are visible and can be replayed after fixes.

## Acceptance Criteria

1. **AC1: DLQ Handler Receives Events** - Given events may fail permanently, When an event is sent to `events.dlq` topic, Then the DLQ handler receives it via streaming subscription

2. **AC2: Events Stored in MongoDB** - Given the DLQ handler receives a failed event, When it processes the event, Then it stores the event in MongoDB `event_dead_letter` collection And includes: original topic, event data, received_at, status And increments `event_dead_letter_total` metric for alerting

3. **AC3: Events Queryable** - Given failed events are stored, When I query the `event_dead_letter` collection, Then I can see all failed events with their original context And status is initially "pending_review"

## Tasks / Subtasks

- [ ] **Task 1: Create DLQ Handler Module** (AC: 1, 2)
  - [ ] Create `libs/fp-common/fp_common/events/__init__.py`
  - [ ] Create `libs/fp-common/fp_common/events/dlq_handler.py`
  - [ ] Implement `handle_dead_letter(message) -> TopicEventResponse`
  - [ ] Add OpenTelemetry counter metric

- [ ] **Task 2: Implement MongoDB Storage** (AC: 2, 3)
  - [ ] Create `DLQRepository` class
  - [ ] Define schema for `event_dead_letter` collection
  - [ ] Implement `store_failed_event()` method
  - [ ] Add indexes for querying by topic, status, received_at

- [ ] **Task 3: Create DLQ Subscription Startup** (AC: 1)
  - [ ] Create `start_dlq_subscription()` function
  - [ ] Subscribe to `events.dlq` topic
  - [ ] Export for use by services

- [ ] **Task 4: Create Unit Tests** (AC: All)
  - [ ] Create `tests/unit/fp_common/events/test_dlq_handler.py`
  - [ ] Test handler stores event correctly
  - [ ] Test metric is incremented
  - [ ] Mock MongoDB for isolation

- [ ] **Task 5: Integrate with Services** (AC: 1)
  - [ ] Add DLQ subscription to plantation-model startup
  - [ ] Add DLQ subscription to collection-model startup
  - [ ] Or create dedicated DLQ service (discuss with architect)

- [ ] **Task 6: Verify Integration** (AC: All)
  - [ ] Run PoC DLQ test
  - [ ] Verify MongoDB storage
  - [ ] Run full E2E suite

## Git Workflow (MANDATORY)

**Branch name:** `story/0-6-8-dead-letter-queue-handler`

---

## Unit Tests Required

```python
# tests/unit/fp_common/events/test_dlq_handler.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC
from dapr.clients.grpc._response import TopicEventResponse

from fp_common.events.dlq_handler import handle_dead_letter, DLQRepository


class TestDLQHandler:
    """Tests for dead letter queue handler."""

    @pytest.mark.asyncio
    async def test_handler_stores_event_in_mongodb(self):
        """Handler stores failed event in MongoDB."""
        message = MagicMock()
        message.data.return_value = {
            "document_id": "doc-123",
            "error": "validation_failed",
        }
        message.topic.return_value = "collection.quality_result.received"

        with patch("fp_common.events.dlq_handler.dlq_repository") as mock_repo:
            mock_repo.store_failed_event = AsyncMock()

            result = handle_dead_letter(message)

            mock_repo.store_failed_event.assert_called_once()
            call_args = mock_repo.store_failed_event.call_args[1]
            assert call_args["event_data"]["document_id"] == "doc-123"
            assert call_args["original_topic"] == "collection.quality_result.received"
            assert result.status == "success"

    @pytest.mark.asyncio
    async def test_handler_increments_metric(self):
        """Handler increments DLQ counter metric."""
        message = MagicMock()
        message.data.return_value = {"test": "data"}
        message.topic.return_value = "test.topic"

        with patch("fp_common.events.dlq_handler.dlq_counter") as mock_counter:
            with patch("fp_common.events.dlq_handler.dlq_repository"):
                handle_dead_letter(message)

            mock_counter.add.assert_called_once_with(1, {"topic": "test.topic"})

    @pytest.mark.asyncio
    async def test_handler_extracts_original_topic(self):
        """Handler extracts original topic from message."""
        message = MagicMock()
        message.data.return_value = {"data": "value"}
        message.topic.return_value = "original.topic.name"

        with patch("fp_common.events.dlq_handler.dlq_repository") as mock_repo:
            mock_repo.store_failed_event = AsyncMock()

            handle_dead_letter(message)

            call_args = mock_repo.store_failed_event.call_args[1]
            assert call_args["original_topic"] == "original.topic.name"


class TestDLQRepository:
    """Tests for DLQ MongoDB repository."""

    @pytest.mark.asyncio
    async def test_store_failed_event_creates_document(self):
        """store_failed_event creates MongoDB document with correct schema."""
        mock_collection = AsyncMock()

        repo = DLQRepository(mock_collection)
        await repo.store_failed_event(
            event_data={"document_id": "doc-123"},
            original_topic="collection.quality_result.received",
        )

        mock_collection.insert_one.assert_called_once()
        doc = mock_collection.insert_one.call_args[0][0]

        assert doc["event"]["document_id"] == "doc-123"
        assert doc["original_topic"] == "collection.quality_result.received"
        assert doc["status"] == "pending_review"
        assert "received_at" in doc
```

---

## Implementation Reference

### DLQ Handler Module

```python
# libs/fp-common/fp_common/events/dlq_handler.py
from dapr.clients import DaprClient
from dapr.clients.grpc._response import TopicEventResponse
from opentelemetry import metrics
from datetime import datetime, UTC
import structlog

logger = structlog.get_logger("fp_common.events.dlq")
meter = metrics.get_meter("fp-common")

dlq_counter = meter.create_counter(
    name="event_dead_letter_total",
    description="Total events sent to dead letter queue",
)


def handle_dead_letter(message) -> TopicEventResponse:
    """Handle dead-lettered events for inspection and replay.

    IMPORTANT: message.data() returns a dict, NOT a JSON string.
    """
    # Extract event data
    data = message.data()
    original_topic = message.topic() if hasattr(message, 'topic') else "unknown"

    # Increment metric for alerting
    dlq_counter.add(1, {"topic": original_topic})

    # Store in MongoDB
    dlq_repository.store_failed_event(
        event_data=data,
        original_topic=original_topic,
    )

    logger.error(
        "Event dead-lettered",
        topic=original_topic,
        event_keys=list(data.keys()) if isinstance(data, dict) else None,
    )

    return TopicEventResponse("success")


async def start_dlq_subscription() -> callable:
    """Start DLQ subscription during service startup."""
    client = DaprClient()

    close_fn = client.subscribe_with_handler(
        pubsub_name="pubsub",
        topic="events.dlq",
        handler_fn=handle_dead_letter,
        # No DLQ for the DLQ handler itself!
    )

    logger.info("DLQ subscription started", topic="events.dlq")

    return close_fn
```

### DLQ Repository

```python
# libs/fp-common/fp_common/events/dlq_repository.py
from datetime import datetime, UTC
from motor.motor_asyncio import AsyncIOMotorCollection


class DLQRepository:
    """Repository for dead letter queue events."""

    def __init__(self, collection: AsyncIOMotorCollection):
        self._collection = collection

    async def store_failed_event(
        self,
        event_data: dict,
        original_topic: str,
    ) -> str:
        """Store a failed event in the DLQ collection.

        Returns the inserted document ID.
        """
        document = {
            "event": event_data,
            "original_topic": original_topic,
            "received_at": datetime.now(UTC),
            "status": "pending_review",
            "replayed_at": None,
            "discard_reason": None,
        }

        result = await self._collection.insert_one(document)
        return str(result.inserted_id)

    async def mark_replayed(self, document_id: str) -> None:
        """Mark an event as replayed."""
        await self._collection.update_one(
            {"_id": document_id},
            {"$set": {"status": "replayed", "replayed_at": datetime.now(UTC)}},
        )

    async def mark_discarded(self, document_id: str, reason: str) -> None:
        """Mark an event as discarded with reason."""
        await self._collection.update_one(
            {"_id": document_id},
            {"$set": {"status": "discarded", "discard_reason": reason}},
        )
```

### MongoDB Schema

```javascript
// Collection: event_dead_letter
{
  "_id": ObjectId,
  "event": {
    // Original event payload
    "document_id": "uuid",
    "farmer_id": "WM-4521",
    // ... other fields
  },
  "original_topic": "collection.quality_result.received",
  "received_at": ISODate("2024-12-31T10:00:00Z"),
  "status": "pending_review" | "replayed" | "discarded",
  "replayed_at": ISODate | null,
  "discard_reason": String | null
}

// Indexes
db.event_dead_letter.createIndex({ "original_topic": 1 })
db.event_dead_letter.createIndex({ "status": 1 })
db.event_dead_letter.createIndex({ "received_at": -1 })
```

---

## E2E Test Impact

### PoC Validation

```bash
cd tests/e2e/poc-dapr-patterns
docker compose up --build -d
python run_tests.py --test dlq
docker compose down -v
```

The PoC DLQ test verifies:
1. `TopicEventResponse("drop")` sends message to DLQ topic
2. DLQ handler receives the message
3. (After this story) Message is stored in MongoDB

### Extend PoC Test

Add MongoDB verification to the DLQ test:
```python
# Verify event stored in MongoDB
result = await mongodb["event_dead_letter"].find_one({"original_topic": test_topic})
assert result is not None
assert result["status"] == "pending_review"
```

---

## Files to Create/Modify

| Action | File | Change |
|--------|------|--------|
| CREATE | `fp_common/events/__init__.py` | Package init |
| CREATE | `fp_common/events/dlq_handler.py` | DLQ handler and subscription |
| CREATE | `fp_common/events/dlq_repository.py` | MongoDB repository |
| MODIFY | `plantation-model/main.py` | Add DLQ subscription |
| MODIFY | `collection-model/main.py` | Add DLQ subscription |
| CREATE | `tests/unit/fp_common/events/test_dlq_handler.py` | Unit tests |

---

## Local Test Run Evidence (MANDATORY)

**1. Unit Tests:**
```bash
pytest tests/unit/fp_common/events/ -v
```
**Output:** (paste here)

**2. PoC DLQ Test:**
```bash
cd tests/e2e/poc-dapr-patterns
python run_tests.py --test dlq
```
**Output:** (paste here)

**3. MongoDB Verification:**
```bash
# After DLQ test, check MongoDB
docker exec e2e-mongodb-1 mongosh --eval "db.event_dead_letter.find().pretty()"
```
**Output:** (paste here)

**4. Lint Check:** [ ] Passed

---

## OpenTelemetry Alerting

After this story, configure alerts:

```yaml
# Prometheus alerting rule
groups:
  - name: dead-letter-queue
    rules:
      - alert: EventsDeadLettered
        expr: increase(event_dead_letter_total[5m]) > 0
        for: 0m
        labels:
          severity: warning
        annotations:
          summary: "Events sent to dead letter queue"
          description: "{{ $value }} events dead-lettered from {{ $labels.topic }}"
```

---

## E2E Test Strategy (Mental Model Alignment)

> **Reference:** `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

### Direction of Change

This story **adds NEW behavior** (DLQ storage) that didn't exist before.

| Aspect | Impact |
|--------|--------|
| Proto definitions | **UNCHANGED** |
| Happy path behavior | **UNCHANGED** - Valid events still succeed |
| Failure path behavior | **NEW** - Failed events now stored in MongoDB |
| E2E tests | **EXISTING tests MUST PASS, NEW tests needed** |

### Existing E2E Tests

**ALL existing E2E tests MUST pass unchanged.** The DLQ handler only affects events that fail processing - valid events are unaffected.

### New E2E Tests Needed

**YES - New DLQ verification tests:**

```python
# tests/e2e/scenarios/test_08_dead_letter_queue.py
class TestDeadLetterQueue:
    async def test_invalid_event_goes_to_dlq(self):
        """Invalid events are stored in DLQ collection."""
        # 1. Publish event with invalid farmer_id
        # 2. Wait for processing
        # 3. Verify event appears in event_dead_letter collection
        # 4. Verify original_topic is correct
        # 5. Verify status is "pending_review"

    async def test_dlq_metric_incremented(self):
        """DLQ metric is incremented for failed events."""
        # Check prometheus metrics endpoint
```

**When to add these tests:** After Story 0.6.8 is complete and DLQ handler is integrated.

### If Existing Tests Fail

```
Test Failed
    │
    ▼
Is failure related to DLQ handler?
    │
    ├── YES (subscription conflict, MongoDB error) ──► Fix DLQ handler
    │
    └── NO (unrelated failure) ──► Investigate per Mental Model
```

---

## References

- [ADR-006: Event Delivery and DLQ](../architecture/adr/ADR-006-event-delivery-dead-letter-queue.md)
- [DAPR Dead Letter Topics](https://docs.dapr.io/developing-applications/building-blocks/pubsub/pubsub-deadletter/)
- [PoC: DAPR Patterns](../../../tests/e2e/poc-dapr-patterns/)
