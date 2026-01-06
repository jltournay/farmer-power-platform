# Story 0.6.14: Replace Custom DaprPubSubClient with SDK Publishing

**Status:** done
**GitHub Issue:** #115
**Epic:** [Epic 0.6: Infrastructure Hardening](../epics/epic-0-6-infrastructure-hardening.md)
**ADR:** [ADR-010: DAPR Patterns and Configuration Standards](../architecture/adr/ADR-010-dapr-patterns-configuration.md)
**Story Points:** 3
**Wave:** 4 (Type Safety & Service Boundaries)
**Prerequisites:**
- Story 0.6.5/0.6.6 (DAPR Streaming Subscriptions) - DONE - SDK `subscribe_with_handler()` pattern established
- Story 0.6.13 (CollectionClient gRPC) - DONE - Confirms DAPR service invocation patterns work correctly

---

## CRITICAL REQUIREMENTS FOR DEV AGENT

> **READ THIS FIRST - Replace custom httpx-based publishing with official DAPR SDK!**

### 1. Problem Statement

**`DaprPubSubClient`** (`services/plantation-model/src/plantation_model/infrastructure/dapr_client.py`) currently:
- **Uses `httpx.AsyncClient`** for manual HTTP POST to DAPR API
- Violates ADR-010: "Use the DAPR Python SDK for all pub/sub operations"
- Creates inconsistency: subscribing uses SDK, publishing uses custom HTTP
- Lacks built-in retry, tracing, and SDK benefits

**Evidence from code (lines 56-71):**
```python
# CURRENT (ANTI-PATTERN):
url = f"{self._base_url}/v1.0/publish/{pubsub_name}/{topic}"
async with httpx.AsyncClient() as client:  # Manual HTTP!
    response = await client.post(
        url,
        json=payload,
        headers={"Content-Type": "application/json", ...},
        timeout=10.0,
    )
```

### 2. Goal

Replace `DaprPubSubClient` with official DAPR SDK `DaprClient.publish_event()`:
1. **Use `dapr.clients.DaprClient`** for publishing (consistent with subscribers)
2. **Delete `infrastructure/dapr_client.py`** (custom httpx client)
3. **Update all publishers** to use SDK directly
4. **Maintain functional equivalence** - events still published correctly

### 3. Key Insight - SDK Pattern Already Established!

Story 0.6.5/0.6.6 established SDK usage for **subscribing**:
```python
# CORRECT PATTERN (from events/subscriber.py):
from dapr.clients import DaprClient
client = DaprClient()
client.subscribe_with_handler(...)  # SDK for subscribing
```

This story applies the **same SDK** for **publishing**:
```python
# CORRECT PATTERN (ADR-010):
from dapr.clients import DaprClient
with DaprClient() as client:
    client.publish_event(
        pubsub_name="pubsub",
        topic_name="plantation.quality.graded",
        data=json.dumps(payload),
        data_content_type="application/json",
    )
```

### 4. Definition of Done Checklist

- [x] **Custom DaprPubSubClient deleted** - Replaced with module-level `publish_event()` function
- [x] **plantation_service.py updated** - Uses `publish_event()` from infrastructure.dapr_client
- [x] **quality_event_processor.py updated** - Uses `publish_event()` from infrastructure.dapr_client
- [x] **Unit tests updated** - Mock `DaprClient` SDK instead of `DaprPubSubClient`
- [x] **E2E tests pass** - 102 passed, 1 skipped - Events published and received correctly
- [x] **Lint passes** - ruff check and format

---

## Story

As a **platform engineer**,
I want all DAPR pub/sub publishing to use the official SDK instead of custom httpx-based clients,
So that the codebase follows ADR-010 patterns consistently for both subscribing AND publishing.

## Acceptance Criteria

1. **AC1: Delete Custom DaprPubSubClient** - Given the custom `DaprPubSubClient` exists in `infrastructure/dapr_client.py`, When migration is complete, Then the file is deleted entirely, And no imports reference it.

2. **AC2: PlantationService Uses SDK** - Given `PlantationService.RegisterFarmer()` publishes `FarmerRegisteredEvent`, When I check the implementation, Then it uses `DaprClient().publish_event()` from the official SDK, Not the custom httpx client.

