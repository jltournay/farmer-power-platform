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

## Key Design Decision: Model-Driven, Leaf-Level Classification

### Leaf-Level Classification

**The QC Analyzer (Starfish machine) classifies INDIVIDUAL LEAVES, not bags.** Each leaf is sorted into grade bins defined by the `GradingModel`. The quality document contains:
- Grade counts for each label defined in the grading model (e.g., `primary`, `secondary`)
- `attribute_distribution`: detailed counts per attribute with confidence scores

**There is no single bag classification.** A bag contains leaves of MULTIPLE grades. The QC Analyzer output reports the distribution.

### Model-Driven Design (CRITICAL)

**The code MUST NOT hardcode grade labels.** The `GradingModel` entity is the **single source of truth** for:
- `grade_labels`: The list of valid grade labels (e.g., `["primary", "secondary"]`)
- `attributes_list`: The list of attributes to track (e.g., `["leaf_type", "coarse_subtype", "banji_hardness"]`)

**Why this matters:**
- Different markets have different grading schemes (Kenya: primary/secondary, Rwanda: A/B/C, etc.)
- Changing the grading model configuration should NOT require code changes
- The Plantation Model reads labels from `GradingModel` at runtime

**Plantation Model processing:**
1. Load `GradingModel` using `grading_model_id` from the document
2. Get `grade_labels` from the grading model (e.g., `["primary", "secondary"]`)
3. Extract counts for EACH label dynamically from the QC output
4. Update `FarmerPerformance.today.grade_counts[label]` for each label
5. Emit domain event with grade counts

---

## Acceptance Criteria

1. **Given** a `collection.quality_result.received` event is received from Collection Model
   **When** the Plantation Model processes the event
   **Then** the quality document is retrieved from Collection MCP using the `document_id`
   **And** the `GradingModel` is loaded using both `grading_model_id` AND `grading_model_version` from the document
   **And** grade counts are extracted for each label in `grading_model.grade_labels`

2. **Given** quality data contains grade counts and `attribute_distribution`
   **When** the farmer's performance is updated
   **Then** `FarmerPerformance.today` is updated with:
   - `deliveries` incremented by 1
   - `total_kg` incremented (if `total_weight_kg` available)
   - `grade_counts[label]` incremented by the count for EACH label from the grading model
   - `attribute_counts` updated with attribute distribution (dynamically from `grading_model.attributes_list`)
   - `last_delivery` timestamp updated

   **Note:** `total_weight_kg` is optional - QC Analyzer currently has no scale. Field kept for future scale integration and bonus calculations.

3. **Given** the performance update is complete
   **When** downstream services need notification
   **Then** a `plantation.quality.graded` event is emitted via DAPR Pub/Sub
   **And** the event payload includes: `farmer_id`, `document_id`, `grade_counts` (dict), `attribute_distribution` (dict), `timestamp`

