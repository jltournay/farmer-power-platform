# Story 2.3: Event Grid Trigger Handler

**Status:** ready-for-dev
**GitHub Issue:** #18

---

## Story

As a **Collection Model service**,
I want to receive Azure Event Grid blob-created events and process them,
So that new QC Analyzer uploads trigger automatic ingestion.

---

## Acceptance Criteria

1. **Given** the Collection Model service is running
   **When** Event Grid sends a subscription validation request
   **Then** the service responds with the validationResponse
   **And** the subscription is confirmed

2. **Given** a blob is created in `qc-analyzer-results` container
   **When** Event Grid sends blob-created event
   **Then** the event is parsed: container, blob_path, content_length, timestamp
   **And** source_config is looked up by `landing_container` pattern match
   **And** if source is enabled, ingestion job is queued

3. **Given** the blob matches source_config with mode=BLOB_TRIGGER
   **When** the event is processed
   **Then** blob metadata is extracted using `path_pattern` from config
   **And** processing_status is set to "queued" in MongoDB
   **And** the blob is queued for content processing

4. **Given** no source_config matches the blob container
   **When** the event is processed
   **Then** the event is logged with warning "No matching source config"
   **And** no further processing occurs
   **And** metrics track unmatched events

5. **Given** the same blob event is received twice (Event Grid retry)
   **When** processing is attempted
   **Then** idempotency check detects duplicate (by blob_path + etag)
   **And** duplicate is skipped with log "Already processed"

---

## Tasks / Subtasks

### Task 1: Create SourceConfigService for runtime config lookup (AC: #2, #3)
- [ ] 1.1 Create `services/collection_model/source_config_service.py`
- [ ] 1.2 Implement `get_config_by_container(container: str)` async method
- [ ] 1.3 Implement 5-minute TTL cache for source configs
- [ ] 1.4 Add `is_enabled()` check for source config
- [ ] 1.5 Implement `match_path_pattern(path, pattern)` for metadata extraction

### Task 2: Implement Event Grid event processor (AC: #1, #2)
- [ ] 2.1 Enhance `api/events.py` to process blob-created events (not just log)
- [ ] 2.2 Parse Event Grid event payload: subject, data.url, data.contentLength, data.eTag
- [ ] 2.3 Extract container name and blob path from subject
- [ ] 2.4 Call SourceConfigService to find matching config

### Task 3: Implement ingestion queue mechanism (AC: #2, #3)
- [ ] 3.1 Create `domain/ingestion_job.py` with IngestionJob Pydantic model
- [ ] 3.2 Create `ingestion_queue` MongoDB collection
- [ ] 3.3 Implement `queue_ingestion_job(job: IngestionJob)` method
- [ ] 3.4 Store job with status "queued", blob_path, source_id, metadata

### Task 4: Implement path pattern metadata extraction (AC: #3)
- [ ] 4.1 Parse path_pattern config (e.g., `results/{plantation_id}/{crop}/{market}/{batch_id}.json`)
- [ ] 4.2 Match actual blob path against pattern
- [ ] 4.3 Extract fields defined in `extract_fields` config
- [ ] 4.4 Return extracted metadata dict

### Task 5: Implement idempotency checking (AC: #5)
- [ ] 5.1 Add unique compound index on `ingestion_queue`: (blob_path, blob_etag)
- [ ] 5.2 Check for existing job before queuing
- [ ] 5.3 Return early with log if duplicate detected
- [ ] 5.4 Handle MongoDB duplicate key error gracefully

### Task 6: Implement unmatched event handling (AC: #4)
- [ ] 6.1 Log warning when no source config matches container
- [ ] 6.2 Add metric counter for unmatched events
- [ ] 6.3 Return 202 (event received but not processed)

### Task 7: Write unit tests
- [ ] 7.1 Test SourceConfigService config lookup
- [ ] 7.2 Test SourceConfigService caching behavior
- [ ] 7.3 Test path pattern matching and metadata extraction
- [ ] 7.4 Test Event Grid event parsing
- [ ] 7.5 Test ingestion job queuing
- [ ] 7.6 Test idempotency check (duplicate detection)
- [ ] 7.7 Test unmatched container handling
- [ ] 7.8 Test disabled source config handling

---

## Dev Notes

### Service Location

