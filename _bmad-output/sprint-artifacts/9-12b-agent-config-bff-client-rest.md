# Story 9.12b: Agent Config gRPC Client + REST API in BFF

**Status:** in-progress
**GitHub Issue:** #237

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **frontend developer**,
I want **REST API endpoints in the BFF that proxy agent config and prompt data from AI Model**,
so that **the Admin UI can fetch AI agent configurations and their linked prompts via standard REST calls**.

## Use Case Context

**Epic:** 9 - Platform Admin Portal
**Use Case:** UC9.2: View AI Agent and Prompt Configurations
**Steps Covered:** Step 2 (BFF gRPC client + REST layer)
**Input (from preceding steps):** AgentConfigService gRPC endpoints accessible via DAPR in AI Model (Story 9.12a)
**Output (for subsequent steps):** REST API endpoints `/api/admin/ai-agents` ready for Admin UI consumption (Story 9.12c)
**E2E Verification:** Admin UI (or curl) can call `GET /api/admin/ai-agents` and receive paginated JSON response with agent config summaries; `GET /api/admin/ai-agents/{agent_id}` returns detail with linked prompts

## Acceptance Criteria

### AC 9.12b.1: AgentConfigClient gRPC Client

**Given** the AI Model AgentConfigService exists (from Story 9.12a)
**When** I implement `AgentConfigClient` in the BFF
**Then** the client:
- Inherits from `BaseGrpcClient` with `target_app_id="ai-model"`
- Implements `list_agent_configs()` returning `PaginatedResponse[AgentConfigSummary]`
- Implements `get_agent_config()` returning `AgentConfigDetail`
- Implements `list_prompts_by_agent()` returning `list[PromptSummary]`
- Uses `@grpc_retry` decorator on all methods
- Uses `metadata=self._get_metadata()` for DAPR routing
- Converts proto responses to Pydantic domain models (NOT dicts)
- Handles gRPC errors via `_handle_grpc_error()`

### AC 9.12b.2: Pydantic Domain Models

**Given** converters exist in fp-common that return dicts (from Story 9.12a)
**When** I create domain models for the BFF client
**Then** I have:
- `AgentConfigSummary` model (agent_id, version, agent_type, status, description, model, prompt_count, updated_at)
- `AgentConfigDetail` model (extends summary with config_json, prompts list, created_at)
- `PromptSummary` model (id, prompt_id, agent_id, version, status, author, updated_at)
- Models in `libs/fp-common/fp_common/models/agent_config_summary.py` (new file)
- Exported in `libs/fp-common/fp_common/models/__init__.py`
- Update converters to return Pydantic models instead of dicts

### AC 9.12b.3: REST Endpoint - List AI Agents

**Given** the BFF is running with AgentConfigClient
**When** I call `GET /api/admin/ai-agents`
**Then** I receive:
- JSON response with `data[]` array and `pagination` object (following BFF pattern)
- `pagination` contains `total_count`, `page_size`, `next_page_token`
- Status 200 with paginated AgentConfigSummary records
- Query params supported: `page_size` (default 20, max 100), `page_token`, `agent_type`, `status`
- Status 401 if not authenticated
- Status 403 if not platform_admin role
- Status 503 if AI Model service unavailable

### AC 9.12b.4: REST Endpoint - Get AI Agent Detail

**Given** an agent config exists with agent_id "disease-diagnosis"
**When** I call `GET /api/admin/ai-agents/disease-diagnosis`
**Then** I receive:
- JSON response with full AgentConfigDetail
- `config_json` field containing the complete configuration as JSON string
- `prompts[]` array with linked PromptSummary objects
- Status 200 on success
- Status 404 if agent_id not found
- Status 401/403 for auth errors
- Status 503 for service unavailable

### AC 9.12b.5: REST Endpoint - List Prompts by Agent

**Given** prompts exist linked to agent_id "disease-diagnosis"
**When** I call `GET /api/admin/ai-agents/disease-diagnosis/prompts`
**Then** I receive:
- JSON response with `data[]` array of PromptSummary objects
- `total_count` field
- Query param `status` for optional filtering
- Status 200 on success
- Status 404 if agent_id not found
- Status 401/403 for auth errors

### AC 9.12b.6: Unit Tests

