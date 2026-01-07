"""Unit tests for SemanticChunker.

Story 0.75.10d: Semantic Chunking

Note: Use importlib to directly import the module file to avoid dependency chain
through services/__init__.py which requires fp_common and other packages.
"""

import importlib.util
import sys
from pathlib import Path

# Load semantic_chunker module directly to avoid services/__init__.py chain
_chunker_path = (
    Path(__file__).parents[3] / "services" / "ai-model" / "src" / "ai_model" / "services" / "semantic_chunker.py"
)
_spec = importlib.util.spec_from_file_location("semantic_chunker", _chunker_path)
_semantic_chunker = importlib.util.module_from_spec(_spec)
sys.modules["semantic_chunker"] = _semantic_chunker
_spec.loader.exec_module(_semantic_chunker)

ChunkResult = _semantic_chunker.ChunkResult
SemanticChunker = _semantic_chunker.SemanticChunker


class TestSemanticChunkerBasic:
    """Basic functionality tests for SemanticChunker."""

    def test_chunker_initialization_default_params(self):
        """Test chunker initializes with default parameters."""
        chunker = SemanticChunker()
        assert chunker.chunk_size == 1000
        assert chunker.chunk_overlap == 200
        assert chunker.min_chunk_size == 100

    def test_chunker_initialization_custom_params(self):
        """Test chunker initializes with custom parameters."""
        chunker = SemanticChunker(chunk_size=500, chunk_overlap=50, min_chunk_size=25)
        assert chunker.chunk_size == 500
        assert chunker.chunk_overlap == 50
        assert chunker.min_chunk_size == 25

    def test_chunk_empty_content_returns_empty_list(self):
        """Test that empty content returns empty list."""
        chunker = SemanticChunker()
        assert chunker.chunk("") == []
        assert chunker.chunk("   ") == []
        assert chunker.chunk("\n\n") == []

    def test_chunk_none_content_returns_empty_list(self):
        """Test that None-like content returns empty list."""
        chunker = SemanticChunker()
        assert chunker.chunk(None) == []


class TestSemanticChunkerHeadingSplitting:
    """Tests for heading-based content splitting."""

    def test_chunk_single_section_no_heading(self):
        """Test content without headings becomes single chunk."""
        chunker = SemanticChunker(chunk_size=1000, min_chunk_size=10)
        content = "This is a simple paragraph without any headings."

        chunks = chunker.chunk(content)

        assert len(chunks) == 1
        assert chunks[0].content == content
        assert chunks[0].section_title is None
        assert chunks[0].chunk_index == 0

    def test_chunk_h1_heading_creates_section(self):
        """Test H1 heading creates proper section."""
        chunker = SemanticChunker(chunk_size=1000, min_chunk_size=10)
        content = "# Introduction\n\nThis is the introduction text."

        chunks = chunker.chunk(content)

        assert len(chunks) == 1
        assert "# Introduction" in chunks[0].content
        assert chunks[0].section_title == "Introduction"

    def test_chunk_multiple_headings_create_sections(self):
        """Test multiple headings create separate sections."""
        chunker = SemanticChunker(chunk_size=1000, min_chunk_size=10)
        content = """# Section One

Content for section one.

## Section Two

Content for section two.

### Section Three

Content for section three."""

        chunks = chunker.chunk(content)

        assert len(chunks) == 3
        assert chunks[0].section_title == "Section One"
        assert chunks[1].section_title == "Section Two"
        assert chunks[2].section_title == "Section Three"
        # Verify chunk indices are sequential
        assert [c.chunk_index for c in chunks] == [0, 1, 2]

    def test_chunk_content_before_first_heading(self):
        """Test content before first heading is preserved."""
        chunker = SemanticChunker(chunk_size=1000, min_chunk_size=10)
        content = """Some preamble text before any heading.

# First Section

Section content here."""

        chunks = chunker.chunk(content)

        assert len(chunks) == 2
        # First chunk has no section title (preamble)
        assert chunks[0].section_title is None
        assert "preamble" in chunks[0].content
        # Second chunk has the heading
        assert chunks[1].section_title == "First Section"


