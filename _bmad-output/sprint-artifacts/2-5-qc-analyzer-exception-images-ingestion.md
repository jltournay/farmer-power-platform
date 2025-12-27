# Story 2.5: ZIP Content Processor for Exception Images

**Status:** in-progress
**GitHub Issue:** #20

---

## Story

As a **Knowledge Model AI agent**,
I want secondary leaf exception images automatically extracted and stored,
So that I can analyze poor quality samples with visual evidence.

---

## Acceptance Criteria

### ZIP Processor Framework Integration

1. **Given** the Generic Content Processing Framework exists (Story 2.4)
   **When** a ZIP blob is queued for processing with `processor_type: zip-extraction`
   **Then** the `ZipExtractionProcessor` is selected via `ProcessorRegistry`
   **And** no changes to the core pipeline code are required

2. **Given** the `ZipExtractionProcessor` is invoked
   **When** the blob is downloaded
   **Then** the ZIP is extracted in memory (streaming, no disk write)
   **And** `manifest.json` is validated against `generic-zip-manifest.schema.json`
   **And** `payload` is validated against source-specific schema (`qc-exceptions-manifest.json`)

### File Extraction (Generic)

3. **Given** the manifest contains documents with file roles
   **When** files are processed per `manifest.documents[]`
   **Then** files with storable roles are extracted to container from `storage.file_container` config
   **And** blob path follows pattern from `storage.file_path_pattern` config
   **And** files with `role: metadata` are parsed and merged into document `extracted_fields`
   **And** `manifest.payload` (batch-level data) is merged into each document's `extracted_fields`

4. **Given** a metadata JSON file exists for a document
   **When** the metadata is parsed
   **Then** ALL fields from the metadata file are stored as-is in `extracted_fields`
   **And** NO field names are hardcoded - processor is agnostic to domain schema

### Document Storage (Single Collection, Config-Driven)

5. **Given** images and metadata are extracted
   **When** documents are stored
   **Then** a `DocumentIndex` is created in collection from `storage.index_collection` config
   **And** `linkage_fields` contains ALL fields from `manifest.linkage` AS-IS (no hardcoding)
   **And** `field_mappings` from config are applied to linkage_fields
   **And** `extracted_fields` contains ALL fields from metadata file AS-IS (no hardcoding)
   **And** `raw_document` references the original ZIP blob
   **And** `ingestion.source_id` is set from `manifest.source_id`

6. **Given** multiple documents exist in the manifest
   **When** all documents are stored
   **Then** each document gets a unique `document_id` following pattern: `{source_id}/{linkage[link_field]}/{manifest_doc_id}`
   **And** `link_field` is read from `transformation.link_field` config
   **And** all documents share the same `ingestion_id` (batch processing)

### Event Emission (Config-Driven)

7. **Given** all documents are stored successfully
   **When** processing completes
   **Then** a domain event is emitted to topic from `events.on_success.topic` config
   **And** processing_status is updated to "completed"
   **And** the event payload includes fields from `events.on_success.payload_fields` config
   **And** `document_count` is always included (framework-level field)

### Error Handling (Atomic - All or Nothing)

8. **Given** the ZIP is corrupted or invalid
   **When** extraction fails
   **Then** processing_status is set to "failed"
   **And** error details logged: "Invalid ZIP format" or "Missing manifest.json" or schema validation errors
   **And** original blob is retained for manual review
   **And** no partial documents are stored (atomic operation)

9. **Given** any file extraction or document storage fails
   **When** the error is detected
   **Then** the entire batch is rolled back (no documents stored)
   **And** processing_status is set to "failed"
   **And** error details include which file/document failed
   **And** original ZIP is retained for manual review and retry

---

## Tasks / Subtasks

### Task 1: Create ZipExtractionProcessor (AC: #1, #2)

- [x] 1.1 Create `processors/zip_extraction.py` with:
  - `ZipExtractionProcessor(ContentProcessor)` class
  - `process(job, source_config)` implementation
  - `supports_content_type("application/zip")` returns True
- [x] 1.2 Register processor: `ProcessorRegistry.register("zip-extraction", ZipExtractionProcessor)`
- [x] 1.3 Implement ZIP extraction using `zipfile` module with streaming (no temp files)
- [x] 1.4 Add max size validation (500MB) and max document count (10000)
- [x] 1.5 Write unit tests for ZipExtractionProcessor registration and content type support

