# Story 0.4.9: ZIP Processor Ingestion

**Status:** ready-for-dev
**GitHub Issue:** <!-- Auto-created by dev-story workflow -->
**Epic:** [Epic 0.4: E2E Test Scenarios](../epics/epic-0-4-e2e-tests.md)
**Story Points:** 5

---

## CRITICAL REQUIREMENTS FOR DEV AGENT

> **READ THIS FIRST - Story is NOT done until ALL these steps are completed!**

### 1. E2E Tests REQUIRE Docker (MANDATORY)

This is an E2E story. Tests run against **real Docker containers**, not mocks.

```bash
# STEP 1: Start Docker infrastructure BEFORE writing any test code
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build

# STEP 2: Wait for ALL services to be healthy (takes ~60 seconds)
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml ps
# All services must show "healthy" status before running tests

# STEP 3: Run tests locally (MANDATORY before any push)
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/test_08_zip_ingestion.py -v

# STEP 4: Cleanup when done
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
```

**DO NOT say story is done without running tests locally with Docker!**

### 2. CI Runs on Feature Branches (NOT just main)

**Step-by-step to verify CI on your branch:**

```bash
# 1. Push your changes to the feature branch
git push origin story/0-4-9-zip-processor-ingestion

# 2. Wait ~30 seconds for CI to start, then check status
gh run list --branch story/0-4-9-zip-processor-ingestion --limit 3

# 3. Trigger E2E tests (does NOT auto-run)
gh workflow run e2e.yaml --ref story/0-4-9-zip-processor-ingestion

# 4. Wait for workflow to complete
sleep 10
gh run list --workflow=e2e.yaml --branch story/0-4-9-zip-processor-ingestion --limit 1
```

**Both CI workflows must pass:**
1. **CI workflow** - Unit tests, lint, format check
2. **E2E Tests workflow** - End-to-end tests with Docker

### 3. Update GitHub Issue (MANDATORY)

After implementation, add a comment to the GitHub Issue with:
- Implementation summary
- Test results (pass/fail count)
- Any issues encountered

### 4. Definition of Done Checklist

Story is **NOT DONE** until ALL of these are true:

- [ ] **Tests written** - All 9 tests in `test_08_zip_ingestion.py`
- [ ] **Test fixtures created** - ZIP files in `tests/e2e/fixtures/`
- [ ] **Source config added** - `e2e-qc-analyzer-zip` in seed data
- [ ] **Docker running** - E2E infrastructure started with `docker compose up -d --build`
- [ ] **Tests pass locally** - `pytest` output shows all green (paste evidence below)
- [ ] **Lint passes** - `ruff check . && ruff format --check .`
- [ ] **Pushed to feature branch** - `git push origin story/0-4-9-zip-processor-ingestion`
- [ ] **CI workflow passes on branch** - Verified with `gh run list --branch`
- [ ] **E2E Tests workflow passes on branch** - Run `gh workflow run e2e.yaml --ref story/0-4-9-zip-processor-ingestion`
- [ ] **GitHub issue updated** - Comment with implementation summary
- [ ] **Story file updated** - Fill in "Local Test Run Evidence" section below with actual output

---

## Story

As a **data engineer**,
I want ZIP file ingestion validated with manifest parsing and atomic storage,
So that bulk QC analyzer uploads are processed correctly.

## Acceptance Criteria

1. **AC1: Valid ZIP with Manifest** - Given source config `e2e-qc-analyzer-zip` exists with `processor_type: zip-extraction`, When I upload a valid ZIP with manifest.json and 3 documents, Then all 3 documents are created in MongoDB atomically

2. **AC2: File Extraction to Blob** - Given a ZIP contains multiple documents, When processing completes successfully, Then all files are extracted and stored to blob storage with correct paths

3. **AC3: MCP Query Returns Documents** - Given the ZIP is processed, When I query via `get_documents(source_id="e2e-qc-analyzer-zip")`, Then all documents from the manifest are returned

