# Story 0.6.9: Source Config Cache with MongoDB Change Streams

**Status:** To Do
**GitHub Issue:** TBD
**Epic:** [Epic 0.6: Infrastructure Hardening](../epics/epic-0-6-infrastructure-hardening.md)
**ADR:** [ADR-007: Source Config Cache with Change Streams](../architecture/adr/ADR-007-source-config-cache-change-streams.md)
**Story Points:** 5
**Wave:** 3 (Domain Logic)
**Prerequisites:**
- Wave 2 complete (DLQ for handling errors)
- MongoDB replica set (required for Change Streams)

---

## CRITICAL REQUIREMENTS FOR DEV AGENT

> **READ THIS FIRST - MongoDB Change Streams require replica set!**

### 1. MongoDB Replica Set Required

Change Streams only work with MongoDB replica set, not standalone:

```yaml
# docker-compose.yaml - MUST have replica set
mongodb:
  image: mongo:7
  command: ["--replSet", "rs0"]
```

### 2. Observability is Key

This story adds 5 OpenTelemetry metrics. All must be instrumented and tested.

### 3. Definition of Done Checklist

- [ ] **Startup warming works** - Cache populated before accepting requests
- [ ] **Change Stream invalidates** - Insert/update/delete trigger invalidation
- [ ] **Metrics instrumented** - All 5 metrics emitting data
- [ ] **Resume token handled** - Reconnection doesn't miss changes
- [ ] **Unit tests pass** - All cache behavior tested
- [ ] **E2E tests pass** - No silent event drops
- [ ] **Lint passes**

---

## Story

As a **platform engineer**,
I want source config cache to use MongoDB Change Streams for real-time invalidation,
So that new configs are immediately available without 5-minute stale windows.

## Acceptance Criteria

1. **AC1: Startup Warming** - Given the service is starting up, When the service reaches ready state, Then the source config cache is warmed with all configs from MongoDB And metric `source_config_cache_size` shows the count

2. **AC2: Change Stream Invalidation** - Given the cache is warm, When an operator creates/updates/deletes a source config, Then MongoDB Change Stream fires within milliseconds And the cache is invalidated immediately And metric `source_config_cache_invalidations_total` is incremented

3. **AC3: Cache Hit/Miss Tracking** - Given a blob event arrives, When the source config is looked up, Then cache hits and misses are tracked via metrics And the correct config is returned

4. **AC4: Resilient Reconnection** - Given the Change Stream connection is lost, When the watcher reconnects, Then it resumes from the last resume token And no invalidations are missed

## Tasks / Subtasks

- [ ] **Task 1: Add OpenTelemetry Metrics** (AC: 1, 2, 3)
  - [ ] Create metrics in `SourceConfigService`:
    - `source_config_cache_hits_total` (Counter)
    - `source_config_cache_misses_total` (Counter)
    - `source_config_cache_invalidations_total` (Counter)
    - `source_config_cache_age_seconds` (Gauge)
    - `source_config_cache_size` (Gauge)

- [ ] **Task 2: Implement Startup Cache Warming** (AC: 1)
  - [ ] Create `async def warm_cache()` method
  - [ ] Load all configs from MongoDB on startup
  - [ ] Set `source_config_cache_size` metric
  - [ ] Integrate with FastAPI lifespan

- [ ] **Task 3: Implement Change Stream Watcher** (AC: 2, 4)
  - [ ] Create `async def _watch_changes()` method
  - [ ] Watch for insert, update, replace, delete operations
  - [ ] Invalidate cache on change
  - [ ] Store and use resume token for reconnection
  - [ ] Increment `source_config_cache_invalidations_total`

- [ ] **Task 4: Implement Cache Hit/Miss Tracking** (AC: 3)
  - [ ] Update `get_config_by_source_id()` to track hits/misses
  - [ ] Update `get_all_configs()` to track hits/misses
  - [ ] Increment appropriate counters

- [ ] **Task 5: Add Health Endpoint** (AC: All)
  - [ ] Create `GET /health/cache` endpoint
  - [ ] Return cache size, age, and change stream status

- [ ] **Task 6: Create Unit Tests** (AC: All)
  - [ ] Test startup warming
  - [ ] Test change stream invalidation for each operation type
  - [ ] Test cache hit/miss tracking
  - [ ] Test resume token handling

- [ ] **Task 7: Update E2E Tests** (AC: All)
  - [ ] Verify no silent event drops due to stale cache
  - [ ] Add cache health check to infrastructure tests

## Git Workflow (MANDATORY)

**Branch name:** `story/0-6-9-source-config-cache-change-streams`

