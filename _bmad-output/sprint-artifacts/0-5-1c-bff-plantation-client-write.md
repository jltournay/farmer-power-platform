# Story 0.5.1c: BFF PlantationClient - Write Operations

**Status:** backlog
**GitHub Issue:** <!-- To be created -->
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

- [ ] **Task 1: Farmer Write Methods** (AC: #1)
  - [ ] Implement `create_farmer()` with typed CreateFarmerRequest
  - [ ] Implement `update_farmer()` with typed UpdateFarmerRequest

- [ ] **Task 2: Factory Write Methods** (AC: #1)
  - [ ] Implement `create_factory()`
  - [ ] Implement `update_factory()`
  - [ ] Implement `delete_factory()`

- [ ] **Task 3: Collection Point Write Methods** (AC: #1)
  - [ ] Implement `create_collection_point()`
  - [ ] Implement `update_collection_point()`
  - [ ] Implement `delete_collection_point()`

- [ ] **Task 4: Region & Communication Write Methods** (AC: #1)
  - [ ] Implement `create_region()`
  - [ ] Implement `update_region()`
  - [ ] Implement `update_communication_preferences()`

- [ ] **Task 5: Unit Tests** (AC: #2)
  - [ ] `tests/unit/bff/test_plantation_client_write.py`
  - [ ] Test all 11 write operations
  - [ ] Test validation error handling

## Git Workflow (MANDATORY)

**Branch name:** `story/0-5-1c-bff-plantation-client-write`

### Story Start
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-5-1c-bff-plantation-client-write
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
pytest tests/unit/bff/test_plantation_client_write.py -v
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
{{agent_model_name_version}}

### File List

**Modified:**
- `services/bff/src/bff/infrastructure/clients/plantation_client.py` (add write methods)

**Created:**
- `tests/unit/bff/test_plantation_client_write.py`
