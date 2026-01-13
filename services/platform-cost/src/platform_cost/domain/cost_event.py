"""Domain models for unified cost events.

Story 13.3: Cost Repository and Budget Monitor

This module provides the storage model (UnifiedCostEvent) and response models
for the unified platform cost service. These models support ALL cost types:
- LLM: OpenRouter API calls
- Document: Azure Document Intelligence processing
- Embedding: Text embedding generation
- SMS: Africa's Talking SMS delivery

The storage model converts from the fp_common.events.cost_recorded.CostRecordedEvent
published by services via DAPR pub/sub.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any

from fp_common.events.cost_recorded import CostRecordedEvent, CostType
from pydantic import BaseModel, Field, PlainSerializer

# Custom type for Decimal that serializes as string to preserve precision
DecimalStr = Annotated[Decimal, PlainSerializer(str, return_type=str)]


class UnifiedCostEvent(BaseModel):
    """Unified cost event stored in MongoDB.

    This is the storage model for cost events in the platform_cost.cost_events collection.
    It converts from CostRecordedEvent (the pub/sub payload) and adds MongoDB-specific
    handling (Decimal as string storage, _id field).

    Attributes:
        id: Unique event identifier (UUID string)
        cost_type: Type of cost (llm, document, embedding, sms)
        amount_usd: Cost amount in USD (stored as string for precision)
        quantity: Number of units (tokens, pages, messages, queries)
        unit: Unit type for the quantity
        timestamp: When the cost was incurred (UTC)
        source_service: Service that incurred the cost
        success: Whether the operation succeeded
        metadata: Type-specific metadata (model, agent_type, tokens_in/out, etc.)
        factory_id: Optional factory ID for cost attribution
        request_id: Optional correlation ID for tracing
        agent_type: Extracted from metadata for LLM costs (indexed)
        model: Extracted from metadata for LLM/Embedding costs (indexed)
        knowledge_domain: Extracted from metadata for Embedding costs (indexed)
    """

    id: str = Field(description="Unique event identifier (UUID)")
    cost_type: str = Field(description="Type of cost (llm, document, embedding, sms)")
    amount_usd: DecimalStr = Field(ge=0, description="Cost amount in USD")
    quantity: int = Field(ge=0, description="Number of units consumed")
    unit: str = Field(description="Unit type (tokens, pages, messages, queries)")
    timestamp: datetime = Field(description="When the cost was incurred (UTC)")
    source_service: str = Field(description="Service that incurred the cost")
    success: bool = Field(description="Whether the operation succeeded")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Type-specific metadata")
    factory_id: str | None = Field(default=None, description="Optional factory ID for attribution")
    request_id: str | None = Field(default=None, description="Optional correlation ID for tracing")

    # Indexed fields extracted from metadata for efficient querying
    agent_type: str | None = Field(default=None, description="Agent type for LLM costs")
    model: str | None = Field(default=None, description="Model name for LLM/Embedding costs")
    knowledge_domain: str | None = Field(default=None, description="Knowledge domain for Embedding costs")

    @classmethod
    def from_event(cls, event_id: str, event: CostRecordedEvent) -> "UnifiedCostEvent":
        """Create a UnifiedCostEvent from a CostRecordedEvent.

        Extracts indexed fields from metadata for efficient querying:
        - agent_type: from LLM metadata
        - model: from LLM or Embedding metadata
        - knowledge_domain: from Embedding metadata

        Args:
            event_id: Unique identifier for this event (typically UUID)
            event: The CostRecordedEvent from DAPR pub/sub

        Returns:
            UnifiedCostEvent ready for MongoDB storage
        """
        # Extract indexed fields from metadata
        agent_type = event.metadata.get("agent_type") if event.cost_type == CostType.LLM else None
        model = event.metadata.get("model")  # Present in both LLM and Embedding
        knowledge_domain = event.metadata.get("knowledge_domain") if event.cost_type == CostType.EMBEDDING else None

        return cls(
            id=event_id,
            cost_type=event.cost_type if isinstance(event.cost_type, str) else event.cost_type.value,
            amount_usd=event.amount_usd,
            quantity=event.quantity,
            unit=event.unit if isinstance(event.unit, str) else event.unit.value,
            timestamp=event.timestamp,
            source_service=event.source_service,
            success=event.success,
            metadata=event.metadata,
            factory_id=event.factory_id,
            request_id=event.request_id,
            agent_type=agent_type,
            model=model,
            knowledge_domain=knowledge_domain,
        )

    def to_mongo_doc(self) -> dict[str, Any]:
        """Convert to MongoDB document format.

        - Sets _id to the event id
        - Converts Decimal to string for storage

        Returns:
            Dictionary suitable for MongoDB insertion
        """
        doc = self.model_dump()
        doc["_id"] = self.id
        # Ensure amount_usd is stored as string
        doc["amount_usd"] = str(self.amount_usd)
        # Remove the 'id' field since we use '_id'
        del doc["id"]
        return doc


# Response models for query results


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
        query_count: Number of embedding queries
        percentage: Percentage of total embedding cost
    """

    knowledge_domain: str = Field(description="Knowledge domain name")
    cost_usd: DecimalStr = Field(description="Total cost in USD")
    query_count: int = Field(default=0, description="Number of embedding queries")
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
