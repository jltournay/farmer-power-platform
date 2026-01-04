# Story 0.75.3: Pydantic Model for Agent Configuration + Mongo Repository

**Status:** in-progress
**GitHub Issue:** #93

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer**,
I want Pydantic models and repository pattern for agent configuration,
So that agent configs are type-safe and properly managed in MongoDB.

## Acceptance Criteria

1. **AC1: Agent Config Base Model** - `AgentConfigBase` Pydantic model with common fields (agent_id, version, description, input, output, llm, mcp_sources, error_handling)
2. **AC2: Extractor Config Model** - `ExtractorConfig` with type discriminator and extraction-specific fields
3. **AC3: Explorer Config Model** - `ExplorerConfig` with type discriminator and RAG config
4. **AC4: Generator Config Model** - `GeneratorConfig` with type discriminator, RAG config, and output_format
5. **AC5: Conversational Config Model** - `ConversationalConfig` with type discriminator, RAG, state, intent_model, response_model
6. **AC6: Tiered-Vision Config Model** - `TieredVisionConfig` with type discriminator, tiered_llm, routing config
7. **AC7: Discriminated Union** - `AgentConfig` type using Pydantic discriminated union on "type" field
8. **AC8: Agent Type Enum** - `AgentType` enum with extractor, explorer, generator, conversational, tiered-vision values
9. **AC9: Status Enum** - `AgentConfigStatus` enum with draft, staged, active, archived values
10. **AC10: Repository CRUD** - `AgentConfigRepository` with async CRUD operations (create, get_by_id, update, delete, list)
11. **AC11: Get Active Config** - Repository method to get the currently active config for an agent_id
12. **AC12: Get By Type** - Repository method to list all configs of a specific agent type
13. **AC13: Version Queries** - Repository methods for version-based queries (get_by_version, list_versions)
14. **AC14: MongoDB Collection** - Data stored in `ai_model.agent_configs` collection
15. **AC15: MongoDB Indexes** - Compound indexes on (agent_id, status), (agent_id, version), and (type)
16. **AC16: Unit Tests** - Unit tests for all Pydantic models and repository methods (minimum 30 tests)
17. **AC17: CI Passes** - All lint checks and unit tests pass in CI

## Tasks / Subtasks

