# Story 9.1c: Admin Portal BFF Endpoints

**Status:** ready-for-dev
**GitHub Issue:** <!-- Auto-created by dev-story workflow -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **platform admin frontend**,
I want **REST API endpoints for all admin portal entity management**,
So that **Stories 9.2-9.5 can consume stable, tested APIs without building infrastructure**.

## Acceptance Criteria

### AC1: Region Management Endpoints
**Given** an authenticated platform admin user
**When** calling `/api/admin/regions` endpoints
**Then** the following operations are available:
- `GET /api/admin/regions` - List all regions with pagination
- `GET /api/admin/regions/{region_id}` - Get region detail including weather config and polygon boundaries
- `POST /api/admin/regions` - Create new region with weather configuration and polygon boundaries
- `PUT /api/admin/regions/{region_id}` - Update region including weather config and polygon boundaries

**Validation:**
- Region ID pattern: `^[a-z][a-z0-9-]*[a-z0-9]$` (kebab-case, 3-50 chars)
- Weather configuration required for regions with farms
- Polygon boundaries optional but validated if provided (GeoJSON-like format per ADR-017)

### AC2: Factory Management Endpoints
**Given** an authenticated platform admin user
**When** calling `/api/admin/factories` endpoints
**Then** the following operations are available:
- `GET /api/admin/factories` - List all factories with pagination
- `GET /api/admin/factories/{factory_id}` - Get factory detail including quality thresholds and grading model
- `POST /api/admin/factories` - Create new factory with quality thresholds
- `PUT /api/admin/factories/{factory_id}` - Update factory settings

**Validation:**
- Factory ID pattern: `^[A-Z]{3}-FAC-\d{3}$` (e.g., KEN-FAC-001)
- Quality thresholds required: tier_1, tier_2, tier_3 (each 0-100, tier_1 > tier_2 > tier_3)
- Region ID must reference existing region

### AC3: Collection Point Management Endpoints
**Given** an authenticated platform admin user
**When** calling `/api/admin/collection-points` endpoints
**Then** the following operations are available:
- `GET /api/admin/collection-points` - List collection points with factory_id filter (required)
- `GET /api/admin/collection-points/{cp_id}` - Get collection point detail
- `PUT /api/admin/collection-points/{cp_id}` - Update collection point

**Note:** Collection points are created via `POST /api/admin/factories/{factory_id}/collection-points` (nested under factory)

**Validation:**
- Collection Point ID pattern: `^[a-z][a-z0-9-]*-cp-\d{3}$`
- Location coordinates required (latitude, longitude)
- Factory ID must reference existing factory

### AC4: Farmer Management Endpoints (Admin Context)
**Given** an authenticated platform admin user
**When** calling `/api/admin/farmers` endpoints
**Then** the following operations are available:
- `GET /api/admin/farmers` - List farmers with filters (region_id, factory_id, collection_point_id)
- `GET /api/admin/farmers/{farmer_id}` - Get farmer detail with admin-specific fields
- `POST /api/admin/farmers` - Create new farmer
- `PUT /api/admin/farmers/{farmer_id}` - Update farmer profile
- `POST /api/admin/farmers/import` - Bulk import farmers from CSV

**Validation:**
- Farmer ID pattern: `^WM-\d{4}$` (auto-generated on create)
- Phone number: E.164 format (e.g., +254712345678)
- Collection point must exist

### AC5: Platform Admin Authorization
**Given** any `/api/admin/*` endpoint
**When** a request is made
**Then**:
- Requests without valid JWT return 401
- Requests from non-platform_admin roles return 403
- Requests with valid platform_admin JWT succeed

### AC6: Error Response Format
**Given** any API error condition
**When** the error is returned
**Then** response follows RFC 7807 Problem Details format with:
- `code`: Machine-readable error code (e.g., `not_found`, `validation_error`)
- `message`: Human-readable description
- `details`: Field-level errors for validation failures

### AC7: Service Composition Pattern
**Given** endpoints requiring data from multiple sources
**When** composing responses
**Then**:
- Use `BaseService._parallel_map()` for fan-out scenarios (e.g., enriching factories with grading models)
- Use bounded concurrency (Semaphore(5)) per ADR-012
- Return `PaginatedResponse[T]` or domain models per ADR-012 patterns

### AC8: E2E Test Coverage
**Given** all `/api/admin/*` endpoints
**When** E2E tests run
**Then**:
- Region CRUD flow validates: Create → Get → Update → List
- Factory CRUD flow validates: Create with thresholds → Get → Update → List
- Collection Point flow validates: Get → Update (via factory)
- Farmer CRUD flow validates: Create → Get → Update → List with filters
- Farmer Import flow validates: CSV upload → Validation → Bulk create
- All tests use seed data from `tests/e2e/seed-data/`

