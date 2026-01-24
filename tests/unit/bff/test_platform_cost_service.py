"""Tests for AdminPlatformCostService (Story 9.10a).

Tests service orchestration, transformer calls, and error propagation.
"""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bff.infrastructure.clients import ServiceUnavailableError
from bff.infrastructure.clients.platform_cost_client import PlatformCostClient
from bff.services.admin import platform_cost_service as pcs_module
from bff.services.admin.platform_cost_service import AdminPlatformCostService
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
def mock_platform_cost_client() -> MagicMock:
    """Create a mock PlatformCostClient."""
    client = MagicMock(spec=PlatformCostClient)
    client.get_cost_summary = AsyncMock()
    client.get_daily_cost_trend = AsyncMock()
    client.get_current_day_cost = AsyncMock()
    client.get_llm_cost_by_agent_type = AsyncMock()
    client.get_llm_cost_by_model = AsyncMock()
    client.get_document_cost_summary = AsyncMock()
    client.get_embedding_cost_by_domain = AsyncMock()
    client.get_budget_status = AsyncMock()
    client.configure_budget_threshold = AsyncMock()
    return client


@pytest.fixture
def platform_cost_service(mock_platform_cost_client: MagicMock) -> AdminPlatformCostService:
    """Create AdminPlatformCostService with mock client."""
    return AdminPlatformCostService(
        platform_cost_client=mock_platform_cost_client,
        transformer=PlatformCostTransformer(),
    )


@pytest.fixture
def sample_cost_summary() -> CostSummary:
    """Create a sample CostSummary domain model."""
    return CostSummary(
        total_cost_usd=Decimal("150.75"),
        total_requests=1200,
        by_type=[
            CostTypeSummary(
                cost_type="llm",
                total_cost_usd=Decimal("120.50"),
                total_quantity=5000,
                request_count=900,
                percentage=79.9,
            ),
            CostTypeSummary(
                cost_type="document",
                total_cost_usd=Decimal("30.25"),
                total_quantity=150,
                request_count=300,
                percentage=20.1,
            ),
        ],
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 24),
    )


@pytest.fixture
def sample_daily_trend() -> DailyCostTrend:
    """Create a sample DailyCostTrend."""
    return DailyCostTrend(
        entries=[
            DailyCostEntry(
                entry_date=date(2026, 1, 23),
                total_cost_usd=Decimal("5.50"),
                llm_cost_usd=Decimal("4.00"),
                document_cost_usd=Decimal("1.50"),
                embedding_cost_usd=Decimal("0"),
            ),
            DailyCostEntry(
                entry_date=date(2026, 1, 24),
                total_cost_usd=Decimal("6.25"),
                llm_cost_usd=Decimal("5.00"),
                document_cost_usd=Decimal("1.25"),
                embedding_cost_usd=Decimal("0"),
            ),
        ],
        data_available_from=date(2025, 12, 25),
    )


@pytest.fixture
def sample_current_day_cost() -> CurrentDayCost:
    """Create a sample CurrentDayCost."""
    return CurrentDayCost(
        cost_date=date(2026, 1, 24),
        total_cost_usd=Decimal("3.75"),
        by_type={"llm": Decimal("3.00"), "document": Decimal("0.75")},
        updated_at=datetime(2026, 1, 24, 14, 30, 0),
    )


@pytest.fixture(autouse=True)
def clear_cost_summary_cache():
    """Clear the module-level cost summary cache before each test."""
    pcs_module._cost_summary_cache.clear()
    yield
    pcs_module._cost_summary_cache.clear()


class TestGetCostSummary:
    """Tests for get_cost_summary method."""

    @pytest.mark.asyncio
    async def test_get_cost_summary_success(
        self,
        platform_cost_service: AdminPlatformCostService,
        mock_platform_cost_client: MagicMock,
        sample_cost_summary: CostSummary,
    ):
        """Test successful cost summary retrieval."""
        mock_platform_cost_client.get_cost_summary.return_value = sample_cost_summary

        result = await platform_cost_service.get_cost_summary(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 24),
        )

        assert result.total_cost_usd == Decimal("150.75")
        assert result.total_requests == 1200
        assert len(result.by_type) == 2
        assert result.by_type[0].cost_type == "llm"
        assert result.period_start == date(2026, 1, 1)
        assert result.period_end == date(2026, 1, 24)

        mock_platform_cost_client.get_cost_summary.assert_called_once_with(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 24),
            factory_id=None,
        )

    @pytest.mark.asyncio
    async def test_get_cost_summary_with_factory_filter(
        self,
        platform_cost_service: AdminPlatformCostService,
        mock_platform_cost_client: MagicMock,
        sample_cost_summary: CostSummary,
    ):
        """Test cost summary with factory filter."""
        mock_platform_cost_client.get_cost_summary.return_value = sample_cost_summary

        await platform_cost_service.get_cost_summary(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 24),
            factory_id="factory-001",
        )

        mock_platform_cost_client.get_cost_summary.assert_called_once_with(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 24),
            factory_id="factory-001",
        )

    @pytest.mark.asyncio
    async def test_get_cost_summary_service_unavailable(
        self,
        platform_cost_service: AdminPlatformCostService,
        mock_platform_cost_client: MagicMock,
    ):
        """Test service unavailable error propagation."""
        mock_platform_cost_client.get_cost_summary.side_effect = ServiceUnavailableError("Platform Cost unavailable")

        with pytest.raises(ServiceUnavailableError, match="Platform Cost unavailable"):
            await platform_cost_service.get_cost_summary(
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 24),
            )


