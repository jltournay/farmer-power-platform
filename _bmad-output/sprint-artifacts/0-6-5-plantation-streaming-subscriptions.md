# Story 0.6.5: Plantation Model Streaming Subscriptions

**Status:** To Do
**GitHub Issue:** TBD
**Epic:** [Epic 0.6: Infrastructure Hardening](../epics/epic-0-6-infrastructure-hardening.md)
**ADRs:** [ADR-010](../architecture/adr/ADR-010-dapr-patterns-configuration.md), [ADR-011](../architecture/adr/ADR-011-grpc-fastapi-dapr-architecture.md)
**Story Points:** 5
**Wave:** 2 (DAPR SDK Migration)
**Prerequisite:** Story 0.6.2 (Shared Logging Module)

---

## CRITICAL REQUIREMENTS FOR DEV AGENT

> **READ THIS FIRST - Story is NOT done until ALL these steps are completed!**

### 1. DAPR 1.14.0+ Required

Streaming subscriptions require DAPR 1.14.0 or later. Verify version before starting:
```bash
dapr --version  # Must be >= 1.14.0
```

### 2. Pattern Already Validated

This pattern is validated by the PoC at `tests/e2e/poc-dapr-patterns/`:
- `test_pubsub_success` - Streaming subscription works
- `test_pubsub_retry` - `TopicEventResponse("retry")` triggers retry
- `test_pubsub_dlq` - `TopicEventResponse("drop")` sends to DLQ

### 3. This is HIGH RISK

This story changes the core event handling for Plantation Model. Test thoroughly:
1. Run PoC tests first
2. Run local E2E tests
3. Verify CI passes

### 4. Definition of Done Checklist

- [ ] **FastAPI handlers removed** - No more `@app.post("/events/...")`
- [ ] **Streaming subscriptions work** - `subscribe_with_handler()` receiving events
- [ ] **TopicEventResponse used** - All handlers return proper responses
- [ ] **DLQ configured in code** - `dead_letter_topic="events.dlq"`
- [ ] **Unit tests pass** - New tests in `tests/unit/plantation_model/events/`
- [ ] **E2E tests pass** - Story 0.4.7 (Cross-Model Events) still works
- [ ] **PoC tests pass** - All 5 tests green
- [ ] **Lint passes** - `ruff check . && ruff format --check .`

---

## Story

As a **platform engineer**,
I want Plantation Model to use DAPR SDK streaming subscriptions,
So that event handling is simplified and no extra incoming port is needed.

## Acceptance Criteria

1. **AC1: Current State (Anti-pattern)** - Given Plantation Model currently uses FastAPI HTTP handlers for events, When I check the event handling implementation, Then it uses `@app.post("/events/...")` pattern (anti-pattern)

2. **AC2: Streaming Subscriptions Implemented** - Given the migration is complete, When I check the updated implementation, Then it uses `client.subscribe_with_handler()` from DAPR SDK And handlers return `TopicEventResponse("success"|"retry"|"drop")` And `dead_letter_topic="events.dlq"` is configured in code And no extra incoming port is needed for event handling

3. **AC3: Quality Events Processed** - Given a quality result event is published, When Plantation Model receives it via streaming subscription, Then `QualityEventProcessor` processes the event correctly And farmer performance is updated And metrics are emitted for observability

4. **AC4: Error Handling Works** - Given an event processing fails, When the handler catches the error, Then transient errors return `TopicEventResponse("retry")` And permanent errors return `TopicEventResponse("drop")` And metrics are incremented for alerting

## Tasks / Subtasks

- [ ] **Task 1: Analyze Current Implementation** (AC: 1)
  - [ ] Find all FastAPI event handlers in plantation-model
  - [ ] Document which topics are currently subscribed
  - [ ] Identify the business logic to preserve

- [ ] **Task 2: Create Subscriber Module** (AC: 2)
  - [ ] Create `services/plantation-model/src/plantation_model/events/__init__.py`
  - [ ] Create `services/plantation-model/src/plantation_model/events/subscriber.py`
  - [ ] Import `DaprClient` and `TopicEventResponse`
  - [ ] Create `handle_quality_result(message) -> TopicEventResponse` function

- [ ] **Task 3: Implement Quality Result Handler** (AC: 3, 4)
  - [ ] Extract data using `message.data()` (returns dict, NOT string)
  - [ ] Call existing `QualityEventProcessor.process()`
  - [ ] Return `TopicEventResponse("success")` on success
  - [ ] Return `TopicEventResponse("retry")` on transient error
  - [ ] Return `TopicEventResponse("drop")` on validation error
  - [ ] Add OpenTelemetry metrics for each outcome

- [ ] **Task 4: Create Subscription Startup** (AC: 2)
  - [ ] Create `async def start_subscriptions()` function
  - [ ] Use `client.subscribe_with_handler()` for each topic
  - [ ] Configure `dead_letter_topic="events.dlq"`
  - [ ] Return close functions for cleanup

