"""Source Config admin API schemas (Story 9.11b).

Provides request/response schemas for source configuration viewer:
- SourceConfigSummaryResponse: List view with basic info
- SourceConfigDetailResponse: Full detail with config_json
- SourceConfigListResponse: Paginated list response

These are API-layer schemas that mirror the fp_common domain models
but with ISO-formatted date strings for JSON serialization.
"""

from typing import TYPE_CHECKING

from bff.api.schemas.responses import PaginationMeta
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from fp_common.models import SourceConfigDetail, SourceConfigSummary


class SourceConfigSummaryResponse(BaseModel):
    """Source configuration summary for admin list views.

    Contains essential fields for displaying source configs in a table.
    Does NOT include the full config_json blob.
    """

    source_id: str = Field(description="Unique source identifier (e.g., 'qc-analyzer-result')")
    display_name: str = Field(description="Human-readable display name")
    description: str = Field(description="Brief description of the source")
    enabled: bool = Field(description="Whether this source is currently active")
    ingestion_mode: str = Field(description="Ingestion mode: 'blob_trigger' or 'scheduled_pull'")
    ai_agent_id: str | None = Field(default=None, description="AI agent ID for transformation")
    updated_at: str | None = Field(default=None, description="Last update timestamp (ISO format)")

    @classmethod
    def from_domain(cls, model: "SourceConfigSummary") -> "SourceConfigSummaryResponse":
        """Create API response from domain model.

        Args:
            model: SourceConfigSummary domain model from fp_common.

        Returns:
            SourceConfigSummaryResponse for API response.
        """
        return cls(
            source_id=model.source_id,
            display_name=model.display_name,
            description=model.description,
            enabled=model.enabled,
            ingestion_mode=model.ingestion_mode,
            ai_agent_id=model.ai_agent_id,
            updated_at=model.updated_at.isoformat() if model.updated_at else None,
        )


class SourceConfigDetailResponse(SourceConfigSummaryResponse):
    """Full source configuration detail for admin detail views.

    Extends summary with the complete configuration JSON blob.
    """

    config_json: str = Field(description="Full configuration serialized as JSON string")
    created_at: str | None = Field(default=None, description="Creation timestamp (ISO format)")

    @classmethod
    def from_domain(cls, model: "SourceConfigDetail") -> "SourceConfigDetailResponse":
        """Create API response from domain model.

        Args:
            model: SourceConfigDetail domain model from fp_common.

        Returns:
            SourceConfigDetailResponse for API response.
        """
        return cls(
            source_id=model.source_id,
            display_name=model.display_name,
            description=model.description,
            enabled=model.enabled,
            ingestion_mode=model.ingestion_mode,
            ai_agent_id=model.ai_agent_id,
            updated_at=model.updated_at.isoformat() if model.updated_at else None,
            config_json=model.config_json,
            created_at=model.created_at.isoformat() if model.created_at else None,
        )


class SourceConfigListResponse(BaseModel):
    """Paginated source configuration list response."""

    data: list[SourceConfigSummaryResponse] = Field(
        description="List of source configuration summaries",
    )
    pagination: PaginationMeta = Field(description="Pagination metadata")
