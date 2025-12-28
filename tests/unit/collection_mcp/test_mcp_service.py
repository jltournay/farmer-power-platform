"""Tests for Collection MCP Tool Service."""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from collection_mcp.api.mcp_service import McpToolServiceServicer
from collection_mcp.infrastructure.blob_url_generator import BlobUrlGenerator
from collection_mcp.infrastructure.document_client import (
    DocumentClient,
    DocumentNotFoundError,
)
from collection_mcp.infrastructure.source_config_client import SourceConfigClient


class MockToolCallRequest:
    """Mock gRPC ToolCallRequest."""

    def __init__(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        caller_agent_id: str = "test-agent",
    ) -> None:
        self.tool_name = tool_name
        self.arguments_json = json.dumps(arguments) if arguments else ""
        self.caller_agent_id = caller_agent_id


class MockListToolsRequest:
    """Mock gRPC ListToolsRequest."""

    def __init__(self, category: str = "") -> None:
        self.category = category


class MockContext:
    """Mock gRPC context."""

    pass


@pytest.fixture
def mock_document_client() -> MagicMock:
    """Create a mock document client."""
    client = MagicMock(spec=DocumentClient)
    client.get_documents = AsyncMock(return_value=[])
    client.get_document_by_id = AsyncMock(return_value={})
    client.get_farmer_documents = AsyncMock(return_value=[])
    client.search_documents = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_blob_url_generator() -> MagicMock:
    """Create a mock blob URL generator."""
    generator = MagicMock(spec=BlobUrlGenerator)
    generator.enrich_files_with_sas = MagicMock(return_value=[])
    return generator


@pytest.fixture
def mock_source_config_client() -> MagicMock:
    """Create a mock source config client."""
    client = MagicMock(spec=SourceConfigClient)
    client.list_sources = AsyncMock(return_value=[])
    return client


@pytest.fixture
def servicer(
    mock_document_client: MagicMock,
    mock_blob_url_generator: MagicMock,
    mock_source_config_client: MagicMock,
) -> McpToolServiceServicer:
    """Create a servicer with mocked dependencies."""
    return McpToolServiceServicer(
        document_client=mock_document_client,
        blob_url_generator=mock_blob_url_generator,
        source_config_client=mock_source_config_client,
    )


