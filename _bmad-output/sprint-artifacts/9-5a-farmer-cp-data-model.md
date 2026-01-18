# Story 9.5a: Farmer-CollectionPoint Data Model Refactor

**Status:** ready-for-dev
**GitHub Issue:** #200

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **platform developer**,
I want to refactor the Farmer-CollectionPoint relationship from N:1 to N:M,
So that a farmer can be correctly associated with multiple collection points across different factories.

## Acceptance Criteria

### AC 9.5a.1: Remove collection_point_id from Farmer

**Given** the current Farmer model has `collection_point_id: str`
**When** this story is complete
**Then**:
- Farmer entity no longer has `collection_point_id` field
- Farmer creation does NOT require a collection point
- Farmer proto message updated to remove the field
- All references to `farmer.collection_point_id` are removed or migrated

### AC 9.5a.2: Add farmer_ids to CollectionPoint

**Given** a CollectionPoint entity
**When** this story is complete
**Then**:
- CollectionPoint has `farmer_ids: list[str] = []` field
- Proto `CollectionPoint` message includes `repeated string farmer_ids`
- Existing CPs initialize with empty farmer_ids list

### AC 9.5a.3: Farmer-CP Assignment Endpoints

**Given** the new N:M relationship
**When** admin needs to assign/unassign farmers
**Then** the following endpoints exist:
- `POST /api/admin/collection-points/{cp_id}/farmers/{farmer_id}` - Assign farmer to CP
- `DELETE /api/admin/collection-points/{cp_id}/farmers/{farmer_id}` - Unassign farmer from CP
- Assignment is idempotent (assigning twice = no-op)
- Unassignment is idempotent (unassigning non-member = no-op)

### AC 9.5a.4: Plantation Model gRPC Methods

**Given** the service layer changes
**When** inter-service communication is needed
**Then**:
- `rpc AssignFarmerToCollectionPoint(AssignFarmerRequest) returns (CollectionPoint)`
- `rpc UnassignFarmerFromCollectionPoint(UnassignFarmerRequest) returns (CollectionPoint)`
- Methods validate farmer_id and cp_id exist before assignment

### AC 9.5a.5: Farmer List Shows Factory Count

**Given** the farmer list API
**When** listing farmers
**Then**:
- Response includes `factory_count: int` instead of `collection_point_id`
- Factory count = distinct factories whose CPs contain this farmer
- List can STILL be filtered by `collection_point_id` query param (semantics: "show farmers assigned to this CP")
- The filter now queries CPs that contain the farmer_id, not farmer.collection_point_id

### AC 9.5a.6: Farmer Detail Shows Collection Points

**Given** a farmer detail view
**When** viewing farmer details
**Then**:
- Response includes `collection_points: list[CollectionPointSummary]`
- Each CP summary includes: id, name, factory_id, factory_name
- Empty list if farmer not assigned to any CPs

### AC 9.5a.7: E2E Tests Updated

**Given** the data model changes
**When** E2E tests run
**Then**:
- Seed data updated to use farmer_ids on CPs
- Existing E2E tests updated to work with new model
- New tests for assignment/unassignment endpoints

---

## Tasks / Subtasks

### Task 1: Proto Definition Updates (AC: 1, 2, 4)

Update protocol buffer definitions for the new data model:

- [ ] 1.1 Modify `proto/plantation/v1/plantation.proto`:
  - [ ] 1.1.1 Remove `string collection_point_id = 6` from `Farmer` message (line 502)
  - [ ] 1.1.2 Remove `string collection_point_id = 4` from `ListFarmersRequest` (line 529)
  - [ ] 1.1.3 Remove `string collection_point_id = 3` from `CreateFarmerRequest` (line 542)
  - [ ] 1.1.4 Remove `string collection_point_id = 5` from `FarmerSummary` (line 735)
  - [ ] 1.1.5 Add `repeated string farmer_ids = 14` to `CollectionPoint` message (after line 405)
