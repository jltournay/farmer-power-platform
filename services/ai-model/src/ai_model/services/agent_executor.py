"""Agent Executor - orchestrates agent workflow execution.

Story 0.75.16b: Event Subscriber Workflow Wiring

The AgentExecutor coordinates the complete execution flow:
1. Receive AgentRequestEvent from subscriber
2. Fetch AgentConfig from cache
3. Optionally fetch prompt template from PromptCache
4. Execute workflow via WorkflowExecutionService
5. Build AgentCompletedEvent or AgentFailedEvent from result
6. Publish via EventPublisher

This service bridges the gap between:
- Event subscriber (Story 0.75.8)
- WorkflowExecutionService (Story 0.75.16)
- EventPublisher (Story 0.75.8)
"""

import time
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import structlog
from ai_model.domain.agent_config import AgentConfig, AgentType
from ai_model.workflows.execution_service import WorkflowExecutionError
from fp_common.events import (
    AgentCompletedEvent,
    AgentFailedEvent,
    AgentRequestEvent,
    ConversationalAgentResult,
    ExplorerAgentResult,
    ExtractorAgentResult,
    GeneratorAgentResult,
    TieredVisionAgentResult,
)
from opentelemetry import metrics, trace
from pydantic import TypeAdapter

if TYPE_CHECKING:
    from ai_model.events.publisher import EventPublisher
    from ai_model.services import AgentConfigCache, PromptCache
    from ai_model.workflows.execution_service import WorkflowExecutionService

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter("ai-model")

# Metrics
agent_execution_counter = meter.create_counter(
    name="agent_execution_total",
    description="Total agent executions",
    unit="1",
)
agent_execution_duration = meter.create_histogram(
    name="agent_execution_duration_ms",
    description="Agent execution duration in milliseconds",
    unit="ms",
)
agent_execution_errors = meter.create_counter(
    name="agent_execution_errors_total",
    description="Total agent execution errors",
    unit="1",
)

# TypeAdapter for parsing AgentConfig
_agent_config_adapter = TypeAdapter(AgentConfig)


