"""Extraction job repository for MongoDB persistence.

This module provides the ExtractionJobRepository class for managing extraction jobs
in the ai_model.extraction_jobs MongoDB collection.

Story 0.75.10b: Basic PDF/Markdown Extraction
Story 0.75.10c: Azure Document Intelligence Integration
"""

import logging
from datetime import UTC, datetime

from ai_model.domain.extraction_job import ExtractionJob, ExtractionJobStatus
from ai_model.domain.rag_document import ExtractionMethod
from ai_model.infrastructure.repositories.base import BaseRepository
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

logger = logging.getLogger(__name__)


class ExtractionJobRepository(BaseRepository[ExtractionJob]):
    """Repository for ExtractionJob entities.

    Provides CRUD operations plus specialized queries:
    - get_by_job_id: Get job by its unique job_id
    - get_by_document_id: Get all jobs for a document
    - get_active_jobs: Get jobs that are pending or in_progress
    - update_progress: Atomically update job progress
    - mark_completed: Mark job as completed with final stats
    - mark_failed: Mark job as failed with error message
    """

    COLLECTION_NAME = "extraction_jobs"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the extraction job repository.

        Args:
            db: MongoDB database instance (should be ai_model database).
        """
        super().__init__(db, self.COLLECTION_NAME, ExtractionJob)

    async def get_by_job_id(self, job_id: str) -> ExtractionJob | None:
        """Get an extraction job by its job_id.

        Args:
            job_id: The unique job identifier.

        Returns:
            The job if found, None otherwise.
        """
        doc = await self._collection.find_one({"job_id": job_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return ExtractionJob.model_validate(doc)

    async def get_by_document_id(
        self,
        document_id: str,
        include_completed: bool = True,
    ) -> list[ExtractionJob]:
        """Get all extraction jobs for a document.

        Args:
            document_id: The RAG document ID.
            include_completed: Whether to include completed/failed jobs.

        Returns:
            List of jobs, sorted by started_at descending.
        """
        query: dict = {"document_id": document_id}
        if not include_completed:
            query["status"] = {
                "$in": [
                    ExtractionJobStatus.PENDING.value,
                    ExtractionJobStatus.IN_PROGRESS.value,
                ]
            }

        cursor = self._collection.find(query).sort("started_at", DESCENDING)
        docs = await cursor.to_list(length=None)

        jobs = []
        for doc in docs:
            doc.pop("_id", None)
            jobs.append(ExtractionJob.model_validate(doc))

        return jobs

    async def get_active_jobs(self) -> list[ExtractionJob]:
        """Get all pending or in_progress jobs.

        Returns:
            List of active jobs.
        """
        query = {
            "status": {
                "$in": [
                    ExtractionJobStatus.PENDING.value,
                    ExtractionJobStatus.IN_PROGRESS.value,
                ]
            }
        }

        cursor = self._collection.find(query).sort("started_at", ASCENDING)
        docs = await cursor.to_list(length=None)

        jobs = []
        for doc in docs:
            doc.pop("_id", None)
            jobs.append(ExtractionJob.model_validate(doc))

        return jobs

    async def update_progress(
        self,
        job_id: str,
        progress_percent: int,
        pages_processed: int,
        total_pages: int | None = None,
    ) -> ExtractionJob | None:
        """Atomically update job progress.

        Args:
            job_id: The job identifier.
            progress_percent: Current progress (0-100).
            pages_processed: Number of pages extracted.
            total_pages: Total pages (only updated if provided).

        Returns:
            The updated job if found, None otherwise.
        """
        updates: dict = {
            "progress_percent": progress_percent,
            "pages_processed": pages_processed,
            "status": ExtractionJobStatus.IN_PROGRESS.value,
        }
        if total_pages is not None:
            updates["total_pages"] = total_pages

        result = await self._collection.find_one_and_update(
            {"job_id": job_id},
            {"$set": updates},
            return_document=True,
        )
        if result is None:
            return None
        result.pop("_id", None)
        return ExtractionJob.model_validate(result)

    async def mark_completed(
        self,
        job_id: str,
        pages_processed: int,
        total_pages: int,
        extraction_method: ExtractionMethod | None = None,
    ) -> ExtractionJob | None:
        """Mark a job as completed successfully.

        Args:
            job_id: The job identifier.
            pages_processed: Final count of pages extracted.
            total_pages: Total pages in document.
            extraction_method: Method used for extraction (text_extraction, azure_doc_intel, etc.).

        Returns:
            The updated job if found, None otherwise.
        """
        now = datetime.now(UTC)
        updates: dict = {
            "status": ExtractionJobStatus.COMPLETED.value,
            "progress_percent": 100,
            "pages_processed": pages_processed,
            "total_pages": total_pages,
            "completed_at": now,
        }
        if extraction_method is not None:
            updates["extraction_method"] = extraction_method.value

        result = await self._collection.find_one_and_update(
            {"job_id": job_id},
            {"$set": updates},
            return_document=True,
        )
        if result is None:
            return None
        result.pop("_id", None)
        return ExtractionJob.model_validate(result)

    async def mark_failed(
        self,
        job_id: str,
        error_message: str,
    ) -> ExtractionJob | None:
        """Mark a job as failed with an error message.

        Args:
            job_id: The job identifier.
            error_message: Description of what went wrong.

        Returns:
            The updated job if found, None otherwise.
        """
        now = datetime.now(UTC)
        updates = {
            "status": ExtractionJobStatus.FAILED.value,
            "error_message": error_message,
            "completed_at": now,
        }

        result = await self._collection.find_one_and_update(
            {"job_id": job_id},
            {"$set": updates},
            return_document=True,
        )
        if result is None:
            return None
        result.pop("_id", None)
        return ExtractionJob.model_validate(result)

    async def ensure_indexes(self) -> None:
        """Create indexes for the extraction_jobs collection.

        Indexes:
        - job_id (unique): Fast lookup by job ID
        - document_id: Fast lookup by document
        - status: Fast lookup of active jobs
        - started_at: Ordering and cleanup queries
        """
        # Unique index on job_id
        await self._collection.create_index(
            "job_id",
            unique=True,
            name="idx_job_id_unique",
        )

        # Index for document_id lookups
        await self._collection.create_index(
            "document_id",
            name="idx_document_id",
        )

        # Index for status queries
        await self._collection.create_index(
            "status",
            name="idx_status",
        )

        # Index for ordering and cleanup
        await self._collection.create_index(
            "started_at",
            name="idx_started_at",
        )

        logger.info("ExtractionJob indexes created")
