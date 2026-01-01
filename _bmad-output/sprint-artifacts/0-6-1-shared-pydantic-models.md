# Story 0.6.1: Shared Pydantic Models in fp-common

**Status:** To Do
**GitHub Issue:** TBD
**Epic:** [Epic 0.6: Infrastructure Hardening](../epics/epic-0-6-infrastructure-hardening.md)
**ADR:** [ADR-004: Type Safety Architecture](../architecture/adr/ADR-004-type-safety-shared-pydantic-models.md)
**Story Points:** 5

---

## CRITICAL REQUIREMENTS FOR DEV AGENT

> **READ THIS FIRST - Story is NOT done until ALL these steps are completed!**

### 1. This is a REFACTORING Story (No New Features)

This story MOVES existing models from plantation-model to fp-common. It does NOT create new functionality.

**Key principle:** After this refactoring, ALL existing tests must pass unchanged.

### 2. CI Runs on Feature Branches

**Step-by-step to verify CI on your branch:**

```bash
# 1. Push your changes to the feature branch
git push origin story/0-6-1-shared-pydantic-models

# 2. Wait ~30 seconds for CI to start, then check status
gh run list --branch story/0-6-1-shared-pydantic-models --limit 3

# 3. If CI failed, view the logs
gh run view <run-id> --log-failed
```

### 3. Definition of Done Checklist

Story is **NOT DONE** until ALL of these are true:

- [ ] **Models moved** - All Pydantic models in fp-common/models/
- [ ] **Re-exports work** - plantation-model imports from fp-common
- [ ] **Unit tests created** - New tests in tests/unit/fp_common/models/
- [ ] **Existing tests pass** - ALL plantation-model unit tests still pass
- [ ] **E2E tests pass** - Full E2E suite shows no regressions
- [ ] **Lint passes** - `ruff check . && ruff format --check .`
- [ ] **CI workflow passes** - Both unit and E2E workflows green
- [ ] **GitHub issue updated** - Implementation summary added

---

## Story

As a **developer consuming MCP server responses**,
I want typed Pydantic models shared via fp-common,
So that IDE autocomplete works and validation catches errors at MCP boundaries.

## Acceptance Criteria

1. **AC1: Model Files Created in fp-common** - Given domain models exist in plantation-model, When I check `libs/fp-common/fp_common/models/`, Then I find all models listed in Implementation Plan Phase 1 & 2

2. **AC2: Plantation Model Re-exports** - Given models are moved to fp-common, When plantation-model imports from fp-common, Then `from fp_common.models import Farmer, Factory, Region` works And existing plantation-model code continues to work unchanged

3. **AC3: MCP Servers Return Typed Models** - Given MCP servers return typed models, When I call `get_farmer()` in plantation-mcp, Then the return type is `Farmer` (not `dict[str, Any]`) And Pydantic validation runs on response construction

4. **AC4: All Existing Tests Pass** - Given the refactoring is complete, When I run `pytest tests/unit/` and `pytest tests/e2e/`, Then ALL existing tests pass without modification

## Tasks / Subtasks

- [ ] **Task 1: Create fp-common Model Package Structure** (AC: 1)
  - [ ] Create `libs/fp-common/fp_common/models/__init__.py`
  - [ ] Create `libs/fp-common/fp_common/models/base.py` for shared base models
  - [ ] Add `models` to fp-common package exports

- [ ] **Task 2: Move Plantation Domain Models (Phase 2 from ADR)** (AC: 1, 2)
  - [ ] MOVE `farmer.py` → `fp_common/models/farmer.py`
  - [ ] MOVE `factory.py` → `fp_common/models/factory.py`
  - [ ] MOVE `region.py` → `fp_common/models/region.py`
  - [ ] MOVE `collection_point.py` → `fp_common/models/collection_point.py`
  - [ ] MOVE `grading_model.py` → `fp_common/models/grading_model.py`
  - [ ] MOVE `farmer_performance.py` → `fp_common/models/farmer_performance.py`
  - [ ] MOVE `weather.py` → `fp_common/models/weather.py`
  - [ ] MOVE related enums and value objects