---

## Unit Tests Required

```python
# tests/unit/collection_model/services/test_source_config_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from collection_model.services.source_config_service import SourceConfigService


class TestCacheWarming:
    """Tests for startup cache warming."""

    @pytest.mark.asyncio
    async def test_cache_warmed_on_startup(self, mock_mongodb_client):
        """Cache is populated with all configs on startup."""
        # Arrange
        mock_collection = AsyncMock()
        mock_collection.find.return_value.to_list.return_value = [
            {"source_id": "qc-analyzer", "enabled": True},
            {"source_id": "weather-api", "enabled": True},
        ]

        service = SourceConfigService(mock_collection)

        # Act
        await service.warm_cache()

        # Assert
        assert len(service._cache) == 2
        mock_collection.find.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_size_metric_set_on_warm(self, mock_mongodb_client):
        """Cache size metric is set after warming."""
        with patch("collection_model.services.source_config_service.cache_size_gauge") as mock_gauge:
            service = SourceConfigService(mock_collection)
            await service.warm_cache()

            mock_gauge.set.assert_called_with(2)


class TestChangeStreamInvalidation:
    """Tests for change stream cache invalidation."""

    @pytest.mark.asyncio
    async def test_change_stream_invalidates_on_insert(self):
        """Cache is invalidated when a config is inserted."""
        service = SourceConfigService(mock_collection)
        service._cache = [{"source_id": "existing"}]

        # Simulate change stream event
        change_event = {
            "operationType": "insert",
            "fullDocument": {"source_id": "new-config"},
        }

        service._invalidate_cache(reason="change_stream:insert")

        assert service._cache is None  # Cache invalidated

    @pytest.mark.asyncio
    async def test_change_stream_invalidates_on_update(self):
        """Cache is invalidated when a config is updated."""
        # Similar test for update

    @pytest.mark.asyncio
    async def test_change_stream_invalidates_on_delete(self):
        """Cache is invalidated when a config is deleted."""
        # Similar test for delete

    @pytest.mark.asyncio
    async def test_invalidation_metric_incremented(self):
        """Invalidation metric is incremented on cache clear."""
        with patch("collection_model.services.source_config_service.invalidation_counter") as mock_counter:
            service = SourceConfigService(mock_collection)
            service._invalidate_cache(reason="change_stream:insert")

            mock_counter.add.assert_called_once_with(1, {"reason": "change_stream:insert"})


class TestCacheHitMiss:
    """Tests for cache hit/miss tracking."""

    @pytest.mark.asyncio
    async def test_cache_hit_increments_metric(self):
        """Cache hit increments hit counter."""
        service = SourceConfigService(mock_collection)
        service._cache = [{"source_id": "qc-analyzer", "enabled": True}]

        with patch("collection_model.services.source_config_service.cache_hit_counter") as mock_counter:
            result = await service.get_config_by_source_id("qc-analyzer")

            mock_counter.add.assert_called_once_with(1)
            assert result["source_id"] == "qc-analyzer"

    @pytest.mark.asyncio
    async def test_cache_miss_loads_from_db(self):
        """Cache miss loads from database and increments miss counter."""
        service = SourceConfigService(mock_collection)
        service._cache = None  # Cache empty

        with patch("collection_model.services.source_config_service.cache_miss_counter") as mock_counter:
            result = await service.get_config_by_source_id("qc-analyzer")

            mock_counter.add.assert_called_once_with(1)
```

---

## Implementation Reference

### SourceConfigService with Change Streams

