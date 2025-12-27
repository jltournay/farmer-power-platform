# Story 2.4: Generic Content Processing Framework + JSON Processor

**Status:** ready-for-dev
**GitHub Issue:** <!-- To be created by dev-story workflow -->

---

## Story

As a **platform operator**,
I want a generic, configuration-driven content processing framework,
So that new data sources can be processed without code changes to the core pipeline.

As a **platform data analyst**,
I want QC Analyzer JSON results automatically ingested,
So that bag summaries and grading data are stored for analysis.

---

## Acceptance Criteria

### Framework (Generic)

1. **Given** an ingestion job is dequeued for processing
   **When** the processor is selected
   **Then** the `ingestion.processor_type` field from SourceConfig determines which ContentProcessor is used
   **And** no hardcoded source_type checks exist in the pipeline
   **And** the ProcessorRegistry returns the appropriate processor class

**Note:** `ingestion.processor_type` selects the ContentProcessor class (technical concern). `transformation.ai_agent_id` specifies the AI Model extraction agent (semantic concern). These are SEPARATE concerns.

2. **Given** a new source type needs to be added
   **When** a developer implements ContentProcessor
   **Then** they only need to:
     1. Create a new processor class implementing `ContentProcessor` ABC
     2. Register it in `ProcessorRegistry` with the `ingestion.processor_type` key
     3. Add source configuration YAML with matching `ingestion.processor_type`
   **And** no changes to the core pipeline code are required

3. **Given** an unknown `ingestion.processor_type` value is encountered
   **When** the processor lookup fails
   **Then** processing_status is set to "failed"
   **And** error details include: "No processor registered for processor_type: {processor_type}"
   **And** the job is not retried (configuration error, not transient)

### JSON Processor (QC Analyzer Results)

4. **Given** a JSON blob is queued for processing
   **When** the `JsonExtractionProcessor` is invoked
   **Then** the blob is downloaded from Azure Blob Storage (async streaming)
   **And** the raw JSON is stored in `raw_documents` collection
   **And** processing_status is updated to "extracting"

5. **Given** the raw JSON is stored
   **When** extraction is requested from AI Model via DAPR Service Invocation
   **Then** AI Model runs LLM extraction with configured prompt
   **And** structured data is returned as-is (no business logic applied)
   **And** extracted data is stored in collection specified by `storage.index_collection` from source config

**Note:** Storage is fully config-driven. Collection Model does NOT hardcode collection names.

6. **Given** extraction succeeds
   **When** the document is stored
   **Then** a domain event is emitted via DAPR Pub/Sub using topic from `events.on_success.topic` in source config
   **And** processing_status is updated to "completed"
   **And** the event payload includes fields specified in `events.on_success.payload_fields` from source config

**Note:** Event emission is fully config-driven. Collection Model does NOT hardcode event topics.

8. **Given** LLM extraction fails
   **When** error is detected
   **Then** processing_status is set to "failed"
   **And** error details are stored: error_type, error_message, retry_count
   **And** document is queued for retry (max 3 attempts)

---

## Tasks / Subtasks

### Task 0: Extend IngestionJob Model from Story 2.3 (AC: #4, #8)

**Coherence fix:** Story 2.3 implemented `IngestionJob` but it needs extension for Story 2.4.

- [ ] 0.1 Add `"extracting"` to status Literal in `domain/ingestion_job.py`:
  ```python
  status: Literal["queued", "processing", "extracting", "completed", "failed"]
  ```
- [ ] 0.2 Add `retry_count` field for retry tracking:
  ```python
  retry_count: int = Field(default=0, description="Number of retry attempts")
  ```
- [ ] 0.3 Add `error_type` field for error classification:
  ```python
  error_type: Literal["extraction", "storage", "validation", "config"] | None = Field(
      default=None, description="Type of error if failed"
  )
  ```
- [ ] 0.4 Update `IngestionQueue.update_job_status()` to support new fields
- [ ] 0.5 Add `IngestionQueue.increment_retry_count()` method
- [ ] 0.6 Write unit tests for new fields and methods

### Task 1: Create Content Processing Framework (AC: #1, #2, #3)

- [ ] 1.1 Create `processors/` package in `collection_model/` directory
- [ ] 1.2 Create `processors/base.py` with:
  - `ContentProcessor` ABC with `process()` and `supports_content_type()` abstract methods
  - `ProcessorResult` Pydantic model (success, document_id, extracted_data, error_message)
  - `ProcessorNotFoundError` custom exception
