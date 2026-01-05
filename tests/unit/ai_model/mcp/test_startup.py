"""Unit tests for MCP integration startup.

Tests cover:
- MCP integration initialization in lifespan
- Tools availability in app.state

Story 0.75.8b: MCP Client Integration for Agent Workflows
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from ai_model.domain.agent_config import (
    AgentConfigMetadata,
    AgentConfigStatus,
    ErrorHandlingConfig,
    ExtractorConfig,
    InputConfig,
    LLMConfig,
    MCPSourceConfig,
    OutputConfig,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_agent_config_cache() -> MagicMock:
    """Create a mock AgentConfigCache."""
    cache = MagicMock()
    cache.get_all = AsyncMock(
        return_value=[
            ExtractorConfig(
                id="qc-extractor:1.0.0",
                agent_id="qc-extractor",
                version="1.0.0",
                status=AgentConfigStatus.ACTIVE,
                description="Extract QC data",
                type="extractor",
                input=InputConfig(event="collection.document.received", schema={}),
                output=OutputConfig(event="ai.extraction.complete", schema={}),
                llm=LLMConfig(model="anthropic/claude-3-haiku"),
                mcp_sources=[MCPSourceConfig(server="collection", tools=["get_document"])],
                error_handling=ErrorHandlingConfig(),
                metadata=AgentConfigMetadata(author="test"),
                extraction_schema={},
            )
        ]
    )
    return cache


# =============================================================================
# STARTUP TESTS (2 tests)
# =============================================================================


class TestMcpStartupIntegration:
    """Tests for MCP integration during lifespan startup."""

    @pytest.mark.asyncio
    async def test_mcp_integration_initializes_from_agent_configs(self, mock_agent_config_cache: MagicMock) -> None:
        """Test that MCP integration initializes from cached agent configs."""
        from ai_model.mcp.integration import McpIntegration

        # Create integration
        integration = McpIntegration()

        # Get configs from cache
        configs = await mock_agent_config_cache.get_all()

        # Register servers from configs
        servers = integration.register_from_agent_configs(configs)

        # Verify server was registered
        assert "collection-mcp" in servers

    @pytest.mark.asyncio
    async def test_mcp_integration_handles_empty_configs(self) -> None:
        """Test that MCP integration handles empty config list gracefully."""
        from ai_model.mcp.integration import McpIntegration

        integration = McpIntegration()
        servers = integration.register_from_agent_configs([])

        assert servers == set()


# =============================================================================
# APP STATE TEST (1 test)
# =============================================================================


class TestAppStateAvailability:
    """Tests for tools availability in app.state."""

    def test_tool_provider_created_from_integration(self) -> None:
        """Test that AgentToolProvider can be created from McpIntegration."""
        from ai_model.mcp.integration import McpIntegration
        from ai_model.mcp.provider import AgentToolProvider

        integration = McpIntegration()
        provider = AgentToolProvider(integration)

        # Provider should be usable
        assert provider._integration is integration
