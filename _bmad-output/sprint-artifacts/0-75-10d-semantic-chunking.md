# Story 0.75.10d: Semantic Chunking

**Status:** in-progress
**GitHub Issue:** #123

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer**,
I want semantic chunking for extracted document content,
So that documents are split into meaningful chunks for vectorization.

## Acceptance Criteria

1. **AC1: Semantic Chunker Service** - Implement `SemanticChunker` class that splits extracted content into meaningful chunks based on document structure (headings, paragraphs)
2. **AC2: Configurable Chunk Parameters** - Support configurable `chunk_size` (default 1000 chars), `chunk_overlap` (default 200 chars), and `min_chunk_size` (default 100 chars) via Settings
3. **AC3: Heading-Based Splitting** - Split primarily on Markdown headings (H1, H2, H3) to preserve semantic boundaries
4. **AC4: Paragraph Fallback** - When sections exceed `chunk_size`, split on paragraph boundaries (double newlines)
5. **AC5: Chunk Metadata** - Each chunk includes: `chunk_index`, `section_title` (parent heading), `word_count`, `char_count`
6. **AC6: RagChunk Repository** - Implement `RagChunkRepository` for CRUD operations on `ai_model.rag_chunks` MongoDB collection
7. **AC7: Chunking Workflow Integration** - Integrate chunking into `ExtractionWorkflow` so chunks are created after extraction completes
8. **AC8: Progress Tracking** - Report chunking progress via job status (`chunks_created`, `estimated_total_chunks`)
9. **AC9: gRPC Extensions** - Add `ChunkDocument` RPC and `ListChunks` RPC to `RagDocumentService`
10. **AC10: Unit Tests** - Minimum 15 unit tests covering chunker logic, repository operations, and edge cases
11. **AC11: Integration Test** - At least one integration test verifying full extraction → chunking flow
12. **AC12: CI Passes** - All lint checks and tests pass in CI

## Tasks / Subtasks

