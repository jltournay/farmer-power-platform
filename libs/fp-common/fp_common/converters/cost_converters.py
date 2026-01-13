"""Proto-to-Pydantic converters for Platform Cost domain.

Story 13.6: BFF Integration Layer

These converters centralize the mapping from Proto messages to Pydantic models
for the Platform Cost service. They support bidirectional conversion (proto-to-pydantic
and pydantic-to-proto) for BFF clients and gRPC services.

Field mapping strategy:
- Decimal values in proto are strings -> Pydantic Decimal
- Proto dates (string YYYY-MM-DD) -> Python date
- Proto timestamps (string ISO) -> Python datetime
- All optional fields have sensible defaults

Reference:
- Proto definitions: proto/platform_cost/v1/platform_cost.proto
- Pydantic models: fp_common/models/cost.py
"""

from datetime import date, datetime
from decimal import Decimal

from fp_proto.platform_cost.v1 import platform_cost_pb2

from fp_common.models.cost import (
    AgentTypeCost,
    BudgetStatus,
    BudgetThresholdConfig,
    CostSummary,
    CostTypeSummary,
    CurrentDayCost,
    DailyCostEntry,
    DailyCostTrend,
    DocumentCostSummary,
    DomainCost,
    EmbeddingCostByDomain,
    LlmCostByAgentType,
    LlmCostByModel,
    ModelCost,
)


def _parse_date(date_str: str) -> date:
    """Parse ISO date string to Python date.

    Args:
        date_str: Date string in YYYY-MM-DD format.

    Returns:
        Python date object.
    """
    return date.fromisoformat(date_str)


def _parse_datetime(datetime_str: str) -> datetime:
    """Parse ISO datetime string to Python datetime.

    Args:
        datetime_str: Datetime string in ISO format.

    Returns:
        Python datetime object.
    """
    return datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))


def _to_decimal(value: str) -> Decimal:
    """Convert string to Decimal.

    Args:
        value: String representation of a decimal number.

    Returns:
        Decimal object.
    """
    return Decimal(value) if value else Decimal("0")


# =============================================================================
# Proto-to-Pydantic Converters (for BFF client)
# =============================================================================


def cost_summary_from_proto(response: platform_cost_pb2.CostSummaryResponse) -> CostSummary:
    """Convert CostSummaryResponse proto to Pydantic model.

    Args:
        response: The CostSummaryResponse proto from gRPC.

    Returns:
        CostSummary Pydantic model.
    """
    by_type = [
        CostTypeSummary(
            cost_type=breakdown.cost_type,
            total_cost_usd=_to_decimal(breakdown.total_cost_usd),
            total_quantity=breakdown.total_quantity,
            request_count=breakdown.request_count,
            percentage=breakdown.percentage,
        )
        for breakdown in response.by_type
    ]

    return CostSummary(
        total_cost_usd=_to_decimal(response.total_cost_usd),
        by_type=by_type,
        period_start=_parse_date(response.period_start),
        period_end=_parse_date(response.period_end),
        total_requests=response.total_requests,
    )


def daily_cost_trend_from_proto(response: platform_cost_pb2.DailyCostTrendResponse) -> DailyCostTrend:
    """Convert DailyCostTrendResponse proto to Pydantic model.

    Args:
        response: The DailyCostTrendResponse proto from gRPC.

    Returns:
        DailyCostTrend Pydantic model.
    """
    entries = [
        DailyCostEntry(
            entry_date=_parse_date(entry.date),
            total_cost_usd=_to_decimal(entry.total_cost_usd),
            llm_cost_usd=_to_decimal(entry.llm_cost_usd),
            document_cost_usd=_to_decimal(entry.document_cost_usd),
            embedding_cost_usd=_to_decimal(entry.embedding_cost_usd),
            sms_cost_usd=_to_decimal(entry.sms_cost_usd),
        )
        for entry in response.entries
    ]

    return DailyCostTrend(
        entries=entries,
        data_available_from=_parse_date(response.data_available_from),
    )


def current_day_cost_from_proto(response: platform_cost_pb2.CurrentDayCostResponse) -> CurrentDayCost:
    """Convert CurrentDayCostResponse proto to Pydantic model.

    Args:
        response: The CurrentDayCostResponse proto from gRPC.

    Returns:
        CurrentDayCost Pydantic model.
    """
    by_type = {cost_type: _to_decimal(cost_usd) for cost_type, cost_usd in response.by_type.items()}

    return CurrentDayCost(
        cost_date=_parse_date(response.date),
        total_cost_usd=_to_decimal(response.total_cost_usd),
        by_type=by_type,
        updated_at=_parse_datetime(response.updated_at),
    )


