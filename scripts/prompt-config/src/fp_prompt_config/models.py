"""Prompt models for the CLI.

Re-exports the Prompt Pydantic models from ai_model.domain.prompt.
These models define the schema for prompt YAML files.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PromptStatus(str, Enum):
    """Prompt lifecycle status.

    Status transitions:
    - draft: Development, agent_id validation skipped
    - staged: Ready for promotion, requires valid agent_id
    - active: Currently in use (only one per prompt_id)
    - archived: Historical version, kept for audit

    Transition flow: draft → staged → active → archived
    """

    DRAFT = "draft"
    STAGED = "staged"
    ACTIVE = "active"
    ARCHIVED = "archived"


class PromptContent(BaseModel):
    """Prompt content configuration.

    Contains the actual prompt text and schema definitions.
    """

    system_prompt: str = Field(
        description="Full system prompt text that sets agent behavior"
    )
    template: str = Field(description="Template with {{variables}} for dynamic content")
    output_schema: dict[str, Any] | None = Field(
        default=None,
        description="JSON schema for structured output validation",
    )
    few_shot_examples: list[dict[str, Any]] | None = Field(
        default=None,
        description="Optional few-shot examples for in-context learning",
    )


class PromptMetadata(BaseModel):
    """Prompt metadata for tracking changes.

    Stores authorship, timestamps, and change history.
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
    changelog: str | None = Field(
        default=None,
        description="What changed in this version",
    )
    git_commit: str | None = Field(
        default=None,
        description="Source commit SHA for traceability",
    )


class PromptABTest(BaseModel):
    """A/B test configuration for prompts.

    Enables testing variant prompts against production.
    """

    enabled: bool = Field(
        default=False,
        description="Whether A/B testing is enabled",
    )
    traffic_percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Percentage of traffic for this variant (0-100)",
    )
    test_id: str | None = Field(
        default=None,
        description="Test identifier for metrics grouping",
    )


class Prompt(BaseModel):
    """Prompt entity - AI prompt configuration with versioning.

    Prompts are stored in the ai_model.prompts collection.
    Each prompt has a unique combination of (prompt_id, version).

    Key relationships:
    - prompt_id: Logical identifier (e.g., "disease-diagnosis")
    - agent_id: Links to agent configuration (e.g., "diagnose-quality-issue")
    - version: Semantic version string (e.g., "2.1.0")
    """

    id: str = Field(description="Unique document ID (format: {prompt_id}:{version})")
    prompt_id: str = Field(
        description="Logical prompt identifier (e.g., 'disease-diagnosis')"
    )
    agent_id: str = Field(
        description="Links to agent config (e.g., 'diagnose-quality-issue')"
    )
    version: str = Field(description="Semantic version string (e.g., '2.1.0')")
    status: PromptStatus = Field(
        default=PromptStatus.DRAFT,
        description="Prompt lifecycle status",
    )
    content: PromptContent = Field(
        description="Prompt content configuration",
    )
    metadata: PromptMetadata = Field(
        description="Prompt metadata for tracking",
    )
    ab_test: PromptABTest = Field(
        default_factory=PromptABTest,
        description="A/B test configuration",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "disease-diagnosis:1.0.0",
                "prompt_id": "disease-diagnosis",
                "agent_id": "diagnose-quality-issue",
                "version": "1.0.0",
                "status": "active",
                "content": {
                    "system_prompt": "You are an expert tea disease diagnostician...",
                    "template": "Analyze the following quality event: {{event_data}}",
                    "output_schema": {
                        "type": "object",
                        "properties": {
                            "condition": {"type": "string"},
                            "confidence": {"type": "number"},
                        },
                    },
                    "few_shot_examples": None,
                },
                "metadata": {
                    "author": "admin",
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                    "changelog": "Initial version",
                    "git_commit": "abc123",
                },
                "ab_test": {
                    "enabled": False,
                    "traffic_percentage": 0.0,
                    "test_id": None,
                },
            }
        }
    }
