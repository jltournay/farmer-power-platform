# Story 9.12a: AgentConfigService gRPC in AI Model

**Status:** ready-for-dev
**GitHub Issue:** <!-- Auto-created by dev-story workflow -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **Platform Administrator**,
I want **read-only gRPC endpoints for AI agent and prompt configurations in the AI Model service**,
so that **the Admin UI can display agent configs and their linked prompts without direct MongoDB access, enabling auditability and debugging of AI agent behavior**.

## Use Case Context

**Epic:** 9 - Platform Admin Portal
**Use Case:** UC9.2: View AI Agent and Prompt Configurations
**Steps Covered:** Step 1 (backend gRPC layer)
**Input (from preceding steps):** None (first story in ADR-019 Decision 3 implementation chain)
**Output (for subsequent steps):** AgentConfigService gRPC endpoints accessible via DAPR service invocation from BFF
**E2E Verification:** BFF client can invoke `ListAgentConfigs` via DAPR and receive paginated list of agents with summaries; `GetAgentConfig` returns full config detail with linked prompts in one call; `ListPromptsByAgent` returns prompts for a specific agent

## Acceptance Criteria

### AC 9.12a.1: Proto Service Definition

**Given** the AI Model proto file exists (`proto/ai_model/v1/ai_model.proto`)
**When** I add the AgentConfigService definition
**Then** the proto file contains:
- `service AgentConfigService` with `ListAgentConfigs`, `GetAgentConfig`, and `ListPromptsByAgent` RPCs
- Request/Response messages per ADR-019 Decision 3
- Timestamp imports for `updated_at` and `created_at` fields
- NO write methods (read-only service per ADR-019)

### AC 9.12a.2: ListAgentConfigs RPC

**Given** agent configs exist in MongoDB (`ai_model.agent_configs` collection)
**When** I call `ListAgentConfigs` with optional filters
**Then** I receive:
- Paginated `AgentConfigSummary` records (agent_id, version, agent_type, status, description, model, prompt_count, updated_at)
- `next_page_token` for pagination (empty if no more results)
- `total_count` of matching records
- Filter by `agent_type` returns only matching type ("extractor", "explorer", "generator", "conversational", "tiered-vision")
- Filter by `status` returns only matching status ("draft", "staged", "active", "archived")
- Default page_size=20, max=100

### AC 9.12a.3: GetAgentConfig RPC

**Given** an agent config exists with agent_id "disease-diagnosis"
**When** I call `GetAgentConfig(agent_id="disease-diagnosis")` with optional version
**Then** I receive:
- `AgentConfigResponse` with all summary fields
- `config_json` field containing the full AgentConfig as JSON string
- `prompts` field containing `PromptSummary` records for all linked prompts (denormalized for single call efficiency)
- `created_at` and `updated_at` timestamps
- NOT_FOUND error if agent_id doesn't exist
- Optional version parameter retrieves specific version (empty = active version)

### AC 9.12a.4: ListPromptsByAgent RPC

**Given** prompts exist linked to agent_id "disease-diagnosis"
**When** I call `ListPromptsByAgent(agent_id="disease-diagnosis")` with optional status filter
**Then** I receive:
- `ListPromptsResponse` with `PromptSummary` records (id, prompt_id, agent_id, version, status, author, updated_at)
- `total_count` of matching prompts
- Filter by `status` returns only matching status
- Empty list if no prompts linked to agent

### AC 9.12a.5: gRPC Server Registration

**Given** the AI Model service starts
**When** the gRPC server initializes
**Then** `AgentConfigServiceServicer` is registered alongside existing `AiModelServiceServicer` and `RAGDocumentServiceServicer`
**And** all services are accessible on port 50051

### AC 9.12a.6: Unit Tests

**Given** the AgentConfigService implementation
**When** unit tests run
**Then** all tests pass covering:
- ListAgentConfigs with no filters
- ListAgentConfigs with `agent_type` filter
- ListAgentConfigs with `status` filter
- ListAgentConfigs combined filters
- ListAgentConfigs pagination
- GetAgentConfig success case (active version)
- GetAgentConfig with specific version
- GetAgentConfig NOT_FOUND case
- GetAgentConfig returns linked prompts
- ListPromptsByAgent success case
- ListPromptsByAgent with status filter
- ListPromptsByAgent empty result
- Invalid page_token handling