def llm_cost_by_agent_type_from_proto(response: platform_cost_pb2.LlmCostByAgentTypeResponse) -> LlmCostByAgentType:
    """Convert LlmCostByAgentTypeResponse proto to Pydantic model.

    Args:
        response: The LlmCostByAgentTypeResponse proto from gRPC.

    Returns:
        LlmCostByAgentType Pydantic model.
    """
    agent_costs = [
        AgentTypeCost(
            agent_type=cost.agent_type,
            cost_usd=_to_decimal(cost.cost_usd),
            request_count=cost.request_count,
            tokens_in=cost.tokens_in,
            tokens_out=cost.tokens_out,
            percentage=cost.percentage,
        )
        for cost in response.agent_costs
    ]

    return LlmCostByAgentType(
        agent_costs=agent_costs,
        total_llm_cost_usd=_to_decimal(response.total_llm_cost_usd),
        period_start=_parse_date(response.period_start),
        period_end=_parse_date(response.period_end),
    )


def llm_cost_by_model_from_proto(response: platform_cost_pb2.LlmCostByModelResponse) -> LlmCostByModel:
    """Convert LlmCostByModelResponse proto to Pydantic model.

    Args:
        response: The LlmCostByModelResponse proto from gRPC.

    Returns:
        LlmCostByModel Pydantic model.
    """
    model_costs = [
        ModelCost(
            model=cost.model,
            cost_usd=_to_decimal(cost.cost_usd),
            request_count=cost.request_count,
            tokens_in=cost.tokens_in,
            tokens_out=cost.tokens_out,
            percentage=cost.percentage,
        )
        for cost in response.model_costs
    ]

    return LlmCostByModel(
        model_costs=model_costs,
        total_llm_cost_usd=_to_decimal(response.total_llm_cost_usd),
        period_start=_parse_date(response.period_start),
        period_end=_parse_date(response.period_end),
    )


def document_cost_summary_from_proto(response: platform_cost_pb2.DocumentCostSummaryResponse) -> DocumentCostSummary:
    """Convert DocumentCostSummaryResponse proto to Pydantic model.

    Args:
        response: The DocumentCostSummaryResponse proto from gRPC.

    Returns:
        DocumentCostSummary Pydantic model.
    """
    return DocumentCostSummary(
        total_cost_usd=_to_decimal(response.total_cost_usd),
        total_pages=response.total_pages,
        avg_cost_per_page_usd=_to_decimal(response.avg_cost_per_page_usd),
        document_count=response.document_count,
    )


def embedding_cost_by_domain_from_proto(
    response: platform_cost_pb2.EmbeddingCostByDomainResponse,
) -> EmbeddingCostByDomain:
    """Convert EmbeddingCostByDomainResponse proto to Pydantic model.

    Args:
        response: The EmbeddingCostByDomainResponse proto from gRPC.

    Returns:
        EmbeddingCostByDomain Pydantic model.
    """
    domain_costs = [
        DomainCost(
            knowledge_domain=cost.knowledge_domain,
            cost_usd=_to_decimal(cost.cost_usd),
            tokens_total=cost.tokens_total,
            texts_count=cost.texts_count,
            percentage=cost.percentage,
        )
        for cost in response.domain_costs
    ]

    return EmbeddingCostByDomain(
        domain_costs=domain_costs,
        total_embedding_cost_usd=_to_decimal(response.total_embedding_cost_usd),
        period_start=_parse_date(response.period_start),
        period_end=_parse_date(response.period_end),
    )


