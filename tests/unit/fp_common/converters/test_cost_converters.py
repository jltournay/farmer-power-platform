"""Unit tests for cost_converters module.

Story 13.6: BFF Integration Layer

Tests verify Proto-to-Pydantic conversion correctness including:
- Basic field mapping
- Decimal string to Decimal conversion
- Date string parsing
- Nested list handling
- Round-trip validation (proto -> pydantic -> model_dump)
"""

from datetime import UTC, date, datetime
from decimal import Decimal

from fp_common.converters import (
    budget_status_from_proto,
    budget_threshold_config_from_proto,
    cost_summary_from_proto,
    current_day_cost_from_proto,
    daily_cost_trend_from_proto,
    document_cost_summary_from_proto,
    embedding_cost_by_domain_from_proto,
    llm_cost_by_agent_type_from_proto,
    llm_cost_by_model_from_proto,
)
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
from fp_proto.platform_cost.v1 import platform_cost_pb2


class TestCostSummaryFromProto:
    """Tests for cost_summary_from_proto converter."""

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped."""
        proto = platform_cost_pb2.CostSummaryResponse(
            total_cost_usd="123.45",
            period_start="2025-01-01",
            period_end="2025-01-31",
            total_requests=500,
        )
        proto.by_type.append(
            platform_cost_pb2.CostTypeBreakdown(
                cost_type="llm",
                total_cost_usd="100.00",
                total_quantity=10000,
                request_count=400,
                percentage=81.0,
            )
        )
        proto.by_type.append(
            platform_cost_pb2.CostTypeBreakdown(
                cost_type="sms",
                total_cost_usd="23.45",
                total_quantity=1000,
                request_count=100,
                percentage=19.0,
            )
        )

        result = cost_summary_from_proto(proto)

        assert isinstance(result, CostSummary)
        assert result.total_cost_usd == Decimal("123.45")
        assert result.period_start == date(2025, 1, 1)
        assert result.period_end == date(2025, 1, 31)
        assert result.total_requests == 500
        assert len(result.by_type) == 2
        assert result.by_type[0].cost_type == "llm"
        assert result.by_type[0].total_cost_usd == Decimal("100.00")
        assert result.by_type[1].cost_type == "sms"

    def test_empty_by_type(self):
        """Empty by_type list is handled."""
        proto = platform_cost_pb2.CostSummaryResponse(
            total_cost_usd="0.00",
            period_start="2025-01-01",
            period_end="2025-01-31",
            total_requests=0,
        )

        result = cost_summary_from_proto(proto)

        assert result.total_cost_usd == Decimal("0.00")
        assert result.by_type == []


class TestDailyCostTrendFromProto:
    """Tests for daily_cost_trend_from_proto converter."""

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped."""
        proto = platform_cost_pb2.DailyCostTrendResponse(
            data_available_from="2025-01-01",
        )
        proto.entries.append(
            platform_cost_pb2.DailyCostEntry(
                date="2025-01-01",
                total_cost_usd="10.00",
                llm_cost_usd="8.00",
                document_cost_usd="1.00",
                embedding_cost_usd="0.50",
                sms_cost_usd="0.50",
            )
        )
        proto.entries.append(
            platform_cost_pb2.DailyCostEntry(
                date="2025-01-02",
                total_cost_usd="12.00",
                llm_cost_usd="10.00",
                document_cost_usd="1.00",
                embedding_cost_usd="0.50",
                sms_cost_usd="0.50",
            )
        )

        result = daily_cost_trend_from_proto(proto)

        assert isinstance(result, DailyCostTrend)
        assert result.data_available_from == date(2025, 1, 1)
        assert len(result.entries) == 2
        assert result.entries[0].entry_date == date(2025, 1, 1)
        assert result.entries[0].total_cost_usd == Decimal("10.00")
        assert result.entries[0].llm_cost_usd == Decimal("8.00")
        assert result.entries[1].entry_date == date(2025, 1, 2)

    def test_empty_entries(self):
        """Empty entries list is handled."""
        proto = platform_cost_pb2.DailyCostTrendResponse(
            data_available_from="2025-01-01",
        )

        result = daily_cost_trend_from_proto(proto)

        assert result.entries == []


