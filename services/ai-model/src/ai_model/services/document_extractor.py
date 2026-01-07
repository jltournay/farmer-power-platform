"""Document content extraction service for RAG documents.

This module provides extraction logic for PDF, Markdown, and plain text files.
PDF extraction uses PyMuPDF (synchronous library) wrapped in async via thread pool.
For scanned/image-based PDFs, Azure Document Intelligence OCR is used when available.

Story 0.75.10b: Basic PDF/Markdown Extraction
Story 0.75.10c: Azure Document Intelligence Integration
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pymupdf
import structlog
from ai_model.config import Settings, settings
from ai_model.domain.rag_document import ExtractionMethod, FileType
from ai_model.services.scan_detection import detect_scanned_pdf

if TYPE_CHECKING:
    from ai_model.infrastructure.azure_doc_intel_client import (
        AzureDocumentIntelligenceClient,
    )

logger = structlog.get_logger(__name__)

# Thread pool for running synchronous PyMuPDF operations
_executor = ThreadPoolExecutor(max_workers=settings.extraction_max_workers)


class ExtractionError(Exception):
    """Base exception for extraction failures."""

    pass


class PasswordProtectedError(ExtractionError):
    """Raised when a PDF is password-protected."""

    pass


class CorruptedFileError(ExtractionError):
    """Raised when a file cannot be parsed."""

    pass


@dataclass
class ExtractionResult:
    """Result of document extraction.

    Attributes:
        content: Extracted text content (Markdown format).
        page_count: Number of pages extracted (1 for non-PDF files).
        extraction_method: Method used for extraction.
        confidence: Quality score 0.0-1.0 based on content density.
        warnings: List of warning messages (e.g., fallback scenarios).
    """

    content: str
    page_count: int
    extraction_method: ExtractionMethod
    confidence: float
    warnings: list[str] = field(default_factory=list)


# Type alias for progress callback
ProgressCallback = Callable[[int, int, int], None]  # (percent, pages_done, total_pages)


class DocumentExtractor:
    """Extracts text content from uploaded files for RAG ingestion.

    Supports:
    - PDF files (digital/text-based via PyMuPDF)
    - PDF files (scanned/image-based via Azure Document Intelligence)
    - Markdown files (pass-through with structure preservation)
    - Plain text files (simple extraction)

    Scanned PDF Detection (Story 0.75.10c):
    - Digital PDFs (text-rich) use PyMuPDF for fast, free extraction
    - Scanned PDFs are detected via dual-signal detection:
      - Signal 1: Low text content (< 150 chars/page avg)
      - Signal 2: Full-page image (> 80% of page area, >50% of pages)
    - Scanned PDFs route to Azure Document Intelligence if configured
    - Falls back to PyMuPDF with warning if Azure DI unavailable

    Usage:
        # Basic usage (no Azure DI)
        extractor = DocumentExtractor()
        file_type = extractor.detect_file_type("guide.pdf", content)
        result = await extractor.extract(content, file_type)

        # With Azure DI for scanned PDFs
        extractor = DocumentExtractor(
            azure_di_client=AzureDocumentIntelligenceClient(settings),
            settings=settings,
        )
        result = await extractor.extract(content, file_type)
    """

    def __init__(
        self,
        azure_di_client: AzureDocumentIntelligenceClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Initialize the document extractor.

        Args:
            azure_di_client: Optional Azure DI client for OCR extraction.
                            If None, scanned PDFs fall back to PyMuPDF.
            settings: Optional settings instance. Uses global settings if None.
        """
        self._azure_di_client = azure_di_client
        self._settings = settings or Settings()

    def detect_file_type(self, filename: str, content: bytes) -> FileType:
        """Detect file type from extension and magic bytes.

        Uses magic bytes for reliable detection, with extension fallback.

        Args:
            filename: Original filename for extension-based detection.
            content: File content bytes for magic byte detection.

        Returns:
            Detected FileType enum value.
        """
        # Check PDF magic bytes: %PDF
        if len(content) >= 4 and content[:4] == b"%PDF":
            return FileType.PDF

        # Extension-based fallback
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

        type_map = {
            "pdf": FileType.PDF,
            "md": FileType.MD,
            "markdown": FileType.MD,
            "txt": FileType.TXT,
            "text": FileType.TXT,
        }

        return type_map.get(ext, FileType.TXT)

    async def extract(
        self,
        content: bytes,
        file_type: FileType,
        progress_callback: ProgressCallback | None = None,
        document_id: str = "",
        job_id: str = "",
    ) -> ExtractionResult:
        """Extract text content from file bytes.

        Args:
            content: Raw file content as bytes.
            file_type: Type of file being extracted.
            progress_callback: Optional callback for progress updates.
                              Called with (percent, pages_done, total_pages).
            document_id: Optional document ID for cost tracking (Azure DI).
            job_id: Optional job ID for cost tracking (Azure DI).

        Returns:
            ExtractionResult with extracted content and metadata.

        Raises:
            PasswordProtectedError: If PDF is password-protected.
            CorruptedFileError: If file cannot be parsed.
            ExtractionError: For other extraction failures.
        """
        if file_type == FileType.PDF:
            return await self._extract_pdf(content, progress_callback, document_id, job_id)
        elif file_type == FileType.MD:
            return self._extract_markdown(content)
        else:
            return self._extract_text(content)

    async def _extract_pdf(
        self,
        content: bytes,
        progress_callback: ProgressCallback | None = None,
        document_id: str = "",
        job_id: str = "",
    ) -> ExtractionResult:
        """Extract text from PDF using appropriate method.

        For digital PDFs (text-rich): Uses PyMuPDF (fast, free).
        For scanned PDFs (image-based): Routes to Azure DI if available.

        Scanned PDF detection uses dual signals:
        - Signal 1: Low text content (< 150 chars/page avg)
        - Signal 2: Full-page image (> 80% of page area, >50% of pages)

        Args:
            content: PDF file content as bytes.
            progress_callback: Optional callback for progress updates.
            document_id: Optional document ID for cost tracking.
            job_id: Optional job ID for cost tracking.

        Returns:
            ExtractionResult with extracted markdown content.

        Raises:
            PasswordProtectedError: If PDF requires password.
            CorruptedFileError: If PDF cannot be opened/parsed.
        """
        # Step 1: Detect if PDF is scanned (dual-signal detection)
        detection = detect_scanned_pdf(content)
        logger.info(
            "PDF scan detection complete",
            is_scanned=detection.is_scanned,
            reason=detection.reason,
            confidence=detection.confidence,
            signals=detection.detection_signals,
        )

        # Step 2: Digital PDF - use PyMuPDF only
        if not detection.is_scanned:
            return await self._extract_pdf_with_pymupdf(content, progress_callback)

        # Step 3: Scanned PDF - try Azure DI if available
        if not self._is_azure_di_available():
            # Azure DI not configured - fallback to PyMuPDF with warning
            logger.warning(
                "Azure DI not available for scanned PDF",
                reason=detection.reason,
            )
            result = await self._extract_pdf_with_pymupdf(content, progress_callback)
            result.warnings.append(f"{detection.reason}, but Azure DI not configured - extraction quality may be poor")
            return result

        # Step 4: Call Azure DI for OCR
        try:
            azure_result = await self._azure_di_client.analyze_pdf(
                content=content,
                progress_callback=progress_callback,
                document_id=document_id,
                job_id=job_id,
            )
            return ExtractionResult(
                content=azure_result.markdown_content,
                page_count=azure_result.page_count,
                extraction_method=ExtractionMethod.AZURE_DOC_INTEL,
                confidence=azure_result.confidence,
            )
        except Exception as e:
            # Azure DI failed - fallback to PyMuPDF result
            logger.error(
                "Azure DI failed, falling back to PyMuPDF",
                error=str(e),
            )
            result = await self._extract_pdf_with_pymupdf(content, progress_callback)
            result.warnings.append(f"Azure DI failed: {e}, using PyMuPDF fallback")
            return result

    def _is_azure_di_available(self) -> bool:
        """Check if Azure DI is configured and client is available.

        Returns:
            True if Azure DI client is provided and settings enable it.
        """
        return self._azure_di_client is not None and self._settings.azure_doc_intel_enabled

    async def _extract_pdf_with_pymupdf(
        self,
        content: bytes,
        progress_callback: ProgressCallback | None = None,
    ) -> ExtractionResult:
        """Extract text from PDF using PyMuPDF in thread pool.

        Runs synchronous PyMuPDF operations in executor to avoid blocking.
        Logs progress at 10% intervals for observability.

        Args:
            content: PDF file content as bytes.
            progress_callback: Optional callback for progress updates.

        Returns:
            ExtractionResult with extracted markdown content.

        Raises:
            PasswordProtectedError: If PDF requires password.
            CorruptedFileError: If PDF cannot be opened/parsed.
        """
        loop = asyncio.get_event_loop()

        def _sync_extract() -> tuple[str, int, float]:
            """Synchronous PDF extraction run in thread pool."""
            try:
                doc = pymupdf.open(stream=content, filetype="pdf")
            except Exception as e:
                error_msg = str(e).lower()
                if "password" in error_msg or "encrypted" in error_msg:
                    raise PasswordProtectedError("PDF is password-protected")
                raise CorruptedFileError(f"Failed to parse PDF: {e}")

            try:
                total_pages = len(doc)
                if total_pages == 0:
                    doc.close()
                    return "", 0, 0.0

                full_text: list[str] = []
                last_logged_percent = 0

                for page_num, page in enumerate(doc):
                    # Extract text from page
                    text = page.get_text("text")
                    if text.strip():
                        full_text.append(text)

                    # Calculate progress
                    progress = int((page_num + 1) / total_pages * 100)

                    # Log at 10% intervals
                    if progress >= last_logged_percent + 10:
                        logger.info(
                            "PDF extraction progress",
                            page=page_num + 1,
                            total=total_pages,
                            percent=progress,
                        )
                        last_logged_percent = (progress // 10) * 10

                        # Call progress callback if provided
                        if progress_callback:
                            try:
                                progress_callback(progress, page_num + 1, total_pages)
                            except Exception as cb_err:
                                logger.warning(
                                    "Progress callback failed",
                                    error=str(cb_err),
                                )

                doc.close()

                # Join pages with double newlines for paragraph separation
                content_str = "\n\n".join(full_text)

                # Calculate confidence based on text density
                # 500+ chars per page on average = 1.0 confidence (text-rich PDF)
                avg_chars_per_page = len(content_str) / max(total_pages, 1)
                confidence = min(1.0, avg_chars_per_page / 500)

                # Low confidence suggests scanned/image PDF
                if confidence < 0.3:
                    logger.warning(
                        "Low confidence extraction - may be scanned PDF",
                        avg_chars_per_page=avg_chars_per_page,
                        confidence=confidence,
                        recommendation="Consider Azure Document Intelligence for OCR",
                    )

                return content_str, total_pages, confidence

            except Exception as e:
                doc.close()
                if isinstance(e, (PasswordProtectedError, CorruptedFileError)):
                    raise
                # Check if error indicates password protection
                error_msg = str(e).lower()
                if "password" in error_msg or "encrypted" in error_msg:
                    raise PasswordProtectedError("PDF is password-protected")
                raise CorruptedFileError(f"Error during PDF extraction: {e}")

        text, page_count, confidence = await loop.run_in_executor(_executor, _sync_extract)

        return ExtractionResult(
            content=text,
            page_count=page_count,
            extraction_method=ExtractionMethod.TEXT_EXTRACTION,
            confidence=confidence,
        )

    def _extract_markdown(self, content: bytes) -> ExtractionResult:
        """Parse Markdown file preserving structure.

        Markdown files are already in the target format, so we simply
        decode and return with high confidence.

        Args:
            content: Markdown file content as bytes.

        Returns:
            ExtractionResult with markdown content.
        """
        try:
            text = content.decode("utf-8", errors="replace")
        except Exception as e:
            raise CorruptedFileError(f"Failed to decode Markdown file: {e}")

        # Count word density for sanity check
        word_count = len(text.split())

        logger.debug(
            "Markdown extraction complete",
            word_count=word_count,
            char_count=len(text),
        )

        return ExtractionResult(
            content=text,
            page_count=1,
            extraction_method=ExtractionMethod.MANUAL,  # Markdown is essentially manual input
            confidence=1.0,  # Markdown is already in target format
        )

    def _extract_text(self, content: bytes) -> ExtractionResult:
        """Parse plain text file.

        Args:
            content: Plain text file content as bytes.

        Returns:
            ExtractionResult with text content.
        """
        try:
            text = content.decode("utf-8", errors="replace")
        except Exception as e:
            raise CorruptedFileError(f"Failed to decode text file: {e}")

        logger.debug(
            "Text extraction complete",
            char_count=len(text),
        )

        return ExtractionResult(
            content=text,
            page_count=1,
            extraction_method=ExtractionMethod.MANUAL,
            confidence=1.0,  # Plain text has no ambiguity
        )