- [ ] 1.3 Create `processors/registry.py` with:
  - `ProcessorRegistry` class with `register()` and `get_processor()` class methods
  - `_processors: dict[str, type[ContentProcessor]]` class variable
  - Return instantiated processor from `get_processor()`
- [ ] 1.4 Create `processors/__init__.py` with processor registration on import
- [ ] 1.5 Write unit tests for ProcessorRegistry (registration, lookup, missing agent error)

### Task 2: Create Content Processor Worker (AC: #1, #3)

- [ ] 2.1 Create `services/content_processor_worker.py` with:
  - `process_pending_jobs()` async function that polls `ingestion_queue`
  - Pure config-driven processor selection via `ProcessorRegistry.get_processor(processor_type)`
  - Reads `ingestion.processor_type` from source config (NOT `transformation.agent`)
  - Status updates: "queued" -> "processing" -> "extracting" -> "completed"/"failed"
- [ ] 2.2 Implement job status update methods in `IngestionQueue`:
  - `update_status(ingestion_id, status, error_message=None)`
  - `increment_retry_count(ingestion_id)` with max 3 retries
- [ ] 2.3 Integrate worker into `main.py` lifespan (background task with asyncio.create_task)
- [ ] 2.4 Add configuration for worker poll interval (default: 5 seconds)
- [ ] 2.5 Write unit tests for worker (job processing, status transitions, retry logic)

### Task 3: Implement Azure Blob Storage Client (AC: #4)

- [ ] 3.1 Create `infrastructure/blob_storage.py` with:
  - `BlobStorageClient` class with async download and upload methods
  - Use `azure.storage.blob.aio` for async operations
  - Streaming download to handle large files
- [ ] 3.2 Add blob storage connection config to `config.py`
- [ ] 3.3 Implement `download_blob(container, blob_path)` -> bytes
- [ ] 3.4 Implement `upload_blob(container, blob_path, content, content_type)` -> BlobReference
- [ ] 3.5 Write unit tests with mocked blob client

### Task 4: Create Raw Document Storage (AC: #4)

- [ ] 4.1 Create `infrastructure/raw_document_store.py` with:
  - `store_raw_document(content, source_config)` -> BlobReference
  - Compute SHA-256 content hash for deduplication
  - Store to appropriate raw container from source_config
- [ ] 4.2 Create `raw_documents` MongoDB collection schema
- [ ] 4.3 Create `domain/raw_document.py` with Pydantic model:
  - document_id, source_id, blob_reference, content_hash, stored_at
- [ ] 4.4 Implement `RawDocumentRepository` with CRUD operations
- [ ] 4.5 Write unit tests for raw document storage

### Task 5: Implement AI Model Client (AC: #5)

- [ ] 5.1 Create `infrastructure/ai_model_client.py` with:
  - `AiModelClient` class for DAPR Service Invocation to AI Model
  - `extract_structured_data(raw_content, ai_agent_id, source_config)` -> ExtractionResult
  - Reads `transformation.ai_agent_id` from source config
  - Uses DAPR HTTP client to call `ai-model` service
- [ ] 5.2 Create `domain/extraction_result.py` with Pydantic model:
  - extracted_fields: dict, confidence: float, validation_passed: bool, warnings: list[str]
- [ ] 5.3 Define request/response schemas for AI Model extraction endpoint
- [ ] 5.4 Add DAPR app-id configuration for AI Model service
- [ ] 5.5 Write unit tests with mocked DAPR client (use fixtures from `tests/fixtures/llm_responses/`)

**CRITICAL:** Collection Model does NOT call LLM directly. All LLM calls go through AI Model via DAPR Service Invocation. Prompts are owned by AI Model.

### Task 6: Implement JsonExtractionProcessor (AC: #4, #5, #6, #7)

- [ ] 6.1 Create `processors/json_extraction.py` with:
  - `JsonExtractionProcessor(ContentProcessor)` class
  - `process(job, source_config)` implementation
  - `supports_content_type("application/json")` returns True
- [ ] 6.2 Implement GENERIC processing pipeline in `process()`:
  1. Download blob from Azure Blob Storage
  2. Store raw document with content hash
  3. Call AI Model via DAPR Service Invocation for extraction
  4. Store extracted data AS-IS (no business logic!) to collection from `source_config.storage.index_collection`
  5. Emit domain event to topic from `source_config.events.on_success.topic`
- [ ] 6.3 Register processor: `ProcessorRegistry.register("json-extraction", JsonExtractionProcessor)`
- [ ] 6.4 Write unit tests for JsonExtractionProcessor (mock blob storage, AI Model, MongoDB)

