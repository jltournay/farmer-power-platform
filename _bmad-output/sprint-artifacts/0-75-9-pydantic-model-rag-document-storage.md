# Story 0.75.9: Pydantic Model for RAG Document Storage

**Status:** done
**GitHub Issue:** #107

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer**,
I want Pydantic models for RAG document storage,
So that knowledge documents are type-safe and properly structured.

## Acceptance Criteria

1. **AC1: RagDocument Pydantic Model** - Create `RagDocument` Pydantic model in `services/ai-model/src/ai_model/domain/rag_document.py` matching the architecture specification in `rag-document-api.md`
2. **AC2: RagChunk Model** - Create `RagChunk` Pydantic model for document chunks with parent document reference
3. **AC3: SourceFile Model** - Create `SourceFile` model for PDF extraction metadata (method, confidence, page count)
4. **AC4: RAGDocumentMetadata Model** - Create metadata model for author, source, region, season, tags
5. **AC5: Status Enum** - Create `RagDocumentStatus` enum with lifecycle states: draft, staged, active, archived
6. **AC6: Domain Enum** - Create `KnowledgeDomain` enum with knowledge domains: plant_diseases, tea_cultivation, weather_patterns, quality_standards, regional_context
7. **AC7: RagDocumentRepository** - Create repository class with CRUD operations in `services/ai-model/src/ai_model/infrastructure/repositories/rag_document_repository.py`
8. **AC8: MongoDB Collection** - Repository uses `ai_model.rag_documents` collection
9. **AC9: Specialized Repository Queries** - Implement `get_active()`, `get_by_version()`, `list_versions()`, `list_by_domain()`, `list_by_status()`
10. **AC10: Versioning Support** - Support document versioning via `document_id` + `version` combination
11. **AC11: MongoDB Indexes** - Create indexes for (document_id, status), (document_id, version unique), (domain), (status)
12. **AC12: Unit Tests** - Minimum 20 unit tests covering models, repository CRUD, and specialized queries
13. **AC13: CI Passes** - All lint checks and unit tests pass in CI

## Tasks / Subtasks

