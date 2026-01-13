# Story 13.7: AI Model Refactor - Publish Costs via DAPR

**Status:** ready-for-dev
**GitHub Issue:** #175

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **Platform Developer**,
I want **ai-model to publish cost events via DAPR pub/sub instead of persisting them locally**,
so that **platform-cost becomes the single source of truth for costs and ai-model becomes a pure cost producer**.

## Acceptance Criteria

1. **AC1: LLM Gateway publishes cost events** - When LLM Gateway processes a request, it publishes a `CostRecordedEvent` to `platform.cost.recorded` topic with cost_type=llm and includes model, agent_type, tokens_in, tokens_out in metadata
2. **AC2: EmbeddingService publishes cost events** - When EmbeddingService processes embeddings, it publishes a `CostRecordedEvent` with cost_type=embedding and includes model, knowledge_domain, texts_count, batch_count in metadata
3. **AC3: AzureDocumentIntelligenceClient publishes cost events** - When Azure DI processes a document, it publishes a `CostRecordedEvent` with cost_type=document and includes model_id, page_count, document_id in metadata
4. **AC4: Delete cost_service.py** - The `ai_model/api/cost_service.py` file is deleted (CostService moves to platform-cost)
5. **AC5: Delete cost_event_repository.py** - The `ai_model/infrastructure/repositories/cost_event_repository.py` file is deleted
6. **AC6: Delete embedding_cost_repository.py** - The `ai_model/infrastructure/repositories/embedding_cost_repository.py` file is deleted
7. **AC7: Delete budget_monitor.py** - The `ai_model/llm/budget_monitor.py` file is deleted (BudgetMonitor moves to platform-cost)
8. **AC8: Remove CostService from proto** - The CostService and all related messages are removed from `proto/ai_model/v1/ai_model.proto`
9. **AC9: Update config.py** - Remove cost persistence settings, add `unified_cost_topic` and `embedding_cost_per_1k_tokens` settings
10. **AC10: Update main.py** - Remove cost repository and budget monitor initialization, add DAPR client initialization
11. **AC11: Update grpc_server.py** - Remove CostService registration
12. **AC12: Best-effort publishing** - If DAPR publish fails, warning is logged but the LLM/embedding/document operation still succeeds
13. **AC13: Unit tests updated** - All unit tests pass after refactoring with mocked DAPR client
14. **AC14: No regressions** - Existing ai-model functionality (agents, workflows, RAG) continues to work

## Tasks / Subtasks

- [ ] Task 1: Update config.py settings (AC: 9)
  - [ ] 1.1: Remove `llm_cost_tracking_enabled`, `llm_cost_alert_daily_usd`, `llm_cost_alert_monthly_usd` settings
  - [ ] 1.2: Remove `llm_cost_event_topic`, `llm_cost_alert_topic` settings
  - [ ] 1.3: Add `unified_cost_topic: str = "platform.cost.recorded"` setting
  - [ ] 1.4: Add `embedding_cost_per_1k_tokens: float = 0.0001` setting

- [ ] Task 2: Refactor LLM Gateway (AC: 1, 12)
  - [ ] 2.1: Update `__init__` to accept `DaprClient` instead of `cost_repository` and `budget_monitor`
  - [ ] 2.2: Replace cost persistence logic (lines ~557-577) with `CostRecordedEvent` publishing
  - [ ] 2.3: Remove imports for `LlmCostEventRepository` and `BudgetMonitor`
  - [ ] 2.4: Add import for `DaprClient` and `CostRecordedEvent` from fp-common

- [ ] Task 3: Refactor EmbeddingService (AC: 2, 12)
  - [ ] 3.1: Update `__init__` to accept `DaprClient` instead of `cost_repository`
  - [ ] 3.2: Rename `_record_cost_event` method to `_publish_cost_event`
  - [ ] 3.3: Replace cost persistence with `CostRecordedEvent` publishing
  - [ ] 3.4: Calculate USD cost using `embedding_cost_per_1k_tokens` setting
  - [ ] 3.5: Remove imports for `EmbeddingCostEventRepository`

- [ ] Task 4: Refactor AzureDocumentIntelligenceClient (AC: 3, 12)
  - [ ] 4.1: Update `__init__` to accept optional `on_cost_event` callback
  - [ ] 4.2: Add callback invocation after creating cost_event
  - [ ] 4.3: Create publish_document_cost helper in the instantiating module (main.py or extraction_workflow.py)

