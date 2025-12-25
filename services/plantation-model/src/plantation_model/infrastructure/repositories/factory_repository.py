"""Factory repository for MongoDB persistence."""

import logging

from motor.motor_asyncio import AsyncIOMotorDatabase
from plantation_model.domain.models.factory import Factory
from plantation_model.infrastructure.repositories.base import BaseRepository
from pymongo import ASCENDING

logger = logging.getLogger(__name__)


class FactoryRepository(BaseRepository[Factory]):
    """Repository for Factory entities."""

    COLLECTION_NAME = "factories"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the factory repository.

        Args:
            db: MongoDB database instance.
        """
        super().__init__(db, self.COLLECTION_NAME, Factory)

    async def get_by_code(self, code: str) -> Factory | None:
        """Get a factory by its unique code.

        Args:
            code: The factory's unique code.

        Returns:
            The factory if found, None otherwise.
        """
        doc = await self._collection.find_one({"code": code})
        if doc is None:
            return None
        doc.pop("_id", None)
        return Factory.model_validate(doc)

    async def list_by_region(
        self,
        region_id: str,
        active_only: bool = True,
        page_size: int = 100,
        page_token: str | None = None,
    ) -> tuple[list[Factory], str | None, int]:
        """List factories in a specific region.

        Args:
            region_id: The region identifier.
            active_only: If True, only return active factories.
            page_size: Number of results per page.
            page_token: Token for the next page.

        Returns:
            Tuple of (factories, next_page_token, total_count).
        """
        filters: dict = {"region_id": region_id}
        if active_only:
            filters["is_active"] = True
        return await self.list(filters, page_size, page_token)

    async def list_active(
        self,
        page_size: int = 100,
        page_token: str | None = None,
    ) -> tuple[list[Factory], str | None, int]:
        """List all active factories.

        Args:
            page_size: Number of results per page.
            page_token: Token for the next page.

        Returns:
            Tuple of (factories, next_page_token, total_count).
        """
        return await self.list({"is_active": True}, page_size, page_token)

    async def ensure_indexes(self) -> None:
        """Create indexes for the factories collection."""
        await self._collection.create_index(
            [("id", ASCENDING)],
            unique=True,
            name="idx_factory_id",
        )
        await self._collection.create_index(
            [("code", ASCENDING)],
            unique=True,
            name="idx_factory_code",
        )
        await self._collection.create_index(
            [("region_id", ASCENDING)],
            name="idx_factory_region",
        )
        await self._collection.create_index(
            [("is_active", ASCENDING)],
            name="idx_factory_active",
        )
        logger.info("Factory indexes created")