### AC-E2E (from Use Case)

**Given** the AI Model service is running with seed data containing at least 2 agent configs with linked prompts
**When** an external client (simulating BFF) invokes `ListAgentConfigs` via DAPR service invocation
**Then** the response contains `total_count >= 2` and `agents[]` with `agent_id` fields populated
**And** invoking `GetAgentConfig` for one of those agents returns `prompts[]` with linked prompt summaries

## Tasks / Subtasks

### Task 1: Add Proto Service Definition (AC: 1)

- [ ] Add `AgentConfigService` to `proto/ai_model/v1/ai_model.proto`
- [ ] Define `ListAgentConfigsRequest` and `ListAgentConfigsResponse` messages
- [ ] Define `GetAgentConfigRequest` and `AgentConfigResponse` messages
- [ ] Define `ListPromptsByAgentRequest` and `ListPromptsResponse` messages
- [ ] Define `AgentConfigSummary` and `PromptSummary` messages
- [ ] Regenerate proto stubs: `bash scripts/proto-gen.sh`
- [ ] Verify generated files in `libs/fp-proto/src/fp_proto/ai_model/v1/`

### Task 2: Extend AgentConfigRepository (AC: 2, 3)

- [ ] Add `list_all()` method with pagination support to `AgentConfigRepository`
- [ ] Add optional filters: `agent_type`, `status`
- [ ] Add `count()` method for total count queries
- [ ] Verify existing `get_active()` and `get_by_version()` methods work for GetAgentConfig

### Task 3: Extend PromptRepository (AC: 4)

- [ ] Add `count_by_agent()` method to `PromptRepository` for prompt_count in summary
- [ ] Verify existing `list_by_agent()` method works for ListPromptsByAgent

### Task 4: Create Agent Config Converters in fp_common (AC: 2, 3, 4)

- [ ] Create `libs/fp-common/fp_common/converters/agent_config_converters.py`
- [ ] Implement `agent_config_summary_to_proto(config: AgentConfig, prompt_count: int) -> AgentConfigSummary` (Pydantic → Proto)
- [ ] Implement `agent_config_response_to_proto(config: AgentConfig, prompts: list[Prompt]) -> AgentConfigResponse` (Pydantic → Proto)
- [ ] Implement `prompt_summary_to_proto(prompt: Prompt) -> PromptSummary` (Pydantic → Proto)
- [ ] Implement `agent_config_summary_from_proto(proto: AgentConfigSummary) -> dict` (Proto → dict, for BFF in 9.12b)
- [ ] Implement `agent_config_response_from_proto(proto: AgentConfigResponse) -> dict` (Proto → dict, for BFF in 9.12b)
- [ ] Implement `prompt_summary_from_proto(proto: PromptSummary) -> dict` (Proto → dict, for BFF in 9.12b)
- [ ] Add helper `_datetime_to_proto_timestamp()` if not already shared
- [ ] Export converters in `libs/fp-common/fp_common/converters/__init__.py`
- [ ] Follow existing converter patterns (see `source_config_converters.py`, `cost_converters.py`)

### Task 5: Implement AgentConfigServiceServicer (AC: 2, 3, 4)

- [ ] Create `services/ai-model/src/ai_model/api/agent_config_service.py`
- [ ] Implement `AgentConfigServiceServicer` class skeleton
- [ ] Implement `ListAgentConfigs` RPC with:
  - Pagination via skip/limit (page_token is skip encoded as string)
  - Filter by `agent_type`
  - Filter by `status`
  - Return `AgentConfigSummary` for each config with `prompt_count` from PromptRepository
- [ ] Implement `GetAgentConfig` RPC:
  - Lookup by `agent_id` + optional `version`
  - Use `repository.get_active()` if version empty
  - Use `repository.get_by_version()` if version specified
  - Return full config as JSON in `config_json` field via `config.model_dump_json()`
  - Denormalize linked prompts into response using `prompt_repository.list_by_agent()`
  - Return NOT_FOUND gRPC error if agent_id doesn't exist
