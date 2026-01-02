# Story 0.5.1b: BFF PlantationClient - Read Operations

**Status:** backlog
**GitHub Issue:** <!-- To be created -->
**Story Points:** 3

<!-- Note: This is part 2 of 4 from the original Story 0.5.1 split -->

## Story

As a **BFF developer**,
I want a PlantationClient with read operations,
So that the BFF can fetch farmer, factory, region, and collection point data for the dashboard.

## Acceptance Criteria

### AC1: BFF Base Client Infrastructure
**Given** BFF needs to call multiple backend services via DAPR
**When** I implement the base gRPC client
**Then** Base client uses native gRPC with `dapr-app-id` metadata header
**And** Singleton channel pattern with lazy initialization
**And** Retry logic via tenacity (3-5 attempts, exponential backoff 1-10s)
**And** Proper channel reset on connection errors

### AC2: PlantationClient Read Methods
**Given** BFF needs to read data from Plantation Model
**When** I implement `PlantationClient`
**Then** Client calls `plantation-model` via DAPR service invocation
**And** Implements 13 read methods across 5 domains:

  **Farmer operations (4 read methods):**
  - `get_farmer(farmer_id)` - Single farmer by ID
  - `get_farmer_by_phone(phone)` - Lookup by phone number
  - `list_farmers(region_id, collection_point_id, page)` - Paginated list
  - `get_farmer_summary(farmer_id)` - Farmer with performance metrics

  **Factory operations (2 read methods):**
  - `get_factory(factory_id)` - Factory details with thresholds
  - `list_factories(region_id, page)` - Factory list

  **Collection Point operations (2 read methods):**
  - `get_collection_point(id)` - Collection point details
  - `list_collection_points(factory_id, region_id)` - For filters

  **Region operations (4 read methods):**
  - `get_region(region_id)` - Region with geography/agronomic data
  - `list_regions(county, altitude_band)` - For filters
  - `get_region_weather(region_id, days)` - Weather history
  - `get_current_flush(region_id)` - Current tea flush period

  **Performance operations (1 read method):**
  - `get_performance_summary(entity_type, entity_id, period)` - Metrics

**And** All methods return typed domain models (NOT dict[str, Any])
**And** Pattern follows ADR-002 §"Service Invocation Pattern"
**And** Retry logic implemented per ADR-005

### AC3: Unit Tests
**Given** PlantationClient read methods are implemented
**When** I run unit tests
**Then** All 13 read methods have test coverage
**And** DAPR channel is mocked properly
**And** Error handling and retry logic is tested

## Tasks / Subtasks

- [ ] **Task 1: BFF Base Client** (AC: #1)
  - [ ] Create `services/bff/src/bff/infrastructure/clients/base.py`
  - [ ] Implement DAPR gRPC invocation pattern with `dapr-app-id` metadata
  - [ ] Add retry decorator (tenacity) per ADR-005
  - [ ] Singleton channel with reset on error

- [ ] **Task 2: PlantationClient Read Methods** (AC: #2)
  - [ ] Create `services/bff/src/bff/infrastructure/clients/plantation_client.py`
  - [ ] Implement 13 read methods grouped by domain
  - [ ] Use fp-common domain models for return types

- [ ] **Task 3: Unit Tests** (AC: #3)
  - [ ] `tests/unit/bff/test_plantation_client_read.py`
  - [ ] Mock DAPR channel, test all read operations
  - [ ] Test retry logic and error handling

## Git Workflow (MANDATORY)

**Branch name:** `story/0-5-1b-bff-plantation-client-read`

### Story Start
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-5-1b-bff-plantation-client-read
  ```

### Story Done
- [ ] Create Pull Request
- [ ] CI passes on PR
- [ ] Code review completed
- [ ] PR merged

**PR URL:** _______________

---

## Local Test Run Evidence (MANDATORY)

### 1. Unit Tests
```bash
pytest tests/unit/bff/test_plantation_client_read.py -v
```
**Output:**
```
(paste test summary here)
```

### 2. Lint Check
```bash
ruff check . && ruff format --check .
```
**Lint passed:** [ ] Yes / [ ] No

---

## Dev Notes

### DAPR gRPC Service Invocation (CRITICAL)

Use native gRPC with `dapr-app-id` metadata header, NOT `DaprClient().invoke_method()`:

```python
# CORRECT: Native gRPC stub with dapr-app-id metadata
import grpc
from fp_proto.plantation.v1 import plantation_pb2, plantation_pb2_grpc

class PlantationClient:
    def __init__(self, dapr_grpc_port: int = 50001):
        self._port = dapr_grpc_port
        self._channel: grpc.aio.Channel | None = None
        self._stub: plantation_pb2_grpc.PlantationServiceStub | None = None

    async def _get_stub(self) -> plantation_pb2_grpc.PlantationServiceStub:
        if self._channel is None:
            self._channel = grpc.aio.insecure_channel(f"localhost:{self._port}")
            self._stub = plantation_pb2_grpc.PlantationServiceStub(self._channel)
        return self._stub

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def get_farmer(self, farmer_id: str) -> Farmer:
        stub = await self._get_stub()
        metadata = [("dapr-app-id", "plantation-model")]
        request = plantation_pb2.GetFarmerRequest(id=farmer_id)
        response = await stub.GetFarmer(request, metadata=metadata)
        return Farmer.from_proto(response)
```

### Type Safety Requirements (CRITICAL)

**DO NOT use `dict[str, Any]`** - Use fp-common domain models:

```python
# WRONG
async def get_farmer(farmer_id: str) -> dict[str, Any]: ...

# CORRECT
from fp_common.domain.plantation import Farmer
async def get_farmer(farmer_id: str) -> Farmer: ...
```

### gRPC Client Retry Requirements (ADR-005)

| Requirement | Details |
|-------------|---------|
| Retry decorator | Tenacity with 3-5 attempts, exponential backoff 1-10s |
| Channel pattern | Singleton (lazy init), NOT per-request |
| Keepalive | 10-30s interval, 5-10s timeout |
| Reset on error | Set `_channel = None` and `_stub = None` to force reconnection |

### Dependencies

**This story requires:**
- Story 0.5.1a complete (proto stubs exist)
- Plantation Model gRPC service running

**This story blocks:**
- Story 0.5.1c: PlantationClient Write Operations
- Story 0.5.4: BFF API Routes

---

## Dev Agent Record

### Agent Model Used
{{agent_model_name_version}}

### File List

**Created:**
- `services/bff/src/bff/infrastructure/clients/__init__.py`
- `services/bff/src/bff/infrastructure/clients/base.py`
- `services/bff/src/bff/infrastructure/clients/plantation_client.py`
- `tests/unit/bff/test_plantation_client_read.py`
