"""Tests for Platform Cost API schemas (Story 9.10a).

Tests Pydantic schema validation, serialization, and edge cases.
"""

from datetime import date, datetime
from decimal import Decimal

import pytest
from bff.api.schemas.admin.platform_cost_schemas import (
    BudgetConfigRequest,
    BudgetConfigResponse,
    BudgetStatusResponse,
    CostSummaryResponse,
    CostTypeBreakdown,
    CurrentDayCostResponse,
    DailyTrendEntry,
    DailyTrendResponse,
    DocumentCostResponse,
    DomainCostEntry,
    EmbeddingByDomainResponse,
    LlmByAgentTypeResponse,
    LlmByModelResponse,
)
from pydantic import ValidationError


class TestCostSummaryResponse:
    """Tests for CostSummaryResponse schema."""

    def test_valid_cost_summary(self):
        """Test valid cost summary creation."""
        response = CostSummaryResponse(
            total_cost_usd=Decimal("150.75"),
            total_requests=1200,
            by_type=[
                CostTypeBreakdown(
                    cost_type="llm",
                    total_cost_usd=Decimal("120.50"),
                    percentage=79.9,
                ),
            ],
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 24),
        )
        assert response.total_cost_usd == Decimal("150.75")
        assert response.total_requests == 1200

    def test_decimal_serializes_as_string(self):
        """Test that Decimal fields serialize as strings for precision."""
        response = CostSummaryResponse(
            total_cost_usd=Decimal("0.00001"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 1),
        )
        dumped = response.model_dump()
        assert dumped["total_cost_usd"] == "0.00001"

    def test_empty_by_type(self):
        """Test cost summary with empty breakdown."""
        response = CostSummaryResponse(
            total_cost_usd=Decimal("0"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 1),
        )
        assert response.by_type == []


class TestDailyTrendResponse:
    """Tests for DailyTrendResponse schema."""

    def test_valid_daily_trend(self):
        """Test valid daily trend creation."""
        response = DailyTrendResponse(
            entries=[
                DailyTrendEntry(
                    entry_date=date(2026, 1, 24),
                    total_cost_usd=Decimal("5.50"),
                    llm_cost_usd=Decimal("4.00"),
                ),
            ],
            data_available_from=date(2025, 12, 1),
        )
        assert len(response.entries) == 1
        assert response.entries[0].entry_date == date(2026, 1, 24)

    def test_default_costs_are_zero(self):
        """Test that optional cost fields default to zero."""
        entry = DailyTrendEntry(
            entry_date=date(2026, 1, 24),
            total_cost_usd=Decimal("5.00"),
        )
        assert entry.llm_cost_usd == Decimal("0")
        assert entry.document_cost_usd == Decimal("0")
        assert entry.embedding_cost_usd == Decimal("0")


class TestCurrentDayCostResponse:
    """Tests for CurrentDayCostResponse schema."""

    def test_valid_current_day_cost(self):
        """Test valid current day cost creation."""
        response = CurrentDayCostResponse(
            cost_date=date(2026, 1, 24),
            total_cost_usd=Decimal("3.75"),
            by_type={"llm": Decimal("3.00")},
            updated_at=datetime(2026, 1, 24, 14, 30, 0),
        )
        assert response.total_cost_usd == Decimal("3.75")


class TestBudgetConfigRequest:
    """Tests for BudgetConfigRequest schema."""

    def test_valid_daily_only(self):
        """Test request with only daily threshold."""
        request = BudgetConfigRequest(
            daily_threshold_usd=Decimal("50.00"),
        )
        assert request.daily_threshold_usd == Decimal("50.00")
        assert request.monthly_threshold_usd is None

    def test_valid_both_thresholds(self):
        """Test request with both thresholds."""
        request = BudgetConfigRequest(
            daily_threshold_usd=Decimal("50.00"),
            monthly_threshold_usd=Decimal("1000.00"),
        )
        assert request.daily_threshold_usd == Decimal("50.00")
        assert request.monthly_threshold_usd == Decimal("1000.00")

    def test_rejects_zero_daily(self):
        """Test that zero daily threshold is rejected."""
        with pytest.raises(ValidationError):
            BudgetConfigRequest(
                daily_threshold_usd=Decimal("0"),
            )

    def test_rejects_negative_monthly(self):
        """Test that negative monthly threshold is rejected."""
        with pytest.raises(ValidationError):
            BudgetConfigRequest(
                monthly_threshold_usd=Decimal("-10.00"),
            )

    def test_both_none_is_valid_schema(self):
        """Test that both None is valid at schema level (route validates)."""
        request = BudgetConfigRequest()
        assert request.daily_threshold_usd is None
        assert request.monthly_threshold_usd is None


class TestBudgetStatusResponse:
    """Tests for BudgetStatusResponse schema."""

    def test_valid_budget_status(self):
        """Test valid budget status creation."""
        response = BudgetStatusResponse(
            daily_threshold_usd=Decimal("50.00"),
            daily_total_usd=Decimal("10.00"),
            daily_remaining_usd=Decimal("40.00"),
            daily_utilization_percent=20.0,
            monthly_threshold_usd=Decimal("1000.00"),
            monthly_total_usd=Decimal("150.00"),
            monthly_remaining_usd=Decimal("850.00"),
            monthly_utilization_percent=15.0,
            by_type={"llm": Decimal("8.00")},
            current_day="2026-01-24",
            current_month="2026-01",
        )
        assert response.daily_utilization_percent == 20.0
        assert response.current_day == "2026-01-24"


class TestDocumentCostResponse:
    """Tests for DocumentCostResponse schema."""

    def test_valid_document_cost(self):
        """Test valid document cost creation."""
        response = DocumentCostResponse(
            total_cost_usd=Decimal("25.00"),
            total_pages=500,
            avg_cost_per_page_usd=Decimal("0.05"),
            document_count=50,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 24),
        )
        assert response.total_pages == 500
        assert response.document_count == 50


class TestEmbeddingByDomainResponse:
    """Tests for EmbeddingByDomainResponse schema."""

    def test_valid_embedding_response(self):
        """Test valid embedding by domain response."""
        response = EmbeddingByDomainResponse(
            domain_costs=[
                DomainCostEntry(
                    knowledge_domain="tea-quality",
                    cost_usd=Decimal("5.00"),
                    tokens_total=50000,
                    texts_count=200,
                    percentage=100.0,
                ),
            ],
            total_embedding_cost_usd=Decimal("5.00"),
        )
        assert len(response.domain_costs) == 1


class TestLlmResponses:
    """Tests for LLM response schemas."""

    def test_llm_by_agent_type_response(self):
        """Test LLM by agent type response."""
        response = LlmByAgentTypeResponse(
            agent_costs=[],
            total_llm_cost_usd=Decimal("0"),
        )
        assert response.total_llm_cost_usd == Decimal("0")

    def test_llm_by_model_response(self):
        """Test LLM by model response."""
        response = LlmByModelResponse(
            model_costs=[],
            total_llm_cost_usd=Decimal("0"),
        )
        assert response.total_llm_cost_usd == Decimal("0")


class TestBudgetConfigResponse:
    """Tests for BudgetConfigResponse schema."""

    def test_valid_config_response(self):
        """Test valid budget config response."""
        response = BudgetConfigResponse(
            daily_threshold_usd=Decimal("75.00"),
            monthly_threshold_usd=Decimal("1500.00"),
            message="Updated",
            updated_at=datetime(2026, 1, 24, 15, 0, 0),
        )
        assert response.message == "Updated"
