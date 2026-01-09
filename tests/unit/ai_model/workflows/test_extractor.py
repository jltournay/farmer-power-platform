"""Unit tests for Extractor workflow.

Tests ExtractorWorkflow implementation with mocked LLM gateway.

Story 0.75.16: LangGraph SDK Integration & Base Workflows
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from ai_model.domain.agent_config import (
    AgentConfigMetadata,
    ExtractorConfig,
    InputConfig,
    LLMConfig,
    OutputConfig,
)
from ai_model.workflows.extractor import ExtractorWorkflow
from ai_model.workflows.states.extractor import ExtractorState


@pytest.fixture
def mock_llm_gateway() -> MagicMock:
    """Create a mock LLM gateway."""
    gateway = MagicMock()
    gateway.complete = AsyncMock(
        return_value={
            "content": json.dumps({"farmer_id": "F123", "grade": "A"}),
            "model": "anthropic/claude-3-5-sonnet",
            "tokens_in": 100,
            "tokens_out": 50,
        }
    )
    return gateway


@pytest.fixture
def extractor_workflow(mock_llm_gateway: MagicMock) -> ExtractorWorkflow:
    """Create an ExtractorWorkflow instance."""
    return ExtractorWorkflow(llm_gateway=mock_llm_gateway)


@pytest.fixture
def extractor_config() -> ExtractorConfig:
    """Create a test ExtractorConfig."""
    return ExtractorConfig(
        id="test-extractor:1.0.0",
        agent_id="test-extractor",
        version="1.0.0",
        description="Test extractor agent",
        input=InputConfig(event="test.input", schema={"type": "object"}),
        output=OutputConfig(event="test.output", schema={"type": "object"}),
        llm=LLMConfig(model="anthropic/claude-3-5-sonnet", temperature=0.1),
        metadata=AgentConfigMetadata(author="test"),
        extraction_schema={
            "required_fields": ["farmer_id", "grade"],
            "optional_fields": ["notes"],
        },
    )


class TestExtractorWorkflow:
    """Tests for ExtractorWorkflow."""

    def test_workflow_properties(self, extractor_workflow: ExtractorWorkflow) -> None:
        """Test workflow name and version."""
        assert extractor_workflow.workflow_name == "extractor"
        assert extractor_workflow.workflow_version == "1.0.0"

    def test_compiles_successfully(self, extractor_workflow: ExtractorWorkflow) -> None:
        """Test that workflow compiles without errors."""
        graph = extractor_workflow.compile()
        assert graph is not None

    @pytest.mark.asyncio
    async def test_execute_successful_extraction(
        self,
        extractor_workflow: ExtractorWorkflow,
        extractor_config: ExtractorConfig,
        mock_llm_gateway: MagicMock,
    ) -> None:
        """Test successful extraction flow."""
        initial_state: ExtractorState = {
            "input_data": {"doc_id": "123", "content": "Test document content"},
            "agent_id": "qc-extractor",
            "agent_config": extractor_config,
            "prompt_template": "Extract from: {{content}}",
            "correlation_id": "corr-123",
        }

        result = await extractor_workflow.execute(initial_state)

        assert result["success"] is True
        assert result["output"]["farmer_id"] == "F123"
        assert result["output"]["grade"] == "A"
        assert mock_llm_gateway.complete.called

    @pytest.mark.asyncio
    async def test_execute_with_validation_errors(
        self,
        extractor_workflow: ExtractorWorkflow,
        extractor_config: ExtractorConfig,
        mock_llm_gateway: MagicMock,
    ) -> None:
        """Test extraction with validation errors."""
        # Return incomplete data missing required field
        mock_llm_gateway.complete.return_value = {
            "content": json.dumps({"farmer_id": "F123"}),  # Missing "grade"
            "model": "test",
            "tokens_in": 50,
            "tokens_out": 25,
        }

        initial_state: ExtractorState = {
            "input_data": {"content": "test"},
            "agent_id": "test-extractor",
            "agent_config": extractor_config,
            "correlation_id": "corr-123",
        }

        result = await extractor_workflow.execute(initial_state)

        # Should fail due to missing required field
        assert result["success"] is False
        assert "grade" in result.get("error_message", "").lower()

    @pytest.mark.asyncio
    async def test_execute_with_empty_input(
        self,
        extractor_workflow: ExtractorWorkflow,
        extractor_config: ExtractorConfig,
    ) -> None:
        """Test extraction with empty input data."""
        initial_state: ExtractorState = {
            "input_data": {},
            "agent_id": "test-extractor",
            "agent_config": extractor_config,
            "correlation_id": "corr-123",
        }

        result = await extractor_workflow.execute(initial_state)

        assert result["success"] is False
        assert "no input" in result.get("error_message", "").lower()


class TestExtractorHelpers:
    """Tests for ExtractorWorkflow helper methods."""

    @pytest.fixture
    def workflow(self, mock_llm_gateway: MagicMock) -> ExtractorWorkflow:
        return ExtractorWorkflow(llm_gateway=mock_llm_gateway)

    def test_build_system_prompt(self, workflow: ExtractorWorkflow) -> None:
        """Test system prompt generation."""
        schema = {
            "required_fields": ["farmer_id", "grade"],
            "optional_fields": ["notes"],
        }

        prompt = workflow._build_system_prompt(schema)

        assert "farmer_id" in prompt
        assert "grade" in prompt
        assert "notes" in prompt
        assert "Required" in prompt
        assert "Optional" in prompt

    def test_build_user_prompt_with_template(self, workflow: ExtractorWorkflow) -> None:
        """Test user prompt with template substitution."""
        template = "Extract from: {{content}}"
        data = {"content": "Test data here"}

        prompt = workflow._build_user_prompt(template, data)

        assert "Test data here" in prompt
        assert "{{content}}" not in prompt

    def test_build_user_prompt_without_template(self, workflow: ExtractorWorkflow) -> None:
        """Test user prompt without template (JSON dump)."""
        data = {"doc_id": "123", "text": "content"}

        prompt = workflow._build_user_prompt("", data)

        assert "123" in prompt
        assert "content" in prompt

    def test_parse_json_response_clean(self, workflow: ExtractorWorkflow) -> None:
        """Test parsing clean JSON response."""
        content = '{"field1": "value1", "field2": 42}'

        result = workflow._parse_json_response(content)

        assert result["field1"] == "value1"
        assert result["field2"] == 42

    def test_parse_json_response_with_markdown(self, workflow: ExtractorWorkflow) -> None:
        """Test parsing JSON wrapped in markdown code blocks."""
        content = '```json\n{"field": "value"}\n```'

        result = workflow._parse_json_response(content)

        assert result["field"] == "value"

    def test_parse_json_response_invalid(self, workflow: ExtractorWorkflow) -> None:
        """Test parsing invalid JSON returns empty dict."""
        content = "Not valid JSON at all"

        result = workflow._parse_json_response(content)

        assert result == {}

    def test_validate_type_string(self, workflow: ExtractorWorkflow) -> None:
        """Test type validation for strings."""
        assert workflow._validate_type("hello", "string") is True
        assert workflow._validate_type(123, "string") is False

    def test_validate_type_number(self, workflow: ExtractorWorkflow) -> None:
        """Test type validation for numbers."""
        assert workflow._validate_type(123, "int") is True
        assert workflow._validate_type(123.45, "float") is True
        assert workflow._validate_type(123, "number") is True
        assert workflow._validate_type("123", "int") is False

    def test_validate_type_boolean(self, workflow: ExtractorWorkflow) -> None:
        """Test type validation for booleans."""
        assert workflow._validate_type(True, "bool") is True
        assert workflow._validate_type(False, "boolean") is True
        assert workflow._validate_type(1, "bool") is False

    def test_validate_type_list(self, workflow: ExtractorWorkflow) -> None:
        """Test type validation for lists."""
        assert workflow._validate_type([1, 2, 3], "list") is True
        assert workflow._validate_type([], "array") is True
        assert workflow._validate_type("list", "list") is False

    def test_validate_type_unknown(self, workflow: ExtractorWorkflow) -> None:
        """Test type validation for unknown types passes."""
        assert workflow._validate_type("anything", "unknown_type") is True

    def test_apply_transform_uppercase(self, workflow: ExtractorWorkflow) -> None:
        """Test uppercase transformation."""
        result = workflow._apply_transform("hello", "uppercase")
        assert result == "HELLO"

    def test_apply_transform_lowercase(self, workflow: ExtractorWorkflow) -> None:
        """Test lowercase transformation."""
        result = workflow._apply_transform("HELLO", "lowercase")
        assert result == "hello"

    def test_apply_transform_strip(self, workflow: ExtractorWorkflow) -> None:
        """Test strip transformation."""
        result = workflow._apply_transform("  hello  ", "strip")
        assert result == "hello"

    def test_apply_transform_title(self, workflow: ExtractorWorkflow) -> None:
        """Test title transformation."""
        result = workflow._apply_transform("hello world", "title")
        assert result == "Hello World"

    def test_apply_transform_non_string(self, workflow: ExtractorWorkflow) -> None:
        """Test transformation on non-string returns unchanged."""
        result = workflow._apply_transform(123, "uppercase")
        assert result == 123

    def test_apply_transform_unknown(self, workflow: ExtractorWorkflow) -> None:
        """Test unknown transformation returns unchanged."""
        result = workflow._apply_transform("hello", "unknown")
        assert result == "hello"
