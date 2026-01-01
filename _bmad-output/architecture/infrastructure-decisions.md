# Infrastructure Decisions

## MCP Server Scaling

**Decision:** MCP servers are stateless and deployed as separate Kubernetes pods, enabling horizontal scaling via HPA.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    MCP SERVER SCALING (Kubernetes)                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  AI MODEL (MCP Client)                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  MCP Client calls → Kubernetes Service (load balanced)           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                          │                                              │
│          ┌───────────────┼───────────────┐                              │
│          ▼               ▼               ▼                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                    │
│  │ Collection   │ │ Plantation   │ │ Knowledge    │                    │
│  │ MCP Service  │ │ MCP Service  │ │ MCP Service  │                    │
│  │ (ClusterIP)  │ │ (ClusterIP)  │ │ (ClusterIP)  │                    │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘                    │
│         │                │                │                             │
│    ┌────┴────┐      ┌────┴────┐      ┌────┴────┐                       │
│    ▼    ▼    ▼      ▼    ▼    ▼      ▼    ▼    ▼                       │
│  ┌───┐┌───┐┌───┐  ┌───┐┌───┐┌───┐  ┌───┐┌───┐┌───┐                    │
│  │Pod││Pod││Pod│  │Pod││Pod││Pod│  │Pod││Pod││Pod│                    │
│  └───┘└───┘└───┘  └───┘└───┘└───┘  └───┘└───┘└───┘                    │
│         │                │                │                             │
│         ▼                ▼                ▼                             │
│      MongoDB          MongoDB          MongoDB                          │
│      (Read            (Read            (Read                            │
│       Replicas)        Replicas)        Replicas)                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Scaling Configuration:**

```yaml
# kubernetes/mcp-servers/collection-mcp-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: collection-mcp-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: collection-mcp-server
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: mcp_requests_per_second
        target:
          type: AverageValue
          averageValue: "100"
```

**Key Points:**
- All state in MongoDB (read replicas for queries)
- Kubernetes Service provides load balancing
- HPA scales based on CPU and request rate
- Each MCP server (Collection, Plantation, Knowledge) scales independently

## MCP Protocol Decision: gRPC over JSON-RPC

**Decision:** MCP servers use gRPC protocol (not standard JSON-RPC) to maintain unified internal communication through DAPR.

### Context

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io/specification/2025-11-25) standard defines JSON-RPC 2.0 as the wire protocol, typically transported over stdio or HTTP+SSE. However, our architecture mandates gRPC for all internal service communication via DAPR sidecars.

### Problem Statement

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PROTOCOL TENSION                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Standard MCP                          Our Architecture                     │
│  ┌─────────────────┐                  ┌─────────────────┐                  │
│  │ JSON-RPC 2.0    │                  │ gRPC via DAPR   │                  │
│  │ over HTTP/stdio │       vs         │ for all internal│                  │
│  │                 │                  │ communication   │                  │
│  └─────────────────┘                  └─────────────────┘                  │
│                                                                             │
│  Options Evaluated:                                                         │
│  A) JSON-RPC bypassing DAPR  → Loses observability, mTLS, circuit breaker  │
│  B) JSON-RPC through DAPR    → Mixed protocols, added complexity           │
│  C) gRPC native (chosen)     → Unified protocol, full DAPR benefits        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Decision: gRPC-Native MCP (Option C)

