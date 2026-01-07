"""Embedding Cost Event Repository for MongoDB persistence.

This module provides the repository for storing and querying embedding cost events.
It supports:
- Event insertion with automatic index creation
- Querying by knowledge domain for attribution
- Basic cost summaries for embedding operations

Note: Unlike LlmCostEventRepository, this repository does not track USD costs
because Pinecone Inference API embedding is included in index pricing.

Story 0.75.12: RAG Embedding Configuration (Pinecone Inference)
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any

import structlog
from ai_model.domain.embedding import EmbeddingCostEvent
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel

logger = structlog.get_logger(__name__)

# Collection name for embedding cost events
COLLECTION_NAME = "embedding_cost_events"


class EmbeddingCostEventRepository:
    """Repository for embedding cost event persistence and querying.

    This repository follows the same pattern as LlmCostEventRepository
    but without USD cost tracking (Pinecone Inference is included in index pricing).
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the repository.

        Args:
            db: MongoDB database instance.
        """
        self._db = db
        self._collection = db[COLLECTION_NAME]

    async def ensure_indexes(self) -> None:
        """Create indexes for efficient querying.

        Indexes are created for:
        - timestamp (descending) for recent events
        - model for grouping by model
        - knowledge_domain for per-domain attribution
        - Compound index on (timestamp, knowledge_domain)
        """
        indexes = [
            IndexModel([("timestamp", DESCENDING)], name="idx_timestamp"),
            IndexModel([("model", ASCENDING)], name="idx_model"),
            IndexModel(
                [("knowledge_domain", ASCENDING)],
                name="idx_knowledge_domain",
                sparse=True,  # Only index documents with knowledge_domain
            ),
            IndexModel(
                [("timestamp", DESCENDING), ("knowledge_domain", ASCENDING)],
                name="idx_timestamp_domain",
            ),
            IndexModel(
                [("request_id", ASCENDING)],
                name="idx_request_id",
            ),
        ]

        try:
            await self._collection.create_indexes(indexes)
            logger.info("Embedding cost event indexes created", collection=COLLECTION_NAME)
        except Exception as e:
            logger.warning(
                "Failed to create some indexes",
                collection=COLLECTION_NAME,
                error=str(e),
            )

    async def insert(self, event: EmbeddingCostEvent) -> str:
        """Insert a new embedding cost event.

        Args:
            event: The cost event to insert.

        Returns:
            The event ID.
        """
        doc = event.model_dump_for_mongo()
        doc["_id"] = event.id
        await self._collection.insert_one(doc)
        logger.debug(
            "Embedding cost event inserted",
            event_id=event.id,
            model=event.model,
            texts_count=event.texts_count,
            tokens_total=event.tokens_total,
        )
        return event.id

    async def get_by_id(self, event_id: str) -> EmbeddingCostEvent | None:
        """Get an embedding cost event by ID.

        Args:
            event_id: The event's unique identifier.

        Returns:
            The cost event if found, None otherwise.
        """
        doc = await self._collection.find_one({"_id": event_id})
        if doc is None:
            return None
        return EmbeddingCostEvent.from_mongo(doc)

    async def get_by_request_id(self, request_id: str) -> list[EmbeddingCostEvent]:
        """Get all embedding cost events for a request ID.

        Args:
            request_id: The correlation ID to search for.

        Returns:
            List of matching cost events.
        """
        cursor = self._collection.find({"request_id": request_id})
        events = []
        async for doc in cursor:
            events.append(EmbeddingCostEvent.from_mongo(doc))
        return events

    async def get_daily_summary(
        self,
        target_date: date,
        knowledge_domain: str | None = None,
    ) -> dict[str, Any]:
        """Get embedding usage summary for a specific date.

        Args:
            target_date: The date to get summary for.
            knowledge_domain: Optional domain filter.

        Returns:
            Summary dict with total_texts, total_tokens, total_requests, success_count, failure_count.
        """
        start = datetime.combine(target_date, datetime.min.time(), tzinfo=UTC)
        end = start + timedelta(days=1)

        match_filter: dict[str, Any] = {
            "timestamp": {"$gte": start, "$lt": end},
        }
        if knowledge_domain:
            match_filter["knowledge_domain"] = knowledge_domain

        pipeline: list[dict[str, Any]] = [
            {"$match": match_filter},
            {
                "$group": {
                    "_id": None,
                    "total_texts": {"$sum": "$texts_count"},
                    "total_tokens": {"$sum": "$tokens_total"},
                    "total_requests": {"$sum": 1},
                    "success_count": {"$sum": {"$cond": [{"$eq": ["$success", True]}, 1, 0]}},
                    "failure_count": {"$sum": {"$cond": [{"$eq": ["$success", False]}, 1, 0]}},
                    "total_batches": {"$sum": "$batch_count"},
                }
            },
        ]

        cursor = self._collection.aggregate(pipeline)
        results = await cursor.to_list(length=1)

        if not results:
            return {
                "date": target_date.isoformat(),
                "total_texts": 0,
                "total_tokens": 0,
                "total_requests": 0,
                "success_count": 0,
                "failure_count": 0,
                "total_batches": 0,
            }

        result = results[0]
        return {
            "date": target_date.isoformat(),
            "total_texts": result.get("total_texts", 0),
            "total_tokens": result.get("total_tokens", 0),
            "total_requests": result.get("total_requests", 0),
            "success_count": result.get("success_count", 0),
            "failure_count": result.get("failure_count", 0),
            "total_batches": result.get("total_batches", 0),
        }

    async def get_summary_by_domain(
        self,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Get embedding usage summary grouped by knowledge domain.

        Args:
            start_date: Start of the date range (inclusive).
            end_date: End of the date range (inclusive).

        Returns:
            List of summary dicts grouped by knowledge_domain.
        """
        start = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
        end = datetime.combine(end_date, datetime.min.time(), tzinfo=UTC) + timedelta(days=1)

        pipeline: list[dict[str, Any]] = [
            {
                "$match": {
                    "timestamp": {"$gte": start, "$lt": end},
                }
            },
            {
                "$group": {
                    "_id": "$knowledge_domain",
                    "total_texts": {"$sum": "$texts_count"},
                    "total_tokens": {"$sum": "$tokens_total"},
                    "total_requests": {"$sum": 1},
                }
            },
            {"$sort": {"total_tokens": -1}},
        ]

        cursor = self._collection.aggregate(pipeline)
        results = await cursor.to_list(length=100)

        return [
            {
                "knowledge_domain": result["_id"] or "unattributed",
                "total_texts": result.get("total_texts", 0),
                "total_tokens": result.get("total_tokens", 0),
                "total_requests": result.get("total_requests", 0),
            }
            for result in results
        ]
