# ADR-008: Invalid Linkage Field Handling with Metrics

**Status:** Accepted
**Date:** 2025-12-31
**Deciders:** Winston (Architect), Murat (TEA), Amelia (Dev), Jeanlouistournay
**Related Stories:** Epic 0-4 (Grading Validation)

## Context

When Plantation Model receives quality events, the document may contain invalid linkage fields:
- `farmer_id` - Farmer doesn't exist in Plantation Model
- `factory_id` - Factory doesn't exist
- `grading_model_id` - Grading model doesn't exist
- `region_id` - Region doesn't exist

**Current behavior (inconsistent):**

| Field | Current Behavior | Problem |
|-------|------------------|---------|
| `grading_model_id` missing | ✅ Raises exception | OK |
| `grading_model` not found | ✅ Raises exception | OK |
| `farmer_id` not found | ⚠️ Logs warning, skips | Silent data loss |
| `factory_id` not found | ⚠️ Returns "unknown" | Invalid data saved |
| `region_id` not found | ❌ Not validated | Not checked |

## Decision

**All invalid linkage fields MUST raise an exception with a metric for OpenTelemetry alerting.** Combined with ADR-006's DLQ, invalid events will:

1. Fail with exception (return 500 RETRY)
2. Increment validation failure metric
3. Retry 3 times (per ADR-006 resiliency policy)
4. Go to dead letter queue
5. Trigger alert in OpenTelemetry

## Alternatives Considered

| Option | Description | Verdict |
|--------|-------------|---------|
| Skip silently | Log warning, continue | Rejected: Data loss |
| Save with "unknown" | Store placeholder | Rejected: Invalid data |
| **Exception + Metric** | Fail fast, alert via DLQ | **Selected** |

## Implementation

### 1. Validation Metrics

```python
from opentelemetry import metrics

meter = metrics.get_meter("plantation-model")

linkage_validation_failures = meter.create_counter(
    name="event_linkage_validation_failures_total",
    description="Total events with invalid linkage fields",
    unit="1",
)
```

### 2. Validate All Linkage Fields

```python
async def process(self, document_id: str, farmer_id: str, ...) -> dict[str, Any]:
    # Validate farmer exists
    farmer = await self._farmer_repo.get_by_id(farmer_id)
    if farmer is None:
        linkage_validation_failures.add(1, {"field": "farmer_id", "error": "not_found"})
        raise QualityEventProcessingError(
            f"Farmer not found: {farmer_id}",
            document_id=document_id,
            error_type="farmer_not_found",
        )

    # Validate grading_model exists
    grading_model = await self._load_grading_model(grading_model_id, version)
    if grading_model is None:
        linkage_validation_failures.add(1, {"field": "grading_model_id", "error": "not_found"})
        raise QualityEventProcessingError(...)

    # Validate factory exists
    factory = await self._factory_repo.get_by_id(factory_id)
    if factory is None:
        linkage_validation_failures.add(1, {"field": "factory_id", "error": "not_found"})
        raise QualityEventProcessingError(...)

    # Validate region exists (via farmer's region_id)
    if farmer.region_id:
        region = await self._region_repo.get_by_id(farmer.region_id)
        if region is None:
            linkage_validation_failures.add(1, {"field": "region_id", "error": "not_found"})
            raise QualityEventProcessingError(...)
```

### 3. Error Types for Metrics

| Error Type | Metric Labels | Description |
|------------|---------------|-------------|
| `farmer_not_found` | `field=farmer_id, error=not_found` | Farmer ID doesn't exist |
| `factory_not_found` | `field=factory_id, error=not_found` | Factory ID doesn't exist |
| `grading_model_not_found` | `field=grading_model_id, error=not_found` | Grading model doesn't exist |
| `missing_grading_model` | `field=grading_model_id, error=missing` | Document missing grading_model_id |
| `region_not_found` | `field=region_id, error=not_found` | Region ID doesn't exist |

### 4. OpenTelemetry Alert Configuration

```yaml
# Prometheus alerting rule
groups:
  - name: linkage-validation
    rules:
      - alert: LinkageValidationFailures
        expr: increase(event_linkage_validation_failures_total[5m]) > 0
        for: 0m
        labels:
          severity: warning
        annotations:
          summary: "Event linkage validation failures"
          description: "{{ $value }} events failed validation for {{ $labels.field }}"

      - alert: HighLinkageFailureRate
        expr: rate(event_linkage_validation_failures_total[5m]) > 1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High rate of linkage validation failures"
```

## Consequences

### Positive

- **No silent data loss** - All invalid linkage caught
- **Observable** - Metrics enable alerting
- **Debuggable** - DLQ contains full event for investigation
- **Consistent** - All linkage fields treated the same

### Negative

- **Events may fail initially** - If master data not yet loaded
- **Requires master data sync** - Farmer, Factory, Region must exist before events

## Event Flow with Invalid Linkage

```
Event received
    │
    ▼
Validate farmer_id ──NOT FOUND──► Metric + Exception
    │                                    │
    ▼                                    ▼
Validate grading_model ─NOT FOUND─► Metric + Exception
    │                                    │
    ▼                                    ▼
Validate factory_id ──NOT FOUND──► Metric + Exception
    │                                    │
    ▼                                    ▼
Process event                     Return 500 RETRY
    │                                    │
    ▼                                    ▼
Return 200 SUCCESS              DAPR retries (3x)
                                         │
                                         ▼
                                   Dead Letter Queue
                                         │
                                         ▼
                                   Alert triggered
```

## Revisit Triggers

Re-evaluate this decision if:

1. **Too many false positives** - May need eventual consistency delay
2. **Master data sync issues** - May need separate validation queue
3. **Performance impact** - May need cached validation

## References

- Epic 0-4: Grading Validation
- Related: ADR-006 (Event Delivery - DLQ handles failed events)
- Requires: `FarmerRepository`, `FactoryRepository`, `RegionRepository`
