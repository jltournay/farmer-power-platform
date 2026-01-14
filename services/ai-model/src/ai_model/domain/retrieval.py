"""Retrieval domain models for RAG retrieval operations.

This module re-exports Pydantic models for the RAG retrieval service
from fp_common for backward compatibility:
- RetrievalQuery: Input parameters for a retrieval request
- RetrievalMatch: Single match from a retrieval query
- RetrievalResult: Container for all retrieval matches

Story 0.75.14: RAG Retrieval Service
Story 0.75.23: Models moved to fp_common.models.rag for BFF sharing
"""

# Re-export from fp_common for backward compatibility
from fp_common.models import RetrievalMatch, RetrievalQuery, RetrievalResult

__all__ = ["RetrievalMatch", "RetrievalQuery", "RetrievalResult"]