- [ ] 1.2 Add new RPC methods to `PlantationService`:
  ```protobuf
  rpc AssignFarmerToCollectionPoint(AssignFarmerRequest) returns (CollectionPoint);
  rpc UnassignFarmerFromCollectionPoint(UnassignFarmerRequest) returns (CollectionPoint);
  ```
- [ ] 1.3 Add request messages:
  ```protobuf
  message AssignFarmerRequest {
    string collection_point_id = 1;
    string farmer_id = 2;
  }
  message UnassignFarmerRequest {
    string collection_point_id = 1;
    string farmer_id = 2;
  }
  ```
- [ ] 1.4 Regenerate proto stubs: `bash scripts/generate-protos.sh`
- [ ] 1.5 Update `libs/fp-proto/src/fp_proto/plantation/v1/plantation_pb2.pyi` type hints

### Task 2: Pydantic Model Updates (AC: 1, 2)

Update fp-common Pydantic models:

- [ ] 2.1 Modify `libs/fp-common/fp_common/models/farmer.py`:
  - Remove `collection_point_id: str` field from `Farmer` class (line 127)
  - Remove `collection_point_id` from `FarmerCreate` class (line 206)
  - Update example in `model_config` to remove collection_point_id
- [ ] 2.2 Modify `libs/fp-common/fp_common/models/collection_point.py`:
  - Add `farmer_ids: list[str] = Field(default_factory=list, description="Farmers assigned to this CP")` to `CollectionPoint` class
  - Update example in `model_config` to include farmer_ids
- [ ] 2.3 Update proto-to-Pydantic converters in `libs/fp-common/fp_common/converters/plantation_converters.py`:
  - Update `farmer_from_proto()` to remove collection_point_id mapping (line 147)
  - Update `farmer_to_proto()` to remove collection_point_id mapping
  - Update `farmer_summary_from_proto()` to remove collection_point_id from returned dict (line 537)
  - Update `collection_point_from_proto()` to map farmer_ids
  - Update `collection_point_to_proto()` to map farmer_ids
- [ ] 2.4 Update unit tests in `tests/unit/fp_common/`:
  - `tests/unit/fp_common/models/test_farmer.py` - remove collection_point_id tests
  - `tests/unit/fp_common/converters/test_plantation_converters.py` - update converter tests

### Task 3: Plantation Model Service Updates (AC: 1, 2, 4, 5, 6)

Update Plantation Model gRPC service:

- [ ] 3.1 Update `services/plantation-model/src/plantation_model/infrastructure/repositories/farmer_repository.py`:
  - Remove `get_by_collection_point()` method (lines 68-84)
  - Remove collection_point_id from filters docstring (line 162)
  - Remove collection_point_id index from `_ensure_indexes()` (line 183)
- [ ] 3.2 Update `services/plantation-model/src/plantation_model/infrastructure/repositories/collection_point_repository.py`:
  - [ ] 3.2.1 Add farmer_ids to model serialization/deserialization
  - [ ] 3.2.2 Add `add_farmer(cp_id, farmer_id)` method (uses $addToSet for idempotency)
  - [ ] 3.2.3 Add `remove_farmer(cp_id, farmer_id)` method (uses $pull for idempotency)
  - [ ] 3.2.4 Add `get_cps_for_farmer(farmer_id)` method (query: farmer_id in farmer_ids)
- [ ] 3.3 Update `services/plantation-model/src/plantation_model/api/plantation_service.py`:
  - [ ] 3.3.1 Remove collection_point_id from ListFarmers filter (lines 861-862)
  - [ ] 3.3.2 Remove collection_point_id validation in CreateFarmer (lines 908-912)
  - [ ] 3.3.3 Remove collection_point_id from farmer creation dict (line 942)
  - [ ] 3.3.4 Remove collection_point_id from _farmer_to_proto helper (lines 798, 968, 976, 1355)
  - [ ] 3.3.5 Update GetFarmerSummary to get CPs from CP repo (line 1399)
  - [ ] 3.3.6 Add `AssignFarmerToCollectionPoint` handler (validate both IDs exist, call repo)
  - [ ] 3.3.7 Add `UnassignFarmerFromCollectionPoint` handler (validate both IDs exist, call repo)
