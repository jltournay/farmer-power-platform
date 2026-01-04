"""Unit tests for AI Model gRPC server."""

from unittest.mock import MagicMock

import pytest


class TestAiModelServiceServicer:
    """Tests for AiModelService gRPC servicer."""

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create a mock gRPC context."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy(self, mock_context: MagicMock) -> None:
        """HealthCheck RPC should return healthy=True with version."""
        from ai_model.api.grpc_server import AiModelServiceServicer
        from fp_proto.ai_model.v1 import ai_model_pb2

        servicer = AiModelServiceServicer()
        request = ai_model_pb2.HealthCheckRequest()

        response = await servicer.HealthCheck(request, mock_context)

        assert response.healthy is True
        assert response.version == "0.1.0"

    @pytest.mark.asyncio
    async def test_extract_returns_not_implemented(self, mock_context: MagicMock) -> None:
        """Extract RPC should return success=False as it's a stub."""
        from ai_model.api.grpc_server import AiModelServiceServicer
        from fp_proto.ai_model.v1 import ai_model_pb2

        servicer = AiModelServiceServicer()
        request = ai_model_pb2.ExtractionRequest(
            raw_content="test content",
            ai_agent_id="test-agent",
            content_type="application/json",
        )

        response = await servicer.Extract(request, mock_context)

        assert response.success is False
        assert "not implemented" in response.error_message.lower()
        assert response.confidence == 0.0
        assert response.validation_passed is False


class TestGrpcServer:
    """Tests for GrpcServer wrapper class."""

    def test_grpc_server_initializes_with_none(self) -> None:
        """GrpcServer should initialize with no server instance."""
        from ai_model.api.grpc_server import GrpcServer

        server = GrpcServer()

        assert server._server is None
        assert server._health_servicer is None

    @pytest.mark.asyncio
    async def test_stop_does_nothing_when_not_started(self) -> None:
        """stop() should handle case when server not started."""
        from ai_model.api.grpc_server import GrpcServer

        server = GrpcServer()
        # Should not raise any exception
        await server.stop()

    @pytest.mark.asyncio
    async def test_wait_for_termination_does_nothing_when_not_started(self) -> None:
        """wait_for_termination() should handle case when server not started."""
        from ai_model.api.grpc_server import GrpcServer

        server = GrpcServer()
        # Should not raise any exception
        await server.wait_for_termination()


class TestGrpcServerFunctions:
    """Tests for module-level gRPC server functions."""

    @pytest.mark.asyncio
    async def test_get_grpc_server_returns_singleton(self) -> None:
        """get_grpc_server should return the same instance."""
        from ai_model.api import grpc_server

        # Reset global state
        grpc_server._grpc_server = None

        server1 = await grpc_server.get_grpc_server()
        server2 = await grpc_server.get_grpc_server()

        assert server1 is server2

        # Cleanup
        grpc_server._grpc_server = None

    @pytest.mark.asyncio
    async def test_stop_grpc_server_when_none(self) -> None:
        """stop_grpc_server should handle case when no server exists."""
        from ai_model.api import grpc_server

        grpc_server._grpc_server = None

        # Should not raise any exception
        await grpc_server.stop_grpc_server()
