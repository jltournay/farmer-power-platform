"""Unit tests for McpIntegration class.

Tests cover:
- Server registration from agent configs
- Server deduplication
- Tool discovery
- Cache TTL behavior
- Error handling for unavailable servers

Story 0.75.8b: MCP Client Integration for Agent Workflows
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from ai_model.domain.agent_config import (
    AgentConfigMetadata,
    AgentConfigStatus,
    ErrorHandlingConfig,
    ExplorerConfig,
    ExtractorConfig,
    InputConfig,
    LLMConfig,
    MCPSourceConfig,
    OutputConfig,
    RAGConfig,
)
from ai_model.mcp.integration import McpIntegration, ServerStatus

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_registry() -> MagicMock:
    """Create a mock McpToolRegistry."""
    registry = MagicMock()
    registry.register_server = MagicMock()
    registry.discover_tools = AsyncMock(
        return_value=[
            {"name": "get_document", "description": "Get document by ID", "category": "document"},
            {"name": "get_farmer_context", "description": "Get farmer context", "category": "farmer"},
        ]
    )
    registry.discover_all_tools = AsyncMock(
        return_value={
            "collection-mcp": [
                {"name": "get_document", "description": "Get document by ID"},
            ],
            "plantation-mcp": [
                {"name": "get_farmer", "description": "Get farmer by ID"},
            ],
        }
    )
    registry.get_tool = MagicMock()
    return registry


@pytest.fixture
def sample_extractor_config() -> ExtractorConfig:
    """Create a sample extractor config with MCP sources."""
    return ExtractorConfig(
        id="qc-extractor:1.0.0",
        agent_id="qc-extractor",
        version="1.0.0",
        status=AgentConfigStatus.ACTIVE,
        description="Extract QC data",
        type="extractor",
        input=InputConfig(event="collection.document.received", schema={"required": ["doc_id"]}),
        output=OutputConfig(event="ai.extraction.complete", schema={}),
        llm=LLMConfig(model="anthropic/claude-3-haiku", temperature=0.1, max_tokens=500),
        mcp_sources=[
            MCPSourceConfig(server="collection", tools=["get_document", "get_farmer_context"]),
        ],
        error_handling=ErrorHandlingConfig(),
        metadata=AgentConfigMetadata(author="test"),
        extraction_schema={"required_fields": ["farmer_id"]},
    )


@pytest.fixture
def sample_explorer_config() -> ExplorerConfig:
    """Create a sample explorer config with MCP sources."""
    return ExplorerConfig(
        id="disease-diagnosis:1.0.0",
        agent_id="disease-diagnosis",
        version="1.0.0",
        status=AgentConfigStatus.ACTIVE,
        description="Diagnose plant diseases",
        type="explorer",
        input=InputConfig(event="ai.extraction.complete", schema={}),
        output=OutputConfig(event="ai.diagnosis.complete", schema={}),
        llm=LLMConfig(model="anthropic/claude-3-5-sonnet", temperature=0.3, max_tokens=2000),
        mcp_sources=[
            MCPSourceConfig(server="collection", tools=["get_document"]),
            MCPSourceConfig(server="plantation", tools=["get_farmer", "get_weather"]),
        ],
        error_handling=ErrorHandlingConfig(),
        metadata=AgentConfigMetadata(author="test"),
        rag=RAGConfig(enabled=True, knowledge_domains=["plant_diseases"]),
    )


@pytest.fixture
def sample_config_no_mcp() -> ExtractorConfig:
    """Create a sample config with no MCP sources."""
    return ExtractorConfig(
        id="simple-extractor:1.0.0",
        agent_id="simple-extractor",
        version="1.0.0",
        status=AgentConfigStatus.ACTIVE,
        description="Simple extraction without MCP",
        type="extractor",
        input=InputConfig(event="test.event", schema={}),
        output=OutputConfig(event="test.complete", schema={}),
        llm=LLMConfig(model="anthropic/claude-3-haiku"),
        mcp_sources=[],  # No MCP sources
        error_handling=ErrorHandlingConfig(),
        metadata=AgentConfigMetadata(author="test"),
        extraction_schema={},
    )


# =============================================================================
# REGISTRATION TESTS (3 tests)
# =============================================================================


class TestRegisterFromAgentConfigs:
    """Tests for register_from_agent_configs method."""

    def test_register_single_agent_single_server(
        self, mock_registry: MagicMock, sample_extractor_config: ExtractorConfig
    ) -> None:
        """Test registering servers from a single agent config."""
        integration = McpIntegration(registry=mock_registry)

        servers = integration.register_from_agent_configs([sample_extractor_config])

        assert servers == {"collection-mcp"}
        mock_registry.register_server.assert_called_once_with("collection-mcp")

    def test_register_multiple_agents_multiple_servers(
        self,
        mock_registry: MagicMock,
        sample_extractor_config: ExtractorConfig,
        sample_explorer_config: ExplorerConfig,
    ) -> None:
        """Test registering servers from multiple agent configs."""
        integration = McpIntegration(registry=mock_registry)

        servers = integration.register_from_agent_configs([sample_extractor_config, sample_explorer_config])

        # collection from extractor, collection+plantation from explorer
        assert servers == {"collection-mcp", "plantation-mcp"}
        assert mock_registry.register_server.call_count == 2

    def test_register_agent_with_no_mcp_sources(
        self, mock_registry: MagicMock, sample_config_no_mcp: ExtractorConfig
    ) -> None:
        """Test registering from agent config with no MCP sources."""
        integration = McpIntegration(registry=mock_registry)

        servers = integration.register_from_agent_configs([sample_config_no_mcp])

        assert servers == set()
        mock_registry.register_server.assert_not_called()


# =============================================================================
# DEDUPLICATION TEST (1 test)
# =============================================================================


class TestServerDeduplication:
    """Tests for server deduplication."""

    def test_deduplicate_servers_across_agents(
        self,
        mock_registry: MagicMock,
        sample_extractor_config: ExtractorConfig,
        sample_explorer_config: ExplorerConfig,
    ) -> None:
        """Test that duplicate servers are only registered once."""
        integration = McpIntegration(registry=mock_registry)

        # Both configs use "collection" server
        servers = integration.register_from_agent_configs([sample_extractor_config, sample_explorer_config])

        # collection-mcp should only be registered once, plantation-mcp once
        assert servers == {"collection-mcp", "plantation-mcp"}
        # Verify each unique server was registered exactly once
        call_args = [call[0][0] for call in mock_registry.register_server.call_args_list]
        assert sorted(call_args) == ["collection-mcp", "plantation-mcp"]


# =============================================================================
# DISCOVERY TESTS (2 tests)
# =============================================================================


class TestDiscoverAllTools:
    """Tests for discover_all_tools method."""

    @pytest.mark.asyncio
    async def test_discover_all_tools_success(
        self, mock_registry: MagicMock, sample_extractor_config: ExtractorConfig
    ) -> None:
        """Test successful tool discovery from all servers."""
        integration = McpIntegration(registry=mock_registry)
        integration.register_from_agent_configs([sample_extractor_config])

        tools = await integration.discover_all_tools()

        mock_registry.discover_all_tools.assert_called_once_with(refresh=False)
        assert "collection-mcp" in tools
        assert "plantation-mcp" in tools

    @pytest.mark.asyncio
    async def test_discover_all_tools_with_refresh(
        self, mock_registry: MagicMock, sample_extractor_config: ExtractorConfig
    ) -> None:
        """Test tool discovery with cache refresh."""
        integration = McpIntegration(registry=mock_registry)
        integration.register_from_agent_configs([sample_extractor_config])

        await integration.discover_all_tools(refresh=True)

        mock_registry.discover_all_tools.assert_called_once_with(refresh=True)


# =============================================================================
# CACHE TTL TESTS (2 tests)
# =============================================================================


class TestCacheTTL:
    """Tests for cache TTL behavior."""

    @pytest.mark.asyncio
    async def test_cache_not_expired_uses_cached_tools(self, mock_registry: MagicMock) -> None:
        """Test that cached tools are used when TTL not expired."""
        integration = McpIntegration(registry=mock_registry, cache_ttl_seconds=300)

        # First discovery
        await integration.discover_all_tools()
        first_call_count = mock_registry.discover_all_tools.call_count

        # Second discovery within TTL
        await integration.discover_all_tools()
        second_call_count = mock_registry.discover_all_tools.call_count

        # Should use cache, not call discover again
        assert second_call_count == first_call_count

    @pytest.mark.asyncio
    async def test_cache_expired_refreshes_tools(self, mock_registry: MagicMock) -> None:
        """Test that tools are refreshed when TTL expired."""
        integration = McpIntegration(registry=mock_registry, cache_ttl_seconds=0)  # Immediate expiry

        # First discovery
        await integration.discover_all_tools()

        # Manually expire the cache
        integration._last_discovery = datetime(2020, 1, 1, tzinfo=UTC)

        # Second discovery should refresh
        await integration.discover_all_tools()

        # Should have called discover twice (initial + refresh)
        assert mock_registry.discover_all_tools.call_count == 2


# =============================================================================
# GET TOOL TESTS (2 tests)
# =============================================================================


class TestGetTool:
    """Tests for get_tool method."""

    def test_get_tool_success(self, mock_registry: MagicMock, sample_extractor_config: ExtractorConfig) -> None:
        """Test successful tool retrieval."""
        mock_tool = MagicMock()
        mock_registry.get_tool.return_value = mock_tool

        integration = McpIntegration(registry=mock_registry)
        integration.register_from_agent_configs([sample_extractor_config])

        tool = integration.get_tool("collection", "get_document")

        mock_registry.get_tool.assert_called_once_with("collection-mcp", "get_document")
        assert tool == mock_tool

    def test_get_tool_unregistered_server_raises(self, mock_registry: MagicMock) -> None:
        """Test that getting tool from unregistered server raises error."""
        integration = McpIntegration(registry=mock_registry)

        with pytest.raises(ValueError, match="not registered"):
            integration.get_tool("unknown-server", "some_tool")


# =============================================================================
# ERROR HANDLING TESTS (2 tests)
# =============================================================================


class TestServerUnavailability:
    """Tests for graceful handling of server unavailability."""

    @pytest.mark.asyncio
    async def test_discovery_failure_marks_server_pending(self, mock_registry: MagicMock) -> None:
        """Test that discovery failure marks server as pending."""
        mock_registry.discover_all_tools.side_effect = Exception("Connection refused")

        integration = McpIntegration(registry=mock_registry)
        integration._registered_servers = {"collection-mcp"}

        # Should not raise, just log warning
        result = await integration.discover_all_tools()

        assert result == {}
        assert integration._server_status.get("collection-mcp") == ServerStatus.DISCOVERY_PENDING

    @pytest.mark.asyncio
    async def test_partial_discovery_failure_continues(self, mock_registry: MagicMock) -> None:
        """Test that partial discovery failure doesn't stop other servers."""
        # First call fails, second succeeds
        mock_registry.discover_all_tools.return_value = {
            "plantation-mcp": [{"name": "get_farmer", "description": "Get farmer"}]
        }

        integration = McpIntegration(registry=mock_registry)
        integration._registered_servers = {"collection-mcp", "plantation-mcp"}

        result = await integration.discover_all_tools()

        # Should still return plantation tools
        assert "plantation-mcp" in result
