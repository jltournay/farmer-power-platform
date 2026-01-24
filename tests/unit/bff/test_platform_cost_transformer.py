"""Tests for PlatformCostTransformer (Story 9.10a).

Tests transformation from fp-common domain models to API response schemas.
"""

from datetime import date, datetime
from decimal import Decimal

import pytest
from bff.transformers.admin.platform_cost_transformer import PlatformCostTransformer
from fp_common.models import (
    BudgetStatus,
    BudgetThresholdConfig,
    CostSummary,
    CurrentDayCost,
    DailyCostTrend,
    DocumentCostSummary,
    EmbeddingCostByDomain,
    LlmCostByAgentType,
    LlmCostByModel,
)
from fp_common.models.cost import (
    AgentTypeCost,
    CostTypeSummary,
    DailyCostEntry,
    DomainCost,
    ModelCost,
)


@pytest.fixture
def transformer() -> PlatformCostTransformer:
    """Create a PlatformCostTransformer."""
    return PlatformCostTransformer()


class TestToCostSummaryResponse:
    """Tests for to_cost_summary_response."""

    def test_transforms_all_fields(self, transformer: PlatformCostTransformer):
        """Test that all CostSummary fields are correctly transformed."""
        summary = CostSummary(
            total_cost_usd=Decimal("250.50"),
            total_requests=2000,
            by_type=[
                CostTypeSummary(
                    cost_type="llm",
                    total_cost_usd=Decimal("200.00"),
                    total_quantity=10000,
                    request_count=1500,
                    percentage=79.8,
                ),
                CostTypeSummary(
                    cost_type="sms",
                    total_cost_usd=Decimal("50.50"),
                    total_quantity=500,
                    request_count=500,
                    percentage=20.2,
                ),
            ],
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 24),
        )

        result = transformer.to_cost_summary_response(summary)

        assert result.total_cost_usd == Decimal("250.50")
        assert result.total_requests == 2000
        assert len(result.by_type) == 2
        assert result.by_type[0].cost_type == "llm"
        assert result.by_type[0].total_cost_usd == Decimal("200.00")
        assert result.by_type[1].cost_type == "sms"
        assert result.period_start == date(2026, 1, 1)
        assert result.period_end == date(2026, 1, 24)

    def test_empty_by_type(self, transformer: PlatformCostTransformer):
        """Test transformation with empty cost type breakdown."""
        summary = CostSummary(
            total_cost_usd=Decimal("0"),
            total_requests=0,
            by_type=[],
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 1),
        )

        result = transformer.to_cost_summary_response(summary)

        assert result.total_cost_usd == Decimal("0")
        assert len(result.by_type) == 0


class TestToDailyTrendResponse:
    """Tests for to_daily_trend_response."""

    def test_transforms_entries(self, transformer: PlatformCostTransformer):
        """Test daily trend entries are correctly transformed."""
        trend = DailyCostTrend(
            entries=[
                DailyCostEntry(
                    entry_date=date(2026, 1, 23),
                    total_cost_usd=Decimal("10.00"),
                    llm_cost_usd=Decimal("7.00"),
                    document_cost_usd=Decimal("2.00"),
                    embedding_cost_usd=Decimal("1.00"),
                ),
            ],
            data_available_from=date(2025, 12, 1),
        )

        result = transformer.to_daily_trend_response(trend)

        assert len(result.entries) == 1
        assert result.entries[0].entry_date == date(2026, 1, 23)
        assert result.entries[0].total_cost_usd == Decimal("10.00")
        assert result.entries[0].llm_cost_usd == Decimal("7.00")
        assert result.entries[0].document_cost_usd == Decimal("2.00")
        assert result.entries[0].embedding_cost_usd == Decimal("1.00")
        assert result.data_available_from == date(2025, 12, 1)

    def test_empty_entries(self, transformer: PlatformCostTransformer):
        """Test transformation with no entries."""
        trend = DailyCostTrend(
            entries=[],
            data_available_from=date(2026, 1, 1),
        )

        result = transformer.to_daily_trend_response(trend)

        assert len(result.entries) == 0


class TestToCurrentDayCostResponse:
    """Tests for to_current_day_cost_response."""

    def test_transforms_current_day(self, transformer: PlatformCostTransformer):
        """Test current day cost transformation."""
        current = CurrentDayCost(
            cost_date=date(2026, 1, 24),
            total_cost_usd=Decimal("5.50"),
            by_type={"llm": Decimal("4.00"), "document": Decimal("1.50")},
            updated_at=datetime(2026, 1, 24, 10, 0, 0),
        )

        result = transformer.to_current_day_cost_response(current)

        assert result.cost_date == date(2026, 1, 24)
        assert result.total_cost_usd == Decimal("5.50")
        assert result.by_type["llm"] == Decimal("4.00")
        assert result.updated_at == datetime(2026, 1, 24, 10, 0, 0)


