### Epic 0: Platform Infrastructure Foundation

Cross-cutting infrastructure that enables domain model services. These stories establish shared libraries, proto definitions, and foundational patterns used across all epics.

**Scope:**
- Shared proto definitions for cross-cutting concerns
- Common library utilities (fp-common, fp-proto, fp-testing)
- Infrastructure patterns that block multiple domain stories

---

#### Story 0.1: MCP gRPC Infrastructure

**[📄 Story File](../sprint-artifacts/0-1-mcp-grpc-infrastructure.md)** | Status: Done

As a **developer implementing MCP servers**,
I want shared proto definitions, generated stubs, and client utilities for gRPC-based MCP,
So that all MCP servers follow a consistent pattern and AI agents can invoke tools via DAPR.

**Context:**
Per architecture decision (see `infrastructure-decisions.md#mcp-protocol-decision-grpc-over-json-rpc`), MCP servers use gRPC protocol instead of standard JSON-RPC to maintain unified internal communication through DAPR sidecars.

**Acceptance Criteria:**

**Given** the proto definition needs to be created
**When** I check `proto/mcp/v1/mcp_tool.proto`
**Then** it defines:
  - `McpToolService` with `ListTools` and `CallTool` RPCs
  - `ListToolsRequest`, `ListToolsResponse`, `ToolDefinition` messages
  - `ToolCallRequest`, `ToolCallResponse` messages
  - Proper package naming: `farmer_power.mcp.v1`

**Given** the proto is defined
**When** I run `make proto` or `./scripts/proto-gen.sh`
**Then** Python stubs are generated in `libs/fp-proto/fp_proto/mcp/v1/`
**And** includes: `mcp_tool_pb2.py`, `mcp_tool_pb2_grpc.py`, `mcp_tool_pb2.pyi`

**Given** AI agents need to call MCP servers
**When** I import from `fp_common.mcp`
**Then** `GrpcMcpClient` is available for raw gRPC calls via DAPR
**And** `GrpcMcpTool` is available as a LangChain `BaseTool` wrapper
**And** `McpToolRegistry` is available for tool discovery

**Given** the `GrpcMcpClient` is initialized with a DAPR app_id
**When** I call `client.call_tool("get_farmer", {"farmer_id": "WM-4521"})`
**Then** the request is routed through DAPR service invocation
**And** the response is deserialized from `ToolCallResponse`
**And** OpenTelemetry trace context is propagated

**Given** the `GrpcMcpTool` is used in a LangChain agent
**When** the LLM invokes the tool
**Then** arguments are JSON-serialized and passed to `ToolCallRequest`
**And** the result is returned as a string for LLM consumption
**And** errors are raised as `ToolExecutionError` with context

**Given** unit tests need to mock MCP servers
**When** I import from `fp_testing.mocks`
**Then** `MockMcpServer` is available to stub tool responses
**And** `mock_mcp_tool` fixture is available for pytest

**Given** a tool call fails due to network error or timeout
**When** the error is caught by `GrpcMcpClient`
**Then** a `McpToolError` is raised with: error_code, message, trace_id
**And** the error is logged with full context (app_id, tool_name, arguments)
**And** OpenTelemetry span is marked as error with exception details

**Given** a tool call fails due to invalid arguments
**When** the MCP server validates the request
**Then** a `ToolCallResponse` is returned with `success=false`
**And** `error_code` is set to `INVALID_ARGUMENTS`
**And** `error_message` describes the validation failure

**Given** a tool call fails due to downstream service unavailable
**When** the MCP server cannot reach MongoDB or other dependencies
**Then** a `ToolCallResponse` is returned with `success=false`
**And** `error_code` is set to `SERVICE_UNAVAILABLE`
**And** DAPR retry policies are respected before returning error

**Given** the infrastructure is complete
**When** I run the test suite
**Then** all unit tests pass
**And** type checking (mypy) passes with no errors

**Technical Notes:**
- Proto location: `proto/mcp/v1/mcp_tool.proto`
- Generated stubs: `libs/fp-proto/fp_proto/mcp/v1/`
- Client utilities: `libs/fp-common/fp_common/mcp/`
  - `client.py` - GrpcMcpClient
  - `tool.py` - GrpcMcpTool (LangChain wrapper)
  - `registry.py` - McpToolRegistry
  - `errors.py` - McpToolError, error codes (INVALID_ARGUMENTS, SERVICE_UNAVAILABLE, etc.)
- Test utilities: `libs/fp-testing/fp_testing/mocks/mcp_mock.py`
- Error codes defined in proto: INVALID_ARGUMENTS, SERVICE_UNAVAILABLE, TOOL_NOT_FOUND, INTERNAL_ERROR
- Reference: `_bmad-output/architecture/infrastructure-decisions.md#mcp-protocol-decision-grpc-over-json-rpc`

**Dependencies:**
- None (foundational)

**Blocks:**
- Story 1.6: Plantation Model MCP Server
- Story 2.9: Collection Model MCP Server
- Story 5.9: Knowledge Model MCP Server
- Story 6.6: Action Plan MCP Server
- Story 6.1: Action Plan Model Service Setup (MCP client usage)
- Story 8.1: Conversational AI Service Setup (MCP client usage)

**Story Points:** 3

---

## Retrospective

**[📋 Epic 0 Retrospective](../sprint-artifacts/epic-0-retro-2025-12-25.md)** | Completed: 2025-12-25
