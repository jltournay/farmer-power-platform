"""Unit tests for RankingService.

Tests cover:
1. RankingService orchestration (retrieve -> rerank -> boost -> dedup)
2. Pinecone reranker integration (mocked)
3. Domain boosting calculations
4. Recency weighting calculations
5. Deduplication logic
6. Graceful degradation when reranker unavailable
7. Edge cases (empty results, single result, all duplicates)

Story 0.75.15: RAG Ranking Logic
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from ai_model.domain.ranking import RankedMatch, RankingConfig, RankingResult
from ai_model.domain.retrieval import RetrievalMatch, RetrievalResult
from ai_model.services.deduplication import calculate_jaccard_similarity, deduplicate_matches
from ai_model.services.ranking_service import (
    RankingService,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings for ranking service."""
    settings = MagicMock()
    settings.pinecone_enabled = True
    settings.pinecone_api_key = MagicMock()
    settings.pinecone_api_key.get_secret_value.return_value = "test-api-key"
    return settings


@pytest.fixture
def mock_settings_no_pinecone() -> MagicMock:
    """Create mock settings without Pinecone enabled."""
    settings = MagicMock()
    settings.pinecone_enabled = False
    settings.pinecone_api_key = None
    return settings


@pytest.fixture
def mock_retrieval_service() -> MagicMock:
    """Create mock retrieval service."""
    service = MagicMock()
    service.retrieve = AsyncMock()
    return service


@pytest.fixture
def sample_retrieval_result() -> RetrievalResult:
    """Create sample retrieval result for testing."""
    return RetrievalResult(
        matches=[
            RetrievalMatch(
                chunk_id="chunk-1",
                content="This is content about blister blight disease affecting tea plants.",
                score=0.85,
                document_id="doc-1",
                title="Blister Blight Guide",
                domain="plant_diseases",
                metadata={"region": "Kenya"},
            ),
            RetrievalMatch(
                chunk_id="chunk-2",
                content="This is content about tea plucking standards and techniques.",
                score=0.78,
                document_id="doc-2",
                title="Plucking Standards",
                domain="tea_cultivation",
                metadata={"region": "Kenya"},
            ),
            RetrievalMatch(
                chunk_id="chunk-3",
                content="This is content about frost damage prevention in tea.",
                score=0.72,
                document_id="doc-3",
                title="Frost Prevention",
                domain="weather_patterns",
                metadata={"region": "Kenya"},
            ),
        ],
        query="tea disease treatment",
        namespace="test-ns",
        total_matches=3,
    )


@pytest.fixture
def mock_pinecone_client() -> MagicMock:
    """Create mock Pinecone client with reranker."""
    client = MagicMock()

    def mock_rerank(
        model: str,
        query: str,
        documents: list[dict],
        top_n: int = 5,
        return_documents: bool = False,
    ) -> MagicMock:
        """Mock reranker that reverses scores for testing."""
        result = MagicMock()
        result.data = [
            {"index": i, "score": 0.9 - (i * 0.1), "document": doc} for i, doc in enumerate(documents[:top_n])
        ]
        return result

    client.inference.rerank = mock_rerank
    return client


# ============================================================================
# Deduplication Unit Tests
# ============================================================================


class TestJaccardSimilarity:
    """Test Jaccard similarity calculation."""

    def test_identical_texts_return_one(self) -> None:
        """Test that identical texts return similarity of 1.0."""
        text = "hello world"
        assert calculate_jaccard_similarity(text, text) == 1.0

    def test_completely_different_texts_return_zero(self) -> None:
        """Test that completely different texts return 0.0."""
        assert calculate_jaccard_similarity("abc def", "xyz uvw") == 0.0

    def test_partial_overlap(self) -> None:
        """Test partial overlap calculation."""
        # "hello" overlaps, "world" and "there" don't
        # Intersection: 1, Union: 3, Jaccard: 1/3 ≈ 0.333
        result = calculate_jaccard_similarity("hello world", "hello there")
        assert 0.3 < result < 0.4

    def test_empty_texts_return_zero(self) -> None:
        """Test that empty texts return 0.0."""
        assert calculate_jaccard_similarity("", "hello") == 0.0
        assert calculate_jaccard_similarity("hello", "") == 0.0
        assert calculate_jaccard_similarity("", "") == 0.0

    def test_case_insensitive(self) -> None:
        """Test that comparison is case-insensitive."""
        assert calculate_jaccard_similarity("HELLO world", "hello WORLD") == 1.0