We adopt the **MCP conceptual model** (tools, resources) but implement it with **gRPC transport**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    gRPC-NATIVE MCP ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  AI Model                                          MCP Server               │
│  ┌─────────────────┐                              ┌─────────────────┐      │
│  │  LangChain/     │                              │  gRPC Service   │      │
│  │  LangGraph      │                              │                 │      │
│  │                 │                              │  Implements:    │      │
│  │  GrpcMcpTool    │                              │  McpToolService │      │
│  │  (wrapper)      │                              │                 │      │
│  └────────┬────────┘                              └────────▲────────┘      │
│           │                                                │                │
│           │ gRPC                                     gRPC  │                │
│           ▼                                                │                │
│  ┌─────────────────┐        gRPC            ┌─────────────────┐            │
│  │  DAPR Sidecar   │ ─────────────────────▶ │  DAPR Sidecar   │            │
│  │  :50001         │   (sidecar-to-sidecar) │  :50001         │            │
│  └─────────────────┘                        └─────────────────┘            │
│                                                                             │
│  Benefits:                                                                  │
│  ✓ Unified protocol (gRPC everywhere)                                      │
│  ✓ All traffic through DAPR sidecars                                       │
│  ✓ mTLS, observability, retries, circuit breaking                          │
│  ✓ Strong typing via proto definitions                                     │
│  ✓ Streaming support for large results                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Proto Definition

MCP tool calls are defined in `proto/mcp/v1/mcp_tool.proto`:

```protobuf
syntax = "proto3";
package farmer_power.mcp.v1;

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
  string error_message = 3;           // Error details if success=false
  string error_code = 4;              // Machine-readable error code
}
```

### LangChain Integration

The AI Model wraps gRPC calls in LangChain-compatible tools:

```python
# ai-model/src/ai_model/tools/grpc_mcp_tool.py
from langchain.tools import BaseTool
from dapr.clients import DaprClient

class GrpcMcpTool(BaseTool):
    """Wraps gRPC MCP call as LangChain tool."""

    name: str
    description: str
    mcp_server_app_id: str  # DAPR app-id

    async def _arun(self, **kwargs) -> str:
        async with DaprClient() as client:
            request = ToolCallRequest(
                tool_name=self.name,
                arguments_json=json.dumps(kwargs),
                trace_id=get_current_trace_id(),
                caller_agent_id=get_current_agent_id()
            )

            response = await client.invoke_method(
                app_id=self.mcp_server_app_id,
                method_name="CallTool",
                data=request.SerializeToString(),
                content_type="application/grpc"
            )

            result = ToolCallResponse.FromString(response.data)
            if not result.success:
                raise ToolExecutionError(result.error_message)
            return result.result_json
```

### Trade-offs

| Factor | gRPC Native | Standard MCP (JSON-RPC) |
|--------|-------------|-------------------------|
| **DAPR Integration** | ✅ Native | ⚠️ Requires app-protocol: http |
| **Protocol Consistency** | ✅ Unified gRPC | ❌ Mixed protocols |
| **Type Safety** | ✅ Proto definitions | ⚠️ Runtime validation |
| **Streaming** | ✅ Native support | ❌ Not in JSON-RPC |
| **Claude Desktop/ChatGPT** | ❌ Incompatible | ✅ Works directly |
| **MCP Inspector Tool** | ❌ Won't work | ✅ Full support |
| **External MCP Servers** | ❌ Need adapter | ✅ Direct connection |
| **Development Effort** | ⚠️ +13-16h per server | ✅ Use SDK |

### When Standard MCP Compatibility is Needed

If future requirements demand standard MCP compatibility (e.g., external developers building tools), add an **MCP Adapter Gateway**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FUTURE: MCP ADAPTER (if needed)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  External MCP Client                              Internal gRPC MCP         │
│  (Claude Desktop, etc.)                                                     │
│  ┌─────────────────┐                              ┌─────────────────┐      │
│  │  JSON-RPC 2.0   │                              │  gRPC Service   │      │
│  │  over HTTP      │                              │  (unchanged)    │      │
│  └────────┬────────┘                              └────────▲────────┘      │
│           │                                                │                │
│           │ JSON-RPC                                 gRPC  │                │
│           ▼                                                │                │
│  ┌─────────────────────────────────────────────────────────┘               │
│  │  MCP Adapter Gateway                                                    │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  │  - Translates JSON-RPC ↔ gRPC                                    │   │
│  │  │  - Implements MCP initialization handshake                       │   │
│  │  │  - Routes to appropriate internal MCP server                     │   │
│  │  │  - Effort: ~8 hours to implement                                 │   │
│  │  └─────────────────────────────────────────────────────────────────┘   │
│  └─────────────────────────────────────────────────────────────────────────┘
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Estimated effort for adapter:** ~8 hours (deferred until needed)

