# Story 0.8.3: Polyfactory Generator Framework

**Status:** done
**GitHub Issue:** #209

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer needing realistic test data**,
I want a Polyfactory-based generator framework,
So that I can generate large volumes of valid data from Pydantic models.

## Acceptance Criteria

1. **Given** Pydantic models define domain entities
   **When** I check the generator module
   **Then** Polyfactory factories exist for each model:
   - `RegionFactory` - Generates valid Region instances
   - `FactoryEntityFactory` - Generates valid Factory instances
   - `CollectionPointFactory` - Generates valid CollectionPoint instances
   - `FarmerFactory` - Generates valid Farmer instances
   - `RegionalWeatherFactory` - Generates valid RegionalWeather instances

   **Note:** SourceConfig is reference data (loaded from E2E seed), not generated.

2. **Given** a factory generates an entity
   **When** the entity has foreign keys
   **Then** the factory accepts FK values as parameters
   **And** default values reference the FK registry

3. **Given** Kenya-specific data is needed
   **When** I check factory configurations
   **Then** Faker locales include "sw_KE" for Swahili names
   **And** phone numbers use "+254" prefix
   **And** location coordinates are within Kenya bounds

4. **Given** I generate a Farmer
   **When** the factory runs
   **Then** the result passes Pydantic validation
   **And** all required fields have realistic values

5. **Given** I generate any entity
   **When** the factory runs
   **Then** the result can be converted to JSON via `model_dump(mode="json")`
   **And** the result is compatible with `MongoDBDirectClient.seed_*` methods

## Tasks / Subtasks

