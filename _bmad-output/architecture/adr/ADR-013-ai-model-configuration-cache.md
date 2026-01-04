# ADR-013: AI Model Configuration Cache with MongoDB Change Streams

**Status:** Accepted
**Date:** 2026-01-04
**Deciders:** Winston (Architect), Jeanlouistournay
**Related:** ADR-007 (Source Config Cache), AI Model Architecture

## Context

The AI Model service manages two types of configuration loaded from MongoDB:

1. **Agent Configurations** - Define agent behavior (type, LLM settings, RAG config, etc.)
2. **Prompts** - System prompts, templates, few-shot examples per agent

**Current state:**

| Configuration | Cache Strategy | Problem |
|---------------|----------------|---------|
| Agent Config | No cache | Direct DB query on every agent invocation |
| Prompts | 5-min TTL only | No startup warming, stale data window |

**Issues identified:**

1. **Agent Config: No caching** - Every agent invocation queries MongoDB
2. **Agent Config: No warming** - Cold start on service restart
3. **Prompts: TTL-only** - 5-minute stale data window after config change
4. **Prompts: No warming** - First request after restart hits DB
5. **Inconsistency** - Collection Model has robust cache (ADR-007), AI Model does not

**Failure scenario (Agent Config):**
```
T=0:00  Agent invocation → DB query
T=0:01  Agent invocation → DB query
T=0:02  Agent invocation → DB query
...     (Every invocation hits MongoDB)
```

**Failure scenario (Prompts):**
```
T=0:00  Operator updates prompt in MongoDB
T=0:30  Agent invocation uses OLD cached prompt
T=5:00  Cache expires, next request gets new prompt
```

## Decision

**Implement production-ready cache for both Agent Configurations and Prompts using:**

1. **MongoDB Change Streams** for automatic invalidation
2. **Startup cache warming** before accepting requests
3. **Shared base class** (`MongoChangeStreamCache`) for DRY code
4. **OpenTelemetry metrics** for observability
5. **Health endpoints** for monitoring

This aligns with the pattern established in ADR-007 (Collection Model Source Config Cache).

## Alternatives Considered

| Option | Description | Verdict |
|--------|-------------|---------|
| Short TTL (30s) | Reduce TTL for faster updates | Rejected: High DB load |
| Event-based pub/sub | DAPR events on config change | Rejected: Extra complexity |
| **Change Streams** | MongoDB watches collection | **Selected** |
| Redis distributed cache | External cache layer | Rejected: Over-engineered |

## Implementation

### 1. Shared Base Class: MongoChangeStreamCache

