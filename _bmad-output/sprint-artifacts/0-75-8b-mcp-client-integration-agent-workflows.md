# Story 0.75.8b: MCP Client Integration for Agent Workflows

**Status:** in-progress
**GitHub Issue:** #105

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer**,
I want AI Model agents to use existing MCP client infrastructure,
So that agents can fetch data from Collection, Plantation, and other domain models.

## Acceptance Criteria

1. **AC1: MCP Integration Module** - Create `services/ai-model/src/ai_model/mcp/integration.py` that integrates existing `fp_common.mcp` with AI Model agent workflows
2. **AC2: Server Registration at Startup** - Register MCP servers at AI Model startup based on agent configurations' `mcp_sources` field
3. **AC3: Parse mcp_sources Config** - Parse `mcp_sources` from `AgentConfig` and register servers with `McpToolRegistry`:
   ```yaml
   mcp_sources:
     - server: collection
       tools: [get_document, get_farmer_context]
     - server: plantation
       tools: [get_plantation_details]
   ```
4. **AC4: Tool Discovery** - Discover tools from registered servers using `McpToolRegistry.discover_tools()`
5. **AC5: Tool Access for Agents** - Make registered MCP tools available to LangGraph agent workflows via `McpToolRegistry.get_tool()`
6. **AC6: Agent Tool Provider** - Create `AgentToolProvider` class that resolves agent's `mcp_sources` to list of `GrpcMcpTool` instances
7. **AC7: Main.py Integration** - Add MCP registry initialization to AI Model lifespan, after cache warming
8. **AC8: Tool Caching** - Cache discovered tools per server with configurable TTL (default 5 minutes)
9. **AC9: Error Handling** - Handle MCP server unavailability gracefully with retry logic and fallback behavior
10. **AC10: Unit Tests** - Minimum 25 unit tests covering registration, discovery, tool access, error scenarios
11. **AC11: CI Passes** - All lint checks and unit tests pass in CI

## Tasks / Subtasks

