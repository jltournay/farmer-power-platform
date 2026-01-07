"""Chunking workflow for RAG document processing.

This module provides the ChunkingWorkflow service that orchestrates
document chunking after extraction, integrating with the extraction
workflow to create chunks automatically.

Story 0.75.10d: Semantic Chunking
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog
from ai_model.config import Settings
from ai_model.domain.rag_document import RagChunk, RagDocument
from ai_model.services.semantic_chunker import ChunkResult, SemanticChunker

if TYPE_CHECKING:
    from ai_model.infrastructure.repositories import RagChunkRepository

logger = structlog.get_logger(__name__)


class ChunkingError(Exception):
    """Base exception for chunking failures."""

    pass


class TooManyChunksError(ChunkingError):
    """Raised when document produces more chunks than allowed."""

    pass


class ChunkingWorkflow:
    """Orchestrates document chunking after extraction.

    Integrates with ExtractionWorkflow to create chunks from
    extracted content. Tracks progress and stores chunks in MongoDB.

    Usage:
        workflow = ChunkingWorkflow(chunk_repo, settings)
        chunks = await workflow.chunk_document(document)
    """

    def __init__(
        self,
        chunk_repository: RagChunkRepository,
        settings: Settings | None = None,
    ) -> None:
        """Initialize the chunking workflow.

        Args:
            chunk_repository: Repository for RagChunk persistence.
            settings: Optional settings for chunking configuration.
        """
        self._chunk_repo = chunk_repository
        self._settings = settings or Settings()

        # Create chunker with configured settings
        self._chunker = SemanticChunker(
            chunk_size=self._settings.chunk_size,
            chunk_overlap=self._settings.chunk_overlap,
            min_chunk_size=self._settings.min_chunk_size,
        )

    async def chunk_document(
        self,
        document: RagDocument,
        progress_callback: callable | None = None,
    ) -> list[RagChunk]:
        """Chunk a document's content and store in MongoDB.

        Args:
            document: The RagDocument to chunk (must have content).
            progress_callback: Optional callback(chunks_created, estimated_total)
                              for progress tracking.

        Returns:
            List of created RagChunk entities.

        Raises:
            ChunkingError: If chunking fails.
            TooManyChunksError: If chunk count exceeds maximum.
        """
        logger.info(
            "Starting document chunking",
            document_id=document.document_id,
            version=document.version,
            content_length=len(document.content) if document.content else 0,
        )

        if not document.content or not document.content.strip():
            logger.warning(
                "Document has no content to chunk",
                document_id=document.document_id,
            )
            return []

        # Delete any existing chunks for this document version
        deleted = await self._chunk_repo.delete_by_document(
            document.document_id,
            document.version,
        )
        if deleted > 0:
            logger.info(
                "Deleted existing chunks before re-chunking",
                document_id=document.document_id,
                version=document.version,
                deleted_count=deleted,
            )

        # Perform semantic chunking
        chunk_results = self._chunker.chunk(document.content)

        # Report initial progress estimate
        estimated_total = len(chunk_results)
        if progress_callback:
            progress_callback(0, estimated_total)

        # Check chunk count limit
        if estimated_total > self._settings.max_chunks_per_document:
            raise TooManyChunksError(
                f"Document produces {estimated_total} chunks, "
                f"exceeds maximum of {self._settings.max_chunks_per_document}"
            )

        # Convert chunk results to RagChunk entities
        chunks = self._create_chunk_entities(document, chunk_results)

        # Bulk create chunks in MongoDB
        await self._chunk_repo.bulk_create(chunks)

        # Report completion
        if progress_callback:
            progress_callback(len(chunks), len(chunks))

        logger.info(
            "Document chunking completed",
            document_id=document.document_id,
            version=document.version,
            chunks_created=len(chunks),
        )

        return chunks

    def _create_chunk_entities(
        self,
        document: RagDocument,
        chunk_results: list[ChunkResult],
    ) -> list[RagChunk]:
        """Convert ChunkResult objects to RagChunk entities.

        Args:
            document: Parent document for metadata.
            chunk_results: List of chunk results from semantic chunker.

        Returns:
            List of RagChunk entities ready for persistence.
        """
        chunks: list[RagChunk] = []
        now = datetime.now(UTC)

        for result in chunk_results:
            # Generate unique chunk ID
            chunk_id = f"{document.document_id}-v{document.version}-chunk-{result.chunk_index}"

            chunk = RagChunk(
                chunk_id=chunk_id,
                document_id=document.document_id,
                document_version=document.version,
                chunk_index=result.chunk_index,
                content=result.content,
                section_title=result.section_title,
                word_count=result.word_count,
                char_count=result.char_count,
                created_at=now,
                pinecone_id=None,  # Set after vectorization
            )

            chunks.append(chunk)

        return chunks

    async def get_chunks(
        self,
        document_id: str,
        version: int,
    ) -> list[RagChunk]:
        """Get all chunks for a document version.

        Args:
            document_id: The document ID.
            version: The document version.

        Returns:
            List of chunks, sorted by chunk_index.
        """
        return await self._chunk_repo.get_by_document(document_id, version)

    async def get_chunk_count(
        self,
        document_id: str,
        version: int,
    ) -> int:
        """Get chunk count for a document version.

        Args:
            document_id: The document ID.
            version: The document version.

        Returns:
            Number of chunks.
        """
        return await self._chunk_repo.count_by_document(document_id, version)

    async def delete_chunks(
        self,
        document_id: str,
        version: int,
    ) -> int:
        """Delete all chunks for a document version.

        Args:
            document_id: The document ID.
            version: The document version.

        Returns:
            Number of chunks deleted.
        """
        return await self._chunk_repo.delete_by_document(document_id, version)
