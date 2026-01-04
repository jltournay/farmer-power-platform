# Story 0.75.2: Pydantic Model for Prompt + Mongo Repository

**Status:** ready-for-dev
**GitHub Issue:** <!-- Auto-created by dev-story workflow -->

## Story

As a **developer**,
I want Pydantic models and repository pattern for prompt storage,
So that prompts are type-safe and properly managed in MongoDB.

## Acceptance Criteria

1. **AC1: Prompt Pydantic Model** - `Prompt` Pydantic model exists with versioning fields matching architecture spec
2. **AC2: Prompt Content Model** - `PromptContent` nested model with system_prompt, template, output_schema, few_shot_examples
3. **AC3: Prompt Metadata Model** - `PromptMetadata` nested model with author, timestamps, changelog, git_commit
4. **AC4: A/B Test Config Model** - `PromptABTest` nested model with enabled, traffic_percentage, test_id
5. **AC5: Status Enum** - `PromptStatus` enum with draft, staged, active, archived values
6. **AC6: Repository CRUD** - `PromptRepository` with async CRUD operations (create, get_by_id, update, delete, list)
7. **AC7: Get Active Prompt** - Repository method to get the currently active prompt for a prompt_id
8. **AC8: Version Queries** - Repository methods for version-based queries (get_by_version, list_versions)
9. **AC9: MongoDB Collection** - Data stored in `ai_model.prompts` collection
10. **AC10: MongoDB Indexes** - Compound indexes on (prompt_id, status) and (prompt_id, version)
11. **AC11: Unit Tests** - Unit tests for all Pydantic models and repository methods (≥20 tests)
12. **AC12: CI Passes** - All lint checks and unit tests pass in CI

## Tasks / Subtasks

