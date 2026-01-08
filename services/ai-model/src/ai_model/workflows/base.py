"""Base workflow builder pattern for LangGraph workflows.

This module provides the abstract base class and utilities for building
LangGraph workflows with consistent patterns for error handling,
telemetry, and state management.

Story 0.75.16: LangGraph SDK Integration & Base Workflows
"""

import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

import structlog
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from opentelemetry import metrics, trace

logger = structlog.get_logger(__name__)

# Type variable for state
StateT = TypeVar("StateT", bound=dict[str, Any])

# OpenTelemetry metrics
meter = metrics.get_meter(__name__)
tracer = trace.get_tracer(__name__)

workflow_execution_duration = meter.create_histogram(
    name="workflow_execution_duration_ms",
    description="Workflow execution duration in milliseconds",
    unit="ms",
)
workflow_execution_counter = meter.create_counter(
    name="workflow_executions_total",
    description="Total workflow executions",
    unit="1",
)
workflow_error_counter = meter.create_counter(
    name="workflow_errors_total",
    description="Total workflow errors",
    unit="1",
)


class WorkflowError(Exception):
    """Base exception for workflow errors."""

    def __init__(
        self,
        message: str,
        node_name: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize workflow error.

        Args:
            message: Error message.
            node_name: Name of the node where error occurred.
            cause: Original exception that caused this error.
        """
        super().__init__(message)
        self.node_name = node_name
        self.cause = cause


class WorkflowBuilder(ABC, Generic[StateT]):
    """Abstract base class for LangGraph workflow builders.

    This class provides a consistent pattern for building workflows:
    1. Define state schema via StateT type parameter
    2. Implement _build_graph() to add nodes and edges
    3. Use compile() to get executable workflow

    Features:
    - Automatic telemetry (metrics + tracing)
    - Consistent error handling
    - Checkpointing support
    - State initialization

    Example:
        ```python
        class ExtractorWorkflow(WorkflowBuilder[ExtractorState]):
            workflow_name = "extractor"

            def _build_graph(self, builder: StateGraph) -> StateGraph:
                builder.add_node("extract", self._extract_node)
                builder.add_node("validate", self._validate_node)
                builder.add_edge(START, "extract")
                builder.add_edge("extract", "validate")
                builder.add_edge("validate", END)
                return builder

            async def _extract_node(self, state: ExtractorState) -> dict:
                # Implementation
                return {"raw_extraction": {...}}
        ```
    """

    workflow_name: str = "base"  # Override in subclasses
    workflow_version: str = "1.0.0"

    def __init__(
        self,
        checkpointer: BaseCheckpointSaver | None = None,
    ) -> None:
        """Initialize the workflow builder.

        Args:
            checkpointer: Optional checkpointer for state persistence.
        """
        self._checkpointer = checkpointer
        self._compiled_graph: CompiledStateGraph | None = None

    @abstractmethod
    def _get_state_schema(self) -> type[StateT]:
        """Return the TypedDict class for this workflow's state.

        Subclasses must implement this to provide their state schema.
        """
        ...

    @abstractmethod
    def _build_graph(self, builder: StateGraph[StateT]) -> StateGraph[StateT]:
        """Build the workflow graph by adding nodes and edges.

        Subclasses must implement this to define their workflow structure.

        Args:
            builder: StateGraph builder initialized with state schema.

        Returns:
            The builder with nodes and edges added.
        """
        ...

    def compile(self) -> CompiledStateGraph:
        """Compile the workflow into an executable graph.

        Returns:
            Compiled LangGraph state graph ready for execution.

        Raises:
            WorkflowError: If compilation fails.
        """
        if self._compiled_graph is not None:
            return self._compiled_graph

        try:
            # Create builder with state schema
            builder = StateGraph(self._get_state_schema())

            # Let subclass build the graph
            builder = self._build_graph(builder)

            # Compile with checkpointer if provided
            self._compiled_graph = builder.compile(
                checkpointer=self._checkpointer,
            )

            logger.info(
                "Workflow compiled",
                workflow_name=self.workflow_name,
                workflow_version=self.workflow_version,
                has_checkpointer=self._checkpointer is not None,
            )

            return self._compiled_graph

        except Exception as e:
            logger.error(
                "Failed to compile workflow",
                workflow_name=self.workflow_name,
                error=str(e),
            )
            raise WorkflowError(
                f"Failed to compile workflow {self.workflow_name}: {e}",
                cause=e,
            ) from e

    def initialize_state(
        self,
        input_data: dict[str, Any],
        agent_id: str,
        agent_config: dict[str, Any],
        correlation_id: str,
        **kwargs: Any,
    ) -> StateT:
        """Initialize workflow state with common fields.

        Provides a standard way to initialize state with required fields.
        Subclasses can override to add workflow-specific initialization.

        Args:
            input_data: Input data for the workflow.
            agent_id: ID of the agent executing the workflow.
            agent_config: Agent configuration.
            correlation_id: Correlation ID for tracing.
            **kwargs: Additional state fields.

        Returns:
            Initialized state dictionary.
        """
        state: dict[str, Any] = {
            "input_data": input_data,
            "agent_id": agent_id,
            "agent_config": agent_config,
            "correlation_id": correlation_id,
            "started_at": datetime.now(UTC),
            "success": False,  # Set to True on successful completion
            **kwargs,
        }
        return state  # type: ignore[return-value]

    async def execute(
        self,
        initial_state: StateT,
        thread_id: str | None = None,
        recursion_limit: int = 25,
    ) -> StateT:
        """Execute the workflow with telemetry and error handling.

        Args:
            initial_state: Initial state for the workflow.
            thread_id: Optional thread ID for checkpointing.
            recursion_limit: Maximum number of node invocations.

        Returns:
            Final state after workflow execution.

        Raises:
            WorkflowError: If execution fails.
        """
        graph = self.compile()

        # Extract agent_id and correlation_id for logging/metrics
        agent_id = initial_state.get("agent_id", "unknown")
        correlation_id = initial_state.get("correlation_id", "unknown")

        config: dict[str, Any] = {
            "recursion_limit": recursion_limit,
        }

        if thread_id:
            config["configurable"] = {"thread_id": thread_id}

        with tracer.start_as_current_span(
            f"workflow.{self.workflow_name}",
            attributes={
                "workflow.name": self.workflow_name,
                "workflow.version": self.workflow_version,
                "agent.id": agent_id,
                "correlation.id": correlation_id,
            },
        ) as span:
            start_time = time.perf_counter()

            try:
                # Execute workflow
                final_state = await graph.ainvoke(
                    initial_state,
                    config=config,
                )

                # Calculate execution time
                execution_time_ms = int((time.perf_counter() - start_time) * 1000)

                # Update state with completion info
                final_state["completed_at"] = datetime.now(UTC)
                final_state["execution_time_ms"] = execution_time_ms

                # Record metrics
                workflow_execution_counter.add(
                    1,
                    {
                        "workflow": self.workflow_name,
                        "agent_id": agent_id,
                        "success": str(final_state.get("success", False)),
                    },
                )
                workflow_execution_duration.record(
                    execution_time_ms,
                    {
                        "workflow": self.workflow_name,
                        "agent_id": agent_id,
                    },
                )

                span.set_attribute("workflow.success", final_state.get("success", False))
                span.set_attribute("workflow.execution_time_ms", execution_time_ms)

                logger.info(
                    "Workflow executed",
                    workflow_name=self.workflow_name,
                    agent_id=agent_id,
                    correlation_id=correlation_id,
                    success=final_state.get("success", False),
                    execution_time_ms=execution_time_ms,
                )

                return final_state

            except Exception as e:
                execution_time_ms = int((time.perf_counter() - start_time) * 1000)

                # Record error metrics
                workflow_error_counter.add(
                    1,
                    {
                        "workflow": self.workflow_name,
                        "agent_id": agent_id,
                        "error_type": type(e).__name__,
                    },
                )

                span.set_attribute("workflow.success", False)
                span.set_attribute("workflow.error", str(e))
                span.record_exception(e)

                logger.error(
                    "Workflow execution failed",
                    workflow_name=self.workflow_name,
                    agent_id=agent_id,
                    correlation_id=correlation_id,
                    error=str(e),
                    execution_time_ms=execution_time_ms,
                )

                raise WorkflowError(
                    f"Workflow {self.workflow_name} failed: {e}",
                    cause=e,
                ) from e


def create_node_wrapper(
    node_name: str,
    workflow_name: str,
) -> Any:
    """Create a decorator that wraps a node function with telemetry.

    This decorator adds:
    - OpenTelemetry span for the node
    - Timing metrics
    - Error handling with consistent logging

    The decorator handles both standalone functions and instance methods.
    For instance methods, it preserves the method descriptor behavior so
    that when used with LangGraph's StateGraph.add_node(), the self
    binding works correctly.

    Args:
        node_name: Name of the node for metrics/tracing.
        workflow_name: Name of the parent workflow.

    Returns:
        Decorator function.

    Example:
        ```python
        class MyWorkflow(WorkflowBuilder):
            @create_node_wrapper("extract", "extractor")
            async def _extract_node(self, state: ExtractorState) -> dict:
                # Implementation - self is preserved
                return {"raw_extraction": {...}}
        ```
    """
    from collections.abc import Callable
    from functools import wraps

    node_tracer = trace.get_tracer(__name__)
    node_duration_histogram = meter.create_histogram(
        name=f"workflow_node_{node_name}_duration_ms",
        description=f"Node {node_name} duration in milliseconds",
        unit="ms",
    )

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
            # Handle both (self, state) and (state,) signatures
            # When used as an instance method, args will be (self, state)
            # When called directly by LangGraph, args will be (state,)
            if len(args) == 2:
                # Instance method call: (self, state)
                instance, state = args
            elif len(args) == 1:
                # Direct call or already bound: (state,)
                instance = None
                state = args[0]
            else:
                raise TypeError(f"Expected 1 or 2 positional arguments, got {len(args)}")

            correlation_id = state.get("correlation_id", "unknown")
            agent_id = state.get("agent_id", "unknown")

            with node_tracer.start_as_current_span(
                f"node.{node_name}",
                attributes={
                    "node.name": node_name,
                    "workflow.name": workflow_name,
                    "agent.id": agent_id,
                    "correlation.id": correlation_id,
                },
            ) as span:
                start_time = time.perf_counter()

                try:
                    # Call the original function with correct arguments
                    if instance is not None:
                        result = await func(instance, state, **kwargs)
                    else:
                        result = await func(state, **kwargs)

                    duration_ms = int((time.perf_counter() - start_time) * 1000)
                    node_duration_histogram.record(
                        duration_ms,
                        {"workflow": workflow_name, "node": node_name},
                    )

                    span.set_attribute("node.success", True)
                    span.set_attribute("node.duration_ms", duration_ms)

                    return result

                except Exception as e:
                    duration_ms = int((time.perf_counter() - start_time) * 1000)

                    span.set_attribute("node.success", False)
                    span.set_attribute("node.error", str(e))
                    span.record_exception(e)

                    logger.error(
                        "Node execution failed",
                        node_name=node_name,
                        workflow_name=workflow_name,
                        agent_id=agent_id,
                        error=str(e),
                        duration_ms=duration_ms,
                    )
                    raise

        return wrapper

    return decorator
