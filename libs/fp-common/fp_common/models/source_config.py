"""Source configuration Pydantic models.

Defines the schema for data source configurations used by the Collection Model
service for ingesting data from various sources (blob storage, APIs, etc.).
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PathPatternConfig(BaseModel):
    """Path pattern extraction configuration.

    Used to extract metadata from blob paths using pattern matching.
    """

    pattern: str = Field(..., description="Path pattern with {field} placeholders")
    extract_fields: list[str] = Field(..., description="Fields to extract from the path")


class ProcessedFileConfig(BaseModel):
    """Configuration for handling files after processing."""

    action: Literal["archive", "move", "delete"] = Field(..., description="Action to take after processing")
    archive_container: str | None = Field(None, description="Container to archive files to")
    archive_ttl_days: int | None = Field(None, description="Days to retain archived files")
    processed_folder: str | None = Field(None, description="Folder to move processed files to")


class ZipConfig(BaseModel):
    """ZIP file handling configuration."""

    manifest_file: str = Field(..., description="Name of the manifest file in ZIP")
    images_folder: str = Field(..., description="Folder containing images in ZIP")
    extract_images: bool = Field(True, description="Whether to extract images")
    image_storage_container: str = Field(..., description="Container to store extracted images")


class RequestConfig(BaseModel):
    """HTTP request configuration for scheduled pulls."""

    base_url: str = Field(..., description="Base URL for the API")
    auth_type: Literal["none", "api_key", "oauth2"] = Field(..., description="Authentication type")
    auth_secret_key: str | None = Field(None, description="DAPR secret key for authentication")
    parameters: dict[str, str] = Field(default_factory=dict, description="Query parameters")
    timeout_seconds: int = Field(30, description="Request timeout in seconds")


class IterationConfig(BaseModel):
    """Iteration configuration for scheduled pulls.

    Defines how to iterate over a list of items (e.g., regions, markets)
    when pulling data from external APIs.
    """

    foreach: str = Field(..., description="Entity type to iterate over")
    source_mcp: str = Field(..., description="MCP server to get list from")
    source_tool: str = Field(..., description="MCP tool to call for the list")
    concurrency: int = Field(5, description="Maximum concurrent requests")


class RetryConfig(BaseModel):
    """Retry configuration for failed operations."""

    max_attempts: int = Field(3, description="Maximum retry attempts")
    backoff: Literal["exponential", "linear"] = Field("exponential", description="Backoff strategy")


class IngestionConfig(BaseModel):
    """Ingestion configuration block.

    Supports two modes:
    - blob_trigger: React to files uploaded to blob storage
    - scheduled_pull: Pull data from external APIs on a schedule
    """

    mode: Literal["blob_trigger", "scheduled_pull"] = Field(..., description="Ingestion mode")

    # blob_trigger fields
    landing_container: str | None = Field(None, description="Blob container to watch for files")
    path_pattern: PathPatternConfig | None = Field(None, description="Path pattern for metadata extraction")
    file_pattern: str | None = Field(None, description="Glob pattern for file matching")
    file_format: Literal["json", "zip"] | None = Field(None, description="Expected file format")
    trigger_mechanism: Literal["event_grid"] | None = Field(None, description="Event trigger mechanism")
    processed_file_config: ProcessedFileConfig | None = Field(None, description="Post-processing configuration")
    zip_config: ZipConfig | None = Field(None, description="ZIP handling configuration")

    # Processor selection (Story 2.4)
    processor_type: str | None = Field(
        None,
        description="ContentProcessor type for ProcessorRegistry lookup (e.g., 'json-extraction')",
    )

    # scheduled_pull fields
    provider: str | None = Field(None, description="External data provider name")
    schedule: str | None = Field(None, description="Cron schedule expression")
    request: RequestConfig | None = Field(None, description="HTTP request configuration")
    iteration: IterationConfig | None = Field(None, description="Iteration configuration")
    retry: RetryConfig | None = Field(None, description="Retry configuration")


class ValidationConfig(BaseModel):
    """Validation configuration block.

    The schema_version field is optional:
    - If specified, the ingestion pipeline uses that exact version
    - If None (default), the pipeline uses the latest deployed version
    """

    schema_name: str = Field(..., description="JSON schema file name for validation")
    schema_version: int | None = Field(
        None,
        description="Schema version to use (None = latest)",
    )
    strict: bool = Field(True, description="Whether to fail on validation errors")


class SchemaDocument(BaseModel):
    """JSON Schema document stored in MongoDB.

    Schemas are stored separately from source configs to allow:
    - Reuse across multiple source configs
    - Independent versioning
    - Runtime lookup by the ingestion pipeline
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., description="Schema name/path (e.g., 'data/qc-bag-result.json')")
    content: dict[str, Any] = Field(..., description="The actual JSON schema content")
    version: int = Field(1, description="Schema version number")
    deployed_at: datetime = Field(..., description="Deployment timestamp")
    deployed_by: str = Field(..., description="User who deployed the schema")
    git_sha: str | None = Field(None, description="Git commit SHA at deployment time")


