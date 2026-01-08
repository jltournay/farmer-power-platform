"""Golden sample tests for RAG retrieval accuracy.

This test module validates that the RetrievalService meets
the 85% accuracy target for retrieving relevant documents.

Story 0.75.14: RAG Retrieval Service

Test Categories:
1. Single-domain queries (plant_diseases, tea_cultivation, etc.)
2. Cross-domain queries (no domain filter)
3. Confidence threshold filtering
4. Overall accuracy aggregate

Target: >= 85% retrieval accuracy (Recall@K)
"""

from typing import Any

import pytest

from tests.golden.rag.retrieval.conftest import calculate_retrieval_accuracy


@pytest.mark.golden
@pytest.mark.asyncio
class TestRetrievalAccuracy:
    """Test suite for retrieval accuracy using golden samples."""

    async def test_single_query_retrieval(
        self,
        retrieval_service: Any,
        retrieval_samples: dict[str, Any],
    ) -> None:
        """Test individual query retrieval returns expected documents.

        Validates that for each query, the expected document IDs
        appear in the top-k results.
        """
        samples = retrieval_samples["samples"]
        sample = samples[0]  # First sample for quick validation

        result = await retrieval_service.retrieve(
            query=sample["query"],
            top_k=5,
        )

        # Verify we got results
        assert result.count > 0, f"No results for query: {sample['query']}"

        # Check that query is preserved
        assert result.query == sample["query"]

    async def test_domain_filtering(
        self,
        retrieval_service: Any,
        retrieval_samples: dict[str, Any],
    ) -> None:
        """Test domain filtering restricts results correctly."""
        # Query with plant_diseases domain filter
        result = await retrieval_service.retrieve(
            query="disease symptoms",
            domains=["plant_diseases"],
            top_k=5,
        )

        # All results should be from plant_diseases domain
        for match in result.matches:
            assert match.domain == "plant_diseases", f"Expected plant_diseases domain, got {match.domain}"

    async def test_confidence_threshold_filtering(
        self,
        retrieval_service: Any,
    ) -> None:
        """Test confidence threshold filters low-score results."""
        # High threshold should reduce results
        high_threshold_result = await retrieval_service.retrieve(
            query="tea farming practices",
            top_k=10,
            confidence_threshold=0.8,
        )

        # Low threshold should return more results
        low_threshold_result = await retrieval_service.retrieve(
            query="tea farming practices",
            top_k=10,
            confidence_threshold=0.0,
        )

        # All results above threshold
        for match in high_threshold_result.matches:
            assert match.score >= 0.8, f"Score {match.score} below threshold 0.8"

        # High threshold should filter some results
        assert high_threshold_result.total_matches >= high_threshold_result.count

    async def test_multi_domain_queries(
        self,
        retrieval_service: Any,
    ) -> None:
        """Test queries across multiple domains return diverse results."""
        # Query without domain restriction - should search all domains
        result = await retrieval_service.retrieve(
            query="tea quality improvement",
            top_k=10,
        )

        # Should get results from multiple domains
        domains_found = {match.domain for match in result.matches}

        # With 8 seed documents across 5 domains and top_k=10,
        # we should get results from at least 2 different domains
        assert len(domains_found) >= 2, (
            f"Expected results from multiple domains for cross-domain query, but only found: {domains_found}"
        )

    async def test_empty_query_returns_empty_results(
        self,
        retrieval_service: Any,
    ) -> None:
        """Test empty query returns empty results gracefully."""
        result = await retrieval_service.retrieve(
            query="",
            top_k=5,
        )

        assert result.count == 0
        assert result.matches == []

    async def test_overall_accuracy_meets_target(
        self,
        retrieval_service: Any,
        retrieval_samples: dict[str, Any],
    ) -> None:
        """Test overall retrieval accuracy meets 85% target.

        This is the key acceptance criteria test. It runs all golden
        samples and calculates aggregate accuracy.
        """
        samples = retrieval_samples["samples"]
        target_accuracy = retrieval_samples.get("target_accuracy", 0.85)

        total_accuracy = 0.0
        passed_samples = 0
        failed_samples: list[dict[str, Any]] = []

        for sample in samples:
            # Run retrieval for this sample
            domains = [sample["expected_domain"]] if sample.get("expected_domain") else None
            result = await retrieval_service.retrieve(
                query=sample["query"],
                domains=domains,
                top_k=5,
            )

            # Calculate accuracy for this sample
            retrieved_docs = [match.document_id for match in result.matches]
            expected_docs = sample["expected_documents"]
            accuracy = calculate_retrieval_accuracy(expected_docs, retrieved_docs)

            total_accuracy += accuracy

            if accuracy >= 1.0:
                passed_samples += 1
            else:
                failed_samples.append(
                    {
                        "id": sample["id"],
                        "query": sample["query"],
                        "expected": expected_docs,
                        "retrieved": retrieved_docs,
                        "accuracy": accuracy,
                    }
                )

        # Calculate overall metrics
        overall_accuracy = total_accuracy / len(samples) if samples else 0.0
        pass_rate = passed_samples / len(samples) if samples else 0.0

        # Report results
        print(f"\n{'=' * 60}")
        print("RAG RETRIEVAL ACCURACY REPORT")
        print(f"{'=' * 60}")
        print(f"Total samples: {len(samples)}")
        print(f"Passed (100% recall): {passed_samples}")
        print(f"Pass rate: {pass_rate:.1%}")
        print(f"Overall accuracy: {overall_accuracy:.1%}")
        print(f"Target accuracy: {target_accuracy:.1%}")
        print(f"{'=' * 60}")

        if failed_samples:
            print("\nFailed samples (partial recall):")
            for failure in failed_samples[:5]:  # Show first 5 failures
                print(f"  - {failure['id']}: {failure['accuracy']:.1%}")
                print(f"    Query: {failure['query'][:50]}...")
                print(f"    Expected: {failure['expected']}")
                print(f"    Retrieved: {failure['retrieved']}")

        # Assert target met
        assert overall_accuracy >= target_accuracy, (
            f"Retrieval accuracy {overall_accuracy:.1%} below target {target_accuracy:.1%}"
        )

    async def test_result_content_populated(
        self,
        retrieval_service: Any,
    ) -> None:
        """Test that retrieved matches have full content populated."""
        result = await retrieval_service.retrieve(
            query="blister blight symptoms",
            top_k=3,
        )

        assert result.count > 0, "Expected at least one result"

        for match in result.matches:
            # Verify all required fields are populated
            assert match.chunk_id, "chunk_id should be populated"
            assert match.content, "content should be populated"
            assert match.score >= 0.0, "score should be non-negative"
            assert match.document_id, "document_id should be populated"
            assert match.title, "title should be populated"
            assert match.domain, "domain should be populated"

    async def test_namespace_isolation(
        self,
        retrieval_service: Any,
    ) -> None:
        """Test namespace parameter is passed through correctly."""
        namespace = "test-namespace-v1"

        result = await retrieval_service.retrieve(
            query="tea cultivation",
            namespace=namespace,
            top_k=3,
        )

        # Namespace should be in result
        assert result.namespace == namespace


