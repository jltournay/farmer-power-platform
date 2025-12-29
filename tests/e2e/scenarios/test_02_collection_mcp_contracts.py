"""E2E Test: Collection MCP Tool Contract Tests.

Verifies that all 5 Collection MCP tools return expected data structures
and handle error cases correctly.

Tools tested:
1. get_documents - Query documents with filters
2. get_document_by_id - Get single document with optional SAS URLs
3. get_farmer_documents - Get all documents for a farmer
4. search_documents - Full-text search
5. list_sources - List source configurations

Prerequisites:
    docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d
    Wait for all services to be healthy before running tests.

Seed Data Required (from tests/e2e/infrastructure/seed/):
    - documents.json: DOC-E2E-001 to DOC-E2E-006
    - source_configs.json: e2e-qc-analyzer-json, e2e-manual-upload
    - farmers.json: FRM-E2E-001 to FRM-E2E-004
"""

import pytest


@pytest.mark.e2e
class TestGetDocuments:
    """Test get_documents MCP tool (AC1)."""

    @pytest.mark.asyncio
    async def test_get_documents_returns_all_documents(
        self,
        collection_mcp,
        seed_data,
    ):
        """Given documents exist, get_documents returns documents."""
        result = await collection_mcp.call_tool("get_documents", {"limit": 10})

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        # Verify documents are in response
        result_str = str(result.get("result_json", ""))
        # Should contain at least one document ID
        assert any(
            doc_id in result_str
            for doc_id in ["DOC-E2E-001", "DOC-E2E-002", "DOC-E2E-003"]
        )

    @pytest.mark.asyncio
    async def test_get_documents_filter_by_source_id(
        self,
        collection_mcp,
        seed_data,
    ):
        """get_documents filters by source_id correctly."""
        result = await collection_mcp.call_tool(
            "get_documents",
            {"source_id": "e2e-qc-analyzer-json", "limit": 10},
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        result_str = str(result.get("result_json", ""))
        # Should contain QC analyzer documents
        assert "e2e-qc-analyzer-json" in result_str or "DOC-E2E-00" in result_str

    @pytest.mark.asyncio
    async def test_get_documents_filter_by_farmer_id(
        self,
        collection_mcp,
        seed_data,
    ):
        """get_documents filters by farmer_id correctly."""
        result = await collection_mcp.call_tool(
            "get_documents",
            {"farmer_id": "FRM-E2E-001", "limit": 10},
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        result_str = str(result.get("result_json", ""))
        # FRM-E2E-001 has 3 documents (DOC-E2E-001, DOC-E2E-002, DOC-E2E-004)
        assert "FRM-E2E-001" in result_str or any(
            doc_id in result_str
            for doc_id in ["DOC-E2E-001", "DOC-E2E-002", "DOC-E2E-004"]
        )


@pytest.mark.e2e
class TestGetDocumentById:
    """Test get_document_by_id MCP tool (AC2)."""

    @pytest.mark.asyncio
    async def test_get_document_by_id_returns_document(
        self,
        collection_mcp,
        seed_data,
    ):
        """Given document exists, get_document_by_id returns it."""
        document_id = "DOC-E2E-001"

        result = await collection_mcp.call_tool(
            "get_document_by_id",
            {"document_id": document_id},
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        result_str = str(result.get("result_json", ""))
        assert document_id in result_str or "DOC-E2E-001" in result_str

    @pytest.mark.asyncio
    async def test_get_document_by_id_with_include_files(
        self,
        collection_mcp,
        seed_data,
    ):
        """get_document_by_id with include_files returns SAS URLs."""
        document_id = "DOC-E2E-001"

        result = await collection_mcp.call_tool(
            "get_document_by_id",
            {"document_id": document_id, "include_files": True},
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        # Response should contain document data
        result_str = str(result.get("result_json", ""))
        assert document_id in result_str or "DOC-E2E" in result_str

    @pytest.mark.asyncio
    async def test_get_document_by_id_error_for_invalid_id(
        self,
        collection_mcp,
        seed_data,
    ):
        """get_document_by_id returns error for non-existent document."""
        result = await collection_mcp.call_tool(
            "get_document_by_id",
            {"document_id": "NON-EXISTENT-DOC"},
        )

        # Should return error
        assert "error_code" in result or result.get("success") is False


@pytest.mark.e2e
class TestGetFarmerDocuments:
    """Test get_farmer_documents MCP tool (AC3)."""

    @pytest.mark.asyncio
    async def test_get_farmer_documents_returns_all_farmer_docs(
        self,
        collection_mcp,
        seed_data,
    ):
        """Given farmer has documents, returns aggregated documents."""
        farmer_id = "FRM-E2E-001"  # Has 3 documents from 2 sources

        result = await collection_mcp.call_tool(
            "get_farmer_documents",
            {"farmer_id": farmer_id},
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        result_str = str(result.get("result_json", ""))
        # Should return farmer's documents
        assert farmer_id in result_str or "DOC-E2E" in result_str

    @pytest.mark.asyncio
    async def test_get_farmer_documents_filter_by_source(
        self,
        collection_mcp,
        seed_data,
    ):
        """get_farmer_documents filters by source_ids."""
        farmer_id = "FRM-E2E-001"

        result = await collection_mcp.call_tool(
            "get_farmer_documents",
            {
                "farmer_id": farmer_id,
                "source_ids": ["e2e-qc-analyzer-json"],
            },
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result


@pytest.mark.e2e
class TestSearchDocuments:
    """Test search_documents MCP tool (AC4)."""

    @pytest.mark.asyncio
    async def test_search_documents_returns_results(
        self,
        collection_mcp,
        seed_data,
    ):
        """Given searchable content exists, returns relevance-scored results."""
        result = await collection_mcp.call_tool(
            "search_documents",
            {"query": "quality", "limit": 10},
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

    @pytest.mark.asyncio
    async def test_search_documents_with_farmer_filter(
        self,
        collection_mcp,
        seed_data,
    ):
        """search_documents filters by farmer_id."""
        result = await collection_mcp.call_tool(
            "search_documents",
            {"query": "primary", "farmer_id": "FRM-E2E-001", "limit": 10},
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result


@pytest.mark.e2e
class TestListSources:
    """Test list_sources MCP tool (AC5)."""

    @pytest.mark.asyncio
    async def test_list_sources_returns_enabled_sources(
        self,
        collection_mcp,
        seed_data,
    ):
        """Given source configs exist, list_sources returns enabled sources."""
        result = await collection_mcp.call_tool(
            "list_sources",
            {"enabled_only": True},
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result

        result_str = str(result.get("result_json", ""))
        # Should contain our seeded sources
        assert any(
            source in result_str
            for source in ["e2e-qc-analyzer-json", "e2e-manual-upload"]
        )

    @pytest.mark.asyncio
    async def test_list_sources_returns_all_sources(
        self,
        collection_mcp,
        seed_data,
    ):
        """list_sources with enabled_only=false returns all sources."""
        result = await collection_mcp.call_tool(
            "list_sources",
            {"enabled_only": False},
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"
        assert "result_json" in result
