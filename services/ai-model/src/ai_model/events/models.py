"""Event payload models for AI Model DAPR pub/sub.

Story 0.75.8: Event Flow, Subscriber, and Publisher (AC: #3)

This module defines Pydantic models for all AI Model event payloads:
- EntityLinkage: Required linkage to Plantation Model entities
- AgentRequestEvent: Inbound request to execute an agent
- AgentResult: Discriminated union of typed results per agent type
- AgentCompletedEvent: Successful agent execution result
- AgentFailedEvent: Failed agent execution
- CostRecordedEvent: LLM cost tracking event
"""

from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, model_validator

# =============================================================================
# Entity Linkage (Required for all agent events)
# =============================================================================


class EntityLinkage(BaseModel):
    """Linkage to Plantation Model entities - at least one field required.

    Every AI analysis must be linked to a plantation entity so results
    can be stored/routed correctly by consuming services.

    Hierarchy: Region → Collection Points → Farmers (with plantations)
               Factory ← receives from Collection Points
    """

    farmer_id: str | None = Field(
        default=None,
        description="Link to specific farmer (most common)",
    )
    region_id: str | None = Field(
        default=None,
        description="Link to region (weather, trends)",
    )
    group_id: str | None = Field(
        default=None,
        description="Link to farmer group (broadcasts)",
    )
    collection_point_id: str | None = Field(
        default=None,
        description="Link to collection point",
    )
    factory_id: str | None = Field(
        default=None,
        description="Link to processing factory",
    )

    @model_validator(mode="after")
    def at_least_one_linkage(self) -> "EntityLinkage":
        """Ensure at least one linkage field is provided."""
        if not any(
            [
                self.farmer_id,
                self.region_id,
                self.group_id,
                self.collection_point_id,
                self.factory_id,
            ]
        ):
            raise ValueError(
                "At least one linkage field required (farmer_id, region_id, "
                "group_id, collection_point_id, or factory_id)"
            )
        return self


# =============================================================================
# Agent Request Event (Inbound)
# =============================================================================


class AgentRequestEvent(BaseModel):
    """Request to execute an agent workflow.

    Published by domain models (Collection, Knowledge, etc.) to trigger
    agent execution in the AI Model.
    """

    request_id: str = Field(
        description="Correlation ID for tracking the request",
    )
    agent_id: str = Field(
        description="Agent config ID (e.g., 'disease-diagnosis', 'qc-event-extractor')",
    )
    linkage: EntityLinkage = Field(
        description="REQUIRED - link to plantation entities for result routing",
    )
    input_data: dict[str, Any] = Field(
        description="Agent-specific input payload",
    )
    context: dict[str, Any] | None = Field(
        default=None,
        description="Optional execution context (e.g., session info, preferences)",
    )
    source: str = Field(
        description="Requesting service (e.g., 'collection-model', 'knowledge-model')",
    )


# =============================================================================
# Agent Result Types (Discriminated Union)
# =============================================================================


class ExtractorAgentResult(BaseModel):
    """Result from extractor agent - field extraction per agent's extraction_schema.

    Note: extracted_fields schema is defined in agent config, not hardcoded here.
    The AI Model is fully configurable - extraction schemas come from agent YAML.
    """

    result_type: Literal["extractor"] = Field(
        default="extractor",
        description="Discriminator for result type",
    )
    extracted_fields: dict[str, Any] = Field(
        description="Fields per agent's extraction_schema config",
    )
    validation_warnings: list[str] = Field(
        default_factory=list,
        description="Non-blocking validation warnings",
    )
    validation_errors: list[str] = Field(
        default_factory=list,
        description="Blocking validation errors",
    )
    normalization_applied: bool = Field(
        default=False,
        description="Whether data normalization was applied",
    )


class ExplorerAgentResult(BaseModel):
    """Result from explorer/diagnosis agent - analysis with confidence."""

    result_type: Literal["explorer"] = Field(
        default="explorer",
        description="Discriminator for result type",
    )
    diagnosis: str = Field(
        description="Primary diagnosis or analysis finding",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0)",
    )
    severity: Literal["low", "medium", "high", "critical"] = Field(
        description="Severity classification of the finding",
    )
    contributing_factors: list[str] = Field(
        default_factory=list,
        description="Factors that contributed to the diagnosis",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Recommended actions based on diagnosis",
    )
    rag_sources_used: list[str] = Field(
        default_factory=list,
        description="RAG document IDs used for the analysis",
    )


