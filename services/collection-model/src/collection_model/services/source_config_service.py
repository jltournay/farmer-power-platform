"""Runtime service for looking up source configurations.

This module provides SourceConfigService which loads source configurations
from MongoDB and caches them with MongoDB Change Streams for real-time
invalidation.

Story 0.6.9: Added MongoDB Change Streams for real-time cache invalidation
and OpenTelemetry metrics for observability (ADR-007).

Story 0.75.4: Refactored to extend MongoChangeStreamCache base class (ADR-013).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import structlog
from fp_common.cache import MongoChangeStreamCache
from fp_common.models.source_config import SourceConfig

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

logger = structlog.get_logger(__name__)


class SourceConfigService(MongoChangeStreamCache[SourceConfig]):
    """Runtime service for looking up source configurations.

    Uses in-memory caching with MongoDB Change Streams for real-time
    invalidation (Story 0.6.9, ADR-007). Refactored to extend shared
    base class (Story 0.75.4, ADR-013).

    Features (inherited from MongoChangeStreamCache):
    - Startup cache warming before accepting requests
    - Change Stream watcher for real-time invalidation
    - Resume token persistence for resilient reconnection
    - OpenTelemetry metrics for observability

    Domain-specific features:
    - get_config(): Lookup by source_id
    - get_config_by_container(): Find config matching blob container
    - extract_path_metadata(): Parse blob paths using config patterns
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the source config service.

        Args:
            db: MongoDB database instance.
        """
        super().__init__(
            db=db,
            collection_name="source_configs",
            cache_name="source_config",
        )

    # -------------------------------------------------------------------------
    # Abstract Method Implementations (required by MongoChangeStreamCache)
    # -------------------------------------------------------------------------

    def _get_cache_key(self, item: SourceConfig) -> str:
        """Extract cache key from SourceConfig.

        Args:
            item: SourceConfig instance.

        Returns:
            The source_id as cache key.
        """
        return item.source_id

    def _parse_document(self, doc: dict) -> SourceConfig:
        """Parse MongoDB document to SourceConfig model.

        Args:
            doc: MongoDB document dict.

        Returns:
            Parsed SourceConfig instance.
        """
        # Remove MongoDB _id if present (not in our Pydantic model)
        doc.pop("_id", None)
        return SourceConfig.model_validate(doc)

    def _get_filter(self) -> dict:
        """Get MongoDB filter for loading enabled configs.

        Returns:
            Filter for enabled configs only.
        """
        return {"enabled": True}

    # -------------------------------------------------------------------------
    # Domain-Specific Methods
    # -------------------------------------------------------------------------

    async def get_config(self, source_id: str) -> SourceConfig | None:
        """Get a single source config by source_id.

        Args:
            source_id: Source identifier.

        Returns:
            Source config or None if not found.
        """
        return await self.get(source_id)

    async def get_config_by_container(self, container: str) -> SourceConfig | None:
        """Find source config matching the given container.

        Searches through enabled source configs for one with blob_trigger mode
        and matching landing_container.

        Args:
            container: Azure Blob Storage container name.

        Returns:
            Matching source config or None if not found.
        """
        configs = await self.get_all()
        for config in configs.values():
            if config.ingestion.mode == "blob_trigger" and config.ingestion.landing_container == container:
                logger.debug(
                    "Found source config for container",
                    container=container,
                    source_id=config.source_id,
                )
                return config
        return None

    async def get_all_configs(self) -> list[SourceConfig]:
        """Get all enabled source configs as a list.

        Returns:
            List of enabled source configurations.

        Note:
            This method exists for backwards compatibility.
            Internally it calls get_all() and returns values as a list.
        """
        configs = await self.get_all()
        return list(configs.values())

    def get_cache_status(self) -> dict:
        """Get cache status for health endpoint.

        Returns:
            Dict with cache_size, cache_age_seconds, change_stream_active.

        Note:
            This method exists for backwards compatibility.
            Same as get_health_status() from base class.
        """
        return self.get_health_status()

    async def warm_cache(self) -> int:
        """Warm the cache on service startup.

        Loads all enabled configs from MongoDB before accepting requests.

        Returns:
            Number of configs loaded into cache.

        Note:
            This method exists for backwards compatibility.
            Calls get_all() which handles cache warming.
        """
        configs = await self.get_all()
        logger.info("Source config cache warmed", config_count=len(configs))
        return len(configs)

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