3. **AC3: QualityEventProcessor Uses SDK** - Given `QualityEventProcessor` publishes `plantation.quality.graded` and `plantation.performance_updated` events, When I check the implementation, Then both use `DaprClient().publish_event()` from the official SDK.

4. **AC4: Correct SDK Parameters** - Given the SDK `publish_event()` method is used, When publishing events, Then parameters match ADR-010:
   - `pubsub_name`: Component name (e.g., "pubsub")
   - `topic_name`: Topic string (e.g., "plantation.quality.graded")
   - `data`: JSON string (`json.dumps(payload)`)
   - `data_content_type`: "application/json"

5. **AC5: No Functional Regression** - Given E2E tests exercise event publishing and subscribing, When I run the full E2E test suite, Then all tests pass unchanged (behavior identical, only implementation changes).

## Tasks / Subtasks

- [x] **Task 1: Create SDK Publisher Wrapper** (AC: 2, 3, 4)
  - [x] Decided: Created module-level `publish_event()` function in `infrastructure/dapr_client.py`
  - [x] Function wraps `DaprClient.publish_event()` with proper error handling
  - [x] Follows ADR-010 pattern - no class needed, simple function approach

- [x] **Task 2: Update QualityEventProcessor** (AC: 3, 4)
  - [x] Updated import to use `from plantation_model.infrastructure.dapr_client import publish_event`
  - [x] Removed `event_publisher` parameter from `__init__`
  - [x] Updated `_emit_quality_graded_event()` to use module-level `publish_event()`
  - [x] Updated `_emit_performance_updated_event()` to use module-level `publish_event()`

- [x] **Task 3: Update PlantationServiceServicer** (AC: 2, 4)
  - [x] Updated import to use `from plantation_model.infrastructure.dapr_client import publish_event`
  - [x] Removed `dapr_client` parameter from `__init__`
  - [x] Updated `CreateFarmer()` event publishing to use module-level `publish_event()`

- [x] **Task 4: Update main.py** (AC: 2, 3)
  - [x] Removed import of `DaprPubSubClient`
  - [x] Removed `event_publisher` instantiation and passing to constructors
  - [x] Services now use module-level `publish_event()` directly

- [x] **Task 5: Refactor dapr_client.py** (AC: 1)
  - [x] Replaced class-based `DaprPubSubClient` with module-level `publish_event()` function
  - [x] Function uses official DAPR SDK `DaprClient.publish_event()`
  - [x] Proper error handling for `DaprInternalError` and `RpcError`

- [x] **Task 6: Update Unit Tests** (AC: All)
  - [x] Updated `tests/unit/plantation/test_dapr_client.py` - Tests SDK-based `publish_event()`
  - [x] Updated `tests/unit/plantation/test_grpc_*.py` - Removed `dapr_client` fixture/parameter
  - [x] Updated `tests/unit/plantation/test_quality_event_processor.py` - Patches module-level function
  - [x] All 420 plantation unit tests pass

- [x] **Task 7: Update Integration Tests** (AC: 5)
  - [x] Updated `tests/integration/test_plantation_farmer_flow.py` - Uses `publish_event` function

- [x] **Task 8: Run Local Tests & E2E** (AC: 5)
  - [x] Run unit tests: `pytest tests/unit/plantation/ -v` - **420 passed**
  - [x] Run E2E with `--build` flag - **102 passed, 1 skipped**
  - [x] Capture E2E test output in story file

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [x] GitHub Issue exists or created: `gh issue create --title "Story 0.6.14: Replace Custom DaprPubSubClient with SDK Publishing"`
- [x] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/0-6-14-dapr-sdk-publishing
  ```

**Branch name:** `feature/0-6-14-dapr-sdk-publishing`

### During Development
- [x] All commits reference GitHub issue: `Relates to #115`
- [x] Commits are atomic by type (production, test, seed - not mixed)
- [x] Push to feature branch: `git push -u origin feature/0-6-14-dapr-sdk-publishing`

