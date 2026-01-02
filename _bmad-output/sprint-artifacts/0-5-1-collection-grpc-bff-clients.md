# Story 0.5.1: Collection Model gRPC Layer & BFF Clients

**Status:** ready-for-dev
**GitHub Issue:** #65
**Story Points:** 5

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **BFF developer**,
I want Collection Model to expose gRPC services and BFF to have DAPR clients for all domain models,
So that the BFF can aggregate data from Plantation and Collection models.

## Acceptance Criteria

### AC1: Collection Model gRPC Service Definition
**Given** Collection Model exists with REST/MCP only
**When** I add gRPC service layer
**Then** `CollectionService` is defined in `proto/collection/v1/collection.proto`
**And** Service implements: `GetQualityEvent`, `ListQualityEvents`, `GetDelivery`, `ListDeliveries`
**And** Aggregation methods: `GetFarmerQualitySummary`, `GetFactoryDailySummary`
**And** gRPC server runs on port 50051 alongside existing FastAPI health endpoints
**And** Unit tests cover all gRPC handlers

### AC2: BFF PlantationClient Implementation
**Given** BFF needs to call Plantation Model
**When** I implement `PlantationClient`
**Then** Client calls `plantation-model` via DAPR service invocation
**And** Methods include: `get_farmer`, `list_farmers`, `get_factory`
**And** Pattern follows ADR-002 §"Service Invocation Pattern" (lines 449-502)
**And** Retry logic implemented per ADR-005 (tenacity, exponential backoff)

### AC3: BFF CollectionClient Implementation
**Given** BFF needs to call Collection Model
**When** I implement `CollectionClient`
**Then** Client calls `collection-model` via DAPR service invocation
**And** Methods include: `get_quality_event`, `list_quality_events`, `get_farmer_quality_summary`
**And** Pattern matches `PlantationClient` implementation
**And** Retry logic implemented per ADR-005

### AC4: E2E Verification
**Given** the gRPC clients are implemented
**When** I run the E2E test suite
**Then** BFF clients successfully call Plantation and Collection via DAPR sidecar
**And** Proto messages are correctly serialized/deserialized

## Tasks / Subtasks

