"""Fixtures for RAG ranking golden sample tests.

This module provides fixtures for testing ranking accuracy using
the same seed documents as retrieval tests but with a separate namespace.

The test suite validates that:
1. Re-ranking improves result ordering vs raw retrieval
2. Domain boosting affects rankings correctly
3. Deduplication removes near-duplicate results
4. Graceful degradation works when reranker unavailable

Story 0.75.15: RAG Ranking Logic
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# Path to golden sample data
GOLDEN_RAG_PATH = Path(__file__).parent.parent
RANKING_SAMPLES_PATH = GOLDEN_RAG_PATH / "ranking" / "samples.json"
SEED_DOCS_PATH = GOLDEN_RAG_PATH / "seed_documents.json"

# Ranking namespace - separate from retrieval tests
RANKING_NAMESPACE = "golden-ranking"


@pytest.fixture
def seed_documents() -> list[dict[str, Any]]:
    """Load seed documents for testing.

    Returns:
        List of seed document dictionaries.
    """
    with SEED_DOCS_PATH.open() as f:
        data = json.load(f)
    return data["documents"]


@pytest.fixture
def ranking_samples() -> dict[str, Any]:
    """Load ranking golden samples.

    Returns:
        Dictionary with samples and metadata.
    """
    with RANKING_SAMPLES_PATH.open() as f:
        return json.load(f)


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings for ranking service.

    Returns:
        Mock Settings object with Pinecone enabled.
    """
    settings = MagicMock()
    settings.pinecone_enabled = True
    settings.pinecone_api_key = MagicMock()
    settings.pinecone_api_key.get_secret_value.return_value = "test-api-key"
    settings.pinecone_rerank_model = "pinecone-rerank-v0"
    return settings


@pytest.fixture
def mock_embedding_service() -> MagicMock:
    """Create a mock embedding service that returns consistent embeddings.

    Returns:
        Mock EmbeddingService with embed_query method.
    """
    service = MagicMock()

    async def mock_embed_query(query: str, request_id: str | None = None) -> list[float]:
        """Generate deterministic mock embedding from query text."""
        query_hash = hash(query.lower())
        return [(query_hash % (i + 1)) / (i + 1) for i in range(1, 1025)]

    service.embed_query = AsyncMock(side_effect=mock_embed_query)
    return service


@pytest.fixture
def mock_vector_store(seed_documents: list[dict[str, Any]]) -> MagicMock:
    """Create a mock vector store pre-loaded with seed documents.

    Args:
        seed_documents: The seed documents to index.

    Returns:
        Mock PineconeVectorStore with query method.
    """
    from ai_model.domain.vector_store import QueryMatch, QueryResult, VectorMetadata

    store = MagicMock()

    doc_metadata: dict[str, dict[str, Any]] = {}
    for doc in seed_documents:
        doc_id = doc["document_id"]
        doc_metadata[doc_id] = {
            "document_id": doc_id,
            "title": doc["title"],
            "domain": doc["domain"],
            "content": doc["content"].lower(),
            "region": doc["metadata"].get("region"),
            "season": doc["metadata"].get("season"),
            "tags": doc["metadata"].get("tags", []),
        }

    async def mock_query(
        embedding: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        namespace: str | None = None,
    ) -> QueryResult:
        """Simulate vector query using text heuristics."""
        matches = []

        for doc_id, meta in doc_metadata.items():
            if filters and "domain" in filters:
                domains = filters["domain"].get("$in", [])
                if domains and meta["domain"] not in domains:
                    continue

            base_score = 0.6 + (hash(doc_id) % 40) / 100
            chunk_id = f"{doc_id}-v1-chunk-0"

            matches.append(
                QueryMatch(
                    id=f"{doc_id}-0",
                    score=min(base_score, 0.99),
                    metadata=VectorMetadata(
                        document_id=doc_id,
                        chunk_id=chunk_id,
                        chunk_index=0,
                        domain=meta["domain"],
                        title=meta["title"],
                        region=meta["region"],
                        season=meta["season"],
                        tags=meta["tags"],
                    ),
                )
            )

        matches.sort(key=lambda m: m.score, reverse=True)
        matches = matches[:top_k]

        return QueryResult(matches=matches, namespace=namespace)

    store.query = AsyncMock(side_effect=mock_query)
    return store


@pytest.fixture
def mock_chunk_repository(seed_documents: list[dict[str, Any]]) -> MagicMock:
    """Create a mock chunk repository with seed document chunks.

    Args:
        seed_documents: The seed documents to use for chunk content.

    Returns:
        Mock RagChunkRepository with get_by_id method.
    """
    from ai_model.domain.rag_document import RagChunk

    repo = MagicMock()

    chunks: dict[str, RagChunk] = {}
    for doc in seed_documents:
        doc_id = doc["document_id"]
        chunk_id = f"{doc_id}-v1-chunk-0"

        chunks[chunk_id] = RagChunk(
            chunk_id=chunk_id,
            document_id=doc_id,
            document_version=1,
            chunk_index=0,
            content=doc["content"],
            section_title=doc["title"],
            word_count=len(doc["content"].split()),
            char_count=len(doc["content"]),
            created_at=datetime.now(UTC),
            pinecone_id=f"{doc_id}-0",
        )

    async def mock_get_by_id(chunk_id: str) -> RagChunk | None:
        return chunks.get(chunk_id)

    repo.get_by_id = AsyncMock(side_effect=mock_get_by_id)
    return repo


