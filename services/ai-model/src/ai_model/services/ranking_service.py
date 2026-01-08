"""Ranking service for RAG result re-ranking and scoring.

This service orchestrates the ranking pipeline:
1. Retrieve candidates using RetrievalService
2. Re-rank using Pinecone Inference reranker
3. Apply domain-specific boosts
4. Apply recency weighting
5. Deduplicate near-similar results

Story 0.75.15: RAG Ranking Logic
"""

import asyncio
from datetime import UTC, datetime

import structlog
from ai_model.config import Settings
from ai_model.domain.ranking import RankedMatch, RankingConfig, RankingResult
from ai_model.domain.retrieval import RetrievalMatch
from ai_model.services.deduplication import deduplicate_matches
from ai_model.services.retrieval_service import RetrievalService
from pinecone import Pinecone

logger = structlog.get_logger(__name__)

# Default max age for recency calculation (1 year in days)
MAX_AGE_DAYS = 365


class RankingServiceError(Exception):
    """Base exception for ranking service errors."""

    pass


class RerankerUnavailableError(RankingServiceError):
    """Raised when Pinecone reranker is unavailable."""

    pass


class RankingService:
    """Ranking service for RAG result re-ranking and scoring.

    This service adds ranking capabilities on top of the RetrievalService:
    - Re-ranking using Pinecone Inference cross-encoder
    - Domain-specific boost factors
    - Recency weighting
    - Near-duplicate removal

    The ranking pipeline:
    1. retrieve(query) → RetrievalResult
    2. _rerank_with_pinecone(matches) → reranked scores
    3. _apply_domain_boosts(matches, config) → boosted scores
    4. _apply_recency_weighting(matches, config) → final scores
    5. deduplicate_matches(matches) → deduplicated results

    All operations are async.
    """

    def __init__(
        self,
        retrieval_service: RetrievalService,
        settings: Settings,
    ) -> None:
        """Initialize the ranking service with dependencies.

        Args:
            retrieval_service: Service for retrieving candidate documents.
            settings: Service configuration with Pinecone credentials.
        """
        self._retrieval_service = retrieval_service
        self._settings = settings
        self._client: Pinecone | None = None

    def _get_client(self) -> Pinecone | None:
        """Get or create the Pinecone client.

        Returns:
            Pinecone client instance or None if not configured.
        """
        if not self._settings.pinecone_enabled:
            return None

        if self._client is None:
            self._client = Pinecone(
                api_key=self._settings.pinecone_api_key.get_secret_value(),  # type: ignore[union-attr]
            )

        return self._client

    async def rank(
        self,
        query: str,
        config: RankingConfig | None = None,
        domains: list[str] | None = None,
        namespace: str | None = None,
    ) -> RankingResult:
        """Rank retrieval results with re-ranking, boosting, and deduplication.

        Orchestrates the full ranking pipeline:
        1. Retrieve candidates using RetrievalService
        2. Re-rank using Pinecone Inference (if available)
        3. Apply domain-specific boosts
        4. Apply recency weighting
        5. Deduplicate near-similar results

        Args:
            query: Search query text.
            config: Ranking configuration (uses defaults if not provided).
            domains: List of knowledge domains to filter.
            namespace: Pinecone namespace for version isolation.

        Returns:
            RankingResult with ranked matches and metadata.
        """
        config = config or RankingConfig()

        # Use settings.pinecone_rerank_model as system default if config uses the default
        if config.rerank_model == "pinecone-rerank-v0" and self._settings.pinecone_rerank_model:
            config = config.model_copy(update={"rerank_model": self._settings.pinecone_rerank_model})

        logger.info(
            "Starting ranking",
            query_length=len(query),
            domains=domains,
            top_n=config.top_n,
            rerank_model=config.rerank_model,
            namespace=namespace,
        )

        # Handle empty query
        if not query or not query.strip():
            logger.debug("Empty query provided, returning empty results")
            return RankingResult(
                matches=[],
                query=query or "",
                ranking_config=config,
                duplicates_removed=0,
                reranker_used=False,
                namespace=namespace,
            )

        # Step 1: Retrieve candidates (fetch more than top_n to allow for deduplication)
        # Request 2x top_n to have buffer after deduplication
        retrieve_count = min(config.top_n * 2, 100)

        retrieval_result = await self._retrieval_service.retrieve(
            query=query,
            domains=domains,
            top_k=retrieve_count,
            confidence_threshold=0.0,  # No filtering at retrieval; ranking handles quality
            namespace=namespace,
        )

        if not retrieval_result.matches:
            logger.debug("No retrieval matches, returning empty results")
            return RankingResult(
                matches=[],
                query=query,
                ranking_config=config,
                duplicates_removed=0,
                reranker_used=False,
                namespace=namespace,
            )

        # Step 2: Convert to RankedMatch and apply reranking
        reranker_used = False
        ranked_matches: list[RankedMatch] = []

        try:
            ranked_matches, reranker_used = await self._rerank_with_pinecone(
                query=query,
                matches=retrieval_result.matches,
                config=config,
            )
        except RerankerUnavailableError:
            logger.warning(
                "Reranker unavailable, falling back to retrieval scores",
                query_length=len(query),
            )
            # Fall back to retrieval scores
            ranked_matches = self._convert_to_ranked_matches(retrieval_result.matches)

        # Step 3: Apply domain boosts
        ranked_matches = self._apply_domain_boosts(ranked_matches, config)

        # Step 4: Apply recency weighting
        ranked_matches = self._apply_recency_weighting(ranked_matches, config)

        # Step 5: Sort by final score and deduplicate
        ranked_matches.sort(key=lambda m: m.rerank_score, reverse=True)
        deduplicated, duplicates_removed = deduplicate_matches(
            ranked_matches,
            threshold=config.dedup_threshold,
        )

        # Limit to top_n
        final_matches = deduplicated[: config.top_n]

        logger.info(
            "Ranking completed",
            query_length=len(query),
            retrieval_count=len(retrieval_result.matches),
            final_count=len(final_matches),
            duplicates_removed=duplicates_removed,
            reranker_used=reranker_used,
            namespace=namespace,
        )

        return RankingResult(
            matches=final_matches,
            query=query,
            ranking_config=config,
            duplicates_removed=duplicates_removed,
            reranker_used=reranker_used,
            namespace=namespace,
        )

    async def _rerank_with_pinecone(
        self,
        query: str,
        matches: list[RetrievalMatch],
        config: RankingConfig,
    ) -> tuple[list[RankedMatch], bool]:
        """Re-rank matches using Pinecone Inference reranker.

        Uses cross-encoder reranking to rescore documents based on
        query-document semantic relevance.

        Args:
            query: Search query text.
            matches: Retrieved matches to rerank.
            config: Ranking configuration.

        Returns:
            Tuple of (list of RankedMatch with rerank scores, success flag).

        Raises:
            RerankerUnavailableError: If Pinecone client is not configured.
        """
        client = self._get_client()
        if client is None:
            raise RerankerUnavailableError("Pinecone client not configured")

        # Format documents for reranking
        docs = [{"id": match.chunk_id, "text": match.content} for match in matches]

        logger.debug(
            "Calling Pinecone reranker",
            query_length=len(query),
            document_count=len(docs),
            model=config.rerank_model,
        )

        try:
            # Run reranker in thread pool since it's synchronous
            loop = asyncio.get_running_loop()
            rerank_result = await loop.run_in_executor(
                None,
                lambda: client.inference.rerank(
                    model=config.rerank_model,
                    query=query,
                    documents=docs,
                    top_n=len(docs),  # Get scores for all, we filter later
                    return_documents=True,
                ),
            )

            # Build ranked matches from reranker results
            ranked_matches: list[RankedMatch] = []

            # Create lookup for original matches by chunk_id
            match_lookup = {m.chunk_id: m for m in matches}

            for item in rerank_result.data:
                # Get original match data
                doc_id = docs[item["index"]]["id"]
                original = match_lookup.get(doc_id)

                if original is None:
                    logger.warning(
                        "Original match not found for reranked document",
                        doc_id=doc_id,
                    )
                    continue

                ranked_matches.append(
                    RankedMatch(
                        chunk_id=original.chunk_id,
                        content=original.content,
                        score=original.score,
                        rerank_score=item["score"],
                        document_id=original.document_id,
                        title=original.title,
                        domain=original.domain,
                        metadata=original.metadata,
                        boost_applied=1.0,
                        recency_factor=0.0,
                        updated_at=None,
                    )
                )

            logger.debug(
                "Pinecone reranking completed",
                input_count=len(matches),
                output_count=len(ranked_matches),
            )

            return ranked_matches, True

        except Exception as e:
            logger.warning(
                "Pinecone reranker failed",
                error=str(e),
                model=config.rerank_model,
            )
            raise RerankerUnavailableError(f"Reranker failed: {e}") from e

    def _convert_to_ranked_matches(
        self,
        matches: list[RetrievalMatch],
    ) -> list[RankedMatch]:
        """Convert RetrievalMatch list to RankedMatch list using retrieval scores.

        Used as fallback when reranker is unavailable.

        Args:
            matches: Retrieved matches to convert.

        Returns:
            List of RankedMatch using retrieval scores as rerank scores.
        """
        return [
            RankedMatch(
                chunk_id=m.chunk_id,
                content=m.content,
                score=m.score,
                rerank_score=m.score,  # Use retrieval score as fallback
                document_id=m.document_id,
                title=m.title,
                domain=m.domain,
                metadata=m.metadata,
                boost_applied=1.0,
                recency_factor=0.0,
                updated_at=None,
            )
            for m in matches
        ]

    def _apply_domain_boosts(
        self,
        matches: list[RankedMatch],
        config: RankingConfig,
    ) -> list[RankedMatch]:
        """Apply domain-specific boost factors to scores.

        Multiplies rerank_score by the boost factor for each match's domain.
        Default boost is 1.0 (no change) if domain not in config.

        Args:
            matches: Ranked matches to boost.
            config: Configuration with domain_boosts mapping.

        Returns:
            List of matches with updated rerank_scores and boost_applied.
        """
        if not config.domain_boosts:
            return matches

        for match in matches:
            boost = config.domain_boosts.get(match.domain, 1.0)
            if boost != 1.0:
                match.rerank_score *= boost
                match.boost_applied = boost

                logger.debug(
                    "Domain boost applied",
                    chunk_id=match.chunk_id,
                    domain=match.domain,
                    boost=boost,
                    new_score=round(match.rerank_score, 4),
                )

        return matches

    def _apply_recency_weighting(
        self,
        matches: list[RankedMatch],
        config: RankingConfig,
    ) -> list[RankedMatch]:
        """Apply time-based score adjustment based on document freshness.

        Formula: final_score = rerank_score * (1 + recency_weight * recency_factor)
        Where recency_factor is 1.0 for today, 0.0 for documents > 1 year old.

        Args:
            matches: Ranked matches to weight.
            config: Configuration with recency_weight.

        Returns:
            List of matches with updated rerank_scores and recency_factor.
        """
        if config.recency_weight <= 0.0:
            return matches

        now = datetime.now(UTC)

        for match in matches:
            # Calculate recency factor
            if match.updated_at:
                days_old = (now - match.updated_at).days
                recency_factor = max(0.0, 1.0 - (days_old / MAX_AGE_DAYS))
            else:
                # If no updated_at, use neutral factor
                recency_factor = 0.5

            match.recency_factor = recency_factor

            # Apply recency weighting
            multiplier = 1.0 + (config.recency_weight * recency_factor)
            match.rerank_score *= multiplier

            logger.debug(
                "Recency weighting applied",
                chunk_id=match.chunk_id,
                recency_factor=round(recency_factor, 3),
                multiplier=round(multiplier, 3),
                new_score=round(match.rerank_score, 4),
            )

        return matches

    async def rank_retrieval_result(
        self,
        query: str,
        matches: list[RetrievalMatch],
        config: RankingConfig | None = None,
        namespace: str | None = None,
    ) -> RankingResult:
        """Rank pre-retrieved results without calling RetrievalService.

        Useful when you already have retrieval results and just want ranking.

        Args:
            query: Original search query (needed for reranking).
            matches: Pre-retrieved matches to rank.
            config: Ranking configuration.
            namespace: Namespace for metadata.

        Returns:
            RankingResult with ranked matches.
        """
        config = config or RankingConfig()

        if not matches:
            return RankingResult(
                matches=[],
                query=query,
                ranking_config=config,
                duplicates_removed=0,
                reranker_used=False,
                namespace=namespace,
            )

        # Apply reranking
        reranker_used = False
        ranked_matches: list[RankedMatch] = []

        try:
            ranked_matches, reranker_used = await self._rerank_with_pinecone(
                query=query,
                matches=matches,
                config=config,
            )
        except RerankerUnavailableError:
            ranked_matches = self._convert_to_ranked_matches(matches)

        # Apply boosts, recency, sort, deduplicate
        ranked_matches = self._apply_domain_boosts(ranked_matches, config)
        ranked_matches = self._apply_recency_weighting(ranked_matches, config)
        ranked_matches.sort(key=lambda m: m.rerank_score, reverse=True)
        deduplicated, duplicates_removed = deduplicate_matches(
            ranked_matches,
            threshold=config.dedup_threshold,
        )

        final_matches = deduplicated[: config.top_n]

        return RankingResult(
            matches=final_matches,
            query=query,
            ranking_config=config,
            duplicates_removed=duplicates_removed,
            reranker_used=reranker_used,
            namespace=namespace,
        )
