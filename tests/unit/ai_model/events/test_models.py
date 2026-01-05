"""Unit tests for AI Model event payload models.

Story 0.75.8: Event Flow, Subscriber, and Publisher (AC: #3, #11)

Tests for:
- EntityLinkage (5 entity types validation)
- AgentResult types (5 result types)
- Event envelopes with linkage
"""

from decimal import Decimal

import pytest
from ai_model.events.models import (
    AgentCompletedEvent,
    AgentFailedEvent,
    AgentRequestEvent,
    ConversationalAgentResult,
    CostRecordedEvent,
    EntityLinkage,
    ExplorerAgentResult,
    ExtractorAgentResult,
    GeneratorAgentResult,
    TieredVisionAgentResult,
)
from pydantic import ValidationError

# =============================================================================
# EntityLinkage Tests (5 entity types)
# =============================================================================


class TestEntityLinkage:
    """Tests for EntityLinkage model."""

    def test_farmer_id_only(self) -> None:
        """Test linkage with only farmer_id."""
        linkage = EntityLinkage(farmer_id="farmer-123")
        assert linkage.farmer_id == "farmer-123"
        assert linkage.region_id is None
        assert linkage.group_id is None
        assert linkage.collection_point_id is None
        assert linkage.factory_id is None

    def test_region_id_only(self) -> None:
        """Test linkage with only region_id."""
        linkage = EntityLinkage(region_id="nyeri-highland")
        assert linkage.region_id == "nyeri-highland"
        assert linkage.farmer_id is None

    def test_group_id_only(self) -> None:
        """Test linkage with only group_id."""
        linkage = EntityLinkage(group_id="group-456")
        assert linkage.group_id == "group-456"
        assert linkage.farmer_id is None

    def test_collection_point_id_only(self) -> None:
        """Test linkage with only collection_point_id."""
        linkage = EntityLinkage(collection_point_id="cp-789")
        assert linkage.collection_point_id == "cp-789"
        assert linkage.farmer_id is None

    def test_factory_id_only(self) -> None:
        """Test linkage with only factory_id."""
        linkage = EntityLinkage(factory_id="factory-001")
        assert linkage.factory_id == "factory-001"
        assert linkage.farmer_id is None

    def test_multiple_linkage_fields(self) -> None:
        """Test linkage with multiple fields."""
        linkage = EntityLinkage(
            farmer_id="farmer-123",
            region_id="nyeri-highland",
            factory_id="factory-001",
        )
        assert linkage.farmer_id == "farmer-123"
        assert linkage.region_id == "nyeri-highland"
        assert linkage.factory_id == "factory-001"

    def test_no_linkage_fields_raises_error(self) -> None:
        """Test that empty linkage raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            EntityLinkage()
        assert "At least one linkage field required" in str(exc_info.value)

    def test_all_none_raises_error(self) -> None:
        """Test that all-None linkage raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            EntityLinkage(
                farmer_id=None,
                region_id=None,
                group_id=None,
                collection_point_id=None,
                factory_id=None,
            )
        assert "At least one linkage field required" in str(exc_info.value)


# =============================================================================
# Agent Result Types Tests (5 result types)
# =============================================================================


class TestExtractorAgentResult:
    """Tests for ExtractorAgentResult model."""

    def test_valid_extractor_result(self) -> None:
        """Test valid extractor result."""
        result = ExtractorAgentResult(
            extracted_fields={"name": "John", "phone": "+254700000000"},
            validation_warnings=["Phone format normalized"],
        )
        assert result.result_type == "extractor"
        assert result.extracted_fields["name"] == "John"
        assert len(result.validation_warnings) == 1
        assert result.validation_errors == []
        assert result.normalization_applied is False

    def test_extractor_result_with_normalization(self) -> None:
        """Test extractor result with normalization applied."""
        result = ExtractorAgentResult(
            extracted_fields={"value": 100},
            normalization_applied=True,
        )
        assert result.normalization_applied is True

    def test_extractor_result_with_errors(self) -> None:
        """Test extractor result with validation errors."""
        result = ExtractorAgentResult(
            extracted_fields={},
            validation_errors=["Missing required field: name"],
        )
        assert len(result.validation_errors) == 1


class TestExplorerAgentResult:
    """Tests for ExplorerAgentResult model."""

    def test_valid_explorer_result(self) -> None:
        """Test valid explorer/diagnosis result."""
        result = ExplorerAgentResult(
            diagnosis="Leaf blight detected",
            confidence=0.85,
            severity="high",
            contributing_factors=["Excessive rainfall", "Poor drainage"],
            recommendations=["Apply fungicide", "Improve drainage"],
            rag_sources_used=["doc-001", "doc-002"],
        )
        assert result.result_type == "explorer"
        assert result.diagnosis == "Leaf blight detected"
        assert result.confidence == 0.85
        assert result.severity == "high"
        assert len(result.contributing_factors) == 2

    def test_explorer_result_confidence_bounds(self) -> None:
        """Test confidence bounds enforcement."""
        # Valid bounds
        result = ExplorerAgentResult(
            diagnosis="Test",
            confidence=0.0,
            severity="low",
        )
        assert result.confidence == 0.0

        result = ExplorerAgentResult(
            diagnosis="Test",
            confidence=1.0,
            severity="low",
        )
        assert result.confidence == 1.0

        # Invalid bounds
        with pytest.raises(ValidationError):
            ExplorerAgentResult(
                diagnosis="Test",
                confidence=1.5,  # > 1.0
                severity="low",
            )