## Tasks / Subtasks

### Task 1: Admin API Schema Layer (AC: 1-4, 6)

Create API-specific Pydantic schemas in `services/bff/src/bff/api/schemas/admin/`:

- [ ] 1.1 Create `admin/__init__.py` - Export all admin schemas
- [ ] 1.2 Create `admin/region_schemas.py`:
  - `RegionSummary`: List view (id, name, factory_count, farmer_count)
  - `RegionDetail`: Full detail (weather_config, polygon_boundaries, factories)
  - `RegionCreateRequest`: Creation payload (name, weather_config, polygon_boundaries)
  - `RegionUpdateRequest`: Update payload (all optional fields)
  - `RegionListResponse`: Paginated list response
- [ ] 1.3 Create `admin/factory_schemas.py`:
  - `FactorySummary`: List view (id, name, region_id, collection_point_count)
  - `FactoryDetail`: Full detail (quality_thresholds, grading_model, collection_points)
  - `FactoryCreateRequest`: Creation payload
  - `FactoryUpdateRequest`: Update payload
  - `FactoryListResponse`: Paginated list response
  - `QualityThresholdsAPI`: Thresholds for API layer
- [ ] 1.4 Create `admin/collection_point_schemas.py`:
  - `CollectionPointSummary`: List view (id, name, factory_id, farmer_count)
  - `CollectionPointDetail`: Full detail (location, lead_farmer)
  - `CollectionPointCreateRequest`: Creation payload (nested under factory)
  - `CollectionPointUpdateRequest`: Update payload
  - `CollectionPointListResponse`: Paginated list response
- [ ] 1.5 Create `admin/farmer_schemas.py`:
  - `AdminFarmerSummary`: Admin list view (id, name, phone, cp_id, region_id, tier)
  - `AdminFarmerDetail`: Full detail (profile, performance, communication_prefs)
  - `AdminFarmerCreateRequest`: Creation payload
  - `AdminFarmerUpdateRequest`: Update payload
  - `AdminFarmerListResponse`: Paginated list response
  - `FarmerImportRequest`: CSV import payload
  - `FarmerImportResponse`: Import result (created_count, error_rows)

### Task 2: Admin Transformers (AC: 1-4)

Create transformers in `services/bff/src/bff/transformers/admin/`:

- [ ] 2.1 Create `admin/__init__.py` - Export all transformers
- [ ] 2.2 Create `admin/region_transformer.py`:
  - `to_summary(region: Region) -> RegionSummary`
  - `to_detail(region: Region, factories: list[Factory]) -> RegionDetail`
- [ ] 2.3 Create `admin/factory_transformer.py`:
  - `to_summary(factory: Factory) -> FactorySummary`
  - `to_detail(factory: Factory, grading_model: GradingModel, cps: list[CollectionPoint]) -> FactoryDetail`
- [ ] 2.4 Create `admin/collection_point_transformer.py`:
  - `to_summary(cp: CollectionPoint) -> CollectionPointSummary`
  - `to_detail(cp: CollectionPoint, lead_farmer: Farmer | None) -> CollectionPointDetail`
- [ ] 2.5 Create `admin/farmer_transformer.py`:
  - `to_admin_summary(farmer: Farmer, performance: FarmerSummary) -> AdminFarmerSummary`
  - `to_admin_detail(farmer: Farmer, performance: FarmerPerformance, comm_prefs: CommunicationPreferences) -> AdminFarmerDetail`

### Task 3: Admin Service Layer (AC: 1-4, 7)

Create services in `services/bff/src/bff/services/admin/`:

- [ ] 3.1 Create `admin/__init__.py` - Export all services
- [ ] 3.2 Create `admin/region_service.py`:
  - `list_regions(page_size, page_token) -> RegionListResponse`
  - `get_region(region_id) -> RegionDetail`
  - `create_region(data: RegionCreateRequest) -> RegionDetail`
  - `update_region(region_id, data: RegionUpdateRequest) -> RegionDetail`
  - Use parallel fetch for factory counts
- [ ] 3.3 Create `admin/factory_service.py`:
  - `list_factories(region_id, page_size, page_token) -> FactoryListResponse`
  - `get_factory(factory_id) -> FactoryDetail`
  - `create_factory(data: FactoryCreateRequest) -> FactoryDetail`
  - `update_factory(factory_id, data: FactoryUpdateRequest) -> FactoryDetail`
  - Use `_parallel_map` for grading model and CP enrichment
