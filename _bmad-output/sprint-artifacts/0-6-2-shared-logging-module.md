# Story 0.6.2: Shared Logging Module with Runtime Configuration

**Status:** To Do
**GitHub Issue:** TBD
**Epic:** [Epic 0.6: Infrastructure Hardening](../epics/epic-0-6-infrastructure-hardening.md)
**ADR:** [ADR-009: Logging Standards and Runtime Configuration](../architecture/adr/ADR-009-logging-standards-runtime-configuration.md)
**Story Points:** 3

---

## CRITICAL REQUIREMENTS FOR DEV AGENT

> **READ THIS FIRST - Story is NOT done until ALL these steps are completed!**

### 1. This Creates SHARED Infrastructure

This story creates a shared logging module in fp-common that ALL services will use. Changes here affect the entire platform.

### 2. CI Runs on Feature Branches

```bash
git push origin story/0-6-2-shared-logging-module
gh run list --branch story/0-6-2-shared-logging-module --limit 3
```

### 3. Definition of Done Checklist

- [ ] **Logging module created** - `fp_common/logging.py` exists
- [ ] **Trace context injection** - OpenTelemetry trace_id/span_id in logs
- [ ] **Runtime endpoint works** - POST/DELETE `/admin/logging/{logger}` tested
- [ ] **Unit tests pass** - New tests in tests/unit/fp_common/logging/
- [ ] **E2E tests pass** - No regressions
- [ ] **Lint passes** - `ruff check . && ruff format --check .`
- [ ] **CI workflow passes**

---

## Story

As a **developer debugging production issues**,
I want consistent structured logging with runtime log level control,
So that I can enable DEBUG for specific packages without pod restart.

## Acceptance Criteria

1. **AC1: Logging Module Available** - Given logging needs to be configured, When I import from fp-common, Then `from fp_common.logging import configure_logging` is available And `configure_logging("plantation-model")` sets up structlog with JSON output

2. **AC2: Structured Log Output** - Given logging is configured, When I call `structlog.get_logger("plantation_model.domain.services")`, Then logs include: service name, timestamp (ISO), log level, trace_id, span_id

3. **AC3: Runtime Level Control** - Given a service is running, When I POST to `/admin/logging/plantation_model.domain?level=DEBUG`, Then that logger and children are set to DEBUG And other loggers remain at INFO

4. **AC4: Level Reset** - Given debug logging was enabled, When I DELETE `/admin/logging/plantation_model.domain`, Then that logger resets to default level

## Tasks / Subtasks

- [ ] **Task 1: Create Logging Module** (AC: 1, 2)
  - [ ] Create `libs/fp-common/fp_common/logging.py`
  - [ ] Implement `configure_logging(service_name: str)` function
  - [ ] Configure structlog with JSON renderer
  - [ ] Add timestamp processor (ISO format)
  - [ ] Add log level processor
  - [ ] Add service name context

- [ ] **Task 2: Add OpenTelemetry Trace Context** (AC: 2)
  - [ ] Create `add_trace_context` processor
  - [ ] Extract trace_id from current span
  - [ ] Extract span_id from current span
  - [ ] Handle case when no span is active

- [ ] **Task 3: Create Admin Router** (AC: 3, 4)
  - [ ] Create `libs/fp-common/fp_common/admin.py`
  - [ ] Implement `POST /admin/logging/{logger_name}` endpoint
  - [ ] Implement `DELETE /admin/logging/{logger_name}` endpoint
  - [ ] Implement `GET /admin/logging` to list current levels

- [ ] **Task 4: Create Unit Tests** (AC: All)
  - [ ] Create `tests/unit/fp_common/logging/test_configure_logging.py`
  - [ ] Create `tests/unit/fp_common/logging/test_trace_context.py`
  - [ ] Create `tests/unit/fp_common/admin/test_logging_endpoint.py`

- [ ] **Task 5: Verify Integration** (AC: All)
  - [ ] Run unit tests: `pytest tests/unit/fp_common/ -v`
  - [ ] Run E2E tests: verify no regressions
  - [ ] Run lint: `ruff check . && ruff format --check .`

## Git Workflow (MANDATORY)

### Story Start
- [ ] GitHub Issue created
- [ ] Feature branch created:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-6-2-shared-logging-module
  ```

**Branch name:** `story/0-6-2-shared-logging-module`

---

## Unit Tests Required

### New Tests to Create

```python
# tests/unit/fp_common/logging/test_configure_logging.py
class TestConfigureLogging:
    def test_configure_logging_sets_json_renderer(self):
        """configure_logging uses JSON renderer."""
        configure_logging("test-service")
        logger = structlog.get_logger("test")
        # Verify output is JSON format
        ...

    def test_configure_logging_adds_service_name(self):
        """Logs include service name in context."""
        configure_logging("plantation-model")
        logger = structlog.get_logger("test")
        # Log and capture output
        # Verify "service": "plantation-model" in output
        ...

    def test_configure_logging_uses_iso_timestamp(self):
        """Timestamps are in ISO format."""
        ...

# tests/unit/fp_common/logging/test_trace_context.py
class TestTraceContext:
    def test_trace_context_adds_trace_id_when_span_active(self):
        """trace_id injected when OpenTelemetry span active."""
        with tracer.start_as_current_span("test-span"):
            logger = structlog.get_logger("test")
            # Capture log output
            # Verify trace_id and span_id present
            ...

    def test_trace_context_handles_no_active_span(self):
        """No error when no span active."""
        logger = structlog.get_logger("test")
        # Should log without trace_id/span_id
        ...

