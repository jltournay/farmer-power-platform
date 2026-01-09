# Story 0.75.16b: Event Subscriber Workflow Wiring

**Status:** in-progress
**GitHub Issue:** #143

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer building AI agent infrastructure**,
I want the event subscriber wired to the workflow execution service,
So that agent requests received via DAPR events can execute workflows and publish results back to domain models.

## Context

Story 0.75.16 implemented the LangGraph SDK integration and `WorkflowExecutionService`. Story 0.75.8 implemented the event subscriber and publisher. However, **these components are NOT connected** - the subscriber currently uses `execute_agent_placeholder()` which returns a mock result.

**CRITICAL GAP FROM 0.75.8:** The subscriber is NOT connected to `WorkflowExecutionService` or `EventPublisher`. Without this wiring, agents cannot be invoked via events and results cannot be published back to domain models.

**TYPE SAFETY ISSUE FROM 0.75.16:** The `WorkflowExecutionService.execute()` accepts `agent_config: dict[str, Any]` instead of the proper Pydantic model. This loses type safety, IDE support, and creates potential runtime errors. This story fixes this technical debt.

**EVENT MODEL SHARING ISSUE:** AI event models (`AgentRequestEvent`, `AgentCompletedEvent`, `EntityLinkage`, etc.) are in `ai_model/events/models.py`. Collection Model needs to subscribe to AI results but CANNOT import from AI Model service. These models must be moved to `fp-common` for cross-service sharing.

This story bridges the gap by:
1. **Moving event models to fp-common:** Share `AgentRequestEvent`, `AgentCompletedEvent`, `EntityLinkage`, etc. with Collection Model
2. **Fixing type safety:** Refactoring `WorkflowExecutionService` to accept `AgentConfig` Pydantic models (not dict)
3. **Using existing event models:** Workflows return `AgentResult`, executor builds `AgentCompletedEvent`/`AgentFailedEvent`
4. **Creating `AgentExecutor`:** Orchestrator that coordinates workflow execution with Pydantic models throughout
5. **Wiring subscriber:** Connect to `AgentExecutor` instead of the placeholder
6. **Publishing results:** Ensure results are published back via `EventPublisher` with `linkage` passthrough

**Data Flow (what this story enables):**
```
Domain Model → publishes ai.agent.requested → AI Model subscriber
    ↓
subscriber.py → AgentExecutor.execute(event)
    ↓
AgentExecutor → AgentConfigCache.get(agent_id) → get agent config from MongoDB
    ↓
AgentExecutor → PromptCache.get(prompt_id) → get prompt from MongoDB
    ↓
WorkflowExecutionService.execute(agent_type, config, prompt, input)
    ↓
LangGraph Workflow runs (Extractor, Explorer, etc.)
    ↓
EventPublisher.publish_agent_completed(result) → Domain Model receives result
```

**Why this is separate from 0.75.17 (Extractor):**
This is **framework infrastructure** that benefits ALL agent types. The Extractor story (0.75.17) focuses on the specific agent type, golden samples, and testing - not on event-driven execution infrastructure.

**Architecture References:**
- Event Flow: `_bmad-output/architecture/ai-model-architecture/event-driven-agent-execution.md`
- Developer Guide SDK: `_bmad-output/ai-model-developer-guide/1-sdk-framework.md`

## Acceptance Criteria

