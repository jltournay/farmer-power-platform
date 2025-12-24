"""GradingModel repository for MongoDB persistence."""

import logging
from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING

from plantation_model.domain.models.grading_model import GradingModel
from plantation_model.infrastructure.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class GradingModelRepository(BaseRepository[GradingModel]):
    """Repository for GradingModel entities.

    Provides CRUD operations plus specialized queries:
    - get_by_factory: Get grading model assigned to a factory
    - add_factory_assignment: Assign model to a factory
    - remove_factory_assignment: Remove factory from model's assignments
    """

    COLLECTION_NAME = "grading_models"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the grading model repository.

        Args:
            db: MongoDB database instance.
        """
        super().__init__(db, self.COLLECTION_NAME, GradingModel)

    async def create(self, entity: GradingModel) -> GradingModel:
        """Create a new grading model.

        Uses model_id as the MongoDB _id.

        Args:
            entity: The grading model to create.

        Returns:
            The created grading model.
        """
        doc = entity.model_dump()
        doc["_id"] = doc["model_id"]
        await self._collection.insert_one(doc)
        logger.debug("Created grading model %s", entity.model_id)
        return entity

    async def get_by_id(self, model_id: str) -> Optional[GradingModel]:
        """Get a grading model by its ID.

        Args:
            model_id: The grading model's unique identifier.

        Returns:
            The grading model if found, None otherwise.
        """
        doc = await self._collection.find_one({"_id": model_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return GradingModel.model_validate(doc)

    async def get_by_factory(self, factory_id: str) -> Optional[GradingModel]:
        """Get the grading model assigned to a factory.

        A factory can have only one active grading model.

        Args:
            factory_id: The factory's unique identifier.

        Returns:
            The grading model if found, None otherwise.
        """
        doc = await self._collection.find_one({"active_at_factory": factory_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return GradingModel.model_validate(doc)

    async def add_factory_assignment(
        self, model_id: str, factory_id: str
    ) -> Optional[GradingModel]:
        """Assign a grading model to a factory.

        Adds the factory_id to the model's active_at_factory list.

        Args:
            model_id: The grading model's unique identifier.
            factory_id: The factory to assign.

        Returns:
            The updated grading model if found, None otherwise.
        """
        result = await self._collection.find_one_and_update(
            {"_id": model_id},
            {
                "$addToSet": {"active_at_factory": factory_id},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
            return_document=True,
        )
        if result is None:
            return None
        result.pop("_id", None)
        logger.info("Assigned grading model %s to factory %s", model_id, factory_id)
        return GradingModel.model_validate(result)

    async def remove_factory_assignment(
        self, model_id: str, factory_id: str
    ) -> Optional[GradingModel]:
        """Remove a factory assignment from a grading model.

        Removes the factory_id from the model's active_at_factory list.

        Args:
            model_id: The grading model's unique identifier.
            factory_id: The factory to remove.

        Returns:
            The updated grading model if found, None otherwise.
        """
        result = await self._collection.find_one_and_update(
            {"_id": model_id},
            {
                "$pull": {"active_at_factory": factory_id},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
            return_document=True,
        )
        if result is None:
            return None
        result.pop("_id", None)
        logger.info(
            "Removed factory %s from grading model %s", factory_id, model_id
        )
        return GradingModel.model_validate(result)

    async def ensure_indexes(self) -> None:
        """Create indexes for the grading_models collection.

        Indexes:
        - model_id (unique): Primary key lookup
        - active_at_factory: Find grading model by factory
        - market_name: Filter by market
        - grading_type: Filter by grading type
        """
        await self._collection.create_index(
            [("model_id", ASCENDING)],
            unique=True,
            name="idx_grading_model_id",
        )
        await self._collection.create_index(
            [("active_at_factory", ASCENDING)],
            name="idx_grading_model_factory",
        )
        await self._collection.create_index(
            [("market_name", ASCENDING)],
            name="idx_grading_model_market",
        )
        await self._collection.create_index(
            [("grading_type", ASCENDING)],
            name="idx_grading_model_type",
        )
        logger.info("Grading model indexes created")
