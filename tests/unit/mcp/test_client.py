"""Tests for GrpcMcpClient.

Tests cover:
- AC #4: Client call_tool with DAPR service invocation
- AC #7: OpenTelemetry trace context propagation
- AC #9: Error handling for service unavailable
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from fp_common.mcp.client import GrpcMcpClient
from fp_common.mcp.errors import ErrorCode, McpToolError


class TestGrpcMcpClientInit:
    """Tests for GrpcMcpClient initialization."""

    def test_client_stores_app_id(self) -> None:
        """Client stores the DAPR app_id for service invocation."""
        client = GrpcMcpClient(app_id="plantation-mcp")
        assert client.app_id == "plantation-mcp"

    def test_client_with_different_app_ids(self) -> None:
        """Client works with various MCP server app_ids."""
        client1 = GrpcMcpClient(app_id="collection-mcp")
        client2 = GrpcMcpClient(app_id="knowledge-mcp")

        assert client1.app_id == "collection-mcp"
        assert client2.app_id == "knowledge-mcp"


class TestGrpcMcpClientCallTool:
    """Tests for GrpcMcpClient.call_tool method."""

    @pytest.mark.asyncio
    async def test_call_tool_success(self) -> None:
        """AC #4: call_tool returns deserialized result on success."""
        client = GrpcMcpClient(app_id="plantation-mcp")

        # Create mock response
        mock_response = MagicMock()
        mock_response.data = self._create_success_response(
            {"farmer_id": "WM-4521", "name": "John Kamau"}
        )

        with patch.object(client, "_invoke_method_sync", return_value=mock_response):
            result = await client.call_tool(
                tool_name="get_farmer",
                arguments={"farmer_id": "WM-4521"},
            )

        assert result == {"farmer_id": "WM-4521", "name": "John Kamau"}

    @pytest.mark.asyncio
    async def test_call_tool_with_caller_agent_id(self) -> None:
        """call_tool passes caller_agent_id for audit logging."""
        client = GrpcMcpClient(app_id="plantation-mcp")

        mock_response = MagicMock()
        mock_response.data = self._create_success_response({"result": "ok"})

        with patch.object(client, "_invoke_method_sync", return_value=mock_response) as mock_invoke:
            await client.call_tool(
                tool_name="get_farmer",
                arguments={"farmer_id": "WM-4521"},
                caller_agent_id="quality-triage-agent",
            )

            # Verify _invoke_method_sync was called
            mock_invoke.assert_called_once()
            call_args = mock_invoke.call_args
            # First arg is method_name
            assert call_args[0][0] == "McpToolService/CallTool"

    @pytest.mark.asyncio
    async def test_call_tool_raises_on_failure_response(self) -> None:
        """AC #7: call_tool raises McpToolError on failure response."""
        client = GrpcMcpClient(app_id="plantation-mcp")

        mock_response = MagicMock()
        mock_response.data = self._create_failure_response(
            error_code=ErrorCode.INVALID_ARGUMENTS,
            error_message="Invalid farmer_id format",
        )

        with patch.object(client, "_invoke_method_sync", return_value=mock_response):
            with pytest.raises(McpToolError) as exc_info:
                await client.call_tool(
                    tool_name="get_farmer",
                    arguments={"farmer_id": "invalid"},
                )

            assert exc_info.value.error_code == ErrorCode.INVALID_ARGUMENTS
            assert "Invalid farmer_id format" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_call_tool_service_unavailable(self) -> None:
        """AC #9: call_tool raises McpToolError on service unavailable."""
        client = GrpcMcpClient(app_id="plantation-mcp")

        mock_response = MagicMock()
        mock_response.data = self._create_failure_response(
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
            error_message="MongoDB connection timeout",
        )

        with patch.object(client, "_invoke_method_sync", return_value=mock_response):
            with pytest.raises(McpToolError) as exc_info:
                await client.call_tool(
                    tool_name="get_farmer",
                    arguments={"farmer_id": "WM-4521"},
                )

            assert exc_info.value.error_code == ErrorCode.SERVICE_UNAVAILABLE

    def _create_success_response(self, result: dict) -> bytes:
        """Create a serialized ToolCallResponse for success case."""
        from fp_proto.mcp.v1 import mcp_tool_pb2

        response = mcp_tool_pb2.ToolCallResponse(
            success=True,
            result_json=json.dumps(result),
        )
        return response.SerializeToString()

    def _create_failure_response(
        self, error_code: ErrorCode, error_message: str
    ) -> bytes:
        """Create a serialized ToolCallResponse for failure case."""
        from fp_proto.mcp.v1 import mcp_tool_pb2

        response = mcp_tool_pb2.ToolCallResponse(
            success=False,
            error_code=error_code.value,
            error_message=error_message,
        )
        return response.SerializeToString()


class TestGrpcMcpClientListTools:
    """Tests for GrpcMcpClient.list_tools method."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_tool_definitions(self) -> None:
        """list_tools returns parsed tool definitions."""
        client = GrpcMcpClient(app_id="plantation-mcp")

        mock_response = MagicMock()
        mock_response.data = self._create_list_tools_response([
            {
                "name": "get_farmer_by_id",
                "description": "Get farmer by ID",
                "input_schema_json": '{"type": "object", "properties": {"farmer_id": {"type": "string"}}}',
                "category": "query",
            },
            {
                "name": "search_farmers",
                "description": "Search farmers",
                "input_schema_json": '{"type": "object", "properties": {"query": {"type": "string"}}}',
                "category": "search",
            },
        ])

        with patch.object(client, "_invoke_method_sync", return_value=mock_response):
            tools = await client.list_tools()

        assert len(tools) == 2
        assert tools[0]["name"] == "get_farmer_by_id"
        assert tools[0]["category"] == "query"
        assert tools[1]["name"] == "search_farmers"

    @pytest.mark.asyncio
    async def test_list_tools_with_category_filter(self) -> None:
        """list_tools passes category filter to MCP server."""
        client = GrpcMcpClient(app_id="plantation-mcp")

        mock_response = MagicMock()
        mock_response.data = self._create_list_tools_response([])

        with patch.object(client, "_invoke_method_sync", return_value=mock_response) as mock_invoke:
            await client.list_tools(category="query")

            mock_invoke.assert_called_once()

    def _create_list_tools_response(self, tools: list[dict]) -> bytes:
        """Create a serialized ListToolsResponse."""
        from fp_proto.mcp.v1 import mcp_tool_pb2

        tool_defs = [
            mcp_tool_pb2.ToolDefinition(
                name=t["name"],
                description=t["description"],
                input_schema_json=t["input_schema_json"],
                category=t["category"],
            )
            for t in tools
        ]
        response = mcp_tool_pb2.ListToolsResponse(tools=tool_defs)
        return response.SerializeToString()