- [ ] 3.4 Update `services/plantation-model/src/plantation_model/domain/events/farmer_events.py`:
  - Remove `collection_point_id` field from `FarmerRegisteredEvent` (line 29)
  - Update example in docstring (line 44)
- [ ] 3.5 Update unit tests:
  - `tests/unit/plantation/test_farmer_repository.py`
  - `tests/unit/plantation/test_grpc_collection_point.py` - add assignment tests

### Task 4: BFF Updates (AC: 3, 5, 6)

Update BFF admin endpoints and services:

- [ ] 4.1 Update BFF admin schemas `services/bff/src/bff/api/schemas/admin/farmer_schemas.py`:
  - [ ] 4.1.1 Remove `collection_point_id` from `AdminFarmerSummary` (line 34)
  - [ ] 4.1.2 Remove `collection_point_id` from `AdminFarmerDetail` (line 76)
  - [ ] 4.1.3 Remove `collection_point_id` from `AdminFarmerCreateRequest` (line 98)
  - [ ] 4.1.4 Remove `collection_point_id` from `FarmerImportRequest` (lines 164-170)
  - [ ] 4.1.5 Add `factory_count: int` to `AdminFarmerSummary`
  - [ ] 4.1.6 Add `collection_points: list[CollectionPointSummary]` to `AdminFarmerDetail`
- [ ] 4.1b Update BFF non-admin schemas `services/bff/src/bff/api/schemas/farmer_schemas.py`:
  - Remove `collection_point_id` from `FarmerBasicInfo` (line 120)
  - Update example in schema (line 146)
- [ ] 4.2 Add CP assignment schemas `services/bff/src/bff/api/schemas/admin/collection_point_schemas.py`:
  - Add `FarmerAssignmentResponse` schema
- [ ] 4.3 Update BFF routes `services/bff/src/bff/api/routes/admin/collection_points.py`:
  - Add `POST /api/admin/collection-points/{cp_id}/farmers/{farmer_id}` route
  - Add `DELETE /api/admin/collection-points/{cp_id}/farmers/{farmer_id}` route
- [ ] 4.4 Update BFF routes `services/bff/src/bff/api/routes/admin/farmers.py`:
  - Remove collection_point_id from create farmer (line 143)
  - Update list farmers query param - keep collection_point_id filter for "farmers at this CP" (lines 55, 67)
  - Update list farmers response to include factory_count
  - Update get farmer to include collection_points list
  - Update farmer import to not require collection_point_id (lines 204, 210, 226)
- [ ] 4.5 Update BFF services `services/bff/src/bff/services/admin/`:
  - Update `farmer_service.py`:
    - Remove collection_point_id from list_farmers params (lines 53, 63, 75, 82, 102)
    - Update get_farmer to fetch CPs from CP repo (line 152)
    - Remove collection_point_id from create_farmer (lines 193, 199, 211)
    - Update _get_farmer_with_cp helper (lines 218, 275)
  - Update `collection_point_service.py`:
    - Add `assign_farmer()` method
    - Add `unassign_farmer()` method
- [ ] 4.6 Update BFF transformers:
  - Update `services/bff/src/bff/transformers/admin/farmer_transformer.py` (lines 84, 137) to handle factory_count and collection_points
  - Update `services/bff/src/bff/transformers/farmer_transformer.py` (line 137) to remove collection_point_id
- [ ] 4.7 Update BFF Plantation client `services/bff/src/bff/infrastructure/clients/plantation_client.py`:
  - [ ] 4.7.1 Remove collection_point_id from list_farmers filter param (lines 218, 227, 242)
  - [ ] 4.7.2 Remove collection_point_id from create_farmer (line 621)
  - [ ] 4.7.3 Remove collection_point_id from _farmer_summary_from_proto (line 1312)
  - [ ] 4.7.4 Add `assign_farmer_to_cp(cp_id, farmer_id)` method (calls new gRPC)
  - [ ] 4.7.5 Add `unassign_farmer_from_cp(cp_id, farmer_id)` method (calls new gRPC)
  - [ ] 4.7.6 Add `get_cps_for_farmer(farmer_id)` method (list CPs where farmer_id in farmer_ids)
