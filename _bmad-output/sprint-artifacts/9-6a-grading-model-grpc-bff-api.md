# Story 9.6a: Grading Model gRPC + BFF API

**Status:** ready-for-dev
**GitHub Issue:** <!-- Auto-created by dev-story workflow -->

## Story

As a **platform administrator**,
I want to view available grading models, retrieve their details, and assign them to factories through the Admin Portal API,
so that factories can be configured with the appropriate quality grading standards for their operations.

## Acceptance Criteria

### AC 9.6a.1: ListGradingModels gRPC Endpoint

**Given** the PlantationService is running
**When** a client calls `ListGradingModels` RPC with optional filters
**Then** the service returns a paginated list of grading models
**And** filters are applied: `crop_type`, `market`, `grading_type`, `is_active`
**And** pagination is supported via `page_size` and `page_token`
**And** results include `total_count` for UI pagination display

### AC 9.6a.2: ListGradingModels Proto Messages

**Given** the plantation.proto file
**When** ListGradingModels RPC is defined
**Then** `ListGradingModelsRequest` includes:
  - `crop_type` (optional filter)
  - `market` (optional filter)
  - `grading_type` (optional filter - enum GradingType)
  - `page_size` (int32, max 100)
  - `page_token` (string, opaque cursor)
**And** `ListGradingModelsResponse` includes:
  - `grading_models` (repeated GradingModel)
  - `next_page_token` (string)
  - `total_count` (int32)

### AC 9.6a.3: BFF REST Endpoints for Grading Models

**Given** the BFF admin API
**When** implementing grading model endpoints
**Then** the following routes are available:
  - `GET /api/admin/grading-models` - List grading models with filters
  - `GET /api/admin/grading-models/{model_id}` - Get single grading model details
  - `POST /api/admin/grading-models/{model_id}/assign` - Assign model to factory

### AC 9.6a.4: Grading Model List API Response

**Given** a `GET /api/admin/grading-models` request
**When** parameters include: `crop_type`, `market`, `page_size`, `page_token`
**Then** response returns JSON with:
  - `data`: Array of `GradingModelSummary` objects
  - `pagination`: `{ page_size, page_token, next_page_token, total_count }`
**And** each summary includes: `model_id`, `model_version`, `crop_name`, `market_name`, `grading_type`, `grade_count`, `factory_count`

### AC 9.6a.5: Grading Model Detail API Response

**Given** a `GET /api/admin/grading-models/{model_id}` request
**When** the grading model exists
**Then** response returns the full `GradingModelDetail`:
  - Identity: `model_id`, `model_version`, `regulatory_authority`
  - Configuration: `crops_name`, `market_name`, `grading_type`
  - Attributes: Full attribute definitions with classes
  - Grade rules: Reject conditions and conditional rules
  - Grade labels: Display labels for each grade
  - Deployment: `active_at_factory` list with factory names
  - Timestamps: `created_at`, `updated_at`

### AC 9.6a.6: Assign Grading Model to Factory

**Given** a `POST /api/admin/grading-models/{model_id}/assign` request
**When** the body contains `{ factory_id: string }`
**Then** the grading model is assigned to the specified factory
**And** the factory's previous grading model (if any) is unassigned
**And** the response returns the updated `GradingModelDetail`
**And** a 404 is returned if model_id or factory_id doesn't exist
**And** a 409 is returned if factory already has this model assigned

### AC 9.6a.7: Error Handling

**Given** any grading model API request
**When** an error occurs
**Then**:
- 401: Authentication required
- 403: Insufficient permissions (non-admin user)
- 404: Grading model or factory not found
- 422: Invalid request parameters
- 503: Plantation service unavailable

---

## Tasks / Subtasks

### Task 1: Proto Definition Updates (AC: 1, 2)

Add ListGradingModels RPC and messages to plantation.proto:

- [ ] 1.1 Add `ListGradingModelsRequest` message to `proto/plantation/v1/plantation.proto`:
  ```protobuf
  message ListGradingModelsRequest {
    string crop_type = 1;       // Optional filter
    string market = 2;          // Optional filter
    GradingType grading_type = 3; // Optional filter
    int32 page_size = 4;        // Max 100, default 50
    string page_token = 5;      // Opaque pagination cursor
  }
  ```
