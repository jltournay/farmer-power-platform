"""Tests for Collection MCP tool definitions."""

import pytest
from jsonschema import validate, ValidationError as JsonSchemaValidationError

from collection_mcp.tools.definitions import (
    TOOL_REGISTRY,
    ToolDefinition,
    get_tool,
    list_tools,
)


class TestToolRegistry:
    """Tests for the tool registry."""

    def test_registry_has_all_tools(self) -> None:
        """Verify all expected tools are in the registry."""
        expected_tools = {
            "get_documents",
            "get_document_by_id",
            "get_farmer_documents",
            "search_documents",
            "list_sources",
        }
        assert set(TOOL_REGISTRY.keys()) == expected_tools

    def test_all_tools_have_valid_definitions(self) -> None:
        """Verify all tools have proper ToolDefinition structure."""
        for name, tool in TOOL_REGISTRY.items():
            assert isinstance(tool, ToolDefinition)
            assert tool.name == name
            assert len(tool.description) > 0
            assert tool.category in ("query", "search")
            assert isinstance(tool.input_schema, dict)

    def test_all_tools_have_valid_json_schemas(self) -> None:
        """Verify all tool input schemas are valid JSON schemas."""
        for name, tool in TOOL_REGISTRY.items():
            schema = tool.input_schema
            assert schema.get("type") == "object", f"Tool {name} should have object schema"
            assert "properties" in schema, f"Tool {name} should have properties"
            assert "required" in schema, f"Tool {name} should have required array"


class TestGetDocumentsTool:
    """Tests for get_documents tool definition."""

    @pytest.fixture
    def tool(self) -> ToolDefinition:
        """Get the get_documents tool definition."""
        tool = get_tool("get_documents")
        assert tool is not None
        return tool

    def test_schema_allows_empty_arguments(self, tool: ToolDefinition) -> None:
        """Verify get_documents accepts empty arguments."""
        validate(instance={}, schema=tool.input_schema)

    def test_schema_accepts_source_id(self, tool: ToolDefinition) -> None:
        """Verify get_documents accepts source_id filter."""
        validate(
            instance={"source_id": "qc-analyzer-result"},
            schema=tool.input_schema,
        )

    def test_schema_accepts_farmer_id(self, tool: ToolDefinition) -> None:
        """Verify get_documents accepts farmer_id filter."""
        validate(
            instance={"farmer_id": "WM-4521"},
            schema=tool.input_schema,
        )

    def test_schema_accepts_linkage(self, tool: ToolDefinition) -> None:
        """Verify get_documents accepts linkage filter."""
        validate(
            instance={"linkage": {"batch_id": "batch-001"}},
            schema=tool.input_schema,
        )

    def test_schema_accepts_attributes(self, tool: ToolDefinition) -> None:
        """Verify get_documents accepts attributes filter with operators."""
        validate(
            instance={
                "attributes": {
                    "bag_summary.primary_percentage": {"$lt": 70},
                    "grade": "A",
                }
            },
            schema=tool.input_schema,
        )

    def test_schema_accepts_date_range(self, tool: ToolDefinition) -> None:
        """Verify get_documents accepts date_range filter."""
        validate(
            instance={
                "date_range": {
                    "start": "2024-01-01T00:00:00Z",
                    "end": "2024-12-31T23:59:59Z",
                }
            },
            schema=tool.input_schema,
        )

    def test_schema_accepts_limit(self, tool: ToolDefinition) -> None:
        """Verify get_documents accepts limit parameter."""
        validate(instance={"limit": 100}, schema=tool.input_schema)

    def test_schema_accepts_combined_filters(self, tool: ToolDefinition) -> None:
        """Verify get_documents accepts combined filters."""
        validate(
            instance={
                "source_id": "qc-analyzer-result",
                "farmer_id": "WM-4521",
                "linkage": {"factory_id": "FAC-001"},
                "attributes": {"grade": "B"},
                "date_range": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z"},
                "limit": 50,
            },
            schema=tool.input_schema,
        )


class TestGetDocumentByIdTool:
    """Tests for get_document_by_id tool definition."""

    @pytest.fixture
    def tool(self) -> ToolDefinition:
        """Get the get_document_by_id tool definition."""
        tool = get_tool("get_document_by_id")
        assert tool is not None
        return tool

    def test_schema_requires_document_id(self, tool: ToolDefinition) -> None:
        """Verify get_document_by_id requires document_id."""
        with pytest.raises(JsonSchemaValidationError):
            validate(instance={}, schema=tool.input_schema)

    def test_schema_accepts_document_id(self, tool: ToolDefinition) -> None:
        """Verify get_document_by_id accepts document_id."""
        validate(
            instance={"document_id": "qc-analyzer-exceptions/batch-001/leaf_001"},
            schema=tool.input_schema,
        )

    def test_schema_accepts_include_files(self, tool: ToolDefinition) -> None:
        """Verify get_document_by_id accepts include_files flag."""
        validate(
            instance={
                "document_id": "qc-analyzer-exceptions/batch-001/leaf_001",
                "include_files": True,
            },
            schema=tool.input_schema,
        )


