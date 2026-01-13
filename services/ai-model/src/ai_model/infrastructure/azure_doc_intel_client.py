"""Azure Document Intelligence client for OCR extraction.

This module provides async integration with Azure Document Intelligence
for extracting text from scanned/image-based PDFs using OCR.

Story 0.75.10c: Azure Document Intelligence Integration
Story 13.7: Refactored to publish costs via DAPR instead of persisting locally (ADR-016)
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

import structlog
from ai_model.config import Settings
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import (
    AnalyzeDocumentRequest,
    AnalyzeResult,
    DocumentParagraph,
    DocumentTable,
)
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ServiceRequestError,
)
from dapr.aio.clients import DaprClient
from fp_common.events.cost_recorded import CostRecordedEvent, CostType, CostUnit
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)


class AzureDocIntelError(Exception):
    """Base exception for Azure Document Intelligence errors."""

    pass


class AzureDocIntelAuthError(AzureDocIntelError):
    """Raised when Azure DI authentication fails (invalid credentials)."""

    pass


class AzureDocIntelRateLimitError(AzureDocIntelError):
    """Raised when Azure DI rate limit is exceeded (429)."""

    pass


class AzureDocIntelUnavailableError(AzureDocIntelError):
    """Raised when Azure DI service is unavailable (5xx)."""

    pass


class AzureDocIntelTimeoutError(AzureDocIntelError):
    """Raised when Azure DI operation times out."""

    pass


class AzureDocIntelDocumentError(AzureDocIntelError):
    """Raised when document is invalid (too large, corrupted, etc.)."""

    pass


@dataclass
class DocumentAnalysisResult:
    """Result of Azure Document Intelligence analysis.

    Attributes:
        markdown_content: Extracted text in Markdown format.
        page_count: Number of pages analyzed.
        confidence: Average confidence score (0.0-1.0).
        paragraphs_count: Number of paragraphs extracted.
        tables_count: Number of tables extracted.
    """

    markdown_content: str
    page_count: int
    confidence: float
    paragraphs_count: int
    tables_count: int


@dataclass
class AzureDocIntelCostEvent:
    """Cost tracking event for Azure DI operations.

    Used for operational visibility and cost monitoring.
    """

    timestamp: datetime
    document_id: str
    job_id: str
    page_count: int
    estimated_cost_usd: Decimal
    model_id: str
    success: bool
    error_message: str | None = None


# Type alias for progress callback
ProgressCallback = Callable[[int, int, int], None]  # (percent, pages_processed, total_pages)


class AzureDocumentIntelligenceClient:
    """Async wrapper for Azure Document Intelligence SDK.

    Provides OCR extraction for scanned/image-based PDFs with:
    - Async operation polling with progress callback
    - Markdown conversion from layout analysis results
    - Retry logic for transient errors (rate limits, service unavailable)
    - Cost publishing via DAPR (Story 13.7, ADR-016)

    Usage:
        client = AzureDocumentIntelligenceClient(settings)
        result = await client.analyze_pdf(content, progress_callback)
    """

    def __init__(
        self,
        settings: Settings,
        dapr_client: DaprClient | None = None,
        pubsub_name: str = "pubsub",
        cost_topic: str = "platform.cost.recorded",
    ) -> None:
        """Initialize the Azure Document Intelligence client.

        Args:
            settings: Application settings with Azure DI configuration.
            dapr_client: DAPR client for publishing cost events (Story 13.7, ADR-016).
            pubsub_name: DAPR pub/sub component name (default: "pubsub").
            cost_topic: Topic for cost events (default: "platform.cost.recorded").

        Raises:
            ValueError: If Azure DI is not properly configured.
        """
        if not settings.azure_doc_intel_enabled:
            raise ValueError(
                "Azure Document Intelligence not configured. Set azure_doc_intel_endpoint and azure_doc_intel_key."
            )

        self._settings = settings
        self._endpoint = settings.azure_doc_intel_endpoint
        self._model_id = settings.azure_doc_intel_model
        self._timeout = settings.azure_doc_intel_timeout
        self._cost_per_page = Decimal(str(settings.azure_doc_intel_cost_per_page))
        self._dapr_client = dapr_client
        self._pubsub_name = pubsub_name
        self._cost_topic = cost_topic

        # Create the sync client (SDK is synchronous)
        # We'll wrap calls in run_in_executor for async operation
        self._client = DocumentIntelligenceClient(
            endpoint=self._endpoint,
            credential=AzureKeyCredential(settings.azure_doc_intel_key.get_secret_value()),
        )

        logger.info(
            "Azure Document Intelligence client initialized",
            endpoint=self._endpoint,
            model_id=self._model_id,
            timeout=self._timeout,
            cost_publishing_enabled=dapr_client is not None,
        )

    @retry(
        retry=retry_if_exception_type(AzureDocIntelRateLimitError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def analyze_pdf(
        self,
        content: bytes,
        progress_callback: ProgressCallback | None = None,
        document_id: str = "",
        job_id: str = "",
    ) -> DocumentAnalysisResult:
        """Analyze a PDF document using Azure Document Intelligence.

        Starts an async analysis operation, polls for completion, and
        converts results to Markdown format.

        Args:
            content: PDF file content as bytes.
            progress_callback: Optional callback for progress updates.
                               Called with (percent, pages_processed, total_pages).
            document_id: Optional document ID for cost tracking.
            job_id: Optional job ID for cost tracking.

        Returns:
            DocumentAnalysisResult with extracted content and metadata.

        Raises:
            AzureDocIntelAuthError: If authentication fails.
            AzureDocIntelRateLimitError: If rate limited (triggers retry).
            AzureDocIntelUnavailableError: If service is unavailable.
            AzureDocIntelTimeoutError: If operation times out.
            AzureDocIntelDocumentError: If document is invalid.
            AzureDocIntelError: For other failures.
        """
        # Validate document size (Azure DI limit: 500 pages, 500 MB)
        if len(content) > 500 * 1024 * 1024:  # 500 MB
            raise AzureDocIntelDocumentError(f"Document too large: {len(content)} bytes (max 500 MB)")

        loop = asyncio.get_event_loop()

        try:
            # Start analysis in executor (SDK is synchronous)
            logger.info(
                "Starting Azure DI analysis",
                content_size=len(content),
                model_id=self._model_id,
            )

            # Create request with document bytes
            request = AnalyzeDocumentRequest(bytes_source=content)

            # Run synchronous begin_analyze_document in thread pool
            poller = await loop.run_in_executor(
                None,
                lambda: self._client.begin_analyze_document(
                    model_id=self._model_id,
                    analyze_request=request,
                    content_type="application/octet-stream",
                ),
            )

            # Poll for completion with timeout
            start_time = datetime.now(UTC)
            poll_interval = 1.0  # Start with 1 second polls

            while True:
                # Check timeout
                elapsed = (datetime.now(UTC) - start_time).total_seconds()
                if elapsed > self._timeout:
                    raise AzureDocIntelTimeoutError(f"Azure DI operation timed out after {self._timeout}s")

                # Check if done (run in executor since SDK is sync)
                is_done = await loop.run_in_executor(None, poller.done)

                if is_done:
                    break

                # Report intermediate progress (Azure doesn't give page-level progress)
                if progress_callback:
                    try:
                        # Estimate progress based on elapsed time (rough approximation)
                        estimated_percent = min(90, int(elapsed / self._timeout * 100))
                        progress_callback(estimated_percent, 0, 0)
                    except Exception as e:
                        logger.warning("Progress callback failed", error=str(e))

                # Wait before next poll
                await asyncio.sleep(poll_interval)
                # Increase poll interval (exponential backoff up to 5s)
                poll_interval = min(5.0, poll_interval * 1.5)

            # Get result (run in executor)
            result: AnalyzeResult = await loop.run_in_executor(None, poller.result)

            # Convert result to markdown
            markdown_content = self._convert_to_markdown(result)
            page_count = len(result.pages) if result.pages else 0

            # Calculate average confidence from paragraphs
            confidence = self._calculate_confidence(result)

            # Count extracted elements
            paragraphs_count = len(result.paragraphs) if result.paragraphs else 0
            tables_count = len(result.tables) if result.tables else 0

            # Story 13.7 (ADR-016): Publish cost event to platform-cost via DAPR
            estimated_cost_usd = self._cost_per_page * page_count
            await self._publish_cost_event(
                page_count=page_count,
                estimated_cost_usd=estimated_cost_usd,
                document_id=document_id,
                job_id=job_id,
                success=True,
            )

            logger.info(
                "Azure DI analysis cost published",
                document_id=document_id,
                job_id=job_id,
                page_count=page_count,
                estimated_cost_usd=str(estimated_cost_usd),
                model_id=self._model_id,
            )

            # Final progress callback
            if progress_callback:
                try:
                    progress_callback(100, page_count, page_count)
                except Exception as e:
                    logger.warning("Final progress callback failed", error=str(e))

            logger.info(
                "Azure DI analysis complete",
                page_count=page_count,
                paragraphs=paragraphs_count,
                tables=tables_count,
                confidence=confidence,
                elapsed_seconds=elapsed,
            )

            return DocumentAnalysisResult(
                markdown_content=markdown_content,
                page_count=page_count,
                confidence=confidence,
                paragraphs_count=paragraphs_count,
                tables_count=tables_count,
            )

        except ClientAuthenticationError as e:
            logger.error("Azure DI authentication failed", error=str(e))
            raise AzureDocIntelAuthError(f"Authentication failed: {e}")

        except HttpResponseError as e:
            if e.status_code == 429:
                logger.warning("Azure DI rate limited, will retry", error=str(e))
                raise AzureDocIntelRateLimitError(f"Rate limited: {e}")
            elif e.status_code and e.status_code >= 500:
                logger.error("Azure DI service error", status=e.status_code, error=str(e))
                raise AzureDocIntelUnavailableError(f"Service unavailable: {e}")
            elif e.status_code == 400:
                logger.error("Azure DI invalid document", error=str(e))
                raise AzureDocIntelDocumentError(f"Invalid document: {e}")
            else:
                logger.error("Azure DI HTTP error", status=e.status_code, error=str(e))
                raise AzureDocIntelError(f"HTTP error {e.status_code}: {e}")

        except ServiceRequestError as e:
            logger.error("Azure DI network error", error=str(e))
            raise AzureDocIntelUnavailableError(f"Network error: {e}")

        except AzureDocIntelError:
            # Re-raise our custom errors
            raise

        except Exception as e:
            logger.exception("Unexpected Azure DI error")
            raise AzureDocIntelError(f"Unexpected error: {e}")

    def _convert_to_markdown(self, result: AnalyzeResult) -> str:
        """Convert Azure Document Intelligence result to Markdown format.

        Processes paragraphs with their roles (title, sectionHeading, etc.)
        and tables to produce well-structured Markdown.

        Args:
            result: Azure DI analysis result.

        Returns:
            Markdown-formatted string.
        """
        sections: list[str] = []

        # Process paragraphs
        if result.paragraphs:
            for paragraph in result.paragraphs:
                md_text = self._paragraph_to_markdown(paragraph)
                if md_text:
                    sections.append(md_text)

        # Process tables
        if result.tables:
            for table in result.tables:
                md_table = self._table_to_markdown(table)
                if md_table:
                    sections.append(md_table)

        return "\n\n".join(sections)

    def _paragraph_to_markdown(self, paragraph: DocumentParagraph) -> str:
        """Convert a single paragraph to Markdown based on its role.

        Args:
            paragraph: Azure DI paragraph object.

        Returns:
            Markdown-formatted paragraph string.
        """
        content = paragraph.content.strip()
        if not content:
            return ""

        role = paragraph.role if hasattr(paragraph, "role") and paragraph.role else None

        # Map Azure DI roles to Markdown formatting
        role_formats = {
            "title": f"# {content}",
            "sectionHeading": f"## {content}",
            "pageHeader": "",  # Skip page headers (usually document title repeated)
            "pageFooter": "",  # Skip page footers (usually page numbers)
            "footnote": f"*{content}*",
        }

        return role_formats.get(role, content) if role else content

    def _table_to_markdown(self, table: DocumentTable) -> str:
        """Convert Azure DI table to Markdown table format.

        Args:
            table: Azure DI table object.

        Returns:
            Markdown-formatted table string.
        """
        if not table.cells:
            return ""

        # Organize cells by row
        rows: dict[int, dict[int, str]] = {}
        for cell in table.cells:
            row_idx = cell.row_index
            col_idx = cell.column_index
            if row_idx not in rows:
                rows[row_idx] = {}
            rows[row_idx][col_idx] = cell.content.strip() if cell.content else ""

        if not rows:
            return ""

        # Build markdown table
        column_count = (
            table.column_count
            if hasattr(table, "column_count")
            else max(max(cols.keys()) + 1 for cols in rows.values())
        )

        md_rows: list[str] = []

        for row_idx in sorted(rows.keys()):
            row = rows[row_idx]
            # Get cells for this row, filling empty cells
            cells = [row.get(col, "") for col in range(column_count)]
            # Escape pipe characters in cell content
            cells = [c.replace("|", "\\|") for c in cells]
            md_rows.append("| " + " | ".join(cells) + " |")

            # Add separator row after header (first row)
            if row_idx == 0:
                md_rows.append("|" + "---|" * column_count)

        return "\n".join(md_rows)

    def _calculate_confidence(self, result: AnalyzeResult) -> float:
        """Calculate average confidence score from analysis result.

        Args:
            result: Azure DI analysis result.

        Returns:
            Average confidence score (0.0-1.0), or 0.9 if not available.
        """
        confidences: list[float] = []

        # Collect confidence from paragraphs
        if result.paragraphs:
            for paragraph in result.paragraphs:
                if hasattr(paragraph, "confidence") and paragraph.confidence is not None:
                    confidences.append(paragraph.confidence)

        if confidences:
            return sum(confidences) / len(confidences)

        # Default high confidence for Azure DI results
        return 0.9

    async def _publish_cost_event(
        self,
        page_count: int,
        estimated_cost_usd: Decimal,
        document_id: str,
        job_id: str,
        success: bool,
        error_message: str | None = None,
    ) -> None:
        """Publish document processing cost event to platform-cost service via DAPR (Story 13.7, ADR-016).

        Cost publishing is best-effort - failures are logged but do not fail the
        primary document processing operation.

        Args:
            page_count: Number of pages processed.
            estimated_cost_usd: Estimated cost in USD.
            document_id: Document identifier.
            job_id: Job identifier.
            success: Whether the operation succeeded.
            error_message: Optional error message if operation failed.
        """
        if self._dapr_client is None:
            logger.debug("DAPR client not configured, skipping cost event")
            return

        try:
            event = CostRecordedEvent(
                cost_type=CostType.DOCUMENT,
                amount_usd=estimated_cost_usd,
                quantity=page_count,
                unit=CostUnit.PAGES,
                timestamp=datetime.now(UTC),
                source_service="ai-model",
                success=success,
                metadata={
                    "model_id": self._model_id,
                    "document_id": document_id,
                    "job_id": job_id,
                    "error_message": error_message,
                },
            )

            await self._dapr_client.publish_event(
                pubsub_name=self._pubsub_name,
                topic_name=self._cost_topic,
                data=event.model_dump_json(),
                data_content_type="application/json",
            )

            logger.debug(
                "Published document processing cost event",
                cost_usd=str(estimated_cost_usd),
                page_count=page_count,
                document_id=document_id,
            )

        except Exception as e:
            # Best-effort publishing - log warning but don't fail the document operation
            logger.warning(
                "Failed to publish document processing cost event",
                error=str(e),
                document_id=document_id,
            )