- [ ] 3.4 Create `admin/collection_point_service.py`:
  - `list_collection_points(factory_id, page_size, page_token) -> CollectionPointListResponse`
  - `get_collection_point(cp_id) -> CollectionPointDetail`
  - `create_collection_point(factory_id, data: CollectionPointCreateRequest) -> CollectionPointDetail`
  - `update_collection_point(cp_id, data: CollectionPointUpdateRequest) -> CollectionPointDetail`
- [ ] 3.5 Create `admin/farmer_service.py`:
  - `list_farmers(filters, page_size, page_token) -> AdminFarmerListResponse`
  - `get_farmer(farmer_id) -> AdminFarmerDetail`
  - `create_farmer(data: AdminFarmerCreateRequest) -> AdminFarmerDetail`
  - `update_farmer(farmer_id, data: AdminFarmerUpdateRequest) -> AdminFarmerDetail`
  - `import_farmers(csv_data) -> FarmerImportResponse`

### Task 4: Admin API Routes (AC: 1-5)

Create routes in `services/bff/src/bff/api/routes/admin/`:

- [ ] 4.1 Create `admin/__init__.py` - Export router combining all admin routes
- [ ] 4.2 Create `admin/regions.py`:
  - `GET /api/admin/regions` - List regions
  - `GET /api/admin/regions/{region_id}` - Get region
  - `POST /api/admin/regions` - Create region
  - `PUT /api/admin/regions/{region_id}` - Update region
  - All routes require `platform_admin` role
- [ ] 4.3 Create `admin/factories.py`:
  - `GET /api/admin/factories` - List factories (optional region_id filter)
  - `GET /api/admin/factories/{factory_id}` - Get factory
  - `POST /api/admin/factories` - Create factory
  - `PUT /api/admin/factories/{factory_id}` - Update factory
  - `POST /api/admin/factories/{factory_id}/collection-points` - Create CP (nested)
- [ ] 4.4 Create `admin/collection_points.py`:
  - `GET /api/admin/collection-points` - List CPs (factory_id required)
  - `GET /api/admin/collection-points/{cp_id}` - Get CP
  - `PUT /api/admin/collection-points/{cp_id}` - Update CP
- [ ] 4.5 Create `admin/farmers.py`:
  - `GET /api/admin/farmers` - List farmers (filters: region_id, factory_id, cp_id)
  - `GET /api/admin/farmers/{farmer_id}` - Get farmer
  - `POST /api/admin/farmers` - Create farmer
  - `PUT /api/admin/farmers/{farmer_id}` - Update farmer
  - `POST /api/admin/farmers/import` - Import from CSV
- [ ] 4.6 Register admin router in `main.py`

### Task 5: Authorization Enhancement (AC: 5)

- [ ] 5.1 Create `require_platform_admin()` dependency in `api/middleware/auth.py`
  - Returns 403 if `user.role != "platform_admin"`
  - Use across all `/api/admin/*` routes
- [ ] 5.2 Add `platform_admin` role to seed data JWT tokens

### Task 6: Unit Tests

Create unit tests in `tests/unit/bff/`:

- [ ] 6.1 Create `test_admin_schemas.py` - Schema validation tests
- [ ] 6.2 Create `test_admin_transformers.py` - Transformer unit tests
- [ ] 6.3 Create `test_admin_services.py` - Service layer tests (mock clients)
- [ ] 6.4 Create `test_admin_routes.py` - Route tests (mock services)
- [ ] 6.5 All tests mock PlantationClient, no real gRPC calls

### Task 7: E2E Test Infrastructure (AC: 8)

- [ ] 7.1 Add admin seed data to `tests/e2e/seed-data/`:
  - `admin_regions.json` - Test regions with weather config
  - `admin_factories.json` - Test factories with thresholds
  - `admin_collection_points.json` - Test CPs
  - `admin_farmers.json` - Test farmers for admin endpoints
- [ ] 7.2 Create E2E scenarios in `tests/e2e/scenarios/test_admin_api_*.py`:
  - `test_admin_api_regions.py` - Region CRUD flow
  - `test_admin_api_factories.py` - Factory CRUD flow
  - `test_admin_api_collection_points.py` - CP operations
  - `test_admin_api_farmers.py` - Farmer CRUD flow
  - `test_admin_api_farmer_import.py` - Bulk import flow

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 9.1c: Admin Portal BFF Endpoints"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/9-1c-admin-portal-bff-endpoints
  ```

**Branch name:** `story/9-1c-admin-portal-bff-endpoints`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/9-1c-admin-portal-bff-endpoints`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 9.1c: Admin Portal BFF Endpoints" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/9-1c-admin-portal-bff-endpoints`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
pytest tests/unit/bff/ -v
```
**Output:**
```
(paste test summary here - e.g., "42 passed in 5.23s")
```

### 2. E2E Tests (MANDATORY)

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
git push origin story/9-1c-admin-portal-bff-endpoints

# Wait ~30s, then check CI status
gh run list --branch story/9-1c-admin-portal-bff-endpoints --limit 3
```
**CI Run ID:** _______________
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## E2E Story Checklist (Additional guidance for E2E-focused stories)

