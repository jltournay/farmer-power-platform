"""Unit tests for Prompt domain models.

Tests cover:
- PromptStatus enum values
- PromptContent model validation
- PromptMetadata model validation
- PromptABTest model validation
- Prompt model validation (complete model)
- Prompt model serialization (model_dump)
- Prompt model deserialization (model_validate)
- Invalid field rejection tests
"""

from datetime import UTC, datetime

import pytest
from ai_model.domain.prompt import (
    Prompt,
    PromptABTest,
    PromptContent,
    PromptMetadata,
    PromptStatus,
)
from pydantic import ValidationError


class TestPromptStatus:
    """Tests for PromptStatus enum."""

    def test_status_has_draft_value(self) -> None:
        """Draft status exists and has correct value."""
        assert PromptStatus.DRAFT.value == "draft"

    def test_status_has_staged_value(self) -> None:
        """Staged status exists and has correct value."""
        assert PromptStatus.STAGED.value == "staged"

    def test_status_has_active_value(self) -> None:
        """Active status exists and has correct value."""
        assert PromptStatus.ACTIVE.value == "active"

    def test_status_has_archived_value(self) -> None:
        """Archived status exists and has correct value."""
        assert PromptStatus.ARCHIVED.value == "archived"

    def test_status_is_string_enum(self) -> None:
        """Status values are strings for MongoDB compatibility."""
        for status in PromptStatus:
            assert isinstance(status.value, str)


class TestPromptContent:
    """Tests for PromptContent model."""

    def test_content_with_required_fields(self) -> None:
        """Content can be created with required fields only."""
        content = PromptContent(
            system_prompt="You are a helpful assistant",
            template="Process: {{input}}",
        )
        assert content.system_prompt == "You are a helpful assistant"
        assert content.template == "Process: {{input}}"
        assert content.output_schema is None
        assert content.few_shot_examples is None

    def test_content_with_all_fields(self) -> None:
        """Content can be created with all fields."""
        schema = {"type": "object", "properties": {"result": {"type": "string"}}}
        examples = [{"input": "test", "output": "response"}]

        content = PromptContent(
            system_prompt="System",
            template="Template",
            output_schema=schema,
            few_shot_examples=examples,
        )

        assert content.output_schema == schema
        assert content.few_shot_examples == examples

    def test_content_requires_system_prompt(self) -> None:
        """Content requires system_prompt field."""
        with pytest.raises(ValidationError) as exc_info:
            PromptContent(template="Template")  # type: ignore[call-arg]
        assert "system_prompt" in str(exc_info.value)

    def test_content_requires_template(self) -> None:
        """Content requires template field."""
        with pytest.raises(ValidationError) as exc_info:
            PromptContent(system_prompt="System")  # type: ignore[call-arg]
        assert "template" in str(exc_info.value)


class TestPromptMetadata:
    """Tests for PromptMetadata model."""

    def test_metadata_with_required_fields(self) -> None:
        """Metadata can be created with required fields only."""
        metadata = PromptMetadata(author="admin")
        assert metadata.author == "admin"
        assert metadata.changelog is None
        assert metadata.git_commit is None
        # Timestamps should be auto-generated
        assert metadata.created_at is not None
        assert metadata.updated_at is not None

    def test_metadata_with_all_fields(self) -> None:
        """Metadata can be created with all fields."""
        now = datetime.now(UTC)
        metadata = PromptMetadata(
            author="developer",
            created_at=now,
            updated_at=now,
            changelog="Fixed bug in template",
            git_commit="abc123def",
        )

        assert metadata.author == "developer"
        assert metadata.created_at == now
        assert metadata.updated_at == now
        assert metadata.changelog == "Fixed bug in template"
        assert metadata.git_commit == "abc123def"

    def test_metadata_requires_author(self) -> None:
        """Metadata requires author field."""
        with pytest.raises(ValidationError) as exc_info:
            PromptMetadata()  # type: ignore[call-arg]
        assert "author" in str(exc_info.value)

    def test_metadata_timestamps_are_utc(self) -> None:
        """Timestamps should be in UTC."""
        metadata = PromptMetadata(author="test")
        assert metadata.created_at.tzinfo is not None
        assert metadata.updated_at.tzinfo is not None


class TestPromptABTest:
    """Tests for PromptABTest model."""

    def test_ab_test_default_values(self) -> None:
        """A/B test has sensible defaults."""
        ab_test = PromptABTest()
        assert ab_test.enabled is False
        assert ab_test.traffic_percentage == 0.0
        assert ab_test.test_id is None

    def test_ab_test_with_all_fields(self) -> None:
        """A/B test can be configured with all fields."""
        ab_test = PromptABTest(
            enabled=True,
            traffic_percentage=10.0,
            test_id="experiment-001",
        )

        assert ab_test.enabled is True
        assert ab_test.traffic_percentage == 10.0
        assert ab_test.test_id == "experiment-001"

    def test_ab_test_traffic_percentage_min_bound(self) -> None:
        """Traffic percentage cannot be negative."""
        with pytest.raises(ValidationError) as exc_info:
            PromptABTest(traffic_percentage=-1.0)
        assert "traffic_percentage" in str(exc_info.value)

    def test_ab_test_traffic_percentage_max_bound(self) -> None:
        """Traffic percentage cannot exceed 100."""
        with pytest.raises(ValidationError) as exc_info:
            PromptABTest(traffic_percentage=101.0)
        assert "traffic_percentage" in str(exc_info.value)

    def test_ab_test_traffic_percentage_at_boundaries(self) -> None:
        """Traffic percentage accepts boundary values."""
        ab_test_min = PromptABTest(traffic_percentage=0.0)
        ab_test_max = PromptABTest(traffic_percentage=100.0)
        assert ab_test_min.traffic_percentage == 0.0
        assert ab_test_max.traffic_percentage == 100.0


