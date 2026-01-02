# Story 0.5.2: BFF Service Setup

**Status:** in-progress
**GitHub Issue:** #73
**Story Points:** 3

## Story

As a **platform operator**,
I want a BFF (Backend for Frontend) service deployed with DAPR sidecar,
So that frontend applications have an optimized API layer.

## Acceptance Criteria

### AC1: FastAPI Application Scaffold
**Given** the services folder structure exists (with infrastructure/clients/ from Story 0.5.1)
**When** I complete the BFF service scaffold
**Then** FastAPI application is created following project conventions
**And** Directory structure matches ADR-002 §"BFF Internal Code Structure" (lines 780-933)
**And** `pyproject.toml` includes dependencies: fastapi, uvicorn, dapr, fp-proto, fp-common

### AC2: Health Endpoints
**Given** the BFF service is created
**When** I start the service
**Then** FastAPI serves on port 8080
**And** Health endpoint `/health` returns 200
**And** Readiness endpoint `/ready` returns 200
**And** OpenTelemetry tracing is configured via fp-common

### AC3: DAPR Configuration
**Given** DAPR configuration is needed
**When** I create `services/bff/dapr/`
**Then** `config.yaml` configures tracing to OTel collector
**And** `resiliency.yaml` defines circuit breaker and retry policies
**And** Configuration matches ADR-002 §"Resiliency Configuration" (lines 735-776)

### AC4: E2E Infrastructure Update
**Given** E2E infrastructure needs updating
**When** I update `docker-compose.e2e.yaml`
**Then** BFF service is added with DAPR sidecar
**And** BFF can invoke `plantation-model` and `collection-model` via DAPR
**And** Configuration matches ADR-002 §"Docker Compose Configuration" (lines 654-729)

### AC5: Unit Tests
**Given** BFF service is scaffolded
**When** I run unit tests
**Then** Health endpoints have test coverage
**And** Config loading is tested
**And** Application startup/shutdown is tested

## Tasks / Subtasks

