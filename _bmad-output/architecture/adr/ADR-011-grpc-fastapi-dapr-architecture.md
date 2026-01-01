# ADR-011: Service Architecture - gRPC APIs and DAPR SDK Pub/Sub

**Status:** Accepted (Revised)
**Date:** 2025-12-31 (Revised: 2026-01-01)
**Deciders:** Winston (Architect), Amelia (Dev), Jeanlouistournay
**Related Stories:** Epic 0-4 (Grading Validation)
**Validated By:** PoC at `tests/e2e/poc-dapr-patterns/` (5/5 tests passing)

## Context

During E2E testing, there was confusion about:
1. The relationship between gRPC services and pub/sub event handling
2. Whether to use HTTP or gRPC for event handlers
3. How DAPR fits into the architecture

## Decision

**Separation of concerns:**
- **gRPC servers** for synchronous service-to-service APIs (PlantationService, etc.)
- **DAPR Python SDK streaming subscriptions** for pub/sub (outbound connection to sidecar)
- **FastAPI** only for health checks and admin endpoints (K8s probes)

The SDK uses **streaming subscriptions** - your app connects outbound to the DAPR sidecar. No extra incoming port is needed for pub/sub.

> **IMPORTANT:** Streaming subscriptions require **DAPR 1.14.0 or later** and **dapr Python SDK 1.14.0+**.

## Architecture Pattern

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SERVICE CONTAINER (e.g., plantation-model)            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────┐  ┌─────────────────────────────────────────┐   │
│  │  FastAPI (8000)     │  │  gRPC Server (50051)                    │   │
│  │  HEALTH/ADMIN ONLY  │  │  SERVICE APIs                          │   │
│  │                     │  │                                         │   │
│  │  /health            │  │  PlantationService                      │   │
│  │  /ready             │  │  - GetFarmer                            │   │
│  │  /admin/logging     │  │  - ListRegions                          │   │
│  └──────────┬──────────┘  └──────────────┬──────────────────────────┘   │
│             │                            │                              │
│        K8s probes                   app-port 50051                      │
│        (direct)                     (service invocation)                │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Pub/Sub via DaprClient() - OUTBOUND connections to sidecar      │   │
│  │                                                                   │   │
│  │  Publishing:    client.publish_event(...)      → outbound        │   │
│  │  Subscribing:   client.subscribe_with_handler(...) → streaming   │   │
│  │                                                                   │   │
│  │  NO INCOMING PORT NEEDED - app initiates connection to sidecar   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### 1. gRPC Server (Port 50051) - Service APIs

For synchronous request/response between services:

```python
# plantation_model/api/grpc_server.py
class PlantationServicer(PlantationServiceServicer):
    """gRPC API for plantation data queries."""

    async def GetFarmer(self, request, context):
        farmer = await self._farmer_repo.get_by_id(request.farmer_id)
        return farmer_to_proto(farmer)

    async def ListCollectionPoints(self, request, context):
        points = await self._cp_repo.list_by_factory(request.factory_id)
        return ListCollectionPointsResponse(collection_points=points)
```

Other services call via DAPR gRPC proxy:

```python
# Caller adds dapr-app-id metadata
channel = grpc.aio.insecure_channel(f"localhost:{DAPR_GRPC_PORT}")
metadata = [("dapr-app-id", "plantation-model")]
stub = PlantationServiceStub(channel)
response = await stub.GetFarmer(request, metadata=metadata)
```

### 2. DAPR SDK Streaming Subscriptions - Pub/Sub

For asynchronous event-driven communication using **outbound streaming**:

```python
# plantation_model/events/subscriber.py
from dapr.clients import DaprClient
from dapr.clients.grpc._response import TopicEventResponse
import structlog

logger = structlog.get_logger("plantation_model.events")

def handle_quality_result(message) -> TopicEventResponse:
    """Handle quality result events from collection-model.

    IMPORTANT:
    - message.data() returns a dict, NOT a JSON string
    - Must return TopicEventResponse
    """
    # message.data() returns dict directly - no json.loads() needed!
    data = message.data()
    document_id = data.get("document_id")

    try:
        quality_processor.process(data)
        logger.info("Quality result processed", document_id=document_id)
        return TopicEventResponse("success")
    except TransientError:
        logger.warning("Transient error, will retry", document_id=document_id)
        return TopicEventResponse("retry")
    except PermanentError:
        logger.error("Permanent error, sending to DLQ", document_id=document_id)
        return TopicEventResponse("drop")

def handle_weather_update(message) -> TopicEventResponse:
    """Handle weather update events."""
    data = message.data()  # Returns dict directly
    weather_processor.process(data)
    return TopicEventResponse("success")

async def start_subscriptions():
    """Start all pub/sub subscriptions - call during service startup."""
    client = DaprClient()

    # Subscribe to quality results with DLQ
    quality_close = client.subscribe_with_handler(
        pubsub_name="pubsub",
        topic="collection.quality_result.received",
        handler_fn=handle_quality_result,
        dead_letter_topic="events.dlq",
    )

    # Subscribe to weather updates with DLQ
    weather_close = client.subscribe_with_handler(
        pubsub_name="pubsub",
        topic="weather.observation.updated",
        handler_fn=handle_weather_update,
        dead_letter_topic="events.dlq",
    )

    return [quality_close, weather_close]
```

Publishing:

```python
# collection_model/services/event_publisher.py
from dapr.clients import DaprClient

class EventPublisher:
    def publish_quality_result(self, document_id: str, grades: dict) -> None:
        with DaprClient() as client:
            client.publish_event(
                pubsub_name="pubsub",
                topic_name="collection.quality_result.received",
                data=json.dumps({"document_id": document_id, "grades": grades}),
            )
```