```python
# libs/fp-common/fp_common/cache/mongo_change_stream_cache.py

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Generic, TypeVar
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from pydantic import BaseModel
from opentelemetry import metrics
import asyncio
import structlog

logger = structlog.get_logger()
T = TypeVar("T", bound=BaseModel)


class MongoChangeStreamCache(ABC, Generic[T]):
    """Base class for MongoDB-backed caches with Change Stream invalidation.

    Provides:
    - Startup cache warming
    - Change Stream auto-invalidation
    - TTL fallback (safety net)
    - OpenTelemetry metrics
    - Health status reporting

    Pattern aligned with ADR-007 (Source Config Cache).
    """

    CACHE_TTL_MINUTES: int = 5  # Fallback TTL

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        collection_name: str,
        cache_name: str,  # For metrics labels
    ):
        self._db = db
        self._collection_name = collection_name
        self._cache_name = cache_name

        self._cache: dict[str, T] | None = None
        self._cache_loaded_at: datetime | None = None
        self._change_stream_task: asyncio.Task | None = None

        # OpenTelemetry metrics
        meter = metrics.get_meter("ai_model")
        self._cache_hits = meter.create_counter(
            f"{cache_name}_cache_hits_total",
            description=f"{cache_name} cache hits"
        )
        self._cache_misses = meter.create_counter(
            f"{cache_name}_cache_misses_total",
            description=f"{cache_name} cache misses"
        )
        self._cache_invalidations = meter.create_counter(
            f"{cache_name}_cache_invalidations_total",
            description=f"{cache_name} cache invalidations"
        )
        self._cache_age = meter.create_gauge(
            f"{cache_name}_cache_age_seconds",
            description=f"Age of {cache_name} cache in seconds"
        )
        self._cache_size = meter.create_gauge(
            f"{cache_name}_cache_size",
            description=f"Number of items in {cache_name} cache"
        )

    @property
    def _collection(self) -> AsyncIOMotorCollection:
        """Get the MongoDB collection."""
        return self._db[self._collection_name]

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

    # ─────────────────────────────────────────────────────────────────────
    # CHANGE STREAM MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────

    async def start_change_stream(self) -> None:
        """Start watching for collection changes."""
        self._change_stream_task = asyncio.create_task(
            self._watch_changes(),
            name=f"{self._cache_name}_change_stream"
        )
        logger.info(f"{self._cache_name} change stream started")

    async def stop_change_stream(self) -> None:
        """Stop the change stream watcher."""
        if self._change_stream_task:
            self._change_stream_task.cancel()
            try:
                await self._change_stream_task
            except asyncio.CancelledError:
                pass
            logger.info(f"{self._cache_name} change stream stopped")

    async def _watch_changes(self) -> None:
        """Watch MongoDB collection for changes and invalidate cache."""
        try:
            async with self._collection.watch(
                pipeline=[
                    {"$match": {"operationType": {"$in": ["insert", "update", "replace", "delete"]}}}
                ],
                full_document="updateLookup"
            ) as stream:
                async for change in stream:
                    operation = change["operationType"]
                    doc_id = str(change.get("documentKey", {}).get("_id", "unknown"))
                    self._invalidate_cache(
                        reason=f"change_stream:{operation}",
                        item_id=doc_id
                    )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(
                f"{self._cache_name} change stream error, restarting",
                error=str(e)
            )
            await asyncio.sleep(5)
            self._change_stream_task = asyncio.create_task(
                self._watch_changes(),
                name=f"{self._cache_name}_change_stream"
            )

    # ─────────────────────────────────────────────────────────────────────
    # CACHE OPERATIONS
    # ─────────────────────────────────────────────────────────────────────

    def _invalidate_cache(self, reason: str, item_id: str = "all") -> None:
        """Invalidate the cache."""
        self._cache = None
        self._cache_loaded_at = None
        self._cache_invalidations.add(1, {"reason": reason, "item_id": item_id})
        logger.info(
            f"{self._cache_name} cache invalidated",
            reason=reason,
            item_id=item_id
        )

    def _is_cache_valid(self) -> bool:
        """Check if cache is valid (not expired)."""
        if self._cache is None or self._cache_loaded_at is None:
            return False
        age = datetime.utcnow() - self._cache_loaded_at
        return age < timedelta(minutes=self.CACHE_TTL_MINUTES)

    def get_cache_age(self) -> float:
        """Get cache age in seconds."""
        if self._cache_loaded_at is None:
            return 0.0
        return (datetime.utcnow() - self._cache_loaded_at).total_seconds()

    async def get_all(self) -> dict[str, T]:
        """Get all items (from cache or DB)."""
        if self._is_cache_valid() and self._cache is not None:
            self._cache_hits.add(1)
            self._cache_age.set(self.get_cache_age())
            return self._cache

        self._cache_misses.add(1)

        # Load from MongoDB
        items: dict[str, T] = {}
        async for doc in self._collection.find(self._get_filter()):
            item = self._parse_document(doc)
            key = self._get_cache_key(item)
            items[key] = item

        # Update cache
        self._cache = items
        self._cache_loaded_at = datetime.utcnow()
        self._cache_size.set(len(items))
        self._cache_age.set(0.0)

        logger.info(
            f"{self._cache_name} cache loaded",
            item_count=len(items)
        )
        return items

    async def get(self, key: str) -> T | None:
        """Get a specific item by key."""
        items = await self.get_all()
        return items.get(key)

    # ─────────────────────────────────────────────────────────────────────
    # HEALTH STATUS
    # ─────────────────────────────────────────────────────────────────────

    def get_health_status(self) -> dict:
        """Get cache health status for health endpoint."""
        return {
            "cache_size": len(self._cache) if self._cache else 0,
            "cache_age_seconds": self.get_cache_age(),
            "change_stream_active": (
                self._change_stream_task is not None
                and not self._change_stream_task.done()
            ),
            "cache_valid": self._is_cache_valid(),
        }
```

