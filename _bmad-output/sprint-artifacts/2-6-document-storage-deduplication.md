# Story 2.6: Document Storage & Deduplication

**Status:** ready-for-dev
**Epic:** 2 - Quality Data Ingestion
**Created:** 2025-12-27

---

## Story

As a **platform operator**,
I want duplicate documents detected and rejected,
So that storage is efficient and downstream analysis is not skewed.

---

## Context

Significant deduplication infrastructure already exists from Story 2-4 and 2-5:

**Implemented:**
- `RawDocumentStore.compute_content_hash()` - SHA-256 hash computation
- `RawDocumentStore.store_raw_document()` - duplicate check before storage
- MongoDB unique index on `(source_id, content_hash)`
- `DuplicateDocumentError` exception handling in processors
- Early return on duplicate (no LLM extraction costs)

**Missing (scope of this story):**
- `is_duplicate` field in `ProcessorResult`
- OpenTelemetry metrics for tracking totals/duplicates/bytes by source

---

## Acceptance Criteria

### Deduplication Result Reporting

1. **Given** a document is detected as duplicate
   **When** the processor returns
   **Then** `ProcessorResult` includes `is_duplicate=True`
   **And** `success=True` (duplicate is expected behavior, not failure)

2. **Given** a duplicate document is detected
   **When** the ingestion completes
   **Then** no domain event is emitted (already implemented)
   **And** the duplicate is logged with content_hash
   **And** duplicate metrics are incremented

### Storage Metrics (OpenTelemetry)

3. **Given** documents are stored over time
   **When** a new document is stored or duplicate detected
   **Then** OpenTelemetry counters are incremented
   **And** metrics include labels: `source_id`, `status` (stored/duplicate)

4. **Given** the following OTel metrics are defined
   **When** exported to Prometheus/Grafana
   **Then** dashboards can show:
   - `collection_documents_total{source_id, status}` - Counter
   - `collection_storage_bytes_total{source_id}` - Counter
   - Duplicate rate = `status=duplicate / total` per source

---

## Technical Tasks

### Task 1: Extend ProcessorResult Model

Update `ProcessorResult` in `processors/base.py`:

```python
class ProcessorResult(BaseModel):
    success: bool
    document_id: str | None = None
    extracted_data: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    error_type: str | None = None

    # Deduplication field (NEW)
    is_duplicate: bool = False
```

### Task 2: Update Processors for Duplicate Handling

Update `ZipExtractionProcessor.process()` to set `is_duplicate` and update metrics:

```python
except DuplicateDocumentError as e:
    logger.info(
        "Duplicate ZIP detected, skipping",
        ingestion_id=job.ingestion_id,
        source_id=source_id,
        content_hash=str(e),
    )
    # Update metrics
    await self._metrics_service.increment_duplicate(source_id)

    return ProcessorResult(
        success=True,
        is_duplicate=True,
    )
```

### Task 3: Create StorageMetrics (OpenTelemetry)

Create new file `infrastructure/storage_metrics.py`:

```python
from opentelemetry import metrics

meter = metrics.get_meter("collection-model")

# Counters
documents_counter = meter.create_counter(
    name="collection_documents_total",
    description="Total documents processed",
    unit="1",
)

storage_bytes_counter = meter.create_counter(
    name="collection_storage_bytes_total",
    description="Total bytes stored",
    unit="By",
)


class StorageMetrics:
    """OpenTelemetry metrics for document storage."""

    @staticmethod
    def record_stored(source_id: str, size_bytes: int) -> None:
        """Record a successfully stored document."""
        documents_counter.add(1, {"source_id": source_id, "status": "stored"})
        storage_bytes_counter.add(size_bytes, {"source_id": source_id})

    @staticmethod
    def record_duplicate(source_id: str) -> None:
        """Record a duplicate detection."""
        documents_counter.add(1, {"source_id": source_id, "status": "duplicate"})
```

### Task 4: Integrate Metrics into Processors

- Import `StorageMetrics` in processors
- Call `StorageMetrics.record_stored()` after successful document storage
- Call `StorageMetrics.record_duplicate()` on duplicate detection

---

## Files to Modify

| File | Change |
|------|--------|
| `processors/base.py` | Add `is_duplicate` to ProcessorResult |
| `processors/zip_extraction.py` | Set `is_duplicate=True`, call metrics |
| `processors/json_extraction.py` | Set `is_duplicate=True`, call metrics |

---

## Files to Create

| File | Purpose |
|------|---------|
| `infrastructure/storage_metrics.py` | OpenTelemetry metrics (counters) |
| `tests/unit/collection_model/test_storage_metrics.py` | Unit tests |
| `tests/unit/collection_model/test_deduplication.py` | Deduplication behavior tests |

---

## Test Requirements

### Unit Tests

1. **test_processor_result_is_duplicate**
   - Verify ProcessorResult includes `is_duplicate=True` for duplicates

2. **test_metrics_record_stored**
   - Store document, verify OTel counter incremented with correct labels

3. **test_metrics_record_duplicate**
   - Attempt duplicate, verify OTel counter incremented with `status=duplicate`

### Integration Tests

1. **test_duplicate_zip_processing**
   - Process ZIP, process same ZIP again, verify `is_duplicate=True` returned

---

## Definition of Done

- [ ] ProcessorResult includes `is_duplicate` field
- [ ] Processors set `is_duplicate=True` on duplicate detection
- [ ] StorageMetrics class created with OTel counters
- [ ] `record_stored()` called after successful storage
- [ ] `record_duplicate()` called on duplicate detection
- [ ] Unit tests pass for deduplication behavior
- [ ] Unit tests pass for metrics
- [ ] No domain events emitted on duplicate (already implemented)
- [ ] CI passes (ruff check, ruff format, tests)

---

## Architecture Notes

### Why Per-Source Deduplication?

The unique index is on `(source_id, content_hash)` rather than just `content_hash` because:
- Same file from different sources = different business context
- Allows each source to have its own deduplication scope
- QC Analyzer may legitimately send same image for different batches

### Why OpenTelemetry Metrics?

- Standard observability pattern (industry best practice)
- DAPR already provides OTel integration
- Real-time dashboards via Prometheus/Grafana
- No custom MongoDB collection to maintain
- Labels (`source_id`, `status`) enable flexible querying

---

## Dependencies

- Story 2-4: Generic Content Processing Framework (provides RawDocumentStore)
- Story 2-5: ZIP Content Processor (provides DuplicateDocumentError handling)

---

## Estimated Complexity

**Effort:** Small-Medium (mostly wiring existing components)
**Risk:** Low (deduplication logic already works, adding reporting layer)

---

_Created: 2025-12-27_
