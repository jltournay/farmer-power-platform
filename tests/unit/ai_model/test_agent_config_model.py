"""Unit tests for Agent Configuration domain models.

Tests cover:
- AgentType enum values (5 tests)
- AgentConfigStatus enum values (4 tests)
- LLMConfig model validation (2 tests)
- RAGConfig model validation (2 tests)
- InputConfig / OutputConfig validation (2 tests)
- MCPSourceConfig validation (2 tests)
- ErrorHandlingConfig validation with defaults (2 tests)
- StateConfig validation with defaults (2 tests)
- ExtractorConfig creation and serialization (2 tests)
- ExplorerConfig creation and serialization (2 tests)
- GeneratorConfig creation and serialization (2 tests)
- ConversationalConfig creation and serialization (2 tests)
- TieredVisionConfig creation and serialization (2 tests)
- Discriminated union auto-selection (5 tests - one per type)
- Invalid type rejection (2 tests)

Total: 38+ tests
"""

import pytest
from ai_model.domain.agent_config import (
    AgentConfig,
    AgentConfigStatus,
    AgentType,
    ConversationalConfig,
    ErrorHandlingConfig,
    ExplorerConfig,
    ExtractorConfig,
    GeneratorConfig,
    InputConfig,
    LLMConfig,
    MCPSourceConfig,
    OutputConfig,
    RAGConfig,
    StateConfig,
    TieredVisionConfig,
)
from pydantic import TypeAdapter, ValidationError

# =============================================================================
# AgentType Enum Tests (5 tests)
# =============================================================================


class TestAgentType:
    """Tests for AgentType enum."""

    def test_agent_type_has_extractor_value(self) -> None:
        """Extractor type exists and has correct value."""
        assert AgentType.EXTRACTOR.value == "extractor"

    def test_agent_type_has_explorer_value(self) -> None:
        """Explorer type exists and has correct value."""
        assert AgentType.EXPLORER.value == "explorer"

    def test_agent_type_has_generator_value(self) -> None:
        """Generator type exists and has correct value."""
        assert AgentType.GENERATOR.value == "generator"

    def test_agent_type_has_conversational_value(self) -> None:
        """Conversational type exists and has correct value."""
        assert AgentType.CONVERSATIONAL.value == "conversational"

    def test_agent_type_has_tiered_vision_value(self) -> None:
        """Tiered-vision type exists and has correct value."""
        assert AgentType.TIERED_VISION.value == "tiered-vision"


# =============================================================================
# AgentConfigStatus Enum Tests (4 tests)
# =============================================================================


class TestAgentConfigStatus:
    """Tests for AgentConfigStatus enum."""

    def test_status_has_draft_value(self) -> None:
        """Draft status exists and has correct value."""
        assert AgentConfigStatus.DRAFT.value == "draft"

    def test_status_has_staged_value(self) -> None:
        """Staged status exists and has correct value."""
        assert AgentConfigStatus.STAGED.value == "staged"

    def test_status_has_active_value(self) -> None:
        """Active status exists and has correct value."""
        assert AgentConfigStatus.ACTIVE.value == "active"

    def test_status_has_archived_value(self) -> None:
        """Archived status exists and has correct value."""
        assert AgentConfigStatus.ARCHIVED.value == "archived"


# =============================================================================
# LLMConfig Tests (2 tests)
# =============================================================================


class TestLLMConfig:
    """Tests for LLMConfig model."""

    def test_llm_config_with_required_fields(self) -> None:
        """LLMConfig can be created with required model field."""
        config = LLMConfig(model="anthropic/claude-3-haiku")
        assert config.model == "anthropic/claude-3-haiku"
        assert config.temperature == 0.3  # default
        assert config.max_tokens == 2000  # default

    def test_llm_config_temperature_validation(self) -> None:
        """LLMConfig validates temperature range."""
        with pytest.raises(ValidationError) as exc_info:
            LLMConfig(model="test", temperature=3.0)  # > 2.0
        assert "temperature" in str(exc_info.value)


# =============================================================================
# RAGConfig Tests (2 tests)
# =============================================================================