### 2. AgentConfigService (Using Base Class)

```python
# services/ai-model/src/ai_model/services/agent_config_service.py

from fp_common.cache import MongoChangeStreamCache
from ai_model.models import AgentConfig


class AgentConfigService(MongoChangeStreamCache[AgentConfig]):
    """Agent configuration service with Change Stream cache.

    Manages agent configs: disease-diagnosis, weekly-action-plan, etc.
    """

    def __init__(self, db):
        super().__init__(
            db=db,
            collection_name="agent_configs",
            cache_name="agent_config"
        )

    def _get_cache_key(self, item: AgentConfig) -> str:
        return item.agent_id

    def _parse_document(self, doc: dict) -> AgentConfig:
        return AgentConfig.model_validate(doc)

    def _get_filter(self) -> dict:
        return {"status": "active"}

    # ─────────────────────────────────────────────────────────────────────
    # DOMAIN-SPECIFIC METHODS
    # ─────────────────────────────────────────────────────────────────────

    async def get_config(self, agent_id: str) -> AgentConfig | None:
        """Get agent config by ID."""
        return await self.get(agent_id)

    async def get_configs_by_type(self, agent_type: str) -> list[AgentConfig]:
        """Get all configs of a specific type."""
        all_configs = await self.get_all()
        return [c for c in all_configs.values() if c.type == agent_type]
```

### 3. PromptService (Upgraded to Use Base Class)

```python
# services/ai-model/src/ai_model/services/prompt_service.py

from fp_common.cache import MongoChangeStreamCache
from ai_model.models import PromptDocument


class PromptService(MongoChangeStreamCache[PromptDocument]):
    """Prompt service with Change Stream cache.

    Manages prompts for all agents with A/B testing support.
    """

    def __init__(self, db):
        super().__init__(
            db=db,
            collection_name="prompts",
            cache_name="prompt"
        )
        # Additional cache for staged prompts (A/B testing)
        self._staged_cache: dict[str, PromptDocument] | None = None

    def _get_cache_key(self, item: PromptDocument) -> str:
        # Key by agent_id (active version)
        return item.agent_id

    def _parse_document(self, doc: dict) -> PromptDocument:
        return PromptDocument.model_validate(doc)

    def _get_filter(self) -> dict:
        return {"status": "active"}

    # ─────────────────────────────────────────────────────────────────────
    # DOMAIN-SPECIFIC METHODS
    # ─────────────────────────────────────────────────────────────────────

    async def get_prompt(self, agent_id: str) -> PromptDocument | None:
        """Get active prompt for an agent."""
        return await self.get(agent_id)

    async def get_prompt_for_ab_test(
        self,
        agent_id: str,
        use_staged: bool = False
    ) -> PromptDocument | None:
        """Get prompt with A/B test variant support."""
        if use_staged:
            return await self._get_staged_prompt(agent_id)
        return await self.get(agent_id)

    async def _get_staged_prompt(self, agent_id: str) -> PromptDocument | None:
        """Get staged prompt for A/B testing."""
        # Staged prompts are queried fresh (not cached) since A/B is temporary
        doc = await self._collection.find_one({
            "agent_id": agent_id,
            "status": "staged"
        })
        if doc:
            return PromptDocument.model_validate(doc)
        return None
```

### 4. Application Lifespan (Startup Warming)