- [ ] Implement `ListPromptsByAgent` RPC:
  - Lookup prompts by `agent_id`
  - Optional filter by `status`
  - Return `PromptSummary` for each prompt
- [ ] Use converters from `fp_common.converters`

### Task 6: Register gRPC Service (AC: 5)

- [ ] Update `GrpcServer.start()` in `grpc_server.py` to register `AgentConfigServiceServicer`
- [ ] Pass MongoDB database + repositories to the servicer
- [ ] Add `AgentConfigService` to server reflection service names
- [ ] Verify all services accessible on port 50051

### Task 7: Unit Tests (AC: 6)

- [ ] Create `tests/unit/ai_model/api/test_agent_config_service.py`
- [ ] Test `ListAgentConfigs` with no filters
- [ ] Test `ListAgentConfigs` with `agent_type="extractor"`
- [ ] Test `ListAgentConfigs` with `agent_type="explorer"`
- [ ] Test `ListAgentConfigs` with `status="active"`
- [ ] Test `ListAgentConfigs` combined filters
- [ ] Test `ListAgentConfigs` pagination (page_size, page_token)
- [ ] Test `ListAgentConfigs` empty result set
- [ ] Test `GetAgentConfig` success case (active version)
- [ ] Test `GetAgentConfig` with specific version
- [ ] Test `GetAgentConfig` returns linked prompts
- [ ] Test `GetAgentConfig` NOT_FOUND case
- [ ] Test `ListPromptsByAgent` success case
- [ ] Test `ListPromptsByAgent` with status filter
- [ ] Test `ListPromptsByAgent` empty result
- [ ] Test invalid `page_token` handling (reset to 0)
- [ ] Mock `AgentConfigRepository` and `PromptRepository` in tests
- [ ] Create `tests/unit/fp_common/converters/test_agent_config_converters.py` for converter unit tests

### Task 8: Create New E2E Tests for AC-E2E (MANDATORY - DO NOT SKIP)

> **CRITICAL: This task is NON-NEGOTIABLE and BLOCKS story completion.**
> - Story CANNOT be marked "review" or "done" without E2E tests
> - Unit tests alone are NOT sufficient - E2E validates real infrastructure
> - Skipping this task violates the Definition of Done

**File to create:** `tests/e2e/scenarios/test_13_agent_config_service.py`

**Why this matters:** E2E tests validate the full stack (gRPC → MongoDB → Response) with real DAPR service invocation. Unit tests with mocks cannot catch integration issues.

#### 8.1 Verify Seed Data Exists
- [ ] Check `tests/e2e/infrastructure/seed_data/` for agent_configs and prompts
- [ ] Verify at least 2 agent configs exist in seed data (different types: extractor, explorer)
- [ ] Verify prompts linked to those agents exist in seed data
- [ ] If missing, create seed data files before writing tests

#### 8.2 Create E2E Test File
- [ ] Create `tests/e2e/scenarios/test_13_agent_config_service.py`
- [ ] Follow existing E2E test patterns (see `test_12_source_config_service.py`)
- [ ] Create `AgentConfigServiceClient` helper in test file (or add to `mcp_clients.py`)

#### 8.3 Implement Required Test Cases
- [ ] `test_list_agent_configs_returns_all()` - ListAgentConfigs returns configs from seed
- [ ] `test_list_agent_configs_with_type_filter()` - Filter by agent_type works
- [ ] `test_list_agent_configs_with_status_filter()` - Filter by status works
- [ ] `test_get_agent_config_returns_full_json()` - GetAgentConfig returns valid config_json
- [ ] `test_get_agent_config_includes_prompts()` - GetAgentConfig returns linked prompts
- [ ] `test_get_agent_config_not_found()` - GetAgentConfig returns NOT_FOUND for invalid ID
- [ ] `test_list_prompts_by_agent_returns_prompts()` - ListPromptsByAgent returns linked prompts
- [ ] `test_list_prompts_by_agent_empty()` - ListPromptsByAgent returns empty for agent with no prompts

