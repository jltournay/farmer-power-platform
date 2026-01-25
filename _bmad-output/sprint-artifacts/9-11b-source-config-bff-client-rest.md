# Story 9.11b: Source Config gRPC Client + REST API in BFF

**Status:** ready-for-dev
**GitHub Issue:** <!-- Auto-created by dev-story workflow -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **frontend developer**,
I want **REST API endpoints in the BFF that proxy source config data from Collection Model**,
so that **the Admin UI can fetch source configurations via standard REST calls**.

## Use Case Context

**Epic:** 9 - Platform Admin Portal
**Use Case:** UC9.1: View Source Configurations
**Steps Covered:** Step 2 (BFF gRPC client + REST layer)
**Input (from preceding steps):** SourceConfigService gRPC endpoints accessible via DAPR in Collection Model (Story 9.11a)
**Output (for subsequent steps):** REST API endpoints `/api/admin/source-configs` ready for Admin UI consumption (Story 9.11c)
**E2E Verification:** Admin UI (or curl) can call `GET /api/admin/source-configs` and receive paginated JSON response with source config summaries

## Acceptance Criteria

### AC 9.11b.1: SourceConfigClient gRPC Client

**Given** the Collection Model SourceConfigService exists (from Story 9.11a)
**When** I implement `SourceConfigClient` in the BFF
**Then** the client:
- Inherits from `BaseGrpcClient` with `target_app_id="collection-model"`
- Implements `list_source_configs()` returning `PaginatedResponse[SourceConfigSummary]`
- Implements `get_source_config()` returning `SourceConfigDetail`
- Uses `@grpc_retry` decorator on all methods
- Uses `metadata=self._get_metadata()` for DAPR routing
- Converts proto responses to Pydantic domain models (NOT dicts)
- Handles gRPC errors via `_handle_grpc_error()`

### AC 9.11b.2: Pydantic Domain Models

**Given** no existing SourceConfig domain models in fp-common for BFF responses
**When** I create domain models for the BFF client
**Then** I have:
- `SourceConfigSummary` model (source_id, display_name, description, enabled, ingestion_mode, ai_agent_id, updated_at)
- `SourceConfigDetail` model (extends summary with config_json, created_at)
- Models in `libs/fp-common/fp_common/models/source_config_summary.py` (new file)
- Exported in `libs/fp-common/fp_common/models/__init__.py`

### AC 9.11b.3: REST Endpoint - List Source Configs

**Given** the BFF is running with SourceConfigClient
**When** I call `GET /api/admin/source-configs`
**Then** I receive:
- JSON response with `items[]`, `total_count`, `page_size`, `next_page_token`
- Status 200 with paginated SourceConfigSummary records
- Query params supported: `page_size` (default 20, max 100), `page_token`, `enabled_only`, `ingestion_mode`
- Status 401 if not authenticated
- Status 403 if not platform_admin role
- Status 503 if Collection Model service unavailable

### AC 9.11b.4: REST Endpoint - Get Source Config Detail

**Given** a source config exists with source_id "qc-analyzer-result"
**When** I call `GET /api/admin/source-configs/qc-analyzer-result`
**Then** I receive:
- JSON response with full SourceConfigDetail
- `config_json` field containing the complete configuration as JSON string
- Status 200 on success
- Status 404 if source_id not found
- Status 401/403 for auth errors
- Status 503 for service unavailable

### AC 9.11b.5: Unit Tests

**Given** the SourceConfigClient and REST routes
**When** unit tests run
**Then** all tests pass covering:
- `SourceConfigClient.list_source_configs()` with no filters
- `SourceConfigClient.list_source_configs()` with all filter combinations
- `SourceConfigClient.get_source_config()` success case
- `SourceConfigClient.get_source_config()` NOT_FOUND error handling
- REST route `/api/admin/source-configs` list endpoint
- REST route `/api/admin/source-configs/{source_id}` detail endpoint
- Auth middleware (mock authenticated user, reject unauthenticated)
- Error response mapping (gRPC → HTTP status codes)

### AC-E2E (from Use Case)

**Given** the E2E infrastructure is running with Collection Model containing seed source configs
**When** I call `GET /api/admin/source-configs` via the BFF
**Then** the response contains `total_count >= 2` and `items[]` with valid SourceConfigSummary objects

## Tasks / Subtasks

### Task 1: Create Pydantic Domain Models (AC: 2)

