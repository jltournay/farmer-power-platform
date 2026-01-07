# Story 0.75.10c: Azure Document Intelligence Integration

**Status:** ready-for-dev
**GitHub Issue:** <!-- Auto-created by dev-story workflow -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer**,
I want Azure Document Intelligence for scanned PDF extraction,
So that scanned/image-based PDFs can be processed with OCR.

## Acceptance Criteria

1. **AC1: Azure Document Intelligence Client** - Implement `AzureDocumentIntelligenceClient` class that wraps Azure's Document Intelligence SDK with async support
2. **AC2: Scanned PDF Detection** - Implement automatic detection of scanned vs digital PDFs based on text extraction confidence (< 0.3 confidence triggers OCR)
3. **AC3: OCR Extraction Method** - Add `azure_doc_intel` extraction method to `DocumentExtractor` service that uses Azure DI for scanned PDFs
4. **AC4: Configuration Settings** - Add Azure Document Intelligence endpoint and key to Pydantic Settings configuration
5. **AC5: Fallback to PyMuPDF** - Implement graceful fallback to PyMuPDF text extraction if Azure DI is unavailable or fails
6. **AC6: Cost Tracking** - Emit cost tracking events for Azure DI calls (page count, cost estimate) to support operational observability
7. **AC7: Confidence Scoring** - Capture and store Azure DI confidence scores in SourceFile.extraction_confidence field
8. **AC8: Azure Operation Polling** - Poll Azure async operation status and surface progress in extraction job status
9. **AC9: Markdown Conversion** - Convert Azure DI layout analysis results to Markdown format (headings, paragraphs, tables)
10. **AC10: Error Handling** - Implement proper error handling for Azure DI failures (rate limits, invalid credentials, network errors)
11. **AC11: Unit Tests** - Minimum 12 unit tests covering Azure DI client mocking, detection logic, and fallback scenarios
12. **AC12: Integration Test** - At least one integration test verifying the full OCR pipeline (with mocked Azure responses)
13. **AC13: CI Passes** - All lint checks and tests pass in CI

## Tasks / Subtasks

