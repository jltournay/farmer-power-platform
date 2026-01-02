"""Collection Model gRPC Service - Document Query API.

Story 0.5.1a: Implements CollectionService gRPC interface for BFF queries.
ADR-011: gRPC server runs on port 50051 alongside FastAPI health on port 8000.

This module provides:
- CollectionServiceServicer: gRPC handler implementation
- serve_grpc: Async function to start gRPC server
"""

from datetime import UTC, datetime
from typing import Any

import grpc
import structlog
from collection_model.domain.document_index import DocumentIndex
from collection_model.infrastructure.document_repository import DocumentRepository
from fp_proto.collection.v1 import collection_pb2, collection_pb2_grpc
from google.protobuf import timestamp_pb2
from motor.motor_asyncio import AsyncIOMotorDatabase

__all__ = ["CollectionServiceServicer", "serve_grpc"]

logger = structlog.get_logger(__name__)


def _datetime_to_proto_timestamp(dt: datetime) -> timestamp_pb2.Timestamp:
    """Convert Python datetime to protobuf Timestamp."""
    ts = timestamp_pb2.Timestamp()
    ts.FromDatetime(dt)
    return ts


def _proto_timestamp_to_datetime(ts: timestamp_pb2.Timestamp) -> datetime | None:
    """Convert protobuf Timestamp to Python datetime."""
    if ts.seconds == 0 and ts.nanos == 0:
        return None
    return ts.ToDatetime(tzinfo=UTC)


def _dict_to_string_map(d: dict[str, Any]) -> dict[str, str]:
    """Convert dict with any values to string map for proto compatibility."""
    return {k: str(v) for k, v in d.items()}


def _document_index_to_proto(doc: DocumentIndex) -> collection_pb2.Document:
    """Convert DocumentIndex Pydantic model to proto Document message."""
    return collection_pb2.Document(
        document_id=doc.document_id,
        raw_document=collection_pb2.RawDocumentRef(
            blob_container=doc.raw_document.blob_container,
            blob_path=doc.raw_document.blob_path,
            content_hash=doc.raw_document.content_hash,
            size_bytes=doc.raw_document.size_bytes,
            stored_at=_datetime_to_proto_timestamp(doc.raw_document.stored_at),
        ),
        extraction=collection_pb2.ExtractionMetadata(
            ai_agent_id=doc.extraction.ai_agent_id,
            extraction_timestamp=_datetime_to_proto_timestamp(doc.extraction.extraction_timestamp),
            confidence=doc.extraction.confidence,
            validation_passed=doc.extraction.validation_passed,
            validation_warnings=doc.extraction.validation_warnings,
        ),
        ingestion=collection_pb2.IngestionMetadata(
            ingestion_id=doc.ingestion.ingestion_id,
            source_id=doc.ingestion.source_id,
            received_at=_datetime_to_proto_timestamp(doc.ingestion.received_at),
            processed_at=_datetime_to_proto_timestamp(doc.ingestion.processed_at),
        ),
        extracted_fields=_dict_to_string_map(doc.extracted_fields),
        linkage_fields=_dict_to_string_map(doc.linkage_fields),
        created_at=_datetime_to_proto_timestamp(doc.created_at),
    )


