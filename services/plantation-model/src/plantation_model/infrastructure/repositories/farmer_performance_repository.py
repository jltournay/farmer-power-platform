"""FarmerPerformance repository for MongoDB persistence."""

import datetime as dt
import logging
from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING

from plantation_model.domain.models.farmer import FarmScale
from plantation_model.domain.models.farmer_performance import (
    FarmerPerformance,
    HistoricalMetrics,
    TodayMetrics,
)
from plantation_model.infrastructure.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class FarmerPerformanceRepository(BaseRepository[FarmerPerformance]):
    """Repository for FarmerPerformance entities.

    Provides CRUD operations plus specialized queries:
    - get_by_farmer_id: Get performance by farmer ID
    - initialize_for_farmer: Create default performance for new farmer
    - update_historical: Update historical metrics (batch job)
    - update_today: Update today's metrics (streaming events)
    - increment_today_delivery: Atomically increment today's delivery count
    - reset_today: Reset today's metrics for a new day
    - list_by_grading_model: List performances using a specific grading model
    """

    COLLECTION_NAME = "farmer_performances"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the farmer performance repository.

        Args:
            db: MongoDB database instance.
        """
        super().__init__(db, self.COLLECTION_NAME, FarmerPerformance)

    async def create(self, entity: FarmerPerformance) -> FarmerPerformance:
        """Create a new farmer performance record.

        Uses farmer_id as the MongoDB _id.

        Args:
            entity: The farmer performance to create.

        Returns:
            The created farmer performance.
        """
        doc = entity.model_dump()
        doc["_id"] = doc["farmer_id"]
        await self._collection.insert_one(doc)
        logger.debug("Created farmer performance for %s", entity.farmer_id)
        return entity

    async def get_by_farmer_id(self, farmer_id: str) -> Optional[FarmerPerformance]:
        """Get a farmer performance by farmer ID.

        Args:
            farmer_id: The farmer's unique identifier.

        Returns:
            The farmer performance if found, None otherwise.
        """
        doc = await self._collection.find_one({"_id": farmer_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return FarmerPerformance.model_validate(doc)

    async def initialize_for_farmer(
        self,
        farmer_id: str,
        farm_size_hectares: float,
        farm_scale: FarmScale,
        grading_model_id: str,
        grading_model_version: str,
    ) -> FarmerPerformance:
        """Create default performance record for a new farmer.

        Called when a farmer is registered to initialize their performance
        tracking with the factory's assigned grading model.

        Args:
            farmer_id: The farmer's unique identifier.
            farm_size_hectares: Farm size for yield calculations.
            farm_scale: Farm scale classification.
            grading_model_id: The grading model assigned to the farmer's factory.
            grading_model_version: Version of the grading model.

        Returns:
            A new FarmerPerformance with default empty metrics.
        """
        performance = FarmerPerformance.initialize_for_farmer(
            farmer_id=farmer_id,
            farm_size_hectares=farm_size_hectares,
            farm_scale=farm_scale,
            grading_model_id=grading_model_id,
            grading_model_version=grading_model_version,
        )
        await self.create(performance)
        return performance

    async def update_historical(
        self, farmer_id: str, historical: HistoricalMetrics
    ) -> Optional[FarmerPerformance]:
        """Update the historical metrics for a farmer.

        Called by batch jobs that aggregate quality events.

        Args:
            farmer_id: The farmer's unique identifier.
            historical: The updated historical metrics.

        Returns:
            The updated farmer performance if found, None otherwise.
        """
        result = await self._collection.find_one_and_update(
            {"_id": farmer_id},
            {
                "$set": {
                    "historical": historical.model_dump(),
                    "updated_at": datetime.now(timezone.utc),
                },
            },
            return_document=True,
        )
        if result is None:
            return None
        result.pop("_id", None)
        logger.debug("Updated historical metrics for farmer %s", farmer_id)
        return FarmerPerformance.model_validate(result)

    async def update_today(
        self, farmer_id: str, today: TodayMetrics
    ) -> Optional[FarmerPerformance]:
        """Update today's metrics for a farmer.

        Args:
            farmer_id: The farmer's unique identifier.
            today: The updated today metrics.

        Returns:
            The updated farmer performance if found, None otherwise.
        """
        result = await self._collection.find_one_and_update(
            {"_id": farmer_id},
            {
                "$set": {
                    "today": today.model_dump(),
                    "updated_at": datetime.now(timezone.utc),
                },
            },
            return_document=True,
        )
        if result is None:
            return None
        result.pop("_id", None)
        logger.debug("Updated today metrics for farmer %s", farmer_id)
        return FarmerPerformance.model_validate(result)

    async def increment_today_delivery(
        self,
        farmer_id: str,
        kg_amount: float,
        grade: str,
        attribute_counts: Optional[dict[str, dict[str, int]]] = None,
    ) -> Optional[FarmerPerformance]:
        """Atomically increment today's delivery metrics.

        Called when a new quality event arrives for a farmer.

        Args:
            farmer_id: The farmer's unique identifier.
            kg_amount: Weight of the delivery in kg.
            grade: The grade assigned to the delivery.
            attribute_counts: Optional attribute class counts.

        Returns:
            The updated farmer performance if found, None otherwise.
        """
        now = datetime.now(timezone.utc)
        today_str = dt.date.today().isoformat()

        # Build atomic update
        update: dict = {
            "$inc": {
                "today.deliveries": 1,
                "today.total_kg": kg_amount,
                f"today.grade_counts.{grade}": 1,
            },
            "$set": {
                "today.last_delivery": now,
                "today.metrics_date": today_str,
                "updated_at": now,
            },
        }

        # Add attribute count increments if provided
        if attribute_counts:
            for attr_name, class_counts in attribute_counts.items():
                for class_name, count in class_counts.items():
                    update["$inc"][
                        f"today.attribute_counts.{attr_name}.counts.{class_name}"
                    ] = count

        result = await self._collection.find_one_and_update(
            {"_id": farmer_id},
            update,
            return_document=True,
        )
        if result is None:
            return None
        result.pop("_id", None)
        logger.debug(
            "Incremented today delivery for farmer %s: +%.1f kg, grade=%s",
            farmer_id,
            kg_amount,
            grade,
        )
        return FarmerPerformance.model_validate(result)

    async def reset_today(self, farmer_id: str) -> Optional[FarmerPerformance]:
        """Reset today's metrics for a new day.

        Called when the date changes or at the start of each day.

        Args:
            farmer_id: The farmer's unique identifier.

        Returns:
            The updated farmer performance if found, None otherwise.
        """
        today_str = dt.date.today().isoformat()

        result = await self._collection.find_one_and_update(
            {"_id": farmer_id},
            {
                "$set": {
                    "today": {
                        "deliveries": 0,
                        "total_kg": 0.0,
                        "grade_counts": {},
                        "attribute_counts": {},
                        "last_delivery": None,
                        "metrics_date": today_str,
                    },
                    "updated_at": datetime.now(timezone.utc),
                },
            },
            return_document=True,
        )
        if result is None:
            return None
        result.pop("_id", None)
        logger.debug("Reset today metrics for farmer %s", farmer_id)
        return FarmerPerformance.model_validate(result)

    async def list_by_grading_model(
        self,
        grading_model_id: str,
        page_size: int = 100,
        page_token: Optional[str] = None,
    ) -> tuple[list[FarmerPerformance], Optional[str], int]:
        """List farmer performances using a specific grading model.

        Args:
            grading_model_id: The grading model identifier.
            page_size: Number of results per page.
            page_token: Token for the next page.

        Returns:
            Tuple of (performances, next_page_token, total_count).
        """
        query = {"grading_model_id": grading_model_id}

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
        performances = []
        for doc in docs:
            doc.pop("_id", None)
            performances.append(FarmerPerformance.model_validate(doc))

        return performances, next_page_token, total_count

    async def ensure_indexes(self) -> None:
        """Create indexes for the farmer_performances collection.

        Indexes:
        - farmer_id (unique): Primary key lookup
        - grading_model_id: List by grading model
        - farm_scale: Filter by farm scale
        - historical.improvement_trend: Filter by trend
        """
        await self._collection.create_index(
            [("farmer_id", ASCENDING)],
            unique=True,
            name="idx_farmer_perf_farmer_id",
        )
        await self._collection.create_index(
            [("grading_model_id", ASCENDING)],
            name="idx_farmer_perf_grading_model",
        )
        await self._collection.create_index(
            [("farm_scale", ASCENDING)],
            name="idx_farmer_perf_farm_scale",
        )
        await self._collection.create_index(
            [("historical.improvement_trend", ASCENDING)],
            name="idx_farmer_perf_trend",
        )
        logger.info("Farmer performance indexes created")
