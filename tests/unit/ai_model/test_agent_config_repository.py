"""Unit tests for AgentConfigRepository.

Tests cover:
- create() - creates new agent config (extractor type)
- create() - creates explorer type
- create() - creates generator type
- create() - creates conversational type
- create() - creates tiered-vision type
- get_by_id() - retrieves config by ID
- get_by_id() - returns correct discriminated type
- update() - updates config fields
- delete() - deletes config
- list() - lists configs with pagination
- get_active() - gets active config for agent_id
- get_by_type() - gets all configs of specific type
- get_by_version() - gets specific version
- list_versions() - lists all versions of an agent
- ensure_indexes() - creates proper indexes

Total: 16 tests
"""

from typing import Any

import pytest
from ai_model.domain.agent_config import (
    AgentConfigMetadata,
    AgentConfigStatus,
    AgentType,
    ConversationalConfig,
    ExplorerConfig,
    ExtractorConfig,
    GeneratorConfig,
    InputConfig,
    LLMConfig,
    OutputConfig,
    RAGConfig,
    StateConfig,
    TieredVisionConfig,
    TieredVisionLLMConfig,
    TieredVisionRoutingConfig,
)
from ai_model.infrastructure.repositories.agent_config_repository import (
    AgentConfigRepository,
)


class TestAgentConfigRepository:
    """Tests for AgentConfigRepository."""

    @pytest.fixture
    def mock_db(self, mock_mongodb_client: Any) -> Any:
        """Get mock database from mock client."""
        return mock_mongodb_client["ai_model"]

    @pytest.fixture
    def repository(self, mock_db: Any) -> AgentConfigRepository:
        """Create repository with mock database."""
        return AgentConfigRepository(mock_db)

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
            status=AgentConfigStatus.STAGED,
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
    def sample_generator_config(self) -> GeneratorConfig:
        """Create a sample generator config for testing."""
        return GeneratorConfig(
            id="weekly-action-plan:1.0.0",
            agent_id="weekly-action-plan",
            version="1.0.0",
            status=AgentConfigStatus.DRAFT,
            description="Generates weekly action plans",
            input=InputConfig(
                event="action_plan.generation.requested",
                schema={"required": ["farmer_id", "week_start"]},
            ),
            output=OutputConfig(
                event="ai.action_plan.complete",
                schema={"fields": ["plan_markdown"]},
            ),
            llm=LLMConfig(model="anthropic/claude-3-5-sonnet", temperature=0.5),
            rag=RAGConfig(enabled=True),
            output_format="markdown",
            metadata=AgentConfigMetadata(author="admin"),
        )

    @pytest.fixture
    def sample_conversational_config(self) -> ConversationalConfig:
        """Create a sample conversational config for testing."""
        return ConversationalConfig(
            id="dialogue-responder:1.0.0",
            agent_id="dialogue-responder",
            version="1.0.0",
            status=AgentConfigStatus.ACTIVE,
            description="Handles farmer dialogues",
            input=InputConfig(
                event="conversation.turn.received",
                schema={"required": ["session_id", "user_message"]},
            ),
            output=OutputConfig(
                event="conversation.turn.response",
                schema={"fields": ["response_text"]},
            ),
            llm=LLMConfig(model="anthropic/claude-3-5-sonnet", temperature=0.4),
            rag=RAGConfig(enabled=True),
            state=StateConfig(max_turns=5, session_ttl_minutes=30),
            intent_model="anthropic/claude-3-haiku",
            response_model="anthropic/claude-3-5-sonnet",
            metadata=AgentConfigMetadata(author="admin"),
        )

    @pytest.fixture
    def sample_tiered_vision_config(self) -> TieredVisionConfig:
        """Create a sample tiered-vision config for testing."""
        return TieredVisionConfig(
            id="leaf-analyzer:1.0.0",
            agent_id="leaf-analyzer",
            version="1.0.0",
            status=AgentConfigStatus.ACTIVE,
            description="Cost-optimized leaf image analysis",
            input=InputConfig(
                event="collection.image.received",
                schema={"required": ["doc_id", "thumbnail_url"]},
            ),
            output=OutputConfig(
                event="ai.vision_analysis.complete",
                schema={"fields": ["classification", "confidence"]},
            ),
            llm=None,
            rag=RAGConfig(enabled=True),
            tiered_llm=TieredVisionLLMConfig(
                screen=LLMConfig(model="anthropic/claude-3-haiku", temperature=0.1),
                diagnose=LLMConfig(model="anthropic/claude-3-5-sonnet"),
            ),
            routing=TieredVisionRoutingConfig(screen_threshold=0.7),
            metadata=AgentConfigMetadata(author="admin"),
        )

    # =========================================================================
    # CRUD Operations - Create (5 tests, one per type)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_create_extractor_config(
        self,
        repository: AgentConfigRepository,
        sample_extractor_config: ExtractorConfig,
    ) -> None:
        """Create stores extractor config and returns it."""
        result = await repository.create(sample_extractor_config)

        assert result.id == sample_extractor_config.id
        assert result.agent_id == "qc-extractor"
        assert result.type == "extractor"
        assert isinstance(result, ExtractorConfig)

    @pytest.mark.asyncio
    async def test_create_explorer_config(
        self,
        repository: AgentConfigRepository,
        sample_explorer_config: ExplorerConfig,
    ) -> None:
        """Create stores explorer config and returns it."""
        result = await repository.create(sample_explorer_config)

        assert result.id == sample_explorer_config.id
        assert result.type == "explorer"
        assert isinstance(result, ExplorerConfig)

    @pytest.mark.asyncio
    async def test_create_generator_config(
        self,
        repository: AgentConfigRepository,
        sample_generator_config: GeneratorConfig,
    ) -> None:
        """Create stores generator config and returns it."""
        result = await repository.create(sample_generator_config)

        assert result.id == sample_generator_config.id
        assert result.type == "generator"
        assert isinstance(result, GeneratorConfig)

    @pytest.mark.asyncio
    async def test_create_conversational_config(
        self,
        repository: AgentConfigRepository,
        sample_conversational_config: ConversationalConfig,
    ) -> None:
        """Create stores conversational config and returns it."""
        result = await repository.create(sample_conversational_config)

        assert result.id == sample_conversational_config.id
        assert result.type == "conversational"
        assert isinstance(result, ConversationalConfig)

    @pytest.mark.asyncio
    async def test_create_tiered_vision_config(
        self,
        repository: AgentConfigRepository,
        sample_tiered_vision_config: TieredVisionConfig,
    ) -> None:
        """Create stores tiered-vision config and returns it."""
        result = await repository.create(sample_tiered_vision_config)

        assert result.id == sample_tiered_vision_config.id
        assert result.type == "tiered-vision"
        assert isinstance(result, TieredVisionConfig)

    # =========================================================================
    # CRUD Operations - Read
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_by_id_existing(
        self,
        repository: AgentConfigRepository,
        sample_extractor_config: ExtractorConfig,
    ) -> None:
        """Get by ID returns config when it exists."""
        await repository.create(sample_extractor_config)

        result = await repository.get_by_id(sample_extractor_config.id)

        assert result is not None
        assert result.id == sample_extractor_config.id
        assert result.agent_id == "qc-extractor"

    @pytest.mark.asyncio
    async def test_get_by_id_returns_correct_type(
        self,
        repository: AgentConfigRepository,
        sample_explorer_config: ExplorerConfig,
    ) -> None:
        """Get by ID returns correct discriminated type."""
        await repository.create(sample_explorer_config)

        result = await repository.get_by_id(sample_explorer_config.id)

        assert result is not None
        assert isinstance(result, ExplorerConfig)
        assert result.rag.enabled is True

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: AgentConfigRepository,
    ) -> None:
        """Get by ID returns None when config doesn't exist."""
        result = await repository.get_by_id("nonexistent:1.0.0")

        assert result is None

    # =========================================================================
    # CRUD Operations - Update
    # =========================================================================

    @pytest.mark.asyncio
    async def test_update_config(
        self,
        repository: AgentConfigRepository,
        sample_extractor_config: ExtractorConfig,
    ) -> None:
        """Update modifies config fields."""
        await repository.create(sample_extractor_config)

        # Modify config
        sample_extractor_config.status = AgentConfigStatus.ARCHIVED
        sample_extractor_config.description = "Updated description"

        result = await repository.update(sample_extractor_config)

        assert result.status == AgentConfigStatus.ARCHIVED
        assert result.description == "Updated description"

    @pytest.mark.asyncio
    async def test_update_nonexistent_raises(
        self,
        repository: AgentConfigRepository,
        sample_extractor_config: ExtractorConfig,
    ) -> None:
        """Update raises ValueError for nonexistent config."""
        with pytest.raises(ValueError) as exc_info:
            await repository.update(sample_extractor_config)
        assert "not found" in str(exc_info.value)

    # =========================================================================
    # CRUD Operations - Delete
    # =========================================================================

    @pytest.mark.asyncio
    async def test_delete_config(
        self,
        repository: AgentConfigRepository,
        sample_extractor_config: ExtractorConfig,
    ) -> None:
        """Delete removes config and returns True."""
        await repository.create(sample_extractor_config)

        result = await repository.delete(sample_extractor_config.id)

        assert result is True

        # Verify deleted
        get_result = await repository.get_by_id(sample_extractor_config.id)
        assert get_result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(
        self,
        repository: AgentConfigRepository,
    ) -> None:
        """Delete returns False for nonexistent config."""
        result = await repository.delete("nonexistent:1.0.0")

        assert result is False

    # =========================================================================
    # CRUD Operations - List
    # =========================================================================

    @pytest.mark.asyncio
    async def test_list_configs(
        self,
        repository: AgentConfigRepository,
        sample_extractor_config: ExtractorConfig,
        sample_explorer_config: ExplorerConfig,
    ) -> None:
        """List returns all configs."""
        await repository.create(sample_extractor_config)
        await repository.create(sample_explorer_config)

        configs = await repository.list()

        assert len(configs) == 2

    @pytest.mark.asyncio
    async def test_list_with_status_filter(
        self,
        repository: AgentConfigRepository,
        sample_extractor_config: ExtractorConfig,
        sample_explorer_config: ExplorerConfig,
    ) -> None:
        """List respects status filter."""
        await repository.create(sample_extractor_config)  # ACTIVE
        await repository.create(sample_explorer_config)  # STAGED

        configs = await repository.list(status=AgentConfigStatus.ACTIVE)

        assert len(configs) == 1
        assert configs[0].status == AgentConfigStatus.ACTIVE

    # =========================================================================
    # Specialized Queries
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_active(
        self,
        repository: AgentConfigRepository,
        sample_extractor_config: ExtractorConfig,
    ) -> None:
        """Get active returns the active config for an agent_id."""
        await repository.create(sample_extractor_config)  # ACTIVE

        # Create another version that's staged
        staged = ExtractorConfig(
            id="qc-extractor:2.0.0",
            agent_id="qc-extractor",
            version="2.0.0",
            status=AgentConfigStatus.STAGED,
            description="Staged version",
            input=sample_extractor_config.input,
            output=sample_extractor_config.output,
            llm=sample_extractor_config.llm,
            extraction_schema={},
            metadata=AgentConfigMetadata(author="developer"),
        )
        await repository.create(staged)

        result = await repository.get_active("qc-extractor")

        assert result is not None
        assert result.status == AgentConfigStatus.ACTIVE
        assert result.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_get_active_not_found(
        self,
        repository: AgentConfigRepository,
        sample_explorer_config: ExplorerConfig,
    ) -> None:
        """Get active returns None when no active config exists."""
        # Only staged version exists
        await repository.create(sample_explorer_config)  # STAGED

        result = await repository.get_active("disease-diagnosis")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_type(
        self,
        repository: AgentConfigRepository,
        sample_extractor_config: ExtractorConfig,
        sample_explorer_config: ExplorerConfig,
        sample_generator_config: GeneratorConfig,
    ) -> None:
        """Get by type returns all configs of specific type."""
        await repository.create(sample_extractor_config)
        await repository.create(sample_explorer_config)
        await repository.create(sample_generator_config)

        # Create another extractor
        extractor2 = ExtractorConfig(
            id="weather-extractor:1.0.0",
            agent_id="weather-extractor",
            version="1.0.0",
            status=AgentConfigStatus.ACTIVE,
            description="Weather data extraction",
            input=sample_extractor_config.input,
            output=sample_extractor_config.output,
            llm=sample_extractor_config.llm,
            extraction_schema={},
            metadata=AgentConfigMetadata(author="admin"),
        )
        await repository.create(extractor2)

        result = await repository.get_by_type(AgentType.EXTRACTOR)

        assert len(result) == 2
        assert all(c.type == "extractor" for c in result)

    @pytest.mark.asyncio
    async def test_get_by_version(
        self,
        repository: AgentConfigRepository,
        sample_extractor_config: ExtractorConfig,
    ) -> None:
        """Get by version returns specific version."""
        await repository.create(sample_extractor_config)

        # Create version 2.0.0
        v2 = ExtractorConfig(
            id="qc-extractor:2.0.0",
            agent_id="qc-extractor",
            version="2.0.0",
            status=AgentConfigStatus.STAGED,
            description="Version 2",
            input=sample_extractor_config.input,
            output=sample_extractor_config.output,
            llm=sample_extractor_config.llm,
            extraction_schema={},
            metadata=AgentConfigMetadata(author="developer"),
        )
        await repository.create(v2)

        result = await repository.get_by_version("qc-extractor", "2.0.0")

        assert result is not None
        assert result.version == "2.0.0"
        assert result.status == AgentConfigStatus.STAGED

    @pytest.mark.asyncio
    async def test_get_by_version_not_found(
        self,
        repository: AgentConfigRepository,
        sample_extractor_config: ExtractorConfig,
    ) -> None:
        """Get by version returns None for nonexistent version."""
        await repository.create(sample_extractor_config)

        result = await repository.get_by_version("qc-extractor", "99.0.0")

        assert result is None

    @pytest.mark.asyncio
    async def test_list_versions(
        self,
        repository: AgentConfigRepository,
        sample_extractor_config: ExtractorConfig,
    ) -> None:
        """List versions returns all versions of an agent config."""
        await repository.create(sample_extractor_config)

        # Create versions 2.0.0 and 3.0.0
        for ver in ["2.0.0", "3.0.0"]:
            config = ExtractorConfig(
                id=f"qc-extractor:{ver}",
                agent_id="qc-extractor",
                version=ver,
                status=AgentConfigStatus.STAGED,
                description=f"Version {ver}",
                input=sample_extractor_config.input,
                output=sample_extractor_config.output,
                llm=sample_extractor_config.llm,
                extraction_schema={},
                metadata=AgentConfigMetadata(author="developer"),
            )
            await repository.create(config)

        # Create a different agent's config
        other = ExtractorConfig(
            id="other-agent:1.0.0",
            agent_id="other-agent",
            version="1.0.0",
            status=AgentConfigStatus.ACTIVE,
            description="Other agent",
            input=sample_extractor_config.input,
            output=sample_extractor_config.output,
            llm=sample_extractor_config.llm,
            extraction_schema={},
            metadata=AgentConfigMetadata(author="admin"),
        )
        await repository.create(other)

        result = await repository.list_versions("qc-extractor")

        assert len(result) == 3
        assert all(c.agent_id == "qc-extractor" for c in result)

    @pytest.mark.asyncio
    async def test_list_versions_exclude_archived(
        self,
        repository: AgentConfigRepository,
        sample_extractor_config: ExtractorConfig,
    ) -> None:
        """List versions can exclude archived configs."""
        await repository.create(sample_extractor_config)

        # Create archived version
        archived = ExtractorConfig(
            id="qc-extractor:0.1.0",
            agent_id="qc-extractor",
            version="0.1.0",
            status=AgentConfigStatus.ARCHIVED,
            description="Old archived version",
            input=sample_extractor_config.input,
            output=sample_extractor_config.output,
            llm=sample_extractor_config.llm,
            extraction_schema={},
            metadata=AgentConfigMetadata(author="admin"),
        )
        await repository.create(archived)

        result = await repository.list_versions("qc-extractor", include_archived=False)

        assert len(result) == 1
        assert result[0].status != AgentConfigStatus.ARCHIVED

    # =========================================================================
    # Index Creation
    # =========================================================================

    @pytest.mark.asyncio
    async def test_ensure_indexes(
        self,
        repository: AgentConfigRepository,
    ) -> None:
        """Ensure indexes creates required indexes without error."""
        # This should not raise any exceptions
        await repository.ensure_indexes()
        # Note: MockMongoCollection accepts create_index calls
        # but doesn't actually create indexes in tests