```python
# services/ai-model/src/ai_model/main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI
import structlog

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with cache warming and change streams."""

    # ─────────────────────────────────────────────────────────────────────
    # STARTUP: Warm caches BEFORE accepting requests
    # ─────────────────────────────────────────────────────────────────────

    logger.info("Warming caches...")

    # 1. Agent Config cache
    agent_configs = await app.state.agent_config_service.get_all()
    logger.info("Agent config cache warmed", config_count=len(agent_configs))

    # 2. Prompt cache
    prompts = await app.state.prompt_service.get_all()
    logger.info("Prompt cache warmed", prompt_count=len(prompts))

    # ─────────────────────────────────────────────────────────────────────
    # STARTUP: Start Change Stream watchers
    # ─────────────────────────────────────────────────────────────────────

    await app.state.agent_config_service.start_change_stream()
    await app.state.prompt_service.start_change_stream()

    logger.info("AI Model ready - caches warmed, change streams active")

    yield

    # ─────────────────────────────────────────────────────────────────────
    # SHUTDOWN: Cleanup
    # ─────────────────────────────────────────────────────────────────────

    await app.state.agent_config_service.stop_change_stream()
    await app.state.prompt_service.stop_change_stream()

    logger.info("AI Model shutdown complete")
```

### 5. Health Endpoint

```python
# services/ai-model/src/ai_model/routes/health.py

from fastapi import APIRouter, Depends

router = APIRouter()


@router.get("/health/cache")
async def cache_health(
    agent_config_service = Depends(get_agent_config_service),
    prompt_service = Depends(get_prompt_service)
):
    """Cache health status for monitoring."""
    return {
        "agent_config": agent_config_service.get_health_status(),
        "prompt": prompt_service.get_health_status(),
    }
```

## Cache Behavior Summary

| Event | Agent Config | Prompt |
|-------|--------------|--------|
| Service starts | Cache warmed before requests | Cache warmed before requests |
| Config inserted | Change Stream → invalidate → reload | Change Stream → invalidate → reload |
| Config updated | Change Stream → invalidate → reload | Change Stream → invalidate → reload |
| Config deleted | Change Stream → invalidate → reload | Change Stream → invalidate → reload |
| TTL expires (fallback) | Next request reloads | Next request reloads |

## OpenTelemetry Metrics

| Metric | Type | Labels |
|--------|------|--------|
| `agent_config_cache_hits_total` | Counter | - |
| `agent_config_cache_misses_total` | Counter | - |
| `agent_config_cache_invalidations_total` | Counter | reason, item_id |
| `agent_config_cache_age_seconds` | Gauge | - |
| `agent_config_cache_size` | Gauge | - |
| `prompt_cache_hits_total` | Counter | - |
| `prompt_cache_misses_total` | Counter | - |
| `prompt_cache_invalidations_total` | Counter | reason, item_id |
| `prompt_cache_age_seconds` | Gauge | - |
| `prompt_cache_size` | Gauge | - |

## Grafana Alert Queries

```promql
# High cache miss rate (> 10% in 5 min)
rate(agent_config_cache_misses_total[5m]) /
(rate(agent_config_cache_hits_total[5m]) + rate(agent_config_cache_misses_total[5m])) > 0.1

# Change stream not active (stale cache risk)
agent_config_cache_age_seconds > 600  # 10 min without refresh

# Cache empty after startup
agent_config_cache_size == 0
```

## Consequences

### Positive

- **Real-time invalidation** - Cache refreshed within milliseconds of config change
- **Warm startup** - No cold cache on service restart
- **Observable** - Metrics for alerting and debugging
- **DRY code** - Shared base class for both caches
- **Consistency** - Same pattern as Collection Model (ADR-007)

### Negative

- **MongoDB replica set required** - Change Streams need replica set
- **Additional complexity** - Background task management
- **Memory usage** - All active configs in memory (acceptable for ~50 configs)

## MongoDB Requirements

Same as ADR-007:
- MongoDB replica set (not standalone)
- `readConcern: majority` (default in Atlas/CosmosDB)
- Appropriate permissions for `watch()`

## Revisit Triggers

Re-evaluate this decision if:

1. **Change stream overhead too high** - May need dedicated watcher service
2. **Config count exceeds 500+** - May need selective caching
3. **Multi-region deployment** - May need distributed cache

## References

- ADR-007: Source Config Cache with MongoDB Change Streams
- AI Model Architecture: Agent Configuration Flow
- [MongoDB Change Streams](https://www.mongodb.com/docs/manual/changeStreams/)
- [Motor Async Change Streams](https://motor.readthedocs.io/en/stable/api-asyncio/)
