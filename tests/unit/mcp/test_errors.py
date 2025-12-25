"""Tests for MCP error handling module.

Tests cover:
- AC #7: Error handling with error_code, message, trace_id
- AC #8: INVALID_ARGUMENTS error code
- AC #9: SERVICE_UNAVAILABLE error code
"""

import pytest

from fp_common.mcp.errors import ErrorCode, McpToolError


class TestErrorCode:
    """Tests for ErrorCode enum matching proto definition."""

    def test_error_codes_exist(self) -> None:
        """All required error codes are defined."""
        assert hasattr(ErrorCode, "UNSPECIFIED")
        assert hasattr(ErrorCode, "INVALID_ARGUMENTS")
        assert hasattr(ErrorCode, "SERVICE_UNAVAILABLE")
        assert hasattr(ErrorCode, "TOOL_NOT_FOUND")
        assert hasattr(ErrorCode, "INTERNAL_ERROR")

    def test_error_code_values(self) -> None:
        """Error codes have correct integer values matching proto enum."""
        assert ErrorCode.UNSPECIFIED.value == 0
        assert ErrorCode.INVALID_ARGUMENTS.value == 1
        assert ErrorCode.SERVICE_UNAVAILABLE.value == 2
        assert ErrorCode.TOOL_NOT_FOUND.value == 3
        assert ErrorCode.INTERNAL_ERROR.value == 4


class TestMcpToolError:
    """Tests for McpToolError exception class."""

    def test_error_has_required_attributes(self) -> None:
        """AC #7: Error has error_code, message, trace_id."""
        error = McpToolError(
            error_code=ErrorCode.INVALID_ARGUMENTS,
            message="Invalid farmer_id format",
            trace_id="abc123",
            app_id="plantation-mcp",
            tool_name="get_farmer",
        )

        assert error.error_code == ErrorCode.INVALID_ARGUMENTS
        assert error.message == "Invalid farmer_id format"
        assert error.trace_id == "abc123"
        assert error.app_id == "plantation-mcp"
        assert error.tool_name == "get_farmer"

    def test_error_is_exception(self) -> None:
        """McpToolError is a proper Exception subclass."""
        error = McpToolError(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Database connection failed",
            trace_id="def456",
            app_id="collection-mcp",
            tool_name="search_documents",
        )

        assert isinstance(error, Exception)

        with pytest.raises(McpToolError):
            raise error

    def test_error_str_includes_context(self) -> None:
        """Error string representation includes full context for logging."""
        error = McpToolError(
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
            message="MongoDB connection timeout",
            trace_id="ghi789",
            app_id="knowledge-mcp",
            tool_name="get_diagnosis",
        )

        error_str = str(error)
        assert "SERVICE_UNAVAILABLE" in error_str
        assert "MongoDB connection timeout" in error_str
        assert "knowledge-mcp" in error_str
        assert "get_diagnosis" in error_str

    def test_error_with_optional_args(self) -> None:
        """Error works with optional arguments as None."""
        error = McpToolError(
            error_code=ErrorCode.TOOL_NOT_FOUND,
            message="Tool not found",
            trace_id="jkl012",
        )

        assert error.app_id is None
        assert error.tool_name is None

    def test_invalid_arguments_error_code(self) -> None:
        """AC #8: INVALID_ARGUMENTS error code is properly set."""
        error = McpToolError(
            error_code=ErrorCode.INVALID_ARGUMENTS,
            message="Missing required field: farmer_id",
            trace_id="mno345",
            app_id="plantation-mcp",
            tool_name="get_farmer",
        )

        assert error.error_code == ErrorCode.INVALID_ARGUMENTS
        assert error.error_code.name == "INVALID_ARGUMENTS"

    def test_service_unavailable_error_code(self) -> None:
        """AC #9: SERVICE_UNAVAILABLE error code is properly set."""
        error = McpToolError(
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
            message="MongoDB replica set unavailable",
            trace_id="pqr678",
            app_id="collection-mcp",
            tool_name="store_document",
        )

        assert error.error_code == ErrorCode.SERVICE_UNAVAILABLE
        assert error.error_code.name == "SERVICE_UNAVAILABLE"
