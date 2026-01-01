"""Collection Model client for fetching quality documents.

This client connects to Collection Model's MongoDB to retrieve quality
documents by ID. This is used when processing quality result events
from the Collection Model pub/sub.

Story 1.7: Quality Grading Event Subscription
"""

from typing import Any

import structlog
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from plantation_model.config import settings
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)


class DocumentNotFoundError(Exception):
    """Raised when a document is not found in Collection Model."""

    def __init__(self, document_id: str) -> None:
        self.document_id = document_id
        super().__init__(f"Document not found: {document_id}")


class CollectionClientError(Exception):
    """Raised when a Collection Model client operation fails."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        self.cause = cause
        super().__init__(message)


class CollectionClient:
    """Async client for fetching documents from Collection Model.

    This client connects to Collection Model's MongoDB database to
    retrieve quality documents. It follows the same pattern as
    Collection MCP's DocumentClient.

    Usage:
        client = CollectionClient()
        document = await client.get_document("doc-123")
        await client.close()
    """

    def __init__(
        self,
        mongodb_uri: str | None = None,
        database_name: str | None = None,
    ) -> None:
        """Initialize the Collection client.

        Args:
            mongodb_uri: MongoDB connection URI. Defaults to settings.
            database_name: Database name. Defaults to settings.
        """
        self._mongodb_uri = mongodb_uri or settings.collection_mongodb_uri
        self._database_name = database_name or settings.collection_mongodb_database
        self._client: AsyncIOMotorClient | None = None
        self._db: AsyncIOMotorDatabase | None = None

    async def _get_collection(self):
        """Get or create the MongoDB collection reference."""
        if self._client is None:
            self._client = AsyncIOMotorClient(self._mongodb_uri)
            self._db = self._client[self._database_name]
        return self._db["quality_documents"]

    @retry(
        retry=retry_if_exception_type((ConnectionError, DocumentNotFoundError)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
        reraise=True,
    )
    async def get_document(self, document_id: str) -> dict[str, Any]:
        """Get a quality document by its ID.

        Retrieves the full document from Collection Model's documents
        collection. The document contains:
        - source_id: The data source (e.g., "qc-analyzer-result")
        - farmer_id: The farmer/plantation ID
        - attributes: QC Analyzer result data including grade counts
        - grading_model_id: ID of the grading model used
        - grading_model_version: Version of the grading model used

        Args:
            document_id: The document's unique identifier.

        Returns:
            The document dictionary with all fields.

        Raises:
            DocumentNotFoundError: If no document with the given ID exists.
            CollectionClientError: If a database error occurs.
        """
        try:
            collection = await self._get_collection()

            logger.debug("Fetching document from Collection Model", document_id=document_id)

            document = await collection.find_one({"document_id": document_id})

            if document is None:
                logger.warning("Document not found in Collection Model", document_id=document_id)
                raise DocumentNotFoundError(document_id)

            # Convert ObjectId to string for JSON serialization
            if "_id" in document:
                document["_id"] = str(document["_id"])

            logger.info(
                "Document retrieved from Collection Model",
                document_id=document_id,
                source_id=document.get("source_id"),
                farmer_id=document.get("farmer_id"),
            )

            return document

        except DocumentNotFoundError:
            raise
        except Exception as e:
            logger.error(
                "Failed to fetch document from Collection Model",
                document_id=document_id,
                error=str(e),
            )
            raise CollectionClientError(f"Failed to fetch document {document_id}", cause=e) from e

    async def close(self) -> None:
        """Close the MongoDB client connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("Collection client connection closed")
