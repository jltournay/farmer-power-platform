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
- Proper deduplication result in `ProcessorResult` (is_duplicate, original_document_id)
- Metrics tracking for duplicate rate per source
- Storage metrics queries (total, duplicates_rejected, bytes, by_source)

---

## Acceptance Criteria

### Deduplication Result Reporting

1. **Given** a document is detected as duplicate
   **When** the processor returns
   **Then** `ProcessorResult` includes `is_duplicate=True`
   **And** `ProcessorResult.original_document_id` contains the existing document's ID
   **And** `success=True` (duplicate is expected behavior, not failure)

2. **Given** a duplicate document is detected
   **When** the ingestion completes
   **Then** no domain event is emitted (already implemented)
   **And** the duplicate is logged with original_document_id
   **And** duplicate metrics are incremented

### Storage Metrics Collection

3. **Given** documents are stored over time
   **When** a new document is stored or duplicate detected
   **Then** metrics are updated in MongoDB `collection_model.storage_metrics` collection
   **And** metrics track: `total_documents`, `duplicates_rejected`, `storage_bytes`
   **And** metrics are broken down by `source_id`

4. **Given** a metrics document structure
   **When** viewed in MongoDB
   **Then** document follows this structure:
   ```python
   {
       "_id": "storage_metrics",
       "updated_at": datetime,
       "by_source": {
           "qc-analyzer-exceptions": {
               "total_documents": int,
               "duplicates_rejected": int,
               "storage_bytes": int
           },
           "weather-api": { ... }
       },
       "totals": {
           "total_documents": int,
           "duplicates_rejected": int,
           "storage_bytes": int
       }
   }
   ```

### Metrics Query API (Internal)

5. **Given** the storage metrics collection exists
   **When** `StorageMetricsService.get_metrics()` is called
   **Then** returns aggregated metrics with by_source breakdown
   **And** query uses efficient MongoDB aggregation

6. **Given** the storage metrics collection exists
   **When** `StorageMetricsService.get_metrics_by_source(source_id)` is called
   **Then** returns metrics for specific source only

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

    # Deduplication fields (NEW)
    is_duplicate: bool = False
    original_document_id: str | None = None
```

### Task 2: Update RawDocumentStore Duplicate Response

Modify `store_raw_document()` to return existing document info on duplicate:

```python
class DuplicateInfo(BaseModel):
    """Information about an existing duplicate document."""
    existing_document_id: str
    existing_ingested_at: datetime
    content_hash: str

async def store_raw_document(...) -> RawDocument:
    # Check for duplicate
    existing = await self.collection.find_one(...)
    if existing:
        raise DuplicateDocumentError(
            message=f"Duplicate content for source {source_id}",
            existing_document_id=existing.get("document_id"),
            content_hash=content_hash,
        )
```

### Task 3: Update Processors for Duplicate Handling

Update `ZipExtractionProcessor.process()`:

```python
except DuplicateDocumentError as e:
    logger.info(
        "Duplicate ZIP detected, skipping",
        ingestion_id=job.ingestion_id,
        source_id=source_id,
        original_document_id=e.existing_document_id,
    )
    # Update metrics
    await self._metrics_service.increment_duplicate(source_id)

    return ProcessorResult(
        success=True,
        is_duplicate=True,
        original_document_id=e.existing_document_id,
    )
```

### Task 4: Create StorageMetricsService

Create new file `infrastructure/storage_metrics.py`:

```python
class StorageMetricsService:
    """Service for tracking storage metrics with MongoDB upserts."""

    COLLECTION_NAME = "storage_metrics"
    METRICS_DOC_ID = "storage_metrics"

    async def increment_stored(
        self,
        source_id: str,
        size_bytes: int,
    ) -> None:
        """Increment counters for successfully stored document."""
        await self.collection.update_one(
            {"_id": self.METRICS_DOC_ID},
            {
                "$set": {"updated_at": datetime.now(UTC)},
                "$inc": {
                    f"by_source.{source_id}.total_documents": 1,
                    f"by_source.{source_id}.storage_bytes": size_bytes,
                    "totals.total_documents": 1,
                    "totals.storage_bytes": size_bytes,
                }
            },
            upsert=True,
        )

    async def increment_duplicate(self, source_id: str) -> None:
        """Increment duplicate counter for source."""
        await self.collection.update_one(
            {"_id": self.METRICS_DOC_ID},
            {
                "$set": {"updated_at": datetime.now(UTC)},
                "$inc": {
                    f"by_source.{source_id}.duplicates_rejected": 1,
                    "totals.duplicates_rejected": 1,
                }
            },
            upsert=True,
        )

    async def get_metrics(self) -> StorageMetrics:
        """Get all storage metrics."""
        doc = await self.collection.find_one({"_id": self.METRICS_DOC_ID})
        if not doc:
            return StorageMetrics(by_source={}, totals=MetricsTotals())
        return StorageMetrics.model_validate(doc)

    async def get_metrics_by_source(self, source_id: str) -> SourceMetrics | None:
        """Get metrics for specific source."""
        doc = await self.collection.find_one(
            {"_id": self.METRICS_DOC_ID},
            {f"by_source.{source_id}": 1}
        )
        if not doc or "by_source" not in doc or source_id not in doc["by_source"]:
            return None
        return SourceMetrics.model_validate(doc["by_source"][source_id])
