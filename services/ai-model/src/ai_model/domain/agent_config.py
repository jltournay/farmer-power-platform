"""Agent configuration domain models for AI Model service.

This module defines the Pydantic models for agent configuration storage.
Agent configs are stored in the ai_model.agent_configs MongoDB collection.

Key design decisions (see architecture/ai-model-architecture/key-decisions.md):
- Single collection with agent_type discriminator field
- Pydantic discriminated unions handle 5 agent types
- Version + status lifecycle for config management

Agent Types:
- extractor: Structured data extraction from unstructured input
- explorer: Multi-step analysis with conditional routing (RAG-enabled)
- generator: Content generation (plans, reports, messages) (RAG-enabled)
- conversational: Multi-turn dialogue with context management (RAG-enabled)
- tiered-vision: Cost-optimized image analysis with two-tier processing
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

# =============================================================================
# ENUMS
# =============================================================================


class AgentType(str, Enum):
    """Agent type enum.

    Defines the 5 agent types supported by the AI Model service.
    Each type has distinct configuration requirements and execution patterns.
    """

    EXTRACTOR = "extractor"
    EXPLORER = "explorer"
    GENERATOR = "generator"
    CONVERSATIONAL = "conversational"
    TIERED_VISION = "tiered-vision"


class AgentConfigStatus(str, Enum):
    """Agent configuration lifecycle status.

    Status transitions:
    - draft: Development, validation relaxed
    - staged: Ready for promotion
    - active: Currently in use (only one per agent_id)
    - archived: Historical version, kept for audit

    Transition flow: draft -> staged -> active -> archived
    """

    DRAFT = "draft"
    STAGED = "staged"
    ACTIVE = "active"
    ARCHIVED = "archived"


# =============================================================================
# SHARED COMPONENT MODELS
# =============================================================================


class LLMConfig(BaseModel):
    """LLM configuration for agent execution.

    Specifies the model and parameters for LLM calls.
    Model is explicit per agent (no task_type routing).
    """

    model: str = Field(description="Explicit model identifier, e.g. 'anthropic/claude-3-5-sonnet'")
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0-2.0)",
    )
    max_tokens: int = Field(
        default=2000,
        ge=1,
        le=100000,
        description="Maximum tokens in response",
    )


class RAGConfig(BaseModel):
    """RAG retrieval configuration.

    Configures knowledge retrieval for RAG-enabled agents
    (Explorer, Generator, Conversational, Tiered-Vision Tier 2).
    """

    enabled: bool = Field(
        default=True,
        description="Whether RAG is enabled for this agent",
    )
    query_template: str | None = Field(
        default=None,
        description="Template for RAG query construction with {{variables}}",
    )
    knowledge_domains: list[str] = Field(
        default_factory=list,
        description="Knowledge domains to search (e.g., 'plant_diseases', 'tea_cultivation')",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Number of documents to retrieve",
    )
    min_similarity: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity threshold for results",
    )


class InputConfig(BaseModel):
    """Agent input contract.

    Defines the event that triggers the agent and expected input schema.
    """

    event: str = Field(description="DAPR event topic that triggers this agent (e.g., 'collection.document.received')")
    schema: dict[str, Any] = Field(description="JSON schema defining required and optional input fields")


class OutputConfig(BaseModel):
    """Agent output contract.

    Defines the event published on completion and output schema.
    """

    event: str = Field(description="DAPR event topic for completion (e.g., 'ai.extraction.complete')")
    schema: dict[str, Any] = Field(description="JSON schema defining output fields")


class MCPSourceConfig(BaseModel):
    """MCP server data source configuration.

    Specifies which MCP server tools the agent can use for data retrieval.
    """

    server: str = Field(description="MCP server name (e.g., 'collection', 'plantation')")
    tools: list[str] = Field(description="List of tools to use from this server (e.g., ['get_document', 'get_farmer'])")


class ErrorHandlingConfig(BaseModel):
    """Error handling and retry configuration.

    Configures retry behavior and failure handling for agent execution.
    """

    max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts",
    )
    backoff_ms: list[int] = Field(
        default_factory=lambda: [100, 500, 2000],
        description="Backoff delays in milliseconds between retries",
    )
    on_failure: Literal["publish_error_event", "dead_letter", "graceful_fallback"] = Field(
        default="publish_error_event",
        description="Action on final failure",
    )
    dead_letter_topic: str | None = Field(
        default=None,
        description="Dead letter topic for failed messages (if on_failure='dead_letter')",
    )


class StateConfig(BaseModel):
    """Conversation state management configuration.

    Used only by Conversational agents for multi-turn dialogue.
    """

    max_turns: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum turns in a conversation",
    )
    session_ttl_minutes: int = Field(
        default=30,
        ge=1,
        le=1440,
        description="Session timeout in minutes",
    )
    checkpoint_backend: Literal["mongodb"] = Field(
        default="mongodb",
        description="Backend for state persistence",
    )
    context_window: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Number of previous turns to include in prompt",
    )


class AgentConfigMetadata(BaseModel):
    """Agent configuration metadata for tracking changes.

    Stores authorship, timestamps, and version control info.
    """

    author: str = Field(description="Author username or system identifier")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last update timestamp",
    )
    git_commit: str | None = Field(
        default=None,
        description="Source commit SHA for traceability",
    )


# =============================================================================
# TIERED-VISION SPECIFIC MODELS
# =============================================================================


class TieredVisionLLMConfig(BaseModel):
    """Two-tier LLM configuration for vision processing.

    Cost-optimized: Haiku for fast screening, Sonnet for deep analysis.
    """

    screen: LLMConfig = Field(description="Tier 1: Fast screening model (typically Haiku)")
    diagnose: LLMConfig = Field(description="Tier 2: Deep analysis model (typically Sonnet)")


class TieredVisionRoutingConfig(BaseModel):
    """Routing configuration for tiered vision processing.

    Determines when to escalate from Tier 1 (screen) to Tier 2 (diagnose).
    """

    screen_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Escalate to Tier 2 if screen confidence < threshold",
    )
    healthy_skip_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Skip Tier 2 for 'healthy' classification above this confidence",
    )
    obvious_skip_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Skip Tier 2 for 'obvious_issue' classification above this confidence",
    )


# =============================================================================
# BASE CLASS (common fields)
# =============================================================================


class AgentConfigBase(BaseModel):
    """Base configuration shared by all agent types.

    Contains common fields that all agent configurations must have.
    Type-specific models inherit from this and add their specialized fields.
    """

    id: str = Field(description="Unique document ID (format: {agent_id}:{version})")
    agent_id: str = Field(description="Logical agent identifier (e.g., 'disease-diagnosis')")
    version: str = Field(description="Semantic version string (e.g., '1.0.0')")
    status: AgentConfigStatus = Field(
        default=AgentConfigStatus.DRAFT,
        description="Agent configuration lifecycle status",
    )
    description: str = Field(description="Human-readable description of what this agent does")
    input: InputConfig = Field(description="Input event and schema contract")
    output: OutputConfig = Field(description="Output event and schema contract")
    llm: LLMConfig = Field(description="LLM configuration for agent execution")
    mcp_sources: list[MCPSourceConfig] = Field(
        default_factory=list,
        description="MCP servers and tools this agent can use",
    )
    error_handling: ErrorHandlingConfig = Field(
        default_factory=ErrorHandlingConfig,
        description="Error handling and retry configuration",
    )
    metadata: AgentConfigMetadata = Field(
        description="Agent configuration metadata",
    )


# =============================================================================
# TYPE-SPECIFIC MODELS
# =============================================================================


class ExtractorConfig(AgentConfigBase):
    """Extractor agent: structured data from unstructured input.

    Uses single LLM call for fast, deterministic extraction.
    No RAG required - works directly on input data.
    """

    type: Literal["extractor"] = Field(
        default="extractor",
        description="Agent type discriminator",
    )
    extraction_schema: dict[str, Any] = Field(description="Schema defining fields to extract and validation rules")
    normalization_rules: list[dict[str, Any]] | None = Field(
        default=None,
        description="Optional rules for value normalization (e.g., uppercase, prefix)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "qc-event-extractor:1.0.0",
                "agent_id": "qc-event-extractor",
                "version": "1.0.0",
                "type": "extractor",
                "status": "active",
                "description": "Extracts structured data from QC analyzer payloads",
                "input": {
                    "event": "collection.document.received",
                    "schema": {"required": ["doc_id"]},
                },
                "output": {
                    "event": "ai.extraction.complete",
                    "schema": {"fields": ["farmer_id", "grade", "quality_score"]},
                },
                "llm": {
                    "model": "anthropic/claude-3-haiku",
                    "temperature": 0.1,
                    "max_tokens": 500,
                },
                "extraction_schema": {"required_fields": ["farmer_id", "grade"]},
            }
        }
    }


class ExplorerConfig(AgentConfigBase):
    """Explorer agent: analyze, diagnose, find patterns.

    Uses RAG for knowledge retrieval to inform analysis.
    Single LLM capable model for complex reasoning.
    """

    type: Literal["explorer"] = Field(
        default="explorer",
        description="Agent type discriminator",
    )
    rag: RAGConfig = Field(description="RAG configuration for knowledge retrieval")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "disease-diagnosis:1.0.0",
                "agent_id": "disease-diagnosis",
                "version": "1.0.0",
                "type": "explorer",
                "status": "active",
                "description": "Analyzes quality issues and produces diagnosis",
                "llm": {
                    "model": "anthropic/claude-3-5-sonnet",
                    "temperature": 0.3,
                    "max_tokens": 2000,
                },
                "rag": {
                    "enabled": True,
                    "knowledge_domains": ["plant_diseases", "tea_cultivation"],
                    "top_k": 5,
                },
            }
        }
    }


class GeneratorConfig(AgentConfigBase):
    """Generator agent: create content (plans, reports, messages).

    Uses RAG for best practices and context.
    Supports multiple output formats (json, markdown, text).
    """

    type: Literal["generator"] = Field(
        default="generator",
        description="Agent type discriminator",
    )
    rag: RAGConfig = Field(description="RAG configuration for knowledge retrieval")
    output_format: Literal["json", "markdown", "text"] = Field(
        default="markdown",
        description="Output content format",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "weekly-action-plan:1.0.0",
                "agent_id": "weekly-action-plan",
                "version": "1.0.0",
                "type": "generator",
                "status": "active",
                "description": "Generates personalized weekly action plans for farmers",
                "llm": {
                    "model": "anthropic/claude-3-5-sonnet",
                    "temperature": 0.5,
                    "max_tokens": 3000,
                },
                "rag": {
                    "enabled": True,
                    "knowledge_domains": ["tea_cultivation", "regional_context"],
                },
                "output_format": "markdown",
            }
        }
    }


class ConversationalConfig(AgentConfigBase):
    """Conversational agent: multi-turn dialogue with persona.

    Uses two LLMs: fast model for intent, capable model for response.
    Includes RAG for knowledge grounding and state management.
    """

    type: Literal["conversational"] = Field(
        default="conversational",
        description="Agent type discriminator",
    )
    rag: RAGConfig = Field(description="RAG configuration for knowledge grounding")
    state: StateConfig = Field(
        default_factory=StateConfig,
        description="Conversation state management configuration",
    )
    intent_model: str = Field(
        default="anthropic/claude-3-haiku",
        description="Fast model for intent classification",
    )
    response_model: str = Field(
        default="anthropic/claude-3-5-sonnet",
        description="Capable model for generating responses",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "dialogue-responder:1.0.0",
                "agent_id": "dialogue-responder",
                "version": "1.0.0",
                "type": "conversational",
                "status": "active",
                "description": "Handles multi-turn dialogue with farmers via voice/WhatsApp",
                "llm": {"model": "anthropic/claude-3-5-sonnet", "temperature": 0.4},
                "rag": {
                    "enabled": True,
                    "knowledge_domains": ["tea_cultivation", "common_questions"],
                },
                "state": {"max_turns": 5, "session_ttl_minutes": 30},
                "intent_model": "anthropic/claude-3-haiku",
                "response_model": "anthropic/claude-3-5-sonnet",
            }
        }
    }


class TieredVisionConfig(AgentConfigBase):
    """Tiered-Vision agent: cost-optimized image analysis.

    Two-tier processing:
    - Tier 1 (screen): Fast Haiku classification on thumbnail
    - Tier 2 (diagnose): Deep Sonnet analysis on full image (if needed)

    Routing config determines when to escalate to Tier 2.
    """

    type: Literal["tiered-vision"] = Field(
        default="tiered-vision",
        description="Agent type discriminator",
    )
    # Override base llm to be optional (replaced by tiered_llm)
    llm: LLMConfig | None = Field(
        default=None,
        description="Not used - tiered_llm replaces this for tiered-vision agents",
    )
    rag: RAGConfig = Field(description="RAG configuration (used in Tier 2 only)")
    tiered_llm: TieredVisionLLMConfig = Field(description="Two-tier LLM configuration (screen + diagnose)")
    routing: TieredVisionRoutingConfig = Field(
        default_factory=TieredVisionRoutingConfig,
        description="Routing thresholds for tier escalation",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "leaf-quality-analyzer:1.0.0",
                "agent_id": "leaf-quality-analyzer",
                "version": "1.0.0",
                "type": "tiered-vision",
                "status": "active",
                "description": "Cost-optimized image analysis for tea leaf quality",
                "llm": None,
                "rag": {
                    "enabled": True,
                    "knowledge_domains": ["plant_diseases", "visual_symptoms"],
                },
                "tiered_llm": {
                    "screen": {
                        "model": "anthropic/claude-3-haiku",
                        "temperature": 0.1,
                        "max_tokens": 200,
                    },
                    "diagnose": {
                        "model": "anthropic/claude-3-5-sonnet",
                        "temperature": 0.3,
                        "max_tokens": 2000,
                    },
                },
                "routing": {
                    "screen_threshold": 0.7,
                    "healthy_skip_threshold": 0.85,
                },
            }
        }
    }


# =============================================================================
# DISCRIMINATED UNION (automatic type detection)
# =============================================================================

AgentConfig = Annotated[
    ExtractorConfig | ExplorerConfig | GeneratorConfig | ConversationalConfig | TieredVisionConfig,
    Field(discriminator="type"),
]
"""Discriminated union of all agent configuration types.

Usage:
    from pydantic import TypeAdapter

    adapter = TypeAdapter(AgentConfig)
    config = adapter.validate_python({"type": "explorer", ...})  # Returns ExplorerConfig

Pydantic automatically selects the correct type based on the "type" field.
"""
