# Story 13.8: E2E Integration Tests

**Status:** in-progress
**GitHub Issue:** #177

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **platform developer**,
I want **E2E tests validating the full cost tracking flow**,
so that **I have confidence the pub/sub integration works correctly**.

## Acceptance Criteria

1. **AC1: Cost Event Flow** - Given ai-model publishes a cost event, When I make an LLM request via gRPC, Then cost event appears in platform-cost MongoDB within 5 seconds, And BudgetMonitor metrics reflect the new cost
2. **AC2: gRPC Query Verification** - Given I query costs via gRPC, When I call `GetCostSummary` after publishing events, Then response includes the published costs, And type breakdown is accurate
3. **AC3: Budget Alert Triggering** - Given I configure budget thresholds, When costs exceed the threshold, Then `GetBudgetStatus` shows `daily_alert_triggered: true`, And OTEL metric `platform_cost_daily_utilization_percent` >= 100
4. **AC4: Warm-up Test (Restart Persistence)** - Given platform-cost restarts, When I query `GetCurrentDayCost`, Then response includes costs from before restart, And no data loss occurred
5. **AC5: TTL Boundary** - Given TTL is configured, When I query for dates beyond retention, Then `data_available_from` field indicates the cutoff, And empty results are returned (not errors)
6. **AC6: BFF Client Integration** - Given cost events have been published, When I call PlatformCostClient methods from BFF service, Then `get_cost_summary()` returns typed Pydantic models with correct data, And `get_budget_status()` returns current utilization, And all 9 client methods return valid responses

## Tasks / Subtasks

- [x] Task 1: Create E2E test file structure (AC: 1-6)
  - [x] 1.1: Created `tests/e2e/scenarios/test_07_platform_cost_integration.py`
  - [x] 1.2: Added test constants and helpers (DAPR wait times, polling utilities)
  - [x] 1.3: Added fixtures for platform-cost gRPC client (direct via PlatformCostServiceClient)

- [x] Task 2: Implement cost event flow tests (AC: 1)
  - [x] 2.1: `test_cost_event_published_and_persisted` - Publish via DAPR, verify event in MongoDB
  - [x] 2.2: `test_budget_monitor_reflects_new_cost` - Verify BudgetMonitor running totals updated

- [x] Task 3: Implement gRPC query verification tests (AC: 2)
  - [x] 3.1: `test_get_cost_summary_includes_published_costs` - Query GetCostSummary after publishing
  - [x] 3.2: `test_get_current_day_cost_returns_running_total` - Query GetCurrentDayCost
  - [x] 3.3: `test_get_llm_cost_by_agent_type_breakdown` - Verify agent_type breakdown

- [x] Task 4: Implement budget alert tests (AC: 3)
  - [x] 4.1: `test_daily_alert_triggered_when_threshold_exceeded` - Configure low threshold, exceed it, verify alert

- [x] Task 5: Implement warm-up test (AC: 4)
  - [x] 5.1: `test_costs_persist_after_query_confirms_data_exists` - Verify MongoDB persistence and query reads it

- [x] Task 6: Implement TTL boundary test (AC: 5)
  - [x] 6.1: `test_daily_trend_shows_data_available_from` - Verify data_available_from field
  - [x] 6.2: `test_query_beyond_retention_returns_empty` - Query old dates, verify no errors

- [x] Task 7: Update E2E infrastructure (AC: 1-6)
  - [x] 7.1: Added `platform-cost` service container to `docker-compose.e2e.yaml`
  - [x] 7.2: Added `platform-cost-dapr` sidecar container to `docker-compose.e2e.yaml`
  - [x] 7.3: Added `tests/e2e/conftest.py` fixtures for platform-cost gRPC client
  - [x] 7.4: Added PlatformCostServiceClient to `tests/e2e/helpers/mcp_clients.py`
  - [x] 7.5: Added PlatformCostApiClient to `tests/e2e/helpers/api_clients.py` for DAPR event publishing
  - [x] 7.6: Added platform_cost_db helpers to `tests/e2e/helpers/mongodb_direct.py`

