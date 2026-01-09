"""Generic document repository for storing extracted documents.

This module provides the DocumentRepository class for storing documents
in MongoDB collections specified by source configuration. The repository
is collection-agnostic - it reads the collection name from config.
"""

from typing import Any

import structlog
from collection_model.domain.document_index import DocumentIndex
from collection_model.domain.exceptions import StorageError
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

logger = structlog.get_logger(__name__)


class DocumentRepository:
    """Generic repository for document indexes.

    Collection name is NOT hardcoded - it's read from source_config.storage.index_collection.
    This enables different source types to store in different collections.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the document repository.

        Args:
            db: MongoDB database instance.
        """
        self.db = db
        self._ensured_collections: set[str] = set()

    async def ensure_indexes(self, collection_name: str, link_field: str) -> None:
        """Ensure indexes exist for a collection.

        Creates indexes dynamically based on the link_field from source config.

        Args:
            collection_name: The collection to ensure indexes for.
            link_field: The field to create an index on for linkage.
        """
        if collection_name in self._ensured_collections:
            return

        collection = self.db[collection_name]

        # Unique index on document_id
        await collection.create_index(
            "document_id",
            unique=True,
            name="idx_document_id_unique",
        )

        # Index on ingestion.source_id
        await collection.create_index(
            "ingestion.source_id",
            name="idx_source_id",
        )

        # Index on linkage field (e.g., farmer_id)
        if link_field:
            await collection.create_index(
                f"linkage_fields.{link_field}",
                name=f"idx_linkage_{link_field}",
            )

        # Index on created_at for time-based queries
        await collection.create_index(
            "created_at",
            name="idx_created_at",
        )

        self._ensured_collections.add(collection_name)
        logger.info(
            "Document repository indexes ensured",
            collection=collection_name,
            link_field=link_field,
        )

    async def save(
        self,
        document: DocumentIndex,
        collection_name: str,
    ) -> str:
        """Save a document to the specified collection.

        Args:
            document: The document to save.
            collection_name: The collection to save to (from config).

        Returns:
            The document_id of the saved document.

        Raises:
            StorageError: If saving fails.
        """
        collection = self.db[collection_name]

        try:
            await collection.insert_one(document.model_dump())
            logger.info(
                "Document saved",
                document_id=document.document_id,
                collection=collection_name,
                source_id=document.ingestion.source_id,
            )
            return document.document_id

        except DuplicateKeyError:
            logger.warning(
                "Duplicate document detected",
                document_id=document.document_id,
                collection=collection_name,
            )
            raise StorageError(f"Duplicate document: {document.document_id}")

        except Exception as e:
            logger.exception(
                "Failed to save document",
                document_id=document.document_id,
                collection=collection_name,
                error=str(e),
            )
            raise StorageError(f"Failed to save document: {e}") from e

    async def get_by_id(
        self,
        document_id: str,
        collection_name: str,
    ) -> DocumentIndex | None:
        """Get a document by its ID.

        Args:
            document_id: The document ID to look up.
            collection_name: The collection to search in.

        Returns:
            DocumentIndex if found, None otherwise.
        """
        collection = self.db[collection_name]
        doc = await collection.find_one({"document_id": document_id})
        if doc:
            return DocumentIndex.model_validate(doc)
        return None

    async def find_by_linkage(
        self,
        link_field: str,
        link_value: Any,
        collection_name: str,
        limit: int = 100,
    ) -> list[DocumentIndex]:
        """Find documents by linkage field value.

        Args:
            link_field: The linkage field name (e.g., "farmer_id").
            link_value: The value to search for.
            collection_name: The collection to search in.
            limit: Maximum number of results.

        Returns:
            List of matching DocumentIndex objects.
        """
        collection = self.db[collection_name]
        cursor = collection.find({f"linkage_fields.{link_field}": link_value}).sort("created_at", -1).limit(limit)

        documents = []
        async for doc in cursor:
            documents.append(DocumentIndex.model_validate(doc))
        return documents

    async def count_by_source(
        self,
        source_id: str,
        collection_name: str,
    ) -> int:
        """Count documents for a source.

        Args:
            source_id: The source configuration ID.
            collection_name: The collection to count in.

        Returns:
            Number of documents for the source.
        """
        collection = self.db[collection_name]
        return await collection.count_documents({"ingestion.source_id": source_id})

    async def update(
        self,
        document: DocumentIndex,
        collection_name: str,
    ) -> bool:
        """Update an existing document in the collection.

        Story 2-12: Used to update document status and extracted_fields
        after AI Model returns the extraction result.

        Args:
            document: The document with updated fields.
            collection_name: The collection containing the document.

        Returns:
            True if document was updated, False if not found.

        Raises:
            StorageError: If update fails.
        """
        collection = self.db[collection_name]

        try:
            result = await collection.replace_one(
                {"document_id": document.document_id},
                document.model_dump(),
            )

            if result.matched_count == 0:
                logger.warning(
                    "Document not found for update",
                    document_id=document.document_id,
                    collection=collection_name,
                )
                return False

            logger.info(
                "Document updated",
                document_id=document.document_id,
                collection=collection_name,
                modified_count=result.modified_count,
            )
            return True

        except Exception as e:
            logger.exception(
                "Failed to update document",
                document_id=document.document_id,
                collection=collection_name,
                error=str(e),
            )
            raise StorageError(f"Failed to update document: {e}") from e

    async def find_pending_by_request_id(
        self,
        request_id: str,
        collection_name: str,
    ) -> DocumentIndex | None:
        """Find a pending document by request_id (which equals document_id).

        Story 2-12: Used to correlate AI Model response back to the
        original pending document.

        Args:
            request_id: The request_id from AgentCompletedEvent (equals document_id).
            collection_name: The collection to search in.

        Returns:
            DocumentIndex if found and pending, None otherwise.
        """
        collection = self.db[collection_name]
        doc = await collection.find_one(
            {
                "document_id": request_id,
                "extraction.status": "pending",
            }
        )
        if doc:
            return DocumentIndex.model_validate(doc)
        return None