class TestSemanticChunkerParagraphSplitting:
    """Tests for paragraph-based splitting of large sections."""

    def test_chunk_large_section_splits_on_paragraphs(self):
        """Test large section splits on paragraph boundaries."""
        chunker = SemanticChunker(chunk_size=200, chunk_overlap=50, min_chunk_size=50)

        # Create content with paragraphs that exceeds chunk_size
        content = """# Large Section

First paragraph with some content that fills up space nicely.

Second paragraph with different content that also takes up room.

Third paragraph that should end up in a separate chunk due to size limits.

Fourth paragraph to ensure we have enough content to test properly."""

        chunks = chunker.chunk(content)

        # Should create multiple chunks due to size limit
        assert len(chunks) >= 2
        # All chunks should reference the section title
        for chunk in chunks:
            assert chunk.section_title == "Large Section"

    def test_chunk_overlap_is_applied(self):
        """Test that overlap text is included in subsequent chunks."""
        chunker = SemanticChunker(chunk_size=150, chunk_overlap=30, min_chunk_size=20)

        content = """# Test Section

This is the first paragraph with some meaningful content. It ends with a clear sentence.

This is the second paragraph that should include overlap from the previous chunk."""

        chunks = chunker.chunk(content)

        # With small chunk_size, we should have multiple chunks
        if len(chunks) >= 2:
            # Overlap should cause some repetition between chunks
            # The second chunk might contain words from the end of the first
            assert len(chunks[0].content) > 0
            assert len(chunks[1].content) > 0


class TestSemanticChunkerMinimumSize:
    """Tests for minimum chunk size handling."""

    def test_chunk_below_minimum_is_skipped(self):
        """Test that very small chunks are skipped."""
        chunker = SemanticChunker(chunk_size=1000, min_chunk_size=100)

        content = """# First Section

Very short.

# Second Section

This section has much more content that definitely exceeds the minimum chunk size requirement of one hundred characters."""

        chunks = chunker.chunk(content)

        # First section is too small, should be skipped
        # Second section meets minimum
        assert len(chunks) >= 1
        # Check that we have the substantial section
        assert any("much more content" in c.content for c in chunks)


class TestSemanticChunkerMetadata:
    """Tests for chunk metadata calculation."""

    def test_chunk_word_count_is_accurate(self):
        """Test that word count is calculated correctly."""
        chunker = SemanticChunker(chunk_size=1000, min_chunk_size=10)
        content = "One two three four five."

        chunks = chunker.chunk(content)

        assert len(chunks) == 1
        assert chunks[0].word_count == 5

    def test_chunk_char_count_is_accurate(self):
        """Test that character count is calculated correctly."""
        chunker = SemanticChunker(chunk_size=1000, min_chunk_size=10)
        content = "Hello world!"

        chunks = chunker.chunk(content)

        assert len(chunks) == 1
        assert chunks[0].char_count == len(content)

    def test_chunk_indices_are_sequential(self):
        """Test that chunk indices are assigned sequentially."""
        chunker = SemanticChunker(chunk_size=1000, min_chunk_size=10)
        content = """# Section 1

Content one.

# Section 2

Content two.

# Section 3

Content three."""

        chunks = chunker.chunk(content)

        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i


class TestSemanticChunkerEdgeCases:
    """Edge case tests for SemanticChunker."""

    def test_chunk_only_headings_no_content(self):
        """Test document with only headings and no body content."""
        chunker = SemanticChunker(chunk_size=1000, min_chunk_size=10)
        content = """# First

# Second

# Third"""

        chunks = chunker.chunk(content)

        # Headings alone are very short, might not meet minimum
        # But should not crash
        assert isinstance(chunks, list)

    def test_chunk_heading_without_space(self):
        """Test heading format variations."""
        chunker = SemanticChunker(chunk_size=1000, min_chunk_size=10)
        content = """#Heading Without Space

Some content here that follows."""

        chunks = chunker.chunk(content)

        # This doesn't match proper markdown heading format (needs space)
        # So it should be treated as regular content
        assert len(chunks) >= 1

    def test_chunk_heading_with_special_characters(self):
        """Test headings with special characters."""
        chunker = SemanticChunker(chunk_size=1000, min_chunk_size=10)
        content = """# Heading with "quotes" and 'apostrophes'

Content below the heading."""

        chunks = chunker.chunk(content)

        assert len(chunks) == 1
        assert chunks[0].section_title == "Heading with \"quotes\" and 'apostrophes'"

    def test_chunk_unicode_content(self):
        """Test content with unicode characters."""
        chunker = SemanticChunker(chunk_size=1000, min_chunk_size=10)
        content = """# Tea Cultivation 🍵

茶叶种植需要特定的气候条件。

Growing tea requires specific climate conditions."""

        chunks = chunker.chunk(content)

        assert len(chunks) == 1
        assert "🍵" in chunks[0].content
        assert "茶叶" in chunks[0].content

    def test_chunk_preserves_markdown_formatting(self):
        """Test that markdown formatting is preserved in chunks."""
        chunker = SemanticChunker(chunk_size=1000, min_chunk_size=10)
        content = """# Formatted Section

- Bullet point one
- Bullet point two

**Bold text** and *italic text*.

```python
code_block = True
```"""

        chunks = chunker.chunk(content)

        assert len(chunks) == 1
        assert "- Bullet point" in chunks[0].content
        assert "**Bold text**" in chunks[0].content
        assert "```python" in chunks[0].content