- [ ] Task 5: Update main.py (AC: 10)
  - [ ] 5.1: Create DAPR client instance in lifespan startup
  - [ ] 5.2: Remove `LlmCostEventRepository` initialization and `ensure_indexes()`
  - [ ] 5.3: Remove `BudgetMonitor` initialization
  - [ ] 5.4: Pass DAPR client to `LLMGateway` and `EmbeddingService`
  - [ ] 5.5: Wire `AzureDocumentIntelligenceClient` with cost callback
  - [ ] 5.6: Store DAPR client in app.state for health checks

- [ ] Task 6: Update grpc_server.py (AC: 11)
  - [ ] 6.1: Remove `CostServiceServicer` import
  - [ ] 6.2: Remove `add_CostServiceServicer_to_server` import
  - [ ] 6.3: Remove CostService registration from `serve()` function

- [ ] Task 7: Update proto/ai_model.proto (AC: 8)
  - [ ] 7.1: Delete `CostService` service definition
  - [ ] 7.2: Delete all CostService-related messages (DailyCostSummaryRequest/Response, CurrentDayCostRequest, CostSummaryResponse, CostByAgentTypeRequest/Response, etc.)
  - [ ] 7.3: Regenerate Python stubs with `make proto` or `scripts/generate-proto.sh`

- [ ] Task 8: Delete obsolete files (AC: 4, 5, 6, 7)
  - [ ] 8.1: Delete `services/ai-model/src/ai_model/api/cost_service.py`
  - [ ] 8.2: Delete `services/ai-model/src/ai_model/infrastructure/repositories/cost_event_repository.py`
  - [ ] 8.3: Delete `services/ai-model/src/ai_model/infrastructure/repositories/embedding_cost_repository.py`
  - [ ] 8.4: Delete `services/ai-model/src/ai_model/llm/budget_monitor.py`
  - [ ] 8.5: Update `__init__.py` files to remove deleted exports

- [ ] Task 9: Update unit tests (AC: 13)
  - [ ] 9.1: Update `tests/unit/ai_model/test_gateway.py` to mock DAPR client instead of cost_repository
  - [ ] 9.2: Update `tests/unit/ai_model/test_embedding_service.py` to mock DAPR client
  - [ ] 9.3: Delete `tests/unit/ai_model/test_cost_service.py`
  - [ ] 9.4: Delete `tests/unit/ai_model/test_budget_monitor.py`
  - [ ] 9.5: Delete `tests/unit/ai_model/test_cost_event_repository.py`
  - [ ] 9.6: Verify all remaining tests pass

- [ ] Task 10: Update domain models (AC: 14)
  - [ ] 10.1: Remove `LlmCostEvent` from `ai_model/domain/cost_event.py` if only used for persistence
  - [ ] 10.2: Keep `AzureDocIntelCostEvent` as internal dataclass (converted to `CostRecordedEvent` for publishing)
  - [ ] 10.3: Keep `EmbeddingCostEvent` as internal dataclass (converted to `CostRecordedEvent` for publishing)

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 13.7: AI Model Refactor - Publish Costs via DAPR"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/13-7-ai-model-refactor-publish-costs
  ```

**Branch name:** `story/13-7-ai-model-refactor-publish-costs`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/13-7-ai-model-refactor-publish-costs`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 13.7: AI Model Refactor - Publish Costs" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/13-7-ai-model-refactor-publish-costs`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
pytest tests/unit/ai_model/ -v
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

# Run E2E tests
bash scripts/e2e-test.sh --keep-up

# Tear down
bash scripts/e2e-up.sh --down
```
**Output:**
```
(paste E2E test output here - story is NOT ready for review without this)
```
**E2E passed:** [ ] Yes / [ ] No

### 3. Lint Check
```bash
ruff check . && ruff format --check .
```
**Lint passed:** [ ] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin story/13-7-ai-model-refactor-publish-costs

# Wait ~30s, then check CI status
gh run list --branch story/13-7-ai-model-refactor-publish-costs --limit 3
```
**CI Run ID:** _______________
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

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
| (none) | | | |

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
# Paste output of: pytest tests/e2e/scenarios/ -v
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