### Task 2: Implement Manifest Validation (AC: #2)

- [x] 2.1 Create `domain/manifest.py` with Pydantic models:
  - `ZipManifest`, `ManifestDocument`, `ManifestFile` models
- [x] 2.2 Manifest validates required fields:
  - `manifest_version`, `source_id`, `created_at`, `documents[]`
- [x] 2.3 Implement `_extract_and_validate_manifest()` in processor
- [x] 2.4 Validation uses Pydantic for type safety and validation
- [x] 2.5 Write unit tests for manifest validation (valid, missing fields, invalid JSON)

### Task 3: Implement File Extraction (AC: #3)

- [x] 3.1 Create `_extract_and_store_file()` method in processor
- [x] 3.2 Process ALL files by role from `manifest.documents[].files[]`
- [x] 3.3 For storable roles (image, primary, thumbnail, attachment):
  - Upload to container from `storage.file_container` config
  - Generate blob path from `storage.file_path_pattern` config
- [x] 3.4 Implement `_build_blob_path()` for config-driven path patterns
- [x] 3.5 Merge `manifest.payload` into each document's `extracted_fields`
- [x] 3.6 Return `dict[str, list[BlobReference]]` keyed by role
- [x] 3.7 Write unit tests for file extraction (mock blob storage)

### Task 4: Implement Metadata Parsing (AC: #4)

- [x] 4.1 Metadata stored via `document.attributes` from manifest
- [x] 4.2 Parse ALL fields as-is into `dict[str, Any]` - NO field name hardcoding
- [x] 4.3 Handle missing attributes gracefully (empty dict)
- [x] 4.4 Merge with `manifest.payload` for batch-level data
- [x] 4.5 Write unit tests for metadata/attribute handling

### Task 5: Store Raw ZIP (AC: #5)

- [x] 5.1 Store original ZIP to `storage.raw_container` before processing
- [x] 5.2 Create `RawDocumentRef` with blob_path, content_hash, size_bytes
- [x] 5.3 Reuse `RawDocumentStore` from Story 2.4
- [x] 5.4 Write unit tests for raw ZIP storage

### Task 6: Implement Document Storage (AC: #5, #6)

- [x] 6.1 Create `DocumentIndex` for each manifest document with:
  - `document_id`: `{source_id}/{linkage[link_field]}/{manifest_document_id}` (pattern from config)
  - `linkage_fields`: ALL fields from `manifest.linkage` as-is (no hardcoding)
  - `extracted_fields`: metadata + `manifest.payload` merged (no hardcoding)
  - `raw_document`: reference to original ZIP blob
- [x] 6.2 Linkage fields copied AS-IS from manifest
- [x] 6.3 Store all documents to collection from `storage.index_collection` config
- [x] 6.4 Implement batch storage with error handling
- [x] 6.5 On any failure, raise BatchProcessingError
- [x] 6.6 Reuse `DocumentRepository` from Story 2.4
- [x] 6.7 Write unit tests for document creation and storage

### Task 7: Implement Event Emission (AC: #7)

- [x] 7.1 Emit event to topic from `events.on_success.topic` config (NO hardcoded topics)
- [x] 7.2 Build event payload from `events.on_success.payload_fields` config
- [x] 7.3 Include `document_count` in payload (framework-level, always present)
- [x] 7.4 Reuse `DaprEventPublisher` from Story 2.4
- [x] 7.5 Write unit tests for event emission (mock DAPR)

### Task 8: Implement Error Handling (AC: #8, #9)

- [x] 8.1 Add `ZipExtractionError`, `ManifestValidationError`, `BatchProcessingError` to `domain/exceptions.py`
- [x] 8.2 Handle corrupt ZIP files gracefully (catch `BadZipFile`)
- [x] 8.3 Handle missing manifest.json with clear error message
- [x] 8.4 Handle file not found in ZIP with clear error message
- [x] 8.5 Ensure no partial documents stored on fatal error (raise BatchProcessingError)
- [x] 8.6 Write unit tests for error scenarios

### Task 9: Update Source Configuration (AC: #1)

- [x] 9.1 Update `config/source-configs/qc-analyzer-exceptions.yaml`:
  - Set `ingestion.processor_type: zip-extraction`
  - Add `storage.file_container: exception-images`
  - Add `storage.file_path_pattern`
  - Verify `storage.index_collection: documents`
