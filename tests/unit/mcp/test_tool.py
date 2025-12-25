"""Tests for GrpcMcpTool LangChain wrapper.

Tests cover:
- AC #5: LangChain BaseTool wrapper for MCP tools
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from fp_common.mcp.client import GrpcMcpClient
from fp_common.mcp.errors import ErrorCode, McpToolError
from fp_common.mcp.tool import GrpcMcpTool


class TestGrpcMcpToolInit:
    """Tests for GrpcMcpTool initialization."""

    def test_tool_has_required_attributes(self) -> None:
        """Tool has name, description, and mcp_client."""
        client = GrpcMcpClient(app_id="plantation-mcp")
        tool = GrpcMcpTool(
            name="get_farmer",
            description="Get farmer by ID",
            mcp_client=client,
        )

        assert tool.name == "get_farmer"
        assert tool.description == "Get farmer by ID"
        assert tool.mcp_client == client

    def test_tool_is_langchain_base_tool(self) -> None:
        """Tool extends LangChain BaseTool."""
        from langchain_core.tools import BaseTool

        client = GrpcMcpClient(app_id="plantation-mcp")
        tool = GrpcMcpTool(
            name="get_farmer",
            description="Get farmer by ID",
            mcp_client=client,
        )

        assert isinstance(tool, BaseTool)


class TestGrpcMcpToolExecution:
    """Tests for GrpcMcpTool execution."""

    @pytest.mark.asyncio
    async def test_arun_calls_mcp_client(self) -> None:
        """AC #5: _arun calls mcp_client.call_tool with arguments."""
        client = GrpcMcpClient(app_id="plantation-mcp")
        tool = GrpcMcpTool(
            name="get_farmer",
            description="Get farmer by ID",
            mcp_client=client,
        )

        with patch.object(client, "call_tool", new=AsyncMock()) as mock_call:
            mock_call.return_value = {"farmer_id": "WM-4521", "name": "John Kamau"}

            result = await tool._arun(farmer_id="WM-4521")

            mock_call.assert_called_once_with(
                tool_name="get_farmer",
                arguments={"farmer_id": "WM-4521"},
            )

    @pytest.mark.asyncio
    async def test_arun_returns_json_string(self) -> None:
        """AC #5: _arun returns JSON string for LLM consumption."""
        client = GrpcMcpClient(app_id="plantation-mcp")
        tool = GrpcMcpTool(
            name="get_farmer",
            description="Get farmer by ID",
            mcp_client=client,
        )

        with patch.object(client, "call_tool", new=AsyncMock()) as mock_call:
            mock_call.return_value = {"farmer_id": "WM-4521", "name": "John Kamau"}

            result = await tool._arun(farmer_id="WM-4521")

            # Result should be valid JSON
            parsed = json.loads(result)
            assert parsed["farmer_id"] == "WM-4521"
            assert parsed["name"] == "John Kamau"

    @pytest.mark.asyncio
    async def test_arun_returns_error_json_on_failure(self) -> None:
        """AC #5: _arun returns error JSON on McpToolError."""
        client = GrpcMcpClient(app_id="plantation-mcp")
        tool = GrpcMcpTool(
            name="get_farmer",
            description="Get farmer by ID",
            mcp_client=client,
        )

        with patch.object(client, "call_tool", new=AsyncMock()) as mock_call:
            mock_call.side_effect = McpToolError(
                error_code=ErrorCode.INVALID_ARGUMENTS,
                message="Invalid farmer_id format",
                trace_id="abc123",
            )

            result = await tool._arun(farmer_id="invalid")

            parsed = json.loads(result)
            assert parsed["error"] is True
            assert parsed["error_code"] == "INVALID_ARGUMENTS"
            assert "Invalid farmer_id format" in parsed["message"]

    def test_run_raises_not_implemented(self) -> None:
        """Sync _run raises NotImplementedError."""
        client = GrpcMcpClient(app_id="plantation-mcp")
        tool = GrpcMcpTool(
            name="get_farmer",
            description="Get farmer by ID",
            mcp_client=client,
        )

        with pytest.raises(NotImplementedError):
            tool._run(farmer_id="WM-4521")
