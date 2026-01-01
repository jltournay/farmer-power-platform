# ADR-006: Event Delivery Guarantees and Dead Letter Queue

**Status:** Accepted (Revised)
**Date:** 2025-12-31 (Revised: 2026-01-01)
**Deciders:** Winston (Architect), Murat (TEA), Amelia (Dev), Jeanlouistournay
**Related Stories:** Epic 0-4 (Grading Validation)
**Validated By:** PoC at `tests/e2e/poc-dapr-patterns/` (DLQ test passing)

## Context

During E2E testing of Epic 0-4, we observed:
1. Old events with empty payloads retrying forever from Redis
2. Had to manually clear Redis and reload seed data
3. No visibility into failed events
4. No alerting when events fail

**Root causes identified:**
- No DAPR retry policy configured (infinite retries by default)
- Event handlers not returning proper status codes
- No dead letter queue configured
- No metrics for failed events

## Decision

**Implement production-ready event delivery using the DAPR Python SDK with declarative dead letter queue configuration and OpenTelemetry metrics.**

> **IMPORTANT:** Streaming subscriptions require **DAPR 1.14.0 or later** and **dapr Python SDK 1.14.0+**.

## Implementation

### 1. Event Handler with Streaming Subscriptions

Use `subscribe_with_handler()` for subscribing to events - your app connects outbound to DAPR (no extra port needed):

```python
from dapr.clients import DaprClient
from dapr.clients.grpc._response import TopicEventResponse
from opentelemetry import metrics
import structlog

logger = structlog.get_logger("plantation_model.events")
meter = metrics.get_meter("plantation-model")

processing_failures = meter.create_counter(
    name="event_processing_failures_total",
    description="Total events that failed processing",
)

def handle_quality_result(message) -> TopicEventResponse:
    """Handle quality result events with proper error handling.

    IMPORTANT:
    - message.data() returns a dict, NOT a JSON string
    - Must return TopicEventResponse
    """
    # message.data() returns dict directly - no json.loads() needed!
    data = message.data()
    document_id = data.get("document_id")

    try:
        # Check if processor is initialized
        if quality_processor is None:
            logger.error("Quality processor not initialized - will retry")
            processing_failures.add(1, {"topic": "quality_result", "error": "not_initialized"})
            return TopicEventResponse("retry")

        # Process the event
        quality_processor.process(data)
        logger.info("Quality result processed", document_id=document_id)
        return TopicEventResponse("success")

    except ValidationError as e:
        # Invalid data - send to DLQ (no point retrying)
        logger.error("Validation failed", error=str(e))
        processing_failures.add(1, {"topic": "quality_result", "error": "validation"})
        return TopicEventResponse("drop")  # Goes to DLQ

    except Exception as e:
        # Unexpected error - retry
        logger.exception("Unexpected error processing event")
        processing_failures.add(1, {"topic": "quality_result", "error": "unexpected"})
        return TopicEventResponse("retry")

async def start_subscriptions():
    """Start subscriptions during service startup."""
    client = DaprClient()

    close_fn = client.subscribe_with_handler(
        pubsub_name="pubsub",
        topic="collection.quality_result.received",
        handler_fn=handle_quality_result,
        dead_letter_topic="events.dlq",  # DLQ configured here!
    )

    return close_fn
```

### 2. Dead Letter Topic Configuration

With streaming subscriptions, DLQ is configured **in code** via the `dead_letter_topic` parameter:

```python
client.subscribe_with_handler(
    pubsub_name="pubsub",
    topic="collection.quality_result.received",
    handler_fn=handle_quality_result,
    dead_letter_topic="events.dlq",  # DLQ configured here!
)
```

No external subscription YAML files needed.

### 3. Resiliency Policy with Max Retries

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

### 4. Dead Letter Queue Handler

Subscribe to the DLQ topic to capture and store failed events:

```python
from dapr.clients import DaprClient
from dapr.clients.grpc._response import TopicEventResponse
from opentelemetry import metrics

meter = metrics.get_meter("plantation-model")
dlq_counter = meter.create_counter(
    name="event_dead_letter_total",
    description="Total events sent to dead letter queue",
)

def handle_dead_letter(message) -> TopicEventResponse:
    """Handle dead-lettered events for inspection and replay.

    IMPORTANT: message.data() returns a dict, NOT a JSON string.
    """
    # message.data() returns dict directly - no json.loads() needed!
    data = message.data()
    # Original topic info may be in metadata
    original_topic = message.topic() if hasattr(message, 'topic') else "unknown"

    # Increment metric for alerting
    dlq_counter.add(1, {"topic": original_topic})

    # Store in MongoDB for inspection/replay (sync version shown)
    dlq_collection.insert_one({
        "event": data,
        "received_at": datetime.utcnow(),
        "original_topic": original_topic,
        "status": "pending_review",
    })

    logger.error(
        "Event dead-lettered",
        topic=original_topic,
    )

    return TopicEventResponse("success")

async def start_dlq_subscription():
    """Start DLQ subscription during service startup."""
    client = DaprClient()

    close_fn = client.subscribe_with_handler(
        pubsub_name="pubsub",
        topic="events.dlq",
        handler_fn=handle_dead_letter,
    )

    return close_fn
```

### 5. Required Metrics for OpenTelemetry Alerting

| Metric | Type | Labels | Alert Threshold |
|--------|------|--------|-----------------|
| `event_dead_letter_total` | Counter | `topic` | Any increment |
| `event_processing_failures_total` | Counter | `topic`, `error` | > 5 per minute |
| `event_processing_duration_seconds` | Histogram | `topic` | p99 > 10s |

## Event Response Semantics (Streaming Subscriptions)

| Handler Return | DAPR Behavior |
|----------------|---------------|
| `TopicEventResponse("success")` | Event processed successfully, removed from queue |
| `TopicEventResponse("retry")` | Retry according to resiliency policy |
| `TopicEventResponse("drop")` | Send to `dead_letter_topic` immediately |

> **Note:** The handler **must** return a `TopicEventResponse`. Raising exceptions also triggers retry, but explicit responses give more control over the retry/DLQ decision.

## DLQ MongoDB Schema

```javascript
// Collection: event_dead_letter
{
  "_id": ObjectId,
  "event": {
    "id": "uuid",
    "data": { ... },
    "source": "collection-model",
    "time": "2024-12-31T10:00:00Z"
  },
  "original_topic": "collection.quality_result.received",
  "received_at": ISODate,
  "status": "pending_review" | "replayed" | "discarded",
  "replayed_at": ISODate | null,
  "discard_reason": String | null
}
```

## Consequences

### Positive

- **Bounded retries** - No more infinite retry loops
- **Visibility** - Failed events visible in DLQ collection
- **Alerting** - OpenTelemetry metrics trigger alerts
- **Replay capability** - Can replay DLQ events after fix
- **SDK simplicity** - No manual HTTP/gRPC handling

### Negative

- **Additional complexity** - DLQ handler and collection to maintain
- **Storage growth** - DLQ events accumulate in MongoDB

## Revisit Triggers

Re-evaluate this decision if:

1. **DLQ volume too high** - May need auto-discard for known-bad events
2. **Replay needed frequently** - May need automated replay tooling
3. **Different retry strategies** - May need per-topic configuration

## PoC Validation

The DLQ pattern was validated in a standalone PoC: `tests/e2e/poc-dapr-patterns/`

| Test | Status | What It Validates |
|------|--------|-------------------|
| Pub/Sub DLQ | ✅ Pass | `TopicEventResponse("drop")` sends message to `dead_letter_topic` |

Key learnings:
- **DAPR 1.14.0+ required** for streaming subscriptions
- **message.data() returns dict** - no `json.loads()` needed
- **TopicEventResponse required** - handler must return explicit response
- **DLQ in code** - `dead_letter_topic` parameter on `subscribe_with_handler()`

Run the PoC:
```bash
cd tests/e2e/poc-dapr-patterns
docker compose up --build -d
python run_tests.py --test dlq  # DLQ test should pass
docker compose down -v
```

## References

- [DAPR Dead Letter Topics](https://docs.dapr.io/developing-applications/building-blocks/pubsub/pubsub-deadletter/)
- [DAPR Resiliency Policies](https://docs.dapr.io/operations/resiliency/policies/)
- [DAPR Python SDK](https://docs.dapr.io/developing-applications/sdks/python/)
- [DAPR Subscription Types](https://docs.dapr.io/developing-applications/building-blocks/pubsub/subscription-methods/)
- Epic 0-4: Grading Validation
- Related: ADR-010 (DAPR Patterns), ADR-011 (Service Architecture)