- [x] 9.2 Source config updated with new storage fields
- [ ] 9.3 Deploy with `fp-source-config deploy --env dev` (manual step)

### Task 10: Write Unit Tests

- [x] 10.1 Create test ZIP helper function with manifest and files
- [x] 10.2 Test full processor pipeline with mocks
- [x] 10.3 Test document creation with correct document_id format
- [x] 10.4 Test file extraction with config-driven paths
- [x] 10.5 Test event emission with correct payload
- [x] 10.6 Test error scenarios (corrupt ZIP, missing manifest, missing files)

---

## Dev Notes

### File Structure

```
services/collection-model/src/collection_model/
├── processors/
│   ├── __init__.py               # Add zip-extraction registration
│   ├── base.py                   # EXISTS from Story 2.4
│   ├── registry.py               # EXISTS from Story 2.4
│   ├── json_extraction.py        # EXISTS from Story 2.4
│   └── zip_extraction.py         # NEW: ZipExtractionProcessor
├── domain/
│   ├── document_index.py         # EXISTS - reuse DocumentIndex model
│   ├── exceptions.py             # EXTEND with ZipExtractionError
│   └── manifest.py               # NEW: Manifest Pydantic models
├── infrastructure/
│   ├── blob_storage.py           # EXISTS - reuse BlobStorageClient
│   ├── document_repository.py    # EXISTS - reuse DocumentRepository
│   └── dapr_event_publisher.py   # EXISTS - reuse DaprEventPublisher
config/
├── schemas/
│   ├── generic-zip-manifest.schema.json    # NEW: Generic manifest schema
│   └── data/
│       └── qc-exceptions-manifest.json     # NEW: Source-specific payload schema
```

### ZipExtractionProcessor Implementation Pattern

```python
# processors/zip_extraction.py
import zipfile
from io import BytesIO
from typing import Any

from collection_model.domain.document_index import DocumentIndex, RawDocumentRef
from collection_model.domain.exceptions import ZipExtractionError
from collection_model.infrastructure.blob_storage import BlobStorageClient
from collection_model.infrastructure.document_repository import DocumentRepository
from collection_model.infrastructure.dapr_event_publisher import DaprEventPublisher

from .base import ContentProcessor, ProcessorResult


class ZipExtractionProcessor(ContentProcessor):
    """Processor for ZIP files containing images and metadata.

    Implements the Generic ZIP Manifest Format from collection-model-architecture.md.
    """

    MAX_ZIP_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_IMAGES = 100
    ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png"}

    def __init__(
        self,
        blob_client: BlobStorageClient,
        doc_repo: DocumentRepository,
        event_publisher: DaprEventPublisher,
    ):
        self.blob_client = blob_client
        self.doc_repo = doc_repo
        self.event_publisher = event_publisher

    def supports_content_type(self, content_type: str) -> bool:
        return content_type in ("application/zip", "application/x-zip-compressed")

    async def process(
        self,
        job: "IngestionJob",
        source_config: dict[str, Any],
    ) -> ProcessorResult:
        """Process ZIP file with manifest and images."""
        try:
            # 1. Download ZIP blob
            zip_content = await self.blob_client.download_blob(
                container=source_config["config"]["ingestion"]["landing_container"],
                blob_path=job.blob_path,
            )

            # 2. Validate size
            if len(zip_content) > self.MAX_ZIP_SIZE:
                raise ZipExtractionError(f"ZIP exceeds max size: {len(zip_content)} > {self.MAX_ZIP_SIZE}")

            # 3. Extract and validate manifest
            manifest = self._extract_manifest(zip_content)
            self._validate_manifest(manifest, source_config)

            # 4. Store raw ZIP first (before processing)
            raw_zip_ref = await self._store_raw_zip(
                zip_content=zip_content,
                job=job,
                source_config=source_config,
            )

            # 5. Process each document in manifest
            documents = []
            for doc_entry in manifest["documents"]:
                doc = await self._process_document(
                    zip_content=zip_content,
                    doc_entry=doc_entry,
                    manifest=manifest,
                    raw_zip_ref=raw_zip_ref,
                    job=job,
                    source_config=source_config,
                )
                documents.append(doc)

            # 6. Store all documents atomically (using MongoDB transaction)
            collection = source_config["config"]["storage"]["index_collection"]
            await self.doc_repo.save_batch(
                documents=documents,
                collection=collection,
                atomic=True,  # All-or-nothing with transaction
            )

            # 7. Emit domain event
            await self._emit_success_event(
                documents=documents,
                manifest=manifest,
                source_config=source_config,
            )

            return ProcessorResult(
                success=True,
                document_id=documents[0].document_id if documents else None,
                extracted_data={"document_count": len(documents)},
            )

        except zipfile.BadZipFile as e:
            return ProcessorResult(
                success=False,
                error_message=f"Invalid ZIP format: {e}",
                error_type="validation",
            )
        except ZipExtractionError as e:
            return ProcessorResult(
                success=False,
                error_message=str(e),
                error_type="extraction",
            )
```