**Given** the AgentConfigClient and REST routes
**When** unit tests run
**Then** all tests pass covering:
- `AgentConfigClient.list_agent_configs()` with no filters
- `AgentConfigClient.list_agent_configs()` with all filter combinations
- `AgentConfigClient.get_agent_config()` success case
- `AgentConfigClient.get_agent_config()` NOT_FOUND error handling
- `AgentConfigClient.list_prompts_by_agent()` success case
- REST route `/api/admin/ai-agents` list endpoint
- REST route `/api/admin/ai-agents/{agent_id}` detail endpoint
- REST route `/api/admin/ai-agents/{agent_id}/prompts` prompts endpoint
- Auth middleware (mock authenticated user, reject unauthenticated)
- Error response mapping (gRPC → HTTP status codes)

### AC-E2E (from Use Case)

**Given** the E2E infrastructure is running with AI Model containing seed agent configs and prompts
**When** I call `GET /api/admin/ai-agents` via the BFF
**Then** the response contains `total_count >= 2` and `data[]` with valid AgentConfigSummary objects
**And** calling `GET /api/admin/ai-agents/{agent_id}` returns AgentConfigDetail with `prompts[]` containing linked prompts

## Tasks / Subtasks

### Task 1: Create Pydantic Domain Models (AC: 2)

- [ ] Create `libs/fp-common/fp_common/models/agent_config_summary.py`
- [ ] Define `AgentConfigSummary` Pydantic model
- [ ] Define `AgentConfigDetail` Pydantic model
- [ ] Define `PromptSummary` Pydantic model
- [ ] Export models in `libs/fp-common/fp_common/models/__init__.py`
- [ ] Run: `ruff check libs/fp-common/ && ruff format libs/fp-common/`

### Task 2: Update Proto-to-Domain Converters (AC: 2)

- [ ] Update `libs/fp-common/fp_common/converters/agent_config_converters.py`
- [ ] Change `agent_config_summary_from_proto()` to return `AgentConfigSummary` model (not dict)
- [ ] Change `agent_config_response_from_proto()` to return `AgentConfigDetail` model (not dict)
- [ ] Change `prompt_summary_from_proto()` to return `PromptSummary` model (not dict)
- [ ] Ensure converters handle timestamp conversion properly
- [ ] Export updated converters in `libs/fp-common/fp_common/converters/__init__.py`

### Task 3: Implement AgentConfigClient (AC: 1)

- [ ] Create `services/bff/src/bff/infrastructure/clients/agent_config_client.py`
- [ ] Inherit from `BaseGrpcClient` with `target_app_id="ai-model"`
- [ ] Implement `list_agent_configs()` returning `PaginatedResponse[AgentConfigSummary]`
- [ ] Implement `get_agent_config()` returning `AgentConfigDetail`
- [ ] Implement `list_prompts_by_agent()` returning `list[PromptSummary]`
- [ ] Use `AgentConfigServiceStub` from `ai_model_pb2_grpc`
- [ ] Use converters from `fp_common.converters.agent_config_converters`
- [ ] Handle gRPC errors with `_handle_grpc_error()`
- [ ] Export client in `services/bff/src/bff/infrastructure/clients/__init__.py`

### Task 4: Implement REST Routes (AC: 3, 4, 5)

- [ ] Create `services/bff/src/bff/api/routes/admin/ai_agents.py`
- [ ] Implement list endpoint `GET /api/admin/ai-agents` with pagination and filters
- [ ] Implement detail endpoint `GET /api/admin/ai-agents/{agent_id}`
- [ ] Implement prompts endpoint `GET /api/admin/ai-agents/{agent_id}/prompts`
- [ ] Create response schema models in `services/bff/src/bff/api/schemas/admin/agent_config_schemas.py`
- [ ] Register router in `services/bff/src/bff/api/routes/admin/__init__.py`
- [ ] Routes auto-registered via admin router (no main.py changes needed)

### Task 5: Create Response Schema Models (AC: 3, 4, 5)