**Read First:** `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

### Pre-Implementation
- [ ] Read and understood `E2E-TESTING-MENTAL-MODEL.md`
- [ ] Understand: Proto = source of truth, tests verify (not define) behavior

### Before Starting Docker
- [ ] Validate seed data: `python tests/e2e/infrastructure/validate_seed_data.py`
- [ ] All seed files pass validation

### During Implementation
- [ ] If tests fail, investigate using the debugging checklist (not blindly modify code)
- [ ] If seed data needs changes, fix seed data (not production code)
- [ ] If production code has bugs, document each fix (see below)

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
| (none) | | | |

**Key insight:** If a change affects how production services BEHAVE (even via configuration), document it.

### Unit Test Changes (if any)
If you modified ANY unit test behavior, document here:

| Test File | Test Name Before | Test Name After | Behavior Change | Justification |
|-----------|------------------|-----------------|-----------------|---------------|
| (none) | | | | |

**Rules:**
- Changing "expect failure" to "expect success" REQUIRES justification
- Reference the AC, proto, or requirement that proves the new behavior is correct
- If you can't justify, the original test was probably right - investigate more

### Local Test Run Evidence (MANDATORY before any push)

**First run timestamp:** _______________

**Docker stack status:**
```
# Paste output of: docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml ps
```

**Test run output:**
```
# Paste output of: pytest tests/e2e/scenarios/test_admin_*.py -v
# Must show: X passed, 0 failed
```

**If tests failed before passing, explain what you fixed:**

| Attempt | Failure | Root Cause | Fix Applied | Layer Fixed |
|---------|---------|------------|-------------|-------------|
| 1 | | | | |

### Before Marking Done
- [ ] All tests pass locally with Docker infrastructure
- [ ] `ruff check` and `ruff format --check` pass
- [ ] CI pipeline is green
- [ ] If production code changed: Change log above is complete
- [ ] If unit tests changed: Change log above is complete
- [ ] Story file updated with completion notes

---

## Dev Notes

### Architectural Patterns (ADR-012)

This story implements ADR-012 BFF Service Composition patterns for admin endpoints:

1. **Service Composition**: Use `BaseService._parallel_map()` for enrichment scenarios
2. **Response Wrappers**: Use `PaginatedResponse[T]` from infrastructure/clients/responses.py
3. **API Schemas**: Separate from domain models in `api/schemas/admin/`
4. **Transformers**: Domain → API conversion in `transformers/admin/`
5. **Error Handling**: Use `ApiError` factory methods (not_found, forbidden, etc.)

### gRPC Service & Methods (CRITICAL)

**Service:** Plantation Model (`plantation-model` via DAPR service invocation)
**Proto:** `proto/plantation/v1/plantation.proto`
**BFF Client:** `services/bff/src/bff/infrastructure/clients/plantation_client.py`

All required gRPC methods are **already implemented** in PlantationClient. DO NOT create new clients.

| Entity | PlantationClient Method | Proto RPC | Line |
|--------|------------------------|-----------|------|
| **Region** | `list_regions()` | `ListRegions` | ~440 |
| | `get_region()` | `GetRegion` | ~400 |
| | `create_region()` | `CreateRegion` | ~974 |
| | `update_region()` | `UpdateRegion` | ~1061 |
| **Factory** | `list_factories()` | `ListFactories` | ~307 |
| | `get_factory()` | `GetFactory` | ~270 |
| | `create_factory()` | `CreateFactory` | ~682 |
| | `update_factory()` | `UpdateFactory` | ~742 |
| | `delete_factory()` | `DeleteFactory` | ~812 |
| **Collection Point** | `list_collection_points()` | `ListCollectionPoints` | ~372 |
| | `get_collection_point()` | `GetCollectionPoint` | ~340 |
| | `create_collection_point()` | `CreateCollectionPoint` | ~839 |
| | `update_collection_point()` | `UpdateCollectionPoint` | ~892 |
| | `delete_collection_point()` | `DeleteCollectionPoint` | ~947 |
| **Farmer** | `list_farmers()` | `ListFarmers` | ~213 |
| | `get_farmer()` | `GetFarmer` | ~180 |
| | `create_farmer()` | `CreateFarmer` | ~603 |
| | `update_farmer()` | `UpdateFarmer` | ~641 |
| | `get_farmer_summary()` | `GetFarmerSummary` | ~500 |
| **Grading Model** | `get_factory_grading_model()` | `GetFactoryGradingModel` | ~560 |

### Existing Patterns to Follow

**Reference Implementation:** `services/bff/src/bff/api/routes/farmers.py`
- Route structure with FastAPI decorators
- Dependency injection for services
- Permission checking via `require_permission()`
- Error handling with HTTPException + ApiError

**gRPC Client Usage Pattern:**
```python
# In your admin service, inject PlantationClient (already exists)
from bff.infrastructure.clients.plantation_client import PlantationClient