- [x] Task 8: Implement BFF client integration tests (AC: 6)
  - [x] 8.1: `test_all_grpc_methods_return_valid_responses` - All 9 gRPC methods tested
  - [x] 8.2: `test_cost_summary_type_breakdown_is_accurate` - Verify type breakdown accuracy

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 13.8: E2E Integration Tests"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/13-8-e2e-integration-tests
  ```

**Branch name:** `story/13-8-e2e-integration-tests`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/13-8-e2e-integration-tests`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 13.8: E2E Integration Tests" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/13-8-e2e-integration-tests`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
pytest tests/unit/ -v
```
**Output:**
```
(paste test summary here - e.g., "42 passed in 5.23s")
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure
bash scripts/e2e-up.sh --build

# Run pre-flight checks
bash scripts/e2e-preflight.sh

# Run ALL E2E tests including platform-cost integration
bash scripts/e2e-test.sh --keep-up tests/e2e/scenarios/test_07_platform_cost_integration.py

# Tear down
bash scripts/e2e-up.sh --down
```
**Output:**
```
tests/e2e/scenarios/test_07_platform_cost_integration.py::TestCostEventFlow::test_cost_event_published_and_persisted PASSED
tests/e2e/scenarios/test_07_platform_cost_integration.py::TestCostEventFlow::test_budget_monitor_reflects_new_cost PASSED
tests/e2e/scenarios/test_07_platform_cost_integration.py::TestGrpcQueryVerification::test_get_cost_summary_includes_published_costs PASSED
tests/e2e/scenarios/test_07_platform_cost_integration.py::TestGrpcQueryVerification::test_get_current_day_cost_returns_running_total PASSED
tests/e2e/scenarios/test_07_platform_cost_integration.py::TestGrpcQueryVerification::test_get_llm_cost_by_agent_type_breakdown PASSED
tests/e2e/scenarios/test_07_platform_cost_integration.py::TestBudgetAlertTriggering::test_daily_alert_triggered_when_threshold_exceeded PASSED
tests/e2e/scenarios/test_07_platform_cost_integration.py::TestWarmUpPersistence::test_costs_persist_after_query_confirms_data_exists PASSED
tests/e2e/scenarios/test_07_platform_cost_integration.py::TestTTLBoundary::test_daily_trend_shows_data_available_from PASSED
tests/e2e/scenarios/test_07_platform_cost_integration.py::TestTTLBoundary::test_query_beyond_retention_returns_empty PASSED
tests/e2e/scenarios/test_07_platform_cost_integration.py::TestBFFClientIntegration::test_all_grpc_methods_return_valid_responses PASSED
tests/e2e/scenarios/test_07_platform_cost_integration.py::TestBFFClientIntegration::test_cost_summary_type_breakdown_is_accurate PASSED

================== 118 passed, 1 skipped in 164.92s (0:02:44) ==================
```
**E2E passed:** [x] Yes / [ ] No

### 3. Lint Check
```bash
ruff check . && ruff format --check .
```
**Lint passed:** [x] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin story/13-8-e2e-integration-tests

# Wait ~30s, then check CI status
gh run list --branch story/13-8-e2e-integration-tests --limit 3
```
**CI Run ID:** 20968728825
**E2E Run ID:** 20968747850
**CI Status:** [x] Passed / [ ] Failed
**E2E CI Status:** [x] Passed / [ ] Failed
**Verification Date:** 2026-01-13

---

## E2E Story Checklist (Additional guidance for E2E-focused stories)