4. **AC4: Corrupt ZIP Handling** - Given a corrupt ZIP file is uploaded, When the blob event is triggered, Then processing fails gracefully with "Corrupt ZIP file detected" error

5. **AC5: Missing Manifest Handling** - Given a ZIP without manifest.json is uploaded, When the blob event is triggered, Then processing fails with "Missing manifest file: manifest.json" error

6. **AC6: Invalid Manifest Schema** - Given an invalid manifest schema is in the ZIP, When the blob event is triggered, Then processing fails with manifest validation error

7. **AC7: Path Traversal Security** - Given a ZIP with path traversal attempt (`../etc/passwd`) is uploaded, When the blob event is triggered, Then processing fails with "path traversal rejected" security error

8. **AC8: Size Limit Enforcement** - Given a ZIP exceeds 500MB size limit, When upload is attempted, Then processing fails with size limit error

9. **AC9: Duplicate Detection** - Given a duplicate ZIP (same content hash) is uploaded, When the blob event is triggered, Then the duplicate is detected and skipped

## Tasks / Subtasks

- [ ] **Task 1: Create Test Fixtures** (AC: 1, 4, 5, 6, 7, 9)
  - [ ] Create `tests/e2e/fixtures/valid_batch_3_docs.zip` with manifest.json and 3 leaf samples
  - [ ] Create `tests/e2e/fixtures/corrupt_zip.zip` (intentionally corrupt)
  - [ ] Create `tests/e2e/fixtures/missing_manifest.zip` (no manifest.json)
  - [ ] Create `tests/e2e/fixtures/invalid_manifest_schema.zip` (malformed manifest)
  - [ ] Create `tests/e2e/fixtures/path_traversal_attempt.zip` (contains `../etc/passwd`)

- [ ] **Task 2: Add Source Config** (AC: 1, 2, 3)
  - [ ] Add `e2e-qc-analyzer-zip` to `tests/e2e/infrastructure/seed/source_configs.json`
  - [ ] Configure `processor_type: zip-extraction`
  - [ ] Configure `storage.index_collection: quality_documents`
  - [ ] Configure `storage.file_container: extracted-files-e2e`
  - [ ] Configure `events.on_success.topic: collection.quality_result.received`

- [ ] **Task 3: Create Test File Scaffold** (AC: All)
  - [ ] Create `tests/e2e/scenarios/test_08_zip_ingestion.py`
  - [ ] Import fixtures: `collection_api`, `collection_mcp`, `azurite_client`, `mongodb_direct`
  - [ ] Add `@pytest.mark.e2e` class marker
  - [ ] Add file docstring documenting test scope

- [ ] **Task 4: Implement Valid ZIP Tests** (AC: 1, 2, 3)
  - [ ] Test AC1: Upload valid_batch_3_docs.zip → 3 documents created
  - [ ] Test AC2: Verify files extracted to blob storage
  - [ ] Test AC3: Query via Collection MCP returns all documents

- [ ] **Task 5: Implement Error Handling Tests** (AC: 4, 5, 6)
  - [ ] Test AC4: Corrupt ZIP → "Corrupt ZIP file detected"
  - [ ] Test AC5: Missing manifest → "Missing manifest file: manifest.json"
  - [ ] Test AC6: Invalid manifest schema → validation error

- [ ] **Task 6: Implement Security Tests** (AC: 7, 8)
  - [ ] Test AC7: Path traversal → "path traversal rejected"
  - [ ] Test AC8: Size limit exceeded → size limit error

- [ ] **Task 7: Implement Duplicate Detection Test** (AC: 9)
  - [ ] Test AC9: Upload same ZIP twice → second is skipped as duplicate

