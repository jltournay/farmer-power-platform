"""Embedding service using Pinecone Inference API.

This service provides document embedding functionality using Pinecone's
multilingual-e5-large model. It handles:
- Single and batch embedding operations
- Automatic batching for large requests (max 96 texts per batch)
- Retry logic with exponential backoff for transient errors
- Cost tracking via MongoDB persistence

Story 0.75.12: RAG Embedding Configuration (Pinecone Inference)
"""

import asyncio
import uuid
from typing import Any

import structlog
from ai_model.config import Settings
from ai_model.domain.embedding import (
    EmbeddingCostEvent,
    EmbeddingInputType,
    EmbeddingResult,
    EmbeddingUsage,
)
from ai_model.infrastructure.repositories.embedding_cost_repository import (
    EmbeddingCostEventRepository,
)
from pinecone import Pinecone
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)


class EmbeddingServiceError(Exception):
    """Base exception for embedding service errors."""

    pass


class PineconeNotConfiguredError(EmbeddingServiceError):
    """Raised when Pinecone API key is not configured."""

    pass


class EmbeddingBatchError(EmbeddingServiceError):
    """Raised when a batch embedding operation fails."""

    def __init__(self, message: str, batch_index: int, original_error: Exception | None = None):
        super().__init__(message)
        self.batch_index = batch_index
        self.original_error = original_error


