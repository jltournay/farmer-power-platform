"""Collection Point repository for MongoDB persistence."""

import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase
from plantation_model.domain.models import CollectionPoint
from plantation_model.infrastructure.repositories.base import BaseRepository
from pymongo import ASCENDING

logger = structlog.get_logger("plantation_model.infrastructure.repositories.collection_point_repository")


class CollectionPointRepository(BaseRepository[CollectionPoint]):
    """Repository for CollectionPoint entities."""

    COLLECTION_NAME = "collection_points"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the collection point repository.

        Args:
            db: MongoDB database instance.
        """
        super().__init__(db, self.COLLECTION_NAME, CollectionPoint)

    async def list_by_factory(
        self,
        factory_id: str,
        active_only: bool = False,
        page_size: int = 100,
        page_token: str | None = None,
    ) -> tuple[list[CollectionPoint], str | None, int]:
        """List collection points for a specific factory.

        Args:
            factory_id: The parent factory identifier.
            active_only: If True, only return active collection points.
            page_size: Number of results per page.
            page_token: Token for the next page.

        Returns:
            Tuple of (collection_points, next_page_token, total_count).
        """
        filters: dict = {"factory_id": factory_id}
        if active_only:
            filters["status"] = "active"
        return await self.list(filters, page_size, page_token)

    async def list_by_region(
        self,
        region_id: str,
        status: str | None = None,
        page_size: int = 100,
        page_token: str | None = None,
    ) -> tuple[list[CollectionPoint], str | None, int]:
        """List collection points in a specific region.

        Args:
            region_id: The region identifier.
            status: Optional status filter (active, inactive, seasonal).
            page_size: Number of results per page.
            page_token: Token for the next page.

        Returns:
            Tuple of (collection_points, next_page_token, total_count).
        """
        filters: dict = {"region_id": region_id}
        if status:
            filters["status"] = status
        return await self.list(filters, page_size, page_token)

    async def list_by_clerk(
        self,
        clerk_id: str,
        page_size: int = 100,
        page_token: str | None = None,
    ) -> tuple[list[CollectionPoint], str | None, int]:
        """List collection points assigned to a specific clerk.

        Args:
            clerk_id: The clerk identifier.
            page_size: Number of results per page.
            page_token: Token for the next page.

        Returns:
            Tuple of (collection_points, next_page_token, total_count).
        """
        return await self.list({"clerk_id": clerk_id}, page_size, page_token)

    async def list_by_status(
        self,
        status: str,
        page_size: int = 100,
        page_token: str | None = None,
    ) -> tuple[list[CollectionPoint], str | None, int]:
        """List collection points by status.

        Args:
            status: The status filter (active, inactive, seasonal).
            page_size: Number of results per page.
            page_token: Token for the next page.

        Returns:
            Tuple of (collection_points, next_page_token, total_count).
        """
        return await self.list({"status": status}, page_size, page_token)

    async def ensure_indexes(self) -> None:
        """Create indexes for the collection_points collection."""
        await self._collection.create_index(
            [("id", ASCENDING)],
            unique=True,
            name="idx_cp_id",
        )
        await self._collection.create_index(
            [("factory_id", ASCENDING)],
            name="idx_cp_factory",
        )
        await self._collection.create_index(
            [("region_id", ASCENDING)],
            name="idx_cp_region",
        )
        await self._collection.create_index(
            [("status", ASCENDING)],
            name="idx_cp_status",
        )
        await self._collection.create_index(
            [("clerk_id", ASCENDING)],
            name="idx_cp_clerk",
        )
        logger.info("CollectionPoint indexes created")
