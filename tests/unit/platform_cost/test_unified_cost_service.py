"""Unit tests for UnifiedCostService gRPC servicer.

Story 13.4: gRPC UnifiedCostService

Tests:
- GetCostSummary returns proper response
- GetDailyCostTrend includes data_available_from (AC #2)
- GetCurrentDayCost returns real-time totals
- GetBudgetStatus returns thresholds and utilization
- ConfigureBudgetThreshold persists and updates in-memory state (AC #3)
- Invalid date format returns INVALID_ARGUMENT
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from fp_proto.platform_cost.v1 import platform_cost_pb2
from platform_cost.api.unified_cost_service import UnifiedCostServiceServicer
from platform_cost.domain.cost_event import (
    AgentTypeCost,
    CostTypeSummary,
    CurrentDayCost,
    DailyCostEntry,
    DocumentCostSummary,
    DomainCost,
    ModelCost,
)
from platform_cost.infrastructure.repositories.threshold_repository import (
    ThresholdConfig,
)
from platform_cost.services.budget_monitor import BudgetStatus


@pytest.fixture
def mock_cost_repository():
    """Create mock cost repository."""
    repo = MagicMock()
    repo.data_available_from = datetime(2024, 10, 15, tzinfo=UTC)
    return repo


@pytest.fixture
def mock_budget_monitor():
    """Create mock budget monitor."""
    return MagicMock()


@pytest.fixture
def mock_threshold_repository():
    """Create mock threshold repository."""
    return MagicMock()


@pytest.fixture
def mock_context():
    """Create mock gRPC context."""
    context = AsyncMock()
    return context


@pytest.fixture
def servicer(mock_cost_repository, mock_budget_monitor, mock_threshold_repository):
    """Create UnifiedCostServiceServicer with mocks."""
    return UnifiedCostServiceServicer(
        cost_repository=mock_cost_repository,
        budget_monitor=mock_budget_monitor,
        threshold_repository=mock_threshold_repository,
    )


class TestGetCostSummary:
    """Tests for GetCostSummary RPC."""

    @pytest.mark.asyncio
    async def test_returns_cost_summary_response(self, servicer, mock_cost_repository, mock_context) -> None:
        """Test GetCostSummary returns proper response structure."""
        mock_cost_repository.get_summary_by_type = AsyncMock(
            return_value=[
                CostTypeSummary(
                    cost_type="llm",
                    total_cost_usd=Decimal("5.00"),
                    total_quantity=50000,
                    request_count=100,
                    percentage=83.33,
                ),
                CostTypeSummary(
                    cost_type="document",
                    total_cost_usd=Decimal("1.00"),
                    total_quantity=20,
                    request_count=5,
                    percentage=16.67,
                ),
            ]
        )

        request = platform_cost_pb2.CostSummaryRequest(
            start_date="2024-01-01",
            end_date="2024-01-31",
        )

        response = await servicer.GetCostSummary(request, mock_context)

        assert response.total_cost_usd == "6.00"
        assert len(response.by_type) == 2
        assert response.by_type[0].cost_type == "llm"
        assert response.by_type[0].total_cost_usd == "5.00"
        assert response.period_start == "2024-01-01"
        assert response.period_end == "2024-01-31"

    @pytest.mark.asyncio
    async def test_invalid_date_format_aborts(self, servicer, mock_context) -> None:
        """Test invalid date format returns INVALID_ARGUMENT."""
        # Make abort raise an exception to simulate gRPC behavior
        import grpc

        mock_context.abort = AsyncMock(side_effect=grpc.RpcError())

        request = platform_cost_pb2.CostSummaryRequest(
            start_date="not-a-date",
            end_date="2024-01-31",
        )

        with pytest.raises(Exception):  # Can be ValueError or grpc.RpcError
            await servicer.GetCostSummary(request, mock_context)

    @pytest.mark.asyncio
    async def test_invalid_date_range_aborts(self, servicer, mock_context) -> None:
        """Test start_date > end_date returns INVALID_ARGUMENT."""
        import grpc

        mock_context.abort = AsyncMock(side_effect=grpc.RpcError())

        request = platform_cost_pb2.CostSummaryRequest(
            start_date="2024-12-31",
            end_date="2024-01-01",  # end before start
        )

        with pytest.raises(Exception):
            await servicer.GetCostSummary(request, mock_context)

        mock_context.abort.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_factory_id_to_repository(self, servicer, mock_cost_repository, mock_context) -> None:
        """Test factory_id is passed to repository when provided."""
        mock_cost_repository.get_summary_by_type = AsyncMock(return_value=[])

        request = platform_cost_pb2.CostSummaryRequest(
            start_date="2024-01-01",
            end_date="2024-01-31",
            factory_id="FAC-001",
        )

        await servicer.GetCostSummary(request, mock_context)

        mock_cost_repository.get_summary_by_type.assert_called_once()
        call_kwargs = mock_cost_repository.get_summary_by_type.call_args.kwargs
        assert call_kwargs["factory_id"] == "FAC-001"


class TestGetDailyCostTrend:
    """Tests for GetDailyCostTrend RPC."""

    @pytest.mark.asyncio
    async def test_returns_data_available_from(self, servicer, mock_cost_repository, mock_context) -> None:
        """Test GetDailyCostTrend includes data_available_from (AC #2)."""
        mock_cost_repository.get_daily_trend = AsyncMock(
            return_value=[
                DailyCostEntry(
                    entry_date=date(2024, 1, 1),
                    total_cost_usd=Decimal("2.50"),
                    llm_cost_usd=Decimal("2.00"),
                    document_cost_usd=Decimal("0.50"),
                    embedding_cost_usd=Decimal("0"),
                    sms_cost_usd=Decimal("0"),
                ),
            ]
        )

        request = platform_cost_pb2.DailyCostTrendRequest()

        response = await servicer.GetDailyCostTrend(request, mock_context)

        # AC #2: data_available_from indicates earliest available date
        assert response.data_available_from == "2024-10-15"
        assert len(response.entries) == 1
        assert response.entries[0].date == "2024-01-01"


class TestGetCurrentDayCost:
    """Tests for GetCurrentDayCost RPC."""

    @pytest.mark.asyncio
    async def test_returns_current_day_cost(self, servicer, mock_cost_repository, mock_context) -> None:
        """Test GetCurrentDayCost returns real-time totals."""
        now = datetime.now(UTC)
        today = date.today()

        mock_cost_repository.get_current_day_cost = AsyncMock(
            return_value=CurrentDayCost(
                cost_date=today,
                total_cost_usd=Decimal("3.75"),
                by_type={
                    "llm": Decimal("3.00"),
                    "document": Decimal("0.75"),
                },
                updated_at=now,
            )
        )

        request = platform_cost_pb2.CurrentDayCostRequest()

        response = await servicer.GetCurrentDayCost(request, mock_context)

        assert response.total_cost_usd == "3.75"
        assert "llm" in response.by_type
        assert response.by_type["llm"] == "3.00"


class TestGetLlmCostByAgentType:
    """Tests for GetLlmCostByAgentType RPC."""

    @pytest.mark.asyncio
    async def test_returns_agent_type_breakdown(self, servicer, mock_cost_repository, mock_context) -> None:
        """Test GetLlmCostByAgentType returns per-agent breakdown."""
        mock_cost_repository.get_llm_cost_by_agent_type = AsyncMock(
            return_value=[
                AgentTypeCost(
                    agent_type="extractor",
                    cost_usd=Decimal("4.00"),
                    request_count=80,
                    tokens_in=50000,
                    tokens_out=25000,
                    percentage=80.0,
                ),
                AgentTypeCost(
                    agent_type="explorer",
                    cost_usd=Decimal("1.00"),
                    request_count=20,
                    tokens_in=10000,
                    tokens_out=5000,
                    percentage=20.0,
                ),
            ]
        )

        request = platform_cost_pb2.LlmCostByAgentTypeRequest()

        response = await servicer.GetLlmCostByAgentType(request, mock_context)

        assert len(response.agent_costs) == 2
        assert response.agent_costs[0].agent_type == "extractor"
        assert response.total_llm_cost_usd == "5.00"


class TestGetLlmCostByModel:
    """Tests for GetLlmCostByModel RPC."""

    @pytest.mark.asyncio
    async def test_returns_model_breakdown(self, servicer, mock_cost_repository, mock_context) -> None:
        """Test GetLlmCostByModel returns per-model breakdown."""
        mock_cost_repository.get_llm_cost_by_model = AsyncMock(
            return_value=[
                ModelCost(
                    model="anthropic/claude-3-haiku",
                    cost_usd=Decimal("2.00"),
                    request_count=100,
                    tokens_in=100000,
                    tokens_out=50000,
                    percentage=100.0,
                ),
            ]
        )

        request = platform_cost_pb2.LlmCostByModelRequest()

        response = await servicer.GetLlmCostByModel(request, mock_context)

        assert len(response.model_costs) == 1
        assert response.model_costs[0].model == "anthropic/claude-3-haiku"


class TestGetDocumentCostSummary:
    """Tests for GetDocumentCostSummary RPC."""

    @pytest.mark.asyncio
    async def test_returns_document_summary(self, servicer, mock_cost_repository, mock_context) -> None:
        """Test GetDocumentCostSummary returns document cost details."""
        mock_cost_repository.get_document_cost_summary = AsyncMock(
            return_value=DocumentCostSummary(
                total_cost_usd=Decimal("2.50"),
                total_pages=50,
                avg_cost_per_page_usd=Decimal("0.05"),
                document_count=10,
            )
        )

        request = platform_cost_pb2.DocumentCostSummaryRequest(
            start_date="2024-01-01",
            end_date="2024-01-31",
        )

        response = await servicer.GetDocumentCostSummary(request, mock_context)

        assert response.total_cost_usd == "2.50"
        assert response.total_pages == 50
        assert response.avg_cost_per_page_usd == "0.05"


class TestGetEmbeddingCostByDomain:
    """Tests for GetEmbeddingCostByDomain RPC."""

    @pytest.mark.asyncio
    async def test_returns_domain_breakdown(self, servicer, mock_cost_repository, mock_context) -> None:
        """Test GetEmbeddingCostByDomain returns per-domain breakdown."""
        mock_cost_repository.get_embedding_cost_by_domain = AsyncMock(
            return_value=[
                DomainCost(
                    knowledge_domain="tea-quality",
                    cost_usd=Decimal("0.50"),
                    tokens_total=50000,
                    texts_count=100,
                    percentage=100.0,
                ),
            ]
        )

        request = platform_cost_pb2.EmbeddingCostByDomainRequest()

        response = await servicer.GetEmbeddingCostByDomain(request, mock_context)

        assert len(response.domain_costs) == 1
        assert response.domain_costs[0].knowledge_domain == "tea-quality"


class TestGetBudgetStatus:
    """Tests for GetBudgetStatus RPC."""

    @pytest.mark.asyncio
    async def test_returns_budget_status(self, servicer, mock_budget_monitor, mock_context) -> None:
        """Test GetBudgetStatus returns thresholds and utilization."""
        mock_budget_monitor.get_status.return_value = BudgetStatus(
            daily_threshold_usd="10.00",
            daily_total_usd="3.50",
            daily_alert_triggered=False,
            daily_remaining_usd="6.50",
            daily_utilization_percent=35.0,
            monthly_threshold_usd="100.00",
            monthly_total_usd="25.00",
            monthly_alert_triggered=False,
            monthly_remaining_usd="75.00",
            monthly_utilization_percent=25.0,
            by_type={"llm": "3.00", "document": "0.50"},
            current_day="2024-01-15",
            current_month="2024-01",
        )

        request = platform_cost_pb2.BudgetStatusRequest()

        response = await servicer.GetBudgetStatus(request, mock_context)

        assert response.daily_threshold_usd == "10.00"
        assert response.daily_utilization_percent == 35.0
        assert response.monthly_utilization_percent == 25.0


class TestConfigureBudgetThreshold:
    """Tests for ConfigureBudgetThreshold RPC."""

    @pytest.mark.asyncio
    async def test_updates_thresholds_and_persists(
        self, servicer, mock_threshold_repository, mock_budget_monitor, mock_context
    ) -> None:
        """Test ConfigureBudgetThreshold persists to MongoDB and updates in-memory (AC #3)."""
        mock_threshold_repository.set_thresholds = AsyncMock(
            return_value=ThresholdConfig(
                daily_threshold_usd=Decimal("20.00"),
                monthly_threshold_usd=Decimal("200.00"),
                updated_at=datetime.now(UTC),
                updated_by="grpc_client",
            )
        )

        request = platform_cost_pb2.ConfigureBudgetThresholdRequest(
            daily_threshold_usd="20.00",
            monthly_threshold_usd="200.00",
        )

        response = await servicer.ConfigureBudgetThreshold(request, mock_context)

        # Verify MongoDB persistence
        mock_threshold_repository.set_thresholds.assert_called_once()

        # Verify in-memory update
        mock_budget_monitor.update_thresholds.assert_called()

        # Verify response
        assert response.daily_threshold_usd == "20.00"
        assert response.monthly_threshold_usd == "200.00"
        assert "successfully" in response.message

    @pytest.mark.asyncio
    async def test_negative_threshold_aborts(self, servicer, mock_context) -> None:
        """Test negative threshold returns INVALID_ARGUMENT."""
        import grpc

        mock_context.abort = AsyncMock(side_effect=grpc.RpcError())

        request = platform_cost_pb2.ConfigureBudgetThresholdRequest(
            daily_threshold_usd="-5.00",
        )

        with pytest.raises(Exception):  # Can be ValueError or grpc.RpcError
            await servicer.ConfigureBudgetThreshold(request, mock_context)