- [ ] 1.2 Add `ListGradingModelsResponse` message:
  ```protobuf
  message ListGradingModelsResponse {
    repeated GradingModel grading_models = 1;
    string next_page_token = 2;
    int32 total_count = 3;
  }
  ```
- [ ] 1.3 Add `ListGradingModels` RPC to PlantationService (after line 56):
  ```protobuf
  rpc ListGradingModels(ListGradingModelsRequest) returns (ListGradingModelsResponse);
  ```
- [ ] 1.4 Run `make proto` to regenerate Python stubs
- [ ] 1.5 Verify generated files in `libs/fp-proto/src/farmer_power/plantation/v1/`

### Task 2: Pydantic-Proto Bidirectional Converters in fp-common (AC: 1, 4, 5)

Add grading model converters following the established pattern in `libs/fp-common/fp_common/converters/`:

**Both directions needed:**
- **Proto → Pydantic** (`_from_proto`): Used by BFF gRPC client to convert responses into Pydantic models
- **Pydantic → Proto** (`_to_proto`): Used by Plantation gRPC server to build proto responses

- [ ] 2.1 Add converters to `libs/fp-common/fp_common/converters/plantation_converters.py`:
  ```python
  # Proto → Pydantic (for gRPC CLIENT in BFF)
  def grading_model_from_proto(proto: plantation_pb2.GradingModel) -> GradingModel:
      """Convert GradingModel proto message to Pydantic model.
      Used by: BFF PlantationClient to return typed Pydantic models.
      """
      ...

  def grading_attribute_from_proto(proto: plantation_pb2.GradingAttribute) -> GradingAttribute:
      """Convert GradingAttribute proto to Pydantic."""
      ...

  def grade_rules_from_proto(proto: plantation_pb2.GradeRules) -> GradeRules:
      """Convert GradeRules proto to Pydantic."""
      ...

  # Pydantic → Proto (for gRPC SERVER in Plantation)
  def grading_model_to_proto(model: GradingModel) -> plantation_pb2.GradingModel:
      """Convert GradingModel Pydantic model to proto message.
      Used by: Plantation gRPC service to build ListGradingModelsResponse.
      """
      ...

  def grading_attribute_to_proto(attr: GradingAttribute) -> plantation_pb2.GradingAttribute:
      """Convert GradingAttribute Pydantic to proto."""
      ...

  def grade_rules_to_proto(rules: GradeRules) -> plantation_pb2.GradeRules:
      """Convert GradeRules Pydantic to proto."""
      ...
  ```
- [ ] 2.2 Ensure GradingModel Pydantic model exists in `libs/fp-common/fp_common/models/grading_model.py`
- [ ] 2.3 Export ALL converters in `libs/fp-common/fp_common/converters/__init__.py`
- [ ] 2.4 Follow existing patterns:
  - Use `_proto_enum_to_pydantic()` for GradingType enum (Proto → Pydantic)
  - Use `_pydantic_enum_to_proto()` or manual mapping for GradingType (Pydantic → Proto)
  - Use `_timestamp_to_datetime()` for created_at/updated_at (Proto → Pydantic)
  - Use `_datetime_to_timestamp()` for created_at/updated_at (Pydantic → Proto)
  - Handle optional fields with defaults

### Task 3: Plantation Service - ListGradingModels Handler (AC: 1)

Implement the gRPC handler in plantation-model service:

- [ ] 3.1 Add `list_grading_models` method to `GradingModelRepository` in `services/plantation-model/src/plantation_model/repositories/grading_model_repository.py`:
  - Accept filters: `crop_type`, `market`, `grading_type`
  - Implement pagination with `page_size` and `page_token`
  - Return `(models: list[GradingModel], next_token: str, total: int)`