- [ ] **Task 8: Test Validation** (AC: All)
  - [ ] Run `ruff check tests/e2e/scenarios/test_08_zip_ingestion.py`
  - [ ] Run `ruff format` on new files
  - [ ] Run all tests locally with Docker infrastructure
  - [ ] Verify CI pipeline passes

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.4.9: ZIP Processor Ingestion"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-4-9-zip-processor-ingestion
  ```

**Branch name:** `story/0-4-9-zip-processor-ingestion`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/0-4-9-zip-processor-ingestion`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.4.9: ZIP Processor Ingestion" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/0-4-9-zip-processor-ingestion`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
pytest tests/unit/ -v
```
**Output:**
```
(paste test summary here - e.g., "42 passed in 5.23s")
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure (--build is MANDATORY to include code changes)
docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build

# Wait for services, then run tests
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/test_08_zip_ingestion.py -v

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
git push origin story/0-4-9-zip-processor-ingestion

# Wait ~30s, then check CI status
gh run list --branch story/0-4-9-zip-processor-ingestion --limit 3

# Trigger E2E tests (MANDATORY - does NOT auto-run)
gh workflow run e2e.yaml --ref story/0-4-9-zip-processor-ingestion
sleep 10
gh run list --workflow=e2e.yaml --branch story/0-4-9-zip-processor-ingestion --limit 1
```
**CI Run ID:** _______________
**E2E Run ID:** _______________
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## E2E Story Checklist (MANDATORY for E2E stories)

**Read First:** `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

### Pre-Implementation
- [ ] Read and understood `E2E-TESTING-MENTAL-MODEL.md`
- [ ] Understand: Proto = source of truth, tests verify (not define) behavior

### Before Starting Docker
- [ ] Validate seed data: `PYTHONPATH="${PYTHONPATH}:services/plantation-model/src:services/collection-model/src" python tests/e2e/infrastructure/validate_seed_data.py`
- [ ] All seed files pass validation

### During Implementation
- [ ] If tests fail, investigate using the debugging checklist (not blindly modify code)
- [ ] If seed data needs changes, fix seed data (not production code)
- [ ] If production code has bugs, document each fix (see below)

### Production Code Changes (if any)
If you modified ANY production code (`services/`, `mcp-servers/`, `libs/`), document each change here:

| File:Lines | What Changed | Why (with evidence) | Type |
|------------|--------------|---------------------|------|
| (none) | | | |

**Rules:**
- "To pass tests" is NOT a valid reason
- Must reference proto line, API spec, or other evidence
- If you can't fill this out, you may not understand what you're changing

### Infrastructure/Integration Changes (if any)
If you modified mock servers, docker-compose, env vars, or seed data that affects service behavior:

| File | What Changed | Why | Impact |
|------|--------------|-----|--------|
| (none) | | | |

### Unit Test Changes (if any)
If you modified ANY unit test behavior, document here:

| Test File | Test Name Before | Test Name After | Behavior Change | Justification |
|-----------|------------------|-----------------|-----------------|---------------|
| (none) | | | | |

### Local Test Run Evidence (MANDATORY before any push)

**First run timestamp:** _______________

**Docker stack status:**
```
# Paste output of: docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml ps
```

**Test run output:**
```
# Paste output of: pytest tests/e2e/scenarios/test_08_zip_ingestion.py -v
# Must show: 9 passed, 0 failed
```

**If tests failed before passing, explain what you fixed:**

| Attempt | Failure | Root Cause | Fix Applied | Layer Fixed |
|---------|---------|------------|-------------|-------------|
| 1 | | | | |

### Before Marking Done
- [ ] All tests pass locally with Docker infrastructure
- [ ] `ruff check` and `ruff format --check` pass
- [ ] CI pipeline is green
- [ ] E2E CI workflow triggered and passed
- [ ] If production code changed: Change log above is complete
- [ ] If unit tests changed: Change log above is complete
- [ ] Story file updated with completion notes

---

## Dev Notes

### ZIP Processor Architecture

This story validates the **ZipExtractionProcessor** which handles bulk QC analyzer uploads.

