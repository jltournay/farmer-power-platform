"""Pinecone Vector Store for RAG vector operations.

This module provides the PineconeVectorStore class for CRUD operations on
vectors stored in Pinecone. It handles:
- Upsert with automatic batching (100 vectors per batch)
- Similarity queries with metadata filtering
- Delete by IDs and delete all in namespace
- Index statistics

All operations are async (using run_in_executor for sync Pinecone SDK).

Story 0.75.13: RAG Vector Storage (Pinecone Repository)
"""

import asyncio
import logging
from typing import Any

import structlog
from ai_model.config import Settings
from ai_model.domain.vector_store import (
    VECTOR_DIMENSIONS,
    IndexStats,
    NamespaceStats,
    QueryMatch,
    QueryResult,
    UpsertResult,
    VectorMetadata,
    VectorUpsertRequest,
)
from pinecone import Pinecone
from pinecone.exceptions import NotFoundException, PineconeException
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)


# Batch limits from Pinecone documentation
UPSERT_BATCH_SIZE = 100  # Max vectors per upsert request
DELETE_BATCH_SIZE = 1000  # Max IDs per delete request

# Retryable exceptions (transient errors)
RETRYABLE_EXCEPTIONS = (ConnectionError, TimeoutError, OSError, PineconeException)


class PineconeVectorStoreError(Exception):
    """Base exception for vector store errors."""

    pass


class PineconeNotConfiguredError(PineconeVectorStoreError):
    """Raised when Pinecone API key is not configured."""

    pass


class PineconeIndexNotFoundError(PineconeVectorStoreError):
    """Raised when the configured Pinecone index does not exist."""

    pass


