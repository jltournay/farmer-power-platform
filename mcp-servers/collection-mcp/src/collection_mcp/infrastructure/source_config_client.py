"""Source configuration client for querying available sources."""

from typing import Any

import structlog
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = structlog.get_logger(__name__)


class SourceConfigClientError(Exception):
    """Raised when source config operations fail."""

    pass


class SourceConfigClient:
    """Async MongoDB client for source configuration operations.

    Uses direct MongoDB read from source_configs collection for simplicity.
    This is read-only access - source configs are managed by collection-model service.
    """

    def __init__(self, mongodb_uri: str, database_name: str) -> None:
        """Initialize the source config client.

        Args:
            mongodb_uri: MongoDB connection URI
            database_name: Name of the database to use
        """
        self._client: AsyncIOMotorClient = AsyncIOMotorClient(mongodb_uri)
        self._db: AsyncIOMotorDatabase = self._client[database_name]
        self._collection = self._db["source_configs"]

    async def list_sources(
        self,
        enabled_only: bool = True,
    ) -> list[dict[str, Any]]:
        """List all configured data sources.

        Args:
            enabled_only: If True, only return enabled sources

        Returns:
            List of source configuration summaries containing:
            - source_id
            - display_name
            - ingestion.mode
            - description
        """
        query: dict[str, Any] = {}

        if enabled_only:
            query["enabled"] = True

        logger.debug(
            "Listing source configurations",
            enabled_only=enabled_only,
        )

        # Project only the fields needed for MCP response
        projection = {
            "_id": 0,
            "source_id": 1,
            "display_name": 1,
            "description": 1,
            "enabled": 1,
            "ingestion.mode": 1,
            "ingestion.schedule": 1,
        }

        cursor = self._collection.find(query, projection).sort("source_id", 1)
        sources = await cursor.to_list(length=100)

        # Transform to expected format
        result = []
        for source in sources:
            ingestion = source.get("ingestion", {})
            result.append(
                {
                    "source_id": source.get("source_id"),
                    "display_name": source.get("display_name", source.get("source_id")),
                    "description": source.get("description", ""),
                    "enabled": source.get("enabled", True),
                    "ingestion_mode": ingestion.get("mode", "unknown"),
                    "ingestion_schedule": ingestion.get("schedule"),
                }
            )

        logger.info(
            "Source configurations listed",
            count=len(result),
            enabled_only=enabled_only,
        )

        return result

    async def get_source(self, source_id: str) -> dict[str, Any] | None:
        """Get a single source configuration by ID.

        Args:
            source_id: The source identifier

        Returns:
            Source configuration dictionary or None if not found
        """
        logger.debug("Getting source configuration", source_id=source_id)

        source = await self._collection.find_one({"source_id": source_id})

        if source:
            # Convert ObjectId to string if present
            if "_id" in source:
                source["_id"] = str(source["_id"])
            logger.info("Source configuration retrieved", source_id=source_id)
        else:
            logger.warning("Source configuration not found", source_id=source_id)

        return source

    async def close(self) -> None:
        """Close the MongoDB client connection."""
        self._client.close()
        logger.info("Source config client connection closed")