# tests/unit/fp_common/admin/test_logging_endpoint.py
class TestLoggingEndpoint:
    @pytest.fixture
    def client(self):
        from fp_common.admin import create_admin_router
        app = FastAPI()
        app.include_router(create_admin_router())
        return TestClient(app)

    def test_set_log_level_updates_logger(self, client):
        """POST /admin/logging/{name}?level=DEBUG sets level."""
        response = client.post("/admin/logging/test_logger?level=DEBUG")
        assert response.status_code == 200
        assert logging.getLogger("test_logger").level == logging.DEBUG

    def test_reset_log_level_restores_default(self, client):
        """DELETE /admin/logging/{name} resets level."""
        logging.getLogger("test_logger").setLevel(logging.DEBUG)
        response = client.delete("/admin/logging/test_logger")
        assert response.status_code == 200
        assert logging.getLogger("test_logger").level == logging.NOTSET

    def test_get_log_levels_lists_configured(self, client):
        """GET /admin/logging lists non-default levels."""
        ...
```

---

## E2E Test Impact

### Expected Behavior
- **No breaking changes** - Services continue to log as before
- **New capability** - `/admin/logging` endpoint available for debugging

### Verification
E2E tests should pass unchanged. New logging format is JSON (already the case for most services).

### Future Use
When debugging E2E failures:
```bash
# Enable DEBUG logging for quality processor
curl -X POST "http://localhost:8001/admin/logging/plantation_model.domain.services.quality_event_processor?level=DEBUG"

# Run failing test
pytest tests/e2e/scenarios/test_07_grading_validation.py -v

# Reset logging
curl -X DELETE "http://localhost:8001/admin/logging/plantation_model.domain.services.quality_event_processor"
```

---

## Implementation Notes

### Logging Module Structure

```python
# libs/fp-common/fp_common/logging.py
import logging
import structlog
from opentelemetry import trace

def add_service_context(service_name: str):
    """Create processor that adds service name to all logs."""
    def processor(logger, method_name, event_dict):
        event_dict["service"] = service_name
        return event_dict
    return processor

def add_trace_context(logger, method_name, event_dict):
    """Add OpenTelemetry trace context to logs."""
    span = trace.get_current_span()
    if span.is_recording():
        ctx = span.get_span_context()
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict

def configure_logging(service_name: str, log_format: str = "json") -> None:
    """Configure structured logging for a service.

    Args:
        service_name: Name of the service for log context
        log_format: Output format - "json" or "console"
    """
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        add_service_context(service_name),
        add_trace_context,
    ]

    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

### Admin Router Structure

```python
# libs/fp-common/fp_common/admin.py
import logging
from fastapi import APIRouter, Query

def create_admin_router() -> APIRouter:
    """Create admin router with logging endpoints."""
    router = APIRouter(prefix="/admin", tags=["admin"])

    @router.post("/logging/{logger_name}")
    async def set_log_level(logger_name: str, level: str = Query(...)):
        """Set log level for a specific logger at runtime."""
        logging.getLogger(logger_name).setLevel(level.upper())
        return {"logger": logger_name, "level": level, "status": "updated"}

    @router.delete("/logging/{logger_name}")
    async def reset_log_level(logger_name: str):
        """Reset logger to default level."""
        logging.getLogger(logger_name).setLevel(logging.NOTSET)
        return {"logger": logger_name, "status": "reset"}

    @router.get("/logging")
    async def list_log_levels():
        """List all loggers with non-default levels."""
        loggers = {}
        for name, logger in logging.Logger.manager.loggerDict.items():
            if isinstance(logger, logging.Logger) and logger.level != logging.NOTSET:
                loggers[name] = logging.getLevelName(logger.level)
        return {"loggers": loggers}

    return router
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Default log level |
| `LOG_FORMAT` | `json` | Output format: `json` or `console` |

---

## Local Test Run Evidence (MANDATORY)

**1. Unit Tests:**
```bash
pytest tests/unit/fp_common/logging/ -v
pytest tests/unit/fp_common/admin/ -v
```
**Output:**
```
(paste test output here)
```

**2. E2E Tests Pass:**
```bash
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v
```
**Output:**
```
(paste test output here)
```

**3. Lint Check:**
```bash
ruff check . && ruff format --check .
```
**Lint passed:** [ ] Yes / [ ] No

---

## E2E Test Strategy (Mental Model Alignment)

> **Reference:** `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

### Direction of Change

This story **adds new infrastructure** (shared logging module). It does NOT change existing behavior.

| Aspect | Impact |
|--------|--------|
| Proto definitions | **UNCHANGED** |
| Production behavior | **UNCHANGED** - Services log the same events |
| E2E tests | **MUST PASS WITHOUT MODIFICATION** |
| New capability | `/admin/logging` endpoint for debugging |

### Existing E2E Tests

**ALL existing E2E tests MUST pass unchanged.** The logging format (JSON) is already used by services.

If tests fail after this change:
1. Check if log output is interfering with assertions
2. Check if the admin router conflicts with existing routes
3. This would be a production bug - fix the production code

### New E2E Tests Needed

**Optional:** Add integration test for `/admin/logging` endpoint if time permits.

This is primarily validated by unit tests since it's shared infrastructure.

### If Existing Tests Fail

```
Test Failed
    │
    ▼
Is failure related to logging changes?
    │
    ├── YES (output format, route conflict) ──► Fix production code
    │
    └── NO (unrelated failure) ──► Investigate per Mental Model
```

---

## References

- [ADR-009: Logging Standards](../architecture/adr/ADR-009-logging-standards-runtime-configuration.md)
- [Structlog Documentation](https://www.structlog.org/)
- [OpenTelemetry Python Logging](https://opentelemetry.io/docs/instrumentation/python/)
