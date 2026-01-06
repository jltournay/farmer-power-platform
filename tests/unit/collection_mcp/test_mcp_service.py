"""Tests for Collection MCP Tool Service."""

import json
from datetime import UTC, datetime
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
from fp_common.models import (
    Document,
    ExtractionMetadata,
    IngestionMetadata,
    RawDocumentRef,
    SearchResult,
)


def _create_test_document(
    document_id: str = "doc-001",
    source_id: str = "qc-analyzer-result",
    **kwargs: Any,
) -> Document:
    """Create a test Document Pydantic model for unit tests."""
    now = datetime.now(UTC)
    return Document(
        document_id=document_id,
        raw_document=RawDocumentRef(
            blob_container="raw",
            blob_path=f"path/{document_id}",
            content_hash="abc123",
            size_bytes=1024,
            stored_at=now,
        ),
        extraction=ExtractionMetadata(
            ai_agent_id="test-agent",
            extraction_timestamp=now,
            confidence=0.95,
            validation_passed=True,
        ),
        ingestion=IngestionMetadata(
            ingestion_id=f"ing-{document_id}",
            source_id=source_id,
            received_at=now,
            processed_at=now,
        ),
        extracted_fields=kwargs.get("extracted_fields", {}),
        linkage_fields=kwargs.get("linkage_fields", {}),
        created_at=now,
    )


def _create_test_search_result(
    document_id: str = "doc-001",
    source_id: str = "qc-analyzer-result",
    relevance_score: float = 1.0,
    **kwargs: Any,
) -> SearchResult:
    """Create a test SearchResult Pydantic model for unit tests."""
    now = datetime.now(UTC)
    return SearchResult(
        document_id=document_id,
        raw_document=RawDocumentRef(
            blob_container="raw",
            blob_path=f"path/{document_id}",
            content_hash="abc123",
            size_bytes=1024,
            stored_at=now,
        ),
        extraction=ExtractionMetadata(
            ai_agent_id="test-agent",
            extraction_timestamp=now,
            confidence=0.95,
            validation_passed=True,
        ),
        ingestion=IngestionMetadata(
            ingestion_id=f"ing-{document_id}",
            source_id=source_id,
            received_at=now,
            processed_at=now,
        ),
        extracted_fields=kwargs.get("extracted_fields", {}),
        linkage_fields=kwargs.get("linkage_fields", {}),
        created_at=now,
        relevance_score=relevance_score,
    )


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
    client.get_source = AsyncMock(return_value=None)
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
        """Verify get_documents returns Document Pydantic models serialized as JSON."""
        # DocumentClient now returns Pydantic Document models (Story 0.6.12)
        mock_docs = [
            _create_test_document("doc-001", "qc-analyzer-result"),
            _create_test_document("doc-002", "qc-analyzer-result"),
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
            collection_name=None,
        )


class TestGetDocumentByIdHandler:
    """Tests for get_document_by_id tool handler."""

    @pytest.mark.asyncio
    async def test_get_document_by_id_success(
        self,
        servicer: McpToolServiceServicer,
        mock_document_client: MagicMock,
    ) -> None:
        """Verify get_document_by_id returns Document Pydantic model serialized as JSON."""
        # DocumentClient now returns Pydantic Document models (Story 0.6.12)
        mock_doc = _create_test_document(
            "qc-analyzer/batch-001/leaf_001",
            "qc-analyzer-exceptions",
            extracted_fields={"issue": "coarse leaf"},
        )
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
    async def test_get_document_by_id_with_include_files_flag(
        self,
        servicer: McpToolServiceServicer,
        mock_document_client: MagicMock,
    ) -> None:
        """Verify get_document_by_id handles include_files flag without error.

        Note: File enrichment is no longer supported with Pydantic Document models
        per Story 0.6.12. The include_files flag is accepted for API compatibility
        but no longer triggers SAS URL enrichment.
        """
        mock_doc = _create_test_document("doc-001", "qc-analyzer-exceptions")
        mock_document_client.get_document_by_id.return_value = mock_doc

        request = MockToolCallRequest(
            tool_name="get_document_by_id",
            arguments={"document_id": "doc-001", "include_files": True},
        )
        context = MockContext()

        response = await servicer.CallTool(request, context)

        # Should succeed - include_files is accepted but no longer triggers enrichment
        assert response.success is True
        result = json.loads(response.result_json)
        assert result["document"]["document_id"] == "doc-001"

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
        """Verify get_farmer_documents returns Document Pydantic models serialized as JSON."""
        # DocumentClient now returns Pydantic Document models (Story 0.6.12)
        mock_docs = [
            _create_test_document("doc-001", linkage_fields={"farmer_id": "WM-4521"}),
            _create_test_document("doc-002", linkage_fields={"farmer_id": "WM-4521"}),
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
        """Verify search_documents returns SearchResult Pydantic models serialized as JSON."""
        # DocumentClient now returns Pydantic SearchResult models (Story 0.6.12)
        mock_docs = [
            _create_test_search_result("doc-001", relevance_score=0.95),
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