#### 8.4 Run E2E Tests Locally (BEFORE marking story complete)
```bash
# Start E2E infrastructure
bash scripts/e2e-up.sh --build

# Run pre-flight validation
bash scripts/e2e-preflight.sh

# Run the new E2E tests specifically
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/test_13_agent_config_service.py -v

# Run FULL E2E suite to check for regressions
bash scripts/e2e-test.sh --keep-up

# Tear down
bash scripts/e2e-up.sh --down
```

#### 8.5 Capture Evidence
- [ ] Paste test output in "Local Test Run Evidence" section below
- [ ] All test cases PASS
- [ ] No regressions in other E2E tests

**BLOCKER:** Do NOT proceed to Git Workflow until Task 8 is 100% complete with passing tests.

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 9.12a: AgentConfigService gRPC in AI Model"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/9-12a-agent-config-grpc
  ```

**Branch name:** `story/9-12a-agent-config-grpc`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/9-12a-agent-config-grpc`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 9.12a: AgentConfigService gRPC in AI Model" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/9-12a-agent-config-grpc`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

> **REGRESSION RULE - NO EXCEPTIONS:**
> - Run the **FULL** test suite, not just tests you think are related to your change.
> - A previously passing test that now fails **IS a regression caused by your change**.
> - **Zero failures** is the only acceptable outcome. Fix all regressions before proceeding.

### 1. Unit Tests
```bash
pytest tests/unit/ -v
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

# Wait for services, then run tests
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v

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
git push origin story/9-12a-agent-config-grpc

# Trigger E2E CI workflow
gh workflow run "E2E Tests" --ref story/9-12a-agent-config-grpc

# Wait and check status
sleep 10
gh run list --workflow="E2E Tests" --branch story/9-12a-agent-config-grpc --limit 1
```
**CI Run ID:** _______________
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### Architecture Compliance

**This is a backend-only story.** No frontend changes required.

**Layer Architecture (ADR-019):**
```
Admin UI (future 9.12c) → BFF (future 9.12b) → AI Model gRPC → MongoDB
                                                 ↑ THIS STORY
```

### Critical: Read-Only Service

Per ADR-019, this service is **READ-ONLY**. All write operations (create, update, delete) are handled by the `agent-config` and `prompt-config` CLI tools.

| Operation | Tool | Rationale |
|-----------|------|-----------|
| **Create/Update/Delete** | `agent-config` / `prompt-config` CLI | Complex validation, version management |
| **Read/List** | AgentConfigService gRPC | Simple queries for Admin UI |

### Proto Definition (from ADR-019 Decision 3)

Add to `proto/ai_model/v1/ai_model.proto` after existing services:

```protobuf
// ============================================================================
// Agent Config Service - Read-only admin visibility (ADR-019)
// Write operations handled by agent-config and prompt-config CLIs
// ============================================================================

service AgentConfigService {
  // List all agent configurations with optional filters
  rpc ListAgentConfigs(ListAgentConfigsRequest) returns (ListAgentConfigsResponse);

  // Get a single agent configuration with its linked prompts
  rpc GetAgentConfig(GetAgentConfigRequest) returns (AgentConfigResponse);

  // List prompts for a specific agent
  rpc ListPromptsByAgent(ListPromptsByAgentRequest) returns (ListPromptsResponse);
}

message ListAgentConfigsRequest {
  int32 page_size = 1;         // Max 100, default 20
  string page_token = 2;       // Pagination cursor
  string agent_type = 3;       // Filter: "extractor", "explorer", "generator", etc.
  string status = 4;           // Filter: "draft", "staged", "active", "archived"
}

message ListAgentConfigsResponse {
  repeated AgentConfigSummary agents = 1;
  string next_page_token = 2;
  int32 total_count = 3;
}

message GetAgentConfigRequest {
  string agent_id = 1;
  string version = 2;          // Optional: specific version (empty = active)
}

message AgentConfigSummary {
  string agent_id = 1;
  string version = 2;
  string agent_type = 3;       // "extractor", "explorer", "generator", "conversational", "tiered-vision"
  string status = 4;           // "draft", "staged", "active", "archived"
  string description = 5;
  string model = 6;            // LLM model identifier
  int32 prompt_count = 7;      // Number of linked prompts
  google.protobuf.Timestamp updated_at = 8;
}

message AgentConfigResponse {
  string agent_id = 1;
  string version = 2;
  string agent_type = 3;
  string status = 4;
  string description = 5;

  // Full config as JSON for detail view
  string config_json = 6;

  // Linked prompts (denormalized for single call)
  repeated PromptSummary prompts = 7;

  google.protobuf.Timestamp created_at = 8;
  google.protobuf.Timestamp updated_at = 9;
}

// Prompt messages
message ListPromptsByAgentRequest {
  string agent_id = 1;
  string status = 2;           // Filter: "draft", "staged", "active", "archived"
}

message ListPromptsResponse {
  repeated PromptSummary prompts = 1;
  int32 total_count = 2;
}

message PromptSummary {
  string id = 1;               // Format: {prompt_id}:{version}
  string prompt_id = 2;
  string agent_id = 3;
  string version = 4;
  string status = 5;           // "draft", "staged", "active", "archived"
  string author = 6;
  google.protobuf.Timestamp updated_at = 7;
}
```