class TestDeduplicateMatches:
    """Test deduplication function."""

    def test_empty_list_returns_empty(self) -> None:
        """Test that empty list returns empty list."""
        result, removed = deduplicate_matches([], threshold=0.9)
        assert result == []
        assert removed == 0

    def test_single_item_returns_unchanged(self) -> None:
        """Test that single item list returns unchanged."""
        match = RankedMatch(
            chunk_id="c1",
            content="test content",
            score=0.8,
            rerank_score=0.9,
            document_id="d1",
            title="Test",
            domain="test",
        )
        result, removed = deduplicate_matches([match], threshold=0.9)
        assert len(result) == 1
        assert removed == 0

    def test_removes_duplicates_above_threshold(self) -> None:
        """Test that duplicates above threshold are removed."""
        match1 = RankedMatch(
            chunk_id="c1",
            content="blister blight disease affects tea plants severely",
            score=0.8,
            rerank_score=0.9,
            document_id="d1",
            title="Test 1",
            domain="test",
        )
        match2 = RankedMatch(
            chunk_id="c2",
            content="blister blight disease affects tea plants severely",  # Identical
            score=0.7,
            rerank_score=0.85,
            document_id="d2",
            title="Test 2",
            domain="test",
        )

        result, removed = deduplicate_matches([match1, match2], threshold=0.9)
        assert len(result) == 1
        assert removed == 1
        assert result[0].chunk_id == "c1"  # Higher scored one kept

    def test_keeps_different_content(self) -> None:
        """Test that different content is kept."""
        match1 = RankedMatch(
            chunk_id="c1",
            content="blister blight disease",
            score=0.8,
            rerank_score=0.9,
            document_id="d1",
            title="Test 1",
            domain="test",
        )
        match2 = RankedMatch(
            chunk_id="c2",
            content="frost damage prevention",  # Different
            score=0.7,
            rerank_score=0.85,
            document_id="d2",
            title="Test 2",
            domain="test",
        )

        result, removed = deduplicate_matches([match1, match2], threshold=0.9)
        assert len(result) == 2
        assert removed == 0

    def test_threshold_zero_disables(self) -> None:
        """Test that threshold=0 disables deduplication."""
        match1 = RankedMatch(
            chunk_id="c1",
            content="same content",
            score=0.8,
            rerank_score=0.9,
            document_id="d1",
            title="Test 1",
            domain="test",
        )
        match2 = RankedMatch(
            chunk_id="c2",
            content="same content",
            score=0.7,
            rerank_score=0.85,
            document_id="d2",
            title="Test 2",
            domain="test",
        )

        result, removed = deduplicate_matches([match1, match2], threshold=0.0)
        assert len(result) == 2
        assert removed == 0


# ============================================================================
# RankingService Unit Tests
# ============================================================================


class TestRankingServiceOrchestration:
    """Test RankingService orchestration flow."""

    @pytest.mark.asyncio
    async def test_rank_calls_retrieval_service(
        self,
        mock_retrieval_service: MagicMock,
        mock_settings: MagicMock,
        sample_retrieval_result: RetrievalResult,
    ) -> None:
        """Test that rank() calls retrieval service."""
        mock_retrieval_service.retrieve.return_value = sample_retrieval_result

        service = RankingService(
            retrieval_service=mock_retrieval_service,
            settings=mock_settings,
        )
        # Disable reranker for this test
        mock_settings.pinecone_enabled = False

        await service.rank(query="test query", config=RankingConfig(top_n=5))

        mock_retrieval_service.retrieve.assert_called_once()

    @pytest.mark.asyncio
    async def test_rank_returns_ranking_result(
        self,
        mock_retrieval_service: MagicMock,
        mock_settings_no_pinecone: MagicMock,
        sample_retrieval_result: RetrievalResult,
    ) -> None:
        """Test that rank() returns RankingResult."""
        mock_retrieval_service.retrieve.return_value = sample_retrieval_result

        service = RankingService(
            retrieval_service=mock_retrieval_service,
            settings=mock_settings_no_pinecone,
        )

        result = await service.rank(query="test query", config=RankingConfig(top_n=5))

        assert isinstance(result, RankingResult)
        assert result.query == "test query"

    @pytest.mark.asyncio
    async def test_empty_query_returns_empty_result(
        self,
        mock_retrieval_service: MagicMock,
        mock_settings_no_pinecone: MagicMock,
    ) -> None:
        """Test that empty query returns empty result."""
        service = RankingService(
            retrieval_service=mock_retrieval_service,
            settings=mock_settings_no_pinecone,
        )

        result = await service.rank(query="", config=RankingConfig(top_n=5))

        assert result.matches == []
        assert result.reranker_used is False


