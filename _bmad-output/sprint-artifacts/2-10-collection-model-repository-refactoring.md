# Story 2.10: Collection Model Repository Pattern Refactoring

**Status:** done
**GitHub Issue:** #35
**Epic:** [Epic 2: Quality Data Ingestion](../epics/epic-2-collection-model.md)

## Story

As a **developer**,
I want Collection Model to use Pydantic models and repository pattern for source configs,
So that type safety catches bugs at development time instead of E2E testing.

## Problem Statement

During Story 0.4.6 (Weather Data Ingestion), multiple production code bugs were discovered that should have been caught by type safety:

1. **DAPR gRPC invocation pattern** - Code used `DaprClient().invoke_method()` (HTTP) for gRPC services
2. **Source config wrapper bug** - Code accessed `config.get("config", {}).get(X)` but Pydantic model has direct fields
3. **Collection MCP hardcoded collection** - Queried wrong collection instead of using `storage.index_collection`
4. **No Pydantic validation** - `SourceConfigService` returns `dict[str, Any]` instead of `SourceConfig` model

**Root Cause:** Collection Model doesn't follow the repository pattern used by Plantation Model. It manipulates raw dicts everywhere despite having a well-defined `SourceConfig` Pydantic model in `fp_common/models/source_config.py`.

**Contrast:**
- **Plantation Model**: `BaseRepository[T]` pattern, returns typed Pydantic models, type-safe access
- **Collection Model**: Raw `dict[str, Any]` everywhere, no validation, runtime errors

## Acceptance Criteria

1. **AC1: BaseRepository in Collection Model** - Given Plantation Model has a working `BaseRepository` pattern, When I check Collection Model, Then it has an equivalent `BaseRepository` class in `infrastructure/repositories/base.py`

2. **AC2: SourceConfigRepository** - Given `SourceConfig` Pydantic model exists in `fp_common`, When source configs are accessed, Then `SourceConfigRepository` returns `SourceConfig` objects (not dicts)

3. **AC3: SourceConfigService Refactor** - Given `SourceConfigService` currently returns `dict[str, Any]`, When refactored, Then all methods return `SourceConfig | None` or `list[SourceConfig]`

4. **AC4: Consumer Migration** - Given 12+ files access source config as dicts, When migration is complete, Then all files use typed attribute access (`config.ingestion.mode` not `config.get("ingestion", {}).get("mode")`)

5. **AC5: Unit Test Coverage** - Given unit tests currently mock with dicts, When updated, Then tests use real Pydantic models and would fail on schema violations

6. **AC6: DAPR Pattern Documentation** - Given DAPR gRPC invocation was misunderstood, When documentation is updated, Then `project-context.md` includes the correct gRPC proxying pattern

## Tasks / Subtasks

- [x] **Task 1: Create BaseRepository in Collection Model** (AC: 1)
  - [x] Copy `BaseRepository` pattern from `services/plantation-model/src/plantation_model/infrastructure/repositories/base.py`
  - [x] Create `services/collection-model/src/collection_model/infrastructure/repositories/base.py`
  - [x] Create `services/collection-model/src/collection_model/infrastructure/repositories/__init__.py`

- [x] **Task 2: Create SourceConfigRepository** (AC: 2)
  - [x] Create `services/collection-model/src/collection_model/infrastructure/repositories/source_config_repository.py`
  - [x] Implement `get_by_source_id(source_id: str) -> SourceConfig | None`
  - [x] Implement `get_all_enabled() -> list[SourceConfig]`
  - [x] Implement `get_by_container(container: str) -> SourceConfig | None`
  - [x] Use `SourceConfig.model_validate()` for all returns

- [x] **Task 3: Refactor SourceConfigService** (AC: 3)
  - [x] Inject `SourceConfigRepository` instead of direct MongoDB access
  - [x] Change `get_all_configs() -> list[SourceConfig]`
  - [x] Change `get_config(source_id) -> SourceConfig | None`
  - [x] Change `get_config_by_container(container) -> SourceConfig | None`
  - [x] Update cache to store `list[SourceConfig]` not `list[dict]`

- [x] **Task 4: Migrate pull_job_handler.py** (AC: 4)
  - [x] Replace `config.get("ingestion", {})` with `config.ingestion`
  - [x] Replace `config.get("transformation", {})` with `config.transformation`
  - [x] Update type hints to use `SourceConfig`

- [x] **Task 5: Migrate content_processor_worker.py** (AC: 4)
  - [x] Replace all dict access with typed attribute access
  - [x] Update method signatures to accept `SourceConfig`

- [x] **Task 6: Migrate processors** (AC: 4)
  - [x] `json_extraction.py` - typed access
  - [x] `zip_extraction.py` - typed access
  - [x] Update `ContentProcessor.process()` signature: `source_config: SourceConfig`

- [x] **Task 7: Migrate infrastructure clients** (AC: 4)
  - [x] `iteration_resolver.py` - typed access
  - [x] `ai_model_client.py` - typed access
  - [x] `raw_document_store.py` - typed access
  - [x] `dapr_event_publisher.py` - typed access