**CRITICAL:** JsonExtractionProcessor is GENERIC:
- NO `bag_summary` calculation (business logic belongs to Plantation Model)
- NO hardcoded collection names (use `source_config.storage.index_collection`)
- NO hardcoded event topics (use `source_config.events.on_success.topic`)
- Stores `extracted_fields` from AI Model AS-IS

### Task 7: Extend SourceConfig Schema (AC: #1, #6)

**Coherence fix:** Adds `processor_type` to `IngestionConfig` and `EventsConfig` to root model.

- [ ] 7.1 Add `processor_type` to `IngestionConfig` in `libs/fp-common/fp_common/models/source_config.py`:
  ```python
  class IngestionConfig(BaseModel):
      # ... existing fields ...
      processor_type: str | None = Field(
          None,
          description="ContentProcessor type for ProcessorRegistry lookup (e.g., 'json-extraction')"
      )
  ```
- [ ] 7.2 Rename `transformation.agent` to `transformation.ai_agent_id` for clarity:
  ```python
  class TransformationConfig(BaseModel):
      ai_agent_id: str = Field(..., description="AI Model agent ID for LLM extraction")
      # Keep 'agent' as deprecated alias for backward compatibility
      # ... rest of fields ...
  ```
- [ ] 7.3 Add `EventsConfig` to `libs/fp-common/fp_common/models/source_config.py`:
  ```python
  class EventConfig(BaseModel):
      topic: str  # e.g., "collection.quality_result.received"
      payload_fields: list[str]  # Fields to include in event payload

  class EventsConfig(BaseModel):
      on_success: EventConfig | None = None
      on_failure: EventConfig | None = None
  ```
- [ ] 7.4 Add `events: EventsConfig | None` to root `SourceConfig` model
- [ ] 7.5 Update source config YAML files with:
  - `ingestion.processor_type: json-extraction`
  - `transformation.ai_agent_id` (rename from `agent`)
  - `events` section
- [ ] 7.6 Run `fp-source-config validate` to verify schema changes
- [ ] 7.7 Deploy updated configs with `fp-source-config deploy --env dev`

### Task 8: Create Generic Document Storage (AC: #5)

- [ ] 8.1 Create `domain/document_index.py` with:
  - `DocumentIndex` Pydantic model inheriting from `BaseDocumentIndex`
  - `extracted_fields: dict[str, Any]` for storing any extracted data
  - Linkage fields dynamically populated from `transformation.extract_fields`
- [ ] 8.2 Create `infrastructure/document_repository.py` with:
  - `DocumentRepository` class with `collection_name` parameter
  - `save(document, collection_name)` -> document_id (collection from config!)
  - `get_by_id(document_id, collection_name)` -> DocumentIndex
- [ ] 8.3 Create indexes dynamically based on `transformation.link_field`
- [ ] 8.4 Write unit tests for generic repository

**CRITICAL:** Repository does NOT hardcode collection names. Collection comes from `storage.index_collection` in source config.

### Task 9: Implement Config-Driven Event Emission (AC: #6)

- [ ] 9.1 Create `infrastructure/dapr_pubsub.py` with:
  - `DaprEventPublisher` class using DAPR Pub/Sub HTTP API
  - `publish(topic, payload)` - topic from config, NOT hardcoded
- [ ] 9.2 Create `domain/events/document_event.py` with:
  - `DocumentProcessedEvent` generic Pydantic model
  - Payload fields populated from `events.on_success.payload_fields` config
- [ ] 9.3 Integrate event emission into processor using source config
- [ ] 9.4 Write unit tests for event publishing (mock DAPR HTTP client)

**CRITICAL:** Event topic comes from `events.on_success.topic` in source config. Collection Model does NOT hardcode topics.

### Task 10: Implement Error Handling and Retry Logic (AC: #3, #7)

- [ ] 10.1 Create custom exceptions in `domain/exceptions.py`:
  - `ProcessorNotFoundError` (config error, no retry)
  - `ExtractionError` (LLM failure, retry)
  - `StorageError` (transient, retry)
- [ ] 10.2 Implement retry logic in worker:
  - Max 3 attempts with exponential backoff
  - Store retry_count and last_error in ingestion_queue
  - Move to dead-letter after max retries
- [ ] 10.3 Add error metrics via OpenTelemetry:
  - `collection.processing.errors` counter with labels (source_id, error_type)
- [ ] 10.4 Write unit tests for error handling and retry scenarios

### Task 11: Write Integration Tests