- [ ] Create `libs/fp-common/fp_common/models/source_config_summary.py`
- [ ] Define `SourceConfigSummary` Pydantic model:
  ```python
  class SourceConfigSummary(BaseModel):
      source_id: str
      display_name: str
      description: str
      enabled: bool
      ingestion_mode: str  # "blob_trigger" or "scheduled_pull"
      ai_agent_id: str | None = None
      updated_at: datetime | None = None
  ```
- [ ] Define `SourceConfigDetail` Pydantic model:
  ```python
  class SourceConfigDetail(SourceConfigSummary):
      config_json: str  # Full config as JSON string
      created_at: datetime | None = None
  ```
- [ ] Export models in `libs/fp-common/fp_common/models/__init__.py`
- [ ] Run: `ruff check libs/fp-common/ && ruff format libs/fp-common/`

### Task 2: Update Proto-to-Domain Converters (AC: 2)

- [ ] Update `libs/fp-common/fp_common/converters/source_config_converters.py`
- [ ] Change `source_config_summary_from_proto()` to return `SourceConfigSummary` model (not dict)
- [ ] Change `source_config_response_from_proto()` to return `SourceConfigDetail` model (not dict)
- [ ] Ensure converters handle timestamp conversion properly
- [ ] Export updated converters in `libs/fp-common/fp_common/converters/__init__.py`

### Task 3: Implement SourceConfigClient (AC: 1)

- [ ] Create `services/bff/src/bff/infrastructure/clients/source_config_client.py`
- [ ] Inherit from `BaseGrpcClient` with `target_app_id="collection-model"`
- [ ] Implement `list_source_configs()`:
  ```python
  @grpc_retry
  async def list_source_configs(
      self,
      page_size: int = 20,
      page_token: str | None = None,
      enabled_only: bool = False,
      ingestion_mode: str | None = None,
  ) -> PaginatedResponse[SourceConfigSummary]:
      """List source configs with pagination and filters."""
  ```
- [ ] Implement `get_source_config()`:
  ```python
  @grpc_retry
  async def get_source_config(self, source_id: str) -> SourceConfigDetail:
      """Get source config detail by ID."""
  ```
- [ ] Use `SourceConfigServiceStub` from `collection_pb2_grpc`
- [ ] Use converters from `fp_common.converters.source_config_converters`
- [ ] Handle gRPC errors with `_handle_grpc_error()`
- [ ] Export client in `services/bff/src/bff/infrastructure/clients/__init__.py`

### Task 4: Implement REST Routes (AC: 3, 4)

- [ ] Create `services/bff/src/bff/api/routes/admin/source_configs.py`
- [ ] Implement list endpoint:
  ```python
  @router.get(
      "",
      response_model=SourceConfigListResponse,
  )
  async def list_source_configs(
      page_size: int = Query(20, ge=1, le=100),
      page_token: str | None = Query(None),
      enabled_only: bool = Query(False),
      ingestion_mode: str | None = Query(None),
      user: TokenClaims = require_platform_admin(),
      client: SourceConfigClient = Depends(get_source_config_client),
  ) -> SourceConfigListResponse:
  ```
- [ ] Implement detail endpoint:
  ```python
  @router.get(
      "/{source_id}",
      response_model=SourceConfigDetailResponse,
  )
  async def get_source_config(
      source_id: str = Path(...),
      user: TokenClaims = require_platform_admin(),
      client: SourceConfigClient = Depends(get_source_config_client),
  ) -> SourceConfigDetailResponse:
  ```
- [ ] Create response schema models in `services/bff/src/bff/api/schemas/admin/source_configs.py`
- [ ] Register router in `services/bff/src/bff/api/routes/admin/__init__.py`
- [ ] Add router to main app in `services/bff/src/bff/main.py` (if not auto-registered)

### Task 5: Create Response Schema Models (AC: 3, 4)

- [ ] Create `services/bff/src/bff/api/schemas/admin/source_configs.py`:
  ```python
  class SourceConfigSummaryResponse(BaseModel):
      source_id: str
      display_name: str
      description: str
      enabled: bool
      ingestion_mode: str
      ai_agent_id: str | None
      updated_at: str | None  # ISO format

  class SourceConfigListResponse(BaseModel):
      items: list[SourceConfigSummaryResponse]
      total_count: int
      page_size: int
      next_page_token: str | None

  class SourceConfigDetailResponse(SourceConfigSummaryResponse):
      config_json: str
      created_at: str | None  # ISO format
  ```
- [ ] Export schemas in `services/bff/src/bff/api/schemas/admin/__init__.py`

### Task 6: Unit Tests - Client (AC: 5)

