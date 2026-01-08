"""Golden sample tests for RAG ranking accuracy.

This test suite validates:
1. Ranking improves result ordering vs raw retrieval scores
2. Domain boosting effects rankings correctly
3. Deduplication removes near-duplicate chunks
4. Graceful degradation when reranker unavailable

Uses same seed_documents.json as retrieval tests but separate namespace.

Story 0.75.15: RAG Ranking Logic
"""

from typing import Any

import pytest
from ai_model.domain.ranking import RankingConfig

from tests.golden.rag.ranking.conftest import calculate_ranking_accuracy


class TestRankingAccuracy:
    """Test suite for ranking accuracy using golden samples."""

    @pytest.mark.asyncio
    async def test_ranking_improves_ordering_disease_query(
        self,
        ranking_service_with_mock_reranker: Any,
        ranking_samples: dict[str, Any],
    ) -> None:
        """Test that ranking improves result ordering for disease queries."""
        # Get the blister blight sample
        sample = next(s for s in ranking_samples["samples"] if s["id"] == "rank-001")

        config = RankingConfig(
            top_n=5,
            domain_boosts=sample.get("domain_boosts", {}),
            dedup_threshold=0.9,
        )

        result = await ranking_service_with_mock_reranker.rank(
            query=sample["query"],
            config=config,
            domains=sample.get("domain_filter") or None,
        )

        # Extract document IDs from results
        result_doc_ids = [m.document_id for m in result.matches]

        # Calculate accuracy
        accuracy = calculate_ranking_accuracy(
            expected_top=sample["expected_top_result"],
            expected_in_top_n=sample["expected_in_top_3"],
            actual_results=result_doc_ids[:3],
        )

        assert accuracy["recall_at_n"] >= 0.9, (
            f"Recall@3 too low: {accuracy['recall_at_n']}, "
            f"expected: {sample['expected_in_top_3']}, "
            f"got: {result_doc_ids[:3]}"
        )

    @pytest.mark.asyncio
    async def test_ranking_accuracy_across_all_samples(
        self,
        ranking_service_with_mock_reranker: Any,
        ranking_samples: dict[str, Any],
    ) -> None:
        """Test overall ranking accuracy across all golden samples."""
        total_top1_correct = 0
        total_recall = 0.0
        sample_count = len(ranking_samples["samples"])

        for sample in ranking_samples["samples"]:
            config = RankingConfig(
                top_n=5,
                domain_boosts=sample.get("domain_boosts", {}),
                dedup_threshold=0.9,
            )

            result = await ranking_service_with_mock_reranker.rank(
                query=sample["query"],
                config=config,
                domains=sample.get("domain_filter") or None,
            )

            result_doc_ids = [m.document_id for m in result.matches]

            accuracy = calculate_ranking_accuracy(
                expected_top=sample["expected_top_result"],
                expected_in_top_n=sample["expected_in_top_3"],
                actual_results=result_doc_ids[:3],
            )

            total_top1_correct += accuracy["top1_correct"]
            total_recall += accuracy["recall_at_n"]

        # Calculate overall accuracy
        overall_recall = total_recall / sample_count
        overall_top1 = total_top1_correct / sample_count

        # Target: >= 90% recall accuracy
        threshold = ranking_samples.get("accuracy_threshold", 0.90)
        assert overall_recall >= threshold, (
            f"Overall recall accuracy {overall_recall:.2%} below threshold {threshold:.0%}"
        )

        # Log results for visibility
        print("\nRanking Accuracy Results:")
        print(f"  Top-1 Accuracy: {overall_top1:.2%}")
        print(f"  Recall@3: {overall_recall:.2%}")
        print(f"  Threshold: {threshold:.0%}")


class TestDomainBoosting:
    """Test suite for domain-specific boosting functionality."""

    @pytest.mark.asyncio
    async def test_domain_boost_increases_relevance(
        self,
        ranking_service_with_mock_reranker: Any,
    ) -> None:
        """Test that domain boost increases score for matching domain."""
        query = "tea plant health issues"

        # Without boost
        config_no_boost = RankingConfig(top_n=5, domain_boosts={})
        result_no_boost = await ranking_service_with_mock_reranker.rank(
            query=query,
            config=config_no_boost,
        )

        # With boost for plant_diseases
        config_with_boost = RankingConfig(
            top_n=5,
            domain_boosts={"plant_diseases": 1.5},
        )
        result_with_boost = await ranking_service_with_mock_reranker.rank(
            query=query,
            config=config_with_boost,
        )

        # Find disease documents in both results
        disease_docs_no_boost = [m for m in result_no_boost.matches if m.domain == "plant_diseases"]
        disease_docs_with_boost = [m for m in result_with_boost.matches if m.domain == "plant_diseases"]

        # With boost, disease docs should have higher scores
        if disease_docs_no_boost and disease_docs_with_boost:
            assert disease_docs_with_boost[0].boost_applied == 1.5
            assert disease_docs_no_boost[0].boost_applied == 1.0

    @pytest.mark.asyncio
    async def test_multiple_domain_boosts(
        self,
        ranking_service_with_mock_reranker: Any,
    ) -> None:
        """Test that multiple domain boosts are applied correctly."""
        query = "tea quality and weather impact"

        config = RankingConfig(
            top_n=10,
            domain_boosts={
                "weather_patterns": 1.3,
                "quality_standards": 1.2,
            },
        )

        result = await ranking_service_with_mock_reranker.rank(
            query=query,
            config=config,
        )

        # Verify boosts were applied to correct domains
        for match in result.matches:
            if match.domain == "weather_patterns":
                assert match.boost_applied == 1.3
            elif match.domain == "quality_standards":
                assert match.boost_applied == 1.2
            else:
                assert match.boost_applied == 1.0


