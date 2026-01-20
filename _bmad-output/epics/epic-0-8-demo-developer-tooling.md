### Epic 0.8: Demo & Developer Tooling

**Priority:** P1

**Dependencies:** Epic 0.4 (E2E Tests) - for seed data structure, Epic 1 & 2 (Domain Models) - for Pydantic models

Cross-cutting developer tooling that enables demo environments and developer productivity. These stories implement the unified demo data strategy per ADR-020, providing tools to load validated seed data and generate realistic test data for demos, development, and frontend testing.

**Related ADRs:**
- ADR-020: Demo Data Strategy with Pydantic Validation

---

## Architecture Context

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  DEMO & DEVELOPER TOOLING (Epic 0.8)                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  TOOL 1: SEED DATA LOADER (Stories 0.8.1-0.8.2)                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    load-demo-data.py                             │   │
│  │                                                                  │   │
│  │  Phase 1: Schema Validation                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │   │
│  │  │  JSON Files  │─▶│   Pydantic   │─▶│  Validated   │          │   │
│  │  │ (seed/*.json)│  │   Models     │  │   Models     │          │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘          │   │
│  │                                                                  │   │
│  │  Phase 2: Foreign Key Validation                                 │   │
│  │  ┌─────────────────────────────────────────────────────────┐    │   │
│  │  │  Region ◀── Factory ◀── CollectionPoint ◀── Farmer     │    │   │
│  │  │                         FK Registry                      │    │   │
│  │  └─────────────────────────────────────────────────────────┘    │   │
│  │                                                                  │   │
│  │  Phase 3: Database Load (Dependency Order)                       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │   │
│  │  │ Level 0:     │─▶│ Level 1:     │─▶│ Level 2-5:   │          │   │
│  │  │ source_config│  │ regions,     │  │ factories,   │          │   │
│  │  │ ai_prompts   │  │ grading      │  │ CPs, farmers │          │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  TOOL 2: DATA GENERATOR (Stories 0.8.3-0.8.5)                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                   generate-demo-data.py                          │   │
│  │                                                                  │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │   │
│  │  │   Profiles   │  │  Polyfactory │  │   FK Graph   │          │   │
│  │  │  (YAML cfg)  │─▶│  Generators  │─▶│  Traversal   │          │   │
│  │  │ minimal/demo │  │ Faker-backed │  │  Validation  │          │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘          │   │
│  │                                                                  │   │
│  │  Profiles:                                                       │   │
│  │  ├─ minimal   (3 farmers, 1 factory)  ~5 KB                     │   │
│  │  ├─ demo      (50 farmers, 3 factories, quality history)        │   │
│  │  └─ demo-large (200+ farmers, realistic scenarios)              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  OUTPUT: JSON files in tests/demo/ (git-ignored, reproducible)          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Stories

### Story 0.8.1: Pydantic Validation Infrastructure for Seed Data

**Status:** To Do

As a **developer loading demo data**,
I want a validation library that loads JSON through Pydantic models,
So that schema errors are caught before any database write.

**ADR:** ADR-020 - Demo Data Strategy with Pydantic Validation

**Acceptance Criteria:**

**Given** seed JSON files exist in `tests/e2e/infrastructure/seed/`
**When** I run the validation module
**Then** each JSON file is loaded and validated through its corresponding Pydantic model
**And** validation errors include: filename, record index, field name, error message

**Given** a JSON record has an unknown field
**When** Pydantic validation runs
**Then** the field is rejected (not silently ignored)
**And** the error message identifies the invalid field

**Given** a JSON record is missing a required field
**When** Pydantic validation runs
**Then** a clear error identifies the missing field
**And** the record index and filename are included

**Given** all records pass Pydantic validation
**When** FK validation runs
**Then** each foreign key is checked against the FK registry
**And** errors report: source entity, field name, invalid FK value

**Given** Pydantic models exist in services (plantation-model, collection-model)
**When** I check the validation module
**Then** it imports models directly from service packages (no duplication)
**And** the model-to-file mapping is explicit and documented

**Deliverables:**
- `scripts/demo/validation.py` - Core validation functions
- `scripts/demo/fk_registry.py` - FK tracking and validation
- `scripts/demo/model_mapping.py` - JSON file to Pydantic model mapping

**Unit Tests Required:**
- `tests/unit/demo/test_validation.py`
  - `test_valid_json_passes_pydantic`
  - `test_invalid_field_rejected`
  - `test_missing_required_field_error`
  - `test_unknown_field_rejected`
- `tests/unit/demo/test_fk_registry.py`
  - `test_fk_lookup_success`
  - `test_fk_lookup_failure_reports_context`

**Story Points:** 5

---

### Story 0.8.2: Seed Data Loader Script (load-demo-data.py)

**Status:** To Do | **Depends On:** Story 0.8.1

As a **developer setting up a demo environment**,
I want a script that loads E2E seed data with full validation,
So that I can quickly populate a local MongoDB with valid demo data.

**ADR:** ADR-020 - Demo Data Strategy with Pydantic Validation

**Acceptance Criteria:**

**Given** the validation infrastructure exists (Story 0.8.1)
**When** I run `python scripts/demo/load-demo-data.py --source e2e`
**Then** Phase 1 runs: all JSON files validated through Pydantic models
**And** Phase 2 runs: all foreign keys validated against FK registry
**And** Phase 3 runs: data loaded to MongoDB in dependency order

**Given** validation fails in Phase 1 or 2
**When** the script runs
**Then** it stops before any database write
**And** all errors are printed with context
**And** exit code is non-zero

**Given** the script runs successfully
**When** I check the output
**Then** it shows: files processed, records loaded per collection, total time
**And** MongoDB collections contain the seed data

**Given** I run the script twice
**When** the data already exists
**Then** upsert pattern is used (no duplicates)
**And** existing records are updated if changed

**Given** I want to load from a custom directory
**When** I run `python scripts/demo/load-demo-data.py --source custom --path ./my-data/`
**Then** the script validates and loads from the custom path

**Deliverables:**
- `scripts/demo/load-demo-data.py` - Main loader script
- `scripts/demo/loader.py` - Database loading logic (reuses MongoDBDirectClient pattern)

**Unit Tests Required:**
- `tests/unit/demo/test_loader.py`
  - `test_load_order_respects_dependencies`
  - `test_validation_failure_prevents_load`
  - `test_upsert_pattern_no_duplicates`

**E2E Test Impact:**
- Script should work with existing E2E seed data
- Run validation: `python scripts/demo/load-demo-data.py --source e2e --dry-run`

**Story Points:** 5

---

### Story 0.8.3: Polyfactory Generator Framework

**Status:** To Do | **Depends On:** Story 0.8.1

As a **developer needing realistic test data**,
I want a Polyfactory-based generator framework,
So that I can generate large volumes of valid data from Pydantic models.

**ADR:** ADR-020 - Demo Data Strategy with Pydantic Validation

**Acceptance Criteria:**

**Given** Pydantic models define domain entities
**When** I check the generator module
**Then** Polyfactory factories exist for each model:
  - `RegionFactory` - Generates valid Region instances
  - `FactoryEntityFactory` - Generates valid Factory instances
  - `CollectionPointFactory` - Generates valid CollectionPoint instances
  - `FarmerFactory` - Generates valid Farmer instances
  - `SourceConfigFactory` - Generates valid SourceConfig instances

**Given** a factory generates an entity
**When** the entity has foreign keys
**Then** the factory accepts FK values as parameters
**And** default values reference the FK registry

**Given** Kenya-specific data is needed
**When** I check factory configurations
**Then** Faker locales include "sw_KE" for Swahili names
**And** phone numbers use "+254" prefix
**And** location coordinates are within Kenya bounds

**Given** I generate a Farmer
**When** the factory runs
**Then** the result passes Pydantic validation
**And** all required fields have realistic values

**Deliverables:**
- `tests/demo/generators/__init__.py` - Package init
- `tests/demo/generators/base.py` - Base factory with FK registry integration
- `tests/demo/generators/plantation.py` - Region, Factory, CollectionPoint, Farmer factories
- `tests/demo/generators/collection.py` - SourceConfig, QualityResult factories
- `tests/demo/generators/ai_model.py` - AIPrompt, AIModel factories

**Unit Tests Required:**
- `tests/unit/demo/generators/test_plantation.py`
  - `test_farmer_factory_produces_valid_model`
  - `test_factory_entity_factory_respects_region_fk`
  - `test_kenya_locale_phone_numbers`
- `tests/unit/demo/generators/test_collection.py`
  - `test_source_config_factory_valid`

**Story Points:** 5

---

### Story 0.8.4: Profile-Based Data Generation (generate-demo-data.py)

**Status:** To Do | **Depends On:** Story 0.8.3

As a **developer preparing demo environments**,
I want profile-based data generation with different volumes,
So that I can generate appropriate data for different scenarios.

**ADR:** ADR-020 - Demo Data Strategy with Pydantic Validation

**Acceptance Criteria:**

**Given** profiles are defined in YAML
**When** I check `tests/demo/profiles/`
**Then** I find:
  - `minimal.yaml` - 1 region, 1 factory, 3 farmers
  - `demo.yaml` - 2 regions, 3 factories, 50 farmers with quality history
  - `demo-large.yaml` - 4 regions, 10 factories, 200+ farmers

**Given** I run `python scripts/demo/generate-demo-data.py --profile demo`
**When** generation completes
**Then** JSON files are written to `tests/demo/generated/demo/`
**And** files follow the same structure as E2E seed files
**And** all generated data passes Pydantic validation

**Given** I run with `--seed 12345`
**When** generation completes
**Then** the output is deterministic
**And** running again with same seed produces identical files

**Given** I run with `--load` flag
**When** generation completes
**Then** the generated data is also loaded to MongoDB
**And** validation runs before load (same as Story 0.8.2)

**Given** the demo profile is selected
**When** generation runs
**Then** quality history scenarios are included:
  - Improving farmer (3→4→5 star trajectory)
  - Declining farmer (4→3→2 star trajectory)
  - Consistent farmer (4 star stable)

**Deliverables:**
- `scripts/demo/generate-demo-data.py` - Main generator script
- `tests/demo/profiles/minimal.yaml` - Minimal profile
- `tests/demo/profiles/demo.yaml` - Demo profile with scenarios
- `tests/demo/profiles/demo-large.yaml` - Large volume profile

**Unit Tests Required:**
- `tests/unit/demo/test_generate.py`
  - `test_profile_loading`
  - `test_deterministic_with_seed`
  - `test_output_structure_matches_e2e`
- `tests/unit/demo/test_scenarios.py`
  - `test_improving_farmer_trajectory`
  - `test_declining_farmer_trajectory`

**E2E Test Impact:**
- Generated data should be loadable with load-demo-data.py
- Validation: `python scripts/demo/load-demo-data.py --source custom --path tests/demo/generated/demo/`

**Story Points:** 5

---

### Story 0.8.5: Demo Data Documentation & Usage Guide

**Status:** To Do | **Depends On:** Stories 0.8.2, 0.8.4

As a **new developer joining the project**,
I want clear documentation for demo data tooling,
So that I can quickly set up a working demo environment.

**ADR:** ADR-020 - Demo Data Strategy with Pydantic Validation

**Acceptance Criteria:**

**Given** a developer needs to set up a demo environment
**When** they read `docs/demo-data.md`
**Then** they find step-by-step instructions for:
  - Loading E2E seed data: `python scripts/demo/load-demo-data.py --source e2e`
  - Generating demo data: `python scripts/demo/generate-demo-data.py --profile demo --load`
  - Validating custom data: `python scripts/demo/load-demo-data.py --dry-run`

**Given** a developer wants to add new seed data
**When** they read the documentation
**Then** they understand:
  - JSON file structure requirements
  - Pydantic model locations
  - FK dependency order
  - Validation error interpretation

**Given** a developer wants to customize data generation
**When** they read the documentation
**Then** they understand:
  - Profile YAML structure
  - How to add new scenarios
  - How to extend factories

**Given** the README exists
**When** I check `scripts/demo/README.md`
**Then** it includes quick-start commands and links to full docs

**Deliverables:**
- `docs/demo-data.md` - Full documentation
- `scripts/demo/README.md` - Quick reference
- Updated `CLAUDE.md` with demo data section

**Story Points:** 2

---

## Summary

| Story | Description | ADR | Points | Status | Depends On |
|-------|-------------|-----|--------|--------|------------|
| 0.8.1 | Pydantic Validation Infrastructure | ADR-020 | 5 | To Do | - |
| 0.8.2 | Seed Data Loader Script | ADR-020 | 5 | To Do | 0.8.1 |
| 0.8.3 | Polyfactory Generator Framework | ADR-020 | 5 | To Do | 0.8.1 |
| 0.8.4 | Profile-Based Data Generation | ADR-020 | 5 | To Do | 0.8.3 |
| 0.8.5 | Documentation & Usage Guide | ADR-020 | 2 | To Do | 0.8.2, 0.8.4 |
| **Total** | | | **22** | | |

---

## Dependency Graph

```
Story 0.8.1 (Validation Infrastructure)
    │
    ├───────────────┬───────────────┐
    ▼               ▼               │
Story 0.8.2     Story 0.8.3         │
(Loader)        (Generators)        │
    │               │               │
    │               ▼               │
    │          Story 0.8.4          │
    │          (Generate CLI)       │
    │               │               │
    └───────────────┴───────────────┘
                    │
                    ▼
              Story 0.8.5
              (Documentation)
```

---

## Testing Strategy

### Unit Tests (Per Story)
Each story includes specific unit test requirements. Tests must:
- Be placed in `tests/unit/demo/`
- Use fixtures from `tests/conftest.py` (DO NOT override)
- Run with `pytest tests/unit/demo/ -v`

### Integration Validation
After completing Stories 0.8.2 and 0.8.4:
```bash
# Validate E2E seed data loads correctly
python scripts/demo/load-demo-data.py --source e2e --dry-run

# Generate demo data and validate
python scripts/demo/generate-demo-data.py --profile demo --seed 12345
python scripts/demo/load-demo-data.py --source custom --path tests/demo/generated/demo/ --dry-run

# Load to local MongoDB
python scripts/demo/load-demo-data.py --source e2e
```

---

## CI Requirements

All stories must pass CI before merge:
1. `ruff check . && ruff format --check .`
2. `pytest tests/unit/demo/ -v` (unit tests)
3. GitHub Actions CI workflow (on feature branch)

---

## Definition of Done

- [ ] Stories 0.8.1-0.8.5 implemented and merged
- [ ] All unit tests pass
- [ ] E2E seed data validates and loads successfully
- [ ] Generated demo data validates and loads successfully
- [ ] Documentation complete and reviewed
- [ ] CI pipelines green on all PRs
- [ ] ADR-020 marked as "Implemented"

---

**Total Story Points:** 22

**Estimated Duration:** 1-2 sprints
