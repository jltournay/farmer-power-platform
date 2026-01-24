"""Platform Cost API schemas for admin portal (Story 9.10a).

Defines request/response schemas for platform cost monitoring endpoints.
Follows ADR-012 BFF patterns with separate API schemas from domain models.

All monetary values use string type (DecimalStr) to preserve precision.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, PlainSerializer

# Custom type for Decimal that serializes as string to preserve precision
DecimalStr = Annotated[Decimal, PlainSerializer(str, return_type=str)]


# =============================================================================
# Response Schemas - Cost Summary (AC 9.10a.1)
# =============================================================================


class CostTypeBreakdown(BaseModel):
    """Cost breakdown by type for pie charts.

    Attributes:
        cost_type: Cost type (llm, document, embedding, sms).
        total_cost_usd: Total cost for this type.
        total_quantity: Total units consumed.
        request_count: Number of operations.
        percentage: Percentage of total cost (0-100).
    """

    cost_type: str = Field(description="Cost type (llm, document, embedding, sms)")
    total_cost_usd: DecimalStr = Field(description="Total cost in USD")
    total_quantity: int = Field(default=0, description="Total units consumed")
    request_count: int = Field(default=0, description="Number of operations")
    percentage: float = Field(default=0.0, description="Percentage of total cost")


class CostSummaryResponse(BaseModel):
    """Cost summary response (AC 9.10a.1).

    Attributes:
        total_cost_usd: Total cost across all types.
        total_requests: Total operations across all types.
        by_type: Breakdown by cost type.
        period_start: Start of the query period.
        period_end: End of the query period.
    """

    total_cost_usd: DecimalStr = Field(description="Total cost across all types")
    total_requests: int = Field(default=0, description="Total operations")
    by_type: list[CostTypeBreakdown] = Field(default_factory=list, description="Breakdown by cost type")
    period_start: date = Field(description="Start of query period")
    period_end: date = Field(description="End of query period")


# =============================================================================
# Response Schemas - Daily Trend (AC 9.10a.2)
# =============================================================================


class DailyTrendEntry(BaseModel):
    """Single day cost entry for trend charts.

    Attributes:
        entry_date: The date.
        total_cost_usd: Total cost for the day.
        llm_cost_usd: LLM cost portion.
        document_cost_usd: Document processing cost portion.
        embedding_cost_usd: Embedding cost portion.
    """

    entry_date: date = Field(description="The date (YYYY-MM-DD)")
    total_cost_usd: DecimalStr = Field(description="Total cost in USD")
    llm_cost_usd: DecimalStr = Field(default=Decimal("0"), description="LLM cost portion")
    document_cost_usd: DecimalStr = Field(default=Decimal("0"), description="Document cost portion")
    embedding_cost_usd: DecimalStr = Field(default=Decimal("0"), description="Embedding cost portion")


class DailyTrendResponse(BaseModel):
    """Daily cost trend response (AC 9.10a.2).

    Attributes:
        entries: Daily cost entries sorted by date.
        data_available_from: Earliest date with data.
    """

    entries: list[DailyTrendEntry] = Field(default_factory=list, description="Daily cost entries")
    data_available_from: date = Field(description="Earliest date with available data")


# =============================================================================
# Response Schemas - Current Day (AC 9.10a.3)
# =============================================================================


class CurrentDayCostResponse(BaseModel):
    """Current day cost response (AC 9.10a.3).

    Attributes:
        cost_date: Today's date.
        total_cost_usd: Running total for today.
        by_type: Breakdown by cost type.
        updated_at: When this summary was computed.
    """

    cost_date: date = Field(description="Today's date")
    total_cost_usd: DecimalStr = Field(description="Running total for today")
    by_type: dict[str, DecimalStr] = Field(default_factory=dict, description="Cost by type")
    updated_at: datetime = Field(description="When summary was computed")


# =============================================================================
# Response Schemas - LLM Breakdown (AC 9.10a.4)
# =============================================================================


class AgentTypeCostEntry(BaseModel):
    """LLM cost per agent type.

    Attributes:
        agent_type: Agent type name (extractor, explorer, etc.).
        cost_usd: Total cost for this agent type.
        request_count: Number of LLM calls.
        tokens_in: Total input tokens.
        tokens_out: Total output tokens.
        percentage: Percentage of total LLM cost.
    """

    agent_type: str = Field(description="Agent type name")
    cost_usd: DecimalStr = Field(description="Total cost in USD")
    request_count: int = Field(default=0, description="Number of LLM calls")
    tokens_in: int = Field(default=0, description="Total input tokens")
    tokens_out: int = Field(default=0, description="Total output tokens")
    percentage: float = Field(default=0.0, description="Percentage of total LLM cost")


class LlmByAgentTypeResponse(BaseModel):
    """LLM cost by agent type response (AC 9.10a.4).

    Attributes:
        agent_costs: Agent cost breakdown sorted by cost descending.
        total_llm_cost_usd: Total LLM cost.
    """

    agent_costs: list[AgentTypeCostEntry] = Field(default_factory=list, description="Agent cost breakdown")
    total_llm_cost_usd: DecimalStr = Field(description="Total LLM cost")


class ModelCostEntry(BaseModel):
    """LLM cost per model.

    Attributes:
        model: Model name (e.g., anthropic/claude-3-haiku).
        cost_usd: Total cost for this model.
        request_count: Number of LLM calls.
        tokens_in: Total input tokens.
        tokens_out: Total output tokens.
        percentage: Percentage of total LLM cost.
    """

    model: str = Field(description="Model name")
    cost_usd: DecimalStr = Field(description="Total cost in USD")
    request_count: int = Field(default=0, description="Number of LLM calls")
    tokens_in: int = Field(default=0, description="Total input tokens")
    tokens_out: int = Field(default=0, description="Total output tokens")
    percentage: float = Field(default=0.0, description="Percentage of total LLM cost")


class LlmByModelResponse(BaseModel):
    """LLM cost by model response (AC 9.10a.4).

    Attributes:
        model_costs: Model cost breakdown sorted by cost descending.
        total_llm_cost_usd: Total LLM cost.
    """

    model_costs: list[ModelCostEntry] = Field(default_factory=list, description="Model cost breakdown")
    total_llm_cost_usd: DecimalStr = Field(description="Total LLM cost")


# =============================================================================
# Response Schemas - Document Costs (AC 9.10a.5)
# =============================================================================


class DocumentCostResponse(BaseModel):
    """Document cost summary response (AC 9.10a.5).

    Attributes:
        total_cost_usd: Total document processing cost.
        total_pages: Total pages processed.
        avg_cost_per_page_usd: Average cost per page.
        document_count: Number of documents processed.
        period_start: Start of query period.
        period_end: End of query period.
    """

    total_cost_usd: DecimalStr = Field(description="Total document processing cost")
    total_pages: int = Field(default=0, description="Total pages processed")
    avg_cost_per_page_usd: DecimalStr = Field(default=Decimal("0"), description="Average cost per page")
    document_count: int = Field(default=0, description="Number of documents processed")
    period_start: date = Field(description="Start of query period")
    period_end: date = Field(description="End of query period")


# =============================================================================
# Response Schemas - Embedding Costs (AC 9.10a.6)
# =============================================================================


class DomainCostEntry(BaseModel):
    """Embedding cost per knowledge domain.

    Attributes:
        knowledge_domain: Domain name (e.g., tea-quality).
        cost_usd: Total cost for this domain.
        tokens_total: Total embedding tokens.
        texts_count: Number of texts embedded.
        percentage: Percentage of total embedding cost.
    """

    knowledge_domain: str = Field(description="Knowledge domain name")
    cost_usd: DecimalStr = Field(description="Total cost in USD")
    tokens_total: int = Field(default=0, description="Total embedding tokens")
    texts_count: int = Field(default=0, description="Number of texts embedded")
    percentage: float = Field(default=0.0, description="Percentage of total embedding cost")


class EmbeddingByDomainResponse(BaseModel):
    """Embedding cost by domain response (AC 9.10a.6).

    Attributes:
        domain_costs: Domain cost breakdown sorted by cost descending.
        total_embedding_cost_usd: Total embedding cost.
    """

    domain_costs: list[DomainCostEntry] = Field(default_factory=list, description="Domain cost breakdown")
    total_embedding_cost_usd: DecimalStr = Field(description="Total embedding cost")


# =============================================================================
# Response Schemas - Budget (AC 9.10a.7)
# =============================================================================


class BudgetStatusResponse(BaseModel):
    """Budget status response (AC 9.10a.7).

    Attributes:
        daily_threshold_usd: Daily budget threshold.
        daily_total_usd: Current daily total.
        daily_remaining_usd: Remaining daily budget.
        daily_utilization_percent: Daily utilization (0-100).
        monthly_threshold_usd: Monthly budget threshold.
        monthly_total_usd: Current monthly total.
        monthly_remaining_usd: Remaining monthly budget.
        monthly_utilization_percent: Monthly utilization (0-100).
        by_type: Cost breakdown by type for current day.
        current_day: Current day (YYYY-MM-DD).
        current_month: Current month (YYYY-MM).
    """

    daily_threshold_usd: DecimalStr = Field(description="Daily budget threshold")
    daily_total_usd: DecimalStr = Field(description="Current daily total")
    daily_remaining_usd: DecimalStr = Field(description="Remaining daily budget")
    daily_utilization_percent: float = Field(default=0.0, description="Daily utilization %")
    monthly_threshold_usd: DecimalStr = Field(description="Monthly budget threshold")
    monthly_total_usd: DecimalStr = Field(description="Current monthly total")
    monthly_remaining_usd: DecimalStr = Field(description="Remaining monthly budget")
    monthly_utilization_percent: float = Field(default=0.0, description="Monthly utilization %")
    by_type: dict[str, DecimalStr] = Field(default_factory=dict, description="Cost breakdown by type")
    current_day: str = Field(description="Current day (YYYY-MM-DD)")
    current_month: str = Field(description="Current month (YYYY-MM)")


# =============================================================================
# Request Schemas - Budget Configuration (AC 9.10a.7)
# =============================================================================


class BudgetConfigRequest(BaseModel):
    """Budget threshold configuration request (AC 9.10a.7).

    At least one threshold must be provided.

    Attributes:
        daily_threshold_usd: New daily budget threshold (must be > 0).
        monthly_threshold_usd: New monthly budget threshold (must be > 0).
    """

    daily_threshold_usd: DecimalStr | None = Field(
        default=None,
        gt=Decimal("0"),
        description="New daily budget threshold (> 0)",
    )
    monthly_threshold_usd: DecimalStr | None = Field(
        default=None,
        gt=Decimal("0"),
        description="New monthly budget threshold (> 0)",
    )


class BudgetConfigResponse(BaseModel):
    """Budget threshold configuration response (AC 9.10a.7).

    Attributes:
        daily_threshold_usd: Updated daily threshold.
        monthly_threshold_usd: Updated monthly threshold.
        message: Confirmation message.
        updated_at: When the threshold was updated.
    """

    daily_threshold_usd: DecimalStr = Field(description="Updated daily threshold")
    monthly_threshold_usd: DecimalStr = Field(description="Updated monthly threshold")
    message: str = Field(description="Confirmation message")
    updated_at: datetime = Field(description="When threshold was updated")