### Implementation Pattern (Follow Story 9.11a)

The new `AgentConfigServiceServicer` should follow the pattern from `SourceConfigServiceServicer`:

```python
# services/ai-model/src/ai_model/api/agent_config_service.py
"""AgentConfig gRPC Service - Read-only admin visibility (ADR-019)."""

import json

import grpc
import structlog
from ai_model.domain.agent_config import AgentConfig, AgentConfigStatus, AgentType
from ai_model.domain.prompt import Prompt, PromptStatus
from ai_model.infrastructure.repositories.agent_config_repository import AgentConfigRepository
from ai_model.infrastructure.repositories.prompt_repository import PromptRepository
from fp_common.converters.agent_config_converters import (
    agent_config_response_to_proto,
    agent_config_summary_to_proto,
    prompt_summary_to_proto,
)
from fp_proto.ai_model.v1 import ai_model_pb2, ai_model_pb2_grpc
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = structlog.get_logger(__name__)


class AgentConfigServiceServicer(ai_model_pb2_grpc.AgentConfigServiceServicer):
    """gRPC service implementation for agent config read-only queries (ADR-019)."""

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        agent_config_repository: AgentConfigRepository,
        prompt_repository: PromptRepository,
    ) -> None:
        self._db = db
        self._agent_config_repository = agent_config_repository
        self._prompt_repository = prompt_repository

    async def ListAgentConfigs(
        self,
        request: ai_model_pb2.ListAgentConfigsRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.ListAgentConfigsResponse:
        """List agent configs with optional filters and pagination."""
        # Implementation here...
        pass

    async def GetAgentConfig(
        self,
        request: ai_model_pb2.GetAgentConfigRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.AgentConfigResponse:
        """Get a single agent config by ID with linked prompts."""
        # Implementation here...
        pass

    async def ListPromptsByAgent(
        self,
        request: ai_model_pb2.ListPromptsByAgentRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.ListPromptsResponse:
        """List prompts for a specific agent."""
        # Implementation here...
        pass
```

### Repository Extensions Required

**AgentConfigRepository** - Add these methods:

```python
async def list_all(
    self,
    page_size: int = 20,
    skip: int = 0,
    agent_type: AgentType | None = None,
    status: AgentConfigStatus | None = None,
) -> list[AgentConfig]:
    """List agent configs with pagination and optional filters."""
    query: dict[str, Any] = {}

    if agent_type is not None:
        query["type"] = agent_type.value

    if status is not None:
        query["status"] = status.value

    cursor = self._collection.find(query).skip(skip).limit(page_size)
    docs = await cursor.to_list(length=page_size)

    return [self._deserialize(doc) for doc in docs]

async def count(
    self,
    agent_type: AgentType | None = None,
    status: AgentConfigStatus | None = None,
) -> int:
    """Count agent configs matching filters."""
    query: dict[str, Any] = {}

    if agent_type is not None:
        query["type"] = agent_type.value

    if status is not None:
        query["status"] = status.value

    return await self._collection.count_documents(query)
```