class CollectionServiceServicer(collection_pb2_grpc.CollectionServiceServicer):
    """gRPC service implementation for Collection Model document queries.

    This servicer implements 4 document query methods:
    - GetDocument: Retrieve single document by ID
    - ListDocuments: Paginated list with optional farmer_id filter
    - GetDocumentsByFarmer: All documents for a specific farmer
    - SearchDocuments: Advanced search with multiple filters

    ADR-011 compliant: Pure query-only, no mutations exposed via gRPC.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the gRPC servicer with MongoDB database.

        Args:
            db: Async MongoDB database connection.
        """
        self.db = db
        self.document_repository = DocumentRepository(db)

    async def GetDocument(
        self,
        request: collection_pb2.GetDocumentRequest,
        context: grpc.aio.ServicerContext,
    ) -> collection_pb2.Document:
        """Get a single document by ID.

        Args:
            request: Contains document_id and collection_name.
            context: gRPC context for setting error codes.

        Returns:
            Document if found.

        Raises:
            NOT_FOUND if document doesn't exist.
            INVALID_ARGUMENT if required fields missing.
        """
        if not request.document_id:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "document_id is required")
            return collection_pb2.Document()  # Never reached, satisfies type checker

        if not request.collection_name:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "collection_name is required")
            return collection_pb2.Document()

        logger.info(
            "GetDocument request",
            document_id=request.document_id,
            collection_name=request.collection_name,
        )

        doc = await self.document_repository.get_by_id(
            document_id=request.document_id,
            collection_name=request.collection_name,
        )

        if doc is None:
            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Document not found: {request.document_id}",
            )
            return collection_pb2.Document()

        return _document_index_to_proto(doc)

    async def ListDocuments(
        self,
        request: collection_pb2.ListDocumentsRequest,
        context: grpc.aio.ServicerContext,
    ) -> collection_pb2.ListDocumentsResponse:
        """List documents with pagination and optional farmer_id filter.

        Args:
            request: Contains pagination params and optional farmer_id.
            context: gRPC context.

        Returns:
            ListDocumentsResponse with documents and pagination token.
        """
        if not request.collection_name:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "collection_name is required")
            return collection_pb2.ListDocumentsResponse()

        # Default and cap page size
        page_size = min(request.page_size or 20, 100)

        logger.info(
            "ListDocuments request",
            collection_name=request.collection_name,
            farmer_id=request.farmer_id or None,
            page_size=page_size,
            page_token=request.page_token or None,
        )

        collection = self.db[request.collection_name]

        # Build query
        query: dict[str, Any] = {}
        if request.farmer_id:
            query["linkage_fields.farmer_id"] = request.farmer_id

        # Handle pagination via skip (page_token is skip count encoded as string)
        skip = 0
        if request.page_token:
            try:
                skip = int(request.page_token)
                if skip < 0:
                    logger.warning("Negative page_token received, resetting to 0", page_token=request.page_token)
                    skip = 0
            except ValueError:
                logger.warning("Invalid page_token format, resetting to 0", page_token=request.page_token)
                skip = 0

        # Execute query
        cursor = collection.find(query).sort("created_at", -1).skip(skip).limit(page_size + 1)

        documents: list[collection_pb2.Document] = []
        has_more = False

        async for raw_doc in cursor:
            if len(documents) >= page_size:
                has_more = True
                break
            doc = DocumentIndex.model_validate(raw_doc)
            documents.append(_document_index_to_proto(doc))

        # Get total count
        total_count = await collection.count_documents(query)

        # Build next page token
        next_page_token = ""
        if has_more:
            next_page_token = str(skip + page_size)

        return collection_pb2.ListDocumentsResponse(
            documents=documents,
            next_page_token=next_page_token,
            total_count=total_count,
        )

    async def GetDocumentsByFarmer(
        self,
        request: collection_pb2.GetDocumentsByFarmerRequest,
        context: grpc.aio.ServicerContext,
    ) -> collection_pb2.GetDocumentsByFarmerResponse:
        """Get all documents for a specific farmer.

        Convenience method that queries by linkage_fields.farmer_id.

        Args:
            request: Contains farmer_id, collection_name, and optional limit.
            context: gRPC context.

        Returns:
            GetDocumentsByFarmerResponse with documents.
        """
        if not request.farmer_id:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "farmer_id is required")
            return collection_pb2.GetDocumentsByFarmerResponse()

        if not request.collection_name:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "collection_name is required")
            return collection_pb2.GetDocumentsByFarmerResponse()

        # Default and cap limit
        limit = min(request.limit or 100, 1000)

        logger.info(
            "GetDocumentsByFarmer request",
            farmer_id=request.farmer_id,
            collection_name=request.collection_name,
            limit=limit,
        )

        docs = await self.document_repository.find_by_linkage(
            link_field="farmer_id",
            link_value=request.farmer_id,
            collection_name=request.collection_name,
            limit=limit,
        )

        proto_docs = [_document_index_to_proto(doc) for doc in docs]

        return collection_pb2.GetDocumentsByFarmerResponse(
            documents=proto_docs,
            total_count=len(proto_docs),
        )

    async def SearchDocuments(
        self,
        request: collection_pb2.SearchDocumentsRequest,
        context: grpc.aio.ServicerContext,
    ) -> collection_pb2.SearchDocumentsResponse:
        """Search documents with filters (source_id, date range, linkage fields).

        Args:
            request: Contains search filters and pagination.
            context: gRPC context.

        Returns:
            SearchDocumentsResponse with matching documents.
        """
        if not request.collection_name:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "collection_name is required")
            return collection_pb2.SearchDocumentsResponse()

        # Default and cap page size
        page_size = min(request.page_size or 20, 100)

        logger.info(
            "SearchDocuments request",
            collection_name=request.collection_name,
            source_id=request.source_id or None,
            page_size=page_size,
        )

        collection = self.db[request.collection_name]

        # Build query
        query: dict[str, Any] = {}

        # Source ID filter
        if request.source_id:
            query["ingestion.source_id"] = request.source_id

        # Date range filters
        start_date = _proto_timestamp_to_datetime(request.start_date)
        end_date = _proto_timestamp_to_datetime(request.end_date)

        if start_date or end_date:
            date_query: dict[str, Any] = {}
            if start_date:
                date_query["$gte"] = start_date
            if end_date:
                date_query["$lte"] = end_date
            if date_query:
                query["created_at"] = date_query

        # Linkage field filters
        for field_name, field_value in request.linkage_filters.items():
            query[f"linkage_fields.{field_name}"] = field_value

        # Handle pagination
        skip = 0
        if request.page_token:
            try:
                skip = int(request.page_token)
                if skip < 0:
                    logger.warning("Negative page_token received, resetting to 0", page_token=request.page_token)
                    skip = 0
            except ValueError:
                logger.warning("Invalid page_token format, resetting to 0", page_token=request.page_token)
                skip = 0

        # Execute query
        cursor = collection.find(query).sort("created_at", -1).skip(skip).limit(page_size + 1)

        documents: list[collection_pb2.Document] = []
        has_more = False

        async for raw_doc in cursor:
            if len(documents) >= page_size:
                has_more = True
                break
            doc = DocumentIndex.model_validate(raw_doc)
            documents.append(_document_index_to_proto(doc))

        # Get total count
        total_count = await collection.count_documents(query)

        # Build next page token
        next_page_token = ""
        if has_more:
            next_page_token = str(skip + page_size)

        return collection_pb2.SearchDocumentsResponse(
            documents=documents,
            next_page_token=next_page_token,
            total_count=total_count,
        )


async def serve_grpc(
    db: AsyncIOMotorDatabase,
    host: str = "0.0.0.0",
    port: int = 50051,
) -> grpc.aio.Server:
    """Start the gRPC server.

    Args:
        db: MongoDB database connection.
        host: Host to bind to.
        port: Port to listen on.

    Returns:
        Running gRPC server instance.
    """
    server = grpc.aio.server()
    collection_pb2_grpc.add_CollectionServiceServicer_to_server(CollectionServiceServicer(db), server)
    server.add_insecure_port(f"{host}:{port}")
    await server.start()
    logger.info("gRPC server started", host=host, port=port)
    return server