### Manifest Pydantic Models

```python
# domain/manifest.py
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ManifestFile(BaseModel):
    """File entry in manifest document."""
    path: str
    role: str  # image, metadata, primary, thumbnail, attachment
    mime_type: str | None = None
    size_bytes: int | None = None


class ManifestDocument(BaseModel):
    """Document entry in manifest."""
    document_id: str
    files: list[ManifestFile]
    attributes: dict[str, Any] | None = None  # Pre-extracted or from metadata file


class ZipManifest(BaseModel):
    """Generic ZIP manifest following collection-model-architecture.md spec."""
    manifest_version: str = "1.0"
    source_id: str
    created_at: datetime

    # Cross-reference fields for entity relationships
    linkage: dict[str, Any] = Field(default_factory=dict)

    # Documents in this ZIP
    documents: list[ManifestDocument]

    # Batch-level domain-specific data
    payload: dict[str, Any] = Field(default_factory=dict)
```

### File Extraction Pattern (Config-Driven)

```python
async def _extract_and_store_file(
    self,
    zip_file: zipfile.ZipFile,
    file_entry: ManifestFile,
    manifest: ZipManifest,
    doc_id: str,
    source_config: dict,
) -> BlobReference:
    """Extract single file and store to blob - FULLY CONFIG-DRIVEN."""
    # Extract file from ZIP (works for any file type: image, PDF, CSV, etc.)
    file_data = zip_file.read(file_entry.path)

    # Get container from config (NO hardcoded container names)
    container = source_config["config"]["storage"]["file_container"]

    # Build blob path from pattern in config
    # Example pattern: "{link_field}/{batch_id}/{doc_id}.{ext}"
    path_pattern = source_config["config"]["storage"].get(
        "file_path_pattern",
        "{source_id}/{doc_id}.{ext}"  # Default fallback
    )

    ext = file_entry.path.split(".")[-1]
    blob_path = path_pattern.format(
        source_id=manifest.source_id,
        doc_id=doc_id,
        ext=ext,
        **manifest.linkage,  # All linkage fields available for pattern
    )

    # Upload to blob storage
    return await self.blob_client.upload_blob(
        container=container,
        blob_path=blob_path,
        content=file_data,
        content_type=file_entry.mime_type or "application/octet-stream",
    )
```

### DocumentIndex Creation (Config-Driven)