```
ZIP PROCESSOR INGESTION FLOW (Story 0.4.9)

┌─────────────────────────────────────────────────────────────────────────┐
│                         ZIP INGESTION PIPELINE                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. UPLOAD                2. TRIGGER               3. PROCESS           │
│  ┌─────────────┐         ┌─────────────┐         ┌─────────────┐       │
│  │  valid.zip  │ ──────► │  Azurite    │ ──────► │  Collection │       │
│  │  (3 docs)   │  blob   │  Blob Event │  POST   │    Model    │       │
│  └─────────────┘         └─────────────┘  /blob  └──────┬──────┘       │
│                                                          │              │
│  4. VALIDATE              5. EXTRACT               6. STORE            │
│  ┌─────────────┐         ┌─────────────┐         ┌─────────────┐       │
│  │  manifest   │ ──────► │   Files to  │ ──────► │   MongoDB   │       │
│  │  .json      │  parse  │    Blob     │ atomic  │  Documents  │       │
│  └─────────────┘         └─────────────┘         └─────────────┘       │
│                                                                         │
│  SECURITY CHECKS:                                                       │
│  - Corrupt ZIP detection (testzip())                                   │
│  - Missing manifest detection                                          │
│  - Manifest schema validation (Pydantic)                               │
│  - Path traversal rejection (../)                                      │
│  - Size limit enforcement (500MB max)                                  │
│  - Content hash deduplication                                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### ZIP Manifest Format

**Source:** `services/collection-model/src/collection_model/domain/manifest.py`

```json
{
  "manifest_version": "1.0",
  "source_id": "e2e-qc-analyzer-zip",
  "created_at": "2025-01-01T00:00:00Z",
  "linkage": {
    "farmer_id": "FRM-E2E-ZIP-001",
    "factory_id": "FAC-E2E-001"
  },
  "payload": {
    "grading_model_id": "tbk_kenya_tea_v1",
    "grading_model_version": "1.0.0"
  },
  "documents": [
    {
      "document_id": "leaf_001",
      "files": [
        {"path": "images/leaf_001.jpg", "role": "image", "mime_type": "image/jpeg"},
        {"path": "metadata/leaf_001.json", "role": "metadata"}
      ],
      "attributes": {
        "leaf_type": "two_leaves_bud",
        "grade": "Primary",
        "weight_kg": 5.0
      }
    }
  ]
}
```

### ZipExtractionProcessor Key Methods

**Source:** `services/collection-model/src/collection_model/processors/zip_extraction.py`

| Method | Purpose |
|--------|---------|
| `process()` | Main entry point - orchestrates ZIP processing pipeline |
| `_download_blob()` | Downloads ZIP from Azure Blob Storage |
| `_store_raw_zip()` | Stores raw ZIP before processing |
| `_extract_and_validate_manifest()` | Extracts and validates manifest.json |
| `_process_document()` | Processes each document in manifest |
| `_extract_and_store_file()` | Extracts files with path traversal check |
| `_store_documents_atomic()` | Atomic MongoDB batch insert |

### Security Validations

| Check | Location | Error |
|-------|----------|-------|
| Corrupt ZIP | Line 337-338 | "Corrupt ZIP file detected" |
| Missing manifest | Line 345-346 | "Missing manifest file: manifest.json" |
| Invalid schema | Line 357-360 | "Invalid manifest structure: ..." |
| Path traversal | Line 461-464 | "path traversal rejected" |
| Size limit | Line 122-123 | "ZIP exceeds maximum size" |
| Document count | Line 139-142 | "ZIP exceeds maximum document count" |

### Source Config for ZIP Ingestion

Add to `tests/e2e/infrastructure/seed/source_configs.json`:

```json
{
  "source_id": "e2e-qc-analyzer-zip",
  "display_name": "E2E QC Analyzer ZIP",
  "enabled": true,
  "description": "E2E Test - ZIP processor for bulk QC analyzer uploads (Story 0.4.9)",
  "ingestion": {
    "mode": "blob_trigger",
    "processor_type": "zip-extraction",
    "landing_container": "quality-events-e2e",
    "path_pattern": {
      "pattern": "zip/{factory_id}/{batch_id}.zip",
      "extract_fields": ["factory_id", "batch_id"]
    },
    "zip_config": {
      "manifest_file": "manifest.json"
    }
  },
  "transformation": {
    "ai_agent_id": null,
    "link_field": "farmer_id",
    "extract_fields": [
      "farmer_id",
      "factory_id",
      "grading_model_id",
      "grading_model_version",
      "leaf_type",
      "grade",
      "weight_kg"
    ]
  },
  "storage": {
    "index_collection": "quality_documents",
    "raw_container": "raw-documents-e2e",
    "file_container": "extracted-files-e2e",
    "file_path_pattern": "{source_id}/{farmer_id}/{doc_id}/{filename}"
  },
  "events": {
    "on_success": {
      "topic": "collection.quality_result.received",
      "payload_fields": ["farmer_id", "document_count"]
    }
  },
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

### Test File Structure

```
tests/e2e/
├── fixtures/
│   ├── valid_batch_3_docs.zip      # 3 leaf samples with images + metadata
│   ├── corrupt_zip.zip             # Intentionally corrupt (invalid header)
│   ├── missing_manifest.zip        # No manifest.json inside
│   ├── invalid_manifest_schema.zip # manifest.json with wrong structure
│   └── path_traversal_attempt.zip  # Contains ../etc/passwd path
└── scenarios/
    └── test_08_zip_ingestion.py    # 9 E2E tests
```

### Test Implementation Pattern

```python
@pytest.mark.e2e
class TestValidZipIngestion:
    """Valid ZIP ingestion tests (AC1-AC3)."""

    @pytest.mark.asyncio
    async def test_valid_zip_creates_all_documents(
        self,
        collection_api,
        azurite_client,
        mongodb_direct,
        seed_data,
    ):
        """AC1: Upload valid ZIP with 3 documents → all created atomically."""
        # 1. Load valid_batch_3_docs.zip from fixtures
        zip_path = Path(__file__).parent.parent / "fixtures" / "valid_batch_3_docs.zip"
        with open(zip_path, "rb") as f:
            zip_content = f.read()

        # 2. Upload to Azurite
        blob_path = "zip/FAC-E2E-001/batch_001.zip"
        await azurite_client.upload_blob(
            container="quality-events-e2e",
            blob_path=blob_path,
            content=zip_content,
        )

        # 3. Trigger blob event
        result = await collection_api.trigger_blob_event(
            container="quality-events-e2e",
            blob_path=blob_path,
        )
        assert result["accepted"] is True

        # 4. Wait for processing
        await asyncio.sleep(5)

        # 5. Verify 3 documents created
        documents = await mongodb_direct.find_documents(
            collection="quality_documents",
            query={"ingestion.source_id": "e2e-qc-analyzer-zip"},
        )
        assert len(documents) == 3, f"Expected 3 documents, got {len(documents)}"
```

### Creating Test ZIP Files

Use Python's zipfile module to create test fixtures programmatically:

```python
import io
import json
import zipfile

def create_valid_batch_zip():
    """Create valid_batch_3_docs.zip for E2E tests."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Create manifest
        manifest = {
            "manifest_version": "1.0",
            "source_id": "e2e-qc-analyzer-zip",
            "created_at": "2025-01-01T00:00:00Z",
            "linkage": {
                "farmer_id": "FRM-E2E-ZIP-001",
                "factory_id": "FAC-E2E-001"
            },
            "payload": {
                "grading_model_id": "tbk_kenya_tea_v1"
            },
            "documents": [
                {
                    "document_id": "leaf_001",
                    "files": [
                        {"path": "metadata/leaf_001.json", "role": "metadata"}
                    ],
                    "attributes": {"leaf_type": "two_leaves_bud", "grade": "Primary"}
                },
                # ... 2 more documents
            ]
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        # Add metadata files
        for i in range(1, 4):
            metadata = {"leaf_id": f"leaf_00{i}", "weight_kg": 5.0}
            zf.writestr(f"metadata/leaf_00{i}.json", json.dumps(metadata))

    return buffer.getvalue()
```

### Test Prioritization

| Test | AC | Priority | Reason |
|------|-----|----------|--------|
| Valid ZIP (3 docs) | AC1 | P0 | Core happy path |
| File extraction | AC2 | P0 | Core functionality |
| MCP query | AC3 | P0 | Integration verification |
| Corrupt ZIP | AC4 | P0 | Security/robustness |
| Missing manifest | AC5 | P0 | Error handling |
| Invalid schema | AC6 | P1 | Validation |
| Path traversal | AC7 | P0 | **SECURITY CRITICAL** |
| Size limit | AC8 | P1 | Resource protection |
| Duplicate | AC9 | P1 | Idempotency |

### Learnings from Previous Stories

**From Story 0.4.8 (Grading Validation):**
- Delta-based assertions (`final >= 1`) are more robust than (`final > initial`) for date rollovers
- Use `get_grade_distribution()` helper pattern for before/after verification
- Query `today.grade_counts` not `historical.grade_distribution_30d` for real-time updates

**From Story 0.4.5 (Quality Blob Ingestion):**
- Blob trigger pattern: upload to Azurite → POST /events/blob → wait 3-5s → verify
- Source config `ai_agent_id: null` enables direct extraction without AI
- Use `ingestion.source_id` in MongoDB queries for document filtering

**From Story 0.4.7 (Cross-Model Events):**
- DAPR event propagation takes ~5s for cross-model updates
- Use polling helpers instead of fixed `asyncio.sleep()` for robustness

### Potential Issues to Watch

1. **Azurite container creation** - Ensure `quality-events-e2e` and `extracted-files-e2e` containers exist
2. **ZipFile testzip()** - Only catches structural corruption, not content issues
3. **Atomic storage** - MongoDB transaction support is TODO in `_store_documents_atomic()`
4. **File path patterns** - Verify `file_path_pattern` placeholders resolve correctly
5. **Content hash calculation** - Verify `RawDocumentStore` calculates consistent hashes

### References

- [Source: `_bmad-output/epics/epic-0-4-e2e-tests.md` - Story 0.4.9 acceptance criteria]
- [Source: `services/collection-model/src/collection_model/processors/zip_extraction.py` - ZIP processor implementation]
- [Source: `services/collection-model/src/collection_model/domain/manifest.py` - Manifest models]
- [Source: `tests/e2e/E2E-TESTING-MENTAL-MODEL.md` - E2E testing guide]
- [Source: `tests/e2e/scenarios/test_05_weather_ingestion.py` - Pattern to follow]
- [Source: `tests/unit/collection/test_zip_extraction.py` - Unit test coverage reference]

### Critical Implementation Notes

1. **Config-driven processor** - ZipExtractionProcessor reads all settings from `source_config`, no hardcoded values
2. **Path traversal check** - Line 461-464 rejects paths containing `..` or starting with `/`
3. **Size constants** - `MAX_ZIP_SIZE_BYTES = 500 * 1024 * 1024` (500MB), `MAX_DOCUMENTS_PER_ZIP = 10000`
4. **Manifest validation** - Uses Pydantic `ZipManifest.model_validate()` for schema validation
5. **File role grouping** - Files grouped by role (image, metadata, primary, thumbnail, attachment) in `file_refs`

---

## Code Review Record

### Review Date: _______________

### Reviewer: _______________

### Issues Found: ___ High, ___ Medium, ___ Low

### Issues Fixed:

| ID | Severity | Issue | Fix Applied |
|----|----------|-------|-------------|
| | | | |

---

## Dev Agent Record

### Agent Model Used

(To be filled by dev agent)

### Debug Log References

### Completion Notes List

### File List

**Created:**
- (list new files)

**Modified:**
- (list modified files with brief description)
