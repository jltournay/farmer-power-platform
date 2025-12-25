"""Mock MCP server for testing.

Provides MockMcpServer class and mock_mcp_tool fixture for testing
AI agents that use MCP tools.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from fp_common.mcp.errors import ErrorCode, McpToolError

if TYPE_CHECKING:
    from collections.abc import Callable, Generator


class MockMcpServer:
    """Mock MCP server for testing AI agents.

    Allows stubbing tool responses and tracking tool calls for verification.

    Example:
        ```python
        mock = MockMcpServer(app_id="plantation-mcp")
        mock.stub_tool_response(
            "get_farmer",
            {"farmer_id": "WM-4521", "name": "John Kamau"}
        )

        # Use in tests
        result = await mock.call_tool("get_farmer", {"farmer_id": "WM-4521"})
        assert result["name"] == "John Kamau"

        # Verify calls
        assert mock.get_tool_calls("get_farmer") == [{"farmer_id": "WM-4521"}]
        ```
    """

    def __init__(self, app_id: str) -> None:
        """Initialize mock MCP server.

        Args:
            app_id: DAPR app ID this mock represents
        """
        self.app_id = app_id
        self._tool_responses: dict[str, Any] = {}
        self._tool_handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {}
        self._tool_calls: dict[str, list[dict[str, Any]]] = {}
        self._tools: list[dict[str, Any]] = []

    def stub_tool_response(
        self,
        tool_name: str,
        response: dict[str, Any],
    ) -> None:
        """Stub a tool to return a fixed response.

        Args:
            tool_name: Name of the tool to stub
            response: Response to return when tool is called
        """
        self._tool_responses[tool_name] = response

    def stub_tool_handler(
        self,
        tool_name: str,
        handler: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        """Stub a tool with a custom handler function.

        Args:
            tool_name: Name of the tool to stub
            handler: Function that takes arguments and returns response
        """
        self._tool_handlers[tool_name] = handler

    def stub_tool_error(
        self,
        tool_name: str,
        error_code: int,
        error_message: str,
    ) -> None:
        """Stub a tool to return an error response.

        Args:
            tool_name: Name of the tool to stub
            error_code: Error code to return
            error_message: Error message to return
        """
        self._tool_responses[tool_name] = {
            "__error__": True,
            "error_code": error_code,
            "error_message": error_message,
        }

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any] | None = None,
        category: str = "query",
    ) -> None:
        """Register a tool definition for list_tools.

        Args:
            name: Tool name
            description: Tool description
            input_schema: JSON Schema for tool arguments
            category: Tool category
        """
        self._tools.append(
            {
                "name": name,
                "description": description,
                "input_schema": input_schema or {},
                "category": category,
            }
        )

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Simulate calling a tool.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Stubbed response or error
        """
        # Track the call
        if tool_name not in self._tool_calls:
            self._tool_calls[tool_name] = []
        self._tool_calls[tool_name].append(arguments)

        # Check for handler
        if tool_name in self._tool_handlers:
            handler_result = self._tool_handlers[tool_name](arguments)
            return handler_result

        # Check for stubbed response
        if tool_name in self._tool_responses:
            response = self._tool_responses[tool_name]
            if isinstance(response, dict) and response.get("__error__"):
                raise McpToolError(
                    error_code=ErrorCode(response["error_code"]),
                    message=response["error_message"],
                    trace_id="mock-trace-id",
                    app_id=self.app_id,
                    tool_name=tool_name,
                )
            return cast("dict[str, Any]", response)

        # Default: return empty response
        return {}

    async def list_tools(
        self,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """List registered tools.

        Args:
            category: Optional category filter

        Returns:
            List of tool definitions
        """
        if category:
            return [t for t in self._tools if t["category"] == category]
        return self._tools

    def get_tool_calls(self, tool_name: str) -> list[dict[str, Any]]:
        """Get all calls made to a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            List of argument dictionaries for each call
        """
        return self._tool_calls.get(tool_name, [])

    def reset(self) -> None:
        """Reset all stubbed responses and call history."""
        self._tool_responses.clear()
        self._tool_handlers.clear()
        self._tool_calls.clear()
        self._tools.clear()

    def create_mock_client(self) -> MagicMock:
        """Create a mock GrpcMcpClient that uses this mock server.

        Returns:
            MagicMock configured to use this mock server's responses
        """
        from fp_common.mcp.client import GrpcMcpClient

        mock_client = MagicMock(spec=GrpcMcpClient)
        mock_client.app_id = self.app_id
        mock_client.call_tool = AsyncMock(side_effect=self.call_tool)
        mock_client.list_tools = AsyncMock(side_effect=self.list_tools)
        return mock_client


@pytest.fixture
def mock_mcp_tool() -> Generator[Callable[[str], MockMcpServer], None, None]:
    """Pytest fixture for creating mock MCP servers.

    Example:
        ```python
        def test_my_agent(mock_mcp_tool):
            mock = mock_mcp_tool("plantation-mcp")
            mock.stub_tool_response("get_farmer", {"name": "John"})

            # Your test code here
        ```

    Yields:
        Factory function that creates MockMcpServer instances
    """
    mocks: dict[str, MockMcpServer] = {}

    def factory(app_id: str) -> MockMcpServer:
        if app_id not in mocks:
            mocks[app_id] = MockMcpServer(app_id)
        return mocks[app_id]

    yield factory

    # Cleanup
    for mock in mocks.values():
        mock.reset()
