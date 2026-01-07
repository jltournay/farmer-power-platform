"""Scanned PDF detection for routing to OCR extraction.

This module provides detection logic to identify scanned/image-based PDFs
that require OCR (Azure Document Intelligence) vs digital PDFs that can
be extracted with PyMuPDF.

Detection uses TWO signals:
1. Low text content: avg chars/page < 150 (confidence < 0.3)
2. Full-page image: image covers > 80% of page area on >50% of pages

Either signal triggers scanned classification.

Story 0.75.10c: Azure Document Intelligence Integration
"""

import contextlib
from dataclasses import dataclass, field

import pymupdf
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ScanDetectionResult:
    """Result of scanned PDF detection.

    Attributes:
        is_scanned: True if PDF appears to be scanned/image-based.
        reason: Human-readable explanation of detection decision.
        confidence: Text extraction confidence (0.0-1.0).
        detection_signals: List of signals that triggered scanned classification.
    """

    is_scanned: bool
    reason: str
    confidence: float
    detection_signals: list[str] = field(default_factory=list)


def detect_scanned_pdf(content: bytes) -> ScanDetectionResult:
    """Detect if PDF is scanned/image-based using multiple signals.

    Uses two detection signals that catch different types of scanned PDFs:
    - Signal 1: Low text content (< 150 chars/page average)
    - Signal 2: Full-page image (> 80% of page area, on >50% of pages)

    Either signal triggers scanned classification. This dual approach
    catches both "true" scanned PDFs (no text layer) and OCR'd scanned
    PDFs (have text layer but are image-based).

    Args:
        content: PDF file content as bytes.

    Returns:
        ScanDetectionResult with detection decision and reasoning.

    Example:
        detection = detect_scanned_pdf(pdf_bytes)
        if detection.is_scanned:
            # Route to Azure Document Intelligence
            result = await azure_di_client.analyze_pdf(pdf_bytes)
        else:
            # Use PyMuPDF text extraction
            result = await extractor._extract_pdf(pdf_bytes)
    """
    try:
        doc = pymupdf.open(stream=content, filetype="pdf")
    except Exception as e:
        # If we can't open the PDF, assume not scanned (let extractor handle error)
        logger.warning("Failed to open PDF for scan detection", error=str(e))
        return ScanDetectionResult(
            is_scanned=False,
            reason=f"Could not open PDF for detection: {e}",
            confidence=0.0,
            detection_signals=[],
        )

    try:
        total_pages = len(doc)
        if total_pages == 0:
            doc.close()
            return ScanDetectionResult(
                is_scanned=False,
                reason="Empty PDF (0 pages)",
                confidence=0.0,
                detection_signals=[],
            )

        signals_triggered: list[str] = []

        # Counters for analysis
        total_chars = 0
        pages_with_fullpage_image = 0

        for page in doc:
            # Signal 1: Count text content
            text = page.get_text()
            total_chars += len(text.strip())

            # Signal 2: Check for full-page image
            images = page.get_images()
            if images:
                # Check if any image covers most of the page
                page_area = page.rect.width * page.rect.height
                if page_area > 0:
                    for img_info in images:
                        try:
                            # img_info is a tuple, we need xref for bbox
                            img_rect = page.get_image_bbox(img_info)
                            if img_rect:
                                img_area = img_rect.width * img_rect.height
                                if (img_area / page_area) > 0.8:
                                    pages_with_fullpage_image += 1
                                    break  # Only count once per page
                        except Exception:
                            # Some images may not have valid bbox
                            pass

        doc.close()

        # Calculate confidence from text content
        # 500+ chars/page on average = 1.0 confidence (text-rich PDF)
        avg_chars_per_page = total_chars / max(total_pages, 1)
        confidence = min(1.0, avg_chars_per_page / 500)

        # Check Signal 1: Low text content (confidence < 0.3)
        if confidence < 0.3:
            signals_triggered.append(f"low_text_content (avg {avg_chars_per_page:.0f} chars/page)")

        # Check Signal 2: Majority of pages are full-page images
        fullpage_image_ratio = pages_with_fullpage_image / max(total_pages, 1)
        if fullpage_image_ratio > 0.5:  # >50% pages are full-page images
            signals_triggered.append(f"fullpage_images ({pages_with_fullpage_image}/{total_pages} pages)")

        # Scanned if ANY signal triggered
        is_scanned = len(signals_triggered) > 0

        if is_scanned:
            reason = f"Scanned PDF detected: {', '.join(signals_triggered)}"
        else:
            reason = f"Digital PDF (confidence: {confidence:.2f}, no full-page images)"

        logger.debug(
            "PDF scan detection complete",
            is_scanned=is_scanned,
            reason=reason,
            confidence=confidence,
            total_pages=total_pages,
            total_chars=total_chars,
            avg_chars_per_page=avg_chars_per_page,
            fullpage_image_pages=pages_with_fullpage_image,
            signals=signals_triggered,
        )

        return ScanDetectionResult(
            is_scanned=is_scanned,
            reason=reason,
            confidence=confidence,
            detection_signals=signals_triggered,
        )

    except Exception as e:
        logger.warning("Error during scan detection", error=str(e))
        # On error, assume not scanned (conservative approach)
        with contextlib.suppress(Exception):
            doc.close()
        return ScanDetectionResult(
            is_scanned=False,
            reason=f"Detection error: {e}",
            confidence=0.0,
            detection_signals=[],
        )
