# Story 0.75.4: Source Cache for Agent Types and Prompt Config

**Status:** review
**GitHub Issue:** #95

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer**,
I want in-memory caching with MongoDB change streams for agent and prompt configs,
So that configuration lookups are fast without stale data.

## Acceptance Criteria

1. **AC1: Shared Base Class** - `MongoChangeStreamCache` abstract base class created in `libs/fp-common/fp_common/cache/mongo_change_stream_cache.py` per ADR-013
2. **AC2: Generic Type Support** - Base class is generic (`Generic[T]`) supporting any Pydantic model type
3. **AC3: Abstract Methods** - Three abstract methods: `_get_cache_key()`, `_parse_document()`, `_get_filter()`
4. **AC4: Change Stream Watcher** - Background task watching for insert/update/replace/delete operations with auto-reconnect
5. **AC5: Resume Token Persistence** - Change stream uses resume token for resilient reconnection
6. **AC6: Cache Warming** - `get_all()` method loads all items on first call, subsequent calls return cached data
7. **AC7: TTL Fallback** - 5-minute TTL as safety net if change stream disconnects
8. **AC8: OpenTelemetry Metrics** - Metrics for hits, misses, invalidations, age, and size per cache instance
9. **AC9: Health Status** - `get_health_status()` returns cache size, age, change stream status, and validity
10. **AC10: Collection Model Refactor** - `SourceConfigService` refactored to extend `MongoChangeStreamCache[SourceConfig]`
11. **AC11: Agent Config Cache** - `AgentConfigCache` class extending base class for `agent_configs` collection
12. **AC12: Prompt Cache** - `PromptCache` class extending base class for `prompts` collection
13. **AC13: AI Model Lifespan** - AI Model `main.py` lifespan hook warms both caches and starts change streams
14. **AC14: AI Model Health Endpoint** - `/health/cache` endpoint returns status of both AI Model caches
15. **AC15: fp-common Exports** - `MongoChangeStreamCache` exported from `fp_common.cache`
16. **AC16: Unit Tests** - Unit tests for base class, refactored SourceConfigService, and AI Model caches (minimum 40 tests)
17. **AC17: E2E Tests Pass** - All existing E2E tests pass (no regressions)
18. **AC18: CI Passes** - All lint checks and unit tests pass in CI

## Tasks / Subtasks

