"""Raw document storage for persisting raw blob content.

This module provides the RawDocumentStore class for storing raw documents
in Azure Blob Storage and tracking them in MongoDB with content hashes
for deduplication.
"""

import hashlib
from datetime import UTC, datetime
from typing import Any

import structlog
from collection_model.domain.exceptions import DuplicateDocumentError, StorageError
from collection_model.domain.raw_document import RawDocument
from collection_model.infrastructure.blob_storage import BlobStorageClient
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

logger = structlog.get_logger(__name__)

COLLECTION_NAME = "raw_documents"


class RawDocumentStore:
    """Store for raw documents with deduplication via content hash.

    Stores raw content in Azure Blob Storage and maintains a MongoDB
    index for deduplication based on content hash.
    """

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        blob_client: BlobStorageClient,
    ) -> None:
        """Initialize the raw document store.

        Args:
            db: MongoDB database instance.
            blob_client: Azure Blob Storage client.
        """
        self.db = db
        self.collection = db[COLLECTION_NAME]
        self.blob_client = blob_client

    async def ensure_indexes(self) -> None:
        """Create required indexes for raw documents.

        Creates:
        - Unique compound index on (source_id, content_hash) for deduplication
        - Index on ingestion_id for lookups
        """
        await self.collection.create_index(
            [("source_id", 1), ("content_hash", 1)],
            unique=True,
            name="idx_source_content_hash_unique",
        )
        await self.collection.create_index(
            "ingestion_id",
            name="idx_ingestion_id",
        )
        await self.collection.create_index(
            "document_id",
            unique=True,
            name="idx_document_id_unique",
        )
        logger.info("Raw document indexes ensured")

    @staticmethod
    def compute_content_hash(content: bytes) -> str:
        """Compute SHA-256 hash of content.

        Args:
            content: The content bytes to hash.

        Returns:
            Hex-encoded SHA-256 hash string.
        """
        return hashlib.sha256(content).hexdigest()

    async def store_raw_document(
        self,
        content: bytes,
        source_config: dict[str, Any],
        ingestion_id: str,
        metadata: dict[str, str] | None = None,
    ) -> RawDocument:
        """Store raw document content with deduplication.

        Computes content hash and checks for duplicates before storing.
        If a duplicate exists, raises DuplicateDocumentError.

        Args:
            content: The raw content bytes to store.
            source_config: Source configuration with storage settings.
            ingestion_id: ID of the ingestion job.
            metadata: Optional metadata from path extraction.

        Returns:
            RawDocument with storage details.

        Raises:
            DuplicateDocumentError: If content with same hash exists for source.
            StorageError: If storage operation fails.
        """
        source_id = source_config.get("source_id", "unknown")
        storage = source_config.get("storage", {})
        raw_container = storage.get("raw_container", "raw-documents")

        content_hash = self.compute_content_hash(content)

        # Check for duplicate
        existing = await self.collection.find_one(
            {
                "source_id": source_id,
                "content_hash": content_hash,
            }
        )
        if existing:
            logger.info(
                "Duplicate content detected",
                source_id=source_id,
                content_hash=content_hash,
                existing_document_id=existing.get("document_id"),
            )
            raise DuplicateDocumentError(f"Duplicate content for source {source_id}: {content_hash}")

        # Store to blob storage
        blob_path = f"{source_id}/{ingestion_id}/{content_hash}"
        content_type = self._get_content_type(source_config)

        try:
            await self.blob_client.upload_blob(
                container=raw_container,
                blob_path=blob_path,
                content=content,
                content_type=content_type,
            )
        except Exception as e:
            logger.exception(
                "Failed to upload raw document to blob storage",
                source_id=source_id,
                ingestion_id=ingestion_id,
                error=str(e),
            )
            raise StorageError(f"Failed to upload raw document: {e}") from e

        # Create raw document record
        raw_doc = RawDocument(
            source_id=source_id,
            ingestion_id=ingestion_id,
            blob_container=raw_container,
            blob_path=blob_path,
            content_hash=content_hash,
            content_type=content_type,
            size_bytes=len(content),
            stored_at=datetime.now(UTC),
            metadata=metadata or {},
        )

        # Store in MongoDB
        try:
            await self.collection.insert_one(raw_doc.model_dump())
            logger.info(
                "Raw document stored",
                document_id=raw_doc.document_id,
                source_id=source_id,
                content_hash=content_hash,
                size_bytes=len(content),
            )
            return raw_doc
        except DuplicateKeyError:
            # Race condition - another process stored the same content
            logger.info(
                "Duplicate detected during insert (race condition)",
                source_id=source_id,
                content_hash=content_hash,
            )
            raise DuplicateDocumentError(f"Duplicate content for source {source_id}: {content_hash}")
        except Exception as e:
            logger.exception(
                "Failed to store raw document metadata",
                source_id=source_id,
                ingestion_id=ingestion_id,
                error=str(e),
            )
            raise StorageError(f"Failed to store raw document metadata: {e}") from e

    async def get_by_id(self, document_id: str) -> RawDocument | None:
        """Get a raw document by its ID.

        Args:
            document_id: The document ID to look up.

        Returns:
            RawDocument if found, None otherwise.
        """
        doc = await self.collection.find_one({"document_id": document_id})
        if doc:
            return RawDocument.model_validate(doc)
        return None

    async def get_by_content_hash(
        self,
        source_id: str,
        content_hash: str,
    ) -> RawDocument | None:
        """Get a raw document by source ID and content hash.

        Args:
            source_id: The source configuration ID.
            content_hash: The SHA-256 content hash.

        Returns:
            RawDocument if found, None otherwise.
        """
        doc = await self.collection.find_one(
            {
                "source_id": source_id,
                "content_hash": content_hash,
            }
        )
        if doc:
            return RawDocument.model_validate(doc)
        return None

    @staticmethod
    def _get_content_type(source_config: dict[str, Any]) -> str:
        """Get content type from source configuration.

        Args:
            source_config: The source configuration.

        Returns:
            MIME type string.
        """
        ingestion = source_config.get("ingestion", {})
        file_format = ingestion.get("file_format", "")

        if file_format == "json":
            return "application/json"
        elif file_format == "zip":
            return "application/zip"
        else:
            return "application/octet-stream"