class TestCurrentDayCostFromProto:
    """Tests for current_day_cost_from_proto converter."""

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped."""
        proto = platform_cost_pb2.CurrentDayCostResponse(
            date="2025-01-15",
            total_cost_usd="45.67",
            updated_at="2025-01-15T12:30:00+00:00",
        )
        proto.by_type["llm"] = "30.00"
        proto.by_type["sms"] = "15.67"

        result = current_day_cost_from_proto(proto)

        assert isinstance(result, CurrentDayCost)
        assert result.cost_date == date(2025, 1, 15)
        assert result.total_cost_usd == Decimal("45.67")
        assert result.by_type["llm"] == Decimal("30.00")
        assert result.by_type["sms"] == Decimal("15.67")
        assert result.updated_at == datetime(2025, 1, 15, 12, 30, 0, tzinfo=UTC)

    def test_empty_by_type(self):
        """Empty by_type map is handled."""
        proto = platform_cost_pb2.CurrentDayCostResponse(
            date="2025-01-15",
            total_cost_usd="0.00",
            updated_at="2025-01-15T00:00:00+00:00",
        )

        result = current_day_cost_from_proto(proto)

        assert result.by_type == {}


class TestLlmCostByAgentTypeFromProto:
    """Tests for llm_cost_by_agent_type_from_proto converter."""

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped."""
        proto = platform_cost_pb2.LlmCostByAgentTypeResponse(
            total_llm_cost_usd="100.00",
            period_start="2025-01-01",
            period_end="2025-01-31",
        )
        proto.agent_costs.append(
            platform_cost_pb2.AgentTypeCost(
                agent_type="extractor",
                cost_usd="60.00",
                request_count=300,
                tokens_in=50000,
                tokens_out=10000,
                percentage=60.0,
            )
        )
        proto.agent_costs.append(
            platform_cost_pb2.AgentTypeCost(
                agent_type="explorer",
                cost_usd="40.00",
                request_count=200,
                tokens_in=30000,
                tokens_out=8000,
                percentage=40.0,
            )
        )

        result = llm_cost_by_agent_type_from_proto(proto)

        assert isinstance(result, LlmCostByAgentType)
        assert result.total_llm_cost_usd == Decimal("100.00")
        assert result.period_start == date(2025, 1, 1)
        assert result.period_end == date(2025, 1, 31)
        assert len(result.agent_costs) == 2
        assert result.agent_costs[0].agent_type == "extractor"
        assert result.agent_costs[0].cost_usd == Decimal("60.00")
        assert result.agent_costs[0].tokens_in == 50000


class TestLlmCostByModelFromProto:
    """Tests for llm_cost_by_model_from_proto converter."""

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped."""
        proto = platform_cost_pb2.LlmCostByModelResponse(
            total_llm_cost_usd="100.00",
            period_start="2025-01-01",
            period_end="2025-01-31",
        )
        proto.model_costs.append(
            platform_cost_pb2.ModelCost(
                model="anthropic/claude-3-haiku",
                cost_usd="70.00",
                request_count=350,
                tokens_in=60000,
                tokens_out=12000,
                percentage=70.0,
            )
        )
        proto.model_costs.append(
            platform_cost_pb2.ModelCost(
                model="openai/gpt-4o-mini",
                cost_usd="30.00",
                request_count=150,
                tokens_in=20000,
                tokens_out=6000,
                percentage=30.0,
            )
        )

        result = llm_cost_by_model_from_proto(proto)

        assert isinstance(result, LlmCostByModel)
        assert result.total_llm_cost_usd == Decimal("100.00")
        assert len(result.model_costs) == 2
        assert result.model_costs[0].model == "anthropic/claude-3-haiku"
        assert result.model_costs[0].cost_usd == Decimal("70.00")


class TestDocumentCostSummaryFromProto:
    """Tests for document_cost_summary_from_proto converter."""

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped."""
        proto = platform_cost_pb2.DocumentCostSummaryResponse(
            total_cost_usd="50.00",
            total_pages=1000,
            avg_cost_per_page_usd="0.05",
            document_count=50,
            period_start="2025-01-01",
            period_end="2025-01-31",
        )

        result = document_cost_summary_from_proto(proto)

        assert isinstance(result, DocumentCostSummary)
        assert result.total_cost_usd == Decimal("50.00")
        assert result.total_pages == 1000
        assert result.avg_cost_per_page_usd == Decimal("0.05")
        assert result.document_count == 50


