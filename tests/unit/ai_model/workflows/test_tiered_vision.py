"""Unit tests for Tiered-Vision workflow.

Tests TieredVisionWorkflow with MCP integration for cost-optimized image analysis.

Story 0.75.16: LangGraph SDK Integration & Base Workflows
Story 0.75.22: MCP integration for image fetching
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from ai_model.domain.agent_config import (
    AgentConfigMetadata,
    InputConfig,
    LLMConfig,
    OutputConfig,
    RAGConfig,
    TieredVisionConfig,
    TieredVisionLLMConfig,
    TieredVisionRoutingConfig,
)
from ai_model.workflows.states.tiered_vision import (
    DiagnoseResult,
    ScreenResult,
    TieredVisionState,
)
from ai_model.workflows.tiered_vision import (
    COLLECTION_MCP_APP_ID,
    TieredVisionWorkflow,
)


@pytest.fixture
def mock_llm_gateway() -> MagicMock:
    """Create a mock LLM gateway."""
    gateway = MagicMock()
    gateway.complete = AsyncMock()
    return gateway


@pytest.fixture
def mock_mcp_client() -> MagicMock:
    """Create a mock MCP client."""
    client = MagicMock()
    client.call_tool = AsyncMock()
    return client


@pytest.fixture
def mock_ranking_service() -> MagicMock:
    """Create a mock ranking service."""
    service = MagicMock()
    service.rank = AsyncMock(return_value=MagicMock(matches=[]))
    return service


@pytest.fixture
def tiered_vision_workflow(
    mock_llm_gateway: MagicMock,
    mock_mcp_client: MagicMock,
    mock_ranking_service: MagicMock,
) -> TieredVisionWorkflow:
    """Create a TieredVisionWorkflow instance."""
    return TieredVisionWorkflow(
        llm_gateway=mock_llm_gateway,
        mcp_client=mock_mcp_client,
        ranking_service=mock_ranking_service,
    )


@pytest.fixture
def tiered_vision_config() -> TieredVisionConfig:
    """Create a test TieredVisionConfig."""
    return TieredVisionConfig(
        id="leaf-quality-analyzer:1.0.0",
        agent_id="leaf-quality-analyzer",
        version="1.0.0",
        description="Cost-optimized image analysis for tea leaf quality",
        input=InputConfig(event="collection.document.received", schema={"type": "object"}),
        output=OutputConfig(event="ai.vision.complete", schema={"type": "object"}),
        llm=None,  # Not used for tiered-vision
        metadata=AgentConfigMetadata(author="test"),
        rag=RAGConfig(enabled=True, knowledge_domains=["plant_diseases", "visual_symptoms"]),
        tiered_llm=TieredVisionLLMConfig(
            screen=LLMConfig(model="anthropic/claude-3-haiku", temperature=0.1, max_tokens=200),
            diagnose=LLMConfig(model="anthropic/claude-3-5-sonnet", temperature=0.3, max_tokens=2000),
        ),
        routing=TieredVisionRoutingConfig(
            screen_threshold=0.7,
            healthy_skip_threshold=0.85,
            obvious_skip_threshold=0.75,
        ),
    )


class TestTieredVisionWorkflow:
    """Tests for TieredVisionWorkflow."""

    def test_workflow_properties(self, tiered_vision_workflow: TieredVisionWorkflow) -> None:
        """Test workflow name and version."""
        assert tiered_vision_workflow.workflow_name == "tiered_vision"
        assert tiered_vision_workflow.workflow_version == "2.0.0"

    def test_compiles_successfully(self, tiered_vision_workflow: TieredVisionWorkflow) -> None:
        """Test that workflow compiles without errors."""
        graph = tiered_vision_workflow.compile()
        assert graph is not None

    def test_mcp_client_default(self, mock_llm_gateway: MagicMock) -> None:
        """Test default MCP client creation."""
        workflow = TieredVisionWorkflow(llm_gateway=mock_llm_gateway)
        assert workflow._mcp_client is not None
        assert workflow._mcp_client.app_id == COLLECTION_MCP_APP_ID


class TestPreprocessNode:
    """Tests for preprocess node MCP integration."""

    @pytest.fixture
    def workflow(
        self,
        mock_llm_gateway: MagicMock,
        mock_mcp_client: MagicMock,
    ) -> TieredVisionWorkflow:
        return TieredVisionWorkflow(
            llm_gateway=mock_llm_gateway,
            mcp_client=mock_mcp_client,
        )

    @pytest.mark.asyncio
    async def test_preprocess_with_thumbnail(
        self,
        workflow: TieredVisionWorkflow,
        mock_mcp_client: MagicMock,
    ) -> None:
        """Test preprocessing fetches thumbnail via MCP when has_thumbnail=True."""
        # Configure mock
        mock_mcp_client.call_tool.return_value = {
            "thumbnail_base64": "dGh1bWJuYWls",  # "thumbnail" base64
            "content_type": "image/jpeg",
            "size_bytes": 1024,
        }

        state: TieredVisionState = {
            "doc_id": "test-doc-001",
            "has_thumbnail": True,
            "agent_id": "test-agent",
        }

        result = await workflow._preprocess_node(state)

        # Verify MCP call
        mock_mcp_client.call_tool.assert_called_once_with(
            tool_name="get_document_thumbnail",
            arguments={"document_id": "test-doc-001"},
            caller_agent_id="test-agent",
        )

        # Verify state update
        assert result["thumbnail_data"] == "dGh1bWJuYWls"
        assert "original_data" not in result  # Only fetched in Tier 2

    @pytest.mark.asyncio
    async def test_preprocess_without_thumbnail(
        self,
        workflow: TieredVisionWorkflow,
        mock_mcp_client: MagicMock,
    ) -> None:
        """Test preprocessing fetches original via MCP when has_thumbnail=False."""
        # Configure mock
        mock_mcp_client.call_tool.return_value = {
            "image_base64": "b3JpZ2luYWw=",  # "original" base64
            "content_type": "image/jpeg",
            "size_bytes": 2048,
        }

        state: TieredVisionState = {
            "doc_id": "test-doc-002",
            "has_thumbnail": False,
            "agent_id": "test-agent",
        }

        result = await workflow._preprocess_node(state)

        # Verify MCP call
        mock_mcp_client.call_tool.assert_called_once_with(
            tool_name="get_document_image",
            arguments={"document_id": "test-doc-002"},
            caller_agent_id="test-agent",
        )

        # Verify state update - original used for both tiers
        assert result["thumbnail_data"] == "b3JpZ2luYWw="
        assert result["original_data"] == "b3JpZ2luYWw="

    @pytest.mark.asyncio
    async def test_preprocess_no_doc_id(
        self,
        workflow: TieredVisionWorkflow,
    ) -> None:
        """Test preprocessing fails gracefully without doc_id."""
        state: TieredVisionState = {
            "has_thumbnail": True,
            "agent_id": "test-agent",
        }

        result = await workflow._preprocess_node(state)

        assert result["preprocessing_error"] == "No doc_id provided"

    @pytest.mark.asyncio
    async def test_preprocess_mcp_error(
        self,
        workflow: TieredVisionWorkflow,
        mock_mcp_client: MagicMock,
    ) -> None:
        """Test preprocessing handles MCP errors gracefully."""
        mock_mcp_client.call_tool.side_effect = Exception("MCP connection failed")

        state: TieredVisionState = {
            "doc_id": "test-doc-003",
            "has_thumbnail": True,
            "agent_id": "test-agent",
        }

        result = await workflow._preprocess_node(state)

        assert "MCP connection failed" in result["preprocessing_error"]


class TestScreenNode:
    """Tests for screen node (Tier 1)."""

    @pytest.fixture
    def workflow(
        self,
        mock_llm_gateway: MagicMock,
        mock_mcp_client: MagicMock,
    ) -> TieredVisionWorkflow:
        return TieredVisionWorkflow(
            llm_gateway=mock_llm_gateway,
            mcp_client=mock_mcp_client,
        )

    @pytest.mark.asyncio
    async def test_screen_healthy_high_confidence_skips_tier2(
        self,
        workflow: TieredVisionWorkflow,
        mock_llm_gateway: MagicMock,
        tiered_vision_config: TieredVisionConfig,
    ) -> None:
        """Test healthy classification with high confidence skips Tier 2."""
        # Configure mock LLM response
        mock_llm_gateway.complete.return_value = {
            "content": json.dumps(
                {
                    "classification": "healthy",
                    "confidence": 0.92,
                    "findings": ["Good leaf color", "No visible damage"],
                }
            ),
            "tokens_in": 100,
            "tokens_out": 50,
        }

        state: TieredVisionState = {
            "thumbnail_data": "dGh1bWJuYWls",
            "image_mime_type": "image/jpeg",
            "agent_id": "test-agent",
            "agent_config": tiered_vision_config,
        }

        result = await workflow._screen_node(state)

        assert result["screen_result"]["classification"] == "healthy"
        assert result["screen_result"]["confidence"] == 0.92
        assert result["proceed_to_tier2"] is False
        assert "Healthy with high confidence" in result["tier2_skip_reason"]
        assert result["tier1_executed"] is True

    @pytest.mark.asyncio
    async def test_screen_obvious_issue_high_confidence_skips_tier2(
        self,
        workflow: TieredVisionWorkflow,
        mock_llm_gateway: MagicMock,
        tiered_vision_config: TieredVisionConfig,
    ) -> None:
        """Test obvious_issue classification with high confidence skips Tier 2."""
        mock_llm_gateway.complete.return_value = {
            "content": json.dumps(
                {
                    "classification": "obvious_issue",
                    "confidence": 0.82,
                    "findings": ["Blistered lesions visible"],
                }
            ),
            "tokens_in": 100,
            "tokens_out": 50,
        }

        state: TieredVisionState = {
            "thumbnail_data": "dGh1bWJuYWls",
            "image_mime_type": "image/jpeg",
            "agent_id": "test-agent",
            "agent_config": tiered_vision_config,
        }

        result = await workflow._screen_node(state)

        assert result["screen_result"]["classification"] == "obvious_issue"
        assert result["proceed_to_tier2"] is False
        assert "Obvious issue with high confidence" in result["tier2_skip_reason"]

    @pytest.mark.asyncio
    async def test_screen_uncertain_proceeds_to_tier2(
        self,
        workflow: TieredVisionWorkflow,
        mock_llm_gateway: MagicMock,
        tiered_vision_config: TieredVisionConfig,
    ) -> None:
        """Test uncertain classification proceeds to Tier 2."""
        mock_llm_gateway.complete.return_value = {
            "content": json.dumps(
                {
                    "classification": "uncertain",
                    "confidence": 0.55,
                    "findings": ["Small specks visible"],
                }
            ),
            "tokens_in": 100,
            "tokens_out": 50,
        }

        state: TieredVisionState = {
            "thumbnail_data": "dGh1bWJuYWls",
            "image_mime_type": "image/jpeg",
            "agent_id": "test-agent",
            "agent_config": tiered_vision_config,
        }

        result = await workflow._screen_node(state)

        assert result["screen_result"]["classification"] == "uncertain"
        assert result["proceed_to_tier2"] is True
        assert result["tier2_skip_reason"] is None

    @pytest.mark.asyncio
    async def test_screen_low_confidence_proceeds_to_tier2(
        self,
        workflow: TieredVisionWorkflow,
        mock_llm_gateway: MagicMock,
        tiered_vision_config: TieredVisionConfig,
    ) -> None:
        """Test low confidence classification proceeds to Tier 2."""
        mock_llm_gateway.complete.return_value = {
            "content": json.dumps(
                {
                    "classification": "obvious_issue",
                    "confidence": 0.65,  # Below obvious_skip_threshold (0.75)
                    "findings": ["Yellowing visible"],
                }
            ),
            "tokens_in": 100,
            "tokens_out": 50,
        }

        state: TieredVisionState = {
            "thumbnail_data": "dGh1bWJuYWls",
            "image_mime_type": "image/jpeg",
            "agent_id": "test-agent",
            "agent_config": tiered_vision_config,
        }

        result = await workflow._screen_node(state)

        assert result["proceed_to_tier2"] is True


class TestDiagnoseNode:
    """Tests for diagnose node (Tier 2)."""

    @pytest.fixture
    def workflow(
        self,
        mock_llm_gateway: MagicMock,
        mock_mcp_client: MagicMock,
        mock_ranking_service: MagicMock,
    ) -> TieredVisionWorkflow:
        return TieredVisionWorkflow(
            llm_gateway=mock_llm_gateway,
            mcp_client=mock_mcp_client,
            ranking_service=mock_ranking_service,
        )

    @pytest.mark.asyncio
    async def test_diagnose_fetches_original_via_mcp(
        self,
        workflow: TieredVisionWorkflow,
        mock_llm_gateway: MagicMock,
        mock_mcp_client: MagicMock,
        tiered_vision_config: TieredVisionConfig,
    ) -> None:
        """Test diagnose fetches original image via MCP when not in state."""
        # Configure mocks
        mock_mcp_client.call_tool.return_value = {
            "image_base64": "b3JpZ2luYWw=",
            "content_type": "image/jpeg",
            "size_bytes": 4096,
        }

        mock_llm_gateway.complete.return_value = {
            "content": json.dumps(
                {
                    "primary_issue": "red_spider_mite_infestation",
                    "confidence": 0.91,
                    "findings": ["Fine webbing", "Stippled surface"],
                    "recommendations": ["Apply acaricide"],
                    "severity": "moderate",
                }
            ),
            "tokens_in": 500,
            "tokens_out": 200,
        }

        state: TieredVisionState = {
            "doc_id": "test-doc-001",
            "image_mime_type": "image/jpeg",
            "agent_id": "test-agent",
            "agent_config": tiered_vision_config,
            "screen_result": ScreenResult(
                classification="uncertain",
                confidence=0.55,
                preliminary_findings=["Small specks visible"],
                skip_reason=None,
            ),
            # original_data NOT in state - should be fetched
        }

        result = await workflow._diagnose_node(state)

        # Verify MCP call for original
        mock_mcp_client.call_tool.assert_called_once_with(
            tool_name="get_document_image",
            arguments={"document_id": "test-doc-001"},
            caller_agent_id="test-agent",
        )

        # Verify result
        assert result["original_data"] == "b3JpZ2luYWw="
        assert result["diagnose_result"]["primary_issue"] == "red_spider_mite_infestation"
        assert result["tier2_executed"] is True

    @pytest.mark.asyncio
    async def test_diagnose_uses_existing_original(
        self,
        workflow: TieredVisionWorkflow,
        mock_llm_gateway: MagicMock,
        mock_mcp_client: MagicMock,
        tiered_vision_config: TieredVisionConfig,
    ) -> None:
        """Test diagnose uses original_data from state (small image scenario)."""
        mock_llm_gateway.complete.return_value = {
            "content": json.dumps(
                {
                    "primary_issue": "healthy",
                    "confidence": 0.88,
                    "findings": ["No issues found"],
                    "recommendations": ["Continue monitoring"],
                    "severity": "low",
                }
            ),
            "tokens_in": 500,
            "tokens_out": 200,
        }

        state: TieredVisionState = {
            "doc_id": "test-doc-002",
            "image_mime_type": "image/jpeg",
            "agent_id": "test-agent",
            "agent_config": tiered_vision_config,
            "screen_result": ScreenResult(
                classification="uncertain",
                confidence=0.55,
                preliminary_findings=["Small specks visible"],
                skip_reason=None,
            ),
            "original_data": "YWxyZWFkeV9mZXRjaGVk",  # Already in state
        }

        result = await workflow._diagnose_node(state)

        # Verify MCP NOT called (original already in state)
        mock_mcp_client.call_tool.assert_not_called()

        # Verify result
        assert result["diagnose_result"]["primary_issue"] == "healthy"
        assert result["tier2_executed"] is True


class TestRoutingLogic:
    """Tests for workflow routing logic."""

    @pytest.fixture
    def workflow(
        self,
        mock_llm_gateway: MagicMock,
        mock_mcp_client: MagicMock,
    ) -> TieredVisionWorkflow:
        return TieredVisionWorkflow(
            llm_gateway=mock_llm_gateway,
            mcp_client=mock_mcp_client,
        )

    def test_route_error_on_preprocessing_error(
        self,
        workflow: TieredVisionWorkflow,
    ) -> None:
        """Test routing to error on preprocessing error."""
        state: TieredVisionState = {
            "preprocessing_error": "MCP connection failed",
        }

        result = workflow._route_after_screen(state)
        assert result == "error"

    def test_route_error_on_screen_error(
        self,
        workflow: TieredVisionWorkflow,
    ) -> None:
        """Test routing to error on screen error."""
        state: TieredVisionState = {
            "screen_error": "LLM call failed",
        }

        result = workflow._route_after_screen(state)
        assert result == "error"

    def test_route_diagnose_when_proceed_to_tier2(
        self,
        workflow: TieredVisionWorkflow,
    ) -> None:
        """Test routing to diagnose when proceed_to_tier2 is True."""
        state: TieredVisionState = {
            "proceed_to_tier2": True,
        }

        result = workflow._route_after_screen(state)
        assert result == "diagnose"

    def test_route_skip_when_not_proceeding(
        self,
        workflow: TieredVisionWorkflow,
    ) -> None:
        """Test routing to skip (output) when not proceeding to Tier 2."""
        state: TieredVisionState = {
            "proceed_to_tier2": False,
        }

        result = workflow._route_after_screen(state)
        assert result == "skip"


class TestOutputNode:
    """Tests for output node."""

    @pytest.fixture
    def workflow(
        self,
        mock_llm_gateway: MagicMock,
        mock_mcp_client: MagicMock,
    ) -> TieredVisionWorkflow:
        return TieredVisionWorkflow(
            llm_gateway=mock_llm_gateway,
            mcp_client=mock_mcp_client,
        )

    @pytest.mark.asyncio
    async def test_output_tier1_only(
        self,
        workflow: TieredVisionWorkflow,
    ) -> None:
        """Test output packaging for Tier 1 only execution."""
        state: TieredVisionState = {
            "agent_id": "test-agent",
            "screen_result": ScreenResult(
                classification="healthy",
                confidence=0.92,
                preliminary_findings=["Good color"],
                skip_reason="High confidence healthy",
            ),
            "tier1_executed": True,
            "tier2_executed": False,
            "tier1_tokens": 150,
            "tier2_skip_reason": "High confidence healthy",
        }

        result = await workflow._output_node(state)

        assert result["final_classification"] == "healthy"
        assert result["final_confidence"] == 0.92
        assert result["success"] is True
        assert result["output"]["tier1"]["executed"] is True
        assert result["output"]["tier2"]["executed"] is False

    @pytest.mark.asyncio
    async def test_output_tier2_executed(
        self,
        workflow: TieredVisionWorkflow,
    ) -> None:
        """Test output packaging for Tier 2 execution."""
        state: TieredVisionState = {
            "agent_id": "test-agent",
            "screen_result": ScreenResult(
                classification="uncertain",
                confidence=0.55,
                preliminary_findings=["Unclear"],
                skip_reason=None,
            ),
            "diagnose_result": DiagnoseResult(
                primary_issue="red_spider_mite",
                confidence=0.91,
                detailed_findings=["Webbing found"],
                recommendations=["Apply treatment"],
                severity="moderate",
            ),
            "tier1_executed": True,
            "tier2_executed": True,
            "tier1_tokens": 150,
            "tier2_tokens": 700,
        }

        result = await workflow._output_node(state)

        assert result["final_classification"] == "red_spider_mite"
        assert result["final_confidence"] == 0.91
        assert result["success"] is True
        assert result["output"]["tier2"]["executed"] is True
        assert result["output"]["severity"] == "moderate"

    @pytest.mark.asyncio
    async def test_output_error_state(
        self,
        workflow: TieredVisionWorkflow,
    ) -> None:
        """Test output packaging for error state."""
        state: TieredVisionState = {
            "agent_id": "test-agent",
            "preprocessing_error": "MCP connection failed",
        }

        result = await workflow._output_node(state)

        assert result["final_classification"] == "error"
        assert result["success"] is False
        assert result["error_message"] == "MCP connection failed"
