# Story 1.7: Quality Grading Event Subscription

**Status:** ready-for-dev
**GitHub Issue:** <!-- To be created -->

---

## Story

As a **factory quality manager**,
I want farmer performance metrics updated automatically when grading results arrive from the QC Analyzer,
So that I can see real-time quality trends without manual data entry.

---

## Context: Continuation of Story 1-4

This story implements the **Event subscription** that was explicitly excluded from Story 1-4:

> **What This Story Does NOT Include:**
> | Event subscription | Collection Model doesn't exist yet | Epic 2 |

Now that Epic 2 is complete:
- Collection Model emits `collection.quality_result.received` events via DAPR Pub/Sub
- Story 1-4 created `GradingModel` and `FarmerPerformance` domain models
- Story 1-4 created repositories for both entities
- This story connects them via event-driven updates

---

## Key Design Decision: No Recalculation

**The QC Analyzer (Starfish machine) already calculates the grade.** The quality document contains:
- `classification`: "primary" or "secondary" (the pre-calculated grade)
- `leaf_type_distribution`: counts per leaf type (for attribute tracking)

**Plantation Model does NOT recalculate the grade.** It simply:
1. Extracts the `classification` from the document
2. Extracts `leaf_type_distribution` for performance tracking
3. Updates `FarmerPerformance.today` metrics
4. Emits domain event for downstream consumers

The `GradingModel` is used only for:
- Display label mapping (if needed)
- Knowing attribute structure for proper tracking

---

## Acceptance Criteria

1. **Given** a `collection.quality_result.received` event is received from Collection Model
   **When** the Plantation Model processes the event
   **Then** the quality document is retrieved from Collection MCP using the `document_id`
   **And** the `classification` (pre-calculated grade) is extracted from `bag_summary`

2. **Given** quality data contains `classification` and `leaf_type_distribution`
   **When** the farmer's performance is updated
   **Then** `FarmerPerformance.today` is updated with:
   - `deliveries` incremented by 1
   - `total_kg` incremented (if `total_weight_kg` available)
   - `grade_counts[classification]` incremented by 1
   - `attribute_counts` updated with leaf type distribution
   - `last_delivery` timestamp updated

3. **Given** the performance update is complete
   **When** downstream services need notification
   **Then** a `plantation.quality.graded` event is emitted via DAPR Pub/Sub
   **And** the event payload includes: `farmer_id`, `document_id`, `classification`, `graded_at`

4. **Given** it's the first delivery of a new day
   **When** the performance is updated
   **Then** `FarmerPerformance.today` is reset before applying the update

5. **Given** invalid or incomplete quality data is received (missing classification, farmer not found)
   **When** processing fails
   **Then** the event is logged with error details
   **And** the farmer's record is NOT updated
   **And** metrics are emitted for monitoring

---

## Tasks / Subtasks