- [ ] **Task 1: Shared Component Models** (AC: #1)
  - [ ] Create `services/ai-model/src/ai_model/domain/agent_config.py`
  - [ ] Implement `LLMConfig` Pydantic model (model, temperature, max_tokens)
  - [ ] Implement `RAGConfig` Pydantic model (enabled, query_template, knowledge_domains, top_k, min_similarity)
  - [ ] Implement `InputConfig` Pydantic model (event, schema)
  - [ ] Implement `OutputConfig` Pydantic model (event, schema)
  - [ ] Implement `MCPSourceConfig` Pydantic model (server, tools)
  - [ ] Implement `ErrorHandlingConfig` Pydantic model (max_attempts, backoff_ms, on_failure, dead_letter_topic)
  - [ ] Implement `StateConfig` Pydantic model (max_turns, session_ttl_minutes, checkpoint_backend, context_window)
  - [ ] Implement `AgentType` enum (extractor, explorer, generator, conversational, tiered-vision)
  - [ ] Implement `AgentConfigStatus` enum (draft, staged, active, archived)

- [ ] **Task 2: Agent Config Base Model** (AC: #1)
  - [ ] Implement `AgentConfigBase` Pydantic model with all common fields
  - [ ] Include: agent_id, version, description, input, output, llm, mcp_sources, error_handling
  - [ ] Add metadata fields: created_at, updated_at, author, git_commit

- [ ] **Task 3: Type-Specific Models** (AC: #2, #3, #4, #5, #6, #7)
  - [ ] Implement `ExtractorConfig(AgentConfigBase)` with:
    - `type: Literal["extractor"]`
    - `extraction_schema: dict`
    - `normalization_rules: list[dict] | None`
  - [ ] Implement `ExplorerConfig(AgentConfigBase)` with:
    - `type: Literal["explorer"]`
    - `rag: RAGConfig`
  - [ ] Implement `GeneratorConfig(AgentConfigBase)` with:
    - `type: Literal["generator"]`
    - `rag: RAGConfig`
    - `output_format: Literal["json", "markdown", "text"]`
  - [ ] Implement `ConversationalConfig(AgentConfigBase)` with:
    - `type: Literal["conversational"]`
    - `rag: RAGConfig`
    - `state: StateConfig`
    - `intent_model: str`
    - `response_model: str`
  - [ ] Implement `TieredVisionLLMConfig` Pydantic model (screen, diagnose)
  - [ ] Implement `TieredVisionRoutingConfig` Pydantic model (screen_threshold, healthy_skip_threshold, obvious_skip_threshold)
  - [ ] Implement `TieredVisionConfig(AgentConfigBase)` with:
    - `type: Literal["tiered-vision"]`
    - `llm: LLMConfig | None = None` (not used, replaced by tiered_llm)
    - `rag: RAGConfig`
    - `tiered_llm: TieredVisionLLMConfig`
    - `routing: TieredVisionRoutingConfig`
  - [ ] Create discriminated union `AgentConfig` using `Annotated[..., Field(discriminator="type")]`

- [ ] **Task 4: Agent Config Repository** (AC: #10, #11, #12, #13, #14, #15)
  - [ ] Create `services/ai-model/src/ai_model/infrastructure/repositories/agent_config_repository.py`
  - [ ] Inherit from `BaseRepository[AgentConfig]`
  - [ ] Set `COLLECTION_NAME = "agent_configs"`
  - [ ] Implement `get_active(agent_id: str) -> AgentConfig | None` - get currently active config
  - [ ] Implement `get_by_type(agent_type: AgentType) -> list[AgentConfig]` - list by agent type
  - [ ] Implement `get_by_version(agent_id: str, version: str) -> AgentConfig | None`
  - [ ] Implement `list_versions(agent_id: str) -> list[AgentConfig]`
  - [ ] Implement `ensure_indexes()` - create compound indexes

- [ ] **Task 5: Repository Discriminated Union Handling** (AC: #7, #10)
  - [ ] Override `create()` to use discriminated union validation
  - [ ] Override `get_by_id()` to return correct subtype via discriminated union
  - [ ] Override `list()` to return correct subtypes
  - [ ] Ensure all repository methods properly handle the 5 config types

- [ ] **Task 6: Unit Tests - Models** (AC: #16)
  - [ ] Create `tests/unit/ai_model/test_agent_config_model.py` with tests for:
    - [ ] AgentType enum values (5 tests)
    - [ ] AgentConfigStatus enum values (4 tests)
    - [ ] LLMConfig validation (2 tests)
    - [ ] RAGConfig validation (2 tests)
    - [ ] InputConfig / OutputConfig validation (2 tests)
    - [ ] MCPSourceConfig validation (2 tests)
    - [ ] ErrorHandlingConfig validation with defaults (2 tests)
    - [ ] StateConfig validation with defaults (2 tests)
    - [ ] ExtractorConfig creation and serialization (2 tests)
    - [ ] ExplorerConfig creation and serialization (2 tests)
    - [ ] GeneratorConfig creation and serialization (2 tests)
    - [ ] ConversationalConfig creation and serialization (2 tests)
    - [ ] TieredVisionConfig creation and serialization (2 tests)
    - [ ] Discriminated union auto-selection (5 tests - one per type)
    - [ ] Invalid type rejection (2 tests)

- [ ] **Task 7: Unit Tests - Repository** (AC: #16)
  - [ ] Create `tests/unit/ai_model/test_agent_config_repository.py` with tests for:
    - [ ] create() - creates new agent config (extractor type)
    - [ ] create() - creates explorer type
    - [ ] create() - creates generator type
    - [ ] create() - creates conversational type
    - [ ] create() - creates tiered-vision type
    - [ ] get_by_id() - retrieves config by ID
    - [ ] get_by_id() - returns correct discriminated type
    - [ ] update() - updates config fields
    - [ ] delete() - deletes config
    - [ ] list() - lists configs with pagination
    - [ ] get_active() - gets active config for agent_id
    - [ ] get_by_type() - gets all configs of specific type
    - [ ] get_by_version() - gets specific version
    - [ ] list_versions() - lists all versions of an agent
    - [ ] ensure_indexes() - creates proper indexes

- [ ] **Task 8: Export and Integration** (AC: #14)
  - [ ] Update `services/ai-model/src/ai_model/domain/__init__.py` to export all new models
  - [ ] Update `services/ai-model/src/ai_model/infrastructure/repositories/__init__.py` to export `AgentConfigRepository`
  - [ ] Verify imports work correctly

- [ ] **Task 9: CI Verification** (AC: #17)
  - [ ] Run `ruff check services/ai-model/` - lint passes
  - [ ] Run `ruff format --check services/ai-model/` - format passes
  - [ ] Run unit tests locally with minimum 30 tests passing
  - [ ] Push and verify CI passes

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.75.3: Pydantic Model for Agent Configuration + Mongo Repository"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-75-3-pydantic-model-agent-config-mongo-repository
  ```

**Branch name:** `story/0-75-3-pydantic-model-agent-config-mongo-repository`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/0-75-3-pydantic-model-agent-config-mongo-repository`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.75.3: Pydantic Model for Agent Configuration + Mongo Repository" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/0-75-3-pydantic-model-agent-config-mongo-repository`

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
(paste test summary here - e.g., "XX passed in X.XXs")
```

### 2. E2E Tests (MANDATORY)

> **Note:** This story is data model only. E2E tests for AI Model will be added in Story 0.75.18.
> For this story, verify existing E2E tests still pass (no regressions).

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
git push origin story/0-75-3-pydantic-model-agent-config-mongo-repository

# Wait ~30s, then check CI status
gh run list --branch story/0-75-3-pydantic-model-agent-config-mongo-repository --limit 3
```
**Quality CI Run ID:** _______________
**Quality CI Status:** [ ] Passed / [ ] Failed
**E2E CI Run ID:** _______________
**E2E CI Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### Architecture Reference

**Source:** `_bmad-output/architecture/ai-model-architecture/agent-configuration-schema.md`
**Source:** `_bmad-output/architecture/ai-model-architecture/key-decisions.md`

### Key Decision: Single Collection with Discriminated Union

> **Decision:** Single `agent_configs` collection with `agent_type` discriminator field. Pydantic discriminated unions handle 5 agent types. See `key-decisions.md`.

This enables:
- Simpler queries across all agent types
- One repository class instead of five
- MongoDB schema-flexible storage
- Automatic type selection via Pydantic discriminator

### Agent Config Schema (MUST MATCH architecture/ai-model-architecture/agent-configuration-schema.md)

```python
# ═══════════════════════════════════════════════════════════════════════════
# SHARED COMPONENTS
# ═══════════════════════════════════════════════════════════════════════════

class LLMConfig(BaseModel):
    """LLM configuration for agent execution."""
    model: str                          # Explicit model, e.g. "anthropic/claude-3-5-sonnet"
    temperature: float = 0.3
    max_tokens: int = 2000

class RAGConfig(BaseModel):
    """RAG retrieval configuration."""
    enabled: bool = True
    query_template: str | None = None
    knowledge_domains: list[str] = []
    top_k: int = 5
    min_similarity: float = 0.7

class InputConfig(BaseModel):
    """Agent input contract."""
    event: str
    schema: dict

class OutputConfig(BaseModel):
    """Agent output contract."""
    event: str
    schema: dict

class MCPSourceConfig(BaseModel):
    """MCP server data source."""
    server: str
    tools: list[str]

class ErrorHandlingConfig(BaseModel):
    """Error handling and retry configuration."""
    max_attempts: int = 3
    backoff_ms: list[int] = [100, 500, 2000]
    on_failure: Literal["publish_error_event", "dead_letter"] = "publish_error_event"
    dead_letter_topic: str | None = None

class StateConfig(BaseModel):
    """Conversation state management (Conversational only)."""
    max_turns: int = 5
    session_ttl_minutes: int = 30
    checkpoint_backend: Literal["mongodb"] = "mongodb"
    context_window: int = 3

# ═══════════════════════════════════════════════════════════════════════════
# TYPE-SPECIFIC MODELS (see architecture doc for full schema)
# ═══════════════════════════════════════════════════════════════════════════

# ExtractorConfig: extraction_schema, normalization_rules
# ExplorerConfig: rag
# GeneratorConfig: rag, output_format
# ConversationalConfig: rag, state, intent_model, response_model
# TieredVisionConfig: rag, tiered_llm, routing

# ═══════════════════════════════════════════════════════════════════════════
# DISCRIMINATED UNION
# ═══════════════════════════════════════════════════════════════════════════

AgentConfig = Annotated[
    ExtractorConfig | ExplorerConfig | GeneratorConfig | ConversationalConfig | TieredVisionConfig,
    Field(discriminator="type")
]
```

### MongoDB Indexes (CRITICAL)

```python
# Compound indexes to create in ensure_indexes()
await collection.create_index(
    [("agent_id", 1), ("status", 1)],
    name="idx_agent_id_status",
)
await collection.create_index(
    [("agent_id", 1), ("version", 1)],
    unique=True,  # Each version is unique per agent
    name="idx_agent_id_version_unique",
)
await collection.create_index(
    "type",
    name="idx_type",
)
```

### Status Lifecycle (Same as Prompts)

```
draft → staged → active → archived
```

- `draft`: Development, validation relaxed
- `staged`: Ready for promotion
- `active`: Currently in use (only one per agent_id)
- `archived`: Historical version, kept for audit

### Discriminated Union Repository Pattern

The repository must handle discriminated unions correctly:

```python
from typing import Annotated, Union
from pydantic import Field

# When loading from MongoDB, use TypeAdapter for discriminated union
from pydantic import TypeAdapter

AgentConfig = Annotated[
    Union[ExtractorConfig, ExplorerConfig, GeneratorConfig, ConversationalConfig, TieredVisionConfig],
    Field(discriminator="type")
]

agent_config_adapter = TypeAdapter(AgentConfig)

# In repository get_by_id:
doc = await self._collection.find_one({"_id": entity_id})
if doc is None:
    return None
doc.pop("_id", None)
return agent_config_adapter.validate_python(doc)  # Auto-selects correct type
```

### Reference Implementation from Story 0.75.2

**Pattern to follow:**
- `services/ai-model/src/ai_model/domain/prompt.py` - Pydantic model pattern
- `services/ai-model/src/ai_model/infrastructure/repositories/base.py` - BaseRepository pattern
- `services/ai-model/src/ai_model/infrastructure/repositories/prompt_repository.py` - Specialized queries

**Key learnings from 0.75.2:**
1. Use `model_dump()` not `dict()` (Pydantic 2.0)
2. Use `model_validate()` not `parse_obj()` (Pydantic 2.0)
3. Use `_id` = `id` pattern for MongoDB
4. All I/O must be async
5. Export new models from `domain/__init__.py`
6. Export repository from `infrastructure/repositories/__init__.py`

### Testing Strategy

**Unit Tests Required (minimum 30 tests):**

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_agent_config_model.py` | 18+ | All enums, shared models, type-specific models, discriminated union |
| `test_agent_config_repository.py` | 15+ | All CRUD + specialized queries + type handling |

**Fixtures to Use:**
- Use `mock_mongodb_client` from root `tests/conftest.py`
- **DO NOT override** `mock_mongodb_client` in local conftest.py
- Follow pattern from `tests/unit/ai_model/test_prompt_repository.py`

### What This Story Does NOT Include

| Not in Scope | Implemented In |
|--------------|----------------|
| Cache layer | Story 0.75.4 |
| CLI tooling | Story 0.75.7 |
| Prompt validation against agent | Story 0.75.6 (CLI implements) |
| Agent workflow execution | Stories 0.75.17+ |

### Project Structure Notes

Files to create/modify:
```
services/ai-model/src/ai_model/
├── domain/
│   ├── __init__.py           # Add exports for new models
│   ├── prompt.py             # (exists from 0.75.2)
│   └── agent_config.py       # NEW: All agent config models
└── infrastructure/
    └── repositories/
        ├── __init__.py       # Add export for AgentConfigRepository
        ├── base.py           # (exists from 0.75.2)
        ├── prompt_repository.py  # (exists from 0.75.2)
        └── agent_config_repository.py  # NEW: Agent config repository
```

### Anti-Patterns to AVOID

| Anti-Pattern | Correct Approach |
|--------------|------------------|
| `dict[str, Any]` returns | Return `AgentConfig` discriminated union from repository |
| Separate repositories per type | Single `AgentConfigRepository` with discriminated union |
| `dict()` method | Use `model_dump()` (Pydantic 2.0) |
| `parse_obj()` | Use `model_validate()` or `TypeAdapter.validate_python()` |
| Relative imports | Use absolute imports only |
| Synchronous I/O | ALL database calls must be async |
| Hardcoded LLM models | Use config fields (model is explicit per agent) |

### References

- [Source: `_bmad-output/project-context.md`] - Critical rules
- [Source: `_bmad-output/architecture/ai-model-architecture/agent-configuration-schema.md`] - Full agent config schema with examples
- [Source: `_bmad-output/architecture/ai-model-architecture/key-decisions.md`] - Single collection decision
- [Source: `_bmad-output/epics/epic-0-75-ai-model.md`] - Story requirements
- [Source: `services/ai-model/src/ai_model/domain/prompt.py`] - Pydantic model pattern from 0.75.2
- [Source: `services/ai-model/src/ai_model/infrastructure/repositories/base.py`] - BaseRepository pattern from 0.75.2

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
