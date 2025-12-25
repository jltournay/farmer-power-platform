"""GradingModel repository for MongoDB persistence."""

import logging
from datetime import UTC, datetime

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

    async def get_by_id(self, model_id: str) -> GradingModel | None:
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

    async def get_by_factory(self, factory_id: str) -> GradingModel | None:
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
    ) -> GradingModel | None:
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
                "$set": {"updated_at": datetime.now(UTC)},
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
    ) -> GradingModel | None:
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
                "$set": {"updated_at": datetime.now(UTC)},
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

    async def update(
        self, model_id: str, updates: dict
    ) -> GradingModel | None:
        """Update a grading model.

        Updates the specified fields in the grading model.

        Args:
            model_id: The grading model's unique identifier.
            updates: Dictionary of fields to update.

        Returns:
            The updated grading model if found, None otherwise.
        """
        if not updates:
            return await self.get_by_id(model_id)

        updates["updated_at"] = datetime.now(UTC)
        result = await self._collection.find_one_and_update(
            {"_id": model_id},
            {"$set": updates},
            return_document=True,
        )
        if result is None:
            return None
        result.pop("_id", None)
        logger.info("Updated grading model %s", model_id)
        return GradingModel.model_validate(result)

    async def list_all(
        self,
        page_size: int = 100,
        page_token: str | None = None,
        filters: dict | None = None,
    ) -> tuple[list[GradingModel], str | None, int]:
        """List all grading models with optional filtering.

        Args:
            page_size: Number of results per page.
            page_token: Token for the next page.
            filters: Optional filters (e.g., {"market_name": "Kenya_TBK"}).

        Returns:
            Tuple of (grading_models, next_page_token, total_count).
        """
        query = filters.copy() if filters else {}

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
        models = []
        for doc in docs:
            doc.pop("_id", None)
            models.append(GradingModel.model_validate(doc))

        return models, next_page_token, total_count

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
