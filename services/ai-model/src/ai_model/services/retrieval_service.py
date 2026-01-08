"""Retrieval service for RAG knowledge queries.

This service orchestrates the retrieval pipeline:
1. Embed query using EmbeddingService
2. Search vectors using PineconeVectorStore
3. Apply confidence threshold filtering
4. Fetch chunk content from MongoDB

Story 0.75.14: RAG Retrieval Service
"""

import structlog
from ai_model.domain.retrieval import RetrievalMatch, RetrievalQuery, RetrievalResult
from ai_model.infrastructure.pinecone_vector_store import (
    PineconeNotConfiguredError as VectorStoreNotConfiguredError,
    PineconeVectorStore,
)
from ai_model.infrastructure.repositories.rag_chunk_repository import RagChunkRepository
from ai_model.services.embedding_service import (
    EmbeddingService,
    PineconeNotConfiguredError as EmbeddingNotConfiguredError,
)

logger = structlog.get_logger(__name__)


class RetrievalServiceError(Exception):
    """Base exception for retrieval service errors."""

    pass


class RetrievalService:
    """Retrieval service for RAG knowledge queries.

    This service orchestrates the retrieval pipeline by coordinating:
    - EmbeddingService: Generate query embeddings
    - PineconeVectorStore: Perform similarity search
    - RagChunkRepository: Fetch chunk content from MongoDB

    Features:
    - Domain filtering via Pinecone metadata
    - Confidence threshold filtering (post-query)
    - Multi-domain queries
    - Graceful handling of Pinecone not configured

    All operations are async.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: PineconeVectorStore,
        chunk_repository: RagChunkRepository,
    ) -> None:
        """Initialize the retrieval service with dependencies.

        Args:
            embedding_service: Service for generating query embeddings.
            vector_store: Pinecone vector store for similarity search.
            chunk_repository: MongoDB repository for chunk content.
        """
        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._chunk_repository = chunk_repository

    async def retrieve(
        self,
        query: str,
        domains: list[str] | None = None,
        top_k: int = 5,
        confidence_threshold: float = 0.0,
        namespace: str | None = None,
    ) -> RetrievalResult:
        """Retrieve relevant knowledge chunks for a query.

        Orchestrates the full retrieval pipeline:
        1. Embed query using EmbeddingService (input_type=QUERY)
        2. Search Pinecone for similar vectors
        3. Filter results by confidence threshold
        4. Fetch full chunk content from MongoDB

        Args:
            query: Search query text.
            domains: List of knowledge domains to filter (empty = all domains).
            top_k: Maximum number of results to return.
            confidence_threshold: Minimum similarity score (0-1) to include.
            namespace: Pinecone namespace for version isolation.

        Returns:
            RetrievalResult with matches and metadata.

        Note:
            If Pinecone is not configured, returns empty results with a warning.
        """
        # Validate input
        if not query or not query.strip():
            logger.debug("Empty query provided, returning empty results")
            return RetrievalResult(
                matches=[],
                query=query or "",
                namespace=namespace,
                total_matches=0,
            )

        query = query.strip()
        domains = domains or []

        logger.info(
            "Starting retrieval",
            query_length=len(query),
            domains=domains,
            top_k=top_k,
            confidence_threshold=confidence_threshold,
            namespace=namespace,
        )

        # Step 1: Embed query
        try:
            embedding = await self._embedding_service.embed_query(query)
        except EmbeddingNotConfiguredError:
            logger.warning(
                "Pinecone not configured for embedding, returning empty results",
            )
            return RetrievalResult(
                matches=[],
                query=query,
                namespace=namespace,
                total_matches=0,
            )

        if not embedding:
            logger.warning("Embedding returned empty vector, returning empty results")
            return RetrievalResult(
                matches=[],
                query=query,
                namespace=namespace,
                total_matches=0,
            )

        # Step 2: Build filters and query Pinecone
        filters = None
        if domains:
            # Pinecone filter syntax for domain filtering
            filters = {"domain": {"$in": domains}}
            logger.debug("Applying domain filter", domains=domains)

        try:
            query_result = await self._vector_store.query(
                embedding=embedding,
                top_k=top_k,
                filters=filters,
                namespace=namespace,
            )
        except VectorStoreNotConfiguredError:
            logger.warning(
                "Pinecone not configured for vector store, returning empty results",
            )
            return RetrievalResult(
                matches=[],
                query=query,
                namespace=namespace,
                total_matches=0,
            )

        total_matches = len(query_result.matches)

        # Step 3: Apply confidence threshold filtering
        filtered_matches = [m for m in query_result.matches if m.score >= confidence_threshold]

        logger.debug(
            "Confidence filtering applied",
            total_matches=total_matches,
            filtered_matches=len(filtered_matches),
            confidence_threshold=confidence_threshold,
        )

        # Step 4: Fetch chunk content from MongoDB
        retrieval_matches: list[RetrievalMatch] = []
        for match in filtered_matches:
            if not match.metadata:
                logger.warning(
                    "Match missing metadata, skipping",
                    vector_id=match.id,
                )
                continue

            chunk_id = match.metadata.chunk_id
            chunk = await self._chunk_repository.get_by_id(chunk_id)

            if chunk is None:
                logger.warning(
                    "Chunk not found in MongoDB, skipping",
                    chunk_id=chunk_id,
                    vector_id=match.id,
                )
                continue

            # Build metadata dict for additional info
            additional_metadata: dict[str, str | list[str] | None] = {}
            if match.metadata.region:
                additional_metadata["region"] = match.metadata.region
            if match.metadata.season:
                additional_metadata["season"] = match.metadata.season
            if match.metadata.tags:
                additional_metadata["tags"] = match.metadata.tags

            retrieval_matches.append(
                RetrievalMatch(
                    chunk_id=chunk_id,
                    content=chunk.content,
                    score=match.score,
                    document_id=match.metadata.document_id,
                    title=match.metadata.title,
                    domain=match.metadata.domain,
                    metadata=additional_metadata,
                )
            )

        logger.info(
            "Retrieval completed",
            query_length=len(query),
            total_matches=total_matches,
            returned_matches=len(retrieval_matches),
            confidence_threshold=confidence_threshold,
            namespace=namespace,
        )

        return RetrievalResult(
            matches=retrieval_matches,
            query=query,
            namespace=namespace,
            total_matches=total_matches,
        )

    async def retrieve_from_query(self, retrieval_query: RetrievalQuery) -> RetrievalResult:
        """Retrieve using a RetrievalQuery object.

        Convenience method that unpacks a RetrievalQuery into retrieve() parameters.

        Args:
            retrieval_query: Query parameters as a Pydantic model.

        Returns:
            RetrievalResult with matches and metadata.
        """
        return await self.retrieve(
            query=retrieval_query.query,
            domains=retrieval_query.domains,
            top_k=retrieval_query.top_k,
            confidence_threshold=retrieval_query.confidence_threshold,
            namespace=retrieval_query.namespace,
        )