@pytest.fixture
def mock_retrieval_service(
    mock_embedding_service: MagicMock,
    mock_vector_store: MagicMock,
    mock_chunk_repository: MagicMock,
) -> Any:
    """Create RetrievalService with mock dependencies.

    Returns:
        Configured RetrievalService instance.
    """
    from ai_model.services.retrieval_service import RetrievalService

    return RetrievalService(
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,
        chunk_repository=mock_chunk_repository,
    )


@pytest.fixture
def mock_pinecone_client(seed_documents: list[dict[str, Any]]) -> MagicMock:
    """Create a mock Pinecone client with reranker.

    The mock reranker simulates relevance scoring based on text overlap
    between query and document content.

    Args:
        seed_documents: The seed documents for relevance calculation.

    Returns:
        Mock Pinecone client with inference.rerank method.
    """
    client = MagicMock()

    # Build content lookup for reranking simulation
    doc_content: dict[str, str] = {}
    for doc in seed_documents:
        doc_id = doc["document_id"]
        doc_content[doc_id] = doc["content"].lower()

    def mock_rerank(
        model: str,
        query: str,
        documents: list[dict[str, str]],
        top_n: int = 5,
        return_documents: bool = False,
    ) -> MagicMock:
        """Simulate reranking based on query-document text overlap."""
        query_words = set(query.lower().split())
        results = []

        for idx, doc in enumerate(documents):
            doc_text = doc.get("text", "").lower()
            doc_words = set(doc_text.split())

            # Calculate overlap-based relevance score
            overlap = len(query_words & doc_words)
            max_possible = len(query_words)
            base_score = overlap / max_possible if max_possible > 0 else 0.0

            # Add document-specific bonus for more realistic scores
            doc_id = doc.get("id", "").replace("-v1-chunk-0", "")
            if doc_id in doc_content:
                # Boost if query keywords appear in document title keywords
                doc_keywords = doc_id.replace("-", " ").split()
                keyword_overlap = len(query_words & set(doc_keywords))
                base_score += keyword_overlap * 0.15

            # Clamp to valid range
            score = min(max(base_score, 0.1), 0.99)

            results.append(
                {
                    "index": idx,
                    "score": score,
                    "document": doc if return_documents else None,
                }
            )

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)

        result = MagicMock()
        result.data = results[:top_n]
        return result

    client.inference.rerank = mock_rerank
    return client


@pytest.fixture
def ranking_service_with_mock_reranker(
    mock_retrieval_service: Any,
    mock_settings: MagicMock,
    mock_pinecone_client: MagicMock,
) -> Any:
    """Create RankingService with mock reranker.

    Returns:
        Configured RankingService with mocked Pinecone client.
    """
    from ai_model.services.ranking_service import RankingService

    service = RankingService(
        retrieval_service=mock_retrieval_service,
        settings=mock_settings,
    )
    # Inject mock client
    service._client = mock_pinecone_client
    return service


@pytest.fixture
def ranking_service_no_reranker(
    mock_retrieval_service: Any,
    mock_settings: MagicMock,
) -> Any:
    """Create RankingService without reranker (for graceful degradation tests).

    Returns:
        RankingService that will fall back to retrieval scores.
    """
    from ai_model.services.ranking_service import RankingService

    # Disable Pinecone
    mock_settings.pinecone_enabled = False

    return RankingService(
        retrieval_service=mock_retrieval_service,
        settings=mock_settings,
    )


def calculate_ranking_accuracy(
    expected_top: str | None,
    expected_in_top_n: list[str],
    actual_results: list[str],
) -> dict[str, float]:
    """Calculate ranking accuracy metrics.

    Args:
        expected_top: Expected top-1 result (None = any is acceptable).
        expected_in_top_n: Documents that should appear in top N results.
        actual_results: List of document IDs in ranked order.

    Returns:
        Dictionary with accuracy metrics:
        - top1_correct: 1.0 if top result matches expected, else 0.0
        - recall_at_n: Fraction of expected docs found in results
    """
    metrics = {
        "top1_correct": 0.0,
        "recall_at_n": 0.0,
    }

    if not actual_results:
        return metrics

    # Top-1 accuracy
    if expected_top is None or actual_results[0] == expected_top:
        metrics["top1_correct"] = 1.0

    # Recall@N
    if expected_in_top_n:
        found = sum(1 for doc in expected_in_top_n if doc in actual_results)
        metrics["recall_at_n"] = found / len(expected_in_top_n)
    else:
        metrics["recall_at_n"] = 1.0

    return metrics
