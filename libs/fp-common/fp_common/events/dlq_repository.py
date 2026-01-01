"""Dead Letter Queue MongoDB Repository.

Story 0.6.8: Dead Letter Queue Handler (ADR-006)

This module provides MongoDB storage for dead-lettered events,
enabling inspection, replay, and tracking of failed event processing.

Schema:
    event_dead_letter collection:
    - event: Original event payload
    - original_topic: Topic the event was published to
    - received_at: Timestamp when DLQ received the event
    - status: pending_review | replayed | discarded
    - replayed_at: Timestamp if replayed
    - discard_reason: Reason if discarded
"""

from datetime import UTC, datetime
from typing import Any, Literal

from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import BaseModel, Field

# Type-safe status values
DLQStatus = Literal["pending_review", "replayed", "discarded"]


class DLQRecord(BaseModel):
    """Pydantic model for DLQ MongoDB documents.

    This model is used for both creating and querying DLQ records,
    following the project convention of using Pydantic models over raw dicts.
    """

    event: dict[str, Any] = Field(description="Original event payload")
    original_topic: str = Field(description="Topic the event was published to")
    received_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when DLQ received the event",
    )
    status: DLQStatus = Field(
        default="pending_review",
        description="Status: pending_review | replayed | discarded",
    )
    replayed_at: datetime | None = Field(
        default=None,
        description="Timestamp if event was replayed",
    )
    discard_reason: str | None = Field(
        default=None,
        description="Reason if event was discarded",
    )


class DLQRepository:
    """Repository for dead letter queue events.

    Provides CRUD operations for the event_dead_letter MongoDB collection.
    All methods are async to comply with project requirements.

    Usage:
        repo = DLQRepository(mongodb_collection)
        doc_id = await repo.store_failed_event(
            event_data={"document_id": "doc-123"},
            original_topic="collection.quality_result.received",
        )
    """

    def __init__(self, collection: AsyncIOMotorCollection):
        """Initialize the DLQ repository.

        Args:
            collection: Motor async MongoDB collection for event_dead_letter.
        """
        self._collection = collection

    async def store_failed_event(
        self,
        event_data: dict[str, Any],
        original_topic: str,
    ) -> str:
        """Store a failed event in the DLQ collection.

        Creates a new DLQ record with status "pending_review".

        Args:
            event_data: Original event payload that failed processing.
            original_topic: Topic the event was published to.

        Returns:
            The inserted document's string ID.
        """
        record = DLQRecord(
            event=event_data,
            original_topic=original_topic,
            received_at=datetime.now(UTC),
            status="pending_review",
        )

        result = await self._collection.insert_one(record.model_dump())
        return str(result.inserted_id)

    async def mark_replayed(self, document_id: str) -> bool:
        """Mark an event as replayed.

        Args:
            document_id: The document ID to update.

        Returns:
            True if document was updated, False if not found.
        """
        from bson import ObjectId

        result = await self._collection.update_one(
            {"_id": ObjectId(document_id)},
            {
                "$set": {
                    "status": "replayed",
                    "replayed_at": datetime.now(UTC),
                }
            },
        )
        return result.modified_count > 0

    async def mark_discarded(self, document_id: str, reason: str) -> bool:
        """Mark an event as discarded with reason.

        Args:
            document_id: The document ID to update.
            reason: The reason for discarding the event.

        Returns:
            True if document was updated, False if not found.
        """
        from bson import ObjectId

        result = await self._collection.update_one(
            {"_id": ObjectId(document_id)},
            {
                "$set": {
                    "status": "discarded",
                    "discard_reason": reason,
                }
            },
        )
        return result.modified_count > 0

    async def get_pending_events(
        self,
        limit: int = 100,
        topic_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get pending events for review.

        Args:
            limit: Maximum number of events to return.
            topic_filter: Optional filter by original_topic.

        Returns:
            List of pending DLQ records as dicts.
        """
        query: dict[str, Any] = {"status": "pending_review"}
        if topic_filter:
            query["original_topic"] = topic_filter

        cursor = self._collection.find(query).sort("received_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def count_by_status(self) -> dict[str, int]:
        """Count events by status.

        Returns:
            Dict mapping status to count.
        """
        pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]
        counts: dict[str, int] = {}
        async for doc in self._collection.aggregate(pipeline):
            counts[doc["_id"]] = doc["count"]
        return counts

    async def ensure_indexes(self) -> None:
        """Create indexes for efficient DLQ queries.

        Creates indexes on:
        - original_topic: For filtering by source topic
        - status: For filtering pending vs replayed/discarded
        - received_at: For sorting by newest first (descending)
        """
        await self._collection.create_index("original_topic")
        await self._collection.create_index("status")
        await self._collection.create_index([("received_at", -1)])
