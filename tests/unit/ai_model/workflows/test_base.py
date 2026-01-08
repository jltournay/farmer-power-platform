"""Unit tests for base workflow builder.

Tests WorkflowBuilder abstract class and utilities.

Story 0.75.16: LangGraph SDK Integration & Base Workflows
"""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest
from ai_model.workflows.base import (
    WorkflowBuilder,
    WorkflowError,
    create_node_wrapper,
)
from ai_model.workflows.states.extractor import ExtractorState
from langgraph.graph import END, START, StateGraph


class ConcreteWorkflow(WorkflowBuilder[ExtractorState]):
    """Concrete implementation for testing."""

    workflow_name = "test_workflow"
    workflow_version = "1.0.0"

    def _get_state_schema(self) -> type[ExtractorState]:
        return ExtractorState

    def _build_graph(self, builder: StateGraph[ExtractorState]) -> StateGraph[ExtractorState]:
        builder.add_node("test_node", self._test_node)
        builder.add_edge(START, "test_node")
        builder.add_edge("test_node", END)
        return builder

    async def _test_node(self, state: ExtractorState) -> dict[str, Any]:
        return {"success": True, "output": {"result": "done"}}


class TestWorkflowBuilder:
    """Tests for WorkflowBuilder abstract class."""

    def test_initialization(self) -> None:
        """Test workflow builder initialization."""
        workflow = ConcreteWorkflow()

        assert workflow.workflow_name == "test_workflow"
        assert workflow.workflow_version == "1.0.0"
        assert workflow._checkpointer is None

    def test_initialization_with_checkpointer(self) -> None:
        """Test initialization with checkpointer."""
        mock_checkpointer = MagicMock()
        workflow = ConcreteWorkflow(checkpointer=mock_checkpointer)

        assert workflow._checkpointer is mock_checkpointer

    def test_compile_creates_graph(self) -> None:
        """Test that compile() creates a compiled graph."""
        workflow = ConcreteWorkflow()
        graph = workflow.compile()

        assert graph is not None
        # Should be cached
        assert workflow.compile() is graph

    def test_initialize_state(self) -> None:
        """Test state initialization with common fields."""
        workflow = ConcreteWorkflow()

        state = workflow.initialize_state(
            input_data={"doc_id": "123"},
            agent_id="test-agent",
            agent_config={"llm": {"model": "test"}},
            correlation_id="corr-123",
            prompt_template="Test template",
        )

        assert state["input_data"]["doc_id"] == "123"
        assert state["agent_id"] == "test-agent"
        assert state["correlation_id"] == "corr-123"
        assert state["success"] is False
        assert "started_at" in state

    def test_initialize_state_with_kwargs(self) -> None:
        """Test state initialization with extra kwargs."""
        workflow = ConcreteWorkflow()

        state = workflow.initialize_state(
            input_data={},
            agent_id="test",
            agent_config={},
            correlation_id="123",
            custom_field="custom_value",
        )

        assert state.get("custom_field") == "custom_value"

    @pytest.mark.asyncio
    async def test_execute_runs_workflow(self) -> None:
        """Test that execute() runs the compiled workflow."""
        workflow = ConcreteWorkflow()

        initial_state: ExtractorState = {
            "input_data": {"doc_id": "123"},
            "agent_id": "test-agent",
            "agent_config": {},
            "correlation_id": "corr-123",
        }

        result = await workflow.execute(initial_state)

        assert result["success"] is True
        assert "output" in result
        assert "completed_at" in result
        assert "execution_time_ms" in result

    @pytest.mark.asyncio
    async def test_execute_with_thread_id(self) -> None:
        """Test execute with thread ID for checkpointing."""
        workflow = ConcreteWorkflow()

        initial_state: ExtractorState = {
            "input_data": {},
            "agent_id": "test",
            "agent_config": {},
            "correlation_id": "123",
        }

        result = await workflow.execute(
            initial_state,
            thread_id="thread-123",
        )

        assert result["success"] is True


