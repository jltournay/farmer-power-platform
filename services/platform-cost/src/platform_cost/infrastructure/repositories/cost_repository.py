"""Unified Cost Repository for MongoDB persistence.

Story 13.3: Cost Repository and Budget Monitor

This module provides the repository for storing and querying unified cost events
across all cost types (LLM, Document, Embedding, SMS). It supports:
- Event insertion with automatic index creation (including TTL)
- Cost summaries by type
- Daily cost trends with breakdown
- Current day/month cost for budget monitoring
- LLM-specific breakdowns by agent type and model

Indexes (per AC #1):
- timestamp (descending) for recent queries
- cost_type for type filtering
- cost_type + timestamp (compound) for type+time queries
- factory_id (sparse) for attribution
- agent_type (sparse) for LLM breakdowns
- model (sparse) for LLM/Embedding breakdowns
- knowledge_domain (sparse) for Embedding breakdowns
- TTL index on timestamp (90 days default)
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import structlog
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel

from platform_cost.domain.cost_event import (
    AgentTypeCost,
    CostTypeSummary,
    CurrentDayCost,
    DailyCostEntry,
    DocumentCostSummary,
    DomainCost,
    ModelCost,
    UnifiedCostEvent,
)

logger = structlog.get_logger(__name__)

# Collection name for cost events
COLLECTION_NAME = "cost_events"


class UnifiedCostRepository:
    """Repository for unified cost event persistence and querying.

    This repository stores all platform cost events (LLM, Document, Embedding, SMS)
    in a single collection with appropriate indexes for efficient querying.
    A TTL index automatically removes events older than the retention period.
    """

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        retention_days: int = 90,
    ) -> None:
        """Initialize the repository.

        Args:
            db: MongoDB database instance.
            retention_days: Number of days to retain cost events (default 90).
                           Events older than this are automatically deleted via TTL.
        """
        self._db = db
        self._collection = db[COLLECTION_NAME]
        self._retention_days = retention_days

    @property
    def data_available_from(self) -> datetime:
        """Get the earliest date for which cost data is available.

        This is based on the TTL retention period. Data older than this
        date may have been automatically deleted.

        Returns:
            datetime: Earliest available data date (UTC).
        """
        return datetime.now(UTC) - timedelta(days=self._retention_days)

    async def ensure_indexes(self) -> None:
        """Create indexes for efficient querying.

        Creates all indexes required per AC #1:
        - timestamp (descending) for recent queries
        - cost_type for type filtering
        - cost_type + timestamp (compound) for type+time queries
        - factory_id (sparse) for attribution
        - agent_type (sparse) for LLM breakdowns
        - model (sparse) for LLM/Embedding breakdowns
        - knowledge_domain (sparse) for Embedding breakdowns
        - request_id (sparse) for tracing
        - Compound indexes for LLM agent/model queries
        - TTL index on timestamp
        """
        # Calculate TTL in seconds (0 means no TTL, keep forever)
        ttl_seconds = self._retention_days * 86400 if self._retention_days > 0 else 0

        indexes = [
            # Primary query patterns
            IndexModel(
                [("timestamp", DESCENDING)],
                name="idx_timestamp",
            ),
            IndexModel(
                [("cost_type", ASCENDING)],
                name="idx_cost_type",
            ),
            IndexModel(
                [("cost_type", ASCENDING), ("timestamp", DESCENDING)],
                name="idx_cost_type_timestamp",
            ),
            # Attribution and tracing
            IndexModel(
                [("factory_id", ASCENDING)],
                name="idx_factory_id",
                sparse=True,
            ),
            IndexModel(
                [("request_id", ASCENDING)],
                name="idx_request_id",
                sparse=True,
            ),
            # LLM-specific indexes
            IndexModel(
                [("agent_type", ASCENDING)],
                name="idx_agent_type",
                sparse=True,
            ),
            IndexModel(
                [("model", ASCENDING)],
                name="idx_model",
                sparse=True,
            ),
            # Embedding-specific index
            IndexModel(
                [("knowledge_domain", ASCENDING)],
                name="idx_knowledge_domain",
                sparse=True,
            ),
            # Compound indexes for LLM breakdowns
            IndexModel(
                [("cost_type", ASCENDING), ("agent_type", ASCENDING), ("timestamp", DESCENDING)],
                name="idx_llm_agent_type",
                sparse=True,
            ),
            IndexModel(
                [("cost_type", ASCENDING), ("model", ASCENDING), ("timestamp", DESCENDING)],
                name="idx_llm_model",
                sparse=True,
            ),
        ]

        # Add TTL index if retention is configured
        if ttl_seconds > 0:
            indexes.append(
                IndexModel(
                    [("timestamp", ASCENDING)],
                    name="idx_ttl",
                    expireAfterSeconds=ttl_seconds,
                )
            )
            logger.info(
                "TTL index configured",
                collection=COLLECTION_NAME,
                retention_days=self._retention_days,
                ttl_seconds=ttl_seconds,
            )

        try:
            await self._collection.create_indexes(indexes)
            logger.info(
                "Cost event indexes created",
                collection=COLLECTION_NAME,
                index_count=len(indexes),
            )
        except Exception as e:
            logger.warning(
                "Failed to create some indexes",
                collection=COLLECTION_NAME,
                error=str(e),
            )

    async def insert(self, event: UnifiedCostEvent) -> str:
        """Insert a new cost event.

        Args:
            event: The cost event to insert.

        Returns:
            The event ID.
        """
        doc = event.to_mongo_doc()
        await self._collection.insert_one(doc)
        logger.debug(
            "Cost event inserted",
            event_id=event.id,
            cost_type=event.cost_type,
            amount_usd=str(event.amount_usd),
        )
        return event.id

    async def get_summary_by_type(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        factory_id: str | None = None,
    ) -> list[CostTypeSummary]:
        """Get cost summary grouped by cost type.

        Args:
            start_date: Start of date range (inclusive). None = data_available_from.
            end_date: End of date range (inclusive). None = today.
            factory_id: Optional factory ID to filter costs by.

        Returns:
            List of CostTypeSummary models, sorted by total cost descending.
        """
        # Build time filter
        start_dt = (
            datetime.combine(start_date, datetime.min.time(), tzinfo=UTC) if start_date else self.data_available_from
        )
        end_dt = (
            datetime.combine(end_date, datetime.min.time(), tzinfo=UTC) + timedelta(days=1)
            if end_date
            else datetime.now(UTC)
        )

        # Build match filter
        match_filter: dict[str, Any] = {"timestamp": {"$gte": start_dt, "$lt": end_dt}}
        if factory_id:
            match_filter["factory_id"] = factory_id

        pipeline: list[dict[str, Any]] = [
            {"$match": match_filter},
            {
                "$group": {
                    "_id": "$cost_type",
                    "total_cost_usd": {"$sum": {"$toDecimal": "$amount_usd"}},
                    "total_quantity": {"$sum": "$quantity"},
                    "request_count": {"$sum": 1},
                }
            },
            {"$sort": {"total_cost_usd": -1}},
        ]

        cursor = self._collection.aggregate(pipeline)
        results = await cursor.to_list(length=100)

        # Calculate total for percentages
        total_cost = sum(Decimal(str(r.get("total_cost_usd", 0))) for r in results)

        summaries = []
        for result in results:
            cost = Decimal(str(result.get("total_cost_usd", 0)))
            percentage = float(cost / total_cost * 100) if total_cost > 0 else 0.0
            summaries.append(
                CostTypeSummary(
                    cost_type=result["_id"],
                    total_cost_usd=cost,
                    total_quantity=result.get("total_quantity", 0),
                    request_count=result.get("request_count", 0),
                    percentage=round(percentage, 2),
                )
            )

        return summaries

    async def get_daily_trend(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        days: int = 30,
    ) -> list[DailyCostEntry]:
        """Get daily cost trend with breakdown by type.

        Args:
            start_date: Start of date range (inclusive). None = end_date - days.
            end_date: End of date range (inclusive). None = today.
            days: Number of days to include if start_date is None.

        Returns:
            List of DailyCostEntry models, sorted by date ascending.
        """
        # Determine date range
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=days - 1)

        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
        end_dt = datetime.combine(end_date, datetime.min.time(), tzinfo=UTC) + timedelta(days=1)

        pipeline: list[dict[str, Any]] = [
            {"$match": {"timestamp": {"$gte": start_dt, "$lt": end_dt}}},
            {
                "$group": {
                    "_id": {
                        "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                        "cost_type": "$cost_type",
                    },
                    "cost_usd": {"$sum": {"$toDecimal": "$amount_usd"}},
                }
            },
            {"$sort": {"_id.date": 1}},
        ]

        cursor = self._collection.aggregate(pipeline)
        results = await cursor.to_list(length=1000)  # Up to ~365 days * 4 types

        # Aggregate by date
        daily_costs: dict[str, dict[str, Decimal]] = {}
        for result in results:
            date_str = result["_id"]["date"]
            cost_type = result["_id"]["cost_type"]
            cost = Decimal(str(result.get("cost_usd", 0)))

            if date_str not in daily_costs:
                daily_costs[date_str] = {
                    "total": Decimal("0"),
                    "llm": Decimal("0"),
                    "document": Decimal("0"),
                    "embedding": Decimal("0"),
                    "sms": Decimal("0"),
                }

            daily_costs[date_str]["total"] += cost
            if cost_type in daily_costs[date_str]:
                daily_costs[date_str][cost_type] += cost

        # Convert to DailyCostEntry models
        entries = []
        for date_str in sorted(daily_costs.keys()):
            costs = daily_costs[date_str]
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            entries.append(
                DailyCostEntry(
                    entry_date=parsed_date,
                    total_cost_usd=costs["total"],
                    llm_cost_usd=costs["llm"],
                    document_cost_usd=costs["document"],
                    embedding_cost_usd=costs["embedding"],
                    sms_cost_usd=costs["sms"],
                )
            )

        return entries

    async def get_current_day_cost(self) -> CurrentDayCost:
        """Get the current day's running cost total with breakdown.

        Used for real-time budget monitoring and dashboard widgets.

        Returns:
            CurrentDayCost model with today's running total.
        """
        today = date.today()
        start_dt = datetime.combine(today, datetime.min.time(), tzinfo=UTC)
        now = datetime.now(UTC)

        pipeline: list[dict[str, Any]] = [
            {"$match": {"timestamp": {"$gte": start_dt, "$lte": now}}},
            {
                "$group": {
                    "_id": "$cost_type",
                    "cost_usd": {"$sum": {"$toDecimal": "$amount_usd"}},
                }
            },
        ]

        cursor = self._collection.aggregate(pipeline)
        results = await cursor.to_list(length=10)

        # Build by_type dict and calculate total
        by_type: dict[str, Decimal] = {}
        total_cost = Decimal("0")
        for result in results:
            cost_type = result["_id"]
            cost = Decimal(str(result.get("cost_usd", 0)))
            by_type[cost_type] = cost
            total_cost += cost

        return CurrentDayCost(
            cost_date=today,
            total_cost_usd=total_cost,
            by_type=by_type,
            updated_at=now,
        )

    async def get_current_month_cost(self) -> Decimal:
        """Get the current month's running cost total.

        Used for monthly budget monitoring and warm-up.

        Returns:
            Total cost in USD for the current month.
        """
        today = date.today()
        start_of_month = datetime(today.year, today.month, 1, tzinfo=UTC)
        now = datetime.now(UTC)

        pipeline: list[dict[str, Any]] = [
            {"$match": {"timestamp": {"$gte": start_of_month, "$lte": now}}},
            {
                "$group": {
                    "_id": None,
                    "total_cost_usd": {"$sum": {"$toDecimal": "$amount_usd"}},
                }
            },
        ]

        cursor = self._collection.aggregate(pipeline)
        results = await cursor.to_list(length=1)

        if not results:
            return Decimal("0")

        return Decimal(str(results[0].get("total_cost_usd", 0)))

    async def get_llm_cost_by_agent_type(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[AgentTypeCost]:
        """Get LLM cost breakdown by agent type.

        Args:
            start_date: Start of date range (inclusive). None = data_available_from.
            end_date: End of date range (inclusive). None = today.

        Returns:
            List of AgentTypeCost models, sorted by cost descending.
        """
        start_dt = (
            datetime.combine(start_date, datetime.min.time(), tzinfo=UTC) if start_date else self.data_available_from
        )
        end_dt = (
            datetime.combine(end_date, datetime.min.time(), tzinfo=UTC) + timedelta(days=1)
            if end_date
            else datetime.now(UTC)
        )

        pipeline: list[dict[str, Any]] = [
            {
                "$match": {
                    "timestamp": {"$gte": start_dt, "$lt": end_dt},
                    "cost_type": "llm",
                    "agent_type": {"$ne": None},
                }
            },
            {
                "$group": {
                    "_id": "$agent_type",
                    "cost_usd": {"$sum": {"$toDecimal": "$amount_usd"}},
                    "request_count": {"$sum": 1},
                    "tokens_in": {"$sum": {"$ifNull": ["$metadata.tokens_in", 0]}},
                    "tokens_out": {"$sum": {"$ifNull": ["$metadata.tokens_out", 0]}},
                }
            },
            {"$sort": {"cost_usd": -1}},
        ]

        cursor = self._collection.aggregate(pipeline)
        results = await cursor.to_list(length=100)

        # Calculate total for percentages
        total_cost = sum(Decimal(str(r.get("cost_usd", 0))) for r in results)

        agent_costs = []
        for result in results:
            cost = Decimal(str(result.get("cost_usd", 0)))
            percentage = float(cost / total_cost * 100) if total_cost > 0 else 0.0
            agent_costs.append(
                AgentTypeCost(
                    agent_type=result["_id"],
                    cost_usd=cost,
                    request_count=result.get("request_count", 0),
                    tokens_in=result.get("tokens_in", 0),
                    tokens_out=result.get("tokens_out", 0),
                    percentage=round(percentage, 2),
                )
            )

        return agent_costs

    async def get_llm_cost_by_model(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[ModelCost]:
        """Get LLM cost breakdown by model.

        Args:
            start_date: Start of date range (inclusive). None = data_available_from.
            end_date: End of date range (inclusive). None = today.

        Returns:
            List of ModelCost models, sorted by cost descending.
        """
        start_dt = (
            datetime.combine(start_date, datetime.min.time(), tzinfo=UTC) if start_date else self.data_available_from
        )
        end_dt = (
            datetime.combine(end_date, datetime.min.time(), tzinfo=UTC) + timedelta(days=1)
            if end_date
            else datetime.now(UTC)
        )

        pipeline: list[dict[str, Any]] = [
            {
                "$match": {
                    "timestamp": {"$gte": start_dt, "$lt": end_dt},
                    "cost_type": "llm",
                    "model": {"$ne": None},
                }
            },
            {
                "$group": {
                    "_id": "$model",
                    "cost_usd": {"$sum": {"$toDecimal": "$amount_usd"}},
                    "request_count": {"$sum": 1},
                    "tokens_in": {"$sum": {"$ifNull": ["$metadata.tokens_in", 0]}},
                    "tokens_out": {"$sum": {"$ifNull": ["$metadata.tokens_out", 0]}},
                }
            },
            {"$sort": {"cost_usd": -1}},
        ]

        cursor = self._collection.aggregate(pipeline)
        results = await cursor.to_list(length=100)

        # Calculate total for percentages
        total_cost = sum(Decimal(str(r.get("cost_usd", 0))) for r in results)

        model_costs = []
        for result in results:
            cost = Decimal(str(result.get("cost_usd", 0)))
            percentage = float(cost / total_cost * 100) if total_cost > 0 else 0.0
            model_costs.append(
                ModelCost(
                    model=result["_id"],
                    cost_usd=cost,
                    request_count=result.get("request_count", 0),
                    tokens_in=result.get("tokens_in", 0),
                    tokens_out=result.get("tokens_out", 0),
                    percentage=round(percentage, 2),
                )
            )

        return model_costs

    async def get_document_cost_summary(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> DocumentCostSummary:
        """Get document processing cost summary.

        Args:
            start_date: Start of date range (inclusive). None = data_available_from.
            end_date: End of date range (inclusive). None = today.

        Returns:
            DocumentCostSummary with total, pages, avg cost per page.
        """
        start_dt = (
            datetime.combine(start_date, datetime.min.time(), tzinfo=UTC) if start_date else self.data_available_from
        )
        end_dt = (
            datetime.combine(end_date, datetime.min.time(), tzinfo=UTC) + timedelta(days=1)
            if end_date
            else datetime.now(UTC)
        )

        pipeline: list[dict[str, Any]] = [
            {
                "$match": {
                    "timestamp": {"$gte": start_dt, "$lt": end_dt},
                    "cost_type": "document",
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_cost_usd": {"$sum": {"$toDecimal": "$amount_usd"}},
                    "total_pages": {"$sum": "$quantity"},
                    "document_count": {"$sum": 1},
                }
            },
        ]

        cursor = self._collection.aggregate(pipeline)
        results = await cursor.to_list(length=1)

        if not results:
            return DocumentCostSummary(
                total_cost_usd=Decimal("0"),
                total_pages=0,
                avg_cost_per_page_usd=Decimal("0"),
                document_count=0,
            )

        result = results[0]
        total_cost = Decimal(str(result.get("total_cost_usd", 0)))
        total_pages = result.get("total_pages", 0)
        avg_cost = total_cost / total_pages if total_pages > 0 else Decimal("0")

        return DocumentCostSummary(
            total_cost_usd=total_cost,
            total_pages=total_pages,
            avg_cost_per_page_usd=avg_cost,
            document_count=result.get("document_count", 0),
        )

    async def get_embedding_cost_by_domain(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[DomainCost]:
        """Get embedding cost breakdown by knowledge domain.

        Args:
            start_date: Start of date range (inclusive). None = data_available_from.
            end_date: End of date range (inclusive). None = today.

        Returns:
            List of DomainCost models, sorted by cost descending.
        """
        start_dt = (
            datetime.combine(start_date, datetime.min.time(), tzinfo=UTC) if start_date else self.data_available_from
        )
        end_dt = (
            datetime.combine(end_date, datetime.min.time(), tzinfo=UTC) + timedelta(days=1)
            if end_date
            else datetime.now(UTC)
        )

        pipeline: list[dict[str, Any]] = [
            {
                "$match": {
                    "timestamp": {"$gte": start_dt, "$lt": end_dt},
                    "cost_type": "embedding",
                    "knowledge_domain": {"$ne": None},
                }
            },
            {
                "$group": {
                    "_id": "$knowledge_domain",
                    "cost_usd": {"$sum": {"$toDecimal": "$amount_usd"}},
                    "tokens_total": {"$sum": "$quantity"},
                    "texts_count": {"$sum": 1},
                }
            },
            {"$sort": {"cost_usd": -1}},
        ]

        cursor = self._collection.aggregate(pipeline)
        results = await cursor.to_list(length=100)

        # Calculate total for percentages
        total_cost = sum(Decimal(str(r.get("cost_usd", 0))) for r in results)

        domain_costs = []
        for result in results:
            cost = Decimal(str(result.get("cost_usd", 0)))
            percentage = float(cost / total_cost * 100) if total_cost > 0 else 0.0
            domain_costs.append(
                DomainCost(
                    knowledge_domain=result["_id"],
                    cost_usd=cost,
                    tokens_total=result.get("tokens_total", 0),
                    texts_count=result.get("texts_count", 0),
                    percentage=round(percentage, 2),
                )
            )

        return domain_costs
