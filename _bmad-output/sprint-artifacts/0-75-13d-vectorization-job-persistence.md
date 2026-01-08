# Story 0.75.13d: Vectorization Job Persistence

**Status:** in-progress
**GitHub Issue:** #135

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **platform operator**,
I want vectorization job status persisted to Redis or MongoDB,
So that job tracking survives pod restarts and works across multiple replicas.

## Context

Story 0.75.13c implemented in-memory job tracking (`self._jobs: dict[str, VectorizationResult]`) which has the following production limitations documented in `vectorization_pipeline.py` (lines 88-94):
1. Job status is lost on pod restart
2. With multiple replicas, `get_job_status()` may miss jobs on other pods
3. No automatic cleanup - jobs accumulate over time

This story addresses these limitations by persisting job state to a shared data store.

## Acceptance Criteria

1. **AC1: Repository Pattern** - Create `VectorizationJobRepository` with async CRUD operations:
   - `create(job: VectorizationResult) -> str` - Store new job, return job_id
   - `get(job_id: str) -> VectorizationResult | None` - Get job by ID
   - `update(job: VectorizationResult) -> None` - Update existing job
   - `list_by_document(document_id: str) -> list[VectorizationResult]` - List jobs for document
   - `list_by_status(status: VectorizationJobStatus) -> list[VectorizationResult]` - Filter by status

2. **AC2: MongoDB Implementation** - Implement `MongoDBVectorizationJobRepository`:
   - MongoDB collection: `ai_model.vectorization_jobs`
   - Index on `job_id` (unique)
   - Index on `document_id` for filtering
   - Index on `status` for filtering
   - TTL index on `completed_at` for automatic cleanup (configurable, default 24h)

3. **AC3: Settings Configuration** - Add configuration in `Settings`:
   - `VECTORIZATION_JOB_TTL_HOURS: int = 24` - TTL for completed jobs
   - Storage backend is always MongoDB (no Redis option for simplicity)

4. **AC4: Pipeline Integration** - Update `VectorizationPipeline`:
   - Accept `VectorizationJobRepository` as constructor parameter
   - Replace `self._jobs: dict` with repository calls
   - `create_job()` stores via repository instead of in-memory
   - `get_job_status()` queries repository
   - `vectorize_document()` updates job via repository on completion

5. **AC5: Graceful Fallback** - If repository is None (for backwards compatibility):
   - Fall back to in-memory dict (current behavior)
   - Log warning at startup about in-memory mode

6. **AC6: CLI job-status Works Across Restarts** - Verify CLI `fp-knowledge job-status` returns correct status after AI Model pod restart

7. **AC7: Unit Tests** - Minimum 8 unit tests covering:
   - Repository CRUD operations (create, get, update)
   - Repository list operations (by document, by status)
   - TTL expiry behavior (mock time advancement)
   - Pipeline integration with repository
   - Graceful fallback to in-memory when repository is None

8. **AC8: E2E Regression (MANDATORY)** - All existing E2E tests continue to pass:
   - Run full E2E suite with `--build` flag to rebuild ai-model container
   - All 99 existing tests must pass (8 skipped is acceptable)
   - No modifications to existing E2E test files (except if fixing bugs)
   - Vectorization tests (`test_09_rag_vectorization.py`) must continue passing

9. **AC9: CI Passes** - All lint checks and tests pass in CI

## Tasks / Subtasks