- [ ] **Task 1: Create DAPR Pub/Sub subscription handler** (AC: #1)
  - [ ] 1.1 Create `api/event_handlers/quality_result_handler.py`
  - [ ] 1.2 Implement DAPR subscription endpoint for `collection.quality_result.received`
  - [ ] 1.3 Parse event payload: `document_id`, `plantation_id`, `batch_timestamp`
  - [ ] 1.4 Add OpenTelemetry tracing for event processing
  - [ ] 1.5 Register subscription in DAPR component config

- [ ] **Task 2: Create Collection MCP client** (AC: #1)
  - [ ] 2.1 Create `infrastructure/clients/collection_mcp_client.py`
  - [ ] 2.2 Implement `get_document(document_id)` via gRPC to Collection MCP
  - [ ] 2.3 Handle connection errors and timeouts gracefully
  - [ ] 2.4 Add retry logic with exponential backoff

- [ ] **Task 3: Implement performance update service** (AC: #2, #4)
  - [ ] 3.1 Create `domain/services/performance_update_service.py`
  - [ ] 3.2 Implement `update_today_metrics(farmer_id, classification, leaf_type_distribution, weight_kg)`
  - [ ] 3.3 Handle date rollover (reset `today` when date changes)
  - [ ] 3.4 Use atomic MongoDB update with `$inc` for counters
  - [ ] 3.5 Handle farmer not found (log warning, skip update)

- [ ] **Task 4: Implement domain event emission** (AC: #3)
  - [ ] 4.1 Add `plantation.quality.graded` to domain event registry
  - [ ] 4.2 Create event payload model in `domain/events/quality_graded.py`
  - [ ] 4.3 Emit event via `DaprEventPublisher` after performance update
  - [ ] 4.4 Include: `farmer_id`, `document_id`, `classification`, `graded_at`

- [ ] **Task 5: Implement error handling** (AC: #5)
  - [ ] 5.1 Define `QualityEventProcessingError` exception class
  - [ ] 5.2 Handle: document not found, farmer not found, missing classification
  - [ ] 5.3 Log errors with full context (document_id, farmer_id, error details)
  - [ ] 5.4 Emit failure metrics: `plantation.quality_event.failed`
  - [ ] 5.5 Return appropriate DAPR acknowledgment (SUCCESS, RETRY, DROP)

- [ ] **Task 6: Write unit tests** (AC: #1-5)
  - [ ] 6.1 Test event handler parses payload correctly
  - [ ] 6.2 Test performance update increments counters correctly
  - [ ] 6.3 Test date rollover resets today metrics
  - [ ] 6.4 Test domain event is emitted with correct payload
  - [ ] 6.5 Test error cases: missing document, missing farmer, missing classification

- [ ] **Task 7: Integration test with mock DAPR** (AC: #1-5)
  - [ ] 7.1 Create integration test simulating full event flow
  - [ ] 7.2 Use mock Collection MCP client
  - [ ] 7.3 Verify MongoDB updates are correct
  - [ ] 7.4 Verify domain event is published

---

## Dev Notes

### Service Location

All code goes in the existing Plantation Model service:

```
services/plantation-model/
├── src/plantation_model/
│   ├── api/
│   │   └── event_handlers/
│   │       └── quality_result_handler.py      # NEW - DAPR subscription
│   ├── domain/
│   │   ├── services/
│   │   │   └── performance_update_service.py  # NEW - Performance updates
│   │   └── events/
│   │       └── quality_graded.py              # NEW - Domain event model
│   └── infrastructure/
│       └── clients/
│           └── collection_mcp_client.py       # NEW - Collection MCP client
└── ...
```

### Simplified Event Flow

```
┌─────────────────────────┐
│  QC Analyzer (Starfish) │
│  - Analyzes tea leaves  │
│  - Calculates grade     │
│  - Outputs JSON         │
└───────────┬─────────────┘
            │ Blob upload
            ▼
┌─────────────────────────┐
│  Collection Model       │
│  (Epic 2)               │
│  - Stores document      │
│  - Emits event          │
└───────────┬─────────────┘
            │ DAPR Pub/Sub
            │ topic: collection.quality_result.received
            │ payload: {document_id, plantation_id, batch_timestamp}
            ▼
┌─────────────────────────┐
│  Plantation Model       │
│  (This Story)           │
│                         │
│  1. Receive event       │
│  2. Get doc from        │
│     Collection MCP      │
│  3. Extract:            │
│     - classification    │  ← Pre-calculated by QC Analyzer
│     - leaf_type_dist    │  ← For attribute tracking
│     - weight_kg         │
│  4. Update farmer's     │
│     today metrics       │
│  5. Emit graded event   │
└───────────┬─────────────┘
            │ DAPR Pub/Sub
            │ topic: plantation.quality.graded
            ▼
┌─────────────────────────┐
│  Downstream Services    │
│  (Knowledge Model,      │
│   Notification Model)   │
└─────────────────────────┘
```

### DAPR Subscription Configuration

```yaml
# deploy/dapr/components/subscription-quality-result.yaml
apiVersion: dapr.io/v2alpha1
kind: Subscription
metadata:
  name: quality-result-subscription
spec:
  pubsubname: collection-events
  topic: collection.quality_result.received
  routes:
    default: /api/v1/events/quality-result
  scopes:
    - plantation-model
```

### Event Payload from Collection Model

From `config/source-configs/qc-analyzer-result.yaml`:
```yaml
events:
  on_success:
    topic: collection.quality_result.received
    payload_fields:
      - document_id
      - plantation_id    # Maps to farmer_id
      - batch_timestamp
```

### Quality Document Structure (from Collection MCP)

The document retrieved from Collection MCP contains the **pre-calculated grade**:
```python
{
    "document_id": "doc-abc123",
    "source_id": "qc-analyzer-result",
    "extracted_fields": {
        "plantation_id": "WM-4521",         # farmer_id
        "factory_id": "factory-001",
        "grading_model_id": "tbk_kenya_tea_v1",
        "grading_model_version": "1.0.0",
        "bag_summary": {
            "total_weight_kg": 25.5,
            "classification": "primary",     # ← ALREADY CALCULATED BY QC ANALYZER
            "leaf_type_distribution": {      # ← For attribute tracking
                "bud": 15,
                "one_leaf_bud": 45,
                "two_leaves_bud": 50,
                "three_plus_leaves_bud": 10,
                "coarse_leaf": 15,
                "banji": 5
            },
            "grade_details": {...}
        }
    }
}
```

### Event Handler - Simple Extraction

```python
# api/event_handlers/quality_result_handler.py
from fastapi import APIRouter
from dapr.ext.fastapi import DaprApp

router = APIRouter()
dapr_app = DaprApp()


@dapr_app.subscribe(pubsub="collection-events", topic="collection.quality_result.received")
async def handle_quality_result(event: dict) -> dict:
    """Handle quality result event from Collection Model.

    Simply extracts pre-calculated grade and updates farmer performance.
    No grade recalculation - QC Analyzer already did that.
    """
    document_id = event["document_id"]
    farmer_id = event["plantation_id"]  # plantation_id = farmer_id

    # 1. Get full document from Collection MCP
    document = await collection_mcp_client.get_document(document_id)

    # 2. Extract pre-calculated data (NO recalculation)
    bag_summary = document["extracted_fields"]["bag_summary"]
    classification = bag_summary["classification"]  # "primary" or "secondary"
    leaf_type_distribution = bag_summary["leaf_type_distribution"]
    weight_kg = bag_summary.get("total_weight_kg")

    # 3. Update farmer's today metrics
    await performance_update_service.update_today_metrics(
        farmer_id=farmer_id,
        classification=classification,
        leaf_type_distribution=leaf_type_distribution,
        weight_kg=weight_kg,
    )

    # 4. Emit domain event
    await event_publisher.publish(
        topic="plantation.quality.graded",
        payload={
            "farmer_id": farmer_id,
            "document_id": document_id,
            "classification": classification,
            "graded_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    return {"status": "SUCCESS"}
```

### Performance Update - Atomic MongoDB Operations

```python
# domain/services/performance_update_service.py
from datetime import date, datetime, timezone


async def update_today_metrics(
    db: AsyncIOMotorDatabase,
    farmer_id: str,
    classification: str,
    leaf_type_distribution: dict[str, int],
    weight_kg: float | None = None,
) -> None:
    """Update farmer's today metrics atomically.

    Uses MongoDB $inc for atomic counter updates.
    Handles date rollover automatically.

    Args:
        farmer_id: The farmer who delivered
        classification: Pre-calculated grade from QC Analyzer ("primary"/"secondary")
        leaf_type_distribution: Leaf type counts for attribute tracking
        weight_kg: Weight of delivery (optional)
    """
    today = date.today().isoformat()
    now = datetime.now(timezone.utc)

    # Build atomic update
    update = {
        "$inc": {
            "today.deliveries": 1,
            f"today.grade_counts.{classification}": 1,
        },
        "$set": {
            "today.last_delivery": now,
            "today.date": today,
            "updated_at": now,
        },
    }

    # Add weight if available
    if weight_kg:
        update["$inc"]["today.total_kg"] = weight_kg

    # Add attribute counts for trend analysis
    for leaf_type, count in leaf_type_distribution.items():
        update["$inc"][f"today.attribute_counts.leaf_type.{leaf_type}"] = count

    # Atomic update with date check
    result = await db["farmer_performance"].update_one(
        {
            "farmer_id": farmer_id,
            "today.date": today,  # Only if same day
        },
        update,
    )

    # Handle date rollover (first delivery of new day)
    if result.matched_count == 0:
        # Reset today and apply update
        await db["farmer_performance"].update_one(
            {"farmer_id": farmer_id},
            {
                "$set": {
                    "today": {
                        "deliveries": 1,
                        "total_kg": weight_kg or 0,
                        "grade_counts": {classification: 1},
                        "attribute_counts": {"leaf_type": leaf_type_distribution},
                        "last_delivery": now,
                        "date": today,
                    },
                    "updated_at": now,
                },
            },
        )
```

### Domain Event: plantation.quality.graded

Add to `libs/fp-common/fp_common/models/domain_events.py`:
```python
class PlantationEventTopic(str, Enum):
    """Valid Plantation Model event topics."""

    # Farmer events
    FARMER_REGISTERED = "plantation.farmer.registered"
    FARMER_UPDATED = "plantation.farmer.updated"

    # Quality events (NEW)
    QUALITY_GRADED = "plantation.quality.graded"
```

Event payload model:
```python
# domain/events/quality_graded.py
from datetime import datetime
from pydantic import BaseModel, Field


class QualityGradedEvent(BaseModel):
    """Payload for plantation.quality.graded event."""

    farmer_id: str = Field(description="Farmer who delivered the tea")
    document_id: str = Field(description="Original document from Collection Model")
    classification: str = Field(description="Grade from QC Analyzer (primary/secondary)")
    graded_at: datetime = Field(description="When event was processed")

    # Optional enrichment
    weight_kg: float | None = Field(default=None, description="Weight if available")
    factory_id: str | None = Field(default=None, description="Factory ID")
```

### Critical Implementation Rules

**From project-context.md:**

1. **ALL I/O operations MUST be async** - Event handler, MCP client, MongoDB updates
2. **Use DAPR for inter-service communication** - Collection MCP via DAPR Service Invocation
3. **Use DAPR Pub/Sub for events** - Both subscription and emission
4. **No grade recalculation** - QC Analyzer already calculated the grade
5. **Atomic MongoDB updates** - Use `$inc` to avoid race conditions

### Testing Strategy

**Unit Tests (`tests/unit/plantation/`):**
- `test_performance_update_service.py` - Update logic, date rollover
- `test_quality_result_handler.py` - Event parsing, error handling

**Integration Tests (`tests/integration/`):**
- `test_quality_event_flow.py` - Full flow with mock DAPR

### OpenTelemetry Metrics

```python
# Metrics to emit
plantation.quality_event.processed{classification="primary"}  # Counter
plantation.quality_event.processed{classification="secondary"}  # Counter
plantation.quality_event.failed{reason="document_not_found"}  # Counter
plantation.quality_event.latency_ms  # Histogram
```

### References

- [Source: _bmad-output/sprint-artifacts/1-4-farmer-performance-history-structure.md] - FarmerPerformance model
- [Source: config/source-configs/qc-analyzer-result.yaml] - Event topic and payload
- [Source: libs/fp-common/fp_common/models/domain_events.py] - Domain event registry
- [Source: _bmad-output/architecture/collection-model-architecture.md] - Collection Model event emission
- [Source: _bmad-output/project-context.md] - Critical rules

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
