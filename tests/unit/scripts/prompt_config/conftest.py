"""Shared fixtures for fp-prompt-config CLI tests."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the prompt_config fixtures directory."""
    return Path(__file__).parents[3] / "fixtures" / "prompt_config"


@pytest.fixture
def valid_prompt_yaml(fixtures_dir: Path) -> Path:
    """Return the path to the valid prompt YAML fixture."""
    return fixtures_dir / "valid-prompt.yaml"


@pytest.fixture
def invalid_prompt_missing_fields_yaml(fixtures_dir: Path) -> Path:
    """Return the path to the invalid prompt (missing fields) YAML fixture."""
    return fixtures_dir / "invalid-prompt-missing-fields.yaml"


@pytest.fixture
def invalid_prompt_bad_version_yaml(fixtures_dir: Path) -> Path:
    """Return the path to the invalid prompt (bad version) YAML fixture."""
    return fixtures_dir / "invalid-prompt-bad-version.yaml"


@pytest.fixture
def invalid_prompt_bad_status_yaml(fixtures_dir: Path) -> Path:
    """Return the path to the invalid prompt (bad status) YAML fixture."""
    return fixtures_dir / "invalid-prompt-bad-status.yaml"


@pytest.fixture
def sample_prompt_yaml(tmp_path: Path) -> Path:
    """Create a valid sample prompt YAML file."""
    yaml_content = """
prompt_id: test-prompt
agent_id: test-agent
version: "1.0.0"
status: draft

content:
  system_prompt: Test system prompt
  template: Test template with {{variable}}

metadata:
  author: test-user
  changelog: Test version
"""
    file_path = tmp_path / "test-prompt.yaml"
    file_path.write_text(yaml_content)
    return file_path


@pytest.fixture
def sample_staged_prompt_yaml(tmp_path: Path) -> Path:
    """Create a staged sample prompt YAML file."""
    yaml_content = """
prompt_id: test-prompt
agent_id: test-agent
version: "2.0.0"
status: staged

content:
  system_prompt: Test system prompt v2
  template: Test template v2 with {{variable}}

metadata:
  author: test-user
  changelog: Second version for staging
"""
    file_path = tmp_path / "test-prompt-staged.yaml"
    file_path.write_text(yaml_content)
    return file_path


@pytest.fixture
def invalid_yaml(tmp_path: Path) -> Path:
    """Create an invalid YAML file (malformed syntax)."""
    yaml_content = """
prompt_id: test-prompt
  bad_indent: this is not valid yaml
agent_id: test-agent
"""
    file_path = tmp_path / "invalid.yaml"
    file_path.write_text(yaml_content)
    return file_path


@pytest.fixture
def mock_prompt_client():
    """Mock PromptClient for CLI tests."""
    client = AsyncMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.create = AsyncMock()
    client.get_active = AsyncMock(return_value=None)
    client.get_latest_staged = AsyncMock(return_value=None)
    client.get_by_version = AsyncMock(return_value=None)
    client.list_prompts = AsyncMock(return_value=[])
    client.list_versions = AsyncMock(return_value=[])
    client.validate_agent_reference = AsyncMock(return_value=None)
    client.promote = AsyncMock()
    client.rollback = AsyncMock()
    return client


@pytest.fixture
def mock_settings():
    """Mock Settings for CLI tests."""
    settings = MagicMock()
    settings.database_name = "ai_model"
    settings.prompts_collection = "prompts"
    settings.agent_configs_collection = "agent_configs"
    settings.get_mongodb_uri.return_value = "mongodb://localhost:27017"
    return settings