class GeneratorAgentResult(BaseModel):
    """Result from generator agent - formatted content output."""

    result_type: Literal["generator"] = Field(
        default="generator",
        description="Discriminator for result type",
    )
    content: str = Field(
        description="The generated content",
    )
    format: Literal["json", "markdown", "text", "sms", "voice_script"] = Field(
        description="Output format of the generated content",
    )
    target_audience: str | None = Field(
        default=None,
        description="Intended audience for the content (e.g., 'farmer', 'factory_manager')",
    )
    language: str = Field(
        default="en",
        description="Language code (e.g., 'en', 'sw', 'ki')",
    )


class ConversationalAgentResult(BaseModel):
    """Result from conversational agent - dialogue response."""

    result_type: Literal["conversational"] = Field(
        default="conversational",
        description="Discriminator for result type",
    )
    response_text: str = Field(
        description="The response text to send to the user",
    )
    detected_intent: str = Field(
        description="Detected user intent (e.g., 'ask_quality', 'request_action_plan')",
    )
    intent_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in intent detection (0.0-1.0)",
    )
    session_id: str = Field(
        description="Conversation session identifier",
    )
    turn_number: int = Field(
        ge=1,
        description="Turn number in the conversation (1-indexed)",
    )
    suggested_actions: list[str] = Field(
        default_factory=list,
        description="Suggested follow-up actions for the user",
    )


class TieredVisionAgentResult(BaseModel):
    """Result from tiered-vision agent - cost-optimized image analysis."""

    result_type: Literal["tiered-vision"] = Field(
        default="tiered-vision",
        description="Discriminator for result type",
    )
    classification: str = Field(
        description="Classification result (healthy, diseased, damaged, unknown)",
    )
    classification_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in classification (0.0-1.0)",
    )
    diagnosis: str | None = Field(
        default=None,
        description="Detailed diagnosis (only if escalated to diagnose tier)",
    )
    tier_used: Literal["screen", "diagnose"] = Field(
        description="Which tier was used for analysis",
    )
    cost_saved: bool = Field(
        description="True if screen tier was sufficient (avoided expensive diagnose tier)",
    )


# Discriminated union - client matches on result_type
# Linkage is in the event envelope (AgentCompletedEvent), not in result
AgentResult = Annotated[
    ExtractorAgentResult
    | ExplorerAgentResult
    | GeneratorAgentResult
    | ConversationalAgentResult
    | TieredVisionAgentResult,
    Field(discriminator="result_type"),
]


# =============================================================================
# Agent Completed Event (Outbound - Success)
# =============================================================================


class AgentCompletedEvent(BaseModel):
    """Successful agent execution result.

    Published by AI Model when an agent workflow completes successfully.
    Consumers match on result.result_type to determine which result type to parse.
    """

    request_id: str = Field(
        description="Correlation ID from the original request",
    )
    agent_id: str = Field(
        description="Agent config ID that was executed",
    )
    linkage: EntityLinkage = Field(
        description="Which entity this result belongs to",
    )
    result: AgentResult = Field(
        description="Typed result - client matches on result_type discriminator",
    )
    execution_time_ms: int = Field(
        ge=0,
        description="Total execution time in milliseconds",
    )
    model_used: str = Field(
        description="Which LLM model was used (e.g., 'anthropic/claude-3-haiku')",
    )
    cost_usd: Decimal | None = Field(
        default=None,
        description="Total cost in USD for this execution",
    )


# =============================================================================
# Agent Failed Event (Outbound - Failure)
# =============================================================================


class AgentFailedEvent(BaseModel):
    """Failed agent execution.

    Published by AI Model when an agent workflow fails after all retries.
    """

    request_id: str = Field(
        description="Correlation ID from the original request",
    )
    agent_id: str = Field(
        description="Agent config ID that was attempted",
    )
    linkage: EntityLinkage = Field(
        description="Which entity this failure relates to",
    )
    error_type: str = Field(
        description="Error category (validation, llm_error, timeout, config_not_found, etc.)",
    )
    error_message: str = Field(
        description="Human-readable error message",
    )
    retry_count: int = Field(
        ge=0,
        description="Number of retry attempts made",
    )


# =============================================================================
# Cost Recorded Event (Outbound - Telemetry)
# =============================================================================


class CostRecordedEvent(BaseModel):
    """LLM cost tracking event.

    Published after each LLM call for cost monitoring and budget alerting.
    From Story 0.75.5 - OpenRouter LLM Gateway with Cost Observability.
    """

    request_id: str = Field(
        description="Correlation ID for the request",
    )
    agent_id: str = Field(
        description="Agent config ID that made the LLM call",
    )
    model: str = Field(
        description="LLM model used (e.g., 'anthropic/claude-3-haiku')",
    )
    tokens_in: int = Field(
        ge=0,
        description="Input tokens consumed",
    )
    tokens_out: int = Field(
        ge=0,
        description="Output tokens generated",
    )
    cost_usd: Decimal = Field(
        description="Total cost in USD",
    )