- [ ] **Task 3: Create New Models (Phase 1 from ADR)** (AC: 1)
  - [ ] Create `fp_common/models/document.py` - RawDocumentRef, ExtractionMetadata, IngestionMetadata, Document, SearchResult
  - [ ] Create `fp_common/models/source_summary.py` - SourceSummary
  - [ ] Create `fp_common/models/flush.py` - Flush

- [ ] **Task 4: Update Plantation Model Imports** (AC: 2)
  - [ ] Update `plantation_model/domain/models/__init__.py` to re-export from fp-common
  - [ ] Verify ALL existing imports still work (no breaking changes)
  - [ ] Run `pytest tests/unit/plantation_model/` - must pass unchanged

- [ ] **Task 5: Update MCP Server Return Types** (AC: 3)
  - [ ] Update `plantation_client.py` methods to return typed models
  - [ ] Update `document_client.py` methods to return typed models
  - [ ] Update `source_config_client.py` methods to return typed models
  - [ ] Remove `_to_dict()` anti-pattern calls

- [ ] **Task 6: Create Unit Tests for New Models** (AC: 4)
  - [ ] Create `tests/unit/fp_common/models/test_farmer.py`
  - [ ] Create `tests/unit/fp_common/models/test_factory.py`
  - [ ] Create `tests/unit/fp_common/models/test_region.py`
  - [ ] Create `tests/unit/fp_common/models/test_document.py`
  - [ ] Create `tests/unit/fp_common/models/test_source_summary.py`

- [ ] **Task 7: Verify No Regressions** (AC: 4)
  - [ ] Run `pytest tests/unit/ -v` - ALL existing tests pass
  - [ ] Run E2E suite - ALL scenarios pass
  - [ ] Run `ruff check . && ruff format --check .`
  - [ ] Verify CI pipeline passes

## Git Workflow (MANDATORY)

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.6.1: Shared Pydantic Models in fp-common"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-6-1-shared-pydantic-models
  ```

**Branch name:** `story/0-6-1-shared-pydantic-models`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by phase (model move, import update, test)
- [ ] Push to feature branch: `git push -u origin story/0-6-1-shared-pydantic-models`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.6.1: Shared Pydantic Models" --base main`
- [ ] CI passes on PR
- [ ] Code review completed
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up

---

## Unit Tests Required

### New Tests to Create

```python
# tests/unit/fp_common/models/test_farmer.py
class TestFarmerModel:
    def test_farmer_creation_with_required_fields(self):
        """Farmer model accepts valid required fields."""
        farmer = Farmer(
            id="WM-4521",
            name="John Kamau",
            phone="+254712345678",
            farm_size_hectares=2.5,
            collection_point_id="CP-001",
        )
        assert farmer.id == "WM-4521"

    def test_farmer_validation_rejects_invalid_phone(self):
        """Farmer model rejects invalid phone format."""
        with pytest.raises(ValidationError):
            Farmer(id="WM-4521", name="Test", phone="invalid", ...)

    def test_farmer_model_dump_excludes_none(self):
        """model_dump() excludes None values by default."""
        farmer = Farmer(id="WM-4521", name="Test", phone="+254712345678", ...)
        data = farmer.model_dump(exclude_none=True)
        assert "middle_name" not in data  # Optional field not present

# tests/unit/fp_common/models/test_factory.py
class TestFactoryModel:
    def test_factory_with_grading_model_reference(self):
        """Factory model includes grading_model_id reference."""
        ...

# tests/unit/fp_common/models/test_region.py
class TestRegionModel:
    def test_region_with_flush_calendar(self):
        """Region model includes flush calendar configuration."""
        ...

# tests/unit/fp_common/models/test_document.py
class TestDocumentModel:
    def test_document_with_extracted_fields(self):
        """Document model stores extracted_fields dict."""
        ...

    def test_search_result_with_relevance_score(self):
        """SearchResult includes relevance_score field."""
        ...
```