- [ ] 3.2 Add `ListGradingModels` handler to `PlantationServicer` in `services/plantation-model/src/plantation_model/grpc_server/plantation_service.py`:
  ```python
  from fp_common.converters import grading_model_to_proto

  async def ListGradingModels(
      self, request: plantation_pb2.ListGradingModelsRequest, context
  ) -> plantation_pb2.ListGradingModelsResponse:
      models, next_token, total = await self._grading_model_repo.list_grading_models(
          crop_type=request.crop_type or None,
          market=request.market or None,
          grading_type=request.grading_type if request.grading_type else None,
          page_size=request.page_size or 50,
          page_token=request.page_token or None,
      )
      return plantation_pb2.ListGradingModelsResponse(
          grading_models=[grading_model_to_proto(m) for m in models],  # Pydantic → Proto
          next_page_token=next_token,
          total_count=total,
      )
  ```
- [ ] 3.3 **IMPORTANT:** Replace existing local `_grading_model_to_proto()` helper with import from fp-common to maintain single source of truth
- [ ] 3.4 Update other grading model handlers (CreateGradingModel, GetGradingModel, etc.) to use fp-common converters

### Task 4: PlantationClient - Grading Model Methods (AC: 3, 4, 5, 6)

Add gRPC client methods for grading model operations using fp-common converters:

- [ ] 4.1 Add to `services/bff/src/bff/infrastructure/clients/plantation_client.py`:
  ```python
  from fp_common.converters import grading_model_from_proto

  @grpc_retry(max_retries=3)
  async def list_grading_models(
      self,
      crop_type: str | None = None,
      market: str | None = None,
      grading_type: str | None = None,
      page_size: int = 50,
      page_token: str | None = None,
  ) -> tuple[list[GradingModel], str, int]:
      """Returns (models as Pydantic, next_page_token, total_count)."""
      request = plantation_pb2.ListGradingModelsRequest(...)
      response = await self._stub.ListGradingModels(request, metadata=self._metadata)
      models = [grading_model_from_proto(gm) for gm in response.grading_models]
      return models, response.next_page_token, response.total_count

  @grpc_retry(max_retries=3)
  async def get_grading_model(self, model_id: str) -> GradingModel:
      """Returns Pydantic GradingModel (NOT proto)."""
      request = plantation_pb2.GetGradingModelRequest(model_id=model_id)
      response = await self._stub.GetGradingModel(request, metadata=self._metadata)
      return grading_model_from_proto(response)

  @grpc_retry(max_retries=3)
  async def assign_grading_model_to_factory(
      self, model_id: str, factory_id: str
  ) -> GradingModel:
      """Returns Pydantic GradingModel (NOT proto)."""
      request = plantation_pb2.AssignGradingModelToFactoryRequest(...)
      response = await self._stub.AssignGradingModelToFactory(request, metadata=self._metadata)
      return grading_model_from_proto(response)
  ```
- [ ] 4.2 Follow existing pattern: BFF clients return **Pydantic models**, NOT proto messages (ADR-004)
- [ ] 4.3 Add required imports from `fp_common.converters` and `fp_common.models`

### Task 5: BFF Schemas for Grading Models (AC: 4, 5)

Create typed schemas for REST API responses:

- [ ] 5.1 Create `services/bff/src/bff/api/schemas/admin/grading_model_schemas.py`:
  ```python
  class GradingAttributeResponse(BaseModel):
      num_classes: int
      classes: list[str]

  class GradeRulesResponse(BaseModel):
      reject_conditions: dict[str, list[str]]
      conditional_reject: list[ConditionalRejectResponse]

  class GradingModelSummary(BaseModel):
      model_id: str
      model_version: str
      crops_name: str
      market_name: str
      grading_type: str  # "binary", "ternary", "multi_level"
      grade_count: int
      factory_count: int

  class GradingModelDetail(BaseModel):
      model_id: str
      model_version: str
      regulatory_authority: str | None
      crops_name: str
      market_name: str
      grading_type: str
      attributes: dict[str, GradingAttributeResponse]
      grade_rules: GradeRulesResponse
      grade_labels: dict[str, str]
      active_at_factory: list[FactoryReference]
      created_at: datetime
      updated_at: datetime

  class GradingModelListResponse(BaseModel):
      data: list[GradingModelSummary]
      pagination: PaginationMeta

  class AssignGradingModelRequest(BaseModel):
      factory_id: str
  ```
- [ ] 5.2 Add exports to `services/bff/src/bff/api/schemas/admin/__init__.py`

