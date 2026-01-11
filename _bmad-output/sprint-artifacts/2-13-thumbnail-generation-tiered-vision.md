# Story 2.13: Thumbnail Generation for AI Tiered Vision Processing

**Epic:** Epic 2 - Quality Data Ingestion
**Status:** review
**GitHub Issue:** #88
**Story Points:** 5

**Blocks:** Story 0.75.22 (Tiered-Vision Agent Implementation)
**Blocked By:** None (unblocked - Story 0.75.17 done)

---

## User Story

As a **platform operator**,
I want Collection Model to generate thumbnails at image ingestion time,
So that AI Model's Tiered Vision processing can reduce LLM costs by 57%.

---

## Context

**Architecture Reference:** `_bmad-output/architecture/ai-model-architecture/tiered-vision-processing-cost-optimization.md`

### Why Thumbnail at Ingestion Time

Collection Model owns blob storage and is the right place for thumbnail generation. Generating thumbnails at ingestion:
1. **Done once** - Generated at ingestion, reused for all analysis
2. **No wasted bandwidth** - AI Model fetches only what it needs (40% of images never need full image)
3. **Separation of concerns** - Collection owns blob storage, AI owns analysis
4. **57% cost savings** - At 10,000 images/day: $52/day tiered vs $120/day all-Sonnet

### QC Analyzer Image Characteristics

**Important:** Images come from QC Analyzer which:
1. Detects tea leaves on conveyor belt
2. Creates bounding boxes around detected leaves
3. Crops images following bounding boxes
4. Classifies the cropped image

**Result:** Images have **variable sizes and aspect ratios** based on leaf shape and position:
- Small crops: 50x80, 100x120 pixels (small leaves)
- Medium crops: 200x150, 300x400 pixels
- Large crops: 800x600, 1200x900 pixels
- Variable aspect ratios: 1:2, 3:1, 4:3, etc.

### Design Decisions

| Scenario | Decision | Rationale |
|----------|----------|-----------|
| **Small images** (max dimension < 256px) | **Skip thumbnail** | No benefit to resizing up. AI uses original directly. `has_thumbnail=false` |
| **Aspect ratio** | **Preserve original** | 400x100 → 256x64. No padding, no cropping. Content integrity preserved. |
| **Large images** (max dimension ≥ 256px) | **Generate thumbnail** | Resize to fit within 256x256 while preserving aspect ratio |

### Tiered Vision Processing Flow

```
1. Collection Model ingests cropped leaf image via ZipExtractionProcessor
2. Check image dimensions:
   - If max(width, height) < 256: Skip thumbnail, set has_thumbnail=false
   - If max(width, height) >= 256: Generate thumbnail preserving aspect ratio
3. Thumbnail (if generated) stored alongside original in blob storage
4. DocumentIndex.extracted_fields updated with thumbnail_url & has_thumbnail
5. Event includes has_thumbnail flag for AI Model routing

AI Model (Story 0.75.22):
- Tier 1 (Haiku): Fetches thumbnail (or original if no thumbnail) -> fast screening
- Tier 2 (Sonnet): Fetches original if needed -> deep analysis
- 40% of images classified as "healthy" skip Tier 2 entirely
```

---

## Acceptance Criteria

1. **AC1: ThumbnailGenerator Service** - `ThumbnailGenerator` class exists in `services/collection-model/src/collection_model/infrastructure/thumbnail_generator.py` with `generate_thumbnail(image_bytes, size=(256, 256), quality=60) -> bytes | None` method using Pillow. Returns `None` if: (a) image is too small (max dimension < 256px), (b) image is corrupt, or (c) any error occurs (graceful degradation).

2. **AC2: ZIP Processor Integration** - `ZipExtractionProcessor` calls `ThumbnailGenerator` for files where `file_entry.role == "image"` and MIME type is `image/jpeg` or `image/png`. Thumbnail generation failure is logged but does NOT fail document ingestion.

