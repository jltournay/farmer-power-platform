"""Unit tests for LlmCostEvent domain model.

Story 0.75.5: OpenRouter LLM Gateway with Cost Observability
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from ai_model.domain.cost_event import (
    AgentTypeCost,
    CostSummary,
    DailyCostSummary,
    LlmCostEvent,
    ModelCost,
)


class TestLlmCostEvent:
    """Tests for LlmCostEvent model."""

    def test_create_cost_event(self) -> None:
        """Test creating a cost event with all fields."""
        event = LlmCostEvent(
            id="event-123",
            timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
            request_id="req-456",
            agent_type="extractor",
            agent_id="qc-extractor",
            model="anthropic/claude-3-5-sonnet",
            tokens_in=150,
            tokens_out=200,
            cost_usd=Decimal("0.00175"),
            factory_id="factory-001",
            success=True,
            retry_count=0,
        )

        assert event.id == "event-123"
        assert event.agent_type == "extractor"
        assert event.model == "anthropic/claude-3-5-sonnet"
        assert event.tokens_in == 150
        assert event.tokens_out == 200
        assert event.cost_usd == Decimal("0.00175")
        assert event.success is True

    def test_total_tokens_property(self) -> None:
        """Test total_tokens property."""
        event = LlmCostEvent(
            id="event-123",
            request_id="req-456",
            agent_type="extractor",
            agent_id="qc-extractor",
            model="test-model",
            tokens_in=100,
            tokens_out=50,
        )
        assert event.total_tokens == 150

    def test_default_values(self) -> None:
        """Test default field values."""
        event = LlmCostEvent(
            id="event-123",
            request_id="req-456",
            agent_type="extractor",
            agent_id="qc-extractor",
            model="test-model",
        )

        assert event.tokens_in == 0
        assert event.tokens_out == 0
        assert event.cost_usd == Decimal("0")
        assert event.factory_id is None
        assert event.success is True
        assert event.retry_count == 0

    def test_model_dump_for_mongo(self) -> None:
        """Test model_dump_for_mongo converts Decimal to string."""
        event = LlmCostEvent(
            id="event-123",
            request_id="req-456",
            agent_type="extractor",
            agent_id="qc-extractor",
            model="test-model",
            cost_usd=Decimal("0.00175"),
        )

        doc = event.model_dump_for_mongo()
        assert doc["cost_usd"] == "0.00175"
        assert isinstance(doc["cost_usd"], str)

    def test_from_mongo(self) -> None:
        """Test from_mongo converts string to Decimal."""
        doc = {
            "id": "event-123",
            "request_id": "req-456",
            "agent_type": "extractor",
            "agent_id": "qc-extractor",
            "model": "test-model",
            "cost_usd": "0.00175",
            "tokens_in": 100,
            "tokens_out": 50,
            "success": True,
            "retry_count": 0,
            "_id": "event-123",  # MongoDB adds this
        }

        event = LlmCostEvent.from_mongo(doc)
        assert event.cost_usd == Decimal("0.00175")
        assert isinstance(event.cost_usd, Decimal)

    def test_validation_tokens_non_negative(self) -> None:
        """Test tokens must be non-negative."""
        with pytest.raises(ValueError):
            LlmCostEvent(
                id="event-123",
                request_id="req-456",
                agent_type="extractor",
                agent_id="qc-extractor",
                model="test-model",
                tokens_in=-1,
            )

    def test_validation_cost_non_negative(self) -> None:
        """Test cost must be non-negative."""
        with pytest.raises(ValueError):
            LlmCostEvent(
                id="event-123",
                request_id="req-456",
                agent_type="extractor",
                agent_id="qc-extractor",
                model="test-model",
                cost_usd=Decimal("-0.01"),
            )


class TestDailyCostSummary:
    """Tests for DailyCostSummary model."""

    def test_create_daily_summary(self) -> None:
        """Test creating a daily cost summary."""
        summary = DailyCostSummary(
            date=datetime(2024, 1, 15, 0, 0, 0, tzinfo=UTC),
            total_cost_usd=Decimal("12.50"),
            total_requests=100,
            total_tokens_in=5000,
            total_tokens_out=3000,
            success_count=95,
            failure_count=5,
        )

        assert summary.total_cost_usd == Decimal("12.50")
        assert summary.total_requests == 100
        assert summary.success_count == 95


class TestAgentTypeCost:
    """Tests for AgentTypeCost model."""

    def test_create_agent_type_cost(self) -> None:
        """Test creating agent type cost summary."""
        cost = AgentTypeCost(
            agent_type="extractor",
            total_cost_usd=Decimal("5.25"),
            total_requests=50,
            total_tokens=8000,
        )

        assert cost.agent_type == "extractor"
        assert cost.total_cost_usd == Decimal("5.25")


class TestModelCost:
    """Tests for ModelCost model."""

    def test_create_model_cost(self) -> None:
        """Test creating model cost summary."""
        cost = ModelCost(
            model="anthropic/claude-3-5-sonnet",
            total_cost_usd=Decimal("8.75"),
            total_requests=75,
            total_tokens=12000,
        )

        assert cost.model == "anthropic/claude-3-5-sonnet"
        assert cost.total_cost_usd == Decimal("8.75")


class TestCostSummary:
    """Tests for CostSummary model."""

    def test_create_cost_summary(self) -> None:
        """Test creating cost summary."""
        summary = CostSummary(
            total_cost_usd=Decimal("25.00"),
            total_requests=200,
            total_tokens_in=10000,
            total_tokens_out=8000,
        )

        assert summary.total_cost_usd == Decimal("25.00")
        assert summary.total_requests == 200

    def test_default_values(self) -> None:
        """Test default values."""
        summary = CostSummary()
        assert summary.total_cost_usd == Decimal("0")
        assert summary.total_requests == 0