class TestGetCostSummaryCaching:
    """Tests for cost summary TTL caching (AC 9.10a.1)."""

    @pytest.mark.asyncio
    async def test_second_call_returns_cached_response(
        self,
        platform_cost_service: AdminPlatformCostService,
        mock_platform_cost_client: MagicMock,
        sample_cost_summary: CostSummary,
    ):
        """Test that repeated calls within TTL return cached response."""
        mock_platform_cost_client.get_cost_summary.return_value = sample_cost_summary

        # First call - hits client
        result1 = await platform_cost_service.get_cost_summary(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 24),
        )

        # Second call - should use cache
        result2 = await platform_cost_service.get_cost_summary(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 24),
        )

        assert result1.total_cost_usd == result2.total_cost_usd
        # Client should only be called once
        assert mock_platform_cost_client.get_cost_summary.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_expires_after_ttl(
        self,
        platform_cost_service: AdminPlatformCostService,
        mock_platform_cost_client: MagicMock,
        sample_cost_summary: CostSummary,
    ):
        """Test that cache expires after 5 minutes."""
        mock_platform_cost_client.get_cost_summary.return_value = sample_cost_summary

        with patch("bff.services.admin.platform_cost_service.time") as mock_time:
            mock_time.time.return_value = 1000.0

            # First call
            await platform_cost_service.get_cost_summary(
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 24),
            )

            # Advance time past TTL (301 seconds)
            mock_time.time.return_value = 1301.0

            # Second call - cache expired, should hit client again
            await platform_cost_service.get_cost_summary(
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 24),
            )

        assert mock_platform_cost_client.get_cost_summary.call_count == 2

    @pytest.mark.asyncio
    async def test_different_params_not_shared(
        self,
        platform_cost_service: AdminPlatformCostService,
        mock_platform_cost_client: MagicMock,
        sample_cost_summary: CostSummary,
    ):
        """Test that different parameters use separate cache entries."""
        mock_platform_cost_client.get_cost_summary.return_value = sample_cost_summary

        # Call with one date range
        await platform_cost_service.get_cost_summary(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 24),
        )

        # Call with different date range - should NOT use cache
        await platform_cost_service.get_cost_summary(
            start_date=date(2026, 1, 10),
            end_date=date(2026, 1, 24),
        )

        assert mock_platform_cost_client.get_cost_summary.call_count == 2

    @pytest.mark.asyncio
    async def test_factory_id_included_in_cache_key(
        self,
        platform_cost_service: AdminPlatformCostService,
        mock_platform_cost_client: MagicMock,
        sample_cost_summary: CostSummary,
    ):
        """Test that factory_id differentiates cache entries."""
        mock_platform_cost_client.get_cost_summary.return_value = sample_cost_summary

        # Call without factory
        await platform_cost_service.get_cost_summary(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 24),
        )

        # Call with factory - should NOT use cache
        await platform_cost_service.get_cost_summary(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 24),
            factory_id="factory-001",
        )

        assert mock_platform_cost_client.get_cost_summary.call_count == 2


class TestGetDailyCostTrend:
    """Tests for get_daily_cost_trend method."""

    @pytest.mark.asyncio
    async def test_get_daily_cost_trend_default_days(
        self,
        platform_cost_service: AdminPlatformCostService,
        mock_platform_cost_client: MagicMock,
        sample_daily_trend: DailyCostTrend,
    ):
        """Test daily trend with default days parameter."""
        mock_platform_cost_client.get_daily_cost_trend.return_value = sample_daily_trend

        result = await platform_cost_service.get_daily_cost_trend()

        assert len(result.entries) == 2
        assert result.entries[0].entry_date == date(2026, 1, 23)
        assert result.entries[0].total_cost_usd == Decimal("5.50")
        assert result.data_available_from == date(2025, 12, 25)

        mock_platform_cost_client.get_daily_cost_trend.assert_called_once_with(
            start_date=None,
            end_date=None,
            days=30,
        )

    @pytest.mark.asyncio
    async def test_get_daily_cost_trend_with_dates(
        self,
        platform_cost_service: AdminPlatformCostService,
        mock_platform_cost_client: MagicMock,
        sample_daily_trend: DailyCostTrend,
    ):
        """Test daily trend with explicit date range."""
        mock_platform_cost_client.get_daily_cost_trend.return_value = sample_daily_trend

        await platform_cost_service.get_daily_cost_trend(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 24),
            days=7,
        )

        mock_platform_cost_client.get_daily_cost_trend.assert_called_once_with(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 24),
            days=7,
        )


