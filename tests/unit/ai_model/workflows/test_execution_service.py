"""Unit tests for Workflow Execution Service.

Tests WorkflowExecutionService factory and execution methods.

Story 0.75.16: LangGraph SDK Integration & Base Workflows
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from ai_model.domain.agent_config import (
    AgentConfigMetadata,
    AgentType,
    ConversationalConfig,
    ExtractorConfig,
    GeneratorConfig,
    InputConfig,
    LLMConfig,
    OutputConfig,
    RAGConfig,
    TieredVisionConfig,
    TieredVisionLLMConfig,
)
from ai_model.workflows.execution_service import (
    WorkflowExecutionError,
    WorkflowExecutionService,
)


@pytest.fixture
def mock_llm_gateway() -> MagicMock:
    """Create a mock LLM gateway."""
    gateway = MagicMock()
    gateway.complete = AsyncMock(
        return_value={
            "content": json.dumps({"result": "success"}),
            "model": "test-model",
            "tokens_in": 100,
            "tokens_out": 50,
        }
    )
    return gateway


@pytest.fixture
def base_input_config() -> InputConfig:
    """Create a test InputConfig."""
    return InputConfig(
        event="test.input.event",
        schema={"type": "object"},
    )


@pytest.fixture
def base_output_config() -> OutputConfig:
    """Create a test OutputConfig."""
    return OutputConfig(
        event="test.output.event",
        schema={"type": "object"},
    )


@pytest.fixture
def base_metadata() -> AgentConfigMetadata:
    """Create a test AgentConfigMetadata."""
    return AgentConfigMetadata(author="test")


@pytest.fixture
def extractor_config(
    base_input_config: InputConfig,
    base_output_config: OutputConfig,
    base_metadata: AgentConfigMetadata,
) -> ExtractorConfig:
    """Create a test ExtractorConfig."""
    return ExtractorConfig(
        id="test-extractor:1.0.0",
        agent_id="test-extractor",
        version="1.0.0",
        description="Test extractor agent",
        input=base_input_config,
        output=base_output_config,
        llm=LLMConfig(model="anthropic/claude-3-haiku"),
        metadata=base_metadata,
        extraction_schema={"type": "object", "properties": {}},
    )


@pytest.fixture
def generator_config(
    base_input_config: InputConfig,
    base_output_config: OutputConfig,
    base_metadata: AgentConfigMetadata,
) -> GeneratorConfig:
    """Create a test GeneratorConfig."""
    return GeneratorConfig(
        id="test-generator:1.0.0",
        agent_id="test-generator",
        version="1.0.0",
        description="Test generator agent",
        input=base_input_config,
        output=base_output_config,
        llm=LLMConfig(model="anthropic/claude-3-sonnet"),
        metadata=base_metadata,
        rag=RAGConfig(knowledge_domains=["knowledge"]),
    )


@pytest.fixture
def conversational_config(
    base_input_config: InputConfig,
    base_output_config: OutputConfig,
    base_metadata: AgentConfigMetadata,
) -> ConversationalConfig:
    """Create a test ConversationalConfig."""
    return ConversationalConfig(
        id="test-conversational:1.0.0",
        agent_id="test-conversational",
        version="1.0.0",
        description="Test conversational agent",
        input=base_input_config,
        output=base_output_config,
        llm=LLMConfig(model="anthropic/claude-3-sonnet"),
        metadata=base_metadata,
        rag=RAGConfig(knowledge_domains=["faq"]),
    )


@pytest.fixture
def tiered_vision_config(
    base_input_config: InputConfig,
    base_output_config: OutputConfig,
    base_metadata: AgentConfigMetadata,
) -> TieredVisionConfig:
    """Create a test TieredVisionConfig."""
    return TieredVisionConfig(
        id="test-vision:1.0.0",
        agent_id="test-vision",
        version="1.0.0",
        description="Test tiered vision agent",
        input=base_input_config,
        output=base_output_config,
        metadata=base_metadata,
        tiered_llm=TieredVisionLLMConfig(
            screen=LLMConfig(model="anthropic/claude-3-haiku"),
            diagnose=LLMConfig(model="anthropic/claude-3-sonnet"),
        ),
        rag=RAGConfig(knowledge_domains=["plant-diseases"]),
    )


@pytest.fixture
def mock_ranking_service() -> MagicMock:
    """Create a mock ranking service."""
    service = MagicMock()
    service.rank = AsyncMock(return_value=MagicMock(matches=[]))
    return service


@pytest.fixture
def execution_service(
    mock_llm_gateway: MagicMock,
    mock_ranking_service: MagicMock,
) -> WorkflowExecutionService:
    """Create a WorkflowExecutionService instance with mocked MongoClient."""
    with patch("ai_model.workflows.execution_service.MongoClient"):
        return WorkflowExecutionService(
            mongodb_uri="mongodb://localhost:27017",
            mongodb_database="test_db",
            llm_gateway=mock_llm_gateway,
            ranking_service=mock_ranking_service,
        )


class TestWorkflowExecutionService:
    """Tests for WorkflowExecutionService."""

    def test_initialization(
        self,
        mock_llm_gateway: MagicMock,
    ) -> None:
        """Test service initialization."""
        with patch("ai_model.workflows.execution_service.MongoClient"):
            service = WorkflowExecutionService(
                mongodb_uri="mongodb://localhost:27017",
                mongodb_database="test_db",
                llm_gateway=mock_llm_gateway,
            )

            assert service._mongodb_database == "test_db"
            assert service._llm_gateway is mock_llm_gateway

    def test_create_workflow_extractor(
        self,
        execution_service: WorkflowExecutionService,
    ) -> None:
        """Test creating extractor workflow."""
        workflow = execution_service._create_workflow(AgentType.EXTRACTOR)

        assert workflow.workflow_name == "extractor"

    def test_create_workflow_explorer(
        self,
        execution_service: WorkflowExecutionService,
    ) -> None:
        """Test creating explorer workflow."""
        workflow = execution_service._create_workflow(AgentType.EXPLORER)

        assert workflow.workflow_name == "explorer"

    def test_create_workflow_generator(
        self,
        execution_service: WorkflowExecutionService,
    ) -> None:
        """Test creating generator workflow."""
        workflow = execution_service._create_workflow(AgentType.GENERATOR)

        assert workflow.workflow_name == "generator"

    def test_create_workflow_conversational(
        self,
        execution_service: WorkflowExecutionService,
    ) -> None:
        """Test creating conversational workflow."""
        workflow = execution_service._create_workflow(AgentType.CONVERSATIONAL)

        assert workflow.workflow_name == "conversational"

    def test_create_workflow_tiered_vision(
        self,
        execution_service: WorkflowExecutionService,
    ) -> None:
        """Test creating tiered-vision workflow."""
        workflow = execution_service._create_workflow(AgentType.TIERED_VISION)

        assert workflow.workflow_name == "tiered_vision"

    def test_create_workflow_from_string(
        self,
        execution_service: WorkflowExecutionService,
    ) -> None:
        """Test creating workflow from string type."""
        workflow = execution_service._create_workflow("extractor")

        assert workflow.workflow_name == "extractor"

    def test_create_workflow_unknown_raises_error(
        self,
        execution_service: WorkflowExecutionService,
    ) -> None:
        """Test that unknown type raises error."""
        with pytest.raises(WorkflowExecutionError, match="Unknown agent type"):
            execution_service._create_workflow("unknown_type")


class TestTypeSpecificState:
    """Tests for type-specific state initialization."""

    def test_generator_state(
        self,
        execution_service: WorkflowExecutionService,
    ) -> None:
        """Test generator-specific state fields."""
        state = execution_service._get_type_specific_state(
            AgentType.GENERATOR,
            session_id=None,
            kwargs={"output_format": "json"},
        )

        assert state["output_format"] == "json"

    def test_generator_state_default_format(
        self,
        execution_service: WorkflowExecutionService,
    ) -> None:
        """Test generator default format."""
        state = execution_service._get_type_specific_state(
            AgentType.GENERATOR,
            session_id=None,
            kwargs={},
        )

        assert state["output_format"] == "markdown"

    def test_conversational_state(
        self,
        execution_service: WorkflowExecutionService,
    ) -> None:
        """Test conversational-specific state fields."""
        state = execution_service._get_type_specific_state(
            AgentType.CONVERSATIONAL,
            session_id="sess-123",
            kwargs={
                "user_message": "Hello",
                "conversation_history": [{"role": "user", "content": "Hi"}],
            },
        )

        assert state["session_id"] == "sess-123"
        assert state["user_message"] == "Hello"
        assert len(state["conversation_history"]) == 1

    def test_tiered_vision_state(
        self,
        execution_service: WorkflowExecutionService,
    ) -> None:
        """Test tiered-vision-specific state fields."""
        state = execution_service._get_type_specific_state(
            AgentType.TIERED_VISION,
            session_id=None,
            kwargs={
                "image_data": "base64data",
                "image_mime_type": "image/png",
            },
        )

        assert state["image_data"] == "base64data"
        assert state["image_mime_type"] == "image/png"

    def test_extractor_state_empty(
        self,
        execution_service: WorkflowExecutionService,
    ) -> None:
        """Test extractor has no type-specific state."""
        state = execution_service._get_type_specific_state(
            AgentType.EXTRACTOR,
            session_id=None,
            kwargs={},
        )

        assert state == {}


class TestExecuteMethods:
    """Tests for execute convenience methods."""

    @pytest.mark.asyncio
    async def test_execute_extractor(
        self,
        execution_service: WorkflowExecutionService,
        extractor_config: ExtractorConfig,
    ) -> None:
        """Test execute_extractor convenience method."""
        with patch.object(
            execution_service,
            "execute",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = {"success": True}

            result = await execution_service.execute_extractor(
                agent_id="test-extractor",
                agent_config=extractor_config,
                input_data={"doc_id": "123"},
            )

            mock_execute.assert_called_once()
            call_kwargs = mock_execute.call_args.kwargs
            assert call_kwargs["agent_type"] == AgentType.EXTRACTOR
            assert call_kwargs["agent_id"] == "test-extractor"

    @pytest.mark.asyncio
    async def test_execute_generator(
        self,
        execution_service: WorkflowExecutionService,
        generator_config: GeneratorConfig,
    ) -> None:
        """Test execute_generator convenience method."""
        with patch.object(
            execution_service,
            "execute",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = {"success": True}

            result = await execution_service.execute_generator(
                agent_id="weekly-plan",
                agent_config=generator_config,
                input_data={"topic": "tea"},
                output_format="json",
            )

            call_kwargs = mock_execute.call_args.kwargs
            assert call_kwargs["agent_type"] == AgentType.GENERATOR
            assert call_kwargs["output_format"] == "json"

    @pytest.mark.asyncio
    async def test_execute_conversational(
        self,
        execution_service: WorkflowExecutionService,
        conversational_config: ConversationalConfig,
    ) -> None:
        """Test execute_conversational convenience method."""
        with patch.object(
            execution_service,
            "execute",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = {"success": True}

            result = await execution_service.execute_conversational(
                agent_id="dialogue",
                agent_config=conversational_config,
                user_message="Hello",
                session_id="sess-123",
            )

            call_kwargs = mock_execute.call_args.kwargs
            assert call_kwargs["agent_type"] == AgentType.CONVERSATIONAL
            assert call_kwargs["user_message"] == "Hello"
            assert call_kwargs["session_id"] == "sess-123"
            assert call_kwargs["use_checkpointer"] is True

    @pytest.mark.asyncio
    async def test_execute_tiered_vision(
        self,
        execution_service: WorkflowExecutionService,
        tiered_vision_config: TieredVisionConfig,
    ) -> None:
        """Test execute_tiered_vision convenience method."""
        with patch.object(
            execution_service,
            "execute",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = {"success": True}

            result = await execution_service.execute_tiered_vision(
                agent_id="leaf-analyzer",
                agent_config=tiered_vision_config,
                image_data="base64data",
                image_mime_type="image/jpeg",
            )

            call_kwargs = mock_execute.call_args.kwargs
            assert call_kwargs["agent_type"] == AgentType.TIERED_VISION
            assert call_kwargs["image_data"] == "base64data"


class TestWorkflowExecutionError:
    """Tests for WorkflowExecutionError exception."""

    def test_basic_error(self) -> None:
        """Test basic error creation."""
        error = WorkflowExecutionError("Test error")

        assert str(error) == "Test error"
        assert error.agent_type is None
        assert error.agent_id is None

    def test_error_with_details(self) -> None:
        """Test error with agent details."""
        error = WorkflowExecutionError(
            "Execution failed",
            agent_type="extractor",
            agent_id="test-agent",
        )

        assert error.agent_type == "extractor"
        assert error.agent_id == "test-agent"

    def test_error_with_cause(self) -> None:
        """Test error with cause exception."""
        cause = ValueError("Root cause")
        error = WorkflowExecutionError(
            "Wrapped error",
            cause=cause,
        )

        assert error.cause is cause