- [ ] **Task 1: Add Chunking Configuration Settings** (AC: #2)
  - [ ] Edit `services/ai-model/src/ai_model/config.py`
  - [ ] Add `chunk_size: int = 1000` setting (default 1000 chars)
  - [ ] Add `chunk_overlap: int = 200` setting (default 200 chars)
  - [ ] Add `min_chunk_size: int = 100` setting (minimum viable chunk)
  - [ ] Add `max_chunks_per_document: int = 500` setting (safety limit)

- [ ] **Task 2: Create Semantic Chunker Service** (AC: #1, #3, #4, #5)
  - [ ] Create `services/ai-model/src/ai_model/services/semantic_chunker.py`
  - [ ] Implement `SemanticChunker` class with `chunk(content: str) -> list[ChunkResult]`
  - [ ] Implement heading detection regex for H1 (`# `), H2 (`## `), H3 (`### `)
  - [ ] Implement `_split_by_headings()` to create section boundaries
  - [ ] Implement `_split_large_section()` for sections exceeding chunk_size
  - [ ] Implement `_create_chunk_with_overlap()` for maintaining context
  - [ ] Return `ChunkResult` dataclass with content, section_title, word_count, char_count

- [ ] **Task 3: Create RagChunk Repository** (AC: #6)
  - [ ] Create `services/ai-model/src/ai_model/infrastructure/repositories/rag_chunk_repository.py`
  - [ ] Implement `RagChunkRepository` class with async MongoDB operations
  - [ ] Implement `create_many(chunks: list[RagChunk]) -> list[str]` for bulk insert
  - [ ] Implement `get_by_document(document_id: str, version: int) -> list[RagChunk]`
  - [ ] Implement `delete_by_document(document_id: str, version: int) -> int` for cleanup
  - [ ] Implement `count_by_document(document_id: str, version: int) -> int`
  - [ ] Add index on `(document_id, document_version, chunk_index)`

- [ ] **Task 4: Integrate Chunking into Extraction Workflow** (AC: #7, #8)
  - [ ] Edit `services/ai-model/src/ai_model/services/extraction_workflow.py`
  - [ ] Add `SemanticChunker` dependency injection
  - [ ] Add `RagChunkRepository` dependency injection
  - [ ] After extraction completes, call chunker with extracted content
  - [ ] Create `RagChunk` instances from `ChunkResult` objects
  - [ ] Bulk insert chunks via repository
  - [ ] Update `ExtractionJob` with `chunks_created` count
  - [ ] Log chunking progress at milestones (every 50 chunks)

- [ ] **Task 5: Update ExtractionJob Model** (AC: #8)
  - [ ] Edit `services/ai-model/src/ai_model/domain/extraction_job.py`
  - [ ] Add `chunks_created: int = 0` field
  - [ ] Add `estimated_total_chunks: int | None = None` field
  - [ ] Update `ExtractionJobRepository.mark_completed()` to accept chunk count

- [ ] **Task 6: Add gRPC Service Extensions** (AC: #9)
  - [ ] Edit `proto/ai_model/v1/ai_model.proto`
  - [ ] Add `ChunkDocumentRequest` and `ChunkDocumentResponse` messages
  - [ ] Add `ListChunksRequest` and `ListChunksResponse` messages
  - [ ] Add `RagChunk` message definition
  - [ ] Add `ChunkDocument` RPC to `RagDocumentService`
  - [ ] Add `ListChunks` RPC to `RagDocumentService`
  - [ ] Run `make proto` to regenerate stubs

- [ ] **Task 7: Implement gRPC Service Methods** (AC: #9)
  - [ ] Edit `services/ai-model/src/ai_model/api/rag_document_service.py`
  - [ ] Implement `ChunkDocument` RPC handler
  - [ ] Implement `ListChunks` RPC handler
  - [ ] Wire repository and chunker dependencies

- [ ] **Task 8: Unit Tests** (AC: #10)
  - [ ] Create `tests/unit/ai_model/test_semantic_chunker.py`
  - [ ] Test heading-based splitting (H1, H2, H3 boundaries)
  - [ ] Test paragraph fallback for large sections
  - [ ] Test chunk overlap preservation
  - [ ] Test minimum chunk size enforcement
  - [ ] Test empty content handling
  - [ ] Test content with no headings (paragraph-only)
  - [ ] Test chunk metadata accuracy (word_count, section_title)
  - [ ] Create `tests/unit/ai_model/test_rag_chunk_repository.py`
  - [ ] Test bulk create operations
  - [ ] Test get_by_document retrieval
  - [ ] Test delete_by_document cleanup

- [ ] **Task 9: Integration Test** (AC: #11)
  - [ ] Add integration test to `tests/unit/ai_model/test_extraction_workflow.py`
  - [ ] Test full flow: PDF upload → extraction → chunking → chunk storage
  - [ ] Verify chunks reference correct document_id and version

- [ ] **Task 10: CI Verification** (AC: #12)
  - [ ] Run lint checks: `ruff check . && ruff format --check .`
  - [ ] Run unit tests with correct PYTHONPATH
  - [ ] Push to feature branch and verify CI passes

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.75.10d: Semantic Chunking"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/0-75-10d-semantic-chunking
  ```

**Branch name:** `feature/0-75-10d-semantic-chunking`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin feature/0-75-10d-semantic-chunking`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.75.10d: Semantic Chunking" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d feature/0-75-10d-semantic-chunking`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
PYTHONPATH="${PYTHONPATH}:.:services/ai-model/src:libs/fp-common:libs/fp-proto/src" pytest tests/unit/ai_model/test_semantic_chunker.py tests/unit/ai_model/test_rag_chunk_repository.py -v
```
**Output:**
```
(paste test summary here - e.g., "XX passed in X.XXs")
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
git push origin feature/0-75-10d-semantic-chunking

# Wait ~30s, then check CI status
gh run list --branch feature/0-75-10d-semantic-chunking --limit 3
```
**CI Run ID:** _______________
**CI Status:** [ ] Passed / [ ] Failed
**E2E CI Run ID:** _______________
**E2E CI Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### CRITICAL: Follow Existing Patterns - DO NOT Reinvent

**This story builds on Stories 0.75.10, 0.75.10b, and 0.75.10c. Reuse patterns from:**

| Component | Reference | Pattern |
|-----------|-----------|---------|
| Document extractor | `services/ai-model/src/ai_model/services/document_extractor.py` | Async extraction pattern |
| Extraction workflow | `services/ai-model/src/ai_model/services/extraction_workflow.py` | Job tracking, progress callbacks |
| RagDocument repository | `services/ai-model/src/ai_model/infrastructure/repositories/rag_document_repository.py` | MongoDB async repository |
| RagChunk model | `services/ai-model/src/ai_model/domain/rag_document.py` | **Already defined** - use this model |
| Config settings | `services/ai-model/src/ai_model/config.py` | Pydantic Settings pattern |

### RagChunk Model Already Exists (CRITICAL)

**The `RagChunk` Pydantic model is already defined in `rag_document.py`:**

```python
class RagChunk(BaseModel):
    """Individual chunk of a RAG document for vectorization."""
    chunk_id: str
    document_id: str
    document_version: int
    chunk_index: int
    content: str
    section_title: str | None = None
    word_count: int
    created_at: datetime
    pinecone_id: str | None = None  # Populated by Story 0.75.13b
```

**DO NOT create a new model.** Use this existing model and implement the repository and chunker service.

### Semantic Chunking Algorithm

**Primary Strategy: Heading-Based Splitting**

```python
import re
from dataclasses import dataclass

@dataclass
class ChunkResult:
    """Result of chunking operation."""
    content: str
    section_title: str | None
    word_count: int
    char_count: int
    chunk_index: int

class SemanticChunker:
    """Split document content into semantic chunks for vectorization.

    Chunking strategy:
    1. Split on Markdown headings (H1, H2, H3) to preserve semantic boundaries
    2. If section exceeds chunk_size, split on paragraph boundaries
    3. If paragraph exceeds chunk_size, split at sentence boundaries
    4. Apply overlap to maintain context across chunk boundaries
    """

    HEADING_PATTERN = re.compile(r'^(#{1,3})\s+(.+)$', re.MULTILINE)

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk(self, content: str) -> list[ChunkResult]:
        """Split content into semantic chunks."""
        if not content or not content.strip():
            return []

        # Step 1: Split by headings into sections
        sections = self._split_by_headings(content)

        # Step 2: Process each section
        chunks: list[ChunkResult] = []
        chunk_index = 0

        for section_title, section_content in sections:
            # If section fits in one chunk, keep it whole
            if len(section_content) <= self.chunk_size:
                if len(section_content) >= self.min_chunk_size:
                    chunks.append(ChunkResult(
                        content=section_content,
                        section_title=section_title,
                        word_count=len(section_content.split()),
                        char_count=len(section_content),
                        chunk_index=chunk_index,
                    ))
                    chunk_index += 1
            else:
                # Section too large - split further
                sub_chunks = self._split_large_section(
                    section_content, section_title, chunk_index
                )
                chunks.extend(sub_chunks)
                chunk_index += len(sub_chunks)

        return chunks

    def _split_by_headings(self, content: str) -> list[tuple[str | None, str]]:
        """Split content by Markdown headings.

        Returns list of (section_title, section_content) tuples.
        Content before first heading has section_title=None.
        """
        sections: list[tuple[str | None, str]] = []

        # Find all heading positions
        matches = list(self.HEADING_PATTERN.finditer(content))

        if not matches:
            # No headings - return entire content as one section
            return [(None, content.strip())]

        # Content before first heading
        if matches[0].start() > 0:
            pre_content = content[:matches[0].start()].strip()
            if pre_content:
                sections.append((None, pre_content))

        # Process each heading and its content
        for i, match in enumerate(matches):
            heading_text = match.group(2).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            section_content = content[start:end].strip()

            # Include heading in content for context
            full_content = f"{match.group(0)}\n\n{section_content}"
            sections.append((heading_text, full_content.strip()))

        return sections

    def _split_large_section(
        self,
        content: str,
        section_title: str | None,
        start_index: int,
    ) -> list[ChunkResult]:
        """Split a large section into smaller chunks.

        Uses paragraph boundaries (double newlines) for splitting.
        """
        paragraphs = content.split('\n\n')
        chunks: list[ChunkResult] = []
        current_chunk = ""
        chunk_index = start_index

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Check if adding this paragraph exceeds chunk_size
            test_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para

            if len(test_chunk) <= self.chunk_size:
                current_chunk = test_chunk
            else:
                # Save current chunk if it meets minimum size
                if len(current_chunk) >= self.min_chunk_size:
                    chunks.append(ChunkResult(
                        content=current_chunk,
                        section_title=section_title,
                        word_count=len(current_chunk.split()),
                        char_count=len(current_chunk),
                        chunk_index=chunk_index,
                    ))
                    chunk_index += 1

                    # Start new chunk with overlap
                    overlap_text = self._get_overlap_text(current_chunk)
                    current_chunk = f"{overlap_text}\n\n{para}" if overlap_text else para
                else:
                    # Current chunk too small, just add paragraph
                    current_chunk = test_chunk

        # Don't forget the last chunk
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            chunks.append(ChunkResult(
                content=current_chunk,
                section_title=section_title,
                word_count=len(current_chunk.split()),
                char_count=len(current_chunk),
                chunk_index=chunk_index,
            ))

        return chunks

    def _get_overlap_text(self, content: str) -> str:
        """Extract overlap text from end of content."""
        if len(content) <= self.chunk_overlap:
            return content

        # Try to break at sentence boundary within overlap region
        overlap_region = content[-self.chunk_overlap:]

        # Find last sentence end in overlap region
        sentence_ends = [
            overlap_region.rfind('. '),
            overlap_region.rfind('? '),
            overlap_region.rfind('! '),
        ]
        best_break = max(sentence_ends)

        if best_break > 0:
            return overlap_region[best_break + 2:]  # Skip ". "

        return overlap_region
```

### Workflow Integration Point (CRITICAL)

**The `ExtractionWorkflow` must be extended to include chunking:**

```python
# services/ai-model/src/ai_model/services/extraction_workflow.py

class ExtractionWorkflow:
    def __init__(
        self,
        document_repository: RagDocumentRepository,
        job_repository: ExtractionJobRepository,
        chunk_repository: RagChunkRepository,  # NEW
        blob_client: BlobStorageClient,
        settings: Settings,
    ):
        # ... existing init ...
        self._chunk_repository = chunk_repository
        self._chunker = SemanticChunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            min_chunk_size=settings.min_chunk_size,
        )

    async def _run_extraction(self, job: ExtractionJob, document: RagDocument):
        # ... existing extraction code ...

        # After extraction completes successfully:
        extraction_result = await self._extractor.extract(...)

        # Update document with extracted content
        document.content = extraction_result.content
        await self._document_repository.update(document)

        # NEW: Perform semantic chunking
        await self._perform_chunking(job, document, extraction_result.content)

    async def _perform_chunking(
        self,
        job: ExtractionJob,
        document: RagDocument,
        content: str,
    ):
        """Chunk extracted content and store in MongoDB."""
        logger.info(
            "Starting semantic chunking",
            document_id=document.document_id,
            content_length=len(content),
        )

        # Estimate total chunks for progress
        estimated_chunks = max(1, len(content) // self._chunker.chunk_size)
        await self._job_repository.update_progress(
            job.job_id,
            progress_percent=90,  # Extraction done, chunking starting
            estimated_total_chunks=estimated_chunks,
        )

        # Perform chunking
        chunk_results = self._chunker.chunk(content)

        # Convert to RagChunk domain models
        rag_chunks = [
            RagChunk(
                chunk_id=f"{document.document_id}:v{document.version}:chunk-{cr.chunk_index}",
                document_id=document.document_id,
                document_version=document.version,
                chunk_index=cr.chunk_index,
                content=cr.content,
                section_title=cr.section_title,
                word_count=cr.word_count,
            )
            for cr in chunk_results
        ]

        # Delete any existing chunks for this document version (idempotency)
        await self._chunk_repository.delete_by_document(
            document.document_id, document.version
        )

        # Bulk insert new chunks
        if rag_chunks:
            await self._chunk_repository.create_many(rag_chunks)

        # Update job with final chunk count
        await self._job_repository.update_progress(
            job.job_id,
            progress_percent=100,
            chunks_created=len(rag_chunks),
        )

        logger.info(
            "Chunking complete",
            document_id=document.document_id,
            chunks_created=len(rag_chunks),
        )
```

### gRPC Proto Extensions

**Add to `proto/ai_model/v1/ai_model.proto`:**

```protobuf
// Chunk-related messages
message RagChunk {
  string chunk_id = 1;
  string document_id = 2;
  int32 document_version = 3;
  int32 chunk_index = 4;
  string content = 5;
  optional string section_title = 6;
  int32 word_count = 7;
  google.protobuf.Timestamp created_at = 8;
  optional string pinecone_id = 9;  // Populated after vectorization
}

message ChunkDocumentRequest {
  string document_id = 1;
  optional int32 version = 2;  // If omitted, chunks latest version
}

message ChunkDocumentResponse {
  string document_id = 1;
  int32 version = 2;
  int32 chunks_created = 3;
  string job_id = 4;  // For async tracking
}

message ListChunksRequest {
  string document_id = 1;
  int32 version = 2;
  int32 page = 3;
  int32 page_size = 4;
}

message ListChunksResponse {
  repeated RagChunk chunks = 1;
  int32 total_count = 2;
  int32 page = 3;
  int32 page_size = 4;
}

// Add to RagDocumentService
service RagDocumentService {
  // ... existing RPCs ...

  // Chunk operations
  rpc ChunkDocument(ChunkDocumentRequest) returns (ChunkDocumentResponse);
  rpc ListChunks(ListChunksRequest) returns (ListChunksResponse);
}
```

### MongoDB Collection Setup

**Collection:** `ai_model.rag_chunks`

**Indexes:**
```python
# In repository initialization
await collection.create_index(
    [
        ("document_id", 1),
        ("document_version", 1),
        ("chunk_index", 1),
    ],
    unique=True,
    name="document_chunk_idx",
)

# For efficient document-based queries
await collection.create_index(
    [("document_id", 1), ("document_version", 1)],
    name="document_version_idx",
)
```

### Edge Cases to Handle

| Scenario | Behavior |
|----------|----------|
| Empty content | Return empty list, no chunks created |
| Content < min_chunk_size | Return single chunk if > 0 chars, else empty |
| No headings | Split on paragraphs only |
| Single heading, huge content | Split into multiple chunks under that heading |
| Nested headings (H1 > H2 > H3) | Treat each as section boundary |
| Code blocks in Markdown | Preserve code blocks intact (don't split mid-block) |
| Very long single paragraph | Split at sentence boundaries |

### Previous Story Intelligence (Stories 0.75.10b/10c)

**Key Learnings:**
1. **PyMuPDF is synchronous** - Already wrapped in `run_in_executor()` for async
2. **Progress callback pattern** - Use `asyncio.run_coroutine_threadsafe()` for updates from sync context
3. **Job repository pattern** - `mark_completed()` accepts additional metadata fields
4. **ExtractionResult dataclass** - Has `content`, `page_count`, `extraction_method`, `confidence`, `warnings`

**Files to extend (not create from scratch):**
- `services/ai-model/src/ai_model/services/extraction_workflow.py` - Add chunking step
- `services/ai-model/src/ai_model/domain/extraction_job.py` - Add chunk fields
- `services/ai-model/src/ai_model/infrastructure/repositories/extraction_job_repository.py` - Update methods

### File Structure After Story

```
services/ai-model/
├── src/ai_model/
│   ├── config.py                      # MODIFIED - add chunking settings
│   ├── domain/
│   │   ├── rag_document.py            # EXISTING - RagChunk already defined
│   │   └── extraction_job.py          # MODIFIED - add chunk fields
│   ├── services/
│   │   ├── semantic_chunker.py        # NEW - chunking service
│   │   ├── document_extractor.py      # EXISTING - no changes
│   │   └── extraction_workflow.py     # MODIFIED - integrate chunking
│   ├── infrastructure/
│   │   └── repositories/
│   │       ├── rag_document_repository.py     # EXISTING - no changes
│   │       ├── rag_chunk_repository.py        # NEW - chunk storage
│   │       └── extraction_job_repository.py   # MODIFIED - chunk fields
│   └── api/
│       └── rag_document_service.py    # MODIFIED - add chunk RPCs

proto/ai_model/v1/
└── ai_model.proto                     # MODIFIED - add chunk messages/RPCs

tests/
├── unit/ai_model/
│   ├── test_semantic_chunker.py       # NEW - chunker unit tests
│   ├── test_rag_chunk_repository.py   # NEW - repository tests
│   └── test_extraction_workflow.py    # MODIFIED - integration tests
```

### Testing Strategy

**Unit Tests Required (minimum 15 tests):**

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_semantic_chunker.py` | 10 | Chunking algorithm, edge cases |
| `test_rag_chunk_repository.py` | 5 | CRUD operations, bulk insert |

**Key Test Cases:**

```python
import pytest
from ai_model.services.semantic_chunker import SemanticChunker, ChunkResult

class TestSemanticChunker:
    """Test semantic chunking algorithm."""

    def test_empty_content_returns_empty_list(self):
        chunker = SemanticChunker()
        assert chunker.chunk("") == []
        assert chunker.chunk("   ") == []

    def test_small_content_single_chunk(self):
        chunker = SemanticChunker(chunk_size=1000)
        content = "# Title\n\nShort content."
        chunks = chunker.chunk(content)
        assert len(chunks) == 1
        assert chunks[0].section_title == "Title"

    def test_heading_based_splitting(self):
        chunker = SemanticChunker(chunk_size=500)
        content = """# Section 1

Content for section 1.

## Section 2

Content for section 2.

### Section 3

Content for section 3.
"""
        chunks = chunker.chunk(content)
        assert len(chunks) >= 3
        section_titles = [c.section_title for c in chunks]
        assert "Section 1" in section_titles
        assert "Section 2" in section_titles
        assert "Section 3" in section_titles

    def test_large_section_splits_on_paragraphs(self):
        chunker = SemanticChunker(chunk_size=200, min_chunk_size=50)
        # Create content with one heading but multiple paragraphs
        paragraphs = ["Paragraph " + str(i) + " " * 50 for i in range(10)]
        content = "# Big Section\n\n" + "\n\n".join(paragraphs)
        chunks = chunker.chunk(content)
        assert len(chunks) > 1  # Should split into multiple chunks
        for chunk in chunks:
            assert chunk.section_title == "Big Section"

    def test_chunk_overlap_preserved(self):
        chunker = SemanticChunker(chunk_size=100, chunk_overlap=20, min_chunk_size=30)
        content = "# Title\n\n" + "Word " * 100  # ~500 chars
        chunks = chunker.chunk(content)
        # Check that chunks have some overlap
        if len(chunks) > 1:
            for i in range(len(chunks) - 1):
                # End of chunk i should appear in start of chunk i+1
                end_of_current = chunks[i].content[-20:]
                # Overlap should be present
                assert len(chunks[i + 1].content) > 0

    def test_no_headings_splits_on_paragraphs(self):
        chunker = SemanticChunker(chunk_size=200, min_chunk_size=50)
        content = "Para 1 " * 20 + "\n\n" + "Para 2 " * 20 + "\n\n" + "Para 3 " * 20
        chunks = chunker.chunk(content)
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.section_title is None  # No heading

    def test_word_count_accuracy(self):
        chunker = SemanticChunker()
        content = "# Title\n\nOne two three four five."
        chunks = chunker.chunk(content)
        assert len(chunks) == 1
        # "# Title" + "One two three four five." = 7 words
        assert chunks[0].word_count == 7

    def test_chunk_index_sequential(self):
        chunker = SemanticChunker(chunk_size=100, min_chunk_size=20)
        content = "# S1\n\n" + "A " * 50 + "\n\n# S2\n\n" + "B " * 50
        chunks = chunker.chunk(content)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_min_chunk_size_enforced(self):
        chunker = SemanticChunker(min_chunk_size=50)
        content = "# Title\n\nTiny."  # < 50 chars
        chunks = chunker.chunk(content)
        # Should still create chunk if content exists but is small
        # Behavior depends on implementation - either skip or allow
        # This test documents expected behavior
```

### Dependencies

**No new dependencies required.** Uses existing:
- `pymupdf` (already installed)
- `motor` (async MongoDB)
- `pydantic` v2
- `structlog`

### Anti-Patterns to AVOID

| Anti-Pattern | Correct Approach |
|--------------|------------------|
| Creating new `RagChunk` model | Use existing model in `rag_document.py` |
| Synchronous MongoDB operations | Use async `motor` client |
| Hardcoding chunk sizes | Use Settings configuration |
| Splitting mid-word | Always split at word/sentence boundaries |
| Ignoring empty chunks | Filter out chunks below min_chunk_size |
| Creating chunks without section_title | Preserve heading context |

### References

- [Source: `services/ai-model/src/ai_model/domain/rag_document.py`] - RagChunk model (lines 156-197)
- [Source: `services/ai-model/src/ai_model/services/extraction_workflow.py`] - Workflow to extend
- [Source: `_bmad-output/architecture/ai-model-architecture/rag-document-api.md`] - Chunking architecture
- [Source: `_bmad-output/epics/epic-0-75-ai-model.md#story-07510d`] - Story requirements
- [Source: `_bmad-output/sprint-artifacts/0-75-10c-azure-document-intelligence-integration.md`] - Previous story patterns

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
