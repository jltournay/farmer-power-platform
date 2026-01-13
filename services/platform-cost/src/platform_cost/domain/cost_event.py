"""Domain models for unified cost events.

Story 13.3: Cost Repository and Budget Monitor
Story 13.6: BFF Integration Layer (moved response models to fp-common)

This module provides the storage model (UnifiedCostEvent) for the platform-cost service.
Response models are now imported from fp_common.models.cost for shared use by BFF.

The storage model converts from the fp_common.events.cost_recorded.CostRecordedEvent
published by services via DAPR pub/sub.
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from fp_common.events.cost_recorded import CostRecordedEvent, CostType

# Import response models from fp-common for backward compatibility
# Story 13.6: These models are now defined in fp_common.models.cost
from fp_common.models.cost import (
    AgentTypeCost,
    CostTypeSummary,
    CurrentDayCost,
    DailyCostEntry,
    DecimalStr,
    DocumentCostSummary,
    DomainCost,
    ModelCost,
)
from pydantic import BaseModel, Field, PlainSerializer

# Re-export for backward compatibility
__all__ = [
    "AgentTypeCost",
    "CostTypeSummary",
    "CurrentDayCost",
    "DailyCostEntry",
    "DecimalStr",
    "DocumentCostSummary",
    "DomainCost",
    "ModelCost",
    "UnifiedCostEvent",
]

# Local DecimalStr alias for UnifiedCostEvent (same definition as fp_common.models.cost)
_DecimalStr = Annotated[Decimal, PlainSerializer(str, return_type=str)]


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
    amount_usd: _DecimalStr = Field(ge=0, description="Cost amount in USD")
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
