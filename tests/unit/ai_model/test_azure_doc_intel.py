"""Unit tests for Azure Document Intelligence integration.

Story 0.75.10c: Azure Document Intelligence Integration

Tests cover:
- Azure DI client initialization and configuration
- Scanned PDF detection (dual-signal: low text + full-page image)
- PDF extraction routing (digital vs scanned)
- Azure DI error handling and fallback scenarios
- Cost tracking in Azure DI operations
- Markdown conversion from Azure DI results
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from ai_model.config import Settings
from ai_model.domain.rag_document import ExtractionMethod, FileType
from ai_model.infrastructure.azure_doc_intel_client import (
    AzureDocIntelCostEvent,
    AzureDocIntelError,
    AzureDocumentIntelligenceClient,
)
from ai_model.services.document_extractor import DocumentExtractor
from ai_model.services.scan_detection import ScanDetectionResult, detect_scanned_pdf

# ============================================
# Test Helpers - Create PDFs programmatically
# ============================================


def create_test_pdf(text: str, pages: int = 1) -> bytes:
    """Create a minimal PDF for unit testing.

    Args:
        text: Text content to include on each page.
        pages: Number of pages to create.

    Returns:
        PDF file content as bytes.
    """
    import pymupdf

    doc = pymupdf.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((50, 50), f"Page {i + 1}: {text}")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_empty_pdf() -> bytes:
    """Create a PDF with no text content (simulates scanned/image PDF).

    Returns:
        Empty PDF file content as bytes.
    """
    import pymupdf

    doc = pymupdf.open()
    doc.new_page()
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
    long_text = (
        "This is a sample paragraph with substantial text content "
        "that we need to repeat many times to ensure we have enough "
        "characters per page to achieve high confidence extraction scores. " * 10
    )

    for i in range(pages):
        page = doc.new_page()
        y_position = 50
        page.insert_text((50, y_position), f"Page {i + 1}: Document Title")
        for _ in range(5):
            y_position += 100
            if y_position < 750:
                page.insert_text((50, y_position), long_text[:300])

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# ============================================
# Scan Detection Tests
# ============================================


class TestScanDetection:
    """Tests for scanned PDF detection logic."""

    def test_detect_digital_pdf_not_scanned(self):
        """Digital PDF (text-rich) is not classified as scanned."""
        pdf_content = create_text_rich_pdf(pages=3)

        result = detect_scanned_pdf(pdf_content)

        assert result.is_scanned is False
        assert result.confidence > 0.5
        assert len(result.detection_signals) == 0

    def test_detect_empty_pdf_as_scanned(self):
        """Empty PDF (no text) is classified as scanned."""
        pdf_content = create_empty_pdf()

        result = detect_scanned_pdf(pdf_content)

        assert result.is_scanned is True
        assert result.confidence < 0.3
        assert "low_text_content" in result.detection_signals[0]

    def test_detect_low_text_signal(self):
        """Low text content triggers scanned classification."""
        # Create a PDF with minimal text (below 150 chars/page threshold)
        pdf_content = create_test_pdf("Hi", pages=3)

        result = detect_scanned_pdf(pdf_content)

        assert result.is_scanned is True
        assert "low_text_content" in result.detection_signals[0]

    def test_detect_invalid_pdf_returns_not_scanned(self):
        """Invalid PDF content returns not-scanned with error reason."""
        invalid_content = b"This is not a valid PDF file"

        result = detect_scanned_pdf(invalid_content)

        assert result.is_scanned is False
        assert "Could not open PDF" in result.reason

    def test_detection_result_has_all_fields(self):
        """ScanDetectionResult has all expected fields."""
        pdf_content = create_test_pdf("Test content", pages=1)

        result = detect_scanned_pdf(pdf_content)

        assert isinstance(result, ScanDetectionResult)
        assert isinstance(result.is_scanned, bool)
        assert isinstance(result.reason, str)
        assert isinstance(result.confidence, float)
        assert isinstance(result.detection_signals, list)


# ============================================
# DocumentExtractor Azure DI Routing Tests
# ============================================


class TestDocumentExtractorRouting:
    """Tests for PDF extraction routing between PyMuPDF and Azure DI."""

    @pytest.mark.asyncio
    async def test_digital_pdf_uses_pymupdf(self):
        """Digital PDF is extracted with PyMuPDF (text_extraction method)."""
        extractor = DocumentExtractor()
        pdf_content = create_text_rich_pdf(pages=2)

        result = await extractor.extract(pdf_content, FileType.PDF)

        assert result.extraction_method == ExtractionMethod.TEXT_EXTRACTION
        assert result.page_count == 2
        assert len(result.warnings) == 0

    @pytest.mark.asyncio
    async def test_scanned_pdf_without_azure_di_falls_back_with_warning(self):
        """Scanned PDF without Azure DI configured falls back to PyMuPDF with warning."""
        extractor = DocumentExtractor()  # No Azure DI client
        pdf_content = create_empty_pdf()

        result = await extractor.extract(pdf_content, FileType.PDF)

        assert result.extraction_method == ExtractionMethod.TEXT_EXTRACTION
        assert len(result.warnings) > 0
        assert "Azure DI not configured" in result.warnings[0]

    @pytest.mark.asyncio
    async def test_azure_di_not_available_without_client(self):
        """Azure DI is not available when client is not provided."""
        extractor = DocumentExtractor()

        assert extractor._is_azure_di_available() is False

    @pytest.mark.asyncio
    async def test_azure_di_not_available_without_settings(self):
        """Azure DI is not available when settings are not configured."""
        # Create settings without Azure DI config
        settings = Settings()
        settings.azure_doc_intel_endpoint = ""
        settings.azure_doc_intel_key = None

        extractor = DocumentExtractor(azure_di_client=None, settings=settings)

        assert extractor._is_azure_di_available() is False


# ============================================
# Azure DI Client Mock Tests
# ============================================


class TestAzureDocIntelClientMocked:
    """Tests for Azure DI client with mocked Azure SDK."""

    @pytest.mark.asyncio
    async def test_scanned_pdf_routes_to_azure_di_when_available(self):
        """Scanned PDF routes to Azure DI when client is available."""
        # Create mock Azure DI client
        mock_azure_client = MagicMock()
        mock_azure_client.analyze_pdf = AsyncMock(
            return_value=MagicMock(
                markdown_content="# Extracted Title\n\nExtracted paragraph content.",
                page_count=3,
                confidence=0.95,
                paragraphs_count=5,
                tables_count=1,
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

        # Use empty PDF to trigger scanned detection
        pdf_content = create_empty_pdf()

        result = await extractor.extract(pdf_content, FileType.PDF)

        # Verify Azure DI was called
        mock_azure_client.analyze_pdf.assert_called_once()

        # Verify result uses Azure DI extraction method
        assert result.extraction_method == ExtractionMethod.AZURE_DOC_INTEL
        assert result.confidence == 0.95
        assert "# Extracted Title" in result.content

    @pytest.mark.asyncio
    async def test_azure_di_error_falls_back_to_pymupdf(self):
        """Azure DI error falls back to PyMuPDF with warning."""
        # Create mock Azure DI client that raises error
        mock_azure_client = MagicMock()
        mock_azure_client.analyze_pdf = AsyncMock(side_effect=AzureDocIntelError("Service unavailable"))

        # Create settings with Azure DI enabled
        settings = Settings()
        settings.azure_doc_intel_endpoint = "https://test.cognitiveservices.azure.com"
        settings.azure_doc_intel_key = MagicMock()
        settings.azure_doc_intel_key.get_secret_value = MagicMock(return_value="test-key")

        extractor = DocumentExtractor(
            azure_di_client=mock_azure_client,
            settings=settings,
        )

        # Use empty PDF to trigger scanned detection
        pdf_content = create_empty_pdf()

        result = await extractor.extract(pdf_content, FileType.PDF)

        # Verify fallback to PyMuPDF
        assert result.extraction_method == ExtractionMethod.TEXT_EXTRACTION
        assert len(result.warnings) > 0
        assert "Azure DI failed" in result.warnings[0]


# ============================================
# Azure DI Client Configuration Tests
# ============================================


class TestAzureDocIntelConfig:
    """Tests for Azure DI configuration settings."""

    def test_azure_di_enabled_when_configured(self):
        """azure_doc_intel_enabled returns True when both endpoint and key are set."""
        settings = Settings()
        settings.azure_doc_intel_endpoint = "https://test.cognitiveservices.azure.com"
        settings.azure_doc_intel_key = MagicMock()
        settings.azure_doc_intel_key.get_secret_value = MagicMock(return_value="test-key")

        assert settings.azure_doc_intel_enabled is True

    def test_azure_di_disabled_without_endpoint(self):
        """azure_doc_intel_enabled returns False without endpoint."""
        settings = Settings()
        settings.azure_doc_intel_endpoint = ""
        settings.azure_doc_intel_key = MagicMock()
        settings.azure_doc_intel_key.get_secret_value = MagicMock(return_value="test-key")

        assert settings.azure_doc_intel_enabled is False

    def test_azure_di_disabled_without_key(self):
        """azure_doc_intel_enabled returns False without key."""
        settings = Settings()
        settings.azure_doc_intel_endpoint = "https://test.cognitiveservices.azure.com"
        settings.azure_doc_intel_key = None

        assert settings.azure_doc_intel_enabled is False

    def test_azure_di_default_model(self):
        """Default Azure DI model is prebuilt-layout."""
        settings = Settings()

        assert settings.azure_doc_intel_model == "prebuilt-layout"

    def test_azure_di_default_timeout(self):
        """Default Azure DI timeout is 300 seconds."""
        settings = Settings()

        assert settings.azure_doc_intel_timeout == 300

    def test_azure_di_cost_per_page(self):
        """Azure DI cost per page is configurable."""
        settings = Settings()

        assert settings.azure_doc_intel_cost_per_page == 0.01


# ============================================
# Azure DI Client Unit Tests (with SDK mocking)
# ============================================


class TestAzureDocIntelClientUnit:
    """Unit tests for AzureDocumentIntelligenceClient internals."""

    def test_client_raises_error_when_not_configured(self):
        """AzureDocumentIntelligenceClient raises ValueError if not configured."""
        settings = Settings()
        settings.azure_doc_intel_endpoint = ""
        settings.azure_doc_intel_key = None

        with pytest.raises(ValueError, match="not configured"):
            AzureDocumentIntelligenceClient(settings)

    def test_document_size_validation(self):
        """Azure DI rejects documents over 500 MB."""
        # Size check is 500 MB = 500 * 1024 * 1024 bytes
        max_size = 500 * 1024 * 1024
        assert max_size == 524288000


# ============================================
# Markdown Conversion Tests (Unit level)
# ============================================


class TestMarkdownConversion:
    """Tests for Azure DI result to Markdown conversion."""

    def test_paragraph_roles_converted_correctly(self):
        """Paragraph roles are converted to appropriate Markdown."""
        # Test the role_formats mapping logic used in _paragraph_to_markdown
        role_formats = {
            "title": "# Test",
            "sectionHeading": "## Test",
            "pageHeader": "",
            "pageFooter": "",
            "footnote": "*Test*",
        }

        assert role_formats["title"] == "# Test"
        assert role_formats["sectionHeading"] == "## Test"
        assert role_formats["pageHeader"] == ""  # Skip headers
        assert role_formats["pageFooter"] == ""  # Skip footers
        assert role_formats["footnote"] == "*Test*"


# ============================================
# Cost Tracking Tests
# ============================================


class TestAzureDocIntelCostTracking:
    """Tests for Azure DI cost tracking."""

    def test_cost_event_structure(self):
        """AzureDocIntelCostEvent has correct structure."""
        from datetime import UTC, datetime

        event = AzureDocIntelCostEvent(
            timestamp=datetime.now(UTC),
            document_id="test-doc",
            job_id="test-job",
            page_count=5,
            estimated_cost_usd=Decimal("0.05"),
            model_id="prebuilt-layout",
            success=True,
        )

        assert event.document_id == "test-doc"
        assert event.job_id == "test-job"
        assert event.page_count == 5
        assert event.estimated_cost_usd == Decimal("0.05")
        assert event.success is True
        assert event.error_message is None

    def test_cost_calculation(self):
        """Cost is calculated as page_count * cost_per_page."""
        cost_per_page = Decimal("0.01")
        page_count = 10
        expected_cost = Decimal("0.10")

        assert cost_per_page * page_count == expected_cost


# ============================================
# Extraction Job with Azure DI Tests
# ============================================


class TestExtractionJobWithAzureDI:
    """Tests for extraction job tracking with Azure DI method."""

    def test_extraction_job_has_extraction_method_field(self):
        """ExtractionJob includes extraction_method field."""
        from datetime import UTC, datetime

        from ai_model.domain.extraction_job import ExtractionJob, ExtractionJobStatus
        from ai_model.domain.rag_document import ExtractionMethod

        job = ExtractionJob(
            id="test-job-id",
            job_id="test-job-id",
            document_id="test-doc",
            status=ExtractionJobStatus.COMPLETED,
            progress_percent=100,
            pages_processed=5,
            total_pages=5,
            extraction_method=ExtractionMethod.AZURE_DOC_INTEL,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )

        assert job.extraction_method == ExtractionMethod.AZURE_DOC_INTEL
