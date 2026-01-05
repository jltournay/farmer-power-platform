# Story 0.75.7: CLI to Manage Agent Configuration

**Status:** done
**GitHub Issue:** #101

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **platform operator**,
I want a CLI to manage agent configurations,
So that agents can be deployed and updated without code changes.

## Acceptance Criteria

1. **AC1: CLI Scaffold** - `fp-agent-config` CLI created using Typer framework in `scripts/agent-config/`
2. **AC2: Deploy Command** - `deploy` command uploads agent config YAML to MongoDB with validation
3. **AC3: Validate Command** - `validate` command validates agent config YAML against schema without deploying
4. **AC4: List Command** - `list` command shows all agents with status filter (draft/staged/active/archived)
5. **AC5: Get Command** - `get` command retrieves specific agent by agent_id (optionally version)
6. **AC6: Stage Command** - `stage` command creates new version with status=staged
7. **AC7: Promote Command** - `promote` command transitions staged config to active (archives previous active)
8. **AC8: Rollback Command** - `rollback` command reverts to previous version by archiving current and promoting specified version
9. **AC9: Versions Command** - `versions` command lists all versions of an agent_id with status
10. **AC10: Enable Command** - `enable` command enables an agent at runtime (agent_id only, unique to fp-agent-config)
11. **AC11: Disable Command** - `disable` command disables an agent at runtime (agent_id only, unique to fp-agent-config)
12. **AC12: Type-Specific Validation** - Validation discriminates 5 agent types (extractor, explorer, generator, conversational, tiered-vision) and validates type-specific fields
13. **AC13: YAML Schema** - YAML agent definition format matches AgentConfig Pydantic discriminated union (agent_id, type, version, status, llm, input, output, mcp_sources, etc.)
14. **AC14: Help Text** - Built-in `--help` with usage examples for each command
15. **AC15: Error Handling** - Exit code 0 = success, 1 = error; Error messages to stderr with format `Error: <message>`
16. **AC16: Verbosity Flags** - `--verbose` for detailed output, `--quiet` for minimal output (errors only)
17. **AC17: Rich Output** - Use Rich library for formatted tables and colored output
18. **AC18: Environment Config** - Support `--env` flag for environment selection (dev/staging/prod) via MongoDB URI
19. **AC19: Unit Tests** - Unit tests for CLI commands (minimum 30 tests covering all 5 agent types)
20. **AC20: CI Passes** - All lint checks and unit tests pass in CI

## Tasks / Subtasks

