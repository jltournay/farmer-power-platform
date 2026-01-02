# Story 0.5.1b: BFF PlantationClient - Read Operations

**Status:** done
**GitHub Issue:** #67
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

- [x] **Task 1: BFF Base Client** (AC: #1)
  - [x] Create `services/bff/src/bff/infrastructure/clients/base.py`
  - [x] Implement DAPR gRPC invocation pattern with `dapr-app-id` metadata
  - [x] Add retry decorator (tenacity) per ADR-005
  - [x] Singleton channel with reset on error

- [x] **Task 2: PlantationClient Read Methods** (AC: #2)
  - [x] Create `services/bff/src/bff/infrastructure/clients/plantation_client.py`
  - [x] Implement 13 read methods grouped by domain
  - [x] Use fp-common domain models for return types

- [x] **Task 3: Unit Tests** (AC: #3)
  - [x] `tests/unit/bff/test_plantation_client.py`
  - [x] Mock DAPR channel, test all read operations
  - [x] Test retry logic and error handling

## Git Workflow (MANDATORY)

**Branch name:** `story/0-5-1b-bff-plantation-client-read`

### Story Start
- [x] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-5-1b-bff-plantation-client-read
  ```

### Story Done
- [x] Create Pull Request
- [x] CI passes on PR
- [x] Code review completed
- [ ] PR merged

**PR URL:** https://github.com/jltournay/farmer-power-platform/pull/68

---

## Local Test Run Evidence (MANDATORY)

### 1. Unit Tests
```bash
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src:libs/fp-common:services/bff/src" pytest tests/unit/bff/ -v
```
**Output:**
```
collected 28 items
tests/unit/bff/test_plantation_client.py::TestPlantationClientInit::test_default_init PASSED
tests/unit/bff/test_plantation_client.py::TestPlantationClientInit::test_direct_host_init PASSED
tests/unit/bff/test_plantation_client.py::TestPlantationClientInit::test_custom_dapr_port PASSED
tests/unit/bff/test_plantation_client.py::TestPlantationClientMetadata::test_metadata_with_dapr PASSED
tests/unit/bff/test_plantation_client.py::TestPlantationClientMetadata::test_metadata_direct_connection PASSED
tests/unit/bff/test_plantation_client.py::TestFarmerOperations::test_get_farmer_success PASSED
tests/unit/bff/test_plantation_client.py::TestFarmerOperations::test_get_farmer_not_found PASSED
tests/unit/bff/test_plantation_client.py::TestFarmerOperations::test_get_farmer_by_phone_success PASSED
tests/unit/bff/test_plantation_client.py::TestFarmerOperations::test_list_farmers_success PASSED
tests/unit/bff/test_plantation_client.py::TestFarmerOperations::test_list_farmers_with_pagination PASSED
tests/unit/bff/test_plantation_client.py::TestFarmerOperations::test_get_farmer_summary_success PASSED
tests/unit/bff/test_plantation_client.py::TestFactoryOperations::test_get_factory_success PASSED
tests/unit/bff/test_plantation_client.py::TestFactoryOperations::test_get_factory_not_found PASSED
tests/unit/bff/test_plantation_client.py::TestFactoryOperations::test_list_factories_success PASSED
tests/unit/bff/test_plantation_client.py::TestCollectionPointOperations::test_get_collection_point_success PASSED
tests/unit/bff/test_plantation_client.py::TestCollectionPointOperations::test_list_collection_points_success PASSED
tests/unit/bff/test_plantation_client.py::TestRegionOperations::test_get_region_success PASSED
tests/unit/bff/test_plantation_client.py::TestRegionOperations::test_list_regions_success PASSED
tests/unit/bff/test_plantation_client.py::TestRegionOperations::test_get_region_weather_success PASSED
tests/unit/bff/test_plantation_client.py::TestRegionOperations::test_get_current_flush_success PASSED
tests/unit/bff/test_plantation_client.py::TestPerformanceOperations::test_get_performance_summary_success PASSED
tests/unit/bff/test_plantation_client.py::TestErrorHandling::test_service_unavailable_error PASSED
tests/unit/bff/test_plantation_client.py::TestErrorHandling::test_channel_reset_on_unavailable PASSED
tests/unit/bff/test_plantation_client.py::TestErrorHandling::test_unknown_grpc_error_propagated PASSED
tests/unit/bff/test_plantation_client.py::TestProtoConversion::test_farmer_enum_conversion PASSED
tests/unit/bff/test_plantation_client.py::TestProtoConversion::test_factory_default_quality_thresholds PASSED
tests/unit/bff/test_plantation_client.py::TestClientClose::test_close_cleans_up_channel PASSED
tests/unit/bff/test_plantation_client.py::TestClientClose::test_close_without_channel PASSED

======================== 28 passed in 4.26s ========================
```

### 2. Lint Check
```bash
ruff check services/bff/ tests/unit/bff/ && ruff format --check services/bff/ tests/unit/bff/
```
**Lint passed:** [x] Yes / [ ] No

### 3. E2E Tests (Local - Step 7b)
```bash
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```
**Output:**
```
============================= test session starts ==============================
platform darwin -- Python 3.11.12, pytest-9.0.2, pluggy-1.6.0
plugins: anyio-4.12.0, asyncio-1.3.0, langsmith-0.5.1
asyncio: mode=Mode.AUTO

tests/e2e/scenarios/test_00_infrastructure_verification.py 22 passed
tests/e2e/scenarios/test_01_plantation_mcp_contracts.py 13 passed
tests/e2e/scenarios/test_02_collection_mcp_contracts.py 12 passed
tests/e2e/scenarios/test_03_factory_farmer_flow.py 5 passed
tests/e2e/scenarios/test_04_quality_blob_ingestion.py 6 passed
tests/e2e/scenarios/test_05_weather_ingestion.py 6 passed
tests/e2e/scenarios/test_06_cross_model_events.py 5 passed
tests/e2e/scenarios/test_07_grading_validation.py 6 passed
tests/e2e/scenarios/test_08_zip_ingestion.py 10 passed (1 skipped)

================== 85 passed, 1 skipped in 123.49s (0:02:03) ===================
```
**E2E passed:** [x] Yes / [ ] No

### 4. E2E Tests (CI - Step 9c)
```bash
gh workflow run "E2E Tests" --ref story/0-5-1b-bff-plantation-client-read
gh run watch <run-id>
```
**Run ID:** 20663146283
**Result:** PASSED (85 passed, 1 skipped)

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
Claude Opus 4.5 (claude-opus-4-5-20251101)

### File List

**Created:**
- `services/bff/pyproject.toml`
- `services/bff/src/bff/infrastructure/__init__.py`
- `services/bff/src/bff/infrastructure/clients/__init__.py`
- `services/bff/src/bff/infrastructure/clients/base.py`
- `services/bff/src/bff/infrastructure/clients/plantation_client.py`
- `tests/unit/bff/__init__.py`
- `tests/unit/bff/conftest.py`
- `tests/unit/bff/test_plantation_client.py`

**Modified:**
- `.github/workflows/ci.yaml` - Added `services/bff/src` to PYTHONPATH
- `_bmad-output/sprint-artifacts/sprint-status.yaml`
- `_bmad-output/sprint-artifacts/0-5-1b-bff-plantation-client-read.md`

---

## Code Review Record

### Review Outcome: ✅ APPROVED (after fixes)

**Reviewer:** Claude Opus 4.5 (adversarial code review workflow)
**Date:** 2026-01-02

### Issues Found and Fixed

| ID | Severity | Issue | Resolution |
|----|----------|-------|------------|
| H1 | HIGH | `get_performance_summary` returned `dict` instead of typed model, violating AC2 | ✅ Created `PerformanceSummary` model in fp-common, updated return type |
| M1 | MEDIUM | CI PYTHONPATH missing `services/bff/src` in integration-tests job | ✅ Added to integration-tests PYTHONPATH |
| M2 | MEDIUM | Story File List missing `.github/workflows/ci.yaml` | ✅ Updated File List |
| M3 | MEDIUM | Missing test for `period_start` parameter | ✅ Added `test_get_performance_summary_with_period_start` test |

### Files Changed During Review

**Created:**
- `libs/fp-common/fp_common/models/performance_summary.py` - PerformanceSummary typed model

**Modified:**
- `libs/fp-common/fp_common/models/__init__.py` - Export PerformanceSummary
- `services/bff/src/bff/infrastructure/clients/plantation_client.py` - Use typed return
- `tests/unit/bff/test_plantation_client.py` - Updated test + added period_start test
- `.github/workflows/ci.yaml` - Fixed integration-tests PYTHONPATH

### Test Verification After Fixes
```
29 passed in 4.18s
```
