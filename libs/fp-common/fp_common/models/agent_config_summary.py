"""Agent Config Summary and Detail models for BFF responses.

Story 9.12b: Agent Config gRPC Client + REST API in BFF

These models represent agent configurations and prompts for the Admin UI.
Used by the BFF to return typed responses instead of dicts.

Field mapping from Proto:
- AgentConfigSummary: Summary fields for list views
- AgentConfigDetail: Full config including JSON blob for detail views
- PromptSummary: Summary of a prompt linked to an agent

Reference:
- Proto definitions: proto/ai_model/v1/ai_model.proto
- Story: _bmad-output/sprint-artifacts/9-12b-agent-config-bff-client-rest.md
"""

from datetime import datetime

from pydantic import BaseModel, Field


class PromptSummary(BaseModel):
    """Summary view of a prompt for list endpoints.

    Contains essential fields for displaying prompts in a list view.

    Attributes:
        id: MongoDB document ID.
        prompt_id: Logical prompt identifier.
        agent_id: ID of the agent this prompt belongs to.
        version: Version string (semver format).
        status: Prompt status (draft, staged, active, archived).
        author: Author of the prompt.
        updated_at: When this prompt was last modified.
    """

    id: str = Field(description="MongoDB document ID")
    prompt_id: str = Field(description="Logical prompt identifier")
    agent_id: str = Field(description="Agent ID this prompt belongs to")
    version: str = Field(description="Version string (semver)")
    status: str = Field(description="Prompt status: draft, staged, active, archived")
    author: str = Field(default="", description="Author of the prompt")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")

    model_config = {"frozen": True}


class AgentConfigSummary(BaseModel):
    """Summary view of an agent configuration for list endpoints.

    Contains essential fields for displaying agent configs in a table/list view.
    Does NOT include the full config_json blob.

    Attributes:
        agent_id: Unique identifier for the agent configuration.
        version: Version string (semver format).
        agent_type: Type of agent (extractor, explorer, generator, conversational, tiered-vision).
        status: Configuration status (draft, staged, active, archived).
        description: Brief description of what this agent does.
        model: The LLM model used by this agent.
        prompt_count: Number of prompts linked to this agent.
        updated_at: When this config was last modified.
    """

    agent_id: str = Field(description="Unique agent identifier")
    version: str = Field(description="Version string (semver)")
    agent_type: str = Field(description="Agent type: extractor, explorer, generator, conversational, tiered-vision")
    status: str = Field(description="Config status: draft, staged, active, archived")
    description: str = Field(description="Agent description")
    model: str = Field(default="", description="LLM model used by this agent")
    prompt_count: int = Field(default=0, description="Number of linked prompts")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")

    model_config = {"frozen": True}


class PromptDetail(BaseModel):
    """Full detail view of a prompt for inline expansion (Story 9.12c - AC 9.12c.4).

    Contains all prompt content fields for displaying in the Admin UI
    prompt detail expansion view.

    Attributes:
        id: MongoDB document ID (format: {prompt_id}:{version}).
        prompt_id: Logical prompt identifier.
        agent_id: Agent ID this prompt belongs to.
        version: Version string (semver format).
        status: Prompt status (draft, staged, active, archived).
        author: Author of the prompt.
        updated_at: When this prompt was last modified.
        created_at: When this prompt was first created.
        changelog: What changed in this version.
        git_commit: Source commit SHA for traceability.
        system_prompt: Full system prompt text.
        template: Template with {{variables}}.
        output_schema_json: Output schema as JSON string.
        few_shot_examples_json: Few-shot examples as JSON array string.
        ab_test_enabled: Whether A/B testing is enabled.
        ab_test_traffic_percentage: Percentage of traffic for this variant (0-100).
    """

    id: str = Field(description="MongoDB document ID")
    prompt_id: str = Field(description="Logical prompt identifier")
    agent_id: str = Field(description="Agent ID this prompt belongs to")
    version: str = Field(description="Version string (semver)")
    status: str = Field(description="Prompt status: draft, staged, active, archived")
    author: str = Field(default="", description="Author of the prompt")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    changelog: str | None = Field(default=None, description="What changed in this version")
    git_commit: str | None = Field(default=None, description="Source commit SHA")
    system_prompt: str = Field(default="", description="Full system prompt text")
    template: str = Field(default="", description="Template with {{variables}}")
    output_schema_json: str | None = Field(default=None, description="Output schema as JSON string")
    few_shot_examples_json: str | None = Field(default=None, description="Few-shot examples as JSON array")
    ab_test_enabled: bool = Field(default=False, description="A/B test enabled")
    ab_test_traffic_percentage: float = Field(default=0.0, description="A/B test traffic percentage")

    model_config = {"frozen": True}


class AgentConfigDetail(AgentConfigSummary):
    """Full detail view of an agent configuration.

    Extends AgentConfigSummary with the complete configuration JSON blob
    and linked prompts. Used for detail views in the Admin UI.

    Attributes:
        config_json: Full configuration serialized as JSON string.
        prompts: List of PromptSummary objects linked to this agent.
        created_at: When this config was first created.
    """

    config_json: str = Field(description="Full configuration as JSON string")
    prompts: list[PromptSummary] = Field(default_factory=list, description="Linked prompts")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")

    model_config = {"frozen": True}
