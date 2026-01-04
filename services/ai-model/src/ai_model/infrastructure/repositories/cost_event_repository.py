"""LLM Cost Event Repository for MongoDB persistence.

This module provides the repository for storing and querying LLM cost events.
It supports:
- Event insertion with automatic index creation
- Daily and monthly cost summaries
- Cost breakdown by agent type and model
- Current day cost tracking for budget alerts

Story 0.75.5: OpenRouter LLM Gateway with Cost Observability
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import structlog
from ai_model.domain.cost_event import (
    AgentTypeCost,
    CostSummary,
    DailyCostSummary,
    LlmCostEvent,
    ModelCost,
)
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel

logger = structlog.get_logger(__name__)

# Collection name for cost events
COLLECTION_NAME = "llm_cost_events"


class LlmCostEventRepository:
    """Repository for LLM cost event persistence and querying.

    This repository follows the same pattern as PromptRepository and
    AgentConfigRepository, but with specialized aggregation queries
    for cost reporting.
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
        - agent_type for grouping by agent
        - model for grouping by model
        - factory_id for per-factory attribution
        - Compound index on (timestamp, agent_type) for daily breakdowns
        """
        indexes = [
            IndexModel([("timestamp", DESCENDING)], name="idx_timestamp"),
            IndexModel([("agent_type", ASCENDING)], name="idx_agent_type"),
            IndexModel([("model", ASCENDING)], name="idx_model"),
            IndexModel(
                [("factory_id", ASCENDING)],
                name="idx_factory_id",
                sparse=True,  # Only index documents with factory_id
            ),
            IndexModel(
                [("timestamp", DESCENDING), ("agent_type", ASCENDING)],
                name="idx_timestamp_agent_type",
            ),
            IndexModel(
                [("timestamp", DESCENDING), ("model", ASCENDING)],
                name="idx_timestamp_model",
            ),
        ]

        try:
            await self._collection.create_indexes(indexes)
            logger.info("Cost event indexes created", collection=COLLECTION_NAME)
        except Exception as e:
            logger.warning(
                "Failed to create some indexes",
                collection=COLLECTION_NAME,
                error=str(e),
            )

    async def insert(self, event: LlmCostEvent) -> str:
        """Insert a new cost event.

        Args:
            event: The cost event to insert.

        Returns:
            The event ID.
        """
        doc = event.model_dump_for_mongo()
        doc["_id"] = event.id
        await self._collection.insert_one(doc)
        logger.debug(
            "Cost event inserted",
            event_id=event.id,
            model=event.model,
            cost_usd=str(event.cost_usd),
        )
        return event.id

    async def get_by_id(self, event_id: str) -> LlmCostEvent | None:
        """Get a cost event by ID.

        Args:
            event_id: The event's unique identifier.

        Returns:
            The cost event if found, None otherwise.
        """
        doc = await self._collection.find_one({"_id": event_id})
        if doc is None:
            return None
        return LlmCostEvent.from_mongo(doc)

    async def get_daily_summary(
        self,
        target_date: date,
    ) -> DailyCostSummary:
        """Get cost summary for a specific date.

        Args:
            target_date: The date to get summary for.

        Returns:
            Daily cost summary.
        """
        start = datetime.combine(target_date, datetime.min.time(), tzinfo=UTC)
        end = start + timedelta(days=1)

        pipeline: list[dict[str, Any]] = [
            {
                "$match": {
                    "timestamp": {"$gte": start, "$lt": end},
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_cost_usd": {"$sum": {"$toDecimal": "$cost_usd"}},
                    "total_requests": {"$sum": 1},
                    "total_tokens_in": {"$sum": "$tokens_in"},
                    "total_tokens_out": {"$sum": "$tokens_out"},
                    "success_count": {"$sum": {"$cond": [{"$eq": ["$success", True]}, 1, 0]}},
                    "failure_count": {"$sum": {"$cond": [{"$eq": ["$success", False]}, 1, 0]}},
                }
            },
        ]

        cursor = self._collection.aggregate(pipeline)
        results = await cursor.to_list(length=1)

        if not results:
            return DailyCostSummary(
                date=start,
                total_cost_usd=Decimal("0"),
                total_requests=0,
                total_tokens_in=0,
                total_tokens_out=0,
                success_count=0,
                failure_count=0,
            )

        result = results[0]
        return DailyCostSummary(
            date=start,
            total_cost_usd=Decimal(str(result.get("total_cost_usd", 0))),
            total_requests=result.get("total_requests", 0),
            total_tokens_in=result.get("total_tokens_in", 0),
            total_tokens_out=result.get("total_tokens_out", 0),
            success_count=result.get("success_count", 0),
            failure_count=result.get("failure_count", 0),
        )

    async def get_daily_summaries(
        self,
        start_date: date,
        end_date: date,
    ) -> list[DailyCostSummary]:
        """Get daily cost summaries for a date range.

        Args:
            start_date: Start of the date range (inclusive).
            end_date: End of the date range (inclusive).

        Returns:
            List of daily cost summaries.
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
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$timestamp",
                        }
                    },
                    "total_cost_usd": {"$sum": {"$toDecimal": "$cost_usd"}},
                    "total_requests": {"$sum": 1},
                    "total_tokens_in": {"$sum": "$tokens_in"},
                    "total_tokens_out": {"$sum": "$tokens_out"},
                    "success_count": {"$sum": {"$cond": [{"$eq": ["$success", True]}, 1, 0]}},
                    "failure_count": {"$sum": {"$cond": [{"$eq": ["$success", False]}, 1, 0]}},
                }
            },
            {"$sort": {"_id": 1}},
        ]

        cursor = self._collection.aggregate(pipeline)
        results = await cursor.to_list(length=100)

        summaries = []
        for result in results:
            date_str = result["_id"]
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
            summaries.append(
                DailyCostSummary(
                    date=parsed_date,
                    total_cost_usd=Decimal(str(result.get("total_cost_usd", 0))),
                    total_requests=result.get("total_requests", 0),
                    total_tokens_in=result.get("total_tokens_in", 0),
                    total_tokens_out=result.get("total_tokens_out", 0),
                    success_count=result.get("success_count", 0),
                    failure_count=result.get("failure_count", 0),
                )
            )

        return summaries

    async def get_cost_by_agent_type(
        self,
        start_date: date,
        end_date: date,
    ) -> list[AgentTypeCost]:
        """Get cost breakdown by agent type for a date range.

        Args:
            start_date: Start of the date range (inclusive).
            end_date: End of the date range (inclusive).

        Returns:
            List of cost summaries grouped by agent type.
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
                    "_id": "$agent_type",
                    "total_cost_usd": {"$sum": {"$toDecimal": "$cost_usd"}},
                    "total_requests": {"$sum": 1},
                    "total_tokens": {"$sum": {"$add": ["$tokens_in", "$tokens_out"]}},
                }
            },
            {"$sort": {"total_cost_usd": -1}},
        ]

        cursor = self._collection.aggregate(pipeline)
        results = await cursor.to_list(length=100)

        return [
            AgentTypeCost(
                agent_type=result["_id"],
                total_cost_usd=Decimal(str(result.get("total_cost_usd", 0))),
                total_requests=result.get("total_requests", 0),
                total_tokens=result.get("total_tokens", 0),
            )
            for result in results
        ]

    async def get_cost_by_model(
        self,
        start_date: date,
        end_date: date,
    ) -> list[ModelCost]:
        """Get cost breakdown by model for a date range.

        Args:
            start_date: Start of the date range (inclusive).
            end_date: End of the date range (inclusive).

        Returns:
            List of cost summaries grouped by model.
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
                    "_id": "$model",
                    "total_cost_usd": {"$sum": {"$toDecimal": "$cost_usd"}},
                    "total_requests": {"$sum": 1},
                    "total_tokens": {"$sum": {"$add": ["$tokens_in", "$tokens_out"]}},
                }
            },
            {"$sort": {"total_cost_usd": -1}},
        ]

        cursor = self._collection.aggregate(pipeline)
        results = await cursor.to_list(length=100)

        return [
            ModelCost(
                model=result["_id"],
                total_cost_usd=Decimal(str(result.get("total_cost_usd", 0))),
                total_requests=result.get("total_requests", 0),
                total_tokens=result.get("total_tokens", 0),
            )
            for result in results
        ]

    async def get_current_day_cost(self) -> CostSummary:
        """Get the current day's running cost total.

        This is used for real-time budget monitoring and alerting.

        Returns:
            Current day cost summary.
        """
        today = date.today()
        start = datetime.combine(today, datetime.min.time(), tzinfo=UTC)
        now = datetime.now(UTC)

        pipeline: list[dict[str, Any]] = [
            {
                "$match": {
                    "timestamp": {"$gte": start, "$lte": now},
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_cost_usd": {"$sum": {"$toDecimal": "$cost_usd"}},
                    "total_requests": {"$sum": 1},
                    "total_tokens_in": {"$sum": "$tokens_in"},
                    "total_tokens_out": {"$sum": "$tokens_out"},
                }
            },
        ]

        cursor = self._collection.aggregate(pipeline)
        results = await cursor.to_list(length=1)

        if not results:
            return CostSummary(
                total_cost_usd=Decimal("0"),
                total_requests=0,
                total_tokens_in=0,
                total_tokens_out=0,
            )

        result = results[0]
        return CostSummary(
            total_cost_usd=Decimal(str(result.get("total_cost_usd", 0))),
            total_requests=result.get("total_requests", 0),
            total_tokens_in=result.get("total_tokens_in", 0),
            total_tokens_out=result.get("total_tokens_out", 0),
        )

    async def get_current_month_cost(self) -> CostSummary:
        """Get the current month's running cost total.

        This is used for monthly budget monitoring and alerting.

        Returns:
            Current month cost summary.
        """
        today = date.today()
        start_of_month = datetime(today.year, today.month, 1, tzinfo=UTC)
        now = datetime.now(UTC)

        pipeline: list[dict[str, Any]] = [
            {
                "$match": {
                    "timestamp": {"$gte": start_of_month, "$lte": now},
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_cost_usd": {"$sum": {"$toDecimal": "$cost_usd"}},
                    "total_requests": {"$sum": 1},
                    "total_tokens_in": {"$sum": "$tokens_in"},
                    "total_tokens_out": {"$sum": "$tokens_out"},
                }
            },
        ]

        cursor = self._collection.aggregate(pipeline)
        results = await cursor.to_list(length=1)

        if not results:
            return CostSummary(
                total_cost_usd=Decimal("0"),
                total_requests=0,
                total_tokens_in=0,
                total_tokens_out=0,
            )

        result = results[0]
        return CostSummary(
            total_cost_usd=Decimal(str(result.get("total_cost_usd", 0))),
            total_requests=result.get("total_requests", 0),
            total_tokens_in=result.get("total_tokens_in", 0),
            total_tokens_out=result.get("total_tokens_out", 0),
        )