class TestRAGConfig:
    """Tests for RAGConfig model."""

    def test_rag_config_default_values(self) -> None:
        """RAGConfig has sensible defaults."""
        config = RAGConfig()
        assert config.enabled is True
        assert config.top_k == 5
        assert config.min_similarity == 0.7
        assert config.knowledge_domains == []

    def test_rag_config_with_all_fields(self) -> None:
        """RAGConfig can be created with all fields."""
        config = RAGConfig(
            enabled=True,
            query_template="Query: {{input}}",
            knowledge_domains=["tea_cultivation", "plant_diseases"],
            top_k=10,
            min_similarity=0.8,
        )
        assert config.query_template == "Query: {{input}}"
        assert len(config.knowledge_domains) == 2


# =============================================================================
# InputConfig / OutputConfig Tests (2 tests)
# =============================================================================


class TestInputOutputConfig:
    """Tests for InputConfig and OutputConfig models."""

    def test_input_config_with_required_fields(self) -> None:
        """InputConfig can be created with required fields."""
        config = InputConfig(
            event="collection.document.received",
            schema={"required": ["doc_id"]},
        )
        assert config.event == "collection.document.received"
        assert config.schema == {"required": ["doc_id"]}

    def test_output_config_with_required_fields(self) -> None:
        """OutputConfig can be created with required fields."""
        config = OutputConfig(
            event="ai.extraction.complete",
            schema={"fields": ["farmer_id", "grade"]},
        )
        assert config.event == "ai.extraction.complete"


# =============================================================================
# MCPSourceConfig Tests (2 tests)
# =============================================================================


class TestMCPSourceConfig:
    """Tests for MCPSourceConfig model."""

    def test_mcp_source_config_with_required_fields(self) -> None:
        """MCPSourceConfig can be created with required fields."""
        config = MCPSourceConfig(
            server="collection",
            tools=["get_document", "get_farmer_documents"],
        )
        assert config.server == "collection"
        assert len(config.tools) == 2

    def test_mcp_source_config_requires_tools(self) -> None:
        """MCPSourceConfig requires tools field."""
        with pytest.raises(ValidationError) as exc_info:
            MCPSourceConfig(server="collection")  # type: ignore[call-arg]
        assert "tools" in str(exc_info.value)


# =============================================================================
# ErrorHandlingConfig Tests (2 tests)
# =============================================================================


class TestErrorHandlingConfig:
    """Tests for ErrorHandlingConfig model."""

    def test_error_handling_config_defaults(self) -> None:
        """ErrorHandlingConfig has sensible defaults."""
        config = ErrorHandlingConfig()
        assert config.max_attempts == 3
        assert config.backoff_ms == [100, 500, 2000]
        assert config.on_failure == "publish_error_event"
        assert config.dead_letter_topic is None

    def test_error_handling_config_with_dead_letter(self) -> None:
        """ErrorHandlingConfig supports dead letter topic."""
        config = ErrorHandlingConfig(
            on_failure="dead_letter",
            dead_letter_topic="ai.errors.dead_letter",
        )
        assert config.on_failure == "dead_letter"
        assert config.dead_letter_topic == "ai.errors.dead_letter"


# =============================================================================
# StateConfig Tests (2 tests)
# =============================================================================


class TestStateConfig:
    """Tests for StateConfig model."""

    def test_state_config_defaults(self) -> None:
        """StateConfig has sensible defaults."""
        config = StateConfig()
        assert config.max_turns == 5
        assert config.session_ttl_minutes == 30
        assert config.checkpoint_backend == "mongodb"
        assert config.context_window == 3

    def test_state_config_with_custom_values(self) -> None:
        """StateConfig can be customized."""
        config = StateConfig(
            max_turns=10,
            session_ttl_minutes=60,
            context_window=5,
        )
        assert config.max_turns == 10
        assert config.session_ttl_minutes == 60


# =============================================================================
# ExtractorConfig Tests (2 tests)
# =============================================================================