class AgentExecutionError(Exception):
    """Error during agent execution."""

    def __init__(
        self,
        message: str,
        error_type: str,
        agent_id: str,
        retry_count: int = 0,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.agent_id = agent_id
        self.retry_count = retry_count
        self.cause = cause


class AgentExecutor:
    """Orchestrates agent workflow execution.

    This class coordinates the complete execution flow from receiving
    an AgentRequestEvent to publishing the result event.

    Usage:
        ```python
        executor = AgentExecutor(
            agent_config_cache=cache,
            prompt_cache=prompt_cache,
            workflow_service=workflow_service,
            event_publisher=publisher,
        )

        # Execute and publish result
        await executor.execute_and_publish(request_event)

        # Or execute without publishing (for testing)
        result_event = await executor.execute(request_event)
        ```
    """

    def __init__(
        self,
        agent_config_cache: "AgentConfigCache",
        prompt_cache: "PromptCache",
        workflow_service: "WorkflowExecutionService",
        event_publisher: "EventPublisher",
    ) -> None:
        """Initialize the agent executor.

        Args:
            agent_config_cache: Cache for agent configurations.
            prompt_cache: Cache for prompt templates.
            workflow_service: Service for executing workflows.
            event_publisher: Publisher for result events.
        """
        self._agent_config_cache = agent_config_cache
        self._prompt_cache = prompt_cache
        self._workflow_service = workflow_service
        self._event_publisher = event_publisher

    async def execute_and_publish(
        self,
        request: AgentRequestEvent,
    ) -> AgentCompletedEvent | AgentFailedEvent:
        """Execute agent and publish result event.

        This is the main entry point for the event subscriber.

        Args:
            request: The agent request event.

        Returns:
            The result event (completed or failed).
        """
        result = await self.execute(request)

        # Publish the result
        if isinstance(result, AgentCompletedEvent):
            await self._event_publisher.publish_agent_completed(result)
        else:
            await self._event_publisher.publish_agent_failed(result)

        return result

    async def execute(
        self,
        request: AgentRequestEvent,
    ) -> AgentCompletedEvent | AgentFailedEvent:
        """Execute agent workflow and return result event.

        Does not publish - use execute_and_publish for full flow.

        Args:
            request: The agent request event.

        Returns:
            AgentCompletedEvent on success, AgentFailedEvent on failure.
        """
        with tracer.start_as_current_span(
            "agent_executor.execute",
            attributes={
                "agent.id": request.agent_id,
                "request.id": request.request_id,
                "request.source": request.source,
            },
        ) as span:
            start_time = time.perf_counter()

            try:
                # Step 1: Fetch agent config
                agent_config = await self._get_agent_config(request.agent_id)
                if agent_config is None:
                    return self._build_failed_event(
                        request=request,
                        error_type="config_not_found",
                        error_message=f"Agent config not found: {request.agent_id}",
                        retry_count=0,
                    )

                # Step 2: Get prompt template if configured
                prompt_template = await self._get_prompt_template(agent_config)

                # Step 3: Execute workflow
                workflow_result = await self._execute_workflow(
                    request=request,
                    agent_config=agent_config,
                    prompt_template=prompt_template,
                )

                # Step 4: Build result event
                execution_time_ms = int((time.perf_counter() - start_time) * 1000)

                if workflow_result.get("success", False):
                    result_event = self._build_completed_event(
                        request=request,
                        agent_config=agent_config,
                        workflow_result=workflow_result,
                        execution_time_ms=execution_time_ms,
                    )
                    span.set_attribute("execution.success", True)
                    agent_execution_counter.add(
                        1,
                        {"agent_id": request.agent_id, "status": "success"},
                    )
                else:
                    result_event = self._build_failed_event(
                        request=request,
                        error_type="workflow_failed",
                        error_message=workflow_result.get(
                            "error_message",
                            "Workflow execution failed",
                        ),
                        retry_count=0,
                    )
                    span.set_attribute("execution.success", False)
                    agent_execution_errors.add(
                        1,
                        {"agent_id": request.agent_id, "error_type": "workflow_failed"},
                    )

                agent_execution_duration.record(
                    execution_time_ms,
                    {"agent_id": request.agent_id},
                )

                return result_event

            except AgentExecutionError as e:
                execution_time_ms = int((time.perf_counter() - start_time) * 1000)
                span.set_attribute("execution.success", False)
                span.set_attribute("error.type", e.error_type)
                span.record_exception(e)

                agent_execution_errors.add(
                    1,
                    {"agent_id": request.agent_id, "error_type": e.error_type},
                )
                agent_execution_duration.record(
                    execution_time_ms,
                    {"agent_id": request.agent_id},
                )

                return self._build_failed_event(
                    request=request,
                    error_type=e.error_type,
                    error_message=str(e),
                    retry_count=e.retry_count,
                )

            except Exception as e:
                execution_time_ms = int((time.perf_counter() - start_time) * 1000)
                span.set_attribute("execution.success", False)
                span.set_attribute("error.type", "internal_error")
                span.record_exception(e)

                logger.exception(
                    "Unexpected error in agent execution",
                    agent_id=request.agent_id,
                    request_id=request.request_id,
                )

                agent_execution_errors.add(
                    1,
                    {"agent_id": request.agent_id, "error_type": "internal_error"},
                )
                agent_execution_duration.record(
                    execution_time_ms,
                    {"agent_id": request.agent_id},
                )

                return self._build_failed_event(
                    request=request,
                    error_type="internal_error",
                    error_message=f"Internal error: {e}",
                    retry_count=0,
                )

    async def _get_agent_config(
        self,
        agent_id: str,
    ) -> AgentConfig | None:
        """Fetch agent configuration from cache.

        Args:
            agent_id: The agent configuration ID.

        Returns:
            Parsed AgentConfig or None if not found.
        """
        config_dict = await self._agent_config_cache.get(agent_id)
        if config_dict is None:
            logger.warning("Agent config not found", agent_id=agent_id)
            return None

        try:
            return _agent_config_adapter.validate_python(config_dict)
        except Exception as e:
            logger.error(
                "Failed to parse agent config",
                agent_id=agent_id,
                error=str(e),
            )
            raise AgentExecutionError(
                f"Invalid agent config: {e}",
                error_type="config_invalid",
                agent_id=agent_id,
                cause=e,
            ) from e

    async def _get_prompt_template(
        self,
        agent_config: AgentConfig,
    ) -> str:
        """Fetch prompt template if configured.

        Args:
            agent_config: The agent configuration.

        Returns:
            Prompt template string or empty string.
        """
        # Check if agent has a prompt reference
        # Prompt reference would be stored as metadata or in a field
        # For now, use agent_id as prompt key (convention)
        prompt = await self._prompt_cache.get(agent_config.agent_id)
        if prompt and isinstance(prompt, dict):
            return prompt.get("template", "")
        return ""

    async def _execute_workflow(
        self,
        request: AgentRequestEvent,
        agent_config: AgentConfig,
        prompt_template: str,
    ) -> dict[str, Any]:
        """Execute the workflow for the agent.

        Args:
            request: The agent request event.
            agent_config: The agent configuration.
            prompt_template: Optional prompt template.

        Returns:
            Workflow result dictionary.
        """
        try:
            # Determine agent type
            agent_type = AgentType(agent_config.type)

            # Build workflow-specific kwargs
            kwargs: dict[str, Any] = {}

            # Handle conversational agent
            if agent_type == AgentType.CONVERSATIONAL:
                kwargs["user_message"] = request.input_data.get("message", "")
                kwargs["session_id"] = request.context.get("session_id") if request.context else None
                kwargs["conversation_history"] = (
                    request.context.get("conversation_history", []) if request.context else []
                )

            # Handle tiered-vision agent
            elif agent_type == AgentType.TIERED_VISION:
                kwargs["image_data"] = request.input_data.get("image", "")
                kwargs["image_mime_type"] = request.input_data.get("mime_type", "image/jpeg")

            # Execute workflow
            result = await self._workflow_service.execute(
                agent_type=agent_type,
                agent_id=request.agent_id,
                agent_config=agent_config,
                input_data=request.input_data,
                correlation_id=request.request_id,
                prompt_template=prompt_template,
                **kwargs,
            )

            return result

        except WorkflowExecutionError as e:
            logger.error(
                "Workflow execution failed",
                agent_id=request.agent_id,
                request_id=request.request_id,
                error=str(e),
            )
            raise AgentExecutionError(
                str(e),
                error_type="workflow_error",
                agent_id=request.agent_id,
                cause=e,
            ) from e

    def _build_completed_event(
        self,
        request: AgentRequestEvent,
        agent_config: AgentConfig,
        workflow_result: dict[str, Any],
        execution_time_ms: int,
    ) -> AgentCompletedEvent:
        """Build AgentCompletedEvent from workflow result.

        Args:
            request: Original request event.
            agent_config: Agent configuration.
            workflow_result: Workflow execution result.
            execution_time_ms: Total execution time.

        Returns:
            AgentCompletedEvent with typed result.
        """
        agent_type = AgentType(agent_config.type)

        # Build typed result based on agent type
        result = self._build_typed_result(agent_type, workflow_result)

        # Get cost if available
        cost_usd: Decimal | None = None
        if "cost_usd" in workflow_result:
            cost_usd = Decimal(str(workflow_result["cost_usd"]))

        return AgentCompletedEvent(
            request_id=request.request_id,
            agent_id=request.agent_id,
            linkage=request.linkage,
            result=result,
            execution_time_ms=execution_time_ms,
            model_used=workflow_result.get("model_used", "unknown"),
            cost_usd=cost_usd,
        )

    def _build_typed_result(
        self,
        agent_type: AgentType,
        workflow_result: dict[str, Any],
    ) -> (
        ExtractorAgentResult
        | ExplorerAgentResult
        | GeneratorAgentResult
        | ConversationalAgentResult
        | TieredVisionAgentResult
    ):
        """Build typed result from workflow output.

        Args:
            agent_type: Type of agent.
            workflow_result: Raw workflow result.

        Returns:
            Typed result model.
        """
        output = workflow_result.get("output", {})

        if agent_type == AgentType.EXTRACTOR:
            return ExtractorAgentResult(
                extracted_fields=output,
                validation_warnings=workflow_result.get("validation_warnings", []),
                validation_errors=workflow_result.get("validation_errors", []),
                normalization_applied=bool(workflow_result.get("normalization_applied")),
            )

        elif agent_type == AgentType.EXPLORER:
            return ExplorerAgentResult(
                diagnosis=output.get("diagnosis", ""),
                confidence=output.get("confidence", 0.0),
                severity=output.get("severity", "low"),
                contributing_factors=output.get("contributing_factors", []),
                recommendations=output.get("recommendations", []),
                rag_sources_used=workflow_result.get("rag_sources", []),
            )

        elif agent_type == AgentType.GENERATOR:
            return GeneratorAgentResult(
                content=output.get("content", ""),
                format=output.get("format", "text"),
                target_audience=output.get("target_audience"),
                language=output.get("language", "en"),
            )

        elif agent_type == AgentType.CONVERSATIONAL:
            return ConversationalAgentResult(
                response_text=output.get("response", ""),
                detected_intent=output.get("intent", "unknown"),
                intent_confidence=output.get("intent_confidence", 0.0),
                session_id=workflow_result.get("session_id", ""),
                turn_number=workflow_result.get("turn_number", 1),
                suggested_actions=output.get("suggested_actions", []),
            )

        elif agent_type == AgentType.TIERED_VISION:
            return TieredVisionAgentResult(
                classification=output.get("classification", "unknown"),
                classification_confidence=output.get("confidence", 0.0),
                diagnosis=output.get("diagnosis"),
                tier_used=output.get("tier_used", "screen"),
                cost_saved=output.get("cost_saved", True),
            )

        else:
            # Fallback - should not happen
            logger.warning(
                "Unknown agent type, falling back to extractor result",
                agent_type=str(agent_type),
            )
            return ExtractorAgentResult(
                extracted_fields=output,
            )

    def _build_failed_event(
        self,
        request: AgentRequestEvent,
        error_type: str,
        error_message: str,
        retry_count: int,
    ) -> AgentFailedEvent:
        """Build AgentFailedEvent.

        Args:
            request: Original request event.
            error_type: Error category.
            error_message: Human-readable error message.
            retry_count: Number of retries attempted.

        Returns:
            AgentFailedEvent.
        """
        return AgentFailedEvent(
            request_id=request.request_id,
            agent_id=request.agent_id,
            linkage=request.linkage,
            error_type=error_type,
            error_message=error_message,
            retry_count=retry_count,
        )