### Story Done
- [x] Create Pull Request: `gh pr create --title "Story 0.6.14: Replace Custom DaprPubSubClient with SDK Publishing" --base main`
- [x] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d feature/0-6-14-dapr-sdk-publishing`

**PR URL:** https://github.com/jltournay/farmer-power-platform/pull/116

---

## Implementation Reference

### File Structure

```
services/plantation-model/src/plantation_model/
├── infrastructure/
│   ├── __init__.py                 # MODIFY - Remove DaprPubSubClient export
│   └── dapr_client.py              # DELETE (custom httpx client)
├── api/
│   └── plantation_service.py       # MODIFY - Use DaprClient
├── domain/services/
│   └── quality_event_processor.py  # MODIFY - Use DaprClient
└── main.py                         # MODIFY - Use DaprClient

tests/unit/plantation/
├── test_dapr_client.py             # DELETE (tests deleted class)
├── test_grpc_*.py                  # MODIFY - Mock DaprClient
└── test_quality_event_processor.py # MODIFY - Mock DaprClient

tests/integration/
├── test_plantation_farmer_flow.py  # MODIFY - Use DaprClient
└── test_quality_event_flow.py      # MODIFY - Mock DaprClient
```

### SDK Publishing Pattern (ADR-010)

```python
# CORRECT PATTERN (from ADR-010):
import json
from dapr.clients import DaprClient

async def publish_quality_result(document_id: str, grades: dict) -> None:
    """Publish quality result event using DAPR SDK."""
    with DaprClient() as client:
        client.publish_event(
            pubsub_name="pubsub",
            topic_name="plantation.quality.graded",
            data=json.dumps({
                "document_id": document_id,
                "grades": grades,
            }),
            data_content_type="application/json",
        )
```

### Migration Example: QualityEventProcessor

**BEFORE (custom httpx):**
```python
# quality_event_processor.py (CURRENT - lines 743-747)
success = await self._event_publisher.publish_event(
    pubsub_name=settings.dapr_pubsub_name,
    topic="plantation.quality.graded",
    data=payload,
)
```

**AFTER (SDK):**
```python
# quality_event_processor.py (TARGET)
import json
from dapr.clients import DaprClient

# In publish method:
with DaprClient() as client:
    client.publish_event(
        pubsub_name=settings.dapr_pubsub_name,
        topic_name="plantation.quality.graded",
        data=json.dumps(payload.model_dump(mode="json")) if hasattr(payload, 'model_dump') else json.dumps(payload),
        data_content_type="application/json",
    )
```

### Migration Example: PlantationServiceServicer

**BEFORE (custom httpx):**
```python
# plantation_service.py (CURRENT - lines 944-948)
await self._dapr_client.publish_event(
    pubsub_name=settings.dapr_pubsub_name,
    topic=settings.dapr_farmer_events_topic,
    data=event,
)
```

**AFTER (SDK):**
```python
# plantation_service.py (TARGET)
import json
from dapr.clients import DaprClient

# In RegisterFarmer method:
with DaprClient() as client:
    client.publish_event(
        pubsub_name=settings.dapr_pubsub_name,
        topic_name=settings.dapr_farmer_events_topic,
        data=json.dumps(event.model_dump(mode="json")),
        data_content_type="application/json",
    )
```

### SDK vs Custom Client Comparison

| Aspect | Custom `DaprPubSubClient` | Official `DaprClient` |
|--------|---------------------------|----------------------|
| Transport | Manual httpx HTTP | SDK handles transport |
| Error handling | Custom try/except | SDK built-in retry |
| Tracing | Manual (missing) | OpenTelemetry integrated |
| Configuration | Manual URL construction | Auto-discovers sidecar |
| Maintenance | Must maintain ourselves | Maintained by DAPR team |

### Key Differences in Parameters

| Parameter | Custom Client | SDK Client |
|-----------|---------------|------------|
| Topic | `topic` | `topic_name` |
| Data | `dict` or `BaseModel` | `json.dumps(...)` string |
| Content type | Header in request | `data_content_type` param |

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
PYTHONPATH="${PYTHONPATH}:libs/fp-common:libs/fp-proto/src:libs/fp-testing:services/plantation-model/src:services/collection-model/src:services/bff/src:services/ai-model/src" pytest tests/unit/plantation/ -v
```
**Output:**
```
================= 420 passed, 15 warnings in 127.13s (0:02:07) =================
```
**Unit tests passed:** ✅ Yes

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure with --build (MANDATORY)
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build

