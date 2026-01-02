"""Runtime service for looking up source configurations.

This module provides SourceConfigService which loads source configurations
from MongoDB via SourceConfigRepository and caches them with a TTL for
efficient runtime lookups when processing Event Grid blob-created events.

Story 0.6.9: Added MongoDB Change Streams for real-time cache invalidation
and OpenTelemetry metrics for observability (ADR-007).
"""

import asyncio
import contextlib
import re
from datetime import UTC, datetime, timedelta

import structlog
from collection_model.infrastructure.repositories import SourceConfigRepository
from fp_common.models.source_config import SourceConfig
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from opentelemetry import metrics

logger = structlog.get_logger(__name__)

# Get the meter for collection_model
meter = metrics.get_meter("collection_model")

# Story 0.6.9: Cache metrics (ADR-007)
cache_hits_counter = meter.create_counter(
    name="source_config_cache_hits_total",
    description="Total number of source config cache hits",
    unit="1",
)

cache_misses_counter = meter.create_counter(
    name="source_config_cache_misses_total",
    description="Total number of source config cache misses",
    unit="1",
)

cache_invalidations_counter = meter.create_counter(
    name="source_config_cache_invalidations_total",
    description="Total number of cache invalidations",
    unit="1",
)

cache_size_gauge = meter.create_gauge(
    name="source_config_cache_size",
    description="Current number of items in the cache",
    unit="1",
)

cache_age_gauge = meter.create_gauge(
    name="source_config_cache_age_seconds",
    description="Age of the cache in seconds",
    unit="s",
)


