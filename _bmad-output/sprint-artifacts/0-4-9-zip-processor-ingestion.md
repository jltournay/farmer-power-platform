# Story 0.4.9: ZIP Processor E2E Tests (Exception Images)

**Status:** review
**GitHub Issue:** #63
**Epic:** [Epic 0.4: E2E Test Scenarios](../epics/epic-0-4-e2e-tests.md)
**Story Points:** 5
**Validates:** Story 2.5 (ZIP Content Processor for Exception Images)

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
- [ ] **Source config added** - `e2e-exception-images-zip` in seed data
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

As a **Knowledge Model AI agent**,
I want the ZIP processor for exception images validated end-to-end,
So that secondary leaf images requiring manual review are correctly extracted, stored, and events emitted.

**Context:** Story 2.5 implemented the ZipExtractionProcessor for exception images. This story provides E2E test coverage to validate the implementation works correctly in the full Docker environment.

## Acceptance Criteria

1. **AC1: Valid ZIP with Manifest** - Given source config `e2e-exception-images-zip` exists with `processor_type: zip-extraction`, When I upload a valid ZIP with manifest.json and 3 exception image documents, Then all 3 documents are created in MongoDB atomically

2. **AC2: File Extraction to Blob** - Given a ZIP contains exception images, When processing completes successfully, Then all images are extracted and stored to `exception-images-e2e` container with correct paths

3. **AC3: MCP Query Returns Documents** - Given the ZIP is processed, When I query via `get_documents(source_id="e2e-exception-images-zip")`, Then all documents from the manifest are returned

4. **AC4: Corrupt ZIP Handling** - Given a corrupt ZIP file is uploaded, When the blob event is triggered, Then processing fails gracefully with "Corrupt ZIP file detected" error

5. **AC5: Missing Manifest Handling** - Given a ZIP without manifest.json is uploaded, When the blob event is triggered, Then processing fails with "Missing manifest file: manifest.json" error

6. **AC6: Invalid Manifest Schema** - Given an invalid manifest schema is in the ZIP, When the blob event is triggered, Then processing fails with manifest validation error

7. **AC7: Path Traversal Security** - Given a ZIP with path traversal attempt (`../etc/passwd`) is uploaded, When the blob event is triggered, Then processing fails with "path traversal rejected" security error

8. **AC8: Size Limit Enforcement** - Given a ZIP exceeds 500MB size limit, When upload is attempted, Then processing fails with size limit error

9. **AC9: Duplicate Detection** - Given a duplicate ZIP (same content hash) is uploaded, When the blob event is triggered, Then the duplicate is detected and skipped

## Tasks / Subtasks

- [ ] **Task 1: Create Test Fixtures** (AC: 1, 4, 5, 6, 7, 9)
  - [ ] Create `tests/e2e/fixtures/valid_exception_batch.zip` with manifest.json and 3 exception images
  - [ ] Create `tests/e2e/fixtures/corrupt_zip.zip` (intentionally corrupt)
  - [ ] Create `tests/e2e/fixtures/missing_manifest.zip` (no manifest.json)
  - [ ] Create `tests/e2e/fixtures/invalid_manifest_schema.zip` (malformed manifest)
  - [ ] Create `tests/e2e/fixtures/path_traversal_attempt.zip` (contains `../etc/passwd`)
  - [ ] Create `tests/e2e/fixtures/generate_zip_fixtures.py` (fixture generator script)

- [ ] **Task 2: Add Source Config** (AC: 1, 2, 3)
  - [ ] Add `e2e-exception-images-zip` to `tests/e2e/infrastructure/seed/source_configs.json`
  - [ ] Configure `processor_type: zip-extraction`
  - [ ] Configure `landing_container: exception-landing-e2e` (dedicated container)
  - [ ] Configure `storage.index_collection: documents`
  - [ ] Configure `storage.file_container: exception-images-e2e`
  - [ ] Configure `events.on_success.topic: collection.exception_images.received`
  - [ ] Update `tests/e2e/conftest.py` to create required containers

- [ ] **Task 3: Create Test File Scaffold** (AC: All)
  - [ ] Create `tests/e2e/scenarios/test_08_zip_ingestion.py`
  - [ ] Import fixtures: `collection_api`, `collection_mcp`, `azurite_client`, `mongodb_direct`
  - [ ] Add `@pytest.mark.e2e` class marker
  - [ ] Add file docstring documenting test scope

