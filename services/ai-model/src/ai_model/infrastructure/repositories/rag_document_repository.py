"""RAG Document repository for MongoDB persistence.

This module provides the RagDocumentRepository class for managing RAG documents
in the ai_model.rag_documents MongoDB collection.

Indexes:
- (document_id, status): Fast lookup of active/staged documents
- (document_id, version): Unique constraint for version uniqueness
- (domain): Fast lookup by knowledge domain
- (status): Fast lookup by lifecycle status
"""

import logging

from ai_model.domain.rag_document import KnowledgeDomain, RagDocument, RagDocumentStatus
from ai_model.infrastructure.repositories.base import BaseRepository
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

logger = logging.getLogger(__name__)


class RagDocumentRepository(BaseRepository[RagDocument]):
    """Repository for RagDocument entities.

    Provides CRUD operations plus specialized queries:
    - get_active: Get currently active document for a document_id
    - get_by_version: Get specific version of a document
    - list_versions: List all versions of a document
    - list_by_domain: List documents by knowledge domain
    - list_by_status: List documents by lifecycle status
    """

    COLLECTION_NAME = "rag_documents"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the RAG document repository.

        Args:
            db: MongoDB database instance (should be ai_model database).
        """
        super().__init__(db, self.COLLECTION_NAME, RagDocument)

    async def get_active(self, document_id: str) -> RagDocument | None:
        """Get the currently active document for a document_id.

        Only one document per document_id should have status=active.

        Args:
            document_id: The stable document identifier (e.g., "disease-diagnosis-guide").

        Returns:
            The active document if found, None otherwise.
        """
        doc = await self._collection.find_one(
            {
                "document_id": document_id,
                "status": RagDocumentStatus.ACTIVE.value,
            }
        )
        if doc is None:
            return None
        doc.pop("_id", None)
        return RagDocument.model_validate(doc)

    async def get_by_version(
        self,
        document_id: str,
        version: int,
    ) -> RagDocument | None:
        """Get a specific version of a document.

        Args:
            document_id: The stable document identifier.
            version: The version number.

        Returns:
            The document if found, None otherwise.
        """
        doc = await self._collection.find_one(
            {
                "document_id": document_id,
                "version": version,
            }
        )
        if doc is None:
            return None
        doc.pop("_id", None)
        return RagDocument.model_validate(doc)

    async def get_latest(self, document_id: str) -> RagDocument | None:
        """Get the latest version of a document regardless of status.

        Args:
            document_id: The stable document identifier.

        Returns:
            The latest version if found, None otherwise.
        """
        cursor = self._collection.find({"document_id": document_id}).sort("version", DESCENDING).limit(1)
        docs = await cursor.to_list(length=1)
        if not docs:
            return None
        docs[0].pop("_id", None)
        return RagDocument.model_validate(docs[0])

    async def list_versions(
        self,
        document_id: str,
        include_archived: bool = True,
    ) -> list[RagDocument]:
        """List all versions of a document.

        Args:
            document_id: The stable document identifier.
            include_archived: Whether to include archived versions.

        Returns:
            List of document versions, sorted by version descending.
        """
        query: dict = {"document_id": document_id}
        if not include_archived:
            query["status"] = {"$ne": RagDocumentStatus.ARCHIVED.value}

        cursor = self._collection.find(query).sort("version", DESCENDING)
        docs = await cursor.to_list(length=None)

        documents = []
        for doc in docs:
            doc.pop("_id", None)
            documents.append(RagDocument.model_validate(doc))

        return documents

    async def list_by_domain(
        self,
        domain: KnowledgeDomain,
        status: RagDocumentStatus | None = None,
    ) -> list[RagDocument]:
        """List documents by knowledge domain.

        Args:
            domain: The knowledge domain to filter by.
            status: Optional status filter.

        Returns:
            List of documents in the domain.
        """
        query: dict = {"domain": domain.value}
        if status is not None:
            query["status"] = status.value

        cursor = self._collection.find(query).sort(
            [
                ("document_id", ASCENDING),
                ("version", DESCENDING),
            ]
        )
        docs = await cursor.to_list(length=None)

        documents = []
        for doc in docs:
            doc.pop("_id", None)
            documents.append(RagDocument.model_validate(doc))

        return documents

    async def list_by_status(
        self,
        status: RagDocumentStatus,
    ) -> list[RagDocument]:
        """List documents by lifecycle status.

        Args:
            status: The status to filter by.

        Returns:
            List of documents with the specified status.
        """
        query = {"status": status.value}

        cursor = self._collection.find(query).sort(
            [
                ("document_id", ASCENDING),
                ("version", DESCENDING),
            ]
        )
        docs = await cursor.to_list(length=None)

        documents = []
        for doc in docs:
            doc.pop("_id", None)
            documents.append(RagDocument.model_validate(doc))

        return documents

    async def list_with_pagination(
        self,
        filters: dict | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[RagDocument], int]:
        """List documents with pagination and filtering.

        Args:
            filters: Optional MongoDB filter query (domain, status, author, etc.).
            skip: Number of documents to skip (for pagination).
            limit: Maximum number of documents to return.

        Returns:
            Tuple of (documents, total_count).
        """
        query = filters or {}

        # Get total count
        total_count = await self._collection.count_documents(query)

        # Execute query with pagination (sort by created_at desc for consistent ordering)
        cursor = self._collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)

        # Convert to models
        documents = []
        for doc in docs:
            doc.pop("_id", None)
            documents.append(RagDocument.model_validate(doc))

        return documents, total_count

    async def replace(self, document: RagDocument) -> RagDocument | None:
        """Replace a RAG document with new values.

        Replaces the entire document in MongoDB with the provided document model.
        Use this for full document updates (e.g., after vectorization).

        Args:
            document: The updated document (must have id field).

        Returns:
            The updated document if found, None otherwise.
        """
        doc = document.model_dump()
        doc["_id"] = document.id

        result = await self._collection.find_one_and_replace(
            {"_id": document.id},
            doc,
            return_document=True,
        )
        if result is None:
            return None
        result.pop("_id", None)
        return RagDocument.model_validate(result)

    async def search(
        self,
        query_text: str,
        filters: dict | None = None,
        limit: int = 20,
    ) -> list[RagDocument]:
        """Search documents by title and content using regex.

        Uses MongoDB $regex for MVP (no text index required).

        Args:
            query_text: Text to search for in title and content.
            filters: Optional additional filters (domain, status).
            limit: Maximum number of results.

        Returns:
            List of matching documents.
        """
        # Build regex search query
        regex_filter = {
            "$or": [
                {"title": {"$regex": query_text, "$options": "i"}},
                {"content": {"$regex": query_text, "$options": "i"}},
            ]
        }

        # Combine with additional filters
        filter_query = {**regex_filter}
        if filters:
            filter_query.update(filters)

        # Execute search
        cursor = self._collection.find(filter_query).limit(limit)
        docs = await cursor.to_list(length=limit)

        # Convert to models
        documents = []
        for doc in docs:
            doc.pop("_id", None)
            documents.append(RagDocument.model_validate(doc))

        return documents

    async def ensure_indexes(self) -> None:
        """Create indexes for the rag_documents collection.

        Indexes:
        - (document_id, status): Fast lookup of active/staged documents
        - (document_id, version): Unique constraint, fast version lookup
        - (domain): Fast lookup by knowledge domain
        - (status): Fast lookup by lifecycle status
        """
        # Compound index for document_id + status (get_active query)
        await self._collection.create_index(
            [("document_id", ASCENDING), ("status", ASCENDING)],
            name="idx_document_id_status",
        )

        # Compound unique index for document_id + version
        await self._collection.create_index(
            [("document_id", ASCENDING), ("version", ASCENDING)],
            unique=True,
            name="idx_document_id_version_unique",
        )

        # Index for domain (list_by_domain query)
        await self._collection.create_index(
            "domain",
            name="idx_domain",
        )

        # Index for status (list_by_status query)
        await self._collection.create_index(
            "status",
            name="idx_status",
        )

        logger.info("RagDocument indexes created")