- [x] **Task 8: Migrate remaining files** (AC: 4)
  - [x] `document_index.py` - typed access
  - [x] `job_registration_service.py` - typed access
  - [x] `events.py` (API handlers) - typed access

- [x] **Task 9: Write unit tests for SourceConfigRepository** (AC: 5)
  - [x] Test `get_by_source_id` returns `SourceConfig` model
  - [x] Test invalid data raises Pydantic `ValidationError`
  - [x] Test `get_all_enabled` returns typed list
  - [x] Test `get_by_container` with matching/non-matching containers

- [x] **Task 10: Update existing unit tests** (AC: 5)
  - [x] `tests/unit/collection/` - replace dict mocks with `SourceConfig` instances
  - [x] Verify tests would fail if wrong fields accessed
  - [x] Update `conftest.py` with `SourceConfig` fixtures

- [x] **Task 11: Document DAPR gRPC pattern** (AC: 6)
  - [x] Add section to `_bmad-output/project-context.md`
  - [x] Document: "DAPR gRPC proxying requires native gRPC stub with `dapr-app-id` metadata header"
  - [x] Include code example from `plantation_client.py:81`
  - [x] Reference DAPR docs: howto-invoke-services-grpc

- [x] **Task 12: Validation and CI** (AC: All)
  - [x] Run `ruff check .` and `ruff format --check .`
  - [x] Run full unit test suite
  - [x] Verify CI pipeline passes
  - [x] Run E2E tests to verify no regressions

## Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `infrastructure/repositories/base.py` | NEW | BaseRepository pattern |
| `infrastructure/repositories/source_config_repository.py` | NEW | SourceConfigRepository |
| `infrastructure/repositories/__init__.py` | NEW | Package init |
| `services/source_config_service.py` | MODIFY | Use repository, return typed models |
| `services/pull_job_handler.py` | MODIFY | Typed access |
| `services/content_processor_worker.py` | MODIFY | Typed access |
| `services/job_registration_service.py` | MODIFY | Typed access |
| `processors/json_extraction.py` | MODIFY | Typed access |
| `processors/zip_extraction.py` | MODIFY | Typed access |
| `processors/base.py` | MODIFY | Update ABC signature |
| `infrastructure/iteration_resolver.py` | MODIFY | Typed access |
| `infrastructure/ai_model_client.py` | MODIFY | Typed access |
| `infrastructure/raw_document_store.py` | MODIFY | Typed access |
| `infrastructure/dapr_event_publisher.py` | MODIFY | Typed access |
| `domain/document_index.py` | MODIFY | Typed access |
| `api/events.py` | MODIFY | Typed access |
| `_bmad-output/project-context.md` | MODIFY | Add DAPR gRPC pattern |
| `tests/unit/collection/*.py` | MODIFY | Use Pydantic models in tests |

## Technical Notes

### Reference Implementation (Plantation Model)

```python
# services/plantation-model/src/plantation_model/infrastructure/repositories/base.py
class BaseRepository(Generic[T]):
    def __init__(self, db, collection_name, model_class: type[T]):
        self._model_class = model_class

    async def get_by_id(self, entity_id: str) -> T | None:
        doc = await self._collection.find_one({"_id": entity_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return self._model_class.model_validate(doc)  # ← TYPE SAFE
```

### Target Implementation (Collection Model)

```python
# services/collection-model/src/collection_model/infrastructure/repositories/source_config_repository.py
from fp_common.models.source_config import SourceConfig

class SourceConfigRepository(BaseRepository[SourceConfig]):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "source_configs", SourceConfig)

    async def get_by_source_id(self, source_id: str) -> SourceConfig | None:
        doc = await self._collection.find_one({"source_id": source_id, "enabled": True})
        if doc is None:
            return None
        doc.pop("_id", None)
        return SourceConfig.model_validate(doc)  # ← Pydantic validates!
```

### Before/After Consumer Code

**Before (dict access - no type safety):**
```python
ingestion = config.get("ingestion", {})
mode = ingestion.get("mode")
iteration = ingestion.get("iteration", {})
source_mcp = iteration.get("source_mcp")
```

**After (typed access - compile-time safety):**
```python
mode = config.ingestion.mode
if config.ingestion.iteration:
    source_mcp = config.ingestion.iteration.source_mcp
```

### DAPR gRPC Pattern to Document

```python
# CORRECT: Native gRPC with dapr-app-id metadata
import grpc
from fp_proto.mcp.v1 import mcp_tool_pb2_grpc

async with grpc.aio.insecure_channel("localhost:50001") as channel:  # DAPR sidecar
    stub = mcp_tool_pb2_grpc.McpToolServiceStub(channel)
    metadata = [("dapr-app-id", "plantation-mcp")]  # Target service
    response = await stub.CallTool(request, metadata=metadata)

# WRONG: DaprClient HTTP invocation for gRPC services
# This fails with HTTP 501 "Not Implemented"
```

## Success Metrics

- [x] All source config access uses typed `SourceConfig` model
- [x] Zero `dict[str, Any]` returns from `SourceConfigService`
- [x] All unit tests use real Pydantic models
- [x] Invalid schema access would fail at test time (not E2E)
- [x] DAPR gRPC pattern documented for future developers
- [x] CI passes with no regressions