class SourceConfigService:
    """Runtime service for looking up source configurations.

    Uses in-memory caching with MongoDB Change Streams for real-time
    invalidation (Story 0.6.9, ADR-007).

    Features:
    - Startup cache warming before accepting requests
    - Change Stream watcher for real-time invalidation
    - Resume token persistence for resilient reconnection
    - OpenTelemetry metrics for observability

    Attributes:
        CACHE_TTL_MINUTES: Fallback cache time-to-live in minutes.

    """

    CACHE_TTL_MINUTES = 5

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the source config service.

        Args:
            db: MongoDB database instance.

        """
        self._db = db
        self._repository = SourceConfigRepository(db)
        self._collection: AsyncIOMotorCollection = db["source_configs"]

        # In-memory cache of typed SourceConfig objects
        self._cache: list[SourceConfig] | None = None
        self._cache_loaded_at: datetime | None = None
        self._cache_expires: datetime | None = None

        # Story 0.6.9: Change Stream support (ADR-007)
        self._change_stream_task: asyncio.Task | None = None
        self._resume_token: dict | None = None
        self._change_stream_active: bool = False

    # -------------------------------------------------------------------------
    # Story 0.6.9: Startup Cache Warming (Task 2, AC1)
    # -------------------------------------------------------------------------

    async def warm_cache(self) -> int:
        """Warm the cache on service startup.

        Loads all enabled configs from MongoDB before accepting requests.
        Sets the cache size metric.

        Returns:
            Number of configs loaded into cache.
        """
        logger.info("Warming source config cache...")
        self._cache = await self._repository.get_all_enabled()
        self._cache_loaded_at = datetime.now(UTC)
        self._cache_expires = self._cache_loaded_at + timedelta(minutes=self.CACHE_TTL_MINUTES)

        config_count = len(self._cache)
        cache_size_gauge.set(config_count)

        logger.info("Cache warmed", config_count=config_count)
        return config_count

    # -------------------------------------------------------------------------
    # Story 0.6.9: Change Stream Watcher (Task 3, AC2, AC4)
    # -------------------------------------------------------------------------

    async def start_change_stream(self) -> None:
        """Start watching for collection changes.

        Spawns a background task that watches the source_configs collection
        for insert, update, replace, and delete operations. On any change,
        the cache is invalidated.
        """
        if self._change_stream_task is not None and not self._change_stream_task.done():
            logger.warning("Change stream already running")
            return

        self._change_stream_task = asyncio.create_task(self._watch_changes())
        self._change_stream_active = True
        logger.info("Change stream watcher started")

    async def stop_change_stream(self) -> None:
        """Stop the change stream watcher."""
        self._change_stream_active = False
        if self._change_stream_task:
            self._change_stream_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._change_stream_task
            self._change_stream_task = None
        logger.info("Change stream watcher stopped")

    async def _watch_changes(self) -> None:
        """Watch MongoDB collection for changes.

        Uses resume token for resilient reconnection (AC4).
        """
        pipeline = [{"$match": {"operationType": {"$in": ["insert", "update", "replace", "delete"]}}}]

        while self._change_stream_active:
            try:
                async with self._collection.watch(
                    pipeline,
                    full_document="updateLookup",
                    resume_after=self._resume_token,
                ) as stream:
                    logger.debug("Change stream connected", resume_token=self._resume_token is not None)
                    async for change in stream:
                        if not self._change_stream_active:
                            break
                        # Store resume token for reconnection (AC4)
                        self._resume_token = change.get("_id")
                        operation = change.get("operationType", "unknown")
                        source_id = change.get("documentKey", {}).get("_id", "unknown")

                        self._invalidate_cache(reason=f"change_stream:{operation}")
                        logger.info(
                            "Cache invalidated by change stream",
                            operation=operation,
                            source_id=source_id,
                        )

            except asyncio.CancelledError:
                logger.debug("Change stream watcher cancelled")
                break
            except Exception as e:
                if not self._change_stream_active:
                    break
                logger.warning(
                    "Change stream disconnected, reconnecting...",
                    error=str(e),
                    resume_token=self._resume_token is not None,
                )
                await asyncio.sleep(1)  # Brief pause before reconnect

    # -------------------------------------------------------------------------
    # Story 0.6.9: Cache Invalidation with Metrics (Task 1)
    # -------------------------------------------------------------------------

    def _invalidate_cache(self, reason: str) -> None:
        """Invalidate the cache and record metrics.

        Args:
            reason: Reason for invalidation (for metrics label).
        """
        self._cache = None
        self._cache_loaded_at = None
        self._cache_expires = None
        cache_invalidations_counter.add(1, {"reason": reason})
        cache_size_gauge.set(0)
        logger.debug("Source config cache invalidated", reason=reason)

    def invalidate_cache(self) -> None:
        """Force cache refresh on next call (public API)."""
        self._invalidate_cache(reason="manual")

    # -------------------------------------------------------------------------
    # Story 0.6.9: Cache Hit/Miss Tracking (Task 4, AC3)
    # -------------------------------------------------------------------------

    async def get_all_configs(self) -> list[SourceConfig]:
        """Get all enabled source configs (cached with change stream invalidation).

        Tracks cache hits and misses via metrics.

        Returns:
            List of enabled source configurations as typed SourceConfig models.
        """
        now = datetime.now(UTC)

        # Cache hit
        if self._cache is not None and self._cache_expires is not None and now < self._cache_expires:
            cache_hits_counter.add(1)
            self._update_cache_age_metric()
            logger.debug("Cache hit", count=len(self._cache))
            return self._cache

        # Cache miss
        cache_misses_counter.add(1)
        logger.debug("Cache miss, reloading from database")

        self._cache = await self._repository.get_all_enabled()
        self._cache_loaded_at = datetime.now(UTC)
        self._cache_expires = self._cache_loaded_at + timedelta(minutes=self.CACHE_TTL_MINUTES)

        cache_size_gauge.set(len(self._cache))
        self._update_cache_age_metric()

        logger.info(
            "Refreshed source configs cache",
            count=len(self._cache),
            expires_at=self._cache_expires.isoformat(),
        )
        return self._cache

    def _update_cache_age_metric(self) -> None:
        """Update the cache age gauge metric."""
        age = self.get_cache_age()
        if age >= 0:
            cache_age_gauge.set(age)

    # -------------------------------------------------------------------------
    # Story 0.6.9: Health Endpoint Support (Task 5)
    # -------------------------------------------------------------------------

    def get_cache_age(self) -> float:
        """Get cache age in seconds.

        Returns:
            Age in seconds, or -1 if cache is not loaded.
        """
        if self._cache_loaded_at is None:
            return -1.0
        return (datetime.now(UTC) - self._cache_loaded_at).total_seconds()

    def get_cache_status(self) -> dict:
        """Get cache status for health endpoint.

        Returns:
            Dict with cache_size, cache_age_seconds, change_stream_active.
        """
        return {
            "cache_size": len(self._cache) if self._cache else 0,
            "cache_age_seconds": round(self.get_cache_age(), 2),
            "change_stream_active": (self._change_stream_task is not None and not self._change_stream_task.done()),
        }

    async def get_config(self, source_id: str) -> SourceConfig | None:
        """Get a single source config by source_id.

        Args:
            source_id: Source identifier.

        Returns:
            Source config or None if not found.
        """
        configs = await self.get_all_configs()
        for config in configs:
            if config.source_id == source_id:
                return config
        return None

    async def get_config_by_container(self, container: str) -> SourceConfig | None:
        """Find source config matching the given container.

        Searches through enabled source configs for one with blob_trigger mode
        and matching landing_container.

        Args:
            container: Azure Blob Storage container name.

        Returns:
            Matching source config or None if not found.

        """
        configs = await self.get_all_configs()
        for config in configs:
            if config.ingestion.mode == "blob_trigger" and config.ingestion.landing_container == container:
                logger.debug(
                    "Found source config for container",
                    container=container,
                    source_id=config.source_id,
                )
                return config
        return None

    @staticmethod
    def extract_path_metadata(
        blob_path: str,
        config: SourceConfig,
    ) -> dict[str, str]:
        """Extract metadata from blob path using config pattern.

        Uses regex for robust pattern matching.

        Example:
            Pattern: "results/{plantation_id}/{crop}/{market}/{batch_id}.json"
            Path: "results/WM-4521/tea/mombasa/batch-001.json"
            Result: {"plantation_id": "WM-4521", "crop": "tea", ...}

        Args:
            blob_path: Full blob path from Event Grid event.
            config: Source configuration with path_pattern.

        Returns:
            Dict of extracted field values, empty if pattern doesn't match.

        """
        path_pattern = config.ingestion.path_pattern
        if not path_pattern:
            return {}

        pattern = path_pattern.pattern
        extract_fields = set(path_pattern.extract_fields)

        if not pattern:
            return {}

        # Convert pattern to regex with named groups
        def replace_placeholder(match_obj: re.Match[str]) -> str:
            field_name = match_obj.group(1)
            return f"(?P<{field_name}>[^/]+)"

        regex_pattern = re.sub(r"\{(\w+)\}", replace_placeholder, pattern)
        # Escape dots for file extensions
        regex_pattern = regex_pattern.replace(".", r"\.")
        regex_pattern = f"^{regex_pattern}$"

        match_result = re.match(regex_pattern, blob_path)
        if not match_result:
            logger.debug(
                "Blob path does not match pattern",
                blob_path=blob_path,
                pattern=pattern,
            )
            return {}

        # Return only fields specified in extract_fields
        extracted = {k: v for k, v in match_result.groupdict().items() if k in extract_fields}

        logger.debug(
            "Extracted path metadata",
            blob_path=blob_path,
            extracted=extracted,
        )
        return extracted