- [ ] **Task 5: Update Service Startup** (AC: 2)
  - [ ] Modify `main.py` to call `start_subscriptions()` on startup
  - [ ] Store close functions for graceful shutdown
  - [ ] Remove old FastAPI event handlers

- [ ] **Task 6: Remove FastAPI Event Handlers** (AC: 1, 2)
  - [ ] Delete `@app.post("/events/...")` handlers
  - [ ] Remove event-related routes from FastAPI app
  - [ ] Keep only health/admin endpoints on FastAPI

- [ ] **Task 7: Create Unit Tests** (AC: All)
  - [ ] Create `tests/unit/plantation_model/events/test_subscriber.py`
  - [ ] Test handler returns correct response types
  - [ ] Test `message.data()` returns dict
  - [ ] Mock `QualityEventProcessor` for isolation

- [ ] **Task 8: Verify Integration** (AC: 3)
  - [ ] Run PoC tests: `cd tests/e2e/poc-dapr-patterns && python run_tests.py`
  - [ ] Run E2E tests: Story 0.4.7 (Cross-Model Events)
  - [ ] Run lint: `ruff check . && ruff format --check .`

## Git Workflow (MANDATORY)

### Story Start
- [ ] GitHub Issue created
- [ ] Feature branch created:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-6-5-plantation-streaming-subscriptions
  ```

**Branch name:** `story/0-6-5-plantation-streaming-subscriptions`

---

## Unit Tests Required

### New Tests to Create

```python
# tests/unit/plantation_model/events/test_subscriber.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dapr.clients.grpc._response import TopicEventResponse

from plantation_model.events.subscriber import handle_quality_result


class TestQualityResultHandler:
    """Tests for quality result event handler."""

    @pytest.mark.asyncio
    async def test_handler_returns_success_on_valid_event(self):
        """Handler returns success when processing succeeds."""
        message = MagicMock()
        message.data.return_value = {
            "document_id": "doc-123",
            "farmer_id": "WM-4521",
            "grades": {"Primary": 5, "Secondary": 2},
        }

        with patch("plantation_model.events.subscriber.quality_processor") as mock_processor:
            mock_processor.process = AsyncMock()

            result = handle_quality_result(message)

            assert isinstance(result, TopicEventResponse)
            assert result.status == "success"

    @pytest.mark.asyncio
    async def test_handler_returns_retry_on_transient_error(self):
        """Handler returns retry on transient errors."""
        message = MagicMock()
        message.data.return_value = {"document_id": "doc-123"}

        with patch("plantation_model.events.subscriber.quality_processor") as mock_processor:
            mock_processor.process = AsyncMock(side_effect=ConnectionError("DB unavailable"))

            result = handle_quality_result(message)

            assert result.status == "retry"

    @pytest.mark.asyncio
    async def test_handler_returns_drop_on_validation_error(self):
        """Handler returns drop on permanent validation errors."""
        message = MagicMock()
        message.data.return_value = {"invalid": "data"}  # Missing required fields

        with patch("plantation_model.events.subscriber.quality_processor") as mock_processor:
            from pydantic import ValidationError
            mock_processor.process = AsyncMock(side_effect=ValidationError.from_exception_data("test", []))

            result = handle_quality_result(message)

            assert result.status == "drop"

    def test_message_data_returns_dict_not_string(self):
        """Verify message.data() returns dict, not JSON string."""
        message = MagicMock()
        message.data.return_value = {"key": "value"}

        data = message.data()

        assert isinstance(data, dict)
        assert data["key"] == "value"
        # Should NOT need json.loads()


class TestSubscriptionStartup:
    """Tests for subscription startup."""

    @pytest.mark.asyncio
    async def test_start_subscriptions_returns_close_functions(self):
        """start_subscriptions returns close functions for cleanup."""
        with patch("plantation_model.events.subscriber.DaprClient") as MockClient:
            mock_client = MagicMock()
            mock_close = MagicMock()
            mock_client.subscribe_with_handler.return_value = mock_close
            MockClient.return_value = mock_client

            from plantation_model.events.subscriber import start_subscriptions
            close_fns = await start_subscriptions()

            assert len(close_fns) > 0
            assert mock_close in close_fns
```

---

## E2E Test Impact

### Critical Test: Story 0.4.7 (Cross-Model Events)

This story MUST NOT break the cross-model event flow:
```
Collection Model → publishes quality_result.received → Plantation Model receives → updates farmer
```

**Test file:** `tests/e2e/scenarios/test_06_cross_model_events.py`

### Verification Steps

```bash
# 1. Run PoC tests first (should all pass)
cd tests/e2e/poc-dapr-patterns
docker compose up --build -d
python run_tests.py
docker compose down -v

# 2. Run full E2E suite
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/test_06_cross_model_events.py -v
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```

---

## Implementation Reference

### Required Pattern (from ADR-010/011)

```python
# services/plantation-model/src/plantation_model/events/subscriber.py
from dapr.clients import DaprClient
from dapr.clients.grpc._response import TopicEventResponse
from opentelemetry import metrics
import structlog