1. **AC1: Fix WorkflowExecutionService Type Safety** - Refactor to accept Pydantic models:
   - **CRITICAL:** Current `execute()` accepts `agent_config: dict[str, Any]` - this loses type safety
   - **Use EXISTING event models** - do NOT create new `WorkflowResult`:
     - `AgentResult` (discriminated union) for workflow output
     - `AgentCompletedEvent` / `AgentFailedEvent` for publishing
   - Update `WorkflowExecutionService.execute()` signature:
     ```python
     # BEFORE (dict - unsafe):
     async def execute(self, agent_config: dict[str, Any], ...) -> dict[str, Any]:

     # AFTER (Pydantic - type safe, uses existing models):
     async def execute(self, agent_config: AgentConfig, ...) -> AgentResult:
     ```
   - Update all convenience methods (`execute_extractor`, `execute_explorer`, etc.) to return typed results:
     - `execute_extractor()` → `ExtractorAgentResult`
     - `execute_explorer()` → `ExplorerAgentResult`
     - etc.
   - Update workflow builders to accept `AgentConfig` instead of dict
   - Update existing unit tests to pass Pydantic models
   - **Refactor all workflow implementations** to use Pydantic attribute access:
     ```python
     # BEFORE (dict - unsafe, loses IDE support):
     agent_config = state.get("agent_config", {})
     extraction_schema = agent_config.get("extraction_schema", {})
     llm_config = agent_config.get("llm", {})
     model = llm_config.get("model", "default")

     # AFTER (Pydantic - type safe, IDE autocomplete):
     agent_config: ExtractorConfig = state["agent_config"]
     extraction_schema = agent_config.extraction_schema
     model = agent_config.llm.model
     ```
   - Update `ExtractorState`, `ExplorerState`, etc. to type `agent_config` field as `AgentConfig`
   - Update all 5 workflow implementations: `extractor.py`, `explorer.py`, `generator.py`, `conversational.py`, `tiered_vision.py`

2. **AC2: AgentExecutor Orchestrator** - Create coordinator for workflow execution:
   - **CRITICAL:** Must pass `linkage` from request through to response events
   - Create `services/ai-model/src/ai_model/events/agent_executor.py`:
     ```python
     class AgentExecutor:
         """Executes agents via WorkflowExecutionService and publishes results."""

         def __init__(
             self,
             workflow_service: WorkflowExecutionService,
             event_publisher: EventPublisher,
             agent_config_cache: AgentConfigCache,
             prompt_cache: PromptCache,
         ):
             ...

         async def execute(self, event: AgentRequestEvent) -> None:
             """Execute agent and publish result.

             CRITICAL: event.linkage MUST be passed to completed/failed events.
             """
             start_time = time.monotonic()

             # 1. Get agent config - returns typed AgentConfig Pydantic model
             agent_config = await self.agent_config_cache.get(event.agent_id)

             # 2. Get prompt template from cache
             prompt_template = await self.prompt_cache.get(agent_config.prompt_id)

             try:
                 # 3. Execute workflow - returns typed AgentResult (discriminated union)
                 result: AgentResult = await self.workflow_service.execute(
                     agent_config=agent_config,  # Pydantic model, NOT dict
                     input_data=event.input_data,
                     prompt_template=prompt_template.template,
                     correlation_id=event.request_id,
                 )

                 execution_time_ms = int((time.monotonic() - start_time) * 1000)

                 # 4. Publish completed - PASS LINKAGE from original request
                 completed = AgentCompletedEvent(
                     request_id=event.request_id,
                     agent_id=event.agent_id,
                     linkage=event.linkage,  # CRITICAL: pass through from request
                     result=result,
                     execution_time_ms=execution_time_ms,
                     model_used=agent_config.llm.model,
                 )
                 await self.event_publisher.publish_agent_completed(completed)

             except Exception as e:
                 # 5. Publish failed - PASS LINKAGE from original request
                 failed = AgentFailedEvent(
                     request_id=event.request_id,
                     agent_id=event.agent_id,
                     linkage=event.linkage,  # CRITICAL: pass through from request
                     error_type=type(e).__name__,
                     error_message=str(e),
                     retry_count=0,
                 )
                 await self.event_publisher.publish_agent_failed(failed)
     ```

3. **AC3: Subscriber Wiring** - Connect subscriber to AgentExecutor:
   - Update `subscriber.py`:
     - Add module-level `_agent_executor: AgentExecutor | None = None`
     - Add `set_agent_executor(executor: AgentExecutor)` function
     - Replace `execute_agent_placeholder(event_data)` with `_agent_executor.execute(event_data)`
     - Remove `execute_agent_placeholder()` function

