"""Unit tests for prompt MongoDB client."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fp_prompt_config.client import PromoteResult, PromptClient, RollbackResult
from fp_prompt_config.models import (
    Prompt,
    PromptABTest,
    PromptContent,
    PromptMetadata,
    PromptStatus,
)
from fp_prompt_config.settings import Settings


def make_prompt(
    prompt_id: str = "test-prompt",
    agent_id: str = "test-agent",
    version: str = "1.0.0",
    status: PromptStatus = PromptStatus.DRAFT,
) -> Prompt:
    """Create a test Prompt object."""
    return Prompt(
        id=f"{prompt_id}:{version}",
        prompt_id=prompt_id,
        agent_id=agent_id,
        version=version,
        status=status,
        content=PromptContent(
            system_prompt="Test system prompt",
            template="Test template with {{variable}}",
        ),
        metadata=PromptMetadata(
            author="test-user",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
            changelog="Test version",
        ),
        ab_test=PromptABTest(),
    )


def make_prompt_doc(
    prompt_id: str = "test-prompt",
    agent_id: str = "test-agent",
    version: str = "1.0.0",
    status: str = "draft",
) -> dict:
    """Create a test prompt MongoDB document."""
    return {
        "_id": f"{prompt_id}:{version}",
        "id": f"{prompt_id}:{version}",
        "prompt_id": prompt_id,
        "agent_id": agent_id,
        "version": version,
        "status": status,
        "content": {
            "system_prompt": "Test system prompt",
            "template": "Test template with {{variable}}",
            "output_schema": None,
            "few_shot_examples": None,
        },
        "metadata": {
            "author": "test-user",
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-01T00:00:00+00:00",
            "changelog": "Test version",
            "git_commit": None,
        },
        "ab_test": {
            "enabled": False,
            "traffic_percentage": 0.0,
            "test_id": None,
        },
    }


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings."""
    settings = MagicMock(spec=Settings)
    settings.database_name = "ai_model"
    settings.prompts_collection = "prompts"
    settings.agent_configs_collection = "agent_configs"
    settings.get_mongodb_uri.return_value = "mongodb://localhost:27017"
    return settings


class TestPromptClientVersionIncrement:
    """Tests for version increment logic."""

    def test_increment_version_normal(self, mock_settings: Settings) -> None:
        """Test normal version increment."""
        client = PromptClient(mock_settings, "dev")
        assert client._increment_version("1.0.0") == "1.0.1"
        assert client._increment_version("2.3.4") == "2.3.5"
        assert client._increment_version("10.20.30") == "10.20.31"

    def test_increment_version_invalid(self, mock_settings: Settings) -> None:
        """Test version increment with invalid format."""
        client = PromptClient(mock_settings, "dev")
        # Invalid formats get .1 appended
        assert client._increment_version("1.0") == "1.0.1"
        assert client._increment_version("invalid") == "invalid.1"


class TestPromptClientSerialization:
    """Tests for serialization/deserialization."""

    def test_serialize_prompt(self, mock_settings: Settings) -> None:
        """Test prompt serialization to MongoDB document."""
        client = PromptClient(mock_settings, "dev")
        prompt = make_prompt()

        doc = client._serialize(prompt)

        assert doc["_id"] == "test-prompt:1.0.0"
        assert doc["prompt_id"] == "test-prompt"
        assert doc["agent_id"] == "test-agent"
        assert doc["version"] == "1.0.0"
        assert doc["status"] == "draft"

    def test_deserialize_prompt(self, mock_settings: Settings) -> None:
        """Test prompt deserialization from MongoDB document."""
        client = PromptClient(mock_settings, "dev")
        doc = make_prompt_doc()

        prompt = client._deserialize(doc)

        assert prompt.id == "test-prompt:1.0.0"
        assert prompt.prompt_id == "test-prompt"
        assert prompt.agent_id == "test-agent"
        assert prompt.version == "1.0.0"
        assert prompt.status == PromptStatus.DRAFT


class TestPromptClientAgentValidation:
    """Tests for agent reference validation."""

    @pytest.mark.asyncio
    async def test_validate_agent_reference_draft_skips(self, mock_settings: Settings) -> None:
        """Test that draft prompts skip agent validation."""
        client = PromptClient(mock_settings, "dev")
        # Mock the database connection
        client._db = MagicMock()
        client._db.__getitem__ = MagicMock(return_value=MagicMock())

        prompt = make_prompt(status=PromptStatus.DRAFT)

        result = await client.validate_agent_reference(prompt)

        assert result is None  # No error = valid

    @pytest.mark.asyncio
    async def test_validate_agent_reference_staged_requires_agent(self, mock_settings: Settings) -> None:
        """Test that staged prompts require valid agent."""
        client = PromptClient(mock_settings, "dev")

        # Mock the database and collection
        mock_collection = AsyncMock()
        mock_collection.find_one = AsyncMock(return_value=None)  # Agent not found

        client._db = MagicMock()
        client._db.__getitem__ = MagicMock(return_value=mock_collection)

        prompt = make_prompt(status=PromptStatus.STAGED)

        result = await client.validate_agent_reference(prompt)

        assert result is not None
        assert "does not exist" in result

    @pytest.mark.asyncio
    async def test_validate_agent_reference_staged_agent_exists(self, mock_settings: Settings) -> None:
        """Test that staged prompts pass when agent exists."""
        client = PromptClient(mock_settings, "dev")

        # Mock the database and collection
        mock_collection = AsyncMock()
        mock_collection.find_one = AsyncMock(return_value={"agent_id": "test-agent", "status": "active"})

        client._db = MagicMock()
        client._db.__getitem__ = MagicMock(return_value=mock_collection)

        prompt = make_prompt(status=PromptStatus.STAGED)

        result = await client.validate_agent_reference(prompt)

        assert result is None  # No error = valid


class TestPromptClientDataclasses:
    """Tests for result dataclasses."""

    def test_promote_result_success(self) -> None:
        """Test PromoteResult success case."""
        result = PromoteResult(
            success=True,
            promoted_version="2.0.0",
            archived_version="1.0.0",
        )

        assert result.success is True
        assert result.promoted_version == "2.0.0"
        assert result.archived_version == "1.0.0"
        assert result.error is None

    def test_promote_result_failure(self) -> None:
        """Test PromoteResult failure case."""
        result = PromoteResult(
            success=False,
            error="No staged prompt found",
        )

        assert result.success is False
        assert result.error == "No staged prompt found"

    def test_rollback_result_success(self) -> None:
        """Test RollbackResult success case."""
        result = RollbackResult(
            success=True,
            new_version="1.0.1",
            archived_version="2.0.0",
        )

        assert result.success is True
        assert result.new_version == "1.0.1"
        assert result.archived_version == "2.0.0"
        assert result.error is None

    def test_rollback_result_failure(self) -> None:
        """Test RollbackResult failure case."""
        result = RollbackResult(
            success=False,
            error="Version not found",
        )

        assert result.success is False
        assert result.error == "Version not found"
