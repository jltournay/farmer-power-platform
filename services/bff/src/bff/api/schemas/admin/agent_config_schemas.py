"""Agent Config admin API schemas (Story 9.12b).

Provides request/response schemas for AI agent configuration viewer:
- PromptSummaryResponse: Prompt summary for agent detail views
- AgentConfigSummaryResponse: List view with basic agent info
- AgentConfigDetailResponse: Full detail with config_json and prompts
- AgentConfigListResponse: Paginated list response
- PromptListResponse: List of prompts for an agent

These are API-layer schemas that mirror the fp_common domain models
but with ISO-formatted date strings for JSON serialization.
"""

from typing import TYPE_CHECKING

from bff.api.schemas.responses import PaginationMeta
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from fp_common.models import AgentConfigDetail, AgentConfigSummary, PromptSummary


class PromptSummaryResponse(BaseModel):
    """Prompt summary for admin views.

    Contains essential fields for displaying prompts in a list.
    """

    id: str = Field(description="MongoDB document ID")
    prompt_id: str = Field(description="Logical prompt identifier")
    agent_id: str = Field(description="Agent ID this prompt belongs to")
    version: str = Field(description="Version string (semver)")
    status: str = Field(description="Prompt status: draft, staged, active, archived")
    author: str = Field(default="", description="Author of the prompt")
    updated_at: str | None = Field(default=None, description="Last update timestamp (ISO format)")

    @classmethod
    def from_domain(cls, model: "PromptSummary") -> "PromptSummaryResponse":
        """Create API response from domain model.

        Args:
            model: PromptSummary domain model from fp_common.

        Returns:
            PromptSummaryResponse for API response.
        """
        return cls(
            id=model.id,
            prompt_id=model.prompt_id,
            agent_id=model.agent_id,
            version=model.version,
            status=model.status,
            author=model.author,
            updated_at=model.updated_at.isoformat() if model.updated_at else None,
        )


class AgentConfigSummaryResponse(BaseModel):
    """Agent configuration summary for admin list views.

    Contains essential fields for displaying agent configs in a table.
    Does NOT include the full config_json blob or linked prompts.
    """

    agent_id: str = Field(description="Unique agent identifier (e.g., 'disease-diagnosis')")
    version: str = Field(description="Version string (semver)")
    agent_type: str = Field(description="Agent type: extractor, explorer, generator, conversational, tiered-vision")
    status: str = Field(description="Config status: draft, staged, active, archived")
    description: str = Field(description="Brief description of the agent")
    model: str = Field(default="", description="LLM model used by this agent")
    prompt_count: int = Field(default=0, description="Number of linked prompts")
    updated_at: str | None = Field(default=None, description="Last update timestamp (ISO format)")

    @classmethod
    def from_domain(cls, model: "AgentConfigSummary") -> "AgentConfigSummaryResponse":
        """Create API response from domain model.

        Args:
            model: AgentConfigSummary domain model from fp_common.

        Returns:
            AgentConfigSummaryResponse for API response.
        """
        return cls(
            agent_id=model.agent_id,
            version=model.version,
            agent_type=model.agent_type,
            status=model.status,
            description=model.description,
            model=model.model,
            prompt_count=model.prompt_count,
            updated_at=model.updated_at.isoformat() if model.updated_at else None,
        )


class AgentConfigDetailResponse(AgentConfigSummaryResponse):
    """Full agent configuration detail for admin detail views.

    Extends summary with the complete configuration JSON blob and linked prompts.
    """

    config_json: str = Field(description="Full configuration serialized as JSON string")
    prompts: list[PromptSummaryResponse] = Field(default_factory=list, description="Linked prompt summaries")
    created_at: str | None = Field(default=None, description="Creation timestamp (ISO format)")

    @classmethod
    def from_domain(cls, model: "AgentConfigDetail") -> "AgentConfigDetailResponse":
        """Create API response from domain model.

        Args:
            model: AgentConfigDetail domain model from fp_common.

        Returns:
            AgentConfigDetailResponse for API response.
        """
        return cls(
            agent_id=model.agent_id,
            version=model.version,
            agent_type=model.agent_type,
            status=model.status,
            description=model.description,
            model=model.model,
            prompt_count=model.prompt_count,
            updated_at=model.updated_at.isoformat() if model.updated_at else None,
            config_json=model.config_json,
            prompts=[PromptSummaryResponse.from_domain(p) for p in model.prompts],
            created_at=model.created_at.isoformat() if model.created_at else None,
        )


class AgentConfigListResponse(BaseModel):
    """Paginated agent configuration list response."""

    data: list[AgentConfigSummaryResponse] = Field(
        description="List of agent configuration summaries",
    )
    pagination: PaginationMeta = Field(description="Pagination metadata")


class PromptListResponse(BaseModel):
    """List of prompts for an agent."""

    data: list[PromptSummaryResponse] = Field(
        description="List of prompt summaries",
    )
    total_count: int = Field(description="Total number of prompts")