- [ ] Create `services/bff/src/bff/api/schemas/admin/agent_config_schemas.py`
- [ ] Define `AgentConfigSummaryResponse` with `from_domain()` classmethod
- [ ] Define `AgentConfigDetailResponse` with `from_domain()` classmethod
- [ ] Define `PromptSummaryResponse` with `from_domain()` classmethod
- [ ] Define `AgentConfigListResponse` using `PaginationMeta`
- [ ] Define `PromptListResponse` for prompts endpoint
- [ ] Export schemas in `services/bff/src/bff/api/schemas/admin/__init__.py`

### Task 6: Unit Tests - Client (AC: 6)

- [ ] Create `tests/unit/bff/test_agent_config_client.py`
- [ ] Test client initialization (target_app_id, dapr_grpc_port, direct_host, channel)
- [ ] Test metadata generation for DAPR routing
- [ ] Test `list_agent_configs()` returns `PaginatedResponse[AgentConfigSummary]`
- [ ] Test `list_agent_configs()` with `agent_type` filter
- [ ] Test `list_agent_configs()` with `status` filter
- [ ] Test `list_agent_configs()` pagination (page_size, page_token, next_page_token)
- [ ] Test `get_agent_config()` returns `AgentConfigDetail` with prompts
- [ ] Test `get_agent_config()` raises `NotFoundError` when not found
- [ ] Test `get_agent_config()` raises `ServiceUnavailableError` on connection failure
- [ ] Test `list_prompts_by_agent()` returns `list[PromptSummary]`
- [ ] Test `list_prompts_by_agent()` with status filter
- [ ] Test proto-to-domain conversion (timestamps, optional fields)

### Task 7: Unit Tests - Routes (AC: 6)

- [ ] Create `tests/unit/bff/test_agent_config_routes.py`
- [ ] Test `GET /api/admin/ai-agents` returns 200 with valid response
- [ ] Test `GET /api/admin/ai-agents` with pagination params (page_size, page_token)
- [ ] Test `GET /api/admin/ai-agents` with agent_type filter
- [ ] Test `GET /api/admin/ai-agents` with status filter
- [ ] Test page_size validation (max 100) returns 422
- [ ] Test empty result returns 200 with empty data array
- [ ] Test `GET /api/admin/ai-agents/{agent_id}` returns 200 with config_json and prompts
- [ ] Test `GET /api/admin/ai-agents/{agent_id}` returns 404 when not found
- [ ] Test `GET /api/admin/ai-agents/{agent_id}/prompts` returns 200 with prompts list
- [ ] Test `GET /api/admin/ai-agents/{agent_id}/prompts` with status filter
- [ ] Test auth middleware rejects non-admin users (403)
- [ ] Test 503 response when service unavailable
- [ ] Test response format compliance (timestamps, pagination)

### Task 8: E2E Tests (MANDATORY - DO NOT SKIP)

> **This task is NON-NEGOTIABLE and BLOCKS story completion.**

- [ ] Create `tests/e2e/scenarios/test_15_agent_config_bff.py`
- [ ] Test `GET /api/admin/ai-agents` returns paginated data with at least 3 configs
- [ ] Test pagination with page_size=2 and page_token navigation
- [ ] Test agent_type filter (extractor, explorer, etc.)
- [ ] Test status filter (active, archived)
- [ ] Test `GET /api/admin/ai-agents/{agent_id}` returns detail with config_json
- [ ] Test `GET /api/admin/ai-agents/{agent_id}` returns linked prompts array
- [ ] Test 404 response for nonexistent agent_id
- [ ] Test `GET /api/admin/ai-agents/{agent_id}/prompts` returns prompts list
- [ ] Test 403 response for non-admin users (factory_manager)
- [ ] Run full E2E suite to verify no regressions

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 9.12b: Agent Config gRPC Client + REST API in BFF"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/9-12b-agent-config-bff-client-rest
  ```

**Branch name:** `feature/9-12b-agent-config-bff-client-rest`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin feature/9-12b-agent-config-bff-client-rest`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 9.12b: Agent Config gRPC Client + REST API in BFF" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d feature/9-12b-agent-config-bff-client-rest`

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
pytest tests/unit/bff/test_agent_config_client.py tests/unit/bff/test_agent_config_routes.py -v
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

# Pre-flight validation
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
git push origin feature/9-12b-agent-config-bff-client-rest

# Trigger E2E CI workflow
gh workflow run "E2E Tests" --ref feature/9-12b-agent-config-bff-client-rest