- [ ] **Task 1: Add Azure Document Intelligence Dependency** (AC: #1)
  - [ ] Add `azure-ai-documentintelligence` to `services/ai-model/pyproject.toml`
  - [ ] Run `poetry lock && poetry install`

- [ ] **Task 2: Add Azure DI Configuration Settings** (AC: #4)
  - [ ] Edit `services/ai-model/src/ai_model/config.py`
  - [ ] Add `azure_doc_intel_endpoint: str` setting (default empty)
  - [ ] Add `azure_doc_intel_key: str` setting (default empty, SecretStr type)
  - [ ] Add `azure_doc_intel_enabled: bool` setting (default True, but disabled if endpoint/key empty)

- [ ] **Task 3: Create Azure Document Intelligence Client** (AC: #1, #8, #9)
  - [ ] Create `services/ai-model/src/ai_model/infrastructure/azure_doc_intel_client.py`
  - [ ] Implement `AzureDocumentIntelligenceClient` class
  - [ ] Implement `analyze_pdf(content: bytes) -> DocumentAnalysisResult` async method
  - [ ] Poll operation status with exponential backoff
  - [ ] Convert `prebuilt-layout` results to Markdown format
  - [ ] Handle tables, headings, paragraphs from Azure response

- [ ] **Task 4: Implement Scanned PDF Detection** (AC: #2)
  - [ ] Create `services/ai-model/src/ai_model/services/scan_detection.py` (new module)
  - [ ] Implement `ScanDetectionResult` dataclass with fields: is_scanned, reason, confidence, detection_signals
  - [ ] Implement `detect_scanned_pdf(content: bytes) -> ScanDetectionResult` function
  - [ ] Detection Signal 1: Low text content (< 150 chars/page average → confidence < 0.3)
  - [ ] Detection Signal 2: Full-page image (image covers > 80% of page area, >50% of pages)
  - [ ] Combine signals: Either signal triggers scanned classification
  - [ ] Log detection decision with reason for observability
  - [ ] Import and use in `document_extractor.py`

- [ ] **Task 5: Add Azure DI Extraction Method** (AC: #3, #5, #7, #10)
  - [ ] Edit `services/ai-model/src/ai_model/services/document_extractor.py`
  - [ ] Update `_extract_pdf()` method to check for scanned PDF
  - [ ] If scanned AND Azure DI enabled → call Azure DI
  - [ ] If scanned AND Azure DI unavailable → return low-confidence PyMuPDF result with warning
  - [ ] Store extraction_method as `azure_doc_intel` when Azure DI used
  - [ ] Handle Azure DI errors gracefully with fallback

- [ ] **Task 6: Wire Azure DI Progress to Job Status** (AC: #8)
  - [ ] Update `extraction_workflow.py` to pass progress callback to Azure DI client
  - [ ] Azure DI client must call `progress_callback(percent, pages_processed, total_pages)` during polling
  - [ ] Progress callback uses `asyncio.run_coroutine_threadsafe()` to update `ExtractionJobRepository`
  - [ ] `StreamExtractionProgress` RPC (from 0.75.10b) automatically picks up job updates via polling loop
  - [ ] Add extraction_method field to `ExtractionJob` model to indicate "azure_doc_intel" vs "text_extraction"
  - [ ] Update gRPC `ExtractionProgressEvent` to include extraction_method for client display

- [ ] **Task 7: Implement Cost Tracking** (AC: #6)
  - [ ] Create cost event model or reuse from existing infrastructure
  - [ ] Emit cost event after successful Azure DI call
  - [ ] Include: page_count, estimated_cost_usd ($0.01/page), document_id

- [ ] **Task 8: Unit Tests** (AC: #11)
  - [ ] Create `tests/unit/ai_model/test_azure_doc_intel_client.py`
  - [ ] Test Azure DI client with mocked Azure SDK - 4 tests
  - [ ] Test Markdown conversion from Azure response - 3 tests
  - [ ] Create `tests/unit/ai_model/test_scan_detection.py`
  - [ ] Test Signal 1: Low text content detection - 2 tests
  - [ ] Test Signal 2: Full-page image detection - 2 tests
  - [ ] Test combined signals (both triggered, one triggered, none) - 3 tests
  - [ ] Test fallback scenarios when Azure DI unavailable - 2 tests

- [ ] **Task 9: Integration Test** (AC: #12)
  - [ ] Add integration test to `tests/unit/ai_model/test_document_extractor.py`
  - [ ] Test full extraction flow with mocked Azure DI responses

- [ ] **Task 10: CI Verification** (AC: #13)
  - [ ] Run lint checks: `ruff check . && ruff format --check .`
  - [ ] Run unit tests with correct PYTHONPATH
  - [ ] Push to feature branch and verify CI passes

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.75.10c: Azure Document Intelligence Integration"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/0-75-10c-azure-document-intelligence-integration
  ```

**Branch name:** `feature/0-75-10c-azure-document-intelligence-integration`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin feature/0-75-10c-azure-document-intelligence-integration`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.75.10c: Azure Document Intelligence Integration" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d feature/0-75-10c-azure-document-intelligence-integration`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
PYTHONPATH="${PYTHONPATH}:.:services/ai-model/src:libs/fp-common:libs/fp-proto/src" pytest tests/unit/ai_model/test_azure_doc_intel_client.py tests/unit/ai_model/test_document_extractor.py -v
```
**Output:**
```
(paste test summary here - e.g., "42 passed in 5.23s")
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure (--build is MANDATORY)
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build

# Wait for services, then run tests
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v

# Tear down
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```
**Output:**
```
(paste E2E test output here - story is NOT ready for review without this)
```
**E2E passed:** [ ] Yes / [ ] No

### 3. Lint Check
```bash
ruff check . && ruff format --check .
```
**Lint passed:** [ ] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin feature/0-75-10c-azure-document-intelligence-integration

# Wait ~30s, then check CI status
gh run list --branch feature/0-75-10c-azure-document-intelligence-integration --limit 3
```
**CI Run ID:** _______________
**CI Status:** [ ] Passed / [ ] Failed
**E2E CI Run ID:** _______________
**E2E CI Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### CRITICAL: Follow Existing Patterns - DO NOT Reinvent

**This story builds on Story 0.75.10b. Reuse patterns from:**

| Component | Reference | Pattern |
|-----------|-----------|---------|
| Document extractor | `services/ai-model/src/ai_model/services/document_extractor.py` | PyMuPDF extraction, async pattern |
| Extraction workflow | `services/ai-model/src/ai_model/services/extraction_workflow.py` | Job tracking, progress callbacks |
| Job repository | `services/ai-model/src/ai_model/infrastructure/repositories/extraction_job_repository.py` | MongoDB async repository |
| Blob storage client | `services/ai-model/src/ai_model/infrastructure/blob_storage.py` | Azure SDK async wrapper |
| Config settings | `services/ai-model/src/ai_model/config.py` | Pydantic Settings pattern |

### Pipeline Integration Point (CRITICAL)

**The existing `DocumentExtractor._extract_pdf()` from 0.75.10b must be modified to integrate Azure DI:**

```python
# services/ai-model/src/ai_model/services/document_extractor.py
# CURRENT (from 0.75.10b):

class DocumentExtractor:
    async def _extract_pdf(
        self,
        content: bytes,
        progress_callback: Callable | None = None,
    ) -> ExtractionResult:
        """Extract text from PDF using PyMuPDF in thread pool."""
        # ... PyMuPDF extraction only ...
        return ExtractionResult(
            content=text,
            page_count=page_count,
            extraction_method=ExtractionMethod.TEXT_EXTRACTION,
            confidence=confidence,
        )
```

**MODIFIED (for 0.75.10c) - Add Azure DI fallback with enhanced detection:**

```python
# services/ai-model/src/ai_model/services/document_extractor.py

from ai_model.services.scan_detection import detect_scanned_pdf, ScanDetectionResult

class DocumentExtractor:
    def __init__(
        self,
        azure_di_client: AzureDocumentIntelligenceClient | None = None,
        settings: Settings | None = None,
    ):
        self._azure_di_client = azure_di_client
        self._settings = settings or Settings()

    async def _extract_pdf(
        self,
        content: bytes,
        progress_callback: Callable | None = None,
    ) -> ExtractionResult:
        """Extract text from PDF - uses Azure DI for scanned PDFs."""

        # Step 1: Detect if PDF is scanned (using dual-signal detection)
        detection = detect_scanned_pdf(content)
        logger.info(
            "PDF scan detection complete",
            is_scanned=detection.is_scanned,
            reason=detection.reason,
            signals=detection.detection_signals,
        )

        # Step 2: Digital PDF - use PyMuPDF only
        if not detection.is_scanned:
            return await self._extract_pdf_with_pymupdf(content, progress_callback)

        # Step 3: Scanned PDF - try Azure DI if available
        if not self._is_azure_di_available():
            # Azure DI not configured - fallback to PyMuPDF with warning
            logger.warning("Azure DI not available for scanned PDF", reason=detection.reason)
            result = await self._extract_pdf_with_pymupdf(content, progress_callback)
            result.warnings.append(f"{detection.reason}, but Azure DI not configured")
            return result

        # Step 4: Call Azure DI for OCR
        try:
            azure_result = await self._azure_di_client.analyze_pdf(
                content=content,
                progress_callback=progress_callback,
            )
            return ExtractionResult(
                content=azure_result.markdown_content,
                page_count=azure_result.page_count,
                extraction_method=ExtractionMethod.AZURE_DOC_INTEL,
                confidence=azure_result.confidence,
            )
        except AzureDocIntelError as e:
            # Azure DI failed - fallback to PyMuPDF result
            logger.error("Azure DI failed, falling back to PyMuPDF", error=str(e))
            result = await self._extract_pdf_with_pymupdf(content, progress_callback)
            result.warnings.append(f"Azure DI failed: {e}, using PyMuPDF fallback")
            return result

    async def _extract_pdf_with_pymupdf(
        self,
        content: bytes,
        progress_callback: Callable | None = None,
    ) -> ExtractionResult:
        """Original PyMuPDF extraction logic (extracted from 0.75.10b)."""
        # ... existing PyMuPDF code from 0.75.10b ...

    def _is_azure_di_available(self) -> bool:
        """Check if Azure DI is configured and client is available."""
        return (
            self._azure_di_client is not None
            and self._settings.azure_doc_intel_enabled
        )
```

**Key Integration Points:**

| Component | Change | Reason |
|-----------|--------|--------|
| `scan_detection.py` | NEW module with `detect_scanned_pdf()` | Dual-signal scanned PDF detection |
| `DocumentExtractor.__init__` | Add `azure_di_client` dependency | Inject Azure DI client |
| `_extract_pdf()` | Call `detect_scanned_pdf()` + route to Azure DI | Route scanned PDFs to OCR |
| `_extract_pdf_with_pymupdf()` | Extract existing PyMuPDF logic | Reusable for fallback |
| `ExtractionResult` | Add `warnings` field | Report fallback scenarios |

**Dependency Injection in extraction_workflow.py:**

```python
# services/ai-model/src/ai_model/services/extraction_workflow.py

class ExtractionWorkflow:
    def __init__(
        self,
        document_repository: RagDocumentRepository,
        job_repository: ExtractionJobRepository,
        blob_client: BlobStorageClient,
        settings: Settings,
    ):
        # Create Azure DI client if configured
        azure_di_client = None
        if settings.azure_doc_intel_enabled:
            azure_di_client = AzureDocumentIntelligenceClient(settings)

        # Inject into DocumentExtractor
        self._extractor = DocumentExtractor(
            azure_di_client=azure_di_client,
            settings=settings,
        )
```

---

### Streaming Progress Integration (CRITICAL)

**The `StreamExtractionProgress` RPC from 0.75.10b uses a polling pattern:**

```python
# From rag_document_service.py (existing - DO NOT MODIFY the RPC)
async def StreamExtractionProgress(
    self,
    request: StreamExtractionProgressRequest,
    context: grpc.aio.ServicerContext,
) -> AsyncIterator[ExtractionProgressEvent]:
    """Stream extraction progress events to client."""
    job_id = request.job_id

    while True:
        job = await self._job_repository.get(job_id)  # <-- Reads from MongoDB
        # ... yields progress events ...
        await asyncio.sleep(0.5)  # Poll interval
```

**Your Azure DI client must update the job in MongoDB for streaming to work:**

```python
# In azure_doc_intel_client.py
class AzureDocumentIntelligenceClient:
    async def analyze_pdf(
        self,
        content: bytes,
        progress_callback: Callable[[int, int, int], None] | None = None,
    ) -> DocumentAnalysisResult:
        """Analyze PDF with Azure DI, reporting progress via callback."""
        poller = await self._client.begin_analyze_document(...)

        # Poll Azure operation status
        while not poller.done():
            # Get operation status from Azure
            status = await poller.status()

            # Calculate progress (Azure doesn't give page-by-page, estimate from status)
            if status == "running":
                # Report progress - this MUST update MongoDB via callback
                if progress_callback:
                    progress_callback(50, 0, 0)  # Intermediate progress

            await asyncio.sleep(1.0)  # Azure polling interval

        result = await poller.result()
        return result
```

**In extraction_workflow.py, wire the callback to update MongoDB:**

```python
# In extraction_workflow.py
async def _run_extraction(self, job: ExtractionJob, document: RagDocument):
    # Progress callback that updates MongoDB (same pattern as 0.75.10b)
    loop = asyncio.get_event_loop()

    def progress_callback(percent: int, pages_processed: int, total_pages: int):
        """Update job progress in MongoDB from sync/async context."""
        asyncio.run_coroutine_threadsafe(
            self._job_repository.update_progress(
                job.job_id, percent, pages_processed, total_pages
            ),
            loop,
        )

    # Pass callback to Azure DI client
    result = await self._azure_di_client.analyze_pdf(
        content=pdf_bytes,
        progress_callback=progress_callback,
    )
```

**Key Point:** The streaming RPC polls MongoDB every 0.5s. As long as you update the job record in MongoDB, clients will see progress automatically.

---

### Azure Document Intelligence SDK (Latest)

**Package:** `azure-ai-documentintelligence` (formerly `azure-ai-formrecognizer`)

**Version:** 1.0.0+ (December 2025)

**Import:**
```python
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, DocumentAnalysisFeature
from azure.core.credentials import AzureKeyCredential
```

**Basic Usage:**
```python
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

client = DocumentIntelligenceClient(
    endpoint=settings.azure_doc_intel_endpoint,
    credential=AzureKeyCredential(settings.azure_doc_intel_key)
)

# Async operation - returns poller
poller = await client.begin_analyze_document(
    model_id="prebuilt-layout",  # Best for general documents
    body=pdf_bytes,
    content_type="application/pdf"
)
result = await poller.result()
```

**Key Model IDs:**

| Model | Use Case | Output |
|-------|----------|--------|
| `prebuilt-layout` | General documents, tables, headings | Paragraphs, tables, sections |
| `prebuilt-read` | Pure text extraction | Raw text |
| `prebuilt-document` | Key-value extraction | Fields, values |

**Use `prebuilt-layout`** for RAG documents - best for preserving structure.

**Result Structure:**
```python
result.paragraphs  # List of paragraphs with role (title, sectionHeading, etc.)
result.tables      # List of tables with cells
result.pages       # Page-level metadata
```

**CRITICAL: Azure DI is async by nature.** Use `begin_analyze_document()` which returns a poller. Poll for completion.

### Scanned PDF Detection Logic (Enhanced)

**Detection uses TWO signals to catch edge cases:**

| Signal | Check | Threshold | Catches |
|--------|-------|-----------|---------|
| Low text content | `avg_chars_per_page` | < 150 chars | PDFs with no/minimal text layer |
| Full-page image | `image_area / page_area` | > 80% | Scanned pages rendered as images |

**Implementation:**

```python
import pymupdf
from dataclasses import dataclass

@dataclass
class ScanDetectionResult:
    """Result of scanned PDF detection."""
    is_scanned: bool
    reason: str
    confidence: float  # 0.0-1.0 text extraction confidence
    detection_signals: list[str]  # Which signals triggered

def detect_scanned_pdf(content: bytes) -> ScanDetectionResult:
    """Detect if PDF is scanned using multiple signals.

    Returns detection result with reason for logging/observability.
    """
    doc = pymupdf.open(stream=content, filetype="pdf")
    total_pages = len(doc)
    signals_triggered = []

    total_chars = 0
    pages_with_fullpage_image = 0

    for page in doc:
        # Signal 1: Check text content
        text = page.get_text()
        total_chars += len(text.strip())

        # Signal 2: Check for full-page image
        images = page.get_images()
        if images:
            # Get bounding box of first (usually largest) image
            try:
                img_rect = page.get_image_bbox(images[0])
                page_area = page.rect.width * page.rect.height
                img_area = img_rect.width * img_rect.height

                if page_area > 0 and (img_area / page_area) > 0.8:
                    pages_with_fullpage_image += 1
            except Exception:
                pass  # Some images may not have valid bbox

    doc.close()

    # Calculate confidence from text content
    avg_chars_per_page = total_chars / max(total_pages, 1)
    confidence = min(1.0, avg_chars_per_page / 500)  # 500+ chars/page = 1.0

    # Check Signal 1: Low text content
    if confidence < 0.3:
        signals_triggered.append(f"low_text_content (avg {avg_chars_per_page:.0f} chars/page)")

    # Check Signal 2: Majority of pages are full-page images
    fullpage_image_ratio = pages_with_fullpage_image / max(total_pages, 1)
    if fullpage_image_ratio > 0.5:  # >50% pages are full-page images
        signals_triggered.append(f"fullpage_images ({pages_with_fullpage_image}/{total_pages} pages)")

    # Scanned if ANY signal triggered
    is_scanned = len(signals_triggered) > 0

    if is_scanned:
        reason = f"Scanned PDF detected: {', '.join(signals_triggered)}"
    else:
        reason = f"Digital PDF (confidence: {confidence:.2f}, no full-page images)"

    return ScanDetectionResult(
        is_scanned=is_scanned,
        reason=reason,
        confidence=confidence,
        detection_signals=signals_triggered,
    )
```

**Usage in DocumentExtractor:**

```python
async def _extract_pdf(self, content: bytes, ...) -> ExtractionResult:
    # Step 1: Detect if scanned
    detection = detect_scanned_pdf(content)
    logger.info("PDF scan detection", **detection.__dict__)

    # Step 2: Route based on detection
    if not detection.is_scanned:
        # Digital PDF - use PyMuPDF
        return await self._extract_pdf_with_pymupdf(content, ...)

    # Step 3: Scanned PDF - try Azure DI
    if self._is_azure_di_available():
        return await self._extract_with_azure_di(content, ...)

    # Step 4: Fallback with warning
    result = await self._extract_pdf_with_pymupdf(content, ...)
    result.warnings.append(detection.reason)
    return result
```

**Why two signals?**

| Scenario | Signal 1 (text) | Signal 2 (image) | Result |
|----------|-----------------|------------------|--------|
| True scanned PDF | Low | High | ✅ Detected |
| Digital PDF with images | High | Low | ✅ Not triggered |
| OCR'd scanned PDF | High | High | ✅ Detected (image signal) |
| PDF with only headers | Low | Low | ✅ Detected (text signal) |

### Azure DI Result to Markdown Conversion

**Conversion Logic:**
```python
def azure_result_to_markdown(result) -> str:
    """Convert Azure Document Intelligence result to Markdown."""
    sections = []

    for paragraph in result.paragraphs or []:
        if paragraph.role == "title":
            sections.append(f"# {paragraph.content}")
        elif paragraph.role == "sectionHeading":
            sections.append(f"## {paragraph.content}")
        else:
            sections.append(paragraph.content)

    for table in result.tables or []:
        sections.append(table_to_markdown(table))

    return "\n\n".join(sections)

def table_to_markdown(table) -> str:
    """Convert Azure table to Markdown table format."""
    rows = {}
    for cell in table.cells:
        row_idx = cell.row_index
        if row_idx not in rows:
            rows[row_idx] = {}
        rows[row_idx][cell.column_index] = cell.content

    # Build markdown table
    md_rows = []
    for row_idx in sorted(rows.keys()):
        row = rows[row_idx]
        cells = [row.get(col, "") for col in range(table.column_count)]
        md_rows.append("| " + " | ".join(cells) + " |")

        # Add separator after header row
        if row_idx == 0:
            md_rows.append("|" + "---|" * table.column_count)

    return "\n".join(md_rows)
```

### Error Handling Scenarios

| Scenario | Error Code | Response |
|----------|------------|----------|
| Azure DI endpoint not configured | N/A | Fallback to PyMuPDF with warning |
| Azure DI invalid credentials | UNAUTHENTICATED | Fallback to PyMuPDF, log error |
| Azure DI rate limited (429) | RESOURCE_EXHAUSTED | Retry with exponential backoff (max 3 retries) |
| Azure DI service unavailable | UNAVAILABLE | Fallback to PyMuPDF, log warning |
| Azure DI timeout | DEADLINE_EXCEEDED | Fallback to PyMuPDF, log error |
| Document too large (> 500 pages) | INVALID_ARGUMENT | Return error, do not attempt extraction |

### Cost Tracking Design

**Cost Estimation:**
- Azure Document Intelligence pricing: ~$0.01 per page (prebuilt-layout)
- Track per-extraction for operational visibility

**Cost Event Schema:**
```python
class AzureDocIntelCostEvent(BaseModel):
    """Track Azure DI costs for observability."""
    timestamp: datetime
    document_id: str
    job_id: str
    page_count: int
    estimated_cost_usd: Decimal  # page_count * 0.01
    model_id: str  # "prebuilt-layout"
    success: bool
```

**Note:** This story implements cost tracking logging. Full cost dashboard is in Epic 9 (Story 9.6).

### Fallback Flow Design

```
PDF Upload
    │
    ▼
┌─────────────────────────────┐
│ 1. Try PyMuPDF Extraction   │
│    (fast, free)             │
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│ 2. Check Confidence         │
│    confidence < 0.3?        │
└─────────────────────────────┘
    │           │
   NO          YES (likely scanned)
    │           │
    ▼           ▼
 Return     ┌─────────────────────────────┐
 Result     │ 3. Check Azure DI Available │
            │    endpoint + key configured? │
            └─────────────────────────────┘
                │           │
               NO          YES
                │           │
                ▼           ▼
            Return      ┌─────────────────────────────┐
            with        │ 4. Call Azure DI            │
            warning     │    • OCR extraction         │
                        │    • Track cost             │
                        └─────────────────────────────┘
                            │           │
                          SUCCESS     FAILURE
                            │           │
                            ▼           ▼
                        Return      Fallback to
                        Azure DI    PyMuPDF result
                        result      with warning
```

### Previous Story Intelligence (Story 0.75.10b)

**Key Learnings from 0.75.10b:**

1. **PyMuPDF is synchronous** - Must wrap in `run_in_executor()` for async context
2. **Progress callback in sync context** - Use `asyncio.run_coroutine_threadsafe()` to update job status from sync thread
3. **ThreadPoolExecutor pattern** - Use shared executor with configurable max_workers (default 4)
4. **Confidence calculation** - Based on avg_chars_per_page / 500

**Files created in 0.75.10b to extend:**
- `services/ai-model/src/ai_model/services/document_extractor.py` - Add Azure DI extraction
- `services/ai-model/src/ai_model/services/extraction_workflow.py` - Wire Azure DI progress
- `services/ai-model/src/ai_model/config.py` - Add Azure DI settings

### File Structure After Story

```
services/ai-model/
├── src/ai_model/
│   ├── config.py                      # MODIFIED - add Azure DI settings
│   ├── infrastructure/
│   │   ├── azure_doc_intel_client.py  # NEW - Azure DI SDK wrapper
│   │   └── blob_storage.py            # EXISTING - no changes
│   └── services/
│       ├── scan_detection.py          # NEW - Dual-signal scanned PDF detection
│       ├── document_extractor.py      # MODIFIED - integrate scan_detection + Azure DI
│       └── extraction_workflow.py     # MODIFIED - wire Azure DI progress

tests/
├── unit/ai_model/
│   ├── test_azure_doc_intel_client.py # NEW - Azure DI client tests
│   ├── test_scan_detection.py         # NEW - Scanned PDF detection tests
│   ├── test_document_extractor.py     # MODIFIED - add integration tests
│   └── test_extraction_job.py         # EXISTING - no changes
```

### Testing Strategy

**Unit Tests Required (minimum 12 tests):**

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_azure_doc_intel_client.py` | 7 | Azure DI client mocking, markdown conversion |
| `test_document_extractor.py` | 5 | Scanned PDF detection, fallback scenarios |

**Mock Azure DI Responses:**
```python
@pytest.fixture
def mock_azure_di_result():
    """Create mock Azure Document Intelligence result."""
    return {
        "paragraphs": [
            {"content": "Document Title", "role": "title"},
            {"content": "Introduction", "role": "sectionHeading"},
            {"content": "This is the first paragraph of text.", "role": None},
        ],
        "tables": [
            {
                "row_count": 2,
                "column_count": 2,
                "cells": [
                    {"row_index": 0, "column_index": 0, "content": "Header 1"},
                    {"row_index": 0, "column_index": 1, "content": "Header 2"},
                    {"row_index": 1, "column_index": 0, "content": "Value 1"},
                    {"row_index": 1, "column_index": 1, "content": "Value 2"},
                ],
            }
        ],
        "pages": [{"page_number": 1, "width": 8.5, "height": 11}],
    }
```

**Scanned PDF Test Fixtures:**

```python
import pymupdf

def create_digital_pdf(text: str = "This is a digital PDF with lots of text content.", pages: int = 1) -> bytes:
    """Create a digital PDF with extractable text (confidence > 0.3)."""
    doc = pymupdf.open()
    for i in range(pages):
        page = doc.new_page()
        # Add substantial text content (500+ chars/page for confidence = 1.0)
        full_text = f"Page {i+1}\n\n" + (text + " ") * 20  # ~1000 chars
        page.insert_text((50, 50), full_text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def create_scanned_pdf_low_text() -> bytes:
    """Create PDF with minimal text (Signal 1: low text content)."""
    doc = pymupdf.open()
    page = doc.new_page()
    # Only add page number - simulates scanned PDF header
    page.insert_text((50, 750), "Page 1")  # < 150 chars/page
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def create_scanned_pdf_fullpage_image() -> bytes:
    """Create PDF with full-page image (Signal 2: image > 80% of page).

    This simulates a scanned document where each page is an image.
    """
    doc = pymupdf.open()
    page = doc.new_page()

    # Create a full-page rectangle (covers >80% of page)
    page_rect = page.rect
    img_rect = pymupdf.Rect(
        page_rect.x0 + 10,  # Small margin
        page_rect.y0 + 10,
        page_rect.x1 - 10,
        page_rect.y1 - 10,
    )

    # Insert a placeholder image (1x1 white pixel, stretched to full page)
    # In real tests, you could use an actual scanned image
    img_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xdc\xccY\xe7\x00\x00\x00\x00IEND\xaeB`\x82'
    page.insert_image(img_rect, stream=img_bytes)

    # Add minimal text (so it's detected by image signal, not text signal)
    page.insert_text((50, 50), "Scanned document with OCR text overlay " * 15)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def create_ocrd_scanned_pdf() -> bytes:
    """Create PDF that was scanned then OCR'd (has text + full-page image).

    This tests Signal 2 catching OCR'd scanned PDFs that have text layer.
    """
    doc = pymupdf.open()
    page = doc.new_page()

    # Full-page image (the scan)
    page_rect = page.rect
    img_rect = pymupdf.Rect(
        page_rect.x0 + 5,
        page_rect.y0 + 5,
        page_rect.x1 - 5,
        page_rect.y1 - 5,
    )
    img_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xdc\xccY\xe7\x00\x00\x00\x00IEND\xaeB`\x82'
    page.insert_image(img_rect, stream=img_bytes)

    # OCR text layer (lots of text - would pass Signal 1)
    page.insert_text((50, 50), "This is OCR extracted text. " * 50)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes
```

**Test Cases for Enhanced Detection:**

```python
import pytest
from ai_model.services.document_extractor import detect_scanned_pdf

class TestScanDetection:
    """Test scanned PDF detection with dual signals."""

    def test_digital_pdf_not_detected(self):
        """Digital PDF should NOT be flagged as scanned."""
        pdf = create_digital_pdf()
        result = detect_scanned_pdf(pdf)
        assert not result.is_scanned
        assert result.confidence >= 0.3
        assert len(result.detection_signals) == 0

    def test_low_text_triggers_signal_1(self):
        """PDF with minimal text should trigger Signal 1."""
        pdf = create_scanned_pdf_low_text()
        result = detect_scanned_pdf(pdf)
        assert result.is_scanned
        assert result.confidence < 0.3
        assert any("low_text_content" in s for s in result.detection_signals)

    def test_fullpage_image_triggers_signal_2(self):
        """PDF with full-page image should trigger Signal 2."""
        pdf = create_scanned_pdf_fullpage_image()
        result = detect_scanned_pdf(pdf)
        assert result.is_scanned
        assert any("fullpage_images" in s for s in result.detection_signals)

    def test_ocrd_scanned_detected_by_image_signal(self):
        """OCR'd scanned PDF (has text) should still be detected via Signal 2."""
        pdf = create_ocrd_scanned_pdf()
        result = detect_scanned_pdf(pdf)
        assert result.is_scanned
        # Has text so Signal 1 won't trigger, but Signal 2 should
        assert any("fullpage_images" in s for s in result.detection_signals)

    def test_detection_reason_logged(self):
        """Detection result should include human-readable reason."""
        pdf = create_scanned_pdf_low_text()
        result = detect_scanned_pdf(pdf)
        assert "Scanned PDF detected" in result.reason
```

### Dependencies

**New dependencies to add:**
```toml
# services/ai-model/pyproject.toml
[tool.poetry.dependencies]
azure-ai-documentintelligence = "^1.0.0"  # Azure DI SDK
```

**Already installed (from previous stories):**
- `pymupdf` ^1.26.0 (from 0.75.10b)
- `azure-storage-blob` ^12.0.0 (from 0.75.10b)
- `pydantic` ^2.0
- `motor` (async MongoDB)
- `structlog`

### Configuration

```python
# Add to services/ai-model/src/ai_model/config.py

from pydantic import SecretStr

class Settings(BaseSettings):
    # ... existing settings ...

    # Azure Document Intelligence
    azure_doc_intel_endpoint: str = Field(
        default="",
        description="Azure Document Intelligence endpoint URL",
    )
    azure_doc_intel_key: SecretStr = Field(
        default="",
        description="Azure Document Intelligence API key",
    )
    azure_doc_intel_model: str = Field(
        default="prebuilt-layout",
        description="Azure DI model ID for layout analysis",
    )
    azure_doc_intel_timeout: int = Field(
        default=300,
        ge=60,
        le=600,
        description="Timeout in seconds for Azure DI operations",
    )

    @property
    def azure_doc_intel_enabled(self) -> bool:
        """Check if Azure DI is configured and available."""
        return bool(self.azure_doc_intel_endpoint and self.azure_doc_intel_key.get_secret_value())
```

### Anti-Patterns to AVOID

| Anti-Pattern | Correct Approach |
|--------------|------------------|
| Blocking on Azure DI polling | Use async polling with `await asyncio.sleep()` |
| Ignoring Azure DI failures | Always fallback to PyMuPDF with warning logged |
| Hardcoding API keys | Use Pydantic Settings with SecretStr |
| Not tracking costs | Emit cost event for every Azure DI call |
| Skipping confidence scoring | Always capture Azure DI confidence in result |

### References

- [Source: `services/ai-model/src/ai_model/services/document_extractor.py`] - Existing extraction service to extend
- [Source: `services/ai-model/src/ai_model/config.py`] - Settings to extend
- [Source: `_bmad-output/epics/epic-0-75-ai-model.md#story-07510c`] - Story requirements
- [Source: `_bmad-output/architecture/ai-model-architecture/rag-document-api.md`] - PDF ingestion pipeline architecture
- [Source: `_bmad-output/sprint-artifacts/0-75-10b-basic-pdf-markdown-extraction.md`] - Previous story patterns
- [Azure Document Intelligence Documentation](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/)
- [Azure DI Python SDK](https://pypi.org/project/azure-ai-documentintelligence/)

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

**Created:**
- (list new files)

**Modified:**
- (list modified files with brief description)
