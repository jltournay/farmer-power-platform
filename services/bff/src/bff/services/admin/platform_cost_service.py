"""Platform Cost service for admin API (Story 9.10a).

Orchestrates PlatformCostClient calls and transforms responses to API schemas.
"""

import time
from datetime import date
from decimal import Decimal

from bff.api.schemas.admin.platform_cost_schemas import (
    BudgetConfigResponse,
    BudgetStatusResponse,
    CostSummaryResponse,
    CurrentDayCostResponse,
    DailyTrendResponse,
    DocumentCostResponse,
    EmbeddingByDomainResponse,
    LlmByAgentTypeResponse,
    LlmByModelResponse,
)
from bff.infrastructure.clients.platform_cost_client import PlatformCostClient
from bff.services.base_service import BaseService
from bff.transformers.admin.platform_cost_transformer import PlatformCostTransformer

# Module-level TTL cache for cost summary (AC 9.10a.1: cached for 5 minutes)
_CACHE_TTL_SECONDS = 300
_cost_summary_cache: dict[str, tuple[float, CostSummaryResponse]] = {}


class AdminPlatformCostService(BaseService):
    """Service for admin platform cost operations.

    Orchestrates PlatformCostClient calls and transforms to API schemas.
    """

    def __init__(
        self,
        platform_cost_client: PlatformCostClient | None = None,
        transformer: PlatformCostTransformer | None = None,
    ) -> None:
        """Initialize the platform cost service.

        Args:
            platform_cost_client: Optional PlatformCostClient (created if not provided).
            transformer: Optional PlatformCostTransformer (created if not provided).
        """
        super().__init__()
        self._client = platform_cost_client or PlatformCostClient()
        self._transformer = transformer or PlatformCostTransformer()

    async def get_cost_summary(
        self,
        start_date: date,
        end_date: date,
        factory_id: str | None = None,
    ) -> CostSummaryResponse:
        """Get cost summary for a date range.

        Cached for 5 minutes per AC 9.10a.1.

        Args:
            start_date: Start of date range (inclusive).
            end_date: End of date range (inclusive).
            factory_id: Optional filter by factory.

        Returns:
            CostSummaryResponse with total and breakdown.
        """
        cache_key = f"{start_date}:{end_date}:{factory_id}"

        # Check TTL cache (AC 9.10a.1: cached for 5 minutes)
        if cache_key in _cost_summary_cache:
            cached_time, cached_response = _cost_summary_cache[cache_key]
            if time.time() - cached_time < _CACHE_TTL_SECONDS:
                self._logger.info("cost_summary_cache_hit", cache_key=cache_key)
                return cached_response
            del _cost_summary_cache[cache_key]

        self._logger.info(
            "getting_cost_summary",
            start_date=str(start_date),
            end_date=str(end_date),
            factory_id=factory_id,
        )

        summary = await self._client.get_cost_summary(
            start_date=start_date,
            end_date=end_date,
            factory_id=factory_id,
        )

        response = self._transformer.to_cost_summary_response(summary)

        # Store in TTL cache
        _cost_summary_cache[cache_key] = (time.time(), response)

        self._logger.info(
            "got_cost_summary",
            total_cost=str(summary.total_cost_usd),
            type_count=len(summary.by_type),
        )

        return response

    async def get_daily_cost_trend(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        days: int = 30,
    ) -> DailyTrendResponse:
        """Get daily cost trend for chart visualization.

        Args:
            start_date: Optional start of date range.
            end_date: Optional end of date range.
            days: Number of days if dates not specified (default: 30).

        Returns:
            DailyTrendResponse with daily entries.
        """
        self._logger.info(
            "getting_daily_cost_trend",
            start_date=str(start_date) if start_date else None,
            end_date=str(end_date) if end_date else None,
            days=days,
        )

        trend = await self._client.get_daily_cost_trend(
            start_date=start_date,
            end_date=end_date,
            days=days,
        )

        response = self._transformer.to_daily_trend_response(trend)

        self._logger.info(
            "got_daily_cost_trend",
            entry_count=len(trend.entries),
        )

        return response

    async def get_current_day_cost(self) -> CurrentDayCostResponse:
        """Get current day running cost total.

        Returns:
            CurrentDayCostResponse with today's running total.
        """
        self._logger.info("getting_current_day_cost")

        current = await self._client.get_current_day_cost()
        response = self._transformer.to_current_day_cost_response(current)

        self._logger.info(
            "got_current_day_cost",
            total_cost=str(current.total_cost_usd),
        )

        return response

    async def get_llm_cost_by_agent_type(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> LlmByAgentTypeResponse:
        """Get LLM cost breakdown by agent type.

        Args:
            start_date: Optional start of date range.
            end_date: Optional end of date range.

        Returns:
            LlmByAgentTypeResponse with per-agent breakdown.
        """
        self._logger.info(
            "getting_llm_cost_by_agent_type",
            start_date=str(start_date) if start_date else None,
            end_date=str(end_date) if end_date else None,
        )

        breakdown = await self._client.get_llm_cost_by_agent_type(
            start_date=start_date,
            end_date=end_date,
        )

        response = self._transformer.to_llm_by_agent_type_response(breakdown)

        self._logger.info(
            "got_llm_cost_by_agent_type",
            agent_count=len(breakdown.agent_costs),
        )

        return response

    async def get_llm_cost_by_model(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> LlmByModelResponse:
        """Get LLM cost breakdown by model.

        Args:
            start_date: Optional start of date range.
            end_date: Optional end of date range.

        Returns:
            LlmByModelResponse with per-model breakdown.
        """
        self._logger.info(
            "getting_llm_cost_by_model",
            start_date=str(start_date) if start_date else None,
            end_date=str(end_date) if end_date else None,
        )

        breakdown = await self._client.get_llm_cost_by_model(
            start_date=start_date,
            end_date=end_date,
        )

        response = self._transformer.to_llm_by_model_response(breakdown)

        self._logger.info(
            "got_llm_cost_by_model",
            model_count=len(breakdown.model_costs),
        )

        return response

    async def get_document_cost_summary(
        self,
        start_date: date,
        end_date: date,
    ) -> DocumentCostResponse:
        """Get document processing cost summary.

        Args:
            start_date: Start of date range (required).
            end_date: End of date range (required).

        Returns:
            DocumentCostResponse with document cost summary.
        """
        self._logger.info(
            "getting_document_cost_summary",
            start_date=str(start_date),
            end_date=str(end_date),
        )

        doc_cost = await self._client.get_document_cost_summary(
            start_date=start_date,
            end_date=end_date,
        )

        response = self._transformer.to_document_cost_response(
            doc_cost=doc_cost,
            period_start=start_date,
            period_end=end_date,
        )

        self._logger.info(
            "got_document_cost_summary",
            total_cost=str(doc_cost.total_cost_usd),
            document_count=doc_cost.document_count,
        )

        return response

    async def get_embedding_cost_by_domain(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> EmbeddingByDomainResponse:
        """Get embedding cost breakdown by knowledge domain.

        Args:
            start_date: Optional start of date range.
            end_date: Optional end of date range.

        Returns:
            EmbeddingByDomainResponse with per-domain breakdown.
        """
        self._logger.info(
            "getting_embedding_cost_by_domain",
            start_date=str(start_date) if start_date else None,
            end_date=str(end_date) if end_date else None,
        )

        breakdown = await self._client.get_embedding_cost_by_domain(
            start_date=start_date,
            end_date=end_date,
        )

        response = self._transformer.to_embedding_by_domain_response(breakdown)

        self._logger.info(
            "got_embedding_cost_by_domain",
            domain_count=len(breakdown.domain_costs),
        )

        return response

    async def get_budget_status(self) -> BudgetStatusResponse:
        """Get current budget thresholds and utilization.

        Returns:
            BudgetStatusResponse with budget status.
        """
        self._logger.info("getting_budget_status")

        status = await self._client.get_budget_status()
        response = self._transformer.to_budget_status_response(status)

        self._logger.info(
            "got_budget_status",
            daily_utilization=status.daily_utilization_percent,
            monthly_utilization=status.monthly_utilization_percent,
        )

        return response

    async def configure_budget_threshold(
        self,
        daily_threshold_usd: Decimal | None = None,
        monthly_threshold_usd: Decimal | None = None,
    ) -> BudgetConfigResponse:
        """Configure budget thresholds.

        Args:
            daily_threshold_usd: New daily threshold (optional).
            monthly_threshold_usd: New monthly threshold (optional).

        Returns:
            BudgetConfigResponse with updated thresholds.
        """
        self._logger.info(
            "configuring_budget_threshold",
            daily_threshold=str(daily_threshold_usd) if daily_threshold_usd else None,
            monthly_threshold=str(monthly_threshold_usd) if monthly_threshold_usd else None,
        )

        config = await self._client.configure_budget_threshold(
            daily_threshold_usd=daily_threshold_usd,
            monthly_threshold_usd=monthly_threshold_usd,
        )

        response = self._transformer.to_budget_config_response(config)

        self._logger.info(
            "configured_budget_threshold",
            message=config.message,
        )

        return response