class TestEmbeddingCostByDomainFromProto:
    """Tests for embedding_cost_by_domain_from_proto converter."""

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped."""
        proto = platform_cost_pb2.EmbeddingCostByDomainResponse(
            total_embedding_cost_usd="25.00",
            period_start="2025-01-01",
            period_end="2025-01-31",
        )
        proto.domain_costs.append(
            platform_cost_pb2.DomainCost(
                knowledge_domain="tea-quality",
                cost_usd="15.00",
                tokens_total=100000,
                texts_count=500,
                percentage=60.0,
            )
        )
        proto.domain_costs.append(
            platform_cost_pb2.DomainCost(
                knowledge_domain="farming-practices",
                cost_usd="10.00",
                tokens_total=60000,
                texts_count=300,
                percentage=40.0,
            )
        )

        result = embedding_cost_by_domain_from_proto(proto)

        assert isinstance(result, EmbeddingCostByDomain)
        assert result.total_embedding_cost_usd == Decimal("25.00")
        assert len(result.domain_costs) == 2
        assert result.domain_costs[0].knowledge_domain == "tea-quality"


class TestBudgetStatusFromProto:
    """Tests for budget_status_from_proto converter."""

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped."""
        proto = platform_cost_pb2.BudgetStatusResponse(
            daily_threshold_usd="100.00",
            daily_total_usd="45.00",
            daily_alert_triggered=False,
            daily_remaining_usd="55.00",
            daily_utilization_percent=45.0,
            monthly_threshold_usd="2000.00",
            monthly_total_usd="1200.00",
            monthly_alert_triggered=False,
            monthly_remaining_usd="800.00",
            monthly_utilization_percent=60.0,
            current_day="2025-01-15",
            current_month="2025-01",
        )
        proto.by_type["llm"] = "30.00"
        proto.by_type["sms"] = "15.00"

        result = budget_status_from_proto(proto)

        assert isinstance(result, BudgetStatus)
        assert result.daily_threshold_usd == Decimal("100.00")
        assert result.daily_total_usd == Decimal("45.00")
        assert result.daily_alert_triggered is False
        assert result.daily_remaining_usd == Decimal("55.00")
        assert result.daily_utilization_percent == 45.0
        assert result.monthly_threshold_usd == Decimal("2000.00")
        assert result.monthly_total_usd == Decimal("1200.00")
        assert result.monthly_alert_triggered is False
        assert result.current_day == "2025-01-15"
        assert result.current_month == "2025-01"
        assert result.by_type["llm"] == Decimal("30.00")

    def test_alert_triggered_states(self):
        """Alert triggered states are correctly mapped."""
        proto = platform_cost_pb2.BudgetStatusResponse(
            daily_threshold_usd="100.00",
            daily_total_usd="120.00",
            daily_alert_triggered=True,
            daily_remaining_usd="-20.00",
            daily_utilization_percent=120.0,
            monthly_threshold_usd="2000.00",
            monthly_total_usd="2500.00",
            monthly_alert_triggered=True,
            monthly_remaining_usd="-500.00",
            monthly_utilization_percent=125.0,
            current_day="2025-01-15",
            current_month="2025-01",
        )

        result = budget_status_from_proto(proto)

        assert result.daily_alert_triggered is True
        assert result.monthly_alert_triggered is True


class TestBudgetThresholdConfigFromProto:
    """Tests for budget_threshold_config_from_proto converter."""

    def test_basic_fields_mapped(self):
        """Basic fields are correctly mapped."""
        proto = platform_cost_pb2.ConfigureBudgetThresholdResponse(
            daily_threshold_usd="150.00",
            monthly_threshold_usd="3000.00",
            message="Thresholds updated successfully",
            updated_at="2025-01-15T14:30:00+00:00",
        )

        result = budget_threshold_config_from_proto(proto)

        assert isinstance(result, BudgetThresholdConfig)
        assert result.daily_threshold_usd == Decimal("150.00")
        assert result.monthly_threshold_usd == Decimal("3000.00")
        assert result.message == "Thresholds updated successfully"
        assert result.updated_at == datetime(2025, 1, 15, 14, 30, 0, tzinfo=UTC)


class TestRoundTrip:
    """Tests for round-trip conversion."""

    def test_cost_summary_round_trip(self):
        """Proto -> Pydantic -> dict produces expected structure."""
        proto = platform_cost_pb2.CostSummaryResponse(
            total_cost_usd="123.45",
            period_start="2025-01-01",
            period_end="2025-01-31",
            total_requests=500,
        )
        proto.by_type.append(
            platform_cost_pb2.CostTypeBreakdown(
                cost_type="llm",
                total_cost_usd="100.00",
                total_quantity=10000,
                request_count=400,
                percentage=81.0,
            )
        )

        result = cost_summary_from_proto(proto)
        data = result.model_dump()

        assert data["total_cost_usd"] == "123.45"  # Decimal serialized as string
        assert data["period_start"] == date(2025, 1, 1)
        assert data["total_requests"] == 500
        assert len(data["by_type"]) == 1
        assert data["by_type"][0]["cost_type"] == "llm"

    def test_budget_status_round_trip(self):
        """Proto -> Pydantic -> dict produces expected structure."""
        proto = platform_cost_pb2.BudgetStatusResponse(
            daily_threshold_usd="100.00",
            daily_total_usd="45.00",
            daily_alert_triggered=False,
            daily_remaining_usd="55.00",
            daily_utilization_percent=45.0,
            monthly_threshold_usd="2000.00",
            monthly_total_usd="1200.00",
            monthly_alert_triggered=False,
            monthly_remaining_usd="800.00",
            monthly_utilization_percent=60.0,
            current_day="2025-01-15",
            current_month="2025-01",
        )

        result = budget_status_from_proto(proto)
        data = result.model_dump()

        assert data["daily_threshold_usd"] == "100.00"
        assert data["daily_alert_triggered"] is False
        assert data["current_day"] == "2025-01-15"