```

### Task 5: Integrate Metrics into Processor Pipeline

- Inject `StorageMetricsService` as dependency in `ContentProcessorWorker`
- Call `increment_stored()` after successful document storage
- Call `increment_duplicate()` on duplicate detection

### Task 6: Update DuplicateDocumentError

Modify exception to carry existing document info:

```python
class DuplicateDocumentError(Exception):
    """Raised when duplicate content is detected."""

    def __init__(
        self,
        message: str,
        existing_document_id: str | None = None,
        content_hash: str | None = None,
    ):
        super().__init__(message)
        self.existing_document_id = existing_document_id
        self.content_hash = content_hash
```

---

## Files to Modify

| File | Change |
|------|--------|
| `processors/base.py` | Add `is_duplicate`, `original_document_id` to ProcessorResult |
| `domain/exceptions.py` | Add fields to DuplicateDocumentError |
| `infrastructure/raw_document_store.py` | Include existing doc info in exception |
| `processors/zip_extraction.py` | Update duplicate handling to use new fields |
| `processors/json_extraction.py` | Update duplicate handling to use new fields |
| `infrastructure/storage_metrics.py` | NEW: StorageMetricsService |
| `infrastructure/mongodb.py` | Add metrics collection reference |

---

## Files to Create

| File | Purpose |
|------|---------|
| `infrastructure/storage_metrics.py` | Storage metrics tracking service |
| `domain/storage_metrics.py` | Pydantic models for metrics |
| `tests/unit/collection_model/test_storage_metrics.py` | Unit tests |
| `tests/unit/collection_model/test_deduplication.py` | Deduplication behavior tests |

---

## Test Requirements

### Unit Tests

1. **test_duplicate_detection_returns_original_id**
   - Store document, attempt duplicate, verify original_document_id returned

2. **test_metrics_increment_on_store**
   - Store document, verify metrics incremented

3. **test_metrics_increment_on_duplicate**
   - Attempt duplicate, verify duplicates_rejected incremented

4. **test_metrics_aggregation_by_source**
   - Store from multiple sources, verify by_source breakdown

5. **test_processor_result_duplicate_fields**
   - Verify ProcessorResult includes is_duplicate=True for duplicates

### Integration Tests

1. **test_duplicate_zip_processing**
   - Process ZIP, process same ZIP again, verify duplicate handling

2. **test_metrics_persistence**
   - Store documents, restart service, verify metrics survive

---

## Definition of Done

- [ ] ProcessorResult includes is_duplicate and original_document_id fields
- [ ] DuplicateDocumentError carries existing_document_id
- [ ] Processors return duplicate info in ProcessorResult
- [ ] StorageMetricsService created with increment/query methods
- [ ] Metrics collection created with proper indexes
- [ ] Metrics incremented on store and on duplicate detection
- [ ] Unit tests pass for deduplication behavior
- [ ] Unit tests pass for metrics service
- [ ] Integration test verifies end-to-end duplicate handling
- [ ] No domain events emitted on duplicate (already implemented)
- [ ] CI passes (ruff check, ruff format, tests)

---

## Architecture Notes

### Why Per-Source Deduplication?

The unique index is on `(source_id, content_hash)` rather than just `content_hash` because:
- Same file from different sources = different business context
- Allows each source to have its own deduplication scope
- QC Analyzer may legitimately send same image for different batches

### Why Single Metrics Document?

Using a single document with `$inc` operations provides:
- Atomic counter updates (no race conditions)
- Efficient upsert (no separate insert/update logic)
- Simple retrieval (single document read)
- Easy backup and debugging

For high-volume systems, consider sharding by time period (daily/weekly docs).

### Metrics Update Timing

Metrics are updated **asynchronously** after processing:
- Don't block processing on metrics writes
- Use fire-and-forget pattern with error logging
- Metrics lag is acceptable (eventually consistent)

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
