"""Runtime service for looking up source configurations.

This module provides SourceConfigService which loads source configurations
from MongoDB and caches them with a TTL for efficient runtime lookups
when processing Event Grid blob-created events.
"""

import re
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = structlog.get_logger(__name__)


class SourceConfigService:
    """Runtime service for looking up source configurations.

    Uses in-memory caching with TTL instead of aiocache to avoid
    serialization issues with Motor async cursors.

    Attributes:
        CACHE_TTL_MINUTES: Cache time-to-live in minutes.
        MAX_CONFIGS: Maximum number of source configs to cache.
        COLLECTION_NAME: MongoDB collection name for source configs.

    """

    CACHE_TTL_MINUTES = 5
    MAX_CONFIGS = 100  # Maximum source configs expected per deployment
    COLLECTION_NAME = "source_configs"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the source config service.

        Args:
            db: MongoDB database instance.

        """
        self.db = db
        self.collection = db[self.COLLECTION_NAME]
        # In-memory cache (avoids aiocache async serialization issues)
        self._cache: list[dict[str, Any]] | None = None
        self._cache_expires: datetime | None = None

    async def get_all_configs(self) -> list[dict[str, Any]]:
        """Get all enabled source configs (cached with 5-min TTL).

        Returns:
            List of enabled source configuration documents.

        """
        now = datetime.now(UTC)
        if self._cache is not None and self._cache_expires is not None and now < self._cache_expires:
            logger.debug("Returning cached source configs", count=len(self._cache))
            return self._cache

        cursor = self.collection.find({"enabled": True})
        self._cache = await cursor.to_list(length=self.MAX_CONFIGS)
        self._cache_expires = now + timedelta(minutes=self.CACHE_TTL_MINUTES)

        logger.info(
            "Refreshed source configs cache",
            count=len(self._cache),
            expires_at=self._cache_expires.isoformat(),
        )
        return self._cache

    def invalidate_cache(self) -> None:
        """Force cache refresh on next call."""
        self._cache = None
        self._cache_expires = None
        logger.debug("Source config cache invalidated")

    async def get_config(self, source_id: str) -> dict[str, Any] | None:
        """Get a single source config by source_id.

        Args:
            source_id: Source identifier.

        Returns:
            Source config document or None if not found.
        """
        configs = await self.get_all_configs()
        for config in configs:
            if config.get("source_id") == source_id:
                return config
        return None

    async def get_config_by_container(self, container: str) -> dict[str, Any] | None:
        """Find source config matching the given container.

        Searches through enabled source configs for one with BLOB_TRIGGER mode
        and matching landing_container.

        Args:
            container: Azure Blob Storage container name.

        Returns:
            Matching source config document or None if not found.

        """
        configs = await self.get_all_configs()
        for config in configs:
            ingestion = config.get("ingestion", {})
            if ingestion.get("mode") == "blob_trigger":
                landing_container = ingestion.get("landing_container")
                if landing_container == container:
                    logger.debug(
                        "Found source config for container",
                        container=container,
                        source_id=config.get("source_id"),
                    )
                    return config
        return None

    @staticmethod
    def extract_path_metadata(
        blob_path: str,
        config: dict[str, Any],
    ) -> dict[str, str]:
        """Extract metadata from blob path using config pattern.

        Uses regex for robust pattern matching.

        Example:
            Pattern: "results/{plantation_id}/{crop}/{market}/{batch_id}.json"
            Path: "results/WM-4521/tea/mombasa/batch-001.json"
            Result: {"plantation_id": "WM-4521", "crop": "tea", ...}

        Args:
            blob_path: Full blob path from Event Grid event.
            config: Source configuration document with path_pattern.

        Returns:
            Dict of extracted field values, empty if pattern doesn't match.

        """
        ingestion = config.get("ingestion", {})
        path_pattern = ingestion.get("path_pattern")
        if not path_pattern:
            return {}

        pattern = path_pattern.get("pattern", "")
        extract_fields = set(path_pattern.get("extract_fields", []))

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
