"""Farmer repository for MongoDB persistence."""

import logging

from motor.motor_asyncio import AsyncIOMotorDatabase
from plantation_model.domain.models.farmer import Farmer
from plantation_model.infrastructure.repositories.base import BaseRepository
from pymongo import ASCENDING

logger = logging.getLogger(__name__)


class FarmerRepository(BaseRepository[Farmer]):
    """Repository for Farmer entities.

    Provides CRUD operations plus specialized queries:
    - get_by_phone: For duplicate phone detection during registration
    - get_by_national_id: For duplicate national ID detection
    - list_by_collection_point: List farmers registered at a collection point
    - list_by_region: List farmers in a region
    """

    COLLECTION_NAME = "farmers"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the farmer repository.

        Args:
            db: MongoDB database instance.
        """
        super().__init__(db, self.COLLECTION_NAME, Farmer)

    async def get_by_phone(self, phone: str) -> Farmer | None:
        """Get a farmer by phone number.

        Used for duplicate detection during registration.

        Args:
            phone: The farmer's phone number.

        Returns:
            The farmer if found, None otherwise.
        """
        doc = await self._collection.find_one({"contact.phone": phone})
        if doc is None:
            return None
        doc.pop("_id", None)
        return Farmer.model_validate(doc)

    async def get_by_national_id(self, national_id: str) -> Farmer | None:
        """Get a farmer by national ID.

        Used for duplicate detection during registration.

        Args:
            national_id: The farmer's government-issued national ID.

        Returns:
            The farmer if found, None otherwise.
        """
        doc = await self._collection.find_one({"national_id": national_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return Farmer.model_validate(doc)

    async def list_by_collection_point(
        self,
        collection_point_id: str,
        active_only: bool = True,
        page_size: int = 100,
        page_token: str | None = None,
    ) -> tuple[list[Farmer], str | None, int]:
        """List farmers registered at a specific collection point.

        Args:
            collection_point_id: The collection point identifier.
            active_only: If True, only return active farmers.
            page_size: Number of results per page.
            page_token: Token for the next page.

        Returns:
            Tuple of (farmers, next_page_token, total_count).
        """
        filters: dict = {"collection_point_id": collection_point_id}
        if active_only:
            filters["is_active"] = True
        return await self.list(filters, page_size, page_token)

    async def list_by_region(
        self,
        region_id: str,
        active_only: bool = True,
        page_size: int = 100,
        page_token: str | None = None,
    ) -> tuple[list[Farmer], str | None, int]:
        """List farmers in a specific region.

        Args:
            region_id: The region identifier.
            active_only: If True, only return active farmers.
            page_size: Number of results per page.
            page_token: Token for the next page.

        Returns:
            Tuple of (farmers, next_page_token, total_count).
        """
        filters: dict = {"region_id": region_id}
        if active_only:
            filters["is_active"] = True
        return await self.list(filters, page_size, page_token)

    async def list_by_farm_scale(
        self,
        farm_scale: str,
        region_id: str | None = None,
        active_only: bool = True,
        page_size: int = 100,
        page_token: str | None = None,
    ) -> tuple[list[Farmer], str | None, int]:
        """List farmers by farm scale classification.

        Args:
            farm_scale: The farm scale (smallholder, medium, estate).
            region_id: Optional region filter.
            active_only: If True, only return active farmers.
            page_size: Number of results per page.
            page_token: Token for the next page.

        Returns:
            Tuple of (farmers, next_page_token, total_count).
        """
        filters: dict = {"farm_scale": farm_scale}
        if region_id:
            filters["region_id"] = region_id
        if active_only:
            filters["is_active"] = True
        return await self.list(filters, page_size, page_token)

    async def list_active(
        self,
        page_size: int = 100,
        page_token: str | None = None,
    ) -> tuple[list[Farmer], str | None, int]:
        """List all active farmers.

        Args:
            page_size: Number of results per page.
            page_token: Token for the next page.

        Returns:
            Tuple of (farmers, next_page_token, total_count).
        """
        return await self.list({"is_active": True}, page_size, page_token)

    async def ensure_indexes(self) -> None:
        """Create indexes for the farmers collection.

        Indexes:
        - id (unique): Primary key lookup
        - contact.phone (unique): Phone duplicate detection
        - national_id (unique): National ID duplicate detection
        - collection_point_id: List farmers by CP
        - region_id: List farmers by region
        - farm_scale: Filter by farm classification
        - is_active: Filter active/inactive farmers
        """
        await self._collection.create_index(
            [("id", ASCENDING)],
            unique=True,
            name="idx_farmer_id",
        )
        await self._collection.create_index(
            [("contact.phone", ASCENDING)],
            unique=True,
            name="idx_farmer_phone",
        )
        await self._collection.create_index(
            [("national_id", ASCENDING)],
            unique=True,
            name="idx_farmer_national_id",
        )
        await self._collection.create_index(
            [("collection_point_id", ASCENDING)],
            name="idx_farmer_collection_point",
        )
        await self._collection.create_index(
            [("region_id", ASCENDING)],
            name="idx_farmer_region",
        )
        await self._collection.create_index(
            [("farm_scale", ASCENDING)],
            name="idx_farmer_farm_scale",
        )
        await self._collection.create_index(
            [("is_active", ASCENDING)],
            name="idx_farmer_active",
        )
        logger.info("Farmer indexes created")
