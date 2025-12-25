# Story 1.6: Plantation Model MCP Server

**Status:** review
**GitHub Issue:** #13

---

## Story

As an **AI agent**,
I want to access farmer and factory data via MCP tools,
So that I can generate personalized recommendations.

**Context:**
This story implements the first MCP server in the platform, using the gRPC MCP infrastructure created in Story 0-1. The Plantation MCP Server provides read-only access to farmer, factory, and collection point data for AI agents in the Knowledge Model and Action Plan Model services.

---

## Acceptance Criteria

1. **Given** the Plantation MCP Server is deployed
   **When** an AI agent calls `get_farmer(farmer_id)`
   **Then** the response includes: name, phone, farm_size_hectares, farm_scale, region, collection_point_id, pref_lang, notification_channel, interaction_pref

2. **Given** a farmer_id exists
   **When** an AI agent calls `get_farmer_summary(farmer_id)`
   **Then** the response includes: performance metrics, trend, yield_vs_regional_avg, last_delivery_date, historical quality data

3. **Given** a factory_id exists
   **When** an AI agent calls `get_collection_points(factory_id)`
   **Then** all collection points for that factory are returned with their details

4. **Given** a collection_point_id exists
   **When** an AI agent calls `get_farmers_by_collection_point(cp_id)`
   **Then** all farmers registered at that collection point are returned

5. **Given** the MCP Server receives a request
   **When** processing completes
   **Then** OpenTelemetry traces are emitted with tool name and duration
   **And** errors are logged with full context

6. **Given** an AI agent calls a tool with invalid arguments
   **When** validation fails
   **Then** a ToolCallResponse is returned with success=false and error_code=INVALID_ARGUMENTS

7. **Given** the Plantation Model service is unavailable
   **When** the MCP Server tries to fetch data
   **Then** a ToolCallResponse is returned with success=false and error_code=SERVICE_UNAVAILABLE

---

## Tasks / Subtasks

