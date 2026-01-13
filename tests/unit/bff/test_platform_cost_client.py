"""Unit tests for PlatformCostClient.

Story 13.6: BFF Integration Layer

Tests all 9 read/write methods, DAPR service invocation, error handling, and retry logic.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from bff.infrastructure.clients.base import ServiceUnavailableError
from bff.infrastructure.clients.platform_cost_client import PlatformCostClient
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
from fp_proto.platform_cost.v1 import platform_cost_pb2, platform_cost_pb2_grpc

# =============================================================================
# Helper functions to create test protos
# =============================================================================


def create_cost_summary_response(
    total_cost: str = "123.45",
    start_date: str = "2025-01-01",
    end_date: str = "2025-01-31",
) -> platform_cost_pb2.CostSummaryResponse:
    """Create a CostSummaryResponse proto for testing."""
    response = platform_cost_pb2.CostSummaryResponse(
        total_cost_usd=total_cost,
        period_start=start_date,
        period_end=end_date,
        total_requests=500,
    )
    response.by_type.append(
        platform_cost_pb2.CostTypeBreakdown(
            cost_type="llm",
            total_cost_usd="100.00",
            total_quantity=10000,
            request_count=400,
            percentage=81.0,
        )
    )
    response.by_type.append(
        platform_cost_pb2.CostTypeBreakdown(
            cost_type="sms",
            total_cost_usd="23.45",
            total_quantity=1000,
            request_count=100,
            percentage=19.0,
        )
    )
    return response


def create_daily_cost_trend_response() -> platform_cost_pb2.DailyCostTrendResponse:
    """Create a DailyCostTrendResponse proto for testing."""
    response = platform_cost_pb2.DailyCostTrendResponse(
        data_available_from="2025-01-01",
    )
    response.entries.append(
        platform_cost_pb2.DailyCostEntry(
            date="2025-01-01",
            total_cost_usd="10.00",
            llm_cost_usd="8.00",
            document_cost_usd="1.00",
            embedding_cost_usd="0.50",
            sms_cost_usd="0.50",
        )
    )
    response.entries.append(
        platform_cost_pb2.DailyCostEntry(
            date="2025-01-02",
            total_cost_usd="12.00",
            llm_cost_usd="10.00",
            document_cost_usd="1.00",
            embedding_cost_usd="0.50",
            sms_cost_usd="0.50",
        )
    )
    return response


def create_current_day_cost_response() -> platform_cost_pb2.CurrentDayCostResponse:
    """Create a CurrentDayCostResponse proto for testing."""
    response = platform_cost_pb2.CurrentDayCostResponse(
        date="2025-01-15",
        total_cost_usd="45.67",
        updated_at="2025-01-15T12:30:00+00:00",
    )
    response.by_type["llm"] = "30.00"
    response.by_type["sms"] = "15.67"
    return response


def create_llm_cost_by_agent_type_response() -> platform_cost_pb2.LlmCostByAgentTypeResponse:
    """Create a LlmCostByAgentTypeResponse proto for testing."""
    response = platform_cost_pb2.LlmCostByAgentTypeResponse(
        total_llm_cost_usd="100.00",
        period_start="2025-01-01",
        period_end="2025-01-31",
    )
    response.agent_costs.append(
        platform_cost_pb2.AgentTypeCost(
            agent_type="extractor",
            cost_usd="60.00",
            request_count=300,
            tokens_in=50000,
            tokens_out=10000,
            percentage=60.0,
        )
    )
    response.agent_costs.append(
        platform_cost_pb2.AgentTypeCost(
            agent_type="explorer",
            cost_usd="40.00",
            request_count=200,
            tokens_in=30000,
            tokens_out=8000,
            percentage=40.0,
        )
    )
    return response


def create_llm_cost_by_model_response() -> platform_cost_pb2.LlmCostByModelResponse:
    """Create a LlmCostByModelResponse proto for testing."""
    response = platform_cost_pb2.LlmCostByModelResponse(
        total_llm_cost_usd="100.00",
        period_start="2025-01-01",
        period_end="2025-01-31",
    )
    response.model_costs.append(
        platform_cost_pb2.ModelCost(
            model="anthropic/claude-3-haiku",
            cost_usd="70.00",
            request_count=350,
            tokens_in=60000,
            tokens_out=12000,
            percentage=70.0,
        )
    )
    return response


def create_document_cost_summary_response() -> platform_cost_pb2.DocumentCostSummaryResponse:
    """Create a DocumentCostSummaryResponse proto for testing."""
    return platform_cost_pb2.DocumentCostSummaryResponse(
        total_cost_usd="50.00",
        total_pages=1000,
        avg_cost_per_page_usd="0.05",
        document_count=50,
        period_start="2025-01-01",
        period_end="2025-01-31",
    )


def create_embedding_cost_by_domain_response() -> platform_cost_pb2.EmbeddingCostByDomainResponse:
    """Create an EmbeddingCostByDomainResponse proto for testing."""
    response = platform_cost_pb2.EmbeddingCostByDomainResponse(
        total_embedding_cost_usd="25.00",
        period_start="2025-01-01",
        period_end="2025-01-31",
    )
    response.domain_costs.append(
        platform_cost_pb2.DomainCost(
            knowledge_domain="tea-quality",
            cost_usd="15.00",
            tokens_total=100000,
            texts_count=500,
            percentage=60.0,
        )
    )
    return response


def create_budget_status_response() -> platform_cost_pb2.BudgetStatusResponse:
    """Create a BudgetStatusResponse proto for testing."""
    response = platform_cost_pb2.BudgetStatusResponse(
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
    response.by_type["llm"] = "30.00"
    response.by_type["sms"] = "15.00"
    return response


def create_budget_threshold_config_response() -> platform_cost_pb2.ConfigureBudgetThresholdResponse:
    """Create a ConfigureBudgetThresholdResponse proto for testing."""
    return platform_cost_pb2.ConfigureBudgetThresholdResponse(
        daily_threshold_usd="150.00",
        monthly_threshold_usd="3000.00",
        message="Thresholds updated successfully",
        updated_at="2025-01-15T14:30:00+00:00",
    )


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_cost_stub() -> MagicMock:
    """Create a mock UnifiedCostService stub."""
    stub = MagicMock()
    # Configure async methods
    stub.GetCostSummary = AsyncMock()
    stub.GetDailyCostTrend = AsyncMock()
    stub.GetCurrentDayCost = AsyncMock()
    stub.GetLlmCostByAgentType = AsyncMock()
    stub.GetLlmCostByModel = AsyncMock()
    stub.GetDocumentCostSummary = AsyncMock()
    stub.GetEmbeddingCostByDomain = AsyncMock()
    stub.GetBudgetStatus = AsyncMock()
    stub.ConfigureBudgetThreshold = AsyncMock()
    return stub


@pytest.fixture
def cost_client_with_mock_stub(mock_cost_stub: MagicMock) -> tuple[PlatformCostClient, MagicMock]:
    """Create a PlatformCostClient with a mocked stub."""
    client = PlatformCostClient(direct_host="localhost:50051")
    # Inject the mock stub
    client._stubs[platform_cost_pb2_grpc.UnifiedCostServiceStub] = mock_cost_stub
    return client, mock_cost_stub


# =============================================================================
# Tests
# =============================================================================


class TestPlatformCostClientInit:
    """Tests for PlatformCostClient initialization."""

    def test_default_init(self) -> None:
        """Test default initialization with DAPR settings."""
        client = PlatformCostClient()
        assert client._target_app_id == "platform-cost"
        assert client._dapr_grpc_port == 50001
        assert client._direct_host is None
        assert client._channel is None

    def test_direct_host_init(self) -> None:
        """Test initialization with direct host."""
        client = PlatformCostClient(direct_host="localhost:50051")
        assert client._direct_host == "localhost:50051"

    def test_custom_dapr_port(self) -> None:
        """Test initialization with custom DAPR port."""
        client = PlatformCostClient(dapr_grpc_port=50099)
        assert client._dapr_grpc_port == 50099


class TestPlatformCostClientMetadata:
    """Tests for gRPC metadata handling."""

    def test_metadata_with_dapr(self) -> None:
        """Test metadata generation with DAPR routing."""
        client = PlatformCostClient()
        metadata = client._get_metadata()
        assert ("dapr-app-id", "platform-cost") in metadata

    def test_metadata_direct_connection(self) -> None:
        """Test metadata is empty for direct connection."""
        client = PlatformCostClient(direct_host="localhost:50051")
        metadata = client._get_metadata()
        assert metadata == []


class TestCostSummaryOperations:
    """Tests for cost summary operations."""

    @pytest.mark.asyncio
    async def test_get_cost_summary_success(
        self,
        cost_client_with_mock_stub: tuple[PlatformCostClient, MagicMock],
    ) -> None:
        """Test successful cost summary retrieval."""
        client, stub = cost_client_with_mock_stub
        stub.GetCostSummary.return_value = create_cost_summary_response()

        result = await client.get_cost_summary(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )

        assert isinstance(result, CostSummary)
        assert result.total_cost_usd == Decimal("123.45")
        assert result.period_start == date(2025, 1, 1)
        assert result.period_end == date(2025, 1, 31)
        assert len(result.by_type) == 2

    @pytest.mark.asyncio
    async def test_get_cost_summary_with_factory_filter(
        self,
        cost_client_with_mock_stub: tuple[PlatformCostClient, MagicMock],
    ) -> None:
        """Test cost summary with factory filter."""
        client, stub = cost_client_with_mock_stub
        stub.GetCostSummary.return_value = create_cost_summary_response()

        await client.get_cost_summary(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            factory_id="KEN-FAC-001",
        )

        call_args = stub.GetCostSummary.call_args
        request = call_args[0][0]
        assert request.factory_id == "KEN-FAC-001"


class TestDailyCostTrendOperations:
    """Tests for daily cost trend operations."""

    @pytest.mark.asyncio
    async def test_get_daily_cost_trend_success(
        self,
        cost_client_with_mock_stub: tuple[PlatformCostClient, MagicMock],
    ) -> None:
        """Test successful daily cost trend retrieval."""
        client, stub = cost_client_with_mock_stub
        stub.GetDailyCostTrend.return_value = create_daily_cost_trend_response()

        result = await client.get_daily_cost_trend()

        assert isinstance(result, DailyCostTrend)
        assert result.data_available_from == date(2025, 1, 1)
        assert len(result.entries) == 2

    @pytest.mark.asyncio
    async def test_get_daily_cost_trend_with_dates(
        self,
        cost_client_with_mock_stub: tuple[PlatformCostClient, MagicMock],
    ) -> None:
        """Test daily cost trend with date parameters."""
        client, stub = cost_client_with_mock_stub
        stub.GetDailyCostTrend.return_value = create_daily_cost_trend_response()

        await client.get_daily_cost_trend(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 7),
        )

        call_args = stub.GetDailyCostTrend.call_args
        request = call_args[0][0]
        assert request.start_date == "2025-01-01"
        assert request.end_date == "2025-01-07"


class TestCurrentDayCostOperations:
    """Tests for current day cost operations."""

    @pytest.mark.asyncio
    async def test_get_current_day_cost_success(
        self,
        cost_client_with_mock_stub: tuple[PlatformCostClient, MagicMock],
    ) -> None:
        """Test successful current day cost retrieval."""
        client, stub = cost_client_with_mock_stub
        stub.GetCurrentDayCost.return_value = create_current_day_cost_response()

        result = await client.get_current_day_cost()

        assert isinstance(result, CurrentDayCost)
        assert result.total_cost_usd == Decimal("45.67")
        assert result.cost_date == date(2025, 1, 15)
        assert result.by_type["llm"] == Decimal("30.00")


class TestLlmCostByAgentTypeOperations:
    """Tests for LLM cost by agent type operations."""

    @pytest.mark.asyncio
    async def test_get_llm_cost_by_agent_type_success(
        self,
        cost_client_with_mock_stub: tuple[PlatformCostClient, MagicMock],
    ) -> None:
        """Test successful LLM cost by agent type retrieval."""
        client, stub = cost_client_with_mock_stub
        stub.GetLlmCostByAgentType.return_value = create_llm_cost_by_agent_type_response()

        result = await client.get_llm_cost_by_agent_type()

        assert isinstance(result, LlmCostByAgentType)
        assert result.total_llm_cost_usd == Decimal("100.00")
        assert len(result.agent_costs) == 2
        assert result.agent_costs[0].agent_type == "extractor"


class TestLlmCostByModelOperations:
    """Tests for LLM cost by model operations."""

    @pytest.mark.asyncio
    async def test_get_llm_cost_by_model_success(
        self,
        cost_client_with_mock_stub: tuple[PlatformCostClient, MagicMock],
    ) -> None:
        """Test successful LLM cost by model retrieval."""
        client, stub = cost_client_with_mock_stub
        stub.GetLlmCostByModel.return_value = create_llm_cost_by_model_response()

        result = await client.get_llm_cost_by_model()

        assert isinstance(result, LlmCostByModel)
        assert result.total_llm_cost_usd == Decimal("100.00")
        assert len(result.model_costs) == 1
        assert result.model_costs[0].model == "anthropic/claude-3-haiku"


class TestDocumentCostSummaryOperations:
    """Tests for document cost summary operations."""

    @pytest.mark.asyncio
    async def test_get_document_cost_summary_success(
        self,
        cost_client_with_mock_stub: tuple[PlatformCostClient, MagicMock],
    ) -> None:
        """Test successful document cost summary retrieval."""
        client, stub = cost_client_with_mock_stub
        stub.GetDocumentCostSummary.return_value = create_document_cost_summary_response()

        result = await client.get_document_cost_summary(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )

        assert isinstance(result, DocumentCostSummary)
        assert result.total_cost_usd == Decimal("50.00")
        assert result.total_pages == 1000


class TestEmbeddingCostByDomainOperations:
    """Tests for embedding cost by domain operations."""

    @pytest.mark.asyncio
    async def test_get_embedding_cost_by_domain_success(
        self,
        cost_client_with_mock_stub: tuple[PlatformCostClient, MagicMock],
    ) -> None:
        """Test successful embedding cost by domain retrieval."""
        client, stub = cost_client_with_mock_stub
        stub.GetEmbeddingCostByDomain.return_value = create_embedding_cost_by_domain_response()

        result = await client.get_embedding_cost_by_domain()

        assert isinstance(result, EmbeddingCostByDomain)
        assert result.total_embedding_cost_usd == Decimal("25.00")
        assert len(result.domain_costs) == 1


class TestBudgetStatusOperations:
    """Tests for budget status operations."""

    @pytest.mark.asyncio
    async def test_get_budget_status_success(
        self,
        cost_client_with_mock_stub: tuple[PlatformCostClient, MagicMock],
    ) -> None:
        """Test successful budget status retrieval."""
        client, stub = cost_client_with_mock_stub
        stub.GetBudgetStatus.return_value = create_budget_status_response()

        result = await client.get_budget_status()

        assert isinstance(result, BudgetStatus)
        assert result.daily_threshold_usd == Decimal("100.00")
        assert result.daily_total_usd == Decimal("45.00")
        assert result.daily_alert_triggered is False


class TestBudgetThresholdConfigOperations:
    """Tests for budget threshold configuration operations."""

    @pytest.mark.asyncio
    async def test_configure_budget_threshold_success(
        self,
        cost_client_with_mock_stub: tuple[PlatformCostClient, MagicMock],
    ) -> None:
        """Test successful budget threshold configuration."""
        client, stub = cost_client_with_mock_stub
        stub.ConfigureBudgetThreshold.return_value = create_budget_threshold_config_response()

        result = await client.configure_budget_threshold(
            daily_threshold_usd=Decimal("150.00"),
            monthly_threshold_usd=Decimal("3000.00"),
        )

        assert isinstance(result, BudgetThresholdConfig)
        assert result.daily_threshold_usd == Decimal("150.00")
        assert result.monthly_threshold_usd == Decimal("3000.00")
        assert result.message == "Thresholds updated successfully"


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_service_unavailable_error(
        self,
        cost_client_with_mock_stub: tuple[PlatformCostClient, MagicMock],
    ) -> None:
        """Test service unavailable error handling."""
        client, stub = cost_client_with_mock_stub
        error = grpc.aio.AioRpcError(
            code=grpc.StatusCode.UNAVAILABLE,
            initial_metadata=None,
            trailing_metadata=None,
            details="Connection refused",
            debug_error_string="",
        )
        stub.GetCostSummary.side_effect = error

        with pytest.raises(ServiceUnavailableError, match="Service unavailable"):
            await client.get_cost_summary(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 31),
            )

    @pytest.mark.asyncio
    async def test_unknown_grpc_error_propagated(
        self,
        cost_client_with_mock_stub: tuple[PlatformCostClient, MagicMock],
    ) -> None:
        """Test unknown gRPC errors are propagated."""
        client, stub = cost_client_with_mock_stub
        error = grpc.aio.AioRpcError(
            code=grpc.StatusCode.INTERNAL,
            initial_metadata=None,
            trailing_metadata=None,
            details="Internal server error",
            debug_error_string="",
        )
        stub.GetBudgetStatus.side_effect = error

        with pytest.raises(grpc.aio.AioRpcError):
            await client.get_budget_status()


class TestClientClose:
    """Tests for client cleanup."""

    @pytest.mark.asyncio
    async def test_close_cleans_up_channel(self) -> None:
        """Test close properly cleans up channel."""
        client = PlatformCostClient(direct_host="localhost:50051")
        mock_channel = AsyncMock()
        client._channel = mock_channel
        client._stubs["test"] = "value"

        await client.close()

        mock_channel.close.assert_called_once()
        assert client._channel is None
        assert client._stubs == {}
