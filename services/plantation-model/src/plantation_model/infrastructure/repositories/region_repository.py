"""Region repository for MongoDB persistence."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from plantation_model.domain.models.region import Region
from pymongo import ASCENDING

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class RegionRepository:
    """Repository for Region entities.

    Note: Region uses `region_id` as the primary key (not `id` like other entities).
    This is intentional since region_id follows a semantic format: {county}-{altitude_band}.
    """

    COLLECTION_NAME = "regions"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the region repository.

        Args:
            db: MongoDB database instance.
        """
        self._db = db
        self._collection: AsyncIOMotorCollection = db[self.COLLECTION_NAME]

    async def create(self, region: Region) -> Region:
        """Create a new region.

        Args:
            region: The region to create.

        Returns:
            The created region.
        """
        doc = region.model_dump()
        # Use region_id as MongoDB _id for efficient lookups
        doc["_id"] = doc["region_id"]
        await self._collection.insert_one(doc)
        logger.debug("Created Region with id %s", doc["region_id"])
        return region

    async def get_by_id(self, region_id: str) -> Region | None:
        """Get a region by its ID.

        Args:
            region_id: The region's unique identifier (e.g., "nyeri-highland").

        Returns:
            The region if found, None otherwise.
        """
        doc = await self._collection.find_one({"_id": region_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return Region.model_validate(doc)

    async def update(self, region_id: str, updates: dict) -> Region | None:
        """Update a region.

        Args:
            region_id: The region's unique identifier.
            updates: Dictionary of fields to update.

        Returns:
            The updated region if found, None otherwise.
        """
        # Add updated_at timestamp
        updates["updated_at"] = datetime.now(UTC)

        result = await self._collection.update_one(
            {"_id": region_id},
            {"$set": updates},
        )
        if result.matched_count == 0:
            return None

        # Fetch the updated document
        return await self.get_by_id(region_id)

    async def delete(self, region_id: str) -> bool:
        """Delete a region.

        Args:
            region_id: The region's unique identifier.

        Returns:
            True if deleted, False if not found.
        """
        result = await self._collection.delete_one({"_id": region_id})
        return result.deleted_count > 0

    async def list(
        self,
        county: str | None = None,
        altitude_band: str | None = None,
        active_only: bool = True,
        page_size: int = 100,
        page_token: str | None = None,
    ) -> tuple[list[Region], str | None, int]:
        """List regions with optional filtering.

        Args:
            county: Optional filter by county name.
            altitude_band: Optional filter by altitude band (highland/midland/lowland).
            active_only: If True, only return active regions.
            page_size: Number of results per page.
            page_token: Token for the next page (region_id).

        Returns:
            Tuple of (regions, next_page_token, total_count).
        """
        query: dict = {}

        if county:
            query["county"] = county
        if altitude_band:
            # Match altitude_band.label in geography
            query["geography.altitude_band.label"] = altitude_band
        if active_only:
            query["is_active"] = True

        # Get total count
        total_count = await self._collection.count_documents(query)

        # Add pagination if page_token provided
        if page_token:
            query["_id"] = {"$gt": page_token}

        # Execute query
        cursor = self._collection.find(query).sort("_id", 1).limit(page_size + 1)
        docs = await cursor.to_list(length=page_size + 1)

        # Check if there are more results
        next_page_token = None
        if len(docs) > page_size:
            docs = docs[:page_size]
            next_page_token = docs[-1]["_id"] if docs else None

        # Convert to models
        regions = []
        for doc in docs:
            doc.pop("_id", None)
            regions.append(Region.model_validate(doc))

        return regions, next_page_token, total_count

    async def list_by_county(
        self,
        county: str,
        active_only: bool = True,
        page_size: int = 100,
        page_token: str | None = None,
    ) -> tuple[list[Region], str | None, int]:
        """List regions in a specific county.

        Args:
            county: The county name.
            active_only: If True, only return active regions.
            page_size: Number of results per page.
            page_token: Token for the next page.

        Returns:
            Tuple of (regions, next_page_token, total_count).
        """
        return await self.list(
            county=county,
            active_only=active_only,
            page_size=page_size,
            page_token=page_token,
        )

    async def list_active(
        self,
        page_size: int = 100,
        page_token: str | None = None,
    ) -> tuple[list[Region], str | None, int]:
        """List all active regions.

        Args:
            page_size: Number of results per page.
            page_token: Token for the next page.

        Returns:
            Tuple of (regions, next_page_token, total_count).
        """
        return await self.list(
            active_only=True,
            page_size=page_size,
            page_token=page_token,
        )

    async def ensure_indexes(self) -> None:
        """Create indexes for the regions collection."""
        # Primary key index (region_id)
        await self._collection.create_index(
            [("region_id", ASCENDING)],
            unique=True,
            name="idx_region_id",
        )
        # County index for filtering
        await self._collection.create_index(
            [("county", ASCENDING)],
            name="idx_region_county",
        )
        # Altitude band index for filtering
        await self._collection.create_index(
            [("geography.altitude_band.label", ASCENDING)],
            name="idx_region_altitude_band",
        )
        # Active flag index
        await self._collection.create_index(
            [("is_active", ASCENDING)],
            name="idx_region_active",
        )
        logger.info("Region indexes created")