4. **Given** the performance update is complete
   **When** the Engagement Model needs historical context
   **Then** a `plantation.performance_updated` event is emitted via DAPR Pub/Sub
   **And** the event payload includes computed summary:
   - `farmer_id`, `factory_id`, `timestamp`
   - `primary_percentage` (computed from today's grade_counts)
   - `improvement_trend` (improving/stable/declining)
   - `today` summary (deliveries, grade_counts)
   - `triggered_by_document_id` (for traceability)

   **Note:** NO `current_category` field - Engagement Model owns WIN/WATCH/WORK/WARN vocabulary and computes category from `primary_percentage` + factory thresholds.

5. **Given** it's the first delivery of a new day
   **When** the performance is updated
   **Then** `FarmerPerformance.today` is reset before applying the update

6. **Given** invalid or incomplete quality data is received (missing grade counts, farmer not found, grading model not found)
   **When** processing fails
   **Then** the event is logged with error details
   **And** the farmer's record is NOT updated
   **And** metrics are emitted for monitoring

---

## Tasks / Subtasks

- [ ] **Task 0: Add quality thresholds to Factory entity** (Prerequisite for Engagement Model)
  - [ ] 0.1 Create `QualityThresholds` value object in `domain/models/value_objects.py`:
    ```python
    class QualityThresholds(BaseModel):
        """Factory-configurable quality thresholds.

        NEUTRAL NAMING: tier_1, tier_2, tier_3 (NOT WIN/WATCH/WORK)
        Engagement Model maps these to engagement categories.
        Factory Admin UI shows as: Premium/Standard/Acceptable/Below Standard.
        """
        tier_1: float = Field(default=85.0, ge=0, le=100, description="Premium tier threshold (≥X% Primary)")
        tier_2: float = Field(default=70.0, ge=0, le=100, description="Standard tier threshold (≥X% Primary)")
        tier_3: float = Field(default=50.0, ge=0, le=100, description="Acceptable tier threshold (≥X% Primary)")
        # Below tier_3 = Below Standard (auto-calculated)
    ```
  - [ ] 0.2 Add `quality_thresholds: QualityThresholds` field to `Factory` entity in `domain/models/factory.py`
  - [ ] 0.3 Add `quality_thresholds` to `FactoryCreate` and `FactoryUpdate` models
  - [ ] 0.4 Update gRPC service to handle quality_thresholds field
  - [ ] 0.5 Update MCP server's `get_factory` tool to include quality_thresholds in response
  - [ ] 0.6 Add unit tests for threshold validation (tier_1 > tier_2 > tier_3)

- [ ] **Task 1: Create DAPR Pub/Sub subscription handler** (AC: #1)
  - [ ] 1.1 Create `api/event_handlers/quality_result_handler.py`
  - [ ] 1.2 Implement DAPR subscription endpoint for `collection.quality_result.received`
  - [ ] 1.3 Parse event payload: `document_id`, `plantation_id`, `batch_timestamp`
  - [ ] 1.4 Add OpenTelemetry tracing for event processing
  - [ ] 1.5 Register subscription in DAPR component config

- [ ] **Task 2: Add versioned lookup to GradingModelRepository** (AC: #1)
  - [ ] 2.1 Add `get_by_id_and_version(model_id, model_version)` method to `GradingModelRepository`
  - [ ] 2.2 Query by both `model_id` AND `model_version` fields
  - [ ] 2.3 Add composite index on `(model_id, model_version)` for efficient lookup
  - [ ] 2.4 Add unit tests for versioned lookup

- [ ] **Task 3: Create Collection MCP client** (AC: #1)
  - [ ] 3.1 Create `infrastructure/clients/collection_mcp_client.py`
  - [ ] 3.2 Implement `get_document(document_id)` via gRPC to Collection MCP
  - [ ] 3.3 Handle connection errors and timeouts gracefully
  - [ ] 3.4 Add retry logic with exponential backoff

- [ ] **Task 4: Implement performance update service** (AC: #2, #4)
  - [ ] 4.1 Create `domain/services/performance_update_service.py`
  - [ ] 4.2 Implement `update_today_metrics(farmer_id, primary_count, secondary_count, attribute_distribution, weight_kg)`
  - [ ] 4.3 Handle date rollover (reset `today` when date changes)
  - [ ] 4.4 Use atomic MongoDB update with `$inc` for counters
  - [ ] 4.5 Handle farmer not found (log warning, skip update)

- [ ] **Task 5: Implement domain event emission - plantation.quality.graded** (AC: #3)
  - [ ] 5.1 Reuse `DaprEventPublisher` pattern from Collection Model (generic payload dict)
  - [ ] 5.2 Emit `plantation.quality.graded` event via `event_publisher.publish()` after performance update
  - [ ] 5.3 Include payload fields: `farmer_id`, `document_id`, `grading_model_id`, `grading_model_version`, `grade_counts`, `attribute_distribution`, `timestamp`
  - [ ] 5.4 **NO dedicated Pydantic model** - use dynamic dict like Collection Model

- [ ] **Task 5b: Implement performance summary computation** (AC: #4)
  - [ ] 5b.1 Create `domain/services/performance_summary_service.py`
  - [ ] 5b.2 Implement `compute_primary_percentage(grade_counts)` - calculate % from today's counts
  - [ ] 5b.3 Implement `compute_improvement_trend(farmer_performance)` - compare recent vs previous (improving/stable/declining)
  - [ ] 5b.4 **NO category computation** - Engagement Model owns WIN/WATCH/WORK/WARN vocabulary

- [ ] **Task 5c: Emit plantation.performance_updated event** (AC: #4)
  - [ ] 5c.1 Emit `plantation.performance_updated` event after summary computation
  - [ ] 5c.2 Include payload: `farmer_id`, `factory_id`, `primary_percentage`, `improvement_trend`, `today`, `triggered_by_document_id`
  - [ ] 5c.3 **NO `current_category`** - Engagement Model computes from primary_percentage + factory thresholds
  - [ ] 5c.4 This event is consumed by Engagement Model for streak/milestone updates

- [ ] **Task 6: Implement error handling** (AC: #5)
  - [ ] 6.1 Define `QualityEventProcessingError` exception class
  - [ ] 6.2 Handle: document not found, farmer not found, missing grade counts
  - [ ] 6.3 Log errors with full context (document_id, farmer_id, error details)
  - [ ] 6.4 Emit failure metrics: `plantation.quality_event.failed`
  - [ ] 6.5 Return appropriate DAPR acknowledgment (SUCCESS, RETRY, DROP)

- [ ] **Task 7: Write unit tests** (AC: #1-5)
  - [ ] 7.1 Test event handler parses payload correctly
  - [ ] 7.2 Test performance update increments both primary and secondary counters correctly
  - [ ] 7.3 Test date rollover resets today metrics
  - [ ] 7.4 Test domain event is emitted with correct payload (including `attribute_distribution`)
  - [ ] 7.5 Test error cases: missing document, missing farmer, missing grade counts

- [ ] **Task 8: Integration test with mock DAPR** (AC: #1-5)
  - [ ] 8.1 Create integration test simulating full event flow
  - [ ] 8.2 Use mock Collection MCP client
  - [ ] 8.3 Verify MongoDB updates are correct
  - [ ] 8.4 Verify domain event is published

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

### Event Flow (Two Events Emitted)

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
┌─────────────────────────────────────────────────────────────────────┐
│  Plantation Model (This Story)                                      │
│                                                                     │
│  1. Receive event                                                   │
│  2. Get doc from Collection MCP                                     │
│  3. Extract: primary/secondary counts, attribute_dist, weight_kg    │
│  4. Update farmer's today metrics (FarmerPerformance.today)         │
│  5. Compute performance summary:                                    │
│     - primary_percentage from grade_counts                          │
│     - improvement_trend (comparing recent vs previous)              │
│     - NO category computation (Engagement Model owns vocabulary)    │
│  6. Emit TWO events:                                                │
│                                                                     │
│     ┌────────────────────────────┐  ┌────────────────────────────┐  │
│     │ plantation.quality.graded  │  │ plantation.performance_    │  │
│     │ (per-delivery data)        │  │ updated (summary + trends) │  │
│     └─────────────┬──────────────┘  └─────────────┬──────────────┘  │
│                   │                               │                  │
└───────────────────┼───────────────────────────────┼──────────────────┘
                    │                               │
                    ▼                               ▼
┌─────────────────────────────┐   ┌─────────────────────────────────┐
│  Consumers:                 │   │  Consumers:                     │
│  - Knowledge Model          │   │  - Engagement Model             │
│    (diagnosis on bag)       │   │    (streaks, milestones)        │
│  - Notification Model       │   │  - Action Plan Model            │
│    (immediate SMS feedback) │   │    (personalized recommendations)│
└─────────────────────────────┘   └─────────────────────────────────┘
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

### Field Mapping (MVP: Keep It Simple)

**Use the same field names as QC Analyzer JSON** - no renaming for MVP.

| QC Analyzer Field        | Used For                                                 | Notes                             |
|--------------------------|----------------------------------------------------------|-----------------------------------|
| `primary`                | `grade_counts.primary`                                   | Combined into dict                |
| `secondary`              | `grade_counts.secondary`                                 | Combined into dict                |
| `timestamp`              | Event payload                                            | Pass through as-is                |
| `bag_id`                 | Event payload                                            | Pass through                      |
| `farmer_id`              | Event payload + FarmerPerformance lookup                 | Pass through                      |
| `factory_id`             | Event payload                                            | Pass through                      |
| `grading_model_id`       | Event payload + GradingModel lookup                      | Pass through                      |
| `grading_model_version`  | Event payload + GradingModel lookup                      | **Required for versioned lookup** |
| `total_weight_kg`        | Event payload + FarmerPerformance.today.total_kg         | Pass through (optional)           |
| `attribute_distribution` | Event payload + FarmerPerformance.today.attribute_counts | **Required for dashboard**        |
| —                        | `document_id` in event payload                           | Added by Collection Model         |

**Transformations:**
1. `grade_counts` dict built dynamically from `grading_model.grade_labels`
2. `attribute_distribution` passed through as-is (required for leaf type breakdown UI)

### Quality Document Structure (from Collection MCP)

The document retrieved from Collection MCP contains **leaf-level classification counts** (not a single bag grade):
```json
{
    "document_id": "doc-abc123",
    "source_id": "qc-analyzer-result",
    "extracted_fields": {
        "farmer_id": "KEN-FRM-567890",
        "factory_id": "KEN-FAC-001",
        "bag_id": "2dd2fa43-85be-4fe6-a44a-b209135d9e9f",
        "grading_model_id": "tbk_kenya_tea_v1",
        "grading_model_version": "1.0.0",
        "total": 102,
        "primary": 61,
        "secondary": 41,
        "attribute_distribution": {
            "leaf_type": {
                "bud": {"count": 12, "avg_confidence": 0.91},
                "one_leaf_bud": {"count": 15, "avg_confidence": 0.83},
                "two_leaves_bud": {"count": 11, "avg_confidence": 0.83},
                "three_plus_leaves_bud": {"count": 20, "avg_confidence": 0.87},
                "single_soft_leaf": {"count": 16, "avg_confidence": 0.82},
                "coarse_leaf": {"count": 16, "avg_confidence": 0.85},
                "banji": {"count": 12, "avg_confidence": 0.81}
            }
        }
    }
}
```

### Event Handler - Model-Driven Extraction

```python
# api/event_handlers/quality_result_handler.py
from fastapi import APIRouter
from dapr.ext.fastapi import DaprApp

router = APIRouter()
dapr_app = DaprApp()


@dapr_app.subscribe(pubsub="collection-events", topic="collection.quality_result.received")
async def handle_quality_result(event: dict) -> dict:
    """Handle quality result event from Collection Model.

    Uses GradingModel to dynamically extract grade counts.
    No hardcoded grade labels - fully model-driven.
    """
    document_id = event["document_id"]
    farmer_id = event["plantation_id"]  # plantation_id = farmer_id

    # 1. Get full document from Collection MCP
    document = await collection_mcp_client.get_document(document_id)
    extracted = document["extracted_fields"]

    # 2. Load GradingModel to get grade labels dynamically
    grading_model_id = extracted["grading_model_id"]
    grading_model_version = extracted["grading_model_version"]
    grading_model = await grading_model_repository.get_by_id_and_version(
        model_id=grading_model_id,
        model_version=grading_model_version,
    )
    if not grading_model:
        raise GradingModelNotFoundError(grading_model_id, grading_model_version)

    # 3. TRANSFORM: Build grade_counts dict from individual count fields
    # QC Analyzer outputs: {"primary": 61, "secondary": 41}
    # We transform to: {"primary": 61, "secondary": 41} as grade_counts dict
    grade_counts = {}
    for label in grading_model.grade_labels:  # e.g., ["primary", "secondary"]
        grade_counts[label] = extracted.get(label, 0)

    # 4. Extract attribute distribution and optional weight (pass through)
    attribute_distribution = extracted.get("attribute_distribution", {})
    weight_kg = extracted.get("total_weight_kg")  # Optional: future scale integration

    # 5. Note: graded_at is NEW timestamp (when we processed), not source timestamp

    # 5. Update farmer's today metrics
    await performance_update_service.update_today_metrics(
        farmer_id=farmer_id,
        grade_counts=grade_counts,
        attribute_distribution=attribute_distribution,
        weight_kg=weight_kg,  # None if no scale data available
    )

    # 6. Emit domain event (generic payload dict, use same field names as QC Analyzer)
    await event_publisher.publish(
        topic="plantation.quality.graded",
        payload={
            "document_id": document_id,
            "farmer_id": farmer_id,
            "factory_id": extracted.get("factory_id"),
            "bag_id": extracted.get("bag_id"),
            "grading_model_id": grading_model_id,
            "grading_model_version": grading_model_version,
            "timestamp": extracted.get("timestamp"),  # Original QC Analyzer timestamp
            "grade_counts": grade_counts,  # Transformation: combined into dict
            "attribute_distribution": attribute_distribution,  # Required for leaf type breakdown UI
            "total_weight_kg": weight_kg,
        },
        source_id="plantation-model",
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
    grade_counts: dict[str, int],
    attribute_distribution: dict[str, dict],
    weight_kg: float | None = None,
) -> None:
    """Update farmer's today metrics atomically.

    Uses MongoDB $inc for atomic counter updates.
    Handles date rollover automatically.
    Grade labels are dynamic - no hardcoded labels.

    Args:
        farmer_id: The farmer who delivered
        grade_counts: Dict of grade_label -> count (e.g., {"primary": 61, "secondary": 41})
        attribute_distribution: Attribute counts from QC Analyzer
        weight_kg: Optional weight (future: from QC Analyzer scale)
    """
    today = date.today().isoformat()
    now = datetime.now(timezone.utc)

    # Build atomic update with dynamic grade labels
    update = {
        "$inc": {
            "today.deliveries": 1,
        },
        "$set": {
            "today.last_delivery": now,
            "today.date": today,
            "updated_at": now,
        },
    }

    # Add grade counts dynamically for each label
    for label, count in grade_counts.items():
        update["$inc"][f"today.grade_counts.{label}"] = count

    # Add weight if available (future: from QC Analyzer scale)
    if weight_kg:
        update["$inc"]["today.total_kg"] = weight_kg

    # Add attribute counts for trend analysis (extract count from nested structure)
    for attr_name, attr_values in attribute_distribution.items():
        for value_name, value_data in attr_values.items():
            count = value_data.get("count", 0) if isinstance(value_data, dict) else value_data
            update["$inc"][f"today.attribute_counts.{attr_name}.{value_name}"] = count

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
        # Build initial attribute_counts
        initial_attr_counts = {}
        for attr_name, attr_values in attribute_distribution.items():
            initial_attr_counts[attr_name] = {}
            for value_name, value_data in attr_values.items():
                count = value_data.get("count", 0) if isinstance(value_data, dict) else value_data
                initial_attr_counts[attr_name][value_name] = count

        # Reset today and apply update
        await db["farmer_performance"].update_one(
            {"farmer_id": farmer_id},
            {
                "$set": {
                    "today": {
                        "deliveries": 1,
                        "total_kg": weight_kg or 0,
                        "grade_counts": grade_counts,
                        "attribute_counts": initial_attr_counts,
                        "last_delivery": now,
                        "date": today,
                    },
                    "updated_at": now,
                },
            },
        )
```

### Domain Event: plantation.quality.graded

**Follow the Collection Model pattern** - use generic event wrapper with dynamic payload dict, NOT dedicated Pydantic models per event type.

Reuse `DaprEventPublisher` pattern from Collection Model:
```python
# Use same field names as QC Analyzer JSON (MVP: keep it simple)
await event_publisher.publish(
    topic="plantation.quality.graded",
    payload={
        "document_id": document_id,  # Added by Collection Model
        "farmer_id": farmer_id,
        "factory_id": factory_id,
        "bag_id": bag_id,
        "grading_model_id": grading_model_id,
        "grading_model_version": grading_model_version,
        "timestamp": timestamp,  # Original QC Analyzer timestamp
        "grade_counts": grade_counts,  # Transformation: combined into dict
        "attribute_distribution": attribute_distribution,  # Required for leaf type breakdown UI
        "total_weight_kg": total_weight_kg,  # Optional
    },
    source_id="plantation-model",
)
```

**Payload fields for `plantation.quality.graded`** (same names as QC Analyzer JSON):

| Field                    | Type      | Description                                        |
|--------------------------|-----------|----------------------------------------------------|
| `document_id`            | str       | Added by Collection Model                          |
| `farmer_id`              | str       | Farmer who delivered                               |
| `factory_id`             | str       | Factory ID                                         |
| `bag_id`                 | str       | Bag identifier                                     |
| `grading_model_id`       | str       | Grading model ID                                   |
| `grading_model_version`  | str       | Grading model version (required for lookup)        |
| `timestamp`              | str (ISO) | Original QC Analyzer timestamp                     |
| `grade_counts`           | dict      | Transformation: combined from individual counts    |
| `attribute_distribution` | dict      | **Required**: Leaf type breakdown for dashboard UI |
| `total_weight_kg`        | float?    | Weight (optional, future: from scale)              |

### Domain Event: plantation.performance_updated

This event provides **raw performance data** for downstream services. Engagement Model computes categories from this data.

**Key Design Decision:** Plantation Model does NOT compute WIN/WATCH/WORK/WARN categories. That vocabulary is owned by Engagement Model.

```python
await event_publisher.publish(
    topic="plantation.performance_updated",
    payload={
        # Identity
        "farmer_id": farmer_id,
        "factory_id": factory_id,
        "triggered_by_document_id": document_id,  # Traceability
        "timestamp": datetime.now(timezone.utc).isoformat(),

        # Raw performance data (NO category - Engagement Model computes)
        "primary_percentage": 85.2,  # Computed from today's grade_counts
        "improvement_trend": "improving",  # improving/stable/declining

        # Today's aggregates
        "today": {
            "deliveries": 3,
            "grade_counts": {"primary": 185, "secondary": 32},
            "total_kg": 45.5,  # Optional
        },
    },
    source_id="plantation-model",
)
```

**Payload fields for `plantation.performance_updated`:**

| Field                      | Type      | Description                                            |
|----------------------------|-----------|--------------------------------------------------------|
| `farmer_id`                | str       | Farmer ID                                              |
| `factory_id`               | str       | Factory ID                                             |
| `triggered_by_document_id` | str       | Document that triggered this update (traceability)     |
| `timestamp`                | str (ISO) | When this summary was computed                         |
| `primary_percentage`       | float     | Computed from today's grade_counts                     |
| `improvement_trend`        | str       | "improving" / "stable" / "declining"                   |
| `today`                    | dict      | Today's aggregates: deliveries, grade_counts, total_kg |

**Note:** NO `current_category` field. Engagement Model fetches factory thresholds and computes WIN/WATCH/WORK/WARN.

### Performance Summary Logic

```python
# domain/services/performance_summary_service.py

def compute_primary_percentage(grade_counts: dict[str, int]) -> float:
    """Compute Primary % from grade counts."""
    primary = grade_counts.get("primary", 0)
    secondary = grade_counts.get("secondary", 0)
    total = primary + secondary
    if total == 0:
        return 0.0
    return (primary / total) * 100


def compute_improvement_trend(farmer_performance: dict) -> str:
    """Compute improvement trend from recent history.

    MVP: Simple comparison of today vs previous average.
    Future: More sophisticated trend analysis using 30d/90d distributions.

    Returns: "improving" | "stable" | "declining"
    """
    today_counts = farmer_performance.get("today", {}).get("grade_counts", {})
    today_pct = compute_primary_percentage(today_counts)

    # Get previous average (from grade_distribution_30d or similar)
    prev_pct = farmer_performance.get("previous_primary_pct", today_pct)

    diff = today_pct - prev_pct
    if diff > 5:  # More than 5% improvement
        return "improving"
    elif diff < -5:  # More than 5% decline
        return "declining"
    else:
        return "stable"

# NOTE: determine_category() is NOT here - it's in Engagement Model
# Engagement Model owns WIN/WATCH/WORK/WARN vocabulary
```

### Critical Implementation Rules

**From project-context.md:**

1. **ALL I/O operations MUST be async** - Event handler, MCP client, MongoDB updates
2. **Use DAPR for inter-service communication** - Collection MCP via DAPR Service Invocation
3. **Use DAPR Pub/Sub for events** - Both subscription and emission
4. **Model-driven design** - Grade labels come from `GradingModel`, never hardcoded
5. **Atomic MongoDB updates** - Use `$inc` to avoid race conditions
6. **No grade recalculation** - QC Analyzer already classified the leaves

### Testing Strategy

**Unit Tests (`tests/unit/plantation/`):**
- `test_performance_update_service.py` - Update logic, date rollover
- `test_quality_result_handler.py` - Event parsing, error handling

**Integration Tests (`tests/integration/`):**
- `test_quality_event_flow.py` - Full flow with mock DAPR

### OpenTelemetry Metrics

```python
# Metrics to emit (labels are dynamic based on grading model)
plantation.quality_event.processed{grading_model_id="..."}  # Counter
plantation.quality_event.leaves_graded{grade_label="..."}   # Counter (for each label)
plantation.quality_event.failed{reason="document_not_found"}  # Counter
plantation.quality_event.failed{reason="grading_model_not_found"}  # Counter
plantation.quality_event.latency_ms  # Histogram
```

### GradingModel Entity Requirement

The `GradingModel` entity (from Story 1-4) must include:

```python
class GradingModel(BaseModel):
    """Grading model configuration."""

    grading_model_id: str
    grading_model_version: str
    grade_labels: list[str]  # e.g., ["primary", "secondary"] - REQUIRED for this story
    attributes_list: list[str]  # e.g., ["leaf_type", "coarse_subtype", "banji_hardness"]
    # ... other fields
```

The `grade_labels` field is extracted from the grading config's `binary_labels` values:
```json
"binary_labels": {
  "ACCEPT": "primary",   // → grade_labels[0]
  "REJECT": "secondary"  // → grade_labels[1]
}
```

### References

- [Source: _bmad-output/sprint-artifacts/1-4-farmer-performance-history-structure.md] - FarmerPerformance model
- [Source: _bmad-output/analysis/tbk-kenya-tea-grading-model-specification.md] - TBK grading spec
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