### Existing Tests Must Pass

These test files must continue to pass WITHOUT modification:

- `tests/unit/plantation_model/domain/models/` - All model tests
- `tests/unit/plantation_model/domain/services/` - All service tests
- `tests/unit/plantation_mcp/` - All MCP tests

---

## E2E Test Impact

### Expected Behavior
- **No breaking changes** - All E2E tests should pass unchanged
- Models are backwards compatible (same field names, same validation)

### Verification Steps
```bash
# After implementation, run full E2E suite
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```

### If E2E Tests Fail
1. Check if MCP response format changed
2. Verify model field names match proto definitions
3. Check for import errors in service logs

---

## Implementation Notes

### Model Migration Strategy

```
BEFORE:
services/plantation-model/src/plantation_model/domain/models/farmer.py
                                                         /factory.py
                                                         /region.py
                                                         /...

AFTER:
libs/fp-common/fp_common/models/farmer.py      ← MOVED here
                        /models/factory.py     ← MOVED here
                        /models/region.py      ← MOVED here
                        /models/...

services/plantation-model/src/plantation_model/domain/models/__init__.py
    # Re-exports from fp-common (backwards compatible)
    from fp_common.models import Farmer, Factory, Region, ...
```

### Import Pattern After Migration

```python
# In plantation-model services (continues to work)
from plantation_model.domain.models import Farmer, Factory

# In MCP servers (new pattern)
from fp_common.models import Farmer, Factory

# In collection-model (new access to plantation models)
from fp_common.models import Farmer, Region
```

### MCP Return Type Update

```python
# BEFORE (anti-pattern)
async def get_farmer(self, farmer_id: str) -> dict[str, Any]:
    response = await stub.GetFarmer(request)
    return self._to_dict(response)  # TYPE LOST!

# AFTER (correct pattern)
async def get_farmer(self, farmer_id: str) -> Farmer:
    response = await stub.GetFarmer(request)
    return Farmer.model_validate(MessageToDict(response))  # TYPED!
```

### CI PYTHONPATH Update Required

Update `.github/workflows/ci.yaml` to include fp-common models:

```yaml
env:
  PYTHONPATH: "${PYTHONPATH}:libs/fp-common/src:..."
```

---

## Potential Issues to Watch

1. **Circular imports** - fp-common models must not import from services
2. **Proto conversion** - Ensure `MessageToDict` output matches Pydantic model fields
3. **Optional vs required** - Match proto field optionality in Pydantic models
4. **Enum compatibility** - Ensure GradeType, GradingType enums work across packages

---

## Local Test Run Evidence (MANDATORY - Fill BEFORE marking done)

**1. Unit Tests:**
```bash
pytest tests/unit/fp_common/models/ -v
```
**Output:**
```
(paste test output here)
```

**2. Existing Tests Still Pass:**
```bash
pytest tests/unit/plantation_model/ -v
```
**Output:**
```
(paste test output here)
```

**3. E2E Tests Pass:**
```bash
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v
```
**Output:**
```
(paste test output here)
```

**4. Lint Check:**
```bash
ruff check . && ruff format --check .
```
**Lint passed:** [ ] Yes / [ ] No

**5. CI Check:**
```bash
gh run list --branch story/0-6-1-shared-pydantic-models --limit 5
```
**CI output:**
```
(paste CI status here)
```

---

## References

- [ADR-004: Type Safety Architecture](../architecture/adr/ADR-004-type-safety-shared-pydantic-models.md)
- [Source: plantation-model domain models](../../../services/plantation-model/src/plantation_model/domain/models/)
- [Source: plantation-mcp client](../../../mcp-servers/plantation-mcp/src/plantation_mcp/plantation_client.py)