class TestGetCurrentDayCost:
    """Tests for get_current_day_cost method."""

    @pytest.mark.asyncio
    async def test_get_current_day_cost_success(
        self,
        platform_cost_service: AdminPlatformCostService,
        mock_platform_cost_client: MagicMock,
        sample_current_day_cost: CurrentDayCost,
    ):
        """Test successful current day cost retrieval."""
        mock_platform_cost_client.get_current_day_cost.return_value = sample_current_day_cost

        result = await platform_cost_service.get_current_day_cost()

        assert result.cost_date == date(2026, 1, 24)
        assert result.total_cost_usd == Decimal("3.75")
        assert result.by_type["llm"] == Decimal("3.00")
        assert result.updated_at == datetime(2026, 1, 24, 14, 30, 0)


class TestGetLlmCostByAgentType:
    """Tests for get_llm_cost_by_agent_type method."""

    @pytest.mark.asyncio
    async def test_get_llm_cost_by_agent_type_success(
        self,
        platform_cost_service: AdminPlatformCostService,
        mock_platform_cost_client: MagicMock,
    ):
        """Test LLM cost by agent type retrieval."""
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
                AgentTypeCost(
                    agent_type="explorer",
                    cost_usd=Decimal("33.33"),
                    request_count=200,
                    tokens_in=80000,
                    tokens_out=15000,
                    percentage=40.0,
                ),
            ],
            total_llm_cost_usd=Decimal("83.33"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 24),
        )
        mock_platform_cost_client.get_llm_cost_by_agent_type.return_value = breakdown

        result = await platform_cost_service.get_llm_cost_by_agent_type()

        assert len(result.agent_costs) == 2
        assert result.agent_costs[0].agent_type == "extractor"
        assert result.agent_costs[0].cost_usd == Decimal("50.00")
        assert result.total_llm_cost_usd == Decimal("83.33")


class TestGetLlmCostByModel:
    """Tests for get_llm_cost_by_model method."""

    @pytest.mark.asyncio
    async def test_get_llm_cost_by_model_success(
        self,
        platform_cost_service: AdminPlatformCostService,
        mock_platform_cost_client: MagicMock,
    ):
        """Test LLM cost by model retrieval."""
        breakdown = LlmCostByModel(
            model_costs=[
                ModelCost(
                    model="anthropic/claude-3-haiku",
                    cost_usd=Decimal("10.00"),
                    request_count=800,
                    tokens_in=200000,
                    tokens_out=40000,
                    percentage=25.0,
                ),
            ],
            total_llm_cost_usd=Decimal("40.00"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 24),
        )
        mock_platform_cost_client.get_llm_cost_by_model.return_value = breakdown

        result = await platform_cost_service.get_llm_cost_by_model()

        assert len(result.model_costs) == 1
        assert result.model_costs[0].model == "anthropic/claude-3-haiku"
        assert result.total_llm_cost_usd == Decimal("40.00")


class TestGetDocumentCostSummary:
    """Tests for get_document_cost_summary method."""

    @pytest.mark.asyncio
    async def test_get_document_cost_summary_success(
        self,
        platform_cost_service: AdminPlatformCostService,
        mock_platform_cost_client: MagicMock,
    ):
        """Test document cost summary retrieval."""
        doc_cost = DocumentCostSummary(
            total_cost_usd=Decimal("25.00"),
            total_pages=500,
            avg_cost_per_page_usd=Decimal("0.05"),
            document_count=50,
        )
        mock_platform_cost_client.get_document_cost_summary.return_value = doc_cost

        result = await platform_cost_service.get_document_cost_summary(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 24),
        )

        assert result.total_cost_usd == Decimal("25.00")
        assert result.total_pages == 500
        assert result.avg_cost_per_page_usd == Decimal("0.05")
        assert result.document_count == 50
        assert result.period_start == date(2026, 1, 1)
        assert result.period_end == date(2026, 1, 24)


