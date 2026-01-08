"""Vectorization job repository for persistence.

This module provides the repository interface and MongoDB implementation
for persisting vectorization job status.

Story 0.75.13d: Vectorization Job Persistence
"""

from abc import ABC, abstractmethod
from datetime import UTC, datetime

import structlog
from ai_model.domain.vectorization import VectorizationJobStatus, VectorizationResult
from ai_model.domain.vectorization_job_document import VectorizationJobDocument
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING

logger = structlog.get_logger(__name__)


class VectorizationJobRepository(ABC):
    """Abstract base class for vectorization job persistence.

    Defines the interface for storing and retrieving vectorization job status.
    Implementations may use MongoDB, Redis, or in-memory storage.
    """

    @abstractmethod
    async def create(self, result: VectorizationResult) -> str:
        """Store a new vectorization job.

        Args:
            result: The job result to store.

        Returns:
            The job_id of the stored job.
        """
        pass

    @abstractmethod
    async def get(self, job_id: str) -> VectorizationResult | None:
        """Get a job by its ID.

        Args:
            job_id: The unique job identifier.

        Returns:
            The job result if found, None otherwise.
        """
        pass

    @abstractmethod
    async def update(self, result: VectorizationResult) -> None:
        """Update an existing job.

        Args:
            result: The updated job result.
        """
        pass

    @abstractmethod
    async def list_by_document(
        self,
        document_id: str,
    ) -> list[VectorizationResult]:
        """List all jobs for a specific document.

        Args:
            document_id: The document identifier.

        Returns:
            List of job results for the document, sorted by created_at descending.
        """
        pass

    @abstractmethod
    async def list_by_status(
        self,
        status: VectorizationJobStatus,
    ) -> list[VectorizationResult]:
        """List all jobs with a specific status.

        Args:
            status: The status to filter by.

        Returns:
            List of job results with the specified status.
        """
        pass


class MongoDBVectorizationJobRepository(VectorizationJobRepository):
    """MongoDB implementation of the vectorization job repository.

    Stores jobs in the ai_model.vectorization_jobs collection with:
    - Unique index on job_id
    - Index on document_id for filtering
    - Index on status for filtering
    - TTL index on completed_at for automatic cleanup
    """

    COLLECTION_NAME = "vectorization_jobs"

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        ttl_hours: int = 24,
    ) -> None:
        """Initialize the repository.

        Args:
            db: MongoDB database instance (should be ai_model database).
            ttl_hours: Hours after completion to automatically delete jobs.
                       Default: 24 hours. Set to 0 to disable TTL.
        """
        self._db = db
        self._collection = db[self.COLLECTION_NAME]
        self._ttl_hours = ttl_hours
        self._indexes_ensured = False

    async def ensure_indexes(self) -> None:
        """Create indexes for the collection.

        Indexes:
        - job_id: Unique index for fast lookup
        - document_id: For filtering jobs by document
        - status: For filtering jobs by status
        - completed_at: TTL index for automatic cleanup of completed jobs
        """
        if self._indexes_ensured:
            return

        # Unique index on job_id
        await self._collection.create_index(
            "job_id",
            unique=True,
            name="idx_job_id_unique",
        )

        # Index on document_id for list_by_document queries
        await self._collection.create_index(
            "document_id",
            name="idx_document_id",
        )

        # Index on status for list_by_status queries
        await self._collection.create_index(
            "status",
            name="idx_status",
        )

        # TTL index on completed_at for automatic cleanup
        # Only applies to documents where completed_at is set and status is terminal
        # Note: Using $type instead of $ne: null because partial filter expressions
        # don't support $ne operator in MongoDB
        if self._ttl_hours > 0:
            await self._collection.create_index(
                "completed_at",
                expireAfterSeconds=self._ttl_hours * 3600,
                name="idx_completed_at_ttl",
                partialFilterExpression={
                    "status": {"$in": ["completed", "partial", "failed"]},
                    "completed_at": {"$type": "date"},
                },
            )

        # Compound index for ordering queries
        await self._collection.create_index(
            [("document_id", ASCENDING), ("created_at", ASCENDING)],
            name="idx_document_id_created_at",
        )

        self._indexes_ensured = True
        logger.info("VectorizationJob indexes created", ttl_hours=self._ttl_hours)

    async def create(self, result: VectorizationResult) -> str:
        """Store a new vectorization job.

        Args:
            result: The job result to store.

        Returns:
            The job_id of the stored job.
        """
        doc = VectorizationJobDocument.from_result(result)
        mongo_doc = doc.model_dump()
        mongo_doc["_id"] = doc.job_id  # Use job_id as MongoDB _id

        await self._collection.insert_one(mongo_doc)

        logger.debug(
            "Created vectorization job",
            job_id=doc.job_id,
            document_id=doc.document_id,
            status=doc.status.value,
        )

        return doc.job_id

    async def get(self, job_id: str) -> VectorizationResult | None:
        """Get a job by its ID.

        Args:
            job_id: The unique job identifier.

        Returns:
            The job result if found, None otherwise.
        """
        mongo_doc = await self._collection.find_one({"_id": job_id})
        if mongo_doc is None:
            return None

        mongo_doc.pop("_id", None)
        doc = VectorizationJobDocument.model_validate(mongo_doc)
        return doc.to_result()

    async def update(self, result: VectorizationResult) -> None:
        """Update an existing job.

        Args:
            result: The updated job result.
        """
        doc = VectorizationJobDocument.from_result(result)
        doc_dict = doc.model_dump()
        doc_dict["_id"] = doc.job_id
        doc_dict["updated_at"] = datetime.now(UTC)

        await self._collection.replace_one(
            {"_id": doc.job_id},
            doc_dict,
            upsert=True,  # Allow upsert in case job doesn't exist yet
        )

        logger.debug(
            "Updated vectorization job",
            job_id=doc.job_id,
            status=doc.status.value,
        )

    async def list_by_document(
        self,
        document_id: str,
    ) -> list[VectorizationResult]:
        """List all jobs for a specific document.

        Args:
            document_id: The document identifier.

        Returns:
            List of job results for the document, sorted by created_at descending.
        """
        cursor = self._collection.find({"document_id": document_id}).sort("created_at", -1)
        docs = await cursor.to_list(length=100)  # Limit to 100 jobs per document

        results = []
        for mongo_doc in docs:
            mongo_doc.pop("_id", None)
            doc = VectorizationJobDocument.model_validate(mongo_doc)
            results.append(doc.to_result())

        return results

    async def list_by_status(
        self,
        status: VectorizationJobStatus,
    ) -> list[VectorizationResult]:
        """List all jobs with a specific status.

        Args:
            status: The status to filter by.

        Returns:
            List of job results with the specified status.
        """
        cursor = self._collection.find({"status": status.value}).sort("created_at", -1)
        docs = await cursor.to_list(length=100)  # Limit to 100 jobs

        results = []
        for mongo_doc in docs:
            mongo_doc.pop("_id", None)
            doc = VectorizationJobDocument.model_validate(mongo_doc)
            results.append(doc.to_result())

        return results