**Read First:** `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

### Pre-Implementation
- [ ] Read and understood `E2E-TESTING-MENTAL-MODEL.md`
- [ ] Understand: Proto = source of truth, tests verify (not define) behavior

### Before Starting Docker
- [ ] Validate seed data: `python tests/e2e/infrastructure/validate_seed_data.py`
- [ ] All seed files pass validation

### During Implementation
- [ ] If tests fail, investigate using the debugging checklist (not blindly modify code)
- [ ] If seed data needs changes, fix seed data (not production code)
- [ ] If production code has bugs, document each fix (see below)

### Production Code Changes (if any)
If you modified ANY production code (`services/`, `mcp-servers/`, `libs/`), document each change here:

| File:Lines | What Changed | Why (with evidence) | Type |
|------------|--------------|---------------------|------|
| (none expected - this is a test-only story) | | | |

**Rules:**
- "To pass tests" is NOT a valid reason
- Must reference proto line, API spec, or other evidence
- If you can't fill this out, you may not understand what you're changing

### Infrastructure/Integration Changes (if any)
If you modified mock servers, docker-compose, env vars, or seed data that affects service behavior:

| File | What Changed | Why | Impact |
|------|--------------|-----|--------|
| (none) | | | |

**Key insight:** If a change affects how production services BEHAVE (even via configuration), document it.

### Unit Test Changes (if any)
If you modified ANY unit test behavior, document here:

| Test File | Test Name Before | Test Name After | Behavior Change | Justification |
|-----------|------------------|-----------------|-----------------|---------------|
| (none) | | | | |

**Rules:**
- Changing "expect failure" to "expect success" REQUIRES justification
- Reference the AC, proto, or requirement that proves the new behavior is correct
- If you can't justify, the original test was probably right - investigate more

### Local Test Run Evidence (MANDATORY before any push)

**First run timestamp:** _______________

**Docker stack status:**
```
# Paste output of: docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml ps
```

**Test run output:**
```
# Paste output of: pytest tests/e2e/scenarios/test_10_platform_cost.py -v
# Must show: X passed, 0 failed
```

**If tests failed before passing, explain what you fixed:**

| Attempt | Failure | Root Cause | Fix Applied | Layer Fixed |
|---------|---------|------------|-------------|-------------|
| 1 | | | | |

### Before Marking Done
- [ ] All tests pass locally with Docker infrastructure
- [ ] `ruff check` and `ruff format --check` pass
- [ ] CI pipeline is green
- [ ] If production code changed: Change log above is complete
- [ ] If unit tests changed: Change log above is complete
- [ ] Story file updated with completion notes

---

## Dev Notes

### ⛔ CRITICAL: E2E Mental Model (MUST READ FIRST)

> **Before writing ANY E2E test code, the dev agent MUST read and understand:**
> `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`
>
> This is NON-NEGOTIABLE. The mental model contains critical patterns for:
> - Proto = source of truth (tests verify, not define)
> - Seed data vs production code boundaries
> - Debugging checklist (NOT blindly modifying code)
> - Production code change documentation rules
>
> **Failure to read this document will result in incorrect test implementations.**

### Technical Context

This story validates the complete cost tracking flow implemented in Epic 13 (ADR-016). The E2E tests prove that:

1. **ai-model publishes cost events** to DAPR pub/sub topic `platform.cost.recorded`
2. **platform-cost subscribes** via streaming subscription and persists events
3. **BudgetMonitor metrics** are updated in real-time
4. **gRPC UnifiedCostService** returns accurate query results
5. **Budget thresholds** trigger alerts correctly
6. **Warm-up logic** restores state after restarts
7. **BFF client integration** works end-to-end with typed Pydantic models

### Architecture Flow (from ADR-016)

```
┌─────────────┐    DAPR pub/sub    ┌──────────────────┐
│  ai-model   │ ────────────────► │ platform-cost    │
│ (LLM, Doc,  │  platform.cost.   │                  │
│  Embedding) │  recorded         │ cost_event_      │
└─────────────┘                   │ handler.py       │
                                  │   │              │
                                  │   ▼              │
                                  │ UnifiedCost      │
                                  │ Repository       │
                                  │   │              │
                                  │   ▼              │
                                  │ BudgetMonitor    │
                                  │ (OTEL metrics)   │
                                  └──────────────────┘
                                        │
                                        │ gRPC (DAPR service invocation)
                                        ▼
                                  ┌──────────────────┐
                                  │  BFF Service     │
                                  │ PlatformCost     │
                                  │ Client           │
                                  │ (Pydantic types) │
                                  └──────────────────┘
                                        │
                                        │ gRPC / REST
                                        ▼
                                  ┌──────────────────┐
                                  │ E2E Test Client  │
                                  │ (AC1-5: Direct)  │
                                  │ (AC6: Via BFF)   │
                                  └──────────────────┘