class TransformationConfig(BaseModel):
    """Transformation configuration block.

    Defines how to extract and map fields from ingested data.
    """

    ai_agent_id: str | None = Field(
        None,
        description="AI Model agent ID for LLM extraction (preferred over 'agent')",
    )
    agent: str | None = Field(
        None,
        description="AI agent for data extraction (deprecated, use ai_agent_id)",
    )
    extract_fields: list[str] = Field(..., description="Fields to extract from data")
    link_field: str = Field(..., description="Field to use for linking to other data")
    field_mappings: dict[str, str] = Field(default_factory=dict, description="Field name mappings")

    def get_ai_agent_id(self) -> str | None:
        """Get the AI agent ID, preferring ai_agent_id over deprecated agent field."""
        return self.ai_agent_id or self.agent


class StorageConfig(BaseModel):
    """Storage configuration block."""

    raw_container: str = Field(..., description="Container for raw data storage")
    index_collection: str = Field(..., description="MongoDB collection for index")
    ttl_days: int | None = Field(None, description="Days to retain data")


class EventConfig(BaseModel):
    """Single event configuration for success or failure events."""

    topic: str = Field(..., description="DAPR Pub/Sub topic (e.g., 'collection.quality_result.received')")
    payload_fields: list[str] = Field(
        default_factory=list,
        description="Fields to include in event payload",
    )


class EventsConfig(BaseModel):
    """Events configuration for domain event emission.

    Enables config-driven event emission - processors read topic and
    payload fields from config rather than hardcoding them.
    """

    on_success: EventConfig | None = Field(
        None,
        description="Event to emit when processing succeeds",
    )
    on_failure: EventConfig | None = Field(
        None,
        description="Event to emit when processing fails",
    )


class SourceConfig(BaseModel):
    """Complete source configuration.

    Defines how data from a specific source is ingested, validated,
    transformed, and stored by the Collection Model service.
    """

    model_config = ConfigDict(populate_by_name=True)

    source_id: str = Field(..., description="Unique identifier for this source")
    display_name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Source description")
    enabled: bool = Field(True, description="Whether source is active")

    ingestion: IngestionConfig = Field(..., description="Ingestion configuration")
    validation: ValidationConfig | None = Field(None, description="Validation configuration")
    transformation: TransformationConfig = Field(..., description="Transformation configuration")
    storage: StorageConfig = Field(..., description="Storage configuration")
    events: EventsConfig | None = Field(None, description="Domain event emission configuration")


def generate_json_schema(output_path: str | None = None) -> dict:
    """Generate JSON Schema from SourceConfig Pydantic model.

    This utility generates a JSON Schema file that can be used for IDE
    autocomplete and validation of source configuration YAML files.

    Args:
        output_path: If provided, write schema to this file path.

    Returns:
        The generated JSON Schema as a dict.
    """
    import json
    from pathlib import Path

    schema = SourceConfig.model_json_schema()
    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    schema["$id"] = "https://farmerpower.io/schemas/source-config.schema.json"
    schema["title"] = "Farmer Power Source Configuration"

    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open("w") as f:
            json.dump(schema, f, indent=2)

    return schema


if __name__ == "__main__":
    # CLI usage: python -m fp_common.models.source_config
    generate_json_schema("config/schemas/source-config.schema.json")
    print("Generated config/schemas/source-config.schema.json")
