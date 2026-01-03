# Story 0.5.4b: BFF API Routes

**Status:** in-progress
**GitHub Issue:** #79

## Story

As a **frontend developer**,
I want **REST API endpoints for listing and viewing farmers**,
so that **the Factory Portal can display farmer information**.

## Acceptance Criteria

1. **Farmer List Endpoint (AC1)**:
   - `GET /api/farmers?factory_id={id}&page_size={n}&page_token={token}`
   - Returns paginated farmer list with quality summaries
   - Response uses `FarmerListResponse` API schema
   - Each farmer includes: `id`, `name`, `primary_percentage_30d`, `tier`, `trend`
   - `tier` uses Plantation vocabulary: `tier_1`, `tier_2`, `tier_3`, `below_tier_3`
   - Factory authorization is enforced (user must have access to requested factory_id)

2. **Farmer Detail Endpoint (AC2)**:
   - `GET /api/farmers/{farmer_id}`
   - Returns farmer profile with performance summary
   - Response uses `FarmerDetailResponse` API schema
   - Factory authorization enforced (farmer's factory must match user's factory_ids)

3. **Error Handling (AC3)**:
   - All errors use `ApiError` (RFC 7807-style, from Story 0.5.4a)
   - Use `HTTPException` with `ApiError.model_dump()` as detail
   - Internal details NOT exposed to client
   - Error factory methods: `ApiError.not_found()`, `ApiError.forbidden()`, `ApiError.service_unavailable()`

4. **Service Composition (ADR-012 Decision 1)**:
   - FarmerService orchestrates calls to PlantationClient
   - Sequential: Get factory thresholds, then get farmers
   - Parallel (bounded): Enrich each farmer with performance metrics using `Semaphore(5)`
   - Use `BaseService._parallel_map()` for bounded concurrency

5. **API Schema Transformation (ADR-012 Decision 2)**:
   - FarmerTransformer converts domain models to API schemas
   - Tier computed from `Factory.quality_thresholds` (factory-configurable thresholds)
   - API schemas are separate from domain models (not exposing fp_common directly)

6. **Unit Tests**:
   - 95%+ coverage for FarmerService, FarmerTransformer, and route handlers
   - Mock PlantationClient in all tests
   - Test tier computation logic with various threshold combinations
   - Test bounded concurrency behavior

7. **E2E Integration**:
   - `GET /api/farmers?factory_id=KEN-FAC-001` returns paginated response
   - `GET /api/farmers/WM-0001` returns farmer detail with performance enrichment

## Tasks / Subtasks