**PromptRepository** - Add this method:

```python
async def count_by_agent(
    self,
    agent_id: str,
    status: PromptStatus | None = None,
) -> int:
    """Count prompts for an agent."""
    query: dict = {"agent_id": agent_id}
    if status is not None:
        query["status"] = status.value

    return await self._collection.count_documents(query)
```

### Existing Domain Models (DO NOT MODIFY)

**AgentConfig Models** (`services/ai-model/src/ai_model/domain/agent_config.py`):
- `AgentConfig` - Discriminated union of 5 agent types
- `AgentConfigStatus` - draft, staged, active, archived
- `AgentType` - extractor, explorer, generator, conversational, tiered-vision
- All agent types inherit from `AgentConfigBase`

**Prompt Model** (`services/ai-model/src/ai_model/domain/prompt.py`):
- `Prompt` - Prompt entity with versioning
- `PromptStatus` - draft, staged, active, archived
- `PromptContent` - system_prompt, template, output_schema, few_shot_examples
- `PromptMetadata` - author, created_at, updated_at, changelog, git_commit

### Key Design Decisions

1. **Agent + Prompts together** - `GetAgentConfig` returns linked prompts in one call for efficiency
2. **Prompt linked via agent_id** - `Prompt.agent_id` foreign key relationship to `AgentConfig.agent_id`
3. **Version history accessible** - Can query specific versions or list all versions
4. **Full content as JSON** - Complex nested structures returned as JSON strings to avoid proto duplication
5. **Prompt count in summary** - `prompt_count` field requires joining with prompts collection

### Seed Data Requirements

E2E tests require seed data. Create or verify:

**Agent configs** (`tests/e2e/infrastructure/seed_data/agent_configs/`):
```json
[
  {
    "_id": "qc-event-extractor:1.0.0",
    "id": "qc-event-extractor:1.0.0",
    "agent_id": "qc-event-extractor",
    "version": "1.0.0",
    "type": "extractor",
    "status": "active",
    "description": "Extracts structured data from QC analyzer payloads",
    "llm": { "model": "anthropic/claude-3-haiku", "temperature": 0.1, "max_tokens": 500 },
    "input": { "event": "collection.document.received", "schema": {} },
    "output": { "event": "ai.extraction.complete", "schema": {} },
    "extraction_schema": { "required_fields": ["farmer_id", "grade"] },
    "metadata": { "author": "admin", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z" }
  },
  {
    "_id": "disease-diagnosis:1.0.0",
    "id": "disease-diagnosis:1.0.0",
    "agent_id": "disease-diagnosis",
    "version": "1.0.0",
    "type": "explorer",
    "status": "active",
    "description": "Diagnoses tea plant diseases from quality events",
    "llm": { "model": "anthropic/claude-3-5-sonnet", "temperature": 0.3, "max_tokens": 2000 },
    "rag": { "enabled": true, "knowledge_domains": ["plant_diseases"], "top_k": 5, "min_similarity": 0.7 },
    "input": { "event": "knowledge.analysis.requested", "schema": {} },
    "output": { "event": "ai.diagnosis.complete", "schema": {} },
    "metadata": { "author": "admin", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z" }
  }
]
```

**Prompts** (`tests/e2e/infrastructure/seed_data/prompts/`):
```json
[
  {
    "_id": "qc-extraction:1.0.0",
    "id": "qc-extraction:1.0.0",
    "prompt_id": "qc-extraction",
    "agent_id": "qc-event-extractor",
    "version": "1.0.0",
    "status": "active",
    "content": {
      "system_prompt": "You are a data extraction specialist...",
      "template": "Extract data from: {{input}}",
      "output_schema": null,
      "few_shot_examples": null
    },
    "metadata": { "author": "admin", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z" },
    "ab_test": { "enabled": false, "traffic_percentage": 0.0, "test_id": null }
  },
  {
    "_id": "disease-diagnosis-main:1.0.0",
    "id": "disease-diagnosis-main:1.0.0",
    "prompt_id": "disease-diagnosis-main",
    "agent_id": "disease-diagnosis",
    "version": "1.0.0",
    "status": "active",
    "content": {
      "system_prompt": "You are an expert tea plant pathologist...",
      "template": "Analyze quality data for farmer {{farmer_id}}: {{quality_events}}",
      "output_schema": { "type": "object", "properties": { "diagnosis": { "type": "string" } } },
      "few_shot_examples": null
    },
    "metadata": { "author": "jlt", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-15T10:45:00Z" },
    "ab_test": { "enabled": false, "traffic_percentage": 0.0, "test_id": null }
  }
]
```