## Dependencies

- `fp_common.models.source_config.SourceConfig` (already exists)
- Plantation Model `BaseRepository` pattern (reference implementation)

## Risks

- **Scope creep**: Focus only on `SourceConfig`, don't refactor other entities yet
- **Breaking changes**: Ensure all consumers are migrated before merging
- **Test coverage**: May discover additional dict usage in tests

---

## Dev Notes

### E2E Follow-up Fixes (2025-12-30)

During E2E testing with rebuilt Docker containers, the Pydantic type enforcement exposed additional issues that were missed in the initial implementation. All 63 E2E tests now pass after these fixes.

#### Production Code Changes

| File | Change | Why | Evidence | Type |
|------|--------|-----|----------|------|
| `libs/fp-common/fp_common/models/source_config.py:63-66` | Added `tool_arguments`, `result_path`, `inject_linkage` fields to `IterationConfig` | Model was incomplete - fields existed in seed data and were expected by iteration resolver | `iteration_resolver.py:57-61` documents usage | Schema alignment |
| `services/collection-model/src/.../pull_job_handler.py:249-251` | Removed `.model_dump()` call, pass typed `IterationConfig` directly | Resolver expects typed model, not dict | Error: `'dict' object has no attribute 'source_mcp'` | Bug fix |
| `services/collection-model/src/.../pull_job_handler.py:282` | Changed `inject_linkage = []` to `= iteration_config.inject_linkage or []` | Linkage fields weren't injected into documents | Test: `test_weather_document_created_with_region_linkage` | Bug fix |
| `services/collection-model/src/.../iteration_resolver.py:86-87` | Replaced `getattr()` workaround with direct attribute access | Fields now exist in model | Fields added above | Code cleanup |
| `services/collection-model/Dockerfile:63,66` | Added `COPY` for `fp-common` lib and updated `PYTHONPATH` | Story 2-10 added import but Dockerfile not updated | Error: `ModuleNotFoundError: No module named 'fp_common'` | Deployment fix |
| `mcp-servers/collection-mcp/Dockerfile:63,66` | Same as above | Same dependency on fp-common | Same error | Deployment fix |

#### Seed Data Changes

| File | Change | Why |
|------|--------|-----|
| `tests/e2e/infrastructure/seed/source_configs.json:159` | `collection.weather_observation.received` → `collection.weather.updated` | Invalid topic not in `EventTopic` enum, Pydantic validation failed |

#### Commit
- `c3fd744` - fix(e2e): resolve Story 2-10 Pydantic schema enforcement issues

---

### Initial Implementation

Implementation completed across 3 commits:
1. `21752f5` - Main refactoring: repository pattern, typed models, consumer migration
2. `ea531c5` - Integration test fixes for typed SourceConfig
3. `3601ad7` - Fix SourceConfigService constructor (takes db, not repository)

## Dev Agent Record

### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List
- Created `BaseRepository[T]` generic class following Plantation Model pattern
- Created `SourceConfigRepository` with typed `SourceConfig` returns
- Refactored `SourceConfigService` to use repository internally and return typed models
- Migrated all 12+ consumer files from dict access to typed attribute access
- Created `create_source_config()` and `create_iteration_config()` factory functions in conftest.py
- Updated 214 unit tests to use typed fixtures
- Added DAPR gRPC pattern documentation to project-context.md with code examples
- Fixed integration tests to match new SourceConfigService constructor signature
- All CI checks pass (ruff, unit tests, integration tests)

### File List
| File | Change |
|------|--------|
| `infrastructure/repositories/__init__.py` | NEW - Package init |
| `infrastructure/repositories/base.py` | NEW - BaseRepository[T] generic |
| `infrastructure/repositories/source_config_repository.py` | NEW - SourceConfigRepository |
| `services/source_config_service.py` | MODIFIED - Use repository, typed returns |
| `services/pull_job_handler.py` | MODIFIED - Typed SourceConfig access |
| `services/content_processor_worker.py` | MODIFIED - Typed access |
| `services/job_registration_service.py` | MODIFIED - Typed access |
| `processors/base.py` | MODIFIED - SourceConfig signature |
| `processors/json_extraction.py` | MODIFIED - Typed access |
| `processors/zip_extraction.py` | MODIFIED - Typed access |
| `infrastructure/iteration_resolver.py` | MODIFIED - Typed access |
| `infrastructure/ai_model_client.py` | MODIFIED - Typed access |
| `infrastructure/raw_document_store.py` | MODIFIED - Typed access |
| `infrastructure/dapr_event_publisher.py` | MODIFIED - Typed access |
| `domain/document_index.py` | MODIFIED - Typed access |
| `api/events.py` | MODIFIED - Typed access |
| `_bmad-output/project-context.md` | MODIFIED - DAPR gRPC pattern |
| `tests/unit/collection/conftest.py` | MODIFIED - Factory fixtures |
| `tests/unit/collection/test_*.py` | MODIFIED - Typed fixtures (10 files) |
| `tests/integration/test_collection_e2e_open_meteo.py` | MODIFIED - Typed access |