### Task 6: BFF Transformer for Grading Models (AC: 4, 5)

Create proto-to-schema conversion layer:

- [ ] 6.1 Create `services/bff/src/bff/transformers/admin/grading_model_transformer.py`:
  ```python
  def to_summary(model: GradingModel) -> GradingModelSummary
  def to_detail(model: GradingModel, factory_names: dict[str, str]) -> GradingModelDetail
  def grading_type_to_string(grading_type: GradingType) -> str
  ```
- [ ] 6.2 **NOTE:** Transformer receives Pydantic models from PlantationClient (NOT proto)
- [ ] 6.3 Add exports to `services/bff/src/bff/transformers/admin/__init__.py`

### Task 7: BFF Admin Service for Grading Models (AC: 3, 4, 5, 6, 7)

Create the service layer for grading model operations:

- [ ] 7.1 Create `services/bff/src/bff/services/admin/grading_model_service.py`:
  ```python
  class AdminGradingModelService:
      def __init__(self, plantation_client: PlantationClient):
          self._plantation = plantation_client

      async def list_grading_models(
          self,
          crop_type: str | None,
          market: str | None,
          page_size: int,
          page_token: str | None,
      ) -> GradingModelListResponse:
          ...

      async def get_grading_model(self, model_id: str) -> GradingModelDetail:
          ...

      async def assign_to_factory(
          self, model_id: str, factory_id: str
      ) -> GradingModelDetail:
          ...
  ```
- [ ] 7.2 Add exports to `services/bff/src/bff/services/admin/__init__.py`

### Task 8: BFF Admin Routes for Grading Models (AC: 3, 4, 5, 6, 7)

Create REST API endpoints:

- [ ] 8.1 Create `services/bff/src/bff/api/routes/admin/grading_models.py`:
  ```python
  router = APIRouter(prefix="/grading-models", tags=["admin-grading-models"])

  @router.get("", response_model=GradingModelListResponse)
  async def list_grading_models(
      crop_type: str | None = None,
      market: str | None = None,
      page_size: int = Query(default=50, le=100),
      page_token: str | None = None,
      service: AdminGradingModelService = Depends(get_grading_model_service),
  ) -> GradingModelListResponse:
      ...

  @router.get("/{model_id}", response_model=GradingModelDetail)
  async def get_grading_model(
      model_id: str,
      service: AdminGradingModelService = Depends(get_grading_model_service),
  ) -> GradingModelDetail:
      ...

  @router.post("/{model_id}/assign", response_model=GradingModelDetail)
  async def assign_grading_model(
      model_id: str,
      request: AssignGradingModelRequest,
      service: AdminGradingModelService = Depends(get_grading_model_service),
  ) -> GradingModelDetail:
      ...
  ```
- [ ] 8.2 Register router in `services/bff/src/bff/api/routes/admin/__init__.py`
- [ ] 8.3 Add dependency injection for `get_grading_model_service`

### Task 9: Unit Tests (AC: 1-7)

Create unit tests for all components:

- [ ] 9.1 Create `tests/unit/plantation_model/repositories/test_grading_model_repository.py`:
  - Test `list_all` with filters
  - Test pagination
  - Test empty results
- [ ] 9.2 Create `tests/unit/bff/services/admin/test_grading_model_service.py`:
  - Test list with filters
  - Test get model detail
  - Test assign to factory
  - Test error cases (404, 409)
- [ ] 9.3 Create `tests/unit/bff/transformers/admin/test_grading_model_transformer.py`:
  - Test to_summary conversion
  - Test to_detail conversion
  - Test grading_type enum conversion
- [ ] 9.4 Create `tests/unit/fp_common/converters/test_grading_model_converters.py`:
  - Test `grading_model_from_proto` conversion
  - Test `grading_model_to_proto` conversion
  - Test enum conversion (GradingType)
  - Test nested object conversion (GradingAttribute, GradeRules)

### Task 10: Create New E2E Tests (AC: 1-7)

Create E2E test file for grading model API:

- [ ] 10.1 Create `tests/e2e/scenarios/test_36_admin_grading_models.py`:
  ```python
  class TestGradingModelList:
      def test_list_grading_models_returns_seed_data(self)
      def test_list_grading_models_filter_by_crop_type(self)
      def test_list_grading_models_filter_by_market(self)
      def test_list_grading_models_pagination(self)

  class TestGradingModelDetail:
      def test_get_grading_model_returns_full_detail(self)
      def test_get_grading_model_includes_attributes(self)
      def test_get_grading_model_not_found_returns_404(self)

  class TestGradingModelAssignment:
      def test_assign_model_to_factory(self)
      def test_assign_model_to_nonexistent_factory_returns_404(self)
      def test_assign_nonexistent_model_returns_404(self)

  class TestGradingModelAuth:
      def test_non_admin_cannot_access_grading_models(self)
  ```

---

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 9.6a: Grading Model gRPC + BFF API"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/9-6a-grading-model-grpc-bff-api
  ```

**Branch name:** `story/9-6a-grading-model-grpc-bff-api`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/9-6a-grading-model-grpc-bff-api`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 9.6a: Grading Model gRPC + BFF API" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review`)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/9-6a-grading-model-grpc-bff-api`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
pytest tests/unit/plantation_model/repositories/test_grading_model_repository.py tests/unit/bff/services/admin/test_grading_model_service.py tests/unit/bff/transformers/admin/test_grading_model_transformer.py -v
```
**Output:**
```
(paste test summary here)
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure
bash scripts/e2e-up.sh --build

# Run grading model E2E tests
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/test_36_admin_grading_models.py -v

# Tear down
bash scripts/e2e-up.sh --down
```
**Output:**
```
(paste E2E test output here)
```
**E2E passed:** [ ] Yes / [ ] No

### 3. Lint Check
```bash
ruff check . && ruff format --check .
```
**Lint passed:** [ ] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

```bash
# Push to story branch
git push origin story/9-6a-grading-model-grpc-bff-api

# Wait ~30s, then check CI status
gh run list --branch story/9-6a-grading-model-grpc-bff-api --limit 3
```
**CI Run ID:** _______________
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### Existing Code to Extend (NOT Reinvent)

**Proto Messages Already Exist:**
- `GradingModel` message (lines 641-654 in plantation.proto)
- `GradingType` enum (lines 600-605)
- `GradingAttribute` message (lines 616-619)
- `GradeRules` message (lines 630-633)
- `ConditionalReject` message (lines 622-627)

**gRPC Methods Already Exist:**
- `CreateGradingModel` (line 53)
- `GetGradingModel` (line 54)
- `GetFactoryGradingModel` (line 55)
- `AssignGradingModelToFactory` (line 56)

**Repository Methods Already Exist in `grading_model_repository.py`:**
- `create(entity)` - Create grading model
- `get_by_id(model_id)` - Get by ID
- `get_by_id_and_version(model_id, model_version)` - Get specific version
- `get_by_factory(factory_id)` - Get model assigned to factory
- `add_factory_assignment(model_id, factory_id)` - Assign to factory
- `list_all(page_size, page_token, filters)` - Paginated list (extend this!)

**gRPC Handlers Already Exist in `plantation_service.py`:**
- `_grading_model_to_proto(model)` - Converter (line 1054)
- `CreateGradingModel()` handler (line 1099)
- `GetGradingModel()` handler (line 1166)
- `GetFactoryGradingModel()` handler (line 1187)
- `AssignGradingModelToFactory()` handler (line 1208)

### API Patterns to Follow

**BFF Admin Routes Pattern (from `farmers.py`):**
```python
router = APIRouter(prefix="/farmers", tags=["admin-farmers"])

@router.get("", response_model=FarmerListResponse)
async def list_farmers(
    region_id: str | None = None,
    page_size: int = Query(default=50, le=100),
    page_token: str | None = None,
    service: AdminFarmerService = Depends(get_farmer_service),
):
    return await service.list_farmers(region_id, page_size, page_token)
```

**Transformer Pattern (from `factory_transformer.py`):**
```python
def to_summary(proto: plantation_pb2.Factory) -> FactorySummary:
    return FactorySummary(
        id=proto.factory_id,
        name=proto.name,
        # ... map fields
    )