```python
# services/collection-model/src/collection_model/services/source_config_service.py
from opentelemetry import metrics
from datetime import datetime, UTC
import asyncio
import structlog

logger = structlog.get_logger("collection_model.services.source_config")
meter = metrics.get_meter("collection-model")

# Metrics
cache_hit_counter = meter.create_counter("source_config_cache_hits_total")
cache_miss_counter = meter.create_counter("source_config_cache_misses_total")
invalidation_counter = meter.create_counter("source_config_cache_invalidations_total")
cache_age_gauge = meter.create_gauge("source_config_cache_age_seconds")
cache_size_gauge = meter.create_gauge("source_config_cache_size")


class SourceConfigService:
    def __init__(self, collection):
        self._collection = collection
        self._cache: list[dict] | None = None
        self._cache_loaded_at: datetime | None = None
        self._change_stream_task: asyncio.Task | None = None
        self._resume_token: dict | None = None

    async def warm_cache(self) -> None:
        """Warm cache on service startup."""
        logger.info("Warming source config cache...")
        configs = await self._collection.find({}).to_list(length=None)
        self._cache = configs
        self._cache_loaded_at = datetime.now(UTC)
        cache_size_gauge.set(len(configs))
        logger.info("Cache warmed", config_count=len(configs))

    async def start_change_stream(self) -> None:
        """Start watching for collection changes."""
        self._change_stream_task = asyncio.create_task(self._watch_changes())
        logger.info("Change stream watcher started")

    async def stop_change_stream(self) -> None:
        """Stop the change stream watcher."""
        if self._change_stream_task:
            self._change_stream_task.cancel()
            try:
                await self._change_stream_task
            except asyncio.CancelledError:
                pass
        logger.info("Change stream watcher stopped")

    async def _watch_changes(self) -> None:
        """Watch MongoDB collection for changes."""
        pipeline = [
            {"$match": {"operationType": {"$in": ["insert", "update", "replace", "delete"]}}}
        ]

        while True:
            try:
                async with self._collection.watch(
                    pipeline,
                    full_document="updateLookup",
                    resume_after=self._resume_token,
                ) as stream:
                    async for change in stream:
                        self._resume_token = change["_id"]
                        operation = change["operationType"]
                        self._invalidate_cache(reason=f"change_stream:{operation}")
                        logger.info("Cache invalidated by change stream", operation=operation)

            except Exception as e:
                logger.warning("Change stream disconnected, reconnecting...", error=str(e))
                await asyncio.sleep(1)  # Brief pause before reconnect

    def _invalidate_cache(self, reason: str) -> None:
        """Invalidate the cache."""
        self._cache = None
        self._cache_loaded_at = None
        invalidation_counter.add(1, {"reason": reason})

    async def get_config_by_source_id(self, source_id: str) -> dict | None:
        """Get a source config by ID, using cache if available."""
        if self._cache is not None:
            cache_hit_counter.add(1)
            for config in self._cache:
                if config.get("source_id") == source_id:
                    return config
            return None
        else:
            cache_miss_counter.add(1)
            # Reload cache
            await self.warm_cache()
            return await self.get_config_by_source_id(source_id)

    def get_cache_age(self) -> float:
        """Get cache age in seconds."""
        if self._cache_loaded_at is None:
            return -1
        return (datetime.now(UTC) - self._cache_loaded_at).total_seconds()
```

### FastAPI Lifespan Integration

```python
# services/collection-model/src/collection_model/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Warm cache before accepting requests
    await app.state.source_config_service.warm_cache()
    await app.state.source_config_service.start_change_stream()

    yield

    # Shutdown: Stop change stream
    await app.state.source_config_service.stop_change_stream()

app = FastAPI(lifespan=lifespan)
```

### Health Endpoint

```python
@app.get("/health/cache")
async def cache_health():
    service = app.state.source_config_service
    return {
        "cache_size": len(service._cache) if service._cache else 0,
        "cache_age_seconds": service.get_cache_age(),
        "change_stream_active": (
            service._change_stream_task is not None
            and not service._change_stream_task.done()
        ),
    }
```

---

## E2E Test Impact

### Verification Steps

After implementation, verify:

1. **No stale cache drops events:**
   - Create new source config
   - Immediately send blob event for that source
   - Event should be processed (not dropped)

2. **Metrics are emitted:**
   - Check `/metrics` endpoint for cache metrics
   - Verify hit/miss/invalidation counters

3. **Health endpoint works:**
   - Check `/health/cache` returns valid data

---

## MongoDB Requirements

**Change Streams require:**
- MongoDB replica set (not standalone)
- `readConcern: majority` (default in Atlas)
- Appropriate permissions for `watch()`

**Docker Compose update:**
```yaml
mongodb:
  image: mongo:7
  command: ["--replSet", "rs0"]
  # Init script to initialize replica set
```

---

## Local Test Run Evidence (MANDATORY)

**1. Unit Tests:**
```bash
pytest tests/unit/collection_model/services/test_source_config_service.py -v
```
**Output:** (paste here)

**2. E2E Tests:**
```bash
pytest tests/e2e/scenarios/ -v
```
**Output:** (paste here - no regressions)

**3. Cache Health Check:**
```bash
curl http://localhost:8002/health/cache
```
**Output:** (paste here)

**4. Lint Check:** [ ] Passed

---

## References

- [ADR-007: Source Config Cache](../architecture/adr/ADR-007-source-config-cache-change-streams.md)
- [MongoDB Change Streams](https://www.mongodb.com/docs/manual/changeStreams/)
- [Motor Async Change Streams](https://motor.readthedocs.io/en/stable/api-asyncio/)