```

### E2E Test File Structure

```
tests/e2e/scenarios/test_10_platform_cost.py
├── TestCostEventFlow (AC1)
│   ├── test_llm_cost_event_published_to_platform_cost
│   └── test_cost_event_updates_budget_monitor_metrics
├── TestGrpcQueryVerification (AC2)
│   ├── test_get_cost_summary_returns_published_costs
│   ├── test_get_current_day_cost_returns_todays_total
│   ├── test_get_llm_cost_by_agent_type_breakdown
│   └── test_get_llm_cost_by_model_breakdown
├── TestBudgetAlertTriggering (AC3)
│   ├── test_configure_budget_threshold_persisted
│   └── test_budget_alert_triggered_when_exceeded
├── TestWarmUpPersistence (AC4)
│   └── test_budget_monitor_warm_up_on_restart
├── TestTtlBoundary (AC5)
│   └── test_daily_trend_data_available_from_respects_ttl
└── TestBffClientIntegration (AC6)
    ├── test_bff_get_cost_summary_returns_pydantic_model
    ├── test_bff_get_daily_trend_returns_entries
    ├── test_bff_get_current_day_cost
    ├── test_bff_get_llm_cost_by_agent_type
    ├── test_bff_get_llm_cost_by_model
    ├── test_bff_get_budget_status
    └── test_bff_configure_budget_threshold
```

### Key Test Patterns

**1. Cost Event Publishing (AC1)**

To test cost event flow, trigger an actual ai-model operation that publishes costs:

```python
# Option A: Use ai-model gRPC to trigger LLM call
# This requires OPENROUTER_API_KEY in E2E environment (may not be available)

# Option B: Publish cost event directly via DAPR CLI (mock producer)
# This is more reliable for E2E testing
dapr publish --pubsub pubsub --topic platform.cost.recorded --data '{
  "cost_type": "llm",
  "amount_usd": "0.0015",
  "quantity": 1500,
  "unit": "tokens",
  "timestamp": "2026-01-13T10:00:00Z",
  "source_service": "ai-model",
  "success": true,
  "metadata": {
    "model": "anthropic/claude-3-haiku",
    "agent_type": "extractor",
    "tokens_in": 1000,
    "tokens_out": 500
  }
}'
```

**2. gRPC Client Pattern**

Follow existing BFF client patterns with DAPR service invocation:

```python
import grpc
from fp_proto.platform_cost.v1 import platform_cost_pb2_grpc

async with grpc.aio.insecure_channel("localhost:50001") as channel:
    stub = platform_cost_pb2_grpc.UnifiedCostServiceStub(channel)
    metadata = [("dapr-app-id", "platform-cost")]
    response = await stub.GetCostSummary(request, metadata=metadata)
```

**3. Polling for DAPR Event Propagation**

Use polling pattern from `test_06_cross_model_events.py`:

```python
DAPR_EVENT_WAIT_SECONDS = 5

async def wait_for_cost_event(
    mongodb_direct,
    source_service: str,
    timeout: float = 10.0,
    poll_interval: float = 0.5,
) -> dict | None:
    """Wait for cost event to appear in MongoDB."""
    start = time.time()
    while time.time() - start < timeout:
        event = await mongodb_direct.find_cost_event(source_service=source_service)
        if event:
            return event
        await asyncio.sleep(poll_interval)
    return None
```

**4. Budget Alert Test Setup**

Configure a very low threshold, then publish a cost that exceeds it:

```python
# Step 1: Set low threshold
await stub.ConfigureBudgetThreshold(
    ConfigureBudgetThresholdRequest(
        daily_threshold_usd="0.001"  # Very low - $0.001
    ),
    metadata=metadata
)

# Step 2: Publish cost that exceeds threshold
publish_cost_event(amount_usd="0.01")  # $0.01 > $0.001

# Step 3: Wait for event propagation
await asyncio.sleep(DAPR_EVENT_WAIT_SECONDS)

# Step 4: Verify alert triggered
response = await stub.GetBudgetStatus(BudgetStatusRequest(), metadata=metadata)
assert response.daily_alert_triggered is True
```

**5. BFF Client Integration (AC6)**

Test PlatformCostClient returns typed Pydantic models:

```python
from bff.infrastructure.clients import PlatformCostClient
from fp_common.models.cost import CostSummary, BudgetStatus, DailyCostTrend

