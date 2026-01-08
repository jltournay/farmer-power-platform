"""Fixtures for RAG retrieval golden sample tests.

This module provides fixtures for testing retrieval accuracy using
synthetic documents that simulate real tea farming knowledge content.

The test suite validates that:
1. Relevant documents are retrieved for queries
2. Confidence scores meet minimum thresholds
3. Domain filtering works correctly
4. Multi-domain queries return diverse results

Story 0.75.14: RAG Retrieval Service
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# Path to golden sample data
GOLDEN_RAG_PATH = Path(__file__).parent.parent
SAMPLES_PATH = GOLDEN_RAG_PATH / "retrieval" / "samples.json"
SEED_DOCS_PATH = GOLDEN_RAG_PATH / "seed_documents.json"


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
def retrieval_samples() -> dict[str, Any]:
    """Load retrieval golden samples.

    Returns:
        Dictionary with samples and metadata.
    """
    with SAMPLES_PATH.open() as f:
        return json.load(f)


@pytest.fixture
def mock_embedding_service() -> MagicMock:
    """Create a mock embedding service that returns consistent embeddings.

    The mock generates deterministic embeddings based on text content,
    allowing tests to verify retrieval logic without real embeddings.

    Returns:
        Mock EmbeddingService with embed_query method.
    """
    service = MagicMock()

    async def mock_embed_query(query: str, request_id: str | None = None) -> list[float]:
        """Generate deterministic mock embedding from query text."""
        # Simple hash-based embedding for deterministic results
        # In real tests, this would use actual embeddings
        query_hash = hash(query.lower())
        # Generate 1024-dimension vector with values between -1 and 1
        return [(query_hash % (i + 1)) / (i + 1) for i in range(1, 1025)]

    service.embed_query = AsyncMock(side_effect=mock_embed_query)
    return service


@pytest.fixture
def mock_vector_store(seed_documents: list[dict[str, Any]]) -> MagicMock:
    """Create a mock vector store pre-loaded with seed documents.

    This mock simulates Pinecone query responses based on text similarity
    heuristics rather than actual vector similarity.

    Args:
        seed_documents: The seed documents to index.

    Returns:
        Mock PineconeVectorStore with query method.
    """
    from ai_model.domain.vector_store import QueryMatch, QueryResult, VectorMetadata

    store = MagicMock()

    # Pre-compute document metadata for query responses
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
        """Simulate vector query using text heuristics.

        This is a simplified simulation for testing. Real tests would
        use actual embeddings and vector similarity.
        """
        # In a real implementation, query text would come from context
        # For mocking, we use a simple scoring based on embedding hash
        matches = []

        for doc_id, meta in doc_metadata.items():
            # Apply domain filter if present
            if filters and "domain" in filters:
                domains = filters["domain"].get("$in", [])
                if domains and meta["domain"] not in domains:
                    continue

            # Generate mock score based on embedding characteristics
            # This is deterministic but arbitrary for testing
            base_score = 0.6 + (hash(doc_id) % 40) / 100  # 0.6-0.99 range

            # Create chunk ID for this match
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

        # Sort by score descending and limit
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

    # Pre-compute chunks for each document
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
        """Return chunk by ID or None if not found."""
        return chunks.get(chunk_id)

    repo.get_by_id = AsyncMock(side_effect=mock_get_by_id)
    return repo


@pytest.fixture
def retrieval_service(
    mock_embedding_service: MagicMock,
    mock_vector_store: MagicMock,
    mock_chunk_repository: MagicMock,
) -> Any:
    """Create RetrievalService with mock dependencies.

    Args:
        mock_embedding_service: Mock embedding service.
        mock_vector_store: Mock Pinecone vector store.
        mock_chunk_repository: Mock chunk repository.

    Returns:
        Configured RetrievalService instance.
    """
    from ai_model.services.retrieval_service import RetrievalService

    return RetrievalService(
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,
        chunk_repository=mock_chunk_repository,
    )


def calculate_retrieval_accuracy(
    expected_docs: list[str],
    retrieved_docs: list[str],
) -> float:
    """Calculate retrieval accuracy as Recall@K.

    Args:
        expected_docs: List of expected document IDs.
        retrieved_docs: List of actually retrieved document IDs.

    Returns:
        Recall score (0-1) representing fraction of expected docs found.
    """
    if not expected_docs:
        return 1.0

    found = sum(1 for doc in expected_docs if doc in retrieved_docs)
    return found / len(expected_docs)
