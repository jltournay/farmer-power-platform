"""Repository for SourceConfig persistence operations.

This repository handles all database operations for SourceConfig entities,
returning typed Pydantic models instead of raw dicts.
"""

import logging

from collection_model.infrastructure.repositories.base import BaseRepository
from fp_common.models.source_config import SourceConfig
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class SourceConfigRepository(BaseRepository[SourceConfig]):
    """Repository for SourceConfig persistence.

    Note: SourceConfig uses `source_id` as its unique identifier instead of `id`,
    so we override the base methods that rely on `id` field.
    """

    COLLECTION_NAME = "source_configs"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the repository.

        Args:
            db: MongoDB database instance.
        """
        super().__init__(db, self.COLLECTION_NAME, SourceConfig)

    async def create(self, entity: SourceConfig) -> SourceConfig:
        """Create a new source config.

        Args:
            entity: The source config to create.

        Returns:
            The created source config.
        """
        doc = entity.model_dump()
        doc["_id"] = entity.source_id  # Use source_id as MongoDB _id
        await self._collection.insert_one(doc)
        logger.debug("Created SourceConfig with source_id %s", entity.source_id)
        return entity

    async def get_by_source_id(self, source_id: str) -> SourceConfig | None:
        """Get a source config by its source_id.

        Args:
            source_id: The source config's unique identifier.

        Returns:
            The source config if found, None otherwise.
        """
        doc = await self._collection.find_one({"source_id": source_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return SourceConfig.model_validate(doc)

    async def get_all_enabled(self) -> list[SourceConfig]:
        """Get all enabled source configs.

        Returns:
            List of enabled source configs.
        """
        cursor = self._collection.find({"enabled": True})
        docs = await cursor.to_list(length=100)  # MAX_CONFIGS

        configs = []
        for doc in docs:
            doc.pop("_id", None)
            configs.append(SourceConfig.model_validate(doc))

        logger.debug("Loaded %d enabled source configs", len(configs))
        return configs

    async def get_by_container(self, container: str) -> SourceConfig | None:
        """Find source config matching the given container.

        Searches through enabled source configs for one with blob_trigger mode
        and matching landing_container.

        Args:
            container: Azure Blob Storage container name.

        Returns:
            Matching source config or None if not found.
        """
        doc = await self._collection.find_one(
            {
                "enabled": True,
                "ingestion.mode": "blob_trigger",
                "ingestion.landing_container": container,
            }
        )
        if doc is None:
            return None
        doc.pop("_id", None)
        logger.debug(
            "Found source config for container",
            extra={"container": container, "source_id": doc.get("source_id")},
        )
        return SourceConfig.model_validate(doc)

    async def ensure_indexes(self) -> None:
        """Create indexes for the source_configs collection."""
        await self._collection.create_index("source_id", unique=True)
        await self._collection.create_index([("enabled", 1), ("ingestion.mode", 1), ("ingestion.landing_container", 1)])
        logger.debug("Created indexes for source_configs collection")
