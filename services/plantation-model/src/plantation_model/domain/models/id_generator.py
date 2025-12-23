"""ID generation utilities for domain entities."""

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument


class IDGenerator:
    """Generates unique IDs for domain entities using MongoDB atomic counters.

    Factory IDs: KEN-FAC-XXX (e.g., KEN-FAC-001)
    Collection Point IDs: {region_id}-cp-XXX (e.g., nyeri-highland-cp-001)
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the ID generator.

        Args:
            db: MongoDB database instance.
        """
        self._db = db
        self._counters = db["id_counters"]

    async def generate_factory_id(self) -> str:
        """Generate a new factory ID in format KEN-FAC-XXX.

        Returns:
            A unique factory ID string.
        """
        result = await self._counters.find_one_and_update(
            {"_id": "factory"},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return f"KEN-FAC-{result['seq']:03d}"

    async def generate_collection_point_id(self, region_id: str) -> str:
        """Generate a new collection point ID in format {region_id}-cp-XXX.

        Args:
            region_id: The region identifier for the collection point.

        Returns:
            A unique collection point ID string.
        """
        counter_key = f"cp_{region_id}"
        result = await self._counters.find_one_and_update(
            {"_id": counter_key},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return f"{region_id}-cp-{result['seq']:03d}"

    async def generate_farmer_id(self) -> str:
        """Generate a new farmer ID in format WM-XXXX.

        The WM prefix stands for "Wanjiku Mama" - the tea farmer persona.
        IDs are zero-padded 4-digit numbers (e.g., WM-0001, WM-1234).

        Returns:
            A unique farmer ID string.
        """
        result = await self._counters.find_one_and_update(
            {"_id": "farmer"},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return f"WM-{result['seq']:04d}"
