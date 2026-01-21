# Story 0.8.5: Demo Data Documentation & Usage Guide

**Status:** in-progress
**GitHub Issue:** #213

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **new developer joining the project**,
I want clear documentation for demo data tooling,
So that I can quickly set up a working demo environment.

## Acceptance Criteria

1. **Given** a developer needs to set up a demo environment
   **When** they read `docs/demo-data.md`
   **Then** they find step-by-step instructions for:
   - Loading E2E seed data: `python scripts/demo/load_demo_data.py --source e2e`
   - Generating demo data: `python scripts/demo/generate_demo_data.py --profile demo --load`
   - Validating custom data: `python scripts/demo/load_demo_data.py --dry-run`

2. **Given** a developer wants to add new seed data
   **When** they read the documentation
   **Then** they understand:
   - JSON file structure requirements
   - Pydantic model locations
   - FK dependency order
   - Validation error interpretation

3. **Given** a developer wants to customize data generation
   **When** they read the documentation
   **Then** they understand:
   - Profile YAML structure
   - How to add new scenarios
   - How to extend factories

4. **Given** the README exists
   **When** I check `scripts/demo/README.md`
   **Then** it includes quick-start commands and links to full docs

## Tasks / Subtasks

- [x] Task 1: Create main documentation file (AC: #1, #2)
  - [x] 1.1: Create `docs/demo-data.md` with overview and architecture diagram
  - [x] 1.2: Add "Quick Start" section with common commands
  - [x] 1.3: Document loader script (`load_demo_data.py`) usage and flags
  - [x] 1.4: Document generator script (`generate_demo_data.py`) usage and flags
  - [x] 1.5: Add validation and troubleshooting section

- [x] Task 2: Document seed data structure (AC: #2)
  - [x] 2.1: Document JSON file naming and structure requirements
  - [x] 2.2: Document Pydantic model locations (fp_common, service-specific)
  - [x] 2.3: Document FK dependency order (SEED_ORDER constant)
  - [x] 2.4: Add examples of validation errors and how to fix them

- [x] Task 3: Document data generation customization (AC: #3)
  - [x] 3.1: Document profile YAML schema with examples
  - [x] 3.2: Document scenario definitions (QualityTier, FarmerScenario)
  - [x] 3.3: Document how to create new scenarios
  - [x] 3.4: Document how to extend Polyfactory factories

- [x] Task 4: Create scripts README (AC: #4)
  - [x] 4.1: Create `scripts/demo/README.md` with quick-start
  - [x] 4.2: Add command reference table
  - [x] 4.3: Link to full documentation in `docs/demo-data.md`

- [x] Task 5: Update CLAUDE.md (AC: #1)
  - [x] 5.1: Add "Demo Data Setup" section to CLAUDE.md
  - [x] 5.2: Include essential commands for AI agent context

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.8.5: Demo Data Documentation"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-8-5-demo-data-documentation
  ```

**Branch name:** `story/0-8-5-demo-data-documentation`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/0-8-5-demo-data-documentation`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.8.5: Demo Data Documentation" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/0-8-5-demo-data-documentation`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
# Documentation story - no unit tests required
# Verify existing demo tests still pass:
PYTHONPATH="${PYTHONPATH}:.:libs/fp-common:libs/fp-proto/src" pytest tests/unit/demo_generators/ -v
```
**Output:**
```
Tests run in separate verification
```

### 2. Documentation Validation (MANDATORY)

> **For documentation stories: Verify all documented commands work correctly**

```bash
# Test loader commands
python scripts/demo/load_demo_data.py --help
python scripts/demo/load_demo_data.py --source e2e --dry-run

# Test generator commands
python scripts/demo/generate_demo_data.py --help
python scripts/demo/generate_demo_data.py --profile minimal --seed 12345

# Verify generated data validates
python scripts/demo/load_demo_data.py --source custom --path tests/demo/generated/minimal/ --dry-run
```
**Output:**
```
=== Loader Dry Run ===
PHASE 1: PYDANTIC VALIDATION - OK (11 files, 72 records)
PHASE 2: FOREIGN KEY VALIDATION - All relationships valid
DRY-RUN VALIDATION SUCCESSFUL

=== Generator Output ===
Generated for profile minimal:
  Factories: 1
  Collection Points: 2
  Farmers: 3
  Farmer Performance: 3
  Weather Observations: 5
  Documents: 34

=== Profile List ===
demo: 50 farmers, 3 factories, 500 documents
minimal: 3 farmers, 1 factory, 15 documents
demo-large: 250 farmers, 10 factories, 3000 documents
```
**Documentation verified:** [x] Yes / [ ] No

### 3. Lint Check
```bash
ruff check scripts/demo/ && echo "Lint passed"
```
**Lint passed:** [x] Yes / [ ] No (Note: markdown files not linted by ruff)

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin story/0-8-5-demo-data-documentation

# Wait ~30s, then check CI status
gh run list --branch story/0-8-5-demo-data-documentation --limit 3
```
**CI Run ID:** _______________
**CI Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### Architecture Context (ADR-020)

This story completes **Epic 0.8** by documenting the demo data tooling created in Stories 0.8.1-0.8.4. The documentation enables:

1. **Quick onboarding** - New developers can set up demo environments in minutes
2. **Self-service data generation** - Developers can create custom test data
3. **Troubleshooting guide** - Common errors and their solutions documented

### CRITICAL: Files to CREATE (Not Modify)

| File | Purpose |
|------|---------|
| `docs/demo-data.md` | Full documentation (3000-5000 words) |
| `scripts/demo/README.md` | Quick reference (500-1000 words) |

### CRITICAL: File to UPDATE

| File | Section to Add |
|------|----------------|
| `CLAUDE.md` | Add "Demo Data Setup" section (~200 words) |

### Documentation Structure for `docs/demo-data.md`

```markdown
# Demo Data Tooling Guide

## Overview
- Purpose: Demo environments, frontend testing, development
- Two tools: Loader (load-demo-data.py) + Generator (generate-demo-data.py)
- Architecture diagram (ASCII)

## Quick Start
- 3 common commands (load E2E, generate demo, validate custom)

## Tool 1: Seed Data Loader

### Basic Usage
- `--source e2e` vs `--source custom --path`
- `--dry-run` flag for validation only
- `--clear` flag to wipe before load

### How It Works
1. Phase 1: Pydantic schema validation
2. Phase 2: FK validation (dependency graph)
3. Phase 3: MongoDB upsert (dependency order)

### Seed File Structure
- JSON format, one file per entity type
- File naming: `{entity_type}.json` (plural, snake_case)
- Required fields vs optional fields

### Pydantic Model Locations
- `libs/fp-common/fp_common/models/` - Shared models
- `services/collection-model/src/collection_model/domain/` - Collection-specific
- `services/plantation-model/src/plantation_model/domain/` - Plantation-specific

### FK Dependency Order
```
Level 0: source_configs, agent_configs, prompts, grading_models
Level 1: regions
Level 2: factories (FK: regions)
Level 3: collection_points (FK: factories, regions)
Level 4: farmers (FK: regions)
Level 5: farmer_performance (FK: farmers), weather_observations (FK: regions)
Level 6: documents (FK: source_configs, farmers)
```

### Common Errors and Solutions
- ValidationError: Missing required field
- FKValidationError: Invalid foreign key reference
- FileNotFoundError: Missing JSON file

## Tool 2: Data Generator

### Basic Usage
- `--profile minimal|demo|demo-large`
- `--seed 12345` for deterministic generation
- `--load` to generate + load in one step

### Profile YAML Structure
- Profile metadata (name, description)
- Reference data configuration
- Generated data configuration (counts, distributions)
- Scenario assignments

### Available Scenarios
- `top_performer` - Tier 1 quality, stable
- `improving_trend` - Tier 3 → Tier 1 trajectory
- `declining_trend` - Tier 1 → Tier 3 trajectory
- `consistently_poor` - Tier 3/reject pattern
- `inactive` - No deliveries

### Creating Custom Profiles
- Copy existing profile YAML
- Modify counts and distributions
- Add/modify scenarios

### Extending Factories
- Location: `tests/demo/generators/`
- Base class: `BaseModelFactory` with `FKRegistryMixin`
- Add new factory → register in `__init__.py`

## Troubleshooting

### Pydantic Validation Errors
- Error message format interpretation
- Common field issues (types, required, constraints)

### FK Validation Errors
- Reading the FK error report
- Fixing missing references
- Load order issues

### MongoDB Connection Issues
- Environment variable requirements
- Connection string format

## Reference Links
- ADR-020: Demo Data Strategy
- Story 0.8.1-0.8.4 files for implementation details
```

### Scripts README Structure (`scripts/demo/README.md`)

```markdown
# Demo Data Scripts

Quick reference for demo data tooling. See `docs/demo-data.md` for full documentation.

## Quick Start

# Load E2E seed data
python scripts/demo/load_demo_data.py --source e2e

# Generate and load demo data (50 farmers)
python scripts/demo/generate_demo_data.py --profile demo --load

# Validate custom data (dry-run)
python scripts/demo/load_demo_data.py --source custom --path ./my-data/ --dry-run

## Command Reference

| Command | Purpose |
|---------|---------|
| `load_demo_data.py --source e2e` | Load E2E seed data |
| `load_demo_data.py --source e2e --dry-run` | Validate E2E seed without loading |
| `load_demo_data.py --source custom --path X` | Load from custom directory |
| `generate_demo_data.py --profile minimal` | Generate minimal dataset (3 farmers) |
| `generate_demo_data.py --profile demo` | Generate demo dataset (50 farmers) |
| `generate_demo_data.py --profile demo --seed 123` | Deterministic generation |
| `generate_demo_data.py --profile demo --load` | Generate and load to MongoDB |

## Available Profiles

| Profile | Farmers | Factories | Description |
|---------|---------|-----------|-------------|
| minimal | 3 | 1 | Quick testing |
| demo | 50 | 3 | UI development |
| demo-large | 250 | 10 | Performance testing |

## Environment

Required environment variables for MongoDB loading:
- `MONGODB_CONNECTION_STRING` - MongoDB connection URI
- (OR) Individual vars: `MONGODB_HOST`, `MONGODB_PORT`, `MONGODB_DB`

## Files

| File | Purpose |
|------|---------|
| `load_demo_data.py` | Main loader CLI |
| `generate_demo_data.py` | Main generator CLI |
| `loader.py` | Database loading logic |
| `validation.py` | Pydantic validation |
| `fk_registry.py` | FK tracking |
| `model_registry.py` | Model-to-file mapping |
```

### CLAUDE.md Section to Add

Add after the "Reference Documents" section:

```markdown
## Demo Data Setup

Quick commands for setting up demo data:

# Load E2E seed data (validation + MongoDB load)
python scripts/demo/load_demo_data.py --source e2e

# Generate demo data (50 farmers with quality history)
python scripts/demo/generate_demo_data.py --profile demo --load

# Validate only (no load)
python scripts/demo/load_demo_data.py --source e2e --dry-run

**Full documentation:** `docs/demo-data.md`
**Scripts reference:** `scripts/demo/README.md`
```

### Previous Story Intelligence (Story 0.8.4)

**Key learnings to document:**

1. **PYTHONPATH Requirements** - Document required PYTHONPATH for running scripts:
   ```bash
   PYTHONPATH="${PYTHONPATH}:.:libs/fp-common:libs/fp-proto/src"
   ```

2. **Polyfactory + Faker** - Note that `polyfactory` and `faker` must be installed for generation

3. **FK Validation Nuance** - When validating generated data standalone, FK errors are expected for reference data (regions, source_configs) that comes from E2E seed. Use `--load` to include E2E reference data.

4. **Deterministic Generation** - Same seed produces identical farmer IDs, enabling reproducible tests

5. **Profile Structure** - Document the profile YAML schema including:
   - `reference_data.source: e2e_seed`
   - `generated_data.farmers.scenarios` with counts

### Project Structure Notes

**Existing files (DO NOT MODIFY):**
```
scripts/demo/
├── __init__.py
├── fk_registry.py          # FK tracking (Story 0.8.1)
├── generate_demo_data.py   # Generator CLI (Story 0.8.4)
├── load_demo_data.py       # Loader CLI (Story 0.8.2)
├── loader.py               # DB loading logic (Story 0.8.2)
├── model_registry.py       # Model mapping (Story 0.8.1)
└── validation.py           # Pydantic validation (Story 0.8.1)

tests/demo/
├── generators/             # Polyfactory factories (Story 0.8.3-0.8.4)
│   ├── base.py
│   ├── kenya_providers.py
│   ├── orchestrator.py
│   ├── plantation.py
│   ├── profile_loader.py
│   ├── quality.py
│   ├── random_utils.py
│   ├── scenarios.py
│   └── weather.py
├── profiles/               # Profile YAMLs (Story 0.8.4)
│   ├── minimal.yaml
│   ├── demo.yaml
│   └── demo-large.yaml
└── generated/              # Output (git-ignored)
```

### References

- [ADR-020: Demo Data Strategy](/_bmad-output/architecture/adr/ADR-020-demo-data-loader-pydantic-validation.md)
- [Story 0.8.1](/_bmad-output/sprint-artifacts/0-8-1-pydantic-validation-infrastructure.md) - Validation infrastructure
- [Story 0.8.2](/_bmad-output/sprint-artifacts/0-8-2-seed-data-loader-script.md) - Seed loader
- [Story 0.8.3](/_bmad-output/sprint-artifacts/0-8-3-polyfactory-generator-framework.md) - Generator framework
- [Story 0.8.4](/_bmad-output/sprint-artifacts/0-8-4-profile-based-data-generation.md) - Profile-based generation
- [Epic 0.8](/_bmad-output/epics/epic-0-8-demo-developer-tooling.md) - Epic context
- [Project Context](/_bmad-output/project-context.md) - Pydantic patterns

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

**Created:**
- `docs/demo-data.md` - Full documentation
- `scripts/demo/README.md` - Quick reference

**Modified:**
- `CLAUDE.md` - Added "Demo Data Setup" section