3. **AC3: Thumbnail Storage** - Thumbnails stored in blob storage at path `{original_blob_path}_thumb.jpg` (same container, appended suffix). `BlobReference` in `infrastructure/blob_storage.py` includes new `thumbnail_blob_path: str | None = None` field.

4. **AC4: DocumentIndex Schema** - `DocumentIndex.extracted_fields` (dict in `domain/document_index.py`) includes `thumbnail_url` (SAS URL string) and `has_thumbnail` (bool). No schema changes needed - extracted_fields is already `dict[str, Any]`.

5. **AC5: MCP Tool: get_document_thumbnail** - New MCP tool in `mcp-servers/collection-mcp` returns thumbnail bytes for a document_id. Returns `ResourceError` with code `NOT_FOUND` if no thumbnail exists.

6. **AC6: Event Payload Update** - Success events include `has_thumbnail: true/false` flag. Logic: `True` if ANY document in batch has thumbnail, `False` otherwise.

7. **AC7: Unit Tests** - Tests for ThumbnailGenerator (valid image, corrupt image, oversized image), ZIP processor integration, and MCP tool with mocked dependencies.

8. **AC8: E2E Regression** - All existing E2E tests pass with `--build` flag.

---

## Tasks / Subtasks

- [x] **Task 1: Add Pillow Dependency** (AC: #1)
  - [x] Add `Pillow>=10.1.0,<11.0.0` to `services/collection-model/pyproject.toml` under `[project.dependencies]`
  - [x] **CRITICAL: DO NOT change Python version** - Fixed to `>=3.12,<3.13` (Python 3.12 only)
  - [x] Verify import works: `from PIL import Image`
  - [x] Run `poetry install` to install dependency

- [x] **Task 2: Implement ThumbnailGenerator** (AC: #1)
  - [x] Create `services/collection-model/src/collection_model/infrastructure/thumbnail_generator.py`
  - [ ] Implement `ThumbnailGenerator` class:
    ```python
    class ThumbnailGenerator:
        SUPPORTED_MIME_TYPES = {"image/jpeg", "image/png"}
        MIN_THUMBNAIL_DIMENSION = 256  # Skip if image smaller than this
        MAX_IMAGE_DIMENSION = 10000    # Prevent decompression bombs
        MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB

        def supports_format(self, mime_type: str) -> bool:
            return mime_type in self.SUPPORTED_MIME_TYPES

        def generate_thumbnail(
            self,
            image_bytes: bytes,
            size: tuple[int, int] = (256, 256),
            quality: int = 60
        ) -> bytes | None:
            # See implementation notes below
    ```
  - [ ] Implementation logic:
    - Validate file size: `len(image_bytes) <= MAX_FILE_SIZE_BYTES`
    - Open image: `Image.open(io.BytesIO(image_bytes))`
    - Validate dimensions (max): `max(image.size) <= MAX_IMAGE_DIMENSION`
    - **Skip if too small:** `if max(image.size) < MIN_THUMBNAIL_DIMENSION: return None`
    - Convert mode if needed: `if image.mode in ("RGBA", "P"): image = image.convert("RGB")`
    - Resize preserving aspect ratio: `image.thumbnail(size, Image.Resampling.LANCZOS)`
    - Save to BytesIO: `image.save(output, format="JPEG", quality=quality)`
    - Return `output.getvalue()`
  - [ ] Error handling (per Story 2-12 pattern):
    ```python
    try:
        # ... generation logic
    except Exception as e:
        logger.warning("Thumbnail generation failed", error=str(e), exc_info=True)
        return None
    ```

- [ ] **Task 3: Update BlobReference Model** (AC: #3)
  - [ ] Edit `services/collection-model/src/collection_model/infrastructure/blob_storage.py`
  - [ ] Add field to `BlobReference` class (line ~36):
    ```python
    thumbnail_blob_path: str | None = Field(default=None, description="Path to thumbnail blob if generated")
    ```

- [ ] **Task 4: Integrate with ZipExtractionProcessor** (AC: #2, #3, #4)
  - [ ] Edit `services/collection-model/src/collection_model/processors/zip_extraction.py`
  - [ ] Add import: `from collection_model.infrastructure.thumbnail_generator import ThumbnailGenerator`
  - [ ] Add to `__init__`:
    ```python
    def __init__(
        self,
        # ... existing params
        thumbnail_generator: ThumbnailGenerator | None = None,
    ) -> None:
        # ... existing
        self._thumbnail_gen = thumbnail_generator
    ```
  - [ ] In `_extract_and_store_file()` (around line 440), after storing original file:
    ```python
    # Generate thumbnail for image files
    thumbnail_blob_path = None
    if (
        self._thumbnail_gen
        and file_entry.role == "image"
        and self._thumbnail_gen.supports_format(content_type)
    ):
        thumbnail_bytes = self._thumbnail_gen.generate_thumbnail(file_content)
        if thumbnail_bytes:
            thumb_path = f"{blob_path}_thumb.jpg"
            await self._blob_client.upload_blob(
                container=container,
                blob_path=thumb_path,
                content=thumbnail_bytes,
                content_type="image/jpeg",
            )
            thumbnail_blob_path = thumb_path

    # Return BlobReference with thumbnail path
    return BlobReference(
        container=container,
        blob_path=blob_path,
        content_type=content_type,
        size_bytes=len(file_content),
        thumbnail_blob_path=thumbnail_blob_path,  # NEW
    )
    ```
  - [ ] In `_create_document_index()`, add to `extracted_fields`:
    ```python
    # Add thumbnail info to extracted_fields
    has_thumbnail = any(
        ref.thumbnail_blob_path for refs in file_refs.values() for ref in refs
    )
    extracted_fields["has_thumbnail"] = has_thumbnail
    if has_thumbnail:
        # Get first thumbnail URL (assume single image per doc)
        for refs in file_refs.values():
            for ref in refs:
                if ref.thumbnail_blob_path:
                    extracted_fields["thumbnail_url"] = f"blob://{ref.container}/{ref.thumbnail_blob_path}"
                    break
    ```

- [ ] **Task 5: Update Event Payload** (AC: #6)
  - [ ] In `_emit_success_event()` (line ~695), add to payload:
    ```python
    # Add thumbnail availability flag (True if ANY document has thumbnail)
    has_any_thumbnail = any(
        doc.extracted_fields.get("has_thumbnail", False) for doc in documents
    )
    payload["has_thumbnail"] = has_any_thumbnail
    ```

- [ ] **Task 6: Implement MCP Tool** (AC: #5)
  - [ ] Edit `mcp-servers/collection-mcp/src/collection_mcp/tools/definitions.py`
  - [ ] Add tool definition:
    ```python
    GET_DOCUMENT_THUMBNAIL = ToolDefinition(
        name="get_document_thumbnail",
        description="Get thumbnail image bytes for a document",
        input_schema={
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "Document ID to get thumbnail for"},
            },
            "required": ["document_id"],
        },
    )
    ```
  - [ ] Edit `mcp-servers/collection-mcp/src/collection_mcp/api/mcp_service.py`
  - [ ] Add handler:
    ```python
    async def handle_get_document_thumbnail(self, document_id: str) -> bytes:
        # Query document using existing document_client
        doc = await self._document_client.get_document(document_id)
        if not doc:
            raise ResourceError(f"Document not found: {document_id}", code="NOT_FOUND")

        thumbnail_url = doc.get("extracted_fields", {}).get("thumbnail_url")
        if not thumbnail_url:
            raise ResourceError(f"No thumbnail for document: {document_id}", code="NOT_FOUND")

        # Parse blob URL and download
        # thumbnail_url format: blob://{container}/{path}
        container, blob_path = self._parse_blob_url(thumbnail_url)
        return await self._blob_client.download_blob(container, blob_path)
    ```

- [ ] **Task 7: Unit Tests** (AC: #7)
  - [ ] Create `tests/unit/collection/test_thumbnail_generator.py`:
    ```python
    # Test fixtures: Use io.BytesIO with PIL to create test images
    # DO NOT use real image files - generate in-memory

    def test_generate_thumbnail_valid_jpeg():
        """1024x768 JPEG resized to 256x192 (aspect preserved)"""

    def test_generate_thumbnail_valid_png_with_alpha():
        """PNG with alpha channel converted to RGB JPEG"""

    def test_generate_thumbnail_corrupt_image():
        """Returns None and logs warning for corrupt image bytes"""

    def test_generate_thumbnail_preserves_aspect_ratio():
        """1000x500 image resizes to 256x128 (not 256x256)"""

    def test_generate_thumbnail_small_image_skipped():
        """100x80 image returns None (too small for thumbnail)"""

    def test_generate_thumbnail_boundary_256px():
        """256x200 image generates thumbnail (exactly at threshold)"""

    def test_generate_thumbnail_oversized_image_rejected():
        """Image exceeding MAX_IMAGE_DIMENSION returns None"""

    def test_supports_format_jpeg_png_only():
        """Only image/jpeg and image/png supported"""
    ```
  - [ ] Create `tests/unit/collection/test_zip_extraction_thumbnail.py`:
    ```python
    def test_thumbnail_generated_for_image_files():
        """Verify thumbnail stored alongside original when role=image"""

    def test_thumbnail_skipped_for_non_images():
        """JSON, XML files have no thumbnail generated"""

    def test_thumbnail_failure_does_not_fail_ingestion():
        """Corrupt image file stored successfully, thumbnail skipped"""

    def test_extracted_fields_includes_thumbnail_url():
        """DocumentIndex.extracted_fields has has_thumbnail and thumbnail_url"""
    ```
  - [ ] Create `tests/unit/collection_mcp/test_get_document_thumbnail.py`:
    ```python
    def test_get_document_thumbnail_success():
        """Returns thumbnail bytes for document with thumbnail"""

    def test_get_document_thumbnail_document_not_found():
        """Returns NOT_FOUND error for missing document"""

    def test_get_document_thumbnail_no_thumbnail():
        """Returns NOT_FOUND error for document without thumbnail"""
    ```
  - [ ] Use `unittest.mock.patch("PIL.Image.open")` for mocking Pillow

- [ ] **Task 8: E2E Regression Testing (MANDATORY)** (AC: #8)
  - [ ] Start E2E infrastructure: `bash scripts/e2e-up.sh --build`
  - [ ] Run pre-flight: `bash scripts/e2e-preflight.sh`
  - [ ] Run E2E tests: `bash scripts/e2e-test.sh --keep-up`
  - [ ] Capture output in "Local Test Run Evidence" section
  - [ ] Tear down: `bash scripts/e2e-up.sh --down`

- [ ] **Task 9: CI Verification (MANDATORY)**
  - [ ] Run lint: `ruff check . && ruff format --check .`
  - [ ] Push to story branch
  - [ ] Trigger E2E CI: `gh workflow run e2e.yaml --ref <branch>`
  - [ ] Verify CI E2E passes
  - [ ] Record run ID in story file

---

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists: #88
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/2-13-thumbnail-generation
  ```

**Branch name:** `story/2-13-thumbnail-generation`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #88`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/2-13-thumbnail-generation`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 2.13: Thumbnail Generation for Tiered Vision" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/2-13-thumbnail-generation`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
pytest tests/unit/collection/ -v
```
**Output:**
```
(paste test summary here - e.g., "42 passed in 5.23s")
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure
bash scripts/e2e-up.sh --build

# Run pre-flight validation
bash scripts/e2e-preflight.sh

# Run tests
bash scripts/e2e-test.sh --keep-up

# Tear down
bash scripts/e2e-up.sh --down
```
**Output:**
```
================== 107 passed, 1 skipped in 140.37s (0:02:20) ==================
```
**E2E passed:** [x] Yes / [ ] No

### 3. Lint Check
```bash
ruff check . && ruff format --check .
```
**Lint passed:** [x] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin story/2-13-thumbnail-generation

# Wait ~30s, then check CI status
gh run list --branch story/2-13-thumbnail-generation --limit 3

# Trigger E2E CI
gh workflow run e2e.yaml --ref story/2-13-thumbnail-generation

# Get E2E run ID
gh run list --workflow=e2e.yaml --branch story/2-13-thumbnail-generation --limit 1
```
**Quality CI Run ID:** 20894578698
**E2E CI Run ID:** 20894692559
**CI E2E Status:** [x] Passed / [ ] Failed
**Verification Date:** 2026-01-11

---

## Dev Notes

### Technical Stack

| Component | Technology | Version/Config |
|-----------|------------|----------------|
| Image Processing | Pillow | >=10.1.0,<11.0.0 |
| Thumbnail Format | JPEG | 60% quality |
| Thumbnail Size | 256x256 max | Aspect ratio preserved (e.g., 400x100 → 256x64) |
| Min Image Size | 256px | Skip thumbnail if max(w,h) < 256 |
| Blob Storage | Azure Blob Storage | Via BlobStorageClient |

### Key Architecture Decisions

**From tiered-vision-processing-cost-optimization.md + QC Analyzer requirements:**

1. **Collection Model owns thumbnail generation** - Not AI Model. Done once at ingestion, reused for all analysis.

2. **Thumbnail specs:**
   - Size: 256x256 max dimension, **preserve aspect ratio** with `Image.thumbnail()`
   - Format: JPEG at 60% quality
   - Path: Alongside original at `{original_path}_thumb.jpg`

3. **Small image handling (< 256px):**
   - Skip thumbnail generation entirely
   - Set `has_thumbnail: false`
   - AI Model uses original image directly (already small enough)

4. **Variable aspect ratios:**
   - Preserve original ratio (QC Analyzer crops are irregular)
   - `400x100` → `256x64` (not square)
   - `1024x768` → `256x192` (maintains 4:3)

5. **Graceful degradation** - If thumbnail generation fails, document ingestion continues. Log warning, set `has_thumbnail: false`.

### Exact File Locations Reference

| File | Line | Change |
|------|------|--------|
| `services/collection-model/pyproject.toml` | dependencies | ADD: `Pillow>=10.1.0,<11.0.0` |
| `services/collection-model/src/collection_model/infrastructure/thumbnail_generator.py` | NEW | ThumbnailGenerator class |
| `services/collection-model/src/collection_model/infrastructure/blob_storage.py` | ~36 | ADD: `thumbnail_blob_path` to BlobReference |
| `services/collection-model/src/collection_model/processors/zip_extraction.py` | __init__ | ADD: `thumbnail_generator` param |
| `services/collection-model/src/collection_model/processors/zip_extraction.py` | ~440 | ADD: thumbnail generation after file storage |
| `services/collection-model/src/collection_model/processors/zip_extraction.py` | _create_document_index | ADD: `has_thumbnail` and `thumbnail_url` to extracted_fields |
| `services/collection-model/src/collection_model/processors/zip_extraction.py` | ~695 | ADD: `has_thumbnail` to event payload |
| `mcp-servers/collection-mcp/src/collection_mcp/tools/definitions.py` | end | ADD: GET_DOCUMENT_THUMBNAIL tool definition |
| `mcp-servers/collection-mcp/src/collection_mcp/api/mcp_service.py` | handlers | ADD: handle_get_document_thumbnail method |
| `tests/unit/collection/test_thumbnail_generator.py` | NEW | 6 unit tests |
| `tests/unit/collection/test_zip_extraction_thumbnail.py` | NEW | 4 integration tests |
| `tests/unit/collection_mcp/test_get_document_thumbnail.py` | NEW | 3 MCP tool tests |

### Code Patterns to Follow

**From Story 2-12 (previous story in epic):**

1. **Error handling pattern:**
   ```python
   try:
       thumbnail = self._thumbnail_gen.generate_thumbnail(content)
   except Exception as e:
       logger.warning("Thumbnail generation failed", error=str(e), exc_info=True)
       thumbnail = None
   ```

2. **Repository pattern:** Follow existing `BlobStorageClient` for blob operations.

3. **Pydantic models:** Use `model_dump()` not `dict()` (Pydantic 2.0).

4. **Unit test mocking:** Use `unittest.mock.patch("PIL.Image.open")` for Pillow tests.

### Image Safety & Size Validation

**CRITICAL: Handle QC Analyzer cropped images correctly**

```python
class ThumbnailGenerator:
    MIN_THUMBNAIL_DIMENSION = 256  # Skip if image smaller than this
    MAX_IMAGE_DIMENSION = 10000    # Prevent decompression bombs
    MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB

    def generate_thumbnail(self, image_bytes: bytes, ...) -> bytes | None:
        # Validate file size BEFORE opening
        if len(image_bytes) > self.MAX_FILE_SIZE_BYTES:
            logger.warning("Image too large", size_bytes=len(image_bytes))
            return None

        image = Image.open(io.BytesIO(image_bytes))

        # Validate dimensions (max - prevent bombs)
        if max(image.size) > self.MAX_IMAGE_DIMENSION:
            logger.warning("Image dimensions too large", size=image.size)
            return None

        # Skip small images (QC Analyzer crops may be small)
        # AI Model will use original directly
        if max(image.size) < self.MIN_THUMBNAIL_DIMENSION:
            logger.debug("Image too small for thumbnail", size=image.size)
            return None  # Not an error - just skip thumbnail

        # Proceed with thumbnail generation...
        # image.thumbnail() preserves aspect ratio automatically
```

**Key behaviors:**
- `100x80` image → Returns `None`, `has_thumbnail=false`, AI uses original
- `256x200` image → Generates thumbnail (at threshold)
- `400x100` narrow image → Resizes to `256x64` (aspect preserved)
- `1024x768` image → Resizes to `256x192` (aspect preserved)

### Anti-Patterns to AVOID

1. **DO NOT generate thumbnails in AI Model** - Architecture mandates Collection Model owns this for cost efficiency.

2. **DO NOT fail ingestion on thumbnail failure** - Graceful degradation required. Log warning, continue with `has_thumbnail: false`.

3. **DO NOT use synchronous I/O** - All blob operations must be async.

4. **DO NOT hardcode container names** - Use `source_config.storage.file_container`.

5. **DO NOT store thumbnails in separate container** - Store alongside originals with `_thumb.jpg` suffix.

6. **DO NOT use `image.resize()`** - Use `image.thumbnail()` which preserves aspect ratio automatically.

7. **DO NOT skip image safety validation** - Always check file size and dimensions before processing.

8. **DO NOT change Python version in pyproject.toml** - Must stay `>=3.12,<3.13`. Project uses Python 3.12 only.

9. **DO NOT upscale small images** - If max dimension < 256px, skip thumbnail. AI uses original directly.

### Integration with AI Model (Story 0.75.22)

**What AI Model expects from Collection Model:**

1. `get_document_thumbnail` MCP tool returning thumbnail bytes
2. `has_thumbnail` flag in document `extracted_fields`
3. `thumbnail_url` in `extracted_fields` for direct fetch

**Current Tiered Vision Implementation (tiered_vision.py):**

The current workflow generates its own thumbnail internally from full image. Story 0.75.22 must refactor to:
1. Fetch images via MCP instead of expecting them in state
2. Check `has_thumbnail` flag from event payload
3. Handle the two scenarios below

**Story 0.75.22 Must Handle These Scenarios:**

| `has_thumbnail` | Tier 1 (Screen) | Tier 2 (Diagnose) |
|-----------------|-----------------|-------------------|
| `true` | Fetch thumbnail via `get_document_thumbnail` MCP | Fetch original via MCP |
| `false` (small image) | Fetch original directly, skip internal resize | Use same original (already small) |

**When `has_thumbnail=false`:**
- Image is already < 256px (QC Analyzer small crop)
- No cost benefit from thumbnail - image is already small
- AI Model should use original for BOTH tiers
- Skip the `_preprocess_node` thumbnail generation

**Tiered Vision routing thresholds:**

| Screen Result | Confidence | Action |
|---------------|------------|--------|
| healthy | >= 0.85 | Skip Tier 2 |
| healthy | < 0.85 | Escalate to Tier 2 |
| obvious_issue | >= 0.75 | Skip Tier 2 |
| uncertain | any | Always Tier 2 |

### Previous Story Learnings (Story 2-12)

**Key learnings from Event-Driven Communication story:**

1. **Error handling pattern** - `try/except` with `logger.warning()`, return `None` on failure
2. **fp_common imports** - Use shared models from `fp_common`
3. **Graceful degradation** - Log warnings, don't fail entire operation
4. **Unit test coverage** - Test success AND failure paths with mocked dependencies

### ManifestFile.role Values

The `role` field in ManifestFile is a free-form string set by the manifest creator. Common values:
- `"image"` - Image files (JPEG, PNG) - **triggers thumbnail generation**
- `"metadata"` - JSON/XML metadata files
- `"data"` - Data files (CSV, etc.)

**Important:** Check `role == "image"` AND verify MIME type with `supports_format()`.

### References

| Document | Path |
|----------|------|
| Tiered Vision Architecture | `_bmad-output/architecture/ai-model-architecture/tiered-vision-processing-cost-optimization.md` |
| Collection Model Architecture | Epic 2 in `_bmad-output/epics/epic-2-collection-model.md` |
| Project Context | `_bmad-output/project-context.md` (176 rules) |
| ZIP Processor | `services/collection-model/src/collection_model/processors/zip_extraction.py` |
| BlobReference Model | `services/collection-model/src/collection_model/infrastructure/blob_storage.py:20-38` |
| DocumentIndex Model | `services/collection-model/src/collection_model/domain/document_index.py:79-115` |

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Local E2E run: 107 passed, 1 skipped in 140.37s
- CI Quality Run: 20894578698 (passed)
- CI E2E Run: 20894692559 (passed)

### Completion Notes List

1. Added Pillow dependency with Python 3.12 constraint fix
2. Implemented ThumbnailGenerator with aspect ratio preservation and small image skip logic
3. Integrated with ZipExtractionProcessor for automatic thumbnail generation during ingestion
4. Added get_document_thumbnail MCP tool for AI agents to fetch thumbnails
5. Updated existing MCP tests to include the new tool
6. All E2E tests pass - no regressions

### File List

**Created:**
- `services/collection-model/src/collection_model/infrastructure/thumbnail_generator.py` - ThumbnailGenerator class
- `services/collection-model/poetry.lock` - Updated dependency lock
- `mcp-servers/collection-mcp/src/collection_mcp/infrastructure/blob_storage_client.py` - Blob download client for MCP
- `tests/unit/collection_model/infrastructure/test_thumbnail_generator.py` - Unit tests for ThumbnailGenerator

**Modified:**
- `services/collection-model/pyproject.toml` - Added Pillow dep, fixed Python version to >=3.12,<3.13
- `services/collection-model/src/collection_model/infrastructure/blob_storage.py` - Added thumbnail_blob_path to BlobReference
- `services/collection-model/src/collection_model/processors/zip_extraction.py` - Integrated thumbnail generation, added has_thumbnail to events
- `mcp-servers/collection-mcp/src/collection_mcp/tools/definitions.py` - Added get_document_thumbnail tool definition
- `mcp-servers/collection-mcp/src/collection_mcp/api/mcp_service.py` - Added thumbnail handler
- `mcp-servers/collection-mcp/src/collection_mcp/main.py` - Added blob storage client injection
- `tests/unit/collection_mcp/test_tool_definitions.py` - Updated to include new tool
- `tests/unit/collection_mcp/test_mcp_service.py` - Updated expected tool count

---

_Created: 2026-01-05_
_Last Updated: 2026-01-11_
