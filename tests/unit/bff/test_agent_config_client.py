"""Unit tests for AgentConfigClient.

Story 9.12b: Tests for agent config gRPC client methods,
DAPR service invocation, error handling, and proto conversion.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from bff.infrastructure.clients.agent_config_client import AgentConfigClient
from bff.infrastructure.clients.base import NotFoundError, ServiceUnavailableError
from fp_common.models import AgentConfigDetail, AgentConfigSummary, PromptSummary
from fp_proto.ai_model.v1 import ai_model_pb2, ai_model_pb2_grpc
from google.protobuf.timestamp_pb2 import Timestamp


def _datetime_to_timestamp(dt: datetime) -> Timestamp:
    """Convert datetime to proto Timestamp."""
    ts = Timestamp()
    ts.FromDatetime(dt)
    return ts


def create_agent_config_summary_proto(
    agent_id: str = "disease-diagnosis",
    version: str = "1.0.0",
    agent_type: str = "explorer",
    status: str = "active",
    description: str = "Diagnoses plant diseases from quality events",
    model: str = "claude-3-5-sonnet",
    prompt_count: int = 2,
    updated_at: datetime | None = None,
) -> ai_model_pb2.AgentConfigSummary:
    """Create an AgentConfigSummary proto message for testing."""
    if updated_at is None:
        updated_at = datetime.now(UTC)

    return ai_model_pb2.AgentConfigSummary(
        agent_id=agent_id,
        version=version,
        agent_type=agent_type,
        status=status,
        description=description,
        model=model,
        prompt_count=prompt_count,
        updated_at=_datetime_to_timestamp(updated_at),
    )


def create_prompt_summary_proto(
    id: str = "disease-diagnosis:1.0.0",
    prompt_id: str = "disease-diagnosis",
    agent_id: str = "disease-diagnosis",
    version: str = "1.0.0",
    status: str = "active",
    author: str = "admin",
    updated_at: datetime | None = None,
) -> ai_model_pb2.PromptSummary:
    """Create a PromptSummary proto message for testing."""
    if updated_at is None:
        updated_at = datetime.now(UTC)

    return ai_model_pb2.PromptSummary(
        id=id,
        prompt_id=prompt_id,
        agent_id=agent_id,
        version=version,
        status=status,
        author=author,
        updated_at=_datetime_to_timestamp(updated_at),
    )


def create_agent_config_response_proto(
    agent_id: str = "disease-diagnosis",
    version: str = "1.0.0",
    agent_type: str = "explorer",
    status: str = "active",
    description: str = "Diagnoses plant diseases from quality events",
    config_json: str = '{"agent_id": "disease-diagnosis"}',
    prompts: list[ai_model_pb2.PromptSummary] | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> ai_model_pb2.AgentConfigResponse:
    """Create an AgentConfigResponse proto message for testing."""
    now = datetime.now(UTC)
    if created_at is None:
        created_at = now
    if updated_at is None:
        updated_at = now
    if prompts is None:
        prompts = [create_prompt_summary_proto()]

    return ai_model_pb2.AgentConfigResponse(
        agent_id=agent_id,
        version=version,
        agent_type=agent_type,
        status=status,
        description=description,
        config_json=config_json,
        prompts=prompts,
        created_at=_datetime_to_timestamp(created_at),
        updated_at=_datetime_to_timestamp(updated_at),
    )


@pytest.fixture
def mock_agent_config_stub() -> MagicMock:
    """Create a mock AgentConfigService stub."""
    stub = MagicMock()
    stub.ListAgentConfigs = AsyncMock()
    stub.GetAgentConfig = AsyncMock()
    stub.ListPromptsByAgent = AsyncMock()
    return stub


@pytest.fixture
def agent_config_client_with_mock_stub(
    mock_agent_config_stub: MagicMock,
) -> tuple[AgentConfigClient, MagicMock]:
    """Create an AgentConfigClient with a mocked stub."""
    client = AgentConfigClient(direct_host="localhost:50051")
    # Inject the mock stub
    client._stubs[ai_model_pb2_grpc.AgentConfigServiceStub] = mock_agent_config_stub
    return client, mock_agent_config_stub


class TestAgentConfigClientInit:
    """Tests for AgentConfigClient initialization."""

    def test_default_init(self) -> None:
        """Test default initialization with DAPR settings."""
        client = AgentConfigClient()
        assert client._target_app_id == "ai-model"
        assert client._dapr_grpc_port == 50001
        assert client._direct_host is None
        assert client._channel is None

    def test_direct_host_init(self) -> None:
        """Test initialization with direct host."""
        client = AgentConfigClient(direct_host="localhost:50051")
        assert client._direct_host == "localhost:50051"

    def test_custom_dapr_port(self) -> None:
        """Test initialization with custom DAPR port."""
        client = AgentConfigClient(dapr_grpc_port=50099)
        assert client._dapr_grpc_port == 50099


class TestAgentConfigClientMetadata:
    """Tests for gRPC metadata handling."""

    def test_metadata_with_dapr(self) -> None:
        """Test metadata generation with DAPR routing."""
        client = AgentConfigClient()
        metadata = client._get_metadata()
        assert ("dapr-app-id", "ai-model") in metadata

    def test_metadata_direct_connection(self) -> None:
        """Test metadata is empty for direct connection."""
        client = AgentConfigClient(direct_host="localhost:50051")
        metadata = client._get_metadata()
        assert metadata == []


class TestListAgentConfigs:
    """Tests for list_agent_configs method."""

    @pytest.mark.asyncio
    async def test_list_agent_configs_success(
        self,
        agent_config_client_with_mock_stub: tuple[AgentConfigClient, MagicMock],
    ) -> None:
        """Test successful agent config listing returns PaginatedResponse."""
        client, stub = agent_config_client_with_mock_stub
        response = ai_model_pb2.ListAgentConfigsResponse(
            agents=[
                create_agent_config_summary_proto(agent_id="agent-001"),
                create_agent_config_summary_proto(agent_id="agent-002"),
            ],
            next_page_token="token123",
            total_count=100,
        )
        stub.ListAgentConfigs.return_value = response

        result = await client.list_agent_configs()

        assert len(result.data) == 2
        assert all(isinstance(cfg, AgentConfigSummary) for cfg in result.data)
        assert result.data[0].agent_id == "agent-001"
        assert result.data[1].agent_id == "agent-002"
        assert result.pagination.next_page_token == "token123"
        assert result.pagination.total_count == 100
        assert result.pagination.has_next is True

    @pytest.mark.asyncio
    async def test_list_agent_configs_with_pagination(
        self,
        agent_config_client_with_mock_stub: tuple[AgentConfigClient, MagicMock],
    ) -> None:
        """Test agent config listing with pagination parameters."""
        client, stub = agent_config_client_with_mock_stub
        response = ai_model_pb2.ListAgentConfigsResponse(
            agents=[create_agent_config_summary_proto()],
            next_page_token="",
            total_count=1,
        )
        stub.ListAgentConfigs.return_value = response

        result = await client.list_agent_configs(
            page_size=10,
            page_token="prev_token",
        )

        call_args = stub.ListAgentConfigs.call_args
        request = call_args[0][0]
        assert request.page_size == 10
        assert request.page_token == "prev_token"
        assert result.pagination.next_page_token is None
        assert result.pagination.has_next is False

    @pytest.mark.asyncio
    async def test_list_agent_configs_with_agent_type_filter(
        self,
        agent_config_client_with_mock_stub: tuple[AgentConfigClient, MagicMock],
    ) -> None:
        """Test agent config listing with agent_type filter."""
        client, stub = agent_config_client_with_mock_stub
        response = ai_model_pb2.ListAgentConfigsResponse(
            agents=[create_agent_config_summary_proto(agent_type="explorer")],
            next_page_token="",
            total_count=1,
        )
        stub.ListAgentConfigs.return_value = response

        await client.list_agent_configs(agent_type="explorer")

        call_args = stub.ListAgentConfigs.call_args
        request = call_args[0][0]
        assert request.agent_type == "explorer"

    @pytest.mark.asyncio
    async def test_list_agent_configs_with_status_filter(
        self,
        agent_config_client_with_mock_stub: tuple[AgentConfigClient, MagicMock],
    ) -> None:
        """Test agent config listing with status filter."""
        client, stub = agent_config_client_with_mock_stub
        response = ai_model_pb2.ListAgentConfigsResponse(
            agents=[create_agent_config_summary_proto(status="active")],
            next_page_token="",
            total_count=1,
        )
        stub.ListAgentConfigs.return_value = response

        await client.list_agent_configs(status="active")

        call_args = stub.ListAgentConfigs.call_args
        request = call_args[0][0]
        assert request.status == "active"

    @pytest.mark.asyncio
    async def test_list_agent_configs_page_size_capped(
        self,
        agent_config_client_with_mock_stub: tuple[AgentConfigClient, MagicMock],
    ) -> None:
        """Test page_size is capped at 100 in request and response."""
        client, stub = agent_config_client_with_mock_stub
        response = ai_model_pb2.ListAgentConfigsResponse(
            agents=[],
            next_page_token="",
            total_count=0,
        )
        stub.ListAgentConfigs.return_value = response

        result = await client.list_agent_configs(page_size=200)

        call_args = stub.ListAgentConfigs.call_args
        request = call_args[0][0]
        assert request.page_size == 100
        assert result.pagination.page_size == 100

    @pytest.mark.asyncio
    async def test_list_agent_configs_empty_result(
        self,
        agent_config_client_with_mock_stub: tuple[AgentConfigClient, MagicMock],
    ) -> None:
        """Test agent config listing with no results."""
        client, stub = agent_config_client_with_mock_stub
        response = ai_model_pb2.ListAgentConfigsResponse(
            agents=[],
            next_page_token="",
            total_count=0,
        )
        stub.ListAgentConfigs.return_value = response

        result = await client.list_agent_configs()

        assert len(result.data) == 0
        assert result.pagination.total_count == 0


class TestGetAgentConfig:
    """Tests for get_agent_config method."""

    @pytest.mark.asyncio
    async def test_get_agent_config_success(
        self,
        agent_config_client_with_mock_stub: tuple[AgentConfigClient, MagicMock],
    ) -> None:
        """Test successful agent config retrieval."""
        client, stub = agent_config_client_with_mock_stub
        stub.GetAgentConfig.return_value = create_agent_config_response_proto(
            agent_id="disease-diagnosis",
            description="Diagnoses plant diseases",
            config_json='{"agent_id": "disease-diagnosis", "type": "explorer"}',
        )

        result = await client.get_agent_config("disease-diagnosis")

        assert isinstance(result, AgentConfigDetail)
        assert result.agent_id == "disease-diagnosis"
        assert result.description == "Diagnoses plant diseases"
        assert result.config_json == '{"agent_id": "disease-diagnosis", "type": "explorer"}'
        assert result.created_at is not None
        assert result.updated_at is not None
        assert len(result.prompts) == 1
        assert isinstance(result.prompts[0], PromptSummary)

    @pytest.mark.asyncio
    async def test_get_agent_config_with_version(
        self,
        agent_config_client_with_mock_stub: tuple[AgentConfigClient, MagicMock],
    ) -> None:
        """Test agent config retrieval with specific version."""
        client, stub = agent_config_client_with_mock_stub
        stub.GetAgentConfig.return_value = create_agent_config_response_proto(
            agent_id="disease-diagnosis",
            version="2.0.0",
        )

        await client.get_agent_config("disease-diagnosis", version="2.0.0")

        call_args = stub.GetAgentConfig.call_args
        request = call_args[0][0]
        assert request.agent_id == "disease-diagnosis"
        assert request.version == "2.0.0"

    @pytest.mark.asyncio
    async def test_get_agent_config_not_found(
        self,
        agent_config_client_with_mock_stub: tuple[AgentConfigClient, MagicMock],
    ) -> None:
        """Test agent config not found error."""
        client, stub = agent_config_client_with_mock_stub
        error = grpc.aio.AioRpcError(
            code=grpc.StatusCode.NOT_FOUND,
            initial_metadata=None,
            trailing_metadata=None,
            details="Agent config not found",
            debug_error_string="",
        )
        stub.GetAgentConfig.side_effect = error

        with pytest.raises(NotFoundError, match="Agent config nonexistent not found"):
            await client.get_agent_config("nonexistent")

    @pytest.mark.asyncio
    async def test_get_agent_config_request_params(
        self,
        agent_config_client_with_mock_stub: tuple[AgentConfigClient, MagicMock],
    ) -> None:
        """Test get_agent_config sends correct request parameters."""
        client, stub = agent_config_client_with_mock_stub
        stub.GetAgentConfig.return_value = create_agent_config_response_proto()

        await client.get_agent_config("my-agent")

        call_args = stub.GetAgentConfig.call_args
        request = call_args[0][0]
        assert request.agent_id == "my-agent"


class TestListPromptsByAgent:
    """Tests for list_prompts_by_agent method."""

    @pytest.mark.asyncio
    async def test_list_prompts_by_agent_success(
        self,
        agent_config_client_with_mock_stub: tuple[AgentConfigClient, MagicMock],
    ) -> None:
        """Test successful prompt listing for an agent."""
        client, stub = agent_config_client_with_mock_stub
        response = ai_model_pb2.ListPromptsResponse(
            prompts=[
                create_prompt_summary_proto(id="prompt-001:1.0.0", prompt_id="prompt-001"),
                create_prompt_summary_proto(id="prompt-002:1.0.0", prompt_id="prompt-002"),
            ],
            total_count=2,
        )
        stub.ListPromptsByAgent.return_value = response

        result = await client.list_prompts_by_agent("disease-diagnosis")

        assert len(result) == 2
        assert all(isinstance(p, PromptSummary) for p in result)
        assert result[0].prompt_id == "prompt-001"
        assert result[1].prompt_id == "prompt-002"

    @pytest.mark.asyncio
    async def test_list_prompts_by_agent_with_status_filter(
        self,
        agent_config_client_with_mock_stub: tuple[AgentConfigClient, MagicMock],
    ) -> None:
        """Test prompt listing with status filter."""
        client, stub = agent_config_client_with_mock_stub
        response = ai_model_pb2.ListPromptsResponse(
            prompts=[create_prompt_summary_proto(status="active")],
            total_count=1,
        )
        stub.ListPromptsByAgent.return_value = response

        await client.list_prompts_by_agent("disease-diagnosis", status="active")

        call_args = stub.ListPromptsByAgent.call_args
        request = call_args[0][0]
        assert request.agent_id == "disease-diagnosis"
        assert request.status == "active"

    @pytest.mark.asyncio
    async def test_list_prompts_by_agent_empty_result(
        self,
        agent_config_client_with_mock_stub: tuple[AgentConfigClient, MagicMock],
    ) -> None:
        """Test prompt listing with no results."""
        client, stub = agent_config_client_with_mock_stub
        response = ai_model_pb2.ListPromptsResponse(
            prompts=[],
            total_count=0,
        )
        stub.ListPromptsByAgent.return_value = response

        result = await client.list_prompts_by_agent("disease-diagnosis")

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_list_prompts_by_agent_not_found(
        self,
        agent_config_client_with_mock_stub: tuple[AgentConfigClient, MagicMock],
    ) -> None:
        """Test agent not found error when listing prompts."""
        client, stub = agent_config_client_with_mock_stub
        error = grpc.aio.AioRpcError(
            code=grpc.StatusCode.NOT_FOUND,
            initial_metadata=None,
            trailing_metadata=None,
            details="Agent not found",
            debug_error_string="",
        )
        stub.ListPromptsByAgent.side_effect = error

        with pytest.raises(NotFoundError, match="Prompts for agent nonexistent not found"):
            await client.list_prompts_by_agent("nonexistent")


class TestErrorHandling:
    """Tests for error handling and retry logic."""

    @pytest.mark.asyncio
    async def test_service_unavailable_error_on_list(
        self,
        agent_config_client_with_mock_stub: tuple[AgentConfigClient, MagicMock],
    ) -> None:
        """Test service unavailable error handling on list."""
        client, stub = agent_config_client_with_mock_stub
        error = grpc.aio.AioRpcError(
            code=grpc.StatusCode.UNAVAILABLE,
            initial_metadata=None,
            trailing_metadata=None,
            details="Connection refused",
            debug_error_string="",
        )
        stub.ListAgentConfigs.side_effect = error

        with pytest.raises(ServiceUnavailableError, match="Service unavailable"):
            await client.list_agent_configs()

    @pytest.mark.asyncio
    async def test_service_unavailable_error_on_get(
        self,
        agent_config_client_with_mock_stub: tuple[AgentConfigClient, MagicMock],
    ) -> None:
        """Test service unavailable error handling on get."""
        client, stub = agent_config_client_with_mock_stub
        error = grpc.aio.AioRpcError(
            code=grpc.StatusCode.UNAVAILABLE,
            initial_metadata=None,
            trailing_metadata=None,
            details="Connection refused",
            debug_error_string="",
        )
        stub.GetAgentConfig.side_effect = error

        with pytest.raises(ServiceUnavailableError, match="Service unavailable"):
            await client.get_agent_config("agent-123")

    @pytest.mark.asyncio
    async def test_unknown_grpc_error_propagated(
        self,
        agent_config_client_with_mock_stub: tuple[AgentConfigClient, MagicMock],
    ) -> None:
        """Test unknown gRPC errors are propagated."""
        client, stub = agent_config_client_with_mock_stub
        error = grpc.aio.AioRpcError(
            code=grpc.StatusCode.INTERNAL,
            initial_metadata=None,
            trailing_metadata=None,
            details="Internal server error",
            debug_error_string="",
        )
        stub.GetAgentConfig.side_effect = error

        with pytest.raises(grpc.aio.AioRpcError):
            await client.get_agent_config("agent-123")


class TestProtoConversion:
    """Tests for proto-to-domain model conversion."""

    @pytest.mark.asyncio
    async def test_summary_fields_converted(
        self,
        agent_config_client_with_mock_stub: tuple[AgentConfigClient, MagicMock],
    ) -> None:
        """Test all summary fields are correctly converted."""
        client, stub = agent_config_client_with_mock_stub
        proto = create_agent_config_summary_proto(
            agent_id="custom-agent",
            version="2.0.0",
            agent_type="generator",
            status="staged",
            description="A custom agent config",
            model="gpt-4",
            prompt_count=5,
        )
        response = ai_model_pb2.ListAgentConfigsResponse(
            agents=[proto],
            next_page_token="",
            total_count=1,
        )
        stub.ListAgentConfigs.return_value = response

        result = await client.list_agent_configs()

        config = result.data[0]
        assert config.agent_id == "custom-agent"
        assert config.version == "2.0.0"
        assert config.agent_type == "generator"
        assert config.status == "staged"
        assert config.description == "A custom agent config"
        assert config.model == "gpt-4"
        assert config.prompt_count == 5
        assert config.updated_at is not None

    @pytest.mark.asyncio
    async def test_detail_fields_converted(
        self,
        agent_config_client_with_mock_stub: tuple[AgentConfigClient, MagicMock],
    ) -> None:
        """Test all detail fields are correctly converted."""
        client, stub = agent_config_client_with_mock_stub
        config_json = '{"agent_id": "test", "type": "explorer"}'
        stub.GetAgentConfig.return_value = create_agent_config_response_proto(
            agent_id="test-agent",
            version="1.0.0",
            agent_type="explorer",
            status="active",
            description="Test description",
            config_json=config_json,
        )

        result = await client.get_agent_config("test-agent")

        assert result.agent_id == "test-agent"
        assert result.version == "1.0.0"
        assert result.agent_type == "explorer"
        assert result.status == "active"
        assert result.description == "Test description"
        assert result.config_json == config_json
        assert result.created_at is not None
        assert result.updated_at is not None

    @pytest.mark.asyncio
    async def test_prompt_summary_fields_converted(
        self,
        agent_config_client_with_mock_stub: tuple[AgentConfigClient, MagicMock],
    ) -> None:
        """Test all prompt summary fields are correctly converted."""
        client, stub = agent_config_client_with_mock_stub
        response = ai_model_pb2.ListPromptsResponse(
            prompts=[
                create_prompt_summary_proto(
                    id="custom-prompt:2.0.0",
                    prompt_id="custom-prompt",
                    agent_id="custom-agent",
                    version="2.0.0",
                    status="staged",
                    author="test-user",
                ),
            ],
            total_count=1,
        )
        stub.ListPromptsByAgent.return_value = response

        result = await client.list_prompts_by_agent("custom-agent")

        prompt = result[0]
        assert prompt.id == "custom-prompt:2.0.0"
        assert prompt.prompt_id == "custom-prompt"
        assert prompt.agent_id == "custom-agent"
        assert prompt.version == "2.0.0"
        assert prompt.status == "staged"
        assert prompt.author == "test-user"
        assert prompt.updated_at is not None

    @pytest.mark.asyncio
    async def test_nullable_model_field(
        self,
        agent_config_client_with_mock_stub: tuple[AgentConfigClient, MagicMock],
    ) -> None:
        """Test empty model field is converted to empty string."""
        client, stub = agent_config_client_with_mock_stub
        proto = create_agent_config_summary_proto(model="")
        response = ai_model_pb2.ListAgentConfigsResponse(
            agents=[proto],
            next_page_token="",
            total_count=1,
        )
        stub.ListAgentConfigs.return_value = response

        result = await client.list_agent_configs()

        assert result.data[0].model == ""


class TestClientClose:
    """Tests for client cleanup."""

    @pytest.mark.asyncio
    async def test_close_cleans_up_channel(self) -> None:
        """Test close properly cleans up channel."""
        client = AgentConfigClient(direct_host="localhost:50051")
        mock_channel = AsyncMock()
        client._channel = mock_channel
        client._stubs["test"] = "value"

        await client.close()

        mock_channel.close.assert_called_once()
        assert client._channel is None
        assert client._stubs == {}