class TestPineconeRerankerIntegration:
    """Test Pinecone reranker integration."""

    @pytest.mark.asyncio
    async def test_reranker_is_called_when_available(
        self,
        mock_retrieval_service: MagicMock,
        mock_settings: MagicMock,
        mock_pinecone_client: MagicMock,
        sample_retrieval_result: RetrievalResult,
    ) -> None:
        """Test that reranker is called when Pinecone is configured."""
        mock_retrieval_service.retrieve.return_value = sample_retrieval_result

        service = RankingService(
            retrieval_service=mock_retrieval_service,
            settings=mock_settings,
        )
        service._client = mock_pinecone_client

        result = await service.rank(query="test query", config=RankingConfig(top_n=5))

        assert result.reranker_used is True

    @pytest.mark.asyncio
    async def test_rerank_result_contains_scores(
        self,
        mock_retrieval_service: MagicMock,
        mock_settings: MagicMock,
        mock_pinecone_client: MagicMock,
        sample_retrieval_result: RetrievalResult,
    ) -> None:
        """Test that reranked results contain rerank scores."""
        mock_retrieval_service.retrieve.return_value = sample_retrieval_result

        service = RankingService(
            retrieval_service=mock_retrieval_service,
            settings=mock_settings,
        )
        service._client = mock_pinecone_client

        result = await service.rank(query="test query", config=RankingConfig(top_n=5))

        for match in result.matches:
            assert match.rerank_score >= 0.0


class TestDomainBoosting:
    """Test domain boosting functionality."""

    @pytest.mark.asyncio
    async def test_domain_boost_multiplies_score(
        self,
        mock_retrieval_service: MagicMock,
        mock_settings_no_pinecone: MagicMock,
        sample_retrieval_result: RetrievalResult,
    ) -> None:
        """Test that domain boost multiplies the rerank score."""
        mock_retrieval_service.retrieve.return_value = sample_retrieval_result

        service = RankingService(
            retrieval_service=mock_retrieval_service,
            settings=mock_settings_no_pinecone,
        )

        config = RankingConfig(
            top_n=5,
            domain_boosts={"plant_diseases": 1.5},
        )

        result = await service.rank(query="test query", config=config)

        # Find the plant_diseases match
        disease_match = next((m for m in result.matches if m.domain == "plant_diseases"), None)
        assert disease_match is not None
        assert disease_match.boost_applied == 1.5

    @pytest.mark.asyncio
    async def test_no_boost_for_unlisted_domain(
        self,
        mock_retrieval_service: MagicMock,
        mock_settings_no_pinecone: MagicMock,
        sample_retrieval_result: RetrievalResult,
    ) -> None:
        """Test that unlisted domains get no boost (1.0)."""
        mock_retrieval_service.retrieve.return_value = sample_retrieval_result

        service = RankingService(
            retrieval_service=mock_retrieval_service,
            settings=mock_settings_no_pinecone,
        )

        config = RankingConfig(
            top_n=5,
            domain_boosts={"plant_diseases": 1.5},  # Only this domain boosted
        )

        result = await service.rank(query="test query", config=config)

        # Find the tea_cultivation match (not boosted)
        cultivation_match = next((m for m in result.matches if m.domain == "tea_cultivation"), None)
        assert cultivation_match is not None
        assert cultivation_match.boost_applied == 1.0


class TestRecencyWeighting:
    """Test recency weighting functionality."""

    @pytest.mark.asyncio
    async def test_recency_weight_zero_disables(
        self,
        mock_retrieval_service: MagicMock,
        mock_settings_no_pinecone: MagicMock,
        sample_retrieval_result: RetrievalResult,
    ) -> None:
        """Test that recency_weight=0 disables recency scoring."""
        mock_retrieval_service.retrieve.return_value = sample_retrieval_result

        service = RankingService(
            retrieval_service=mock_retrieval_service,
            settings=mock_settings_no_pinecone,
        )

        config = RankingConfig(top_n=5, recency_weight=0.0)

        result = await service.rank(query="test query", config=config)

        for match in result.matches:
            assert match.recency_factor == 0.0

    @pytest.mark.asyncio
    async def test_recency_factor_applied_when_enabled(
        self,
        mock_retrieval_service: MagicMock,
        mock_settings_no_pinecone: MagicMock,
        sample_retrieval_result: RetrievalResult,
    ) -> None:
        """Test that recency factor is applied when weight > 0."""
        mock_retrieval_service.retrieve.return_value = sample_retrieval_result

        service = RankingService(
            retrieval_service=mock_retrieval_service,
            settings=mock_settings_no_pinecone,
        )

        config = RankingConfig(top_n=5, recency_weight=0.2)

        result = await service.rank(query="test query", config=config)

        # With no updated_at, recency_factor should be 0.5 (neutral)
        for match in result.matches:
            assert match.recency_factor == 0.5


