# Story 0.5.1c: BFF PlantationClient - Write Operations

**Status:** review
**GitHub Issue:** #69
**Story Points:** 2

<!-- Note: This is part 3 of 4 from the original Story 0.5.1 split -->

## Story

As a **BFF developer**,
I want PlantationClient write operations,
So that the BFF can create, update, and delete entities in Plantation Model for admin operations.

## Acceptance Criteria

### AC1: PlantationClient Write Methods
**Given** PlantationClient read operations exist (Story 0.5.1b)
**When** I add write methods
**Then** Client implements 11 write methods across 5 domains:

  **Farmer operations (2 write methods):**
  - `create_farmer(...)` - Register new farmer
  - `update_farmer(farmer_id, ...)` - Update farmer details

  **Factory operations (3 write methods):**
  - `create_factory(...)` - Create new factory
  - `update_factory(factory_id, ...)` - Update factory config
  - `delete_factory(factory_id)` - Deactivate factory

  **Collection Point operations (3 write methods):**
  - `create_collection_point(...)` - Create new collection point
  - `update_collection_point(id, ...)` - Update collection point
  - `delete_collection_point(id)` - Deactivate collection point

  **Region operations (2 write methods):**
  - `create_region(...)` - Create new region
  - `update_region(region_id, ...)` - Update region config

  **Communication preferences (1 write method):**
  - `update_communication_preferences(farmer_id, ...)` - Update farmer prefs

**And** All methods accept typed domain models or Pydantic models (NOT dict[str, Any])
**And** All methods return typed response models
**And** Pattern matches read operations from Story 0.5.1b

### AC2: Unit Tests
**Given** PlantationClient write methods are implemented
**When** I run unit tests
**Then** All 11 write methods have test coverage
**And** Create, update, delete flows are tested
**And** Error handling for validation errors is tested

## Tasks / Subtasks

