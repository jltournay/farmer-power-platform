"""LLM Cost Event domain model.

This module defines the Pydantic model for LLM cost events, which tracks
all LLM call costs for observability and budget management.

Story 0.75.5: OpenRouter LLM Gateway with Cost Observability
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field


def _serialize_decimal(value: Decimal) -> str:
    """Serialize Decimal to string for MongoDB storage."""
    return str(value)


DecimalField = Annotated[Decimal, Field(default=Decimal("0"))]


class LlmCostEvent(BaseModel):
    """LLM cost event for tracking all LLM call costs.

    Each LLM call generates a cost event that is stored in MongoDB
    and published via DAPR pub/sub for observability.

    Attributes:
        id: Unique event identifier (UUID).
        timestamp: When the LLM call completed (UTC).
        request_id: Correlation ID for distributed tracing.
        agent_type: Type of agent (extractor, explorer, generator, etc.).
        agent_id: Specific agent configuration ID.
        model: The LLM model used (may differ from requested if fallback).
        tokens_in: Input tokens (native/billing tokens from OpenRouter).
        tokens_out: Output tokens (native/billing tokens).
        cost_usd: Total cost in USD (Decimal for precision).
        factory_id: Optional factory ID for cost attribution.
        success: Whether the request succeeded.
        retry_count: Number of retries before success/failure.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        json_encoders={
            Decimal: _serialize_decimal,
        },
    )

    id: str = Field(
        ...,
        description="Unique event identifier (UUID)",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the LLM call completed (UTC)",
    )
    request_id: str = Field(
        ...,
        description="Correlation ID for distributed tracing",
    )
    agent_type: str = Field(
        ...,
        description="Type of agent (extractor, explorer, generator, conversational, tiered_vision)",
    )
    agent_id: str = Field(
        ...,
        description="Specific agent configuration ID",
    )
    model: str = Field(
        ...,
        description="The LLM model used (e.g., anthropic/claude-3-5-sonnet)",
    )
    tokens_in: int = Field(
        default=0,
        ge=0,
        description="Input tokens (native/billing tokens from OpenRouter)",
    )
    tokens_out: int = Field(
        default=0,
        ge=0,
        description="Output tokens (native/billing tokens)",
    )
    cost_usd: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Total cost in USD (from OpenRouter billing)",
    )
    factory_id: str | None = Field(
        default=None,
        description="Factory ID for per-factory cost attribution",
    )
    success: bool = Field(
        default=True,
        description="Whether the request succeeded",
    )
    retry_count: int = Field(
        default=0,
        ge=0,
        description="Number of retries before success/failure",
    )

    @property
    def total_tokens(self) -> int:
        """Return total tokens (input + output)."""
        return self.tokens_in + self.tokens_out

    def model_dump_for_mongo(self) -> dict[str, Any]:
        """Dump model for MongoDB storage.

        Converts Decimal to string for MongoDB compatibility and
        handles datetime serialization.
        """
        data = self.model_dump()
        # Convert Decimal to string for MongoDB storage
        if isinstance(data.get("cost_usd"), Decimal):
            data["cost_usd"] = str(data["cost_usd"])
        return data

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> "LlmCostEvent":
        """Create instance from MongoDB document.

        Handles conversion of string back to Decimal.
        """
        # Convert string cost back to Decimal
        if "cost_usd" in doc and isinstance(doc["cost_usd"], str):
            doc["cost_usd"] = Decimal(doc["cost_usd"])
        # Remove MongoDB _id if present
        doc.pop("_id", None)
        return cls.model_validate(doc)


class DailyCostSummary(BaseModel):
    """Daily cost summary aggregation.

    Used for reporting daily LLM costs.
    """

    model_config = ConfigDict(
        json_encoders={Decimal: _serialize_decimal},
    )

    date: datetime = Field(..., description="The date (UTC, truncated to day)")
    total_cost_usd: Decimal = Field(
        default=Decimal("0"),
        description="Total cost for the day in USD",
    )
    total_requests: int = Field(
        default=0,
        description="Total number of LLM requests",
    )
    total_tokens_in: int = Field(
        default=0,
        description="Total input tokens",
    )
    total_tokens_out: int = Field(
        default=0,
        description="Total output tokens",
    )
    success_count: int = Field(
        default=0,
        description="Number of successful requests",
    )
    failure_count: int = Field(
        default=0,
        description="Number of failed requests",
    )


class AgentTypeCost(BaseModel):
    """Cost summary grouped by agent type.

    Used for understanding cost distribution across agent types.
    """

    model_config = ConfigDict(
        json_encoders={Decimal: _serialize_decimal},
    )

    agent_type: str = Field(..., description="Agent type")
    total_cost_usd: Decimal = Field(
        default=Decimal("0"),
        description="Total cost for this agent type",
    )
    total_requests: int = Field(
        default=0,
        description="Number of requests",
    )
    total_tokens: int = Field(
        default=0,
        description="Total tokens (in + out)",
    )


class ModelCost(BaseModel):
    """Cost summary grouped by model.

    Used for understanding cost distribution across models.
    """

    model_config = ConfigDict(
        json_encoders={Decimal: _serialize_decimal},
    )

    model: str = Field(..., description="Model identifier")
    total_cost_usd: Decimal = Field(
        default=Decimal("0"),
        description="Total cost for this model",
    )
    total_requests: int = Field(
        default=0,
        description="Number of requests",
    )
    total_tokens: int = Field(
        default=0,
        description="Total tokens (in + out)",
    )


class CostSummary(BaseModel):
    """General cost summary.

    Used for current day cost tracking and alerts.
    """

    model_config = ConfigDict(
        json_encoders={Decimal: _serialize_decimal},
    )

    total_cost_usd: Decimal = Field(
        default=Decimal("0"),
        description="Total cost in USD",
    )
    total_requests: int = Field(
        default=0,
        description="Total number of requests",
    )
    total_tokens_in: int = Field(
        default=0,
        description="Total input tokens",
    )
    total_tokens_out: int = Field(
        default=0,
        description="Total output tokens",
    )