class PineconeVectorStore:
    """Pinecone vector store for RAG operations.

    This class provides async CRUD operations for vectors stored in Pinecone.
    It reuses the Pinecone client pattern from EmbeddingService with:
    - Singleton client (lazy initialization)
    - Lazy index reference with validation
    - Async via run_in_executor (SDK is synchronous)
    - Retry logic with tenacity for transient errors

    Namespace Strategy:
    - Namespaces isolate document versions: knowledge-v{version}
    - Staged: knowledge-v{version}-staged
    - Archived: knowledge-v{version}-archived
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize the vector store.

        Args:
            settings: Service configuration with Pinecone credentials.
        """
        self._settings = settings
        self._client: Pinecone | None = None
        # Note: Using Any because Pinecone SDK doesn't export Index type directly
        self._index: Any | None = None
        self._index_validated: bool = False

    def _get_client(self) -> Pinecone:
        """Get or create the Pinecone client (singleton).

        Returns:
            Pinecone client instance.

        Raises:
            PineconeNotConfiguredError: If API key is not configured.
        """
        if not self._settings.pinecone_enabled:
            raise PineconeNotConfiguredError(
                "Pinecone API key is not configured. Set PINECONE_API_KEY environment variable."
            )

        if self._client is None:
            self._client = Pinecone(
                api_key=self._settings.pinecone_api_key.get_secret_value(),  # type: ignore[union-attr]
            )

        return self._client

    def _get_index(self) -> Any:
        """Get or create the index reference (lazy initialization).

        Returns:
            Pinecone Index instance.

        Raises:
            PineconeNotConfiguredError: If Pinecone is not configured.
        """
        if self._index is None:
            client = self._get_client()
            self._index = client.Index(self._settings.pinecone_index_name)

        return self._index

    async def _validate_index_exists(self) -> None:
        """Validate that the configured index exists (called once on first operation).

        Raises:
            PineconeIndexNotFoundError: If the index does not exist.
        """
        if self._index_validated:
            return

        loop = asyncio.get_running_loop()
        client = self._get_client()

        try:
            # List indexes to check if our index exists
            indexes = await loop.run_in_executor(None, client.list_indexes)
            index_names = [idx.name for idx in indexes]

            if self._settings.pinecone_index_name not in index_names:
                raise PineconeIndexNotFoundError(
                    f"Pinecone index '{self._settings.pinecone_index_name}' does not exist. "
                    f"Available indexes: {index_names}"
                )

            self._index_validated = True
            logger.info(
                "Pinecone index validated",
                index_name=self._settings.pinecone_index_name,
            )
        except NotFoundException as e:
            raise PineconeIndexNotFoundError(f"Pinecone index '{self._settings.pinecone_index_name}' not found: {e}")

    async def upsert(
        self,
        vectors: list[VectorUpsertRequest],
        namespace: str | None = None,
    ) -> UpsertResult:
        """Upsert vectors to Pinecone with automatic batching.

        Args:
            vectors: List of vectors to upsert.
            namespace: Target namespace for version isolation.

        Returns:
            UpsertResult with total upserted count.

        Raises:
            PineconeNotConfiguredError: If Pinecone is not configured.
            PineconeIndexNotFoundError: If the index does not exist.
            PineconeException: On Pinecone API errors after retries.
        """
        if not vectors:
            return UpsertResult(upserted_count=0)

        await self._validate_index_exists()

        total_upserted = 0
        batches = [vectors[i : i + UPSERT_BATCH_SIZE] for i in range(0, len(vectors), UPSERT_BATCH_SIZE)]

        logger.info(
            "Starting vector upsert",
            total_vectors=len(vectors),
            batch_count=len(batches),
            namespace=namespace,
        )

        for batch_idx, batch in enumerate(batches):
            try:
                result = await self._upsert_batch(batch, namespace)
                total_upserted += result
                logger.debug(
                    "Batch upserted",
                    batch_index=batch_idx,
                    batch_size=len(batch),
                    upserted=result,
                )
            except Exception as e:
                logger.error(
                    "Batch upsert failed",
                    batch_index=batch_idx,
                    error=str(e),
                )
                raise

        logger.info(
            "Vector upsert completed",
            total_upserted=total_upserted,
            namespace=namespace,
        )

        return UpsertResult(upserted_count=total_upserted)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _upsert_batch(
        self,
        batch: list[VectorUpsertRequest],
        namespace: str | None,
    ) -> int:
        """Upsert a single batch with retry logic.

        Args:
            batch: List of vectors (max 100).
            namespace: Target namespace.

        Returns:
            Number of vectors upserted.
        """
        index = self._get_index()
        loop = asyncio.get_running_loop()

        # Format vectors for Pinecone
        pinecone_vectors = [
            {
                "id": v.id,
                "values": v.values,
                "metadata": v.metadata.model_dump() if v.metadata else {},
            }
            for v in batch
        ]

        result = await loop.run_in_executor(
            None,
            lambda: index.upsert(vectors=pinecone_vectors, namespace=namespace),
        )

        return result.upserted_count

    async def query(
        self,
        embedding: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        namespace: str | None = None,
    ) -> QueryResult:
        """Query vectors by similarity.

        Args:
            embedding: Query embedding vector (1024 dimensions).
            top_k: Number of results to return.
            filters: Pinecone filter syntax (e.g., {"domain": {"$in": ["plant_diseases"]}}).
            namespace: Namespace to query.

        Returns:
            QueryResult with matches ordered by similarity.

        Raises:
            PineconeNotConfiguredError: If Pinecone is not configured.
            PineconeIndexNotFoundError: If the index does not exist.
            PineconeException: On Pinecone API errors after retries.
        """
        await self._validate_index_exists()

        logger.debug(
            "Querying vectors",
            top_k=top_k,
            has_filters=filters is not None,
            namespace=namespace,
        )

        result = await self._query_with_retry(embedding, top_k, filters, namespace)

        logger.debug(
            "Query completed",
            match_count=len(result.matches),
            namespace=namespace,
        )

        return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _query_with_retry(
        self,
        embedding: list[float],
        top_k: int,
        filters: dict[str, Any] | None,
        namespace: str | None,
    ) -> QueryResult:
        """Execute query with retry logic.

        Args:
            embedding: Query embedding vector.
            top_k: Number of results.
            filters: Pinecone filter dict.
            namespace: Namespace to query.

        Returns:
            QueryResult with matches.
        """
        index = self._get_index()
        loop = asyncio.get_running_loop()

        # Build query kwargs
        query_kwargs: dict[str, Any] = {
            "vector": embedding,
            "top_k": top_k,
            "include_metadata": True,
        }
        if namespace:
            query_kwargs["namespace"] = namespace
        if filters:
            query_kwargs["filter"] = filters

        result = await loop.run_in_executor(
            None,
            lambda: index.query(**query_kwargs),
        )

        # Parse matches
        matches = []
        for match in result.matches:
            metadata = None
            if match.metadata:
                # Parse metadata into VectorMetadata
                try:
                    metadata = VectorMetadata.model_validate(match.metadata)
                except Exception:
                    # If metadata doesn't match schema, skip it
                    logger.warning(
                        "Failed to parse vector metadata",
                        vector_id=match.id,
                    )

            matches.append(
                QueryMatch(
                    id=match.id,
                    score=match.score,
                    metadata=metadata,
                )
            )

        return QueryResult(matches=matches, namespace=namespace)

    async def delete(
        self,
        ids: list[str],
        namespace: str | None = None,
    ) -> int:
        """Delete vectors by IDs with automatic batching.

        Args:
            ids: List of vector IDs to delete.
            namespace: Namespace containing the vectors.

        Returns:
            Number of vectors deleted (estimated - Pinecone doesn't return actual count).

        Raises:
            PineconeNotConfiguredError: If Pinecone is not configured.
            PineconeIndexNotFoundError: If the index does not exist.
            PineconeException: On Pinecone API errors after retries.
        """
        if not ids:
            return 0

        await self._validate_index_exists()

        batches = [ids[i : i + DELETE_BATCH_SIZE] for i in range(0, len(ids), DELETE_BATCH_SIZE)]

        logger.info(
            "Starting vector delete",
            total_ids=len(ids),
            batch_count=len(batches),
            namespace=namespace,
        )

        for batch_idx, batch in enumerate(batches):
            try:
                await self._delete_batch(batch, namespace)
                logger.debug(
                    "Batch deleted",
                    batch_index=batch_idx,
                    batch_size=len(batch),
                )
            except Exception as e:
                logger.error(
                    "Batch delete failed",
                    batch_index=batch_idx,
                    error=str(e),
                )
                raise

        logger.info(
            "Vector delete completed",
            deleted_count=len(ids),
            namespace=namespace,
        )

        return len(ids)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _delete_batch(
        self,
        ids: list[str],
        namespace: str | None,
    ) -> None:
        """Delete a single batch with retry logic.

        Args:
            ids: List of vector IDs (max 1000).
            namespace: Namespace containing the vectors.
        """
        index = self._get_index()
        loop = asyncio.get_running_loop()

        # Build delete kwargs
        delete_kwargs: dict[str, Any] = {"ids": ids}
        if namespace:
            delete_kwargs["namespace"] = namespace

        await loop.run_in_executor(
            None,
            lambda: index.delete(**delete_kwargs),
        )

    async def delete_all(self, namespace: str) -> None:
        """Delete all vectors in a namespace.

        Args:
            namespace: Namespace to clear (required - prevents accidental full delete).

        Raises:
            PineconeNotConfiguredError: If Pinecone is not configured.
            PineconeIndexNotFoundError: If the index does not exist.
            PineconeException: On Pinecone API errors after retries.
            ValueError: If namespace is empty.
        """
        if not namespace:
            raise ValueError("Namespace is required for delete_all to prevent accidental full index deletion")

        await self._validate_index_exists()

        logger.info(
            "Deleting all vectors in namespace",
            namespace=namespace,
        )

        await self._delete_all_with_retry(namespace)

        logger.info(
            "Namespace cleared",
            namespace=namespace,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _delete_all_with_retry(self, namespace: str) -> None:
        """Delete all vectors in namespace with retry logic.

        Args:
            namespace: Namespace to clear.
        """
        index = self._get_index()
        loop = asyncio.get_running_loop()

        await loop.run_in_executor(
            None,
            lambda: index.delete(delete_all=True, namespace=namespace),
        )

    async def get_stats(self, namespace: str | None = None) -> IndexStats:
        """Get index statistics.

        Args:
            namespace: Optional namespace to filter stats (not currently supported by API,
                       but included for future compatibility).

        Returns:
            IndexStats with vector counts per namespace.

        Raises:
            PineconeNotConfiguredError: If Pinecone is not configured.
            PineconeIndexNotFoundError: If the index does not exist.
            PineconeException: On Pinecone API errors after retries.
        """
        await self._validate_index_exists()

        if namespace:
            logger.debug(
                "get_stats namespace parameter ignored - Pinecone API returns all namespaces",
                namespace=namespace,
            )

        stats = await self._get_stats_with_retry()

        logger.debug(
            "Retrieved index stats",
            total_vectors=stats.total_vector_count,
            namespace_count=len(stats.namespaces),
        )

        return stats

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _get_stats_with_retry(self) -> IndexStats:
        """Get index stats with retry logic.

        Returns:
            IndexStats with vector counts.
        """
        index = self._get_index()
        loop = asyncio.get_running_loop()

        result = await loop.run_in_executor(
            None,
            lambda: index.describe_index_stats(),
        )

        # Parse namespace stats
        namespaces = {}
        if result.namespaces:
            for ns_name, ns_stats in result.namespaces.items():
                namespaces[ns_name] = NamespaceStats(
                    vector_count=ns_stats.vector_count,
                )

        return IndexStats(
            total_vector_count=result.total_vector_count,
            namespaces=namespaces,
            dimension=result.dimension if hasattr(result, "dimension") else VECTOR_DIMENSIONS,
        )
