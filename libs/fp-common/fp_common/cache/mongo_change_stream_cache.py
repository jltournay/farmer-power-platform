"""MongoDB Change Stream cache base class.

Provides an abstract base class for in-memory caching with MongoDB Change Streams
for automatic invalidation. Pattern established in ADR-007 (Source Config Cache),
generalized in ADR-013 for reuse across AI Model services.

Features:
- Startup cache warming before accepting requests
- Change Stream watcher for real-time invalidation
- Resume token persistence for resilient reconnection
- TTL fallback (5-minute safety net)
- OpenTelemetry metrics for observability
- Health status reporting

Story 0.75.4: Extracted from Collection Model SourceConfigService for DRY reuse.
"""

from __future__ import annotations

import asyncio
import contextlib
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Generic, TypeVar

import structlog
from opentelemetry import metrics
from pydantic import BaseModel

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class MongoChangeStreamCache(ABC, Generic[T]):
    """Abstract base class for MongoDB-backed caches with Change Stream invalidation.

    Provides:
    - Startup cache warming
    - Change Stream auto-invalidation with resume token
    - TTL fallback (safety net)
    - OpenTelemetry metrics
    - Health status reporting

    Pattern aligned with ADR-007 (Source Config Cache), ADR-013.

    Subclasses must implement:
    - `_get_cache_key(item: T) -> str`: Extract cache key from item
    - `_parse_document(doc: dict) -> T`: Parse MongoDB document to model
    - `_get_filter() -> dict`: Get MongoDB filter for loading cache

    Example:
        class AgentConfigCache(MongoChangeStreamCache[AgentConfig]):
            def _get_cache_key(self, item: AgentConfig) -> str:
                return item.agent_id

            def _parse_document(self, doc: dict) -> AgentConfig:
                doc.pop("_id", None)
                return AgentConfig.model_validate(doc)

            def _get_filter(self) -> dict:
                return {"status": "active"}
    """

    CACHE_TTL_MINUTES: int = 5  # Fallback TTL if change stream disconnects

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        collection_name: str,
        cache_name: str,
    ) -> None:
        """Initialize the cache.

        Args:
            db: MongoDB database instance.
            collection_name: Name of the MongoDB collection to cache.
            cache_name: Cache identifier (used for metrics labels).
        """
        self._db = db
        self._collection_name = collection_name
        self._cache_name = cache_name

        # In-memory cache state
        self._cache: dict[str, T] | None = None
        self._cache_loaded_at: datetime | None = None

        # Change stream state
        self._change_stream_task: asyncio.Task | None = None
        self._change_stream_active: bool = False
        self._resume_token: dict | None = None

        # OpenTelemetry metrics
        meter = metrics.get_meter(cache_name)
        self._cache_hits = meter.create_counter(
            name=f"{cache_name}_cache_hits_total",
            description=f"Total number of {cache_name} cache hits",
            unit="1",
        )
        self._cache_misses = meter.create_counter(
            name=f"{cache_name}_cache_misses_total",
            description=f"Total number of {cache_name} cache misses",
            unit="1",
        )
        self._cache_invalidations = meter.create_counter(
            name=f"{cache_name}_cache_invalidations_total",
            description=f"Total number of {cache_name} cache invalidations",
            unit="1",
        )
        self._cache_size = meter.create_gauge(
            name=f"{cache_name}_cache_size",
            description=f"Current number of items in {cache_name} cache",
            unit="1",
        )
        self._cache_age = meter.create_gauge(
            name=f"{cache_name}_cache_age_seconds",
            description=f"Age of {cache_name} cache in seconds",
            unit="s",
        )

    @property
    def _collection(self) -> AsyncIOMotorCollection:
        """Get the MongoDB collection."""
        return self._db[self._collection_name]

    # -------------------------------------------------------------------------
    # Abstract Methods (must be implemented by subclasses)
    # -------------------------------------------------------------------------

    @abstractmethod
    def _get_cache_key(self, item: T) -> str:
        """Extract cache key from item.

        Args:
            item: Pydantic model instance.

        Returns:
            Cache key string (e.g., agent_id, source_id).
        """
        ...

    @abstractmethod
    def _parse_document(self, doc: dict) -> T:
        """Parse MongoDB document to Pydantic model.

        Args:
            doc: MongoDB document dict.

        Returns:
            Parsed Pydantic model instance.
        """
        ...

    @abstractmethod
    def _get_filter(self) -> dict:
        """Get MongoDB filter for loading cache.

        Returns:
            MongoDB filter dict (e.g., {"enabled": True}).
        """
        ...

    # -------------------------------------------------------------------------
    # Change Stream Management (ADR-007, AC4, AC5)
    # -------------------------------------------------------------------------

    async def start_change_stream(self) -> None:
        """Start watching for collection changes.

        Spawns a background task that watches the collection for
        insert, update, replace, and delete operations. On any change,
        the cache is invalidated.
        """
        if self._change_stream_task is not None and not self._change_stream_task.done():
            logger.warning(
                "Change stream already running",
                cache_name=self._cache_name,
            )
            return

        self._change_stream_active = True
        self._change_stream_task = asyncio.create_task(
            self._watch_changes(),
            name=f"{self._cache_name}_change_stream",
        )
        logger.info(
            "Change stream watcher started",
            cache_name=self._cache_name,
        )

    async def stop_change_stream(self) -> None:
        """Stop the change stream watcher."""
        self._change_stream_active = False
        if self._change_stream_task:
            self._change_stream_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._change_stream_task
            self._change_stream_task = None
        logger.info(
            "Change stream watcher stopped",
            cache_name=self._cache_name,
        )

    async def _watch_changes(self) -> None:
        """Watch MongoDB collection for changes.

        Uses resume token for resilient reconnection (AC5).
        Auto-reconnects on disconnect after brief pause.
        """
        pipeline = [{"$match": {"operationType": {"$in": ["insert", "update", "replace", "delete"]}}}]

        while self._change_stream_active:
            try:
                async with self._collection.watch(
                    pipeline,
                    full_document="updateLookup",
                    resume_after=self._resume_token,
                ) as stream:
                    logger.debug(
                        "Change stream connected",
                        cache_name=self._cache_name,
                        has_resume_token=self._resume_token is not None,
                    )
                    async for change in stream:
                        if not self._change_stream_active:
                            break
                        # Store resume token for reconnection (AC5)
                        self._resume_token = change.get("_id")
                        operation = change.get("operationType", "unknown")
                        doc_key = change.get("documentKey", {})
                        item_id = str(doc_key.get("_id", "unknown"))

                        self._invalidate_cache(
                            reason=f"change_stream:{operation}",
                            item_id=item_id,
                        )
                        logger.info(
                            "Cache invalidated by change stream",
                            cache_name=self._cache_name,
                            operation=operation,
                            item_id=item_id,
                        )

            except asyncio.CancelledError:
                logger.debug(
                    "Change stream watcher cancelled",
                    cache_name=self._cache_name,
                )
                break
            except Exception as e:
                if not self._change_stream_active:
                    break
                logger.warning(
                    "Change stream disconnected, reconnecting...",
                    cache_name=self._cache_name,
                    error=str(e),
                    has_resume_token=self._resume_token is not None,
                )
                await asyncio.sleep(1)  # Brief pause before reconnect

    # -------------------------------------------------------------------------
    # Cache Invalidation (AC7, AC8)
    # -------------------------------------------------------------------------

    def _invalidate_cache(self, reason: str, item_id: str = "all") -> None:
        """Invalidate the cache and record metrics.

        Args:
            reason: Reason for invalidation (for metrics label).
            item_id: ID of the item that triggered invalidation.
        """
        self._cache = None
        self._cache_loaded_at = None
        self._cache_invalidations.add(1, {"reason": reason, "item_id": item_id})
        self._cache_size.set(0)
        logger.debug(
            "Cache invalidated",
            cache_name=self._cache_name,
            reason=reason,
            item_id=item_id,
        )

    def invalidate_cache(self) -> None:
        """Force cache refresh on next call (public API)."""
        self._invalidate_cache(reason="manual")

    # -------------------------------------------------------------------------
    # Cache Validation (AC7)
    # -------------------------------------------------------------------------

    def _is_cache_valid(self) -> bool:
        """Check if cache is valid (not None and not expired).

        Returns:
            True if cache exists and TTL has not expired.
        """
        if self._cache is None or self._cache_loaded_at is None:
            return False
        age = datetime.now(UTC) - self._cache_loaded_at
        return age < timedelta(minutes=self.CACHE_TTL_MINUTES)

    def get_cache_age(self) -> float:
        """Get cache age in seconds.

        Returns:
            Age in seconds, or 0 if cache is not loaded.
        """
        if self._cache_loaded_at is None:
            return 0.0
        return (datetime.now(UTC) - self._cache_loaded_at).total_seconds()

    # -------------------------------------------------------------------------
    # Cache Access (AC6, AC8)
    # -------------------------------------------------------------------------

    async def get_all(self) -> dict[str, T]:
        """Get all items from cache or load from database.

        On first call or after invalidation, loads from MongoDB.
        Subsequent calls return cached data (cache hit).

        Returns:
            Dict mapping cache keys to Pydantic model instances.
        """
        if self._is_cache_valid() and self._cache is not None:
            self._cache_hits.add(1)
            self._update_cache_age_metric()
            logger.debug(
                "Cache hit",
                cache_name=self._cache_name,
                size=len(self._cache),
            )
            return self._cache

        # Cache miss - reload from database
        self._cache_misses.add(1)
        logger.debug(
            "Cache miss, reloading from database",
            cache_name=self._cache_name,
        )

        items: dict[str, T] = {}
        async for doc in self._collection.find(self._get_filter()):
            try:
                item = self._parse_document(doc)
                key = self._get_cache_key(item)
                items[key] = item
            except Exception as e:
                logger.warning(
                    "Failed to parse document, skipping",
                    cache_name=self._cache_name,
                    doc_id=str(doc.get("_id", "unknown")),
                    error=str(e),
                )

        # Update cache state
        self._cache = items
        self._cache_loaded_at = datetime.now(UTC)
        self._cache_size.set(len(items))
        self._update_cache_age_metric()

        logger.info(
            "Cache loaded from database",
            cache_name=self._cache_name,
            item_count=len(items),
        )
        return items

    async def get(self, key: str) -> T | None:
        """Get a specific item by key.

        Args:
            key: Cache key (e.g., agent_id).

        Returns:
            Pydantic model instance or None if not found.
        """
        items = await self.get_all()
        return items.get(key)

    def _update_cache_age_metric(self) -> None:
        """Update the cache age gauge metric."""
        age = self.get_cache_age()
        if age >= 0:
            self._cache_age.set(age)

    # -------------------------------------------------------------------------
    # Health Status (AC9)
    # -------------------------------------------------------------------------

    def get_health_status(self) -> dict[str, Any]:
        """Get cache health status for health endpoint.

        Returns:
            Dict with cache_size, cache_age_seconds, change_stream_active, cache_valid.
        """
        return {
            "cache_size": len(self._cache) if self._cache else 0,
            "cache_age_seconds": round(self.get_cache_age(), 2),
            "change_stream_active": (self._change_stream_task is not None and not self._change_stream_task.done()),
            "cache_valid": self._is_cache_valid(),
        }
