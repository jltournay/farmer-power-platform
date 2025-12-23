"""Base repository class with common CRUD operations."""

import logging
from datetime import datetime, timezone
from typing import Generic, Optional, TypeVar

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class BaseRepository(Generic[T]):
    """Base repository providing common CRUD operations.

    All repository methods are async to comply with the project requirement
    that ALL I/O operations MUST be async.
    """

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        collection_name: str,
        model_class: type[T],
    ) -> None:
        """Initialize the repository.

        Args:
            db: MongoDB database instance.
            collection_name: Name of the collection.
            model_class: Pydantic model class for deserialization.
        """
        self._db = db
        self._collection: AsyncIOMotorCollection = db[collection_name]
        self._model_class = model_class

    async def create(self, entity: T) -> T:
        """Create a new entity.

        Args:
            entity: The entity to create.

        Returns:
            The created entity.
        """
        doc = entity.model_dump()
        doc["_id"] = doc["id"]  # Use id as MongoDB _id
        await self._collection.insert_one(doc)
        logger.debug("Created %s with id %s", self._model_class.__name__, doc["id"])
        return entity

    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get an entity by its ID.

        Args:
            entity_id: The entity's unique identifier.

        Returns:
            The entity if found, None otherwise.
        """
        doc = await self._collection.find_one({"_id": entity_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return self._model_class.model_validate(doc)

    async def update(self, entity_id: str, updates: dict) -> Optional[T]:
        """Update an entity.

        Args:
            entity_id: The entity's unique identifier.
            updates: Dictionary of fields to update.

        Returns:
            The updated entity if found, None otherwise.
        """
        # Add updated_at timestamp
        updates["updated_at"] = datetime.now(timezone.utc)

        result = await self._collection.find_one_and_update(
            {"_id": entity_id},
            {"$set": updates},
            return_document=True,
        )
        if result is None:
            return None
        result.pop("_id", None)
        return self._model_class.model_validate(result)

    async def delete(self, entity_id: str) -> bool:
        """Delete an entity.

        Args:
            entity_id: The entity's unique identifier.

        Returns:
            True if deleted, False if not found.
        """
        result = await self._collection.delete_one({"_id": entity_id})
        return result.deleted_count > 0

    async def list(
        self,
        filters: Optional[dict] = None,
        page_size: int = 100,
        page_token: Optional[str] = None,
    ) -> tuple[list[T], Optional[str], int]:
        """List entities with optional filtering and pagination.

        Args:
            filters: Optional filter criteria.
            page_size: Number of results per page.
            page_token: Token for the next page (entity ID).

        Returns:
            Tuple of (entities, next_page_token, total_count).
        """
        query = filters or {}

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
        entities = []
        for doc in docs:
            doc.pop("_id", None)
            entities.append(self._model_class.model_validate(doc))

        return entities, next_page_token, total_count

    async def ensure_indexes(self) -> None:
        """Create indexes for the collection.

        Override in subclasses to add specific indexes.
        """
        pass