- [ ] 4.8 Update BFF unit tests:
  - `tests/unit/bff/test_admin_schemas.py`
  - `tests/unit/bff/test_admin_transformers.py`
  - `tests/unit/bff/test_plantation_client.py`

### Task 5: MCP Server Updates (AC: 1, 2)

Update Plantation MCP server:

- [ ] 5.1 Update `mcp-servers/plantation-mcp/src/plantation_mcp/tools/definitions.py`:
  - Update farmer-related tool responses to remove collection_point_id
- [ ] 5.2 Update `mcp-servers/plantation-mcp/src/plantation_mcp/api/mcp_service.py`:
  - Update get_farmer tool to not return collection_point_id
- [ ] 5.3 Update `mcp-servers/plantation-mcp/src/plantation_mcp/infrastructure/plantation_client.py`:
  - Remove collection_point_id references
- [ ] 5.4 Update MCP unit tests:
  - `mcp-servers/plantation-mcp/tests/unit/test_mcp_service.py`

### Task 6: Seed Data Updates (AC: 7) ⚠️ MUST COMPLETE BEFORE RUNNING ANY TESTS

> **This task CREATES/UPDATES test data. Complete this BEFORE Task 7, 8, and BEFORE running any tests.**

Update E2E test seed data:

- [ ] 6.1 Update `tests/e2e/infrastructure/seed/farmers.json`:
  - Remove `collection_point_id` from all farmer records
- [ ] 6.2 Update `tests/e2e/infrastructure/seed/collection_points.json`:
  - Add `farmer_ids` arrays to all 3 collection points
  - Map farmers to CPs based on current collection_point_id values:
    - `kericho-highland-cp-100`: ["FRM-E2E-001", "FRM-E2E-002"]
    - `kericho-highland-cp-101`: ["FRM-E2E-003"]
    - `nandi-highland-cp-100`: ["FRM-E2E-004"]
- [ ] 6.3 Update `tests/e2e/infrastructure/mongo-init.js`:
  - Remove collection_point_id index on farmers if exists
  - Add farmer_ids index on collection_points
- [ ] 6.4 Run seed data validation: `python tests/e2e/infrastructure/validate_seed_data.py`

### Task 7: E2E Test Updates (AC: 7) ⚠️ CREATE TESTS BEFORE RUNNING THEM

> **This task CREATES/UPDATES E2E test code. Complete this BEFORE running `bash scripts/e2e-test.sh`.**
> **PREREQUISITE:** Task 6 (Seed Data) must be complete first.

Update existing E2E tests and add new ones:

- [ ] 7.1 Update `tests/e2e/scenarios/test_03_factory_farmer_flow.py`:
  - [ ] 7.1.1 Update farmer creation tests (no collection_point_id in request/response)
  - [ ] 7.1.2 Add test for farmer-CP assignment after creation
- [ ] 7.2 Update `tests/e2e/scenarios/test_30_bff_farmer_api.py`:
  - [ ] 7.2.1 Update farmer list test to check factory_count instead of collection_point_id
  - [ ] 7.2.2 Update farmer detail test to check collection_points list
- [ ] 7.3 Update `tests/e2e/scenarios/test_31_bff_admin_api.py`:
  - [ ] 7.3.1 Add test for POST /api/admin/collection-points/{cp_id}/farmers/{farmer_id}
  - [ ] 7.3.2 Add test for DELETE /api/admin/collection-points/{cp_id}/farmers/{farmer_id}
  - [ ] 7.3.3 Test idempotency of assignment operations
- [ ] 7.4 Update `tests/e2e/scenarios/test_01_plantation_mcp_contracts.py`:
  - [ ] 7.4.1 Update farmer tool contract tests (no collection_point_id in response)