class TestListTools:
    """Tests for ListTools RPC."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_all_tools(self, servicer: McpToolServiceServicer) -> None:
        """Verify ListTools returns all tool definitions."""
        request = MockListToolsRequest()
        context = MockContext()

        response = await servicer.ListTools(request, context)

        assert len(response.tools) == 5
        tool_names = {t.name for t in response.tools}
        assert tool_names == {
            "get_documents",
            "get_document_by_id",
            "get_farmer_documents",
            "search_documents",
            "list_sources",
        }

    @pytest.mark.asyncio
    async def test_list_tools_filters_by_category(self, servicer: McpToolServiceServicer) -> None:
        """Verify ListTools filters by category."""
        request = MockListToolsRequest(category="search")
        context = MockContext()

        response = await servicer.ListTools(request, context)

        assert len(response.tools) == 1
        assert response.tools[0].name == "search_documents"


class TestCallToolValidation:
    """Tests for CallTool validation."""

    @pytest.mark.asyncio
    async def test_call_tool_unknown_tool(self, servicer: McpToolServiceServicer) -> None:
        """Verify CallTool returns error for unknown tool."""
        request = MockToolCallRequest(tool_name="unknown_tool")
        context = MockContext()

        response = await servicer.CallTool(request, context)

        assert response.success is False
        assert "Unknown tool" in response.error_message

    @pytest.mark.asyncio
    async def test_call_tool_invalid_json(self, servicer: McpToolServiceServicer) -> None:
        """Verify CallTool returns error for invalid JSON."""
        request = MockToolCallRequest(tool_name="get_documents")
        request.arguments_json = "{invalid json}"
        context = MockContext()

        response = await servicer.CallTool(request, context)

        assert response.success is False
        assert "Invalid JSON" in response.error_message

    @pytest.mark.asyncio
    async def test_call_tool_schema_validation_error(self, servicer: McpToolServiceServicer) -> None:
        """Verify CallTool returns error for schema validation failure."""
        # get_document_by_id requires document_id
        request = MockToolCallRequest(
            tool_name="get_document_by_id",
            arguments={},  # Missing required document_id
        )
        context = MockContext()

        response = await servicer.CallTool(request, context)

        assert response.success is False
        assert "Validation error" in response.error_message


class TestGetDocumentsHandler:
    """Tests for get_documents tool handler."""

    @pytest.mark.asyncio
    async def test_get_documents_success(
        self,
        servicer: McpToolServiceServicer,
        mock_document_client: MagicMock,
    ) -> None:
        """Verify get_documents returns documents."""
        mock_docs = [
            {"document_id": "doc-001", "source_id": "qc-analyzer-result"},
            {"document_id": "doc-002", "source_id": "qc-analyzer-result"},
        ]
        mock_document_client.get_documents.return_value = mock_docs

        request = MockToolCallRequest(
            tool_name="get_documents",
            arguments={"source_id": "qc-analyzer-result"},
        )
        context = MockContext()

        response = await servicer.CallTool(request, context)

        assert response.success is True
        result = json.loads(response.result_json)
        assert result["count"] == 2
        assert len(result["documents"]) == 2

    @pytest.mark.asyncio
    async def test_get_documents_passes_filters(
        self,
        servicer: McpToolServiceServicer,
        mock_document_client: MagicMock,
    ) -> None:
        """Verify get_documents passes all filters to client."""
        mock_document_client.get_documents.return_value = []

        request = MockToolCallRequest(
            tool_name="get_documents",
            arguments={
                "source_id": "qc-analyzer-result",
                "farmer_id": "WM-4521",
                "linkage": {"batch_id": "batch-001"},
                "attributes": {"grade": "B"},
                "limit": 25,
            },
        )
        context = MockContext()

        await servicer.CallTool(request, context)

        mock_document_client.get_documents.assert_called_once_with(
            source_id="qc-analyzer-result",
            farmer_id="WM-4521",
            linkage={"batch_id": "batch-001"},
            attributes={"grade": "B"},
            date_range=None,
            limit=25,
        )


class TestGetDocumentByIdHandler:
    """Tests for get_document_by_id tool handler."""

    @pytest.mark.asyncio
    async def test_get_document_by_id_success(
        self,
        servicer: McpToolServiceServicer,
        mock_document_client: MagicMock,
    ) -> None:
        """Verify get_document_by_id returns document."""
        mock_doc = {
            "document_id": "qc-analyzer/batch-001/leaf_001",
            "source_id": "qc-analyzer-exceptions",
            "attributes": {"issue": "coarse leaf"},
        }
        mock_document_client.get_document_by_id.return_value = mock_doc

        request = MockToolCallRequest(
            tool_name="get_document_by_id",
            arguments={"document_id": "qc-analyzer/batch-001/leaf_001"},
        )
        context = MockContext()

        response = await servicer.CallTool(request, context)

        assert response.success is True
        result = json.loads(response.result_json)
        assert result["document"]["document_id"] == "qc-analyzer/batch-001/leaf_001"

    @pytest.mark.asyncio
    async def test_get_document_by_id_with_files(
        self,
        servicer: McpToolServiceServicer,
        mock_document_client: MagicMock,
        mock_blob_url_generator: MagicMock,
    ) -> None:
        """Verify get_document_by_id enriches files with SAS URLs."""
        mock_doc = {
            "document_id": "doc-001",
            "files": [
                {"blob_uri": "https://storage.blob.core.windows.net/container/file.jpg"},
            ],
        }
        mock_document_client.get_document_by_id.return_value = mock_doc

        enriched_files = [
            {
                "blob_uri": "https://storage.blob.core.windows.net/container/file.jpg",
                "sas_url": "https://storage.blob.core.windows.net/container/file.jpg?token",
            },
        ]
        mock_blob_url_generator.enrich_files_with_sas.return_value = enriched_files

        request = MockToolCallRequest(
            tool_name="get_document_by_id",
            arguments={"document_id": "doc-001", "include_files": True},
        )
        context = MockContext()

        response = await servicer.CallTool(request, context)

        assert response.success is True
        mock_blob_url_generator.enrich_files_with_sas.assert_called_once()
        result = json.loads(response.result_json)
        assert result["document"]["files"][0]["sas_url"] is not None

    @pytest.mark.asyncio
    async def test_get_document_by_id_not_found(
        self,
        servicer: McpToolServiceServicer,
        mock_document_client: MagicMock,
    ) -> None:
        """Verify get_document_by_id returns NOT_FOUND error."""
        mock_document_client.get_document_by_id.side_effect = DocumentNotFoundError("doc-001")

        request = MockToolCallRequest(
            tool_name="get_document_by_id",
            arguments={"document_id": "doc-001"},
        )
        context = MockContext()

        response = await servicer.CallTool(request, context)

        assert response.success is False
        assert "not found" in response.error_message.lower()


class TestGetFarmerDocumentsHandler:
    """Tests for get_farmer_documents tool handler."""

    @pytest.mark.asyncio
    async def test_get_farmer_documents_success(
        self,
        servicer: McpToolServiceServicer,
        mock_document_client: MagicMock,
    ) -> None:
        """Verify get_farmer_documents returns documents."""
        mock_docs = [
            {"document_id": "doc-001", "farmer_id": "WM-4521"},
            {"document_id": "doc-002", "farmer_id": "WM-4521"},
        ]
        mock_document_client.get_farmer_documents.return_value = mock_docs

        request = MockToolCallRequest(
            tool_name="get_farmer_documents",
            arguments={"farmer_id": "WM-4521"},
        )
        context = MockContext()

        response = await servicer.CallTool(request, context)

        assert response.success is True
        result = json.loads(response.result_json)
        assert result["farmer_id"] == "WM-4521"
        assert result["count"] == 2


class TestSearchDocumentsHandler:
    """Tests for search_documents tool handler."""

    @pytest.mark.asyncio
    async def test_search_documents_success(
        self,
        servicer: McpToolServiceServicer,
        mock_document_client: MagicMock,
    ) -> None:
        """Verify search_documents returns results."""
        mock_docs = [
            {"document_id": "doc-001", "relevance_score": 1.5},
        ]
        mock_document_client.search_documents.return_value = mock_docs

        request = MockToolCallRequest(
            tool_name="search_documents",
            arguments={"query": "coarse leaf"},
        )
        context = MockContext()

        response = await servicer.CallTool(request, context)

        assert response.success is True
        result = json.loads(response.result_json)
        assert result["query"] == "coarse leaf"
        assert result["count"] == 1


class TestListSourcesHandler:
    """Tests for list_sources tool handler."""

    @pytest.mark.asyncio
    async def test_list_sources_success(
        self,
        servicer: McpToolServiceServicer,
        mock_source_config_client: MagicMock,
    ) -> None:
        """Verify list_sources returns source configs."""
        mock_sources = [
            {"source_id": "qc-analyzer-result", "display_name": "QC Analyzer Results"},
            {"source_id": "weather-api", "display_name": "Weather Data"},
        ]
        mock_source_config_client.list_sources.return_value = mock_sources

        request = MockToolCallRequest(
            tool_name="list_sources",
            arguments={},
        )
        context = MockContext()

        response = await servicer.CallTool(request, context)

        assert response.success is True
        result = json.loads(response.result_json)
        assert result["count"] == 2
        assert len(result["sources"]) == 2

    @pytest.mark.asyncio
    async def test_list_sources_enabled_only(
        self,
        servicer: McpToolServiceServicer,
        mock_source_config_client: MagicMock,
    ) -> None:
        """Verify list_sources respects enabled_only flag."""
        mock_source_config_client.list_sources.return_value = []

        request = MockToolCallRequest(
            tool_name="list_sources",
            arguments={"enabled_only": False},
        )
        context = MockContext()

        await servicer.CallTool(request, context)

        mock_source_config_client.list_sources.assert_called_once_with(
            enabled_only=False,
        )