class TestGeneratorAgentResult:
    """Tests for GeneratorAgentResult model."""

    def test_valid_generator_result(self) -> None:
        """Test valid generator result."""
        result = GeneratorAgentResult(
            content="Your quality improved by 15% this week!",
            format="sms",
            target_audience="farmer",
            language="sw",
        )
        assert result.result_type == "generator"
        assert result.format == "sms"
        assert result.language == "sw"

    def test_generator_result_formats(self) -> None:
        """Test different output formats."""
        for fmt in ["json", "markdown", "text", "sms", "voice_script"]:
            result = GeneratorAgentResult(
                content="Test content",
                format=fmt,  # type: ignore[arg-type]
            )
            assert result.format == fmt


class TestConversationalAgentResult:
    """Tests for ConversationalAgentResult model."""

    def test_valid_conversational_result(self) -> None:
        """Test valid conversational result."""
        result = ConversationalAgentResult(
            response_text="Hello! How can I help you today?",
            detected_intent="greeting",
            intent_confidence=0.95,
            session_id="session-abc123",
            turn_number=1,
            suggested_actions=["Ask about quality", "Request action plan"],
        )
        assert result.result_type == "conversational"
        assert result.turn_number == 1
        assert len(result.suggested_actions) == 2

    def test_conversational_result_turn_bounds(self) -> None:
        """Test turn_number >= 1 enforcement."""
        with pytest.raises(ValidationError):
            ConversationalAgentResult(
                response_text="Test",
                detected_intent="test",
                intent_confidence=0.5,
                session_id="session-123",
                turn_number=0,  # Invalid - must be >= 1
            )

    def test_conversational_result_intent_confidence_bounds(self) -> None:
        """Test intent_confidence bounds (0.0-1.0) enforcement."""
        # Valid bounds
        result = ConversationalAgentResult(
            response_text="Test",
            detected_intent="test",
            intent_confidence=0.0,
            session_id="session-123",
            turn_number=1,
        )
        assert result.intent_confidence == 0.0

        result = ConversationalAgentResult(
            response_text="Test",
            detected_intent="test",
            intent_confidence=1.0,
            session_id="session-123",
            turn_number=1,
        )
        assert result.intent_confidence == 1.0

        # Invalid: > 1.0
        with pytest.raises(ValidationError):
            ConversationalAgentResult(
                response_text="Test",
                detected_intent="test",
                intent_confidence=1.5,  # Invalid - must be <= 1.0
                session_id="session-123",
                turn_number=1,
            )


class TestTieredVisionAgentResult:
    """Tests for TieredVisionAgentResult model."""

    def test_screen_tier_result(self) -> None:
        """Test result from screen tier (fast check)."""
        result = TieredVisionAgentResult(
            classification="healthy",
            classification_confidence=0.92,
            tier_used="screen",
            cost_saved=True,
        )
        assert result.result_type == "tiered-vision"
        assert result.tier_used == "screen"
        assert result.cost_saved is True
        assert result.diagnosis is None

    def test_diagnose_tier_result(self) -> None:
        """Test result from diagnose tier (detailed analysis)."""
        result = TieredVisionAgentResult(
            classification="diseased",
            classification_confidence=0.78,
            diagnosis="Coffee leaf rust (Hemileia vastatrix)",
            tier_used="diagnose",
            cost_saved=False,
        )
        assert result.tier_used == "diagnose"
        assert result.cost_saved is False
        assert result.diagnosis is not None


# =============================================================================
# Event Envelope Tests (with linkage)
# =============================================================================


class TestAgentRequestEvent:
    """Tests for AgentRequestEvent model."""

    def test_valid_agent_request(self) -> None:
        """Test valid agent request event."""
        event = AgentRequestEvent(
            request_id="req-123",
            agent_id="disease-diagnosis",
            linkage=EntityLinkage(farmer_id="farmer-456"),
            input_data={"symptoms": ["yellow leaves", "brown spots"]},
            source="collection-model",
        )
        assert event.request_id == "req-123"
        assert event.agent_id == "disease-diagnosis"
        assert event.linkage.farmer_id == "farmer-456"
        assert event.context is None

    def test_agent_request_with_context(self) -> None:
        """Test agent request with optional context."""
        event = AgentRequestEvent(
            request_id="req-123",
            agent_id="qc-extractor",
            linkage=EntityLinkage(factory_id="factory-001"),
            input_data={"document": "raw text"},
            context={"session_id": "sess-789"},
            source="collection-model",
        )
        assert event.context is not None
        assert event.context["session_id"] == "sess-789"


