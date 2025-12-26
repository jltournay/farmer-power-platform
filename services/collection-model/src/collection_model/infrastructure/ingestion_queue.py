"""Ingestion queue for storing and retrieving blob processing jobs.

This module provides the IngestionQueue class which manages the
ingestion_queue MongoDB collection for storing IngestionJob documents.
"""

from datetime import UTC

import structlog
from collection_model.domain.ingestion_job import IngestionJob
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

logger = structlog.get_logger(__name__)

COLLECTION_NAME = "ingestion_queue"


class IngestionQueue:
    """Queue for ingestion jobs stored in MongoDB.

    Provides methods for:
    - Ensuring indexes (idempotency + processing order)
    - Queuing new jobs with duplicate detection
    - Retrieving pending jobs for processing

    Attributes:
        COLLECTION_NAME: Name of the MongoDB collection.

    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the ingestion queue.

        Args:
            db: MongoDB database instance.

        """
        self.db = db
        self.collection = db[COLLECTION_NAME]

    async def ensure_indexes(self) -> None:
        """Create required indexes for the ingestion queue.

        Creates:
        - Unique compound index on (blob_path, blob_etag) for idempotency
        - Index on (status, created_at) for efficient queue processing

        """
        # Unique compound index for Event Grid retry idempotency
        await self.collection.create_index(
            [("blob_path", 1), ("blob_etag", 1)],
            unique=True,
            name="idx_blob_path_etag_unique",
        )

        # Index for queue processing (get oldest queued jobs first)
        await self.collection.create_index(
            [("status", 1), ("created_at", 1)],
            name="idx_status_created",
        )

        # Index for source_id queries
        await self.collection.create_index(
            "source_id",
            name="idx_source_id",
        )

        logger.info("Ingestion queue indexes ensured")

    async def queue_job(self, job: IngestionJob) -> bool:
        """Queue an ingestion job with idempotency check.

        Uses MongoDB's unique index to prevent duplicate jobs for the same
        blob_path + blob_etag combination (Event Grid retry handling).

        Args:
            job: The IngestionJob to queue.

        Returns:
            True if job was queued successfully, False if duplicate detected.

        """
        try:
            await self.collection.insert_one(job.model_dump())
            logger.debug(
                "Ingestion job queued",
                ingestion_id=job.ingestion_id,
                blob_path=job.blob_path,
                source_id=job.source_id,
            )
            return True
        except DuplicateKeyError:
            logger.debug(
                "Duplicate job detected (Event Grid retry)",
                blob_path=job.blob_path,
                blob_etag=job.blob_etag,
            )
            return False

    async def get_pending_jobs(self, limit: int = 10) -> list[IngestionJob]:
        """Get pending jobs for processing.

        Retrieves the oldest queued jobs first (FIFO ordering).

        Args:
            limit: Maximum number of jobs to return.

        Returns:
            List of IngestionJob objects with status "queued".

        """
        cursor = self.collection.find({"status": "queued"}).sort("created_at", 1).limit(limit)
        jobs = []
        async for doc in cursor:
            jobs.append(IngestionJob.model_validate(doc))
        return jobs

    async def update_job_status(
        self,
        ingestion_id: str,
        status: str,
        error_message: str | None = None,
    ) -> bool:
        """Update the status of a job.

        Args:
            ingestion_id: The ingestion_id of the job to update.
            status: New status value.
            error_message: Optional error message if status is "failed".

        Returns:
            True if job was found and updated, False otherwise.

        """
        from datetime import datetime

        update_doc: dict = {"status": status}
        if status in ("completed", "failed"):
            update_doc["processed_at"] = datetime.now(UTC)
        if error_message:
            update_doc["error_message"] = error_message

        result = await self.collection.update_one(
            {"ingestion_id": ingestion_id},
            {"$set": update_doc},
        )

        if result.modified_count > 0:
            logger.debug(
                "Job status updated",
                ingestion_id=ingestion_id,
                status=status,
            )
            return True

        logger.warning(
            "Job not found for status update",
            ingestion_id=ingestion_id,
        )
        return False

    async def get_job_by_id(self, ingestion_id: str) -> IngestionJob | None:
        """Get a job by its ingestion_id.

        Args:
            ingestion_id: The unique ingestion ID.

        Returns:
            IngestionJob if found, None otherwise.

        """
        doc = await self.collection.find_one({"ingestion_id": ingestion_id})
        if doc:
            return IngestionJob.model_validate(doc)
        return None
