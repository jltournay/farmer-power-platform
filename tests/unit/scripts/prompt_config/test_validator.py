"""Unit tests for prompt YAML validator."""

from pathlib import Path

from fp_prompt_config.models import PromptStatus
from fp_prompt_config.validator import validate_prompt_dict, validate_prompt_yaml


class TestValidatePromptYaml:
    """Tests for validate_prompt_yaml function."""

    def test_valid_prompt_passes(self, valid_prompt_yaml: Path) -> None:
        """Test that a valid prompt YAML file passes validation."""
        result = validate_prompt_yaml(valid_prompt_yaml)

        assert result.is_valid is True
        assert result.errors == []
        assert result.prompt is not None
        assert result.prompt.prompt_id == "disease-diagnosis"
        assert result.prompt.agent_id == "diagnose-quality-issue"
        assert result.prompt.version == "1.0.0"
        assert result.prompt.status == PromptStatus.DRAFT

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Test that non-existent file fails validation."""
        result = validate_prompt_yaml(tmp_path / "nonexistent.yaml")

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "File not found" in result.errors[0]

    def test_missing_required_fields(self, invalid_prompt_missing_fields_yaml: Path) -> None:
        """Test that missing required fields fail validation."""
        result = validate_prompt_yaml(invalid_prompt_missing_fields_yaml)

        assert result.is_valid is False
        assert any("agent_id" in e for e in result.errors)
        assert any("version" in e for e in result.errors)
        assert any("content" in e for e in result.errors)

    def test_invalid_version_format(self, invalid_prompt_bad_version_yaml: Path) -> None:
        """Test that invalid version format fails validation."""
        result = validate_prompt_yaml(invalid_prompt_bad_version_yaml)

        assert result.is_valid is False
        assert any("version format" in e.lower() for e in result.errors)

    def test_invalid_status_value(self, invalid_prompt_bad_status_yaml: Path) -> None:
        """Test that invalid status value fails validation."""
        result = validate_prompt_yaml(invalid_prompt_bad_status_yaml)

        assert result.is_valid is False
        assert any("status" in e.lower() for e in result.errors)

    def test_malformed_yaml(self, invalid_yaml: Path) -> None:
        """Test that malformed YAML fails validation."""
        result = validate_prompt_yaml(invalid_yaml)

        assert result.is_valid is False
        assert any("yaml" in e.lower() for e in result.errors)

    def test_generates_id_from_prompt_id_and_version(self, sample_prompt_yaml: Path) -> None:
        """Test that id is generated from prompt_id and version."""
        result = validate_prompt_yaml(sample_prompt_yaml)

        assert result.is_valid is True
        assert result.prompt is not None
        assert result.prompt.id == "test-prompt:1.0.0"

    def test_default_status_is_draft(self, tmp_path: Path) -> None:
        """Test that default status is draft when not specified."""
        yaml_content = """
prompt_id: test-prompt
agent_id: test-agent
version: "1.0.0"

content:
  system_prompt: Test system prompt
  template: Test template
"""
        file_path = tmp_path / "no-status.yaml"
        file_path.write_text(yaml_content)

        result = validate_prompt_yaml(file_path)

        assert result.is_valid is True
        assert result.prompt is not None
        assert result.prompt.status == PromptStatus.DRAFT


class TestValidatePromptDict:
    """Tests for validate_prompt_dict function."""

    def test_valid_dict_passes(self) -> None:
        """Test that a valid prompt dict passes validation."""
        data = {
            "prompt_id": "test-prompt",
            "agent_id": "test-agent",
            "version": "1.0.0",
            "content": {
                "system_prompt": "Test system prompt",
                "template": "Test template",
            },
        }

        result = validate_prompt_dict(data)

        assert result.is_valid is True
        assert result.prompt is not None
        assert result.prompt.prompt_id == "test-prompt"

    def test_missing_required_fields(self) -> None:
        """Test that missing required fields fail validation."""
        data = {"prompt_id": "test-prompt"}  # Missing agent_id, version, content

        result = validate_prompt_dict(data)

        assert result.is_valid is False
        assert any("agent_id" in e for e in result.errors)

    def test_invalid_version_format(self) -> None:
        """Test that invalid version format fails validation."""
        data = {
            "prompt_id": "test-prompt",
            "agent_id": "test-agent",
            "version": "1.0",  # Invalid: missing patch
            "content": {
                "system_prompt": "Test",
                "template": "Test",
            },
        }

        result = validate_prompt_dict(data)

        assert result.is_valid is False
        assert any("version" in e.lower() for e in result.errors)

    def test_missing_content_fields(self) -> None:
        """Test that missing content.system_prompt and template fail."""
        data = {
            "prompt_id": "test-prompt",
            "agent_id": "test-agent",
            "version": "1.0.0",
            "content": {},  # Missing system_prompt and template
        }

        result = validate_prompt_dict(data)

        assert result.is_valid is False
        assert any("system_prompt" in e for e in result.errors)
        assert any("template" in e for e in result.errors)

    def test_non_dict_input(self) -> None:
        """Test that non-dict input fails validation."""
        result = validate_prompt_dict("not a dict")  # type: ignore

        assert result.is_valid is False
        assert any("dictionary" in e.lower() for e in result.errors)

    def test_version_as_number_is_converted(self) -> None:
        """Test that numeric version is converted to string and validated."""
        data = {
            "prompt_id": "test-prompt",
            "agent_id": "test-agent",
            "version": 1.0,  # Numeric, will be converted to "1.0"
            "content": {
                "system_prompt": "Test",
                "template": "Test",
            },
        }

        result = validate_prompt_dict(data)

        # "1.0" is not valid semver (needs X.Y.Z)
        assert result.is_valid is False
        assert any("version" in e.lower() for e in result.errors)