class TestAgentCompletedEvent:
    """Tests for AgentCompletedEvent model."""

    def test_completed_event_with_extractor_result(self) -> None:
        """Test completed event with extractor result."""
        event = AgentCompletedEvent(
            request_id="req-123",
            agent_id="qc-extractor",
            linkage=EntityLinkage(farmer_id="farmer-456"),
            result=ExtractorAgentResult(
                extracted_fields={"grade": "A", "weight": 50.5},
            ),
            execution_time_ms=150,
            model_used="anthropic/claude-3-haiku",
            cost_usd=Decimal("0.001"),
        )
        assert event.result.result_type == "extractor"
        assert event.execution_time_ms == 150

    def test_completed_event_with_explorer_result(self) -> None:
        """Test completed event with explorer result."""
        event = AgentCompletedEvent(
            request_id="req-124",
            agent_id="disease-diagnosis",
            linkage=EntityLinkage(region_id="nyeri-highland"),
            result=ExplorerAgentResult(
                diagnosis="Healthy",
                confidence=0.95,
                severity="low",
            ),
            execution_time_ms=500,
            model_used="anthropic/claude-3-sonnet",
        )
        assert event.result.result_type == "explorer"
        assert event.cost_usd is None

    def test_completed_event_with_generator_result(self) -> None:
        """Test completed event with generator result."""
        event = AgentCompletedEvent(
            request_id="req-125",
            agent_id="action-plan-generator",
            linkage=EntityLinkage(farmer_id="farmer-789"),
            result=GeneratorAgentResult(
                content="1. Dry leaves properly\n2. Harvest in morning",
                format="text",
            ),
            execution_time_ms=300,
            model_used="anthropic/claude-3-haiku",
        )
        assert event.result.result_type == "generator"

    def test_completed_event_with_conversational_result(self) -> None:
        """Test completed event with conversational result."""
        event = AgentCompletedEvent(
            request_id="req-126",
            agent_id="farmer-assistant",
            linkage=EntityLinkage(farmer_id="farmer-101"),
            result=ConversationalAgentResult(
                response_text="Your quality score is 85%",
                detected_intent="quality_inquiry",
                intent_confidence=0.9,
                session_id="sess-abc",
                turn_number=3,
            ),
            execution_time_ms=200,
            model_used="anthropic/claude-3-haiku",
        )
        assert event.result.result_type == "conversational"

    def test_completed_event_with_tiered_vision_result(self) -> None:
        """Test completed event with tiered-vision result."""
        event = AgentCompletedEvent(
            request_id="req-127",
            agent_id="image-analyzer",
            linkage=EntityLinkage(collection_point_id="cp-001"),
            result=TieredVisionAgentResult(
                classification="healthy",
                classification_confidence=0.88,
                tier_used="screen",
                cost_saved=True,
            ),
            execution_time_ms=250,
            model_used="anthropic/claude-3-haiku",
        )
        assert event.result.result_type == "tiered-vision"


class TestAgentFailedEvent:
    """Tests for AgentFailedEvent model."""

    def test_valid_failed_event(self) -> None:
        """Test valid failed event."""
        event = AgentFailedEvent(
            request_id="req-128",
            agent_id="disease-diagnosis",
            linkage=EntityLinkage(farmer_id="farmer-456"),
            error_type="llm_error",
            error_message="Rate limit exceeded",
            retry_count=3,
        )
        assert event.error_type == "llm_error"
        assert event.retry_count == 3

    def test_failed_event_validation_error(self) -> None:
        """Test failed event for validation error."""
        event = AgentFailedEvent(
            request_id="req-129",
            agent_id="qc-extractor",
            linkage=EntityLinkage(factory_id="factory-001"),
            error_type="validation",
            error_message="Missing required input_data",
            retry_count=0,
        )
        assert event.error_type == "validation"
        assert event.retry_count == 0

    def test_failed_event_config_not_found(self) -> None:
        """Test failed event for config not found."""
        event = AgentFailedEvent(
            request_id="req-130",
            agent_id="unknown-agent",
            linkage=EntityLinkage(region_id="mombasa-coastal"),
            error_type="config_not_found",
            error_message="Agent config 'unknown-agent' not found",
            retry_count=0,
        )
        assert event.error_type == "config_not_found"


class TestCostRecordedEvent:
    """Tests for CostRecordedEvent model."""

    def test_valid_cost_event(self) -> None:
        """Test valid cost recorded event."""
        event = CostRecordedEvent(
            request_id="req-131",
            agent_id="disease-diagnosis",
            model="anthropic/claude-3-haiku",
            tokens_in=500,
            tokens_out=150,
            cost_usd=Decimal("0.00035"),
        )
        assert event.tokens_in == 500
        assert event.tokens_out == 150
        assert event.cost_usd == Decimal("0.00035")

    def test_cost_event_with_zero_tokens(self) -> None:
        """Test cost event allows zero tokens."""
        event = CostRecordedEvent(
            request_id="req-132",
            agent_id="test-agent",
            model="test/model",
            tokens_in=0,
            tokens_out=0,
            cost_usd=Decimal("0"),
        )
        assert event.tokens_in == 0
        assert event.tokens_out == 0