- [ ] **Task 4: Implement Valid ZIP Tests** (AC: 1, 2, 3)
  - [ ] Test AC1: Upload valid_exception_batch.zip -> 3 documents created
  - [ ] Test AC2: Verify images extracted to exception-images-e2e container
  - [ ] Test AC3: Query via Collection MCP returns all documents

- [ ] **Task 5: Implement Error Handling Tests** (AC: 4, 5, 6)
  - [ ] Test AC4: Corrupt ZIP -> "Corrupt ZIP file detected"
  - [ ] Test AC5: Missing manifest -> "Missing manifest file: manifest.json"
  - [ ] Test AC6: Invalid manifest schema -> validation error

- [ ] **Task 6: Implement Security Tests** (AC: 7, 8)
  - [ ] Test AC7: Path traversal -> "path traversal rejected"
  - [ ] Test AC8: Size limit exceeded -> SKIPPED (unit test coverage only - 500MB file impractical)

- [ ] **Task 7: Implement Duplicate Detection Test** (AC: 9)
  - [ ] Test AC9: Upload same ZIP twice -> second is skipped as duplicate

- [ ] **Task 8: Test Validation** (AC: All)
  - [ ] Run `ruff check tests/e2e/scenarios/test_08_zip_ingestion.py`
  - [ ] Run `ruff format` on new files
  - [ ] Run all tests locally with Docker infrastructure
  - [ ] Verify CI pipeline passes

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.4.9: ZIP Processor E2E Tests"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-4-9-zip-processor-ingestion
  ```

**Branch name:** `story/0-4-9-zip-processor-ingestion`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #63`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/0-4-9-zip-processor-ingestion`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.4.9: ZIP Processor E2E Tests" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/0-4-9-zip-processor-ingestion`

**PR URL:** https://github.com/jltournay/farmer-power-platform/pull/64

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
pytest tests/unit/ -v
```
**Output:**
```
N/A - This is an E2E test story, no unit tests added
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
============================= test session starts ==============================
platform darwin -- Python 3.11.12, pytest-9.0.2, pluggy-1.6.0
tests/e2e/scenarios/test_08_zip_ingestion.py::TestValidZipProcessing::test_valid_zip_creates_documents PASSED [ 11%]
tests/e2e/scenarios/test_08_zip_ingestion.py::TestValidZipProcessing::test_files_extracted_to_blob_storage PASSED [ 22%]
tests/e2e/scenarios/test_08_zip_ingestion.py::TestValidZipProcessing::test_mcp_query_returns_documents PASSED [ 33%]
tests/e2e/scenarios/test_08_zip_ingestion.py::TestZipErrorHandling::test_corrupt_zip_fails_with_error PASSED [ 44%]
tests/e2e/scenarios/test_08_zip_ingestion.py::TestZipErrorHandling::test_missing_manifest_fails_with_error PASSED [ 55%]
tests/e2e/scenarios/test_08_zip_ingestion.py::TestZipErrorHandling::test_invalid_manifest_schema_fails_with_error PASSED [ 66%]
tests/e2e/scenarios/test_08_zip_ingestion.py::TestZipSecurity::test_path_traversal_attempt_rejected PASSED [ 77%]
tests/e2e/scenarios/test_08_zip_ingestion.py::TestZipSizeLimit::test_size_limit_exceeded_fails SKIPPED [ 88%]
tests/e2e/scenarios/test_08_zip_ingestion.py::TestZipDuplicateDetection::test_duplicate_zip_is_detected_and_skipped PASSED [100%]
======================== 8 passed, 1 skipped in 19.61s =========================
```
**E2E passed:** [x] Yes / [ ] No

### Full E2E Suite Regression Test
```
================== 83 passed, 1 skipped in 127.06s (0:02:07) ===================
```

### 3. Lint Check
```bash
ruff check . && ruff format --check .
```
**Lint passed:** [x] Yes / [ ] No

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
**CI Run ID:** 20658107844
**E2E Run ID:** 20658147387
**CI E2E Status:** [x] Passed / [ ] Failed
**Verification Date:** 2026-01-02

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
| services/collection-model/.../zip_extraction.py:211 | Changed error_type="zip_extraction" to "extraction" | IngestionJob model (line 80) only accepts Literal["extraction", "storage", "validation", "config"]. zip_extraction is invalid and caused Pydantic validation errors that blocked queue processing. | Bugfix |
| services/collection-model/.../exceptions.py:95 | Changed error_type="zip_extraction" to "extraction" | Same as above - ZipExtractionError used invalid error_type | Bugfix |

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

### Domain Context: Exception Images

This story validates the **ZipExtractionProcessor** for **Exception Images** - secondary leaf images requiring manual review or AI analysis by the Knowledge Model.

**Event Flow:**
- Topic: `collection.exception_images.received` (NOT quality_result.received)
- Target: Knowledge Model (NOT Plantation Model)
- Purpose: Exception image analysis, not standard quality grading

### Reference: Production Source Config

Based on `config/source-configs/qc-analyzer-exceptions.yaml`:

```yaml
source_id: qc-analyzer-exceptions
display_name: QC Analyzer - Exception Images
description: Secondary leaf images requiring manual review or AI analysis