### Technical Context

This story refactors ai-model from being a cost **store** to being a cost **producer**. Per ADR-016:

1. **Before:** ai-model persists LLM, embedding, and document costs to its own MongoDB collections and exposes a gRPC CostService
2. **After:** ai-model publishes cost events to DAPR pub/sub topic `platform.cost.recorded` and platform-cost service aggregates all costs

This is a **breaking change** for any consumers of the ai-model CostService gRPC API - they must switch to platform-cost's UnifiedCostService (already implemented in Stories 13.1-13.6).

### Key Architecture Principles (ADR-016)

- **ai-model becomes a pure cost PRODUCER** - publishes events, does not store or expose cost APIs
- **platform-cost is the single source of truth** - stores all costs, exposes all cost APIs
- **Event-driven decoupling** - services don't know about platform-cost, just publish to topic
- **Best-effort publishing** - DAPR failures are logged but don't fail the primary operation

### Files to DELETE

| File | Current Purpose | Why Delete |
|------|-----------------|------------|
| `src/ai_model/api/cost_service.py` | gRPC CostService implementation | Moves to platform-cost |
| `src/ai_model/infrastructure/repositories/cost_event_repository.py` | LLM cost MongoDB repository | Moves to platform-cost |
| `src/ai_model/infrastructure/repositories/embedding_cost_repository.py` | Embedding cost MongoDB repository | Moves to platform-cost |
| `src/ai_model/llm/budget_monitor.py` | Budget threshold alerting | Moves to platform-cost |

### Files to MODIFY

| File | Changes |
|------|---------|
| `config.py` | Remove cost persistence settings, add unified_cost_topic |
| `main.py` | Remove cost repo/monitor init, add DAPR client, wire to services |
| `grpc_server.py` | Remove CostService registration |
| `llm/gateway.py` | Replace cost persistence with DAPR publish |
| `services/embedding_service.py` | Replace cost persistence with DAPR publish |
| `infrastructure/azure_doc_intel_client.py` | Add cost callback invocation |
| `proto/ai_model/v1/ai_model.proto` | Remove CostService and related messages |

### Config Changes

**REMOVE these settings:**
```python
llm_cost_tracking_enabled: bool = True
llm_cost_alert_daily_usd: float = 10.0
llm_cost_alert_monthly_usd: float = 100.0
llm_cost_event_topic: str = "ai.cost.recorded"
llm_cost_alert_topic: str = "ai.cost.threshold_exceeded"
```

**ADD these settings:**
```python
# Unified cost publishing (ADR-016)
unified_cost_topic: str = "platform.cost.recorded"

# Embedding cost per 1K tokens (approximate)
# Source: Pinecone Inference API pricing ~$0.0001/1K tokens
embedding_cost_per_1k_tokens: float = 0.0001
```

### Cost Event Publishing Pattern

Use `CostRecordedEvent` from fp-common for all cost types:

```python
from fp_common.events.cost_recorded import CostRecordedEvent, CostType, CostUnit

event = CostRecordedEvent(
    cost_type=CostType.LLM,  # or DOCUMENT, EMBEDDING
    amount_usd=str(cost_usd),  # Decimal as string for precision
    quantity=total_tokens,
    unit=CostUnit.TOKENS,  # or PAGES
    timestamp=datetime.now(UTC),
    source_service="ai-model",
    success=True,
    factory_id=factory_id,  # Optional
    request_id=request_id,  # Optional
    metadata={
        "model": model,
        "agent_type": agent_type,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
    },
)

await dapr_client.publish_event(
    pubsub_name=settings.dapr_pubsub_name,
    topic_name=settings.unified_cost_topic,
    data=event.model_dump_json(),
    data_content_type="application/json",
)
```

### DAPR Client Usage Pattern

```python
from dapr.aio.clients import DaprClient

# In lifespan startup
async with DaprClient() as dapr_client:
    app.state.dapr_client = dapr_client
    # ... service initialization with dapr_client
```

### Error Handling Pattern

Cost publishing is **best-effort** - failures should not fail the primary operation:

```python
try:
    await dapr_client.publish_event(...)
    logger.debug("Published cost event", cost_usd=str(cost_usd))
except Exception as e:
    logger.warning("Failed to publish cost event", error=str(e))
    # Continue - primary operation succeeds even if cost tracking fails
```

