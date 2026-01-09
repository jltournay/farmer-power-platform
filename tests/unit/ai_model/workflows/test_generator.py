"""Unit tests for Generator workflow.

Tests GeneratorWorkflow implementation with mocked LLM gateway and ranking service.

Story 0.75.16: LangGraph SDK Integration & Base Workflows
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from ai_model.domain.agent_config import (
    AgentConfigMetadata,
    GeneratorConfig,
    InputConfig,
    LLMConfig,
    OutputConfig,
    RAGConfig,
)
from ai_model.workflows.generator import GeneratorWorkflow
from ai_model.workflows.states.generator import GeneratorState


@pytest.fixture
def mock_llm_gateway() -> MagicMock:
    """Create a mock LLM gateway."""
    gateway = MagicMock()
    gateway.complete = AsyncMock(
        return_value={
            "content": "# Weekly Tea Plan\n\nThis is a generated plan.",
            "model": "anthropic/claude-3-5-sonnet",
            "tokens_in": 200,
            "tokens_out": 150,
        }
    )
    return gateway


@pytest.fixture
def mock_ranking_service() -> MagicMock:
    """Create a mock ranking service."""
    service = MagicMock()
    mock_match = MagicMock()
    mock_match.content = "Tea farming best practices"
    mock_match.title = "Tea Guide"
    mock_match.domain = "tea"
    mock_match.rerank_score = 0.95

    service.rank = AsyncMock(return_value=MagicMock(matches=[mock_match]))
    return service


@pytest.fixture
def generator_workflow(mock_llm_gateway: MagicMock) -> GeneratorWorkflow:
    """Create a GeneratorWorkflow instance without ranking."""
    return GeneratorWorkflow(llm_gateway=mock_llm_gateway)


@pytest.fixture
def generator_workflow_with_rag(
    mock_llm_gateway: MagicMock,
    mock_ranking_service: MagicMock,
) -> GeneratorWorkflow:
    """Create a GeneratorWorkflow instance with ranking."""
    return GeneratorWorkflow(
        llm_gateway=mock_llm_gateway,
        ranking_service=mock_ranking_service,
    )


@pytest.fixture
def generator_config() -> GeneratorConfig:
    """Create a test GeneratorConfig."""
    return GeneratorConfig(
        id="test-generator:1.0.0",
        agent_id="test-generator",
        version="1.0.0",
        description="Test generator agent",
        input=InputConfig(event="test.input", schema={"type": "object"}),
        output=OutputConfig(event="test.output", schema={"type": "object"}),
        llm=LLMConfig(model="anthropic/claude-3-5-sonnet", temperature=0.5),
        metadata=AgentConfigMetadata(author="test"),
        rag=RAGConfig(enabled=True, knowledge_domains=["tea"]),
    )


@pytest.fixture
def generator_config_rag_disabled() -> GeneratorConfig:
    """Create a test GeneratorConfig with RAG disabled."""
    return GeneratorConfig(
        id="test-generator:1.0.0",
        agent_id="test-generator",
        version="1.0.0",
        description="Test generator agent",
        input=InputConfig(event="test.input", schema={"type": "object"}),
        output=OutputConfig(event="test.output", schema={"type": "object"}),
        llm=LLMConfig(model="anthropic/claude-3-5-sonnet", temperature=0.5),
        metadata=AgentConfigMetadata(author="test"),
        rag=RAGConfig(enabled=False, knowledge_domains=[]),
    )


class TestGeneratorWorkflow:
    """Tests for GeneratorWorkflow."""

    def test_workflow_properties(self, generator_workflow: GeneratorWorkflow) -> None:
        """Test workflow name and version."""
        assert generator_workflow.workflow_name == "generator"
        assert generator_workflow.workflow_version == "1.0.0"

    def test_compiles_successfully(self, generator_workflow: GeneratorWorkflow) -> None:
        """Test that workflow compiles without errors."""
        graph = generator_workflow.compile()
        assert graph is not None

    def test_state_schema(self, generator_workflow: GeneratorWorkflow) -> None:
        """Test workflow returns correct state schema."""
        schema = generator_workflow._get_state_schema()
        assert schema == GeneratorState

    @pytest.mark.asyncio
    async def test_execute_markdown_generation(
        self,
        generator_workflow: GeneratorWorkflow,
        generator_config: GeneratorConfig,
        mock_llm_gateway: MagicMock,
    ) -> None:
        """Test successful markdown generation."""
        initial_state: GeneratorState = {
            "input_data": {"topic": "tea cultivation", "request": "create weekly plan"},
            "agent_id": "weekly-plan-generator",
            "agent_config": generator_config,
            "prompt_template": "Generate a {{topic}} plan",
            "correlation_id": "corr-456",
            "output_format": "markdown",
        }

        result = await generator_workflow.execute(initial_state)

        assert result["success"] is True
        assert "Weekly Tea Plan" in result["output"]["content"]
        assert result["output"]["format"] == "markdown"
        assert mock_llm_gateway.complete.called

    @pytest.mark.asyncio
    async def test_execute_json_generation(
        self,
        generator_workflow: GeneratorWorkflow,
        generator_config: GeneratorConfig,
        mock_llm_gateway: MagicMock,
    ) -> None:
        """Test successful JSON generation."""
        mock_llm_gateway.complete.return_value = {
            "content": json.dumps({"plan": "weekly", "tasks": ["task1", "task2"]}),
            "model": "test-model",
            "tokens_in": 100,
            "tokens_out": 80,
        }

        initial_state: GeneratorState = {
            "input_data": {"topic": "tea"},
            "agent_id": "json-generator",
            "agent_config": generator_config,
            "prompt_template": "",
            "correlation_id": "corr-789",
            "output_format": "json",
        }

        result = await generator_workflow.execute(initial_state)

        assert result["success"] is True
        assert result["output"]["format"] == "json"
        assert result["output"]["content"]["plan"] == "weekly"

    @pytest.mark.asyncio
    async def test_execute_text_generation(
        self,
        generator_workflow: GeneratorWorkflow,
        generator_config: GeneratorConfig,
        mock_llm_gateway: MagicMock,
    ) -> None:
        """Test successful text generation."""
        mock_llm_gateway.complete.return_value = {
            "content": "Simple text output",
            "model": "test-model",
            "tokens_in": 50,
            "tokens_out": 20,
        }

        initial_state: GeneratorState = {
            "input_data": {"message": "greet"},
            "agent_id": "text-generator",
            "agent_config": generator_config,
            "prompt_template": "",
            "correlation_id": "corr-text",
            "output_format": "text",
        }

        result = await generator_workflow.execute(initial_state)

        assert result["success"] is True
        assert result["output"]["format"] == "text"
        assert result["output"]["content"] == "Simple text output"

    @pytest.mark.asyncio
    async def test_execute_with_rag_context(
        self,
        generator_workflow_with_rag: GeneratorWorkflow,
        generator_config: GeneratorConfig,
        mock_llm_gateway: MagicMock,
        mock_ranking_service: MagicMock,
    ) -> None:
        """Test generation with RAG context retrieval."""
        initial_state: GeneratorState = {
            "input_data": {"topic": "pest control"},
            "agent_id": "rag-generator",
            "agent_config": generator_config,
            "prompt_template": "",
            "correlation_id": "corr-rag",
            "output_format": "markdown",
        }

        result = await generator_workflow_with_rag.execute(initial_state)

        assert result["success"] is True
        assert mock_ranking_service.rank.called
        assert result["output"]["metadata"]["rag_sources_used"] == 1

    @pytest.mark.asyncio
    async def test_execute_with_rag_disabled(
        self,
        generator_workflow_with_rag: GeneratorWorkflow,
        generator_config_rag_disabled: GeneratorConfig,
        mock_ranking_service: MagicMock,
    ) -> None:
        """Test generation with RAG explicitly disabled."""
        initial_state: GeneratorState = {
            "input_data": {"topic": "simple"},
            "agent_id": "no-rag",
            "agent_config": generator_config_rag_disabled,
            "prompt_template": "",
            "correlation_id": "corr-no-rag",
            "output_format": "text",
        }

        result = await generator_workflow_with_rag.execute(initial_state)

        assert result["success"] is True
        assert not mock_ranking_service.rank.called
        assert result["output"]["metadata"]["rag_sources_used"] == 0

    @pytest.mark.asyncio
    async def test_execute_llm_failure(
        self,
        generator_workflow: GeneratorWorkflow,
        generator_config: GeneratorConfig,
        mock_llm_gateway: MagicMock,
    ) -> None:
        """Test handling of LLM failure."""
        mock_llm_gateway.complete.side_effect = Exception("LLM API error")

        initial_state: GeneratorState = {
            "input_data": {"topic": "test"},
            "agent_id": "fail-test",
            "agent_config": generator_config,
            "prompt_template": "",
            "correlation_id": "corr-fail",
            "output_format": "markdown",
        }

        result = await generator_workflow.execute(initial_state)

        assert result["success"] is False
        assert result["error_message"] == "LLM API error"


class TestGeneratorHelpers:
    """Tests for Generator helper methods."""

    def test_render_template(self, generator_workflow: GeneratorWorkflow) -> None:
        """Test template rendering."""
        template = "Hello {{name}}, your topic is {{topic}}"
        data = {"name": "John", "topic": "farming"}

        result = generator_workflow._render_template(template, data)

        assert result == "Hello John, your topic is farming"

    def test_render_template_missing_placeholder(
        self,
        generator_workflow: GeneratorWorkflow,
    ) -> None:
        """Test template rendering with missing placeholder."""
        template = "Hello {{name}}, welcome!"
        data = {"other": "value"}

        result = generator_workflow._render_template(template, data)

        # Missing placeholders are left unchanged
        assert result == "Hello {{name}}, welcome!"

    def test_build_generation_query(
        self,
        generator_workflow: GeneratorWorkflow,
    ) -> None:
        """Test generation query building from input data."""
        input_data = {"topic": "tea farming", "description": "best practices"}

        result = generator_workflow._build_generation_query(input_data)

        assert "tea farming" in result
        assert "best practices" in result

    def test_format_as_json_with_code_block(
        self,
        generator_workflow: GeneratorWorkflow,
    ) -> None:
        """Test JSON formatting removes code block wrappers."""
        content = '```json\n{"key": "value"}\n```'

        result = generator_workflow._format_as_json(content)

        assert result == {"key": "value"}

    def test_format_as_markdown_with_code_block(
        self,
        generator_workflow: GeneratorWorkflow,
    ) -> None:
        """Test markdown formatting removes code block wrappers."""
        content = "```markdown\n# Title\n\nContent\n```"

        result = generator_workflow._format_as_markdown(content)

        assert result == "# Title\n\nContent"

    def test_build_generation_system_prompt_json(
        self,
        generator_workflow: GeneratorWorkflow,
    ) -> None:
        """Test system prompt for JSON output."""
        result = generator_workflow._build_generation_system_prompt("json")

        assert "JSON" in result
        assert "valid JSON only" in result

    def test_build_generation_system_prompt_markdown(
        self,
        generator_workflow: GeneratorWorkflow,
    ) -> None:
        """Test system prompt for markdown output."""
        result = generator_workflow._build_generation_system_prompt("markdown")

        assert "Markdown" in result
        assert "headers" in result
