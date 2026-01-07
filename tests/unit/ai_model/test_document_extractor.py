"""Unit tests for DocumentExtractor service.

Story 0.75.10b: Basic PDF/Markdown Extraction
Story 0.75.10c: Azure Document Intelligence Integration

Tests cover:
- File type detection (magic bytes and extension)
- PDF text extraction with progress callback
- Markdown extraction preserving structure
- Plain text extraction
- Error handling for corrupted/password-protected files
- Confidence calculation
- Integration tests for Azure DI extraction flow (0.75.10c)
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from ai_model.config import Settings
from ai_model.domain.rag_document import ExtractionMethod, FileType
from ai_model.services.document_extractor import (
    CorruptedFileError,
    DocumentExtractor,
    ExtractionResult,
)

# ============================================
# Test Helpers - Create PDFs programmatically
# ============================================


def create_test_pdf(text: str, pages: int = 1) -> bytes:
    """Create a minimal PDF for unit testing - no external files.

    Uses PyMuPDF to create a PDF with the given text content.

    Args:
        text: Text content to include on each page.
        pages: Number of pages to create.

    Returns:
        PDF file content as bytes.
    """
    import pymupdf

    doc = pymupdf.open()  # New empty PDF
    for i in range(pages):
        page = doc.new_page()
        # Insert text at position (50, 50)
        page.insert_text((50, 50), f"Page {i + 1}: {text}")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_empty_pdf() -> bytes:
    """Create a PDF with no text content (for testing low confidence).

    Returns:
        Empty PDF file content as bytes.
    """
    import pymupdf

    doc = pymupdf.open()
    doc.new_page()  # At least 1 page required
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_text_rich_pdf(pages: int = 5) -> bytes:
    """Create a PDF with substantial text content (high confidence).

    Args:
        pages: Number of pages to create.

    Returns:
        Text-rich PDF file content as bytes.
    """
    import pymupdf

    doc = pymupdf.open()
    # Create a very long text to hit >500 chars per page
    long_text = (
        "This is a sample paragraph with substantial text content that we need to repeat many times to ensure we have enough characters per page to achieve high confidence extraction scores. "
        * 10
    )

    for i in range(pages):
        page = doc.new_page()
        # Insert multiple lines of text to simulate a text-rich document
        y_position = 50
        page.insert_text((50, y_position), f"Page {i + 1}: Document Title")
        for _j in range(5):  # Add 5 paragraphs per page
            y_position += 100
            if y_position < 750:  # Stay within page bounds
                page.insert_text((50, y_position), long_text[:300])  # Truncate to fit

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# ============================================
# File Type Detection Tests
# ============================================


class TestFileTypeDetection:
    """Tests for file type detection from filename and magic bytes."""

    def test_detect_pdf_by_magic_bytes(self):
        """PDF detected by magic bytes regardless of extension."""
        extractor = DocumentExtractor()
        pdf_content = create_test_pdf("test content")

        # Even with wrong extension, magic bytes win
        result = extractor.detect_file_type("document.txt", pdf_content)
        assert result == FileType.PDF

    def test_detect_markdown_by_extension(self):
        """Markdown detected by .md extension."""
        extractor = DocumentExtractor()
        md_content = b"# Heading\n\nSome content"

        result = extractor.detect_file_type("readme.md", md_content)
        assert result == FileType.MD

    def test_detect_markdown_by_markdown_extension(self):
        """Markdown detected by .markdown extension."""
        extractor = DocumentExtractor()
        md_content = b"# Heading"

        result = extractor.detect_file_type("guide.markdown", md_content)
        assert result == FileType.MD

    def test_detect_txt_by_extension(self):
        """Plain text detected by .txt extension."""
        extractor = DocumentExtractor()
        txt_content = b"Plain text content"

        result = extractor.detect_file_type("notes.txt", txt_content)
        assert result == FileType.TXT

    def test_detect_unknown_extension_defaults_to_txt(self):
        """Unknown extensions default to TXT."""
        extractor = DocumentExtractor()
        content = b"Some content"

        result = extractor.detect_file_type("file.xyz", content)
        assert result == FileType.TXT


# ============================================
# PDF Extraction Tests
# ============================================


class TestPDFExtraction:
    """Tests for PDF text extraction using PyMuPDF."""

    @pytest.mark.asyncio
    async def test_extract_pdf_single_page(self):
        """Extract text from single-page PDF."""
        extractor = DocumentExtractor()
        pdf_content = create_test_pdf("Hello World")

        result = await extractor.extract(pdf_content, FileType.PDF)

        assert isinstance(result, ExtractionResult)
        assert "Page 1: Hello World" in result.content
        assert result.page_count == 1
        assert result.extraction_method == ExtractionMethod.TEXT_EXTRACTION

    @pytest.mark.asyncio
    async def test_extract_pdf_multi_page(self):
        """Extract text from multi-page PDF."""
        extractor = DocumentExtractor()
        pdf_content = create_test_pdf("Test content", pages=5)

        result = await extractor.extract(pdf_content, FileType.PDF)

        assert result.page_count == 5
        assert "Page 1" in result.content
        assert "Page 5" in result.content

    @pytest.mark.asyncio
    async def test_extract_pdf_empty_has_low_confidence(self):
        """Empty PDF extraction has low confidence score."""
        extractor = DocumentExtractor()
        pdf_content = create_empty_pdf()

        result = await extractor.extract(pdf_content, FileType.PDF)

        assert result.page_count == 1
        assert result.confidence < 0.3  # Low confidence for empty/scanned

    @pytest.mark.asyncio
    async def test_extract_pdf_text_rich_has_high_confidence(self):
        """Text-rich PDF extraction has high confidence score."""
        extractor = DocumentExtractor()
        pdf_content = create_text_rich_pdf(pages=5)

        result = await extractor.extract(pdf_content, FileType.PDF)

        assert result.page_count == 5
        assert result.confidence > 0.5  # Higher confidence for text-rich

    @pytest.mark.asyncio
    async def test_extract_pdf_with_progress_callback(self):
        """Progress callback is invoked during extraction."""
        extractor = DocumentExtractor()
        pdf_content = create_test_pdf("Test", pages=10)

        progress_calls = []

        def progress_callback(percent, pages_done, total):
            progress_calls.append((percent, pages_done, total))

        result = await extractor.extract(pdf_content, FileType.PDF, progress_callback=progress_callback)

        assert result.page_count == 10
        # Progress is logged at 10% intervals
        # With 10 pages, we expect callbacks at 10%, 20%, ... 100%
        assert len(progress_calls) > 0, "Progress callback should have been called"
        # Verify callback received correct total pages
        assert all(total == 10 for _, _, total in progress_calls)
        # Verify we got the 100% callback (final page)
        percentages = [p for p, _, _ in progress_calls]
        assert 100 in percentages, "Should have received 100% progress callback"

    @pytest.mark.asyncio
    async def test_extract_corrupted_pdf_raises_error(self):
        """Corrupted PDF raises CorruptedFileError."""
        extractor = DocumentExtractor()
        corrupted_content = b"Not a valid PDF content"

        with pytest.raises(CorruptedFileError):
            await extractor.extract(corrupted_content, FileType.PDF)

    @pytest.mark.asyncio
    async def test_extract_password_protected_pdf_raises_error(self):
        """Password-protected PDF raises PasswordProtectedError."""
        import pymupdf
        from ai_model.services.document_extractor import PasswordProtectedError

        # Create a password-protected PDF using PyMuPDF
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Secret content")

        # Encrypt with password
        pdf_bytes = doc.tobytes(
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            user_pw="user123",
            owner_pw="owner456",
        )
        doc.close()

        extractor = DocumentExtractor()

        with pytest.raises(PasswordProtectedError):
            await extractor.extract(pdf_bytes, FileType.PDF)


# ============================================
# Markdown Extraction Tests
# ============================================


class TestMarkdownExtraction:
    """Tests for Markdown file parsing."""

    @pytest.mark.asyncio
    async def test_extract_markdown_preserves_structure(self):
        """Markdown extraction preserves headings and structure."""
        extractor = DocumentExtractor()
        md_content = b"# Main Heading\n\n## Subheading\n\n- List item 1\n- List item 2\n\n```python\ncode block\n```"

        result = await extractor.extract(md_content, FileType.MD)

        assert "# Main Heading" in result.content
        assert "## Subheading" in result.content
        assert "- List item 1" in result.content
        assert "```python" in result.content
        assert result.page_count == 1
        assert result.extraction_method == ExtractionMethod.MANUAL
        assert result.confidence == 1.0

    @pytest.mark.asyncio
    async def test_extract_markdown_handles_encoding(self):
        """Markdown extraction handles UTF-8 encoding with special chars."""
        extractor = DocumentExtractor()
        md_content = "# Café résumé naïve 日本語".encode()

        result = await extractor.extract(md_content, FileType.MD)

        assert "Café" in result.content
        assert "日本語" in result.content


# ============================================
# Plain Text Extraction Tests
# ============================================


class TestTextExtraction:
    """Tests for plain text file extraction."""

    @pytest.mark.asyncio
    async def test_extract_text_simple(self):
        """Plain text extraction works correctly."""
        extractor = DocumentExtractor()
        txt_content = b"Simple plain text content."

        result = await extractor.extract(txt_content, FileType.TXT)

        assert result.content == "Simple plain text content."
        assert result.page_count == 1
        assert result.extraction_method == ExtractionMethod.MANUAL
        assert result.confidence == 1.0

    @pytest.mark.asyncio
    async def test_extract_text_multiline(self):
        """Plain text extraction preserves line breaks."""
        extractor = DocumentExtractor()
        txt_content = b"Line 1\nLine 2\nLine 3"

        result = await extractor.extract(txt_content, FileType.TXT)

        assert result.content == "Line 1\nLine 2\nLine 3"


# ============================================
# Confidence Calculation Tests
# ============================================


class TestConfidenceCalculation:
    """Tests for extraction confidence score calculation."""

    @pytest.mark.asyncio
    async def test_confidence_capped_at_one(self):
        """Confidence score is capped at 1.0 even for very text-rich PDFs."""
        extractor = DocumentExtractor()
        # Create a very text-heavy PDF
        pdf_content = create_text_rich_pdf(pages=10)

        result = await extractor.extract(pdf_content, FileType.PDF)

        assert result.confidence <= 1.0


# ============================================
# Integration Tests (Story 0.75.10c)
# ============================================


class TestAzureDIIntegration:
    """Integration tests for Azure DI extraction flow.

    Story 0.75.10c: Azure Document Intelligence Integration

    These tests verify the full extraction flow with mocked Azure DI responses,
    ensuring proper routing between PyMuPDF and Azure DI based on PDF characteristics.
    """

    @pytest.mark.asyncio
    async def test_full_extraction_flow_digital_pdf_bypasses_azure_di(self):
        """Digital PDF bypasses Azure DI and uses PyMuPDF directly.

        Even when Azure DI is configured, digital PDFs (high confidence)
        should not trigger Azure DI calls.
        """
        # Create mock Azure DI client (should NOT be called)
        mock_azure_client = MagicMock()
        mock_azure_client.analyze_pdf = AsyncMock()

        # Create settings with Azure DI enabled
        settings = Settings()
        settings.azure_doc_intel_endpoint = "https://test.cognitiveservices.azure.com"
        settings.azure_doc_intel_key = MagicMock()
        settings.azure_doc_intel_key.get_secret_value = MagicMock(return_value="test-key")

        extractor = DocumentExtractor(
            azure_di_client=mock_azure_client,
            settings=settings,
        )

        # Create text-rich digital PDF (should NOT trigger Azure DI)
        pdf_content = create_text_rich_pdf(pages=3)

        result = await extractor.extract(pdf_content, FileType.PDF)

        # Verify Azure DI was NOT called
        mock_azure_client.analyze_pdf.assert_not_called()

        # Verify PyMuPDF was used
        assert result.extraction_method == ExtractionMethod.TEXT_EXTRACTION
        assert result.page_count == 3
        assert result.confidence > 0.5  # High confidence for digital PDF

    @pytest.mark.asyncio
    async def test_full_extraction_flow_scanned_pdf_uses_azure_di(self):
        """Scanned PDF routes to Azure DI when configured.

        Low-confidence PDFs (scanned/image-based) should trigger Azure DI
        when the client is available and configured.
        """
        # Create mock Azure DI client
        mock_azure_client = MagicMock()
        mock_azure_client.analyze_pdf = AsyncMock(
            return_value=MagicMock(
                markdown_content="# OCR Extracted Title\n\nExtracted text from scanned document.",
                page_count=5,
                confidence=0.92,
                paragraphs_count=10,
                tables_count=0,
            )
        )

        # Create settings with Azure DI enabled
        settings = Settings()
        settings.azure_doc_intel_endpoint = "https://test.cognitiveservices.azure.com"
        settings.azure_doc_intel_key = MagicMock()
        settings.azure_doc_intel_key.get_secret_value = MagicMock(return_value="test-key")

        extractor = DocumentExtractor(
            azure_di_client=mock_azure_client,
            settings=settings,
        )

        # Create empty PDF to trigger scanned detection
        pdf_content = create_empty_pdf()

        result = await extractor.extract(pdf_content, FileType.PDF)

        # Verify Azure DI was called
        mock_azure_client.analyze_pdf.assert_called_once()

        # Verify result uses Azure DI extraction method
        assert result.extraction_method == ExtractionMethod.AZURE_DOC_INTEL
        assert result.page_count == 5
        assert result.confidence == 0.92
        assert "OCR Extracted Title" in result.content

    @pytest.mark.asyncio
    async def test_full_extraction_flow_scanned_pdf_fallback_on_error(self):
        """Scanned PDF falls back to PyMuPDF when Azure DI fails.

        If Azure DI raises an error, the extractor should gracefully
        fall back to PyMuPDF and include a warning.
        """
        # Create mock Azure DI client that fails
        mock_azure_client = MagicMock()
        mock_azure_client.analyze_pdf = AsyncMock(side_effect=RuntimeError("Azure service unavailable"))

        # Create settings with Azure DI enabled
        settings = Settings()
        settings.azure_doc_intel_endpoint = "https://test.cognitiveservices.azure.com"
        settings.azure_doc_intel_key = MagicMock()
        settings.azure_doc_intel_key.get_secret_value = MagicMock(return_value="test-key")

        extractor = DocumentExtractor(
            azure_di_client=mock_azure_client,
            settings=settings,
        )

        # Create empty PDF to trigger scanned detection
        pdf_content = create_empty_pdf()

        result = await extractor.extract(pdf_content, FileType.PDF)

        # Verify Azure DI was attempted
        mock_azure_client.analyze_pdf.assert_called_once()

        # Verify fallback to PyMuPDF
        assert result.extraction_method == ExtractionMethod.TEXT_EXTRACTION

        # Verify warning was added
        assert len(result.warnings) > 0
        assert "Azure DI failed" in result.warnings[0]

    @pytest.mark.asyncio
    async def test_full_extraction_flow_with_progress_callback(self):
        """Progress callback is invoked correctly during Azure DI extraction."""
        progress_calls = []

        def progress_callback(percent, pages_done, total):
            progress_calls.append((percent, pages_done, total))

        # Create mock Azure DI client that calls progress callback
        async def mock_analyze_pdf(content, progress_callback=None, **kwargs):
            # Simulate progress updates during analysis
            if progress_callback:
                progress_callback(50, 2, 5)
                progress_callback(100, 5, 5)
            return MagicMock(
                markdown_content="# Title\n\nContent",
                page_count=5,
                confidence=0.95,
                paragraphs_count=3,
                tables_count=0,
            )

        mock_azure_client = MagicMock()
        mock_azure_client.analyze_pdf = mock_analyze_pdf

        # Create settings with Azure DI enabled
        settings = Settings()
        settings.azure_doc_intel_endpoint = "https://test.cognitiveservices.azure.com"
        settings.azure_doc_intel_key = MagicMock()
        settings.azure_doc_intel_key.get_secret_value = MagicMock(return_value="test-key")

        extractor = DocumentExtractor(
            azure_di_client=mock_azure_client,
            settings=settings,
        )

        # Create empty PDF to trigger scanned detection
        pdf_content = create_empty_pdf()

        result = await extractor.extract(
            pdf_content,
            FileType.PDF,
            progress_callback=progress_callback,
        )

        # Verify progress callbacks were received
        assert len(progress_calls) == 2
        assert progress_calls[0] == (50, 2, 5)
        assert progress_calls[1] == (100, 5, 5)

        # Verify extraction completed
        assert result.extraction_method == ExtractionMethod.AZURE_DOC_INTEL