# Wait and check status
sleep 10
gh run list --workflow="E2E Tests" --branch feature/9-12b-agent-config-bff-client-rest --limit 1
```
**CI Run ID:** _______________
**CI Status:** [ ] Passed / [ ] Failed
**CI E2E Status:** [ ] Passed
**Verification Date:** _______________

---

## Dev Notes

### Architecture Compliance

**This is a BFF layer story.** Connects frontend (future 9.12c) to backend (9.12a).

**Layer Architecture (ADR-019):**
```
Admin UI (future 9.12c) → BFF REST API → AgentConfigClient → AI Model gRPC
                          ↑ THIS STORY
```

**Pattern to Follow:** ADR-012 BFF Service Composition

### Critical: Follow Existing BFF Patterns

**MUST USE THESE PATTERNS:**

1. **BaseGrpcClient inheritance** - See `services/bff/src/bff/infrastructure/clients/base.py`
2. **`@grpc_retry` decorator** - All methods must have retry logic
3. **DAPR metadata** - `metadata=self._get_metadata()` on all gRPC calls
4. **Pydantic models** - Return domain models, NOT `dict[str, Any]`
5. **PaginatedResponse** - Use `PaginatedResponse.from_client_response()` for list methods
6. **Error handling** - Map gRPC errors to domain exceptions, then to HTTP status codes

### Existing Converters (From Story 9.12a)

The converters exist in `libs/fp-common/fp_common/converters/agent_config_converters.py`:
- `agent_config_summary_from_proto()` - Currently returns dict, update to return Pydantic model
- `agent_config_response_from_proto()` - Currently returns dict, update to return Pydantic model
- `prompt_summary_from_proto()` - Currently returns dict, update to return Pydantic model

**Update these converters to return Pydantic models instead of dicts to follow BFF patterns.**

### gRPC Stub Usage

```python
from fp_proto.ai_model.v1 import ai_model_pb2, ai_model_pb2_grpc

# In AgentConfigClient
stub = await self._get_stub(ai_model_pb2_grpc.AgentConfigServiceStub)
request = ai_model_pb2.ListAgentConfigsRequest(
    page_size=page_size,
    page_token=page_token or "",
    agent_type=agent_type or "",
    status=status or "",
)
response = await stub.ListAgentConfigs(request, metadata=self._get_metadata())
```

### REST Route Pattern

```python
from bff.infrastructure.clients import NotFoundError, ServiceUnavailableError
from bff.api.middleware.auth import require_platform_admin
from bff.infrastructure.clients.agent_config_client import AgentConfigClient

router = APIRouter(prefix="/ai-agents", tags=["admin-ai-agents"])

def get_agent_config_client() -> AgentConfigClient:
    """Dependency for AgentConfigClient."""
    direct_host = os.environ.get("AI_MODEL_GRPC_HOST")
    return AgentConfigClient(direct_host=direct_host)

@router.get("")
async def list_ai_agents(...) -> AgentConfigListResponse:
    try:
        result = await client.list_agent_configs(...)
        return AgentConfigListResponse(
            data=[AgentConfigSummaryResponse.from_domain(item) for item in result.data],
            pagination=PaginationMeta(
                total_count=result.pagination.total_count,
                page_size=result.pagination.page_size,
                next_page_token=result.pagination.next_page_token,
            ),
        )
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=...) from e
```

### Previous Story Intelligence (9.12a & 9.11b)

**From Story 9.12a completed 2026-01-28:**
- AgentConfigService gRPC implemented in AI Model
- Proto definitions added to `proto/ai_model/v1/ai_model.proto`
- E2E tests pass (16 tests in `test_14_agent_config_service.py`)
- Converters created but return dicts (need update to return Pydantic models)
- Seed data: 3 agent configs, 3 prompts in `tests/e2e/infrastructure/seed/`

**From Story 9.11b (Reference Pattern):**
- Follow exact same pattern for BFF client implementation
- `SourceConfigClient` at `services/bff/src/bff/infrastructure/clients/source_config_client.py`
- REST routes at `services/bff/src/bff/api/routes/admin/source_configs.py`
- Response schemas at `services/bff/src/bff/api/schemas/admin/source_config_schemas.py`
- PaginatedResponse field access: `result.data` not `result.items`, `result.pagination.*`

**Key learnings:**
- Use `AgentConfigServiceStub` (not `AiModelServiceStub`) for agent config operations
- Page token is skip offset encoded as string
- `config_json` contains full model serialized via `model_dump_json()`
- Empty strings for nullable proto fields (agent_type, status) convert to None for API response
- Add `AI_MODEL_GRPC_HOST` env var to docker-compose for E2E tests

### File Structure (Changes)

```
libs/fp-common/fp_common/
├── models/
│   ├── __init__.py                    # MODIFIED - Export new models
│   └── agent_config_summary.py        # NEW - AgentConfigSummary, AgentConfigDetail, PromptSummary
├── converters/
│   └── agent_config_converters.py     # MODIFIED - Return Pydantic models not dicts

