"""Workflow Execution Service for running LangGraph workflows.

This service provides a unified interface for executing any workflow type
with proper initialization, checkpointing, and error handling.

Story 0.75.16: LangGraph SDK Integration & Base Workflows
Story 0.75.16b: Refactored to accept Pydantic AgentConfig models for type safety
"""

import uuid
from typing import Any

import structlog
from ai_model.domain.agent_config import (
    AgentConfig,
    AgentType,
    ConversationalConfig,
    ExplorerConfig,
    ExtractorConfig,
    GeneratorConfig,
    TieredVisionConfig,
)
from ai_model.workflows.checkpointer import create_mongodb_checkpointer
from ai_model.workflows.conversational import ConversationalWorkflow
from ai_model.workflows.explorer import ExplorerWorkflow
from ai_model.workflows.extractor import ExtractorWorkflow
from ai_model.workflows.generator import GeneratorWorkflow
from ai_model.workflows.tiered_vision import TieredVisionWorkflow
from pydantic import TypeAdapter
from pymongo import MongoClient

logger = structlog.get_logger(__name__)

# TypeAdapter for parsing AgentConfig from dict
_agent_config_adapter = TypeAdapter(AgentConfig)


class WorkflowExecutionError(Exception):
    """Error during workflow execution."""

    def __init__(
        self,
        message: str,
        agent_type: str | None = None,
        agent_id: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.agent_type = agent_type
        self.agent_id = agent_id
        self.cause = cause


class WorkflowExecutionService:
    """Service for executing LangGraph workflows.

    This service provides:
    - Workflow factory by agent type
    - MongoDB checkpointer integration (using PyMongo for langgraph compatibility)
    - Unified execution interface
    - Proper state initialization

    Note:
        langgraph-checkpoint-mongodb requires PyMongo (sync), not Motor (async).
        This service creates its own PyMongo client for checkpointing.

    Usage:
        ```python
        service = WorkflowExecutionService(
            mongodb_uri="mongodb://localhost:27017",
            mongodb_database="ai_model",
            llm_gateway=llm_gateway,
            ranking_service=ranking_service,
        )

        result = await service.execute(
            agent_type=AgentType.EXTRACTOR,
            agent_id="qc-extractor",
            agent_config=config,
            input_data={"doc_id": "123"},
        )
        ```
    """

    def __init__(
        self,
        mongodb_uri: str,
        mongodb_database: str,
        llm_gateway: Any,  # LLMGateway
        ranking_service: Any | None = None,  # RankingService
        mcp_integration: Any | None = None,  # MCPIntegration
        tool_provider: Any | None = None,  # AgentToolProvider (Story 0.75.16b)
        checkpoint_ttl_seconds: int = 1800,  # 30 minutes
    ) -> None:
        """Initialize the workflow execution service.

        Args:
            mongodb_uri: MongoDB connection string.
            mongodb_database: Database name for checkpoints.
            llm_gateway: LLM gateway for all workflows.
            ranking_service: Optional ranking service for RAG workflows.
            mcp_integration: Optional MCP integration for context.
            tool_provider: Optional AgentToolProvider for resolving agent tools.
            checkpoint_ttl_seconds: TTL for checkpoints (default 30 min).
        """
        # Create PyMongo client for checkpointer (langgraph requires sync client)
        self._pymongo_client: MongoClient[Any] = MongoClient(mongodb_uri)
        self._mongodb_database = mongodb_database
        self._llm_gateway = llm_gateway
        self._ranking_service = ranking_service
        self._mcp_integration = mcp_integration
        self._tool_provider = tool_provider
        self._checkpoint_ttl_seconds = checkpoint_ttl_seconds
        self._checkpointer: Any | None = None

    def _get_checkpointer(self) -> Any:
        """Get or create the MongoDB checkpointer.

        Note: This is sync because langgraph-checkpoint-mongodb uses PyMongo (sync).
        """
        if self._checkpointer is None:
            self._checkpointer = create_mongodb_checkpointer(
                client=self._pymongo_client,
                database=self._mongodb_database,
                ttl_seconds=self._checkpoint_ttl_seconds,
            )
        return self._checkpointer

    def _create_workflow(
        self,
        agent_type: AgentType | str,
        use_checkpointer: bool = False,
        checkpointer: Any = None,
    ) -> Any:
        """Create a workflow instance for the given agent type.

        Args:
            agent_type: Type of agent/workflow to create.
            use_checkpointer: Whether to enable checkpointing.
            checkpointer: Optional pre-created checkpointer.

        Returns:
            Workflow instance.

        Raises:
            WorkflowExecutionError: If agent type is unknown.
        """
        if isinstance(agent_type, str):
            try:
                agent_type = AgentType(agent_type)
            except ValueError:
                raise WorkflowExecutionError(f"Unknown agent type: {agent_type}")

        cp = checkpointer if use_checkpointer else None

        if agent_type == AgentType.EXTRACTOR:
            return ExtractorWorkflow(
                llm_gateway=self._llm_gateway,
                checkpointer=cp,
            )
        elif agent_type == AgentType.EXPLORER:
            return ExplorerWorkflow(
                llm_gateway=self._llm_gateway,
                ranking_service=self._ranking_service,
                mcp_integration=self._mcp_integration,
                checkpointer=cp,
            )
        elif agent_type == AgentType.GENERATOR:
            return GeneratorWorkflow(
                llm_gateway=self._llm_gateway,
                ranking_service=self._ranking_service,
                mcp_integration=self._mcp_integration,
                checkpointer=cp,
            )
        elif agent_type == AgentType.CONVERSATIONAL:
            return ConversationalWorkflow(
                llm_gateway=self._llm_gateway,
                ranking_service=self._ranking_service,
                checkpointer=cp,
            )
        elif agent_type == AgentType.TIERED_VISION:
            return TieredVisionWorkflow(
                llm_gateway=self._llm_gateway,
                ranking_service=self._ranking_service,
                checkpointer=cp,
            )
        else:
            raise WorkflowExecutionError(f"Unknown agent type: {agent_type}")

    async def execute(
        self,
        agent_type: AgentType | str,
        agent_id: str,
        agent_config: AgentConfig,
        input_data: dict[str, Any],
        correlation_id: str | None = None,
        prompt_template: str = "",
        session_id: str | None = None,
        use_checkpointer: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a workflow with proper initialization.

        Args:
            agent_type: Type of workflow to execute.
            agent_id: ID of the agent being executed.
            agent_config: Agent configuration (typed Pydantic model).
            input_data: Input data for the workflow.
            correlation_id: Optional correlation ID for tracing.
            prompt_template: Optional prompt template.
            session_id: Optional session ID for conversational workflows.
            use_checkpointer: Whether to use MongoDB checkpointing.
            **kwargs: Additional workflow-specific arguments.

        Returns:
            Final workflow state dictionary.

        Raises:
            WorkflowExecutionError: If execution fails.

        Note:
            Story 0.75.16b: agent_config MUST be a typed Pydantic model for type safety.
        """
        correlation_id = correlation_id or str(uuid.uuid4())

        logger.info(
            "Executing workflow",
            agent_type=str(agent_type),
            agent_id=agent_id,
            correlation_id=correlation_id,
            use_checkpointer=use_checkpointer,
        )

        try:
            # Get checkpointer if needed (sync - langgraph uses PyMongo)
            checkpointer = self._get_checkpointer() if use_checkpointer else None

            # Create workflow
            workflow = self._create_workflow(
                agent_type=agent_type,
                use_checkpointer=use_checkpointer,
                checkpointer=checkpointer,
            )

            # Initialize state with workflow-specific fields
            # Note: Pass Pydantic model directly for type safety
            initial_state = workflow.initialize_state(
                input_data=input_data,
                agent_id=agent_id,
                agent_config=agent_config,
                correlation_id=correlation_id,
                prompt_template=prompt_template,
                **self._get_type_specific_state(agent_type, session_id, kwargs),
            )

            # Execute workflow
            thread_id = session_id or correlation_id if use_checkpointer else None
            final_state = await workflow.execute(
                initial_state=initial_state,
                thread_id=thread_id,
            )

            logger.info(
                "Workflow execution completed",
                agent_type=str(agent_type),
                agent_id=agent_id,
                correlation_id=correlation_id,
                success=final_state.get("success", False),
                execution_time_ms=final_state.get("execution_time_ms", 0),
            )

            return final_state

        except Exception as e:
            logger.error(
                "Workflow execution failed",
                agent_type=str(agent_type),
                agent_id=agent_id,
                correlation_id=correlation_id,
                error=str(e),
            )
            raise WorkflowExecutionError(
                f"Failed to execute {agent_type} workflow: {e}",
                agent_type=str(agent_type),
                agent_id=agent_id,
                cause=e,
            ) from e

    def _get_type_specific_state(
        self,
        agent_type: AgentType | str,
        session_id: str | None,
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """Get type-specific initial state fields.

        Args:
            agent_type: Type of agent/workflow.
            session_id: Optional session ID.
            kwargs: Additional arguments.

        Returns:
            Dictionary of type-specific state fields.
        """
        if isinstance(agent_type, str):
            try:
                agent_type = AgentType(agent_type)
            except ValueError:
                return {}

        if agent_type == AgentType.GENERATOR:
            return {
                "output_format": kwargs.get("output_format", "markdown"),
            }
        elif agent_type == AgentType.CONVERSATIONAL:
            return {
                "session_id": session_id or str(uuid.uuid4()),
                "user_message": kwargs.get("user_message", ""),
                "conversation_history": kwargs.get("conversation_history", []),
            }
        elif agent_type == AgentType.TIERED_VISION:
            return {
                "image_data": kwargs.get("image_data", ""),
                "image_url": kwargs.get("image_url"),
                "image_mime_type": kwargs.get("image_mime_type", "image/jpeg"),
            }

        return {}

    async def execute_extractor(
        self,
        agent_id: str,
        agent_config: ExtractorConfig,
        input_data: dict[str, Any],
        prompt_template: str = "",
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Convenience method to execute an extractor workflow.

        Args:
            agent_id: ID of the extractor agent.
            agent_config: Agent configuration (ExtractorConfig or dict).
            input_data: Data to extract from.
            prompt_template: Optional prompt template.
            correlation_id: Optional correlation ID.

        Returns:
            Final workflow state.
        """
        return await self.execute(
            agent_type=AgentType.EXTRACTOR,
            agent_id=agent_id,
            agent_config=agent_config,
            input_data=input_data,
            prompt_template=prompt_template,
            correlation_id=correlation_id,
        )

    async def execute_explorer(
        self,
        agent_id: str,
        agent_config: ExplorerConfig,
        input_data: dict[str, Any],
        prompt_template: str = "",
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Convenience method to execute an explorer workflow.

        Args:
            agent_id: ID of the explorer agent.
            agent_config: Agent configuration (ExplorerConfig or dict).
            input_data: Data to analyze.
            prompt_template: Optional prompt template.
            correlation_id: Optional correlation ID.

        Returns:
            Final workflow state.
        """
        return await self.execute(
            agent_type=AgentType.EXPLORER,
            agent_id=agent_id,
            agent_config=agent_config,
            input_data=input_data,
            prompt_template=prompt_template,
            correlation_id=correlation_id,
        )

    async def execute_generator(
        self,
        agent_id: str,
        agent_config: GeneratorConfig,
        input_data: dict[str, Any],
        output_format: str = "markdown",
        prompt_template: str = "",
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Convenience method to execute a generator workflow.

        Args:
            agent_id: ID of the generator agent.
            agent_config: Agent configuration (GeneratorConfig or dict).
            input_data: Generation request data.
            output_format: Output format (json/markdown/text).
            prompt_template: Optional prompt template.
            correlation_id: Optional correlation ID.

        Returns:
            Final workflow state.
        """
        return await self.execute(
            agent_type=AgentType.GENERATOR,
            agent_id=agent_id,
            agent_config=agent_config,
            input_data=input_data,
            prompt_template=prompt_template,
            correlation_id=correlation_id,
            output_format=output_format,
        )

    async def execute_conversational(
        self,
        agent_id: str,
        agent_config: ConversationalConfig,
        user_message: str,
        session_id: str | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Convenience method to execute a conversational workflow.

        Args:
            agent_id: ID of the conversational agent.
            agent_config: Agent configuration (ConversationalConfig or dict).
            user_message: User's message.
            session_id: Session ID for continuity.
            conversation_history: Previous conversation turns.
            correlation_id: Optional correlation ID.

        Returns:
            Final workflow state.
        """
        return await self.execute(
            agent_type=AgentType.CONVERSATIONAL,
            agent_id=agent_id,
            agent_config=agent_config,
            input_data={"message": user_message},
            correlation_id=correlation_id,
            session_id=session_id,
            use_checkpointer=True,
            user_message=user_message,
            conversation_history=conversation_history or [],
        )

    async def execute_tiered_vision(
        self,
        agent_id: str,
        agent_config: TieredVisionConfig,
        image_data: str,
        image_mime_type: str = "image/jpeg",
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Convenience method to execute a tiered-vision workflow.

        Args:
            agent_id: ID of the tiered-vision agent.
            agent_config: Agent configuration (TieredVisionConfig or dict).
            image_data: Base64-encoded image data.
            image_mime_type: MIME type of the image.
            correlation_id: Optional correlation ID.

        Returns:
            Final workflow state.
        """
        return await self.execute(
            agent_type=AgentType.TIERED_VISION,
            agent_id=agent_id,
            agent_config=agent_config,
            input_data={"image": image_data},
            correlation_id=correlation_id,
            image_data=image_data,
            image_mime_type=image_mime_type,
        )
