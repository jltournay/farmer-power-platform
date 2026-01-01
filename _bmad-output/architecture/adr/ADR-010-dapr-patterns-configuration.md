# ADR-010: DAPR Patterns and Configuration Standards

**Status:** Accepted (Revised)
**Date:** 2025-12-31 (Revised: 2026-01-01)
**Deciders:** Winston (Architect), Amelia (Dev), Jeanlouistournay
**Related Stories:** Epic 0-4 (Grading Validation)
**Validated By:** PoC at `tests/e2e/poc-dapr-patterns/` (5/5 tests passing)

## Context

During E2E testing and development of Epic 0-4, we frequently encountered confusion about:
1. How to publish and subscribe to events
2. DAPR sidecar configuration
3. Dead letter queue setup

## Decision

**Use the DAPR Python SDK for all pub/sub operations. The SDK abstracts transport details (HTTP/gRPC) - we don't need to manage them manually.**

> **IMPORTANT:** Streaming subscriptions require **DAPR 1.14.0 or later**. Earlier versions do not support `subscribe_with_handler()`.

## DAPR Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DAPR MESH (always gRPC internally)               │
│                                                                          │
│   DAPR Sidecar A ◄────────── gRPC ──────────► DAPR Sidecar B            │
│         ▲                                           ▲                    │
│         │                                           │                    │
│    SDK handles                                 SDK handles               │
│    communication                               communication             │
│         │                                           │                    │
│         ▼                                           ▼                    │
│   Publisher Service                           Subscriber Service         │
│   DaprClient()                                @app.subscribe()           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key insight:** DAPR sidecars communicate via gRPC internally. The SDK handles sidecar-to-app communication - we don't specify `app-protocol` for pub/sub.

## Publishing Events

Use `DaprClient` from the SDK:

```python
from dapr.clients import DaprClient

async def publish_quality_result(document_id: str, grades: dict) -> None:
    """Publish quality result event."""
    with DaprClient() as client:
        client.publish_event(
            pubsub_name="pubsub",
            topic_name="collection.quality_result.received",
            data=json.dumps({
                "document_id": document_id,
                "grades": grades,
            }),
            data_content_type="application/json",
        )
```

## Subscribing to Events

Use **streaming subscriptions** with `subscribe_with_handler()` - your app connects outbound to the DAPR sidecar (no extra port needed):

```python
from dapr.clients import DaprClient
from dapr.clients.grpc._response import TopicEventResponse

def handle_quality_result(message) -> TopicEventResponse:
    """Handle quality result events.

    IMPORTANT:
    - message.data() returns a dict, NOT a JSON string
    - Must return TopicEventResponse, not None
    """
    # message.data() returns dict directly - no json.loads() needed!
    data = message.data()

    try:
        process_quality_result(data)
        return TopicEventResponse("success")  # Message processed
    except TransientError:
        return TopicEventResponse("retry")    # Retry the message
    except PermanentError:
        return TopicEventResponse("drop")     # Send to DLQ

async def start_subscriptions():
    """Start subscriptions during service startup."""
    client = DaprClient()

    close_fn = client.subscribe_with_handler(
        pubsub_name="pubsub",
        topic="collection.quality_result.received",
        handler_fn=handle_quality_result,
        dead_letter_topic="events.dlq",  # DLQ configured in code!
    )

    return close_fn  # Call this to stop subscription
```

## Why Streaming Subscriptions?

| Approach | Direction | Extra Port? | DLQ in Code? |
|----------|-----------|-------------|--------------|
| `@app.subscribe()` | DAPR pushes to app | Yes | No (YAML only) |
| `subscribe_with_handler()` | App pulls from DAPR | **No** | **Yes** |

## Event Error Handling

| Handler Return | Result |
|----------------|--------|
| `TopicEventResponse("success")` | Event processed successfully |
| `TopicEventResponse("retry")` | DAPR retries the message |
| `TopicEventResponse("drop")` | Event sent to `dead_letter_topic` |

> **Note:** The handler **must** return a `TopicEventResponse`. Raising exceptions also works (triggers retry), but explicit responses give more control.

## Dead Letter Queue Configuration

With streaming subscriptions, DLQ is configured **in code**:

```python
client.subscribe_with_handler(
    pubsub_name="pubsub",
    topic="collection.quality_result.received",
    handler_fn=handle_quality_result,
    dead_letter_topic="events.dlq",  # DLQ right here!
)
```

No external YAML needed for subscriptions when using streaming mode.

## Resiliency Policy

Configure retry behavior before dead-lettering:

```yaml
# deploy/dapr/components/resiliency.yaml
apiVersion: dapr.io/v1alpha1
kind: Resiliency
metadata:
  name: pubsub-resiliency
spec:
  policies:
    retries:
      eventRetry:
        policy: exponential
        maxRetries: 3
        duration: 1s
        maxInterval: 30s
  targets:
    components:
      pubsub:
        inbound:
          retry: eventRetry
```

## Port Reference (for gRPC Services)

These ports are for **service-to-service gRPC calls**, not pub/sub:

| Port | Protocol | Purpose |
|------|----------|---------|
| `3500` | HTTP | DAPR HTTP API (state, secrets, bindings) |
| `50001` | gRPC | DAPR gRPC proxy for service invocation |
| `50051` | gRPC | Your service's gRPC API (e.g., PlantationService) |

## Common Mistakes

| Mistake | Correct Approach |
|---------|------------------|
| Manually implementing `AppCallback` | Use `subscribe_with_handler()` |
| Using `@app.subscribe()` (needs extra port) | Use streaming `subscribe_with_handler()` |
| Worrying about `app-protocol` for pub/sub | SDK handles transport automatically |
| Creating HTTP/FastAPI handlers for events | Use SDK streaming subscriptions |

## Consequences

### Positive

- **Simple code** - SDK abstracts transport details
- **DLQ externalized** - Configuration separate from code
- **Consistent patterns** - Same approach across all services

### Negative

- **SDK dependency** - Must use DAPR Python SDK
- **Less control** - Transport details abstracted away

## PoC Validation

These patterns were validated in a standalone PoC: `tests/e2e/poc-dapr-patterns/`

| Test | Status | What It Validates |
|------|--------|-------------------|
| gRPC Service A Echo | ✅ Pass | gRPC service invocation |
| gRPC Service B Calculator | ✅ Pass | gRPC via DAPR proxy with `dapr-app-id` |
| Pub/Sub Success message | ✅ Pass | `subscribe_with_handler()` + `TopicEventResponse("success")` |
| Pub/Sub Retry behavior | ✅ Pass | `TopicEventResponse("retry")` triggers retry |
| Pub/Sub DLQ | ✅ Pass | `TopicEventResponse("drop")` sends to DLQ |

Run the PoC:
```bash
cd tests/e2e/poc-dapr-patterns
docker compose up --build -d
python run_tests.py
docker compose down -v
```

## References

- [DAPR Python SDK](https://docs.dapr.io/developing-applications/sdks/python/)
- [DAPR Subscription Types](https://docs.dapr.io/developing-applications/building-blocks/pubsub/subscription-methods/)
- [DAPR Dead Letter Topics](https://docs.dapr.io/developing-applications/building-blocks/pubsub/pubsub-deadletter/)
- Epic 0-4: Grading Validation
- Related: ADR-006 (Dead Letter Queue), ADR-011 (Service Architecture)
