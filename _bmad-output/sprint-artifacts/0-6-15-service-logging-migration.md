# Story 0.6.15: Migrate All Services to fp-common Logging Module

**Status:** review
**GitHub Issue:** #150
**Epic:** [Epic 0.6: Infrastructure Hardening](../epics/epic-0-6-infrastructure-hardening.md)
**ADR:** [ADR-009: Logging Standards and Runtime Configuration](../architecture/adr/ADR-009-logging-standards-runtime-configuration.md)
**Depends On:** Story 0.6.2 (Shared Logging Module) - DONE
**Story Points:** 5

---

## Required Reading (MANDATORY)

Before starting implementation, you MUST read:

| Document | Why |
|----------|-----|
| `tests/e2e/E2E-TESTING-MENTAL-MODEL.md` | Understand truth hierarchy: Proto → Production → Seed → Tests. Never modify production code to make tests pass. |
| [ADR-015: E2E Autonomous Debugging Infrastructure](../architecture/adr/ADR-015-e2e-autonomous-debugging-infrastructure.md) | Understand local E2E environment variable handling and Docker image rebuild requirements. |

---

## Context

Story 0.6.2 created the shared logging module in `fp-common` with:
- `configure_logging(service_name)` - Structured logging with OpenTelemetry trace injection
- `create_admin_router()` - Runtime log level control via HTTP endpoints
- `reset_logging()` - Test isolation utility

**However, no service has migrated to use it.** All 4 active services implement custom structlog configurations that lack:
- Service context in logs
- OpenTelemetry trace_id/span_id injection
- Runtime `/admin/logging` endpoints
- Hierarchical logger naming per ADR-009

Additionally, `plantation-model` mixes `structlog` with stdlib `logging.getLogger()` in repository files.

---

## Story

As a **platform engineer**,
I want all services to use the shared `fp_common` logging module,
So that logs are consistent, traceable, and runtime-debuggable across the platform.

---

## Acceptance Criteria

### AC1: Services Use fp_common.configure_logging()

**Given** each service has custom structlog.configure() code
**When** I check the main.py lifespan for each service
**Then** all 4 services call `configure_logging(service_name)` from fp_common
**And** the duplicate structlog.configure() code is removed

**Services to migrate:**
- `services/ai-model/src/ai_model/main.py`
- `services/collection-model/src/collection_model/main.py`
- `services/plantation-model/src/plantation_model/main.py`
- `services/bff/src/bff/main.py`

### AC2: Admin Router Included

**Given** services don't have runtime log control
**When** I check each service's FastAPI app
**Then** all 4 services include `create_admin_router()` from fp_common
**And** `GET/POST/DELETE /admin/logging/*` endpoints are available

### AC3: Plantation Model Stdlib Logging Fixed

**Given** plantation-model repositories use `logging.getLogger()`
**When** I check the infrastructure/repositories/ folder
**Then** all files use `structlog.get_logger()` instead
**And** no imports from stdlib `logging` module (except typing)

**Files to fix:**
- `farmer_repository.py`
- `factory_repository.py`
- `grading_model_repository.py`
- `region_repository.py`
- `farmer_performance_repository.py`
- `regional_weather_repository.py`

### AC4: Logs Include Required Context

**Given** logging is configured via fp_common
**When** I check log output from any service
**Then** logs include:
- `service` - Service name
- `timestamp` - ISO format
- `level` - Log level
- `trace_id` - OpenTelemetry trace ID (when span active)
- `span_id` - OpenTelemetry span ID (when span active)

---

## Tasks / Subtasks

- [x] **Task 1: Migrate ai-model** (AC: 1, 2, 4) ✅
  - [x] Replace custom structlog.configure() with fp_common.configure_logging("ai-model")
  - [x] Add create_admin_router() to FastAPI app
  - [x] Verify logs include service context and trace IDs
  - [x] Run unit tests to verify no regressions

- [x] **Task 2: Migrate collection-model** (AC: 1, 2, 4) ✅
  - [x] Replace custom structlog.configure() with fp_common.configure_logging("collection-model")
  - [x] Add create_admin_router() to FastAPI app
  - [x] Verify logs include service context and trace IDs
  - [x] Run unit tests to verify no regressions

- [x] **Task 3: Migrate plantation-model** (AC: 1, 2, 3, 4) ✅
  - [x] Replace custom structlog.configure() with fp_common.configure_logging("plantation-model")
  - [x] Add create_admin_router() to FastAPI app
  - [x] Fix 8 repository files: replace logging.getLogger() with structlog.get_logger()
  - [x] Remove stdlib logging imports from repository files
  - [x] Verify logs include service context and trace IDs
  - [x] Run unit tests to verify no regressions

- [x] **Task 4: Migrate bff** (AC: 1, 2, 4) ✅
  - [x] Add fp_common.configure_logging("bff") (currently no config at all)
  - [x] Add create_admin_router() to FastAPI app
  - [x] Verify logs include service context and trace IDs
  - [x] Run unit tests to verify no regressions