### Previous Story Intelligence

**Story 13.6 (BFF Integration Layer):**
- Established pattern for shared cost models in fp-common
- Created `CostRecordedEvent` in `fp_common/events/cost_recorded.py`
- BFF client already prepared to consume from platform-cost

**Story 13.5 (DAPR Cost Event Subscription):**
- platform-cost subscribes to `platform.cost.recorded` topic
- Handler parses `CostRecordedEvent` and persists as `UnifiedCostEvent`
- BudgetMonitor metrics updated on each event

**Story 13.1 (Shared Cost Event Model):**
- `CostRecordedEvent`, `CostType`, `CostUnit` defined in fp-common
- All cost producers use this unified schema

### Dependencies

**Upstream (must be complete):**
- Story 13.1: Shared Cost Event Model (provides `CostRecordedEvent`)
- Story 13.5: DAPR subscription handler (consumes published events)

**Downstream (will benefit):**
- Story 13.8: E2E integration tests (validates full pub/sub flow)

### Testing Strategy

**Unit Tests:**
- Mock `DaprClient.publish_event()` to verify correct event construction
- Verify best-effort error handling (log warning, don't fail operation)
- Verify correct `CostType` and metadata for each cost source

**E2E Tests:**
- Existing ai-model E2E tests should still pass (cost tracking is transparent)
- Story 13.8 will add comprehensive cost flow E2E tests

### Proto Changes

**DELETE from `proto/ai_model/v1/ai_model.proto`:**
```protobuf
service CostService {
  rpc GetDailyCostSummary(DailyCostSummaryRequest) returns (DailyCostSummaryResponse);
  rpc GetCurrentDayCost(CurrentDayCostRequest) returns (CostSummaryResponse);
  rpc GetCostByAgentType(CostByAgentTypeRequest) returns (CostByAgentTypeResponse);
  rpc GetCostByModel(CostByModelRequest) returns (CostByModelResponse);
  rpc GetCostAlerts(CostAlertsRequest) returns (CostAlertsResponse);
  rpc ConfigureCostThreshold(ConfigureCostThresholdRequest) returns (ConfigureCostThresholdResponse);
}

// All related messages...
```

### Rollback Plan

If this story needs to be rolled back:
1. Revert the commit that deleted cost files
2. ai-model will continue to persist costs locally
3. platform-cost will stop receiving events from ai-model (but other services can still publish)

### References

- [Source: `_bmad-output/architecture/adr/ADR-016-unified-cost-model.md`] - Part 2: Changes in ai-model Service
- [Source: `_bmad-output/epics/epic-13-platform-cost.md`] - Story 13.7 definition
- [Source: `libs/fp-common/fp_common/events/cost_recorded.py`] - CostRecordedEvent model
- [Source: `services/platform-cost/src/platform_cost/handlers/cost_event_handler.py`] - Consumer reference
- [Source: `services/ai-model/src/ai_model/llm/gateway.py`] - Current cost persistence (lines ~557-577)
- [Source: `services/ai-model/src/ai_model/services/embedding_service.py`] - Current cost persistence

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

**Created:**
- (none expected - this story is a refactor)

**Modified:**
- `services/ai-model/src/ai_model/config.py`
- `services/ai-model/src/ai_model/main.py`
- `services/ai-model/src/ai_model/api/grpc_server.py`
- `services/ai-model/src/ai_model/llm/gateway.py`
- `services/ai-model/src/ai_model/services/embedding_service.py`
- `services/ai-model/src/ai_model/infrastructure/azure_doc_intel_client.py`
- `services/ai-model/src/ai_model/infrastructure/repositories/__init__.py`
- `proto/ai_model/v1/ai_model.proto`

**Deleted:**
- `services/ai-model/src/ai_model/api/cost_service.py`
- `services/ai-model/src/ai_model/infrastructure/repositories/cost_event_repository.py`
- `services/ai-model/src/ai_model/infrastructure/repositories/embedding_cost_repository.py`
- `services/ai-model/src/ai_model/llm/budget_monitor.py`
- `tests/unit/ai_model/test_cost_service.py` (if exists)
- `tests/unit/ai_model/test_budget_monitor.py` (if exists)
- `tests/unit/ai_model/test_cost_event_repository.py` (if exists)
