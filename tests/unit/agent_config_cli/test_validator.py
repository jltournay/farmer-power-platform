"""Unit tests for agent config validator."""

from pathlib import Path

from fp_agent_config.validator import (
    validate_agent_config_dict,
    validate_agent_config_yaml,
)


class TestValidateAgentConfigYaml:
    """Tests for validate_agent_config_yaml function."""

    def test_validate_extractor_valid(self, fixtures_dir: Path):
        """Test validation of valid extractor config."""
        file_path = fixtures_dir / "extractor_valid.yaml"
        result = validate_agent_config_yaml(file_path)

        assert result.is_valid is True
        assert result.errors == []
        assert result.config is not None
        assert result.config.agent_id == "qc-event-extractor"
        assert result.config.type == "extractor"
        assert result.config.version == "1.0.0"

    def test_validate_explorer_valid(self, fixtures_dir: Path):
        """Test validation of valid explorer config."""
        file_path = fixtures_dir / "explorer_valid.yaml"
        result = validate_agent_config_yaml(file_path)

        assert result.is_valid is True
        assert result.errors == []
        assert result.config is not None
        assert result.config.agent_id == "disease-diagnosis"
        assert result.config.type == "explorer"

    def test_validate_generator_valid(self, fixtures_dir: Path):
        """Test validation of valid generator config."""
        file_path = fixtures_dir / "generator_valid.yaml"
        result = validate_agent_config_yaml(file_path)

        assert result.is_valid is True
        assert result.errors == []
        assert result.config is not None
        assert result.config.agent_id == "weekly-action-plan"
        assert result.config.type == "generator"

    def test_validate_conversational_valid(self, fixtures_dir: Path):
        """Test validation of valid conversational config."""
        file_path = fixtures_dir / "conversational_valid.yaml"
        result = validate_agent_config_yaml(file_path)

        assert result.is_valid is True
        assert result.errors == []
        assert result.config is not None
        assert result.config.agent_id == "dialogue-responder"
        assert result.config.type == "conversational"

    def test_validate_tiered_vision_valid(self, fixtures_dir: Path):
        """Test validation of valid tiered-vision config."""
        file_path = fixtures_dir / "tiered_vision_valid.yaml"
        result = validate_agent_config_yaml(file_path)

        assert result.is_valid is True
        assert result.errors == []
        assert result.config is not None
        assert result.config.agent_id == "leaf-quality-analyzer"
        assert result.config.type == "tiered-vision"

    def test_validate_missing_type_invalid(self, fixtures_dir: Path):
        """Test validation fails for missing type field."""
        file_path = fixtures_dir / "invalid_missing_type.yaml"
        result = validate_agent_config_yaml(file_path)

        assert result.is_valid is False
        assert any("type" in error for error in result.errors)
        assert result.config is None

    def test_validate_invalid_version(self, fixtures_dir: Path):
        """Test validation fails for invalid version format."""
        file_path = fixtures_dir / "invalid_version.yaml"
        result = validate_agent_config_yaml(file_path)

        assert result.is_valid is False
        assert any("version" in error.lower() for error in result.errors)
        assert result.config is None

    def test_validate_file_not_found(self):
        """Test validation fails for non-existent file."""
        file_path = Path("/nonexistent/file.yaml")
        result = validate_agent_config_yaml(file_path)

        assert result.is_valid is False
        assert any("not found" in error.lower() for error in result.errors)
        assert result.config is None


