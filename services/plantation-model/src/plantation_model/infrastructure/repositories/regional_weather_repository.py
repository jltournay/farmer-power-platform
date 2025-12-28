"""RegionalWeather repository for MongoDB persistence."""

from __future__ import annotations

import datetime as dt
import logging
from datetime import UTC
from typing import TYPE_CHECKING

from plantation_model.domain.models.regional_weather import RegionalWeather, WeatherObservation
from pymongo import ASCENDING, DESCENDING

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# TTL for weather data in seconds (90 days)
WEATHER_TTL_SECONDS = 90 * 24 * 60 * 60


class RegionalWeatherRepository:
    """Repository for RegionalWeather entities.

    Weather observations are stored with a composite key (region_id, date).
    TTL is managed via MongoDB TTL index on created_at field (90 days).
    """

    COLLECTION_NAME = "regional_weather"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the regional weather repository.

        Args:
            db: MongoDB database instance.
        """
        self._db = db
        self._collection: AsyncIOMotorCollection = db[self.COLLECTION_NAME]

    async def upsert_observation(
        self,
        region_id: str,
        observation_date: dt.date,
        observation: WeatherObservation,
        source: str = "open-meteo",
    ) -> RegionalWeather:
        """Upsert a weather observation for a region on a specific date.

        Args:
            region_id: The region's unique identifier.
            observation_date: The date of the observation.
            observation: The weather observation data.
            source: The data source (default: open-meteo).

        Returns:
            The upserted RegionalWeather entity.
        """
        # Create composite key
        composite_id = f"{region_id}_{observation_date.isoformat()}"

        # Build the document
        now = dt.datetime.now(UTC)
        doc = {
            "_id": composite_id,
            "region_id": region_id,
            "date": observation_date.isoformat(),
            "temp_min": observation.temp_min,
            "temp_max": observation.temp_max,
            "precipitation_mm": observation.precipitation_mm,
            "humidity_avg": observation.humidity_avg,
            "source": source,
            "created_at": now,
        }

        # Upsert the document
        await self._collection.update_one(
            {"_id": composite_id},
            {"$set": doc},
            upsert=True,
        )

        logger.debug("Upserted weather observation for %s on %s", region_id, observation_date)

        return RegionalWeather(
            region_id=region_id,
            date=observation_date,
            temp_min=observation.temp_min,
            temp_max=observation.temp_max,
            precipitation_mm=observation.precipitation_mm,
            humidity_avg=observation.humidity_avg,
            source=source,
            created_at=now,
        )

    async def get_weather_history(
        self,
        region_id: str,
        days: int = 7,
    ) -> list[RegionalWeather]:
        """Get weather history for a region.

        Args:
            region_id: The region's unique identifier.
            days: Number of days of history to return (default: 7).

        Returns:
            List of RegionalWeather entities ordered by date descending.
        """
        # Calculate the start date
        today = dt.date.today()
        start_date = today - dt.timedelta(days=days)

        # Query for observations within the date range
        cursor = (
            self._collection.find(
                {
                    "region_id": region_id,
                    "date": {"$gte": start_date.isoformat()},
                }
            )
            .sort("date", DESCENDING)
            .limit(days)
        )

        docs = await cursor.to_list(length=days)

        # Convert to models
        results = []
        for doc in docs:
            doc.pop("_id", None)
            # Parse date string back to date object
            if isinstance(doc.get("date"), str):
                doc["date"] = dt.date.fromisoformat(doc["date"])
            results.append(RegionalWeather.model_validate(doc))

        return results

    async def get_observation(
        self,
        region_id: str,
        observation_date: dt.date,
    ) -> RegionalWeather | None:
        """Get a specific weather observation.

        Args:
            region_id: The region's unique identifier.
            observation_date: The date of the observation.

        Returns:
            The RegionalWeather if found, None otherwise.
        """
        composite_id = f"{region_id}_{observation_date.isoformat()}"
        doc = await self._collection.find_one({"_id": composite_id})

        if doc is None:
            return None

        doc.pop("_id", None)
        # Parse date string back to date object
        if isinstance(doc.get("date"), str):
            doc["date"] = dt.date.fromisoformat(doc["date"])
        return RegionalWeather.model_validate(doc)

    async def delete_observation(
        self,
        region_id: str,
        observation_date: dt.date,
    ) -> bool:
        """Delete a specific weather observation.

        Args:
            region_id: The region's unique identifier.
            observation_date: The date of the observation.

        Returns:
            True if deleted, False if not found.
        """
        composite_id = f"{region_id}_{observation_date.isoformat()}"
        result = await self._collection.delete_one({"_id": composite_id})
        return result.deleted_count > 0

    async def count_observations(self, region_id: str) -> int:
        """Count observations for a region.

        Args:
            region_id: The region's unique identifier.

        Returns:
            Number of observations stored for the region.
        """
        return await self._collection.count_documents({"region_id": region_id})

    async def ensure_indexes(self) -> None:
        """Create indexes for the regional_weather collection."""
        # Compound index for region_id + date queries
        await self._collection.create_index(
            [("region_id", ASCENDING), ("date", DESCENDING)],
            name="idx_region_date",
        )

        # TTL index for automatic expiration (90 days)
        await self._collection.create_index(
            [("created_at", ASCENDING)],
            name="idx_ttl",
            expireAfterSeconds=WEATHER_TTL_SECONDS,
        )

        logger.info("RegionalWeather indexes created")