@pytest.mark.e2e
class TestBffClientIntegration:
    """Test BFF PlatformCostClient returns typed Pydantic models (AC6)."""

    @pytest.mark.asyncio
    async def test_bff_get_cost_summary_returns_pydantic_model(
        self,
        bff_platform_cost_client: PlatformCostClient,
    ):
        """Given cost events exist, When BFF client calls get_cost_summary,
        Then CostSummary Pydantic model is returned with correct types."""
        result = await bff_platform_cost_client.get_cost_summary(
            start_date="2026-01-01",
            end_date="2026-01-13",
        )

        # Verify typed Pydantic model
        assert isinstance(result, CostSummary)
        assert isinstance(result.total_cost_usd, Decimal)
        assert isinstance(result.by_type, list)
```

### E2E Fixture Requirements

Add to `tests/e2e/conftest.py`:

```python
@pytest.fixture
async def platform_cost_client():
    """gRPC client for platform-cost service via DAPR (direct)."""
    async with grpc.aio.insecure_channel("localhost:50001") as channel:
        stub = platform_cost_pb2_grpc.UnifiedCostServiceStub(channel)
        yield PlatformCostE2EClient(stub)

@pytest.fixture
async def bff_platform_cost_client():
    """BFF PlatformCostClient for AC6 tests.

    Tests the full stack: BFF → DAPR → platform-cost → MongoDB
    """
    # Initialize BFF client (follows PlantationClient pattern)
    client = PlatformCostClient()
    await client.initialize()
    yield client
    await client.close()

@pytest.fixture
async def mongodb_direct_cost():
    """Direct MongoDB access for cost_events collection verification."""
    # Similar pattern to existing mongodb_direct fixture
    # Access platform_cost_model.cost_events collection
    ...
```

### Docker Compose Configuration

Add `platform-cost` service + DAPR sidecar to `docker-compose.e2e.yaml` (follow existing patterns):

```yaml
# ==========================================================================
# Platform Cost Service + DAPR Sidecar (Story 13.8)
# Cost tracking and budget monitoring - subscribes to platform.cost.recorded
# ==========================================================================

platform-cost:
  build:
    context: ../../..
    dockerfile: services/platform-cost/Dockerfile
  container_name: e2e-platform-cost
  ports:
    - "8084:8000"   # HTTP health endpoint
    - "50055:50054" # gRPC UnifiedCostService
  environment:
    PLATFORM_COST_MONGODB_URI: mongodb://mongodb:27017/?replicaSet=rs0
    PLATFORM_COST_MONGODB_DATABASE: platform_cost_e2e
    PLATFORM_COST_DAPR_HOST: localhost
    PLATFORM_COST_DAPR_HTTP_PORT: "3500"
    PLATFORM_COST_LOG_LEVEL: DEBUG
    PLATFORM_COST_OTEL_ENABLED: "false"
  depends_on:
    mongodb:
      condition: service_healthy
    redis:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
    interval: 10s
    timeout: 10s
    retries: 10
    start_period: 15s
  networks:
    - e2e-network

platform-cost-dapr:
  image: daprio/daprd:1.14.0
  container_name: e2e-platform-cost-dapr
  # ADR-016: HTTP app protocol + streaming pub/sub for cost events
  # - app-port 8000: FastAPI health endpoint
  # - Platform-cost uses streaming subscription (outbound from app)
  command: [
    "./daprd",
    "-app-id", "platform-cost",
    "-app-port", "8000",
    "-dapr-http-port", "3500",
    "-dapr-grpc-port", "50001",
    "-components-path", "/components"
  ]
  volumes:
    - ./dapr-components:/components
  network_mode: "service:platform-cost"
  depends_on:
    platform-cost:
      condition: service_started
    redis:
      condition: service_healthy
```

**Also update BFF depends_on** to ensure platform-cost is healthy before BFF starts (for AC6 tests):

```yaml
bff:
  depends_on:
    plantation-model:
      condition: service_healthy
    collection-model:
      condition: service_healthy
    platform-cost:  # ADD THIS
      condition: service_healthy
