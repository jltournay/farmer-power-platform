# Story 13.5: DAPR Cost Event Subscription

## Status: done

## Story

- **ID**: 13.5
- **Epic**: 13 - Unified Platform Cost Service
- **Title**: DAPR Cost Event Subscription
- **GitHub Issue**: [#171](https://github.com/jltournay/farmer-power-platform/issues/171)

## Goal

Add DAPR streaming subscription handler to the platform-cost service that receives cost events from all services via pub/sub and persists them to MongoDB.

## Context & Background

Story 13.4 implemented the gRPC UnifiedCostService for querying cost data. This story adds the event ingestion path - the DAPR streaming subscription that receives `CostRecordedEvent` messages from the `platform.cost.recorded` topic and:

1. Parses and validates incoming events
2. Converts to `UnifiedCostEvent` domain model
3. Persists to MongoDB via `UnifiedCostRepository`
4. Updates `BudgetMonitor` metrics for alerting

### ADR-016 Reference

Section 3.7 specifies the cost event handler implementation:
- Handler receives events via `subscribe_with_handler()`
- Returns `TopicEventResponse("success"|"retry"|"drop")`
- Uses existing repository and budget monitor

### Predecessor Stories

- **13.1**: ✅ Shared `CostRecordedEvent` model in `fp_common.events.cost_recorded`
- **13.2**: ✅ Platform-cost service scaffold with FastAPI + DAPR + gRPC
- **13.3**: ✅ `UnifiedCostRepository` and `BudgetMonitor` implementations
- **13.4**: ✅ gRPC `UnifiedCostService` for cost queries

### Existing Patterns

The collection-model service demonstrates the DAPR streaming subscription pattern in `services/collection-model/src/collection_model/events/subscriber.py`:
- Background thread with `DaprClient.subscribe_with_handler()`
- `message.data()` returns dict directly (NOT JSON string)
- Return `TopicEventResponse` with success/retry/drop
- Use `asyncio.run_coroutine_threadsafe()` for async operations on main event loop
- Module-level service references set during startup

## Detailed Requirements

### AC1: CostEventHandler Class

Create `services/platform-cost/src/platform_cost/handlers/cost_event_handler.py`:

```python
"""DAPR subscription handler for cost events.

Receives cost events from all services via pub/sub and persists them.
Alerting is handled via OTEL metrics, NOT via pub/sub events.
"""

import asyncio
import json
import uuid
from typing import TYPE_CHECKING

import structlog
from dapr.clients.grpc._response import TopicEventResponse
from fp_common.events.cost_recorded import CostRecordedEvent
from opentelemetry import metrics, trace
from pydantic import ValidationError

from platform_cost.domain.cost_event import UnifiedCostEvent

if TYPE_CHECKING:
    from platform_cost.infrastructure.repositories.cost_repository import UnifiedCostRepository
    from platform_cost.services.budget_monitor import BudgetMonitor

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter("platform_cost.cost_event_handler")

# Metrics for event processing
event_processing_counter = meter.create_counter(
    name="platform_cost_event_processing_total",
    description="Total cost events processed by subscription handler",
    unit="1",
)
```

**Required components**:
1. Module-level `_cost_repository`, `_budget_monitor`, `_main_event_loop` references
2. `set_handler_dependencies()` function called during startup
3. `set_main_event_loop()` function to capture main loop
4. `handle_cost_event(message) -> TopicEventResponse` handler function
5. `_process_cost_event_async()` coroutine for actual processing
6. `run_cost_subscription()` function to start subscription in background thread

### AC2: Event Processing Logic

The handler must:
1. Parse `message.data()` (handles dict, str, bytes formats)
2. Validate as `CostRecordedEvent` using Pydantic
3. Generate UUID for event ID
4. Convert to `UnifiedCostEvent.from_event()`
5. Insert via `UnifiedCostRepository.insert()`
6. Record cost via `BudgetMonitor.record_cost()`
7. Return appropriate `TopicEventResponse`:
   - `"success"`: Event processed successfully
   - `"retry"`: Transient error (database, timeout) - will retry
   - `"drop"`: Permanent error (validation) - send to DLQ

### AC3: Streaming Subscription Setup

Create `run_cost_subscription()` that:
1. Waits for DAPR sidecar readiness (configurable wait time)
2. Creates `DaprClient()`
3. Calls `subscribe_with_handler()` for `platform.cost.recorded` topic
4. Configures dead letter topic `events.dlq`
5. Keeps client alive in infinite loop
6. Handles graceful shutdown

### AC4: Main.py Integration

Update `services/platform-cost/src/platform_cost/main.py` lifespan to:
1. Import handler module
2. Call `set_handler_dependencies(cost_repository, budget_monitor)` after initialization
3. Call `set_main_event_loop(asyncio.get_running_loop())` to capture loop
4. Start subscription in daemon thread: `threading.Thread(target=run_cost_subscription, daemon=True)`
5. Log subscription startup

### AC5: Configuration

Add to `config.py`:
```python
# DAPR sidecar wait time (seconds before starting subscriptions)
dapr_sidecar_wait_seconds: int = 5
```

### AC6: DAPR Subscription YAML (Documentation Only)

Create `services/platform-cost/dapr/subscription.yaml` for documentation/reference:
```yaml
# DAPR Pub/Sub Subscription Configuration for Platform Cost Service
# NOTE: With streaming subscriptions, this file is for documentation only.
# The actual subscription is created programmatically via subscribe_with_handler().

apiVersion: dapr.io/v1alpha1
kind: Subscription
metadata:
  name: platform-cost-subscription
spec:
  pubsubname: pubsub
  topic: platform.cost.recorded
  route: /cost-event  # Not used with streaming
  deadLetterTopic: events.dlq
```

### AC7: Unit Tests

Create `tests/unit/platform_cost/test_cost_event_handler.py`:

1. **test_handle_cost_event_success** - Valid event is processed and persisted
2. **test_handle_cost_event_validation_error** - Invalid payload returns "drop"
3. **test_handle_cost_event_repository_error** - Repository error returns "retry"
4. **test_handle_cost_event_budget_monitor_update** - Budget monitor is updated on success
5. **test_handle_cost_event_dict_payload** - Handles dict from message.data()
6. **test_handle_cost_event_string_payload** - Handles JSON string payload
7. **test_handle_cost_event_services_not_initialized** - Returns "retry" if services not set

Mock requirements:
- Mock `DaprClient` and `subscribe_with_handler`
- Mock `UnifiedCostRepository.insert()`
- Mock `BudgetMonitor.record_cost()`
- Use `fp_common.events.cost_recorded.CostRecordedEvent` for test payloads

## Technical Design

### File Structure

```
services/platform-cost/
├── src/
│   └── platform_cost/
│       ├── handlers/
│       │   ├── __init__.py          # Export handler functions
│       │   └── cost_event_handler.py # DAPR subscription handler
│       └── main.py                   # Updated with subscription startup
├── dapr/
│   ├── config.yaml                   # Existing
│   └── subscription.yaml             # NEW - documentation only
```

### Event Flow

```
┌─────────────┐    pub/sub     ┌──────────────────┐
│ ai-model    │ ────────────► │ platform-cost    │
│ collection  │  platform.    │                  │
│ plantation  │  cost.        │ cost_event_      │
└─────────────┘  recorded     │ handler.py       │
                              │   │              │
                              │   ▼              │
                              │ UnifiedCost      │
                              │ Repository       │
                              │   │              │
                              │   ▼              │
                              │ BudgetMonitor    │
                              │ (OTEL metrics)   │
                              └──────────────────┘
```

### Error Handling Strategy

| Error Type | Response | Reason |
|------------|----------|--------|
| ValidationError | `drop` | Malformed event, won't fix on retry |
| Repository insert error | `retry` | Transient DB issue |
| Budget monitor error | `retry` | Transient, should succeed on retry |
| Parse error | `drop` | Malformed payload |
| Services not initialized | `retry` | Startup timing, will resolve |

## Implementation Tasks

### Task 1: Create cost_event_handler.py
- [x] Create `handlers/cost_event_handler.py` with full implementation
- [x] Export from `handlers/__init__.py`

### Task 2: Update Configuration
- [x] Add `dapr_sidecar_wait_seconds` to `config.py`

### Task 3: Integrate into main.py
- [x] Import handler module
- [x] Set dependencies during lifespan startup
- [x] Start subscription thread

### Task 4: Create subscription.yaml
- [x] Create `dapr/subscription.yaml` for documentation

### Task 5: Unit Tests
- [x] Create `tests/unit/platform_cost/test_cost_event_handler.py`
- [x] All 14 test cases passing

### Task 6: E2E Verification
- [x] Local E2E tests passing (107 passed, 1 skipped)
- [x] CI E2E tests passing (Run 20957179821)

## Dependencies

### Upstream
- `fp_common.events.cost_recorded.CostRecordedEvent` (Story 13.1)
- `platform_cost.infrastructure.repositories.cost_repository.UnifiedCostRepository` (Story 13.3)
- `platform_cost.services.budget_monitor.BudgetMonitor` (Story 13.3)

### Downstream
- Story 13.6: BFF Client (depends on platform-cost service being fully operational)
- Story 13.7: ai-model migration (will start publishing to this subscription)

## Acceptance Criteria Summary

- [x] AC1: `CostEventHandler` class with required components
- [x] AC2: Event processing logic with proper error handling
- [x] AC3: Streaming subscription setup in background thread
- [x] AC4: Main.py lifespan integration
- [x] AC5: Configuration for sidecar wait time
- [x] AC6: DAPR subscription.yaml for documentation
- [x] AC7: 14 unit tests passing (expanded from original 7)

## Testing Notes

### Unit Test Setup

```python
@pytest.fixture
def sample_cost_event() -> dict:
    """Sample cost event payload as received from DAPR."""
    return {
        "cost_type": "llm",
        "amount_usd": "0.0015",
        "quantity": 1500,
        "unit": "tokens",
        "timestamp": "2025-01-13T10:00:00Z",
        "source_service": "ai-model",
        "success": True,
        "metadata": {
            "model": "anthropic/claude-3-haiku",
            "agent_type": "extractor",
            "tokens_in": 1000,
            "tokens_out": 500,
        },
    }
```

### E2E Test Command

```bash
# Publish test event via DAPR CLI
dapr publish --publish-app-id platform-cost --pubsub pubsub --topic platform.cost.recorded --data '{
  "cost_type": "llm",
  "amount_usd": "0.0015",
  "quantity": 1500,
  "unit": "tokens",
  "timestamp": "2025-01-13T10:00:00Z",
  "source_service": "ai-model",
  "success": true,
  "metadata": {"model": "anthropic/claude-3-haiku", "agent_type": "extractor"}
}'
```

## Definition of Done

- [x] All implementation tasks completed
- [x] All unit tests passing (14/14)
- [x] Ruff lint and format passing
- [x] CI pipeline green (Run ID: 20956619971)
- [x] E2E tests passing - Local: 107 passed, 1 skipped
- [x] E2E CI passing (Run ID: 20957179821)
- [x] Code review approved
- [ ] PR merged to main

## Code Review (2026-01-13)

### Review Outcome: ✅ APPROVED with suggestions

### Findings Addressed

| # | Severity | Issue | Status |
|---|----------|-------|--------|
| 1 | MEDIUM | Missing type annotation for `message` parameter | ✅ Fixed |
| 2 | LOW | Hardcoded DLQ topic name | Deferred (consistent with collection-model) |
| 3 | LOW | Test cleanup not using `autouse` fixture | ✅ Fixed |
| 4 | LOW | Docstring mentions "class" but uses functions | ✅ Fixed |
| 5 | LOW | Hardcoded timeout value | Deferred (consistent with collection-model) |
| 6 | MEDIUM | Missing test coverage strategy comment | ✅ Fixed |

### Fixes Applied

1. Added `Any` type annotation to `handle_cost_event(message: Any)` - `cost_event_handler.py:167`
2. Added `autouse` fixture for test cleanup - `test_cost_event_handler.py:29-40`
3. Updated `__init__.py` docstring to reflect function-based implementation
4. Added test coverage strategy comment explaining why full handler isn't unit tested

### Post-Fix Validation
```
pytest tests/unit/platform_cost/test_cost_event_handler.py -v
======================== 14 passed in 1.27s ========================
```

## Test Results

### Unit Tests (2026-01-13)
```
pytest tests/unit/platform_cost/test_cost_event_handler.py -v
======================== 14 passed in 1.18s ========================
```

### Platform-Cost Unit Test Suite
```
pytest tests/unit/platform_cost/ -v
======================== 108 passed in 1.91s ========================
```

### Local E2E Tests (2026-01-13)
```bash
bash scripts/e2e-test.sh --keep-up
================== 107 passed, 1 skipped in 136.49s (0:02:16) ==================
```

### CI Results
- CI Workflow: Run 20956619971 - **PASSED** (8m49s)
- E2E Workflow: Run 20957179821 - **PASSED** (5m10s)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| DAPR sidecar not ready | Configurable wait time, retry on transient errors |
| Event loop threading issues | Use `run_coroutine_threadsafe()` pattern from collection-model |
| High event volume | Async processing, DAPR handles backpressure |

## Notes

- Budget alerting is NOT done via pub/sub events - BudgetMonitor exposes OTEL metrics that Prometheus/Grafana use for alerting
- The subscription.yaml is documentation-only since we use streaming subscriptions
- Follow exact patterns from `collection-model/events/subscriber.py` for thread safety
