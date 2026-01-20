# Story 0.8.1: Pydantic Validation Infrastructure for Seed Data

**Status:** in-progress
**GitHub Issue:** #205

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer loading demo data**,
I want a validation library that loads JSON through Pydantic models,
So that schema errors are caught before any database write.

## Acceptance Criteria

1. **Given** seed JSON files exist in any directory (e.g., `tests/e2e/infrastructure/seed/` or `tests/demo/generated/demo/`)
   **When** I run the validation module with that directory path
   **Then** each JSON file is loaded and validated through its corresponding Pydantic model
   **And** validation errors include: filename, record index, field name, error message

2. **Given** a JSON record has an unknown field
   **When** Pydantic validation runs
   **Then** the field is rejected (not silently ignored)
   **And** the error message identifies the invalid field

3. **Given** a JSON record is missing a required field
   **When** Pydantic validation runs
   **Then** a clear error identifies the missing field
   **And** the record index and filename are included

4. **Given** all records pass Pydantic validation
   **When** FK validation runs
   **Then** each foreign key is checked against the FK registry
   **And** errors report: source entity, field name, invalid FK value

5. **Given** Pydantic models exist in services (plantation-model, collection-model, ai-model)
   **When** I check the validation module
   **Then** it imports models directly from service packages (no duplication)
   **And** the model-to-file mapping is explicit and documented

6. **Given** the validation module is called
   **When** any source directory path is provided
   **Then** validation works regardless of path (path-agnostic design)
   **And** default paths are configured by the caller (Story 0.8.2 loader script)

## Tasks / Subtasks

