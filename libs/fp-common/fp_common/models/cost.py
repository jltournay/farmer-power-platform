"""Cost domain models for unified cost reporting.

Story 13.6: BFF Integration Layer

These models represent the response types for cost queries. They are used by:
- platform-cost service (internal repository responses)
- BFF platform_cost_client (gRPC response conversion)
- Admin Dashboard (API responses)

The models support ALL cost types:
- LLM: OpenRouter API calls
- Document: Azure Document Intelligence processing
- Embedding: Text embedding generation
- SMS: Africa's Talking SMS delivery
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, PlainSerializer

# Custom type for Decimal that serializes as string to preserve precision
DecimalStr = Annotated[Decimal, PlainSerializer(str, return_type=str)]


# =============================================================================
# Response Models (moved from platform-cost domain)
# =============================================================================


class CostTypeSummary(BaseModel):
    """Cost breakdown by type.

    Used for pie charts and cost type distribution reports.

    Attributes:
        cost_type: The cost type (llm, document, embedding, sms)
        total_cost_usd: Total cost for this type
        total_quantity: Total units consumed
        request_count: Number of requests/operations
        percentage: Percentage of total cost
    """

    cost_type: str = Field(description="Cost type (llm, document, embedding, sms)")
    total_cost_usd: DecimalStr = Field(description="Total cost in USD")
    total_quantity: int = Field(default=0, description="Total units consumed")
    request_count: int = Field(default=0, description="Number of operations")
    percentage: float = Field(default=0.0, description="Percentage of total cost")


class DailyCostEntry(BaseModel):
    """Daily cost trend entry.

    Used for trend charts showing cost over time with breakdown by type.

    Attributes:
        entry_date: The date (UTC)
        total_cost_usd: Total cost for the day
        llm_cost_usd: LLM portion
        document_cost_usd: Document processing portion
        embedding_cost_usd: Embedding portion
        sms_cost_usd: SMS portion
    """

    entry_date: date = Field(description="The date (UTC)")
    total_cost_usd: DecimalStr = Field(description="Total cost in USD")
    llm_cost_usd: DecimalStr = Field(default=Decimal("0"), description="LLM cost portion")
    document_cost_usd: DecimalStr = Field(default=Decimal("0"), description="Document cost portion")
    embedding_cost_usd: DecimalStr = Field(default=Decimal("0"), description="Embedding cost portion")
    sms_cost_usd: DecimalStr = Field(default=Decimal("0"), description="SMS cost portion")


class CurrentDayCost(BaseModel):
    """Real-time current day cost summary.

    Used for dashboard widgets showing today's running cost.

    Attributes:
        cost_date: Today's date
        total_cost_usd: Running total for today
        by_type: Breakdown by cost type
        updated_at: When this summary was computed
    """

    cost_date: date = Field(description="Today's date")
    total_cost_usd: DecimalStr = Field(description="Running total for today")
    by_type: dict[str, DecimalStr] = Field(default_factory=dict, description="Breakdown by cost type")
    updated_at: datetime = Field(description="When this summary was computed")


class AgentTypeCost(BaseModel):
    """LLM cost breakdown by agent type.

    Used for understanding which AI agents are most expensive.

    Attributes:
        agent_type: The agent type (extractor, explorer, generator, etc.)
        cost_usd: Total cost for this agent type
        request_count: Number of LLM calls
        tokens_in: Total input tokens
        tokens_out: Total output tokens
        percentage: Percentage of total LLM cost
    """

    agent_type: str = Field(description="Agent type name")
    cost_usd: DecimalStr = Field(description="Total cost in USD")
    request_count: int = Field(default=0, description="Number of LLM calls")
    tokens_in: int = Field(default=0, description="Total input tokens")
    tokens_out: int = Field(default=0, description="Total output tokens")
    percentage: float = Field(default=0.0, description="Percentage of total LLM cost")


class ModelCost(BaseModel):
    """LLM cost breakdown by model.

    Used for understanding which models are most expensive.

    Attributes:
        model: The model name (e.g., anthropic/claude-3-haiku)
        cost_usd: Total cost for this model
        request_count: Number of LLM calls
        tokens_in: Total input tokens
        tokens_out: Total output tokens
        percentage: Percentage of total LLM cost
    """

    model: str = Field(description="Model name (e.g., anthropic/claude-3-haiku)")
    cost_usd: DecimalStr = Field(description="Total cost in USD")
    request_count: int = Field(default=0, description="Number of LLM calls")
    tokens_in: int = Field(default=0, description="Total input tokens")
    tokens_out: int = Field(default=0, description="Total output tokens")
    percentage: float = Field(default=0.0, description="Percentage of total LLM cost")


class DomainCost(BaseModel):
    """Embedding cost breakdown by knowledge domain.

    Used for understanding which knowledge domains consume embedding costs.

    Attributes:
        knowledge_domain: The domain (e.g., tea-quality, farming-practices)
        cost_usd: Total cost for this domain
        tokens_total: Total embedding tokens
        texts_count: Number of texts embedded
        percentage: Percentage of total embedding cost
    """

    knowledge_domain: str = Field(description="Knowledge domain name")
    cost_usd: DecimalStr = Field(description="Total cost in USD")
    tokens_total: int = Field(default=0, description="Total embedding tokens")
    texts_count: int = Field(default=0, description="Number of texts embedded")
    percentage: float = Field(default=0.0, description="Percentage of total embedding cost")


class DocumentCostSummary(BaseModel):
    """Document processing cost summary.

    Used for understanding document processing costs.

    Attributes:
        total_cost_usd: Total document processing cost
        total_pages: Total pages processed
        avg_cost_per_page_usd: Average cost per page
        document_count: Number of documents processed
    """

    total_cost_usd: DecimalStr = Field(description="Total document processing cost")
    total_pages: int = Field(default=0, description="Total pages processed")
    avg_cost_per_page_usd: DecimalStr = Field(default=Decimal("0"), description="Average cost per page")
    document_count: int = Field(default=0, description="Number of documents processed")


# =============================================================================
# BFF Aggregate Response Models
# =============================================================================


class CostSummary(BaseModel):
    """Aggregate cost summary for BFF responses.

    Represents the complete response from GetCostSummary RPC.

    Attributes:
        total_cost_usd: Total cost across all types
        by_type: Breakdown by cost type
        period_start: Start of the query period
        period_end: End of the query period
        total_requests: Total operations across all types
    """

    total_cost_usd: DecimalStr = Field(description="Total cost across all types")
    by_type: list[CostTypeSummary] = Field(default_factory=list, description="Breakdown by cost type")
    period_start: date = Field(description="Start of the query period")
    period_end: date = Field(description="End of the query period")
    total_requests: int = Field(default=0, description="Total operations across all types")


class DailyCostTrend(BaseModel):
    """Daily cost trend response for BFF.

    Represents the complete response from GetDailyCostTrend RPC.

    Attributes:
        entries: Daily cost entries sorted by date
        data_available_from: Earliest date with data (TTL boundary)
    """

    entries: list[DailyCostEntry] = Field(default_factory=list, description="Daily cost entries")
    data_available_from: date = Field(description="Earliest date with available data")


class LlmCostByAgentType(BaseModel):
    """LLM cost breakdown by agent type for BFF.

    Represents the complete response from GetLlmCostByAgentType RPC.

    Attributes:
        agent_costs: Costs sorted by cost descending
        total_llm_cost_usd: Total LLM cost
        period_start: Start of the query period
        period_end: End of the query period
    """

    agent_costs: list[AgentTypeCost] = Field(default_factory=list, description="Agent cost breakdown")
    total_llm_cost_usd: DecimalStr = Field(description="Total LLM cost")
    period_start: date = Field(description="Start of the query period")
    period_end: date = Field(description="End of the query period")


class LlmCostByModel(BaseModel):
    """LLM cost breakdown by model for BFF.

    Represents the complete response from GetLlmCostByModel RPC.

    Attributes:
        model_costs: Costs sorted by cost descending
        total_llm_cost_usd: Total LLM cost
        period_start: Start of the query period
        period_end: End of the query period
    """

    model_costs: list[ModelCost] = Field(default_factory=list, description="Model cost breakdown")
    total_llm_cost_usd: DecimalStr = Field(description="Total LLM cost")
    period_start: date = Field(description="Start of the query period")
    period_end: date = Field(description="End of the query period")


class EmbeddingCostByDomain(BaseModel):
    """Embedding cost breakdown by domain for BFF.

    Represents the complete response from GetEmbeddingCostByDomain RPC.

    Attributes:
        domain_costs: Costs sorted by cost descending
        total_embedding_cost_usd: Total embedding cost
        period_start: Start of the query period
        period_end: End of the query period
    """

    domain_costs: list[DomainCost] = Field(default_factory=list, description="Domain cost breakdown")
    total_embedding_cost_usd: DecimalStr = Field(description="Total embedding cost")
    period_start: date = Field(description="Start of the query period")
    period_end: date = Field(description="End of the query period")


class BudgetStatus(BaseModel):
    """Current budget thresholds and utilization for BFF.

    Represents the complete response from GetBudgetStatus RPC.

    Attributes:
        daily_threshold_usd: Daily budget threshold
        daily_total_usd: Current daily total
        daily_alert_triggered: Whether daily alert is triggered
        daily_remaining_usd: Remaining daily budget
        daily_utilization_percent: Daily utilization percentage
        monthly_threshold_usd: Monthly budget threshold
        monthly_total_usd: Current monthly total
        monthly_alert_triggered: Whether monthly alert is triggered
        monthly_remaining_usd: Remaining monthly budget
        monthly_utilization_percent: Monthly utilization percentage
        by_type: Cost breakdown by type for current day
        current_day: Current day (YYYY-MM-DD)
        current_month: Current month (YYYY-MM)
    """

    daily_threshold_usd: DecimalStr = Field(description="Daily budget threshold")
    daily_total_usd: DecimalStr = Field(description="Current daily total")
    daily_alert_triggered: bool = Field(default=False, description="Daily alert status")
    daily_remaining_usd: DecimalStr = Field(description="Remaining daily budget")
    daily_utilization_percent: float = Field(default=0.0, description="Daily utilization percentage")
    monthly_threshold_usd: DecimalStr = Field(description="Monthly budget threshold")
    monthly_total_usd: DecimalStr = Field(description="Current monthly total")
    monthly_alert_triggered: bool = Field(default=False, description="Monthly alert status")
    monthly_remaining_usd: DecimalStr = Field(description="Remaining monthly budget")
    monthly_utilization_percent: float = Field(default=0.0, description="Monthly utilization percentage")
    by_type: dict[str, DecimalStr] = Field(default_factory=dict, description="Cost breakdown by type")
    current_day: str = Field(description="Current day (YYYY-MM-DD)")
    current_month: str = Field(description="Current month (YYYY-MM)")


class BudgetThresholdConfig(BaseModel):
    """Budget threshold configuration response for BFF.

    Represents the complete response from ConfigureBudgetThreshold RPC.

    Attributes:
        daily_threshold_usd: Updated daily threshold
        monthly_threshold_usd: Updated monthly threshold
        message: Confirmation message
        updated_at: When the threshold was updated
    """

    daily_threshold_usd: DecimalStr = Field(description="Daily budget threshold")
    monthly_threshold_usd: DecimalStr = Field(description="Monthly budget threshold")
    message: str = Field(description="Confirmation message")
    updated_at: datetime = Field(description="When the threshold was updated")