- [ ] **Task 1: Create Pydantic Models** (AC: #1)
  - [ ] Create `VectorizationJobDocument` Pydantic model for MongoDB storage
  - [ ] Map to/from existing `VectorizationResult` domain model
  - [ ] Include MongoDB-specific fields (`_id`, `created_at`, `completed_at`)

- [ ] **Task 2: Implement Repository** (AC: #1, #2)
  - [ ] Create `ai_model/infrastructure/repositories/vectorization_job_repository.py`
  - [ ] Implement `VectorizationJobRepository` abstract base class
  - [ ] Implement `MongoDBVectorizationJobRepository` concrete class
  - [ ] Add indexes: unique on `job_id`, standard on `document_id`, `status`
  - [ ] Add TTL index on `completed_at` field

- [ ] **Task 3: Add Settings Configuration** (AC: #3)
  - [ ] Add `VECTORIZATION_JOB_TTL_HOURS` to `ai_model/config.py`
  - [ ] Default value: 24 hours
  - [ ] Document in settings docstring

- [ ] **Task 4: Update VectorizationPipeline** (AC: #4, #5)
  - [ ] Add `job_repository: VectorizationJobRepository | None = None` to constructor
  - [ ] Update `create_job()` to use repository when available
  - [ ] Update `get_job_status()` to query repository when available
  - [ ] Update `vectorize_document()` to update repository on completion
  - [ ] Add fallback to in-memory dict when repository is None
  - [ ] Log warning if using in-memory mode

- [ ] **Task 5: Wire Repository in grpc_server.py** (AC: #4)
  - [ ] Create `MongoDBVectorizationJobRepository` instance
  - [ ] Ensure indexes on startup
  - [ ] Inject into `VectorizationPipeline`

- [ ] **Task 6: Create Unit Tests** (AC: #7)
  - [ ] Create `tests/unit/ai_model/test_vectorization_job_repository.py`
  - [ ] Test create and get operations
  - [ ] Test update operation
  - [ ] Test list_by_document operation
  - [ ] Test list_by_status operation
  - [ ] Test TTL expiry (mock `datetime.now()`)
  - [ ] Test pipeline with repository injection
  - [ ] Test pipeline fallback to in-memory mode

- [ ] **Task 7: Verify CLI Works Across Restarts** (AC: #6)
  - [ ] Manual verification: Start AI Model, create job, restart pod, query job
  - [ ] Document results in this story file

- [ ] **Task 8: E2E Regression Testing (MANDATORY)** (AC: #8)
  - [ ] Rebuild and start E2E infrastructure with `--build` flag:
    ```bash
    docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build
    ```
  - [ ] Verify Docker images were rebuilt (NOT cached) for ai-model
  - [ ] Run full E2E test suite:
    ```bash
    PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v
    ```
  - [ ] Verify: 99 passed, 8 skipped (same as Story 0.75.13c baseline)
  - [ ] Capture output in "Local Test Run Evidence" section
  - [ ] Tear down infrastructure:
    ```bash
    docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
    ```

- [ ] **Task 9: CI Verification** (AC: #9)
  - [ ] Run lint: `ruff check . && ruff format --check .`
  - [ ] Run unit tests locally
  - [ ] Push and verify CI passes
  - [ ] Trigger E2E CI workflow: `gh workflow run e2e.yaml --ref <story-branch>`
  - [ ] Verify E2E CI passes before code review

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.75.13d: Vectorization Job Persistence"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/0-75-13d-vectorization-job-persistence
  ```

**Branch name:** `feature/0-75-13d-vectorization-job-persistence`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin feature/0-75-13d-vectorization-job-persistence`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.75.13d: Vectorization Job Persistence" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d feature/0-75-13d-vectorization-job-persistence`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
PYTHONPATH=".:services/ai-model/src:libs/fp-common:libs/fp-proto/src" pytest tests/unit/ai_model/test_vectorization_job_repository.py -v
```
**Output:**
```
(paste test summary here - e.g., "42 passed in 5.23s")
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure
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
git push origin feature/0-75-13d-vectorization-job-persistence

# Wait ~30s, then check CI status
gh run list --branch feature/0-75-13d-vectorization-job-persistence --limit 3
```
**CI Run ID:** _______________
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### Repository Pattern

This story follows the established repository pattern in AI Model:
- Abstract base class defines interface
- MongoDB implementation is the concrete class
- Repository is injected into services via constructor

### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `ai_model/domain/vectorization_job.py` | CREATE | Pydantic model for MongoDB storage |
| `ai_model/infrastructure/repositories/vectorization_job_repository.py` | CREATE | Repository interface + MongoDB implementation |
| `ai_model/config.py` | MODIFY | Add TTL configuration |
| `ai_model/services/vectorization_pipeline.py` | MODIFY | Add repository integration |
| `ai_model/api/grpc_server.py` | MODIFY | Wire repository |
| `tests/unit/ai_model/test_vectorization_job_repository.py` | CREATE | Unit tests |

### MongoDB Collection Schema

```python
# Collection: ai_model.vectorization_jobs
{
    "_id": ObjectId,
    "job_id": str,  # UUID, unique index
    "status": str,  # "pending" | "running" | "completed" | "partial" | "failed"
    "document_id": str,  # Index for filtering
    "document_version": int,
    "namespace": str,
    "chunks_total": int,
    "chunks_embedded": int,
    "chunks_stored": int,
    "failed_count": int,
    "content_hash": str | None,
    "pinecone_ids": list[str] | None,
    "failed_chunks": list[dict] | None,
    "started_at": datetime | None,
    "completed_at": datetime | None,  # TTL index target
    "created_at": datetime,
    "updated_at": datetime,
}
```

### TTL Index

MongoDB TTL indexes automatically delete documents after a specified time:

```python
# In repository ensure_indexes():
await self._collection.create_index(
    "completed_at",
    expireAfterSeconds=settings.vectorization_job_ttl_hours * 3600,
    partialFilterExpression={"status": {"$in": ["completed", "partial", "failed"]}}
)
```

**Note:** TTL only applies to completed jobs. Pending/running jobs are never auto-deleted.

### Design Decision: MongoDB over Redis

MongoDB was chosen over Redis because:
1. AI Model already uses MongoDB - no new infrastructure
2. TTL indexes provide automatic cleanup
3. Rich query support (filter by document_id, status)
4. Persistence guarantees match job tracking needs

Redis would be better for high-frequency reads, but vectorization jobs are infrequent (minutes to hours apart).

### Backwards Compatibility

The `VectorizationJobRepository` is optional in the constructor:

```python
def __init__(
    self,
    # ... existing params ...
    job_repository: VectorizationJobRepository | None = None,
) -> None:
```

If `None`, the pipeline falls back to in-memory dict (current behavior). This ensures:
1. Existing tests pass without modification
2. E2E tests work without MongoDB job collection
3. Gradual migration path

### Project Structure Notes

- Repository follows `ai_model/infrastructure/repositories/` pattern (see `rag_document_repository.py`)
- Domain model in `ai_model/domain/` follows existing patterns
- Uses `structlog` for logging (consistent with rest of service)
- Uses Pydantic V2 syntax (`model_dump()`, not `dict()`)

### References

- [Source: `services/ai-model/src/ai_model/services/vectorization_pipeline.py:88-94`] - In-memory limitation documentation
- [Source: `_bmad-output/sprint-artifacts/0-75-13c-rag-vectorization-grpc-wiring.md`] - Code review that flagged this issue
- [Source: `_bmad-output/epics/epic-0-75-ai-model.md`] - Story 0.75.13d definition
- [Source: `_bmad-output/project-context.md`] - Repository patterns and MongoDB conventions

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