class TestGracefulDegradation:
    """Test graceful degradation when reranker unavailable."""

    @pytest.mark.asyncio
    async def test_fallback_when_pinecone_disabled(
        self,
        mock_retrieval_service: MagicMock,
        mock_settings_no_pinecone: MagicMock,
        sample_retrieval_result: RetrievalResult,
    ) -> None:
        """Test fallback to retrieval scores when Pinecone disabled."""
        mock_retrieval_service.retrieve.return_value = sample_retrieval_result

        service = RankingService(
            retrieval_service=mock_retrieval_service,
            settings=mock_settings_no_pinecone,
        )

        result = await service.rank(query="test query", config=RankingConfig(top_n=5))

        assert result.reranker_used is False
        assert len(result.matches) > 0

    @pytest.mark.asyncio
    async def test_fallback_uses_retrieval_scores(
        self,
        mock_retrieval_service: MagicMock,
        mock_settings_no_pinecone: MagicMock,
        sample_retrieval_result: RetrievalResult,
    ) -> None:
        """Test that fallback uses retrieval scores as rerank scores."""
        mock_retrieval_service.retrieve.return_value = sample_retrieval_result

        service = RankingService(
            retrieval_service=mock_retrieval_service,
            settings=mock_settings_no_pinecone,
        )

        result = await service.rank(query="test query", config=RankingConfig(top_n=5))

        # rerank_score should equal original score in fallback
        for match in result.matches:
            assert match.rerank_score == match.score


class TestEdgeCases:
    """Test edge cases."""

    @pytest.mark.asyncio
    async def test_whitespace_query_returns_empty(
        self,
        mock_retrieval_service: MagicMock,
        mock_settings_no_pinecone: MagicMock,
    ) -> None:
        """Test that whitespace query returns empty result."""
        service = RankingService(
            retrieval_service=mock_retrieval_service,
            settings=mock_settings_no_pinecone,
        )

        result = await service.rank(query="   ", config=RankingConfig(top_n=5))

        assert result.matches == []

    @pytest.mark.asyncio
    async def test_empty_retrieval_returns_empty(
        self,
        mock_retrieval_service: MagicMock,
        mock_settings_no_pinecone: MagicMock,
    ) -> None:
        """Test that empty retrieval result returns empty ranking."""
        mock_retrieval_service.retrieve.return_value = RetrievalResult(
            matches=[],
            query="test",
            namespace="test-ns",
            total_matches=0,
        )

        service = RankingService(
            retrieval_service=mock_retrieval_service,
            settings=mock_settings_no_pinecone,
        )

        result = await service.rank(query="test query", config=RankingConfig(top_n=5))

        assert result.matches == []
        assert result.reranker_used is False

    @pytest.mark.asyncio
    async def test_top_n_limits_results(
        self,
        mock_retrieval_service: MagicMock,
        mock_settings_no_pinecone: MagicMock,
        sample_retrieval_result: RetrievalResult,
    ) -> None:
        """Test that top_n limits the number of results."""
        mock_retrieval_service.retrieve.return_value = sample_retrieval_result

        service = RankingService(
            retrieval_service=mock_retrieval_service,
            settings=mock_settings_no_pinecone,
        )

        # Request only 2 results
        result = await service.rank(query="test query", config=RankingConfig(top_n=2))

        assert len(result.matches) <= 2


class TestRankRetrievalResult:
    """Test rank_retrieval_result method."""

    @pytest.mark.asyncio
    async def test_ranks_pre_retrieved_results(
        self,
        mock_retrieval_service: MagicMock,
        mock_settings_no_pinecone: MagicMock,
        sample_retrieval_result: RetrievalResult,
    ) -> None:
        """Test ranking pre-retrieved results without calling retrieval."""
        service = RankingService(
            retrieval_service=mock_retrieval_service,
            settings=mock_settings_no_pinecone,
        )

        result = await service.rank_retrieval_result(
            query="test query",
            matches=sample_retrieval_result.matches,
            config=RankingConfig(top_n=5),
        )

        # Should not have called retrieve
        mock_retrieval_service.retrieve.assert_not_called()
        # Should have results
        assert len(result.matches) > 0

    @pytest.mark.asyncio
    async def test_empty_matches_returns_empty(
        self,
        mock_retrieval_service: MagicMock,
        mock_settings_no_pinecone: MagicMock,
    ) -> None:
        """Test that empty matches returns empty result."""
        service = RankingService(
            retrieval_service=mock_retrieval_service,
            settings=mock_settings_no_pinecone,
        )

        result = await service.rank_retrieval_result(
            query="test query",
            matches=[],
            config=RankingConfig(top_n=5),
        )

        assert result.matches == []