4. **AC4: Main.py Dependency Wiring** - Wire all dependencies at startup:
   - Update `main.py` startup to:
     - Create `PromptCache` instance
     - Create `WorkflowExecutionService` instance with `mcp_integration` from `app.state`
     - Create `EventPublisher` instance (from 0.75.8)
     - Create `AgentExecutor` with all dependencies
     - Call `set_agent_executor(agent_executor)`

5. **AC5: Implement MCP Context Fetching** - Replace placeholder implementations:
   - **CRITICAL:** `_fetch_mcp_context()` in `explorer.py:534` and `generator.py:345` are placeholders returning `{}`
   - Implement actual MCP context fetching using `AgentToolProvider`:
     ```python
     # BEFORE (placeholder):
     async def _fetch_mcp_context(self, mcp_sources, input_data) -> dict:
         return {}  # Placeholder

     # AFTER (real implementation):
     async def _fetch_mcp_context(self, mcp_sources, input_data) -> dict:
         if not self._tool_provider:
             return {}

         context = {}
         for source in mcp_sources:
             server = source.server
             for tool_name in source.tools:
                 tool = self._tool_provider.get_tool(server, tool_name)
                 result = await tool.ainvoke(input_data)
                 context[f"{server}.{tool_name}"] = result
         return context
     ```
   - Update `ExplorerWorkflow` and `GeneratorWorkflow` constructors to accept `tool_provider: AgentToolProvider`
   - Update `WorkflowExecutionService._create_workflow()` to pass `tool_provider`

6. **AC6: Wire AgentToolProvider** - Connect the unused tool provider:
   - **CRITICAL:** `AgentToolProvider` is created in `main.py:151` but NEVER USED
   - Pass `tool_provider` from `app.state` to `WorkflowExecutionService`
   - Update `WorkflowExecutionService.__init__()` to accept `tool_provider: AgentToolProvider`
   - Pass `tool_provider` to workflows that need MCP context (Explorer, Generator)

7. **AC7: Unit Tests** - Comprehensive test coverage:
   - Test AgentExecutor: successful execution → publishes completed event
   - Test AgentExecutor: failed execution → publishes failed event
   - Test AgentExecutor: missing prompt → appropriate error handling
   - Test AgentExecutor: LLM error → publishes failed event
   - Test subscriber integration: event → executor → workflow → publisher
   - Test type safety: verify Pydantic models flow through entire pipeline
   - Test MCP context fetching: tool invocation → context returned
   - Test MCP error handling: server unavailable → graceful fallback

8. **AC8: E2E Regression** - All existing E2E tests continue to pass:
   - Run full E2E suite with `--build` flag
   - No modifications to existing E2E test files

9. **AC9: CI Passes** - All lint checks and tests pass in CI

## Tasks / Subtasks