- [x] **Task 1: Create MCP Server project structure** (AC: #5)
  - [x] 1.1 Create `mcp-servers/plantation-mcp/` directory
  - [x] 1.2 Create `pyproject.toml` with dependencies (fp-common, fp-proto, grpcio)
  - [x] 1.3 Create `src/plantation_mcp/` package structure
  - [x] 1.4 Create `Dockerfile` following service pattern
  - [x] 1.5 Create `main.py` with gRPC server startup

- [x] **Task 2: Implement McpToolService servicer** (AC: #1, #2, #3, #4, #5)
  - [x] 2.1 Create `src/plantation_mcp/api/mcp_service.py`
  - [x] 2.2 Implement `ListTools()` returning all available tools
  - [x] 2.3 Implement `CallTool()` with tool dispatch logic
  - [x] 2.4 Add OpenTelemetry tracing to all tool calls

- [x] **Task 3: Implement tool handlers** (AC: #1, #2, #3, #4, #6, #7)
  - [x] 3.1 Create `src/plantation_mcp/tools/` package
  - [x] 3.2 Implement `get_farmer` tool handler
  - [x] 3.3 Implement `get_farmer_summary` tool handler
  - [x] 3.4 Implement `get_collection_points` tool handler
  - [x] 3.5 Implement `get_farmers_by_collection_point` tool handler
  - [x] 3.6 Add input validation with JSON Schema
  - [x] 3.7 Add error handling for service unavailable

- [x] **Task 4: Create PlantationService client** (AC: #1, #2, #3, #4, #7)
  - [x] 4.1 Create `src/plantation_mcp/infrastructure/plantation_client.py`
  - [x] 4.2 Implement gRPC client via DAPR service invocation
  - [x] 4.3 Add retry logic with exponential backoff
  - [x] 4.4 Add circuit breaker for service unavailable

- [x] **Task 5: Create tool definitions** (AC: #1, #2, #3, #4)
  - [x] 5.1 Create `src/plantation_mcp/tools/definitions.py`
  - [x] 5.2 Define JSON Schema for each tool's input
  - [x] 5.3 Define tool descriptions for LLM consumption
  - [x] 5.4 Register all tools in a central registry

- [x] **Task 6: Write unit tests** (AC: #1, #2, #3, #4, #5, #6, #7)
  - [x] 6.1 Create `tests/unit/plantation_mcp/` directory
  - [x] 6.2 Test ListTools returns all tools with schemas
  - [x] 6.3 Test get_farmer tool with valid farmer_id
  - [x] 6.4 Test get_farmer tool with non-existent farmer (NOT_FOUND)
  - [x] 6.5 Test get_farmer_summary tool
  - [x] 6.6 Test get_collection_points tool
  - [x] 6.7 Test get_farmers_by_collection_point tool
  - [x] 6.8 Test invalid arguments return INVALID_ARGUMENTS
  - [x] 6.9 Test service unavailable returns SERVICE_UNAVAILABLE

- [x] **Task 7: Create Kubernetes deployment** (AC: #5)
  - [x] 7.1 Create `deploy/kubernetes/base/mcp-servers/plantation-mcp/deployment.yaml`
  - [x] 7.2 Create `service.yaml` for gRPC service
  - [x] 7.3 Create `hpa.yaml` with min=2, max=10 replicas
  - [x] 7.4 Add DAPR annotations for sidecar injection
  - [x] 7.5 Add health check and readiness probe

- [x] **Task 8: Run validation**
  - [x] 8.1 Run pytest with coverage >90%
  - [x] 8.2 Run mypy with no errors
  - [x] 8.3 Run ruff check with no errors

---

## Dev Notes

### Phase 1 Scope

This story implements **4 core tools** for the Plantation MCP Server. The architecture defines 17 total tools, but we're delivering in phases based on epic dependencies:

**Phase 1 (This Story):** Farmer-centric queries for Action Plan Generator
- `get_farmer` - Farmer profile with preferences
- `get_farmer_summary` - Performance metrics and trends
- `get_collection_points` - Collection points by factory
- `get_farmers_by_collection_point` - Farmers at a collection point

**Deferred to Future Stories:**
| Tool | Needed By | Epic |
|------|-----------|------|
| `get_factory`, `get_factory_config` | Admin UI, Market Analysis | Epic 2, 4 |
| `get_region`, `list_regions`, `get_region_weather`, `get_current_flush` | Weather Analyzer | Epic 3 |
| `get_regional_yield_benchmark` | Action Plan Generator (advanced) | Epic 3 |
| `get_buyer_profiles` | Market Analysis Model | Epic 4 |
| `get_grading_model`, `list_grading_models`, `get_factory_grading_model` | Collection Model, Admin UI | Epic 2 |
| `get_farmer_context` | Action Plan Generator (convenience wrapper) | Epic 3 |
| `get_collection_point`, `list_collection_points`, `get_cp_performance` | Admin UI, Reports | Epic 5 |

This phased approach allows us to deliver value early while deferring complexity until needed.

---

### Architecture Overview

```
┌─────────────────────┐     ┌──────────────────────┐
│   AI Agent          │     │  Plantation MCP      │
│   (Knowledge/       │────▶│  Server              │
│    Action Plan)     │     │                      │
└─────────────────────┘     └──────────┬───────────┘
        │                              │
        │ DAPR Service                 │ DAPR Service
        │ Invocation                   │ Invocation
        ▼                              ▼
┌─────────────────────┐     ┌──────────────────────┐
│   GrpcMcpClient     │     │  Plantation Model    │
│   (from fp-common)  │     │  Service (gRPC)      │
└─────────────────────┘     └──────────────────────┘
```

### File Locations

```
mcp-servers/plantation-mcp/
├── src/plantation_mcp/
│   ├── __init__.py
│   ├── main.py                    # gRPC server entrypoint
│   ├── config.py                  # Service configuration
│   ├── api/
│   │   ├── __init__.py
│   │   └── mcp_service.py         # McpToolService implementation
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── definitions.py         # Tool schemas and registry
│   │   ├── get_farmer.py
│   │   ├── get_farmer_summary.py
│   │   ├── get_collection_points.py
│   │   └── get_farmers_by_collection_point.py
│   └── infrastructure/
│       ├── __init__.py
│       └── plantation_client.py   # PlantationService gRPC client
├── tests/
│   └── unit/
│       ├── __init__.py
│       ├── test_mcp_service.py
│       └── test_tools.py
├── Dockerfile
└── pyproject.toml

deploy/kubernetes/base/mcp-servers/plantation-mcp/
├── deployment.yaml
├── service.yaml
├── hpa.yaml
└── kustomization.yaml
```

### MCP Tool Service Implementation Pattern

The MCP Server implements the `McpToolService` from `proto/mcp/v1/mcp_tool.proto`:

```python
# src/plantation_mcp/api/mcp_service.py
from fp_proto.mcp.v1 import mcp_tool_pb2, mcp_tool_pb2_grpc
from plantation_mcp.tools.definitions import TOOL_REGISTRY

class McpToolServiceServicer(mcp_tool_pb2_grpc.McpToolServiceServicer):
    """MCP Tool Service implementation for Plantation data."""

    def __init__(self, plantation_client: PlantationClient) -> None:
        self._plantation_client = plantation_client
        self._tool_handlers = {
            "get_farmer": self._handle_get_farmer,
            "get_farmer_summary": self._handle_get_farmer_summary,
            "get_collection_points": self._handle_get_collection_points,
            "get_farmers_by_collection_point": self._handle_get_farmers_by_collection_point,
        }

    async def ListTools(
        self,
        request: mcp_tool_pb2.ListToolsRequest,
        context: grpc.aio.ServicerContext,
    ) -> mcp_tool_pb2.ListToolsResponse:
        """Return all available tools with their schemas."""
        return mcp_tool_pb2.ListToolsResponse(
            tools=[
                mcp_tool_pb2.ToolDefinition(
                    name=tool.name,
                    description=tool.description,
                    input_schema_json=json.dumps(tool.input_schema),
                    category=tool.category,
                )
                for tool in TOOL_REGISTRY.values()
            ]
        )

    async def CallTool(
        self,
        request: mcp_tool_pb2.ToolCallRequest,
        context: grpc.aio.ServicerContext,
    ) -> mcp_tool_pb2.ToolCallResponse:
        """Dispatch tool call to appropriate handler."""
        with tracer.start_as_current_span(f"mcp.call_tool.{request.tool_name}") as span:
            handler = self._tool_handlers.get(request.tool_name)
            if not handler:
                return mcp_tool_pb2.ToolCallResponse(
                    success=False,
                    error_code=mcp_tool_pb2.ERROR_CODE_TOOL_NOT_FOUND,
                    error_message=f"Unknown tool: {request.tool_name}",
                )

            try:
                arguments = json.loads(request.arguments_json)
                result = await handler(arguments)
                return mcp_tool_pb2.ToolCallResponse(
                    success=True,
                    result_json=json.dumps(result),
                )
            except ValidationError as e:
                return mcp_tool_pb2.ToolCallResponse(
                    success=False,
                    error_code=mcp_tool_pb2.ERROR_CODE_INVALID_ARGUMENTS,
                    error_message=str(e),
                )
            except ServiceUnavailableError as e:
                return mcp_tool_pb2.ToolCallResponse(
                    success=False,
                    error_code=mcp_tool_pb2.ERROR_CODE_SERVICE_UNAVAILABLE,
                    error_message=str(e),
                )
```

### Tool Definition Pattern

```python
# src/plantation_mcp/tools/definitions.py
from dataclasses import dataclass
from typing import Any

@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    category: str

TOOL_REGISTRY: dict[str, ToolDefinition] = {
    "get_farmer": ToolDefinition(
        name="get_farmer",
        description="Get farmer details by ID. Returns name, phone, farm size, preferences.",
        input_schema={
            "type": "object",
            "properties": {
                "farmer_id": {
                    "type": "string",
                    "description": "Farmer ID in format WM-XXXX",
                    "pattern": "^WM-\\d{4}$"
                }
            },
            "required": ["farmer_id"]
        },
        category="query"
    ),
    "get_farmer_summary": ToolDefinition(
        name="get_farmer_summary",
        description="Get farmer performance summary including quality history and trends.",
        input_schema={
            "type": "object",
            "properties": {
                "farmer_id": {
                    "type": "string",
                    "description": "Farmer ID in format WM-XXXX"
                }
            },
            "required": ["farmer_id"]
        },
        category="query"
    ),
    "get_collection_points": ToolDefinition(
        name="get_collection_points",
        description="Get all collection points for a factory.",
        input_schema={
            "type": "object",
            "properties": {
                "factory_id": {
                    "type": "string",
                    "description": "Factory ID"
                }
            },
            "required": ["factory_id"]
        },
        category="query"
    ),
    "get_farmers_by_collection_point": ToolDefinition(
        name="get_farmers_by_collection_point",
        description="Get all farmers registered at a collection point.",
        input_schema={
            "type": "object",
            "properties": {
                "collection_point_id": {
                    "type": "string",
                    "description": "Collection point ID"
                }
            },
            "required": ["collection_point_id"]
        },
        category="query"
    ),
}
```

### PlantationService Client Pattern

```python
# src/plantation_mcp/infrastructure/plantation_client.py
from dapr.clients import DaprClient
from fp_proto.plantation.v1 import plantation_pb2, plantation_pb2_grpc

class PlantationClient:
    """Client for Plantation Model service via DAPR."""

    PLANTATION_APP_ID = "plantation-model"

    async def get_farmer(self, farmer_id: str) -> dict[str, Any]:
        """Get farmer by ID."""
        request = plantation_pb2.GetFarmerRequest(id=farmer_id)

        async with DaprClient() as client:
            response = await client.invoke_method(
                app_id=self.PLANTATION_APP_ID,
                method_name="PlantationService/GetFarmer",
                data=request.SerializeToString(),
                content_type="application/grpc",
            )

        farmer = plantation_pb2.Farmer()
        farmer.ParseFromString(response.data)

        return {
            "farmer_id": farmer.id,
            "first_name": farmer.first_name,
            "last_name": farmer.last_name,
            "phone": farmer.contact.phone,
            "farm_size_hectares": farmer.farm_size_hectares,
            "farm_scale": plantation_pb2.FarmScale.Name(farmer.farm_scale),
            "region_id": farmer.region_id,
            "collection_point_id": farmer.collection_point_id,
            "notification_channel": plantation_pb2.NotificationChannel.Name(farmer.notification_channel),
            "interaction_pref": plantation_pb2.InteractionPreference.Name(farmer.interaction_pref),
            "pref_lang": plantation_pb2.PreferredLanguage.Name(farmer.pref_lang),
        }
```

### Critical Implementation Rules

**From Story 0-1 (MCP Infrastructure):**
- Use `McpToolService` proto from `proto/mcp/v1/mcp_tool.proto`
- Return `ToolCallResponse` with success/error fields
- Error codes: `INVALID_ARGUMENTS`, `SERVICE_UNAVAILABLE`, `TOOL_NOT_FOUND`, `INTERNAL_ERROR`

**From project-context.md:**
- ALL I/O operations MUST be async
- Use DAPR service invocation for calling PlantationService
- Use Pydantic 2.0 syntax (`model_dump()` not `dict()`)
- ALL function signatures MUST have type hints
- Use OpenTelemetry tracing (via DAPR sidecar)

### Dependencies

**pyproject.toml:**
```toml
[tool.poetry.dependencies]
python = "^3.12"
grpcio = "^1.60.0"
grpcio-health-checking = "^1.60.0"
dapr = "^1.12.0"
opentelemetry-api = "^1.22.0"
pydantic = "^2.0.0"
fp-common = { path = "../../libs/fp-common" }
fp-proto = { path = "../../libs/fp-proto" }

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.23.0"
fp-testing = { path = "../../libs/fp-testing" }
```

### Kubernetes HPA Configuration

```yaml
# deploy/kubernetes/base/mcp-servers/plantation-mcp/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: plantation-mcp
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: plantation-mcp
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### References

- [Source: Story 0-1] - MCP gRPC Infrastructure (proto, client, registry)
- [Source: _bmad-output/architecture/infrastructure-decisions.md#mcp-protocol-decision-grpc-over-json-rpc] - gRPC decision
- [Source: _bmad-output/project-context.md#repository-structure] - File locations
- [Source: _bmad-output/project-context.md#python-specific-rules] - Async/Pydantic rules

---

## Previous Story Intelligence

**From Story 0-1 (MCP Infrastructure):**
- Proto definition: `proto/mcp/v1/mcp_tool.proto` defines McpToolService
- Client library: `libs/fp-common/fp_common/mcp/` has GrpcMcpClient, GrpcMcpTool, McpToolRegistry
- Test mocks: `libs/fp-testing/fp_testing/mocks/mcp_mock.py` has MockMcpServer
- Error handling: Use `McpToolError` with error codes from proto enum

**From Story 1-5 (Farmer Communication Preferences):**
- Farmer model now includes: notification_channel, interaction_pref, pref_lang
- These fields should be included in get_farmer and get_farmer_summary responses

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Completion Notes List

- Implemented complete Plantation MCP Server with 4 tools (Phase 1 scope)
- Created McpToolService gRPC servicer with ListTools and CallTool RPCs
- Implemented PlantationClient with retry logic (tenacity) and error handling
- Added JSON Schema validation for all tool inputs
- All 12 unit tests pass covering all acceptance criteria
- Full test suite (294 tests) passes with no regressions
- Kubernetes deployment with HPA (min 2, max 10 replicas) configured
- OpenTelemetry tracing integrated for all tool calls

### File List

**New Files:**
- `mcp-servers/plantation-mcp/pyproject.toml` - Project dependencies
- `mcp-servers/plantation-mcp/Dockerfile` - Container build
- `mcp-servers/plantation-mcp/src/plantation_mcp/__init__.py`
- `mcp-servers/plantation-mcp/src/plantation_mcp/config.py` - Service settings
- `mcp-servers/plantation-mcp/src/plantation_mcp/main.py` - gRPC server entrypoint
- `mcp-servers/plantation-mcp/src/plantation_mcp/api/__init__.py`
- `mcp-servers/plantation-mcp/src/plantation_mcp/api/mcp_service.py` - McpToolService implementation
- `mcp-servers/plantation-mcp/src/plantation_mcp/tools/__init__.py`
- `mcp-servers/plantation-mcp/src/plantation_mcp/tools/definitions.py` - Tool schemas and registry
- `mcp-servers/plantation-mcp/src/plantation_mcp/infrastructure/__init__.py`
- `mcp-servers/plantation-mcp/src/plantation_mcp/infrastructure/plantation_client.py` - PlantationService client
- `mcp-servers/plantation-mcp/tests/__init__.py`
- `mcp-servers/plantation-mcp/tests/conftest.py`
- `mcp-servers/plantation-mcp/tests/unit/__init__.py`
- `mcp-servers/plantation-mcp/tests/unit/test_mcp_service.py` - 12 unit tests
- `deploy/kubernetes/base/mcp-servers/plantation-mcp/deployment.yaml`
- `deploy/kubernetes/base/mcp-servers/plantation-mcp/service.yaml`
- `deploy/kubernetes/base/mcp-servers/plantation-mcp/hpa.yaml`
- `deploy/kubernetes/base/mcp-servers/plantation-mcp/kustomization.yaml`