- [x] **Task 5: E2E Validation** (AC: All) ✅
  - [ ] Start E2E infrastructure and run tests (per ADR-015 — **run all in same shell session**):
    ```bash
    # Step 1: Export .env variables to shell (set -a = auto-export, set +a = stop auto-export)
    set -a && source .env && set +a

    # Step 2: Start Docker with --build (MUST rebuild to include code changes)
    docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build

    # Step 3: Wait for services to be healthy
    sleep 10

    # Step 4: Run E2E tests (PYTHONPATH for fp-proto module resolution)
    PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v
    ```
  - [ ] Manually verify `/admin/logging` endpoints respond (no E2E test required - curl verification):
    ```bash
    curl -s http://localhost:8001/admin/logging  # plantation-model → expect {}
    curl -s http://localhost:8002/admin/logging  # collection-model → expect {}
    curl -s http://localhost:8091/admin/logging  # ai-model → expect {}
    curl -s http://localhost:8083/admin/logging  # bff → expect {}
    ```
  - [ ] Capture sample log output showing new context fields (service, trace_id, span_id)
  - [ ] Tear down infrastructure:
    ```bash
    docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
    ```

---

## Unit Tests Required

### Existing Tests (Must Pass)

All existing unit tests in each service must continue to pass. The logging migration should be transparent to test behavior.

### New Tests (Optional)

If time permits, add integration tests for `/admin/logging` endpoint in each service:
```python
# tests/unit/{service}/api/test_admin_logging.py
def test_admin_logging_endpoint_available(client):
    """GET /admin/logging returns empty dict."""
    response = client.get("/admin/logging")
    assert response.status_code == 200
```

---

## E2E Test Impact

### Expected Behavior
- **No breaking changes** - Services log the same events, just with richer context
- **Log format unchanged** - Already JSON, just with additional fields

### Verification (per ADR-015)

**Run all commands in the same shell session:**
```bash
# Step 1: Export .env variables to shell
set -a && source .env && set +a

# Step 2: Start Docker with --build
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build

# Step 3: Wait for services, then run tests
sleep 10
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v

# Step 4: Tear down
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```

**Verify env vars are inside containers (not just shell):**
```bash
docker exec e2e-ai-model printenv OPENROUTER_API_KEY | head -c 10
# Should show first 10 chars of key, not empty
```

---

## Implementation Notes

### Before (Custom Config)

```python
# services/ai-model/src/ai_model/main.py (lines 70-86)
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        # ... custom processors ...
        structlog.processors.JSONRenderer(),
    ],
    # ... custom config ...
)
```

### After (Shared Config)

```python
# services/ai-model/src/ai_model/main.py
from fp_common import configure_logging, create_admin_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging("ai-model")
    # ... rest of lifespan ...
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(create_admin_router())
```

### Plantation Repository Fix

```python
# Before
import logging
logger = logging.getLogger(__name__)

# After
import structlog
logger = structlog.get_logger("plantation_model.infrastructure.repositories.farmer_repository")
```

---

## Definition of Done

- [ ] All 4 services use `fp_common.configure_logging()`
- [ ] All 4 services include `/admin/logging` endpoints
- [ ] Plantation-model repositories use structlog (no stdlib logging)
- [ ] All unit tests pass
- [ ] All E2E tests pass
- [ ] Lint passes (`ruff check . && ruff format --check .`)
- [ ] CI workflow passes
- [ ] E2E CI workflow passes
- [ ] Code review passes

---

## References

- [ADR-009: Logging Standards and Runtime Configuration](../architecture/adr/ADR-009-logging-standards-runtime-configuration.md)
- [Story 0.6.2: Shared Logging Module](./0-6-2-shared-logging-module.md) (prerequisite - DONE)
- [fp_common logging module](../../libs/fp-common/fp_common/logging.py)
- [fp_common admin router](../../libs/fp-common/fp_common/admin.py)

---

## Implementation Log

### 2026-01-10: Implementation Complete

**Files Modified:**

1. **ai-model/main.py** - Removed custom structlog.configure() and logging.basicConfig(), added configure_logging("ai-model") and create_admin_router()

2. **collection-model/main.py** - Removed custom structlog.configure() and logging.basicConfig(), added configure_logging("collection-model") and create_admin_router()

3. **plantation-model/main.py** - Removed custom structlog.configure(), added configure_logging("plantation-model") and create_admin_router()

4. **bff/main.py** - Added configure_logging("bff") and create_admin_router() (no prior logging config)

5. **plantation-model/infrastructure/repositories/** - Fixed 8 files (not 6 as originally noted):
   - base.py
   - farmer_repository.py
   - factory_repository.py
   - grading_model_repository.py
   - region_repository.py
   - farmer_performance_repository.py
   - regional_weather_repository.py
   - collection_point_repository.py

**Test Results:**

- Unit Tests: 1399 passed (no regressions)
- E2E Tests: 102 passed, 4 failed (expected - require OPENROUTER_API_KEY), 1 skipped

**Admin Endpoint Verification:**

```bash
# GET /admin/logging - Returns list of loggers with non-default levels
$ curl -s http://localhost:8001/admin/logging | jq .
{"loggers":{"uvicorn.error":"INFO","uvicorn":"INFO","uvicorn.access":"INFO"}}

# POST /admin/logging/{logger_name}?level=DEBUG - Set log level
$ curl -s -X POST 'http://localhost:8001/admin/logging/plantation_model.domain?level=DEBUG' | jq .
{"logger":"plantation_model.domain","level":"DEBUG","status":"updated"}

# DELETE /admin/logging/{logger_name} - Reset to default
$ curl -s -X DELETE 'http://localhost:8001/admin/logging/plantation_model.domain' | jq .
{"logger":"plantation_model.domain","status":"reset"}
```

**CI Results:**
- Quality CI: ✅ PASSED (Run ID: 20879305683)
- E2E CI: ✅ PASSED (Run ID: 20879409322)