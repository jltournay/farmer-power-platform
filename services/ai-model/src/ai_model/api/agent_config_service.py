"""AgentConfig gRPC Service - Read-only admin visibility (ADR-019).

Story 9.12a: Implements AgentConfigService gRPC interface for Admin UI queries.
This is a read-only service - write operations are handled by agent-config and prompt-config CLIs.

This module provides:
- AgentConfigServiceServicer: gRPC handler implementation for agent config and prompt queries
"""

import grpc
import structlog
from ai_model.domain.agent_config import AgentConfigStatus, AgentType
from ai_model.domain.prompt import PromptStatus
from ai_model.infrastructure.repositories.agent_config_repository import AgentConfigRepository
from ai_model.infrastructure.repositories.prompt_repository import PromptRepository
from fp_common.converters import (
    agent_config_response_to_proto,
    agent_config_summary_to_proto,
    prompt_summary_to_proto,
)
from fp_proto.ai_model.v1 import ai_model_pb2, ai_model_pb2_grpc
from motor.motor_asyncio import AsyncIOMotorDatabase

__all__ = ["AgentConfigServiceServicer"]

logger = structlog.get_logger(__name__)


class AgentConfigServiceServicer(ai_model_pb2_grpc.AgentConfigServiceServicer):
    """gRPC service implementation for AgentConfig read-only queries (ADR-019).

    This servicer implements 3 query methods:
    - ListAgentConfigs: Paginated list with optional filters (agent_type, status)
    - GetAgentConfig: Single config by agent_id with full JSON and linked prompts
    - ListPromptsByAgent: Prompts for a specific agent with optional status filter

    ADR-019 compliant: Pure query-only, no mutations exposed via gRPC.
    """

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        agent_config_repository: AgentConfigRepository,
        prompt_repository: PromptRepository,
    ) -> None:
        """Initialize the gRPC servicer with repositories.

        Args:
            db: Async MongoDB database connection.
            agent_config_repository: Repository for agent config queries.
            prompt_repository: Repository for prompt queries.
        """
        self._db = db
        self._agent_config_repository = agent_config_repository
        self._prompt_repository = prompt_repository

    async def ListAgentConfigs(
        self,
        request: ai_model_pb2.ListAgentConfigsRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.ListAgentConfigsResponse:
        """List agent configs with optional filters and pagination.

        Args:
            request: Contains pagination params and optional filters
                (agent_type, status).
            context: gRPC context.

        Returns:
            ListAgentConfigsResponse with configs, pagination token, and total count.
        """
        # Default and cap page size
        page_size = min(request.page_size or 20, 100)

        # Handle pagination via skip (page_token is skip count encoded as string)
        skip = 0
        if request.page_token:
            try:
                skip = int(request.page_token)
                if skip < 0:
                    logger.warning(
                        "Negative page_token received, resetting to 0",
                        page_token=request.page_token,
                    )
                    skip = 0
            except ValueError:
                logger.warning(
                    "Invalid page_token format, resetting to 0",
                    page_token=request.page_token,
                )
                skip = 0

        # Convert proto filter to enum
        agent_type = None
        if request.agent_type:
            try:
                agent_type = AgentType(request.agent_type)
            except ValueError:
                logger.warning(
                    "Invalid agent_type filter, ignoring",
                    agent_type=request.agent_type,
                )

        status = None
        if request.status:
            try:
                status = AgentConfigStatus(request.status)
            except ValueError:
                logger.warning(
                    "Invalid status filter, ignoring",
                    status=request.status,
                )

        logger.info(
            "ListAgentConfigs request",
            page_size=page_size,
            page_token=request.page_token or None,
            agent_type=request.agent_type or None,
            status=request.status or None,
        )

        # Get total count for pagination
        total_count = await self._agent_config_repository.count(
            agent_type=agent_type,
            status=status,
        )

        # Fetch one extra to detect if there are more results
        configs = await self._agent_config_repository.list_all(
            page_size=page_size + 1,
            skip=skip,
            agent_type=agent_type,
            status=status,
        )

        # Check if there are more results
        has_more = len(configs) > page_size
        if has_more:
            configs = configs[:page_size]

        # Convert to proto summaries (need prompt_count for each)
        proto_configs = []
        for config in configs:
            prompt_count = await self._prompt_repository.count_by_agent(config.agent_id)
            proto_configs.append(agent_config_summary_to_proto(config, prompt_count))

        # Build next page token
        next_page_token = ""
        if has_more:
            next_page_token = str(skip + page_size)

        return ai_model_pb2.ListAgentConfigsResponse(
            agents=proto_configs,
            next_page_token=next_page_token,
            total_count=total_count,
        )

    async def GetAgentConfig(
        self,
        request: ai_model_pb2.GetAgentConfigRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.AgentConfigResponse:
        """Get a single agent config by ID with full JSON and linked prompts.

        Args:
            request: Contains agent_id and optional version.
            context: gRPC context for setting error codes.

        Returns:
            AgentConfigResponse with full config as JSON and linked prompts.

        Raises:
            INVALID_ARGUMENT if agent_id is empty.
            NOT_FOUND if agent_id doesn't exist.
        """
        if not request.agent_id:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "agent_id is required")
            return ai_model_pb2.AgentConfigResponse()

        logger.info(
            "GetAgentConfig request",
            agent_id=request.agent_id,
            version=request.version or None,
        )

        # Lookup config
        if request.version:
            # Get specific version
            config = await self._agent_config_repository.get_by_version(
                request.agent_id,
                request.version,
            )
        else:
            # Get active version
            config = await self._agent_config_repository.get_active(request.agent_id)

        if config is None:
            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Agent config not found: {request.agent_id}"
                + (f" version {request.version}" if request.version else " (active)"),
            )
            return ai_model_pb2.AgentConfigResponse()

        # Get linked prompts (denormalized for efficiency)
        prompts = await self._prompt_repository.list_by_agent(config.agent_id)

        # Convert to proto response
        return agent_config_response_to_proto(config, prompts)

    async def ListPromptsByAgent(
        self,
        request: ai_model_pb2.ListPromptsByAgentRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.ListPromptsResponse:
        """List prompts for a specific agent.

        Args:
            request: Contains agent_id and optional status filter.
            context: gRPC context.

        Returns:
            ListPromptsResponse with prompt summaries and total count.
        """
        if not request.agent_id:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "agent_id is required")
            return ai_model_pb2.ListPromptsResponse()

        # Convert proto filter to enum
        status = None
        if request.status:
            try:
                status = PromptStatus(request.status)
            except ValueError:
                logger.warning(
                    "Invalid status filter, ignoring",
                    status=request.status,
                )

        logger.info(
            "ListPromptsByAgent request",
            agent_id=request.agent_id,
            status=request.status or None,
        )

        # Get prompts for agent
        prompts = await self._prompt_repository.list_by_agent(
            request.agent_id,
            status=status,
        )

        # Get total count
        total_count = await self._prompt_repository.count_by_agent(
            request.agent_id,
            status=status,
        )

        # Convert to proto summaries
        proto_prompts = [prompt_summary_to_proto(p) for p in prompts]

        return ai_model_pb2.ListPromptsResponse(
            prompts=proto_prompts,
            total_count=total_count,
        )
