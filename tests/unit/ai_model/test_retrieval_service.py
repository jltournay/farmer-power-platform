"""Unit tests for RetrievalService.

Story 0.75.14: RAG Retrieval Service

Tests cover:
1. Orchestration flow (embed -> query -> fetch)
2. Domain filtering behavior
3. Confidence threshold filtering
4. Multi-domain queries
5. Error handling (Pinecone not configured, chunk not found)
6. Empty results handling
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from ai_model.domain.rag_document import RagChunk
from ai_model.domain.retrieval import RetrievalQuery, RetrievalResult
from ai_model.domain.vector_store import QueryMatch, QueryResult, VectorMetadata
from ai_model.infrastructure.pinecone_vector_store import PineconeNotConfiguredError as VectorStoreNotConfiguredError
from ai_model.services.embedding_service import PineconeNotConfiguredError as EmbeddingNotConfiguredError
from ai_model.services.retrieval_service import RetrievalService


@pytest.fixture
def mock_embedding_service() -> MagicMock:
    """Create a mock embedding service."""
    service = MagicMock()
    service.embed_query = AsyncMock(return_value=[0.1] * 1024)
    return service


@pytest.fixture
def mock_vector_store() -> MagicMock:
    """Create a mock Pinecone vector store."""
    store = MagicMock()
    store.query = AsyncMock(
        return_value=QueryResult(
            matches=[
                QueryMatch(
                    id="doc-1-0",
                    score=0.85,
                    metadata=VectorMetadata(
                        document_id="doc-1",
                        chunk_id="doc-1-v1-chunk-0",
                        chunk_index=0,
                        domain="plant_diseases",
                        title="Test Document 1",
                        region="Kenya",
                        season=None,
                        tags=["test", "diseases"],
                    ),
                ),
                QueryMatch(
                    id="doc-2-0",
                    score=0.72,
                    metadata=VectorMetadata(
                        document_id="doc-2",
                        chunk_id="doc-2-v1-chunk-0",
                        chunk_index=0,
                        domain="tea_cultivation",
                        title="Test Document 2",
                        region="Rwanda",
                        season="dry_season",
                        tags=["cultivation"],
                    ),
                ),
            ],
            namespace="test-namespace",
        )
    )
    return store


@pytest.fixture
def mock_chunk_repository() -> MagicMock:
    """Create a mock chunk repository."""
    repo = MagicMock()

    async def get_by_id(chunk_id: str) -> RagChunk | None:
        chunks = {
            "doc-1-v1-chunk-0": RagChunk(
                chunk_id="doc-1-v1-chunk-0",
                document_id="doc-1",
                document_version=1,
                chunk_index=0,
                content="This is test content about plant diseases.",
                section_title="Test Section 1",
                word_count=8,
                char_count=46,
                created_at=datetime.now(UTC),
            ),
            "doc-2-v1-chunk-0": RagChunk(
                chunk_id="doc-2-v1-chunk-0",
                document_id="doc-2",
                document_version=1,
                chunk_index=0,
                content="This is test content about tea cultivation.",
                section_title="Test Section 2",
                word_count=8,
                char_count=45,
                created_at=datetime.now(UTC),
            ),
        }
        return chunks.get(chunk_id)

    repo.get_by_id = AsyncMock(side_effect=get_by_id)
    return repo


@pytest.fixture
def retrieval_service(
    mock_embedding_service: MagicMock,
    mock_vector_store: MagicMock,
    mock_chunk_repository: MagicMock,
) -> RetrievalService:
    """Create RetrievalService with mock dependencies."""
    return RetrievalService(
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,
        chunk_repository=mock_chunk_repository,
    )


@pytest.mark.asyncio
class TestRetrievalServiceOrchestration:
    """Test the retrieval orchestration flow."""

    async def test_basic_retrieval_flow(
        self,
        retrieval_service: RetrievalService,
        mock_embedding_service: MagicMock,
        mock_vector_store: MagicMock,
        mock_chunk_repository: MagicMock,
    ) -> None:
        """Test complete retrieval flow: embed -> query -> fetch."""
        result = await retrieval_service.retrieve(query="test query")

        # Verify embedding was called
        mock_embedding_service.embed_query.assert_called_once_with("test query")

        # Verify vector store query was called
        mock_vector_store.query.assert_called_once()
        call_kwargs = mock_vector_store.query.call_args.kwargs
        assert call_kwargs["embedding"] == [0.1] * 1024
        assert call_kwargs["top_k"] == 5

        # Verify chunk repository was called for each match
        assert mock_chunk_repository.get_by_id.call_count == 2

        # Verify result structure
        assert isinstance(result, RetrievalResult)
        assert result.query == "test query"
        assert result.count == 2
        assert result.total_matches == 2

    async def test_retrieval_preserves_query(
        self,
        retrieval_service: RetrievalService,
    ) -> None:
        """Test that the original query is preserved in results."""
        query = "What are the symptoms of blister blight?"
        result = await retrieval_service.retrieve(query=query)

        assert result.query == query

    async def test_retrieval_with_custom_top_k(
        self,
        retrieval_service: RetrievalService,
        mock_vector_store: MagicMock,
    ) -> None:
        """Test retrieval with custom top_k parameter."""
        await retrieval_service.retrieve(query="test", top_k=10)

        call_kwargs = mock_vector_store.query.call_args.kwargs
        assert call_kwargs["top_k"] == 10

    async def test_retrieval_with_namespace(
        self,
        retrieval_service: RetrievalService,
        mock_vector_store: MagicMock,
    ) -> None:
        """Test retrieval with namespace parameter."""
        await retrieval_service.retrieve(query="test", namespace="my-namespace")

        call_kwargs = mock_vector_store.query.call_args.kwargs
        assert call_kwargs["namespace"] == "my-namespace"


@pytest.mark.asyncio
class TestDomainFiltering:
    """Test domain filtering behavior."""

    async def test_single_domain_filter(
        self,
        retrieval_service: RetrievalService,
        mock_vector_store: MagicMock,
    ) -> None:
        """Test filtering by single domain."""
        await retrieval_service.retrieve(
            query="test",
            domains=["plant_diseases"],
        )

        call_kwargs = mock_vector_store.query.call_args.kwargs
        assert call_kwargs["filters"] == {"domain": {"$in": ["plant_diseases"]}}

    async def test_multi_domain_filter(
        self,
        retrieval_service: RetrievalService,
        mock_vector_store: MagicMock,
    ) -> None:
        """Test filtering by multiple domains."""
        await retrieval_service.retrieve(
            query="test",
            domains=["plant_diseases", "tea_cultivation"],
        )

        call_kwargs = mock_vector_store.query.call_args.kwargs
        assert call_kwargs["filters"] == {"domain": {"$in": ["plant_diseases", "tea_cultivation"]}}

    async def test_no_domain_filter_queries_all(
        self,
        retrieval_service: RetrievalService,
        mock_vector_store: MagicMock,
    ) -> None:
        """Test that no domain filter queries all domains."""
        await retrieval_service.retrieve(query="test", domains=[])

        call_kwargs = mock_vector_store.query.call_args.kwargs
        assert call_kwargs["filters"] is None

    async def test_none_domains_queries_all(
        self,
        retrieval_service: RetrievalService,
        mock_vector_store: MagicMock,
    ) -> None:
        """Test that None domains queries all domains."""
        await retrieval_service.retrieve(query="test", domains=None)

        call_kwargs = mock_vector_store.query.call_args.kwargs
        assert call_kwargs["filters"] is None


@pytest.mark.asyncio
class TestConfidenceThreshold:
    """Test confidence threshold filtering."""

    async def test_default_threshold_no_filtering(
        self,
        retrieval_service: RetrievalService,
    ) -> None:
        """Test default threshold (0.0) doesn't filter results."""
        result = await retrieval_service.retrieve(query="test")

        # Both matches should be returned (scores 0.85 and 0.72)
        assert result.count == 2

    async def test_high_threshold_filters_results(
        self,
        retrieval_service: RetrievalService,
    ) -> None:
        """Test high threshold filters low-score results."""
        result = await retrieval_service.retrieve(
            query="test",
            confidence_threshold=0.80,
        )

        # Only first match (score 0.85) should pass threshold
        assert result.count == 1
        assert result.matches[0].score == 0.85

    async def test_very_high_threshold_returns_empty(
        self,
        retrieval_service: RetrievalService,
    ) -> None:
        """Test very high threshold returns empty results."""
        result = await retrieval_service.retrieve(
            query="test",
            confidence_threshold=0.95,
        )

        assert result.count == 0
        assert result.total_matches == 2  # Original matches before filtering

    async def test_all_scores_above_threshold(
        self,
        retrieval_service: RetrievalService,
    ) -> None:
        """Test when all results are above threshold."""
        result = await retrieval_service.retrieve(
            query="test",
            confidence_threshold=0.50,
        )

        # Both matches should pass (0.85 > 0.5 and 0.72 > 0.5)
        assert result.count == 2