```
services/collection-model/src/collection_model/
├── api/
│   └── events.py                 # Enhanced Event Grid handler
├── domain/
│   ├── models.py
│   └── ingestion_job.py          # NEW: IngestionJob model
├── services/
│   └── source_config_service.py  # NEW: Runtime config lookup
└── infrastructure/
    ├── mongodb.py
    └── ingestion_queue.py        # NEW: Queue operations
```

### Technology Stack

| Component | Choice | Version |
|-----------|--------|---------|
| Language | Python | 3.12 |
| Web Framework | FastAPI | Latest |
| Validation | Pydantic | 2.0+ |
| MongoDB Driver | Motor (async) | Latest |
| Caching | aiocache | Latest |

### Critical Implementation Rules

**From project-context.md:**

1. **ALL I/O operations MUST be async** - Use `async def` for all database and network operations
2. **Use Pydantic 2.0 syntax** - `model_dump()` not `dict()`, `model_validate()` not `parse_obj()`
3. **Type hints required** - ALL function signatures MUST have type hints
4. **Absolute imports only** - No relative imports

### SourceConfigService Implementation

```python
# services/source_config_service.py
from datetime import datetime, timezone
from typing import Any

from aiocache import cached
from motor.motor_asyncio import AsyncIOMotorDatabase

from fp_common.models.source_config import SourceConfig, ValidationConfig


class SourceConfigService:
    """Runtime service for looking up source configurations."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.collection = db["source_configs"]

    @cached(ttl=300)  # 5-minute TTL cache
    async def get_all_configs(self) -> list[dict[str, Any]]:
        """Get all enabled source configs (cached)."""
        cursor = self.collection.find({"enabled": True})
        return await cursor.to_list(length=100)

    async def get_config_by_container(
        self, container: str
    ) -> dict[str, Any] | None:
        """Find source config matching the given container.

        Args:
            container: Azure Blob Storage container name

        Returns:
            Matching source config or None
        """
        configs = await self.get_all_configs()
        for config in configs:
            ingestion = config.get("config", {}).get("ingestion", {})
            if ingestion.get("mode") == "blob_trigger":
                landing_container = ingestion.get("landing_container")
                if landing_container == container:
                    return config
        return None

    def extract_path_metadata(
        self,
        blob_path: str,
        config: dict[str, Any],
    ) -> dict[str, str]:
        """Extract metadata from blob path using config pattern.

        Args:
            blob_path: Full blob path (e.g., results/WM-4521/tea/mombasa/batch-001.json)
            config: Source configuration with path_pattern

        Returns:
            Dict of extracted field values
        """
        ingestion = config.get("config", {}).get("ingestion", {})
        path_pattern = ingestion.get("path_pattern")
        if not path_pattern:
            return {}

        pattern = path_pattern.get("pattern", "")
        extract_fields = path_pattern.get("extract_fields", [])

        # Parse pattern and extract values
        # Pattern: "results/{plantation_id}/{crop}/{market}/{batch_id}.json"
        # Path: "results/WM-4521/tea/mombasa/batch-001.json"
        metadata = {}
        pattern_parts = pattern.split("/")
        path_parts = blob_path.split("/")

        for i, part in enumerate(pattern_parts):
            if i < len(path_parts) and part.startswith("{") and part.endswith("}"):
                field_name = part[1:-1].replace(".json", "")
                value = path_parts[i].replace(".json", "")
                if field_name in extract_fields:
                    metadata[field_name] = value

        return metadata
```

### IngestionJob Model

```python
# domain/ingestion_job.py
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class IngestionJob(BaseModel):
    """Represents a queued ingestion job."""

    blob_path: str = Field(..., description="Full blob path")
    blob_etag: str = Field(..., description="Blob ETag for idempotency")
    container: str = Field(..., description="Storage container name")
    source_id: str = Field(..., description="Matched source config ID")
    content_length: int = Field(..., description="Blob size in bytes")

    status: Literal["queued", "processing", "completed", "failed"] = "queued"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Extracted metadata from path pattern
    metadata: dict[str, str] = Field(default_factory=dict)

    # Processing info
    error_message: str | None = None
    processed_at: datetime | None = None
```

### Enhanced Event Grid Handler