def budget_status_from_proto(response: platform_cost_pb2.BudgetStatusResponse) -> BudgetStatus:
    """Convert BudgetStatusResponse proto to Pydantic model.

    Args:
        response: The BudgetStatusResponse proto from gRPC.

    Returns:
        BudgetStatus Pydantic model.
    """
    by_type = {cost_type: _to_decimal(cost_usd) for cost_type, cost_usd in response.by_type.items()}

    return BudgetStatus(
        daily_threshold_usd=_to_decimal(response.daily_threshold_usd),
        daily_total_usd=_to_decimal(response.daily_total_usd),
        daily_alert_triggered=response.daily_alert_triggered,
        daily_remaining_usd=_to_decimal(response.daily_remaining_usd),
        daily_utilization_percent=response.daily_utilization_percent,
        monthly_threshold_usd=_to_decimal(response.monthly_threshold_usd),
        monthly_total_usd=_to_decimal(response.monthly_total_usd),
        monthly_alert_triggered=response.monthly_alert_triggered,
        monthly_remaining_usd=_to_decimal(response.monthly_remaining_usd),
        monthly_utilization_percent=response.monthly_utilization_percent,
        by_type=by_type,
        current_day=response.current_day,
        current_month=response.current_month,
    )


def budget_threshold_config_from_proto(
    response: platform_cost_pb2.ConfigureBudgetThresholdResponse,
) -> BudgetThresholdConfig:
    """Convert ConfigureBudgetThresholdResponse proto to Pydantic model.

    Args:
        response: The ConfigureBudgetThresholdResponse proto from gRPC.

    Returns:
        BudgetThresholdConfig Pydantic model.
    """
    return BudgetThresholdConfig(
        daily_threshold_usd=_to_decimal(response.daily_threshold_usd),
        monthly_threshold_usd=_to_decimal(response.monthly_threshold_usd),
        message=response.message,
        updated_at=_parse_datetime(response.updated_at),
    )


# =============================================================================
# Pydantic-to-Proto Converters (for gRPC service responses)
# =============================================================================


def cost_type_summary_to_proto(model: CostTypeSummary) -> platform_cost_pb2.CostTypeBreakdown:
    """Convert CostTypeSummary Pydantic model to proto.

    Args:
        model: The CostTypeSummary Pydantic model.

    Returns:
        CostTypeBreakdown proto message.
    """
    return platform_cost_pb2.CostTypeBreakdown(
        cost_type=model.cost_type,
        total_cost_usd=str(model.total_cost_usd),
        total_quantity=model.total_quantity,
        request_count=model.request_count,
        percentage=model.percentage,
    )


def daily_cost_entry_to_proto(model: DailyCostEntry) -> platform_cost_pb2.DailyCostEntry:
    """Convert DailyCostEntry Pydantic model to proto.

    Args:
        model: The DailyCostEntry Pydantic model.

    Returns:
        DailyCostEntry proto message.
    """
    return platform_cost_pb2.DailyCostEntry(
        date=model.entry_date.isoformat(),
        total_cost_usd=str(model.total_cost_usd),
        llm_cost_usd=str(model.llm_cost_usd),
        document_cost_usd=str(model.document_cost_usd),
        embedding_cost_usd=str(model.embedding_cost_usd),
        sms_cost_usd=str(model.sms_cost_usd),
    )


def agent_type_cost_to_proto(model: AgentTypeCost) -> platform_cost_pb2.AgentTypeCost:
    """Convert AgentTypeCost Pydantic model to proto.

    Args:
        model: The AgentTypeCost Pydantic model.

    Returns:
        AgentTypeCost proto message.
    """
    return platform_cost_pb2.AgentTypeCost(
        agent_type=model.agent_type,
        cost_usd=str(model.cost_usd),
        request_count=model.request_count,
        tokens_in=model.tokens_in,
        tokens_out=model.tokens_out,
        percentage=model.percentage,
    )


def model_cost_to_proto(model: ModelCost) -> platform_cost_pb2.ModelCost:
    """Convert ModelCost Pydantic model to proto.

    Args:
        model: The ModelCost Pydantic model.

    Returns:
        ModelCost proto message.
    """
    return platform_cost_pb2.ModelCost(
        model=model.model,
        cost_usd=str(model.cost_usd),
        request_count=model.request_count,
        tokens_in=model.tokens_in,
        tokens_out=model.tokens_out,
        percentage=model.percentage,
    )


def domain_cost_to_proto(model: DomainCost) -> platform_cost_pb2.DomainCost:
    """Convert DomainCost Pydantic model to proto.

    Args:
        model: The DomainCost Pydantic model.

    Returns:
        DomainCost proto message.
    """
    return platform_cost_pb2.DomainCost(
        knowledge_domain=model.knowledge_domain,
        cost_usd=str(model.cost_usd),
        tokens_total=model.tokens_total,
        texts_count=model.texts_count,
        percentage=model.percentage,
    )