- [ ] 7.5 Update `tests/e2e/helpers/api_clients.py`:
  - [ ] 7.5.1 Add `assign_farmer_to_cp(cp_id, farmer_id)` method
  - [ ] 7.5.2 Add `unassign_farmer_from_cp(cp_id, farmer_id)` method
  - [ ] 7.5.3 Update `admin_create_farmer()` to not require collection_point_id
- [ ] 7.6 Create new test file `tests/e2e/scenarios/test_35_farmer_cp_assignment.py`:
  - [ ] 7.6.1 Test assign farmer to CP (POST returns updated CP with farmer in farmer_ids)
  - [ ] 7.6.2 Test unassign farmer from CP (DELETE returns updated CP without farmer)
  - [ ] 7.6.3 Test idempotent assign (POST twice = 200, no duplicate in farmer_ids)
  - [ ] 7.6.4 Test idempotent unassign (DELETE non-member = 200, no error)
  - [ ] 7.6.5 Test farmer appears in multiple CPs (assign same farmer to 2 CPs)
  - [ ] 7.6.6 Test factory_count calculation (farmer in 2 CPs of same factory = 1, different factories = 2)
  - [ ] 7.6.7 Test assign with invalid farmer_id (404)
  - [ ] 7.6.8 Test assign with invalid cp_id (404)

### Task 8: Integration Tests Updates

> **PREREQUISITE:** Task 6 (Seed Data Updates) MUST be completed first. Integration tests use the same seed data patterns.

Update integration tests:

- [ ] 8.0 Verify seed data is updated (Task 6 complete):
  - [ ] 8.0.1 farmers.json has NO collection_point_id fields
  - [ ] 8.0.2 collection_points.json has farmer_ids arrays
- [ ] 8.1 Update `tests/integration/test_plantation_farmer_flow.py`:
  - [ ] 8.1.1 Remove collection_point_id from farmer creation test data
  - [ ] 8.1.2 Update assertions that check farmer.collection_point_id
- [ ] 8.2 Update `tests/integration/test_plantation_cp_flow.py`:
  - [ ] 8.2.1 Add test for `add_farmer()` repository method
  - [ ] 8.2.2 Add test for `remove_farmer()` repository method
  - [ ] 8.2.3 Add test for `get_cps_for_farmer()` repository method
  - [ ] 8.2.4 Test idempotency of add/remove operations
- [ ] 8.3 Update `tests/integration/test_farmer_repository_mongodb.py`:
  - [ ] 8.3.1 Remove collection_point_id from test farmer dicts
  - [ ] 8.3.2 Remove tests for `get_by_collection_point()` method (deleted)
  - [ ] 8.3.3 Update index verification tests

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 9.5a: Farmer-CP Data Model Refactor"` → **#200**
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/9-5a-farmer-cp-data-model
  ```

**Branch name:** `story/9-5a-farmer-cp-data-model`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #200`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/9-5a-farmer-cp-data-model`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 9.5a: Farmer-CP Data Model Refactor" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review`)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/9-5a-farmer-cp-data-model`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

> **⛔ CRITICAL: ALL TEST FAILURES ARE YOUR RESPONSIBILITY**
>
> This story changes a **fundamental data model field** (`collection_point_id` → `farmer_ids`).
> - If a unit test fails → YOU broke it, fix it
> - If an integration test fails → YOU broke it, fix it
> - If an E2E test fails → YOU broke it, fix it
> - If seed data validation fails → YOU broke it, fix it
>
> **DO NOT say "this test failure is not related to my changes"** - in this story, EVERY failure is related to your changes because you changed a core data model field that touches 105 files.
>
> **Your job is not done until ALL tests pass.**

### 1. Unit Tests
```bash
pytest tests/unit/ -v
```
**Output:**
```
(paste test summary here - e.g., "42 passed in 5.23s")
```

### 2. E2E Tests (MANDATORY)

> **⛔ BLOCKER: You CANNOT run E2E tests until Tasks 6,7 and 8 are COMPLETE.**
>
> **CREATE tests FIRST, then RUN them:**
> - [ ] Task 6 (Seed Data Updates) - COMPLETE?
> - [ ] Task 7 (E2E Test Updates) - COMPLETE?
> - [ ] Task 8 (Integration Test Updates) - COMPLETE?
>
> **If any checkbox above is unchecked, STOP. Go back and complete those tasks BEFORE running tests.**

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure with rebuild
bash scripts/e2e-up.sh --build

# Run pre-flight validation
bash scripts/e2e-preflight.sh

# Run E2E test suite
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
git push origin story/9-5a-farmer-cp-data-model

# Wait ~30s, then check CI status
gh run list --branch story/9-5a-farmer-cp-data-model --limit 3
```
**CI Run ID:** _______________
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### Data Model Change Summary

