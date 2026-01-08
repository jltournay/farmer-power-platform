"""Deduplication utilities for RAG ranking results.

This module provides functions for detecting and removing near-duplicate
chunks from retrieval results using Jaccard similarity on word tokens.

Story 0.75.15: RAG Ranking Logic
"""

import structlog

logger = structlog.get_logger(__name__)


def calculate_jaccard_similarity(text_a: str, text_b: str) -> float:
    """Calculate Jaccard similarity coefficient between two texts.

    Uses word-level tokenization to compute the Jaccard index,
    which is the ratio of intersection to union of word sets.

    Args:
        text_a: First text to compare.
        text_b: Second text to compare.

    Returns:
        Similarity score between 0 (no overlap) and 1 (identical).

    Examples:
        >>> calculate_jaccard_similarity("hello world", "hello world")
        1.0
        >>> calculate_jaccard_similarity("hello world", "goodbye world")
        0.33...
        >>> calculate_jaccard_similarity("abc", "xyz")
        0.0
    """
    if not text_a or not text_b:
        return 0.0

    # Tokenize (simple word split, lowercased)
    tokens_a = set(text_a.lower().split())
    tokens_b = set(text_b.lower().split())

    # Handle empty token sets
    if not tokens_a or not tokens_b:
        return 0.0

    # Calculate Jaccard coefficient: intersection / union
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)

    return intersection / union if union > 0 else 0.0


def deduplicate_matches(
    matches: list,
    threshold: float = 0.9,
) -> tuple[list, int]:
    """Remove near-duplicate matches based on content similarity.

    Compares each match's content with all preceding matches. If the
    Jaccard similarity exceeds the threshold, the match is considered
    a duplicate and removed. Keeps the match with the highest rerank_score.

    Args:
        matches: List of RankedMatch objects to deduplicate.
        threshold: Similarity threshold (0-1). Pairs above this are duplicates.

    Returns:
        Tuple of (deduplicated matches list, count of removed duplicates).

    Note:
        Matches must have 'content' and 'rerank_score' attributes.
        The input list should be sorted by rerank_score descending so that
        higher-scored matches are kept over lower-scored duplicates.
    """
    if not matches:
        return [], 0

    if threshold <= 0.0:
        # No deduplication if threshold is 0 or negative
        return list(matches), 0

    deduplicated: list = []
    removed_count = 0

    for match in matches:
        is_duplicate = False

        for existing in deduplicated:
            similarity = calculate_jaccard_similarity(match.content, existing.content)

            if similarity >= threshold:
                logger.debug(
                    "Duplicate detected",
                    new_chunk_id=match.chunk_id,
                    existing_chunk_id=existing.chunk_id,
                    similarity=round(similarity, 3),
                    threshold=threshold,
                )
                is_duplicate = True
                removed_count += 1
                break

        if not is_duplicate:
            deduplicated.append(match)

    if removed_count > 0:
        logger.info(
            "Deduplication completed",
            original_count=len(matches),
            deduplicated_count=len(deduplicated),
            removed_count=removed_count,
            threshold=threshold,
        )

    return deduplicated, removed_count
