"""Agent Config gRPC client for BFF.

Story 9.12b: Agent Config gRPC Client + REST API in BFF

Provides typed access to AI Model's AgentConfigService via DAPR service invocation.
Implements list and get operations for agent configurations and prompts.

Per ADR-002 §"Service Invocation Pattern", ADR-005 for retry logic,
and ADR-012 for response wrappers (list methods return PaginatedResponse).
"""

import grpc
import grpc.aio
from bff.api.schemas import PaginatedResponse
from bff.infrastructure.clients.base import (
    BaseGrpcClient,
    grpc_retry,
)
from fp_common.converters import (
    agent_config_detail_from_proto,
    agent_config_summary_from_proto,
    prompt_detail_from_proto,
    prompt_summary_from_proto,
)
from fp_common.models import (
    AgentConfigDetail,
    AgentConfigSummary,
    PromptDetail,
    PromptSummary,
)
from fp_proto.ai_model.v1 import ai_model_pb2, ai_model_pb2_grpc


class AgentConfigClient(BaseGrpcClient):
    """gRPC client for AI Model's AgentConfigService.

    Provides typed access to agent configuration operations via DAPR service invocation.
    All methods return Pydantic domain models (NOT dict[str, Any]).

    Example:
        >>> client = AgentConfigClient()
        >>> configs = await client.list_agent_configs(page_size=10)
        >>> assert isinstance(configs, PaginatedResponse)
        >>> assert isinstance(configs.data[0], AgentConfigSummary)

        >>> # With direct connection for testing
        >>> client = AgentConfigClient(direct_host="localhost:50051")
        >>> detail = await client.get_agent_config("disease-diagnosis")
        >>> assert isinstance(detail, AgentConfigDetail)
    """

    def __init__(
        self,
        dapr_grpc_port: int = 50001,
        direct_host: str | None = None,
        channel: grpc.aio.Channel | None = None,
    ) -> None:
        """Initialize the AgentConfigClient.

        Args:
            dapr_grpc_port: Port for DAPR sidecar gRPC endpoint (default: 50001).
            direct_host: Optional direct host for testing (e.g., "localhost:50051").
                        If provided, DAPR routing is bypassed.
            channel: Optional pre-configured channel for testing.
        """
        super().__init__(
            target_app_id="ai-model",
            dapr_grpc_port=dapr_grpc_port,
            direct_host=direct_host,
            channel=channel,
        )

    # =========================================================================
    # Agent Config Query Methods
    # =========================================================================

    @grpc_retry
    async def list_agent_configs(
        self,
        page_size: int = 20,
        page_token: str | None = None,
        agent_type: str | None = None,
        status: str | None = None,
    ) -> PaginatedResponse[AgentConfigSummary]:
        """List agent configurations with pagination and optional filters.

        Args:
            page_size: Maximum number of configs to return (max 100, default 20).
            page_token: Pagination cursor from previous response.
            agent_type: Filter by agent type (extractor, explorer, generator, conversational, tiered-vision).
            status: Filter by status (draft, staged, active, archived).

        Returns:
            PaginatedResponse containing AgentConfigSummary items with pagination metadata.

        Raises:
            ServiceUnavailableError: If the AI Model service is unavailable.
        """
        stub = await self._get_stub(ai_model_pb2_grpc.AgentConfigServiceStub)
        effective_page_size = max(1, min(page_size, 100))

        request = ai_model_pb2.ListAgentConfigsRequest(
            page_size=effective_page_size,
            page_token=page_token or "",
            agent_type=agent_type or "",
            status=status or "",
        )

        try:
            response = await stub.ListAgentConfigs(request, metadata=self._get_metadata())
            configs = [agent_config_summary_from_proto(cfg) for cfg in response.agents]
            next_token = response.next_page_token if response.next_page_token else None

            return PaginatedResponse.from_client_response(
                items=configs,
                total_count=response.total_count,
                page_size=effective_page_size,
                next_page_token=next_token,
            )
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "List agent configs")
            raise  # For type checker, _handle_grpc_error always raises

    @grpc_retry
    async def get_agent_config(
        self,
        agent_id: str,
        version: str | None = None,
    ) -> AgentConfigDetail:
        """Get agent configuration detail by ID.

        Args:
            agent_id: The agent configuration ID (e.g., "disease-diagnosis").
            version: Optional specific version to retrieve (default: active version).

        Returns:
            AgentConfigDetail with full configuration including config_json and linked prompts.

        Raises:
            NotFoundError: If the agent configuration is not found.
            ServiceUnavailableError: If the AI Model service is unavailable.
        """
        stub = await self._get_stub(ai_model_pb2_grpc.AgentConfigServiceStub)

        request = ai_model_pb2.GetAgentConfigRequest(
            agent_id=agent_id,
            version=version or "",
        )

        try:
            response = await stub.GetAgentConfig(request, metadata=self._get_metadata())
            return agent_config_detail_from_proto(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Agent config {agent_id}")
            raise  # For type checker, _handle_grpc_error always raises

    @grpc_retry
    async def list_prompts_by_agent(
        self,
        agent_id: str,
        status: str | None = None,
    ) -> list[PromptSummary]:
        """List prompts linked to a specific agent.

        Args:
            agent_id: The agent ID to get prompts for.
            status: Optional filter by prompt status (draft, staged, active, archived).

        Returns:
            List of PromptSummary objects linked to the agent.

        Raises:
            NotFoundError: If the agent is not found.
            ServiceUnavailableError: If the AI Model service is unavailable.
        """
        stub = await self._get_stub(ai_model_pb2_grpc.AgentConfigServiceStub)

        request = ai_model_pb2.ListPromptsByAgentRequest(
            agent_id=agent_id,
            status=status or "",
        )

        try:
            response = await stub.ListPromptsByAgent(request, metadata=self._get_metadata())
            return [prompt_summary_from_proto(p) for p in response.prompts]
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Prompts for agent {agent_id}")
            raise  # For type checker, _handle_grpc_error always raises

    @grpc_retry
    async def get_prompt(
        self,
        prompt_id: str,
        version: str | None = None,
    ) -> PromptDetail:
        """Get full prompt detail including content (Story 9.12c - AC 9.12c.4).

        Args:
            prompt_id: The prompt ID (e.g., "disease-diagnosis-main").
            version: Optional specific version to retrieve (default: active version).

        Returns:
            PromptDetail with all content fields (system_prompt, template, output_schema, etc.).

        Raises:
            NotFoundError: If the prompt is not found.
            ServiceUnavailableError: If the AI Model service is unavailable.
        """
        stub = await self._get_stub(ai_model_pb2_grpc.AgentConfigServiceStub)

        request = ai_model_pb2.GetPromptRequest(
            prompt_id=prompt_id,
            version=version or "",
        )

        try:
            response = await stub.GetPrompt(request, metadata=self._get_metadata())
            return prompt_detail_from_proto(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Prompt {prompt_id}")
            raise  # For type checker, _handle_grpc_error always raises