# Wait for services, then run tests
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src:libs/fp-common" pytest tests/e2e/scenarios/ -v

# Tear down
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```
**Output:**
```
================== 102 passed, 1 skipped in 130.28s (0:02:10) ==================
```
**E2E passed:** ✅ Yes

### 3. Lint Check
```bash
ruff check . && ruff format --check .
```
**Lint passed:** ✅ Yes

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin feature/0-6-14-dapr-sdk-publishing

# Wait ~30s, then check CI status
gh run list --branch feature/0-6-14-dapr-sdk-publishing --limit 3
```
**CI Run ID:** 20760330148
**CI Status:** [x] Passed / [ ] Failed
**Verification Date:** 2026-01-06

### 5. E2E CI Verification (MANDATORY - Step 9c)

> **After push, E2E CI workflow must be triggered and pass**

```bash
# Trigger E2E workflow
gh workflow run e2e.yaml --ref feature/0-6-14-dapr-sdk-publishing

# Wait and check status
gh run list --workflow=e2e.yaml --branch feature/0-6-14-dapr-sdk-publishing --limit 3
```
**E2E CI Run ID:** 20759879155
**E2E CI Status:** [x] Passed / [ ] Failed
**Verification Date:** 2026-01-06

---

## Dev Notes

### Architecture Context

**Wave 4 Overview:**
1. **Story 0.6.11** - Create converters in fp-common - DONE
2. **Story 0.6.12** - MCP clients use converters, return Pydantic - DONE
3. **Story 0.6.13** - Replace CollectionClient direct DB with gRPC - DONE
4. **Story 0.6.14 (this)** - Replace custom DaprPubSubClient with SDK

This story **completes ADR-010 compliance** by ensuring BOTH subscribing AND publishing use the official DAPR SDK.

### Key Technical Decisions

1. **Use SDK directly in services** - No wrapper needed. The SDK is simple enough to use inline. Avoid creating another abstraction layer.

2. **Synchronous `with DaprClient()` context manager** - The SDK's `publish_event()` is synchronous (not async). Use `with` statement for proper cleanup.

3. **JSON serialization** - SDK expects `data` as string, not dict. Always use `json.dumps()`.

4. **Pydantic to JSON** - For `BaseModel` objects, use `model.model_dump(mode="json")` before `json.dumps()`.

### Learnings from Previous Stories

**From Story 0.6.5/0.6.6 (DAPR Streaming Subscriptions):**
- `DaprClient` requires DAPR 1.14.0+ for streaming subscriptions
- Same client works for publishing - no separate class needed
- SDK auto-discovers DAPR sidecar at `localhost:3500` (HTTP) and `localhost:50001` (gRPC)

**From Story 0.6.13 (CollectionClient gRPC):**
- Confirmed DAPR service invocation works correctly in E2E
- Plantation Model can communicate with other services via DAPR

### SDK Method Signature Reference

```python
# From dapr-python SDK
def publish_event(
    self,
    pubsub_name: str,           # Component name, e.g., "pubsub"
    topic_name: str,            # Topic, e.g., "plantation.quality.graded"
    data: Union[bytes, str],    # Must be bytes or string, NOT dict
    data_content_type: str = "text/plain",  # Usually "application/json"
    publish_metadata: Optional[Dict[str, str]] = None,
) -> DaprResponse:
    ...
```

### Anti-Patterns to Avoid

1. **DO NOT pass dict to `data`** - SDK expects `bytes` or `str`, not dict
2. **DO NOT use async `await`** - SDK `publish_event()` is synchronous
3. **DO NOT forget `data_content_type`** - Omitting causes subscriber parsing issues
4. **DO NOT mix `topic` and `topic_name`** - SDK uses `topic_name`, custom used `topic`

### Potential Gotchas

1. **Pydantic serialization** - `model.model_dump()` returns dict, not JSON string. Chain with `json.dumps()`.

2. **Error handling** - SDK raises `DaprInternalError` on failure. Consider wrapping with try/except and logging.

