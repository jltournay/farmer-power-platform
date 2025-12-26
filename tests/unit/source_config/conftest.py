"""Fixtures for fp-source-config unit tests."""

from pathlib import Path
from typing import Any

import pytest

# Sample valid source configuration for testing
SAMPLE_VALID_CONFIG: dict[str, Any] = {
    "source_id": "test-source",
    "display_name": "Test Source",
    "description": "A test source configuration",
    "enabled": True,
    "ingestion": {
        "mode": "blob_trigger",
        "landing_container": "test-landing",
        "path_pattern": {
            "pattern": "results/{plantation_id}/{batch_id}.json",
            "extracted_fields": ["plantation_id", "batch_id"],
        },
    },
    "validation": {
        "schema_name": "data/test-schema.json",
        "required_fields": ["plantation_id", "batch_id"],
    },
    "transformation": {
        "agent": "test-extraction-agent",
        "model_config": {
            "model": "anthropic/claude-3-haiku",
            "temperature": 0.1,
            "max_tokens": 2000,
        },
    },
    "storage": {
        "raw_container": "test-raw",
        "index_collection": "test_index",
        "retention_days": 365,
    },
}


SAMPLE_SCHEDULED_CONFIG: dict[str, Any] = {
    "source_id": "scheduled-source",
    "display_name": "Scheduled Source",
    "description": "A scheduled pull source",
    "enabled": True,
    "ingestion": {
        "mode": "scheduled_pull",
        "api_endpoint": "https://api.example.com/data",
        "schedule": {"cron": "0 6 * * *"},
    },
    "transformation": {
        "agent": "scheduled-extraction-agent",
    },
    "storage": {
        "raw_container": "scheduled-raw",
        "index_collection": "scheduled_index",
    },
}


SAMPLE_INVALID_CONFIG: dict[str, Any] = {
    "source_id": "invalid-source",
    # Missing required fields: display_name, description, ingestion, transformation, storage
}


@pytest.fixture
def sample_valid_config() -> dict[str, Any]:
    """Provide a sample valid source configuration."""
    return SAMPLE_VALID_CONFIG.copy()


@pytest.fixture
def sample_scheduled_config() -> dict[str, Any]:
    """Provide a sample scheduled pull configuration."""
    return SAMPLE_SCHEDULED_CONFIG.copy()


@pytest.fixture
def sample_invalid_config() -> dict[str, Any]:
    """Provide a sample invalid configuration."""
    return SAMPLE_INVALID_CONFIG.copy()


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for config files."""
    config_dir = tmp_path / "source-configs"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def create_config_file(temp_config_dir: Path):
    """Factory fixture to create config files in the temp directory."""
    import yaml

    def _create(filename: str, config: dict[str, Any]) -> Path:
        file_path = temp_config_dir / filename
        with file_path.open("w") as f:
            yaml.dump(config, f)
        return file_path

    return _create