services/bff/src/bff/
├── infrastructure/clients/
│   ├── __init__.py                    # MODIFIED - Export AgentConfigClient
│   └── agent_config_client.py         # NEW - AgentConfigClient
├── api/
│   ├── routes/admin/
│   │   ├── __init__.py                # MODIFIED - Register router
│   │   └── ai_agents.py               # NEW - REST endpoints
│   └── schemas/admin/
│       ├── __init__.py                # MODIFIED - Export schemas
│       └── agent_config_schemas.py    # NEW - Response schemas

tests/
├── unit/bff/
│   ├── test_agent_config_client.py    # NEW - Client unit tests
│   └── test_agent_config_routes.py    # NEW - Route unit tests
├── unit/fp_common/converters/
│   └── test_agent_config_converters.py  # MODIFIED - Proto-to-Pydantic tests
├── e2e/scenarios/
│   └── test_15_agent_config_bff.py    # NEW - E2E tests
├── e2e/infrastructure/
│   └── docker-compose.e2e.yaml        # MODIFIED - Add AI_MODEL_GRPC_HOST env var
```

### Dependencies

- **Depends on:** Story 9.12a (AgentConfigService gRPC in AI Model) - DONE
- **Blocks:** Story 9.12c (AI Agent & Prompt Viewer UI)

### Proto Definition Reference (from 9.12a)

```protobuf
service AgentConfigService {
  rpc ListAgentConfigs(ListAgentConfigsRequest) returns (ListAgentConfigsResponse);
  rpc GetAgentConfig(GetAgentConfigRequest) returns (AgentConfigResponse);
  rpc ListPromptsByAgent(ListPromptsByAgentRequest) returns (ListPromptsResponse);
}
```

The response messages include:
- `AgentConfigSummary`: agent_id, version, agent_type, status, description, model, prompt_count, updated_at
- `AgentConfigResponse`: includes above + config_json, prompts[], created_at
- `PromptSummary`: id, prompt_id, agent_id, version, status, author, updated_at

### E2E Seed Data Available

From Story 9.12a, seed data exists:
- `tests/e2e/infrastructure/seed/agent_configs.json` - 3 agent configs
- `tests/e2e/infrastructure/seed/prompts.json` - 3 prompts

Agent configs: qc-event-extractor (extractor), disease-diagnosis (explorer), weekly-action-plan (generator)
Prompts: qc-extraction, disease-diagnosis-main, weekly-action-plan-main

### References

- [Source: _bmad-output/architecture/adr/ADR-019-admin-configuration-visibility.md#Decision-4] - BFF layer architecture
- [Source: _bmad-output/architecture/adr/ADR-012-bff-service-composition.md] - BFF patterns
- [Source: services/bff/src/bff/infrastructure/clients/base.py] - BaseGrpcClient pattern
- [Source: services/bff/src/bff/infrastructure/clients/source_config_client.py] - Reference client implementation (9.11b)
- [Source: services/bff/src/bff/api/routes/admin/source_configs.py] - Reference REST route pattern (9.11b)
- [Source: libs/fp-common/fp_common/converters/agent_config_converters.py] - Existing converters (need update)
- [Source: _bmad-output/sprint-artifacts/9-12a-agent-config-grpc-ai-model.md] - Dependency story
- [Source: _bmad-output/sprint-artifacts/9-11b-source-config-bff-client-rest.md] - Reference pattern story
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