- [ ] Create `tests/unit/bff/infrastructure/clients/test_source_config_client.py`
- [ ] Test `list_source_configs()` returns `PaginatedResponse[SourceConfigSummary]`
- [ ] Test `list_source_configs()` with `enabled_only=True`
- [ ] Test `list_source_configs()` with `ingestion_mode="blob_trigger"`
- [ ] Test `list_source_configs()` pagination
- [ ] Test `get_source_config()` returns `SourceConfigDetail`
- [ ] Test `get_source_config()` raises `NotFoundError` when not found
- [ ] Test `get_source_config()` raises `ServiceUnavailableError` on connection failure
- [ ] Mock gRPC stub and proto responses

### Task 7: Unit Tests - Routes (AC: 5)

- [ ] Create `tests/unit/bff/api/routes/admin/test_source_configs.py`
- [ ] Test `GET /api/admin/source-configs` returns 200 with valid response
- [ ] Test `GET /api/admin/source-configs` with query params
- [ ] Test `GET /api/admin/source-configs/{source_id}` returns 200
- [ ] Test `GET /api/admin/source-configs/{source_id}` returns 404 when not found
- [ ] Test auth middleware rejects unauthenticated requests (401)
- [ ] Test auth middleware rejects non-admin users (403)
- [ ] Test 503 response when service unavailable
- [ ] Use `TestClient` and mock `SourceConfigClient`

### Task 8: E2E Test (MANDATORY - DO NOT SKIP)

> **This task is NON-NEGOTIABLE and BLOCKS story completion.**

- [ ] Create `tests/e2e/scenarios/test_13_source_config_bff.py`
- [ ] Test `GET /api/admin/source-configs` via BFF returns source configs from seed data
- [ ] Test `GET /api/admin/source-configs/{source_id}` returns detail with `config_json`
- [ ] Test query filters work correctly
- [ ] Verify response matches schema
- [ ] Run full E2E suite to check for regressions

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 9.11b: Source Config gRPC Client + REST API in BFF"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/9-11b-source-config-bff-client-rest
  ```

**Branch name:** `story/9-11b-source-config-bff-client-rest`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/9-11b-source-config-bff-client-rest`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 9.11b: Source Config gRPC Client + REST API in BFF" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/9-11b-source-config-bff-client-rest`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

> **REGRESSION RULE - NO EXCEPTIONS:**
> - Run the **FULL** test suite, not just tests you think are related to your change.
> - A previously passing test that now fails **IS a regression caused by your change**.
> - **Zero failures** is the only acceptable outcome. Fix all regressions before proceeding.

### 1. Unit Tests
```bash
pytest tests/unit/ -v
```
**Output:**
```
(paste test summary here - e.g., "XX passed in X.XXs")
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure
bash scripts/e2e-up.sh --build

# Pre-flight validation
bash scripts/e2e-preflight.sh

# Run E2E tests
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
git push origin story/9-11b-source-config-bff-client-rest

# Trigger E2E CI workflow
gh workflow run "E2E Tests" --ref story/9-11b-source-config-bff-client-rest

# Wait and check status
sleep 10
gh run list --workflow="E2E Tests" --branch story/9-11b-source-config-bff-client-rest --limit 1
```
**CI Run ID:** _______________
**CI Status:** [ ] Passed / [ ] Failed
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### Architecture Compliance

**This is a BFF layer story.** Connects frontend (future 9.11c) to backend (9.11a).

**Layer Architecture (ADR-019):**
```
Admin UI (future 9.11c) → BFF REST API → SourceConfigClient → Collection Model gRPC
                          ↑ THIS STORY
```

**Pattern to Follow:** ADR-012 BFF Service Composition

### Critical: Follow Existing BFF Patterns

**MUST USE THESE PATTERNS:**

1. **BaseGrpcClient inheritance** - See `services/bff/src/bff/infrastructure/clients/base.py`
2. **`@grpc_retry` decorator** - All methods must have retry logic
3. **DAPR metadata** - `metadata=self._get_metadata()` on all gRPC calls
4. **Pydantic models** - Return domain models, NOT `dict[str, Any]`
5. **PaginatedResponse** - Use `PaginatedResponse.from_client_response()` for list methods
6. **Error handling** - Map gRPC errors to domain exceptions, then to HTTP status codes

### Existing Converters (From Story 9.11a)

The converters already exist in `libs/fp-common/fp_common/converters/source_config_converters.py`:
- `source_config_summary_from_proto()` - Currently returns dict, update to return Pydantic model
- `source_config_response_from_proto()` - Currently returns dict, update to return Pydantic model