class TestGetFarmerDocumentsTool:
    """Tests for get_farmer_documents tool definition."""

    @pytest.fixture
    def tool(self) -> ToolDefinition:
        """Get the get_farmer_documents tool definition."""
        tool = get_tool("get_farmer_documents")
        assert tool is not None
        return tool

    def test_schema_requires_farmer_id(self, tool: ToolDefinition) -> None:
        """Verify get_farmer_documents requires farmer_id."""
        with pytest.raises(JsonSchemaValidationError):
            validate(instance={}, schema=tool.input_schema)

    def test_schema_accepts_farmer_id(self, tool: ToolDefinition) -> None:
        """Verify get_farmer_documents accepts farmer_id."""
        validate(
            instance={"farmer_id": "WM-4521"},
            schema=tool.input_schema,
        )

    def test_schema_accepts_source_ids(self, tool: ToolDefinition) -> None:
        """Verify get_farmer_documents accepts source_ids array."""
        validate(
            instance={
                "farmer_id": "WM-4521",
                "source_ids": ["qc-analyzer-result", "qc-analyzer-exceptions"],
            },
            schema=tool.input_schema,
        )

    def test_schema_accepts_all_filters(self, tool: ToolDefinition) -> None:
        """Verify get_farmer_documents accepts all optional filters."""
        validate(
            instance={
                "farmer_id": "WM-4521",
                "source_ids": ["qc-analyzer-result"],
                "date_range": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z"},
                "limit": 100,
            },
            schema=tool.input_schema,
        )


class TestSearchDocumentsTool:
    """Tests for search_documents tool definition."""

    @pytest.fixture
    def tool(self) -> ToolDefinition:
        """Get the search_documents tool definition."""
        tool = get_tool("search_documents")
        assert tool is not None
        return tool

    def test_schema_requires_query(self, tool: ToolDefinition) -> None:
        """Verify search_documents requires query."""
        with pytest.raises(JsonSchemaValidationError):
            validate(instance={}, schema=tool.input_schema)

    def test_schema_accepts_query(self, tool: ToolDefinition) -> None:
        """Verify search_documents accepts query."""
        validate(
            instance={"query": "coarse leaf"},
            schema=tool.input_schema,
        )

    def test_schema_accepts_all_filters(self, tool: ToolDefinition) -> None:
        """Verify search_documents accepts all optional filters."""
        validate(
            instance={
                "query": "coarse leaf",
                "source_ids": ["qc-analyzer-exceptions"],
                "farmer_id": "WM-4521",
                "limit": 20,
            },
            schema=tool.input_schema,
        )


class TestListSourcesTool:
    """Tests for list_sources tool definition."""

    @pytest.fixture
    def tool(self) -> ToolDefinition:
        """Get the list_sources tool definition."""
        tool = get_tool("list_sources")
        assert tool is not None
        return tool

    def test_schema_allows_empty_arguments(self, tool: ToolDefinition) -> None:
        """Verify list_sources accepts empty arguments."""
        validate(instance={}, schema=tool.input_schema)

    def test_schema_accepts_enabled_only(self, tool: ToolDefinition) -> None:
        """Verify list_sources accepts enabled_only flag."""
        validate(
            instance={"enabled_only": False},
            schema=tool.input_schema,
        )


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_tool_returns_tool(self) -> None:
        """Verify get_tool returns tool definition."""
        tool = get_tool("get_documents")
        assert tool is not None
        assert tool.name == "get_documents"

    def test_get_tool_returns_none_for_unknown(self) -> None:
        """Verify get_tool returns None for unknown tool."""
        tool = get_tool("unknown_tool")
        assert tool is None

    def test_list_tools_returns_all_tools(self) -> None:
        """Verify list_tools returns all tools."""
        tools = list_tools()
        assert len(tools) == 5

    def test_list_tools_filters_by_category(self) -> None:
        """Verify list_tools filters by category."""
        query_tools = list_tools(category="query")
        search_tools = list_tools(category="search")

        assert len(query_tools) == 4
        assert len(search_tools) == 1
        assert all(t.category == "query" for t in query_tools)
        assert all(t.category == "search" for t in search_tools)
