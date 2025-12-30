"""Test configuration for Collection Model unit tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fp_common.models.source_config import (
    IterationConfig,
    SourceConfig,
)


@pytest.fixture
def mock_motor_client() -> MagicMock:
    """Mock Motor MongoDB client (for infrastructure tests)."""
    client = MagicMock()
    client.admin.command = AsyncMock(return_value={"ok": 1})
    return client


@pytest.fixture
def mock_database() -> MagicMock:
    """Mock MongoDB database."""
    db = MagicMock()
    db.create_index = AsyncMock()
    return db


# Note: mock_mongodb_client is inherited from tests/conftest.py
# and provides MockMongoClient with proper async collection methods


# ==============================================================================
# SourceConfig Factory Functions and Fixtures
# ==============================================================================


def create_source_config(
    source_id: str = "test-source",
    display_name: str | None = None,
    enabled: bool = True,
    mode: str = "blob_trigger",
    landing_container: str = "test-landing",
    schedule: str | None = None,
    provider: str | None = None,
    iteration: dict | None = None,
    path_pattern: dict | None = None,
    processor_type: str = "json-extraction",
    file_format: str = "json",
    extract_fields: list[str] | None = None,
    link_field: str = "farmer_id",
    raw_container: str = "test-raw",
    index_collection: str = "test_documents",
    file_container: str | None = None,
    ai_agent_id: str | None = None,
) -> SourceConfig:
    """Factory function to create a valid SourceConfig for testing.

    Args:
        source_id: Source identifier.
        display_name: Display name (defaults to source_id).
        enabled: Whether source is enabled.
        mode: Ingestion mode ('blob_trigger' or 'scheduled_pull').
        landing_container: Container for blob trigger mode.
        schedule: Cron schedule for scheduled_pull mode.
        provider: Provider name for scheduled_pull mode.
        iteration: Iteration config dict for scheduled_pull mode.
        path_pattern: Path pattern config dict.
        processor_type: Processor type (e.g., 'json-extraction').
        file_format: File format ('json' or 'zip').
        extract_fields: Fields to extract.
        link_field: Linkage field.
        raw_container: Raw storage container.
        index_collection: MongoDB collection name.
        file_container: File container (for ZIP extraction).
        ai_agent_id: AI agent ID for transformation.

    Returns:
        A valid SourceConfig Pydantic model.
    """
    # Build ingestion config
    ingestion_data = {
        "mode": mode,
        "file_format": file_format,
        "processor_type": processor_type,
    }

    if mode == "blob_trigger":
        ingestion_data["landing_container"] = landing_container
        if path_pattern:
            ingestion_data["path_pattern"] = path_pattern
    elif mode == "scheduled_pull":
        ingestion_data["schedule"] = schedule
        ingestion_data["provider"] = provider
        if iteration:
            ingestion_data["iteration"] = iteration

    # Build storage config
    storage_data = {
        "raw_container": raw_container,
        "index_collection": index_collection,
    }
    if file_container:
        storage_data["file_container"] = file_container

    # Build transformation config
    transformation_data = {
        "extract_fields": extract_fields or ["document_id", "data"],
        "link_field": link_field,
    }
    if ai_agent_id:
        transformation_data["ai_agent_id"] = ai_agent_id

    return SourceConfig.model_validate(
        {
            "source_id": source_id,
            "display_name": display_name or f"{source_id} Test Source",
            "description": f"Test source configuration for {source_id}",
            "enabled": enabled,
            "ingestion": ingestion_data,
            "transformation": transformation_data,
            "storage": storage_data,
        }
    )


def create_iteration_config(
    foreach: str = "regions",
    source_mcp: str = "plantation-mcp",
    source_tool: str = "get_all_regions",
    concurrency: int = 5,
    tool_arguments: dict | None = None,
    result_path: str | None = None,
) -> IterationConfig:
    """Factory function to create an IterationConfig for testing."""
    data = {
        "foreach": foreach,
        "source_mcp": source_mcp,
        "source_tool": source_tool,
        "concurrency": concurrency,
    }
    # Note: tool_arguments and result_path are not in the model, they're accessed via getattr
    return IterationConfig.model_validate(data)


@pytest.fixture
def sample_blob_trigger_config() -> SourceConfig:
    """Create a sample blob_trigger mode SourceConfig."""
    return create_source_config(
        source_id="qc-analyzer",
        mode="blob_trigger",
        landing_container="qc-analyzer-landing",
        path_pattern={
            "pattern": "{year}/{month}/{day}/{filename}.json",
            "extract_fields": ["year", "month", "day", "filename"],
        },
    )


@pytest.fixture
def sample_scheduled_pull_config() -> SourceConfig:
    """Create a sample scheduled_pull mode SourceConfig."""
    return create_source_config(
        source_id="weather-api",
        mode="scheduled_pull",
        schedule="0 */6 * * *",
        provider="open-meteo",
        iteration={
            "foreach": "regions",
            "source_mcp": "plantation-mcp",
            "source_tool": "get_all_regions",
            "concurrency": 3,
        },
    )


@pytest.fixture
def sample_iteration_config() -> IterationConfig:
    """Create a sample IterationConfig."""
    return create_iteration_config()
