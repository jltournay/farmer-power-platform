"""Semantic chunker for RAG document content.

This module provides the SemanticChunker class that splits extracted document
content into meaningful chunks for vectorization. Chunking preserves semantic
boundaries by splitting on headings and paragraphs.

Story 0.75.10d: Semantic Chunking
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ChunkResult:
    """Result of a single chunk operation.

    Contains the chunk content and metadata for creating RagChunk entities.
    """

    content: str
    section_title: str | None
    word_count: int
    char_count: int
    chunk_index: int


class SemanticChunker:
    """Split document content into semantic chunks for vectorization.

    Chunking strategy:
    1. Split on Markdown headings (H1, H2, H3) to preserve semantic boundaries
    2. If section exceeds chunk_size, split on paragraph boundaries
    3. Apply overlap to maintain context across chunk boundaries
    4. Enforce minimum chunk size to avoid low-quality fragments

    Usage:
        chunker = SemanticChunker(chunk_size=1000, chunk_overlap=200)
        chunks = chunker.chunk(content)
    """

    # Regex to match Markdown headings (H1, H2, H3)
    HEADING_PATTERN = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
    ) -> None:
        """Initialize the semantic chunker.

        Args:
            chunk_size: Target maximum chunk size in characters.
            chunk_overlap: Overlap between consecutive chunks.
            min_chunk_size: Minimum viable chunk size.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk(self, content: str) -> list[ChunkResult]:
        """Split content into semantic chunks.

        Args:
            content: The document content to chunk (Markdown text).

        Returns:
            List of ChunkResult objects containing chunk data and metadata.
        """
        if not content or not content.strip():
            return []

        # Step 1: Split by headings into sections
        sections = self._split_by_headings(content)

        # Step 2: Process each section
        chunks: list[ChunkResult] = []
        chunk_index = 0

        for section_title, section_content in sections:
            # Skip empty sections
            if not section_content.strip():
                continue

            # If section fits in one chunk, keep it whole
            if len(section_content) <= self.chunk_size:
                if len(section_content) >= self.min_chunk_size:
                    chunks.append(
                        ChunkResult(
                            content=section_content,
                            section_title=section_title,
                            word_count=len(section_content.split()),
                            char_count=len(section_content),
                            chunk_index=chunk_index,
                        )
                    )
                    chunk_index += 1
            else:
                # Section too large - split further
                sub_chunks = self._split_large_section(section_content, section_title, chunk_index)
                chunks.extend(sub_chunks)
                chunk_index += len(sub_chunks)

        logger.debug(
            "Content chunked",
            total_chunks=len(chunks),
            content_length=len(content),
        )

        return chunks

    def _split_by_headings(self, content: str) -> list[tuple[str | None, str]]:
        """Split content by Markdown headings.

        Returns list of (section_title, section_content) tuples.
        Content before first heading has section_title=None.
        The heading line is included in the section content for context.

        Args:
            content: The full document content.

        Returns:
            List of (section_title, section_content) tuples.
        """
        sections: list[tuple[str | None, str]] = []

        # Find all heading positions
        matches = list(self.HEADING_PATTERN.finditer(content))

        if not matches:
            # No headings - return entire content as one section
            return [(None, content.strip())]

        # Content before first heading
        if matches[0].start() > 0:
            pre_content = content[: matches[0].start()].strip()
            if pre_content:
                sections.append((None, pre_content))

        # Process each heading and its content
        for i, match in enumerate(matches):
            heading_text = match.group(2).strip()
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            section_content = content[start:end].strip()

            sections.append((heading_text, section_content))

        return sections

    def _split_large_section(
        self,
        content: str,
        section_title: str | None,
        start_index: int,
    ) -> list[ChunkResult]:
        """Split a large section into smaller chunks.

        Uses paragraph boundaries (double newlines) for splitting.
        Applies overlap between chunks to maintain context.

        Args:
            content: The section content to split.
            section_title: The heading this section belongs to.
            start_index: Starting chunk index.

        Returns:
            List of ChunkResult objects.
        """
        paragraphs = content.split("\n\n")
        chunks: list[ChunkResult] = []
        current_chunk = ""
        chunk_index = start_index

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Check if adding this paragraph exceeds chunk_size
            test_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para

            if len(test_chunk) <= self.chunk_size:
                current_chunk = test_chunk
            else:
                # Save current chunk if it meets minimum size
                if len(current_chunk) >= self.min_chunk_size:
                    chunks.append(
                        ChunkResult(
                            content=current_chunk,
                            section_title=section_title,
                            word_count=len(current_chunk.split()),
                            char_count=len(current_chunk),
                            chunk_index=chunk_index,
                        )
                    )
                    chunk_index += 1

                    # Start new chunk with overlap from end of previous
                    overlap_text = self._get_overlap_text(current_chunk)
                    current_chunk = f"{overlap_text}\n\n{para}" if overlap_text else para
                else:
                    # Current chunk too small, just add paragraph anyway
                    current_chunk = test_chunk

        # Don't forget the last chunk
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            chunks.append(
                ChunkResult(
                    content=current_chunk,
                    section_title=section_title,
                    word_count=len(current_chunk.split()),
                    char_count=len(current_chunk),
                    chunk_index=chunk_index,
                )
            )

        return chunks

    def _get_overlap_text(self, content: str) -> str:
        """Extract overlap text from end of content.

        Tries to break at a sentence boundary within the overlap region
        for cleaner context preservation.

        Args:
            content: The content to extract overlap from.

        Returns:
            Overlap text from the end of content.
        """
        if len(content) <= self.chunk_overlap:
            return content

        # Get the overlap region from end of content
        overlap_region = content[-self.chunk_overlap :]

        # Try to find a sentence boundary in the overlap region
        # Look for sentence-ending punctuation followed by space
        sentence_ends = [
            overlap_region.rfind(". "),
            overlap_region.rfind("? "),
            overlap_region.rfind("! "),
        ]
        best_break = max(sentence_ends)

        if best_break > 0:
            # Return text after the sentence boundary
            return overlap_region[best_break + 2 :].strip()

        # No good sentence boundary - return full overlap region
        return overlap_region.strip()
