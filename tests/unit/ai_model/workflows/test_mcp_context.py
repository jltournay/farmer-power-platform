"""Unit tests for MCP context fetching in workflows.

Story 0.75.16b: Event Subscriber Workflow Wiring

Tests for:
- _fetch_mcp_context in ExplorerWorkflow
- _fetch_mcp_context in GeneratorWorkflow
- tool_provider vs mcp_integration preference
- Graceful handling of unavailable servers/tools
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from ai_model.workflows.explorer import ExplorerWorkflow
from ai_model.workflows.generator import GeneratorWorkflow

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_llm_gateway() -> MagicMock:
    """Mock LLM gateway."""
    gateway = MagicMock()
    gateway.chat = AsyncMock(
        return_value={
            "content": "test response",
            "model": "test-model",
            "tokens_in": 10,
            "tokens_out": 20,
        }
    )
    return gateway


@pytest.fixture
def mock_tool() -> MagicMock:
    """Mock MCP tool that can be invoked."""
    tool = MagicMock()
    tool.ainvoke = AsyncMock(return_value={"data": "tool_result"})
    return tool


@pytest.fixture
def mock_tool_provider(mock_tool: MagicMock) -> MagicMock:
    """Mock AgentToolProvider."""
    provider = MagicMock()
    provider.get_tool = MagicMock(return_value=mock_tool)
    return provider


@pytest.fixture
def mock_mcp_integration(mock_tool: MagicMock) -> MagicMock:
    """Mock MCPIntegration."""
    integration = MagicMock()
    integration.get_tool = MagicMock(return_value=mock_tool)
    return integration


@pytest.fixture
def explorer_workflow(mock_llm_gateway: MagicMock) -> ExplorerWorkflow:
    """Create ExplorerWorkflow without MCP/tool_provider for base testing."""
    return ExplorerWorkflow(llm_gateway=mock_llm_gateway)


@pytest.fixture
def generator_workflow(mock_llm_gateway: MagicMock) -> GeneratorWorkflow:
    """Create GeneratorWorkflow without MCP/tool_provider for base testing."""
    return GeneratorWorkflow(llm_gateway=mock_llm_gateway)


# =============================================================================
# ExplorerWorkflow MCP Context Tests
# =============================================================================


class TestExplorerWorkflowMcpContext:
    """Tests for ExplorerWorkflow._fetch_mcp_context."""

    @pytest.mark.asyncio
    async def test_fetch_mcp_context_returns_empty_when_no_sources(
        self,
        explorer_workflow: ExplorerWorkflow,
    ) -> None:
        """Test empty dict returned when no mcp_sources provided."""
        result = await explorer_workflow._fetch_mcp_context([], {})
        assert result == {}

    @pytest.mark.asyncio
    async def test_fetch_mcp_context_returns_empty_when_no_provider(
        self,
        mock_llm_gateway: MagicMock,
    ) -> None:
        """Test empty dict returned when neither tool_provider nor mcp_integration set."""
        workflow = ExplorerWorkflow(llm_gateway=mock_llm_gateway)
        mcp_sources = [{"server": "test-server", "tool": "test-tool"}]

        result = await workflow._fetch_mcp_context(mcp_sources, {})
        assert result == {}

    @pytest.mark.asyncio
    async def test_fetch_mcp_context_prefers_tool_provider(
        self,
        mock_llm_gateway: MagicMock,
        mock_tool_provider: MagicMock,
        mock_mcp_integration: MagicMock,
        mock_tool: MagicMock,
    ) -> None:
        """Test tool_provider is preferred over mcp_integration."""
        workflow = ExplorerWorkflow(
            llm_gateway=mock_llm_gateway,
            mcp_integration=mock_mcp_integration,
            tool_provider=mock_tool_provider,
        )

        mcp_sources = [{"server": "test-server", "tool": "test-tool", "arg_mapping": {}}]

        result = await workflow._fetch_mcp_context(mcp_sources, {})

        # tool_provider should be called, not mcp_integration
        mock_tool_provider.get_tool.assert_called_once_with("test-server", "test-tool")
        mock_mcp_integration.get_tool.assert_not_called()
        assert "test-server.test-tool" in result

    @pytest.mark.asyncio
    async def test_fetch_mcp_context_falls_back_to_mcp_integration(
        self,
        mock_llm_gateway: MagicMock,
        mock_mcp_integration: MagicMock,
        mock_tool: MagicMock,
    ) -> None:
        """Test fallback to mcp_integration when tool_provider not set."""
        workflow = ExplorerWorkflow(
            llm_gateway=mock_llm_gateway,
            mcp_integration=mock_mcp_integration,
            tool_provider=None,
        )

        mcp_sources = [{"server": "test-server", "tool": "test-tool", "arg_mapping": {}}]

        result = await workflow._fetch_mcp_context(mcp_sources, {})

        mock_mcp_integration.get_tool.assert_called_once()
        assert "test-server.test-tool" in result

    @pytest.mark.asyncio
    async def test_fetch_mcp_context_with_arg_mapping(
        self,
        mock_llm_gateway: MagicMock,
        mock_tool_provider: MagicMock,
        mock_tool: MagicMock,
    ) -> None:
        """Test arg_mapping correctly maps input_data to tool args."""
        workflow = ExplorerWorkflow(
            llm_gateway=mock_llm_gateway,
            tool_provider=mock_tool_provider,
        )

        mcp_sources = [
            {
                "server": "plantation-mcp",
                "tool": "get_farmer",
                "arg_mapping": {"farmer_id": "linkage_farmer_id"},
            }
        ]
        input_data = {"linkage_farmer_id": "farmer-123", "other_field": "ignored"}

        await workflow._fetch_mcp_context(mcp_sources, input_data)

        # Verify tool was invoked with mapped args
        mock_tool.ainvoke.assert_called_once_with({"farmer_id": "farmer-123"})

    @pytest.mark.asyncio
    async def test_fetch_mcp_context_handles_tool_not_found(
        self,
        mock_llm_gateway: MagicMock,
        mock_tool_provider: MagicMock,
    ) -> None:
        """Test graceful handling when tool not found."""
        mock_tool_provider.get_tool.side_effect = ValueError("Tool not found")

        workflow = ExplorerWorkflow(
            llm_gateway=mock_llm_gateway,
            tool_provider=mock_tool_provider,
        )

        mcp_sources = [{"server": "unknown", "tool": "unknown", "arg_mapping": {}}]

        result = await workflow._fetch_mcp_context(mcp_sources, {})

        # Should return empty dict, not raise
        assert result == {}

    @pytest.mark.asyncio
    async def test_fetch_mcp_context_handles_tool_invocation_error(
        self,
        mock_llm_gateway: MagicMock,
        mock_tool_provider: MagicMock,
        mock_tool: MagicMock,
    ) -> None:
        """Test graceful handling when tool invocation fails."""
        mock_tool.ainvoke.side_effect = Exception("Connection failed")

        workflow = ExplorerWorkflow(
            llm_gateway=mock_llm_gateway,
            tool_provider=mock_tool_provider,
        )

        mcp_sources = [{"server": "test-server", "tool": "test-tool", "arg_mapping": {}}]

        result = await workflow._fetch_mcp_context(mcp_sources, {})

        # Should return empty dict, not raise
        assert result == {}

    @pytest.mark.asyncio
    async def test_fetch_mcp_context_partial_failure(
        self,
        mock_llm_gateway: MagicMock,
    ) -> None:
        """Test partial failure returns successful results only."""
        # Create tools: one succeeds, one fails
        good_tool = MagicMock()
        good_tool.ainvoke = AsyncMock(return_value={"success": True})

        bad_tool = MagicMock()
        bad_tool.ainvoke = AsyncMock(side_effect=Exception("Failed"))

        mock_provider = MagicMock()
        mock_provider.get_tool = MagicMock(
            side_effect=lambda server, tool: good_tool if server == "good" else bad_tool
        )

        workflow = ExplorerWorkflow(
            llm_gateway=mock_llm_gateway,
            tool_provider=mock_provider,
        )

        mcp_sources = [
            {"server": "good", "tool": "tool1", "arg_mapping": {}},
            {"server": "bad", "tool": "tool2", "arg_mapping": {}},
        ]

        result = await workflow._fetch_mcp_context(mcp_sources, {})

        # Only good server result should be present
        assert "good.tool1" in result
        assert "bad.tool2" not in result

    @pytest.mark.asyncio
    async def test_fetch_mcp_context_skips_invalid_sources(
        self,
        mock_llm_gateway: MagicMock,
        mock_tool_provider: MagicMock,
    ) -> None:
        """Test invalid sources (missing server/tool) are skipped."""
        workflow = ExplorerWorkflow(
            llm_gateway=mock_llm_gateway,
            tool_provider=mock_tool_provider,
        )

        mcp_sources = [
            {"server": "", "tool": "test-tool"},  # Missing server
            {"server": "test-server", "tool": ""},  # Missing tool
            {"tool": "test-tool"},  # No server key
        ]

        result = await workflow._fetch_mcp_context(mcp_sources, {})

        # No tools should be called
        mock_tool_provider.get_tool.assert_not_called()
        assert result == {}


# =============================================================================
# GeneratorWorkflow MCP Context Tests
# =============================================================================


class TestGeneratorWorkflowMcpContext:
    """Tests for GeneratorWorkflow._fetch_mcp_context."""

    @pytest.mark.asyncio
    async def test_fetch_mcp_context_returns_empty_when_no_provider(
        self,
        mock_llm_gateway: MagicMock,
    ) -> None:
        """Test empty dict returned when neither tool_provider nor mcp_integration set."""
        workflow = GeneratorWorkflow(llm_gateway=mock_llm_gateway)
        mcp_sources = [{"server": "test-server", "tool": "test-tool"}]

        result = await workflow._fetch_mcp_context(mcp_sources, {})
        assert result == {}

    @pytest.mark.asyncio
    async def test_fetch_mcp_context_prefers_tool_provider(
        self,
        mock_llm_gateway: MagicMock,
        mock_tool_provider: MagicMock,
        mock_mcp_integration: MagicMock,
        mock_tool: MagicMock,
    ) -> None:
        """Test tool_provider is preferred over mcp_integration."""
        workflow = GeneratorWorkflow(
            llm_gateway=mock_llm_gateway,
            mcp_integration=mock_mcp_integration,
            tool_provider=mock_tool_provider,
        )

        mcp_sources = [{"server": "test-server", "tool": "test-tool", "arg_mapping": {}}]

        result = await workflow._fetch_mcp_context(mcp_sources, {})

        mock_tool_provider.get_tool.assert_called_once()
        mock_mcp_integration.get_tool.assert_not_called()
        assert "test-server.test-tool" in result

    @pytest.mark.asyncio
    async def test_fetch_mcp_context_successful_invocation(
        self,
        mock_llm_gateway: MagicMock,
        mock_tool_provider: MagicMock,
        mock_tool: MagicMock,
    ) -> None:
        """Test successful tool invocation returns context."""
        mock_tool.ainvoke = AsyncMock(return_value={"farmer_name": "John Doe"})

        workflow = GeneratorWorkflow(
            llm_gateway=mock_llm_gateway,
            tool_provider=mock_tool_provider,
        )

        mcp_sources = [
            {
                "server": "plantation-mcp",
                "tool": "get_farmer_context",
                "arg_mapping": {"id": "farmer_id"},
            }
        ]
        input_data = {"farmer_id": "farmer-456"}

        result = await workflow._fetch_mcp_context(mcp_sources, input_data)

        assert result == {"plantation-mcp.get_farmer_context": {"farmer_name": "John Doe"}}
        mock_tool.ainvoke.assert_called_once_with({"id": "farmer-456"})

    @pytest.mark.asyncio
    async def test_fetch_mcp_context_handles_errors_gracefully(
        self,
        mock_llm_gateway: MagicMock,
        mock_tool_provider: MagicMock,
        mock_tool: MagicMock,
    ) -> None:
        """Test errors are logged and handled gracefully."""
        mock_tool.ainvoke.side_effect = RuntimeError("Network timeout")

        workflow = GeneratorWorkflow(
            llm_gateway=mock_llm_gateway,
            tool_provider=mock_tool_provider,
        )

        mcp_sources = [{"server": "test", "tool": "failing_tool", "arg_mapping": {}}]

        result = await workflow._fetch_mcp_context(mcp_sources, {})

        # Should not raise, should return empty
        assert result == {}