class EmbeddingService:
    """Embedding service using Pinecone Inference API.

    This service provides methods for embedding text using Pinecone's
    multilingual-e5-large model. It supports:
    - Single query embedding
    - Batch passage embedding with automatic chunking
    - Retry logic for transient errors
    - Cost event persistence for tracking

    The service requires Pinecone API key to be configured in settings.
    All operations are async.
    """

    # Default dimensions for multilingual-e5-large model
    E5_LARGE_DIMENSIONS = 1024

    def __init__(
        self,
        settings: Settings,
        cost_repository: EmbeddingCostEventRepository | None = None,
    ) -> None:
        """Initialize the embedding service.

        Args:
            settings: Service configuration.
            cost_repository: Repository for cost event persistence (optional).
        """
        self._settings = settings
        self._cost_repository = cost_repository
        self._client: Pinecone | None = None

    def _get_client(self) -> Pinecone:
        """Get or create the Pinecone client.

        Returns:
            Pinecone client instance.

        Raises:
            PineconeNotConfiguredError: If API key is not configured.
        """
        if not self._settings.pinecone_enabled:
            raise PineconeNotConfiguredError(
                "Pinecone API key is not configured. Set AI_MODEL_PINECONE_API_KEY environment variable."
            )

        if self._client is None:
            self._client = Pinecone(
                api_key=self._settings.pinecone_api_key.get_secret_value(),  # type: ignore[union-attr]
            )

        return self._client

    async def embed_texts(
        self,
        texts: list[str],
        input_type: EmbeddingInputType = EmbeddingInputType.PASSAGE,
        request_id: str | None = None,
        knowledge_domain: str | None = None,
    ) -> EmbeddingResult:
        """Embed multiple texts with automatic batching.

        This method handles batching automatically if the number of texts
        exceeds the Pinecone batch limit (96 texts per request).

        Args:
            texts: List of texts to embed (any length - will be batched).
            input_type: Whether texts are passages (documents) or queries.
            request_id: Optional correlation ID for tracing.
            knowledge_domain: Optional domain for cost attribution.

        Returns:
            EmbeddingResult with embeddings, dimensions, and usage stats.

        Raises:
            PineconeNotConfiguredError: If Pinecone is not configured.
            EmbeddingBatchError: If a batch operation fails.
        """
        if not texts:
            return EmbeddingResult(
                embeddings=[],
                model=self._settings.pinecone_embedding_model,
                dimensions=self.E5_LARGE_DIMENSIONS,
                usage=EmbeddingUsage(total_tokens=0),
            )

        request_id = request_id or str(uuid.uuid4())
        batch_size = self._settings.embedding_batch_size
        all_embeddings: list[list[float]] = []
        total_tokens = 0
        batch_count = 0
        retry_count = 0

        # Split texts into batches
        batches = [texts[i : i + batch_size] for i in range(0, len(texts), batch_size)]

        logger.info(
            "Starting batch embedding",
            request_id=request_id,
            total_texts=len(texts),
            batch_count=len(batches),
            input_type=input_type.value,
        )

        for batch_idx, batch in enumerate(batches):
            try:
                batch_result, batch_retries = await self._embed_batch_with_retry(
                    batch=batch,
                    input_type=input_type,
                    batch_index=batch_idx,
                )
                all_embeddings.extend(batch_result["embeddings"])
                total_tokens += batch_result["tokens"]
                batch_count += 1
                retry_count += batch_retries
            except Exception as e:
                logger.error(
                    "Batch embedding failed",
                    request_id=request_id,
                    batch_index=batch_idx,
                    error=str(e),
                )
                # Record failure cost event
                await self._record_cost_event(
                    request_id=request_id,
                    texts_count=len(texts),
                    tokens_total=total_tokens,
                    knowledge_domain=knowledge_domain,
                    success=False,
                    batch_count=batch_count,
                    retry_count=retry_count,
                )
                raise EmbeddingBatchError(
                    f"Failed to embed batch {batch_idx}: {e}",
                    batch_index=batch_idx,
                    original_error=e if isinstance(e, Exception) else None,
                )

        # Record successful cost event
        await self._record_cost_event(
            request_id=request_id,
            texts_count=len(texts),
            tokens_total=total_tokens,
            knowledge_domain=knowledge_domain,
            success=True,
            batch_count=batch_count,
            retry_count=retry_count,
        )

        logger.info(
            "Batch embedding completed",
            request_id=request_id,
            total_texts=len(texts),
            total_tokens=total_tokens,
            batch_count=batch_count,
        )

        return EmbeddingResult(
            embeddings=all_embeddings,
            model=self._settings.pinecone_embedding_model,
            dimensions=self.E5_LARGE_DIMENSIONS,
            usage=EmbeddingUsage(total_tokens=total_tokens),
        )

    async def _embed_batch_with_retry(
        self,
        batch: list[str],
        input_type: EmbeddingInputType,
        batch_index: int,
    ) -> tuple[dict[str, Any], int]:
        """Embed a single batch with retry logic.

        Args:
            batch: List of texts to embed (max 96).
            input_type: Whether texts are passages or queries.
            batch_index: Index of this batch (for logging).

        Returns:
            Tuple of (result dict with embeddings and tokens, retry count).
        """
        retry_count = 0

        @retry(
            stop=stop_after_attempt(self._settings.embedding_retry_max_attempts),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
            reraise=True,
        )
        async def _do_embed() -> dict[str, Any]:
            nonlocal retry_count

            client = self._get_client()

            # Run Pinecone embed in a thread pool since it's synchronous
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: client.inference.embed(
                    model=self._settings.pinecone_embedding_model,
                    inputs=batch,
                    parameters={
                        "input_type": input_type.value,
                        "truncate": "END",
                    },
                ),
            )

            # Extract embeddings from result
            embeddings = [item["values"] for item in result.data]
            tokens = result.usage.total_tokens if hasattr(result, "usage") else 0

            logger.debug(
                "Batch embedded",
                batch_index=batch_index,
                texts_count=len(batch),
                tokens=tokens,
            )

            return {"embeddings": embeddings, "tokens": tokens}

        try:
            result = await _do_embed()
            return result, retry_count
        except Exception as e:
            # Count retries from tenacity statistics if available
            if hasattr(_do_embed, "retry"):
                stats = _do_embed.retry.statistics  # type: ignore[attr-defined]
                retry_count = stats.get("attempt_number", 1) - 1
            logger.warning(
                "Embed batch failed after retries",
                batch_index=batch_index,
                retry_count=retry_count,
                error=str(e),
            )
            raise

    async def embed_query(self, query: str, request_id: str | None = None) -> list[float]:
        """Convenience method for single query embedding.

        Uses 'query' input type for optimal E5 performance on search queries.

        Args:
            query: Search query text.
            request_id: Optional correlation ID for tracing.

        Returns:
            Single embedding vector (1024 dimensions for E5-large).

        Raises:
            PineconeNotConfiguredError: If Pinecone is not configured.
        """
        result = await self.embed_texts(
            texts=[query],
            input_type=EmbeddingInputType.QUERY,
            request_id=request_id,
        )
        return result.embeddings[0] if result.embeddings else []

    async def embed_passages(
        self,
        passages: list[str],
        request_id: str | None = None,
        knowledge_domain: str | None = None,
    ) -> list[list[float]]:
        """Convenience method for document passages.

        Uses 'passage' input type for optimal E5 performance on documents.

        Args:
            passages: List of document chunks/passages.
            request_id: Optional correlation ID for tracing.
            knowledge_domain: Optional domain for cost attribution.

        Returns:
            List of embedding vectors (one per passage).

        Raises:
            PineconeNotConfiguredError: If Pinecone is not configured.
        """
        result = await self.embed_texts(
            texts=passages,
            input_type=EmbeddingInputType.PASSAGE,
            request_id=request_id,
            knowledge_domain=knowledge_domain,
        )
        return result.embeddings

    async def _record_cost_event(
        self,
        request_id: str,
        texts_count: int,
        tokens_total: int,
        knowledge_domain: str | None,
        success: bool,
        batch_count: int,
        retry_count: int,
    ) -> None:
        """Record an embedding cost event to MongoDB.

        Args:
            request_id: Correlation ID for tracing.
            texts_count: Number of texts embedded.
            tokens_total: Total tokens processed.
            knowledge_domain: Domain for cost attribution.
            success: Whether the operation succeeded.
            batch_count: Number of batches used.
            retry_count: Number of retries.
        """
        if self._cost_repository is None:
            logger.debug("Cost repository not configured, skipping cost event")
            return

        event = EmbeddingCostEvent(
            id=str(uuid.uuid4()),
            request_id=request_id,
            model=self._settings.pinecone_embedding_model,
            texts_count=texts_count,
            tokens_total=tokens_total,
            knowledge_domain=knowledge_domain,
            success=success,
            batch_count=max(1, batch_count),  # At least 1 for validation
            retry_count=retry_count,
        )

        try:
            await self._cost_repository.insert(event)
            logger.debug(
                "Embedding cost event recorded",
                event_id=event.id,
                request_id=request_id,
            )
        except Exception as e:
            # Don't fail the embedding operation if cost recording fails
            logger.warning(
                "Failed to record embedding cost event",
                request_id=request_id,
                error=str(e),
            )