- [ ] 11.1 Create integration test: Event Grid -> Ingestion Queue -> Processor -> Storage
- [ ] 11.2 Create golden sample test for JSON extraction (config-driven)
- [ ] 11.3 Test full pipeline with sample payload verifying config-driven storage and events
- [ ] 11.4 Verify metrics are emitted correctly

---

## Dev Notes

### Framework Architecture

```
services/collection-model/src/collection_model/
├── processors/                    # NEW: Content Processing Framework
│   ├── __init__.py               # Processor registration
│   ├── base.py                   # ContentProcessor ABC, ProcessorResult
│   ├── registry.py               # ProcessorRegistry
│   └── json_extraction.py        # JsonExtractionProcessor
├── domain/
│   ├── ingestion_job.py          # EXISTS from Story 2.3
│   ├── base_document.py          # NEW: BaseDocumentIndex base class
│   ├── document_index.py         # NEW: Generic DocumentIndex model
│   ├── raw_document.py           # NEW: Raw document model
│   ├── extraction_result.py      # NEW: Extraction result from AI Model
│   ├── exceptions.py             # NEW: Custom exceptions
│   └── events/
│       └── document_event.py     # NEW: Generic DocumentProcessedEvent
# NOTE: No grading.py - grading is owned by Plantation Model
# NOTE: No source-specific models - DocumentIndex is generic for ALL sources
├── services/
│   ├── source_config_service.py  # EXISTS from Story 2.3
│   └── content_processor_worker.py  # NEW: Background worker
├── infrastructure/
│   ├── ingestion_queue.py        # EXISTS from Story 2.3 (enhanced)
│   ├── blob_storage.py           # NEW: Azure Blob client
│   ├── raw_document_store.py     # NEW: Raw document storage
│   ├── document_repository.py    # NEW: Generic document repo (collection from config)
│   ├── ai_model_client.py        # NEW: DAPR client for AI Model
│   └── dapr_pubsub.py            # NEW: DAPR Pub/Sub client (topic from config)
```

### Inter-Service Communication

```
┌─────────────────────┐         DAPR Service Invocation        ┌─────────────────────┐
│   Collection Model  │ ──────────────────────────────────────▶│     AI Model        │
│                     │                                         │                     │
│  JsonExtraction-    │   POST /extract                        │  - Prompt storage   │
│  Processor          │   {raw_content, agent_id, config}      │  - LLM orchestration│
│                     │◀──────────────────────────────────────  │  - OpenRouter calls │
│                     │   {extracted_fields, confidence}        │                     │
└─────────────────────┘                                         └─────────────────────┘
         │
         │ DAPR Pub/Sub
         ▼
┌─────────────────────┐
│  collection-events  │   Topic: collection.quality_result.received
│     (Redis)         │
└─────────────────────┘
```

**CRITICAL Architecture Rules:**
1. **Collection Model does NOT call LLM directly** - All LLM calls via AI Model
2. **Inter-service calls use DAPR Service Invocation** - Not direct HTTP
3. **Domain events use DAPR Pub/Sub** - Not direct Redis
4. **Prompts owned by AI Model** - Collection Model only sends agent_id

### ContentProcessor ABC

```python
# processors/base.py
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from collection_model.domain.ingestion_job import IngestionJob


class ProcessorResult(BaseModel):
    """Result of content processing."""
    success: bool
    document_id: str | None = None
    extracted_data: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    error_type: str | None = None  # "extraction", "storage", "validation"


class ProcessorNotFoundError(Exception):
    """Raised when no processor is registered for the given agent."""
    pass


class ContentProcessor(ABC):
    """Base class for all content processors.

    Extend this class to add new source type support.
    Register with ProcessorRegistry using ingestion.processor_type key.
    """

    @abstractmethod
    async def process(
        self,
        job: IngestionJob,
        source_config: dict[str, Any],
    ) -> ProcessorResult:
        """Process the ingestion job according to source config.

        Args:
            job: The queued ingestion job with blob path and metadata
            source_config: Full source configuration from MongoDB

        Returns:
            ProcessorResult with success status and extracted data
        """
        pass

    @abstractmethod
    def supports_content_type(self, content_type: str) -> bool:
        """Check if processor supports the given content type.

        Args:
            content_type: MIME type (e.g., "application/json", "application/zip")

        Returns:
            True if this processor can handle the content type
        """
        pass
```

### ProcessorRegistry

