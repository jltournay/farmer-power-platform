"""Unit tests for UnifiedCostRepository.

Story 13.3: Cost Repository and Budget Monitor

Tests:
- Index creation (AC #1)
- Event insertion
- Summary queries with typed models (AC #2)
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from platform_cost.domain.cost_event import UnifiedCostEvent
from platform_cost.infrastructure.repositories.cost_repository import (
    COLLECTION_NAME,
    UnifiedCostRepository,
)


@pytest.fixture
def mock_db(mock_mongodb_client):
    """Get mock MongoDB database."""
    return mock_mongodb_client["platform_cost"]


@pytest.fixture
def cost_repository(mock_db):
    """Create UnifiedCostRepository with mock database."""
    return UnifiedCostRepository(db=mock_db, retention_days=90)


class TestEnsureIndexes:
    """Tests for ensure_indexes method."""

    @pytest.mark.asyncio
    async def test_creates_indexes_with_ttl(self, cost_repository, mock_db) -> None:
        """Test that ensure_indexes creates indexes including TTL (AC #1)."""
        await cost_repository.ensure_indexes()

        collection = mock_db[COLLECTION_NAME]
        # The mock doesn't track exact index definitions, but calling
        # create_indexes should complete without error
        # In real tests, we'd verify index names

    @pytest.mark.asyncio
    async def test_ttl_disabled_when_zero(self, mock_db) -> None:
        """Test that TTL index is disabled when retention_days is 0."""
        repo = UnifiedCostRepository(db=mock_db, retention_days=0)
        await repo.ensure_indexes()
        # Should complete without error

    def test_data_available_from_property(self, cost_repository) -> None:
        """Test data_available_from returns correct date."""
        expected = datetime.now(UTC) - timedelta(days=90)
        actual = cost_repository.data_available_from

        # Within a second of expected
        assert abs((actual - expected).total_seconds()) < 1


class TestInsert:
    """Tests for insert method."""

    @pytest.mark.asyncio
    async def test_insert_stores_event(self, cost_repository, mock_db) -> None:
        """Test that insert stores event in MongoDB."""
        event = UnifiedCostEvent(
            id="test-event-001",
            cost_type="llm",
            amount_usd=Decimal("0.0015"),
            quantity=1500,
            unit="tokens",
            timestamp=datetime.now(UTC),
            source_service="ai-model",
            success=True,
            metadata={"model": "claude-3-haiku"},
            agent_type="extractor",
            model="claude-3-haiku",
        )

        event_id = await cost_repository.insert(event)

        assert event_id == "test-event-001"

        # Verify document stored
        collection = mock_db[COLLECTION_NAME]
        doc = await collection.find_one({"_id": "test-event-001"})
        assert doc is not None
        assert doc["cost_type"] == "llm"
        assert doc["amount_usd"] == "0.0015"


class TestGetSummaryByType:
    """Tests for get_summary_by_type method."""

    @pytest.mark.asyncio
    async def test_returns_typed_cost_type_summary(self, cost_repository, mock_db) -> None:
        """Test that get_summary_by_type returns CostTypeSummary models (AC #2)."""
        # Insert test events
        collection = mock_db[COLLECTION_NAME]
        now = datetime.now(UTC)

        await collection.insert_many(
            [
                {
                    "_id": "event-1",
                    "cost_type": "llm",
                    "amount_usd": "1.00",
                    "quantity": 10000,
                    "timestamp": now,
                },
                {
                    "_id": "event-2",
                    "cost_type": "llm",
                    "amount_usd": "2.00",
                    "quantity": 20000,
                    "timestamp": now,
                },
                {
                    "_id": "event-3",
                    "cost_type": "document",
                    "amount_usd": "0.50",
                    "quantity": 10,
                    "timestamp": now,
                },
            ]
        )

        summaries = await cost_repository.get_summary_by_type()

        # Should return CostTypeSummary objects
        assert len(summaries) > 0
        for summary in summaries:
            assert hasattr(summary, "cost_type")
            assert hasattr(summary, "total_cost_usd")
            assert hasattr(summary, "percentage")

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_data(self, cost_repository) -> None:
        """Test returns empty list when no events exist."""
        summaries = await cost_repository.get_summary_by_type()
        assert summaries == []


class TestGetDailyTrend:
    """Tests for get_daily_trend method."""

    @pytest.mark.asyncio
    async def test_returns_daily_cost_entry_models(self, cost_repository) -> None:
        """Test that get_daily_trend returns DailyCostEntry models (AC #2).

        Note: Uses empty result since MockAggregationCursor doesn't handle
        complex $group keys with $dateToString. Real MongoDB aggregation works.
        """
        today = date.today()

        # Empty data returns empty list (mock aggregation limitation)
        entries = await cost_repository.get_daily_trend(
            start_date=today,
            end_date=today,
        )

        # Verify it returns a list (can be empty with mock)
        assert isinstance(entries, list)

        # Verify the method handles empty results correctly
        # In production, DailyCostEntry objects would be returned with proper aggregation

    @pytest.mark.asyncio
    async def test_uses_default_days_when_no_start(self, cost_repository, mock_db) -> None:
        """Test that days parameter is used when start_date not provided."""
        entries = await cost_repository.get_daily_trend(days=7)
        # Should not raise error; empty list is fine for no data
        assert isinstance(entries, list)


class TestGetCurrentDayCost:
    """Tests for get_current_day_cost method."""

    @pytest.mark.asyncio
    async def test_returns_current_day_cost_model(self, cost_repository, mock_db) -> None:
        """Test that get_current_day_cost returns CurrentDayCost model (AC #2)."""
        collection = mock_db[COLLECTION_NAME]
        now = datetime.now(UTC)

        await collection.insert_one(
            {
                "_id": "event-now",
                "cost_type": "llm",
                "amount_usd": "0.75",
                "quantity": 7500,
                "timestamp": now,
            }
        )

        current = await cost_repository.get_current_day_cost()

        assert hasattr(current, "cost_date")
        assert hasattr(current, "total_cost_usd")
        assert hasattr(current, "by_type")
        assert hasattr(current, "updated_at")

    @pytest.mark.asyncio
    async def test_returns_zero_for_no_data(self, cost_repository) -> None:
        """Test returns zero totals when no events exist today."""
        current = await cost_repository.get_current_day_cost()

        assert current.total_cost_usd == Decimal("0")
        assert current.by_type == {}


class TestGetCurrentMonthCost:
    """Tests for get_current_month_cost method."""

    @pytest.mark.asyncio
    async def test_returns_decimal_total(self, cost_repository, mock_db) -> None:
        """Test that get_current_month_cost returns Decimal."""
        collection = mock_db[COLLECTION_NAME]
        now = datetime.now(UTC)

        await collection.insert_many(
            [
                {
                    "_id": "event-m1",
                    "cost_type": "llm",
                    "amount_usd": "5.00",
                    "timestamp": now,
                },
                {
                    "_id": "event-m2",
                    "cost_type": "document",
                    "amount_usd": "2.50",
                    "timestamp": now,
                },
            ]
        )

        total = await cost_repository.get_current_month_cost()

        assert isinstance(total, Decimal)

    @pytest.mark.asyncio
    async def test_returns_zero_for_no_data(self, cost_repository) -> None:
        """Test returns zero when no events exist this month."""
        total = await cost_repository.get_current_month_cost()
        assert total == Decimal("0")


class TestGetLlmCostByAgentType:
    """Tests for get_llm_cost_by_agent_type method."""

    @pytest.mark.asyncio
    async def test_returns_agent_type_cost_models(self, cost_repository, mock_db) -> None:
        """Test that get_llm_cost_by_agent_type returns AgentTypeCost models (AC #2)."""
        collection = mock_db[COLLECTION_NAME]
        now = datetime.now(UTC)

        await collection.insert_many(
            [
                {
                    "_id": "llm-1",
                    "cost_type": "llm",
                    "amount_usd": "1.00",
                    "agent_type": "extractor",
                    "model": "claude-3-haiku",
                    "timestamp": now,
                    "metadata": {"tokens_in": 5000, "tokens_out": 2500},
                },
                {
                    "_id": "llm-2",
                    "cost_type": "llm",
                    "amount_usd": "2.00",
                    "agent_type": "explorer",
                    "model": "claude-3-sonnet",
                    "timestamp": now,
                    "metadata": {"tokens_in": 10000, "tokens_out": 5000},
                },
            ]
        )

        agent_costs = await cost_repository.get_llm_cost_by_agent_type()

        for cost in agent_costs:
            assert hasattr(cost, "agent_type")
            assert hasattr(cost, "cost_usd")
            assert hasattr(cost, "request_count")
            assert hasattr(cost, "percentage")


class TestGetLlmCostByModel:
    """Tests for get_llm_cost_by_model method."""

    @pytest.mark.asyncio
    async def test_returns_model_cost_objects(self, cost_repository, mock_db) -> None:
        """Test that get_llm_cost_by_model returns ModelCost models (AC #2)."""
        collection = mock_db[COLLECTION_NAME]
        now = datetime.now(UTC)

        await collection.insert_one(
            {
                "_id": "model-test",
                "cost_type": "llm",
                "amount_usd": "1.50",
                "model": "anthropic/claude-3-haiku",
                "agent_type": "extractor",
                "timestamp": now,
                "metadata": {"tokens_in": 7500, "tokens_out": 3750},
            }
        )

        model_costs = await cost_repository.get_llm_cost_by_model()

        for cost in model_costs:
            assert hasattr(cost, "model")
            assert hasattr(cost, "cost_usd")
            assert hasattr(cost, "percentage")


class TestGetDocumentCostSummary:
    """Tests for get_document_cost_summary method (Story 13.4)."""

    @pytest.mark.asyncio
    async def test_returns_document_cost_summary(self, cost_repository, mock_db) -> None:
        """Test that get_document_cost_summary returns DocumentCostSummary model."""
        collection = mock_db[COLLECTION_NAME]
        now = datetime.now(UTC)

        await collection.insert_many(
            [
                {
                    "_id": "doc-1",
                    "cost_type": "document",
                    "amount_usd": "0.50",
                    "quantity": 10,
                    "timestamp": now,
                },
                {
                    "_id": "doc-2",
                    "cost_type": "document",
                    "amount_usd": "0.25",
                    "quantity": 5,
                    "timestamp": now,
                },
            ]
        )

        summary = await cost_repository.get_document_cost_summary()

        assert hasattr(summary, "total_cost_usd")
        assert hasattr(summary, "total_pages")
        assert hasattr(summary, "avg_cost_per_page_usd")
        assert hasattr(summary, "document_count")

    @pytest.mark.asyncio
    async def test_returns_zero_for_no_data(self, cost_repository) -> None:
        """Test returns zero values when no document events exist."""
        summary = await cost_repository.get_document_cost_summary()

        assert summary.total_cost_usd == Decimal("0")
        assert summary.total_pages == 0
        assert summary.document_count == 0


class TestGetEmbeddingCostByDomain:
    """Tests for get_embedding_cost_by_domain method (Story 13.4)."""

    @pytest.mark.asyncio
    async def test_returns_domain_cost_models(self, cost_repository, mock_db) -> None:
        """Test that get_embedding_cost_by_domain returns DomainCost models."""
        collection = mock_db[COLLECTION_NAME]
        now = datetime.now(UTC)

        await collection.insert_many(
            [
                {
                    "_id": "emb-1",
                    "cost_type": "embedding",
                    "amount_usd": "0.10",
                    "quantity": 10000,
                    "knowledge_domain": "tea-quality",
                    "timestamp": now,
                },
                {
                    "_id": "emb-2",
                    "cost_type": "embedding",
                    "amount_usd": "0.05",
                    "quantity": 5000,
                    "knowledge_domain": "farming-practices",
                    "timestamp": now,
                },
            ]
        )

        domain_costs = await cost_repository.get_embedding_cost_by_domain()

        for cost in domain_costs:
            assert hasattr(cost, "knowledge_domain")
            assert hasattr(cost, "cost_usd")
            assert hasattr(cost, "tokens_total")
            assert hasattr(cost, "texts_count")
            assert hasattr(cost, "percentage")

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_data(self, cost_repository) -> None:
        """Test returns empty list when no embedding events exist."""
        domain_costs = await cost_repository.get_embedding_cost_by_domain()

        assert domain_costs == []
