"""RAG Chunk repository for MongoDB persistence.

This module provides the RagChunkRepository class for managing RAG chunks
in the ai_model.rag_chunks MongoDB collection.

Story 0.75.10d: Semantic Chunking
"""

import logging

from ai_model.domain.rag_document import RagChunk
from ai_model.infrastructure.repositories.base import BaseRepository
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING

logger = logging.getLogger(__name__)


class RagChunkRepository(BaseRepository[RagChunk]):
    """Repository for RagChunk entities.

    Provides CRUD operations plus specialized queries:
    - get_by_document: Get all chunks for a document version
    - delete_by_document: Delete all chunks for a document version
    - count_by_document: Count chunks for a document version
    - bulk_create: Create multiple chunks in a single operation
    """

    COLLECTION_NAME = "rag_chunks"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the RAG chunk repository.

        Args:
            db: MongoDB database instance (should be ai_model database).
        """
        super().__init__(db, self.COLLECTION_NAME, RagChunk)

    async def get_by_document(
        self,
        document_id: str,
        document_version: int,
    ) -> list[RagChunk]:
        """Get all chunks for a document version.

        Args:
            document_id: The parent document ID.
            document_version: The parent document version.

        Returns:
            List of chunks, sorted by chunk_index ascending.
        """
        cursor = self._collection.find(
            {
                "document_id": document_id,
                "document_version": document_version,
            }
        ).sort("chunk_index", ASCENDING)

        docs = await cursor.to_list(length=None)

        chunks = []
        for doc in docs:
            doc.pop("_id", None)
            chunks.append(RagChunk.model_validate(doc))

        return chunks

    async def delete_by_document(
        self,
        document_id: str,
        document_version: int,
    ) -> int:
        """Delete all chunks for a document version.

        Args:
            document_id: The parent document ID.
            document_version: The parent document version.

        Returns:
            Number of chunks deleted.
        """
        result = await self._collection.delete_many(
            {
                "document_id": document_id,
                "document_version": document_version,
            }
        )

        logger.info(
            "Chunks deleted for document",
            document_id=document_id,
            document_version=document_version,
            deleted_count=result.deleted_count,
        )

        return result.deleted_count

    async def count_by_document(
        self,
        document_id: str,
        document_version: int,
    ) -> int:
        """Count chunks for a document version.

        Args:
            document_id: The parent document ID.
            document_version: The parent document version.

        Returns:
            Number of chunks for this document version.
        """
        return await self._collection.count_documents(
            {
                "document_id": document_id,
                "document_version": document_version,
            }
        )

    async def bulk_create(self, chunks: list[RagChunk]) -> list[RagChunk]:
        """Create multiple chunks in a single operation.

        Uses MongoDB insertMany for efficiency when creating many chunks.

        Args:
            chunks: List of RagChunk entities to create.

        Returns:
            The created chunks (same as input).
        """
        if not chunks:
            return []

        docs = []
        for chunk in chunks:
            doc = chunk.model_dump()
            # RagChunk uses chunk_id as the primary identifier
            doc["_id"] = chunk.chunk_id
            docs.append(doc)

        await self._collection.insert_many(docs)

        logger.debug(
            "Bulk created chunks",
            count=len(chunks),
            document_id=chunks[0].document_id if chunks else None,
        )

        return chunks

    async def update_pinecone_id(
        self,
        chunk_id: str,
        pinecone_id: str,
    ) -> RagChunk | None:
        """Update the Pinecone vector ID for a chunk.

        Called after vectorization to link chunk to its vector.

        Args:
            chunk_id: The chunk identifier.
            pinecone_id: The Pinecone vector ID.

        Returns:
            The updated chunk if found, None otherwise.
        """
        result = await self._collection.find_one_and_update(
            {"_id": chunk_id},
            {"$set": {"pinecone_id": pinecone_id}},
            return_document=True,
        )

        if result is None:
            return None

        result.pop("_id", None)
        return RagChunk.model_validate(result)

    async def get_chunks_without_vectors(
        self,
        document_id: str,
        document_version: int,
    ) -> list[RagChunk]:
        """Get chunks that haven't been vectorized yet.

        Args:
            document_id: The parent document ID.
            document_version: The parent document version.

        Returns:
            List of chunks without pinecone_id set.
        """
        cursor = self._collection.find(
            {
                "document_id": document_id,
                "document_version": document_version,
                "pinecone_id": None,
            }
        ).sort("chunk_index", ASCENDING)

        docs = await cursor.to_list(length=None)

        chunks = []
        for doc in docs:
            doc.pop("_id", None)
            chunks.append(RagChunk.model_validate(doc))

        return chunks

    async def ensure_indexes(self) -> None:
        """Create indexes for the rag_chunks collection.

        Indexes:
        - chunk_id (unique): Fast lookup by chunk ID
        - (document_id, document_version): Fast lookup by parent document
        - (document_id, document_version, chunk_index): Ordered chunk retrieval
        """
        # Unique index on chunk_id
        await self._collection.create_index(
            "chunk_id",
            unique=True,
            name="idx_chunk_id_unique",
        )

        # Compound index for document lookups
        await self._collection.create_index(
            [("document_id", ASCENDING), ("document_version", ASCENDING)],
            name="idx_document_id_version",
        )

        # Compound index for ordered chunk retrieval
        await self._collection.create_index(
            [
                ("document_id", ASCENDING),
                ("document_version", ASCENDING),
                ("chunk_index", ASCENDING),
            ],
            name="idx_document_chunk_order",
        )

        # Index for finding chunks without vectors
        await self._collection.create_index(
            "pinecone_id",
            name="idx_pinecone_id",
            sparse=True,
        )

        logger.info("RagChunk indexes created")
