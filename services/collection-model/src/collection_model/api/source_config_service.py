"""SourceConfig gRPC Service - Read-only admin visibility (ADR-019).

Story 9.11a: Implements SourceConfigService gRPC interface for Admin UI queries.
This is a read-only service - write operations are handled by the source-config CLI.

This module provides:
- SourceConfigServiceServicer: gRPC handler implementation for source config queries
"""

import grpc
import structlog
from collection_model.infrastructure.repositories.source_config_repository import SourceConfigRepository
from fp_common.converters import (
    source_config_response_to_proto,
    source_config_summary_to_proto,
)
from fp_proto.collection.v1 import collection_pb2, collection_pb2_grpc
from motor.motor_asyncio import AsyncIOMotorDatabase

__all__ = ["SourceConfigServiceServicer"]

logger = structlog.get_logger(__name__)


class SourceConfigServiceServicer(collection_pb2_grpc.SourceConfigServiceServicer):
    """gRPC service implementation for SourceConfig read-only queries (ADR-019).

    This servicer implements 2 query methods:
    - ListSourceConfigs: Paginated list with optional filters (enabled_only, ingestion_mode)
    - GetSourceConfig: Single config by source_id with full JSON

    ADR-019 compliant: Pure query-only, no mutations exposed via gRPC.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """Initialize the gRPC servicer with MongoDB database.

        Args:
            db: Async MongoDB database connection.
        """
        self.repository = SourceConfigRepository(db)

    async def ListSourceConfigs(
        self,
        request: collection_pb2.ListSourceConfigsRequest,
        context: grpc.aio.ServicerContext,
    ) -> collection_pb2.ListSourceConfigsResponse:
        """List source configs with optional filters and pagination.

        Args:
            request: Contains pagination params and optional filters
                (enabled_only, ingestion_mode).
            context: gRPC context.

        Returns:
            ListSourceConfigsResponse with configs, pagination token, and total count.
        """
        # Default and cap page size
        page_size = min(request.page_size or 20, 100)

        # Handle pagination via skip (page_token is skip count encoded as string)
        skip = 0
        if request.page_token:
            try:
                skip = int(request.page_token)
                if skip < 0:
                    logger.warning(
                        "Negative page_token received, resetting to 0",
                        page_token=request.page_token,
                    )
                    skip = 0
            except ValueError:
                logger.warning(
                    "Invalid page_token format, resetting to 0",
                    page_token=request.page_token,
                )
                skip = 0

        # Convert proto filter to repository filter
        ingestion_mode = request.ingestion_mode if request.ingestion_mode else None

        logger.info(
            "ListSourceConfigs request",
            page_size=page_size,
            page_token=request.page_token or None,
            enabled_only=request.enabled_only,
            ingestion_mode=ingestion_mode,
        )

        # Get total count for pagination
        total_count = await self.repository.count(
            enabled_only=request.enabled_only,
            ingestion_mode=ingestion_mode,
        )

        # Fetch one extra to detect if there are more results
        configs = await self.repository.list_all(
            page_size=page_size + 1,
            skip=skip,
            enabled_only=request.enabled_only,
            ingestion_mode=ingestion_mode,
        )

        # Check if there are more results
        has_more = len(configs) > page_size
        if has_more:
            configs = configs[:page_size]

        # Convert to proto summaries
        # Note: SourceConfig doesn't have timestamps, so we pass None
        proto_configs = [source_config_summary_to_proto(config, updated_at=None) for config in configs]

        # Build next page token
        next_page_token = ""
        if has_more:
            next_page_token = str(skip + page_size)

        return collection_pb2.ListSourceConfigsResponse(
            configs=proto_configs,
            next_page_token=next_page_token,
            total_count=total_count,
        )

    async def GetSourceConfig(
        self,
        request: collection_pb2.GetSourceConfigRequest,
        context: grpc.aio.ServicerContext,
    ) -> collection_pb2.SourceConfigResponse:
        """Get a single source config by ID with full JSON.

        Args:
            request: Contains source_id.
            context: gRPC context for setting error codes.

        Returns:
            SourceConfigResponse with full config as JSON.

        Raises:
            INVALID_ARGUMENT if source_id is empty.
            NOT_FOUND if source_id doesn't exist.
        """
        if not request.source_id:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "source_id is required")
            return collection_pb2.SourceConfigResponse()

        logger.info("GetSourceConfig request", source_id=request.source_id)

        config = await self.repository.get_by_source_id(request.source_id)

        if config is None:
            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Source config not found: {request.source_id}",
            )
            return collection_pb2.SourceConfigResponse()

        # Convert to proto response
        # Note: SourceConfig doesn't have timestamps, so we pass None
        return source_config_response_to_proto(config, created_at=None, updated_at=None)