- [ ] **Task 1: Create Cache Directory in fp-common** (AC: #1, #15)
  - [ ] Create `libs/fp-common/fp_common/cache/__init__.py`
  - [ ] Create `libs/fp-common/fp_common/cache/mongo_change_stream_cache.py`
  - [ ] Export `MongoChangeStreamCache` from `fp_common.cache`
  - [ ] Update `libs/fp-common/fp_common/__init__.py` to export cache module

- [ ] **Task 2: Implement MongoChangeStreamCache Base Class** (AC: #1, #2, #3, #4, #5, #6, #7, #8, #9)
  - [ ] Define `MongoChangeStreamCache(ABC, Generic[T])` class
  - [ ] Implement `__init__(db, collection_name, cache_name)` constructor
  - [ ] Define abstract method `_get_cache_key(item: T) -> str`
  - [ ] Define abstract method `_parse_document(doc: dict) -> T`
  - [ ] Define abstract method `_get_filter() -> dict`
  - [ ] Implement `start_change_stream()` to spawn background watcher task
  - [ ] Implement `stop_change_stream()` to cancel background task
  - [ ] Implement `_watch_changes()` with resume token and auto-reconnect
  - [ ] Implement `_invalidate_cache(reason: str, item_id: str)` with metrics
  - [ ] Implement `_is_cache_valid()` checking TTL expiry
  - [ ] Implement `get_cache_age() -> float` returning seconds
  - [ ] Implement `get_all() -> dict[str, T]` with cache hit/miss tracking
  - [ ] Implement `get(key: str) -> T | None` using `get_all()`
  - [ ] Implement `get_health_status() -> dict` for health endpoint
  - [ ] Create OpenTelemetry metrics: hits, misses, invalidations, age, size

- [ ] **Task 3: Refactor Collection Model SourceConfigService** (AC: #10)
  - [ ] Modify `services/collection-model/src/collection_model/services/source_config_service.py`
  - [ ] Change class signature to `SourceConfigService(MongoChangeStreamCache[SourceConfig])`
  - [ ] Remove duplicate cache logic (now in base class)
  - [ ] Keep domain-specific methods: `get_config()`, `get_config_by_container()`, `extract_path_metadata()`
  - [ ] Override `_get_cache_key()` to return `config.source_id`
  - [ ] Override `_parse_document()` to return `SourceConfig.model_validate(doc)`
  - [ ] Override `_get_filter()` to return `{"enabled": True}`
  - [ ] Verify all existing SourceConfigService tests still pass

- [ ] **Task 4: Implement AgentConfigCache** (AC: #11)
  - [ ] Create `services/ai-model/src/ai_model/services/agent_config_cache.py`
  - [ ] Extend `MongoChangeStreamCache[AgentConfig]`
  - [ ] Override `_get_cache_key()` to return `config.agent_id`
  - [ ] Override `_parse_document()` using TypeAdapter for discriminated union
  - [ ] Override `_get_filter()` to return `{"status": "active"}`
  - [ ] Add domain method `get_config(agent_id: str) -> AgentConfig | None`
  - [ ] Add domain method `get_configs_by_type(agent_type: AgentType) -> list[AgentConfig]`

- [ ] **Task 5: Implement PromptCache** (AC: #12)
  - [ ] Create `services/ai-model/src/ai_model/services/prompt_cache.py`
  - [ ] Extend `MongoChangeStreamCache[Prompt]`
  - [ ] Override `_get_cache_key()` to return `prompt.agent_id`
  - [ ] Override `_parse_document()` to return `Prompt.model_validate(doc)`
  - [ ] Override `_get_filter()` to return `{"status": "active"}`
  - [ ] Add domain method `get_prompt(agent_id: str) -> Prompt | None`
  - [ ] Add domain method `get_prompt_for_ab_test(agent_id, use_staged: bool) -> Prompt | None`

- [ ] **Task 6: AI Model Lifespan Integration** (AC: #13)
  - [ ] Modify `services/ai-model/src/ai_model/main.py`
  - [ ] Import AgentConfigCache and PromptCache
  - [ ] In lifespan startup: instantiate both caches
  - [ ] In lifespan startup: call `get_all()` to warm each cache
  - [ ] In lifespan startup: call `start_change_stream()` for each cache
  - [ ] Store caches in `app.state` for dependency injection
  - [ ] In lifespan shutdown: call `stop_change_stream()` for each cache
  - [ ] Log cache warming stats and change stream status

- [ ] **Task 7: AI Model Health Endpoint** (AC: #14)
  - [ ] Create or update `services/ai-model/src/ai_model/api/health.py`
  - [ ] Add `/health/cache` endpoint
  - [ ] Return `{"agent_config": {...}, "prompt": {...}}` from both caches' `get_health_status()`
  - [ ] Register health router in main app

- [ ] **Task 8: Export Updates** (AC: #15)
  - [ ] Update `services/ai-model/src/ai_model/services/__init__.py` to export caches
  - [ ] Verify imports work correctly across modules

- [ ] **Task 9: Unit Tests - Base Class** (AC: #16)
  - [ ] Create `tests/unit/fp_common/test_mongo_change_stream_cache.py`
  - [ ] Test `_is_cache_valid()` returns False when cache is None
  - [ ] Test `_is_cache_valid()` returns False when cache expired
  - [ ] Test `_is_cache_valid()` returns True when cache valid
  - [ ] Test `get_all()` loads from DB on first call (cache miss)
  - [ ] Test `get_all()` returns cached data on second call (cache hit)
  - [ ] Test `get()` returns specific item by key
  - [ ] Test `get()` returns None for missing key
  - [ ] Test `_invalidate_cache()` clears cache and records metric
  - [ ] Test `get_cache_age()` returns 0 when cache is None
  - [ ] Test `get_cache_age()` returns positive value when cache exists
  - [ ] Test `get_health_status()` returns correct structure
  - [ ] Test `start_change_stream()` spawns background task
  - [ ] Test `stop_change_stream()` cancels background task

- [ ] **Task 10: Unit Tests - SourceConfigService Refactor** (AC: #16)
  - [ ] Update `tests/unit/collection/test_source_config_service.py`
  - [ ] Verify all existing tests pass with refactored implementation
  - [ ] Add test that `_get_cache_key()` returns `source_id`
  - [ ] Add test that `_get_filter()` returns `{"enabled": True}`

- [ ] **Task 11: Unit Tests - AI Model Caches** (AC: #16)
  - [ ] Create `tests/unit/ai_model/test_agent_config_cache.py`
  - [ ] Test AgentConfigCache inherits from MongoChangeStreamCache
  - [ ] Test `_get_cache_key()` returns `agent_id`
  - [ ] Test `_parse_document()` handles discriminated union correctly
  - [ ] Test `get_config()` returns correct config
  - [ ] Test `get_configs_by_type()` filters by agent type
  - [ ] Create `tests/unit/ai_model/test_prompt_cache.py`
  - [ ] Test PromptCache inherits from MongoChangeStreamCache
  - [ ] Test `_get_cache_key()` returns `agent_id`
  - [ ] Test `get_prompt()` returns correct prompt
  - [ ] Test `get_prompt_for_ab_test()` with use_staged=False
  - [ ] Test `get_prompt_for_ab_test()` with use_staged=True

- [ ] **Task 12: E2E Verification** (AC: #17)
  - [ ] Run full E2E test suite with `--build` flag
  - [ ] Verify no regressions from SourceConfigService refactor
  - [ ] Capture test output in story file

- [ ] **Task 13: CI Verification** (AC: #18)
  - [ ] Run `ruff check .` - lint passes
  - [ ] Run `ruff format --check .` - format passes
  - [ ] Push and verify CI passes
  - [ ] Trigger E2E CI workflow and verify passes

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.75.4: Source Cache for Agent Types and Prompt Config"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-75-4-source-cache-agent-types-prompt-config
  ```

**Branch name:** `feature/0-75-4-source-cache-agent-types-prompt-config`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/...`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.75.4: Source Cache for Agent Types and Prompt Config" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/...`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
# Base class tests
PYTHONPATH="${PYTHONPATH}:.:libs/fp-common:libs/fp-proto/src" pytest tests/unit/fp_common/test_mongo_change_stream_cache.py -v

# Collection Model refactor tests
PYTHONPATH="${PYTHONPATH}:.:services/collection-model/src:libs/fp-common:libs/fp-proto/src" pytest tests/unit/collection/test_source_config_service.py -v

# AI Model cache tests
PYTHONPATH="${PYTHONPATH}:.:services/ai-model/src:libs/fp-common:libs/fp-proto/src" pytest tests/unit/ai_model/test_agent_config_cache.py tests/unit/ai_model/test_prompt_cache.py -v
```
**Output:**
```
52 passed in 1.64s
- tests/unit/fp_common/test_mongo_change_stream_cache.py: 17 passed
- tests/unit/ai_model/test_agent_config_cache.py: 17 passed
- tests/unit/ai_model/test_prompt_cache.py: 18 passed
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
============================= 102 passed, 1 skipped in 34.72s ==============================
All E2E scenarios passed successfully.
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
git push origin story/0-75-4-source-cache-agent-types-prompt-config

# Wait ~30s, then check CI status
gh run list --branch story/0-75-4-source-cache-agent-types-prompt-config --limit 3
```
**Quality CI Run ID:** 20697917790
**Quality CI Status:** [x] Passed / [ ] Failed
**E2E CI Run ID:** 20697953951
**E2E CI Status:** [x] Passed / [ ] Failed
**Verification Date:** 2026-01-04

---

## Dev Notes

### Architecture Reference

**Primary Source:** ADR-013 (AI Model Configuration Cache with MongoDB Change Streams)
- Location: `_bmad-output/architecture/adr/ADR-013-ai-model-configuration-cache.md`

**Pattern Source:** Collection Model SourceConfigService
- Location: `services/collection-model/src/collection_model/services/source_config_service.py`
- Pattern: Story 0.6.9 implementation (ADR-007)

### Key Decision: DRY Cache Pattern via Shared Base Class

> **Decision:** Extract the MongoDB Change Stream cache pattern from Collection Model into `fp-common` as a reusable abstract base class. All caches (SourceConfig, AgentConfig, Prompt) inherit from this base. See ADR-013.

This enables:
- Single implementation of change stream logic
- Consistent metrics across all caches
- Easy addition of new caches in future
- Testable base class

### MongoChangeStreamCache Base Class API (per ADR-013)

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class MongoChangeStreamCache(ABC, Generic[T]):
    """Base class for MongoDB-backed caches with Change Stream invalidation.

    Features:
    - Startup cache warming
    - Change Stream auto-invalidation with resume token
    - TTL fallback (5 min safety net)
    - OpenTelemetry metrics
    - Health status reporting
    """

    CACHE_TTL_MINUTES: int = 5

    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str, cache_name: str):
        ...

    @abstractmethod
    def _get_cache_key(self, item: T) -> str:
        """Extract cache key from item. Override in subclass."""
        ...

    @abstractmethod
    def _parse_document(self, doc: dict) -> T:
        """Parse MongoDB document to Pydantic model. Override in subclass."""
        ...

    @abstractmethod
    def _get_filter(self) -> dict:
        """Get MongoDB filter for loading cache. Override in subclass."""
        ...

    async def start_change_stream(self) -> None: ...
    async def stop_change_stream(self) -> None: ...
    async def get_all(self) -> dict[str, T]: ...
    async def get(self, key: str) -> T | None: ...
    def get_health_status(self) -> dict: ...
```

### Concrete Implementations

| Cache Class | Collection | Cache Key | Filter | Model Type |
|-------------|------------|-----------|--------|------------|
| `SourceConfigService` | `source_configs` | `source_id` | `{"enabled": True}` | `SourceConfig` |
| `AgentConfigCache` | `agent_configs` | `agent_id` | `{"status": "active"}` | `AgentConfig` (discriminated union) |
| `PromptCache` | `prompts` | `agent_id` | `{"status": "active"}` | `Prompt` |

### OpenTelemetry Metrics (per cache instance)

| Metric | Type | Labels |
|--------|------|--------|
| `{cache_name}_cache_hits_total` | Counter | - |
| `{cache_name}_cache_misses_total` | Counter | - |
| `{cache_name}_cache_invalidations_total` | Counter | reason, item_id |
| `{cache_name}_cache_age_seconds` | Gauge | - |
| `{cache_name}_cache_size` | Gauge | - |

### SourceConfigService Refactor Strategy

The existing `SourceConfigService` has ~385 lines. After refactor:

**Moved to Base Class (~200 lines):**
- Change stream management (start/stop/watch)
- Cache invalidation logic
- Cache hit/miss tracking
- TTL expiry checking
- OpenTelemetry metrics setup
- Health status

**Kept in SourceConfigService (~100 lines):**
- `_get_cache_key()` → returns `config.source_id`
- `_parse_document()` → returns `SourceConfig.model_validate(doc)`
- `_get_filter()` → returns `{"enabled": True}`
- `get_config(source_id)` → domain method
- `get_config_by_container(container)` → domain method
- `extract_path_metadata(blob_path, config)` → static utility

### AgentConfigCache: Discriminated Union Handling

The `AgentConfig` is a discriminated union of 5 types. Use `TypeAdapter` for deserialization:

```python
from pydantic import TypeAdapter
from ai_model.domain.agent_config import AgentConfig

agent_config_adapter = TypeAdapter(AgentConfig)

def _parse_document(self, doc: dict) -> AgentConfig:
    doc.pop("_id", None)  # Remove MongoDB _id
    return agent_config_adapter.validate_python(doc)
```

### Previous Story (0.75.3) Learnings

1. **TypeAdapter for discriminated unions** - Correct pattern for `AgentConfig`
2. **Delete+insert for update()** - Works with mock infrastructure
3. **60 unit tests** - Exceeded minimum of 30, good coverage
4. **All E2E tests pass** - 102 passed, 1 skipped, no regressions
5. **CI verification** - Both quality and E2E CI runs passed

### Recent Git Commits

```
2b970a2 Story 0.75.3: Pydantic Model for Agent Configuration + Mongo Repository (#94)
463488e docs(story): Mark Story 0.75.2 as done
6da2c90 Story 0.75.2: Pydantic Model for Prompt + Mongo Repository (#92)
```

**Patterns from recent stories:**
- File naming: `services/ai-model/src/ai_model/services/agent_config_cache.py`
- Test naming: `tests/unit/ai_model/test_agent_config_cache.py`
- Export pattern: Update `__init__.py` files
- Commit format: Include issue reference

### File Structure After Story

```
libs/fp-common/fp_common/
├── cache/
│   ├── __init__.py                    # NEW: Export MongoChangeStreamCache
│   └── mongo_change_stream_cache.py   # NEW: Base class (ADR-013)
├── __init__.py                        # MODIFIED: Add cache exports

services/collection-model/src/collection_model/services/
└── source_config_service.py           # MODIFIED: Extend base class

services/ai-model/src/ai_model/
├── main.py                            # MODIFIED: Add lifespan hooks
├── api/
│   └── health.py                      # NEW: Cache health endpoint
└── services/
    ├── __init__.py                    # MODIFIED: Export caches
    ├── agent_config_cache.py          # NEW: AgentConfigCache
    └── prompt_cache.py                # NEW: PromptCache

tests/unit/
├── fp_common/
│   └── test_mongo_change_stream_cache.py  # NEW: Base class tests
├── collection/
│   └── test_source_config_service.py      # MODIFIED: Add refactor tests
└── ai_model/
    ├── test_agent_config_cache.py         # NEW: AgentConfigCache tests
    └── test_prompt_cache.py               # NEW: PromptCache tests
```

### Testing Strategy

**Unit Tests Required (minimum 40 tests):**

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_mongo_change_stream_cache.py` | 15+ | Base class: caching, invalidation, health, change stream |
| `test_source_config_service.py` | 5+ (additional) | Refactored implementation, abstract method overrides |
| `test_agent_config_cache.py` | 10+ | Discriminated union handling, domain methods |
| `test_prompt_cache.py` | 10+ | Prompt lookups, A/B test support |

**E2E Verification:**
- All existing E2E tests must pass
- SourceConfigService refactor should be transparent to E2E tests
- No new E2E tests needed (AI Model caches tested in Story 0.75.18)

### What This Story Does NOT Include

| Not in Scope | Implemented In |
|--------------|----------------|
| Agent workflow execution | Stories 0.75.17+ |
| LLM gateway integration | Story 0.75.5 |
| CLI tooling | Stories 0.75.6, 0.75.7 |
| E2E tests for AI Model | Story 0.75.18 |

### Anti-Patterns to AVOID

| Anti-Pattern | Correct Approach |
|--------------|------------------|
| Duplicate cache logic | Use shared base class |
| Synchronous I/O | ALL database/change stream calls must be async |
| Missing metrics | Every cache uses OpenTelemetry counters/gauges |
| Hardcoded collection names | Pass as constructor parameter |
| No resume token | Store and use resume token for reconnection |
| Override parent `__init__` incorrectly | Call `super().__init__()` |

### References

- [Source: `_bmad-output/architecture/adr/ADR-013-ai-model-configuration-cache.md`] - Full ADR with implementation details
- [Source: `_bmad-output/architecture/adr/ADR-007-source-config-cache-change-streams.md`] - Original pattern source
- [Source: `services/collection-model/src/collection_model/services/source_config_service.py`] - Existing implementation to refactor
- [Source: `_bmad-output/project-context.md`] - Critical rules
- [Source: `_bmad-output/epics/epic-0-75-ai-model.md`] - Story requirements

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Quality CI Run: https://github.com/jltournay/farmer-power-platform/actions/runs/20697917790
- E2E CI Run: https://github.com/jltournay/farmer-power-platform/actions/runs/20697953951

### Completion Notes List

1. Created MongoChangeStreamCache generic base class in fp-common per ADR-013
2. Refactored SourceConfigService to extend the new base class (reduced ~200 lines of duplicated code)
3. Implemented AgentConfigCache with TypeAdapter for discriminated union handling
4. Implemented PromptCache with A/B test support for staged prompts
5. Added lifespan hooks in AI Model main.py for cache warming and change stream management
6. Added /health/cache endpoint for cache status monitoring
7. Created 52 unit tests exceeding the minimum requirement of 40
8. All 102 E2E tests pass (no regressions)
9. Both Quality CI and E2E CI workflows pass

### File List

**Created:**
- `libs/fp-common/fp_common/cache/__init__.py` - Export MongoChangeStreamCache
- `libs/fp-common/fp_common/cache/mongo_change_stream_cache.py` - Base class implementation
- `services/ai-model/src/ai_model/services/agent_config_cache.py` - AgentConfigCache
- `services/ai-model/src/ai_model/services/prompt_cache.py` - PromptCache
- `services/ai-model/src/ai_model/api/health.py` - Cache health endpoint
- `tests/unit/fp_common/test_mongo_change_stream_cache.py` - 17 tests
- `tests/unit/ai_model/test_agent_config_cache.py` - 17 tests
- `tests/unit/ai_model/test_prompt_cache.py` - 18 tests

**Modified:**
- `libs/fp-common/fp_common/__init__.py` - Add cache module exports
- `services/collection-model/src/collection_model/services/source_config_service.py` - Refactored to extend MongoChangeStreamCache
- `services/ai-model/src/ai_model/main.py` - Added lifespan hooks for cache management
- `services/ai-model/src/ai_model/services/__init__.py` - Export new cache classes
- `tests/unit/collection_model/services/test_source_config_service.py` - Updated for base class changes
- `tests/unit/collection/test_source_config_service.py` - Updated for base class changes