class TestExtractorConfig:
    """Tests for ExtractorConfig model."""

    @pytest.fixture
    def sample_extractor_config(self) -> dict:
        """Provide valid extractor config data."""
        return {
            "id": "qc-extractor:1.0.0",
            "agent_id": "qc-extractor",
            "version": "1.0.0",
            "description": "Extracts QC data",
            "input": {"event": "collection.document.received", "schema": {}},
            "output": {"event": "ai.extraction.complete", "schema": {}},
            "llm": {"model": "anthropic/claude-3-haiku"},
            "extraction_schema": {"required_fields": ["farmer_id"]},
            "metadata": {"author": "admin"},
        }

    def test_extractor_config_creation(self, sample_extractor_config: dict) -> None:
        """ExtractorConfig can be created with required fields."""
        config = ExtractorConfig(**sample_extractor_config)
        assert config.type == "extractor"
        assert config.extraction_schema == {"required_fields": ["farmer_id"]}

    def test_extractor_config_serialization(self, sample_extractor_config: dict) -> None:
        """ExtractorConfig can be serialized with model_dump()."""
        config = ExtractorConfig(**sample_extractor_config)
        data = config.model_dump()
        assert data["type"] == "extractor"
        assert data["extraction_schema"] == {"required_fields": ["farmer_id"]}


# =============================================================================
# ExplorerConfig Tests (2 tests)
# =============================================================================


class TestExplorerConfig:
    """Tests for ExplorerConfig model."""

    @pytest.fixture
    def sample_explorer_config(self) -> dict:
        """Provide valid explorer config data."""
        return {
            "id": "disease-diagnosis:1.0.0",
            "agent_id": "disease-diagnosis",
            "version": "1.0.0",
            "description": "Diagnoses diseases",
            "input": {"event": "collection.poor_quality_detected", "schema": {}},
            "output": {"event": "ai.diagnosis.complete", "schema": {}},
            "llm": {"model": "anthropic/claude-3-5-sonnet"},
            "rag": {"enabled": True, "knowledge_domains": ["plant_diseases"]},
            "metadata": {"author": "admin"},
        }

    def test_explorer_config_creation(self, sample_explorer_config: dict) -> None:
        """ExplorerConfig can be created with required fields."""
        config = ExplorerConfig(**sample_explorer_config)
        assert config.type == "explorer"
        assert config.rag.enabled is True
        assert "plant_diseases" in config.rag.knowledge_domains

    def test_explorer_config_serialization(self, sample_explorer_config: dict) -> None:
        """ExplorerConfig can be serialized with model_dump()."""
        config = ExplorerConfig(**sample_explorer_config)
        data = config.model_dump()
        assert data["type"] == "explorer"
        assert data["rag"]["enabled"] is True


# =============================================================================
# GeneratorConfig Tests (2 tests)
# =============================================================================


class TestGeneratorConfig:
    """Tests for GeneratorConfig model."""

    @pytest.fixture
    def sample_generator_config(self) -> dict:
        """Provide valid generator config data."""
        return {
            "id": "weekly-action-plan:1.0.0",
            "agent_id": "weekly-action-plan",
            "version": "1.0.0",
            "description": "Generates action plans",
            "input": {"event": "action_plan.generation.requested", "schema": {}},
            "output": {"event": "ai.action_plan.complete", "schema": {}},
            "llm": {"model": "anthropic/claude-3-5-sonnet"},
            "rag": {"enabled": True},
            "output_format": "markdown",
            "metadata": {"author": "admin"},
        }

    def test_generator_config_creation(self, sample_generator_config: dict) -> None:
        """GeneratorConfig can be created with required fields."""
        config = GeneratorConfig(**sample_generator_config)
        assert config.type == "generator"
        assert config.output_format == "markdown"

    def test_generator_config_output_format_options(self) -> None:
        """GeneratorConfig supports json, markdown, text formats."""
        for fmt in ["json", "markdown", "text"]:
            config = GeneratorConfig(
                id="test:1.0.0",
                agent_id="test",
                version="1.0.0",
                description="Test",
                input={"event": "test", "schema": {}},
                output={"event": "test", "schema": {}},
                llm={"model": "test"},
                rag={"enabled": False},
                output_format=fmt,  # type: ignore[arg-type]
                metadata={"author": "admin"},
            )
            assert config.output_format == fmt


# =============================================================================
# ConversationalConfig Tests (2 tests)
# =============================================================================