**Before (N:1 - WRONG):**
```python
class Farmer(BaseModel):
    id: str
    collection_point_id: str  # Single FK - implies farmer belongs to ONE CP
    ...

class CollectionPoint(BaseModel):
    id: str
    factory_id: str
    ...
```

**After (N:M - CORRECT):**
```python
class Farmer(BaseModel):
    id: str
    # NO collection_point_id - farmer is independent
    ...

class CollectionPoint(BaseModel):
    id: str
    factory_id: str
    farmer_ids: list[str] = []  # Farmers assigned to this CP
    ...
```

### Query Patterns

| Query | Implementation |
|-------|----------------|
| Farmers at CP X | `cp.farmer_ids` (direct) |
| CPs for Farmer Y | Find all CPs where `farmer_id in farmer_ids` |
| Factory count for Farmer | Count distinct `factory_id` from CPs containing farmer |
| Farmers in Factory Z | Find all CPs for factory, union all farmer_ids |

### Files to Modify Summary

| Layer | Files | Impact |
|-------|-------|--------|
| **Proto** | `proto/plantation/v1/plantation.proto` | Remove field, add field, add RPCs |
| **fp-common models** | `libs/fp-common/fp_common/models/farmer.py`, `collection_point.py` | Remove/add fields |
| **fp-common converters** | `libs/fp-common/fp_common/converters/plantation_converters.py` | Update mappings |
| **Plantation Model** | `services/plantation-model/src/plantation_model/` (handlers, repos) | Major changes |
| **BFF** | `services/bff/src/bff/` (routes, schemas, services, transformers) | Major changes |
| **Plantation MCP** | `mcp-servers/plantation-mcp/src/plantation_mcp/` | Remove field references |
| **Seed Data** | `tests/e2e/infrastructure/seed/` | Update JSON files |
| **E2E Tests** | `tests/e2e/scenarios/` | Update + new tests |
| **Unit Tests** | `tests/unit/` (plantation, bff, fp_common) | Update existing |
| **Integration Tests** | `tests/integration/` | Update existing |

### Impact Analysis (105 files reference collection_point_id)

**Proto Layer (4 references):**
- `proto/plantation/v1/plantation.proto` - lines 502, 529, 542, 735

**Pydantic Models (4 references):**
- `libs/fp-common/fp_common/models/farmer.py` - lines 117, 127, 167, 206

**Converters (2 references):**
- `libs/fp-common/fp_common/converters/plantation_converters.py` - lines 147, 537

**Plantation Model Service (18 references):**
- `services/plantation-model/src/plantation_model/api/plantation_service.py` - 10 refs
- `services/plantation-model/src/plantation_model/infrastructure/repositories/farmer_repository.py` - 5 refs
- `services/plantation-model/src/plantation_model/domain/events/farmer_events.py` - 2 refs
- `services/plantation-model/src/plantation_model/domain/models/id_generator.py` - 1 ref (CP ID gen - KEEP)

