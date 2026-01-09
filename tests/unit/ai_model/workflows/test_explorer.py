"""Unit tests for Explorer workflow.

Tests ExplorerWorkflow saga pattern implementation.

Story 0.75.16: LangGraph SDK Integration & Base Workflows
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from ai_model.domain.agent_config import (
    AgentConfigMetadata,
    ExplorerConfig,
    InputConfig,
    LLMConfig,
    OutputConfig,
    RAGConfig,
)
from ai_model.workflows.explorer import (
    DEFAULT_BRANCH_TIMEOUT,
    ExplorerWorkflow,
)
from ai_model.workflows.states.explorer import AnalyzerResult, ExplorerState


@pytest.fixture
def mock_llm_gateway() -> MagicMock:
    """Create a mock LLM gateway."""
    gateway = MagicMock()
    gateway.complete = AsyncMock()
    return gateway


@pytest.fixture
def mock_ranking_service() -> MagicMock:
    """Create a mock ranking service."""
    service = MagicMock()
    service.rank = AsyncMock(return_value=MagicMock(matches=[]))
    return service


@pytest.fixture
def explorer_workflow(
    mock_llm_gateway: MagicMock,
    mock_ranking_service: MagicMock,
) -> ExplorerWorkflow:
    """Create an ExplorerWorkflow instance."""
    return ExplorerWorkflow(
        llm_gateway=mock_llm_gateway,
        ranking_service=mock_ranking_service,
    )


@pytest.fixture
def explorer_config() -> ExplorerConfig:
    """Create a test ExplorerConfig."""
    return ExplorerConfig(
        id="test-explorer:1.0.0",
        agent_id="test-explorer",
        version="1.0.0",
        description="Test explorer agent",
        input=InputConfig(event="test.input", schema={"type": "object"}),
        output=OutputConfig(event="test.output", schema={"type": "object"}),
        llm=LLMConfig(model="test", temperature=0.3),
        metadata=AgentConfigMetadata(author="test"),
        rag=RAGConfig(enabled=True, knowledge_domains=["test"]),
    )


class TestExplorerWorkflow:
    """Tests for ExplorerWorkflow."""

    def test_workflow_properties(self, explorer_workflow: ExplorerWorkflow) -> None:
        """Test workflow name and version."""
        assert explorer_workflow.workflow_name == "explorer"
        assert explorer_workflow.workflow_version == "1.0.0"

    def test_compiles_successfully(self, explorer_workflow: ExplorerWorkflow) -> None:
        """Test that workflow compiles without errors."""
        graph = explorer_workflow.compile()
        assert graph is not None

    def test_default_branch_timeout(self, explorer_workflow: ExplorerWorkflow) -> None:
        """Test default branch timeout is set."""
        assert explorer_workflow._branch_timeout_seconds == DEFAULT_BRANCH_TIMEOUT


class TestRoutingLogic:
    """Tests for triage routing logic."""

    @pytest.fixture
    def workflow(
        self,
        mock_llm_gateway: MagicMock,
    ) -> ExplorerWorkflow:
        return ExplorerWorkflow(llm_gateway=mock_llm_gateway)

    def test_route_single_on_high_confidence(self, workflow: ExplorerWorkflow) -> None:
        """Test routing to single analyzer on high confidence."""
        state: ExplorerState = {
            "route_type": "single",
        }

        route = workflow._route_after_triage(state)
        assert route == "single"

    def test_route_parallel_on_low_confidence(self, workflow: ExplorerWorkflow) -> None:
        """Test routing to parallel analyzers on low confidence."""
        state: ExplorerState = {
            "route_type": "parallel",
        }

        route = workflow._route_after_triage(state)
        assert route == "parallel"

    def test_route_error_on_error_message(self, workflow: ExplorerWorkflow) -> None:
        """Test routing to error on error message."""
        state: ExplorerState = {
            "error_message": "Something failed",
        }

        route = workflow._route_after_triage(state)
        assert route == "error"


class TestTriageNode:
    """Tests for triage node behavior."""

    @pytest.fixture
    def workflow(
        self,
        mock_llm_gateway: MagicMock,
    ) -> ExplorerWorkflow:
        return ExplorerWorkflow(llm_gateway=mock_llm_gateway)

    @pytest.mark.asyncio
    async def test_triage_high_confidence_single_route(
        self,
        workflow: ExplorerWorkflow,
        explorer_config: ExplorerConfig,
        mock_llm_gateway: MagicMock,
    ) -> None:
        """Test triage with high confidence routes to single."""
        mock_llm_gateway.complete.return_value = {
            "content": json.dumps(
                {
                    "category": "disease",
                    "confidence": 0.85,
                    "secondary_categories": ["nutrition"],
                }
            ),
            "model": "test",
            "tokens_in": 50,
            "tokens_out": 25,
        }

        state: ExplorerState = {
            "input_data": {"symptoms": "yellow leaves"},
            "agent_id": "disease-diagnosis",
            "agent_config": explorer_config,
            "correlation_id": "123",
        }

        result = await workflow._triage_node(state)

        assert result["triage_category"] == "disease"
        assert result["triage_confidence"] == 0.85
        assert result["route_type"] == "single"
        assert result["selected_analyzers"] == ["disease"]

    @pytest.mark.asyncio
    async def test_triage_low_confidence_parallel_route(
        self,
        workflow: ExplorerWorkflow,
        explorer_config: ExplorerConfig,
        mock_llm_gateway: MagicMock,
    ) -> None:
        """Test triage with low confidence routes to parallel."""
        mock_llm_gateway.complete.return_value = {
            "content": json.dumps(
                {
                    "category": "unknown",
                    "confidence": 0.4,
                    "secondary_categories": ["disease", "weather"],
                }
            ),
            "model": "test",
            "tokens_in": 50,
            "tokens_out": 25,
        }

        state: ExplorerState = {
            "input_data": {"symptoms": "unclear symptoms"},
            "agent_id": "disease-diagnosis",
            "agent_config": explorer_config,
            "correlation_id": "123",
        }

        result = await workflow._triage_node(state)

        assert result["triage_confidence"] == 0.4
        assert result["route_type"] == "parallel"
        # Should include primary + secondary categories
        assert len(result["selected_analyzers"]) > 1


class TestAnalyzerExecution:
    """Tests for analyzer node execution."""

    @pytest.fixture
    def workflow(
        self,
        mock_llm_gateway: MagicMock,
    ) -> ExplorerWorkflow:
        return ExplorerWorkflow(llm_gateway=mock_llm_gateway)

    @pytest.mark.asyncio
    async def test_run_analyzer_success(
        self,
        workflow: ExplorerWorkflow,
        explorer_config: ExplorerConfig,
        mock_llm_gateway: MagicMock,
    ) -> None:
        """Test successful analyzer execution."""
        mock_llm_gateway.complete.return_value = {
            "content": json.dumps(
                {
                    "confidence": 0.9,
                    "findings": ["Fungal infection detected"],
                    "recommendations": ["Apply fungicide"],
                }
            ),
            "model": "test",
            "tokens_in": 100,
            "tokens_out": 50,
        }

        state: ExplorerState = {
            "input_data": {"symptoms": "white powder"},
            "agent_id": "test",
            "agent_config": explorer_config,
            "correlation_id": "123",
            "mcp_context": {},
            "rag_context": [],
        }

        result = await workflow._run_analyzer(state, "disease")

        assert result["success"] is True
        assert result["confidence"] == 0.9
        assert "Fungal infection" in result["findings"][0]

    @pytest.mark.asyncio
    async def test_run_analyzer_failure(
        self,
        workflow: ExplorerWorkflow,
        explorer_config: ExplorerConfig,
        mock_llm_gateway: MagicMock,
    ) -> None:
        """Test analyzer execution failure."""
        mock_llm_gateway.complete.side_effect = Exception("LLM error")

        state: ExplorerState = {
            "input_data": {},
            "agent_id": "test",
            "agent_config": explorer_config,
            "correlation_id": "123",
            "mcp_context": {},
            "rag_context": [],
        }

        result = await workflow._run_analyzer(state, "disease")

        assert result["success"] is False
        assert "LLM error" in result["error"]


class TestAggregation:
    """Tests for result aggregation."""

    @pytest.fixture
    def workflow(
        self,
        mock_llm_gateway: MagicMock,
    ) -> ExplorerWorkflow:
        return ExplorerWorkflow(llm_gateway=mock_llm_gateway)

    @pytest.mark.asyncio
    async def test_aggregate_selects_highest_confidence(
        self,
        workflow: ExplorerWorkflow,
    ) -> None:
        """Test aggregation selects highest confidence as primary."""
        state: ExplorerState = {
            "analyzer_results": [
                AnalyzerResult(
                    analyzer_id="weather",
                    category="weather",
                    confidence=0.6,
                    findings=["Cold damage"],
                    recommendations=["Cover plants"],
                    success=True,
                    error=None,
                ),
                AnalyzerResult(
                    analyzer_id="disease",
                    category="disease",
                    confidence=0.9,
                    findings=["Fungal infection"],
                    recommendations=["Apply fungicide"],
                    success=True,
                    error=None,
                ),
            ],
        }

        result = await workflow._aggregate_node(state)

        assert result["primary_diagnosis"]["category"] == "disease"
        assert result["primary_diagnosis"]["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_aggregate_empty_results(
        self,
        workflow: ExplorerWorkflow,
    ) -> None:
        """Test aggregation with no results."""
        state: ExplorerState = {
            "analyzer_results": [],
        }

        result = await workflow._aggregate_node(state)

        assert result["primary_diagnosis"] is None
        assert result["secondary_diagnoses"] == []

    @pytest.mark.asyncio
    async def test_aggregate_filters_secondary_by_confidence(
        self,
        workflow: ExplorerWorkflow,
    ) -> None:
        """Test secondary diagnoses filtered by confidence >= 0.5."""
        state: ExplorerState = {
            "analyzer_results": [
                AnalyzerResult(
                    analyzer_id="primary",
                    category="disease",
                    confidence=0.9,
                    findings=[],
                    recommendations=[],
                    success=True,
                    error=None,
                ),
                AnalyzerResult(
                    analyzer_id="high",
                    category="weather",
                    confidence=0.7,
                    findings=[],
                    recommendations=[],
                    success=True,
                    error=None,
                ),
                AnalyzerResult(
                    analyzer_id="low",
                    category="nutrition",
                    confidence=0.3,  # Below threshold
                    findings=[],
                    recommendations=[],
                    success=True,
                    error=None,
                ),
            ],
        }

        result = await workflow._aggregate_node(state)

        # Should have 1 secondary (0.7 >= 0.5), not the 0.3 one
        assert len(result["secondary_diagnoses"]) == 1
        assert result["secondary_diagnoses"][0]["category"] == "weather"


class TestHelperMethods:
    """Tests for explorer helper methods."""

    @pytest.fixture
    def workflow(
        self,
        mock_llm_gateway: MagicMock,
    ) -> ExplorerWorkflow:
        return ExplorerWorkflow(llm_gateway=mock_llm_gateway)

    def test_build_analysis_query(self, workflow: ExplorerWorkflow) -> None:
        """Test analysis query construction."""
        data = {
            "description": "Yellow leaves",
            "symptoms": "wilting",
            "observations": "dry soil",
        }

        query = workflow._build_analysis_query(data)

        assert "Yellow leaves" in query
        assert "wilting" in query
        assert "dry soil" in query

    def test_build_analysis_query_fallback(self, workflow: ExplorerWorkflow) -> None:
        """Test analysis query fallback to JSON."""
        data = {"custom_field": "value"}

        query = workflow._build_analysis_query(data)

        assert "custom_field" in query

    def test_parse_triage_response_valid(self, workflow: ExplorerWorkflow) -> None:
        """Test parsing valid triage response."""
        content = json.dumps(
            {
                "category": "disease",
                "confidence": 0.8,
                "secondary_categories": ["weather"],
            }
        )

        result = workflow._parse_triage_response(content)

        assert result["category"] == "disease"
        assert result["confidence"] == 0.8

    def test_parse_triage_response_invalid(self, workflow: ExplorerWorkflow) -> None:
        """Test parsing invalid triage response."""
        content = "Not JSON"

        result = workflow._parse_triage_response(content)

        assert result["category"] == "unknown"
        assert result["confidence"] == 0.5
