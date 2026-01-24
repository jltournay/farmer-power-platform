"""Platform Cost transformer for admin API (Story 9.10a).

Transforms fp-common cost domain models to admin API schemas.
Receives Pydantic models from PlatformCostClient (NOT proto).
"""

from datetime import date

from bff.api.schemas.admin.platform_cost_schemas import (
    AgentTypeCostEntry,
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
    ModelCostEntry,
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


class PlatformCostTransformer:
    """Transforms cost domain models to admin API response schemas."""

    @staticmethod
    def to_cost_summary_response(
        summary: CostSummary,
    ) -> CostSummaryResponse:
        """Transform CostSummary to API response.

        Args:
            summary: CostSummary from PlatformCostClient.

        Returns:
            CostSummaryResponse for API.
        """
        return CostSummaryResponse(
            total_cost_usd=summary.total_cost_usd,
            total_requests=summary.total_requests,
            by_type=[
                CostTypeBreakdown(
                    cost_type=ct.cost_type,
                    total_cost_usd=ct.total_cost_usd,
                    total_quantity=ct.total_quantity,
                    request_count=ct.request_count,
                    percentage=ct.percentage,
                )
                for ct in summary.by_type
            ],
            period_start=summary.period_start,
            period_end=summary.period_end,
        )

    @staticmethod
    def to_daily_trend_response(
        trend: DailyCostTrend,
    ) -> DailyTrendResponse:
        """Transform DailyCostTrend to API response.

        Args:
            trend: DailyCostTrend from PlatformCostClient.

        Returns:
            DailyTrendResponse for API.
        """
        return DailyTrendResponse(
            entries=[
                DailyTrendEntry(
                    entry_date=entry.entry_date,
                    total_cost_usd=entry.total_cost_usd,
                    llm_cost_usd=entry.llm_cost_usd,
                    document_cost_usd=entry.document_cost_usd,
                    embedding_cost_usd=entry.embedding_cost_usd,
                )
                for entry in trend.entries
            ],
            data_available_from=trend.data_available_from,
        )

    @staticmethod
    def to_current_day_cost_response(
        current: CurrentDayCost,
    ) -> CurrentDayCostResponse:
        """Transform CurrentDayCost to API response.

        Args:
            current: CurrentDayCost from PlatformCostClient.

        Returns:
            CurrentDayCostResponse for API.
        """
        return CurrentDayCostResponse(
            cost_date=current.cost_date,
            total_cost_usd=current.total_cost_usd,
            by_type=current.by_type,
            updated_at=current.updated_at,
        )

    @staticmethod
    def to_llm_by_agent_type_response(
        breakdown: LlmCostByAgentType,
    ) -> LlmByAgentTypeResponse:
        """Transform LlmCostByAgentType to API response.

        Args:
            breakdown: LlmCostByAgentType from PlatformCostClient.

        Returns:
            LlmByAgentTypeResponse for API.
        """
        return LlmByAgentTypeResponse(
            agent_costs=[
                AgentTypeCostEntry(
                    agent_type=ac.agent_type,
                    cost_usd=ac.cost_usd,
                    request_count=ac.request_count,
                    tokens_in=ac.tokens_in,
                    tokens_out=ac.tokens_out,
                    percentage=ac.percentage,
                )
                for ac in breakdown.agent_costs
            ],
            total_llm_cost_usd=breakdown.total_llm_cost_usd,
        )

    @staticmethod
    def to_llm_by_model_response(
        breakdown: LlmCostByModel,
    ) -> LlmByModelResponse:
        """Transform LlmCostByModel to API response.

        Args:
            breakdown: LlmCostByModel from PlatformCostClient.

        Returns:
            LlmByModelResponse for API.
        """
        return LlmByModelResponse(
            model_costs=[
                ModelCostEntry(
                    model=mc.model,
                    cost_usd=mc.cost_usd,
                    request_count=mc.request_count,
                    tokens_in=mc.tokens_in,
                    tokens_out=mc.tokens_out,
                    percentage=mc.percentage,
                )
                for mc in breakdown.model_costs
            ],
            total_llm_cost_usd=breakdown.total_llm_cost_usd,
        )

    @staticmethod
    def to_document_cost_response(
        doc_cost: DocumentCostSummary,
        period_start: date,
        period_end: date,
    ) -> DocumentCostResponse:
        """Transform DocumentCostSummary to API response.

        Args:
            doc_cost: DocumentCostSummary from PlatformCostClient.
            period_start: Query period start (passed through from request).
            period_end: Query period end (passed through from request).

        Returns:
            DocumentCostResponse for API.
        """
        return DocumentCostResponse(
            total_cost_usd=doc_cost.total_cost_usd,
            total_pages=doc_cost.total_pages,
            avg_cost_per_page_usd=doc_cost.avg_cost_per_page_usd,
            document_count=doc_cost.document_count,
            period_start=period_start,
            period_end=period_end,
        )

    @staticmethod
    def to_embedding_by_domain_response(
        breakdown: EmbeddingCostByDomain,
    ) -> EmbeddingByDomainResponse:
        """Transform EmbeddingCostByDomain to API response.

        Args:
            breakdown: EmbeddingCostByDomain from PlatformCostClient.

        Returns:
            EmbeddingByDomainResponse for API.
        """
        return EmbeddingByDomainResponse(
            domain_costs=[
                DomainCostEntry(
                    knowledge_domain=dc.knowledge_domain,
                    cost_usd=dc.cost_usd,
                    tokens_total=dc.tokens_total,
                    texts_count=dc.texts_count,
                    percentage=dc.percentage,
                )
                for dc in breakdown.domain_costs
            ],
            total_embedding_cost_usd=breakdown.total_embedding_cost_usd,
        )

    @staticmethod
    def to_budget_status_response(
        status: BudgetStatus,
    ) -> BudgetStatusResponse:
        """Transform BudgetStatus to API response.

        Args:
            status: BudgetStatus from PlatformCostClient.

        Returns:
            BudgetStatusResponse for API.
        """
        return BudgetStatusResponse(
            daily_threshold_usd=status.daily_threshold_usd,
            daily_total_usd=status.daily_total_usd,
            daily_remaining_usd=status.daily_remaining_usd,
            daily_utilization_percent=status.daily_utilization_percent,
            monthly_threshold_usd=status.monthly_threshold_usd,
            monthly_total_usd=status.monthly_total_usd,
            monthly_remaining_usd=status.monthly_remaining_usd,
            monthly_utilization_percent=status.monthly_utilization_percent,
            by_type=status.by_type,
            current_day=status.current_day,
            current_month=status.current_month,
        )

    @staticmethod
    def to_budget_config_response(
        config: BudgetThresholdConfig,
    ) -> BudgetConfigResponse:
        """Transform BudgetThresholdConfig to API response.

        Args:
            config: BudgetThresholdConfig from PlatformCostClient.

        Returns:
            BudgetConfigResponse for API.
        """
        return BudgetConfigResponse(
            daily_threshold_usd=config.daily_threshold_usd,
            monthly_threshold_usd=config.monthly_threshold_usd,
            message=config.message,
            updated_at=config.updated_at,
        )
