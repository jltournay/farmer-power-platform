"""Unified Cost Event Model for the Farmer Power Platform.

Story 13.1: Shared Cost Event Model (ADR-016)

This module defines the unified CostRecordedEvent model that ALL services
can use to publish cost events to the `platform.cost.recorded` DAPR topic.

Cost Types Supported:
- llm: LLM API calls (tokens)
- document: Document processing (pages)
- embedding: Text embeddings (queries)
- sms: SMS messages (messages)

Usage:
    from fp_common.events.cost_recorded import CostRecordedEvent, CostType, CostUnit

    event = CostRecordedEvent(
        cost_type=CostType.LLM,
        amount_usd="0.0015",  # String for Decimal precision
        quantity=1500,
        unit=CostUnit.TOKENS,
        timestamp=datetime.now(UTC),
        source_service="ai-model",
        success=True,
        metadata={
            "model": "anthropic/claude-3-haiku",
            "agent_type": "extractor",
            "tokens_in": 1000,
            "tokens_out": 500,
        },
    )

    # Serialize for DAPR pub/sub
    json_str = event.model_dump_json()
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, Field, PlainSerializer, model_validator


class CostType(str, Enum):
    """Types of costs tracked by the platform.

    Each cost type has specific metadata fields expected in the metadata dict.

    Attributes:
        LLM: LLM API calls (OpenRouter, etc.)
             Metadata: model, agent_type, tokens_in, tokens_out
        DOCUMENT: Document processing (Azure Document Intelligence, etc.)
             Metadata: model_id, page_count
        EMBEDDING: Text embedding generation
             Metadata: model, texts_count
        SMS: SMS message delivery (Africa's Talking, etc.)
             Metadata: message_type, recipient_count
    """

    LLM = "llm"
    DOCUMENT = "document"
    EMBEDDING = "embedding"
    SMS = "sms"


class CostUnit(str, Enum):
    """Units for measuring cost quantities.

    Attributes:
        TOKENS: Token count for LLM calls
        PAGES: Page count for document processing
        MESSAGES: Message count for SMS
        QUERIES: Query count for embeddings
    """

    TOKENS = "tokens"
    PAGES = "pages"
    MESSAGES = "messages"
    QUERIES = "queries"


# Custom type for Decimal that serializes as string to preserve precision
DecimalStr = Annotated[Decimal, PlainSerializer(str, return_type=str)]


class CostRecordedEvent(BaseModel):
    """Unified cost event model for all platform cost tracking.

    Published to `platform.cost.recorded` DAPR topic by all services
    that incur billable costs (LLM calls, document processing, SMS, etc.).

    This replaces the previous LLM-only CostRecordedEvent from ai_model_events.py
    with a unified schema that supports all cost types.

    Attributes:
        cost_type: Type of cost (llm, document, embedding, sms)
        amount_usd: Cost amount in USD as string (preserves Decimal precision)
        quantity: Number of units (tokens, pages, messages, queries)
        unit: Unit type for the quantity
        timestamp: When the cost was incurred (UTC)
        source_service: Service that incurred the cost
        success: Whether the operation succeeded
        metadata: Type-specific metadata (model, agent_type, tokens_in/out, etc.)
        factory_id: Optional factory ID for cost attribution
        request_id: Optional correlation ID for tracing
    """

    cost_type: CostType = Field(
        description="Type of cost (llm, document, embedding, sms)",
    )
    amount_usd: DecimalStr = Field(
        ge=0,
        description="Cost amount in USD (serialized as string for precision)",
    )
    quantity: int = Field(
        ge=0,
        description="Number of units consumed (tokens, pages, messages, queries)",
    )
    unit: CostUnit = Field(
        description="Unit type for the quantity",
    )
    timestamp: datetime = Field(
        description="When the cost was incurred (UTC)",
    )
    source_service: str = Field(
        description="Service that incurred the cost (e.g., 'ai-model', 'notification-model')",
    )
    success: bool = Field(
        description="Whether the operation succeeded",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Type-specific metadata (model, agent_type, tokens_in/out, etc.)",
    )
    factory_id: str | None = Field(
        default=None,
        description="Optional factory ID for cost attribution",
    )
    request_id: str | None = Field(
        default=None,
        description="Optional correlation ID for tracing",
    )

    model_config = {
        "use_enum_values": True,  # Serialize enums as their string values
    }

    # Valid CostType → CostUnit mappings
    _VALID_UNIT_BY_TYPE: dict[CostType, CostUnit] = {
        CostType.LLM: CostUnit.TOKENS,
        CostType.DOCUMENT: CostUnit.PAGES,
        CostType.EMBEDDING: CostUnit.QUERIES,
        CostType.SMS: CostUnit.MESSAGES,
    }

    @model_validator(mode="after")
    def validate_cost_type_unit_match(self) -> "CostRecordedEvent":
        """Validate that cost_type and unit are a valid combination."""
        expected_unit = self._VALID_UNIT_BY_TYPE.get(self.cost_type)
        if expected_unit and self.unit != expected_unit:
            raise ValueError(
                f"Invalid unit '{self.unit}' for cost_type '{self.cost_type}'. Expected '{expected_unit}'."
            )
        return self
