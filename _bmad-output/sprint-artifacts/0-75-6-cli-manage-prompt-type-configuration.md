# Story 0.75.6: CLI to Manage Prompt Type Configuration

**Status:** in-progress
**GitHub Issue:** #99

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **platform operator**,
I want a CLI to manage prompt configurations,
So that prompts can be deployed and versioned without code changes.

## Acceptance Criteria

1. **AC1: CLI Scaffold** - `fp-prompt-config` CLI created using Typer framework in `scripts/prompt-config/`
2. **AC2: Deploy Command** - `deploy` command uploads prompt YAML to MongoDB with validation
3. **AC3: Validate Command** - `validate` command validates prompt YAML against schema without deploying
4. **AC4: List Command** - `list` command shows all prompts with status filter (draft/staged/active/archived)
5. **AC5: Get Command** - `get` command retrieves specific prompt by prompt_id (optionally version)
6. **AC6: Stage Command** - `stage` command creates new version with status=staged
7. **AC7: Promote Command** - `promote` command transitions staged prompt to active (archives previous active)
8. **AC8: Rollback Command** - `rollback` command reverts to previous version by archiving current and promoting specified version
9. **AC9: Versions Command** - `versions` command lists all versions of a prompt_id with status
10. **AC10: Agent Validation** - When publishing with status staged/active, validate that agent_id exists in agent_configs collection
11. **AC11: Draft Skip Validation** - Draft status prompts skip agent_id validation (development flexibility)
12. **AC12: YAML Schema** - YAML prompt definition format matches Prompt Pydantic model (prompt_id, agent_id, version, status, content, metadata, ab_test)
13. **AC13: Help Text** - Built-in `--help` with usage examples for each command
14. **AC14: Error Handling** - Exit code 0 = success, 1 = error; Error messages to stderr with format `Error: <message>`
15. **AC15: Verbosity Flags** - `--verbose` for detailed output, `--quiet` for minimal output (errors only)
16. **AC16: Rich Output** - Use Rich library for formatted tables and colored output
17. **AC17: Environment Config** - Support `--env` flag for environment selection (dev/staging/prod) via MongoDB URI
18. **AC18: Unit Tests** - Unit tests for CLI commands (minimum 25 tests)
19. **AC19: CI Passes** - All lint checks and unit tests pass in CI

## Tasks / Subtasks

