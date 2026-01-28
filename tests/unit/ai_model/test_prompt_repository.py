"""Unit tests for PromptRepository.

Tests cover:
- create() - creates new prompt
- get_by_id() - retrieves prompt by ID
- update() - updates prompt fields
- delete() - deletes prompt
- list() - lists prompts with pagination
- get_active() - gets active prompt for prompt_id
- get_by_version() - gets specific version
- list_versions() - lists all versions of a prompt
- list_by_agent() - lists prompts for an agent
- ensure_indexes() - creates proper indexes
"""

from typing import Any

import pytest
from ai_model.domain.prompt import (
    Prompt,
    PromptContent,
    PromptMetadata,
    PromptStatus,
)
from ai_model.infrastructure.repositories.prompt_repository import PromptRepository


class TestPromptRepository:
    """Tests for PromptRepository."""

    @pytest.fixture
    def mock_db(self, mock_mongodb_client: Any) -> Any:
        """Get mock database from mock client."""
        return mock_mongodb_client["ai_model"]

    @pytest.fixture
    def repository(self, mock_db: Any) -> PromptRepository:
        """Create repository with mock database."""
        return PromptRepository(mock_db)

    @pytest.fixture
    def sample_prompt(self) -> Prompt:
        """Create a sample prompt for testing."""
        return Prompt(
            id="disease-diagnosis:1.0.0",
            prompt_id="disease-diagnosis",
            agent_id="diagnose-quality-issue",
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
        """Create a second version of the sample prompt."""
        return Prompt(
            id="disease-diagnosis:2.0.0",
            prompt_id="disease-diagnosis",
            agent_id="diagnose-quality-issue",
            version="2.0.0",
            status=PromptStatus.STAGED,
            content=PromptContent(
                system_prompt="You are an expert diagnostician v2",
                template="Analyze v2: {{data}}",
            ),
            metadata=PromptMetadata(
                author="developer",
                changelog="Improved prompt accuracy",
            ),
        )

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    @pytest.mark.asyncio
    async def test_create_prompt(
        self,
        repository: PromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Create stores prompt and returns it."""
        result = await repository.create(sample_prompt)

        assert result.id == sample_prompt.id
        assert result.prompt_id == sample_prompt.prompt_id
        assert result.version == sample_prompt.version

    @pytest.mark.asyncio
    async def test_get_by_id_existing(
        self,
        repository: PromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Get by ID returns prompt when it exists."""
        await repository.create(sample_prompt)

        result = await repository.get_by_id(sample_prompt.id)

        assert result is not None
        assert result.id == sample_prompt.id
        assert result.prompt_id == sample_prompt.prompt_id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: PromptRepository,
    ) -> None:
        """Get by ID returns None when prompt doesn't exist."""
        result = await repository.get_by_id("nonexistent:1.0.0")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_prompt(
        self,
        repository: PromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Update modifies prompt fields."""
        await repository.create(sample_prompt)

        updates = {
            "status": PromptStatus.ARCHIVED.value,
            "metadata.changelog": "Archived after testing",
        }
        result = await repository.update(sample_prompt.id, updates)

        assert result is not None
        assert result.status == PromptStatus.ARCHIVED
        assert result.metadata.changelog == "Archived after testing"

    @pytest.mark.asyncio
    async def test_update_nonexistent(
        self,
        repository: PromptRepository,
    ) -> None:
        """Update returns None for nonexistent prompt."""
        result = await repository.update("nonexistent:1.0.0", {"status": "archived"})

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_prompt(
        self,
        repository: PromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Delete removes prompt and returns True."""
        await repository.create(sample_prompt)

        result = await repository.delete(sample_prompt.id)

        assert result is True

        # Verify deleted
        get_result = await repository.get_by_id(sample_prompt.id)
        assert get_result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(
        self,
        repository: PromptRepository,
    ) -> None:
        """Delete returns False for nonexistent prompt."""
        result = await repository.delete("nonexistent:1.0.0")

        assert result is False

    @pytest.mark.asyncio
    async def test_list_prompts(
        self,
        repository: PromptRepository,
        sample_prompt: Prompt,
        sample_prompt_v2: Prompt,
    ) -> None:
        """List returns all prompts with pagination info."""
        await repository.create(sample_prompt)
        await repository.create(sample_prompt_v2)

        prompts, next_token, total = await repository.list()

        assert len(prompts) == 2
        assert total == 2
        # No next page since we have less than page_size
        assert next_token is None

    @pytest.mark.asyncio
    async def test_list_with_filters(
        self,
        repository: PromptRepository,
        sample_prompt: Prompt,
        sample_prompt_v2: Prompt,
    ) -> None:
        """List respects filter criteria."""
        await repository.create(sample_prompt)
        await repository.create(sample_prompt_v2)

        prompts, _, total = await repository.list(filters={"status": PromptStatus.ACTIVE.value})

        assert len(prompts) == 1
        assert prompts[0].status == PromptStatus.ACTIVE
        assert total == 1

    # =========================================================================
    # Specialized Queries
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_active(
        self,
        repository: PromptRepository,
        sample_prompt: Prompt,
        sample_prompt_v2: Prompt,
    ) -> None:
        """Get active returns the active prompt for a prompt_id."""
        await repository.create(sample_prompt)  # ACTIVE
        await repository.create(sample_prompt_v2)  # STAGED

        result = await repository.get_active("disease-diagnosis")

        assert result is not None
        assert result.status == PromptStatus.ACTIVE
        assert result.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_get_active_not_found(
        self,
        repository: PromptRepository,
        sample_prompt_v2: Prompt,
    ) -> None:
        """Get active returns None when no active prompt exists."""
        # Only staged version exists
        await repository.create(sample_prompt_v2)

        result = await repository.get_active("disease-diagnosis")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_version(
        self,
        repository: PromptRepository,
        sample_prompt: Prompt,
        sample_prompt_v2: Prompt,
    ) -> None:
        """Get by version returns specific version."""
        await repository.create(sample_prompt)
        await repository.create(sample_prompt_v2)

        result = await repository.get_by_version("disease-diagnosis", "2.0.0")

        assert result is not None
        assert result.version == "2.0.0"
        assert result.status == PromptStatus.STAGED

    @pytest.mark.asyncio
    async def test_get_by_version_not_found(
        self,
        repository: PromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """Get by version returns None for nonexistent version."""
        await repository.create(sample_prompt)

        result = await repository.get_by_version("disease-diagnosis", "99.0.0")

        assert result is None

    @pytest.mark.asyncio
    async def test_list_versions(
        self,
        repository: PromptRepository,
        sample_prompt: Prompt,
        sample_prompt_v2: Prompt,
    ) -> None:
        """List versions returns all versions of a prompt."""
        await repository.create(sample_prompt)
        await repository.create(sample_prompt_v2)

        # Create another prompt for a different prompt_id
        other_prompt = Prompt(
            id="weather-impact:1.0.0",
            prompt_id="weather-impact",
            agent_id="analyze-weather",
            version="1.0.0",
            content=PromptContent(
                system_prompt="Weather",
                template="Template",
            ),
            metadata=PromptMetadata(author="admin"),
        )
        await repository.create(other_prompt)

        result = await repository.list_versions("disease-diagnosis")

        assert len(result) == 2
        # All should be for disease-diagnosis
        assert all(p.prompt_id == "disease-diagnosis" for p in result)

    @pytest.mark.asyncio
    async def test_list_versions_exclude_archived(
        self,
        repository: PromptRepository,
        sample_prompt: Prompt,
    ) -> None:
        """List versions can exclude archived prompts."""
        await repository.create(sample_prompt)

        archived = Prompt(
            id="disease-diagnosis:0.1.0",
            prompt_id="disease-diagnosis",
            agent_id="diagnose-quality-issue",
            version="0.1.0",
            status=PromptStatus.ARCHIVED,
            content=PromptContent(
                system_prompt="Old",
                template="Template",
            ),
            metadata=PromptMetadata(author="admin"),
        )
        await repository.create(archived)

        result = await repository.list_versions(
            "disease-diagnosis",
            include_archived=False,
        )

        assert len(result) == 1
        assert result[0].status != PromptStatus.ARCHIVED

    @pytest.mark.asyncio
    async def test_list_by_agent(
        self,
        repository: PromptRepository,
        sample_prompt: Prompt,
        sample_prompt_v2: Prompt,
    ) -> None:
        """List by agent returns prompts for specific agent."""
        await repository.create(sample_prompt)
        await repository.create(sample_prompt_v2)

        # Create prompt for different agent
        other_agent_prompt = Prompt(
            id="action-plan:1.0.0",
            prompt_id="action-plan",
            agent_id="generate-action-plan",
            version="1.0.0",
            content=PromptContent(
                system_prompt="Generate",
                template="Template",
            ),
            metadata=PromptMetadata(author="admin"),
        )
        await repository.create(other_agent_prompt)

        result = await repository.list_by_agent("diagnose-quality-issue")

        assert len(result) == 2
        assert all(p.agent_id == "diagnose-quality-issue" for p in result)

    @pytest.mark.asyncio
    async def test_list_by_agent_with_status_filter(
        self,
        repository: PromptRepository,
        sample_prompt: Prompt,
        sample_prompt_v2: Prompt,
    ) -> None:
        """List by agent respects status filter."""
        await repository.create(sample_prompt)  # ACTIVE
        await repository.create(sample_prompt_v2)  # STAGED

        result = await repository.list_by_agent(
            "diagnose-quality-issue",
            status=PromptStatus.STAGED,
        )

        assert len(result) == 1
        assert result[0].status == PromptStatus.STAGED

    # =========================================================================
    # Count by Agent (Story 9.12a)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_count_by_agent(
        self,
        repository: PromptRepository,
        sample_prompt: Prompt,
        sample_prompt_v2: Prompt,
    ) -> None:
        """Count_by_agent returns total count for an agent."""
        await repository.create(sample_prompt)
        await repository.create(sample_prompt_v2)

        count = await repository.count_by_agent("diagnose-quality-issue")

        assert count == 2

    @pytest.mark.asyncio
    async def test_count_by_agent_with_status_filter(
        self,
        repository: PromptRepository,
        sample_prompt: Prompt,
        sample_prompt_v2: Prompt,
    ) -> None:
        """Count_by_agent respects status filter."""
        await repository.create(sample_prompt)  # ACTIVE
        await repository.create(sample_prompt_v2)  # STAGED

        count = await repository.count_by_agent("diagnose-quality-issue", status=PromptStatus.ACTIVE)

        assert count == 1

    @pytest.mark.asyncio
    async def test_count_by_agent_returns_zero_for_unknown(
        self,
        repository: PromptRepository,
    ) -> None:
        """Count_by_agent returns 0 for unknown agent."""
        count = await repository.count_by_agent("unknown-agent")

        assert count == 0

    # =========================================================================
    # Index Creation
    # =========================================================================

    @pytest.mark.asyncio
    async def test_ensure_indexes(
        self,
        repository: PromptRepository,
    ) -> None:
        """Ensure indexes creates required indexes without error."""
        # This should not raise any exceptions
        await repository.ensure_indexes()
        # Note: MockMongoCollection doesn't actually implement create_index,
        # but we verify the method doesn't crash
