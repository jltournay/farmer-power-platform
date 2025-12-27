"""MongoDB document client for querying the documents collection."""

from datetime import datetime
from typing import Any

import structlog
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = structlog.get_logger(__name__)


class DocumentNotFoundError(Exception):
    """Raised when a document is not found."""

    def __init__(self, document_id: str) -> None:
        self.document_id = document_id
        super().__init__(f"Document not found: {document_id}")


class DocumentClientError(Exception):
    """Raised when a document client operation fails."""

    pass


class DocumentClient:
    """Async MongoDB client for document operations."""

    def __init__(self, mongodb_uri: str, database_name: str) -> None:
        """Initialize the document client.

        Args:
            mongodb_uri: MongoDB connection URI
            database_name: Name of the database to use
        """
        self._client: AsyncIOMotorClient = AsyncIOMotorClient(mongodb_uri)
        self._db: AsyncIOMotorDatabase = self._client[database_name]
        self._collection = self._db["documents"]

    def _build_query(
        self,
        source_id: str | None = None,
        farmer_id: str | None = None,
        linkage: dict[str, str] | None = None,
        attributes: dict[str, Any] | None = None,
        date_range: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Build a MongoDB query from filter parameters.

        Args:
            source_id: Filter by source ID
            farmer_id: Filter by farmer ID
            linkage: Filter by linkage fields (key-value pairs)
            attributes: Filter by attribute values (supports MongoDB operators)
            date_range: Filter by ingestion date range (start, end)

        Returns:
            MongoDB query dictionary
        """
        query: dict[str, Any] = {}

        if source_id:
            query["source_id"] = source_id

        if farmer_id:
            query["farmer_id"] = farmer_id

        if linkage:
            for key, value in linkage.items():
                query[f"linkage.{key}"] = value

        if attributes:
            for key, value in attributes.items():
                if isinstance(value, dict):
                    # MongoDB operators: {"$lt": 70, "$gt": 50}
                    query[f"attributes.{key}"] = value
                else:
                    # Direct equality match
                    query[f"attributes.{key}"] = value

        if date_range:
            start = date_range.get("start")
            end = date_range.get("end")
            if start and end:
                # Parse ISO strings to datetime if needed
                start_dt = datetime.fromisoformat(start.replace("Z", "+00:00")) if isinstance(start, str) else start
                end_dt = datetime.fromisoformat(end.replace("Z", "+00:00")) if isinstance(end, str) else end
                query["ingested_at"] = {"$gte": start_dt, "$lte": end_dt}

        return query

    async def get_documents(
        self,
        source_id: str | None = None,
        farmer_id: str | None = None,
        linkage: dict[str, str] | None = None,
        attributes: dict[str, Any] | None = None,
        date_range: dict[str, str] | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Query documents with flexible filters.

        Args:
            source_id: Filter by source ID
            farmer_id: Filter by farmer ID
            linkage: Filter by linkage fields
            attributes: Filter by attribute values (supports MongoDB operators)
            date_range: Filter by ingestion date range
            limit: Maximum number of results (default 50, max 1000)

        Returns:
            List of matching documents sorted by ingested_at descending
        """
        query = self._build_query(
            source_id=source_id,
            farmer_id=farmer_id,
            linkage=linkage,
            attributes=attributes,
            date_range=date_range,
        )

        # Enforce maximum limit
        limit = min(limit, 1000)

        logger.debug(
            "Querying documents",
            query=query,
            limit=limit,
        )

        cursor = self._collection.find(query).sort("ingested_at", -1).limit(limit)
        documents = await cursor.to_list(length=limit)

        # Convert ObjectId to string for JSON serialization
        for doc in documents:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])

        logger.info(
            "Documents query completed",
            count=len(documents),
            source_id=source_id,
            farmer_id=farmer_id,
        )

        return documents

    async def get_document_by_id(self, document_id: str) -> dict[str, Any]:
        """Get a single document by its document_id.

        Args:
            document_id: The document's unique identifier

        Returns:
            The document dictionary

        Raises:
            DocumentNotFoundError: If no document with the given ID exists
        """
        logger.debug("Getting document by ID", document_id=document_id)

        document = await self._collection.find_one({"document_id": document_id})

        if document is None:
            logger.warning("Document not found", document_id=document_id)
            raise DocumentNotFoundError(document_id)

        # Convert ObjectId to string
        if "_id" in document:
            document["_id"] = str(document["_id"])

        logger.info("Document retrieved", document_id=document_id)
        return document

    async def get_farmer_documents(
        self,
        farmer_id: str,
        source_ids: list[str] | None = None,
        date_range: dict[str, str] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get all documents for a specific farmer.

        Args:
            farmer_id: The farmer's ID
            source_ids: Optional list of source IDs to filter by
            date_range: Optional date range filter
            limit: Maximum number of results (default 100, max 1000)

        Returns:
            List of matching documents sorted by ingested_at descending
        """
        query: dict[str, Any] = {"farmer_id": farmer_id}

        if source_ids:
            query["source_id"] = {"$in": source_ids}

        if date_range:
            start = date_range.get("start")
            end = date_range.get("end")
            if start and end:
                start_dt = datetime.fromisoformat(start.replace("Z", "+00:00")) if isinstance(start, str) else start
                end_dt = datetime.fromisoformat(end.replace("Z", "+00:00")) if isinstance(end, str) else end
                query["ingested_at"] = {"$gte": start_dt, "$lte": end_dt}

        # Enforce maximum limit
        limit = min(limit, 1000)

        logger.debug(
            "Querying farmer documents",
            farmer_id=farmer_id,
            source_ids=source_ids,
            limit=limit,
        )

        cursor = self._collection.find(query).sort("ingested_at", -1).limit(limit)
        documents = await cursor.to_list(length=limit)

        # Convert ObjectId to string
        for doc in documents:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])

        logger.info(
            "Farmer documents query completed",
            farmer_id=farmer_id,
            count=len(documents),
        )

        return documents

    async def search_documents(
        self,
        query_text: str,
        source_ids: list[str] | None = None,
        farmer_id: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Full-text search across documents.

        Uses MongoDB text index if available, otherwise falls back to regex search.

        Args:
            query_text: The search query
            source_ids: Optional list of source IDs to search within
            farmer_id: Optional farmer ID filter
            limit: Maximum number of results (default 20, max 100)

        Returns:
            List of matching documents with relevance scoring
        """
        # Enforce maximum limit
        limit = min(limit, 100)

        # Build base filter
        filter_query: dict[str, Any] = {}
        if source_ids:
            filter_query["source_id"] = {"$in": source_ids}
        if farmer_id:
            filter_query["farmer_id"] = farmer_id

        logger.debug(
            "Searching documents",
            query=query_text,
            source_ids=source_ids,
            farmer_id=farmer_id,
            limit=limit,
        )

        # Try text search first (requires text index)
        try:
            text_query = {"$text": {"$search": query_text}, **filter_query}
            cursor = (
                self._collection.find(text_query, {"score": {"$meta": "textScore"}})
                .sort([("score", {"$meta": "textScore"})])
                .limit(limit)
            )
            documents = await cursor.to_list(length=limit)

            if documents:
                # Convert ObjectId and add relevance score
                for doc in documents:
                    if "_id" in doc:
                        doc["_id"] = str(doc["_id"])
                    doc["relevance_score"] = doc.pop("score", 0)

                logger.info(
                    "Text search completed",
                    query=query_text,
                    count=len(documents),
                )
                return documents
        except Exception as e:
            logger.debug(
                "Text search failed, falling back to regex",
                error=str(e),
            )

        # Fallback to regex search on common fields
        regex_pattern = {"$regex": query_text, "$options": "i"}
        regex_query = {
            "$or": [
                {"attributes": regex_pattern},
                {"document_id": regex_pattern},
            ],
            **filter_query,
        }

        cursor = self._collection.find(regex_query).limit(limit)
        documents = await cursor.to_list(length=limit)

        # Convert ObjectId
        for doc in documents:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            doc["relevance_score"] = 1.0  # Default score for regex matches

        logger.info(
            "Regex search completed",
            query=query_text,
            count=len(documents),
        )

        return documents

    async def close(self) -> None:
        """Close the MongoDB client connection."""
        self._client.close()
        logger.info("Document client connection closed")