- [x] **Task 1: Create CLI Package Structure** (AC: #1)
  - [x] Create `scripts/prompt-config/` directory
  - [x] Create `scripts/prompt-config/pyproject.toml` with dependencies (typer, rich, motor, pydantic)
  - [x] Create `scripts/prompt-config/src/fp_prompt_config/__init__.py`
  - [x] Create `scripts/prompt-config/src/fp_prompt_config/cli.py` - main CLI entry point
  - [x] Create `scripts/prompt-config/src/fp_prompt_config/settings.py` - environment configuration
  - [x] Follow pattern from `scripts/source-config/` for structure

- [x] **Task 2: Implement Settings** (AC: #17)
  - [x] Create `Settings` Pydantic BaseSettings class
  - [x] Environment-based MongoDB URI: `MONGODB_URI_{DEV,STAGING,PROD}`
  - [x] Database name: `ai_model`
  - [x] Collection: `prompts` and `agent_configs` (for validation)
  - [x] Support `--env` flag to select environment

- [x] **Task 3: Create MongoDB Client** (AC: #2)
  - [x] Create `scripts/prompt-config/src/fp_prompt_config/client.py`
  - [x] Implement async `PromptClient` class using motor
  - [x] Reuse `PromptRepository` pattern from AI Model service
  - [x] Implement `connect()` and `disconnect()` methods
  - [x] Implement prompt CRUD operations matching repository pattern

- [x] **Task 4: Implement Validate Command** (AC: #3)
  - [x] Create validator module `scripts/prompt-config/src/fp_prompt_config/validator.py`
  - [x] Load YAML file and validate against `Prompt` Pydantic model
  - [x] Check required fields: prompt_id, agent_id, version, content.system_prompt, content.template
  - [x] Validate version format (semver: X.Y.Z)
  - [x] Return validation errors with line numbers where possible
  - [x] Use `rich.console.Console` for colored output

- [x] **Task 5: Implement Deploy Command** (AC: #2, #10, #11)
  - [x] Load and validate YAML file
  - [x] Parse YAML into `Prompt` Pydantic model
  - [x] **If status is staged/active**: Use `get_active(agent_id)` to verify agent exists (NOT `get_by_id`)
  - [x] **If status is draft**: Skip agent validation
  - [x] Generate document ID: `{prompt_id}:{version}`
  - [x] Check if version already exists (conflict error)
  - [x] Insert document to MongoDB
  - [x] Print success message with prompt_id and version
  - [x] Support `--dry-run` flag to show what would be deployed without making changes

- [x] **Task 6: Implement List Command** (AC: #4)
  - [x] Query prompts collection
  - [x] Support `--status` filter (draft/staged/active/archived)
  - [x] Support `--agent-id` filter
  - [x] Display as Rich table with columns: prompt_id, version, status, agent_id, updated_at
  - [x] Sort by prompt_id, then version descending

- [x] **Task 7: Implement Get Command** (AC: #5)
  - [x] Accept `--prompt-id` (required) and `--version` (optional)
  - [x] If no version: get active version (fallback to latest staged)
  - [x] Display full prompt as formatted YAML
  - [x] Use `--output` flag for file output

- [x] **Task 8: Implement Stage Command** (AC: #6, #10)
  - [x] Load YAML file with new version content
  - [x] Validate YAML against schema
  - [x] Validate agent_id exists using `get_active(agent_id)` (NOT `get_by_id`)
  - [x] Set status to "staged"
  - [x] Insert as new document (version must be unique)
  - [x] Print staged version details

- [x] **Task 9: Implement Promote Command** (AC: #7)
  - [x] Accept `--prompt-id` (required)
  - [x] Find staged version for prompt_id
  - [x] Error if no staged version exists
  - [x] Use MongoDB transaction (see Dev Notes for motor session pattern):
    1. Archive current active version (if exists)
    2. Update staged version status to active
  - [x] Print promotion details

- [x] **Task 10: Implement Rollback Command** (AC: #8)
  - [x] Accept `--prompt-id` (required) and `--to-version` (required)
  - [x] Find specified version (must exist)
  - [x] Use MongoDB transaction (see Dev Notes for motor session pattern):
    1. Archive current active version
    2. Create new version from rollback target with status=active
  - [x] Increment version (e.g., 1.2.0 → 1.2.1 with rollback note in changelog)
  - [x] Print rollback details

- [x] **Task 11: Implement Versions Command** (AC: #9)
  - [x] Accept `--prompt-id` (required)
  - [x] Query all versions for prompt_id
  - [x] Display as Rich table with columns: version, status, updated_at, author
  - [x] Sort by version descending
  - [x] Highlight active version

- [x] **Task 12: Add Help and Verbosity** (AC: #13, #14, #15)
  - [x] Add comprehensive help text for each command with examples
  - [x] Implement `--verbose` flag for detailed output
  - [x] Implement `--quiet` flag for minimal output
  - [x] Error output to stderr with `Error:` prefix
  - [x] Exit codes: 0 (success), 1 (error)

- [x] **Task 13: Unit Tests - Validator** (AC: #18)
  - [x] Create `tests/unit/scripts/prompt_config/test_validator.py`
  - [x] Test valid YAML validation passes
  - [x] Test missing required fields fails
  - [x] Test invalid version format fails
  - [x] Test malformed YAML fails

- [x] **Task 14: Unit Tests - CLI Commands** (AC: #18)
  - [x] Create `tests/unit/scripts/prompt_config/test_cli.py`
  - [x] Mock MongoDB client for all tests
  - [x] Test `validate` command with valid/invalid files
  - [x] Test `deploy` command with agent validation
  - [x] Test `deploy` command draft skips validation
  - [x] Test `list` command with status filters
  - [x] Test `get` command with/without version
  - [x] Test `stage` command
  - [x] Test `promote` command (staged → active)
  - [x] Test `rollback` command
  - [x] Test `versions` command

- [x] **Task 15: Unit Tests - Error Handling** (AC: #18)
  - [x] Test missing file error
  - [x] Test invalid environment error
  - [x] Test MongoDB connection error
  - [x] Test duplicate version error
  - [x] Test agent_id not found error

- [x] **Task 16: Update CI Configuration** (AC: #19)
  - [x] Add `scripts/prompt-config/src` to PYTHONPATH in `.github/workflows/ci.yaml`
  - [x] Ensure tests run with proper paths

- [ ] **Task 17: E2E Verification** (AC: #19)
  - [ ] Run full E2E test suite with `--build` flag
  - [ ] Verify no regressions
  - [ ] Capture test output in story file

- [ ] **Task 18: CI Verification** (AC: #19)
  - [ ] Run `ruff check .` - lint passes
  - [ ] Run `ruff format --check .` - format passes
  - [ ] Push and verify CI passes
  - [ ] Trigger E2E CI workflow and verify passes

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [x] GitHub Issue exists or created: `gh issue create --title "Story 0.75.6: CLI to Manage Prompt Type Configuration"`
- [x] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/0-75-6-cli-manage-prompt-type-configuration
  ```

**Branch name:** `feature/0-75-6-cli-manage-prompt-type-configuration`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin feature/0-75-6-cli-manage-prompt-type-configuration`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.75.6: CLI to Manage Prompt Type Configuration" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d feature/0-75-6-cli-manage-prompt-type-configuration`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
PYTHONPATH="${PYTHONPATH}:.:scripts/prompt-config/src" pytest tests/unit/scripts/prompt_config/ -v
```
**Output:**
```
47 passed in 0.79s
```
**Test breakdown:**
- test_cli.py: 22 tests (4 validate, 5 deploy, 3 list, 3 get, 1 stage, 2 promote, 2 rollback, 2 versions)
- test_client.py: 11 tests (2 version increment, 2 serialization, 3 agent validation, 4 dataclasses)
- test_validator.py: 14 tests (8 YAML validation, 6 dict validation)

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure (--build is MANDATORY)
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build

# Wait for services, then run tests
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v

# Tear down
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```
**Output:**
```
================== 102 passed, 1 skipped in 124.61s (0:02:04) ==================
```
**E2E passed:** [x] Yes / [ ] No

### 3. Lint Check
```bash
ruff check . && ruff format --check .
```
**Output:**
```
All checks passed!
415 files already formatted
```
**Lint passed:** [x] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to feature branch
git push origin feature/0-75-6-cli-manage-prompt-type-configuration

# Wait ~30s, then check CI status
gh run list --branch feature/0-75-6-cli-manage-prompt-type-configuration --limit 3
```
**Quality CI Run ID:** _______________
**Quality CI Status:** [ ] Passed / [ ] Failed
**E2E CI Run ID:** _______________
**E2E CI Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### Architecture Reference

**Primary Sources:**
- Prompt Management: `_bmad-output/architecture/ai-model-architecture/prompt-management.md`
- Epic 0.75: `_bmad-output/epics/epic-0-75-ai-model.md`
- CLI Standards: Epic 0.75 Overview section "CLI Standards"

**Pattern Sources:**
- CLI Pattern: `scripts/source-config/` (fp-source-config CLI)
- Prompt Model: `services/ai-model/src/ai_model/domain/prompt.py`
- Prompt Repository: `services/ai-model/src/ai_model/infrastructure/repositories/prompt_repository.py`

### CRITICAL: Reuse Existing Prompt Model

**DO NOT create new Pydantic models for prompts.** The models already exist in AI Model service:

```python
# REUSE THESE - DO NOT RECREATE
from ai_model.domain.prompt import Prompt, PromptStatus, PromptContent, PromptMetadata, PromptABTest
```

**Option A (Recommended):** Add `ai_model` as a dependency in `scripts/prompt-config/pyproject.toml`:
```toml
[tool.poetry.dependencies]
ai-model = { path = "../../services/ai-model" }
```

**Option B:** If circular dependency issues, copy the models but keep them in sync.

### Prompt Document Schema (from Prompt model)

```yaml
# YAML file format that CLI should accept
prompt_id: string              # "disease-diagnosis"
agent_id: string               # "diagnose-quality-issue"
version: string                # "2.1.0" (semver)
status: enum                   # "draft" | "staged" | "active" | "archived"

content:
  system_prompt: string        # Full system prompt text
  template: string             # Template with {{variables}}
  output_schema: object        # Optional JSON schema
  few_shot_examples: array     # Optional examples

metadata:
  author: string
  changelog: string            # What changed in this version
  git_commit: string           # Optional source commit SHA
```

### Sample YAML Fixture (for tests)

Create `tests/fixtures/prompt_config/valid-prompt.yaml`:

```yaml
prompt_id: disease-diagnosis
agent_id: diagnose-quality-issue
version: "1.0.0"
status: draft

content:
  system_prompt: |
    You are an expert tea disease diagnostician for the Farmer Power Platform.
    Analyze quality events and identify potential diseases or conditions.
  template: |
    Analyze the following quality event:

    {{event_data}}

    Provide diagnosis with confidence score.
  output_schema:
    type: object
    properties:
      condition:
        type: string
      confidence:
        type: number
        minimum: 0
        maximum: 1
    required:
      - condition
      - confidence

metadata:
  author: test-user
  changelog: Initial version for testing
```

### pyproject.toml Template

Create `scripts/prompt-config/pyproject.toml`:

```toml
[project]
name = "fp-prompt-config"
version = "0.1.0"
description = "Farmer Power Prompt Configuration CLI"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "typer[all]>=0.9.0",
    "rich>=13.0.0",
    "pyyaml>=6.0.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "motor>=3.3.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]

[project.scripts]
fp-prompt-config = "fp_prompt_config.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/fp_prompt_config"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
```

### CLI Standards (from Epic 0.75)

| Command | Purpose |
|---------|---------|
| `deploy` | Upload/create new config |
| `validate` | Validate config file |
| `list` | List all configs |
| `get` | Get specific config |
| `stage` | Stage new version |
| `promote` | Promote staged → active |
| `rollback` | Revert to previous |
| `versions` | List version history |

### Prompt-Agent Validation Rules

From `prompt-management.md`:

| Prompt Status | Agent Validation | Rationale |
|---------------|------------------|-----------|
| `draft` | Not required | Development flexibility |
| `staged` | Required | Pre-production must have valid agent |
| `active` | Required | Production prompts must have valid agent |
| `archived` | Not checked | Historical record |

**Implementation (CRITICAL: Use `get_active`, NOT `get_by_id`):**
```python
async def validate_prompt_agent_reference(prompt: Prompt, agent_repo) -> None:
    """Validate agent_id exists in agent_configs collection.

    IMPORTANT: Use get_active(agent_id) because:
    - prompt.agent_id is like "diagnose-quality-issue"
    - get_by_id expects document _id format "agent_id:version"
    - get_active queries by agent_id field and returns active config
    """
    if prompt.status in (PromptStatus.STAGED, PromptStatus.ACTIVE):
        agent = await agent_repo.get_active(prompt.agent_id)  # NOT get_by_id!
        if agent is None:
            raise ValidationError(
                f"Cannot publish prompt '{prompt.prompt_id}' with status '{prompt.status}': "
                f"agent_id '{prompt.agent_id}' does not exist in agent_configs"
            )
```

### MongoDB Transaction Pattern (for promote/rollback)

Motor requires explicit session handling for transactions:

```python
async def promote_prompt(client: AsyncIOMotorClient, prompt_id: str) -> None:
    """Promote staged prompt to active with transaction."""
    async with await client.start_session() as session:
        async with session.start_transaction():
            db = client["ai_model"]
            prompts = db["prompts"]

            # 1. Archive current active (if exists)
            await prompts.update_one(
                {"prompt_id": prompt_id, "status": "active"},
                {"$set": {"status": "archived"}},
                session=session,
            )

            # 2. Promote staged to active
            result = await prompts.update_one(
                {"prompt_id": prompt_id, "status": "staged"},
                {"$set": {"status": "active"}},
                session=session,
            )

            if result.modified_count == 0:
                raise ValueError(f"No staged prompt found for '{prompt_id}'")
```

### Test Fixtures (conftest.py)

Create `tests/unit/scripts/prompt_config/conftest.py`:

```python
"""Shared fixtures for fp-prompt-config CLI tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path


@pytest.fixture
def mock_prompt_client():
    """Mock PromptClient for CLI tests."""
    client = AsyncMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.create = AsyncMock()
    client.get_active = AsyncMock(return_value=None)
    client.list_prompts = AsyncMock(return_value=[])
    client.list_versions = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_agent_client():
    """Mock for agent_configs validation queries."""
    client = AsyncMock()
    # get_active returns None = agent not found
    client.get_active = AsyncMock(return_value=None)
    return client


@pytest.fixture
def sample_prompt_yaml(tmp_path: Path) -> Path:
    """Create a valid sample prompt YAML file."""
    yaml_content = '''
prompt_id: test-prompt
agent_id: test-agent
version: "1.0.0"
status: draft

content:
  system_prompt: Test system prompt
  template: Test template with {{variable}}

metadata:
  author: test-user
  changelog: Test version
'''
    file_path = tmp_path / "test-prompt.yaml"
    file_path.write_text(yaml_content)
    return file_path


@pytest.fixture
def invalid_prompt_yaml(tmp_path: Path) -> Path:
    """Create an invalid prompt YAML (missing required fields)."""
    yaml_content = '''
prompt_id: test-prompt
# Missing: agent_id, version, content
'''
    file_path = tmp_path / "invalid-prompt.yaml"
    file_path.write_text(yaml_content)
    return file_path
```

### Reference CLI Implementation: fp-source-config

The `scripts/source-config/src/fp_source_config/cli.py` provides the pattern to follow:

1. **Typer app with commands** - Each command as decorated function
2. **Rich console for output** - Tables, panels, colored text
3. **Async operations** - `asyncio.run()` wrapper for async MongoDB calls
4. **Settings class** - Environment-based configuration
5. **Deployer class** - Business logic separate from CLI
6. **Validator module** - Separate validation logic

### File Structure After Story

```
scripts/prompt-config/
├── pyproject.toml                    # Dependencies: typer, rich, motor, pydantic
├── README.md                         # Usage documentation
└── src/fp_prompt_config/
    ├── __init__.py
    ├── cli.py                        # Main CLI with Typer commands
    ├── settings.py                   # Environment configuration
    ├── validator.py                  # YAML validation logic
    └── client.py                     # MongoDB client for prompts

tests/unit/scripts/prompt_config/
├── conftest.py                       # Shared fixtures (mock MongoDB)
├── test_validator.py                 # Validator unit tests
├── test_cli.py                       # CLI command tests
└── test_client.py                    # Client unit tests
```

### Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| `typer` | ^0.9 | CLI framework |
| `rich` | ^13 | Rich console output |
| `motor` | ^3.3 | Async MongoDB driver |
| `pydantic` | ^2.0 | Data validation |
| `pyyaml` | ^6.0 | YAML parsing |

### Testing Strategy

**Unit Tests Required (minimum 25 tests):**

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_validator.py` | 8+ | YAML validation, schema checks |
| `test_cli.py` | 12+ | All CLI commands |
| `test_client.py` | 5+ | MongoDB operations |

**Test Fixtures:**
- Mock MongoDB client using `unittest.mock.AsyncMock`
- Sample YAML files in `tests/fixtures/prompt_config/`
- Use `typer.testing.CliRunner` for CLI testing

### Example Usage

```bash
# Validate a prompt YAML file
fp-prompt-config validate -f prompts/disease-diagnosis/prompt.yaml

# Deploy to staging environment
fp-prompt-config deploy --env staging -f prompts/disease-diagnosis/prompt.yaml

# List all prompts in dev
fp-prompt-config list --env dev

# List only active prompts
fp-prompt-config list --env dev --status active

# Get a specific prompt
fp-prompt-config get --env dev --prompt-id disease-diagnosis

# Get specific version
fp-prompt-config get --env dev --prompt-id disease-diagnosis --version 2.1.0

# Stage a new version
fp-prompt-config stage --env dev -f prompts/disease-diagnosis/v2.2.0.yaml

# Promote staged to active
fp-prompt-config promote --env dev --prompt-id disease-diagnosis

# Rollback to previous version
fp-prompt-config rollback --env dev --prompt-id disease-diagnosis --to-version 2.0.0

# Show version history
fp-prompt-config versions --env dev --prompt-id disease-diagnosis
```

### Previous Story (0.75.5) Learnings

1. **ChatOpenRouter pattern** - Subclass existing LangChain classes when possible
2. **82 unit tests** - High test coverage bar set for AI Model module
3. **E2E verification** - All 102 tests passed
4. **Lifespan hooks** - Gateway initialized in app lifespan
5. **Code review gate** - Story marked review after dev-story, then code-review workflow

### Recent Git Commits

```
2b1daa8 Story 0.75.5: OpenRouter LLM Gateway with Cost Observability (#98)
705fc66 Story 0.75.4: Source Cache for Agent Types and Prompt Config (#96)
2b970a2 Story 0.75.3: Pydantic Model for Agent Configuration + Mongo Repository (#94)
```

**Patterns from recent stories:**
- Commit format: `Story X.Y.Z: <description> (#issue)`
- PR format: Include issue reference
- Test naming: `test_{function}_{scenario}`

### Anti-Patterns to AVOID

| Anti-Pattern | Correct Approach |
|--------------|------------------|
| Recreating Prompt model | Import from `ai_model.domain.prompt` |
| Sync MongoDB calls | ALL MongoDB operations must be async |
| Hardcoded MongoDB URI | Use environment-based settings |
| Skipping agent validation | Always validate agent_id for staged/active |
| Manual JSON/YAML parsing | Use Pydantic model_validate() |
| Print statements | Use Rich console for output |
| Missing error handling | Catch specific exceptions, return exit code 1 |

### What This Story Does NOT Include

| Not in Scope | Implemented In |
|--------------|----------------|
| A/B test commands | Future enhancement |
| Diff command | Future enhancement |
| Agent config CLI | Story 0.75.7 |
| RAG document CLI | Story 0.75.11 |

### References

- [Source: `_bmad-output/architecture/ai-model-architecture/prompt-management.md`] - Prompt lifecycle, validation rules
- [Source: `_bmad-output/epics/epic-0-75-ai-model.md`] - Story requirements, CLI standards
- [Source: `_bmad-output/project-context.md`] - Critical rules, Pydantic 2.0 patterns
- [Source: `scripts/source-config/src/fp_source_config/cli.py`] - Reference CLI implementation
- [Source: `services/ai-model/src/ai_model/domain/prompt.py`] - Prompt Pydantic models
- [Source: `services/ai-model/src/ai_model/infrastructure/repositories/prompt_repository.py`] - Repository pattern

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