- [ ] **Task 1: Proto Definition** (AC: #1)
  - [ ] Create `proto/collection/v1/collection_service.proto` with CollectionService
  - [ ] Define request/response messages for all 6 RPC methods
  - [ ] Generate Python stubs via `scripts/generate_proto.sh`
  - [ ] Update `libs/fp-proto` package

- [ ] **Task 2: Collection Model gRPC Server** (AC: #1)
  - [ ] Create `services/collection-model/src/collection_model/api/grpc_service.py`
  - [ ] Implement all 6 gRPC handler methods
  - [ ] Wire gRPC server to existing service startup (port 50051)
  - [ ] Ensure FastAPI health endpoints continue on port 8000 (ADR-011)

- [ ] **Task 3: BFF Base Client** (AC: #2, #3)
  - [ ] Create `services/bff/src/bff/infrastructure/clients/base.py`
  - [ ] Implement DAPR gRPC invocation pattern with `dapr-app-id` metadata
  - [ ] Add retry decorator (tenacity) per ADR-005

- [ ] **Task 4: PlantationClient** (AC: #2)
  - [ ] Create `services/bff/src/bff/infrastructure/clients/plantation_client.py`
  - [ ] Implement `get_farmer()`, `list_farmers()`, `get_factory()` methods
  - [ ] Unit tests with mocked DAPR channel

- [ ] **Task 5: CollectionClient** (AC: #3)
  - [ ] Create `services/bff/src/bff/infrastructure/clients/collection_client.py`
  - [ ] Implement `get_quality_event()`, `list_quality_events()`, `get_farmer_quality_summary()`
  - [ ] Unit tests with mocked DAPR channel

- [ ] **Task 6: Unit Tests** (AC: #1, #2, #3)
  - [ ] `tests/unit/collection_model/test_grpc_service.py`
  - [ ] `tests/unit/bff/test_plantation_client.py`
  - [ ] `tests/unit/bff/test_collection_client.py`

- [ ] **Task 7: E2E Infrastructure Update** (AC: #4)
  - [ ] Update `tests/e2e/infrastructure/docker-compose.e2e.yaml` with BFF service stub
  - [ ] Add BFF DAPR sidecar configuration
  - [ ] Create basic E2E test for client connectivity

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.5.1: Collection gRPC + BFF Clients"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-5-1-collection-grpc-bff-clients
  ```

**Branch name:** `story/0-5-1-collection-grpc-bff-clients`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/0-5-1-collection-grpc-bff-clients`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.5.1: Collection gRPC + BFF Clients" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/0-5-1-collection-grpc-bff-clients`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
pytest tests/unit/collection_model/test_grpc_service.py tests/unit/bff/ -v
```
**Output:**
```
(paste test summary here - e.g., "42 passed in 5.23s")
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure (--build is MANDATORY)
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build

# Wait for services, then run tests
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v

# Tear down
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
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
git push origin story/0-5-1-collection-grpc-bff-clients

# Wait ~30s, then check CI status
gh run list --branch story/0-5-1-collection-grpc-bff-clients --limit 3
```
**CI Run ID:** _______________
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### Architecture Compliance

**Two-Port Service Architecture (ADR-011):**
Collection Model must expose exactly TWO ports:
| Port | Purpose |
|------|---------|
| **8000** | FastAPI health endpoints (`/health`, `/ready`) - direct, no DAPR |
| **50051** | gRPC API server - domain operations via DAPR sidecar |

**DAPR gRPC Service Invocation (CRITICAL):**
Use native gRPC with `dapr-app-id` metadata header, NOT `DaprClient().invoke_method()`:

```python
# CORRECT: Native gRPC stub with dapr-app-id metadata
import grpc
from fp_proto.collection.v1 import collection_pb2_grpc

async with grpc.aio.insecure_channel("localhost:50001") as channel:  # DAPR sidecar port
    stub = collection_pb2_grpc.CollectionServiceStub(channel)
    metadata = [("dapr-app-id", "collection-model")]  # Target service app-id
    response = await stub.GetQualityEvent(request, metadata=metadata)
```

**Reference:**
- ADR-002 §"Backend Service gRPC Requirements" (lines 514-559)
- ADR-005 §"gRPC Client Retry Strategy"
- ADR-011 §"gRPC/FastAPI/DAPR Service Architecture"

### Proto Definition (CollectionService)

```protobuf
// proto/collection/v1/collection_service.proto
syntax = "proto3";

package farmer_power.collection.v1;

import "collection/v1/collection.proto";

service CollectionService {
  // Quality event queries
  rpc GetQualityEvent(GetQualityEventRequest) returns (QualityEvent);
  rpc ListQualityEvents(ListQualityEventsRequest) returns (ListQualityEventsResponse);

  // Delivery queries
  rpc GetDelivery(GetDeliveryRequest) returns (Delivery);
  rpc ListDeliveries(ListDeliveriesRequest) returns (ListDeliveriesResponse);

  // Aggregations for dashboard
  rpc GetFarmerQualitySummary(GetFarmerQualitySummaryRequest) returns (FarmerQualitySummary);
  rpc GetFactoryDailySummary(GetFactoryDailySummaryRequest) returns (FactoryDailySummary);
}
```

### gRPC Client Retry Requirements (ADR-005)

| Requirement | Details |
|-------------|---------|
| Retry decorator | Tenacity with 3-5 attempts, exponential backoff 1-10s |
| Channel pattern | Singleton (lazy init), NOT per-request |
| Keepalive | 10-30s interval, 5-10s timeout |
| **Reset on error** | Set `_channel = None` and `_stub = None` to force reconnection |

**Reference Pattern:** `mcp-servers/plantation-mcp/src/plantation_mcp/infrastructure/plantation_client.py`

### Directory Structure

**Collection Model gRPC Addition:**
```
services/collection-model/
├── src/collection_model/
│   ├── api/
│   │   ├── grpc_service.py     # NEW: gRPC handlers
│   │   └── health.py           # Existing FastAPI health
│   └── main.py                 # Update: add gRPC server startup
```

**BFF Client Structure:**
```
services/bff/
├── src/bff/
│   └── infrastructure/
│       └── clients/
│           ├── __init__.py
│           ├── base.py              # NEW: Base DAPR gRPC client
│           ├── plantation_client.py # NEW: Plantation Model client
│           └── collection_client.py # NEW: Collection Model client
```

### Testing Standards

- Unit tests in `tests/unit/{model_name}/`
- Mock DAPR channel using `grpcio-testing` or unittest.mock
- DO NOT override `mock_mongodb_client` fixture - use from `tests/conftest.py`
- E2E tests verify actual DAPR service invocation

### Project Context Reference

**Critical Rules to Follow:**
- ALL I/O operations MUST be async
- ALL inter-service communication via DAPR
- Use Pydantic 2.0 syntax (`model_dump()` not `dict()`)
- Type hints on ALL function signatures

**Full Details:** `_bmad-output/project-context.md`

### Dependencies

**This story requires:**
- Plantation Model gRPC service (already implemented)
- Collection Model existing codebase

**This story blocks:**
- Story 0.5.2: BFF Service Setup

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

**Created:**
- `proto/collection/v1/collection_service.proto`
- `services/collection-model/src/collection_model/api/grpc_service.py`
- `services/bff/src/bff/infrastructure/clients/base.py`
- `services/bff/src/bff/infrastructure/clients/plantation_client.py`
- `services/bff/src/bff/infrastructure/clients/collection_client.py`
- `tests/unit/collection_model/test_grpc_service.py`
- `tests/unit/bff/test_plantation_client.py`
- `tests/unit/bff/test_collection_client.py`

**Modified:**
- `services/collection-model/src/collection_model/main.py` (add gRPC server startup)
- `libs/fp-proto/` (regenerate proto stubs)
- `tests/e2e/infrastructure/docker-compose.e2e.yaml` (add BFF service stub)
