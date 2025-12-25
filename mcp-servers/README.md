# MCP Servers

Model Context Protocol (MCP) server implementations for inter-model data access.

## Protocol Decision: gRPC (not JSON-RPC)

**Important:** These MCP servers use **gRPC protocol** (not standard MCP JSON-RPC) to maintain unified internal communication through DAPR sidecars.

See `_bmad-output/architecture/infrastructure-decisions.md#mcp-protocol-decision-grpc-over-json-rpc` for full rationale.

```
┌─────────────────┐        gRPC            ┌─────────────────┐
│  AI Model       │ ─────────────────────▶ │  MCP Server     │
│  (LangChain)    │   (via DAPR sidecar)   │  (gRPC service) │
└─────────────────┘                        └─────────────────┘
```

**Trade-off:** Not compatible with standard MCP clients (Claude Desktop, etc.) but gains:
- Unified gRPC protocol across all services
- Full DAPR benefits (mTLS, observability, retries, circuit breaking)
- Strong typing via proto definitions

## Available MCP Servers

| Server | Domain Model | Purpose | DAPR App ID |
|--------|--------------|---------|-------------|
| `collection-mcp/` | Collection Model | Query quality events, documents | `collection-mcp` |
| `plantation-mcp/` | Plantation Model | Query farmers, factories, regions | `plantation-mcp` |
| `knowledge-mcp/` | Knowledge Model | Query diagnoses, analysis results | `knowledge-mcp` |
| `action-plan-mcp/` | Action Plan Model | Query action plans, recommendations | `action-plan-mcp` |

## Design Rules

1. **MCP servers are STATELESS** - no in-memory caching
2. **Tools return data, NOT make decisions** - business logic stays in domain models
3. **Read-only access** - mutations go through domain model APIs
4. **Use Pydantic models** for tool input/output schemas
5. **Implement `McpToolService`** - gRPC service defined in `proto/mcp/v1/mcp_tool.proto`

## Proto Contract

All MCP servers implement the same gRPC service interface:

```protobuf
service McpToolService {
  rpc ListTools(ListToolsRequest) returns (ListToolsResponse);
  rpc CallTool(ToolCallRequest) returns (ToolCallResponse);
}
```

See `proto/mcp/v1/mcp_tool.proto` for full definition.

## Tool Naming Conventions

- Read operations: `get_*`, `search_*`, `list_*`
- Examples: `get_farmer_by_id`, `search_quality_events`, `list_regions`

## Server Structure

```
mcp-servers/{model-name}-mcp/
├── src/{model_name}_mcp/
│   ├── __init__.py
│   ├── server.py           # gRPC server setup
│   ├── servicer.py         # McpToolService implementation
│   ├── tools/              # Tool implementations
│   └── schemas/            # Pydantic models
├── tests/
├── Dockerfile
└── pyproject.toml
```

## Calling MCP Servers from AI Model

```python
from dapr.clients import DaprClient

async def call_mcp_tool(app_id: str, tool_name: str, args: dict) -> dict:
    async with DaprClient() as client:
        response = await client.invoke_method(
            app_id=app_id,              # e.g., "collection-mcp"
            method_name="CallTool",
            data=ToolCallRequest(
                tool_name=tool_name,
                arguments_json=json.dumps(args)
            ).SerializeToString(),
            content_type="application/grpc"
        )
        result = ToolCallResponse.FromString(response.data)
        return json.loads(result.result_json)
```

See `_bmad-output/project-context.md` for MCP usage rules.
