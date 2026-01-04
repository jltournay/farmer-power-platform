"""Unit tests for LlmCostEventRepository.

Story 0.75.5: OpenRouter LLM Gateway with Cost Observability
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from ai_model.domain.cost_event import LlmCostEvent
from ai_model.infrastructure.repositories.cost_event_repository import (
    LlmCostEventRepository,
)


def create_cost_event(
    agent_type: str = "extractor",
    model: str = "anthropic/claude-3-5-sonnet",
    cost_usd: str = "0.00175",
    tokens_in: int = 100,
    tokens_out: int = 50,
    timestamp: datetime | None = None,
    success: bool = True,
    factory_id: str | None = None,
) -> LlmCostEvent:
    """Create a cost event for testing."""
    return LlmCostEvent(
        id=str(uuid.uuid4()),
        timestamp=timestamp or datetime.now(UTC),
        request_id=str(uuid.uuid4()),
        agent_type=agent_type,
        agent_id=f"{agent_type}-agent",
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=Decimal(cost_usd),
        factory_id=factory_id,
        success=success,
        retry_count=0,
    )


class TestLlmCostEventRepository:
    """Tests for LlmCostEventRepository."""

    @pytest.fixture
    def mock_db(self, mock_mongodb_client: Any) -> Any:
        """Get mock database from mock client."""
        return mock_mongodb_client["ai_model"]

    @pytest.fixture
    def repository(self, mock_db: Any) -> LlmCostEventRepository:
        """Create repository with mock database."""
        return LlmCostEventRepository(mock_db)

    # =========================================================================
    # Insert and Get Operations
    # =========================================================================

    @pytest.mark.asyncio
    async def test_insert_creates_document(
        self,
        repository: LlmCostEventRepository,
    ) -> None:
        """Insert creates document and returns ID."""
        event = create_cost_event()

        result = await repository.insert(event)

        assert result == event.id

    @pytest.mark.asyncio
    async def test_get_by_id_existing(
        self,
        repository: LlmCostEventRepository,
    ) -> None:
        """Get by ID returns event when it exists."""
        event = create_cost_event(cost_usd="0.005")
        await repository.insert(event)

        result = await repository.get_by_id(event.id)

        assert result is not None
        assert result.id == event.id
        assert result.cost_usd == Decimal("0.005")
        assert result.agent_type == "extractor"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: LlmCostEventRepository,
    ) -> None:
        """Get by ID returns None when event doesn't exist."""
        result = await repository.get_by_id("nonexistent-id")

        assert result is None

    # =========================================================================
    # Daily Summary
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_daily_summary_with_data(
        self,
        repository: LlmCostEventRepository,
    ) -> None:
        """Get daily summary aggregates costs for the date."""
        target = date(2024, 1, 15)
        target_start = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        # Insert events for the target date
        await repository.insert(
            create_cost_event(cost_usd="0.01", tokens_in=100, tokens_out=50, timestamp=target_start)
        )
        await repository.insert(
            create_cost_event(cost_usd="0.02", tokens_in=200, tokens_out=100, timestamp=target_start)
        )

        result = await repository.get_daily_summary(target)

        assert result.date == datetime(2024, 1, 15, 0, 0, 0, tzinfo=UTC)
        assert result.total_requests == 2
        # Note: Mock aggregation returns float, real MongoDB returns Decimal128
        assert float(result.total_cost_usd) == pytest.approx(0.03, rel=0.01)

    @pytest.mark.asyncio
    async def test_get_daily_summary_empty(
        self,
        repository: LlmCostEventRepository,
    ) -> None:
        """Get daily summary returns zeros when no data."""
        result = await repository.get_daily_summary(date(2024, 1, 15))

        assert result.total_cost_usd == Decimal("0")
        assert result.total_requests == 0
        assert result.total_tokens_in == 0
        assert result.total_tokens_out == 0

    # =========================================================================
    # Cost by Agent Type
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_cost_by_agent_type(
        self,
        repository: LlmCostEventRepository,
    ) -> None:
        """Get cost by agent type groups costs correctly."""
        target_date = date(2024, 1, 15)
        timestamp = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        # Insert events for different agent types
        await repository.insert(create_cost_event(agent_type="extractor", cost_usd="0.01", timestamp=timestamp))
        await repository.insert(create_cost_event(agent_type="extractor", cost_usd="0.02", timestamp=timestamp))
        await repository.insert(create_cost_event(agent_type="analyzer", cost_usd="0.05", timestamp=timestamp))

        result = await repository.get_cost_by_agent_type(target_date, target_date)

        assert len(result) == 2
        # Results sorted by cost descending
        agent_types = {r.agent_type: r for r in result}
        assert "extractor" in agent_types
        assert "analyzer" in agent_types

    # =========================================================================
    # Cost by Model
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_cost_by_model(
        self,
        repository: LlmCostEventRepository,
    ) -> None:
        """Get cost by model groups costs correctly."""
        target_date = date(2024, 1, 15)
        timestamp = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        # Insert events for different models
        await repository.insert(create_cost_event(model="claude-3-5-sonnet", cost_usd="0.01", timestamp=timestamp))
        await repository.insert(create_cost_event(model="claude-3-haiku", cost_usd="0.001", timestamp=timestamp))

        result = await repository.get_cost_by_model(target_date, target_date)

        assert len(result) == 2
        models = {r.model: r for r in result}
        assert "claude-3-5-sonnet" in models
        assert "claude-3-haiku" in models

    # =========================================================================
    # Current Day Cost
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_current_day_cost(
        self,
        repository: LlmCostEventRepository,
    ) -> None:
        """Get current day cost returns today's running total."""
        now = datetime.now(UTC)

        # Insert events for today
        await repository.insert(create_cost_event(cost_usd="0.01", timestamp=now))
        await repository.insert(create_cost_event(cost_usd="0.02", timestamp=now))

        result = await repository.get_current_day_cost()

        assert result.total_requests == 2
        assert float(result.total_cost_usd) == pytest.approx(0.03, rel=0.01)

    @pytest.mark.asyncio
    async def test_get_current_day_cost_empty(
        self,
        repository: LlmCostEventRepository,
    ) -> None:
        """Get current day cost returns zeros when no data."""
        result = await repository.get_current_day_cost()

        assert result.total_cost_usd == Decimal("0")
        assert result.total_requests == 0

    # =========================================================================
    # Current Month Cost
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_current_month_cost(
        self,
        repository: LlmCostEventRepository,
    ) -> None:
        """Get current month cost returns month's running total."""
        now = datetime.now(UTC)

        # Insert events for this month
        await repository.insert(create_cost_event(cost_usd="1.00", timestamp=now))
        await repository.insert(create_cost_event(cost_usd="2.50", timestamp=now))

        result = await repository.get_current_month_cost()

        assert result.total_requests == 2
        assert float(result.total_cost_usd) == pytest.approx(3.50, rel=0.01)

    @pytest.mark.asyncio
    async def test_get_current_month_cost_empty(
        self,
        repository: LlmCostEventRepository,
    ) -> None:
        """Get current month cost returns zeros when no data."""
        result = await repository.get_current_month_cost()

        assert result.total_cost_usd == Decimal("0")
        assert result.total_requests == 0

    # =========================================================================
    # Index Creation
    # =========================================================================

    @pytest.mark.asyncio
    async def test_ensure_indexes(
        self,
        repository: LlmCostEventRepository,
    ) -> None:
        """Ensure indexes creates required indexes without error."""
        # This should not raise any exceptions
        await repository.ensure_indexes()