class TestConversationalConfig:
    """Tests for ConversationalConfig model."""

    @pytest.fixture
    def sample_conversational_config(self) -> dict:
        """Provide valid conversational config data."""
        return {
            "id": "dialogue-responder:1.0.0",
            "agent_id": "dialogue-responder",
            "version": "1.0.0",
            "description": "Handles dialogue",
            "input": {"event": "conversation.turn.received", "schema": {}},
            "output": {"event": "conversation.turn.response", "schema": {}},
            "llm": {"model": "anthropic/claude-3-5-sonnet"},
            "rag": {"enabled": True},
            "state": {"max_turns": 5, "session_ttl_minutes": 30},
            "intent_model": "anthropic/claude-3-haiku",
            "response_model": "anthropic/claude-3-5-sonnet",
            "metadata": {"author": "admin"},
        }

    def test_conversational_config_creation(self, sample_conversational_config: dict) -> None:
        """ConversationalConfig can be created with required fields."""
        config = ConversationalConfig(**sample_conversational_config)
        assert config.type == "conversational"
        assert config.intent_model == "anthropic/claude-3-haiku"
        assert config.response_model == "anthropic/claude-3-5-sonnet"

    def test_conversational_config_state_defaults(self, sample_conversational_config: dict) -> None:
        """ConversationalConfig has state with defaults."""
        config = ConversationalConfig(**sample_conversational_config)
        assert config.state.max_turns == 5
        assert config.state.checkpoint_backend == "mongodb"


# =============================================================================
# TieredVisionConfig Tests (2 tests)
# =============================================================================


class TestTieredVisionConfig:
    """Tests for TieredVisionConfig model."""

    @pytest.fixture
    def sample_tiered_vision_config(self) -> dict:
        """Provide valid tiered-vision config data."""
        return {
            "id": "leaf-analyzer:1.0.0",
            "agent_id": "leaf-analyzer",
            "version": "1.0.0",
            "description": "Analyzes leaf images",
            "input": {"event": "collection.image.received", "schema": {}},
            "output": {"event": "ai.vision_analysis.complete", "schema": {}},
            "llm": None,  # Not used for tiered-vision
            "rag": {"enabled": True},
            "tiered_llm": {
                "screen": {"model": "anthropic/claude-3-haiku", "temperature": 0.1},
                "diagnose": {"model": "anthropic/claude-3-5-sonnet"},
            },
            "routing": {"screen_threshold": 0.7},
            "metadata": {"author": "admin"},
        }

    def test_tiered_vision_config_creation(self, sample_tiered_vision_config: dict) -> None:
        """TieredVisionConfig can be created with required fields."""
        config = TieredVisionConfig(**sample_tiered_vision_config)
        assert config.type == "tiered-vision"
        assert config.llm is None
        assert config.tiered_llm.screen.model == "anthropic/claude-3-haiku"
        assert config.tiered_llm.diagnose.model == "anthropic/claude-3-5-sonnet"

    def test_tiered_vision_config_routing_defaults(self, sample_tiered_vision_config: dict) -> None:
        """TieredVisionConfig has routing thresholds with defaults."""
        config = TieredVisionConfig(**sample_tiered_vision_config)
        assert config.routing.screen_threshold == 0.7
        assert config.routing.healthy_skip_threshold == 0.85  # default
        assert config.routing.obvious_skip_threshold == 0.75  # default


# =============================================================================
# Discriminated Union Tests (5 tests)
# =============================================================================