```python
# processors/registry.py
from typing import Type

from .base import ContentProcessor, ProcessorNotFoundError


class ProcessorRegistry:
    """Maps ingestion.processor_type values to processor classes.

    Usage:
        # Registration (in __init__.py)
        ProcessorRegistry.register("json-extraction", JsonExtractionProcessor)

        # Lookup (in worker)
        processor = ProcessorRegistry.get_processor("json-extraction")
        result = await processor.process(job, source_config)
    """

    _processors: dict[str, Type[ContentProcessor]] = {}

    @classmethod
    def register(cls, processor_type: str, processor_class: Type[ContentProcessor]) -> None:
        """Register a processor class for a processor_type.

        Args:
            processor_type: The ingestion.processor_type value from source config
            processor_class: The ContentProcessor subclass to instantiate
        """
        cls._processors[processor_type] = processor_class

    @classmethod
    def get_processor(cls, processor_type: str) -> ContentProcessor:
        """Get an instantiated processor for the given processor_type.

        Args:
            processor_type: The ingestion.processor_type value from source config

        Returns:
            Instantiated ContentProcessor

        Raises:
            ProcessorNotFoundError: If no processor is registered for processor_type
        """
        if processor_type not in cls._processors:
            raise ProcessorNotFoundError(
                f"No processor registered for processor_type: {processor_type}"
            )
        return cls._processors[processor_type]()

    @classmethod
    def list_registered(cls) -> list[str]:
        """List all registered agent names."""
        return list(cls._processors.keys())
```

### AI Model Contract (DAPR Service Invocation)

```python
# infrastructure/ai_model_client.py
from pydantic import BaseModel, Field


class ExtractionRequest(BaseModel):
    """Request to AI Model for structured extraction."""
    raw_content: str
    ai_agent_id: str  # e.g., "qc-result-extraction-agent" (from transformation.ai_agent_id)
    source_config: dict  # Extraction hints from source configuration
    content_type: str = "application/json"


class ExtractionResponse(BaseModel):
    """Response from AI Model extraction."""
    extracted_fields: dict  # Structured data extracted by LLM
    confidence: float = Field(ge=0.0, le=1.0)
    validation_passed: bool
    validation_warnings: list[str] = Field(default_factory=list)


class AiModelClient:
    """DAPR Service Invocation client for AI Model.

    All LLM calls go through AI Model - Collection Model never calls LLM directly.
    """

    def __init__(self, dapr_http_port: int = 3500):
        self.base_url = f"http://localhost:{dapr_http_port}"
        self.ai_model_app_id = "ai-model"

    async def extract(self, request: ExtractionRequest) -> ExtractionResponse:
        """Call AI Model to extract structured data from raw content.

        Uses DAPR Service Invocation:
        POST http://localhost:3500/v1.0/invoke/ai-model/method/extract
        """
        url = f"{self.base_url}/v1.0/invoke/{self.ai_model_app_id}/method/extract"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=request.model_dump(),
                timeout=60.0,  # LLM calls can be slow
            )
            response.raise_for_status()
            return ExtractionResponse.model_validate(response.json())
```

**Note:** AI Model service must implement the `/extract` endpoint. If AI Model doesn't exist yet, use mock responses in tests.

### Worker Pipeline Integration