class TestWorkflowError:
    """Tests for WorkflowError exception."""

    def test_basic_error(self) -> None:
        """Test basic error creation."""
        error = WorkflowError("Test error")

        assert str(error) == "Test error"
        assert error.node_name is None
        assert error.cause is None

    def test_error_with_node_name(self) -> None:
        """Test error with node name."""
        error = WorkflowError("Test error", node_name="extract")

        assert error.node_name == "extract"

    def test_error_with_cause(self) -> None:
        """Test error with cause exception."""
        cause = ValueError("Original error")
        error = WorkflowError("Wrapped error", cause=cause)

        assert error.cause is cause

    def test_error_with_all_fields(self) -> None:
        """Test error with all fields."""
        cause = RuntimeError("Root cause")
        error = WorkflowError(
            "Full error",
            node_name="validate",
            cause=cause,
        )

        assert error.node_name == "validate"
        assert error.cause is cause


class TestCreateNodeWrapper:
    """Tests for create_node_wrapper decorator."""

    @pytest.mark.asyncio
    async def test_wrapper_calls_function(self) -> None:
        """Test that wrapper calls the wrapped function."""

        @create_node_wrapper("test_node", "test_workflow")
        async def node_func(state: dict[str, Any]) -> dict[str, Any]:
            return {"result": "success"}

        result = await node_func({"agent_id": "test", "correlation_id": "123"})

        assert result["result"] == "success"

    @pytest.mark.asyncio
    async def test_wrapper_passes_state(self) -> None:
        """Test that wrapper passes state correctly."""
        received_state = None

        @create_node_wrapper("capture_node", "test_workflow")
        async def capture_func(state: dict[str, Any]) -> dict[str, Any]:
            nonlocal received_state
            received_state = state
            return {}

        test_state = {"agent_id": "test", "data": "value"}
        await capture_func(test_state)

        assert received_state is not None
        assert received_state["data"] == "value"

    @pytest.mark.asyncio
    async def test_wrapper_handles_exceptions(self) -> None:
        """Test that wrapper re-raises exceptions."""

        @create_node_wrapper("error_node", "test_workflow")
        async def error_func(state: dict[str, Any]) -> dict[str, Any]:
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await error_func({"agent_id": "test"})


class TestCompileErrors:
    """Tests for compilation error handling."""

    def test_invalid_graph_raises_error(self) -> None:
        """Test that invalid graph definition raises WorkflowError."""

        class InvalidWorkflow(WorkflowBuilder[ExtractorState]):
            workflow_name = "invalid"
            workflow_version = "1.0.0"

            def _get_state_schema(self) -> type[ExtractorState]:
                return ExtractorState

            def _build_graph(self, builder: StateGraph[ExtractorState]) -> StateGraph[ExtractorState]:
                # Invalid: no nodes added
                return builder

        workflow = InvalidWorkflow()

        # LangGraph should raise an error for empty graph
        with pytest.raises(WorkflowError):
            workflow.compile()


class TestExecutionMetrics:
    """Tests for execution metrics recording."""

    @pytest.mark.asyncio
    async def test_execution_records_time(self) -> None:
        """Test that execution time is recorded."""
        workflow = ConcreteWorkflow()

        initial_state: ExtractorState = {
            "input_data": {},
            "agent_id": "test",
            "agent_config": {},
            "correlation_id": "123",
        }

        result = await workflow.execute(initial_state)

        assert "execution_time_ms" in result
        assert isinstance(result["execution_time_ms"], int)
        assert result["execution_time_ms"] >= 0

    @pytest.mark.asyncio
    async def test_execution_records_completion(self) -> None:
        """Test that completion timestamp is recorded."""
        workflow = ConcreteWorkflow()

        initial_state: ExtractorState = {
            "input_data": {},
            "agent_id": "test",
            "agent_config": {},
            "correlation_id": "123",
            "started_at": datetime.now(UTC),
        }

        result = await workflow.execute(initial_state)

        assert "completed_at" in result
        assert isinstance(result["completed_at"], datetime)