ingestion:
  mode: blob_trigger
  landing_container: qc-analyzer-landing
  processor_type: zip-extraction
  path_pattern:
    pattern: "exceptions/{plantation_id}/{batch_id}.zip"
    extract_fields:
      - plantation_id
      - batch_id
  zip_config:
    manifest_file: manifest.json

transformation:
  ai_agent_id: qc-exception-extraction-agent
  extract_fields:
    - plantation_id
    - batch_id
    - batch_result_ref
    - exception_count
    - exception_images
  link_field: batch_result_ref

storage:
  raw_container: exception-images-raw
  file_container: exception-images
  file_path_pattern: "{plantation_id}/{batch_id}/{doc_id}/{filename}"
  index_collection: documents

events:
  on_success:
    topic: collection.exception_images.received
    payload_fields:
      - document_id
      - plantation_id
      - batch_id
      - exception_count
  on_failure:
    topic: collection.exception_images.failed
```

### E2E Source Config (Seed Data)

Add to `tests/e2e/infrastructure/seed/source_configs.json`:

```json
{
  "source_id": "e2e-exception-images-zip",
  "display_name": "E2E Exception Images ZIP",
  "enabled": true,
  "description": "E2E Test - ZIP processor for exception images (Story 0.4.9, validates Story 2.5)",
  "ingestion": {
    "mode": "blob_trigger",
    "processor_type": "zip-extraction",
    "landing_container": "exception-landing-e2e",
    "path_pattern": {
      "pattern": "{plantation_id}/{batch_id}.zip",
      "extract_fields": ["plantation_id", "batch_id"]
    },
    "zip_config": {
      "manifest_file": "manifest.json",
      "images_folder": "images",
      "extract_images": true,
      "image_storage_container": "exception-images-e2e"
    }
  },
  "transformation": {
    "ai_agent_id": null,
    "link_field": "batch_result_ref",
    "extract_fields": [
      "plantation_id",
      "batch_id",
      "batch_result_ref",
      "exception_count",
      "exception_type",
      "severity"
    ]
  },
  "storage": {
    "index_collection": "documents",
    "raw_container": "exception-raw-e2e",
    "file_container": "exception-images-e2e",
    "file_path_pattern": "{plantation_id}/{batch_id}/{doc_id}/{filename}"
  },
  "events": {
    "on_success": {
      "topic": "collection.exception_images.received",
      "payload_fields": ["document_id", "plantation_id", "batch_id", "exception_count"]
    },
    "on_failure": {
      "topic": "collection.exception_images.failed",
      "payload_fields": ["source_id", "error_type", "error_message"]
    }
  },
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

### ZIP Manifest Format (Exception Images)

```json
{
  "manifest_version": "1.0",
  "source_id": "e2e-exception-images-zip",
  "created_at": "2025-01-01T00:00:00Z",
  "linkage": {
    "plantation_id": "PLT-E2E-001",
    "batch_id": "BATCH-E2E-001",
    "batch_result_ref": "QC-RESULT-001"
  },
  "payload": {
    "exception_count": 3,
    "grading_session_id": "GS-001"
  },
  "documents": [
    {
      "document_id": "exception_001",
      "files": [
        {"path": "images/exception_001.jpg", "role": "image", "mime_type": "image/jpeg"},
        {"path": "metadata/exception_001.json", "role": "metadata"}
      ],
      "attributes": {
        "exception_type": "foreign_matter",
        "severity": "high",
        "notes": "Detected debris in sample"
      }
    }
  ]
}
```

### Test File Structure

```
tests/e2e/
├── fixtures/
│   ├── valid_exception_batch.zip      # 3 exception images with metadata
│   ├── corrupt_zip.zip                # Intentionally corrupt (invalid header)
│   ├── missing_manifest.zip           # No manifest.json inside
│   ├── invalid_manifest_schema.zip    # manifest.json with wrong structure
│   ├── path_traversal_attempt.zip     # Contains ../etc/passwd path
│   └── generate_zip_fixtures.py       # Fixture generator script
└── scenarios/
    └── test_08_zip_ingestion.py       # 9 E2E tests
```

### Containers Required

Update `tests/e2e/conftest.py` to create:
- `exception-landing-e2e` - Landing container for ZIP uploads
- `exception-images-e2e` - Extracted exception images
- `exception-raw-e2e` - Raw ZIP storage

### References

- [Source: `config/source-configs/qc-analyzer-exceptions.yaml` - Production config pattern]
- [Source: `_bmad-output/sprint-artifacts/2-5-qc-analyzer-exception-images-ingestion.md` - Story 2.5 implementation]
- [Source: `services/collection-model/src/collection_model/processors/zip_extraction.py` - ZIP processor implementation]
- [Source: `libs/fp-common/fp_common/models/domain_events.py` - Event topics]
- [Source: `tests/e2e/E2E-TESTING-MENTAL-MODEL.md` - E2E testing guide]

---

## Code Review Record

### Review Date: 2026-01-02

### Reviewer: Claude Opus 4.5 (Code Review Agent)

### Issues Found: 0 High, 0 Medium, 2 Low

### Review Outcome: **APPROVED**

### Issues Fixed:

| ID | Severity | Issue | Fix Applied |
|----|----------|-------|-------------|
| 1 | Low | Inline imports in `create_unique_zip()` reduce readability | Moved `io`, `json`, `zipfile` imports to module level in test_08_zip_ingestion.py |
| 2 | Low | Docstring in `create_dummy_jpeg()` inaccurately described image size | Updated docstring to document unused parameters |

### Review Summary:

**Strengths:**
- All 9 acceptance criteria properly covered (8 tests + 1 justified skip)
- Good test isolation with unique UUIDs per test
- Proper async/await patterns throughout
- Production bugfix is well-documented and correct
- Both CI and E2E workflows pass

**Production Code Changes (Approved):**
- `error_type="zip_extraction"` → `error_type="extraction"` is a genuine bugfix
- The IngestionJob model only accepts `Literal["extraction", "storage", "validation", "config"]`
- This pre-existing bug was discovered through E2E testing - good catch!

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Docker logs showing `error_type: 'zip_extraction'` validation error (pre-existing bug discovered during E2E testing)
- IngestionJob model definition at line 80 showing valid error_type values

### Completion Notes List

- Created E2E test file with 8 tests (1 skipped for AC8 - 500MB file impractical)
- Created ZIP fixture generator script and 5 test fixtures
- Added MongoDB helper methods for generic collection queries
- Fixed pre-existing bug: invalid `error_type="zip_extraction"` in ZIP processor
- All 83 E2E tests pass (no regressions)

### File List

**Created:**
- tests/e2e/fixtures/generate_zip_fixtures.py - ZIP fixture generator script
- tests/e2e/fixtures/valid_exception_batch.zip - Valid ZIP with 3 exception images
- tests/e2e/fixtures/corrupt_zip.zip - Intentionally corrupt ZIP
- tests/e2e/fixtures/missing_manifest.zip - ZIP without manifest.json
- tests/e2e/fixtures/invalid_manifest_schema.zip - ZIP with malformed manifest
- tests/e2e/fixtures/path_traversal_attempt.zip - ZIP with path traversal attack
- tests/e2e/scenarios/test_08_zip_ingestion.py - E2E tests for ZIP processor

**Modified:**
- tests/e2e/helpers/mongodb_direct.py - Added generic collection query methods
- tests/e2e/conftest.py - Container creation already existed (reformatted only)
- tests/e2e/infrastructure/seed/source_configs.json - e2e-exception-images-zip already existed
- services/collection-model/.../zip_extraction.py - Fixed invalid error_type (bugfix)
- services/collection-model/.../exceptions.py - Fixed invalid error_type (bugfix)