```python
def _create_document_index(
    self,
    doc_entry: ManifestDocument,
    manifest: ZipManifest,
    file_refs: dict[str, list[BlobReference]],  # Keyed by role: {"image": [...], "metadata": [...]}
    raw_zip_ref: RawDocumentRef,
    job: "IngestionJob",
    source_config: dict,
) -> DocumentIndex:
    """Create DocumentIndex for a single manifest document - FULLY CONFIG-DRIVEN."""

    # Build globally unique document_id from config pattern
    # - manifest.source_id: identifies the source (e.g., "qc-analyzer-exceptions")
    # - link_value: from manifest.linkage using link_field config (e.g., batch_id value)
    # - doc_entry.document_id: local ID within manifest (e.g., "leaf_001")
    link_field = source_config["config"]["transformation"]["link_field"]
    link_value = manifest.linkage.get(link_field, "unknown")
    manifest_doc_id = doc_entry.document_id  # Local ID from manifest

    document_id = f"{manifest.source_id}/{link_value}/{manifest_doc_id}"

    # Copy ALL linkage fields as-is (NO hardcoding of field names)
    linkage_fields = dict(manifest.linkage)

    # Apply field mappings from config (e.g., plantation_id -> farmer_id)
    field_mappings = source_config["config"]["transformation"].get("field_mappings", {})
    for src, dst in field_mappings.items():
        if src in linkage_fields:
            linkage_fields[dst] = linkage_fields[src]

    # Get extracted fields from attributes - stored AS-IS (no validation of field names)
    extracted_fields = doc_entry.attributes or {}

    # Merge batch-level payload data (e.g., grading_model_id, grading_model_version)
    # This makes batch context available at document level for querying
    if manifest.payload:
        extracted_fields.update(manifest.payload)

    # Add file references by role (generic, not image-specific)
    extracted_fields["file_refs"] = {
        role: [ref.model_dump() for ref in refs]
        for role, refs in file_refs.items()
    }

    return DocumentIndex(
        document_id=document_id,
        raw_document=raw_zip_ref,
        extraction=ExtractionMetadata(
            ai_agent_id="zip-extraction",  # Processor type, not domain-specific
            extraction_timestamp=datetime.now(timezone.utc),
            confidence=1.0,  # Manifest is authoritative source
            validation_passed=True,
        ),
        ingestion=IngestionMetadata(
            ingestion_id=job.ingestion_id,
            source_id=manifest.source_id,
            received_at=job.received_at,
            processed_at=datetime.now(timezone.utc),
        ),
        extracted_fields=extracted_fields,  # Attributes + file_refs by role
        linkage_fields=linkage_fields,      # Whatever manifest.linkage contains
    )
```

### Source Configuration Reference (Example)

```yaml
# config/source-configs/qc-analyzer-exceptions.yaml
# This is ONE EXAMPLE - the processor is generic for ANY ZIP source

source_id: qc-analyzer-exceptions
display_name: QC Analyzer - Exception Images

ingestion:
  mode: blob_trigger
  processor_type: zip-extraction  # Maps to ZipExtractionProcessor (GENERIC)
  landing_container: qc-analyzer-landing
  path_pattern:
    pattern: "exceptions/{plantation_id}/{batch_id}.zip"
    extract_fields: [plantation_id, batch_id]
  file_format: zip
  trigger_mechanism: event_grid
  zip_config:
    manifest_file: manifest.json  # Standard manifest location
    images_folder: images         # Where images live in ZIP
    extract_images: true

validation:
  schema_name: data/qc-exceptions-manifest.json  # Source-specific payload schema
  strict: true

transformation:
  ai_agent_id: null  # Not used - manifest provides structured data
  extract_fields: []  # Linkage comes from manifest.linkage
  link_field: batch_id  # Used for document_id pattern
  field_mappings:
    plantation_id: farmer_id  # Domain-specific mapping

storage:
  raw_container: exception-images-raw
  file_container: exception-images        # Config-driven container (works for any file type)
  file_path_pattern: "{plantation_id}/{batch_id}/{doc_id}.{ext}"  # Config-driven path
  index_collection: documents             # Single collection for ALL sources
  ttl_days: 365

events:
  on_success:
    topic: collection.quality-exceptions.ingested  # Config-driven topic
    payload_fields:                                 # Config-driven fields
      - ingestion_id
      - source_id
      - document_count
  on_failure:
    topic: collection.processing.failed
    payload_fields:
      - source_id
      - error_type
      - error_message
```

**Key Principle:** The `ZipExtractionProcessor` reads ALL configuration from this YAML. It has ZERO knowledge of QC exceptions, leaf types, grading models, etc.

### ZIP Manifest Example (from Architecture)

```json
{
  "manifest_version": "1.0",
  "source_id": "qc-analyzer-exceptions",
  "created_at": "2025-12-26T08:32:15Z",

  "linkage": {
    "plantation_id": "WM-4521",
    "batch_id": "batch-2025-12-26-001",
    "factory_id": "KEN-FAC-001",
    "batch_result_ref": "results/WM-4521/tea/mombasa/batch-2025-12-26-001.json"
  },

  "documents": [
    {
      "document_id": "leaf_001",
      "files": [
        { "path": "images/leaf_001.jpg", "role": "image" },
        { "path": "results/leaf_001.json", "role": "metadata" }
      ]
    }
  ],

  "payload": {
    "grading_model_id": "tbk_kenya_tea_v1",
    "grading_model_version": "1.0.0",
    "total_exceptions": 2
  }
}
```

### Metadata File Example (Source-Specific)