```python
# services/content_processor_worker.py
import asyncio
import structlog

from collection_model.domain.exceptions import ProcessorNotFoundError
from collection_model.infrastructure.ingestion_queue import IngestionQueue
from collection_model.processors.registry import ProcessorRegistry
from collection_model.services.source_config_service import SourceConfigService

logger = structlog.get_logger()


class ContentProcessorWorker:
    """Background worker that processes queued ingestion jobs."""

    def __init__(
        self,
        ingestion_queue: IngestionQueue,
        source_config_service: SourceConfigService,
        poll_interval: float = 5.0,
    ):
        self.queue = ingestion_queue
        self.config_service = source_config_service
        self.poll_interval = poll_interval
        self._running = False

    async def start(self) -> None:
        """Start the worker loop."""
        self._running = True
        logger.info("Content processor worker started")

        while self._running:
            try:
                await self._process_pending_jobs()
            except Exception as e:
                logger.exception("Worker loop error", error=str(e))

            await asyncio.sleep(self.poll_interval)

    async def stop(self) -> None:
        """Stop the worker loop."""
        self._running = False
        logger.info("Content processor worker stopped")

    async def _process_pending_jobs(self) -> None:
        """Process all pending jobs in the queue."""
        jobs = await self.queue.get_pending_jobs(limit=10)

        for job in jobs:
            await self._process_job(job)

    async def _process_job(self, job) -> None:
        """Process a single ingestion job."""
        logger.info(
            "Processing job",
            ingestion_id=job.ingestion_id,
            source_id=job.source_id,
            blob_path=job.blob_path,
        )

        try:
            # Update status to processing
            await self.queue.update_status(job.ingestion_id, "processing")

            # Get source config
            source_config = await self.config_service.get_config_by_source_id(job.source_id)
            if not source_config:
                raise ValueError(f"Source config not found: {job.source_id}")

            # Get processor based on ingestion.processor_type - PURE CONFIG-DRIVEN
            processor_type = source_config.get("config", {}).get("ingestion", {}).get("processor_type")
            if not processor_type:
                raise ValueError(f"No ingestion.processor_type in source config: {job.source_id}")

            processor = ProcessorRegistry.get_processor(processor_type)  # No hardcoded checks!

            # Process the job
            result = await processor.process(job, source_config)

            if result.success:
                await self.queue.update_status(
                    job.ingestion_id,
                    "completed",
                    document_id=result.document_id,
                )
                logger.info(
                    "Job completed successfully",
                    ingestion_id=job.ingestion_id,
                    document_id=result.document_id,
                )
            else:
                await self._handle_failure(job, result.error_message, result.error_type)

        except ProcessorNotFoundError as e:
            # Configuration error - do not retry
            await self.queue.update_status(
                job.ingestion_id,
                "failed",
                error_message=str(e),
                no_retry=True,
            )
            logger.error("Processor not found", error=str(e), source_id=job.source_id)

        except Exception as e:
            await self._handle_failure(job, str(e), "unknown")

    async def _handle_failure(self, job, error_message: str, error_type: str) -> None:
        """Handle job failure with retry logic."""
        retry_count = await self.queue.increment_retry_count(job.ingestion_id)

        if retry_count >= 3:
            await self.queue.update_status(
                job.ingestion_id,
                "failed",
                error_message=error_message,
            )
            logger.error(
                "Job failed after max retries",
                ingestion_id=job.ingestion_id,
                retry_count=retry_count,
                error=error_message,
            )
        else:
            await self.queue.update_status(
                job.ingestion_id,
                "queued",  # Re-queue for retry
                error_message=error_message,
            )
            logger.warning(
                "Job failed, will retry",
                ingestion_id=job.ingestion_id,
                retry_count=retry_count,
                error=error_message,
            )
```

### BaseDocumentIndex (Architecture Base Class)

```python
# domain/base_document.py
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class RawDocumentRef(BaseModel):
    """Reference to raw document in blob storage."""
    blob_container: str
    blob_path: str
    content_hash: str  # SHA-256
    size_bytes: int
    stored_at: datetime


class ExtractionMetadata(BaseModel):
    """Metadata about the AI Model extraction."""
    ai_agent_id: str
    extraction_timestamp: datetime
    confidence: float = Field(ge=0.0, le=1.0)
    validation_passed: bool
    validation_warnings: list[str] = Field(default_factory=list)


class IngestionMetadata(BaseModel):
    """Metadata about the ingestion process."""
    ingestion_id: str
    source_id: str
    received_at: datetime
    processed_at: datetime


class BaseDocumentIndex(BaseModel):
    """Base class for all document indexes in Collection Model.

    All extracted documents inherit from this to ensure consistent structure.
    """
    document_id: str
    raw_document: RawDocumentRef
    extraction: ExtractionMetadata
    ingestion: IngestionMetadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DocumentIndex(BaseDocumentIndex):
    """Generic document index for ANY source type.

    Stores extracted fields as-is from AI Model.
    NO business logic - Collection Model only collects and extracts.
    Stored in collection specified by source_config.storage.index_collection.
    """
    # Extracted fields from AI Model (stored as-is)
    extracted_fields: dict[str, Any]

    # Dynamic linkage fields (populated from transformation.extract_fields)
    # These are copied from extracted_fields for indexing purposes
    linkage_fields: dict[str, Any] = Field(default_factory=dict)

# NOTE: This is a GENERIC model - same model for ALL source types
# The collection name comes from config: source_config.storage.index_collection
# Examples:
#   - qc-analyzer-result -> quality_results_index
#   - weather-api -> weather_data_index
#   - market-prices -> market_prices_index
```

### Technology Stack

| Component | Choice | Version |
|-----------|--------|---------|
| Language | Python | 3.12 |
| Web Framework | FastAPI | Latest |
| Validation | Pydantic | 2.0+ |
| MongoDB Driver | Motor (async) | Latest |
| Azure Blob SDK | azure-storage-blob | Latest (async) |
| Inter-service | DAPR | Service Invocation |
| Pub/Sub | DAPR | Redis backend |
| Metrics | OpenTelemetry | Latest |

### Critical Implementation Rules

**From project-context.md:**