class TestValidateAgentConfigDict:
    """Tests for validate_agent_config_dict function."""

    def test_validate_extractor_dict(self, sample_extractor_config: dict):
        """Test validation of extractor config dict."""
        result = validate_agent_config_dict(sample_extractor_config)

        assert result.is_valid is True
        assert result.errors == []
        assert result.config is not None
        assert result.config.agent_id == "qc-event-extractor"

    def test_validate_explorer_dict(self, sample_explorer_config: dict):
        """Test validation of explorer config dict."""
        result = validate_agent_config_dict(sample_explorer_config)

        assert result.is_valid is True
        assert result.errors == []
        assert result.config is not None
        assert result.config.agent_id == "disease-diagnosis"

    def test_validate_generator_dict(self, sample_generator_config: dict):
        """Test validation of generator config dict."""
        result = validate_agent_config_dict(sample_generator_config)

        assert result.is_valid is True
        assert result.errors == []
        assert result.config is not None
        assert result.config.agent_id == "weekly-action-plan"

    def test_validate_conversational_dict(self, sample_conversational_config: dict):
        """Test validation of conversational config dict."""
        result = validate_agent_config_dict(sample_conversational_config)

        assert result.is_valid is True
        assert result.errors == []
        assert result.config is not None
        assert result.config.agent_id == "dialogue-responder"

    def test_validate_tiered_vision_dict(self, sample_tiered_vision_config: dict):
        """Test validation of tiered-vision config dict."""
        result = validate_agent_config_dict(sample_tiered_vision_config)

        assert result.is_valid is True
        assert result.errors == []
        assert result.config is not None
        assert result.config.agent_id == "leaf-quality-analyzer"

    def test_validate_missing_agent_id(self):
        """Test validation fails for missing agent_id."""
        data = {
            "type": "extractor",
            "version": "1.0.0",
            "description": "Test",
            "input": {"event": "test", "schema": {}},
            "output": {"event": "test", "schema": {}},
            "metadata": {"author": "test"},
        }
        result = validate_agent_config_dict(data)

        assert result.is_valid is False
        assert any("agent_id" in error for error in result.errors)

    def test_validate_invalid_type(self):
        """Test validation fails for invalid type value."""
        data = {
            "agent_id": "test",
            "type": "invalid_type",
            "version": "1.0.0",
            "description": "Test",
            "input": {"event": "test", "schema": {}},
            "output": {"event": "test", "schema": {}},
            "metadata": {"author": "test"},
        }
        result = validate_agent_config_dict(data)

        assert result.is_valid is False
        assert any("type" in error.lower() for error in result.errors)

    def test_validate_missing_extractor_specific_fields(self):
        """Test validation fails for missing extractor-specific fields."""
        data = {
            "agent_id": "test-extractor",
            "type": "extractor",
            "version": "1.0.0",
            "description": "Test extractor",
            "input": {"event": "test", "schema": {}},
            "output": {"event": "test", "schema": {}},
            "llm": {"model": "test", "temperature": 0.1, "max_tokens": 100},
            "metadata": {"author": "test"},
            # Missing: extraction_schema
        }
        result = validate_agent_config_dict(data)

        assert result.is_valid is False
        assert any("extraction_schema" in error for error in result.errors)

    def test_validate_missing_explorer_specific_fields(self):
        """Test validation fails for missing explorer-specific fields."""
        data = {
            "agent_id": "test-explorer",
            "type": "explorer",
            "version": "1.0.0",
            "description": "Test explorer",
            "input": {"event": "test", "schema": {}},
            "output": {"event": "test", "schema": {}},
            "llm": {"model": "test", "temperature": 0.1, "max_tokens": 100},
            "metadata": {"author": "test"},
            # Missing: rag
        }
        result = validate_agent_config_dict(data)

        assert result.is_valid is False
        assert any("rag" in error for error in result.errors)

    def test_validate_missing_generator_specific_fields(self):
        """Test validation fails for missing generator-specific fields."""
        data = {
            "agent_id": "test-generator",
            "type": "generator",
            "version": "1.0.0",
            "description": "Test generator",
            "input": {"event": "test", "schema": {}},
            "output": {"event": "test", "schema": {}},
            "llm": {"model": "test", "temperature": 0.1, "max_tokens": 100},
            "metadata": {"author": "test"},
            # Missing: rag, output_format
        }
        result = validate_agent_config_dict(data)

        assert result.is_valid is False
        # Should fail for missing rag
        assert any("rag" in error or "output_format" in error for error in result.errors)

    def test_validate_missing_conversational_specific_fields(self):
        """Test validation fails for missing conversational-specific fields."""
        data = {
            "agent_id": "test-conversational",
            "type": "conversational",
            "version": "1.0.0",
            "description": "Test conversational",
            "input": {"event": "test", "schema": {}},
            "output": {"event": "test", "schema": {}},
            "llm": {"model": "test", "temperature": 0.1, "max_tokens": 100},
            "metadata": {"author": "test"},
            # Missing: rag, state, intent_model, response_model
        }
        result = validate_agent_config_dict(data)

        assert result.is_valid is False

    def test_validate_missing_tiered_vision_specific_fields(self):
        """Test validation fails for missing tiered-vision-specific fields."""
        data = {
            "agent_id": "test-tiered-vision",
            "type": "tiered-vision",
            "version": "1.0.0",
            "description": "Test tiered-vision",
            "input": {"event": "test", "schema": {}},
            "output": {"event": "test", "schema": {}},
            "metadata": {"author": "test"},
            # Missing: tiered_llm, routing, rag
        }
        result = validate_agent_config_dict(data)

        assert result.is_valid is False
        assert any("tiered_llm" in error or "rag" in error for error in result.errors)