class TestPrompt:
    """Tests for Prompt model."""

    @pytest.fixture
    def valid_prompt_data(self) -> dict:
        """Provide valid prompt data for tests."""
        return {
            "id": "disease-diagnosis:1.0.0",
            "prompt_id": "disease-diagnosis",
            "agent_id": "diagnose-quality-issue",
            "version": "1.0.0",
            "status": PromptStatus.ACTIVE,
            "content": {
                "system_prompt": "You are an expert diagnostician",
                "template": "Analyze: {{data}}",
            },
            "metadata": {
                "author": "admin",
            },
        }

    def test_prompt_with_required_fields(self, valid_prompt_data: dict) -> None:
        """Prompt can be created with required fields."""
        prompt = Prompt(**valid_prompt_data)

        assert prompt.id == "disease-diagnosis:1.0.0"
        assert prompt.prompt_id == "disease-diagnosis"
        assert prompt.agent_id == "diagnose-quality-issue"
        assert prompt.version == "1.0.0"
        assert prompt.status == PromptStatus.ACTIVE

    def test_prompt_has_default_ab_test(self, valid_prompt_data: dict) -> None:
        """Prompt has default A/B test configuration."""
        prompt = Prompt(**valid_prompt_data)

        assert prompt.ab_test is not None
        assert prompt.ab_test.enabled is False
        assert prompt.ab_test.traffic_percentage == 0.0

    def test_prompt_serialization_model_dump(self, valid_prompt_data: dict) -> None:
        """Prompt can be serialized with model_dump()."""
        prompt = Prompt(**valid_prompt_data)
        data = prompt.model_dump()

        assert data["id"] == "disease-diagnosis:1.0.0"
        assert data["prompt_id"] == "disease-diagnosis"
        assert data["status"] == "active"  # Enum serialized to string
        assert isinstance(data["content"], dict)
        assert isinstance(data["metadata"], dict)

    def test_prompt_deserialization_model_validate(self) -> None:
        """Prompt can be deserialized with model_validate()."""
        raw_data = {
            "id": "weather-impact:2.0.0",
            "prompt_id": "weather-impact",
            "agent_id": "analyze-weather",
            "version": "2.0.0",
            "status": "staged",  # String, not enum
            "content": {
                "system_prompt": "System",
                "template": "Template",
            },
            "metadata": {
                "author": "developer",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
        }

        prompt = Prompt.model_validate(raw_data)

        assert prompt.prompt_id == "weather-impact"
        assert prompt.status == PromptStatus.STAGED

    def test_prompt_requires_id(self) -> None:
        """Prompt requires id field."""
        with pytest.raises(ValidationError) as exc_info:
            Prompt(
                prompt_id="test",
                agent_id="agent",
                version="1.0.0",
                content={"system_prompt": "S", "template": "T"},
                metadata={"author": "a"},
            )  # type: ignore[call-arg]
        assert "id" in str(exc_info.value)

    def test_prompt_requires_prompt_id(self) -> None:
        """Prompt requires prompt_id field."""
        with pytest.raises(ValidationError) as exc_info:
            Prompt(
                id="test:1.0.0",
                agent_id="agent",
                version="1.0.0",
                content={"system_prompt": "S", "template": "T"},
                metadata={"author": "a"},
            )  # type: ignore[call-arg]
        assert "prompt_id" in str(exc_info.value)

    def test_prompt_requires_agent_id(self) -> None:
        """Prompt requires agent_id field."""
        with pytest.raises(ValidationError) as exc_info:
            Prompt(
                id="test:1.0.0",
                prompt_id="test",
                version="1.0.0",
                content={"system_prompt": "S", "template": "T"},
                metadata={"author": "a"},
            )  # type: ignore[call-arg]
        assert "agent_id" in str(exc_info.value)

    def test_prompt_requires_version(self) -> None:
        """Prompt requires version field."""
        with pytest.raises(ValidationError) as exc_info:
            Prompt(
                id="test:1.0.0",
                prompt_id="test",
                agent_id="agent",
                content={"system_prompt": "S", "template": "T"},
                metadata={"author": "a"},
            )  # type: ignore[call-arg]
        assert "version" in str(exc_info.value)

    def test_prompt_status_defaults_to_draft(self) -> None:
        """Prompt status defaults to draft if not specified."""
        prompt = Prompt(
            id="test:1.0.0",
            prompt_id="test",
            agent_id="agent",
            version="1.0.0",
            content=PromptContent(
                system_prompt="System",
                template="Template",
            ),
            metadata=PromptMetadata(author="admin"),
        )

        assert prompt.status == PromptStatus.DRAFT

    def test_prompt_rejects_invalid_status(self) -> None:
        """Prompt rejects invalid status value."""
        with pytest.raises(ValidationError) as exc_info:
            Prompt(
                id="test:1.0.0",
                prompt_id="test",
                agent_id="agent",
                version="1.0.0",
                status="invalid_status",  # type: ignore[arg-type]
                content={"system_prompt": "S", "template": "T"},
                metadata={"author": "a"},
            )
        assert "status" in str(exc_info.value)
