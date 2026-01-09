"""Unit tests for workflow state definitions.

Tests that state TypedDicts can be properly instantiated and used.

Story 0.75.16: LangGraph SDK Integration & Base Workflows
"""

from datetime import UTC, datetime

from ai_model.domain.agent_config import (
    AgentConfigMetadata,
    ExtractorConfig,
    InputConfig,
    LLMConfig,
    OutputConfig,
)
from ai_model.workflows.states import (
    ConversationalState,
    ExplorerState,
    ExtractorState,
    GeneratorState,
    TieredVisionState,
)
from ai_model.workflows.states.conversational import MessageTurn
from ai_model.workflows.states.explorer import AnalyzerResult
from ai_model.workflows.states.tiered_vision import DiagnoseResult, ScreenResult


def _make_extractor_config() -> ExtractorConfig:
    """Create a minimal ExtractorConfig for testing."""
    return ExtractorConfig(
        id="test-extractor:1.0.0",
        agent_id="test-extractor",
        version="1.0.0",
        description="Test extractor",
        input=InputConfig(event="test.input", schema={"type": "object"}),
        output=OutputConfig(event="test.output", schema={"type": "object"}),
        llm=LLMConfig(model="test"),
        metadata=AgentConfigMetadata(author="test"),
        extraction_schema={"type": "object"},
    )


class TestExtractorState:
    """Tests for ExtractorState TypedDict."""

    def test_create_minimal_state(self) -> None:
        """Test creating state with minimal required fields."""
        state: ExtractorState = {
            "input_data": {"doc_id": "123"},
            "agent_id": "test-extractor",
            "agent_config": _make_extractor_config(),
            "correlation_id": "corr-123",
        }

        assert state["input_data"]["doc_id"] == "123"
        assert state["agent_id"] == "test-extractor"

    def test_create_full_state(self) -> None:
        """Test creating state with all fields."""
        now = datetime.now(UTC)
        state: ExtractorState = {
            "input_data": {"doc_id": "123", "content": "test"},
            "agent_id": "test-extractor",
            "agent_config": _make_extractor_config(),
            "prompt_template": "Extract from {{content}}",
            "correlation_id": "corr-123",
            "raw_extraction": {"field1": "value1"},
            "validated_data": {"field1": "value1"},
            "validation_errors": [],
            "output": {"field1": "value1"},
            "success": True,
            "error_message": None,
            "model_used": "anthropic/claude-3-5-sonnet",
            "tokens_used": 500,
            "execution_time_ms": 1234,
            "started_at": now,
            "completed_at": now,
        }

        assert state["success"] is True
        assert state["tokens_used"] == 500

    def test_state_supports_optional_fields(self) -> None:
        """Test that state works without optional fields."""
        state: ExtractorState = {}
        # Should not raise - TypedDict with total=False allows missing keys
        assert state.get("success") is None
        assert state.get("input_data") is None


class TestExplorerState:
    """Tests for ExplorerState TypedDict."""

    def test_create_minimal_state(self) -> None:
        """Test creating state with minimal fields."""
        state: ExplorerState = {
            "input_data": {"event_id": "456"},
            "agent_id": "disease-diagnosis",
            "correlation_id": "corr-456",
        }

        assert state["agent_id"] == "disease-diagnosis"

    def test_analyzer_result_typed_dict(self) -> None:
        """Test AnalyzerResult TypedDict."""
        result: AnalyzerResult = {
            "analyzer_id": "disease",
            "category": "disease",
            "confidence": 0.85,
            "findings": ["Yellow spots on leaves", "Wilting"],
            "recommendations": ["Apply fungicide", "Improve drainage"],
            "success": True,
            "error": None,
        }

        assert result["confidence"] == 0.85
        assert len(result["findings"]) == 2

    def test_state_with_saga_fields(self) -> None:
        """Test state with saga pattern fields."""
        state: ExplorerState = {
            "route_type": "parallel",
            "selected_analyzers": ["disease", "weather", "nutrition"],
            "analyzer_results": [],
            "branch_timeout_seconds": 30,
            "failed_branches": [],
        }

        assert state["route_type"] == "parallel"
        assert len(state["selected_analyzers"]) == 3


