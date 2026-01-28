"""Unit tests for AgentConfigService gRPC servicer.

Story 9.12a: AgentConfigService gRPC in AI Model

Tests cover:
- ListAgentConfigs RPC (AC 9.12a.2)
- GetAgentConfig RPC (AC 9.12a.3)
- ListPromptsByAgent RPC (AC 9.12a.4)

Total: 15 tests
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from ai_model.api.agent_config_service import AgentConfigServiceServicer
from ai_model.domain.agent_config import (
    AgentConfigMetadata,
    AgentConfigStatus,
    ExplorerConfig,
    ExtractorConfig,
    InputConfig,
    LLMConfig,
    OutputConfig,
    RAGConfig,
)
from ai_model.domain.prompt import Prompt, PromptContent, PromptMetadata, PromptStatus
from ai_model.infrastructure.repositories.agent_config_repository import AgentConfigRepository
from ai_model.infrastructure.repositories.prompt_repository import PromptRepository
from fp_proto.ai_model.v1 import ai_model_pb2


class TestAgentConfigServiceServicer:
    """Tests for AgentConfigServiceServicer."""

    @pytest.fixture
    def mock_db(self, mock_mongodb_client: Any) -> Any:
        """Get mock database from mock client."""
        return mock_mongodb_client["ai_model"]

    @pytest.fixture
    def agent_config_repository(self, mock_db: Any) -> AgentConfigRepository:
        """Create repository with mock database."""
        return AgentConfigRepository(mock_db)

    @pytest.fixture
    def prompt_repository(self, mock_db: Any) -> PromptRepository:
        """Create repository with mock database."""
        return PromptRepository(mock_db)

    @pytest.fixture
    def servicer(
        self,
        mock_db: Any,
        agent_config_repository: AgentConfigRepository,
        prompt_repository: PromptRepository,
    ) -> AgentConfigServiceServicer:
        """Create servicer with mock repositories."""
        return AgentConfigServiceServicer(
            db=mock_db,
            agent_config_repository=agent_config_repository,
            prompt_repository=prompt_repository,
        )

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create mock gRPC context."""
        context = MagicMock(spec=grpc.aio.ServicerContext)
        context.abort = AsyncMock()
        return context

    @pytest.fixture
    def sample_extractor_config(self) -> ExtractorConfig:
        """Create a sample extractor config for testing."""
        return ExtractorConfig(
            id="qc-extractor:1.0.0",
            agent_id="qc-extractor",
            version="1.0.0",
            status=AgentConfigStatus.ACTIVE,
            description="Extracts QC event data",
            input=InputConfig(
                event="collection.document.received",
                schema={"required": ["doc_id"]},
            ),
            output=OutputConfig(
                event="ai.extraction.complete",
                schema={"fields": ["farmer_id", "grade"]},
            ),
            llm=LLMConfig(model="anthropic/claude-3-haiku", temperature=0.1),
            extraction_schema={"required_fields": ["farmer_id", "grade"]},
            metadata=AgentConfigMetadata(author="admin"),
        )

    @pytest.fixture
    def sample_explorer_config(self) -> ExplorerConfig:
        """Create a sample explorer config for testing."""
        return ExplorerConfig(
            id="disease-diagnosis:1.0.0",
            agent_id="disease-diagnosis",
            version="1.0.0",
            status=AgentConfigStatus.ACTIVE,
            description="Diagnoses tea leaf diseases",
            input=InputConfig(
                event="collection.poor_quality_detected",
                schema={"required": ["doc_id", "farmer_id"]},
            ),
            output=OutputConfig(
                event="ai.diagnosis.complete",
                schema={"fields": ["diagnosis", "confidence"]},
            ),
            llm=LLMConfig(model="anthropic/claude-3-5-sonnet"),
            rag=RAGConfig(
                enabled=True,
                knowledge_domains=["plant_diseases", "tea_cultivation"],
            ),
            metadata=AgentConfigMetadata(author="developer"),
        )

    @pytest.fixture
    def sample_prompt(self) -> Prompt:
        """Create a sample prompt for testing."""
        return Prompt(
            id="disease-diagnosis:1.0.0",
            prompt_id="disease-diagnosis",
            agent_id="disease-diagnosis",
            version="1.0.0",
            status=PromptStatus.ACTIVE,
            content=PromptContent(
                system_prompt="You are an expert diagnostician",
                template="Analyze: {{data}}",
            ),
            metadata=PromptMetadata(author="admin"),
        )

    @pytest.fixture
    def sample_prompt_v2(self) -> Prompt:
        """Create a second prompt for testing."""
        return Prompt(
            id="disease-diagnosis:2.0.0",
            prompt_id="disease-diagnosis",
            agent_id="disease-diagnosis",
            version="2.0.0",
            status=PromptStatus.STAGED,
            content=PromptContent(
                system_prompt="You are an expert diagnostician v2",
                template="Analyze v2: {{data}}",
            ),
            metadata=PromptMetadata(author="developer"),
        )

    # =========================================================================
    # ListAgentConfigs RPC Tests (AC 9.12a.2)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_list_agent_configs_returns_all_configs(
        self,
        servicer: AgentConfigServiceServicer,
        agent_config_repository: AgentConfigRepository,
        mock_context: MagicMock,
        sample_extractor_config: ExtractorConfig,
        sample_explorer_config: ExplorerConfig,
    ) -> None:
        """ListAgentConfigs returns all configs with pagination."""
        await agent_config_repository.create(sample_extractor_config)
        await agent_config_repository.create(sample_explorer_config)

        request = ai_model_pb2.ListAgentConfigsRequest(page_size=20)

        response = await servicer.ListAgentConfigs(request, mock_context)

        assert response.total_count == 2
        assert len(response.agents) == 2
        assert response.next_page_token == ""

    @pytest.mark.asyncio
    async def test_list_agent_configs_with_type_filter(
        self,
        servicer: AgentConfigServiceServicer,
        agent_config_repository: AgentConfigRepository,
        mock_context: MagicMock,
        sample_extractor_config: ExtractorConfig,
        sample_explorer_config: ExplorerConfig,
    ) -> None:
        """ListAgentConfigs filters by agent_type."""
        await agent_config_repository.create(sample_extractor_config)
        await agent_config_repository.create(sample_explorer_config)

        request = ai_model_pb2.ListAgentConfigsRequest(
            page_size=20,
            agent_type="extractor",
        )

        response = await servicer.ListAgentConfigs(request, mock_context)

        assert response.total_count == 1
        assert len(response.agents) == 1
        assert response.agents[0].agent_type == "extractor"

    @pytest.mark.asyncio
    async def test_list_agent_configs_with_status_filter(
        self,
        servicer: AgentConfigServiceServicer,
        agent_config_repository: AgentConfigRepository,
        mock_context: MagicMock,
        sample_extractor_config: ExtractorConfig,
    ) -> None:
        """ListAgentConfigs filters by status."""
        await agent_config_repository.create(sample_extractor_config)  # ACTIVE

        # Create a staged config
        staged = ExtractorConfig(
            id="other-extractor:1.0.0",
            agent_id="other-extractor",
            version="1.0.0",
            status=AgentConfigStatus.STAGED,
            description="Other extractor",
            input=sample_extractor_config.input,
            output=sample_extractor_config.output,
            llm=sample_extractor_config.llm,
            extraction_schema={},
            metadata=AgentConfigMetadata(author="admin"),
        )
        await agent_config_repository.create(staged)

        request = ai_model_pb2.ListAgentConfigsRequest(
            page_size=20,
            status="active",
        )

        response = await servicer.ListAgentConfigs(request, mock_context)

        assert response.total_count == 1
        assert len(response.agents) == 1
        assert response.agents[0].status == "active"

    @pytest.mark.asyncio
    async def test_list_agent_configs_pagination(
        self,
        servicer: AgentConfigServiceServicer,
        agent_config_repository: AgentConfigRepository,
        mock_context: MagicMock,
        sample_extractor_config: ExtractorConfig,
    ) -> None:
        """ListAgentConfigs handles pagination correctly."""
        # Create 3 configs
        await agent_config_repository.create(sample_extractor_config)
        for i in range(2, 4):
            config = ExtractorConfig(
                id=f"extractor-{i}:1.0.0",
                agent_id=f"extractor-{i}",
                version="1.0.0",
                status=AgentConfigStatus.ACTIVE,
                description=f"Extractor {i}",
                input=sample_extractor_config.input,
                output=sample_extractor_config.output,
                llm=sample_extractor_config.llm,
                extraction_schema={},
                metadata=AgentConfigMetadata(author="admin"),
            )
            await agent_config_repository.create(config)

        # Request page 1 with page_size=2
        request = ai_model_pb2.ListAgentConfigsRequest(page_size=2)
        response = await servicer.ListAgentConfigs(request, mock_context)

        assert response.total_count == 3
        assert len(response.agents) == 2
        assert response.next_page_token == "2"

        # Request page 2
        request2 = ai_model_pb2.ListAgentConfigsRequest(page_size=2, page_token="2")
        response2 = await servicer.ListAgentConfigs(request2, mock_context)

        assert response2.total_count == 3
        assert len(response2.agents) == 1
        assert response2.next_page_token == ""

    @pytest.mark.asyncio
    async def test_list_agent_configs_includes_prompt_count(
        self,
        servicer: AgentConfigServiceServicer,
        agent_config_repository: AgentConfigRepository,
        prompt_repository: PromptRepository,
        mock_context: MagicMock,
        sample_explorer_config: ExplorerConfig,
        sample_prompt: Prompt,
        sample_prompt_v2: Prompt,
    ) -> None:
        """ListAgentConfigs includes correct prompt_count."""
        await agent_config_repository.create(sample_explorer_config)
        await prompt_repository.create(sample_prompt)
        await prompt_repository.create(sample_prompt_v2)

        request = ai_model_pb2.ListAgentConfigsRequest(page_size=20)

        response = await servicer.ListAgentConfigs(request, mock_context)

        assert len(response.agents) == 1
        assert response.agents[0].prompt_count == 2

    # =========================================================================
    # GetAgentConfig RPC Tests (AC 9.12a.3)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_agent_config_returns_active_by_default(
        self,
        servicer: AgentConfigServiceServicer,
        agent_config_repository: AgentConfigRepository,
        prompt_repository: PromptRepository,
        mock_context: MagicMock,
        sample_explorer_config: ExplorerConfig,
        sample_prompt: Prompt,
    ) -> None:
        """GetAgentConfig returns active config when no version specified."""
        await agent_config_repository.create(sample_explorer_config)
        await prompt_repository.create(sample_prompt)

        request = ai_model_pb2.GetAgentConfigRequest(agent_id="disease-diagnosis")

        response = await servicer.GetAgentConfig(request, mock_context)

        assert response.agent_id == "disease-diagnosis"
        assert response.version == "1.0.0"
        assert response.status == "active"
        assert len(response.prompts) == 1

    @pytest.mark.asyncio
    async def test_get_agent_config_returns_specific_version(
        self,
        servicer: AgentConfigServiceServicer,
        agent_config_repository: AgentConfigRepository,
        mock_context: MagicMock,
        sample_explorer_config: ExplorerConfig,
    ) -> None:
        """GetAgentConfig returns specific version when requested."""
        await agent_config_repository.create(sample_explorer_config)

        # Create version 2.0.0
        v2 = ExplorerConfig(
            id="disease-diagnosis:2.0.0",
            agent_id="disease-diagnosis",
            version="2.0.0",
            status=AgentConfigStatus.STAGED,
            description="Version 2",
            input=sample_explorer_config.input,
            output=sample_explorer_config.output,
            llm=sample_explorer_config.llm,
            rag=RAGConfig(enabled=True),
            metadata=AgentConfigMetadata(author="developer"),
        )
        await agent_config_repository.create(v2)

        request = ai_model_pb2.GetAgentConfigRequest(
            agent_id="disease-diagnosis",
            version="2.0.0",
        )

        response = await servicer.GetAgentConfig(request, mock_context)

        assert response.version == "2.0.0"
        assert response.status == "staged"

    @pytest.mark.asyncio
    async def test_get_agent_config_includes_full_json(
        self,
        servicer: AgentConfigServiceServicer,
        agent_config_repository: AgentConfigRepository,
        mock_context: MagicMock,
        sample_explorer_config: ExplorerConfig,
    ) -> None:
        """GetAgentConfig includes full config as JSON."""
        await agent_config_repository.create(sample_explorer_config)

        request = ai_model_pb2.GetAgentConfigRequest(agent_id="disease-diagnosis")

        response = await servicer.GetAgentConfig(request, mock_context)

        assert response.config_json != ""
        assert "disease-diagnosis" in response.config_json
        assert "anthropic/claude-3-5-sonnet" in response.config_json

    @pytest.mark.asyncio
    async def test_get_agent_config_not_found_aborts(
        self,
        servicer: AgentConfigServiceServicer,
        mock_context: MagicMock,
    ) -> None:
        """GetAgentConfig aborts with NOT_FOUND for nonexistent agent."""
        request = ai_model_pb2.GetAgentConfigRequest(agent_id="nonexistent")

        await servicer.GetAgentConfig(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_agent_config_empty_id_aborts(
        self,
        servicer: AgentConfigServiceServicer,
        mock_context: MagicMock,
    ) -> None:
        """GetAgentConfig aborts with INVALID_ARGUMENT for empty agent_id."""
        request = ai_model_pb2.GetAgentConfigRequest(agent_id="")

        await servicer.GetAgentConfig(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.INVALID_ARGUMENT

    # =========================================================================
    # ListPromptsByAgent RPC Tests (AC 9.12a.4)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_list_prompts_by_agent_returns_all_prompts(
        self,
        servicer: AgentConfigServiceServicer,
        prompt_repository: PromptRepository,
        mock_context: MagicMock,
        sample_prompt: Prompt,
        sample_prompt_v2: Prompt,
    ) -> None:
        """ListPromptsByAgent returns all prompts for an agent."""
        await prompt_repository.create(sample_prompt)
        await prompt_repository.create(sample_prompt_v2)

        request = ai_model_pb2.ListPromptsByAgentRequest(agent_id="disease-diagnosis")

        response = await servicer.ListPromptsByAgent(request, mock_context)

        assert response.total_count == 2
        assert len(response.prompts) == 2

    @pytest.mark.asyncio
    async def test_list_prompts_by_agent_with_status_filter(
        self,
        servicer: AgentConfigServiceServicer,
        prompt_repository: PromptRepository,
        mock_context: MagicMock,
        sample_prompt: Prompt,
        sample_prompt_v2: Prompt,
    ) -> None:
        """ListPromptsByAgent filters by status."""
        await prompt_repository.create(sample_prompt)  # ACTIVE
        await prompt_repository.create(sample_prompt_v2)  # STAGED

        request = ai_model_pb2.ListPromptsByAgentRequest(
            agent_id="disease-diagnosis",
            status="active",
        )

        response = await servicer.ListPromptsByAgent(request, mock_context)

        assert response.total_count == 1
        assert len(response.prompts) == 1
        assert response.prompts[0].status == "active"

    @pytest.mark.asyncio
    async def test_list_prompts_by_agent_empty_id_aborts(
        self,
        servicer: AgentConfigServiceServicer,
        mock_context: MagicMock,
    ) -> None:
        """ListPromptsByAgent aborts with INVALID_ARGUMENT for empty agent_id."""
        request = ai_model_pb2.ListPromptsByAgentRequest(agent_id="")

        await servicer.ListPromptsByAgent(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.INVALID_ARGUMENT

    @pytest.mark.asyncio
    async def test_list_prompts_by_agent_returns_empty_for_unknown_agent(
        self,
        servicer: AgentConfigServiceServicer,
        mock_context: MagicMock,
    ) -> None:
        """ListPromptsByAgent returns empty list for agent with no prompts."""
        request = ai_model_pb2.ListPromptsByAgentRequest(agent_id="unknown-agent")

        response = await servicer.ListPromptsByAgent(request, mock_context)

        assert response.total_count == 0
        assert len(response.prompts) == 0