- [x] Task 1: Create validation module structure (AC: #1, #5)
  - [x] 1.1: Create `scripts/demo/` directory structure
  - [x] 1.2: Create `scripts/demo/validation.py` with core `validate_with_pydantic()` function
  - [x] 1.3: Create `scripts/demo/model_registry.py` with seed file to Pydantic model mapping

- [x] Task 2: Implement Pydantic validation logic (AC: #1, #2, #3)
  - [x] 2.1: Implement `validate_with_pydantic()` that returns `tuple[list[T], list[ValidationError]]`
  - [x] 2.2: Configure Pydantic models with `extra="forbid"` via strict wrapper classes
  - [x] 2.3: Implement error formatting with filename, record index, field path, error message
  - [x] 2.4: Ensure validation collects ALL errors (doesn't stop at first)

- [x] Task 3: Implement FK Registry and validation (AC: #4)
  - [x] 3.1: Create `scripts/demo/fk_registry.py` with `FKRegistry` class
  - [x] 3.2: Implement `register()`, `get_valid_ids()`, `validate_fk()` methods
  - [x] 3.3: Create `validate_foreign_keys()` function for cross-entity FK checks
  - [x] 3.4: FK validation supports list fields (farmer_ids) and optional FKs

- [x] Task 4: Create model mapping configuration (AC: #5, #6)
  - [x] 4.1: Defined `ModelRegistry` with file pattern to model mapping
  - [x] 4.2: Map each seed file to its Pydantic model import path (11 models)
  - [x] 4.3: Models imported directly from service packages - no duplication
  - [x] 4.4: All functions accept `file_path: Path` parameter (path-agnostic)

- [x] Task 5: Write unit tests (AC: #1-5)
  - [x] 5.1: Create `tests/unit/demo/test_validation.py` (10 tests)
  - [x] 5.2: Test valid JSON passes Pydantic validation
  - [x] 5.3: Test invalid field type is rejected with clear error
  - [x] 5.4: Test missing required field produces error with context
  - [x] 5.5: Test unknown/extra field is rejected (not ignored)
  - [x] 5.6: Create `tests/unit/demo/test_fk_registry.py` (14 tests)
  - [x] 5.7: Test FK lookup success
  - [x] 5.8: Test FK lookup failure reports context
  - [x] 5.9: Create `tests/unit/demo/test_model_registry.py` (16 tests)

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [x] GitHub Issue exists or created: #205
- [x] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-8-1-pydantic-validation-infrastructure
  ```

**Branch name:** `story/0-8-1-pydantic-validation-infrastructure`

### During Development
- [x] All commits reference GitHub issue: `Relates to #205`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/0-8-1-pydantic-validation-infrastructure`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.8.1: Pydantic Validation Infrastructure" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/0-8-1-pydantic-validation-infrastructure`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
pytest tests/unit/demo/ -v
```
**Output:**
```
(paste test summary here - e.g., "42 passed in 5.23s")
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure
bash scripts/e2e-up.sh --build

# Run pre-flight validation
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
git push origin story/0-8-1-pydantic-validation-infrastructure

# Wait ~30s, then check CI status
gh run list --branch story/0-8-1-pydantic-validation-infrastructure --limit 3
```
**CI Run ID:** _______________
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### Architecture Context (ADR-020)

This story implements **Part 1** of the Demo Data Strategy defined in ADR-020. The validation infrastructure is the foundation for both the seed loader (Story 0.8.2) and the data generator (Stories 0.8.3-0.8.4).

**Key Design Principles from ADR-020:**
1. **Pydantic models are the single source of truth** - Import from existing packages, no duplication
2. **Fail-fast, fail-complete** - Collect ALL errors, then abort (no partial processing)
3. **FK validation in-memory** - Cross-reference entities before any database writes
4. **Late dict conversion** - Keep models as Pydantic instances until database insert

### File Structure to Create

```
scripts/
└── demo/
    ├── __init__.py
    ├── validation.py       # Core validation functions
    ├── fk_registry.py      # FK tracking and validation
    └── model_mapping.py    # JSON file to Pydantic model mapping
```

### Pydantic Model Locations (DO NOT DUPLICATE)

| Seed File | Pydantic Model | Import Path |
|-----------|----------------|-------------|
| `grading_models.json` | `GradingModel` | `fp_common.models.grading_model` |
| `regions.json` | `Region` | `fp_common.models.region` |
| `factories.json` | `Factory` | `fp_common.models.factory` |
| `collection_points.json` | `CollectionPoint` | `fp_common.models.collection_point` |
| `farmers.json` | `Farmer` | `fp_common.models.farmer` |
| `farmer_performance.json` | `FarmerPerformance` | `fp_common.models.farmer_performance` |
| `weather_observations.json` | `RegionalWeather` | `fp_common.models.regional_weather` |
| `source_configs.json` | `SourceConfig` | `fp_common.models.source_config` |
| `documents.json` | `Document` | `fp_common.models.document` |
| `agent_configs.json` | `AgentConfig` | `ai_model.domain.agent_config` |
| `prompts.json` | `Prompt` | `ai_model.domain.prompt` |

### FK Dependency Graph (CRITICAL - from ADR-020)

```
LEVEL 0 (No dependencies):
├── grading_models
├── regions
├── agent_configs
└── prompts

LEVEL 1 (Depends on Level 0):
├── source_configs
│   └── FK: ai_agent_id → agent_configs.agent_id (optional)
└── factories
    └── FK: region_id → regions.region_id (REQUIRED)

LEVEL 2 (Depends on Level 1):
└── collection_points
    ├── FK: factory_id → factories.id (REQUIRED)
    ├── FK: region_id → regions.region_id (REQUIRED)
    └── farmer_ids[] → farmers.id (validated after farmers load)

LEVEL 3 (Depends on Level 0):
└── farmers
    └── FK: region_id → regions.region_id (REQUIRED)

LEVEL 4 (Depends on Level 3):
├── farmer_performance
│   └── FK: farmer_id → farmers.id (REQUIRED)
└── weather_observations
    └── FK: region_id → regions.region_id (REQUIRED)

LEVEL 5 (Depends on Levels 1, 3):
└── documents
    ├── FK: ingestion.source_id → source_configs.source_id (REQUIRED)
    └── linkage_fields.farmer_id → farmers.id (optional)
```

### Data Source Paths (Path-Agnostic Design)

The validation module accepts **any directory path**. Story 0.8.2 (loader script) will support two sources:

| Source | Path | Usage |
|--------|------|-------|
| E2E Seed | `tests/e2e/infrastructure/seed/` | `--source e2e` (stable, minimal data) |
| Generated Demo | `tests/demo/generated/demo/` | `--source custom --path ...` (rich demo data) |

### Existing E2E Seed Files (DO NOT MODIFY)

Location: `tests/e2e/infrastructure/seed/`

```
grading_models.json      # 2 grading models (TBK, KTDA)
regions.json             # 5 regions
factories.json           # 2 factories
collection_points.json   # 3 collection points
farmers.json             # 4 farmers
farmer_performance.json  # Performance records
weather_observations.json
source_configs.json      # 5 source configs
documents.json           # Quality documents
agent_configs.json       # 2 AI agent configs
prompts.json             # LLM prompts
```

### Pydantic Configuration Requirements

**Models MUST have `extra="forbid"`** to reject unknown fields:

```python
from pydantic import BaseModel, ConfigDict

class MyModel(BaseModel):
    model_config = ConfigDict(extra="forbid")  # Reject unknown fields

    field1: str
    field2: int
```

**Note:** Check if existing fp_common models already have this setting. If not, you may need to wrap them or handle in validation code.

### Existing MongoDBDirectClient (REUSE, DO NOT RECREATE)

Location: `tests/e2e/helpers/mongodb_direct.py`

This client already has seed methods that Story 0.8.2 will use:
- `seed_grading_models()`
- `seed_regions()`
- `seed_factories()`
- `seed_collection_points()`
- `seed_farmers()`
- `seed_farmer_performance()`
- `seed_weather_observations()`
- `seed_source_configs()`
- `seed_documents()`
- `seed_agent_configs()`
- `seed_prompts()`

### PYTHONPATH Setup

The validation module needs to import from multiple packages:

```python
# Required PYTHONPATH additions
PYTHONPATH="${PYTHONPATH}:.:libs/fp-common:libs/fp-proto/src:services/ai-model/src"
```

### Testing Strategy

**Unit tests only** for this story (no E2E infrastructure required):
- Test with minimal fixture data
- Mock file system reads if needed
- Test error message formatting
- Test FK registry operations

### Project Structure Notes

- Scripts go in `scripts/demo/` (alongside other utility scripts)
- Unit tests go in `tests/unit/demo/`
- Uses existing fixtures from `tests/conftest.py` - **DO NOT override** `mock_mongodb_client`

### References

- [ADR-020: Demo Data Strategy](/_bmad-output/architecture/adr/ADR-020-demo-data-loader-pydantic-validation.md)
- [Project Context](/_bmad-output/project-context.md) - Section on Pydantic patterns
- [E2E Seed Data](tests/e2e/infrastructure/seed/) - Existing validated seed files
- [MongoDBDirectClient](tests/e2e/helpers/mongodb_direct.py) - Database loading helper

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- Implemented validation module with 40 passing unit tests
- All Pydantic models wrapped with `extra="forbid"` to reject unknown fields (AC #2)
- Models imported directly from service packages - no duplication (AC #5)
- FK registry supports single FKs, list FKs (farmer_ids), and optional FKs (AC #4)
- Path-agnostic design - all functions accept Path parameter (AC #6)
- Error messages include filename, record index, field path, and error message (AC #1, #3)

### File List

**Created:**
- `scripts/demo/__init__.py` - Package initialization with exports
- `scripts/demo/validation.py` - Core validation functions
- `scripts/demo/fk_registry.py` - FK registry and validation
- `scripts/demo/model_registry.py` - Model mapping configuration
- `tests/unit/demo/__init__.py` - Test package initialization
- `tests/unit/demo/test_validation.py` - 10 validation tests
- `tests/unit/demo/test_fk_registry.py` - 14 FK registry tests
- `tests/unit/demo/test_model_registry.py` - 16 model registry tests

**Modified:**
- `.github/workflows/ci.yaml` - Added `.` to PYTHONPATH, added `--cov=scripts`