@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling scenarios."""

    async def test_embedding_not_configured_returns_empty(
        self,
        mock_embedding_service: MagicMock,
        mock_vector_store: MagicMock,
        mock_chunk_repository: MagicMock,
    ) -> None:
        """Test handling when Pinecone is not configured for embedding."""
        mock_embedding_service.embed_query = AsyncMock(side_effect=EmbeddingNotConfiguredError("Not configured"))

        service = RetrievalService(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            chunk_repository=mock_chunk_repository,
        )

        result = await service.retrieve(query="test")

        assert result.count == 0
        assert result.matches == []

    async def test_vector_store_not_configured_returns_empty(
        self,
        mock_embedding_service: MagicMock,
        mock_vector_store: MagicMock,
        mock_chunk_repository: MagicMock,
    ) -> None:
        """Test handling when Pinecone is not configured for vector store."""
        mock_vector_store.query = AsyncMock(side_effect=VectorStoreNotConfiguredError("Not configured"))

        service = RetrievalService(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            chunk_repository=mock_chunk_repository,
        )

        result = await service.retrieve(query="test")

        assert result.count == 0
        assert result.matches == []

    async def test_chunk_not_found_skipped_gracefully(
        self,
        mock_embedding_service: MagicMock,
        mock_vector_store: MagicMock,
    ) -> None:
        """Test handling when chunk is not found in MongoDB."""
        # Repository returns None for all chunks
        mock_chunk_repository = MagicMock()
        mock_chunk_repository.get_by_id = AsyncMock(return_value=None)

        service = RetrievalService(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            chunk_repository=mock_chunk_repository,
        )

        result = await service.retrieve(query="test")

        # Results should be empty (chunks not found)
        assert result.count == 0
        assert result.total_matches == 2  # Matches existed but chunks not found

    async def test_match_without_metadata_skipped(
        self,
        mock_embedding_service: MagicMock,
        mock_chunk_repository: MagicMock,
    ) -> None:
        """Test handling of matches without metadata."""
        mock_vector_store = MagicMock()
        mock_vector_store.query = AsyncMock(
            return_value=QueryResult(
                matches=[
                    QueryMatch(
                        id="doc-1-0",
                        score=0.85,
                        metadata=None,  # No metadata
                    ),
                ],
                namespace="test",
            )
        )

        service = RetrievalService(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            chunk_repository=mock_chunk_repository,
        )

        result = await service.retrieve(query="test")

        # Match without metadata should be skipped
        assert result.count == 0


@pytest.mark.asyncio
class TestEmptyResults:
    """Test empty results handling."""

    async def test_empty_query_returns_empty(
        self,
        retrieval_service: RetrievalService,
        mock_embedding_service: MagicMock,
    ) -> None:
        """Test empty query returns empty results."""
        result = await retrieval_service.retrieve(query="")

        assert result.count == 0
        assert result.matches == []
        mock_embedding_service.embed_query.assert_not_called()

    async def test_whitespace_query_returns_empty(
        self,
        retrieval_service: RetrievalService,
        mock_embedding_service: MagicMock,
    ) -> None:
        """Test whitespace-only query returns empty results."""
        result = await retrieval_service.retrieve(query="   ")

        assert result.count == 0
        mock_embedding_service.embed_query.assert_not_called()

    async def test_empty_embedding_returns_empty(
        self,
        mock_embedding_service: MagicMock,
        mock_vector_store: MagicMock,
        mock_chunk_repository: MagicMock,
    ) -> None:
        """Test empty embedding returns empty results."""
        mock_embedding_service.embed_query = AsyncMock(return_value=[])

        service = RetrievalService(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            chunk_repository=mock_chunk_repository,
        )

        result = await service.retrieve(query="test")

        assert result.count == 0
        mock_vector_store.query.assert_not_called()

    async def test_no_vector_matches_returns_empty(
        self,
        mock_embedding_service: MagicMock,
        mock_chunk_repository: MagicMock,
    ) -> None:
        """Test handling when no vectors match."""
        mock_vector_store = MagicMock()
        mock_vector_store.query = AsyncMock(return_value=QueryResult(matches=[], namespace="test"))

        service = RetrievalService(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            chunk_repository=mock_chunk_repository,
        )

        result = await service.retrieve(query="test")

        assert result.count == 0
        assert result.total_matches == 0


@pytest.mark.asyncio
class TestRetrievalQuery:
    """Test RetrievalQuery convenience method."""

    async def test_retrieve_from_query(
        self,
        retrieval_service: RetrievalService,
    ) -> None:
        """Test retrieval using RetrievalQuery object."""
        query = RetrievalQuery(
            query="test query",
            domains=["plant_diseases"],
            top_k=3,
            confidence_threshold=0.5,
            namespace="my-namespace",
        )

        result = await retrieval_service.retrieve_from_query(query)

        assert result.query == "test query"
        assert isinstance(result, RetrievalResult)


@pytest.mark.asyncio
class TestResultContent:
    """Test result content structure."""

    async def test_match_content_populated(
        self,
        retrieval_service: RetrievalService,
    ) -> None:
        """Test that match content is properly populated."""
        result = await retrieval_service.retrieve(query="test")

        match = result.matches[0]
        assert match.chunk_id == "doc-1-v1-chunk-0"
        assert match.content == "This is test content about plant diseases."
        assert match.score == 0.85
        assert match.document_id == "doc-1"
        assert match.title == "Test Document 1"
        assert match.domain == "plant_diseases"

    async def test_match_metadata_populated(
        self,
        retrieval_service: RetrievalService,
    ) -> None:
        """Test that match metadata is properly populated."""
        result = await retrieval_service.retrieve(query="test")

        # First match has region and tags
        match1 = result.matches[0]
        assert match1.metadata.get("region") == "Kenya"
        assert match1.metadata.get("tags") == ["test", "diseases"]
        assert "season" not in match1.metadata  # None values excluded

        # Second match has season
        match2 = result.matches[1]
        assert match2.metadata.get("region") == "Rwanda"
        assert match2.metadata.get("season") == "dry_season"
