"""Async extraction workflow orchestration for RAG documents.

This module provides the ExtractionWorkflow service that coordinates
async document extraction jobs, tracking progress and updating document
metadata upon completion.

Story 0.75.10b: Basic PDF/Markdown Extraction
"""

import asyncio
import uuid
from datetime import UTC, datetime

import structlog
from ai_model.domain.extraction_job import ExtractionJob, ExtractionJobStatus
from ai_model.domain.rag_document import RagDocument
from ai_model.infrastructure.blob_storage import BlobNotFoundError, BlobStorageClient
from ai_model.infrastructure.repositories import ExtractionJobRepository, RagDocumentRepository
from ai_model.services.document_extractor import (
    CorruptedFileError,
    DocumentExtractor,
    ExtractionError,
    PasswordProtectedError,
)

logger = structlog.get_logger(__name__)


class ExtractionWorkflowError(Exception):
    """Base exception for extraction workflow failures."""

    pass


class DocumentNotFoundError(ExtractionWorkflowError):
    """Raised when the document to extract cannot be found."""

    pass


class NoSourceFileError(ExtractionWorkflowError):
    """Raised when the document has no source file to extract."""

    pass


class ExtractionWorkflow:
    """Orchestrates async document extraction jobs.

    Coordinates between:
    - RagDocumentRepository: Get document and update extraction metadata
    - ExtractionJobRepository: Track job progress
    - BlobStorageClient: Download source files
    - DocumentExtractor: Perform extraction

    Usage:
        workflow = ExtractionWorkflow(doc_repo, job_repo, blob_client, extractor)
        job_id = await workflow.start_extraction(document_id)
        # Job runs in background, query job_repo for status
    """

    def __init__(
        self,
        document_repository: RagDocumentRepository,
        job_repository: ExtractionJobRepository,
        blob_client: BlobStorageClient,
        extractor: DocumentExtractor,
    ) -> None:
        """Initialize the extraction workflow.

        Args:
            document_repository: Repository for RAG documents.
            job_repository: Repository for extraction jobs.
            blob_client: Client for Azure Blob storage.
            extractor: Document content extractor.
        """
        self._doc_repo = document_repository
        self._job_repo = job_repository
        self._blob_client = blob_client
        self._extractor = extractor
        self._active_tasks: dict[str, asyncio.Task] = {}

    async def start_extraction(self, document_id: str, version: int | None = None) -> str:
        """Start an async extraction job for a document.

        Creates an extraction job, starts background task, and returns job_id.
        The extraction runs asynchronously - use job_id to track progress.

        Args:
            document_id: The document ID to extract content from.
            version: Optional specific version (default: latest version).

        Returns:
            Job ID for tracking extraction progress.

        Raises:
            DocumentNotFoundError: If the document doesn't exist.
            NoSourceFileError: If the document has no source file.
        """
        # Get the document
        if version is not None and version > 0:
            document = await self._doc_repo.get_by_version(document_id, version)
        else:
            # Get latest version
            versions = await self._doc_repo.list_versions(document_id, include_archived=False)
            document = versions[0] if versions else None

        if document is None:
            raise DocumentNotFoundError(f"Document not found: {document_id}")

        if document.source_file is None:
            raise NoSourceFileError(f"Document has no source file to extract: {document_id}")

        # Create extraction job
        job_id = str(uuid.uuid4())
        job = ExtractionJob(
            id=job_id,
            job_id=job_id,
            document_id=document_id,
            status=ExtractionJobStatus.PENDING,
            progress_percent=0,
            pages_processed=0,
            total_pages=0,
            started_at=datetime.now(UTC),
        )
        await self._job_repo.create(job)

        logger.info(
            "Extraction job created",
            job_id=job_id,
            document_id=document_id,
            version=document.version,
            blob_path=document.source_file.blob_path,
        )

        # Start background task
        task = asyncio.create_task(
            self._run_extraction(job_id, document),
            name=f"extraction-{job_id}",
        )
        self._active_tasks[job_id] = task

        # Add callback to clean up task reference
        task.add_done_callback(lambda _: self._active_tasks.pop(job_id, None))

        return job_id

    async def _run_extraction(self, job_id: str, document: RagDocument) -> None:
        """Background task that runs the extraction.

        Args:
            job_id: The job ID for progress updates.
            document: The document to extract content from.
        """
        try:
            # Update status to in_progress
            await self._job_repo.update_progress(job_id, 0, 0, None)

            # Download source file from blob storage
            blob_path = document.source_file.blob_path
            logger.info(
                "Downloading source file",
                job_id=job_id,
                blob_path=blob_path,
            )

            try:
                content = await self._blob_client.download_to_bytes(blob_path)
            except BlobNotFoundError:
                await self._job_repo.mark_failed(
                    job_id,
                    f"Source file not found in blob storage: {blob_path}",
                )
                logger.error(
                    "Blob not found",
                    job_id=job_id,
                    blob_path=blob_path,
                )
                return

            # Detect file type and extract
            file_type = self._extractor.detect_file_type(
                document.source_file.filename,
                content,
            )

            logger.info(
                "Starting content extraction",
                job_id=job_id,
                file_type=file_type.value,
                file_size=len(content),
            )

            # Create progress callback that updates job repository
            async def update_progress(percent: int, pages_done: int, total: int) -> None:
                # Use sync wrapper since callback is called from sync context
                pass

            # For PDF extraction, we'll update progress synchronously within the extractor
            # and then update the job after completion
            try:
                result = await self._extractor.extract(
                    content,
                    file_type,
                    progress_callback=None,  # Progress logged but not persisted per-page
                )
            except PasswordProtectedError as e:
                await self._job_repo.mark_failed(job_id, str(e))
                logger.error(
                    "Password-protected PDF",
                    job_id=job_id,
                    document_id=document.document_id,
                )
                return
            except CorruptedFileError as e:
                await self._job_repo.mark_failed(job_id, str(e))
                logger.error(
                    "Corrupted file",
                    job_id=job_id,
                    document_id=document.document_id,
                    error=str(e),
                )
                return
            except ExtractionError as e:
                await self._job_repo.mark_failed(job_id, str(e))
                logger.error(
                    "Extraction failed",
                    job_id=job_id,
                    document_id=document.document_id,
                    error=str(e),
                )
                return

            # Update document with extraction results
            await self._doc_repo.update(
                document.id,
                {
                    "content": result.content,
                    "source_file.extraction_method": result.extraction_method.value,
                    "source_file.extraction_confidence": result.confidence,
                    "source_file.page_count": result.page_count,
                    "updated_at": datetime.now(UTC),
                },
            )

            # Mark job as completed
            await self._job_repo.mark_completed(
                job_id,
                pages_processed=result.page_count,
                total_pages=result.page_count,
            )

            logger.info(
                "Extraction completed",
                job_id=job_id,
                document_id=document.document_id,
                page_count=result.page_count,
                confidence=result.confidence,
                extraction_method=result.extraction_method.value,
            )

        except Exception as e:
            # Catch-all for unexpected errors
            error_msg = f"Unexpected extraction error: {e}"
            await self._job_repo.mark_failed(job_id, error_msg)
            logger.exception(
                "Unexpected extraction error",
                job_id=job_id,
                document_id=document.document_id,
            )

    async def get_job(self, job_id: str) -> ExtractionJob | None:
        """Get an extraction job by ID.

        Args:
            job_id: The job identifier.

        Returns:
            The job if found, None otherwise.
        """
        return await self._job_repo.get_by_job_id(job_id)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running extraction job.

        Args:
            job_id: The job identifier.

        Returns:
            True if cancelled, False if job not found or already completed.
        """
        task = self._active_tasks.get(job_id)
        if task is None:
            return False

        if task.done():
            return False

        task.cancel()
        await self._job_repo.mark_failed(job_id, "Job cancelled by user")
        logger.info("Extraction job cancelled", job_id=job_id)
        return True