class TestAgentConfigDiscriminatedUnion:
    """Tests for AgentConfig discriminated union auto-selection."""

    @pytest.fixture
    def adapter(self) -> TypeAdapter:
        """Provide TypeAdapter for AgentConfig discriminated union."""
        return TypeAdapter(AgentConfig)

    def test_discriminated_union_selects_extractor(self, adapter: TypeAdapter) -> None:
        """Discriminated union selects ExtractorConfig for type=extractor."""
        data = {
            "id": "test:1.0.0",
            "agent_id": "test",
            "version": "1.0.0",
            "type": "extractor",
            "description": "Test",
            "input": {"event": "test", "schema": {}},
            "output": {"event": "test", "schema": {}},
            "llm": {"model": "test"},
            "extraction_schema": {},
            "metadata": {"author": "admin"},
        }
        config = adapter.validate_python(data)
        assert isinstance(config, ExtractorConfig)
        assert config.type == "extractor"

    def test_discriminated_union_selects_explorer(self, adapter: TypeAdapter) -> None:
        """Discriminated union selects ExplorerConfig for type=explorer."""
        data = {
            "id": "test:1.0.0",
            "agent_id": "test",
            "version": "1.0.0",
            "type": "explorer",
            "description": "Test",
            "input": {"event": "test", "schema": {}},
            "output": {"event": "test", "schema": {}},
            "llm": {"model": "test"},
            "rag": {"enabled": True},
            "metadata": {"author": "admin"},
        }
        config = adapter.validate_python(data)
        assert isinstance(config, ExplorerConfig)
        assert config.type == "explorer"

    def test_discriminated_union_selects_generator(self, adapter: TypeAdapter) -> None:
        """Discriminated union selects GeneratorConfig for type=generator."""
        data = {
            "id": "test:1.0.0",
            "agent_id": "test",
            "version": "1.0.0",
            "type": "generator",
            "description": "Test",
            "input": {"event": "test", "schema": {}},
            "output": {"event": "test", "schema": {}},
            "llm": {"model": "test"},
            "rag": {"enabled": True},
            "metadata": {"author": "admin"},
        }
        config = adapter.validate_python(data)
        assert isinstance(config, GeneratorConfig)
        assert config.type == "generator"

    def test_discriminated_union_selects_conversational(self, adapter: TypeAdapter) -> None:
        """Discriminated union selects ConversationalConfig for type=conversational."""
        data = {
            "id": "test:1.0.0",
            "agent_id": "test",
            "version": "1.0.0",
            "type": "conversational",
            "description": "Test",
            "input": {"event": "test", "schema": {}},
            "output": {"event": "test", "schema": {}},
            "llm": {"model": "test"},
            "rag": {"enabled": True},
            "metadata": {"author": "admin"},
        }
        config = adapter.validate_python(data)
        assert isinstance(config, ConversationalConfig)
        assert config.type == "conversational"

    def test_discriminated_union_selects_tiered_vision(self, adapter: TypeAdapter) -> None:
        """Discriminated union selects TieredVisionConfig for type=tiered-vision."""
        data = {
            "id": "test:1.0.0",
            "agent_id": "test",
            "version": "1.0.0",
            "type": "tiered-vision",
            "description": "Test",
            "input": {"event": "test", "schema": {}},
            "output": {"event": "test", "schema": {}},
            "rag": {"enabled": True},
            "tiered_llm": {
                "screen": {"model": "haiku"},
                "diagnose": {"model": "sonnet"},
            },
            "metadata": {"author": "admin"},
        }
        config = adapter.validate_python(data)
        assert isinstance(config, TieredVisionConfig)
        assert config.type == "tiered-vision"


# =============================================================================
# Invalid Type Rejection Tests (2 tests)
# =============================================================================


class TestInvalidTypeRejection:
    """Tests for invalid type rejection."""

    def test_rejects_invalid_type_value(self) -> None:
        """Discriminated union rejects invalid type value."""
        adapter = TypeAdapter(AgentConfig)
        data = {
            "id": "test:1.0.0",
            "agent_id": "test",
            "version": "1.0.0",
            "type": "invalid_type",  # Not a valid type
            "description": "Test",
            "input": {"event": "test", "schema": {}},
            "output": {"event": "test", "schema": {}},
            "llm": {"model": "test"},
            "metadata": {"author": "admin"},
        }
        with pytest.raises(ValidationError):
            adapter.validate_python(data)

    def test_rejects_missing_type_field(self) -> None:
        """Discriminated union requires type field."""
        adapter = TypeAdapter(AgentConfig)
        data = {
            "id": "test:1.0.0",
            "agent_id": "test",
            "version": "1.0.0",
            # Missing "type" field
            "description": "Test",
            "input": {"event": "test", "schema": {}},
            "output": {"event": "test", "schema": {}},
            "llm": {"model": "test"},
            "metadata": {"author": "admin"},
        }
        with pytest.raises(ValidationError):
            adapter.validate_python(data)
