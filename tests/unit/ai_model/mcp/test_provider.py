"""Unit tests for AgentToolProvider class.

Tests cover:
- Tool resolution from agent config
- Empty mcp_sources handling
- Multiple sources with multiple tools
- Tool filtering
- Error propagation

Story 0.75.8b: MCP Client Integration for Agent Workflows
"""

from unittest.mock import MagicMock

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
from ai_model.mcp.integration import McpIntegration
from ai_model.mcp.provider import AgentToolProvider

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_integration() -> MagicMock:
    """Create a mock McpIntegration."""
    integration = MagicMock(spec=McpIntegration)
    return integration


@pytest.fixture
def mock_tool() -> MagicMock:
    """Create a mock GrpcMcpTool."""
    tool = MagicMock()
    tool.name = "get_document"
    return tool


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
    """Create a sample explorer config with multiple MCP sources."""
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
# GET TOOLS FOR AGENT TESTS (3 tests)
# =============================================================================


class TestGetToolsForAgent:
    """Tests for get_tools_for_agent method."""

    def test_get_tools_returns_correct_tools(
        self,
        mock_integration: MagicMock,
        mock_tool: MagicMock,
        sample_extractor_config: ExtractorConfig,
    ) -> None:
        """Test that correct tools are returned for agent config."""
        mock_integration.get_tool.return_value = mock_tool
        provider = AgentToolProvider(mock_integration)

        tools = provider.get_tools_for_agent(sample_extractor_config)

        # Should have 2 tools (get_document, get_farmer_context)
        assert len(tools) == 2
        assert mock_integration.get_tool.call_count == 2

    def test_get_tools_calls_integration_with_correct_params(
        self,
        mock_integration: MagicMock,
        mock_tool: MagicMock,
        sample_extractor_config: ExtractorConfig,
    ) -> None:
        """Test that integration is called with correct server and tool names."""
        mock_integration.get_tool.return_value = mock_tool
        provider = AgentToolProvider(mock_integration)

        provider.get_tools_for_agent(sample_extractor_config)

        # Verify calls were made with correct parameters
        calls = mock_integration.get_tool.call_args_list
        assert calls[0][0] == ("collection", "get_document")
        assert calls[1][0] == ("collection", "get_farmer_context")

    def test_get_tools_preserves_order(
        self,
        mock_integration: MagicMock,
        sample_extractor_config: ExtractorConfig,
    ) -> None:
        """Test that tools are returned in config order."""
        tool1 = MagicMock()
        tool1.name = "get_document"
        tool2 = MagicMock()
        tool2.name = "get_farmer_context"
        mock_integration.get_tool.side_effect = [tool1, tool2]

        provider = AgentToolProvider(mock_integration)
        tools = provider.get_tools_for_agent(sample_extractor_config)

        assert tools[0].name == "get_document"
        assert tools[1].name == "get_farmer_context"


# =============================================================================
# EMPTY MCP SOURCES TEST (1 test)
# =============================================================================


class TestEmptyMcpSources:
    """Tests for agents with no MCP sources."""

    def test_empty_mcp_sources_returns_empty_list(
        self,
        mock_integration: MagicMock,
        sample_config_no_mcp: ExtractorConfig,
    ) -> None:
        """Test that agent with no MCP sources returns empty list."""
        provider = AgentToolProvider(mock_integration)

        tools = provider.get_tools_for_agent(sample_config_no_mcp)

        assert tools == []
        mock_integration.get_tool.assert_not_called()


# =============================================================================
# MULTIPLE SOURCES TESTS (2 tests)
# =============================================================================


class TestMultipleSources:
    """Tests for agents with multiple MCP sources."""

    def test_multiple_sources_all_tools_returned(
        self,
        mock_integration: MagicMock,
        mock_tool: MagicMock,
        sample_explorer_config: ExplorerConfig,
    ) -> None:
        """Test that tools from all sources are returned."""
        mock_integration.get_tool.return_value = mock_tool
        provider = AgentToolProvider(mock_integration)

        tools = provider.get_tools_for_agent(sample_explorer_config)

        # Should have 3 tools: get_document from collection, get_farmer + get_weather from plantation
        assert len(tools) == 3

    def test_multiple_sources_correct_server_mapping(
        self,
        mock_integration: MagicMock,
        mock_tool: MagicMock,
        sample_explorer_config: ExplorerConfig,
    ) -> None:
        """Test that tools are retrieved from correct servers."""
        mock_integration.get_tool.return_value = mock_tool
        provider = AgentToolProvider(mock_integration)

        provider.get_tools_for_agent(sample_explorer_config)

        # Verify server names in calls
        calls = mock_integration.get_tool.call_args_list
        # First source: collection -> get_document
        assert calls[0][0] == ("collection", "get_document")
        # Second source: plantation -> get_farmer, get_weather
        assert calls[1][0] == ("plantation", "get_farmer")
        assert calls[2][0] == ("plantation", "get_weather")


