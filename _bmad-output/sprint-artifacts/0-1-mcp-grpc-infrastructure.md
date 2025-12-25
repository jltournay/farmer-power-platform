# Story 0.1: MCP gRPC Infrastructure

**Status:** done

---

## Story

As a **developer implementing MCP servers**,
I want shared proto definitions, generated stubs, and client utilities for gRPC-based MCP,
So that all MCP servers follow a consistent pattern and AI agents can invoke tools via DAPR.

**Context:**
Per architecture decision (see `infrastructure-decisions.md#mcp-protocol-decision-grpc-over-json-rpc`), MCP servers use gRPC protocol instead of standard JSON-RPC to maintain unified internal communication through DAPR sidecars.

---

## Acceptance Criteria

1. **Given** the proto definition needs to be created
   **When** I check `proto/mcp/v1/mcp_tool.proto`
   **Then** it defines:
   - `McpToolService` with `ListTools` and `CallTool` RPCs
   - `ListToolsRequest`, `ListToolsResponse`, `ToolDefinition` messages
   - `ToolCallRequest`, `ToolCallResponse` messages
   - Proper package naming: `farmer_power.mcp.v1`

2. **Given** the proto is defined
   **When** I run `make proto` or `./scripts/proto-gen.sh`
   **Then** Python stubs are generated in `libs/fp-proto/fp_proto/mcp/v1/`
   **And** includes: `mcp_tool_pb2.py`, `mcp_tool_pb2_grpc.py`, `mcp_tool_pb2.pyi`

3. **Given** AI agents need to call MCP servers
   **When** I import from `fp_common.mcp`
   **Then** `GrpcMcpClient` is available for raw gRPC calls via DAPR
   **And** `GrpcMcpTool` is available as a LangChain `BaseTool` wrapper
   **And** `McpToolRegistry` is available for tool discovery

4. **Given** the `GrpcMcpClient` is initialized with a DAPR app_id
   **When** I call `client.call_tool("get_farmer", {"farmer_id": "WM-4521"})`
   **Then** the request is routed through DAPR service invocation
   **And** the response is deserialized from `ToolCallResponse`
   **And** OpenTelemetry trace context is propagated

5. **Given** the `GrpcMcpTool` is used in a LangChain agent
   **When** the LLM invokes the tool
   **Then** arguments are JSON-serialized and passed to `ToolCallRequest`
   **And** the result is returned as a string for LLM consumption
   **And** errors are raised as `ToolExecutionError` with context

6. **Given** unit tests need to mock MCP servers
   **When** I import from `fp_testing.mocks`
   **Then** `MockMcpServer` is available to stub tool responses
   **And** `mock_mcp_tool` fixture is available for pytest

7. **Given** a tool call fails due to network error or timeout
   **When** the error is caught by `GrpcMcpClient`
   **Then** a `McpToolError` is raised with: error_code, message, trace_id
   **And** the error is logged with full context (app_id, tool_name, arguments)
   **And** OpenTelemetry span is marked as error with exception details

8. **Given** a tool call fails due to invalid arguments
   **When** the MCP server validates the request
   **Then** a `ToolCallResponse` is returned with `success=false`
   **And** `error_code` is set to `INVALID_ARGUMENTS`
   **And** `error_message` describes the validation failure

9. **Given** a tool call fails due to downstream service unavailable
   **When** the MCP server cannot reach MongoDB or other dependencies
   **Then** a `ToolCallResponse` is returned with `success=false`
   **And** `error_code` is set to `SERVICE_UNAVAILABLE`
   **And** DAPR retry policies are respected before returning error

10. **Given** the infrastructure is complete
    **When** I run the test suite
    **Then** all unit tests pass
    **And** type checking (mypy) passes with no errors

---

## Tasks / Subtasks