```python
# api/events.py (enhanced)
from fastapi import APIRouter, Request, Response
import structlog

from collection_model.domain.ingestion_job import IngestionJob
from collection_model.services.source_config_service import SourceConfigService
from collection_model.infrastructure.ingestion_queue import IngestionQueue

router = APIRouter(prefix="/api/events", tags=["events"])
logger = structlog.get_logger()


@router.post("/blob-created")
async def handle_blob_created(request: Request) -> Response:
    """Handle Azure Event Grid blob-created events."""
    body = await request.json()

    # Handle subscription validation handshake
    if isinstance(body, list) and len(body) > 0:
        event = body[0]
        if event.get("eventType") == "Microsoft.EventGrid.SubscriptionValidationEvent":
            validation_code = event["data"]["validationCode"]
            logger.info("Event Grid subscription validation", code=validation_code)
            return Response(
                content=f'{{"validationResponse": "{validation_code}"}}',
                media_type="application/json"
            )

    # Get dependencies
    source_config_service: SourceConfigService = request.app.state.source_config_service
    ingestion_queue: IngestionQueue = request.app.state.ingestion_queue

    # Process blob-created events
    for event in body:
        if event.get("eventType") != "Microsoft.Storage.BlobCreated":
            continue

        # Parse event data
        subject = event.get("subject", "")  # /blobServices/default/containers/{container}/blobs/{path}
        data = event.get("data", {})
        blob_url = data.get("url", "")
        content_length = data.get("contentLength", 0)
        etag = data.get("eTag", "")

        # Extract container and path from subject
        # Format: /blobServices/default/containers/{container}/blobs/{blob_path}
        parts = subject.split("/containers/")
        if len(parts) < 2:
            logger.warning("Invalid event subject format", subject=subject)
            continue

        container_and_path = parts[1].split("/blobs/")
        if len(container_and_path) < 2:
            logger.warning("Cannot extract container/path", subject=subject)
            continue

        container = container_and_path[0]
        blob_path = container_and_path[1]

        logger.info(
            "Processing blob-created event",
            container=container,
            blob_path=blob_path,
            content_length=content_length,
        )

        # Look up source config
        config = await source_config_service.get_config_by_container(container)
        if config is None:
            logger.warning(
                "No matching source config for container",
                container=container,
                blob_path=blob_path,
            )
            # TODO: Increment unmatched_events metric
            continue

        source_id = config.get("source_id")
        if not config.get("enabled", True):
            logger.info(
                "Source config is disabled",
                source_id=source_id,
                container=container,
            )
            continue

        # Extract metadata from path
        metadata = source_config_service.extract_path_metadata(blob_path, config)

        # Create ingestion job
        job = IngestionJob(
            blob_path=blob_path,
            blob_etag=etag,
            container=container,
            source_id=source_id,
            content_length=content_length,
            metadata=metadata,
        )

        # Queue job (with idempotency check)
        queued = await ingestion_queue.queue_job(job)
        if queued:
            logger.info(
                "Ingestion job queued",
                source_id=source_id,
                blob_path=blob_path,
                metadata=metadata,
            )
        else:
            logger.info(
                "Duplicate event skipped (already processed)",
                blob_path=blob_path,
                etag=etag,
            )

    return Response(status_code=202)
```

### Ingestion Queue Implementation

```python
# infrastructure/ingestion_queue.py
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError
import structlog

from collection_model.domain.ingestion_job import IngestionJob

logger = structlog.get_logger()

COLLECTION_NAME = "ingestion_queue"


class IngestionQueue:
    """Queue for ingestion jobs stored in MongoDB."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.collection = db[COLLECTION_NAME]

    async def ensure_indexes(self) -> None:
        """Create required indexes."""
        # Unique compound index for idempotency
        await self.collection.create_index(
            [("blob_path", 1), ("blob_etag", 1)],
            unique=True,
            name="idx_blob_path_etag_unique",
        )
        # Index for queue processing
        await self.collection.create_index(
            [("status", 1), ("created_at", 1)],
            name="idx_status_created",
        )

    async def queue_job(self, job: IngestionJob) -> bool:
        """Queue an ingestion job.

        Returns:
            True if job was queued, False if duplicate detected.
        """
        try:
            await self.collection.insert_one(job.model_dump())
            return True
        except DuplicateKeyError:
            logger.debug(
                "Duplicate job detected",
                blob_path=job.blob_path,
                etag=job.blob_etag,
            )
            return False

    async def get_pending_jobs(self, limit: int = 10) -> list[IngestionJob]:
        """Get pending jobs for processing."""
        cursor = (
            self.collection
            .find({"status": "queued"})
            .sort("created_at", 1)
            .limit(limit)
        )
        jobs = []
        async for doc in cursor:
            jobs.append(IngestionJob.model_validate(doc))
        return jobs
```

