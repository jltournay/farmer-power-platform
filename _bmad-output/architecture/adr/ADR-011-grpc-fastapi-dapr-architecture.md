# ADR-011: gRPC/FastAPI/DAPR Service Architecture

**Status:** Accepted
**Date:** 2025-12-31
**Deciders:** Winston (Architect), Amelia (Dev), Jeanlouistournay
**Related Stories:** Epic 0-4 (Grading Validation)

## Context

During E2E testing, the relationship between gRPC services, FastAPI endpoints, and DAPR sidecars was unclear:
- Services like `plantation-model` run BOTH gRPC (port 50051) AND FastAPI (port 8000)
- DAPR `app-protocol` only supports ONE protocol ([GitHub Issue #6391](https://github.com/dapr/dapr/issues/6391))

## Decision

**ALL application services use gRPC through DAPR (`app-protocol: grpc`). FastAPI is ONLY for management/admin endpoints accessed directly by K8s probes and operators (health, log level setter). Pub/sub events are delivered via gRPC `AppCallback` service.**

## Architecture Pattern

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SERVICE CONTAINER (e.g., plantation-model)            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────┐    ┌─────────────────────────────────┐        │
│  │  FastAPI (8000)     │    │  gRPC Server (50051)            │        │
│  │  MANAGEMENT ONLY    │    │  APPLICATION SERVICES           │        │
│  │                     │    │                                  │        │
│  │  /health (K8s)      │    │  PlantationService               │        │
│  │  /ready (K8s)       │    │  - GetFarmer                     │        │
│  │  /admin/logging     │    │  - ListCollectionPoints          │        │
│  │                     │    │  grpc.health.v1.Health           │        │
│  │                     │    │  dapr.proto.AppCallback          │        │
│  │                     │    │  - OnTopicEvent (pub/sub)        │        │
│  └──────────┬──────────┘    └──────────────┬──────────────────┘        │
│             │                              │                            │
│   DIRECT ◄──┘                              └──► VIA DAPR               │
│   (no DAPR)                                     (all services)         │
│                                                                         │
│    ┌───────────────────────────────────────────────────────────┐       │
│    │                    DAPR SIDECAR                           │       │
│    │                                                           │       │
│    │  -app-protocol "grpc"  ← ALL services via gRPC           │       │
│    │  -app-port "50051"     ← Points to gRPC server           │       │
│    │                                                           │       │
│    │  Pub/Sub → gRPC AppCallback.OnTopicEvent                 │       │
│    │  Service invocation → gRPC PlantationService             │       │
│    └───────────────────────────────────────────────────────────┘       │
│                                                                         │
│    K8s probes connect DIRECTLY to FastAPI port 8000 (no DAPR)          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Port Responsibilities

| Port | Protocol | Component | Purpose | Accessed By |
|------|----------|-----------|---------|-------------|
| `8000` | HTTP | FastAPI | K8s probes, Admin API | **Direct** (K8s, operators) |
| `50051` | gRPC | gRPC Server | All services + pub/sub | **Via DAPR sidecar** |
| `3500` | HTTP | DAPR Sidecar | Pub/Sub publish, State | Your service code |
| `50001` | gRPC | DAPR Sidecar | Service invocation proxy | Other services |

## DAPR Configuration

```yaml
# ALL services use gRPC for application logic
plantation-model-dapr:
  command: [
    "./daprd",
    "-app-id", "plantation-model",
    "-app-port", "50051",          # gRPC server port
    "-app-protocol", "grpc",       # ALL services use gRPC!
    "-dapr-http-port", "3500",
    "-dapr-grpc-port", "50001",
    "-components-path", "/components"
  ]
```

## Pub/Sub via gRPC (AppCallback Service)

When `app-protocol = grpc`, DAPR delivers pub/sub events via gRPC using the `AppCallback` service. This is NOT a Farmer Power API - it's the internal connection between the service and DAPR sidecar.

```python
class AppCallbackServicer(appcallback_pb2_grpc.AppCallbackServicer):
    """DAPR sidecar connection for pub/sub events (internal, not API)."""

    def __init__(self, quality_processor, weather_processor):
        # Reuse existing business logic processors
        self._quality_processor = quality_processor
        self._weather_processor = weather_processor

    async def OnTopicEvent(self, request, context):
        """Route incoming events to existing business logic."""
        topic = request.topic
        data = json.loads(request.data)

        if topic == "collection.quality_result.received":
            await self._quality_processor.process(data)
        elif topic == "weather.observation.updated":
            await self._weather_processor.process(data)

        return appcallback_pb2.TopicEventResponse(
            status=appcallback_pb2.TopicEventResponse.SUCCESS
        )
```

**Key point:** The `AppCallbackServicer` is a thin DAPR transport layer. The business logic stays in existing processors - no API changes needed.

## FastAPI (Management Only - Direct Access)

FastAPI endpoints are accessed **directly** by K8s and operators - NOT through DAPR:

```yaml
# Kubernetes deployment
livenessProbe:
  httpGet:
    path: /health
    port: 8000    # Direct to container, NOT through DAPR
readinessProbe:
  httpGet:
    path: /ready
    port: 8000    # Direct to container, NOT through DAPR
```

**FastAPI endpoints:**
- `/health` - K8s liveness probe
- `/ready` - K8s readiness probe
- `/admin/logging/{logger}` - Runtime log level (ADR-009)

## Implementation Gap

| Component | Current | Required |
|-----------|---------|----------|
| DAPR sidecar | `app-protocol: http`, `app-port: 8000` | `app-protocol: grpc`, `app-port: 50051` |
| Pub/sub handler | FastAPI HTTP endpoints | gRPC `AppCallback` servicer |

**What changes:**
- Add `AppCallbackServicer` to gRPC server (transport layer only)
- Remove `/dapr/subscribe` and `/api/v1/events/*` from FastAPI
- Update docker-compose DAPR config

**What stays the same:**
- All business logic processors
- FastAPI health/admin endpoints
- gRPC PlantationService API

## Decision Summary

| Concern | Protocol | Port | Via DAPR? |
|---------|----------|------|-----------|
| Application services | gRPC | 50051 | YES |
| Pub/sub events | gRPC (AppCallback) | 50051 | YES |
| K8s health probes | HTTP | 8000 | NO (direct) |
| Admin/management | HTTP | 8000 | NO (direct) |

**Rules:**
1. **ALL application services** → gRPC via DAPR (`app-protocol: grpc`)
2. **Pub/sub events** → gRPC `AppCallback.OnTopicEvent`
3. **K8s probes** → Direct HTTP to FastAPI port 8000
4. **Admin endpoints** → Direct HTTP to FastAPI port 8000
5. **FastAPI has NO DAPR involvement** → purely management

## Consequences

### Positive

- **Unified protocol** for all application services
- **Clear separation** between management and business logic
- **DAPR benefits** (mTLS, retries, observability) for all services

### Negative

- **Migration effort** - Move pub/sub handlers to gRPC
- **Additional complexity** - AppCallback servicer to implement

## Revisit Triggers

Re-evaluate this decision if:

1. **DAPR adds dual protocol** - May simplify architecture
2. **HTTP services needed** - May require separate approach

## References

- [DAPR GitHub Issue #6391 - Dual Protocol](https://github.com/dapr/dapr/issues/6391)
- [DAPR gRPC AppCallback](https://docs.dapr.io/developing-applications/sdks/python/python-sdk-extensions/python-grpc/)
- Epic 0-4: Grading Validation
- Related: ADR-009 (Logging), ADR-010 (DAPR Patterns)
