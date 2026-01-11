"""Config validation tests for Leaf Quality Analyzer Tiered-Vision agent.

Story 0.75.22: Tiered-Vision Agent Implementation - Sample Config & Golden Tests

This module validates that the leaf-quality-analyzer config file is well-formed
and can be successfully loaded and parsed into Pydantic models.

Tests cover:
- YAML config file structure (config/agents/leaf-quality-analyzer.yaml)
- Pydantic model validation (TieredVisionConfig)
- Field constraints and tiered LLM configuration
- Routing threshold validation
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from ai_model.domain.agent_config import AgentConfig, TieredVisionConfig
from pydantic import TypeAdapter, ValidationError

# Mark all tests in this module as config validation tests
pytestmark = [pytest.mark.config, pytest.mark.unit]


# =============================================================================
# Config File Paths
# =============================================================================


@pytest.fixture
def agent_config_path() -> Path:
    """Path to leaf-quality-analyzer agent config YAML."""
    return Path(__file__).parent.parent.parent.parent / "config/agents/leaf-quality-analyzer.yaml"


# =============================================================================
# Agent Config YAML Tests
# =============================================================================


class TestAgentConfigYAML:
    """Tests for leaf-quality-analyzer.yaml agent config file."""

    def test_agent_config_file_exists(self, agent_config_path: Path) -> None:
        """Config file exists at expected path."""
        assert agent_config_path.exists(), f"Agent config not found at: {agent_config_path}"

    def test_agent_config_is_valid_yaml(self, agent_config_path: Path) -> None:
        """Config file is valid YAML."""
        data = yaml.safe_load(agent_config_path.read_text())
        assert isinstance(data, dict)
        assert "id" in data
        assert "type" in data

    def test_agent_config_parses_to_tiered_vision_config(self, agent_config_path: Path) -> None:
        """Config file parses to TieredVisionConfig model."""
        data = yaml.safe_load(agent_config_path.read_text())

        # Use discriminated union adapter
        adapter = TypeAdapter(AgentConfig)
        config = adapter.validate_python(data)

        assert isinstance(config, TieredVisionConfig)
        assert config.type == "tiered-vision"

    def test_agent_config_has_correct_id_format(self, agent_config_path: Path) -> None:
        """Config ID follows format: {agent_id}:{version}."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = TieredVisionConfig(**data)

        expected_id = f"{config.agent_id}:{config.version}"
        assert config.id == expected_id, f"ID '{config.id}' should be '{expected_id}'"

    def test_agent_config_agent_id(self, agent_config_path: Path) -> None:
        """Config has correct agent_id."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = TieredVisionConfig(**data)

        assert config.agent_id == "leaf-quality-analyzer"


class TestTieredLLMConfig:
    """Tests for tiered_llm configuration."""

    def test_has_tiered_llm_config(self, agent_config_path: Path) -> None:
        """Config has tiered_llm section."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = TieredVisionConfig(**data)

        assert config.tiered_llm is not None
        assert config.tiered_llm.screen is not None
        assert config.tiered_llm.diagnose is not None

    def test_screen_uses_fast_model(self, agent_config_path: Path) -> None:
        """Tier 1 (screen) uses fast model like Haiku."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = TieredVisionConfig(**data)

        screen_model = config.tiered_llm.screen.model.lower()
        # Should use a fast/cheap model
        assert "haiku" in screen_model, f"Screen should use Haiku, got: {config.tiered_llm.screen.model}"

    def test_diagnose_uses_capable_model(self, agent_config_path: Path) -> None:
        """Tier 2 (diagnose) uses capable model like Sonnet."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = TieredVisionConfig(**data)

        diagnose_model = config.tiered_llm.diagnose.model.lower()
        # Should use a capable model (not Haiku)
        assert "haiku" not in diagnose_model, f"Diagnose should not use Haiku, got: {config.tiered_llm.diagnose.model}"
        assert "sonnet" in diagnose_model or "opus" in diagnose_model

    def test_screen_has_low_temperature(self, agent_config_path: Path) -> None:
        """Screen model has low temperature for consistent classification."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = TieredVisionConfig(**data)

        assert config.tiered_llm.screen.temperature <= 0.3

    def test_screen_has_low_max_tokens(self, agent_config_path: Path) -> None:
        """Screen model has low max_tokens for brief output."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = TieredVisionConfig(**data)

        assert config.tiered_llm.screen.max_tokens <= 500

    def test_diagnose_has_higher_max_tokens(self, agent_config_path: Path) -> None:
        """Diagnose model has higher max_tokens for detailed analysis."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = TieredVisionConfig(**data)

        assert config.tiered_llm.diagnose.max_tokens >= 1000


class TestRoutingConfig:
    """Tests for routing configuration."""

    def test_has_routing_config(self, agent_config_path: Path) -> None:
        """Config has routing section."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = TieredVisionConfig(**data)

        assert config.routing is not None

    def test_routing_thresholds_valid(self, agent_config_path: Path) -> None:
        """Routing thresholds are valid (0.0-1.0)."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = TieredVisionConfig(**data)

        assert 0.0 <= config.routing.screen_threshold <= 1.0
        assert 0.0 <= config.routing.healthy_skip_threshold <= 1.0
        assert 0.0 <= config.routing.obvious_skip_threshold <= 1.0

    def test_healthy_skip_threshold_higher_than_screen(self, agent_config_path: Path) -> None:
        """Healthy skip threshold should be higher than screen threshold."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = TieredVisionConfig(**data)

        assert config.routing.healthy_skip_threshold >= config.routing.screen_threshold