**BFF Service (52+ references):**
- `services/bff/src/bff/api/schemas/admin/farmer_schemas.py` - 5 refs
- `services/bff/src/bff/api/schemas/farmer_schemas.py` - 2 refs
- `services/bff/src/bff/api/routes/admin/farmers.py` - 9 refs
- `services/bff/src/bff/services/admin/farmer_service.py` - 13 refs
- `services/bff/src/bff/transformers/admin/farmer_transformer.py` - 2 refs
- `services/bff/src/bff/transformers/farmer_transformer.py` - 1 ref
- `services/bff/src/bff/infrastructure/clients/plantation_client.py` - 12 refs
- `services/bff/src/bff/api/schemas/auth.py` - 3 refs (KEEP - clerk assignment context)

**MCP Servers:**
- `mcp-servers/plantation-mcp/src/plantation_mcp/tools/definitions.py`
- `mcp-servers/plantation-mcp/src/plantation_mcp/api/mcp_service.py`
- `mcp-servers/plantation-mcp/src/plantation_mcp/infrastructure/plantation_client.py`

**Seed Data:**
- `tests/e2e/infrastructure/seed/farmers.json` - 4 farmers have collection_point_id
- `tests/e2e/infrastructure/seed/collection_points.json` - needs farmer_ids added

**Test Files to Update:**
- `tests/e2e/scenarios/test_03_factory_farmer_flow.py`
- `tests/e2e/scenarios/test_30_bff_farmer_api.py`
- `tests/e2e/scenarios/test_31_bff_admin_api.py`
- `tests/e2e/scenarios/test_01_plantation_mcp_contracts.py`
- `tests/unit/plantation/test_farmer_repository.py`
- `tests/unit/plantation/test_farmer_events.py`
- `tests/unit/bff/test_admin_schemas.py`
- `tests/unit/bff/test_farmer_transformer.py`
- `tests/unit/fp_common/converters/test_plantation_converters.py`

**NOTE:** `auth.py` collection_point_id is for **clerk assignment** (which CP a clerk works at) - this is a DIFFERENT concept and should NOT be changed.

### Previous Story Intelligence (Story 9.4)

**Key patterns from Collection Point Management:**

1. **API client pattern**: Use native fetch, return `{ data: T }` wrapper in frontend
2. **BFF schema pattern**: Use Pydantic schemas with snake_case, transform for frontend
3. **gRPC handler pattern**: Follow existing handlers in plantation_service.py
4. **Test pattern**: E2E tests use `api_clients.py` helper methods
5. **Seed data pattern**: JSON files in `tests/e2e/infrastructure/seed/`

**Code review findings to remember:**
- Ensure idempotent operations (assign twice = no error)
- Include proper validation (farmer exists, CP exists)
- Update all converters when proto changes

### Technology Stack Reference

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.12 | Service implementation |
| Pydantic | 2.0 | Data validation (`model_dump()`, not `dict()`) |
| gRPC | Latest | Inter-service communication |
| FastAPI | Latest | BFF REST API |
| MongoDB | Managed | Data storage |
| Protobuf | 3 | Service contracts |

### Testing Requirements

| Test Type | Location | What to Test |
|-----------|----------|--------------|
| Unit | `tests/unit/` | Model changes, converter changes |
| Integration | `tests/integration/` | Repository operations |
| E2E | `tests/e2e/scenarios/` | Full API flows, assignment operations |

### References

- [Source: _bmad-output/epics/epic-9-admin-portal/story-95a-farmer-cp-data-model.md] - Original story definition
- [Source: _bmad-output/epics/epic-9-admin-portal/story-95-farmer-management.md] - Parent story context
- [Source: _bmad-output/sprint-artifacts/9-4-collection-point-management.md] - Previous story patterns
- [Source: libs/fp-common/fp_common/models/farmer.py:127] - Current collection_point_id field
- [Source: libs/fp-common/fp_common/models/collection_point.py] - Current CP model (no farmer_ids)
- [Source: proto/plantation/v1/plantation.proto:502] - Proto Farmer.collection_point_id
- [Source: _bmad-output/project-context.md] - Project rules and patterns

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

**Created:**
- (list new files)

**Modified:**
- (list modified files with brief description)