- [ ] **Task 0: Move AI Event Models to fp-common** (AC: #1)
  - [ ] **CRITICAL:** Event models must be shared so ALL client models (Collection, Farm, etc.) can subscribe to AI results
  - [ ] Create `libs/fp-common/fp_common/events/ai_model_events.py`:
    - Move `EntityLinkage` from `ai_model/events/models.py`
    - Move `AgentRequestEvent` from `ai_model/events/models.py`
      - **ADD `source_service: str | None = None`** field for observability (e.g., "collection-model", "farm-model")
    - Move `AgentCompletedEvent` from `ai_model/events/models.py`
    - Move `AgentFailedEvent` from `ai_model/events/models.py`
    - Move `AgentResult` discriminated union (all 5 typed results)
    - Move `CostRecordedEvent` from `ai_model/events/models.py`
  - [ ] Update `libs/fp-common/fp_common/events/__init__.py` to export new models
  - [ ] Add `AIModelEventTopic` enum to `libs/fp-common/fp_common/models/domain_events.py`:
    ```python
    class AIModelEventTopic(StrEnum):
        """Valid DAPR Pub/Sub topics for AI Model events.

        Note: AGENT_COMPLETED and AGENT_FAILED use dynamic topic names with agent_id.
        The enum values are prefixes - actual topics are:
        - ai.agent.{agent_id}.completed
        - ai.agent.{agent_id}.failed

        Collection Model subscribes using the agent_id it sent in the request.
        """
        AGENT_REQUESTED = "ai.agent.requested"
        # Note: These are topic prefixes. Publisher appends agent_id:
        # e.g., ai.agent.qc-event-extractor.completed
        AGENT_COMPLETED_PREFIX = "ai.agent"  # Full: ai.agent.{agent_id}.completed
        AGENT_FAILED_PREFIX = "ai.agent"  # Full: ai.agent.{agent_id}.failed
        COST_RECORDED = "ai.cost.recorded"

        @staticmethod
        def agent_completed_topic(agent_id: str) -> str:
            """Get the completed topic for a specific agent."""
            return f"ai.agent.{agent_id}.completed"

        @staticmethod
        def agent_failed_topic(agent_id: str) -> str:
            """Get the failed topic for a specific agent."""
            return f"ai.agent.{agent_id}.failed"
    ```
  - [ ] Update AI Model to import from `fp_common.events.ai_model_events`:
    - Update `ai_model/events/models.py` → re-export from fp_common (backwards compat)
    - Update `ai_model/events/publisher.py` imports
    - Update `ai_model/events/subscriber.py` imports
  - [ ] Update all unit tests to use new import paths
  - [ ] Verify Collection Model can now import: `from fp_common.events.ai_model_events import AgentCompletedEvent`

- [ ] **Task 1: Refactor WorkflowExecutionService for Type Safety** (AC: #1)
  - [ ] **Use EXISTING event models** - do NOT create new `WorkflowResult`:
    - Workflows return `AgentResult` (discriminated union from `events/models.py`)
    - `AgentExecutor` constructs `AgentCompletedEvent` / `AgentFailedEvent` with `linkage`
  - [ ] Update `WorkflowExecutionService.execute()`:
    - Change `agent_config: dict[str, Any]` → `agent_config: AgentConfig`
    - Change return type `dict[str, Any]` → `AgentResult`
  - [ ] Update convenience methods to return typed results:
    - `execute_extractor()` → `ExtractorAgentResult`
    - `execute_explorer()` → `ExplorerAgentResult`
    - `execute_generator()` → `GeneratorAgentResult`
    - `execute_conversational()` → `ConversationalAgentResult`
    - `execute_tiered_vision()` → `TieredVisionAgentResult`
  - [ ] Update workflow builders `__init__` to accept typed config (e.g., `ExtractorConfig`)
  - [ ] Update state TypedDicts to type `agent_config` field:
    - `ExtractorState`: `agent_config: ExtractorConfig`
    - `ExplorerState`: `agent_config: ExplorerConfig`
    - `GeneratorState`: `agent_config: GeneratorConfig`
    - `ConversationalState`: `agent_config: ConversationalConfig`
    - `TieredVisionState`: `agent_config: TieredVisionConfig`
  - [ ] Refactor `extractor.py` - replace all `.get()` with attribute access, return `ExtractorAgentResult`
  - [ ] Refactor `explorer.py` - replace all `.get()` with attribute access, return `ExplorerAgentResult`
  - [ ] Refactor `generator.py` - replace all `.get()` with attribute access, return `GeneratorAgentResult`
  - [ ] Refactor `conversational.py` - replace all `.get()` with attribute access, return `ConversationalAgentResult`
  - [ ] Refactor `tiered_vision.py` - replace all `.get()` with attribute access, return `TieredVisionAgentResult`
  - [ ] Update all existing unit tests to pass Pydantic models instead of dicts
  - [ ] Verify type checking passes: `pyright services/ai-model/`

- [ ] **Task 2: Create AgentExecutor** (AC: #2)
  - [ ] Create `services/ai-model/src/ai_model/events/agent_executor.py`
  - [ ] Implement `AgentExecutor` class with constructor injection
  - [ ] Implement `async execute(event: AgentRequestEvent) -> None`
  - [ ] Pass `AgentConfig` Pydantic model directly to `workflow_service.execute()` (NO `.model_dump()`)
  - [ ] Handle `WorkflowResult.success` → `publish_agent_completed()`
  - [ ] Handle `not WorkflowResult.success` → `publish_agent_failed()`
  - [ ] Handle missing config/prompt errors gracefully
  - [ ] Add structured logging with correlation_id

- [ ] **Task 3: Update Subscriber** (AC: #3)
  - [ ] Add module-level `_agent_executor: AgentExecutor | None = None`
  - [ ] Add `set_agent_executor(executor: AgentExecutor)` function
  - [ ] Replace `execute_agent_placeholder()` call with `_agent_executor.execute()`
  - [ ] Remove `execute_agent_placeholder()` function
  - [ ] Add check: if `_agent_executor is None` → log error and skip

- [ ] **Task 4: Wire Dependencies in main.py** (AC: #4, #6)
  - [ ] Import `AgentExecutor` and `set_agent_executor`
  - [ ] Create `PromptCache` instance with MongoDB client
  - [ ] **Wire RAG services chain** (for Explorer, Generator, Conversational, TieredVision - NOT Extractor):
    ```python
    # RAG chain: RetrievalService → RankingService → WorkflowExecutionService
    # Note: Extractor workflow does NOT use RAG

    if settings.pinecone_enabled:
        # Reuse embedding_service and vector_store from grpc_server.py
        # or create here if main.py is the initialization point
        retrieval_service = RetrievalService(
            embedding_service=embedding_service,
            vector_store=vector_store,
            chunk_repository=rag_chunk_repository,
        )
        ranking_service = RankingService(
            retrieval_service=retrieval_service,
            settings=settings,
        )
    else:
        ranking_service = None  # Workflows degrade gracefully
    ```
  - [ ] Create `WorkflowExecutionService` instance with:
    - `llm_gateway` from `app.state.llm_gateway`
    - `ranking_service` for RAG-enabled workflows (can be None)
    - `mcp_integration` from `app.state.mcp_integration`
    - `tool_provider` from `app.state.tool_provider`
  - [ ] Get `EventPublisher` instance (already created in 0.75.8)
  - [ ] Create `AgentExecutor` with all dependencies
  - [ ] Call `set_agent_executor(agent_executor)` at startup
  - [ ] Ensure proper async initialization order
  - [ ] **Initialization dependency order:**
    ```
    1. MongoDB client
    2. Repositories (rag_chunk, rag_document)
    3. EmbeddingService (if Pinecone enabled)
    4. PineconeVectorStore (if Pinecone enabled)
    5. RetrievalService (if Pinecone enabled)
    6. RankingService (if Pinecone enabled)
    7. LLMGateway
    8. McpIntegration, AgentToolProvider
    9. WorkflowExecutionService (with ranking_service, tool_provider)
    10. AgentConfigCache, PromptCache
    11. EventPublisher
    12. AgentExecutor
    13. set_agent_executor()
    ```

- [ ] **Task 5: Implement MCP Context Fetching** (AC: #5)
  - [ ] Update `ExplorerWorkflow.__init__()` to accept `tool_provider: AgentToolProvider`
  - [ ] Update `GeneratorWorkflow.__init__()` to accept `tool_provider: AgentToolProvider`
  - [ ] Implement `ExplorerWorkflow._fetch_mcp_context()`:
    - Iterate over `mcp_sources` from agent config
    - Use `tool_provider` to get tools and invoke them
    - Return aggregated context dict
    - Handle errors gracefully (log warning, return partial context)
  - [ ] Implement `GeneratorWorkflow._fetch_mcp_context()` (same pattern)
  - [ ] Update `WorkflowExecutionService._create_workflow()`:
    - Pass `tool_provider` to `ExplorerWorkflow`
    - Pass `tool_provider` to `GeneratorWorkflow`

- [ ] **Task 6: Wire AgentToolProvider to WorkflowExecutionService** (AC: #6)
  - [ ] Update `WorkflowExecutionService.__init__()` to accept `tool_provider: AgentToolProvider`
  - [ ] Store `self._tool_provider = tool_provider`
  - [ ] Update `_create_workflow()` to pass `tool_provider` to Explorer and Generator
  - [ ] Update docstrings to document the new parameter

- [ ] **Task 7: Unit Tests for AgentExecutor** (AC: #7)
  - [ ] Create `tests/unit/ai_model/events/test_agent_executor.py`
  - [ ] Test: successful execution publishes completed event
  - [ ] Test: workflow failure publishes failed event
  - [ ] Test: missing agent config → error handling
  - [ ] Test: missing prompt → error handling
  - [ ] Test: LLM error propagates correctly
  - [ ] Test: Pydantic models flow through entire pipeline (no dict conversion)
  - [ ] Mock all dependencies (workflow service, publisher, caches)

- [ ] **Task 8: Unit Tests for MCP Context Fetching** (AC: #7)
  - [ ] Create `tests/unit/ai_model/workflows/test_mcp_context.py`
  - [ ] Test: successful MCP tool invocation returns context
  - [ ] Test: MCP server unavailable → returns empty context (graceful)
  - [ ] Test: partial tool failure → returns partial context
  - [ ] Test: no mcp_sources configured → returns empty context
  - [ ] Mock `AgentToolProvider` and `GrpcMcpTool`

- [ ] **Task 9: Subscriber Integration Tests** (AC: #7)
  - [ ] Create `tests/unit/ai_model/events/test_subscriber_integration.py`
  - [ ] Test: full flow from event → executor → workflow → publisher
  - [ ] Test: executor not set → graceful error handling
  - [ ] Test: event validation errors handled

- [ ] **Task 10: E2E Regression Testing (MANDATORY)** (AC: #8)
  - [ ] Rebuild and start E2E infrastructure with `--build` flag
  - [ ] Verify Docker images were rebuilt (NOT cached)
  - [ ] Run full E2E test suite
  - [ ] Capture output in "Local Test Run Evidence" section
  - [ ] Tear down infrastructure

- [ ] **Task 11: CI Verification** (AC: #9)
  - [ ] Run lint: `ruff check . && ruff format --check .`
  - [ ] Run unit tests locally
  - [ ] Push and verify CI passes
  - [ ] Trigger E2E CI workflow
  - [ ] Verify E2E CI passes before code review

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.75.16b: Event Subscriber Workflow Wiring"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/0-75-16b-event-subscriber-workflow-wiring
  ```

**Branch name:** `feature/0-75-16b-event-subscriber-workflow-wiring`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin feature/0-75-16b-event-subscriber-workflow-wiring`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.75.16b: Event Subscriber Workflow Wiring" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d feature/0-75-16b-event-subscriber-workflow-wiring`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
PYTHONPATH="libs/fp-common:libs/fp-proto/src:services/ai-model/src" pytest tests/unit/ai_model/events/ -v
```
**Output:**
```
(paste test summary here - e.g., "15 passed in 2.5s")
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

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
ruff check . && ruff format --check .
```
**Lint passed:** [ ] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin feature/0-75-16b-event-subscriber-workflow-wiring

# Wait ~30s, then check CI status
gh run list --branch feature/0-75-16b-event-subscriber-workflow-wiring --limit 3
```
**CI Run ID:** _______________
**CI Status:** [ ] Passed / [ ] Failed
**E2E CI Run ID:** _______________
**E2E CI Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### Existing Code to REUSE (DO NOT RECREATE)

| Component | Location | Purpose |
|-----------|----------|---------|
| `WorkflowExecutionService` | `ai_model/workflows/execution_service.py` | Executes workflows (Story 0.75.16) |
| `EventPublisher` | `ai_model/events/publisher.py` | Publishes agent results (Story 0.75.8) |
| `subscriber.py` | `ai_model/events/subscriber.py` | Receives agent requests (Story 0.75.8) |
| `AgentRequestEvent` | `ai_model/events/models.py` | Event model for agent requests |
| `AgentCompletedEvent` | `ai_model/events/models.py` | Event model for completed results |
| `AgentFailedEvent` | `ai_model/events/models.py` | Event model for failed results |
| `AgentConfigCache` | `ai_model/services/agent_config_cache.py` | Agent config caching (Story 0.75.4) |
| `PromptCache` | `ai_model/services/prompt_cache.py` | Prompt caching (Story 0.75.4) |

### NEW Code to CREATE in this story

| Component | Location | Purpose |
|-----------|----------|---------|
| `AgentExecutor` | `ai_model/events/agent_executor.py` | Orchestrates workflow execution, linkage passthrough, publishing |

### EXISTING Event Models to USE (DO NOT RECREATE)

| Component | Location | Purpose |
|-----------|----------|---------|
| `AgentRequestEvent` | `fp_common/events/ai_model_events.py` | Inbound request with `linkage`, `source_service` |
| `AgentCompletedEvent` | `fp_common/events/ai_model_events.py` | Success response with `linkage`, `result` |
| `AgentFailedEvent` | `fp_common/events/ai_model_events.py` | Failure response with `linkage`, `error` |
| `AgentResult` | `fp_common/events/ai_model_events.py` | Discriminated union of 5 typed results |
| `EntityLinkage` | `fp_common/events/ai_model_events.py` | Linkage to plantation entities |

**`AgentRequestEvent` fields:**
```python
class AgentRequestEvent(BaseModel):
    request_id: str                    # Unique request ID
    agent_id: str                      # Which agent to invoke
    linkage: EntityLinkage             # Links to plantation entities
    input_data: dict[str, Any]         # Data for the agent
    source_service: str | None = None  # Optional: "collection-model", "farm-model", etc. (observability)
```

### RAG Usage by Workflow

| Workflow | Uses RAG | Uses MCP | Notes |
|----------|----------|----------|-------|
| `ExtractorWorkflow` | ❌ No | ❌ No | Pure extraction from input text, no knowledge grounding |
| `ExplorerWorkflow` | ✅ Yes | ✅ Yes | RAG in `fetch_context` node via `ranking_service.rank()` |
| `GeneratorWorkflow` | ✅ Yes | ✅ Yes | RAG in `retrieve_knowledge` node via `ranking_service.rank()` |
| `ConversationalWorkflow` | ✅ Conditional | ❌ No | Only if intent = "knowledge-seeking" (not chitchat) |
| `TieredVisionWorkflow` | ✅ Optional | ❌ No | In Tier 2 based on confidence threshold |

**RAG Chain:**
```
RetrievalService → RankingService → WorkflowExecutionService → Workflow
                                                                   ↓
                                                        ranking_service.rank(query, domains)
```

### MODIFIED Code (Type Safety + MCP + RAG Wiring)

| Component | Location | Change |
|-----------|----------|--------|
| `WorkflowExecutionService` | `ai_model/workflows/execution_service.py` | `dict` → `AgentConfig` + `WorkflowResult`, add `ranking_service`, `tool_provider` |
| `ExtractorWorkflow` | `ai_model/workflows/extractor.py` | `.get()` → attribute access (NO RAG) |
| `ExplorerWorkflow` | `ai_model/workflows/explorer.py` | `.get()` → attribute access, implement `_fetch_mcp_context()`, uses `ranking_service` |
| `GeneratorWorkflow` | `ai_model/workflows/generator.py` | `.get()` → attribute access, implement `_fetch_mcp_context()`, uses `ranking_service` |
| `ConversationalWorkflow` | `ai_model/workflows/conversational.py` | `.get()` → attribute access, uses `ranking_service` conditionally |
| `TieredVisionWorkflow` | `ai_model/workflows/tiered_vision.py` | `.get()` → attribute access, uses `ranking_service` in Tier 2 |
| `ExtractorState` | `ai_model/workflows/states/extractor.py` | `agent_config: ExtractorConfig` |
| `ExplorerState` | `ai_model/workflows/states/explorer.py` | `agent_config: ExplorerConfig` |
| `GeneratorState` | `ai_model/workflows/states/generator.py` | `agent_config: GeneratorConfig` |
| `ConversationalState` | `ai_model/workflows/states/conversational.py` | `agent_config: ConversationalConfig` |
| `TieredVisionState` | `ai_model/workflows/states/tiered_vision.py` | `agent_config: TieredVisionConfig` |
| `main.py` | `ai_model/main.py` | Create `WorkflowExecutionService` with `tool_provider`, wire `AgentExecutor` |
| Existing unit tests | `tests/unit/ai_model/workflows/` | Pass Pydantic models instead of dicts |

### File Structure

```
libs/fp-common/fp_common/
├── events/
│   ├── __init__.py          # MODIFIED: Export ai_model_events
│   └── ai_model_events.py   # NEW: Shared event models (moved from ai_model)
│       ├── EntityLinkage
│       ├── AgentRequestEvent
│       ├── AgentCompletedEvent
│       ├── AgentFailedEvent
│       ├── AgentResult (discriminated union)
│       └── CostRecordedEvent
└── models/
    └── domain_events.py     # MODIFIED: Add AIModelEventTopic enum

services/ai-model/src/ai_model/
├── events/
│   ├── agent_executor.py    # NEW: Orchestrates execution, linkage passthrough, publishing
│   ├── subscriber.py        # MODIFIED: Wire to AgentExecutor
│   ├── publisher.py         # MODIFIED: Import from fp_common
│   └── models.py            # MODIFIED: Re-export from fp_common (backwards compat)
├── main.py                  # MODIFIED: Wire dependencies at startup
├── mcp/
│   ├── integration.py       # EXISTING: McpIntegration
│   └── provider.py          # EXISTING: AgentToolProvider (now used!)
└── workflows/
    ├── extractor.py         # MODIFIED: Pydantic access, returns ExtractorAgentResult
    ├── explorer.py          # MODIFIED: Pydantic access, MCP fetch, returns ExplorerAgentResult
    ├── generator.py         # MODIFIED: Pydantic access, MCP fetch, returns GeneratorAgentResult
    └── execution_service.py # MODIFIED: dict → AgentConfig, returns AgentResult
```

### Error Handling Strategy

| Error Type | Handling | Published Event |
|------------|----------|-----------------|
| Missing agent config | Log error, publish failed | `AgentFailedEvent(error="Agent config not found")` |
| Missing prompt | Log error, publish failed | `AgentFailedEvent(error="Prompt not found")` |
| Workflow execution error | Capture error, publish failed | `AgentFailedEvent(error=str(e))` |
| Workflow success | Publish completed | `AgentCompletedEvent(output=result)` |

### Dependencies from Previous Stories

| Story | What it provides | Used in this story |
|-------|-----------------|-------------------|
| 0.75.4 | AgentConfigCache, PromptCache | Config and prompt loading |
| 0.75.8 | EventPublisher, subscriber.py | Event publishing and receiving |
| 0.75.16 | WorkflowExecutionService | Workflow execution |

### Anti-Patterns to AVOID

1. **DO NOT** use `.model_dump()` to convert Pydantic models to dict - pass models directly
2. **DO NOT** accept `dict[str, Any]` in service methods - use typed Pydantic models
3. **DO NOT** create new result models - use existing `AgentResult`, `AgentCompletedEvent`, `AgentFailedEvent`
4. **DO NOT** lose `linkage` - MUST pass through from `AgentRequestEvent` to response events
5. **DO NOT** put business logic in subscriber - use AgentExecutor
6. **DO NOT** create circular imports - keep dependency direction clean
7. **DO NOT** block the event loop - all operations must be async
8. **DO NOT** skip error handling - always publish failed event on error
9. **DO NOT** hardcode agent IDs or prompts - use cache lookups

### References

- [Source: `_bmad-output/epics/epic-0-75-ai-model.md` - Story definitions]
- [Source: `_bmad-output/architecture/ai-model-architecture/event-driven-agent-execution.md`]
- [Source: `_bmad-output/project-context.md` - Repository patterns and testing rules]
- [Source: Story 0.75.8 - Event subscriber/publisher implementation]
- [Source: Story 0.75.16 - WorkflowExecutionService implementation]

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
