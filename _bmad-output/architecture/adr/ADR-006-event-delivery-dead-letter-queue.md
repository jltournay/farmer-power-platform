# ADR-006: Event Delivery Guarantees and Dead Letter Queue

**Status:** Accepted
**Date:** 2025-12-31
**Deciders:** Winston (Architect), Murat (TEA), Amelia (Dev), Jeanlouistournay
**Related Stories:** Epic 0-4 (Grading Validation)

## Context

During E2E testing of Epic 0-4, we observed:
1. Old events with empty payloads retrying forever from Redis
2. Had to manually clear Redis and reload seed data
3. No visibility into failed events
4. No alerting when events fail

**Root causes identified:**
- No DAPR retry policy configured (infinite retries by default)
- Event handlers return 200 SUCCESS when not initialized (silent drop)
- No dead letter queue configured
- No metrics for failed events

## Decision

**Implement production-ready event delivery with DAPR dead letter queues and OpenTelemetry metrics.**

## Alternatives Considered

| Option | Description | Verdict |
|--------|-------------|---------|
| Application-level retry | Handle retries in app code | Rejected: Duplicates DAPR |
| Infinite retry | Keep retrying forever | Rejected: Blocks queue |
| **DAPR DLQ + Metrics** | Max retries then DLQ with alerting | **Selected** |

## Implementation

### 1. Declarative Subscriptions with Dead Letter Topic

Replace programmatic `/dapr/subscribe` with declarative YAML:

```yaml
# deploy/dapr/subscriptions/plantation-model.yaml
apiVersion: dapr.io/v2alpha1
kind: Subscription
metadata:
  name: quality-result-subscription
spec:
  topic: collection.quality_result.received
  routes:
    default: /api/v1/events/quality-result
  pubsubname: pubsub
  deadLetterTopic: events.dlq
---
apiVersion: dapr.io/v2alpha1
kind: Subscription
metadata:
  name: weather-updated-subscription
spec:
  topic: weather.observation.updated
  routes:
    default: /api/v1/events/weather-updated
  pubsubname: pubsub
  deadLetterTopic: events.dlq
```

### 2. Resiliency Policy with Max Retries

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

### 3. Dead Letter Queue Handler with Metrics

```python
# plantation_model/api/event_handlers/dlq_handler.py
from opentelemetry import metrics

meter = metrics.get_meter("plantation-model")
dlq_counter = meter.create_counter(
    name="event_dead_letter_total",
    description="Total events sent to dead letter queue",
    unit="1",
)

@app.post("/api/v1/events/dlq")
async def handle_dead_letter(request: Request):
    body = await request.json()
    original_topic = body.get("topic", "unknown")

    # Increment metric for alerting
    dlq_counter.add(1, {"topic": original_topic})

    # Store in MongoDB for inspection/replay
    await dlq_collection.insert_one({
        "event": body,
        "received_at": datetime.utcnow(),
        "original_topic": original_topic,
        "status": "pending_review",
    })

    logger.error(
        "Event dead-lettered",
        topic=original_topic,
        event_id=body.get("id"),
    )

    return {"status": "SUCCESS"}
```

### 4. Required Metrics for OpenTelemetry Alerting

| Metric | Type | Labels | Alert Threshold |
|--------|------|--------|-----------------|
| `event_dead_letter_total` | Counter | `topic` | Any increment |
| `event_processing_failures_total` | Counter | `topic`, `error_type` | > 5 per minute |
| `event_processing_duration_seconds` | Histogram | `topic` | p99 > 10s |
| `event_handler_not_ready_total` | Counter | `handler` | Any increment |

### 5. Fix Handler Initialization Bug

```python
# BEFORE (BUG - silent drop)
if quality_event_processor is None:
    return Response(status_code=200, content='{"status": "SUCCESS"}')

# AFTER (correct - will retry then DLQ)
if quality_event_processor is None:
    handler_not_ready_counter.add(1, {"handler": "quality_result"})
    logger.error("Quality event processor not initialized - returning RETRY")
    return Response(status_code=500, content='{"status": "RETRY"}')
```

## Consequences

### Positive

- **Bounded retries** - No more infinite retry loops
- **Visibility** - Failed events visible in DLQ collection
- **Alerting** - OpenTelemetry metrics trigger alerts
- **Replay capability** - Can replay DLQ events after fix

### Negative

- **Additional complexity** - DLQ handler and collection to maintain
- **Storage growth** - DLQ events accumulate in MongoDB

## Event Response Codes (Reference)

| Handler Response | DAPR Behavior |
|------------------|---------------|
| `200` + `SUCCESS` | Event processed, removed from queue |
| `200` + `DROP` | Event dropped (warning logged), removed |
| `500` or non-200 | Retry according to resiliency policy |
| Retries exhausted (3x) | Send to `deadLetterTopic` |

## DLQ MongoDB Schema

```javascript
// Collection: event_dead_letter
{
  "_id": ObjectId,
  "event": {
    "id": "uuid",
    "topic": "collection.quality_result.received",
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

## Revisit Triggers

Re-evaluate this decision if:

1. **DLQ volume too high** - May need auto-discard for known-bad events
2. **Replay needed frequently** - May need automated replay tooling
3. **Different retry strategies** - May need per-topic configuration

## References

- [DAPR Dead Letter Topics](https://docs.dapr.io/developing-applications/building-blocks/pubsub/pubsub-deadletter/)
- [DAPR Resiliency Policies](https://docs.dapr.io/operations/resiliency/policies/)
- Epic 0-4: Grading Validation
- Related: ADR-004 (Type Safety), ADR-005 (gRPC Retry)