class TestGeneratorState:
    """Tests for GeneratorState TypedDict."""

    def test_create_with_output_format(self) -> None:
        """Test creating state with output format."""
        state: GeneratorState = {
            "input_data": {"topic": "tea cultivation"},
            "agent_id": "weekly-plan",
            "output_format": "markdown",
        }

        assert state["output_format"] == "markdown"

    def test_valid_output_formats(self) -> None:
        """Test all valid output formats."""
        for fmt in ["json", "markdown", "text"]:
            state: GeneratorState = {"output_format": fmt}  # type: ignore[typeddict-item]
            assert state["output_format"] == fmt

    def test_state_with_rag_context(self) -> None:
        """Test state with RAG context."""
        state: GeneratorState = {
            "rag_context": [
                {"content": "Tea requires well-drained soil", "domain": "tea"},
                {"content": "Water weekly during dry season", "domain": "irrigation"},
            ],
            "rag_query": "tea cultivation tips",
            "rag_domains": ["tea", "irrigation"],
        }

        assert len(state["rag_context"]) == 2
        assert state["rag_query"] == "tea cultivation tips"


class TestConversationalState:
    """Tests for ConversationalState TypedDict."""

    def test_message_turn_typed_dict(self) -> None:
        """Test MessageTurn TypedDict."""
        turn: MessageTurn = {
            "role": "user",
            "content": "What is the best time to harvest?",
            "timestamp": datetime.now(UTC),
        }

        assert turn["role"] == "user"
        assert "harvest" in turn["content"]

    def test_state_with_session_fields(self) -> None:
        """Test state with session management fields."""
        now = datetime.now(UTC)
        state: ConversationalState = {
            "session_id": "sess-123",
            "conversation_history": [],
            "turn_count": 0,
            "max_turns": 5,
            "context_window": 3,
            "session_started_at": now,
            "session_expires_at": now,
        }

        assert state["max_turns"] == 5
        assert state["turn_count"] == 0

    def test_state_with_intent_fields(self) -> None:
        """Test state with intent classification fields."""
        state: ConversationalState = {
            "intent": "question",
            "intent_confidence": 0.92,
            "entities": {"crop": "tea", "issue": "yellowing"},
            "requires_knowledge": True,
        }

        assert state["intent"] == "question"
        assert state["requires_knowledge"] is True


class TestTieredVisionState:
    """Tests for TieredVisionState TypedDict."""

    def test_screen_result_typed_dict(self) -> None:
        """Test ScreenResult TypedDict."""
        result: ScreenResult = {
            "classification": "healthy",
            "confidence": 0.95,
            "preliminary_findings": ["No visible issues"],
            "skip_reason": "Healthy with high confidence",
        }

        assert result["classification"] == "healthy"
        assert result["confidence"] == 0.95

    def test_diagnose_result_typed_dict(self) -> None:
        """Test DiagnoseResult TypedDict."""
        result: DiagnoseResult = {
            "primary_issue": "fungal infection",
            "confidence": 0.87,
            "detailed_findings": ["White powder on leaves", "Stunted growth"],
            "recommendations": ["Apply fungicide", "Improve air circulation"],
            "severity": "medium",
        }

        assert result["primary_issue"] == "fungal infection"
        assert result["severity"] == "medium"

    def test_state_with_tier_tracking(self) -> None:
        """Test state with tier execution tracking."""
        state: TieredVisionState = {
            "tier1_executed": True,
            "tier2_executed": False,
            "tier1_model": "anthropic/claude-3-haiku",
            "tier2_model": None,
            "tier1_tokens": 150,
            "tier2_tokens": 0,
            "total_cost_usd": 0.001,
        }

        assert state["tier1_executed"] is True
        assert state["tier2_executed"] is False

    def test_state_with_routing_fields(self) -> None:
        """Test state with routing decision fields."""
        state: TieredVisionState = {
            "proceed_to_tier2": False,
            "tier2_skip_reason": "Healthy with high confidence (0.92 >= 0.85)",
        }

        assert state["proceed_to_tier2"] is False
        assert "0.92" in state["tier2_skip_reason"]


class TestStateInteroperability:
    """Tests for state dictionary compatibility."""

    def test_states_are_valid_dicts(self) -> None:
        """Test that all states work as regular dicts."""
        states = [
            ExtractorState(input_data={}, agent_id="test"),  # type: ignore[call-arg]
            ExplorerState(input_data={}, agent_id="test"),  # type: ignore[call-arg]
            GeneratorState(input_data={}, agent_id="test"),  # type: ignore[call-arg]
            ConversationalState(session_id="test"),  # type: ignore[call-arg]
            TieredVisionState(image_data="base64"),  # type: ignore[call-arg]
        ]

        for state in states:
            # TypedDicts are compatible with dict operations
            assert isinstance(state, dict)

    def test_state_copy_and_update(self) -> None:
        """Test that states can be copied and updated."""
        original: ExtractorState = {
            "input_data": {"doc_id": "123"},
            "agent_id": "test",
            "success": False,
        }

        # Copy and update
        updated = {**original, "success": True}

        assert original["success"] is False
        assert updated["success"] is True