### File Structure (Changes)

```
proto/ai_model/v1/
├── ai_model.proto                    # MODIFIED - Add AgentConfigService

libs/fp-common/fp_common/converters/
├── __init__.py                       # MODIFIED - Export new converters
├── agent_config_converters.py        # NEW - Pydantic↔Proto converters

services/ai-model/src/ai_model/
├── api/
│   ├── grpc_server.py                # MODIFIED - Register new servicer
│   └── agent_config_service.py       # NEW - AgentConfigServiceServicer
├── infrastructure/repositories/
│   ├── agent_config_repository.py    # MODIFIED - Add list_all, count
│   └── prompt_repository.py          # MODIFIED - Add count_by_agent

libs/fp-proto/src/fp_proto/ai_model/v1/
├── ai_model_pb2.py                   # AUTO-GENERATED
├── ai_model_pb2_grpc.py              # AUTO-GENERATED

tests/
├── unit/ai_model/api/
│   └── test_agent_config_service.py  # NEW - gRPC service unit tests
├── unit/fp_common/converters/
│   └── test_agent_config_converters.py # NEW - Converter unit tests
├── e2e/scenarios/
│   └── test_13_agent_config_service.py # NEW - E2E tests
├── e2e/infrastructure/seed_data/
│   ├── agent_configs/                # VERIFY or CREATE
│   └── prompts/                      # VERIFY or CREATE
```

### Dependencies

- **None** - This is the first story in ADR-019 Decision 3 chain
- **Blocks:** Story 9.12b (BFF client + REST API)

### Previous Story Intelligence

**From Story 9.11a (SourceConfigService):**
- Follow exact same pattern for proto definition + servicer implementation
- Use `page_token` as encoded skip offset (parse int, default 0 if invalid)
- Return `config_json = config.model_dump_json()` for full detail
- Register in `GrpcServer.start()` alongside existing services
- Add to server reflection service names

**From Story 9.11b/9.11c:**
- Source config BFF client pattern for future 9.12b
- Frontend JSON parsing pattern for future 9.12c

### Git Intelligence

**Recent commits (context):**
- `3400064` feat(admin): Source Configuration Viewer UI - Story 9.11c
- `e06f2e4` Story 9.11b: Source Config gRPC Client + REST API in BFF
- `cf0b599` Story 9.11a: SourceConfigService gRPC in Collection Model

### References

- [Source: _bmad-output/architecture/adr/ADR-019-admin-configuration-visibility.md] - Full proto definitions (Decision 3), architecture decisions
- [Source: services/ai-model/src/ai_model/api/grpc_server.py] - Existing gRPC service pattern
- [Source: services/ai-model/src/ai_model/infrastructure/repositories/agent_config_repository.py] - Repository pattern
- [Source: services/ai-model/src/ai_model/infrastructure/repositories/prompt_repository.py] - Prompt repository pattern
- [Source: services/ai-model/src/ai_model/domain/agent_config.py] - AgentConfig domain models
- [Source: services/ai-model/src/ai_model/domain/prompt.py] - Prompt domain model
- [Source: _bmad-output/sprint-artifacts/9-11a-source-config-grpc-collection-model.md] - Reference implementation pattern
- [Source: _bmad-output/epics/epic-9-admin-portal/story-912a-agent-config-grpc-ai-model.md] - Epic story definition
- [Source: _bmad-output/epics/epic-9-admin-portal/use-cases.md#UC9.2] - Use case definition
- [Source: _bmad-output/project-context.md] - Architecture rules and patterns

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
