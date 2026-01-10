"""Config validation tests for Weekly Action Plan Generator agent.

Story 0.75.20: Generator Agent Implementation - Sample Config & Golden Tests

This module validates that the weekly-action-plan config files are well-formed
and can be successfully loaded and parsed into Pydantic models.

Tests cover:
- YAML config file structure (config/agents/weekly-action-plan.yaml)
- JSON prompt file structure (config/prompts/weekly-action-plan.json)
- Pydantic model validation
- Field constraints
- Cross-reference validation
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from ai_model.domain.agent_config import AgentConfig, GeneratorConfig
from ai_model.domain.prompt import Prompt
from pydantic import TypeAdapter, ValidationError

# Mark all tests in this module as config validation tests
pytestmark = [pytest.mark.config, pytest.mark.unit]


# =============================================================================
# Config File Paths
# =============================================================================


@pytest.fixture
def agent_config_path() -> Path:
    """Path to weekly-action-plan agent config YAML."""
    return Path(__file__).parent.parent.parent.parent / "config/agents/weekly-action-plan.yaml"


@pytest.fixture
def prompt_config_path() -> Path:
    """Path to weekly-action-plan prompt config JSON."""
    return Path(__file__).parent.parent.parent.parent / "config/prompts/weekly-action-plan.json"


# =============================================================================
# Agent Config YAML Tests
# =============================================================================


class TestAgentConfigYAML:
    """Tests for weekly-action-plan.yaml agent config file."""

    def test_agent_config_file_exists(self, agent_config_path: Path) -> None:
        """Config file exists at expected path."""
        assert agent_config_path.exists(), f"Agent config not found at: {agent_config_path}"

    def test_agent_config_is_valid_yaml(self, agent_config_path: Path) -> None:
        """Config file is valid YAML."""
        data = yaml.safe_load(agent_config_path.read_text())
        assert isinstance(data, dict)
        assert "id" in data
        assert "type" in data

    def test_agent_config_parses_to_generator_config(self, agent_config_path: Path) -> None:
        """Config file parses to GeneratorConfig model."""
        data = yaml.safe_load(agent_config_path.read_text())

        # Use discriminated union adapter
        adapter = TypeAdapter(AgentConfig)
        config = adapter.validate_python(data)

        assert isinstance(config, GeneratorConfig)
        assert config.type == "generator"

    def test_agent_config_has_correct_id_format(self, agent_config_path: Path) -> None:
        """Config ID follows format: {agent_id}:{version}."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = GeneratorConfig(**data)

        expected_id = f"{config.agent_id}:{config.version}"
        assert config.id == expected_id, f"ID '{config.id}' should be '{expected_id}'"

    def test_agent_config_has_rag_enabled(self, agent_config_path: Path) -> None:
        """Generator config has RAG enabled (required for Generator agents)."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = GeneratorConfig(**data)

        assert config.rag.enabled is True
        assert len(config.rag.knowledge_domains) >= 1

    def test_agent_config_knowledge_domains(self, agent_config_path: Path) -> None:
        """Generator config has appropriate knowledge domains for action planning."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = GeneratorConfig(**data)

        # Should include tea cultivation and action plan domains
        domain_names = config.rag.knowledge_domains
        assert any("tea" in d.lower() or "cultivation" in d.lower() for d in domain_names), (
            f"Expected tea-related domain, got: {domain_names}"
        )

    def test_agent_config_has_mcp_sources(self, agent_config_path: Path) -> None:
        """Generator config has MCP sources for context fetching."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = GeneratorConfig(**data)

        # Should have at least one MCP source
        assert len(config.mcp_sources) >= 1

    def test_agent_config_llm_uses_capable_model(self, agent_config_path: Path) -> None:
        """Generator config uses a capable model (not Haiku for content generation)."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = GeneratorConfig(**data)

        # Should use Sonnet or better for complex generation
        model = config.llm.model.lower()
        assert "haiku" not in model, f"Generator should use capable model, not Haiku: {config.llm.model}"

    def test_agent_config_has_output_format(self, agent_config_path: Path) -> None:
        """Generator config has output_format specified."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = GeneratorConfig(**data)

        # Output format should be defined and valid
        assert config.output_format in ["json", "markdown", "text"]

    def test_agent_config_input_event(self, agent_config_path: Path) -> None:
        """Generator config has valid input event."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = GeneratorConfig(**data)

        # Input event should be defined
        assert config.input.event is not None
        assert len(config.input.event) > 0

    def test_agent_config_output_event(self, agent_config_path: Path) -> None:
        """Generator config has valid output event."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = GeneratorConfig(**data)

        # Output event should include agent identifier
        assert config.output.event is not None
        assert "weekly" in config.output.event.lower() or "action-plan" in config.output.event.lower()

    def test_agent_config_reasonable_temperature(self, agent_config_path: Path) -> None:
        """Generator config uses reasonable temperature for creativity."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = GeneratorConfig(**data)

        # Generators should have moderate temperature (0.4-0.7) for creative but coherent output
        assert 0.3 <= config.llm.temperature <= 0.8, (
            f"Temperature {config.llm.temperature} outside recommended range [0.3, 0.8]"
        )

    def test_agent_config_sufficient_max_tokens(self, agent_config_path: Path) -> None:
        """Generator config has sufficient max_tokens for action plans."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = GeneratorConfig(**data)

        # Action plans need more tokens than extractors
        assert config.llm.max_tokens >= 2000, (
            f"max_tokens {config.llm.max_tokens} may be too low for detailed action plans"
        )


# =============================================================================
# Prompt Config JSON Tests
# =============================================================================


class TestPromptConfigJSON:
    """Tests for weekly-action-plan.json prompt config file."""

    def test_prompt_config_file_exists(self, prompt_config_path: Path) -> None:
        """Prompt file exists at expected path."""
        assert prompt_config_path.exists(), f"Prompt config not found at: {prompt_config_path}"

    def test_prompt_config_is_valid_json(self, prompt_config_path: Path) -> None:
        """Prompt file is valid JSON."""
        data = json.loads(prompt_config_path.read_text())
        assert isinstance(data, dict)
        assert "id" in data
        assert "content" in data

    def test_prompt_config_parses_to_prompt_model(self, prompt_config_path: Path) -> None:
        """Prompt file parses to Prompt model."""
        data = json.loads(prompt_config_path.read_text())
        prompt = Prompt(**data)

        assert prompt.prompt_id == "weekly-action-plan"
        assert prompt.agent_id == "weekly-action-plan"

    def test_prompt_config_has_system_prompt(self, prompt_config_path: Path) -> None:
        """Prompt config has system_prompt defined."""
        data = json.loads(prompt_config_path.read_text())
        prompt = Prompt(**data)

        assert prompt.content.system_prompt is not None
        assert len(prompt.content.system_prompt) > 100  # Should be substantial

    def test_prompt_config_has_template_with_variables(self, prompt_config_path: Path) -> None:
        """Prompt config has template with Jinja-style variables."""
        data = json.loads(prompt_config_path.read_text())
        prompt = Prompt(**data)

        # Should have template variables
        assert "{{" in prompt.content.template
        assert "}}" in prompt.content.template

    def test_prompt_config_has_output_schema(self, prompt_config_path: Path) -> None:
        """Prompt config has output_schema for structured output."""
        data = json.loads(prompt_config_path.read_text())
        prompt = Prompt(**data)

        assert prompt.content.output_schema is not None
        assert "type" in prompt.content.output_schema

    def test_prompt_config_output_schema_has_action_plan(self, prompt_config_path: Path) -> None:
        """Prompt output_schema includes action_plan field."""
        data = json.loads(prompt_config_path.read_text())
        prompt = Prompt(**data)

        schema = prompt.content.output_schema
        if "properties" in schema:
            assert "action_plan" in schema["properties"]

    def test_prompt_config_output_schema_has_summary(self, prompt_config_path: Path) -> None:
        """Prompt output_schema includes summary field for SMS/voice."""
        data = json.loads(prompt_config_path.read_text())
        prompt = Prompt(**data)

        schema = prompt.content.output_schema
        if "properties" in schema:
            assert "summary" in schema["properties"]

    def test_prompt_config_has_few_shot_examples(self, prompt_config_path: Path) -> None:
        """Prompt config has few-shot examples for guidance."""
        data = json.loads(prompt_config_path.read_text())
        prompt = Prompt(**data)

        assert prompt.content.few_shot_examples is not None
        assert len(prompt.content.few_shot_examples) >= 1

    def test_prompt_config_few_shot_examples_have_input_output(self, prompt_config_path: Path) -> None:
        """Few-shot examples have both input and output."""
        data = json.loads(prompt_config_path.read_text())
        prompt = Prompt(**data)

        for example in prompt.content.few_shot_examples:
            assert "input" in example
            assert "output" in example

    def test_prompt_system_prompt_mentions_priority_levels(self, prompt_config_path: Path) -> None:
        """System prompt defines priority levels (critical, high, medium, low)."""
        data = json.loads(prompt_config_path.read_text())
        prompt = Prompt(**data)

        system_prompt = prompt.content.system_prompt.lower()
        assert "critical" in system_prompt
        assert "high" in system_prompt
        assert "medium" in system_prompt
        assert "low" in system_prompt

    def test_prompt_system_prompt_mentions_sms_constraint(self, prompt_config_path: Path) -> None:
        """System prompt mentions SMS character constraint."""
        data = json.loads(prompt_config_path.read_text())
        prompt = Prompt(**data)

        system_prompt = prompt.content.system_prompt.lower()
        assert "300" in system_prompt or "sms" in system_prompt

    def test_prompt_system_prompt_mentions_voice_constraint(self, prompt_config_path: Path) -> None:
        """System prompt mentions voice script constraint."""
        data = json.loads(prompt_config_path.read_text())
        prompt = Prompt(**data)

        system_prompt = prompt.content.system_prompt.lower()
        assert "voice" in system_prompt or "2000" in system_prompt


# =============================================================================
# Cross-Reference Validation Tests
# =============================================================================


class TestCrossReferenceValidation:
    """Tests for consistency between agent config and prompt config."""

    def test_agent_id_matches_between_configs(
        self,
        agent_config_path: Path,
        prompt_config_path: Path,
    ) -> None:
        """Agent ID matches between agent config and prompt config."""
        agent_data = yaml.safe_load(agent_config_path.read_text())
        prompt_data = json.loads(prompt_config_path.read_text())

        agent_config = GeneratorConfig(**agent_data)
        prompt = Prompt(**prompt_data)

        assert agent_config.agent_id == prompt.agent_id

    def test_version_consistency(
        self,
        agent_config_path: Path,
        prompt_config_path: Path,
    ) -> None:
        """Version is consistent between configs."""
        agent_data = yaml.safe_load(agent_config_path.read_text())
        prompt_data = json.loads(prompt_config_path.read_text())

        agent_config = GeneratorConfig(**agent_data)
        prompt = Prompt(**prompt_data)

        # Versions should match (or at least be compatible)
        assert agent_config.version == prompt.version

    def test_output_schema_alignment(
        self,
        agent_config_path: Path,
        prompt_config_path: Path,
    ) -> None:
        """Output schema is aligned between agent config and prompt config."""
        agent_data = yaml.safe_load(agent_config_path.read_text())
        prompt_data = json.loads(prompt_config_path.read_text())

        agent_config = GeneratorConfig(**agent_data)
        prompt = Prompt(**prompt_data)

        # Both should specify output schema
        assert agent_config.output.schema is not None
        assert prompt.content.output_schema is not None

        # Check that key fields match
        agent_required = agent_config.output.schema.get("required", [])
        prompt_required = prompt.content.output_schema.get("required", [])

        # Both should require action_plan and summary
        if agent_required and prompt_required:
            assert "action_plan" in agent_required
            assert "summary" in agent_required
            assert "action_plan" in prompt_required
            assert "summary" in prompt_required


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestConfigEdgeCases:
    """Tests for edge cases in config handling."""

    def test_agent_config_handles_optional_fields(self, agent_config_path: Path) -> None:
        """Agent config handles optional fields gracefully."""
        data = yaml.safe_load(agent_config_path.read_text())

        # Remove optional fields
        data_copy = data.copy()
        data_copy.pop("mcp_sources", None)

        # Should still parse (mcp_sources has default empty list)
        config = GeneratorConfig(**data_copy)
        assert config.mcp_sources == []

    def test_prompt_config_handles_missing_ab_test(self, prompt_config_path: Path) -> None:
        """Prompt config handles missing ab_test field."""
        data = json.loads(prompt_config_path.read_text())

        # Remove ab_test if present
        data_copy = data.copy()
        data_copy.pop("ab_test", None)

        # Should still parse (ab_test has default)
        prompt = Prompt(**data_copy)
        assert prompt.ab_test.enabled is False

    def test_agent_config_rejects_invalid_rag_threshold(self, agent_config_path: Path) -> None:
        """Agent config rejects invalid RAG min_similarity threshold."""
        data = yaml.safe_load(agent_config_path.read_text())

        # Set invalid threshold
        data["rag"]["min_similarity"] = 1.5  # > 1.0

        with pytest.raises(ValidationError) as exc_info:
            GeneratorConfig(**data)
        assert "min_similarity" in str(exc_info.value)

    def test_prompt_config_rejects_invalid_status(self, prompt_config_path: Path) -> None:
        """Prompt config rejects invalid status value."""
        data = json.loads(prompt_config_path.read_text())

        # Set invalid status
        data["status"] = "invalid_status"

        with pytest.raises(ValidationError) as exc_info:
            Prompt(**data)
        assert "status" in str(exc_info.value)

    def test_agent_config_rejects_invalid_output_format(self, agent_config_path: Path) -> None:
        """Agent config rejects invalid output_format value."""
        data = yaml.safe_load(agent_config_path.read_text())

        # Set invalid output format
        data["output_format"] = "invalid_format"

        with pytest.raises(ValidationError) as exc_info:
            GeneratorConfig(**data)
        assert "output_format" in str(exc_info.value)