```json
// For qc-analyzer-exceptions - processor stores this AS-IS in extracted_fields
// Processor does NOT validate or parse these field names
{
  "quality_grade": "secondary",
  "confidence": 0.91,
  "leaf_type": "coarse_leaf",
  "coarse_subtype": "hard_leaf",
  "banji_hardness": null
}

// For a different source (e.g., weather-images), metadata could be completely different:
{
  "capture_timestamp": "2025-12-26T08:00:00Z",
  "sensor_id": "WS-001",
  "cloud_cover_percent": 45
}
// The ZipExtractionProcessor handles both identically - just stores as dict
```

### Critical Implementation Rules

**From project-context.md:**

1. **ALL I/O operations MUST be async** - Use `async def` for blob operations
2. **Use Pydantic 2.0 syntax** - `model_dump()` not `dict()`
3. **Type hints required** - ALL function signatures
4. **Open/Closed Principle** - ZipExtractionProcessor extends framework, no core changes
5. **Single documents collection** - All sources store to `documents`, differentiated by `source_id`
6. **Config-driven storage** - Collection name from `storage.index_collection`
7. **Config-driven events** - Topic from `events.on_success.topic`

### Testing Strategy

| Test Type | What to Test | Mocking Required |
|-----------|--------------|------------------|
| Unit | ZipExtractionProcessor.process() | mock blob client, doc repo |
| Unit | Manifest validation | None (pure functions) |
| Unit | Image extraction | mock blob client |
| Unit | Metadata parsing | None (pure functions) |
| Unit | Error scenarios | mock to trigger errors |
| Integration | Full ZIP pipeline | mock blob storage only |
| Contract | Event schema | mock DAPR |

### Previous Story Learnings (Story 2.4)

1. **ProcessorRegistry pattern** - Register with `processor_type` key, lookup is pure config-driven
2. **DocumentRepository** - Reuse for storing to `documents` collection
3. **DaprEventPublisher** - Reuse for event emission, topic from config
4. **BlobStorageClient** - Reuse for download/upload operations
5. **Config access pattern** - `source_config["config"]["storage"]["index_collection"]`
6. **Metrics pattern** - Add counters for ZIP processing (images extracted, failures)

### References

- [Source: _bmad-output/architecture/collection-model-architecture.md#generic-zip-manifest-format] - ZIP manifest specification
- [Source: _bmad-output/epics.md#story-25] - Epic story definition (updated for single collection)
- [Source: _bmad-output/project-context.md] - Coding standards and rules
- [Source: Story 2.4] - Generic Content Processing Framework (reuse processors, registry, infrastructure)
- [Source: config/source-configs/qc-analyzer-exceptions.yaml] - Source configuration

---

## Out of Scope

- LLM extraction for ZIP content (manifest is structured, no LLM needed)
- Content-level deduplication (Story 2.6)
- Weather API pull mode (Story 2.7)
- Market prices pull mode (Story 2.8)
- MCP server exposure (Story 2.9)

---

## Definition of Done

- [ ] ZipExtractionProcessor registered in ProcessorRegistry with `zip-extraction` key
- [ ] Manifest validated against generic schema + source-specific payload schema from config
- [ ] Files extracted and stored to container from `storage.file_container` config
- [ ] Blob paths built from `storage.file_path_pattern` config (no hardcoded paths)
- [ ] Metadata files parsed and stored AS-IS in `extracted_fields` (no field validation)
- [ ] `manifest.payload` merged into each document's `extracted_fields`
- [ ] Raw ZIP stored to `storage.raw_container` before processing
- [ ] Documents stored in collection from `storage.index_collection` config
- [ ] Document IDs follow pattern using `link_field` from config
- [ ] `linkage_fields` copied AS-IS from `manifest.linkage` (no hardcoded field names)
- [ ] `field_mappings` from config applied to linkage_fields
- [ ] Domain event emitted to topic from `events.on_success.topic` config
- [ ] Event payload built from `events.on_success.payload_fields` config
- [ ] NO domain-specific code in processor (no leaf_type, grading_model, etc.)
- [ ] Error handling for corrupt ZIPs, missing manifest, invalid images
- [ ] No partial documents on fatal error (atomic operation)
- [ ] Unit tests passing (target: 15+ tests)
- [ ] Integration test with sample ZIP file
- [ ] Source config YAML validates successfully
- [ ] CI passes (lint, format, tests)

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