1. **ALL I/O operations MUST be async** - Use `async def` for all database, blob, and DAPR operations
2. **Use Pydantic 2.0 syntax** - `model_dump()` not `dict()`, `model_validate()` not `parse_obj()`
3. **Type hints required** - ALL function signatures MUST have type hints
4. **Absolute imports only** - No relative imports
5. **Open/Closed Principle** - New processors extend framework, never modify core pipeline
6. **LLM calls via AI Model** - Collection Model NEVER calls LLM directly, always via DAPR to AI Model
7. **Domain events via DAPR Pub/Sub** - Never direct Redis access

### Source Configuration (QC Analyzer Result)

From `config/source-configs/qc-analyzer-result.yaml` (after Story 2.4 updates):

```yaml
source_id: qc-analyzer-result
display_name: QC Analyzer - Bag Result

ingestion:
  mode: blob_trigger
  landing_container: qc-analyzer-landing
  processor_type: json-extraction  # NEW: Maps to ProcessorRegistry (technical concern)
  path_pattern:
    pattern: "results/{plantation_id}/{crop}/{market}/{batch_id}.json"
    extract_fields: [plantation_id, crop, market, batch_id]
  file_format: json
  trigger_mechanism: event_grid

transformation:
  ai_agent_id: qc-result-extraction-agent  # RENAMED: AI Model agent ID (semantic concern)
  extract_fields:
    - plantation_id
    - factory_id
    - collection_point_id
    - grading_model_id
    - grading_model_version
    - batch_timestamp
    - bag_summary
  link_field: plantation_id
  field_mappings:
    plantation_id: farmer_id

storage:
  raw_container: quality-results-raw
  index_collection: quality_results_index  # Config-driven! Processor reads this.

events:  # NEW: Config-driven event emission
  on_success:
    topic: collection.quality_result.received  # DAPR Pub/Sub topic
    payload_fields:  # Fields to include in event payload
      - document_id
      - source_id
      - farmer_id
      - batch_id
  on_failure:
    topic: collection.processing.failed
    payload_fields:
      - document_id
      - source_id
      - error_type
      - error_message
```

**Separation of Concerns:**
- `ingestion.processor_type: json-extraction` → Selects `JsonExtractionProcessor` class (technical)
- `transformation.ai_agent_id: qc-result-extraction-agent` → AI Model extraction agent (semantic)

**Generic Pipeline Pattern:**
```python
# In JsonExtractionProcessor - FULLY CONFIG-DRIVEN
async def process(self, job, source_config):
    # 1. Download blob
    # 2. Extract via AI Model

    # 3. Store to collection FROM CONFIG (not hardcoded!)
    collection = source_config["storage"]["index_collection"]
    await self.doc_repo.save(document, collection=collection)

    # 4. Emit event FROM CONFIG (not hardcoded!)
    event_config = source_config["events"]["on_success"]
    topic = event_config["topic"]
    payload = {f: getattr(document, f) for f in event_config["payload_fields"]}
    await self.event_publisher.publish(topic, payload)
```

### MongoDB Collections

| Collection | Purpose | Key Indexes |
|------------|---------|-------------|
| `ingestion_queue` | Queued jobs (from Story 2.3) | (blob_path, blob_etag) unique |
| `raw_documents` | Raw blob references | (source_id, content_hash) unique |
| `{config-driven}` | Extracted document data | Dynamic based on `transformation.link_field` |

**Config-Driven Collections:**
- Collection name comes from `storage.index_collection` in source config
- Examples: `quality_results_index`, `weather_data_index`, `market_prices_index`
- Indexes created dynamically based on `transformation.link_field`

**Note:** `prompts` collection is owned by AI Model, not Collection Model.

### Testing Strategy

| Test Type | What to Test | Mocking Required |
|-----------|--------------|------------------|
| Unit | ProcessorRegistry lookup | None |
| Unit | ContentProcessor.process() | mock blob, AI Model client, MongoDB |
| Unit | TBK grade calculation | None (pure function) |
| Unit | Worker job processing | mock queue, config service |
| Unit | DAPR Pub/Sub emission | mock DAPR HTTP client |
| Integration | Full pipeline | mock AI Model, blob storage |
| Golden | QC Analyzer extraction | mock AI Model with fixture responses |

### Previous Story Learnings (Stories 2.2, 2.3)

**From Story 2.2 (Source Configuration CLI):**
1. **SourceConfig** Pydantic model exists in `libs/fp-common/fp_common/models/source_config.py`
2. Must extend with `processor_type` in `IngestionConfig` and `ai_agent_id` in `TransformationConfig`
3. Must add `EventsConfig` for config-driven event emission
4. CLI already validates against SourceConfig schema - no CLI changes needed