- [x] **Task 1: Create Domain Models** (AC: #1, #2, #3, #4, #5, #6) ✅
  - [x] Create `services/ai-model/src/ai_model/domain/rag_document.py`
  - [x] Implement `RagDocumentStatus` enum (draft, staged, active, archived)
  - [x] Implement `KnowledgeDomain` enum (plant_diseases, tea_cultivation, weather_patterns, quality_standards, regional_context)
  - [x] Implement `ExtractionMethod` enum (manual, text_extraction, azure_doc_intel, vision_llm)
  - [x] Implement `SourceFile` Pydantic model with extraction metadata
  - [x] Implement `RAGDocumentMetadata` Pydantic model
  - [x] Implement `RagChunk` Pydantic model with parent reference and position metadata
  - [x] Implement `RagDocument` Pydantic model with full schema

- [x] **Task 2: Create RagDocumentRepository** (AC: #7, #8, #9, #10, #11) ✅
  - [x] Create `services/ai-model/src/ai_model/infrastructure/repositories/rag_document_repository.py`
  - [x] Extend `BaseRepository[RagDocument]` pattern from prompt_repository.py
  - [x] Implement `get_active(document_id)` - get currently active version
  - [x] Implement `get_by_version(document_id, version)` - get specific version
  - [x] Implement `list_versions(document_id, include_archived)` - list all versions
  - [x] Implement `list_by_domain(domain, status)` - filter by knowledge domain
  - [x] Implement `list_by_status(status)` - filter by lifecycle status
  - [x] Implement `ensure_indexes()` - create MongoDB indexes

- [x] **Task 3: Update Package Exports** (AC: #1, #7) ✅
  - [x] Update `services/ai-model/src/ai_model/domain/__init__.py` - export new models
  - [x] Update `services/ai-model/src/ai_model/infrastructure/repositories/__init__.py` - export RagDocumentRepository

- [x] **Task 4: Unit Tests - Domain Models** (AC: #12) ✅
  - [x] Create `tests/unit/ai_model/test_rag_document.py`
  - [x] Test RagDocument model validation (required fields, types) - 10 tests
  - [x] Test RagDocumentStatus enum values and transitions - 5 tests
  - [x] Test KnowledgeDomain enum values - 2 tests
  - [x] Test SourceFile model with extraction metadata - 4 tests
  - [x] Test RagChunk model with parent reference - 4 tests
  - [x] Test RAGDocumentMetadata model - 3 tests
  - [x] Test model_dump() produces valid dict for MongoDB - 1 test
  - [x] Test model_validate() from MongoDB doc format - 1 test

- [x] **Task 5: Unit Tests - Repository** (AC: #12) ✅
  - [x] Create `tests/unit/ai_model/test_rag_document_repository.py`
  - [x] Test create() stores document correctly - 1 test
  - [x] Test get_by_id() returns document - 2 tests
  - [x] Test get_active() returns only active status - 2 tests
  - [x] Test get_by_version() returns specific version - 2 tests
  - [x] Test list_versions() returns all versions sorted - 2 tests
  - [x] Test list_by_domain() filters correctly - 2 tests
  - [x] Test list_by_status() filters correctly - 1 test
  - [x] Test ensure_indexes() creates expected indexes - 1 test

- [x] **Task 6: CI Verification** (AC: #13) ✅
  - [x] Run lint checks: `ruff check . && ruff format --check .`
  - [x] Run unit tests with correct PYTHONPATH
  - [x] Push to feature branch and verify CI passes

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [x] GitHub Issue exists or created: `#107`
- [x] Feature branch created from main: `feature/0-75-9-pydantic-model-rag-document-storage`

**Branch name:** `feature/0-75-9-pydantic-model-rag-document-storage`

### During Development
- [x] All commits reference GitHub issue: `Relates to #107`
- [x] Commits are atomic by type (production, test, seed - not mixed)
- [x] Push to feature branch: `git push -u origin feature/0-75-9-pydantic-model-rag-document-storage`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.75.9: Pydantic Model for RAG Document Storage" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d feature/0-75-9-pydantic-model-rag-document-storage`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
PYTHONPATH="${PYTHONPATH}:.:services/ai-model/src:libs/fp-common:libs/fp-proto/src" pytest tests/unit/ai_model/test_rag_document*.py -v
```
**Output:**
```
42 passed, 8 warnings in 0.43s
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
102 passed, 1 skipped in 127.24s (0:02:07)
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
git push origin feature/0-75-9-pydantic-model-rag-document-storage

# Wait ~30s, then check CI status
gh run list --branch feature/0-75-9-pydantic-model-rag-document-storage --limit 3
```
**CI Run ID:** 20726816657 (CI), 20727206246 (E2E)
**CI E2E Status:** [x] Passed / [ ] Failed
**Verification Date:** 2026-01-05

---

## Dev Notes

### CRITICAL: Follow Existing Patterns - DO NOT Reinvent

**This story follows the EXACT same pattern as Story 0.75.2 (Prompt model/repository). Reuse patterns from:**

| Component | Reference | Pattern |
|-----------|-----------|---------|
| Domain model structure | `ai_model/domain/prompt.py` | Status enum, metadata model, main entity model |
| Repository pattern | `ai_model/infrastructure/repositories/prompt_repository.py` | BaseRepository extension, specialized queries |
| Unit test pattern | `tests/unit/ai_model/test_prompt.py` (if exists) or conftest.py | Mock MongoDB, model validation |

### Architecture Reference

**From `_bmad-output/architecture/ai-model-architecture/rag-document-api.md`:**

The RAG document schema is fully defined in the architecture. Follow it exactly:

```python
# RAGDocumentMetadata - Metadata for RAG document
class RAGDocumentMetadata(BaseModel):
    author: str                              # Agronomist who created/updated
    source: str | None = None                # Original source (book, research paper, etc.)
    region: str | None = None                # Geographic relevance
    season: str | None = None                # Seasonal relevance
    tags: list[str] = []                     # Searchable tags

# SourceFile - Original uploaded file reference
class SourceFile(BaseModel):
    filename: str                            # "blister-blight-guide.pdf"
    file_type: Literal["pdf", "docx", "md", "txt"]
    blob_path: str                           # Azure Blob path
    file_size_bytes: int
    extraction_method: Literal["manual", "text_extraction", "azure_doc_intel", "vision_llm"] | None
    extraction_confidence: float | None      # 0-1 quality score
    page_count: int | None

# RagDocument - Main entity
class RagDocument(BaseModel):
    document_id: str                         # Stable ID across versions
    version: int = 1                         # Incrementing version number
    title: str
    domain: Literal["plant_diseases", "tea_cultivation", "weather_patterns", "quality_standards", "regional_context"]
    content: str                             # Extracted/authored markdown text
    source_file: SourceFile | None = None    # Original file reference (if PDF/DOCX)
    status: Literal["draft", "staged", "active", "archived"] = "draft"
    created_at: datetime
    updated_at: datetime
    metadata: RAGDocumentMetadata
    change_summary: str | None = None        # What changed from previous version
    pinecone_namespace: str | None = None    # e.g., "knowledge-v12"
    pinecone_ids: list[str] = []             # Vector IDs in Pinecone
    content_hash: str | None = None          # SHA256 for change detection
```

### RagChunk Model (NOT in architecture doc - derive from context)

RagChunk stores individual chunks of a document for vectorization:

```python
class RagChunk(BaseModel):
    chunk_id: str                            # Unique chunk ID
    document_id: str                         # Parent document reference
    document_version: int                    # Parent version reference
    chunk_index: int                         # Position in document (0-indexed)
    content: str                             # Chunk text content
    section_title: str | None = None         # Heading this chunk belongs to
    word_count: int                          # Word count for statistics
    created_at: datetime
    pinecone_id: str | None = None           # Vector ID after vectorization
```

**Note:** RagChunk is stored in a SEPARATE collection `ai_model.rag_chunks` but is NOT part of this story scope. This story only defines the Pydantic model. Story 0.75.10d (Semantic Chunking) will implement the chunking logic and repository.

### File Structure After Story

```
services/ai-model/
├── src/ai_model/
│   ├── domain/
│   │   ├── __init__.py              # MODIFIED - add exports
│   │   ├── prompt.py                # EXISTING - reference pattern
│   │   ├── agent_config.py          # EXISTING - reference pattern
│   │   ├── cost_event.py            # EXISTING
│   │   └── rag_document.py          # NEW - RagDocument, RagChunk, SourceFile, etc.
│   └── infrastructure/repositories/
│       ├── __init__.py              # MODIFIED - add export
│       ├── base.py                  # EXISTING - BaseRepository
│       ├── prompt_repository.py     # EXISTING - reference pattern
│       ├── agent_config_repository.py
│       ├── cost_event_repository.py
│       └── rag_document_repository.py  # NEW - RagDocumentRepository
└── ...

tests/unit/ai_model/
├── test_rag_document.py             # NEW - domain model tests
└── test_rag_document_repository.py  # NEW - repository tests
```

### MongoDB Collection Design

**Collection:** `ai_model.rag_documents`

**Document Structure (example):**
```json
{
  "document_id": "disease-diagnosis-guide",
  "version": 3,
  "title": "Blister Blight Treatment Guide",
  "domain": "plant_diseases",
  "content": "# Blister Blight\n\nBlister blight is caused by...",
  "status": "active",
  "source_file": {
    "filename": "blister-blight-guide.pdf",
    "file_type": "pdf",
    "blob_path": "rag-documents/disease-diagnosis-guide/v3/blister-blight-guide.pdf",
    "file_size_bytes": 245760,
    "extraction_method": "azure_doc_intel",
    "extraction_confidence": 0.96,
    "page_count": 15
  },
  "metadata": {
    "author": "Dr. Wanjiku",
    "source": "Kenya Tea Research Foundation",
    "region": "Kenya",
    "season": null,
    "tags": ["blister-blight", "fungal", "treatment"]
  },
  "change_summary": "Added new treatment protocol for resistant strains",
  "created_at": "2026-01-05T10:00:00Z",
  "updated_at": "2026-01-05T10:00:00Z",
  "pinecone_namespace": "knowledge-v3",
  "pinecone_ids": ["disease-diagnosis-guide-0", "disease-diagnosis-guide-1", "..."],
  "content_hash": "sha256:abc123..."
}
```

**Indexes:**
1. `(document_id, status)` - Fast lookup for get_active()
2. `(document_id, version)` - Unique constraint, get_by_version()
3. `(domain)` - Filter by knowledge domain
4. `(status)` - Filter by lifecycle status

### Key Design Decisions (from key-decisions.md)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| RAG Access | Internal only | Domain models don't need to know about RAG |
| RAG Curation | Admin UI (manual) | Agronomists manage knowledge |
| Instance Config | YAML → MongoDB → Pydantic | Git source, MongoDB runtime, type-safe |

### Pydantic 2.0 Requirements (CRITICAL)

Follow project-context.md Pydantic rules:
- Use `model_dump()` NOT `dict()`
- Use `model_validate()` NOT `parse_obj()`
- Use `Field(description=...)` for documentation
- Define `model_config` as class attribute, NOT `Config` inner class
- Use `datetime` from stdlib with UTC timezone

### Previous Story (0.75.8b) Learnings

From completed Story 0.75.8b:
1. **Follow existing patterns exactly** - Don't reinvent; reuse
2. **25 unit tests** - Achieved exact minimum; target 20 for this story
3. **Thread safety** - Not relevant for models, but keep in mind for cache integration later
4. **Error handling** - Use existing exception patterns

### Testing Strategy

**Unit Tests Required (minimum 20 tests):**

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_rag_document.py` | 12 | Model validation, enums, serialization |
| `test_rag_document_repository.py` | 8 | CRUD, specialized queries, indexes |

**Mock Strategy:**
- Mock MongoDB using `mock_mongodb_client` fixture from `tests/conftest.py`
- DO NOT create a local conftest.py that overrides parent fixtures

### What This Story Does NOT Include

| Not in Scope | Implemented In |
|--------------|----------------|
| gRPC service for RAG documents | Story 0.75.10 |
| PDF extraction logic | Story 0.75.10b |
| Azure Document Intelligence | Story 0.75.10c |
| Semantic chunking implementation | Story 0.75.10d |
| CLI for RAG documents | Story 0.75.11 |
| Vectorization/Pinecone integration | Stories 0.75.12-13b |
| RagChunk repository | Story 0.75.10d |

**This story provides the foundation models only. Service/API layer comes in Story 0.75.10.**

### Dependencies

**Already installed (from previous stories):**
- `pydantic` ^2.0
- `motor` (async MongoDB)
- `pymongo`

**No new dependencies required.**

### Anti-Patterns to AVOID

| Anti-Pattern | Correct Approach |
|--------------|------------------|
| Using `dict()` method | Use `model_dump()` (Pydantic 2.0) |
| Using `parse_obj()` | Use `model_validate()` (Pydantic 2.0) |
| Creating new base repository | Extend existing `BaseRepository` from `base.py` |
| Hardcoding domain values | Use `KnowledgeDomain` enum |
| Hardcoding status values | Use `RagDocumentStatus` enum |
| Creating local conftest.py that overrides fixtures | Use fixtures from root `tests/conftest.py` |
| Returning dicts from repository | Return Pydantic models |

### References

- [Source: `services/ai-model/src/ai_model/domain/prompt.py`] - Reference pattern for domain model
- [Source: `services/ai-model/src/ai_model/infrastructure/repositories/prompt_repository.py`] - Reference pattern for repository
- [Source: `services/ai-model/src/ai_model/infrastructure/repositories/base.py`] - BaseRepository to extend
- [Source: `_bmad-output/architecture/ai-model-architecture/rag-document-api.md`] - Complete schema specification
- [Source: `_bmad-output/architecture/ai-model-architecture/rag-engine.md`] - RAG engine overview
- [Source: `_bmad-output/architecture/ai-model-architecture/key-decisions.md`] - Key architectural decisions
- [Source: `_bmad-output/epics/epic-0-75-ai-model.md#story-0759`] - Story requirements
- [Source: `_bmad-output/project-context.md`] - Critical rules (Pydantic 2.0, repository patterns)

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

### File List

**Created:**
- `services/ai-model/src/ai_model/domain/rag_document.py` - RagDocument, RagChunk, SourceFile, RAGDocumentMetadata models + enums
- `services/ai-model/src/ai_model/infrastructure/repositories/rag_document_repository.py` - RagDocumentRepository with CRUD + specialized queries
- `tests/unit/ai_model/test_rag_document.py` - 29 unit tests for domain models
- `tests/unit/ai_model/test_rag_document_repository.py` - 13 unit tests for repository

**Modified:**
- `services/ai-model/src/ai_model/domain/__init__.py` - Added exports for new RAG models
- `services/ai-model/src/ai_model/infrastructure/repositories/__init__.py` - Added RagDocumentRepository export

**Architecture Deviation (Documented):**
- Added `id` field to `RagDocument` (not in architecture spec) - Required for MongoDB `_id` mapping and `get_by_id()` operations. Format: `{document_id}:v{version}`