- [x] **Task 1: Create Base Service Infrastructure** (AC: #4)
  - [x] 1.1 Create `services/bff/src/bff/services/__init__.py`
  - [x] 1.2 Create `services/bff/src/bff/services/base_service.py` with:
    - `_parallel_map()` helper using `asyncio.Semaphore(5)`
    - Base class for all BFF services
    - Logging integration with structlog
  - [x] 1.3 Create `services/bff/src/bff/transformers/__init__.py`

- [x] **Task 2: Create API Schemas** (AC: #2, #5)
  - [x] 2.1 Create `services/bff/src/bff/api/schemas/farmer_schemas.py` with:
    - `FarmerSummary`: id, name, primary_percentage_30d, tier, trend
    - `FarmerListResponse`: data (list[FarmerSummary]), pagination, meta
    - `FarmerDetailResponse`: farmer profile + FarmerPerformance
  - [x] 2.2 Add tier enum: `tier_1`, `tier_2`, `tier_3`, `below_tier_3`
  - [x] 2.3 Export from `schemas/__init__.py`

- [x] **Task 3: Create Farmer Transformer** (AC: #5)
  - [x] 3.1 Create `services/bff/src/bff/transformers/farmer_transformer.py`
  - [x] 3.2 Implement `to_summary(farmer, performance, thresholds)` method:
    - Compute tier from `primary_percentage_30d` vs thresholds
    - Map TrendDirection to string
  - [x] 3.3 Implement `to_detail(farmer, performance, thresholds)` method
  - [x] 3.4 Add tier computation logic

- [x] **Task 4: Create Farmer Service** (AC: #1, #2, #4)
  - [x] 4.1 Create `services/bff/src/bff/services/farmer_service.py`
  - [x] 4.2 Implement `list_farmers(factory_id, page_size, page_token)`:
    - Get factory (for thresholds) via PlantationClient
    - Get farmers list (paginated) via PlantationClient
    - Parallel enrich with performance using `_parallel_map()`
    - Transform each farmer using FarmerTransformer
  - [x] 4.3 Implement `get_farmer(farmer_id)`:
    - Get farmer via PlantationClient
    - Get collection point to find factory_id
    - Get factory thresholds
    - Get farmer performance summary
    - Transform using FarmerTransformer
  - [x] 4.4 Handle errors using existing ApiError factory methods

- [x] **Task 5: Create Farmer Routes** (AC: #1, #2, #3)
  - [x] 5.1 Create `services/bff/src/bff/api/routes/farmers.py` with APIRouter
  - [x] 5.2 Implement `GET /api/farmers`:
    - Query params: `factory_id` (required), `page_size` (default 50), `page_token` (optional)
    - Validate factory_id against user's token claims
    - Delegate to FarmerService.list_farmers()
    - Return `FarmerListResponse`
  - [x] 5.3 Implement `GET /api/farmers/{farmer_id}`:
    - Path param: `farmer_id`
    - Delegate to FarmerService.get_farmer()
    - Return `FarmerDetailResponse`
  - [x] 5.4 Add `require_permission("farmers:read")` to all handlers
  - [x] 5.5 Use try/except to catch client exceptions and convert to HTTPException

- [x] **Task 6: Register Routes in Main App** (AC: #1, #2)
  - [x] 6.1 Update `services/bff/src/bff/api/routes/__init__.py` to export farmer_router
  - [x] 6.2 Update `services/bff/src/bff/main.py`:
    - Import and register farmer_router
  - [ ] 6.3 Verify OpenAPI docs at `/docs` show both endpoints

- [x] **Task 7: Unit Tests** (AC: #6)
  - [x] 7.1 Create `tests/unit/bff/test_farmer_transformer.py`:
    - Test tier computation for all boundary conditions (10 tests)
    - Test to_summary() with various performance data (3 tests)
    - Test to_detail() response structure (2 tests)
  - [x] 7.2 Create `tests/unit/bff/test_farmer_service.py`:
    - Mock PlantationClient
    - Test list_farmers with pagination
    - Test bounded concurrency
    - Test error handling (9 tests)
  - [x] 7.3 Create `tests/unit/bff/test_farmer_routes.py`:
    - Use FastAPI TestClient with mocked FarmerService
    - Test GET /api/farmers with valid factory_id
    - Test GET /api/farmers without factory_id (422)
    - Test GET /api/farmers/{id} success
    - Test GET /api/farmers/{id} not found (404)
    - Test factory access denied (403) (19 tests)

- [x] **Task 8: E2E Integration Tests** (AC: #7)
  - [x] 8.1 Update BFF docker-compose service if needed
  - [x] 8.2 Create `tests/e2e/scenarios/test_30_bff_farmer_api.py`:
    - Test GET /api/farmers?factory_id=FAC-E2E-001
    - Test GET /api/farmers/FRM-E2E-001
    - Verify response schemas match expectations

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.5.4b: BFF API Routes"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-5-4b-bff-api-routes
  ```

**Branch name:** `story/0-5-4b-bff-api-routes`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/0-5-4b-bff-api-routes`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.5.4b: BFF API Routes" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/0-5-4b-bff-api-routes`

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
196 passed in 5.47s
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build

# Wait for services, then run tests
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v

# Tear down
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```
**Output:**
```
tests/e2e/scenarios/test_30_bff_farmer_api.py::TestBFFHealth::test_bff_health PASSED
tests/e2e/scenarios/test_30_bff_farmer_api.py::TestBFFHealth::test_bff_ready PASSED
tests/e2e/scenarios/test_30_bff_farmer_api.py::TestListFarmersEndpoint::test_list_farmers_for_factory PASSED
tests/e2e/scenarios/test_30_bff_farmer_api.py::TestListFarmersEndpoint::test_list_farmers_tier_computation PASSED
tests/e2e/scenarios/test_30_bff_farmer_api.py::TestListFarmersEndpoint::test_list_farmers_trend_indicator PASSED
tests/e2e/scenarios/test_30_bff_farmer_api.py::TestListFarmersEndpoint::test_list_farmers_pagination_structure PASSED
tests/e2e/scenarios/test_30_bff_farmer_api.py::TestListFarmersEndpoint::test_list_farmers_different_factory PASSED
tests/e2e/scenarios/test_30_bff_farmer_api.py::TestGetFarmerEndpoint::test_get_farmer_detail PASSED
tests/e2e/scenarios/test_30_bff_farmer_api.py::TestGetFarmerEndpoint::test_get_farmer_performance_data PASSED
tests/e2e/scenarios/test_30_bff_farmer_api.py::TestGetFarmerEndpoint::test_get_farmer_tier_detail PASSED
tests/e2e/scenarios/test_30_bff_farmer_api.py::TestGetFarmerEndpoint::test_get_farmer_with_no_deliveries_today PASSED
tests/e2e/scenarios/test_30_bff_farmer_api.py::TestGetFarmerEndpoint::test_get_farmer_not_found PASSED
tests/e2e/scenarios/test_30_bff_farmer_api.py::TestBFFAuthentication::test_factory_manager_can_access_assigned_factory PASSED
tests/e2e/scenarios/test_30_bff_farmer_api.py::TestBFFAuthentication::test_factory_manager_cannot_access_other_factory PASSED
tests/e2e/scenarios/test_30_bff_farmer_api.py::TestBFFAuthentication::test_platform_admin_can_access_any_factory PASSED
tests/e2e/scenarios/test_30_bff_farmer_api.py::TestBFFIntegration::test_bff_fetches_from_plantation_model PASSED
tests/e2e/scenarios/test_30_bff_farmer_api.py::TestBFFIntegration::test_bff_handles_multiple_collection_points PASSED

============================== 17 passed in 1.84s ==============================
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
git push origin story/0-5-4b-bff-api-routes

# Wait ~30s, then check CI status
gh run list --branch story/0-5-4b-bff-api-routes --limit 3
```
**CI Run ID:** _______________
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Production Code Changes (if any)

If you modified ANY production code (`services/`, `mcp-servers/`, `libs/`), document each change here:

| File:Lines | What Changed | Why (with evidence) | Type |
|------------|--------------|---------------------|------|
| services/bff/src/bff/api/routes/farmers.py:66-67,152-154 | Added E2E test patterns to factory_id and farmer_id validation regex | Patterns `FAC-E2E-XXX` and `FRM-E2E-XXX` are used in E2E seed data, production patterns preserved | Test support |
| services/bff/src/bff/api/routes/farmers.py:28-40 | Added PLANTATION_GRPC_HOST env var support in get_farmer_service() | Direct gRPC connection required for E2E tests (DAPR mDNS doesn't work in Docker namespaces) | Test support |
| libs/fp-common/pyproject.toml:13 | Added motor dependency | BFF imports from fp_common which uses motor for DLQRepository | Fix import |

---

## Dev Notes

### Scope Clarification (CRITICAL)

**This story implements ONLY 2 endpoints:**
1. `GET /api/farmers` - Farmer list with quality summaries
2. `GET /api/farmers/{farmer_id}` - Farmer detail with performance

**Out of scope (deferred to future stories):**
- All other Plantation Model endpoints (factories, collection-points, regions)
- Dashboard endpoints
- Quality events endpoints
- Write operations (POST/PUT/DELETE)

Reference: ADR-012 Decision 3 - "Reduce Story 0.5.4 to minimum APIs needed to validate BFF pattern"

### Architecture Layers (ADR-012 Decision 1)

```
┌─────────────────────────────────────────────────────────────┐
│ Route Layer (farmers.py)                                     │
│ - HTTP handling, auth decorator, request validation          │
│ - Delegates to FarmerService                                 │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Service Layer (farmer_service.py)                            │
│ - Orchestrates PlantationClient calls                        │
│ - Sequential: Get factory → Get farmers                      │
│ - Parallel: Enrich with performance (bounded by Semaphore)   │
│ - Uses FarmerTransformer for API schema conversion           │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Transformer Layer (farmer_transformer.py)                    │
│ - Domain model → API schema conversion                       │
│ - Tier computation from factory thresholds                   │
│ - Returns FarmerSummary, FarmerDetailResponse                │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Client Layer (plantation_client.py) - EXISTING               │
│ - gRPC calls to Plantation Model via DAPR                    │
│ - Returns fp_common domain models                            │
└─────────────────────────────────────────────────────────────┘
```

### Tier Computation Logic (ADR-012 Decision 2b)

```python
# Factory-configurable thresholds (from Factory.quality_thresholds)
# Default: tier_1=85%, tier_2=70%, tier_3=50%

def compute_tier(primary_percentage_30d: float, thresholds: QualityThresholds) -> str:
    if primary_percentage_30d >= thresholds.tier_1:
        return "tier_1"
    elif primary_percentage_30d >= thresholds.tier_2:
        return "tier_2"
    elif primary_percentage_30d >= thresholds.tier_3:
        return "tier_3"
    else:
        return "below_tier_3"
```

### Bounded Concurrency Pattern (ADR-012 Decision 1)

```python
# In BaseService
async def _parallel_map(self, items: list[T], func: Callable, max_concurrent: int = 5) -> list[R]:
    """Execute func on each item with bounded concurrency."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def bounded_call(item: T) -> R:
        async with semaphore:
            return await func(item)

    return await asyncio.gather(*[bounded_call(item) for item in items])
```

### Error Handling Pattern (Using Existing ApiError)

```python
from fastapi import HTTPException, status
from bff.api.schemas import ApiError
from bff.infrastructure.clients.base import NotFoundError, ServiceUnavailableError

# In route handlers - catch client exceptions and convert to HTTPException
try:
    farmer = await client.get_farmer(farmer_id)
except NotFoundError:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=ApiError.not_found("Farmer", farmer_id).model_dump(),
    )
except ServiceUnavailableError as e:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=ApiError.service_unavailable("Plantation Model").model_dump(),
    )
```

### Files to Create

| Path | Purpose |
|------|---------|
| `services/bff/src/bff/services/__init__.py` | Service package init |
| `services/bff/src/bff/services/base_service.py` | Abstract base with _parallel_map |
| `services/bff/src/bff/services/farmer_service.py` | Farmer list/detail orchestration |
| `services/bff/src/bff/transformers/__init__.py` | Transformer package init |
| `services/bff/src/bff/transformers/farmer_transformer.py` | Domain→API conversion |
| `services/bff/src/bff/api/schemas/farmer_schemas.py` | FarmerSummary, FarmerListResponse, FarmerDetailResponse |
| `services/bff/src/bff/api/routes/farmers.py` | GET /api/farmers, GET /api/farmers/{id} |
| `tests/unit/bff/test_farmer_transformer.py` | Transformer tests |
| `tests/unit/bff/test_farmer_service.py` | Service tests |
| `tests/unit/bff/test_farmer_routes.py` | Route tests |
| `tests/e2e/scenarios/test_30_bff_farmer_api.py` | E2E tests |

### Files to Modify

| Path | Change |
|------|--------|
| `services/bff/src/bff/api/routes/__init__.py` | Export farmer_router |
| `services/bff/src/bff/api/schemas/__init__.py` | Export farmer schemas |
| `services/bff/src/bff/main.py` | Register farmer_router with `/api` prefix |

### Anti-Patterns to Avoid

1. **DO NOT** call PlantationClient directly from routes - use FarmerService
2. **DO NOT** expose fp_common domain models in API responses - use API schemas
3. **DO NOT** create unlimited parallel calls - use bounded concurrency (Semaphore)
4. **DO NOT** implement more than 2 endpoints - scope is farmer list + detail only
5. **DO NOT** create new exception classes - use existing `ApiError` factory methods with `HTTPException`
6. **DO NOT** hardcode quality thresholds - fetch from Factory entity

### Dependencies (from Previous Stories)

**From Story 0.5.4a:**
- `bff.api.schemas.responses`: ApiResponse, PaginatedResponse, ApiError
- `bff.api.schemas.responses.PaginationMeta`: Pagination metadata

**From Story 0.5.3:**
- `bff.api.middleware.auth`: @require_auth decorator
- `bff.api.schemas.auth.TokenClaims`: factory_ids list

**From Story 0.5.1b:**
- `bff.infrastructure.clients.plantation_client.PlantationClient`:
  - `get_farmer(farmer_id)` → Farmer
  - `list_farmers(region_id, cp_id, page_size, page_token)` → PaginatedResponse[Farmer]
  - `get_farmer_summary(farmer_id)` → FarmerPerformance
  - `get_factory(factory_id)` → Factory

### References

- [Source: _bmad-output/architecture/adr/ADR-012-bff-service-composition-api-design.md]
- [Source: _bmad-output/epics/epic-0-5-frontend.md#Story-0.5.4b]
- [Source: _bmad-output/sprint-artifacts/0-5-4a-bff-client-response-wrappers.md]
- [Source: services/bff/src/bff/infrastructure/clients/plantation_client.py]

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
