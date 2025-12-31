# ADR-010: DAPR Patterns and Configuration Standards

**Status:** Accepted
**Date:** 2025-12-31
**Deciders:** Winston (Architect), Amelia (Dev), Jeanlouistournay
**Related Stories:** Epic 0-4 (Grading Validation)

## Context

During E2E testing and development of Epic 0-4, we frequently encountered confusion about:
1. Which DAPR port to use for different operations
2. How to start DAPR sidecars with correct parameters
3. Component configuration structure
4. URL patterns for pub/sub and service invocation

## Decision

**Document all DAPR patterns as a single reference for developers.**

## DAPR Port Reference

| Port | Protocol | Purpose | Environment Variable |
|------|----------|---------|----------------------|
| `3500` | HTTP | Pub/Sub publish, State, Secrets, Bindings | `DAPR_HTTP_PORT` |
| `50001` | gRPC | Service invocation, gRPC proxying | `DAPR_GRPC_PORT` |

**Service Configuration:**
```python
class Settings(BaseSettings):
    dapr_host: str = "localhost"
    dapr_http_port: int = 3500    # For pub/sub, state, secrets
    dapr_grpc_port: int = 50001   # For service invocation
    dapr_pubsub_name: str = "pubsub"
```

## DAPR Sidecar Startup Parameters

### Docker Compose Example

```yaml
plantation-model-dapr:
  image: daprio/daprd:1.12.0
  command: [
    "./daprd",
    "-app-id", "plantation-model",
    "-app-port", "50051",          # Port YOUR app listens on
    "-app-protocol", "grpc",       # Protocol YOUR app speaks
    "-dapr-http-port", "3500",     # Port YOU call DAPR on
    "-dapr-grpc-port", "50001",
    "-components-path", "/components"
  ]
  network_mode: "service:plantation-model"
```

**Key Parameters:**

| Parameter | Description | Examples |
|-----------|-------------|----------|
| `-app-id` | Unique service identifier | `plantation-model` |
| `-app-port` | Port YOUR service listens on | `8000`, `50051` |
| `-app-protocol` | Protocol YOUR service speaks | `http` or `grpc` |
| `-dapr-http-port` | Port to call DAPR HTTP APIs | `3500` |
| `-dapr-grpc-port` | Port for DAPR gRPC proxy | `50001` |
| `-components-path` | Location of component YAMLs | `/components` |

## Component Configuration

### Pub/Sub Component (Redis)

```yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: pubsub
spec:
  type: pubsub.redis
  version: v1
  metadata:
    - name: redisHost
      value: redis:6379
```

### Subscription (Declarative - RECOMMENDED)

```yaml
apiVersion: dapr.io/v2alpha1
kind: Subscription
metadata:
  name: quality-result-subscription
spec:
  pubsubname: pubsub
  topic: collection.quality_result.received
  routes:
    default: /api/v1/events/quality-result
  deadLetterTopic: events.dlq
scopes:
  - plantation-model
```

**IMPORTANT:** Prefer declarative subscriptions (YAML) over `/dapr/subscribe` endpoint. Declarative subscriptions support `deadLetterTopic` (ADR-006).

## URL Patterns

### Pub/Sub - Publish Event

```python
# URL: http://localhost:3500/v1.0/publish/{pubsub}/{topic}
url = f"http://localhost:{settings.dapr_http_port}/v1.0/publish/{settings.dapr_pubsub_name}/{topic}"

async with httpx.AsyncClient() as client:
    response = await client.post(url, json=payload)
```

### Service Invocation (via gRPC)

```python
# Connect to DAPR's gRPC port, not the service directly
channel = grpc.aio.insecure_channel(f"localhost:{settings.dapr_grpc_port}")

# Add DAPR app-id metadata to route to correct service
metadata = [("dapr-app-id", "ai-model")]

stub = SomeServiceStub(channel)
response = await stub.SomeMethod(request, metadata=metadata)
```

### Health Check

```python
# URL: http://localhost:3500/v1.0/healthz
async def check_dapr_health() -> bool:
    url = f"http://localhost:{settings.dapr_http_port}/v1.0/healthz"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=2.0)
        return response.status_code == 200
```

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────┐
│                     DAPR QUICK REFERENCE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PORTS                                                          │
│  ├── 3500  (HTTP)  → Pub/Sub, State, Secrets                   │
│  └── 50001 (gRPC)  → Service Invocation                        │
│                                                                 │
│  PUBLISH EVENT                                                  │
│  POST http://localhost:3500/v1.0/publish/{pubsub}/{topic}      │
│                                                                 │
│  RECEIVE EVENT                                                  │
│  DAPR → POST http://your-app:8000/api/v1/events/{handler}      │
│  Return: {"status": "SUCCESS" | "RETRY" | "DROP"}              │
│                                                                 │
│  SERVICE INVOCATION (gRPC)                                      │
│  Connect: localhost:50001                                       │
│  Metadata: dapr-app-id = target-service                        │
│                                                                 │
│  HEALTH CHECK                                                   │
│  GET http://localhost:3500/v1.0/healthz                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Common Mistakes

| Mistake | Correct Approach |
|---------|------------------|
| Calling service directly | Use DAPR gRPC proxy with `dapr-app-id` |
| Hardcoding topics | Read topics from source config |
| Using `/dapr/subscribe` for DLQ | Use declarative subscriptions |
| Connecting to `service:50051` | Connect to `localhost:50001` (DAPR port) |
| Missing `network_mode` in Docker | Sidecar must share network with service |

## Consequences

### Positive

- **Single reference** for all DAPR patterns
- **Consistent configuration** across services
- **Onboarding efficiency** for new developers

### Negative

- **Documentation maintenance** required as DAPR evolves

## Revisit Triggers

Re-evaluate this decision if:

1. **DAPR version upgrade** - Check for breaking changes
2. **New DAPR features** - May enable better patterns

## References

- [DAPR Pub/Sub](https://docs.dapr.io/developing-applications/building-blocks/pubsub/)
- [DAPR Service Invocation](https://docs.dapr.io/developing-applications/building-blocks/service-invocation/)
- [DAPR Subscriptions](https://docs.dapr.io/developing-applications/building-blocks/pubsub/subscription-methods/)
- Epic 0-4: Grading Validation
- Related: ADR-006 (Dead Letter Queue)