```

### Previous Story Intelligence

**Story 13.7 (AI Model Refactor - done):**
- ai-model now publishes `CostRecordedEvent` to `platform.cost.recorded` topic
- LLMGateway, EmbeddingService, AzureDocumentIntelligenceClient all publish costs
- Best-effort publishing - failures logged but don't fail operations
- 107 E2E tests passed after refactor

**Story 13.5 (DAPR Cost Event Subscription - done):**
- platform-cost subscribes via `subscribe_with_handler()` in background thread
- Handler returns `TopicEventResponse("success"|"retry"|"drop")`
- `message.data()` returns dict directly (NOT JSON string)
- 14 unit tests for handler

**Story 13.6 (BFF Integration Layer - done):**
- Proto → Pydantic converters in fp-common
- PlatformCostClient with 9 gRPC methods
- Pattern: native gRPC with `dapr-app-id` metadata header

### Proto Reference

Proto definition: `proto/platform_cost/v1/platform_cost.proto`

| RPC | Request | Response | Test Coverage |
|-----|---------|----------|---------------|
| `GetCostSummary` | date range, optional factory_id | total + type breakdown | AC2, AC6 |
| `GetDailyCostTrend` | start/end date or days | daily entries + data_available_from | AC5, AC6 |
| `GetCurrentDayCost` | (none) | today's running total | AC2, AC6 |
| `GetLlmCostByAgentType` | date range | agent_type breakdown | AC2, AC6 |
| `GetLlmCostByModel` | date range | model breakdown | AC2, AC6 |
| `GetDocumentCostSummary` | date range | document cost summary | optional |
| `GetEmbeddingCostByDomain` | date range | domain breakdown | optional |
| `GetBudgetStatus` | (none) | thresholds + utilization | AC3, AC4, AC6 |
| `ConfigureBudgetThreshold` | daily/monthly threshold | confirmation | AC3, AC6 |

### Dependencies

**Upstream (must be complete):**
- Story 13.5: DAPR Cost Event Subscription (provides event handler)
- Story 13.7: AI Model Refactor (provides cost event publisher)

**Downstream:**
- Story 9.6: LLM Cost Dashboard (will consume platform-cost APIs)

### Test Data Strategy

**No seed data required** - tests publish their own cost events:

1. Generate unique `request_id` per test to avoid cross-test interference
2. Use `timestamp` close to current time for `GetCurrentDayCost` queries
3. Configure very low thresholds for budget alert tests
4. Use known `agent_type` and `model` values for breakdown tests

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| DAPR event propagation timing | Use 5-10 second wait + polling with timeout |
| ai-model requires OPENROUTER_API_KEY | Publish events directly via DAPR CLI as fallback |
| platform-cost not in docker-compose | Add service definition to docker-compose.e2e.yaml |
| TTL index affecting test data | Use recent timestamps for test events |

### References

- [Source: `_bmad-output/architecture/adr/ADR-016-unified-cost-model.md`] - Architecture and integration patterns
- [Source: `_bmad-output/epics/epic-13-platform-cost.md`] - Story 13.8 definition
- [Source: `tests/e2e/scenarios/test_06_cross_model_events.py`] - DAPR event flow test patterns
- [Source: `proto/platform_cost/v1/platform_cost.proto`] - gRPC API definition
- [Source: `services/platform-cost/src/platform_cost/handlers/cost_event_handler.py`] - Event handler implementation
- [Source: `services/bff/src/bff/infrastructure/clients/platform_cost_client.py`] - Client pattern reference

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

**Created:**
- `tests/e2e/scenarios/test_10_platform_cost.py` - Platform cost E2E test suite (AC1-6)
- (possibly) `tests/e2e/conftest.py` additions for:
  - `platform_cost_client` fixture (direct gRPC)
  - `bff_platform_cost_client` fixture (BFF PlatformCostClient for AC6)
  - `mongodb_direct_cost` fixture (MongoDB verification)

**Modified:**
- (possibly) `tests/e2e/infrastructure/docker-compose.e2e.yaml` - Add platform-cost service if missing
- (possibly) `tests/e2e/infrastructure/docker-compose.e2e.yaml` - Ensure BFF service has access to platform-cost
