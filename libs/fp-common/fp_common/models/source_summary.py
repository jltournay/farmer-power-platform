"""Source configuration summary model for MCP servers.

This model provides a typed response for source configuration listings,
replacing the dict[str, Any] anti-pattern with proper Pydantic validation.
"""

from pydantic import BaseModel, Field


class SourceSummary(BaseModel):
    """Summary of a data source configuration.

    Returned by list_sources() MCP tool. Contains the essential
    information about a configured data source without the full
    configuration details.

    Attributes:
        source_id: Unique identifier for this source.
        display_name: Human-readable name for the source.
        description: Description of what this source collects.
        enabled: Whether the source is currently enabled.
        ingestion_mode: How data is ingested (blob_trigger, scheduled_pull).
        ingestion_schedule: Cron schedule for scheduled_pull mode.
    """

    source_id: str = Field(description="Unique identifier for this source")
    display_name: str = Field(description="Human-readable name for the source")
    description: str = Field(default="", description="Description of what this source collects")
    enabled: bool = Field(default=True, description="Whether the source is currently enabled")
    ingestion_mode: str = Field(
        default="unknown",
        description="How data is ingested (blob_trigger, scheduled_pull)",
    )
    ingestion_schedule: str | None = Field(
        default=None,
        description="Cron schedule for scheduled_pull mode (e.g., '0 6 * * *')",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "source_id": "qc-analyzer-result",
                "display_name": "QC Analyzer Results",
                "description": "Quality control results from QC Analyzer CV system",
                "enabled": True,
                "ingestion_mode": "blob_trigger",
                "ingestion_schedule": None,
            },
        },
    }