- [x] **Task 1: FastAPI Application Core** (AC: #1, #2)
  - [x] Create `services/bff/src/bff/main.py` - FastAPI app with lifespan handler
  - [x] Create `services/bff/src/bff/config.py` - Environment configuration
  - [x] Create `services/bff/src/bff/api/__init__.py`
  - [x] Create `services/bff/src/bff/api/routes/__init__.py`
  - [x] Create `services/bff/src/bff/api/routes/health.py` - `/health`, `/ready` endpoints
  - [x] Create `services/bff/src/bff/infrastructure/tracing.py` - OpenTelemetry setup
  - [x] Update `services/bff/pyproject.toml` - Add FastAPI dependencies

- [x] **Task 2: DAPR Configuration** (AC: #3)
  - [x] Create `services/bff/dapr/config.yaml` - Tracing to OTel
  - [x] Create `services/bff/dapr/resiliency.yaml` - Circuit breaker, retry

- [x] **Task 3: Dockerfile** (AC: #4)
  - [x] Create `services/bff/Dockerfile` - Python 3.12, uvicorn

- [x] **Task 4: E2E Infrastructure Update** (AC: #4)
  - [x] Update `tests/e2e/infrastructure/docker-compose.e2e.yaml` - Add BFF + DAPR sidecar
  - [x] Verify BFF can reach plantation-model and collection-model via DAPR

- [x] **Task 5: Unit Tests** (AC: #5)
  - [x] Create `tests/unit/bff/test_health.py` - Health endpoint tests
  - [x] Create `tests/unit/bff/test_config.py` - Configuration loading tests
  - [x] Create `tests/unit/bff/test_main.py` - App startup tests

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [x] GitHub Issue exists or created: `gh issue create --title "Story 0.5.2: BFF Service Setup"`
- [x] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-5-2-bff-service-setup
  ```

**Branch name:** `story/0-5-2-bff-service-setup`

### During Development
- [x] All commits reference GitHub issue: `Relates to #73`
- [x] Commits are atomic by type (production, test, seed - not mixed)
- [x] Push to feature branch: `git push -u origin story/0-5-2-bff-service-setup`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.5.2: BFF Service Setup" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/0-5-2-bff-service-setup`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src:libs/fp-common:services/bff/src" pytest tests/unit/bff/ -v
```
**Output:**
```
92 passed, 9 warnings in 14.21s
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure (MUST use --build to rebuild images)
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build

# Wait for services, then run tests
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v

# Tear down
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```
**Output:**
```
85 passed, 1 skipped in 119.90s (0:01:59)
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
git push origin story/0-5-2-bff-service-setup

# Wait ~30s, then check CI status
gh run list --branch story/0-5-2-bff-service-setup --limit 3
```
**CI Run ID:** _______________
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### Previous Story Intelligence (CRITICAL)

**From Story 0.5.1a-d, the following was established:**

1. **PlantationClient Pattern** (`services/bff/src/bff/infrastructure/clients/plantation_client.py`)
   - Uses native gRPC with `dapr-app-id` metadata (NOT DaprClient.invoke_method)
   - Singleton channel pattern with lazy initialization
   - Retry via tenacity (3 attempts, exponential backoff 1-10s)
   - Channel reset on UNAVAILABLE errors
   - Returns typed Pydantic models from fp-common

2. **CollectionClient Pattern** (`services/bff/src/bff/infrastructure/clients/collection_client.py`)
   - Same pattern as PlantationClient
   - 4 document query methods

3. **Code Review Findings Applied:**
   - Always cap `page_size` with `min(page_size, 100)`
   - Use `datetime.now(UTC)` not `datetime.now()` (timezone-aware)
   - Remove unused imports
   - Remove unused fixtures from conftest.py

### Architecture Requirements (ADR-002)

**BFF Service Characteristics:**
- Exposes HTTP REST only (port 8080)
- No database (stateless)
- Consumes events (optional SSE)
- Transforms/aggregates data from backend services
- Called by browser (React frontend)

**Directory Structure (ADR-002 §780-933):**
```
services/bff/
├── src/bff/
│   ├── __init__.py
│   ├── main.py                      # FastAPI app entrypoint
│   ├── config.py                    # Environment configuration
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   └── health.py            # /health, /ready
│   │   ├── middleware/              # (Story 0.5.3)
│   │   └── schemas/                 # (Story 0.5.4)
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── clients/                 # Already exists from 0.5.1
│   │   │   ├── base.py
│   │   │   ├── plantation_client.py
│   │   │   └── collection_client.py
│   │   └── tracing.py               # OpenTelemetry setup
│   ├── services/                    # (Story 0.5.4)
│   └── transformers/                # (Story 0.5.4)
├── dapr/
│   ├── config.yaml
│   └── resiliency.yaml
├── Dockerfile
└── pyproject.toml                   # Already exists, needs updates
```

### DAPR Configuration (ADR-002 §735-776)

**config.yaml:**
```yaml
apiVersion: dapr.io/v1alpha1
kind: Configuration
metadata:
  name: bff-config
spec:
  tracing:
    samplingRate: "1"
    otel:
      endpointAddress: "otel-collector:4317"
      isSecure: false
      protocol: grpc
  metric:
    enabled: true
```

**resiliency.yaml:**
```yaml
apiVersion: dapr.io/v1alpha1
kind: Resiliency
metadata:
  name: bff-resiliency
spec:
  policies:
    timeouts:
      general: 5s
      slow-service: 10s
    retries:
      standard:
        policy: exponential
        maxInterval: 10s
        maxRetries: 3
    circuitBreakers:
      simpleCB:
        maxRequests: 1
        interval: 30s
        timeout: 60s
        trip: consecutiveFailures >= 5
  targets:
    apps:
      plantation-model:
        timeout: general
        retry: standard
        circuitBreaker: simpleCB
      collection-model:
        timeout: general
        retry: standard
        circuitBreaker: simpleCB
```

### Docker Compose Update (ADR-002 §654-729)

Add BFF + DAPR sidecar to E2E infrastructure:

```yaml
# In tests/e2e/infrastructure/docker-compose.e2e.yaml

  # BFF Service
  bff:
    build:
      context: ../../..
      dockerfile: services/bff/Dockerfile
    ports:
      - "8080:8080"
    environment:
      - APP_ENV=test
      - AUTH_PROVIDER=mock
      - MOCK_JWT_SECRET=test-secret-for-e2e
      - DAPR_HTTP_PORT=3500
      - DAPR_GRPC_PORT=50001
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
    depends_on:
      - placement
    networks:
      - farmer-power-e2e

  # BFF DAPR Sidecar
  bff-dapr:
    image: daprio/daprd:1.14
    command:
      - "./daprd"
      - "--app-id=bff"
      - "--app-port=8080"
      - "--dapr-http-port=3500"
      - "--dapr-grpc-port=50001"
      - "--placement-host-address=placement:50006"
      - "--resources-path=/components"
      - "--config=/config/config.yaml"
    volumes:
      - ./dapr-components:/components
      - ../../../services/bff/dapr:/config
    network_mode: "service:bff"
    depends_on:
      - bff
```

### FastAPI App Pattern

**main.py:**
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

from bff.config import settings
from bff.api.routes import health
from bff.infrastructure.tracing import setup_tracing


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_tracing()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="Farmer Power BFF",
    description="Backend for Frontend API gateway",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
```

**config.py:**
```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "development"
    auth_provider: str = "mock"
    mock_jwt_secret: str = "dev-secret"
    dapr_http_port: int = 3500
    dapr_grpc_port: int = 50001
    otel_endpoint: str = "http://localhost:4317"

    class Config:
        env_prefix = ""


settings = Settings()
```

### pyproject.toml Updates

Add these dependencies to existing `pyproject.toml`:

```toml
[project]
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic-settings>=2.6.0",
    "opentelemetry-api>=1.28.0",
    "opentelemetry-sdk>=1.28.0",
    "opentelemetry-exporter-otlp-proto-grpc>=1.28.0",
    "opentelemetry-instrumentation-fastapi>=0.49b0",
]
```

### Dockerfile Pattern

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Copy shared libs first (better caching)
COPY libs/fp-common /app/libs/fp-common
COPY libs/fp-proto /app/libs/fp-proto

# Copy BFF service
COPY services/bff /app/services/bff

# Install dependencies
RUN pip install --no-cache-dir \
    /app/libs/fp-common \
    /app/libs/fp-proto \
    /app/services/bff

EXPOSE 8080

CMD ["uvicorn", "bff.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Dependencies

**This story requires:**
- Story 0.5.1a-d complete (BFF clients exist)
- Plantation Model gRPC service running
- Collection Model gRPC service running

**This story blocks:**
- Story 0.5.3: BFF Auth Middleware
- Story 0.5.4: BFF API Routes

### References

| Document | Location | Relevant Sections |
|----------|----------|-------------------|
| ADR-002 Frontend Architecture | `_bmad-output/architecture/adr/ADR-002-frontend-architecture.md` | §780-933 (BFF structure), §654-729 (Docker), §735-776 (Resiliency) |
| Project Context | `_bmad-output/project-context.md` | Two-Port Architecture, DAPR rules |
| Epic 0.5 | `_bmad-output/epics/epic-0-5-frontend.md` | Story 0.5.2 requirements |

---

## E2E Story Checklist (Additional guidance for E2E-focused stories)

**Read First:** `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

### Pre-Implementation
- [x] Read and understood `E2E-TESTING-MENTAL-MODEL.md`
- [x] Understand: Proto = source of truth, tests verify (not define) behavior

### Before Starting Docker
- [x] Validate seed data: `python tests/e2e/infrastructure/validate_seed_data.py`
- [x] All seed files pass validation

### During Implementation
- [x] If tests fail, investigate using the debugging checklist (not blindly modify code)
- [x] If seed data needs changes, fix seed data (not production code)
- [x] If production code has bugs, document each fix (see below)

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
| docker-compose.e2e.yaml | Added BFF + sidecar | BFF service needed for E2E | New service in stack |

### Before Marking Done
- [x] All tests pass locally with Docker infrastructure
- [x] `ruff check` and `ruff format --check` pass
- [ ] CI pipeline is green (pending push and CI run)
- [x] If production code changed: Change log above is complete (N/A - new service)
- [x] Story file updated with completion notes

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Fixed dependency conflict: BFF pyproject.toml had fastapi ^0.109.0 but fp-common requires ^0.115.0
- Created README.md to satisfy poetry metadata requirement

### Completion Notes List

1. Implemented FastAPI application with lifespan handler and OpenTelemetry tracing
2. Created health (`/health`) and readiness (`/ready`) endpoints
3. Configured DAPR sidecar with tracing and resiliency policies
4. Added BFF service to E2E docker-compose infrastructure
5. All 92 unit tests pass, all 85 E2E tests pass

### File List

**Created:**
- `services/bff/src/bff/main.py` - FastAPI application entrypoint
- `services/bff/src/bff/config.py` - Environment-based settings
- `services/bff/src/bff/api/__init__.py` - API module init
- `services/bff/src/bff/api/routes/__init__.py` - Routes module init
- `services/bff/src/bff/api/routes/health.py` - Health/ready endpoints
- `services/bff/src/bff/infrastructure/tracing.py` - OpenTelemetry setup
- `services/bff/dapr/config.yaml` - DAPR tracing config
- `services/bff/dapr/resiliency.yaml` - DAPR retry/circuit breaker
- `services/bff/Dockerfile` - Container build file
- `services/bff/README.md` - Service documentation
- `tests/unit/bff/test_health.py` - Health endpoint tests
- `tests/unit/bff/test_config.py` - Configuration tests
- `tests/unit/bff/test_main.py` - Application tests

**Modified:**
- `services/bff/pyproject.toml` - Updated fastapi to ^0.115.0, uvicorn to ^0.32.0
- `tests/e2e/infrastructure/docker-compose.e2e.yaml` - Added BFF service + DAPR sidecar