### 3. FastAPI (Port 8000) - Health/Admin Only

For Kubernetes probes and operational endpoints:

```python
# plantation_model/api/health.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health():
    """Liveness probe for K8s."""
    return {"status": "healthy"}

@app.get("/ready")
async def ready():
    """Readiness probe for K8s."""
    if not db_connected:
        return Response(status_code=503)
    return {"status": "ready"}

@app.post("/admin/logging/{logger_name}")
async def set_log_level(logger_name: str, level: str):
    """Runtime log level configuration."""
    logging.getLogger(logger_name).setLevel(level.upper())
    return {"status": "updated"}
```

## Why Streaming Subscriptions?

| Approach | Direction | Extra Port? | DLQ Support |
|----------|-----------|-------------|-------------|
| `@app.subscribe()` decorator | DAPR pushes TO your app | Yes - needs incoming port | Via external YAML only |
| `subscribe_with_handler()` | Your app pulls FROM DAPR | **No** - outbound only | **In code or YAML** |

Streaming subscriptions are simpler:
- No extra port configuration
- No `app-protocol` concerns for pub/sub
- DLQ configurable directly in code
- Your app controls the connection lifecycle

## Service Startup

```python
# plantation_model/main.py
import asyncio
import uvicorn
import grpc.aio

async def main():
    # 1. Start pub/sub subscriptions (outbound to DAPR sidecar)
    subscription_closers = await start_subscriptions()

    # 2. Start FastAPI for health probes
    uvicorn_config = uvicorn.Config(health_app, host="0.0.0.0", port=8000)
    uvicorn_server = uvicorn.Server(uvicorn_config)

    # 3. Start gRPC server for service APIs
    grpc_server = grpc.aio.server()
    add_PlantationServiceServicer_to_server(PlantationServicer(), grpc_server)
    grpc_server.add_insecure_port("[::]:50051")
    await grpc_server.start()

    try:
        await asyncio.gather(
            uvicorn_server.serve(),
            grpc_server.wait_for_termination(),
        )
    finally:
        # Clean up subscriptions
        for close_fn in subscription_closers:
            close_fn()

if __name__ == "__main__":
    asyncio.run(main())
```

## Kubernetes Configuration

```yaml
# deployment.yaml
spec:
  containers:
    - name: plantation-model
      ports:
        - containerPort: 8000   # FastAPI health/admin
        - containerPort: 50051  # gRPC service API
        # NO port needed for pub/sub - outbound streaming
      livenessProbe:
        httpGet:
          path: /health
          port: 8000
      readinessProbe:
        httpGet:
          path: /ready
          port: 8000
```

## DAPR Sidecar Configuration

```yaml
# docker-compose or K8s
plantation-model-dapr:
  command: [
    "./daprd",
    "-app-id", "plantation-model",
    "-app-port", "50051",           # gRPC service port
    "-app-protocol", "grpc",        # For service invocation
    "-dapr-grpc-port", "50001",     # DAPR proxy port
    "-components-path", "/components"
  ]
```

The `app-port` and `app-protocol` are for **service invocation** (other services calling PlantationService). Pub/sub uses streaming subscriptions which are outbound from your app.

## What We DON'T Do

| Anti-Pattern | Why It's Wrong |
|--------------|----------------|
| Extra port for pub/sub | Streaming subscriptions are outbound - no port needed |
| Manual `AppCallbackServicer` | SDK handles subscription protocol |
| FastAPI HTTP handlers for events | Use SDK streaming subscriptions |
| Worrying about `app-protocol` for pub/sub | SDK abstracts transport |

## Consequences

### Positive

- **Two ports only** - 8000 (health) and 50051 (gRPC API)
- **Clear separation** - Each component has one responsibility
- **SDK simplicity** - No manual DAPR protocol handling
- **DLQ in code** - `dead_letter_topic` parameter on subscribe

### Negative

- **Streaming model** - Different pattern than push-based
- **Connection lifecycle** - Must manage close functions

## Migration from Current State

Current services use FastAPI HTTP handlers for pub/sub events. Migration path:

1. Add `dapr` dependency (DaprClient)
2. Create subscriber module with `subscribe_with_handler()` calls
3. Move business logic from HTTP handlers to handler functions
4. Remove `/api/v1/events/*` endpoints from FastAPI
5. Remove extra port configurations

## Revisit Triggers

Re-evaluate this decision if:

1. **DAPR SDK changes** - May offer simpler patterns
2. **Push model needed** - May need `@app.subscribe()` with extra port

## PoC Validation

These patterns were validated in a standalone PoC: `tests/e2e/poc-dapr-patterns/`

Key learnings from the PoC:

| Learning | Details |
|----------|---------|
| **DAPR 1.14.0+ required** | Streaming subscriptions not available in earlier versions |
| **TopicEventResponse required** | Handler must return `TopicEventResponse("success"\|"retry"\|"drop")` |
| **message.data() returns dict** | No need for `json.loads()` - data is already parsed |
| **Two ports validated** | FastAPI 8000 + gRPC 50051 - no extra port for pub/sub |

Run the PoC:
```bash
cd tests/e2e/poc-dapr-patterns
docker compose up --build -d
python run_tests.py  # All 5 tests should pass
docker compose down -v
```

## References

- [DAPR Python SDK](https://docs.dapr.io/developing-applications/sdks/python/)
- [DAPR Subscription Types](https://docs.dapr.io/developing-applications/building-blocks/pubsub/subscription-methods/)
- [DAPR Service Invocation](https://docs.dapr.io/developing-applications/building-blocks/service-invocation/)
- Epic 0-4: Grading Validation
- Related: ADR-010 (DAPR Patterns), ADR-006 (Dead Letter Queue)