class TestRAGConfig:
    """Tests for RAG configuration (used in Tier 2)."""

    def test_has_rag_config(self, agent_config_path: Path) -> None:
        """Config has RAG section for Tier 2 diagnosis."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = TieredVisionConfig(**data)

        assert config.rag is not None

    def test_rag_enabled(self, agent_config_path: Path) -> None:
        """RAG is enabled for enhanced diagnosis."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = TieredVisionConfig(**data)

        assert config.rag.enabled is True

    def test_rag_has_knowledge_domains(self, agent_config_path: Path) -> None:
        """RAG has appropriate knowledge domains."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = TieredVisionConfig(**data)

        assert len(config.rag.knowledge_domains) >= 1
        # Should include disease-related domains
        domain_names = config.rag.knowledge_domains
        has_relevant_domain = any(
            "disease" in d.lower() or "pathology" in d.lower() or "symptom" in d.lower() for d in domain_names
        )
        assert has_relevant_domain, f"Expected disease-related domain, got: {domain_names}"


class TestMCPSourcesConfig:
    """Tests for MCP sources configuration."""

    def test_has_mcp_sources(self, agent_config_path: Path) -> None:
        """Config has MCP sources for image fetching."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = TieredVisionConfig(**data)

        assert len(config.mcp_sources) >= 1

    def test_has_collection_mcp_source(self, agent_config_path: Path) -> None:
        """Config includes collection-mcp for image fetching."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = TieredVisionConfig(**data)

        collection_sources = [s for s in config.mcp_sources if s.server == "collection-mcp"]
        assert len(collection_sources) >= 1

    def test_collection_mcp_has_image_tools(self, agent_config_path: Path) -> None:
        """Collection MCP source includes image fetching tools."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = TieredVisionConfig(**data)

        collection_sources = [s for s in config.mcp_sources if s.server == "collection-mcp"]
        assert len(collection_sources) >= 1

        tools = collection_sources[0].tools
        # Should have thumbnail and image fetch tools
        assert "get_document_thumbnail" in tools or "get_document_image" in tools


class TestInputOutputContracts:
    """Tests for input/output contract configuration."""

    def test_input_requires_doc_id(self, agent_config_path: Path) -> None:
        """Input schema requires doc_id field."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = TieredVisionConfig(**data)

        required = config.input.schema.get("required", [])
        assert "doc_id" in required

    def test_output_event_defined(self, agent_config_path: Path) -> None:
        """Output event is defined."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = TieredVisionConfig(**data)

        assert config.output.event is not None
        assert len(config.output.event) > 0


class TestConfigEdgeCases:
    """Tests for edge cases in config handling."""

    def test_agent_config_has_null_llm(self, agent_config_path: Path) -> None:
        """Tiered-vision config has null llm (uses tiered_llm instead)."""
        data = yaml.safe_load(agent_config_path.read_text())
        config = TieredVisionConfig(**data)

        # llm should be None for tiered-vision (uses tiered_llm)
        assert config.llm is None

    def test_agent_config_rejects_invalid_routing_threshold(self, agent_config_path: Path) -> None:
        """Agent config rejects invalid routing threshold."""
        data = yaml.safe_load(agent_config_path.read_text())

        # Set invalid threshold
        data["routing"]["screen_threshold"] = 1.5  # > 1.0

        with pytest.raises(ValidationError) as exc_info:
            TieredVisionConfig(**data)
        assert "screen_threshold" in str(exc_info.value)

    def test_agent_config_handles_optional_fields(self, agent_config_path: Path) -> None:
        """Agent config handles optional fields gracefully."""
        data = yaml.safe_load(agent_config_path.read_text())

        # Remove optional fields
        data_copy = data.copy()
        data_copy.pop("mcp_sources", None)

        # Should still parse (mcp_sources has default empty list)
        config = TieredVisionConfig(**data_copy)
        assert config.mcp_sources == []