- [x] **Task 1: Farmer Write Methods** (AC: #1)
  - [x] Implement `create_farmer()` with typed FarmerCreate (from fp_common.models)
  - [x] Implement `update_farmer()` with typed FarmerUpdate (from fp_common.models)

- [x] **Task 2: Factory Write Methods** (AC: #1)
  - [x] Implement `create_factory()` with FactoryCreate
  - [x] Implement `update_factory()` with FactoryUpdate
  - [x] Implement `delete_factory()` returns bool

- [x] **Task 3: Collection Point Write Methods** (AC: #1)
  - [x] Implement `create_collection_point()` with CollectionPointCreate
  - [x] Implement `update_collection_point()` with CollectionPointUpdate
  - [x] Implement `delete_collection_point()` returns bool

- [x] **Task 4: Region & Communication Write Methods** (AC: #1)
  - [x] Implement `create_region()` with RegionCreate
  - [x] Implement `update_region()` with RegionUpdate
  - [x] Implement `update_communication_preferences()` accepts individual params

- [x] **Task 5: Unit Tests** (AC: #2)
  - [x] Added 21 write operation tests to `tests/unit/bff/test_plantation_client.py` (17 + 4 code review fixes)
  - [x] Test all 11 write operations
  - [x] Test validation error handling (NotFoundError for updates/deletes, INVALID_ARGUMENT for creates)

## Git Workflow (MANDATORY)

**Branch name:** `story/0-5-1c-bff-plantation-client-write`

### Story Start
- [x] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-5-1c-bff-plantation-client-write
  ```

### Story Done
- [x] Create Pull Request
- [x] CI passes on PR
- [x] Code review completed
- [ ] PR merged

**PR URL:** https://github.com/jltournay/farmer-power-platform/pull/70

---

## Local Test Run Evidence (MANDATORY)

### 1. Unit Tests
```bash
PYTHONPATH="${PYTHONPATH}:services/bff/src:libs/fp-common:libs/fp-proto/src:tests" pytest tests/unit/bff/test_plantation_client.py -v
```
**Output:**
```
============================= test session starts ==============================
platform darwin -- Python 3.11.12, pytest-9.0.2
plugins: anyio-4.12.0, asyncio-1.3.0, langsmith-0.5.1
asyncio: mode=Mode.AUTO
collected 46 items

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
tests/unit/bff/test_plantation_client.py::TestPerformanceOperations::test_get_performance_summary_with_period_start PASSED
tests/unit/bff/test_plantation_client.py::TestErrorHandling::test_service_unavailable_error PASSED
tests/unit/bff/test_plantation_client.py::TestErrorHandling::test_channel_reset_on_unavailable PASSED
tests/unit/bff/test_plantation_client.py::TestErrorHandling::test_unknown_grpc_error_propagated PASSED
tests/unit/bff/test_plantation_client.py::TestProtoConversion::test_farmer_enum_conversion PASSED
tests/unit/bff/test_plantation_client.py::TestProtoConversion::test_factory_default_quality_thresholds PASSED
tests/unit/bff/test_plantation_client.py::TestClientClose::test_close_cleans_up_channel PASSED
tests/unit/bff/test_plantation_client.py::TestClientClose::test_close_without_channel PASSED
tests/unit/bff/test_plantation_client.py::TestFarmerWriteOperations::test_create_farmer_success PASSED
tests/unit/bff/test_plantation_client.py::TestFarmerWriteOperations::test_update_farmer_success PASSED
tests/unit/bff/test_plantation_client.py::TestFarmerWriteOperations::test_update_farmer_not_found PASSED
tests/unit/bff/test_plantation_client.py::TestFactoryWriteOperations::test_create_factory_success PASSED
tests/unit/bff/test_plantation_client.py::TestFactoryWriteOperations::test_update_factory_success PASSED
tests/unit/bff/test_plantation_client.py::TestFactoryWriteOperations::test_delete_factory_success PASSED
tests/unit/bff/test_plantation_client.py::TestFactoryWriteOperations::test_delete_factory_not_found PASSED
tests/unit/bff/test_plantation_client.py::TestCollectionPointWriteOperations::test_create_collection_point_success PASSED
tests/unit/bff/test_plantation_client.py::TestCollectionPointWriteOperations::test_create_collection_point_with_capacity PASSED
tests/unit/bff/test_plantation_client.py::TestCollectionPointWriteOperations::test_update_collection_point_success PASSED
tests/unit/bff/test_plantation_client.py::TestCollectionPointWriteOperations::test_delete_collection_point_success PASSED
tests/unit/bff/test_plantation_client.py::TestRegionWriteOperations::test_create_region_success PASSED
tests/unit/bff/test_plantation_client.py::TestRegionWriteOperations::test_update_region_success PASSED
tests/unit/bff/test_plantation_client.py::TestRegionWriteOperations::test_update_region_not_found PASSED
tests/unit/bff/test_plantation_client.py::TestCommunicationPreferencesWriteOperations::test_update_communication_preferences_success PASSED
tests/unit/bff/test_plantation_client.py::TestCommunicationPreferencesWriteOperations::test_update_communication_preferences_partial PASSED
tests/unit/bff/test_plantation_client.py::TestCommunicationPreferencesWriteOperations::test_update_communication_preferences_not_found PASSED

======================== 46 passed in 4.96s =========================
```

### 2. Lint Check
```bash
ruff check . && ruff format --check .
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
================== 85 passed, 1 skipped in 126.05s (0:02:06) ===================
```

### 4. CI Run (Step 9b)
**CI Run ID:** 20665516999
**Result:** ✅ All jobs passed (Lint, Unit Tests, Integration Tests)

### 5. E2E CI (Step 9c)
**E2E Run ID:** 20665555139
**Result:** ✅ 85 passed, 1 skipped

---

## Dev Notes

### Type Safety Requirements (CRITICAL)

**DO NOT use `dict[str, Any]`** - Use typed request/response models:

```python
# WRONG
async def create_farmer(data: dict[str, Any]) -> dict[str, Any]: ...

# CORRECT
from fp_common.domain.plantation import Farmer, CreateFarmerRequest

async def create_farmer(request: CreateFarmerRequest) -> Farmer: ...
```

### Request Models Pattern

Define typed request models for write operations:

```python
from pydantic import BaseModel
from fp_common.domain.plantation import GeoLocation, ContactInfo

class CreateFarmerRequest(BaseModel):
    first_name: str
    last_name: str
    collection_point_id: str
    farm_location: GeoLocation
    contact: ContactInfo
    farm_size_hectares: float
    national_id: str
    grower_number: str | None = None
```

### Dependencies

**This story requires:**
- Story 0.5.1b complete (PlantationClient with read methods)

**This story blocks:**
- Story 0.5.4: BFF API Routes

---

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)

### File List

**Modified:**
- `services/bff/src/bff/infrastructure/clients/plantation_client.py` (added 11 write methods + 5 converter methods)
- `tests/unit/bff/test_plantation_client.py` (added 17 write operation tests + 4 code review fixes)

---

## Code Review Record

### Review Outcome: APPROVE (after fixes)

### Findings Summary

| Severity | Category | Finding | Resolution |
|----------|----------|---------|------------|
| HIGH | Test Gap | Missing test for `is_active` field in update_farmer | Added `test_update_farmer_deactivate` |
| MEDIUM | Test Gap | No error test for create_farmer validation | Added `test_create_farmer_validation_error` |
| MEDIUM | Test Gap | No error test for create_collection_point | Added `test_create_collection_point_factory_not_found` |
| MEDIUM | Test Gap | No error test for create_region validation | Added `test_create_region_validation_error` |
| LOW | Documentation | Docstrings could mention exception types | Noted for future improvement |
| LOW | Style | Converters could be @staticmethod | Noted, current approach works |

### Tests Added (Code Review Fixes)

1. **test_update_farmer_deactivate** - Tests setting `is_active=False` in update_farmer
2. **test_create_farmer_validation_error** - Tests INVALID_ARGUMENT error handling for create_farmer
3. **test_create_collection_point_factory_not_found** - Tests NOT_FOUND error when factory doesn't exist
4. **test_create_region_validation_error** - Tests INVALID_ARGUMENT error for duplicate region name

### Post-Review Test Results
```
======================== 50 passed in 10.66s ========================
```

### Review Commit
`fdbf4f4` - test: Add code review fixes for PlantationClient write tests
