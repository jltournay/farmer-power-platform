"""Config validation tests for Farmer Voice Advisor Conversational agent.

Story 0.75.21: Conversational Agent Implementation - Sample Config & Golden Tests

This module validates that the farmer-voice-advisor config files are well-formed
and can be successfully loaded and parsed into Pydantic models.

Tests cover:
- YAML config file structure (config/agents/farmer-voice-advisor.yaml)
- JSON prompt file structure (config/prompts/farmer-voice-advisor.json)
- Pydantic model validation
- Field constraints
- Cross-reference validation
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from ai_model.domain.agent_config import AgentConfig, ConversationalConfig
from ai_model.domain.prompt import Prompt
from pydantic import TypeAdapter, ValidationError

# Mark all tests in this module as config validation tests
pytestmark = [pytest.mark.config, pytest.mark.unit]


# =============================================================================
# Config File Paths
# =============================================================================


@pytest.fixture
def agent_config_path() -> Path:
    """Path to farmer-voice-advisor agent config YAML."""
    return Path(__file__).parent.parent.parent.parent / "config/agents/farmer-voice-advisor.yaml"


@pytest.fixture
def prompt_config_path() -> Path:
    """Path to farmer-voice-advisor prompt config JSON."""
    return Path(__file__).parent.parent.parent.parent / "config/prompts/farmer-voice-advisor.json"


# =============================================================================
# Agent Config YAML Tests
# =============================================================================


class TestAgentConfigYAML:
    """Tests for farmer-voice-advisor.yaml agent config file."""

    def test_agent_config_file_exists(self, agent_config_path: Path) -> None:
        """Config file exists at expected path."""
        assert agent_config_path.exists(), f"Agent config not found at: {agent_config_path}"

    def test_agent_config_is_valid_yaml(self, agent_config_path: Path) -> None:
        """Config file is valid YAML."""
        data = yaml.safe_load(agent_config_path.read_text())
        assert isinstance(data, dict)
        assert "id" in data
        assert "type" in data

    def test_agent_config_parses_to_conversational_config(self, agent_config_path: Path) -> None:
        """Config file parses to ConversationalConfig model."""
        data = yaml.safe_load(agent_config_path.read_text())

        # Use discriminated union adapter
        adapter = TypeAdapter(AgentConfig)
        config = adapter.validate_python(data)

        assert isinstance(config, ConversationalConfig)
        assert config.type == "conversational"

    def test_agent_config_has_correct_id_format(self, agent_config_path: Path) -> None:
        """Config ID follows format: {agent_id}:{version}."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = ConversationalConfig(**data)

        expected_id = f"{config.agent_id}:{config.version}"
        assert config.id == expected_id, f"ID '{config.id}' should be '{expected_id}'"

    def test_agent_config_has_rag_enabled(self, agent_config_path: Path) -> None:
        """Conversational config has RAG enabled (required for knowledge grounding)."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = ConversationalConfig(**data)

        assert config.rag.enabled is True
        assert len(config.rag.knowledge_domains) >= 1

    def test_agent_config_knowledge_domains(self, agent_config_path: Path) -> None:
        """Conversational config has appropriate knowledge domains for voice advisor."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = ConversationalConfig(**data)

        # Should include tea/farming-related domains
        domain_names = config.rag.knowledge_domains
        assert any("tea" in d.lower() for d in domain_names) or any("cultivation" in d.lower() for d in domain_names), (
            f"Expected tea/cultivation domain, got: {domain_names}"
        )

    def test_agent_config_has_state_config(self, agent_config_path: Path) -> None:
        """Conversational config has state management configured."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = ConversationalConfig(**data)

        assert config.state is not None
        assert config.state.max_turns >= 3
        assert config.state.session_ttl_minutes >= 15
        assert config.state.context_window >= 1

    def test_agent_config_has_two_models(self, agent_config_path: Path) -> None:
        """Conversational config has both intent and response models."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = ConversationalConfig(**data)

        # Should have intent model (fast, like Haiku)
        assert config.intent_model is not None
        assert len(config.intent_model) > 0

        # Should have response model (capable, like Sonnet)
        assert config.response_model is not None
        assert len(config.response_model) > 0

    def test_agent_config_intent_model_is_fast(self, agent_config_path: Path) -> None:
        """Intent model should be a fast model (Haiku) for classification."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = ConversationalConfig(**data)

        model = config.intent_model.lower()
        assert "haiku" in model, f"Intent model should use fast Haiku, got: {config.intent_model}"

    def test_agent_config_response_model_is_capable(self, agent_config_path: Path) -> None:
        """Response model should be a capable model (Sonnet) for generation."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = ConversationalConfig(**data)

        model = config.response_model.lower()
        assert "sonnet" in model or "opus" in model, (
            f"Response model should use capable Sonnet/Opus, got: {config.response_model}"
        )

    def test_agent_config_input_event(self, agent_config_path: Path) -> None:
        """Conversational config has valid input event."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = ConversationalConfig(**data)

        # Input event should be defined
        assert config.input.event is not None
        assert len(config.input.event) > 0

    def test_agent_config_output_event(self, agent_config_path: Path) -> None:
        """Conversational config has valid output event."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = ConversationalConfig(**data)

        # Output event should include agent identifier
        assert config.output.event is not None
        assert "farmer-voice-advisor" in config.output.event.lower() or "voice" in config.output.event.lower()

    def test_agent_config_error_handling_graceful(self, agent_config_path: Path) -> None:
        """Error handling should use graceful fallback for voice conversations."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = ConversationalConfig(**data)

        # For voice conversations, graceful fallback is preferred
        assert config.error_handling.on_failure == "graceful_fallback"


# =============================================================================
# Prompt Config JSON Tests
# =============================================================================


class TestPromptConfigJSON:
    """Tests for farmer-voice-advisor.json prompt config file."""

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

        assert prompt.prompt_id == "farmer-voice-advisor"
        assert prompt.agent_id == "farmer-voice-advisor"

    def test_prompt_config_has_system_prompt(self, prompt_config_path: Path) -> None:
        """Prompt config has system_prompt defined."""
        data = json.loads(prompt_config_path.read_text())
        prompt = Prompt(**data)

        assert prompt.content.system_prompt is not None
        assert len(prompt.content.system_prompt) > 100  # Should be substantial

    def test_prompt_config_system_prompt_has_persona(self, prompt_config_path: Path) -> None:
        """System prompt includes persona and role guidance."""
        data = json.loads(prompt_config_path.read_text())
        prompt = Prompt(**data)

        system = prompt.content.system_prompt.lower()
        # Should mention being an advisor or assistant
        assert "advisor" in system or "assistant" in system or "shamba" in system

    def test_prompt_config_has_template_with_variables(self, prompt_config_path: Path) -> None:
        """Prompt config has template with Jinja-style variables."""
        data = json.loads(prompt_config_path.read_text())
        prompt = Prompt(**data)

        # Should have template variables
        assert "{{" in prompt.content.template
        assert "}}" in prompt.content.template

    def test_prompt_config_template_has_user_message(self, prompt_config_path: Path) -> None:
        """Template includes user_message variable."""
        data = json.loads(prompt_config_path.read_text())
        prompt = Prompt(**data)

        assert "user_message" in prompt.content.template

    def test_prompt_config_has_output_schema(self, prompt_config_path: Path) -> None:
        """Prompt config has output_schema for structured output."""
        data = json.loads(prompt_config_path.read_text())
        prompt = Prompt(**data)

        assert prompt.content.output_schema is not None
        assert "type" in prompt.content.output_schema

    def test_prompt_config_output_schema_has_response(self, prompt_config_path: Path) -> None:
        """Prompt output_schema includes response field."""
        data = json.loads(prompt_config_path.read_text())
        prompt = Prompt(**data)

        schema = prompt.content.output_schema
        if "properties" in schema:
            assert "response" in schema["properties"]

    def test_prompt_config_has_few_shot_examples(self, prompt_config_path: Path) -> None:
        """Prompt config has few-shot examples for guidance."""
        data = json.loads(prompt_config_path.read_text())
        prompt = Prompt(**data)

        assert prompt.content.few_shot_examples is not None
        assert len(prompt.content.few_shot_examples) >= 2

    def test_prompt_config_few_shot_examples_have_input_output(self, prompt_config_path: Path) -> None:
        """Few-shot examples have both input and output."""
        data = json.loads(prompt_config_path.read_text())
        prompt = Prompt(**data)

        for example in prompt.content.few_shot_examples:
            assert "input" in example
            assert "output" in example


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

        agent_config = ConversationalConfig(**agent_data)
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

        agent_config = ConversationalConfig(**agent_data)
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

        agent_config = ConversationalConfig(**agent_data)
        prompt = Prompt(**prompt_data)

        # Both should specify output schema
        assert agent_config.output.schema is not None
        assert prompt.content.output_schema is not None

        # Both should require response field
        agent_required = agent_config.output.schema.get("required", [])
        prompt_required = prompt.content.output_schema.get("required", [])

        if agent_required:
            assert "response" in agent_required
        if prompt_required:
            assert "response" in prompt_required


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
        config = ConversationalConfig(**data_copy)
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
            ConversationalConfig(**data)
        assert "min_similarity" in str(exc_info.value)

    def test_agent_config_rejects_invalid_max_turns(self, agent_config_path: Path) -> None:
        """Agent config rejects invalid max_turns (negative or zero)."""
        data = yaml.safe_load(agent_config_path.read_text())

        # Set invalid max_turns
        data["state"]["max_turns"] = 0

        with pytest.raises(ValidationError) as exc_info:
            ConversationalConfig(**data)
        assert "max_turns" in str(exc_info.value)

    def test_agent_config_rejects_invalid_context_window(self, agent_config_path: Path) -> None:
        """Agent config rejects invalid context_window (too large)."""
        data = yaml.safe_load(agent_config_path.read_text())

        # Set invalid context_window (larger than max in StateConfig)
        data["state"]["context_window"] = 100  # > max of 20

        with pytest.raises(ValidationError) as exc_info:
            ConversationalConfig(**data)
        assert "context_window" in str(exc_info.value)

    def test_prompt_config_rejects_invalid_status(self, prompt_config_path: Path) -> None:
        """Prompt config rejects invalid status value."""
        data = json.loads(prompt_config_path.read_text())

        # Set invalid status
        data["status"] = "invalid_status"

        with pytest.raises(ValidationError) as exc_info:
            Prompt(**data)
        assert "status" in str(exc_info.value)
