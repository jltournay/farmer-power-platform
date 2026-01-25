"""Source Config Summary and Detail models for BFF responses.

Story 9.11b: Source Config gRPC Client + REST API in BFF

These models represent source configurations for the Admin UI.
Used by the BFF to return typed responses instead of dicts.

Field mapping from Proto:
- SourceConfigSummary: Summary fields for list views
- SourceConfigDetail: Full config including JSON blob for detail views

Reference:
- Proto definitions: proto/collection/v1/collection.proto
- Story: _bmad-output/sprint-artifacts/9-11b-source-config-bff-client-rest.md
"""

from datetime import datetime

from pydantic import BaseModel, Field


class SourceConfigSummary(BaseModel):
    """Summary view of a source configuration for list endpoints.

    Contains essential fields for displaying source configs in a table/list view.
    Does NOT include the full config_json blob.

    Attributes:
        source_id: Unique identifier for the source configuration.
        display_name: Human-readable name for UI display.
        description: Brief description of what this source ingests.
        enabled: Whether this source is currently active.
        ingestion_mode: How data is ingested - "blob_trigger" or "scheduled_pull".
        ai_agent_id: Optional ID of the AI agent used for transformation.
        updated_at: When this config was last modified.
    """

    source_id: str = Field(description="Unique source identifier")
    display_name: str = Field(description="Human-readable display name")
    description: str = Field(description="Source description")
    enabled: bool = Field(description="Whether source is active")
    ingestion_mode: str = Field(description="Ingestion mode: blob_trigger or scheduled_pull")
    ai_agent_id: str | None = Field(default=None, description="AI agent ID for transformation")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")

    model_config = {"frozen": True}


class SourceConfigDetail(SourceConfigSummary):
    """Full detail view of a source configuration.

    Extends SourceConfigSummary with the complete configuration JSON blob.
    Used for detail/edit views in the Admin UI.

    Attributes:
        config_json: Full configuration serialized as JSON string.
        created_at: When this config was first created.
    """

    config_json: str = Field(description="Full configuration as JSON string")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")

    model_config = {"frozen": True}