- [x] **Task 1: Create MCP proto definition** (AC: #1)
  - [x] 1.1 Create `proto/mcp/v1/mcp_tool.proto`
  - [x] 1.2 Define `McpToolService` with `ListTools` and `CallTool` RPCs
  - [x] 1.3 Define message types: `ToolDefinition`, `ToolCallRequest`, `ToolCallResponse`
  - [x] 1.4 Define error codes enum: `INVALID_ARGUMENTS`, `SERVICE_UNAVAILABLE`, `TOOL_NOT_FOUND`, `INTERNAL_ERROR`
  - [x] 1.5 Update `buf.yaml` to include mcp package (N/A - uses grpc_tools.protoc)

- [x] **Task 2: Generate Python stubs** (AC: #2)
  - [x] 2.1 Update `scripts/proto-gen.sh` to include mcp proto (auto-discovery)
  - [x] 2.2 Generate stubs to `libs/fp-proto/fp_proto/mcp/v1/`
  - [x] 2.3 Create `__init__.py` with proper exports
  - [x] 2.4 Verify mypy type stubs are generated (`.pyi` files)

- [x] **Task 3: Implement GrpcMcpClient** (AC: #4, #7, #9)
  - [x] 3.1 Create `libs/fp-common/fp_common/mcp/__init__.py`
  - [x] 3.2 Create `libs/fp-common/fp_common/mcp/client.py`
  - [x] 3.3 Implement `call_tool(tool_name, arguments)` with DAPR service invocation
  - [x] 3.4 Implement `list_tools()` for tool discovery
  - [x] 3.5 Implement OpenTelemetry trace context propagation
  - [x] 3.6 Implement retry logic with DAPR policies (via asyncio.to_thread)

- [x] **Task 4: Implement error handling** (AC: #7, #8, #9)
  - [x] 4.1 Create `libs/fp-common/fp_common/mcp/errors.py`
  - [x] 4.2 Define `McpToolError` exception class
  - [x] 4.3 Define error code constants matching proto enum
  - [x] 4.4 Implement error logging with full context
  - [x] 4.5 Implement OpenTelemetry error span marking

- [x] **Task 5: Implement GrpcMcpTool LangChain wrapper** (AC: #5)
  - [x] 5.1 Create `libs/fp-common/fp_common/mcp/tool.py`
  - [x] 5.2 Implement `GrpcMcpTool` extending `langchain_core.tools.BaseTool`
  - [x] 5.3 Implement `_arun()` for async tool execution
  - [x] 5.4 Implement argument JSON serialization
  - [x] 5.5 Implement result deserialization for LLM consumption

- [x] **Task 6: Implement McpToolRegistry** (AC: #3)
  - [x] 6.1 Create `libs/fp-common/fp_common/mcp/registry.py`
  - [x] 6.2 Implement tool registration by MCP server app_id
  - [x] 6.3 Implement tool discovery via `ListTools` RPC
  - [x] 6.4 Implement caching of tool definitions

- [x] **Task 7: Implement test mocks** (AC: #6)
  - [x] 7.1 Create `libs/fp-testing/fp_testing/mocks/mcp_mock.py`
  - [x] 7.2 Implement `MockMcpServer` class
  - [x] 7.3 Implement `mock_mcp_tool` pytest fixture
  - [x] 7.4 Implement response stubbing for specific tools

- [x] **Task 8: Write unit tests** (AC: #10)
  - [x] 8.1 Create `tests/unit/mcp/test_client.py`
  - [x] 8.2 Create `tests/unit/mcp/test_tool.py`
  - [x] 8.3 Create `tests/unit/mcp/test_registry.py`
  - [x] 8.4 Create `tests/unit/mcp/test_errors.py`
  - [x] 8.5 Achieve >90% code coverage (29 tests passing)

- [x] **Task 9: Run validation** (AC: #10)
  - [x] 9.1 Run `pytest tests/unit/mcp/` (29 passed)
  - [x] 9.2 Run `mypy libs/fp-common/fp_common/mcp/` (no errors)
  - [x] 9.3 Run `ruff check libs/fp-common/fp_common/mcp/` (all passed)

---

## Dev Notes

### File Locations

```
proto/mcp/v1/
└── mcp_tool.proto              # gRPC service definition

libs/fp-proto/fp_proto/mcp/v1/
├── __init__.py
├── mcp_tool_pb2.py             # Generated message types
├── mcp_tool_pb2_grpc.py        # Generated service stubs
└── mcp_tool_pb2.pyi            # Type hints

libs/fp-common/fp_common/mcp/
├── __init__.py                 # Public exports
├── client.py                   # GrpcMcpClient
├── tool.py                     # GrpcMcpTool (LangChain wrapper)
├── registry.py                 # McpToolRegistry
└── errors.py                   # McpToolError, error codes

libs/fp-testing/fp_testing/mocks/
└── mcp_mock.py                 # MockMcpServer, fixtures

tests/unit/mcp/
├── __init__.py
├── test_client.py
├── test_tool.py
├── test_registry.py
└── test_errors.py
```

### Proto Definition

```protobuf
// proto/mcp/v1/mcp_tool.proto
syntax = "proto3";

package farmer_power.mcp.v1;

// Error codes for tool execution failures
enum ErrorCode {
  ERROR_CODE_UNSPECIFIED = 0;
  ERROR_CODE_INVALID_ARGUMENTS = 1;
  ERROR_CODE_SERVICE_UNAVAILABLE = 2;
  ERROR_CODE_TOOL_NOT_FOUND = 3;
  ERROR_CODE_INTERNAL_ERROR = 4;
}

// McpToolService provides tool invocation for AI agents
service McpToolService {
  // List available tools with their schemas
  rpc ListTools(ListToolsRequest) returns (ListToolsResponse);

  // Invoke a specific tool
  rpc CallTool(ToolCallRequest) returns (ToolCallResponse);
}

message ListToolsRequest {
  // Optional filter by tool category
  string category = 1;
}

message ListToolsResponse {
  repeated ToolDefinition tools = 1;
}

message ToolDefinition {
  string name = 1;                    // e.g., "get_farmer_by_id"
  string description = 2;             // Human-readable description
  string input_schema_json = 3;       // JSON Schema for tool arguments
  string category = 4;                // e.g., "query", "search"
}

message ToolCallRequest {
  string tool_name = 1;               // Tool to invoke
  string arguments_json = 2;          // JSON-encoded arguments
  string trace_id = 3;                // OpenTelemetry trace ID
  string caller_agent_id = 4;         // For audit logging
}

message ToolCallResponse {
  bool success = 1;
  string result_json = 2;             // JSON-encoded result
  ErrorCode error_code = 3;           // Error code if success=false
  string error_message = 4;           // Error details if success=false
}
```

### GrpcMcpClient Implementation

```python
# libs/fp-common/fp_common/mcp/client.py
from __future__ import annotations

import json
from typing import Any

from dapr.clients import DaprClient
from opentelemetry import trace

from fp_proto.mcp.v1 import mcp_tool_pb2
from fp_common.mcp.errors import McpToolError, ErrorCode

tracer = trace.get_tracer(__name__)


class GrpcMcpClient:
    """Client for invoking MCP tools via DAPR service invocation."""

    def __init__(self, app_id: str) -> None:
        """Initialize client for a specific MCP server.

        Args:
            app_id: DAPR app ID of the MCP server (e.g., "plantation-mcp")
        """
        self.app_id = app_id

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        caller_agent_id: str | None = None,
    ) -> dict[str, Any]:
        """Invoke an MCP tool and return the result.

        Args:
            tool_name: Name of the tool to invoke
            arguments: Tool arguments as a dictionary
            caller_agent_id: Optional agent ID for audit logging

        Returns:
            Tool result as a dictionary

        Raises:
            McpToolError: If tool execution fails
        """
        with tracer.start_as_current_span(f"mcp.call_tool.{tool_name}") as span:
            span.set_attribute("mcp.app_id", self.app_id)
            span.set_attribute("mcp.tool_name", tool_name)

            request = mcp_tool_pb2.ToolCallRequest(
                tool_name=tool_name,
                arguments_json=json.dumps(arguments),
                trace_id=format(span.get_span_context().trace_id, "032x"),
                caller_agent_id=caller_agent_id or "",
            )

            try:
                async with DaprClient() as client:
                    response = await client.invoke_method(
                        app_id=self.app_id,
                        method_name="McpToolService/CallTool",
                        data=request.SerializeToString(),
                        content_type="application/grpc",
                    )

                result = mcp_tool_pb2.ToolCallResponse()
                result.ParseFromString(response.data)

                if not result.success:
                    raise McpToolError(
                        error_code=ErrorCode(result.error_code),
                        message=result.error_message,
                        trace_id=request.trace_id,
                        app_id=self.app_id,
                        tool_name=tool_name,
                    )

                return json.loads(result.result_json)

            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise

    async def list_tools(self, category: str | None = None) -> list[dict[str, Any]]:
        """List available tools from the MCP server.

        Args:
            category: Optional category filter

        Returns:
            List of tool definitions
        """
        request = mcp_tool_pb2.ListToolsRequest(category=category or "")

        async with DaprClient() as client:
            response = await client.invoke_method(
                app_id=self.app_id,
                method_name="McpToolService/ListTools",
                data=request.SerializeToString(),
                content_type="application/grpc",
            )

        result = mcp_tool_pb2.ListToolsResponse()
        result.ParseFromString(response.data)

        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": json.loads(tool.input_schema_json),
                "category": tool.category,
            }
            for tool in result.tools
        ]
```

### GrpcMcpTool LangChain Wrapper

```python
# libs/fp-common/fp_common/mcp/tool.py
from __future__ import annotations

import json
from typing import Any, Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from fp_common.mcp.client import GrpcMcpClient
from fp_common.mcp.errors import McpToolError


class GrpcMcpTool(BaseTool):
    """LangChain tool wrapper for gRPC MCP tools."""

    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description for LLM")
    mcp_client: GrpcMcpClient = Field(exclude=True)
    args_schema: Type[BaseModel] | None = None

    class Config:
        arbitrary_types_allowed = True

    async def _arun(self, **kwargs: Any) -> str:
        """Execute the tool asynchronously.

        Returns:
            JSON string of the tool result for LLM consumption
        """
        try:
            result = await self.mcp_client.call_tool(
                tool_name=self.name,
                arguments=kwargs,
            )
            return json.dumps(result, indent=2)
        except McpToolError as e:
            return json.dumps({
                "error": True,
                "error_code": e.error_code.name,
                "message": e.message,
            })

    def _run(self, **kwargs: Any) -> str:
        """Sync execution not supported."""
        raise NotImplementedError("Use async execution with _arun()")
```

### Technology Stack

| Component | Choice | Version |
|-----------|--------|---------|
| Language | Python | 3.12 |
| Proto Compiler | buf | Latest |
| gRPC | grpcio | Latest |
| DAPR SDK | dapr | Latest |
| LangChain | langchain-core | Latest |
| Tracing | opentelemetry-api | Latest |
| Validation | Pydantic | 2.0+ |

### Critical Implementation Rules

**From project-context.md:**

1. **ALL I/O operations MUST be async** - Use `async def` for all DAPR and network operations
2. **Use Pydantic 2.0 syntax** - `model_dump()` not `dict()`
3. **ALL inter-service communication via DAPR** - No direct gRPC between services
4. **Type hints required** - ALL function signatures MUST have type hints
5. **Absolute imports only** - No relative imports

### Dependencies to Add

**libs/fp-common/pyproject.toml:**
```toml
[tool.poetry.dependencies]
dapr = "^1.12.0"
grpcio = "^1.60.0"
langchain-core = "^0.1.0"
opentelemetry-api = "^1.22.0"
```

**libs/fp-testing/pyproject.toml:**
```toml
[tool.poetry.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.23.0"
```

### References

- [Source: _bmad-output/architecture/infrastructure-decisions.md#mcp-protocol-decision-grpc-over-json-rpc] - Full architecture decision
- [Source: _bmad-output/architecture/repository-structure.md] - File locations
- [Source: _bmad-output/project-context.md#technology-stack] - Version requirements
- [Source: _bmad-output/project-context.md#python-specific-rules] - Async/Pydantic rules

---

## Blocks

This story blocks the following stories:

| Story | Epic | Description |
|-------|------|-------------|
| 1.6 | Epic 1 | Plantation Model MCP Server |
| 2.8 | Epic 2 | Collection Model MCP Server |
| 5.9 | Epic 5 | Knowledge Model MCP Server |
| 6.6 | Epic 6 | Action Plan MCP Server |
| 6.1 | Epic 6 | Action Plan Model Service Setup (MCP client usage) |
| 8.1 | Epic 8 | Conversational AI Service Setup (MCP client usage) |

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

- Implemented gRPC proto definition for MCP Tool Service with ListTools and CallTool RPCs
- Generated Python stubs using grpc_tools.protoc (not buf)
- Implemented GrpcMcpClient with DAPR service invocation and OpenTelemetry tracing
- Implemented GrpcMcpTool LangChain wrapper with async execution
- Implemented McpToolRegistry with concurrent discovery via asyncio.gather()
- Implemented MockMcpServer and mock_mcp_tool fixture for testing
- All 29 unit tests passing, mypy clean, ruff clean
- Code review fixes applied: asyncio.gather for concurrent ops, logging, raise_on_error option

### File List

**Proto Definition:**
- `proto/mcp/v1/mcp_tool.proto`

**Generated Stubs:**
- `libs/fp-proto/src/fp_proto/mcp/__init__.py`
- `libs/fp-proto/src/fp_proto/mcp/v1/__init__.py`
- `libs/fp-proto/src/fp_proto/mcp/v1/mcp_tool_pb2.py`
- `libs/fp-proto/src/fp_proto/mcp/v1/mcp_tool_pb2.pyi`
- `libs/fp-proto/src/fp_proto/mcp/v1/mcp_tool_pb2_grpc.py`

**MCP Client Library:**
- `libs/fp-common/fp_common/mcp/__init__.py`
- `libs/fp-common/fp_common/mcp/client.py`
- `libs/fp-common/fp_common/mcp/errors.py`
- `libs/fp-common/fp_common/mcp/tool.py`
- `libs/fp-common/fp_common/mcp/registry.py`
- `libs/fp-common/pyproject.toml`

**Test Mocks:**
- `libs/fp-testing/fp_testing/mocks/__init__.py`
- `libs/fp-testing/fp_testing/mocks/mcp_mock.py`
- `libs/fp-testing/pyproject.toml`

**Unit Tests:**
- `tests/unit/mcp/__init__.py`
- `tests/unit/mcp/test_client.py`
- `tests/unit/mcp/test_errors.py`
- `tests/unit/mcp/test_registry.py`
- `tests/unit/mcp/test_tool.py`

### Review Follow-ups (AI Code Review)

**Code Review Date:** 2025-12-25

**Issues Fixed:**
- M3: Changed discover_all_tools to use asyncio.gather() for concurrent discovery
- M4: Added raise_on_error parameter to GrpcMcpTool for programmatic error handling
- M5: Added logging to McpToolRegistry for debugging
- L2: Moved lazy import in mcp_mock.py to module level
- L3: Added defensive None check for span_context in client.py

**Remaining (Low Priority):**
- L1: Consider migrating to structlog in future iteration