```

**PlantationClient Pattern (existing client methods):**
```python
@grpc_retry(max_retries=3)
async def list_factories(
    self, region_id: str | None = None, page_size: int = 50, page_token: str | None = None
) -> ListFactoriesResponse:
    request = plantation_pb2.ListFactoriesRequest(
        region_id=region_id or "",
        page_size=page_size,
        page_token=page_token or "",
    )
    return await self._stub.ListFactories(request, metadata=self._metadata)
```

### File Locations

**Proto:**
- `proto/plantation/v1/plantation.proto` - Add ListGradingModels RPC + messages

**Plantation Service:**
- `services/plantation-model/src/plantation_model/repositories/grading_model_repository.py` - Extend `list_all` if needed
- `services/plantation-model/src/plantation_model/grpc_server/plantation_service.py` - Add `ListGradingModels` handler

**BFF:**
- `services/bff/src/bff/api/schemas/admin/grading_model_schemas.py` - NEW
- `services/bff/src/bff/transformers/admin/grading_model_transformer.py` - NEW
- `services/bff/src/bff/services/admin/grading_model_service.py` - NEW
- `services/bff/src/bff/api/routes/admin/grading_models.py` - NEW
- `services/bff/src/bff/infrastructure/clients/plantation_client.py` - ADD methods

**Tests:**
- `tests/e2e/infrastructure/seed/plantation_model_grading_models.json` - NEW
- `tests/e2e/scenarios/test_36_admin_grading_models.py` - NEW
- `tests/unit/plantation_model/repositories/test_grading_model_repository.py` - NEW
- `tests/unit/bff/services/admin/test_grading_model_service.py` - NEW

### Technical Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.12+ | Backend services |
| gRPC | 1.60+ | Service communication |
| FastAPI | 0.109+ | REST API framework |
| Pydantic | 2.0+ | Schema validation |
| MongoDB | 7.0 | Data storage |
| pytest | 8.0+ | Testing framework |

### Proto Regeneration

After modifying `plantation.proto`, run:
```bash
make proto
```

This regenerates:
- `libs/fp-proto/src/farmer_power/plantation/v1/plantation_pb2.py`
- `libs/fp-proto/src/farmer_power/plantation/v1/plantation_pb2_grpc.py`

### GradingType Enum Mapping

| Proto Value | Python String |
|-------------|---------------|
| `GRADING_TYPE_UNSPECIFIED` | `"unspecified"` |
| `GRADING_TYPE_BINARY` | `"binary"` |
| `GRADING_TYPE_TERNARY` | `"ternary"` |
| `GRADING_TYPE_MULTI_LEVEL` | `"multi_level"` |

### Previous Story Intelligence (Story 9.5)

**Key Learnings:**
1. Use `FarmerListResponse` pattern for pagination (data + pagination meta)
2. Transformer pattern: separate `to_summary()` and `to_detail()` methods
3. Service layer handles business logic, routes just call service
4. Use Pydantic `model_dump()` not deprecated `dict()`
5. Always include factory names when showing factory references (resolve IDs)

**Files Modified Pattern:**
- Create schemas first (types)
- Then transformer (conversion)
- Then service (business logic)
- Then routes (HTTP interface)
- Then tests (validation)

### References

- [Source: proto/plantation/v1/plantation.proto:53-56] - Existing grading model RPCs
- [Source: proto/plantation/v1/plantation.proto:600-654] - GradingModel messages
- [Source: services/plantation-model/src/plantation_model/repositories/grading_model_repository.py] - Existing repository
- [Source: services/plantation-model/src/plantation_model/grpc_server/plantation_service.py:1054-1241] - Existing handlers
- [Source: services/bff/src/bff/api/routes/admin/farmers.py] - Admin routes pattern
- [Source: services/bff/src/bff/transformers/admin/factory_transformer.py] - Transformer pattern
- [Source: _bmad-output/architecture/plantation-model-architecture.md] - Domain architecture
- [Source: _bmad-output/epics/epic-9-admin-portal/epic-summary.md:12] - Story definition
- [Source: _bmad-output/project-context.md] - Project rules and patterns

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

(none yet)

### Completion Notes List

(to be filled during implementation)

### File List

**Created:**
- (to be filled)

**Modified:**
- (to be filled)