# =============================================================================
# TOOL FILTERING TESTS (2 tests)
# =============================================================================


class TestToolFiltering:
    """Tests for tool filtering by configured list."""

    def test_only_configured_tools_returned(
        self,
        mock_integration: MagicMock,
        mock_tool: MagicMock,
    ) -> None:
        """Test that only tools in config are returned, not all server tools."""
        # Config only requests get_document, not all collection tools
        config = ExtractorConfig(
            id="selective:1.0.0",
            agent_id="selective",
            version="1.0.0",
            status=AgentConfigStatus.ACTIVE,
            description="Selective tools",
            type="extractor",
            input=InputConfig(event="test", schema={}),
            output=OutputConfig(event="test.done", schema={}),
            llm=LLMConfig(model="anthropic/claude-3-haiku"),
            mcp_sources=[
                MCPSourceConfig(server="collection", tools=["get_document"]),  # Only one tool
            ],
            error_handling=ErrorHandlingConfig(),
            metadata=AgentConfigMetadata(author="test"),
            extraction_schema={},
        )

        mock_integration.get_tool.return_value = mock_tool
        provider = AgentToolProvider(mock_integration)

        tools = provider.get_tools_for_agent(config)

        # Only one tool requested
        assert len(tools) == 1
        mock_integration.get_tool.assert_called_once_with("collection", "get_document")

    def test_duplicate_tools_across_sources_all_included(
        self,
        mock_integration: MagicMock,
    ) -> None:
        """Test that same tool from different sources returns separate instances."""
        # Hypothetical config with same tool name from different servers
        config = ExtractorConfig(
            id="duplicate:1.0.0",
            agent_id="duplicate",
            version="1.0.0",
            status=AgentConfigStatus.ACTIVE,
            description="Duplicate tools",
            type="extractor",
            input=InputConfig(event="test", schema={}),
            output=OutputConfig(event="test.done", schema={}),
            llm=LLMConfig(model="anthropic/claude-3-haiku"),
            mcp_sources=[
                MCPSourceConfig(server="collection", tools=["get_context"]),
                MCPSourceConfig(server="plantation", tools=["get_context"]),  # Same tool name
            ],
            error_handling=ErrorHandlingConfig(),
            metadata=AgentConfigMetadata(author="test"),
            extraction_schema={},
        )

        tool1 = MagicMock()
        tool1.name = "get_context"
        tool2 = MagicMock()
        tool2.name = "get_context"
        mock_integration.get_tool.side_effect = [tool1, tool2]

        provider = AgentToolProvider(mock_integration)
        tools = provider.get_tools_for_agent(config)

        # Both tools should be returned (different server instances)
        assert len(tools) == 2


# =============================================================================
# ERROR PROPAGATION TESTS (2 tests)
# =============================================================================


class TestErrorPropagation:
    """Tests for error propagation from integration."""

    def test_value_error_propagates(
        self,
        mock_integration: MagicMock,
        sample_extractor_config: ExtractorConfig,
    ) -> None:
        """Test that ValueError from integration propagates."""
        mock_integration.get_tool.side_effect = ValueError("Server not registered")
        provider = AgentToolProvider(mock_integration)

        with pytest.raises(ValueError, match="Server not registered"):
            provider.get_tools_for_agent(sample_extractor_config)

    def test_runtime_error_propagates(
        self,
        mock_integration: MagicMock,
        sample_extractor_config: ExtractorConfig,
    ) -> None:
        """Test that RuntimeError from integration propagates."""
        mock_integration.get_tool.side_effect = RuntimeError("Tool discovery failed")
        provider = AgentToolProvider(mock_integration)

        with pytest.raises(RuntimeError, match="Tool discovery failed"):
            provider.get_tools_for_agent(sample_extractor_config)