3. **Settings reference** - Keep using `settings.dapr_pubsub_name` and `settings.dapr_farmer_events_topic` - no change needed.

4. **Unit test mocking** - SDK `DaprClient` is a class, mock it: `@patch('module.DaprClient')`.

### Files Modified by This Story

**DELETED:**
- `services/plantation-model/src/plantation_model/infrastructure/dapr_client.py`
- `tests/unit/plantation/test_dapr_client.py`

**MODIFIED:**
- `services/plantation-model/src/plantation_model/api/plantation_service.py`
- `services/plantation-model/src/plantation_model/domain/services/quality_event_processor.py`
- `services/plantation-model/src/plantation_model/main.py`
- `services/plantation-model/src/plantation_model/infrastructure/__init__.py`
- `tests/unit/plantation/test_grpc_*.py` (multiple files)
- `tests/integration/test_plantation_farmer_flow.py`
- `tests/integration/test_quality_event_flow.py`

### References

- [ADR-010: DAPR Patterns](../architecture/adr/ADR-010-dapr-patterns-configuration.md) - **Primary reference**
- [DAPR Python SDK Docs](https://docs.dapr.io/developing-applications/sdks/python/)
- [Epic 0.6: Infrastructure Hardening](../epics/epic-0-6-infrastructure-hardening.md)
- [Story 0.6.5: Plantation Streaming Subscriptions](./0-6-5-plantation-streaming-subscriptions.md) - SDK subscriber pattern
- [Story 0.6.13: CollectionClient gRPC](./0-6-13-collection-client-grpc.md) - Recent DAPR patterns
- [project-context.md](../project-context.md) - Critical rules reference

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- CI Run 20760330148: All tests passed (Lint, Unit, Integration, Frontend)
- E2E CI Run 20759879155: All E2E tests passed

### Completion Notes List

1. Replaced class-based `DaprPubSubClient` with module-level `publish_event()` function
2. All services now import and use `publish_event()` directly
3. Fixed additional test file in `tests/unit/plantation_model/` that was missed initially
4. Both CI and E2E CI workflows pass
5. **Code Review Refactoring:** Moved publisher from `infrastructure/dapr_client.py` to `events/publisher.py` for consistency with `events/subscriber.py`

### File List

**Created:**
- `services/plantation-model/src/plantation_model/events/publisher.py` - New location for `publish_event()` function

**Modified:**
- `services/plantation-model/src/plantation_model/events/__init__.py` - Export `publish_event` from publisher
- `services/plantation-model/src/plantation_model/api/plantation_service.py` - Import from `events.publisher`
- `services/plantation-model/src/plantation_model/domain/services/quality_event_processor.py` - Import from `events.publisher`
- `services/plantation-model/src/plantation_model/main.py` - Removed DaprPubSubClient instantiation
- `tests/unit/plantation/test_publisher.py` - Renamed from test_dapr_client.py, updated imports
- `tests/unit/plantation/test_grpc_collection_point.py` - Removed dapr_client fixture
- `tests/unit/plantation/test_grpc_factory.py` - Removed dapr_client fixture
- `tests/unit/plantation/test_grpc_farmer_preferences.py` - Removed dapr_client fixture
- `tests/unit/plantation/test_grpc_farmer_summary.py` - Removed dapr_client fixture
- `tests/unit/plantation/test_grpc_grading_model.py` - Removed dapr_client fixture
- `tests/unit/plantation/test_quality_event_processor.py` - Updated to patch module-level function
- `tests/unit/plantation_model/domain/services/test_quality_event_processor_linkage.py` - Removed event_publisher fixture
- `tests/integration/test_plantation_farmer_flow.py` - Updated imports and mock paths

**Deleted:**
- `services/plantation-model/src/plantation_model/infrastructure/dapr_client.py` - Moved to events/publisher.py

---

## Code Review

**Review Date:** 2026-01-06
**Reviewer:** Claude Opus 4.5 (adversarial code review workflow)
**Review Type:** Adversarial Senior Developer Review

### Review Outcome: ✅ APPROVE (with minor action items)

### Acceptance Criteria Verification

| AC | Status | Evidence |
|----|--------|----------|
| AC1: Delete Custom DaprPubSubClient | ✅ PASS | Class deleted, replaced with module-level `publish_event()` function (acceptable deviation from "delete file entirely") |
| AC2: PlantationService Uses SDK | ✅ PASS | `plantation_service.py:946-949` uses `publish_event()` |
| AC3: QualityEventProcessor Uses SDK | ✅ PASS | Lines 740-744 and 781-785 use `publish_event()` |
| AC4: Correct SDK Parameters | ✅ PASS | `pubsub_name`, `topic_name`, `data` (JSON string), `data_content_type="application/json"` all correct per ADR-010 |
| AC5: No Functional Regression | ✅ PASS | E2E: 102 passed, 1 skipped; CI: all jobs passed |

### Quality Gates Verification

| Gate | Status | Evidence |
|------|--------|----------|
| E2E Tests (Local) | ✅ PASS | 102 passed, 1 skipped in 130.28s |
| E2E Tests (CI) | ✅ PASS | Run ID 20759879155 - success |
| CI Tests | ✅ PASS | Run ID 20760330148 - success |
| PR Created | ✅ PASS | PR #116 |

### Findings Summary

**HIGH Severity:** None

**MEDIUM Severity:**
1. **[M1] Missing test file update: `tests/integration/test_quality_event_flow.py:226`**
   - Problem: Still mocks `plantation_model.main.DaprPubSubClient` which no longer exists
   - Impact: Test will fail if run (but not currently run in CI - marked `@pytest.mark.integration` while CI uses `-m mongodb`)
   - **Action Required:** Update mock path or remove stale mock

**LOW Severity:**
1. **[L1] Story file lists `test_quality_event_flow.py` in task breakdown (line 198) as "MODIFY - Mock DaprClient" but it wasn't updated**
   - Impact: Documentation inconsistency
   - Mitigation: Non-blocking since test isn't run in CI

### Action Items

- [x] **[M1]** Update `tests/integration/test_quality_event_flow.py` to remove/fix stale `DaprPubSubClient` mock
  - **Fixed:** Commit 1373aa8 - Removed stale mock, updated QualityEventProcessor instantiation, patched module-level `publish_event()`

### Reviewer Notes

1. Implementation correctly follows ADR-010 DAPR SDK publishing pattern
2. The choice to refactor `dapr_client.py` instead of deleting it entirely is reasonable - keeps a central location for publish functionality
3. All unit tests pass (6 new tests for `publish_event`, 19 for QualityEventProcessor)
4. The medium severity finding is non-blocking because the affected test is not part of CI's test suite

**Verdict:** Story 0.6.14 meets all acceptance criteria and is approved for merge.

### Post-Review Refactoring

**Date:** 2026-01-06
**Requested by:** User

Moved publisher from `infrastructure/dapr_client.py` to `events/publisher.py` for architectural consistency:
- Publisher and subscriber now both live in the `events/` package
- Cleaner separation: `infrastructure/` for external adapters (MongoDB, gRPC), `events/` for DAPR pub/sub
- All imports and mock paths updated accordingly

---

## Code Review #2 (Follow-up)

**Date:** 2026-01-06
**Reviewer:** Claude Opus 4.5

### Review Scope
Follow-up review to fix action items from Code Review #1.

### Issues Fixed

**[M1] Integration test stale mock (RESOLVED)**
- Updated `tests/integration/test_quality_event_flow.py`:
  - Removed `event_publisher=mock_event_publisher` from `QualityEventProcessor` constructor (parameter no longer exists)
  - Created `mock_publish_event` fixture to mock module-level `publish_event()` function
  - Updated all test methods to use `mock_publish_event` instead of `mock_event_publisher`
  - Added patch for `plantation_model.events.publisher.publish_event` in test context

**[M2] Uncommitted config changes (RESOLVED)**
- Included `extra="ignore"` setting in ai-model and collection-model config.py in this commit per user request

### Verification
- All unit tests pass (6 publisher tests, 19 QualityEventProcessor tests)
- Ruff linting passes
- Code pushed to branch

**Verdict:** ✅ APPROVED - All action items resolved. Story ready for merge.