**From Story 2.3 (Event Grid Trigger Handler):**
1. **SourceConfigService** exists with 5-min TTL cache - reuse for config lookups
2. **IngestionJob** model exists - extend with `extracting` status, `retry_count`, `error_type`
3. **IngestionQueue** exists - enhance with `increment_retry_count()`
4. **OpenTelemetry metrics** pattern established - follow for new metrics
5. **Event Grid handler** queues jobs to `ingestion_queue` - worker consumes from there

### References

- [Source: _bmad-output/architecture/collection-model-architecture.md] - Full architecture design
- [Source: _bmad-output/epics.md#story-24] - Epic story definition (revised with generic framework)
- [Source: _bmad-output/project-context.md] - Coding standards and rules
- [Source: Story 2.3] - Event Grid Trigger Handler (ingestion queue, source config service)
- [Source: Story 2.2] - Source Configuration CLI (source config structure)

---

## Out of Scope

- ZIP file processing (Story 2.5 - ZipExtractionProcessor)
- Content-level deduplication (Story 2.6 - uses content_hash from this story)
- Weather API pull mode (Story 2.7)
- Market prices pull mode (Story 2.8)
- MCP server exposure (Story 2.9)

---

## Coherence Notes (Stories 2.2, 2.3 → 2.4)

**Review Date:** 2025-12-27
**Reviewed by:** Winston (Architect) & Bob (Scrum Master)

This story was reviewed for coherence with Stories 2.2 and 2.3 implementations.

### Issues Identified and Fixed

| Issue | Severity | Resolution |
|-------|----------|------------|
| `transformation.agent` used for two purposes | HIGH | Separated: `ingestion.processor_type` (technical) vs `transformation.ai_agent_id` (semantic) |
| IngestionJob missing `"extracting"` status | MEDIUM | Task 0 added to extend IngestionJob |
| IngestionJob missing `retry_count`, `error_type` | MEDIUM | Task 0 added to extend IngestionJob |
| SourceConfig missing `events` section | HIGH | Task 7 adds `EventsConfig` to fp-common |
| SourceConfig missing `processor_type` | HIGH | Task 7 adds `processor_type` to `IngestionConfig` |

### Backward Compatibility

- `transformation.agent` will be kept as deprecated alias for `transformation.ai_agent_id`
- Existing YAML files will continue to work during transition
- Task 7.2 handles the migration

### Alignment with Implemented Code

| Component | Story 2.2/2.3 Status | Story 2.4 Action |
|-----------|----------------------|------------------|
| `SourceConfig` in fp-common | ✓ Implemented | Extend with `processor_type`, `events` |
| `IngestionJob` model | ✓ Implemented | Extend with `extracting`, `retry_count`, `error_type` |
| `IngestionQueue` | ✓ Implemented | Add `increment_retry_count()` method |
| `SourceConfigService` | ✓ Implemented | Add `get_config_by_source_id()` method |

---

## Definition of Done

- [ ] IngestionJob extended with `extracting` status, `retry_count`, `error_type`
- [ ] ProcessorRegistry correctly maps `ingestion.processor_type` to processor classes
- [ ] JsonExtractionProcessor is FULLY GENERIC (no hardcoded collections/events)
- [ ] No hardcoded source_type checks in the pipeline
- [ ] No business logic (grading) in Collection Model
- [ ] Raw documents stored in Azure Blob with content hash
- [ ] Documents stored in collection from `storage.index_collection` config
- [ ] AI Model called via DAPR Service Invocation (no direct LLM calls)
- [ ] Domain events emitted to topic from `events.on_success.topic` config
- [ ] SourceConfig schema extended with `processor_type` in `IngestionConfig`
- [ ] SourceConfig schema extended with `ai_agent_id` in `TransformationConfig`
- [ ] SourceConfig schema extended with `EventsConfig` in fp-common
- [ ] Source config YAML files updated with `processor_type`, `ai_agent_id`, and `events` section
- [ ] Retry logic works correctly (max 3 attempts)
- [ ] Config errors (unknown processor_type) fail without retry
- [ ] Unit tests passing (target: 20+ tests)
- [ ] Integration test passing (full pipeline)
- [ ] CI passes (lint, format, tests)
- [ ] Code reviewed and merged

---

## Dev Agent Record

### Agent Model Used

<!-- Filled by dev agent -->

### Debug Log References

<!-- Filled by dev agent -->

### Completion Notes List

<!-- Filled by dev agent -->

### File List

<!-- Filled by dev agent -->
