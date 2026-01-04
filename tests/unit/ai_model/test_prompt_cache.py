"""Unit tests for PromptCache.

Story 0.75.4: Tests for prompt caching with Change Streams (ADR-013).
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from ai_model.domain.prompt import (
    Prompt,
    PromptContent,
    PromptMetadata,
    PromptStatus,
)
from ai_model.services.prompt_cache import PromptCache
from fp_common.cache import MongoChangeStreamCache

# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def mock_db():
    """Create mock MongoDB database."""
    db = MagicMock()
    collection = MagicMock()
    db.__getitem__ = MagicMock(return_value=collection)
    return db


@pytest.fixture
def mock_collection(mock_db):
    """Get the mock collection from db."""
    return mock_db["prompts"]


@pytest.fixture
def prompt_cache(mock_db):
    """Create a PromptCache instance."""
    return PromptCache(db=mock_db)


@pytest.fixture
def sample_prompt_doc():
    """Sample prompt document from MongoDB."""
    return {
        "_id": "mongo-id-1",
        "id": "disease-diagnosis:1.0.0",
        "prompt_id": "disease-diagnosis",
        "agent_id": "diagnose-quality-issue",
        "version": "1.0.0",
        "status": "active",
        "content": {
            "system_prompt": "You are an expert tea disease diagnostician...",
            "template": "Analyze: {{event_data}}",
            "output_schema": {"type": "object"},
            "few_shot_examples": None,
        },
        "metadata": {
            "author": "admin",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "changelog": "Initial version",
            "git_commit": "abc123",
        },
        "ab_test": {
            "enabled": False,
            "traffic_percentage": 0.0,
            "test_id": None,
        },
    }


@pytest.fixture
def sample_staged_prompt_doc():
    """Sample staged prompt document for A/B testing."""
    return {
        "_id": "mongo-id-2",
        "id": "disease-diagnosis:2.0.0",
        "prompt_id": "disease-diagnosis",
        "agent_id": "diagnose-quality-issue",
        "version": "2.0.0",
        "status": "staged",
        "content": {
            "system_prompt": "You are a tea expert with deep knowledge...",
            "template": "Please analyze: {{event_data}}",
            "output_schema": {"type": "object"},
            "few_shot_examples": None,
        },
        "metadata": {
            "author": "admin",
            "created_at": "2024-01-15T00:00:00Z",
            "updated_at": "2024-01-15T00:00:00Z",
            "changelog": "Improved prompt for A/B test",
            "git_commit": "def456",
        },
        "ab_test": {
            "enabled": True,
            "traffic_percentage": 10.0,
            "test_id": "ab-test-001",
        },
    }


@pytest.fixture
def sample_prompt():
    """Create a sample Prompt instance."""
    return Prompt(
        id="disease-diagnosis:1.0.0",
        prompt_id="disease-diagnosis",
        agent_id="diagnose-quality-issue",
        version="1.0.0",
        status=PromptStatus.ACTIVE,
        content=PromptContent(
            system_prompt="You are an expert...",
            template="Analyze: {{event_data}}",
        ),
        metadata=PromptMetadata(author="test"),
    )


# =============================================================================
# INHERITANCE TESTS
# =============================================================================


class TestInheritance:
    """Tests for class inheritance."""

    def test_inherits_from_mongo_change_stream_cache(self, prompt_cache):
        """Test PromptCache inherits from MongoChangeStreamCache."""
        assert isinstance(prompt_cache, MongoChangeStreamCache)

    def test_uses_correct_collection_name(self, prompt_cache):
        """Test cache uses prompts collection."""
        assert prompt_cache._collection_name == "prompts"

    def test_uses_correct_cache_name(self, prompt_cache):
        """Test cache uses prompt as cache name."""
        assert prompt_cache._cache_name == "prompt"


# =============================================================================
# ABSTRACT METHOD IMPLEMENTATION TESTS
# =============================================================================


class TestAbstractMethods:
    """Tests for abstract method implementations."""

    def test_get_cache_key_returns_agent_id(self, prompt_cache, sample_prompt):
        """Test _get_cache_key returns the agent_id."""
        key = prompt_cache._get_cache_key(sample_prompt)
        assert key == "diagnose-quality-issue"

    def test_parse_document_creates_prompt_instance(self, prompt_cache, sample_prompt_doc):
        """Test _parse_document correctly parses prompt document."""
        prompt = prompt_cache._parse_document(sample_prompt_doc)

        assert isinstance(prompt, Prompt)
        assert prompt.id == "disease-diagnosis:1.0.0"
        assert prompt.prompt_id == "disease-diagnosis"
        assert prompt.agent_id == "diagnose-quality-issue"
        assert prompt.version == "1.0.0"
        assert prompt.status == PromptStatus.ACTIVE

    def test_parse_document_parses_content(self, prompt_cache, sample_prompt_doc):
        """Test _parse_document parses content block."""
        prompt = prompt_cache._parse_document(sample_prompt_doc)

        assert prompt.content.system_prompt == "You are an expert tea disease diagnostician..."
        assert prompt.content.template == "Analyze: {{event_data}}"
        assert prompt.content.output_schema == {"type": "object"}

    def test_parse_document_parses_metadata(self, prompt_cache, sample_prompt_doc):
        """Test _parse_document parses metadata block."""
        prompt = prompt_cache._parse_document(sample_prompt_doc)

        assert prompt.metadata.author == "admin"
        assert prompt.metadata.changelog == "Initial version"
        assert prompt.metadata.git_commit == "abc123"

    def test_parse_document_parses_ab_test(self, prompt_cache, sample_prompt_doc):
        """Test _parse_document parses ab_test block."""
        prompt = prompt_cache._parse_document(sample_prompt_doc)

        assert prompt.ab_test.enabled is False
        assert prompt.ab_test.traffic_percentage == 0.0
        assert prompt.ab_test.test_id is None

    def test_parse_document_removes_mongo_id(self, prompt_cache, sample_prompt_doc):
        """Test _parse_document removes MongoDB _id field."""
        assert "_id" in sample_prompt_doc

        prompt = prompt_cache._parse_document(sample_prompt_doc)

        # Should not raise - _id was removed before validation
        assert prompt.id == "disease-diagnosis:1.0.0"

    def test_get_filter_returns_active_status(self, prompt_cache):
        """Test _get_filter returns filter for active prompts."""
        filter_dict = prompt_cache._get_filter()
        assert filter_dict == {"status": "active"}


# =============================================================================
# DOMAIN METHOD TESTS
# =============================================================================


class TestDomainMethods:
    """Tests for domain-specific methods."""

    @pytest.mark.asyncio
    async def test_get_prompt_returns_correct_prompt(self, prompt_cache, sample_prompt):
        """Test get_prompt returns the correct prompt by agent_id."""
        # Pre-populate cache
        prompt_cache._cache = {"diagnose-quality-issue": sample_prompt}
        prompt_cache._cache_loaded_at = datetime.now(UTC)

        result = await prompt_cache.get_prompt("diagnose-quality-issue")

        assert result is not None
        assert result.agent_id == "diagnose-quality-issue"
        assert result.prompt_id == "disease-diagnosis"

    @pytest.mark.asyncio
    async def test_get_prompt_returns_none_for_missing(self, prompt_cache):
        """Test get_prompt returns None for non-existent agent_id."""
        prompt_cache._cache = {}
        prompt_cache._cache_loaded_at = datetime.now(UTC)

        result = await prompt_cache.get_prompt("nonexistent")

        assert result is None


# =============================================================================
# A/B TEST SUPPORT TESTS
# =============================================================================


class TestABTestSupport:
    """Tests for A/B testing variant support."""

    @pytest.mark.asyncio
    async def test_get_prompt_for_ab_test_returns_active_when_not_staged(self, prompt_cache, sample_prompt):
        """Test get_prompt_for_ab_test returns active prompt when use_staged=False."""
        prompt_cache._cache = {"diagnose-quality-issue": sample_prompt}
        prompt_cache._cache_loaded_at = datetime.now(UTC)

        result = await prompt_cache.get_prompt_for_ab_test(
            "diagnose-quality-issue",
            use_staged=False,
        )

        assert result is not None
        assert result.status == PromptStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_get_prompt_for_ab_test_returns_staged_prompt(
        self, prompt_cache, mock_collection, sample_staged_prompt_doc
    ):
        """Test get_prompt_for_ab_test returns staged prompt when use_staged=True."""
        # Setup mock to return staged document
        mock_collection.find_one = AsyncMock(return_value=sample_staged_prompt_doc.copy())

        result = await prompt_cache.get_prompt_for_ab_test(
            "diagnose-quality-issue",
            use_staged=True,
        )

        assert result is not None
        assert result.status == PromptStatus.STAGED
        assert result.version == "2.0.0"
        assert result.ab_test.enabled is True
        assert result.ab_test.traffic_percentage == 10.0

        # Verify correct filter was used
        mock_collection.find_one.assert_called_once_with({"agent_id": "diagnose-quality-issue", "status": "staged"})

    @pytest.mark.asyncio
    async def test_get_prompt_for_ab_test_returns_none_when_no_staged(self, prompt_cache, mock_collection):
        """Test get_prompt_for_ab_test returns None when no staged prompt exists."""
        mock_collection.find_one = AsyncMock(return_value=None)

        result = await prompt_cache.get_prompt_for_ab_test(
            "diagnose-quality-issue",
            use_staged=True,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_staged_prompts_not_cached(self, prompt_cache, mock_collection, sample_staged_prompt_doc):
        """Test staged prompts are fetched fresh from DB (not cached)."""
        mock_collection.find_one = AsyncMock(return_value=sample_staged_prompt_doc.copy())

        # Call twice
        await prompt_cache.get_prompt_for_ab_test("diagnose-quality-issue", use_staged=True)
        await prompt_cache.get_prompt_for_ab_test("diagnose-quality-issue", use_staged=True)

        # Should have called find_one twice (not cached)
        assert mock_collection.find_one.call_count == 2


# =============================================================================
# PROMPT STATUS TESTS
# =============================================================================


class TestPromptStatus:
    """Tests for prompt status handling."""

    def test_parses_all_status_values(self, prompt_cache, sample_prompt_doc):
        """Test parsing prompts with different status values."""
        for status in ["draft", "staged", "active", "archived"]:
            doc = sample_prompt_doc.copy()
            doc["status"] = status
            doc.pop("_id", None)

            prompt = prompt_cache._parse_document(doc)

            assert prompt.status.value == status

    def test_only_active_prompts_cached(self, prompt_cache):
        """Test filter only caches active prompts."""
        filter_dict = prompt_cache._get_filter()
        assert filter_dict["status"] == "active"