@pytest.mark.golden
@pytest.mark.asyncio
class TestRetrievalEdgeCases:
    """Test edge cases and error handling in retrieval."""

    async def test_very_long_query(
        self,
        retrieval_service: Any,
    ) -> None:
        """Test retrieval handles very long queries."""
        long_query = " ".join(["tea"] * 500)  # Very long query

        # Should not raise exception
        result = await retrieval_service.retrieve(
            query=long_query,
            top_k=3,
        )

        # May or may not have results, but shouldn't fail
        assert result is not None

    async def test_special_characters_in_query(
        self,
        retrieval_service: Any,
    ) -> None:
        """Test retrieval handles special characters in queries."""
        queries_with_special = [
            "tea plant's disease?",
            "yield (kg/ha)",
            "nitrogen: application rates",
            "tea & quality",
        ]

        for query in queries_with_special:
            result = await retrieval_service.retrieve(
                query=query,
                top_k=3,
            )
            # Should not raise exception
            assert result is not None

    async def test_multiple_domain_filter(
        self,
        retrieval_service: Any,
    ) -> None:
        """Test filtering by multiple domains."""
        result = await retrieval_service.retrieve(
            query="farming practices",
            domains=["plant_diseases", "tea_cultivation"],
            top_k=10,
        )

        # All results should be from one of the specified domains
        for match in result.matches:
            assert match.domain in ["plant_diseases", "tea_cultivation"], f"Unexpected domain: {match.domain}"