class TestGetEmbeddingCostByDomain:
    """Tests for get_embedding_cost_by_domain method."""

    @pytest.mark.asyncio
    async def test_get_embedding_cost_by_domain_success(
        self,
        platform_cost_service: AdminPlatformCostService,
        mock_platform_cost_client: MagicMock,
    ):
        """Test embedding cost by domain retrieval."""
        breakdown = EmbeddingCostByDomain(
            domain_costs=[
                DomainCost(
                    knowledge_domain="tea-quality",
                    cost_usd=Decimal("5.00"),
                    tokens_total=50000,
                    texts_count=200,
                    percentage=100.0,
                ),
            ],
            total_embedding_cost_usd=Decimal("5.00"),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 24),
        )
        mock_platform_cost_client.get_embedding_cost_by_domain.return_value = breakdown

        result = await platform_cost_service.get_embedding_cost_by_domain()

        assert len(result.domain_costs) == 1
        assert result.domain_costs[0].knowledge_domain == "tea-quality"
        assert result.total_embedding_cost_usd == Decimal("5.00")


class TestGetBudgetStatus:
    """Tests for get_budget_status method."""

    @pytest.mark.asyncio
    async def test_get_budget_status_success(
        self,
        platform_cost_service: AdminPlatformCostService,
        mock_platform_cost_client: MagicMock,
    ):
        """Test budget status retrieval."""
        status = BudgetStatus(
            daily_threshold_usd=Decimal("50.00"),
            daily_total_usd=Decimal("10.00"),
            daily_alert_triggered=False,
            daily_remaining_usd=Decimal("40.00"),
            daily_utilization_percent=20.0,
            monthly_threshold_usd=Decimal("1000.00"),
            monthly_total_usd=Decimal("150.00"),
            monthly_alert_triggered=False,
            monthly_remaining_usd=Decimal("850.00"),
            monthly_utilization_percent=15.0,
            by_type={"llm": Decimal("8.00"), "document": Decimal("2.00")},
            current_day="2026-01-24",
            current_month="2026-01",
        )
        mock_platform_cost_client.get_budget_status.return_value = status

        result = await platform_cost_service.get_budget_status()

        assert result.daily_threshold_usd == Decimal("50.00")
        assert result.daily_utilization_percent == 20.0
        assert result.monthly_threshold_usd == Decimal("1000.00")
        assert result.current_day == "2026-01-24"


class TestConfigureBudgetThreshold:
    """Tests for configure_budget_threshold method."""

    @pytest.mark.asyncio
    async def test_configure_budget_threshold_daily(
        self,
        platform_cost_service: AdminPlatformCostService,
        mock_platform_cost_client: MagicMock,
    ):
        """Test configuring daily threshold only."""
        config = BudgetThresholdConfig(
            daily_threshold_usd=Decimal("75.00"),
            monthly_threshold_usd=Decimal("1000.00"),
            message="Budget thresholds updated",
            updated_at=datetime(2026, 1, 24, 15, 0, 0),
        )
        mock_platform_cost_client.configure_budget_threshold.return_value = config

        result = await platform_cost_service.configure_budget_threshold(
            daily_threshold_usd=Decimal("75.00"),
        )

        assert result.daily_threshold_usd == Decimal("75.00")
        assert result.message == "Budget thresholds updated"

        mock_platform_cost_client.configure_budget_threshold.assert_called_once_with(
            daily_threshold_usd=Decimal("75.00"),
            monthly_threshold_usd=None,
        )

    @pytest.mark.asyncio
    async def test_configure_budget_threshold_both(
        self,
        platform_cost_service: AdminPlatformCostService,
        mock_platform_cost_client: MagicMock,
    ):
        """Test configuring both thresholds."""
        config = BudgetThresholdConfig(
            daily_threshold_usd=Decimal("100.00"),
            monthly_threshold_usd=Decimal("2000.00"),
            message="Budget thresholds updated",
            updated_at=datetime(2026, 1, 24, 15, 0, 0),
        )
        mock_platform_cost_client.configure_budget_threshold.return_value = config

        result = await platform_cost_service.configure_budget_threshold(
            daily_threshold_usd=Decimal("100.00"),
            monthly_threshold_usd=Decimal("2000.00"),
        )

        assert result.daily_threshold_usd == Decimal("100.00")
        assert result.monthly_threshold_usd == Decimal("2000.00")

    @pytest.mark.asyncio
    async def test_configure_budget_threshold_service_unavailable(
        self,
        platform_cost_service: AdminPlatformCostService,
        mock_platform_cost_client: MagicMock,
    ):
        """Test service unavailable when configuring threshold."""
        mock_platform_cost_client.configure_budget_threshold.side_effect = ServiceUnavailableError(
            "Platform Cost unavailable"
        )

        with pytest.raises(ServiceUnavailableError):
            await platform_cost_service.configure_budget_threshold(
                daily_threshold_usd=Decimal("50.00"),
            )