class RegionService(BaseService):
    def __init__(self, plantation_client: PlantationClient):
        self._plantation = plantation_client

    async def list_regions(self, page_size: int, page_token: str | None) -> RegionListResponse:
        # Use existing client method - returns PaginatedResponse[Region]
        response = await self._plantation.list_regions(page_size=page_size, page_token=page_token)
        # Transform to API schema
        return RegionListResponse(
            data=[RegionTransformer.to_summary(r) for r in response.items],
            pagination=PaginationMeta.from_client_response(...)
        )
```

### Authorization Requirements

Platform admin endpoints require stricter authorization than factory portal:
- **Factory Portal**: `require_permission("farmers:read")` - factory-scoped access
- **Admin Portal**: `require_platform_admin()` - global platform admin role only

Create new dependency that checks `user.role == "platform_admin"`.

### Polygon Boundary Support (ADR-017)

Region endpoints must support polygon boundaries for GPS-based region assignment:
- `polygon_boundaries: list[Coordinate]` - GeoJSON-like format
- Validated via existing `validate_polygon_boundaries()` in PlantationClient
- See Story 1.10 for implementation reference

### Farmer Import Endpoint

The CSV import endpoint (`POST /api/admin/farmers/import`) should:
1. Accept multipart/form-data with CSV file
2. Parse and validate each row
3. Call `create_farmer()` for valid rows
4. Return summary: `{created_count: N, error_rows: [{row: 5, error: "..."}]}`
5. Use bounded concurrency for batch creation

### Project Structure Notes

Files to create:
```
services/bff/src/bff/
├── api/
│   ├── routes/
│   │   └── admin/
│   │       ├── __init__.py
│   │       ├── regions.py
│   │       ├── factories.py
│   │       ├── collection_points.py
│   │       └── farmers.py
│   └── schemas/
│       └── admin/
│           ├── __init__.py
│           ├── region_schemas.py
│           ├── factory_schemas.py
│           ├── collection_point_schemas.py
│           └── farmer_schemas.py
├── services/
│   └── admin/
│       ├── __init__.py
│       ├── region_service.py
│       ├── factory_service.py
│       ├── collection_point_service.py
│       └── farmer_service.py
└── transformers/
    └── admin/
        ├── __init__.py
        ├── region_transformer.py
        ├── factory_transformer.py
        ├── collection_point_transformer.py
        └── farmer_transformer.py

tests/
├── unit/bff/
│   ├── test_admin_schemas.py
│   ├── test_admin_transformers.py
│   ├── test_admin_services.py
│   └── test_admin_routes.py
└── e2e/
    ├── seed-data/
    │   ├── admin_regions.json
    │   ├── admin_factories.json
    │   ├── admin_collection_points.json
    │   └── admin_farmers.json
    └── scenarios/
        ├── test_admin_api_regions.py
        ├── test_admin_api_factories.py
        ├── test_admin_api_collection_points.py
        ├── test_admin_api_farmers.py
        └── test_admin_api_farmer_import.py
```

### References

- [Source: _bmad-output/architecture/adr/ADR-012-bff-service-composition-api-design.md] - Service composition patterns
- [Source: _bmad-output/architecture/adr/ADR-017-gps-region-assignment.md] - Polygon boundary support
- [Source: services/bff/src/bff/api/routes/farmers.py] - Route implementation pattern
- [Source: services/bff/src/bff/infrastructure/clients/plantation_client.py] - gRPC client methods
- [Source: proto/plantation/v1/plantation.proto:19-47] - Available gRPC RPCs
- [Source: _bmad-output/epics/epic-9-admin-portal/story-91c-admin-portal-bff-endpoints.md] - Original story definition
- [Source: tests/e2e/E2E-TESTING-MENTAL-MODEL.md] - E2E testing approach

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