- [x] **Task 1: Create CLI Package Structure** (AC: #1)
  - [x] Create `scripts/agent-config/` directory
  - [x] Create `scripts/agent-config/pyproject.toml` with dependencies (typer, rich, motor, pydantic)
  - [x] Create `scripts/agent-config/src/fp_agent_config/__init__.py`
  - [x] Create `scripts/agent-config/src/fp_agent_config/cli.py` - main CLI entry point
  - [x] Create `scripts/agent-config/src/fp_agent_config/settings.py` - environment configuration
  - [x] Follow pattern from `scripts/prompt-config/` for structure

- [x] **Task 2: Implement Settings** (AC: #18)
  - [x] Create `Settings` Pydantic BaseSettings class with `@lru_cache` singleton
  - [x] Environment-based MongoDB URI: `MONGODB_URI_{DEV,STAGING,PROD}`
  - [x] Database name: `ai_model`
  - [x] Collection: `agent_configs`
  - [x] Support `--env` flag to select environment

- [x] **Task 3: Create MongoDB Client** (AC: #2)
  - [x] Create `scripts/agent-config/src/fp_agent_config/client.py`
  - [x] Implement async `AgentConfigClient` class using motor
  - [x] Reuse `AgentConfigRepository` pattern from AI Model service
  - [x] Implement `connect()` and `disconnect()` methods
  - [x] Implement agent config CRUD operations matching repository pattern
  - [x] Use `TypeAdapter(AgentConfig)` for discriminated union deserialization

- [x] **Task 4: Create Models Module** (AC: #12, #13)
  - [x] Create `scripts/agent-config/src/fp_agent_config/models.py`
  - [x] Import all models from `ai_model.domain.agent_config` (DO NOT RECREATE)
  - [x] Re-export for CLI convenience: `AgentConfig`, `AgentType`, `AgentConfigStatus`, etc.
  - [x] Add helper for TypeAdapter: `agent_config_adapter = TypeAdapter(AgentConfig)`

- [x] **Task 5: Implement Validator Module** (AC: #3, #12)
  - [x] Create `scripts/agent-config/src/fp_agent_config/validator.py`
  - [x] Load YAML file and validate against Pydantic discriminated union
  - [x] Check required fields per agent type:
    - **All types**: agent_id, type, version, description, input, output, llm, metadata
    - **extractor**: extraction_schema
    - **explorer**: rag
    - **generator**: rag, output_format
    - **conversational**: rag, state, intent_model, response_model
    - **tiered-vision**: tiered_llm, routing, rag (llm is optional/null)
  - [x] Validate version format (semver: X.Y.Z)
  - [x] Return validation errors with specific field paths
  - [x] Use `rich.console.Console` for colored output

- [x] **Task 6: Implement Validate Command** (AC: #3)
  - [x] Accept `--file/-f` option for YAML file path
  - [x] Call validator, print success or errors
  - [x] Support `--verbose` and `--quiet` flags
  - [x] Exit code 0 on success, 1 on failure

- [x] **Task 7: Implement Deploy Command** (AC: #2)
  - [x] Load and validate YAML file
  - [x] Parse YAML into correct AgentConfig type via discriminated union
  - [x] Generate document ID: `{agent_id}:{version}`
  - [x] Check if version already exists (conflict error)
  - [x] Insert document to MongoDB
  - [x] Print success message with agent_id, type, and version
  - [x] Support `--dry-run` flag

- [x] **Task 8: Implement List Command** (AC: #4)
  - [x] Query agent_configs collection
  - [x] Support `--status` filter (draft/staged/active/archived)
  - [x] Support `--type` filter (extractor/explorer/generator/conversational/tiered-vision)
  - [x] Display as Rich table with columns: agent_id, type, version, status, updated_at
  - [x] Sort by agent_id, then version descending

- [x] **Task 9: Implement Get Command** (AC: #5)
  - [x] Accept `--agent-id` (required) and `--version` (optional)
  - [x] If no version: get active version (fallback to latest staged)
  - [x] Display full config as formatted YAML
  - [x] Use `--output` flag for file output

- [x] **Task 10: Implement Stage Command** (AC: #6)
  - [x] Load YAML file with new version content
  - [x] Validate YAML against discriminated union schema
  - [x] Set status to "staged"
  - [x] Insert as new document (version must be unique)
  - [x] Print staged version details

- [x] **Task 11: Implement Promote Command** (AC: #7)
  - [x] Accept `--agent-id` (required)
  - [x] Find staged version for agent_id
  - [x] Error if no staged version exists
  - [x] Use MongoDB transaction (motor session pattern):
    1. Archive current active version (if exists)
    2. Update staged version status to active
  - [x] Print promotion details

- [x] **Task 12: Implement Rollback Command** (AC: #8)
  - [x] Accept `--agent-id` (required) and `--to-version` (required)
  - [x] Find specified version (must exist)
  - [x] Use MongoDB transaction:
    1. Archive current active version
    2. Create new version from rollback target with status=active
  - [x] Increment version (e.g., 1.2.0 → 1.2.1 with rollback note in metadata)
  - [x] Print rollback details

- [x] **Task 13: Implement Versions Command** (AC: #9)
  - [x] Accept `--agent-id` (required)
  - [x] Query all versions for agent_id
  - [x] Display as Rich table with columns: version, type, status, updated_at, author
  - [x] Sort by version descending
  - [x] Highlight active version

- [x] **Task 14: Implement Enable Command** (AC: #10)
  - [x] Accept `--agent-id` (required)
  - [x] Find active config for agent_id
  - [x] Error if no active config exists
  - [x] Set `enabled: true` field on config (add to model if not present)
  - [x] Print enable confirmation

- [x] **Task 15: Implement Disable Command** (AC: #11)
  - [x] Accept `--agent-id` (required)
  - [x] Find active config for agent_id
  - [x] Error if no active config exists
  - [x] Set `enabled: false` field on config
  - [x] Print disable confirmation

- [x] **Task 16: Add Help and Verbosity** (AC: #14, #15, #16, #17)
  - [x] Add comprehensive help text for each command with examples
  - [x] Implement `--verbose` flag for detailed output
  - [x] Implement `--quiet` flag for minimal output
  - [x] Error output to stderr with `Error:` prefix
  - [x] Exit codes: 0 (success), 1 (error)

- [x] **Task 17: Unit Tests - Validator** (AC: #19)
  - [x] Create `tests/unit/agent_config_cli/test_validator.py`
  - [x] Test valid YAML validation passes for each agent type (5 tests)
  - [x] Test missing required fields fails for each type (5 tests)
  - [x] Test invalid version format fails
  - [x] Test malformed YAML fails
  - [x] Test unknown agent type fails

- [x] **Task 18: Unit Tests - CLI Commands** (AC: #19)
  - [x] Create `tests/unit/agent_config_cli/test_cli.py`
  - [x] Mock MongoDB client for all tests
  - [x] Test `validate` command with valid/invalid files (2+ tests)
  - [x] Test `deploy` command with each agent type (5 tests)
  - [x] Test `list` command with status/type filters (3+ tests)
  - [x] Test `get` command with/without version (2+ tests)
  - [x] Test `stage` command (1+ test)
  - [x] Test `promote` command (2+ tests)
  - [x] Test `rollback` command (2+ tests)
  - [x] Test `versions` command (2+ tests)
  - [x] Test `enable` command (2+ tests)
  - [x] Test `disable` command (2+ tests)

- [x] **Task 19: Unit Tests - Error Handling** (AC: #19)
  - [x] Test missing file error
  - [x] Test invalid environment error
  - [x] Test MongoDB connection error
  - [x] Test duplicate version error
  - [x] Test agent not found error

- [x] **Task 20: Create Test Fixtures** (AC: #19)
  - [x] Create `tests/fixtures/agent_config/extractor_valid.yaml`
  - [x] Create `tests/fixtures/agent_config/explorer_valid.yaml`
  - [x] Create `tests/fixtures/agent_config/generator_valid.yaml`
  - [x] Create `tests/fixtures/agent_config/conversational_valid.yaml`
  - [x] Create `tests/fixtures/agent_config/tiered_vision_valid.yaml`
  - [x] Create `tests/fixtures/agent_config/invalid_missing_type.yaml`
  - [x] Create `tests/fixtures/agent_config/invalid_version.yaml`

- [x] **Task 21: Update CI Configuration** (AC: #20)
  - [x] Add `scripts/agent-config/src` to PYTHONPATH in `.github/workflows/ci.yaml`
  - [x] Ensure tests run with proper paths

- [x] **Task 22: E2E Verification** (AC: #20)
  - [x] Run full E2E test suite with `--build` flag
  - [x] Verify no regressions
  - [x] Capture test output in story file

- [x] **Task 23: CI Verification** (AC: #20)
  - [x] Run `ruff check .` - lint passes
  - [x] Run `ruff format --check .` - format passes
  - [x] Push and verify CI passes (Run ID: 20708104019)
  - [x] Trigger E2E CI workflow and verify passes (Run ID: 20708173334)

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [x] GitHub Issue exists or created: #101
- [x] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/0-75-7-cli-manage-agent-configuration
  ```

**Branch name:** `feature/0-75-7-cli-manage-agent-configuration`

### During Development
- [x] All commits reference GitHub issue: `Relates to #101`
- [x] Commits are atomic by type (production, test, seed - not mixed)
- [x] Push to feature branch: `git push -u origin feature/0-75-7-cli-manage-agent-configuration`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.75.7: CLI to Manage Agent Configuration" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d feature/0-75-7-cli-manage-agent-configuration`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
PYTHONPATH="${PYTHONPATH}:.:scripts/agent-config/src:services/ai-model/src" pytest tests/unit/agent_config_cli/ -v
```
**Output:**
```
tests/unit/agent_config_cli/test_cli.py: 31 PASSED
tests/unit/agent_config_cli/test_client.py: 16 PASSED
tests/unit/agent_config_cli/test_validator.py: 20 PASSED
======================== 67 passed, 8 warnings in 0.89s ========================
```

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
tests/e2e/scenarios/test_00_infrastructure_verification.py: 22 passed
tests/e2e/scenarios/test_01_plantation_mcp_contracts.py: 15 passed
tests/e2e/scenarios/test_02_collection_mcp_contracts.py: 12 passed
tests/e2e/scenarios/test_03_factory_farmer_flow.py: 5 passed
tests/e2e/scenarios/test_04_quality_blob_ingestion.py: 6 passed
tests/e2e/scenarios/test_05_weather_ingestion.py: 7 passed
tests/e2e/scenarios/test_06_cross_model_events.py: 5 passed
tests/e2e/scenarios/test_07_grading_validation.py: 6 passed
tests/e2e/scenarios/test_08_zip_ingestion.py: 8 passed, 1 skipped
tests/e2e/scenarios/test_30_bff_farmer_api.py: 16 passed
================== 102 passed, 1 skipped in 120.50s (0:02:00) ==================
```
**E2E passed:** [x] Yes / [ ] No

### 3. Lint Check
```bash
ruff check . && ruff format --check .
```
**Output:**
```
All checks passed!
426 files already formatted
```
**Lint passed:** [x] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to feature branch
git push origin feature/0-75-7-cli-manage-agent-configuration

# Wait ~30s, then check CI status
gh run list --branch feature/0-75-7-cli-manage-agent-configuration --limit 3
```
**CI Run ID:** 20708104019 (CI), 20708173334 (E2E)
**CI E2E Status:** [x] Passed / [ ] Failed
**Verification Date:** 2026-01-05

---

## Dev Notes

### Architecture Reference

**Primary Sources:**
- Agent Configuration Schema: `_bmad-output/architecture/ai-model-architecture/agent-configuration-schema.md`
- Epic 0.75: `_bmad-output/epics/epic-0-75-ai-model.md`
- CLI Standards: Epic 0.75 Overview section "CLI Standards"
- Agent Config Pydantic Models: `services/ai-model/src/ai_model/domain/agent_config.py`
- Agent Config Repository: `services/ai-model/src/ai_model/infrastructure/repositories/agent_config_repository.py`

**Pattern Sources:**
- CLI Pattern: `scripts/prompt-config/` (fp-prompt-config CLI - Story 0.75.6)
- Source Config CLI: `scripts/source-config/` (fp-source-config CLI)

### CRITICAL: Reuse Existing Agent Config Models

**DO NOT create new Pydantic models for agent configs.** The models already exist in AI Model service:

```python
# REUSE THESE - DO NOT RECREATE
from ai_model.domain.agent_config import (
    AgentConfig,           # Discriminated union of all 5 types
    AgentType,            # Enum: extractor, explorer, generator, conversational, tiered-vision
    AgentConfigStatus,    # Enum: draft, staged, active, archived
    ExtractorConfig,
    ExplorerConfig,
    GeneratorConfig,
    ConversationalConfig,
    TieredVisionConfig,
    # ... shared components
    LLMConfig,
    RAGConfig,
    InputConfig,
    OutputConfig,
    MCPSourceConfig,
    ErrorHandlingConfig,
    StateConfig,
    AgentConfigMetadata,
    TieredVisionLLMConfig,
    TieredVisionRoutingConfig,
)
```

**Option A (Recommended):** Add `ai-model` as a dependency in `scripts/agent-config/pyproject.toml`:
```toml
[tool.poetry.dependencies]
ai-model = { path = "../../services/ai-model" }
```

**Option B:** If circular dependency issues, import via `sys.path` manipulation.

### Agent Config Document Schema

The CLI must handle all 5 agent types via Pydantic discriminated union. The `type` field determines which model is used:

```yaml
# YAML file format - type determines which fields are required
agent:
  id: "disease-diagnosis:1.0.0"
  agent_id: "disease-diagnosis"
  type: explorer           # extractor | explorer | generator | conversational | tiered-vision
  version: "1.0.0"
  status: draft            # draft | staged | active | archived
  description: "Analyzes quality issues and produces diagnosis"

  input:
    event: "collection.poor_quality_detected"
    schema:
      required: [doc_id, farmer_id]
      optional: [quality_issues]

  output:
    event: "ai.diagnosis.complete"
    schema:
      fields: [diagnosis, confidence, severity]

  llm:
    model: "anthropic/claude-3-5-sonnet"
    temperature: 0.3
    max_tokens: 2000

  mcp_sources:
    - server: collection
      tools: [get_document, get_farmer_documents]
    - server: plantation
      tools: [get_farmer, get_farmer_summary]

  error_handling:
    max_attempts: 3
    backoff_ms: [100, 500, 2000]
    on_failure: publish_error_event

  metadata:
    author: platform-operator
    git_commit: abc123

  # TYPE-SPECIFIC FIELDS (varies by type)
  rag:                     # Required for: explorer, generator, conversational, tiered-vision
    enabled: true
    query_template: "tea leaf quality issues {{quality_issues}}"
    knowledge_domains: [plant_diseases, tea_cultivation]
    top_k: 5
    min_similarity: 0.7
```

### Type-Specific Required Fields

| Agent Type | Required Fields Beyond Base |
|------------|----------------------------|
| **extractor** | `extraction_schema`, optional `normalization_rules` |
| **explorer** | `rag` |
| **generator** | `rag`, `output_format` (json\|markdown\|text) |
| **conversational** | `rag`, `state`, `intent_model`, `response_model` |
| **tiered-vision** | `tiered_llm` (screen + diagnose), `routing`, `rag`; `llm` is optional/null |

### Sample YAML Fixtures (for tests)

**Extractor (`tests/fixtures/agent_config/valid-extractor.yaml`):**
```yaml
id: "qc-event-extractor:1.0.0"
agent_id: qc-event-extractor
type: extractor
version: "1.0.0"
status: draft
description: "Extracts structured data from QC analyzer payloads"
input:
  event: collection.document.received
  schema:
    required: [doc_id]
output:
  event: ai.extraction.complete
  schema:
    fields: [farmer_id, grade, quality_score]
llm:
  model: anthropic/claude-3-haiku
  temperature: 0.1
  max_tokens: 500
extraction_schema:
  required_fields: [farmer_id, grade]
  validation_rules:
    - field: farmer_id
      pattern: "^WM-\\d+$"
metadata:
  author: test-user
```

**Tiered-Vision (`tests/fixtures/agent_config/valid-tiered-vision.yaml`):**
```yaml
id: "leaf-quality-analyzer:1.0.0"
agent_id: leaf-quality-analyzer
type: tiered-vision
version: "1.0.0"
status: draft
description: "Cost-optimized image analysis for tea leaf quality"
input:
  event: collection.image.received
  schema:
    required: [doc_id, thumbnail_url, original_url]
output:
  event: ai.vision_analysis.complete
  schema:
    fields: [classification, confidence, diagnosis]
tiered_llm:
  screen:
    model: anthropic/claude-3-haiku
    temperature: 0.1
    max_tokens: 200
  diagnose:
    model: anthropic/claude-3-5-sonnet
    temperature: 0.3
    max_tokens: 2000
routing:
  screen_threshold: 0.7
  healthy_skip_threshold: 0.85
  obvious_skip_threshold: 0.75
rag:
  enabled: true
  knowledge_domains: [plant_diseases, visual_symptoms]
  top_k: 5
metadata:
  author: test-user
```

### pyproject.toml Template

Create `scripts/agent-config/pyproject.toml`:

```toml
[project]
name = "fp-agent-config"
version = "0.1.0"
description = "Farmer Power Agent Configuration CLI"
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
fp-agent-config = "fp_agent_config.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/fp_agent_config"]

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
| `enable` | Enable at runtime (fp-agent-config only) |
| `disable` | Disable at runtime (fp-agent-config only) |

### Enable/Disable Commands (Unique to fp-agent-config)

These commands allow runtime control over agents without changing versions:

```python
# Schema addition for enabled field (if not already present in model)
class AgentConfigBase(BaseModel):
    ...
    enabled: bool = Field(
        default=True,
        description="Whether agent is enabled at runtime (can be toggled via enable/disable commands)"
    )
```

**Usage:**
```bash
# Disable agent without archiving
fp-agent-config disable --agent-id disease-diagnosis --env dev

# Re-enable agent
fp-agent-config enable --agent-id disease-diagnosis --env dev
```

### MongoDB Transaction Pattern (for promote/rollback)

Motor requires explicit session handling for transactions (same as fp-prompt-config):

```python
async def promote_agent(client: AsyncIOMotorClient, agent_id: str) -> None:
    """Promote staged agent config to active with transaction."""
    async with await client.start_session() as session:
        async with session.start_transaction():
            db = client["ai_model"]
            configs = db["agent_configs"]

            # 1. Archive current active (if exists)
            await configs.update_one(
                {"agent_id": agent_id, "status": "active"},
                {"$set": {"status": "archived"}},
                session=session,
            )

            # 2. Promote staged to active
            result = await configs.update_one(
                {"agent_id": agent_id, "status": "staged"},
                {"$set": {"status": "active"}},
                session=session,
            )

            if result.modified_count == 0:
                raise ValueError(f"No staged config found for '{agent_id}'")
```

### Using TypeAdapter for Discriminated Union

The `AgentConfig` type is a discriminated union. Use `TypeAdapter` for deserialization:

```python
from pydantic import TypeAdapter
from ai_model.domain.agent_config import AgentConfig

# Create adapter once (module level)
agent_config_adapter: TypeAdapter[AgentConfig] = TypeAdapter(AgentConfig)

def deserialize(doc: dict) -> AgentConfig:
    """Deserialize to correct AgentConfig type based on 'type' field."""
    doc.pop("_id", None)  # Remove MongoDB _id
    return agent_config_adapter.validate_python(doc)
```

### Test Fixtures (conftest.py)

Create `tests/unit/scripts/agent_config/conftest.py`:

```python
"""Shared fixtures for fp-agent-config CLI tests."""

import pytest
from unittest.mock import AsyncMock
from pathlib import Path


@pytest.fixture
def mock_agent_config_client():
    """Mock AgentConfigClient for CLI tests."""
    client = AsyncMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.create = AsyncMock()
    client.get_active = AsyncMock(return_value=None)
    client.get_by_version = AsyncMock(return_value=None)
    client.list_configs = AsyncMock(return_value=[])
    client.list_versions = AsyncMock(return_value=[])
    client.promote = AsyncMock()
    client.rollback = AsyncMock()
    client.enable = AsyncMock()
    client.disable = AsyncMock()
    return client


def make_agent_config(
    agent_id: str = "test-agent",
    agent_type: str = "explorer",
    version: str = "1.0.0",
    status: str = "draft",
) -> dict:
    """Factory for creating test agent config dicts."""
    base = {
        "id": f"{agent_id}:{version}",
        "agent_id": agent_id,
        "type": agent_type,
        "version": version,
        "status": status,
        "description": "Test agent",
        "input": {"event": "test.event", "schema": {"required": ["doc_id"]}},
        "output": {"event": "test.complete", "schema": {"fields": ["result"]}},
        "llm": {"model": "anthropic/claude-3-haiku", "temperature": 0.3, "max_tokens": 1000},
        "mcp_sources": [],
        "error_handling": {"max_attempts": 3, "backoff_ms": [100, 500], "on_failure": "publish_error_event"},
        "metadata": {"author": "test-user", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"},
    }

    # Add type-specific fields
    if agent_type == "extractor":
        base["extraction_schema"] = {"required_fields": ["farmer_id"]}
    elif agent_type in ("explorer", "generator", "conversational", "tiered-vision"):
        base["rag"] = {"enabled": True, "knowledge_domains": ["test"], "top_k": 5}

    if agent_type == "generator":
        base["output_format"] = "markdown"
    elif agent_type == "conversational":
        base["state"] = {"max_turns": 5, "session_ttl_minutes": 30}
        base["intent_model"] = "anthropic/claude-3-haiku"
        base["response_model"] = "anthropic/claude-3-5-sonnet"
    elif agent_type == "tiered-vision":
        base.pop("llm", None)  # tiered-vision doesn't use base llm
        base["tiered_llm"] = {
            "screen": {"model": "anthropic/claude-3-haiku", "temperature": 0.1, "max_tokens": 200},
            "diagnose": {"model": "anthropic/claude-3-5-sonnet", "temperature": 0.3, "max_tokens": 2000},
        }
        base["routing"] = {"screen_threshold": 0.7, "healthy_skip_threshold": 0.85}

    return base
```

### File Structure After Story

```
scripts/agent-config/
├── pyproject.toml                    # Dependencies: typer, rich, motor, pydantic
├── README.md                         # Usage documentation
└── src/fp_agent_config/
    ├── __init__.py
    ├── cli.py                        # Main CLI with Typer commands (10 commands)
    ├── settings.py                   # Environment configuration (@lru_cache singleton)
    ├── validator.py                  # YAML validation with type discrimination
    └── client.py                     # MongoDB client for agent configs

tests/unit/scripts/agent_config/
├── conftest.py                       # Shared fixtures (mock MongoDB, make_agent_config)
├── test_validator.py                 # Validator unit tests (15+ tests)
├── test_cli.py                       # CLI command tests (25+ tests)
└── test_client.py                    # Client unit tests (5+ tests)

tests/fixtures/agent_config/
├── valid-extractor.yaml
├── valid-explorer.yaml
├── valid-generator.yaml
├── valid-conversational.yaml
├── valid-tiered-vision.yaml
├── invalid-missing-type.yaml
├── invalid-unknown-type.yaml
└── invalid-bad-version.yaml
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

**Unit Tests Required (minimum 30 tests):**

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_validator.py` | 15+ | YAML validation per type, schema checks |
| `test_cli.py` | 25+ | All 10 CLI commands |
| `test_client.py` | 5+ | MongoDB operations |

**Test Fixtures:**
- Mock MongoDB client using `unittest.mock.AsyncMock`
- Sample YAML files in `tests/fixtures/agent_config/`
- Use `typer.testing.CliRunner` for CLI testing

### Example Usage

```bash
# Validate an agent config YAML file
fp-agent-config validate -f config/agents/disease-diagnosis.yaml

# Deploy to dev environment
fp-agent-config deploy --env dev -f config/agents/disease-diagnosis.yaml

# List all agents in dev
fp-agent-config list --env dev

# List only active extractor agents
fp-agent-config list --env dev --status active --type extractor

# Get a specific agent
fp-agent-config get --env dev --agent-id disease-diagnosis

# Get specific version
fp-agent-config get --env dev --agent-id disease-diagnosis --version 2.1.0

# Stage a new version
fp-agent-config stage --env dev -f config/agents/disease-diagnosis-v2.yaml

# Promote staged to active
fp-agent-config promote --env dev --agent-id disease-diagnosis

# Rollback to previous version
fp-agent-config rollback --env dev --agent-id disease-diagnosis --to-version 1.0.0

# Show version history
fp-agent-config versions --env dev --agent-id disease-diagnosis

# Disable agent at runtime
fp-agent-config disable --env dev --agent-id disease-diagnosis

# Re-enable agent
fp-agent-config enable --env dev --agent-id disease-diagnosis
```

### Previous Story (0.75.6) Learnings

1. **Singleton Settings** - Use `@lru_cache` decorator on `get_settings()` to avoid creating new instances
2. **48 unit tests** - High test coverage bar set; this story targets 30+ minimum
3. **E2E verification** - All 102 tests passed
4. **get_active not get_by_id** - For validation queries, use `get_active(agent_id)` which queries by agent_id field
5. **TypeAdapter for unions** - Use `TypeAdapter(AgentConfig)` for discriminated union deserialization
6. **File List accuracy** - Ensure File List section matches actual git files created

### Recent Git Commits

```
419b638 Story 0.75.6: CLI to Manage Prompt Type Configuration (#100)
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
| Recreating AgentConfig models | Import from `ai_model.domain.agent_config` |
| Sync MongoDB calls | ALL MongoDB operations must be async |
| Hardcoded MongoDB URI | Use environment-based settings |
| Manual dict parsing for types | Use `TypeAdapter` with discriminated union |
| Print statements | Use Rich console for output |
| Missing error handling | Catch specific exceptions, return exit code 1 |
| New Settings instance per call | Use `@lru_cache` on `get_settings()` |

### What This Story Does NOT Include

| Not in Scope | Implemented In |
|--------------|----------------|
| Prompt config CLI | Story 0.75.6 |
| RAG document CLI | Story 0.75.11 |
| Agent execution | Stories 0.75.17-22 |
| Event pub/sub | Story 0.75.8 |

### References

- [Source: `_bmad-output/architecture/ai-model-architecture/agent-configuration-schema.md`] - Agent type schemas
- [Source: `_bmad-output/epics/epic-0-75-ai-model.md`] - Story requirements, CLI standards
- [Source: `_bmad-output/project-context.md`] - Critical rules, Pydantic 2.0 patterns
- [Source: `scripts/prompt-config/src/fp_prompt_config/cli.py`] - Reference CLI implementation (726 lines)
- [Source: `services/ai-model/src/ai_model/domain/agent_config.py`] - Agent Config Pydantic models (563 lines)
- [Source: `services/ai-model/src/ai_model/infrastructure/repositories/agent_config_repository.py`] - Repository pattern (325 lines)

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

**Created:**
- `scripts/agent-config/pyproject.toml` - CLI package configuration
- `scripts/agent-config/src/fp_agent_config/__init__.py` - Package init
- `scripts/agent-config/src/fp_agent_config/cli.py` - Main CLI with 10 commands
- `scripts/agent-config/src/fp_agent_config/client.py` - MongoDB async client
- `scripts/agent-config/src/fp_agent_config/models.py` - Re-exports from ai_model
- `scripts/agent-config/src/fp_agent_config/settings.py` - Environment settings
- `scripts/agent-config/src/fp_agent_config/validator.py` - YAML validation
- `tests/unit/agent_config_cli/__init__.py` - Test package init
- `tests/unit/agent_config_cli/conftest.py` - Test fixtures
- `tests/unit/agent_config_cli/test_cli.py` - CLI command tests (31 tests)
- `tests/unit/agent_config_cli/test_client.py` - MongoDB client tests (16 tests)
- `tests/unit/agent_config_cli/test_validator.py` - Validator tests (20 tests)
- `tests/fixtures/agent_config/extractor_valid.yaml` - Valid extractor fixture
- `tests/fixtures/agent_config/explorer_valid.yaml` - Valid explorer fixture
- `tests/fixtures/agent_config/generator_valid.yaml` - Valid generator fixture
- `tests/fixtures/agent_config/conversational_valid.yaml` - Valid conversational fixture
- `tests/fixtures/agent_config/tiered_vision_valid.yaml` - Valid tiered-vision fixture
- `tests/fixtures/agent_config/invalid_missing_type.yaml` - Invalid fixture (missing type)
- `tests/fixtures/agent_config/invalid_version.yaml` - Invalid fixture (bad version)

**Modified:**
- `.github/workflows/ci.yaml` - Added agent-config/src to PYTHONPATH
- `_bmad-output/sprint-artifacts/sprint-status.yaml` - Story status update