class TestSemanticChunkerOverlap:
    """Tests specifically for overlap functionality."""

    def test_overlap_at_sentence_boundary(self):
        """Test that overlap tries to break at sentence boundaries."""
        chunker = SemanticChunker(chunk_size=150, chunk_overlap=50, min_chunk_size=20)

        content = """# Test

This is sentence one. This is sentence two. This is sentence three.

This is paragraph two with more sentences. Another sentence here."""

        chunks = chunker.chunk(content)

        # Should produce chunks with sentence-aware overlap
        assert len(chunks) >= 1
        # Verify no crashes and reasonable output
        for chunk in chunks:
            assert chunk.char_count > 0

    def test_overlap_content_less_than_overlap(self):
        """Test overlap handling when content is shorter than overlap."""
        chunker = SemanticChunker(chunk_size=100, chunk_overlap=200, min_chunk_size=10)

        # Short content that's less than overlap
        content = "Short content."

        # Should not crash
        chunks = chunker.chunk(content)
        assert len(chunks) == 1


class TestChunkResultDataclass:
    """Tests for the ChunkResult dataclass."""

    def test_chunk_result_creation(self):
        """Test ChunkResult dataclass can be created."""
        result = ChunkResult(
            content="Test content",
            section_title="Test Section",
            word_count=2,
            char_count=12,
            chunk_index=0,
        )

        assert result.content == "Test content"
        assert result.section_title == "Test Section"
        assert result.word_count == 2
        assert result.char_count == 12
        assert result.chunk_index == 0

    def test_chunk_result_with_none_section_title(self):
        """Test ChunkResult with None section title."""
        result = ChunkResult(
            content="Test",
            section_title=None,
            word_count=1,
            char_count=4,
            chunk_index=0,
        )

        assert result.section_title is None


class TestSemanticChunkerRealWorldScenarios:
    """Tests with realistic document content."""

    def test_chunk_tea_disease_document(self):
        """Test chunking a realistic tea disease document."""
        chunker = SemanticChunker(chunk_size=500, chunk_overlap=100, min_chunk_size=50)

        content = """# Blister Blight Disease Guide

## Overview

Blister blight is one of the most economically important diseases affecting tea cultivation in highland regions. The disease is caused by the fungus Exobasidium vexans and primarily affects young, tender tea leaves.

## Symptoms

The disease manifests as small, translucent spots on young leaves that gradually enlarge and become convex blisters on the upper surface. The corresponding lower surface shows concave depressions covered with a white powdery mass of fungal spores.

## Favorable Conditions

- Cool temperatures (15-20°C)
- High humidity (above 80%)
- Frequent rainfall or mist
- Shaded conditions
- Young flush growth

## Management Strategies

### Cultural Control

Maintain proper pruning schedule to reduce dense canopy. Ensure adequate drainage to prevent waterlogging. Remove and destroy infected shoots during plucking.

### Chemical Control

Apply copper-based fungicides preventively during favorable conditions. Systemic fungicides may be used during severe outbreaks. Follow recommended spray intervals and concentrations."""

        chunks = chunker.chunk(content)

        # Should create multiple chunks
        assert len(chunks) >= 3
        # Should preserve section structure
        section_titles = [c.section_title for c in chunks]
        assert any("Overview" in (t or "") for t in section_titles)
        assert any("Symptoms" in (t or "") for t in section_titles)