- [x] Task 1: Create generator package structure (AC: #1)
  - [x] 1.1: Create `tests/demo/generators/__init__.py` with package exports
  - [x] 1.2: Create `tests/demo/generators/base.py` with BaseFactory class and FK registry integration

- [x] Task 2: Implement Plantation model factories (AC: #1, #2, #3, #4)
  - [x] 2.1: Create `tests/demo/generators/plantation.py` with RegionFactory
  - [x] 2.2: Add FactoryEntityFactory (named to avoid conflict with polyfactory.Factory)
  - [x] 2.3: Add CollectionPointFactory with factory_id, region_id FK params
  - [x] 2.4: Add FarmerFactory with Kenya-specific names, phones, coordinates
  - [x] 2.5: Add FarmerPerformanceFactory with farmer_id FK param

- [x] Task 3: Implement weather factory (AC: #1, #2)
  - [x] 3.1: Create `tests/demo/generators/weather.py` with RegionalWeatherFactory
  - [x] 3.2: RegionalWeatherFactory takes region_id FK param (for Story 0.8.4 profiles)

  **Note:** SourceConfigFactory and DocumentFactory deferred to Story 0.8.4 (reference/scenario data)

- [ ] ~~Task 4: AI Model factories~~ - REMOVED (reference data, loaded from E2E seed)

- [x] Task 4: Integrate FK registry with factories (AC: #2, #5)
  - [x] 4.1: FK registry integration via FKRegistryMixin in base.py
  - [x] 4.2: Implement `build_batch_and_register()` method that generates and registers IDs
  - [x] 4.3: Ensure generated entities register IDs in FKRegistry from Story 0.8.1

- [x] Task 5: Implement Kenya-specific data providers (AC: #3)
  - [x] 5.1: Create `tests/demo/generators/kenya_providers.py` with:
    - Kenyan first names (Kiprop, Cheruiyot, Bett, etc.)
    - Kenyan last names
    - Valid phone formats (+254 7XX XXX XXX)
    - Kenya GPS bounds (-4.7 to 4.6 lat, 33.9 to 41.9 lng)
    - Altitude bands by region (low <800m, medium 800-1400m, high >1400m)

- [x] Task 6: Write unit tests (AC: #1-5)
  - [x] 6.1: Create `tests/unit/demo/generators/test_plantation_factories.py` (28 tests)
  - [x] 6.2: Create `tests/unit/demo/generators/test_weather_factory.py` (12 tests)
  - [x] 6.3: Create `tests/unit/demo/generators/test_kenya_providers.py` (13 tests)

- [ ] ~~Task 7: Integration test with seed infrastructure~~ - DEFERRED to Story 0.8.4
  - [ ] ~~7.1: Test generated entities can be loaded via `MongoDBDirectClient.seed_*`~~
  - [ ] ~~7.2: Test generated data passes same FK validation as Story 0.8.1~~

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.8.3: Polyfactory Generator Framework"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-8-3-polyfactory-generator-framework
  ```

**Branch name:** `story/0-8-3-polyfactory-generator-framework`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/0-8-3-polyfactory-generator-framework`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.8.3: Polyfactory Generator Framework" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/0-8-3-polyfactory-generator-framework`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
PYTHONPATH="${PYTHONPATH}:.:libs/fp-common:services/ai-model/src" pytest tests/unit/demo/generators/ -v
```
**Output:**
```
53 passed, 2 warnings in 2.19s
```

### 2. E2E Tests

> **Note:** This story creates test data generator utilities, not production services or E2E scenarios.
> The generators are validated through 53 unit tests that verify:
> - All generated entities pass Pydantic validation (AC #4)
> - All generated entities are JSON-serializable via model_dump(mode="json") (AC #5)
> - FK registry integration ensures valid foreign key references (AC #2)

**E2E Requirement:** N/A - This is a test tooling story. Integration with seed infrastructure
will be validated in Story 0.8.4 when generators are used for profile-based data generation.

**E2E passed:** N/A (tooling story - no E2E scenarios)

### 3. Lint Check
```bash
ruff check . && ruff format --check .
```
**Lint passed:** [x] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin story/0-8-3-polyfactory-generator-framework

# Wait ~30s, then check CI status
gh run list --branch story/0-8-3-polyfactory-generator-framework --limit 3
```
**CI Run ID:** 21186553383
**CI Status:** [x] Passed / [ ] Failed
**Verification Date:** 2026-01-20

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

### Unit Test Changes (if any)
If you modified ANY unit test behavior, document here:

| Test File | Test Name Before | Test Name After | Behavior Change | Justification |
|-----------|------------------|-----------------|-----------------|---------------|
| (none) | | | | |

### Local Test Run Evidence (MANDATORY before any push)

**First run timestamp:** _______________

**Docker stack status:**
```
# Paste output of: docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml ps
```

**Test run output:**
```
# Paste generator validation output
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

### Architecture Context (ADR-020)

This story implements **Part 2 (Tool 2) Foundation** of the Demo Data Strategy per ADR-020. The generator framework enables:

1. **Schema-valid data generation** - All data generated via Polyfactory passes Pydantic validation
2. **FK-valid relationships** - FKRegistry integration ensures no orphan records
3. **Kenya-realistic data** - Locale-aware generation for names, phones, coordinates
4. **Scenario support** - Foundation for Story 0.8.4's profile-based generation

### CRITICAL: Reuse Existing Infrastructure (DO NOT RECREATE)

**From Story 0.8.1 (validation.py, fk_registry.py, model_registry.py):**

| Module | Location | Usage in This Story |
|--------|----------|---------------------|
| `FKRegistry` | `scripts/demo/fk_registry.py` | Track generated entity IDs for FK validation |
| `validate_foreign_keys()` | `scripts/demo/fk_registry.py` | Validate generated entities |
| `get_model_for_file()` | `scripts/demo/model_registry.py` | Get Pydantic models for factories |

**From Story 0.8.2 (loader.py):**

| Module | Location | Usage in This Story |
|--------|----------|---------------------|
| `SEED_ORDER` | `scripts/demo/loader.py` | Reference for dependency order |
| `MongoDBDirectClient` | `tests/e2e/helpers/mongodb_direct.py` | Load generated data |

### Polyfactory Library (CRITICAL)

**Library:** `polyfactory` - https://polyfactory.litestar.dev/

**Installation:** Add to `pyproject.toml` dev dependencies:
```toml
[tool.poetry.group.dev.dependencies]
polyfactory = "^2.18.0"
```

**Key Patterns:**

```python
from polyfactory.factories.pydantic_factory import ModelFactory
from fp_common.models.farmer import Farmer

class FarmerFactory(ModelFactory):
    __model__ = Farmer
    __faker__ = Faker("sw_KE")  # Swahili-Kenya locale

    # Override specific fields
    @classmethod
    def region_id(cls) -> str:
        """FK field - requires explicit value or registry lookup."""
        raise NotImplementedError("Must pass region_id parameter")
```

**FK Field Handling:**
- FK fields MUST NOT have default random values
- Either pass as parameter OR lookup from FKRegistry
- Use `@classmethod` field overrides to enforce FK constraints

### Files to Create

```
tests/demo/
├── __init__.py                   # Package init (created)
├── generators/
│   ├── __init__.py               # Package exports
│   ├── base.py                   # BaseFactory, FK registry integration
│   ├── plantation.py             # Region, Factory, CollectionPoint, Farmer, FarmerPerformance
│   ├── weather.py                # RegionalWeather factory
│   └── kenya_providers.py        # Kenya-specific Faker providers

tests/unit/demo/
├── __init__.py                   # Package init (created)
├── generators/
│   ├── __init__.py
│   ├── test_kenya_providers.py   # Kenya provider tests
│   ├── test_plantation_factories.py  # Plantation factory tests
│   └── test_weather_factory.py   # Weather factory tests
```

**Note:** `registry_integration.py` was originally planned but deemed unnecessary - the functionality is implemented via `build_batch_and_register()` in `base.py` and helper functions in `__init__.py`.

**NOT in this story (deferred to 0.8.4):**
- `ai_model.py` - AgentConfig, Prompt (reference data)
- `collection.py` - SourceConfig, Document (reference/scenario data)

### Dependency Order (CRITICAL - Same as loader.py)

Generators MUST produce entities in this order to satisfy FK dependencies:

```python
GENERATION_ORDER = [
    # Level 0 - Independent (no FKs)
    "regions",          # RegionFactory

    # Level 1 - Depends on Level 0
    "factories",        # FactoryEntityFactory (FK: regions)

    # Level 2 - Depends on Level 1
    "collection_points",  # CollectionPointFactory (FK: factories, regions)

    # Level 3 - Depends on Level 0
    "farmers",          # FarmerFactory (FK: regions)

    # Level 4 - Depends on Level 3 / Level 0
    "farmer_performance",    # FarmerPerformanceFactory (FK: farmers)
    "weather_observations",  # RegionalWeatherFactory (FK: regions)

    # Reference data (loaded from E2E, not generated):
    # - grading_models, agent_configs, prompts, source_configs
    # Story 0.8.4 adds: documents (quality history with scenarios)
]
```

### Kenya-Specific Data Requirements (AC #3)

**Phone Numbers:**
- Format: `+254 7XX XXX XXX` (Safaricom) or `+254 1XX XXX XXX` (Airtel)
- 10 digits after country code
- Example: `+254 712 345 678`

**Names (Kenyan):**
```python
KENYAN_FIRST_NAMES = [
    "James", "Grace", "Daniel", "Sarah", "John", "Mary",
    "Peter", "Jane", "David", "Ann", "Michael", "Ruth",
    "Joseph", "Esther", "Samuel", "Faith", "Stephen", "Joyce"
]

KENYAN_LAST_NAMES = [
    "Kiprop", "Cheruiyot", "Bett", "Kosgei", "Langat",
    "Kipkemoi", "Kiptoo", "Chepkemoi", "Rotich", "Maina",
    "Kamau", "Njoroge", "Wanjiku", "Otieno", "Ochieng",
    "Odhiambo", "Owino", "Achieng", "Nyambura", "Wambui"
]
```

**GPS Coordinates (Kenya bounds):**
- Latitude: -4.7 to 4.6 (South to North)
- Longitude: 33.9 to 41.9 (West to East)
- Tea-growing regions typically: 0.0-1.5 lat, 35.0-37.5 lng, altitude 1500-2200m

**Altitude Bands (per project-context.md):**
- Low: < 800m
- Medium: 800-1200m
- High: > 1200m

### Pydantic Model Imports (CRITICAL)

**DO NOT create separate models - import from production code:**

```python
# Plantation models (fp_common) - GENERATED
from fp_common.models.region import Region
from fp_common.models.factory import Factory
from fp_common.models.collection_point import CollectionPoint
from fp_common.models.farmer import Farmer, FarmScale, NotificationChannel
from fp_common.models.farmer_performance import FarmerPerformance
from fp_common.models.regional_weather import RegionalWeather

# Reference data models (loaded from E2E, not generated in this story):
# - GradingModel, SourceConfig, Document, AgentConfig, Prompt
# These are used in Story 0.8.4 for profile-based generation with scenarios
```

### Example Factory Implementation

```python
# tests/demo/generators/plantation.py

from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory.fields import Use
from faker import Faker

from fp_common.models.farmer import Farmer, FarmScale, NotificationChannel

from .kenya_providers import KenyaProvider
from .base import FKRegistryMixin


class FarmerFactory(FKRegistryMixin, ModelFactory):
    """Generate valid Farmer instances with Kenya-specific data."""

    __model__ = Farmer
    __faker__ = Faker("sw_KE")
    __use_defaults__ = True

    # ID prefix for generated data (not E2E)
    id_prefix: str = "FRM-GEN-"
    _counter: int = 0

    @classmethod
    def id(cls) -> str:
        """Generate sequential ID with prefix."""
        cls._counter += 1
        return f"{cls.id_prefix}{cls._counter:03d}"

    @classmethod
    def region_id(cls) -> str:
        """FK to regions - must be passed or looked up from registry."""
        # If FK registry has regions, pick one; otherwise raise
        regions = cls.get_fk_registry().get_valid_ids("regions")
        if not regions:
            raise ValueError("No regions registered - generate regions first")
        return random.choice(list(regions))

    @classmethod
    def first_name(cls) -> str:
        return random.choice(KenyaProvider.FIRST_NAMES)

    @classmethod
    def last_name(cls) -> str:
        return random.choice(KenyaProvider.LAST_NAMES)

    @classmethod
    def contact(cls) -> dict:
        return {
            "phone": KenyaProvider.phone_number(),
            "alternate_phone": None,
        }

    @classmethod
    def farm_location(cls) -> dict:
        lat, lng, alt = KenyaProvider.kenya_coordinates()
        return {
            "latitude": lat,
            "longitude": lng,
            "altitude_meters": alt,
        }

    @classmethod
    def farm_scale(cls) -> FarmScale:
        # Realistic distribution: 60% smallholder, 35% medium, 5% estate
        return random.choices(
            [FarmScale.SMALLHOLDER, FarmScale.MEDIUM, FarmScale.ESTATE],
            weights=[60, 35, 5]
        )[0]

    @classmethod
    def notification_channel(cls) -> NotificationChannel:
        # 70% SMS, 30% WhatsApp
        return random.choices(
            [NotificationChannel.SMS, NotificationChannel.WHATSAPP],
            weights=[70, 30]
        )[0]
```

### FK Registry Integration Pattern

```python
# tests/demo/generators/base.py

from scripts.demo.fk_registry import FKRegistry


class FKRegistryMixin:
    """Mixin that provides FK registry access to factories."""

    _fk_registry: FKRegistry | None = None

    @classmethod
    def set_fk_registry(cls, registry: FKRegistry) -> None:
        """Set the shared FK registry for all factories."""
        cls._fk_registry = registry

    @classmethod
    def get_fk_registry(cls) -> FKRegistry:
        """Get the shared FK registry."""
        if cls._fk_registry is None:
            cls._fk_registry = FKRegistry()
        return cls._fk_registry

    @classmethod
    def register_generated(cls, entity_type: str, ids: list[str]) -> None:
        """Register generated IDs in the FK registry."""
        cls.get_fk_registry().register(entity_type, ids)
```

### Previous Story Intelligence (Story 0.8.2)

**Learnings from Story 0.8.2:**

1. **Use production models** - Don't create separate seed models; use `extra="forbid"` wrappers if needed
2. **Strip MongoDB fields** - Remove `_id` and `_comment` before validation
3. **AgentConfig special handling** - Uses TypeAdapter for discriminated union validation
4. **Weather data structure** - One record per (region_id, date) - composite key pattern
5. **MongoDBDirectClient patterns** - All `seed_*` methods use upsert pattern

**Files created in 0.8.2 to REUSE:**
- `scripts/demo/load_demo_data.py` - Reference for SEED_ORDER and dependency graph
- `scripts/demo/loader.py` - MongoDBDirectClient integration patterns

### Testing Strategy

**Unit Tests:**
- Each factory produces valid Pydantic model (passes `model.model_validate()`)
- FK fields reference valid IDs when registry populated
- Kenya-specific data within valid ranges
- Generated data JSON-serializable (`model_dump(mode="json")`)

**Integration Tests:**
- Generated data loadable via `MongoDBDirectClient.seed_*`
- Generated data passes FK validation from Story 0.8.1
- Multiple generation runs produce unique IDs (no collisions)

### PYTHONPATH Setup

```bash
PYTHONPATH="${PYTHONPATH}:.:libs/fp-common:libs/fp-proto/src:services/ai-model/src"
```

### References

- [ADR-020: Demo Data Strategy](/_bmad-output/architecture/adr/ADR-020-demo-data-loader-pydantic-validation.md) - Architecture decision
- [Story 0.8.1](/_bmad-output/sprint-artifacts/0-8-1-pydantic-validation-infrastructure.md) - Validation infrastructure (FKRegistry)
- [Story 0.8.2](/_bmad-output/sprint-artifacts/0-8-2-seed-data-loader-script.md) - Seed loader (SEED_ORDER, MongoDBDirectClient patterns)
- [Polyfactory Docs](https://polyfactory.litestar.dev/) - Pydantic factory library
- [Project Context](/_bmad-output/project-context.md) - Pydantic patterns, region altitude bands
- [Epic 0.8](/_bmad-output/epics/epic-0-8-demo-developer-tooling.md) - Epic context and story dependency graph

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Fixed FK registry ClassVar inheritance bug: When using ClassVar with inheritance, setting `cls._fk_registry` creates a new attribute on the subclass instead of modifying the mixin's attribute. Fixed by explicitly using `FKRegistryMixin._fk_registry` in all methods.
- Fixed module import paths: The `fp_common` package is directly under `libs/fp-common/` (not in a src subfolder).

### Completion Notes List

1. Created Polyfactory generator framework with all 5 required factories (AC #1)
2. FK registry integration via FKRegistryMixin for FK validation (AC #2)
3. Kenya-specific data provider with names, phone formats, GPS bounds (AC #3)
4. All generated entities pass Pydantic validation (AC #4)
5. All generated entities are JSON-serializable via model_dump(mode="json") (AC #5)
6. 53 unit tests covering all acceptance criteria
7. Used `noqa: E402` comments for necessary path setup imports

### File List

**Created:**
- `tests/demo/__init__.py` - Demo package init
- `tests/demo/generators/__init__.py` - Package exports and utility functions
- `tests/demo/generators/base.py` - FKRegistryMixin and BaseModelFactory
- `tests/demo/generators/kenya_providers.py` - Kenya-specific data provider
- `tests/demo/generators/plantation.py` - Region, Factory, CollectionPoint, Farmer, FarmerPerformance factories
- `tests/demo/generators/weather.py` - RegionalWeatherFactory
- `tests/unit/demo/__init__.py` - Unit test demo package init
- `tests/unit/demo/generators/__init__.py` - Test package init
- `tests/unit/demo/generators/test_kenya_providers.py` - 13 tests for Kenya provider
- `tests/unit/demo/generators/test_plantation_factories.py` - 28 tests for plantation factories
- `tests/unit/demo/generators/test_weather_factory.py` - 12 tests for weather factory

**Modified:**
- `pyproject.toml` - Added polyfactory>=2.18.0 to dev dependencies