### Decision Summary

| Aspect | Decision |
|--------|----------|
| **Protocol** | gRPC (not JSON-RPC) |
| **Transport** | DAPR service invocation |
| **Conceptual Model** | MCP (tools, resources) |
| **Standard Compliance** | No (internal only) |
| **Future Compatibility** | Adapter pattern if needed |

### References

- [MCP Specification](https://modelcontextprotocol.io/specification/2025-11-25)
- [Anthropic MCP Introduction](https://www.anthropic.com/news/model-context-protocol)
- [DAPR Service Invocation](https://docs.dapr.io/developing-applications/building-blocks/service-invocation/)

## External API Resiliency (DAPR Circuit Breaker)

**Decision:** Use DAPR's built-in resiliency policies for external API calls (Starfish Network, Weather APIs, Google Elevation API).

```yaml
# dapr/components/resiliency.yaml
apiVersion: dapr.io/v1alpha1
kind: Resiliency
metadata:
  name: external-api-resiliency
spec:
  policies:
    # ═══════════════════════════════════════════════════════════════════════
    # RETRY POLICIES
    # ═══════════════════════════════════════════════════════════════════════
    retries:
      default-retry:
        policy: constant
        maxRetries: 3
        duration: 1s

      starfish-retry:
        policy: exponential
        maxRetries: 5
        maxInterval: 30s

      weather-retry:
        policy: constant
        maxRetries: 3
        duration: 2s

    # ═══════════════════════════════════════════════════════════════════════
    # CIRCUIT BREAKER POLICIES
    # ═══════════════════════════════════════════════════════════════════════
    circuitBreakers:
      starfish-cb:
        maxRequests: 5              # Max requests when half-open
        interval: 30s               # Time window for counting failures
        timeout: 60s                # Time circuit stays open
        trip: consecutiveFailures >= 3

      weather-cb:
        maxRequests: 3
        interval: 60s
        timeout: 120s
        trip: consecutiveFailures >= 5

    # ═══════════════════════════════════════════════════════════════════════
    # TIMEOUT POLICIES
    # ═══════════════════════════════════════════════════════════════════════
    timeouts:
      starfish-timeout: 10s
      weather-timeout: 5s
      elevation-timeout: 3s

  # ═══════════════════════════════════════════════════════════════════════════
  # TARGET CONFIGURATION
  # ═══════════════════════════════════════════════════════════════════════════
  targets:
    components:
      starfish-api:
        outbound:
          retry: starfish-retry
          circuitBreaker: starfish-cb
          timeout: starfish-timeout

      weather-api:
        outbound:
          retry: weather-retry
          circuitBreaker: weather-cb
          timeout: weather-timeout

      google-elevation-api:
        outbound:
          retry: default-retry
          timeout: elevation-timeout
```

**Circuit Breaker Behavior:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CIRCUIT BREAKER STATES                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   CLOSED (Normal)                                                       │
│   ┌─────────────┐                                                       │
│   │ Requests    │──────▶ External API                                   │
│   │ pass through│                                                       │
│   └──────┬──────┘                                                       │
│          │ 3 consecutive failures                                       │
│          ▼                                                              │
│   OPEN (Protecting)                                                     │
│   ┌─────────────┐                                                       │
│   │ Requests    │──────▶ Fail fast (no API call)                        │
│   │ rejected    │        Return cached/default if available             │
│   └──────┬──────┘                                                       │
│          │ After 60s timeout                                            │
│          ▼                                                              │
│   HALF-OPEN (Testing)                                                   │
│   ┌─────────────┐                                                       │
│   │ Limited     │──────▶ External API (max 5 requests)                  │
│   │ requests    │                                                       │
│   └──────┬──────┘                                                       │
│          │                                                              │
│    ┌─────┴─────┐                                                        │
│    │           │                                                        │
│ Success     Failure                                                     │
│    │           │                                                        │
│    ▼           ▼                                                        │
│  CLOSED     OPEN                                                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key Benefits:**
- Configuration-driven (no code changes)
- Prevents cascading failures when external APIs are down
- Automatic recovery when services become healthy
- Consistent resilience pattern across all external calls

## Kubernetes Deployment Architecture

**Decision:** Single namespace per environment on a shared Kubernetes cluster, with Backend-for-Frontend (BFF) pattern for external API exposure.

### Multi-Environment Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SINGLE KUBERNETES CLUSTER - MULTI-ENVIRONMENT            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Namespace: farmer-power-qa                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  All services for QA environment                                    │   │
│  │  ResourceQuota: cpu=4, memory=8Gi                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Namespace: farmer-power-preprod                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  All services for Pre-Production environment                        │   │
│  │  ResourceQuota: cpu=8, memory=16Gi                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Namespace: farmer-power-prod                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  All services for Production environment                            │   │
│  │  ResourceQuota: cpu=32, memory=64Gi (or no limit)                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Namespace: dapr-system (shared across all environments)                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Dapr Control Plane (operator, placement, sentry)                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Benefits:**
- Single cluster reduces infrastructure cost
- Namespace isolation via RBAC, NetworkPolicies, ResourceQuotas
- QA/PreProd can share node pools, Prod uses dedicated nodes
- Simple deployment pipeline per environment

### Namespace Service Organization

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    NAMESPACE: farmer-power-{env}                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────── EDGE LAYER ──────────────────────────┐           │
│  │                                                              │           │
│  │  ┌──────────────────────────────────────────────────────┐   │           │
│  │  │           INGRESS (NGINX / Azure App Gateway)         │   │           │
│  │  │  api.farmerpower.io → bff-service                    │   │           │
│  │  │  webhooks.farmerpower.io → inbound-webhook-svc       │   │           │
│  │  └──────────────────────────────────────────────────────┘   │           │
│  │                          │                                   │           │
│  │                          ▼                                   │           │
│  │  ┌──────────────────────────────────────────────────────┐   │           │
│  │  │              BFF (Backend For Frontend)               │   │           │
│  │  │  ┌────────────────────────────────────────────────┐  │   │           │
│  │  │  │  FastAPI + WebSocket                           │  │   │           │
│  │  │  │  - REST API endpoints for React UI             │  │   │           │
│  │  │  │  - WebSocket for real-time updates             │  │   │           │
│  │  │  │  - OAuth2/JWT authentication                   │  │   │           │
│  │  │  │  - Request aggregation & transformation        │  │   │           │
│  │  │  │  + Dapr sidecar (gRPC to internal services)    │  │   │           │
│  │  │  └────────────────────────────────────────────────┘  │   │           │
│  │  │  replicas: 3 (HPA: 2-10)                             │   │           │
│  │  └──────────────────────────────────────────────────────┘   │           │
│  └──────────────────────────────────────────────────────────────┘           │
│                          │                                                  │
│                          │ gRPC via Dapr                                    │
│                          ▼                                                  │
│  ┌─────────────── BUSINESS MODELS (gRPC + Dapr) ───────────────┐           │
│  │                                                              │           │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │           │
│  │  │ collection-  │ │ knowledge-   │ │ plantation-  │        │           │
│  │  │ model        │ │ model        │ │ model        │        │           │
│  │  │ + dapr       │ │ + dapr       │ │ + dapr       │        │           │
│  │  │ gRPC :50051  │ │ gRPC :50051  │ │ gRPC :50051  │        │           │
│  │  └──────────────┘ └──────────────┘ └──────────────┘        │           │
│  │        │                │                │                  │           │
│  │        └────────────────┼────────────────┘                  │           │
│  │                         │ gRPC via Dapr                     │           │
│  │                         ▼                                   │           │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │           │
│  │  │ action-plan- │ │ market-      │ │ ai-model     │        │           │
│  │  │ model        │ │ analysis     │ │ (LLM gateway)│        │           │
│  │  │ + dapr       │ │ + dapr       │ │ + dapr       │        │           │
│  │  │ gRPC :50051  │ │ gRPC :50051  │ │ gRPC :50051  │        │           │
│  │  └──────────────┘ └──────────────┘ └──────────────┘        │           │
│  └──────────────────────────────────────────────────────────────┘           │
│                          │                                                  │
│                          │ gRPC via Dapr                                    │
│                          ▼                                                  │
│  ┌─────────────── MCP SERVERS (gRPC, HPA-enabled) ─────────────┐           │
│  │                                                              │           │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │           │
│  │  │ collection-  │ │ plantation-  │ │ knowledge-   │        │           │
│  │  │ mcp          │ │ mcp          │ │ mcp          │        │           │
│  │  │ HPA: 2-10    │ │ HPA: 2-10    │ │ HPA: 2-10    │        │           │
│  │  │ gRPC :50051  │ │ gRPC :50051  │ │ gRPC :50051  │        │           │
│  │  └──────────────┘ └──────────────┘ └──────────────┘        │           │
│  └──────────────────────────────────────────────────────────────┘           │
│                                                                             │
│  ┌─────────────── MESSAGING (gRPC + Dapr) ─────────────────────┐           │
│  │                                                              │           │
│  │  ┌──────────────┐ ┌──────────────┐                         │           │
│  │  │ notification-│ │ inbound-     │ ← External webhook      │           │
│  │  │ service      │ │ webhook      │   (Africa's Talking)    │           │
│  │  │ + dapr       │ │ + dapr       │                         │           │
│  │  └──────────────┘ └──────────────┘                         │           │
│  └──────────────────────────────────────────────────────────────┘           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Communication Protocol Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        COMMUNICATION PROTOCOLS                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  React UI                                                                   │
│     │                                                                       │
│     │  HTTPS (REST API + WebSocket)                                        │
│     ▼                                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  BFF (FastAPI)                                                       │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │   │
│  │  │ REST Endpoints  │  │ WebSocket Hub   │  │ Auth Middleware │     │   │
│  │  │ /api/v1/...     │  │ /ws/events      │  │ JWT Validation  │     │   │
│  │  └────────┬────────┘  └────────┬────────┘  └─────────────────┘     │   │
│  │           │                    │                                    │   │
│  │           └─────────┬──────────┘                                    │   │
│  │                     ▼                                               │   │
│  │           ┌─────────────────────┐                                   │   │
│  │           │ Dapr Sidecar        │                                   │   │
│  │           │ (Service Invocation)│                                   │   │
│  │           └─────────┬───────────┘                                   │   │
│  └─────────────────────│───────────────────────────────────────────────┘   │
│                        │                                                    │
│                        │ gRPC (via Dapr service invocation)                │
│                        ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Internal Services (all with Dapr sidecars)                         │   │
│  │                                                                      │   │
│  │  plantation-model ◄──gRPC──► collection-model ◄──gRPC──► ai-model   │   │
│  │         │                          │                        │        │   │
│  │         └──────────gRPC────────────┼────────────────────────┘        │   │
│  │                                    │                                 │   │
│  │                              knowledge-model                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Protocol Summary:**

| Layer | Protocol | Reason |
|-------|----------|--------|
| UI → BFF | REST + WebSocket | Browser-compatible, real-time updates |
| BFF → Services | gRPC via Dapr | Efficient binary protocol, type-safe |
| Service → Service | gRPC via Dapr | Low latency, streaming support |
| Service → MCP | gRPC | LLM tool invocation |

### BFF Responsibilities

| Function | Description |
|----------|-------------|
| **Authentication** | Validate JWT tokens, enforce RBAC per endpoint |
| **API Aggregation** | Combine multiple gRPC calls into single REST response |
| **Protocol Translation** | REST/WebSocket ↔ gRPC conversion |
| **Real-time Events** | Push updates to UI via WebSocket (quality events, alerts) |
| **Rate Limiting** | Protect internal services from abuse |
| **Request Validation** | Validate input schemas before forwarding |

### Deployment Manifest Summary

| Service | Type | Protocol Exposed | Replicas | HPA |
|---------|------|------------------|----------|-----|
| bff | Deployment | REST + WebSocket (external) | 3 | 2-10 |
| collection-model | Deployment | gRPC (internal) | 2 | No |
| knowledge-model | Deployment | gRPC (internal) | 2 | No |
| plantation-model | Deployment | gRPC (internal) | 2 | No |
| action-plan-model | Deployment | gRPC (internal) | 2 | No |
| market-analysis | Deployment | gRPC (internal) | 1 | No |
| ai-model | Deployment | gRPC (internal) | 3 | No |
| collection-mcp | Deployment | gRPC (internal) | 2 | 2-10 |
| plantation-mcp | Deployment | gRPC (internal) | 2 | 2-10 |
| knowledge-mcp | Deployment | gRPC (internal) | 2 | 2-10 |
| notification-service | Deployment | gRPC (internal) | 2 | No |
| inbound-webhook | Deployment | HTTPS (external) | 2 | No |

### External Managed Services

| Service | Provider | Connection |
|---------|----------|------------|
| MongoDB | Atlas or Azure CosmosDB | Connection string in Secret |
| Pinecone | Pinecone Cloud | API key in Secret |
| Azure OpenAI | Azure | Endpoint + key in Secret |
| Azure Blob Storage | Azure | Connection string in Secret |
| Africa's Talking | AT | API credentials in Secret |

### Environment Configuration

```yaml
# configmap-prod.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: farmer-power-prod
data:
  ENVIRONMENT: "production"
  MONGODB_DATABASE: "farmerpower_prod"
  PINECONE_INDEX: "knowledge-prod"
  LOG_LEVEL: "info"
  ENABLE_SMS: "true"
  GRPC_PORT: "50051"

---
# configmap-qa.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: farmer-power-qa
data:
  ENVIRONMENT: "qa"
  MONGODB_DATABASE: "farmerpower_qa"
  PINECONE_INDEX: "knowledge-qa"
  LOG_LEVEL: "debug"
  ENABLE_SMS: "false"  # Mock SMS in QA
  GRPC_PORT: "50051"
```

### Dapr Component Configuration (Per Namespace)

```yaml
# dapr/components/statestore.yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: statestore
  namespace: farmer-power-prod
spec:
  type: state.mongodb
  version: v1
  metadata:
    - name: host
      secretKeyRef:
        name: mongodb-connection
        key: host
    - name: databaseName
      value: "farmerpower_prod"

---
# dapr/components/pubsub.yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: pubsub
  namespace: farmer-power-prod
spec:
  type: pubsub.azure.servicebus
  version: v1
  metadata:
    - name: connectionString
      secretKeyRef:
        name: servicebus-connection
        key: connectionString
```

## Related ADRs

For detailed architecture decisions discovered during E2E testing (Epic 0-4), see the ADR folder:

- [ADR-004: Type Safety - Shared Pydantic Models](./adr/ADR-004-type-safety-shared-pydantic-models.md)
- [ADR-005: gRPC Client Retry Strategy](./adr/ADR-005-grpc-client-retry-strategy.md)
- [ADR-006: Event Delivery & Dead Letter Queue](./adr/ADR-006-event-delivery-dead-letter-queue.md)
- [ADR-007: Source Config Cache with Change Streams](./adr/ADR-007-source-config-cache-change-streams.md)
- [ADR-008: Invalid Linkage Field Handling](./adr/ADR-008-invalid-linkage-field-handling.md)
- [ADR-009: Logging Standards](./adr/ADR-009-logging-standards-runtime-configuration.md)
- [ADR-010: DAPR Patterns](./adr/ADR-010-dapr-patterns-configuration.md)
- [ADR-011: gRPC/FastAPI/DAPR Architecture](./adr/ADR-011-grpc-fastapi-dapr-architecture.md)