- [ ] **Task 1: Prompt Domain Models** (AC: #1, #2, #3, #4, #5)
  - [ ] Create `services/ai-model/src/ai_model/domain/` directory if not exists
  - [ ] Create `services/ai-model/src/ai_model/domain/__init__.py`
  - [ ] Create `services/ai-model/src/ai_model/domain/prompt.py` with:
    - [ ] `PromptStatus` enum (draft, staged, active, archived)
    - [ ] `PromptContent` Pydantic model (system_prompt, template, output_schema, few_shot_examples)
    - [ ] `PromptMetadata` Pydantic model (author, created_at, updated_at, changelog, git_commit)
    - [ ] `PromptABTest` Pydantic model (enabled, traffic_percentage, test_id)
    - [ ] `Prompt` Pydantic model with all fields per architecture spec

- [ ] **Task 2: Prompt Repository** (AC: #6, #7, #8, #9, #10)
  - [ ] Create `services/ai-model/src/ai_model/infrastructure/repositories/` directory
  - [ ] Create `services/ai-model/src/ai_model/infrastructure/repositories/__init__.py`
  - [ ] Create `services/ai-model/src/ai_model/infrastructure/repositories/base.py` (copy pattern from plantation-model)
  - [ ] Create `services/ai-model/src/ai_model/infrastructure/repositories/prompt_repository.py` with:
    - [ ] Inherit from `BaseRepository[Prompt]`
    - [ ] `COLLECTION_NAME = "prompts"`
    - [ ] `get_active(prompt_id: str) -> Prompt | None` - get currently active prompt
    - [ ] `get_by_version(prompt_id: str, version: str) -> Prompt | None`
    - [ ] `list_versions(prompt_id: str) -> list[Prompt]`
    - [ ] `list_by_agent(agent_id: str) -> list[Prompt]`
    - [ ] `ensure_indexes()` - create compound indexes

- [ ] **Task 3: Unit Tests - Models** (AC: #11)
  - [ ] Create `tests/unit/ai_model/test_prompt_model.py` with tests for:
    - [ ] PromptStatus enum values
    - [ ] PromptContent model validation
    - [ ] PromptMetadata model validation
    - [ ] PromptABTest model validation
    - [ ] Prompt model validation (complete model)
    - [ ] Prompt model serialization (model_dump)
    - [ ] Prompt model deserialization (model_validate)
    - [ ] Invalid field rejection tests

- [ ] **Task 4: Unit Tests - Repository** (AC: #11)
  - [ ] Create `tests/unit/ai_model/test_prompt_repository.py` with tests for:
    - [ ] create() - creates new prompt
    - [ ] get_by_id() - retrieves prompt by ID
    - [ ] update() - updates prompt fields
    - [ ] delete() - deletes prompt
    - [ ] list() - lists prompts with pagination
    - [ ] get_active() - gets active prompt for prompt_id
    - [ ] get_by_version() - gets specific version
    - [ ] list_versions() - lists all versions of a prompt
    - [ ] list_by_agent() - lists prompts for an agent
    - [ ] ensure_indexes() - creates proper indexes

- [ ] **Task 5: CI Verification** (AC: #12)
  - [ ] Run `ruff check services/ai-model/` - lint passes
  - [ ] Run `ruff format --check services/ai-model/` - format passes
  - [ ] Run unit tests locally with ≥20 tests passing
  - [ ] Push and verify CI passes

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.75.2: Pydantic Model for Prompt + Mongo Repository"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-75-2-pydantic-model-prompt-mongo-repository
  ```

**Branch name:** `story/0-75-2-pydantic-model-prompt-mongo-repository`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/0-75-2-pydantic-model-prompt-mongo-repository`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.75.2: Pydantic Model for Prompt + Mongo Repository" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/0-75-2-pydantic-model-prompt-mongo-repository`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
PYTHONPATH="${PYTHONPATH}:.:services/ai-model/src:libs/fp-common:libs/fp-proto/src" pytest tests/unit/ai_model/ -v
```
**Output:**
```
(paste test summary here - must show ≥20 tests passing)
```

### 2. E2E Tests (MANDATORY)

> **Note:** This story is data model only. E2E tests for AI Model will be added in Story 0.75.18.
> For this story, verify existing E2E tests still pass (no regressions).

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
(paste E2E test output here - story is NOT ready for review without this)
```
**E2E passed:** [ ] Yes / [ ] No

### 3. Lint Check
```bash
ruff check services/ai-model/ && ruff format --check services/ai-model/
```
**Lint passed:** [ ] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin story/0-75-2-pydantic-model-prompt-mongo-repository

# Wait ~30s, then check CI status
gh run list --branch story/0-75-2-pydantic-model-prompt-mongo-repository --limit 3
```
**Quality CI Run ID:** _______________
**Quality CI Status:** [ ] Passed / [ ] Failed
**E2E CI Run ID:** _______________
**E2E CI Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### Architecture Reference

**Source:** `_bmad-output/architecture/ai-model-architecture/prompt-management.md`
**Source:** `_bmad-output/architecture/ai-model-architecture/key-decisions.md`

### Key Decision: Single Collection

> **Decision:** Single `prompts` collection with `prompt_type` discriminator field. All 5 agent types share one collection. See `key-decisions.md`.

This enables:
- Simpler queries across all prompts
- One repository class instead of multiple
- MongoDB schema-flexible storage

### Prompt Document Schema (MUST MATCH)

```yaml
# MongoDB: ai_model.prompts collection
prompt_document:
  prompt_id: string              # "disease-diagnosis" - logical identifier
  agent_id: string               # "diagnose-quality-issue" - links to agent config
  version: string                # "2.1.0" (semver)
  status: enum                   # "draft" | "staged" | "active" | "archived"

  content:
    system_prompt: string        # Full system prompt text
    template: string             # Template with {{variables}}
    output_schema: object        # JSON schema for validation
    few_shot_examples: array     # Optional examples

  metadata:
    author: string
    created_at: datetime
    updated_at: datetime
    changelog: string            # What changed in this version
    git_commit: string           # Source commit SHA

  ab_test:
    enabled: boolean
    traffic_percentage: number   # 0-100
    test_id: string              # For metrics grouping
```

### MongoDB Indexes (CRITICAL)

```python
# Compound indexes to create in ensure_indexes()
await collection.create_index(
    [("prompt_id", 1), ("status", 1)],
    name="idx_prompt_id_status",
)
await collection.create_index(
    [("prompt_id", 1), ("version", 1)],
    unique=True,  # Each version is unique
    name="idx_prompt_id_version_unique",
)
await collection.create_index(
    "agent_id",
    name="idx_agent_id",
)
```

### Status Lifecycle

```
draft → staged → active → archived
              ↘ (A/B test) ↗
```

- `draft`: Development, agent_id validation skipped
- `staged`: Ready for promotion, requires valid agent_id
- `active`: Currently in use (only one per prompt_id)
- `archived`: Historical version, kept for audit

### Reference Implementation Patterns

**BaseRepository Pattern:**
- Source: `services/plantation-model/src/plantation_model/infrastructure/repositories/base.py`
- Uses Generic[T] for type safety
- Async all I/O operations
- Uses `model_dump()` and `model_validate()` (Pydantic 2.0)
- Uses `_id` = `id` pattern for MongoDB

**Domain Model Pattern:**
- Source: `services/plantation-model/src/plantation_model/domain/models.py`
- Pydantic BaseModel with Field() for descriptions
- datetime with `default_factory=lambda: datetime.now(UTC)`
- Use `Optional[T]` not `T | None` for compatibility

### What This Story Does NOT Include

| Not in Scope | Implemented In |
|--------------|----------------|
| Cache layer | Story 0.75.4 |
| CLI tooling | Story 0.75.6 |
| Agent config validation | Story 0.75.3 (agent configs first) |
| A/B test logic | Story 0.75.6 (CLI implements) |

### Testing Strategy

**Unit Tests Required (≥20 tests):**

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_prompt_model.py` | 10+ | All Pydantic models, enums, serialization |
| `test_prompt_repository.py` | 10+ | All CRUD + specialized queries |

**Fixtures to Use:**
- Use `mock_mongodb_client` from root `tests/conftest.py`
- **DO NOT override** `mock_mongodb_client` in local conftest.py
- Follow pattern from `tests/unit/ai_model/conftest.py` (created in 0.75.1)

### Previous Story Learnings (0.75.1)

From Story 0.75.1 code review:

1. **Test all infrastructure modules** - Code review required adding tests for grpc_server, mongodb, tracing
2. **Follow plantation-model patterns exactly** - Configuration, health endpoints, repository patterns
3. **30 tests total** were required after code review additions
4. **Proto stubs already exist** - No regeneration needed

### Git Commits Reference

Recent commits showing patterns:
```
793fdd6 docs(arch): Add MongoDB collection strategy and prompt-agent validation rules
3f64c70 Story 0.75.1: AI Model Setup (#90)
```

### Anti-Patterns to AVOID

| Anti-Pattern | Correct Approach |
|--------------|------------------|
| `dict[str, Any]` returns | Return `Prompt` model from repository |
| Synchronous I/O | ALL database calls must be async |
| `dict()` method | Use `model_dump()` (Pydantic 2.0) |
| `parse_obj()` | Use `model_validate()` (Pydantic 2.0) |
| Relative imports | Use absolute imports only |
| Bare `except:` | Catch specific exceptions |

### File Structure to Create

```
services/ai-model/src/ai_model/
├── domain/
│   ├── __init__.py           # Export Prompt, PromptStatus, etc.
│   └── prompt.py             # All prompt-related models
└── infrastructure/
    └── repositories/
        ├── __init__.py       # Export PromptRepository
        ├── base.py           # BaseRepository[T] pattern
        └── prompt_repository.py  # PromptRepository class
```

### References

- [Source: `_bmad-output/project-context.md`] - Critical rules
- [Source: `_bmad-output/architecture/ai-model-architecture/prompt-management.md`] - Prompt schema and lifecycle
- [Source: `_bmad-output/architecture/ai-model-architecture/key-decisions.md`] - Single collection decision
- [Source: `_bmad-output/epics/epic-0-75-ai-model.md`] - Story requirements
- [Source: `services/plantation-model/src/plantation_model/infrastructure/repositories/base.py`] - BaseRepository pattern
- [Source: `services/plantation-model/src/plantation_model/infrastructure/repositories/farmer_repository.py`] - Repository example

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