logger = structlog.get_logger("plantation_model.events")
meter = metrics.get_meter("plantation-model")

processing_counter = meter.create_counter(
    name="event_processing_total",
    description="Total events processed",
)

def handle_quality_result(message) -> TopicEventResponse:
    """Handle quality result events from Collection Model.

    CRITICAL:
    - message.data() returns a dict, NOT a JSON string
    - Must return TopicEventResponse, not None
    """
    # message.data() returns dict directly - no json.loads() needed!
    data = message.data()
    document_id = data.get("document_id")

    try:
        # Check if processor is initialized
        if quality_processor is None:
            logger.error("Quality processor not initialized - will retry")
            processing_counter.add(1, {"topic": "quality_result", "status": "retry"})
            return TopicEventResponse("retry")

        # Process the event
        quality_processor.process(data)
        logger.info("Quality result processed", document_id=document_id)
        processing_counter.add(1, {"topic": "quality_result", "status": "success"})
        return TopicEventResponse("success")

    except ValidationError as e:
        # Invalid data - send to DLQ (no point retrying)
        logger.error("Validation failed", error=str(e), document_id=document_id)
        processing_counter.add(1, {"topic": "quality_result", "status": "drop"})
        return TopicEventResponse("drop")

    except (ConnectionError, TimeoutError) as e:
        # Transient error - retry
        logger.warning("Transient error, will retry", error=str(e), document_id=document_id)
        processing_counter.add(1, {"topic": "quality_result", "status": "retry"})
        return TopicEventResponse("retry")

    except Exception as e:
        # Unexpected error - retry (might be transient)
        logger.exception("Unexpected error processing event", document_id=document_id)
        processing_counter.add(1, {"topic": "quality_result", "status": "retry"})
        return TopicEventResponse("retry")


async def start_subscriptions() -> list:
    """Start all pub/sub subscriptions during service startup."""
    client = DaprClient()

    close_fns = []

    # Subscribe to quality results with DLQ
    quality_close = client.subscribe_with_handler(
        pubsub_name="pubsub",
        topic="collection.quality_result.received",
        handler_fn=handle_quality_result,
        dead_letter_topic="events.dlq",
    )
    close_fns.append(quality_close)

    logger.info("Subscriptions started", topics=["collection.quality_result.received"])

    return close_fns
```

### Service Startup Integration

```python
# services/plantation-model/src/plantation_model/main.py
import asyncio
from plantation_model.events.subscriber import start_subscriptions

async def main():
    # 1. Start pub/sub subscriptions (outbound to DAPR sidecar)
    subscription_closers = await start_subscriptions()

    # 2. Start FastAPI for health probes only
    uvicorn_config = uvicorn.Config(health_app, host="0.0.0.0", port=8000)
    uvicorn_server = uvicorn.Server(uvicorn_config)

    # 3. Start gRPC server for service APIs
    grpc_server = grpc.aio.server()
    add_PlantationServiceServicer_to_server(PlantationServicer(), grpc_server)
    grpc_server.add_insecure_port("[::]:50051")
    await grpc_server.start()

    try:
        await asyncio.gather(
            uvicorn_server.serve(),
            grpc_server.wait_for_termination(),
        )
    finally:
        # Clean up subscriptions
        for close_fn in subscription_closers:
            close_fn()
```

---

## Files to Modify

| Action | File | Change |
|--------|------|--------|
| CREATE | `plantation_model/events/__init__.py` | Package init |
| CREATE | `plantation_model/events/subscriber.py` | Streaming subscription handlers |
| MODIFY | `plantation_model/main.py` | Add subscription startup |
| DELETE | `plantation_model/api/events.py` | Remove FastAPI event handlers |
| CREATE | `tests/unit/plantation_model/events/test_subscriber.py` | Unit tests |

---

## Local Test Run Evidence (MANDATORY)

**1. PoC Tests:**
```bash
cd tests/e2e/poc-dapr-patterns
docker compose up --build -d
python run_tests.py
```
**Output:**
```
(paste test output here - all 5 should pass)
```

**2. Unit Tests:**
```bash
pytest tests/unit/plantation_model/events/ -v
```
**Output:**
```
(paste test output here)
```

**3. E2E Cross-Model Events:**
```bash
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/test_06_cross_model_events.py -v
```
**Output:**
```
(paste test output here)
```

**4. Lint Check:**
```bash
ruff check . && ruff format --check .
```
**Lint passed:** [ ] Yes / [ ] No

---

## References

- [ADR-010: DAPR Patterns](../architecture/adr/ADR-010-dapr-patterns-configuration.md)
- [ADR-011: Service Architecture](../architecture/adr/ADR-011-grpc-fastapi-dapr-architecture.md)
- [PoC: DAPR Patterns](../../../tests/e2e/poc-dapr-patterns/)
- [DAPR Python SDK](https://docs.dapr.io/developing-applications/sdks/python/)