- [x] **Task 1: Create MCP Integration Package** (AC: #1, #2)
  - [x] Create `services/ai-model/src/ai_model/mcp/__init__.py`
  - [x] Create `services/ai-model/src/ai_model/mcp/integration.py` - Main integration module
  - [x] Create `services/ai-model/src/ai_model/mcp/provider.py` - AgentToolProvider class
  - [x] Import from existing `fp_common.mcp` (GrpcMcpClient, McpToolRegistry, GrpcMcpTool)

- [x] **Task 2: Implement McpIntegration Class** (AC: #1, #2, #3, #4)
  - [x] Create `McpIntegration` class that wraps `McpToolRegistry`:
    ```python
    class McpIntegration:
        """Manages MCP server registration and tool discovery for AI Model.

        Uses fp_common.mcp infrastructure - this is an integration layer,
        NOT a reimplementation.
        """

        def __init__(self, registry: McpToolRegistry | None = None):
            self._registry = registry or McpToolRegistry()
            self._registered_servers: set[str] = set()
            self._discovery_cache: dict[str, datetime] = {}
            self._cache_ttl_seconds: int = 300  # 5 minutes

        def register_from_agent_configs(
            self,
            agent_configs: list[AgentConfig]
        ) -> set[str]:
            """Extract unique MCP servers from all agent configs and register them."""

        async def discover_all_tools(self, refresh: bool = False) -> dict[str, list[dict]]:
            """Discover tools from all registered servers."""

        def get_tool(self, server: str, tool_name: str) -> GrpcMcpTool:
            """Get a specific tool from a registered server."""
    ```

- [x] **Task 3: Implement AgentToolProvider** (AC: #5, #6)
  - [ ] Create `AgentToolProvider` class:
    ```python
    class AgentToolProvider:
        """Resolves agent config's mcp_sources to LangChain tools.

        This class bridges agent configuration to actual tool instances
        that can be used in LangGraph workflows.
        """

        def __init__(self, integration: McpIntegration):
            self._integration = integration

        def get_tools_for_agent(
            self,
            agent_config: AgentConfig
        ) -> list[GrpcMcpTool]:
            """Get all MCP tools configured for an agent.

            Args:
                agent_config: Agent configuration with mcp_sources

            Returns:
                List of GrpcMcpTool instances ready for LangGraph
            """
            tools = []
            for source in agent_config.mcp_sources:
                for tool_name in source.tools:
                    tool = self._integration.get_tool(source.server, tool_name)
                    tools.append(tool)
            return tools
    ```

- [x] **Task 4: Add Startup Integration** (AC: #7, #8)
  - [x] Modify `main.py` lifespan to initialize MCP integration:
    - After cache warming, before subscription startup
    - Extract all unique MCP servers from cached agent configs
    - Register servers with McpToolRegistry
    - Discover tools from all servers
    - Store integration in `app.state.mcp_integration`
  - [x] Add configurable cache TTL to settings (`mcp_tool_cache_ttl_seconds`)

- [x] **Task 5: Implement Error Handling** (AC: #9)
  - [x] Handle server unavailability during discovery:
    - Log warning but don't fail startup
    - Mark server as "discovery_pending"
    - Retry discovery on first tool access
  - [x] Handle tool invocation errors:
    - Use existing `McpToolError` from `fp_common.mcp.errors`
    - Log with context (agent_id, tool_name, server)

- [x] **Task 6: Unit Tests - Integration** (AC: #10)
  - [x] Create `tests/unit/ai_model/mcp/__init__.py`
  - [x] Create `tests/unit/ai_model/mcp/test_integration.py`:
    - Test register_from_agent_configs with multiple agents (3 tests)
    - Test deduplication of servers (1 test)
    - Test discover_all_tools success (2 tests)
    - Test cache TTL behavior (2 tests)
    - Test get_tool success (2 tests)
    - Test get_tool with unregistered server (1 test)
    - Test server unavailable graceful handling (2 tests)

- [x] **Task 7: Unit Tests - Provider** (AC: #10)
  - [x] Create `tests/unit/ai_model/mcp/test_provider.py`:
    - Test get_tools_for_agent returns correct tools (3 tests)
    - Test empty mcp_sources returns empty list (1 test)
    - Test multiple sources with multiple tools (2 tests)
    - Test tool filtering by configured list (2 tests)
    - Test error propagation from integration (2 tests)

- [x] **Task 8: Integration Tests** (AC: #10)
  - [x] Create `tests/unit/ai_model/mcp/test_startup.py`:
    - Test MCP integration in lifespan startup (2 tests)
    - Test tools available in app.state (1 test)

- [ ] **Task 9: CI Verification** (AC: #11)
  - [x] Run lint checks: `ruff check . && ruff format --check .`
  - [x] Run unit tests with correct PYTHONPATH
  - [ ] Push to feature branch and verify CI passes

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.75.8b: MCP Client Integration for Agent Workflows"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/0-75-8b-mcp-client-integration
  ```

**Branch name:** `feature/0-75-8b-mcp-client-integration`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin feature/0-75-8b-mcp-client-integration`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.75.8b: MCP Client Integration for Agent Workflows" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d feature/0-75-8b-mcp-client-integration`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
PYTHONPATH="${PYTHONPATH}:.:services/ai-model/src:libs/fp-common:libs/fp-proto/src" pytest tests/unit/ai_model/mcp/ -v
```
**Output:**
```
======================== 25 passed, 8 warnings in 1.25s ========================
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
git push origin feature/0-75-8b-mcp-client-integration

# Wait ~30s, then check CI status
gh run list --branch feature/0-75-8b-mcp-client-integration --limit 3
```
**CI Run ID:** _______________
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### CRITICAL: Reuse Existing Infrastructure - DO NOT Reinvent

**The MCP client infrastructure already exists in `libs/fp-common/fp_common/mcp/`:**

| Component | Location | Purpose |
|-----------|----------|---------|
| `GrpcMcpClient` | `fp_common/mcp/client.py:23` | Raw gRPC calls to MCP servers via DAPR |
| `McpToolRegistry` | `fp_common/mcp/registry.py:18` | Tool discovery and registration |
| `GrpcMcpTool` | `fp_common/mcp/tool.py:18` | LangChain BaseTool wrapper for MCP |
| `McpToolError` | `fp_common/mcp/errors.py` | Exception class for tool failures |

**This story creates an INTEGRATION layer, NOT new MCP infrastructure.**

### File Structure After Story

```
services/ai-model/
├── src/ai_model/
│   ├── mcp/                       # NEW - MCP integration package
│   │   ├── __init__.py            # Package exports
│   │   ├── integration.py         # McpIntegration class
│   │   └── provider.py            # AgentToolProvider class
│   └── main.py                    # MODIFIED - Add MCP startup
└── ...

tests/unit/ai_model/mcp/
├── __init__.py
├── test_integration.py            # McpIntegration tests (13 tests)
├── test_provider.py               # AgentToolProvider tests (10 tests)
└── test_startup.py                # Lifespan integration tests (3 tests)
```

### Agent Config mcp_sources Field

From `services/ai-model/src/ai_model/domain/agent_config.py:142`:

```python
class MCPSourceConfig(BaseModel):
    """MCP server data source configuration."""
    server: str = Field(description="MCP server name (e.g., 'collection', 'plantation')")
    tools: list[str] = Field(description="List of tools to use from this server")
```

Agent configs already have `mcp_sources` field. This story makes them functional.

### MCP Server App IDs

MCP servers are accessed via DAPR service invocation. The DAPR app-id format:

| Server Name | DAPR App ID | Available Tools |
|-------------|-------------|-----------------|
| `collection` | `collection-mcp` | `get_document`, `search_documents`, `get_farmer_context` |
| `plantation` | `plantation-mcp` | `get_farmer`, `get_factory`, `get_region`, `get_weather` |

**Server name to app-id mapping:**
```python
SERVER_APP_ID_MAP = {
    "collection": "collection-mcp",
    "plantation": "plantation-mcp",
    # Add more as MCP servers are created
}
```

### How GrpcMcpClient Works

From `libs/fp-common/fp_common/mcp/client.py`:

```python
# 1. Create client with DAPR app-id
client = GrpcMcpClient(app_id="plantation-mcp")

# 2. Call tool with arguments
result = await client.call_tool(
    tool_name="get_farmer",
    arguments={"farmer_id": "WM-1234"},
    caller_agent_id="disease-diagnosis",  # For audit
)

# 3. Or discover available tools
tools = await client.list_tools(category="farmer")
```

### How McpToolRegistry Works

From `libs/fp-common/fp_common/mcp/registry.py`:

```python
# 1. Create registry
registry = McpToolRegistry()

# 2. Register servers
registry.register_server("plantation-mcp")
registry.register_server("collection-mcp")

# 3. Discover tools (caches results)
tools = await registry.discover_tools("plantation-mcp")

# 4. Get LangChain-compatible tool
tool = registry.get_tool("plantation-mcp", "get_farmer")
# Returns GrpcMcpTool(name="get_farmer", mcp_client=...)
```

### How GrpcMcpTool Works with LangGraph

From `libs/fp-common/fp_common/mcp/tool.py`:

```python
# GrpcMcpTool extends LangChain BaseTool
tool = GrpcMcpTool(
    name="get_farmer",
    description="Get farmer details by ID",
    mcp_client=client,
)

# Use in LangGraph workflow
result = await tool._arun(farmer_id="WM-1234")
# Returns JSON string for LLM consumption
```

### Startup Sequence (main.py Integration)

Add after cache warming, before subscription startup:

```python
# In lifespan(), after cache warming:

# Story 0.75.8b: Initialize MCP integration
from ai_model.mcp import McpIntegration, AgentToolProvider

mcp_integration = McpIntegration()

# Extract servers from all cached agent configs
agent_configs = await agent_config_cache.get_all()
registered_servers = mcp_integration.register_from_agent_configs(agent_configs)
logger.info("Registered MCP servers", servers=list(registered_servers))

# Discover tools from all servers (with graceful failure handling)
try:
    await mcp_integration.discover_all_tools()
    logger.info("MCP tools discovered")
except Exception as e:
    logger.warning("Some MCP servers unavailable at startup", error=str(e))

# Create tool provider for agents
tool_provider = AgentToolProvider(mcp_integration)

# Store in app.state
app.state.mcp_integration = mcp_integration
app.state.tool_provider = tool_provider
```

### Testing Strategy

**Unit Tests Required (minimum 25 tests):**

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_integration.py` | 13 | Registration, discovery, caching, errors |
| `test_provider.py` | 10 | Tool resolution, filtering, error handling |
| `test_startup.py` | 3 | Lifespan integration |

**Mock Strategy:**
- Mock `McpToolRegistry` in integration tests
- Mock `GrpcMcpClient.list_tools()` for discovery tests
- Mock `GrpcMcpClient.call_tool()` for tool invocation tests
- Use existing `mock_dapr_client` fixture pattern from conftest.py

### Previous Story (0.75.8) Learnings

From completed Story 0.75.8:

1. **Thread safety with event loops** - Main event loop must be set for async operations in handlers
2. **DAPR app-id pattern** - Use `dapr-app-id` metadata header for gRPC calls
3. **CloudEvent unwrapping** - Messages may be wrapped, handle both formats
4. **Error handling patterns** - Use existing exception classes, don't reinvent
5. **62 unit tests achieved** - Target 25 minimum for this story

### Dependencies

**Already installed (from previous stories):**
- `langchain-core` (for BaseTool base class)
- `fp-common` with `fp_common.mcp` module
- `fp-proto` for gRPC stubs
- `pydantic` ^2.0

**No new dependencies required.**

### Anti-Patterns to AVOID

| Anti-Pattern | Correct Approach |
|--------------|------------------|
| Creating new MCP client | Use existing `GrpcMcpClient` from `fp_common.mcp` |
| Creating new tool registry | Use existing `McpToolRegistry` from `fp_common.mcp` |
| Direct gRPC calls | Use `GrpcMcpClient.call_tool()` which handles DAPR |
| Blocking operations | All tool calls are async via `asyncio.to_thread()` |
| Hardcoded app-ids | Use SERVER_APP_ID_MAP for name → app-id resolution |
| Failing startup on MCP unavailable | Log warning, mark as pending, retry on first access |

### What This Story Does NOT Include

| Not in Scope | Implemented In |
|--------------|----------------|
| Actual agent execution using tools | Stories 0.75.17-22 |
| RAG retrieval via MCP | Stories 0.75.9-15 |
| LangGraph workflow integration | Story 0.75.16 |
| MCP server implementation | Epics 1-2 (already done) |

**This story provides the integration layer. Agent workflows will use it in later stories.**

### Architecture Reference

**From `_bmad-output/architecture/ai-model-architecture/agent-types.md`:**
- Agents use MCP to fetch data from domain models
- `mcp_sources` in agent config specifies which servers/tools to use

**From `_bmad-output/project-context.md`:**
- MCP servers are STATELESS
- Tools return data, NOT make decisions
- Use Pydantic models for tool input/output schemas

### References

- [Source: `libs/fp-common/fp_common/mcp/__init__.py`] - MCP infrastructure exports
- [Source: `libs/fp-common/fp_common/mcp/client.py:23`] - GrpcMcpClient implementation
- [Source: `libs/fp-common/fp_common/mcp/registry.py:18`] - McpToolRegistry implementation
- [Source: `libs/fp-common/fp_common/mcp/tool.py:18`] - GrpcMcpTool LangChain wrapper
- [Source: `services/ai-model/src/ai_model/domain/agent_config.py:142`] - MCPSourceConfig model
- [Source: `services/ai-model/src/ai_model/main.py`] - Lifespan startup pattern
- [Source: `_bmad-output/epics/epic-0-75-ai-model.md#story-075-8b`] - Story requirements
- [Source: `_bmad-output/project-context.md`] - Critical rules

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- Tasks 1-8 completed
- 25 unit tests passing (13 integration, 10 provider, 3 startup)
- All lint and format checks pass
- Task 9 CI verification pending (push and CI run)

### File List

**Created:**
- `services/ai-model/src/ai_model/mcp/__init__.py` - Package exports (McpIntegration, AgentToolProvider, ServerStatus)
- `services/ai-model/src/ai_model/mcp/integration.py` - McpIntegration class (server registration, discovery, caching)
- `services/ai-model/src/ai_model/mcp/provider.py` - AgentToolProvider class (agent config to tools resolution)
- `tests/unit/ai_model/mcp/__init__.py` - Test package
- `tests/unit/ai_model/mcp/test_integration.py` - 13 tests for McpIntegration
- `tests/unit/ai_model/mcp/test_provider.py` - 10 tests for AgentToolProvider
- `tests/unit/ai_model/mcp/test_startup.py` - 3 tests for startup integration

**Modified:**
- `services/ai-model/src/ai_model/main.py` - Added MCP integration to lifespan startup
- `services/ai-model/src/ai_model/config.py` - Added `mcp_tool_cache_ttl_seconds` setting