class TestToLlmByAgentTypeResponse:
    """Tests for to_llm_by_agent_type_response."""

    def test_transforms_agent_costs(self, transformer: PlatformCostTransformer):
        """Test LLM by agent type transformation."""
        breakdown = LlmCostByAgentType(
            agent_costs=[
                AgentTypeCost(
                    agent_type="extractor",
                    cost_usd=Decimal("50.00"),
                    request_count=500,
                    tokens_in=100000,
                    tokens_out=20000,
                    percentage=60.0,
                ),
            ],
            total_llm_cost_usd=Decimal("83.33"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 24),
        )

        result = transformer.to_llm_by_agent_type_response(breakdown)

        assert len(result.agent_costs) == 1
        assert result.agent_costs[0].agent_type == "extractor"
        assert result.agent_costs[0].cost_usd == Decimal("50.00")
        assert result.agent_costs[0].tokens_in == 100000
        assert result.total_llm_cost_usd == Decimal("83.33")


class TestToLlmByModelResponse:
    """Tests for to_llm_by_model_response."""

    def test_transforms_model_costs(self, transformer: PlatformCostTransformer):
        """Test LLM by model transformation."""
        breakdown = LlmCostByModel(
            model_costs=[
                ModelCost(
                    model="anthropic/claude-3-haiku",
                    cost_usd=Decimal("10.00"),
                    request_count=800,
                    tokens_in=200000,
                    tokens_out=40000,
                    percentage=100.0,
                ),
            ],
            total_llm_cost_usd=Decimal("10.00"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 24),
        )

        result = transformer.to_llm_by_model_response(breakdown)

        assert len(result.model_costs) == 1
        assert result.model_costs[0].model == "anthropic/claude-3-haiku"
        assert result.model_costs[0].request_count == 800
        assert result.total_llm_cost_usd == Decimal("10.00")


class TestToDocumentCostResponse:
    """Tests for to_document_cost_response."""

    def test_transforms_document_cost(self, transformer: PlatformCostTransformer):
        """Test document cost summary transformation."""
        doc_cost = DocumentCostSummary(
            total_cost_usd=Decimal("25.00"),
            total_pages=500,
            avg_cost_per_page_usd=Decimal("0.05"),
            document_count=50,
        )

        result = transformer.to_document_cost_response(
            doc_cost=doc_cost,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 24),
        )

        assert result.total_cost_usd == Decimal("25.00")
        assert result.total_pages == 500
        assert result.avg_cost_per_page_usd == Decimal("0.05")
        assert result.document_count == 50
        assert result.period_start == date(2026, 1, 1)
        assert result.period_end == date(2026, 1, 24)


class TestToEmbeddingByDomainResponse:
    """Tests for to_embedding_by_domain_response."""

    def test_transforms_domain_costs(self, transformer: PlatformCostTransformer):
        """Test embedding by domain transformation."""
        breakdown = EmbeddingCostByDomain(
            domain_costs=[
                DomainCost(
                    knowledge_domain="tea-quality",
                    cost_usd=Decimal("3.50"),
                    tokens_total=35000,
                    texts_count=150,
                    percentage=70.0,
                ),
            ],
            total_embedding_cost_usd=Decimal("5.00"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 24),
        )

        result = transformer.to_embedding_by_domain_response(breakdown)

        assert len(result.domain_costs) == 1
        assert result.domain_costs[0].knowledge_domain == "tea-quality"
        assert result.domain_costs[0].cost_usd == Decimal("3.50")
        assert result.total_embedding_cost_usd == Decimal("5.00")


class TestToBudgetStatusResponse:
    """Tests for to_budget_status_response."""

    def test_transforms_budget_status(self, transformer: PlatformCostTransformer):
        """Test budget status transformation."""
        status = BudgetStatus(
            daily_threshold_usd=Decimal("50.00"),
            daily_total_usd=Decimal("30.00"),
            daily_alert_triggered=False,
            daily_remaining_usd=Decimal("20.00"),
            daily_utilization_percent=60.0,
            monthly_threshold_usd=Decimal("1000.00"),
            monthly_total_usd=Decimal("400.00"),
            monthly_alert_triggered=False,
            monthly_remaining_usd=Decimal("600.00"),
            monthly_utilization_percent=40.0,
            by_type={"llm": Decimal("25.00"), "document": Decimal("5.00")},
            current_day="2026-01-24",
            current_month="2026-01",
        )

        result = transformer.to_budget_status_response(status)

        assert result.daily_threshold_usd == Decimal("50.00")
        assert result.daily_total_usd == Decimal("30.00")
        assert result.daily_remaining_usd == Decimal("20.00")
        assert result.daily_utilization_percent == 60.0
        assert result.monthly_threshold_usd == Decimal("1000.00")
        assert result.monthly_utilization_percent == 40.0
        assert result.current_day == "2026-01-24"


class TestToBudgetConfigResponse:
    """Tests for to_budget_config_response."""

    def test_transforms_budget_config(self, transformer: PlatformCostTransformer):
        """Test budget config response transformation."""
        config = BudgetThresholdConfig(
            daily_threshold_usd=Decimal("75.00"),
            monthly_threshold_usd=Decimal("1500.00"),
            message="Budget thresholds updated successfully",
            updated_at=datetime(2026, 1, 24, 15, 30, 0),
        )

        result = transformer.to_budget_config_response(config)

        assert result.daily_threshold_usd == Decimal("75.00")
        assert result.monthly_threshold_usd == Decimal("1500.00")
        assert result.message == "Budget thresholds updated successfully"
        assert result.updated_at == datetime(2026, 1, 24, 15, 30, 0)
