# ADR-007: Source Config Cache with MongoDB Change Streams

**Status:** Accepted
**Date:** 2025-12-31
**Deciders:** Winston (Architect), Murat (TEA), Amelia (Dev), Jeanlouistournay
**Related Stories:** Epic 0-4 (Grading Validation)

## Context

During E2E testing of Epic 0-4, we experienced multiple cache-related issues:

1. **Empty cache on startup** - Service starts with no cached data
2. **5-minute stale data** - New configs not visible until TTL expires
3. **Silent event loss** - Events dropped when config not in cache
4. **No invalidation on config changes** - Cache doesn't refresh when configs are updated
5. **Cache-MCP inconsistency** - Collection Model caches, MCP queries fresh

**Current implementation:**
```python
# Basic TTL cache - NOT production-ready
CACHE_TTL_MINUTES = 5
self._cache: list[SourceConfig] | None = None  # Empty on startup!
```

**Failure scenario:**
```
T=0:00  Operator creates new source config
T=0:30  Blob event arrives
T=0:30  Cache has OLD list (expires at T=5:00)
T=0:30  Event silently dropped!
```

## Decision

**Implement production-ready cache using MongoDB Change Streams for automatic invalidation, with startup warming and observability metrics.**

## Alternatives Considered

| Option | Description | Verdict |
|--------|-------------|---------|
| Short TTL | Reduce TTL to 30 seconds | Rejected: High DB load |
| Event-based invalidation | Publish event on config change | Rejected: Complex |
| **Change Streams** | MongoDB watches collection changes | **Selected** |
| Distributed cache (Redis) | External cache | Rejected: Over-engineered |

## Implementation

### 1. MongoDB Change Stream Watcher

```python
class SourceConfigService:
    async def _watch_changes(self) -> None:
        """Watch MongoDB collection for changes and invalidate cache."""
        collection = self._db["source_configs"]
        async with collection.watch(
            pipeline=[
                {"$match": {"operationType": {"$in": ["insert", "update", "replace", "delete"]}}}
            ],
            full_document="updateLookup"
        ) as stream:
            async for change in stream:
                operation = change["operationType"]
                self._invalidate_cache(reason=f"change_stream:{operation}")
```

### 2. Startup Cache Warming

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm cache on startup (before accepting requests)
    logger.info("Warming source config cache...")
    configs = await app.state.source_config_service.get_all_configs()
    logger.info("Cache warmed", config_count=len(configs))

    # Start change stream watcher
    await app.state.source_config_service.start_change_stream()

    yield

    # Cleanup
    await app.state.source_config_service.stop_change_stream()
```

### 3. OpenTelemetry Metrics

| Metric | Type | Purpose |
|--------|------|---------|
| `source_config_cache_hits_total` | Counter | Track cache efficiency |
| `source_config_cache_misses_total` | Counter | Alert on high miss rate |
| `source_config_cache_invalidations_total` | Counter | Monitor change frequency |
| `source_config_cache_age_seconds` | Gauge | Detect stale cache |
| `source_config_cache_size` | Gauge | Verify configs loaded |

### 4. Health Endpoint for Cache Status

```python
@app.get("/health/cache")
async def cache_health():
    return {
        "cache_size": len(service._cache) if service._cache else 0,
        "cache_age_seconds": service.get_cache_age(),
        "change_stream_active": not service._change_stream_task.done(),
    }
```

## Consequences

### Positive

- **Real-time invalidation** - Cache refreshed within milliseconds of config change
- **Warm startup** - No cold cache on service start
- **Observable** - Metrics for alerting and debugging
- **No silent drops** - Events can't be lost to stale cache

### Negative

- **MongoDB replica set required** - Change streams need replica set
- **Additional complexity** - Background task management

## Cache Behavior Summary

| Event | Behavior |
|-------|----------|
| Service starts | Cache warmed immediately before accepting requests |
| Config inserted | Change stream fires → cache invalidated → next request loads fresh |
| Config updated | Change stream fires → cache invalidated → next request loads fresh |
| Config deleted | Change stream fires → cache invalidated → next request loads fresh |
| TTL expires (fallback) | Next request reloads from database |

## MongoDB Requirements

**Change Streams require:**
- MongoDB replica set (not standalone)
- `readConcern: majority` (default in Atlas/CosmosDB)
- Appropriate permissions for `watch()`

**For local development:**
```yaml
# docker-compose.yaml
mongodb:
  image: mongo:7
  command: ["--replSet", "rs0"]
```

## Revisit Triggers

Re-evaluate this decision if:

1. **Change stream overhead too high** - May need dedicated watcher service
2. **Multi-region deployment** - May need distributed cache
3. **Very frequent changes** - May need debouncing

## References

- [MongoDB Change Streams](https://www.mongodb.com/docs/manual/changeStreams/)
- [Motor Async Change Streams](https://motor.readthedocs.io/en/stable/api-asyncio/)
- Epic 0-4: Grading Validation
- Related: ADR-004 (Type Safety), ADR-005 (gRPC Retry), ADR-006 (Event Delivery)