### MongoDB Collections

| Collection | Purpose | Indexes |
|------------|---------|---------|
| `source_configs` | Source configurations (from CLI) | source_id (unique) |
| `ingestion_queue` | Queued ingestion jobs | (blob_path, blob_etag) unique, (status, created_at) |

### Event Grid Event Schema

```json
{
  "id": "unique-event-id",
  "eventType": "Microsoft.Storage.BlobCreated",
  "subject": "/blobServices/default/containers/qc-analyzer-landing/blobs/results/WM-4521/tea/mombasa/batch-001.json",
  "data": {
    "api": "PutBlob",
    "contentType": "application/json",
    "contentLength": 1234,
    "blobType": "BlockBlob",
    "url": "https://storage.blob.core.windows.net/qc-analyzer-landing/results/WM-4521/tea/mombasa/batch-001.json",
    "eTag": "0x8DB12345ABCD"
  },
  "eventTime": "2025-12-26T08:30:00Z"
}
```

### Testing Strategy

| Test Type | What to Test | Mocking Required |
|-----------|--------------|------------------|
| Unit | SourceConfigService.get_config_by_container | mock_mongodb_client |
| Unit | SourceConfigService.extract_path_metadata | None (pure function) |
| Unit | IngestionQueue.queue_job | mock_mongodb_client |
| Unit | Idempotency (duplicate key handling) | mock_mongodb_client |
| Unit | Event Grid event parsing | None |
| Unit | Unmatched container handling | mock_mongodb_client |

### Previous Stories Learnings

**From Story 2.1:**
- Event Grid webhook handler stub exists in `api/events.py`
- MongoDB connection is configured
- DAPR pub/sub is available for future event emission

**From Story 2.2:**
- SourceConfig Pydantic models in `fp-common`
- Source configs deployed to `source_configs` collection
- Validation schemas in `validation_schemas` collection

### References

- [Source: _bmad-output/architecture/collection-model-architecture.md] - Full architecture design
- [Source: _bmad-output/epics.md#story-23] - Epic story definition
- [Source: _bmad-output/project-context.md] - Coding standards and rules
- [Source: Story 2.1] - Collection Model service setup
- [Source: Story 2.2] - Source Configuration CLI

---

## Out of Scope

- Blob content download and processing (Story 2.4)
- QC Analyzer ZIP file processing (Story 2.5)
- Deduplication of processed documents (Story 2.6)
- Domain event emission after processing (Story 2.10)
- Actual LLM extraction (Story 2.4)

---

## Definition of Done

- [ ] SourceConfigService can look up configs by container name
- [ ] SourceConfigService caches configs with 5-minute TTL
- [ ] Path pattern metadata extraction works correctly
- [ ] Ingestion jobs are queued in MongoDB with status "queued"
- [ ] Idempotency check prevents duplicate processing (same blob_path + etag)
- [ ] Unmatched containers logged with warning
- [ ] Unit tests passing (target: 15+ tests)
- [ ] CI passes (lint, format, tests)
- [ ] Code reviewed and merged

---

## Dev Agent Record

### Agent Model Used

(To be filled after implementation)

### Debug Log References

(To be filled after implementation)

### Completion Notes List

(To be filled after implementation)

### File List

**To Create:**
- `services/collection-model/src/collection_model/services/source_config_service.py`
- `services/collection-model/src/collection_model/domain/ingestion_job.py`
- `services/collection-model/src/collection_model/infrastructure/ingestion_queue.py`
- `tests/unit/collection/test_source_config_service.py`
- `tests/unit/collection/test_ingestion_queue.py`

**To Modify:**
- `services/collection-model/src/collection_model/api/events.py`
- `services/collection-model/src/collection_model/main.py` (add service initialization)