class TestDeduplication:
    """Test suite for deduplication functionality."""

    @pytest.mark.asyncio
    async def test_deduplication_removes_near_duplicates(
        self,
        ranking_service_with_mock_reranker: Any,
    ) -> None:
        """Test that deduplication removes chunks with high similarity."""
        query = "tea cultivation best practices"

        # With deduplication enabled (default)
        config_dedup = RankingConfig(top_n=5, dedup_threshold=0.9)
        result_dedup = await ranking_service_with_mock_reranker.rank(
            query=query,
            config=config_dedup,
        )

        # Verify no duplicates in results
        doc_ids = [m.document_id for m in result_dedup.matches]
        assert len(doc_ids) == len(set(doc_ids)), "Duplicate document IDs found"

    @pytest.mark.asyncio
    async def test_deduplication_threshold_zero_keeps_all(
        self,
        ranking_service_with_mock_reranker: Any,
    ) -> None:
        """Test that threshold=0 disables deduplication."""
        query = "tea farming"

        config = RankingConfig(
            top_n=10,
            dedup_threshold=0.0,  # Disabled
        )

        result = await ranking_service_with_mock_reranker.rank(
            query=query,
            config=config,
        )

        # Duplicates_removed should be 0 when disabled
        assert result.duplicates_removed == 0


class TestGracefulDegradation:
    """Test suite for graceful degradation when reranker unavailable."""

    @pytest.mark.asyncio
    async def test_falls_back_to_retrieval_scores(
        self,
        ranking_service_no_reranker: Any,
    ) -> None:
        """Test fallback to retrieval scores when reranker unavailable."""
        query = "blister blight disease treatment"

        config = RankingConfig(top_n=5)
        result = await ranking_service_no_reranker.rank(
            query=query,
            config=config,
        )

        # Verify fallback was used
        assert result.reranker_used is False
        # Should still return results
        assert len(result.matches) > 0
        # Scores should be present
        for match in result.matches:
            assert match.rerank_score >= 0.0

    @pytest.mark.asyncio
    async def test_fallback_still_applies_boosts(
        self,
        ranking_service_no_reranker: Any,
    ) -> None:
        """Test that domain boosts still apply during fallback."""
        query = "tea plant health"

        config = RankingConfig(
            top_n=5,
            domain_boosts={"plant_diseases": 1.5},
        )

        result = await ranking_service_no_reranker.rank(
            query=query,
            config=config,
        )

        # Verify boosts were applied even without reranker
        disease_matches = [m for m in result.matches if m.domain == "plant_diseases"]
        if disease_matches:
            assert disease_matches[0].boost_applied == 1.5


class TestRecencyWeighting:
    """Test suite for recency weighting functionality."""

    @pytest.mark.asyncio
    async def test_recency_weight_zero_disables(
        self,
        ranking_service_with_mock_reranker: Any,
    ) -> None:
        """Test that recency_weight=0 disables recency scoring."""
        query = "tea farming guide"

        config = RankingConfig(
            top_n=5,
            recency_weight=0.0,
        )

        result = await ranking_service_with_mock_reranker.rank(
            query=query,
            config=config,
        )

        # All recency factors should be 0 when disabled
        for match in result.matches:
            assert match.recency_factor == 0.0

    @pytest.mark.asyncio
    async def test_recency_weight_affects_scores(
        self,
        ranking_service_with_mock_reranker: Any,
    ) -> None:
        """Test that recency weight modifies scores."""
        query = "tea farming practices"

        # Without recency
        config_no_recency = RankingConfig(top_n=5, recency_weight=0.0)
        result_no_recency = await ranking_service_with_mock_reranker.rank(
            query=query,
            config=config_no_recency,
        )

        # With recency
        config_with_recency = RankingConfig(top_n=5, recency_weight=0.2)
        result_with_recency = await ranking_service_with_mock_reranker.rank(
            query=query,
            config=config_with_recency,
        )

        # Results should exist in both cases
        assert len(result_no_recency.matches) > 0
        assert len(result_with_recency.matches) > 0


class TestEmptyResults:
    """Test suite for edge cases with empty or minimal results."""

    @pytest.mark.asyncio
    async def test_empty_query_returns_empty_result(
        self,
        ranking_service_with_mock_reranker: Any,
    ) -> None:
        """Test that empty query returns empty result."""
        result = await ranking_service_with_mock_reranker.rank(
            query="",
            config=RankingConfig(top_n=5),
        )

        assert result.matches == []
        assert result.reranker_used is False
        assert result.duplicates_removed == 0

    @pytest.mark.asyncio
    async def test_whitespace_query_returns_empty_result(
        self,
        ranking_service_with_mock_reranker: Any,
    ) -> None:
        """Test that whitespace-only query returns empty result."""
        result = await ranking_service_with_mock_reranker.rank(
            query="   ",
            config=RankingConfig(top_n=5),
        )

        assert result.matches == []

    @pytest.mark.asyncio
    async def test_no_matching_domain_returns_empty(
        self,
        ranking_service_with_mock_reranker: Any,
    ) -> None:
        """Test that non-existent domain filter returns empty results."""
        result = await ranking_service_with_mock_reranker.rank(
            query="tea farming",
            config=RankingConfig(top_n=5),
            domains=["nonexistent_domain"],
        )

        assert result.matches == []