**Update these converters to return Pydantic models instead of dicts to follow BFF patterns.**

### gRPC Stub Usage

```python
from fp_proto.collection.v1 import collection_pb2, collection_pb2_grpc

# In SourceConfigClient
stub = await self._get_stub(collection_pb2_grpc.SourceConfigServiceStub)
request = collection_pb2.ListSourceConfigsRequest(
    page_size=page_size,
    page_token=page_token or "",
    enabled_only=enabled_only,
    ingestion_mode=ingestion_mode or "",
)
response = await stub.ListSourceConfigs(request, metadata=self._get_metadata())
```

### REST Route Pattern

```python
from bff.infrastructure.clients import NotFoundError, ServiceUnavailableError
from bff.api.middleware.auth import require_platform_admin
from bff.infrastructure.clients.source_config_client import SourceConfigClient

router = APIRouter(prefix="/source-configs", tags=["admin-source-configs"])

def get_source_config_client() -> SourceConfigClient:
    """Dependency for SourceConfigClient."""
    direct_host = os.environ.get("COLLECTION_GRPC_HOST")
    return SourceConfigClient(direct_host=direct_host)

@router.get("")
async def list_source_configs(...) -> SourceConfigListResponse:
    try:
        result = await client.list_source_configs(...)
        return SourceConfigListResponse(
            items=[SourceConfigSummaryResponse.from_domain(item) for item in result.items],
            total_count=result.total_count,
            page_size=result.page_size,
            next_page_token=result.next_page_token,
        )
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=...) from e
```

### Previous Story Intelligence (9.11a)

**From Story 9.11a completed 2026-01-25:**
- SourceConfigService gRPC implemented in Collection Model
- Proto definitions added to `proto/collection/v1/collection.proto`
- E2E tests pass (11 tests in `test_12_source_config_service.py`)
- Converters created but return dicts (need update to return Pydantic models)

**Key learnings:**
- Use `SourceConfigServiceStub` (not `CollectionServiceStub`) for source config operations
- Page token is skip offset encoded as string
- `config_json` contains full model serialized via `model_dump_json()`
- Empty ai_agent_id returns as empty string, convert to None for API response

### File Structure (Changes)

```
libs/fp-common/fp_common/
├── models/
│   ├── __init__.py                    # MODIFIED - Export new models
│   └── source_config_summary.py       # NEW - SourceConfigSummary, SourceConfigDetail
├── converters/
│   ├── __init__.py                    # MODIFIED - Ensure exports correct
│   └── source_config_converters.py    # MODIFIED - Return Pydantic models not dicts

services/bff/src/bff/
├── infrastructure/clients/
│   ├── __init__.py                    # MODIFIED - Export SourceConfigClient
│   └── source_config_client.py        # NEW - SourceConfigClient
├── api/
│   ├── routes/admin/
│   │   ├── __init__.py                # MODIFIED - Register router
│   │   └── source_configs.py          # NEW - REST endpoints
│   └── schemas/admin/
│       ├── __init__.py                # MODIFIED - Export schemas
│       └── source_configs.py          # NEW - Response schemas

tests/
├── unit/bff/
│   ├── infrastructure/clients/
│   │   └── test_source_config_client.py  # NEW - Client unit tests
│   └── api/routes/admin/
│       └── test_source_configs.py        # NEW - Route unit tests
├── e2e/scenarios/
│   └── test_13_source_config_bff.py      # NEW - E2E tests
```

### Dependencies

- **Depends on:** Story 9.11a (SourceConfigService gRPC in Collection Model) - DONE
- **Blocks:** Story 9.11c (Source Configuration Viewer UI)

### References

- [Source: _bmad-output/architecture/adr/ADR-019-admin-configuration-visibility.md#Decision-4] - BFF layer architecture
- [Source: _bmad-output/architecture/adr/ADR-012-bff-service-composition.md] - BFF patterns
- [Source: services/bff/src/bff/infrastructure/clients/base.py] - BaseGrpcClient pattern
- [Source: services/bff/src/bff/infrastructure/clients/collection_client.py] - Example client implementation
- [Source: services/bff/src/bff/api/routes/admin/grading_models.py] - Example REST route pattern
- [Source: libs/fp-common/fp_common/converters/source_config_converters.py] - Existing converters (need update)
- [Source: _bmad-output/sprint-artifacts/9-11a-source-config-grpc-collection-model.md] - Previous story
- [Source: _bmad-output/project-context.md] - Architecture rules and patterns

---

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
