"""PlantationService gRPC implementation."""

import logging
from datetime import datetime, timezone
from typing import Optional, Set

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

# Valid values for enum-like fields
VALID_CP_STATUSES: Set[str] = {"active", "inactive", "seasonal"}
VALID_STORAGE_TYPES: Set[str] = {"covered_shed", "open_air", "refrigerated"}
VALID_COLLECTION_DAYS: Set[str] = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}

from fp_proto.plantation.v1 import plantation_pb2, plantation_pb2_grpc
from plantation_model.domain.models.factory import Factory
from plantation_model.domain.models.collection_point import CollectionPoint
from plantation_model.domain.models.value_objects import (
    CollectionPointCapacity,
    ContactInfo,
    GeoLocation,
    OperatingHours,
)
from plantation_model.domain.models.id_generator import IDGenerator
from plantation_model.infrastructure.repositories.factory_repository import (
    FactoryRepository,
)
from plantation_model.infrastructure.repositories.collection_point_repository import (
    CollectionPointRepository,
)
from plantation_model.infrastructure.google_elevation import GoogleElevationClient

logger = logging.getLogger(__name__)


def datetime_to_timestamp(dt: datetime) -> Timestamp:
    """Convert datetime to protobuf Timestamp."""
    ts = Timestamp()
    ts.FromDatetime(dt)
    return ts


def timestamp_to_datetime(ts: Timestamp) -> datetime:
    """Convert protobuf Timestamp to datetime."""
    return ts.ToDatetime().replace(tzinfo=timezone.utc)


class PlantationServiceServicer(plantation_pb2_grpc.PlantationServiceServicer):
    """gRPC servicer for Plantation operations."""

    def __init__(
        self,
        factory_repo: FactoryRepository,
        collection_point_repo: CollectionPointRepository,
        id_generator: IDGenerator,
        elevation_client: GoogleElevationClient,
    ) -> None:
        """Initialize the servicer.

        Args:
            factory_repo: Factory repository instance.
            collection_point_repo: Collection point repository instance.
            id_generator: ID generator instance.
            elevation_client: Google Elevation API client.
        """
        self._factory_repo = factory_repo
        self._cp_repo = collection_point_repo
        self._id_generator = id_generator
        self._elevation_client = elevation_client

    # =========================================================================
    # Factory Operations
    # =========================================================================

    def _factory_to_proto(self, factory: Factory) -> plantation_pb2.Factory:
        """Convert Factory domain model to protobuf message."""
        return plantation_pb2.Factory(
            id=factory.id,
            name=factory.name,
            code=factory.code,
            region_id=factory.region_id,
            location=plantation_pb2.GeoLocation(
                latitude=factory.location.latitude,
                longitude=factory.location.longitude,
                altitude_meters=factory.location.altitude_meters,
            ),
            contact=plantation_pb2.ContactInfo(
                phone=factory.contact.phone,
                email=factory.contact.email,
                address=factory.contact.address,
            ),
            processing_capacity_kg=factory.processing_capacity_kg,
            is_active=factory.is_active,
            created_at=datetime_to_timestamp(factory.created_at),
            updated_at=datetime_to_timestamp(factory.updated_at),
        )

    async def _get_altitude_for_location(
        self, latitude: float, longitude: float
    ) -> float:
        """Fetch altitude from Google Elevation API.

        Args:
            latitude: Latitude in decimal degrees.
            longitude: Longitude in decimal degrees.

        Returns:
            Altitude in meters, or 0.0 if unavailable.
        """
        altitude = await self._elevation_client.get_altitude(latitude, longitude)
        return altitude if altitude is not None else 0.0

    async def GetFactory(
        self,
        request: plantation_pb2.GetFactoryRequest,
        context: grpc.aio.ServicerContext,
    ) -> plantation_pb2.Factory:
        """Get a factory by ID."""
        factory = await self._factory_repo.get_by_id(request.id)
        if factory is None:
            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Factory {request.id} not found",
            )
        return self._factory_to_proto(factory)

    async def ListFactories(
        self,
        request: plantation_pb2.ListFactoriesRequest,
        context: grpc.aio.ServicerContext,
    ) -> plantation_pb2.ListFactoriesResponse:
        """List factories with optional filtering."""
        filters = {}
        if request.region_id:
            filters["region_id"] = request.region_id
        if request.active_only:
            filters["is_active"] = True

        page_size = request.page_size if request.page_size > 0 else 100
        page_token = request.page_token if request.page_token else None

        factories, next_token, total = await self._factory_repo.list(
            filters=filters if filters else None,
            page_size=page_size,
            page_token=page_token,
        )

        return plantation_pb2.ListFactoriesResponse(
            factories=[self._factory_to_proto(f) for f in factories],
            next_page_token=next_token or "",
            total_count=total,
        )

    async def CreateFactory(
        self,
        request: plantation_pb2.CreateFactoryRequest,
        context: grpc.aio.ServicerContext,
    ) -> plantation_pb2.Factory:
        """Create a new factory."""
        # Check for duplicate code
        existing = await self._factory_repo.get_by_code(request.code)
        if existing:
            await context.abort(
                grpc.StatusCode.ALREADY_EXISTS,
                f"Factory with code {request.code} already exists",
            )

        # Generate unique ID
        factory_id = await self._id_generator.generate_factory_id()

        # Fetch altitude from Google Elevation API
        altitude = await self._get_altitude_for_location(
            request.location.latitude,
            request.location.longitude,
        )

        # Create factory
        now = datetime.now(timezone.utc)
        factory = Factory(
            id=factory_id,
            name=request.name,
            code=request.code,
            region_id=request.region_id,
            location=GeoLocation(
                latitude=request.location.latitude,
                longitude=request.location.longitude,
                altitude_meters=altitude,
            ),
            contact=ContactInfo(
                phone=request.contact.phone if request.contact else "",
                email=request.contact.email if request.contact else "",
                address=request.contact.address if request.contact else "",
            ),
            processing_capacity_kg=request.processing_capacity_kg,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        await self._factory_repo.create(factory)
        logger.info("Created factory %s (%s)", factory.id, factory.name)

        return self._factory_to_proto(factory)

    async def UpdateFactory(
        self,
        request: plantation_pb2.UpdateFactoryRequest,
        context: grpc.aio.ServicerContext,
    ) -> plantation_pb2.Factory:
        """Update an existing factory."""
        # Build updates dict from optional fields
        updates = {}

        if request.HasField("name"):
            updates["name"] = request.name
        if request.HasField("code"):
            # Check for duplicate code
            existing = await self._factory_repo.get_by_code(request.code)
            if existing and existing.id != request.id:
                await context.abort(
                    grpc.StatusCode.ALREADY_EXISTS,
                    f"Factory with code {request.code} already exists",
                )
            updates["code"] = request.code
        if request.HasField("location"):
            # Fetch new altitude for updated location
            altitude = await self._get_altitude_for_location(
                request.location.latitude,
                request.location.longitude,
            )
            updates["location"] = GeoLocation(
                latitude=request.location.latitude,
                longitude=request.location.longitude,
                altitude_meters=altitude,
            ).model_dump()
        if request.HasField("contact"):
            updates["contact"] = ContactInfo(
                phone=request.contact.phone,
                email=request.contact.email,
                address=request.contact.address,
            ).model_dump()
        if request.HasField("processing_capacity_kg"):
            updates["processing_capacity_kg"] = request.processing_capacity_kg
        if request.HasField("is_active"):
            updates["is_active"] = request.is_active

        if not updates:
            # No updates, just return current factory
            factory = await self._factory_repo.get_by_id(request.id)
            if factory is None:
                await context.abort(
                    grpc.StatusCode.NOT_FOUND,
                    f"Factory {request.id} not found",
                )
            return self._factory_to_proto(factory)

        factory = await self._factory_repo.update(request.id, updates)
        if factory is None:
            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Factory {request.id} not found",
            )

        logger.info("Updated factory %s", factory.id)
        return self._factory_to_proto(factory)

    async def DeleteFactory(
        self,
        request: plantation_pb2.DeleteFactoryRequest,
        context: grpc.aio.ServicerContext,
    ) -> plantation_pb2.DeleteFactoryResponse:
        """Delete a factory by ID."""
        # Check if factory has any collection points
        cps, _, count = await self._cp_repo.list(
            filters={"factory_id": request.id},
            page_size=1,
        )
        if count > 0:
            await context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                f"Cannot delete factory {request.id}: {count} collection point(s) still exist. Delete them first.",
            )

        deleted = await self._factory_repo.delete(request.id)
        if not deleted:
            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Factory {request.id} not found",
            )

        logger.info("Deleted factory %s", request.id)
        return plantation_pb2.DeleteFactoryResponse(success=True)

    # =========================================================================
    # Collection Point Operations
    # =========================================================================

    def _cp_to_proto(self, cp: CollectionPoint) -> plantation_pb2.CollectionPoint:
        """Convert CollectionPoint domain model to protobuf message."""
        return plantation_pb2.CollectionPoint(
            id=cp.id,
            name=cp.name,
            factory_id=cp.factory_id,
            location=plantation_pb2.GeoLocation(
                latitude=cp.location.latitude,
                longitude=cp.location.longitude,
                altitude_meters=cp.location.altitude_meters,
            ),
            region_id=cp.region_id,
            clerk_id=cp.clerk_id or "",
            clerk_phone=cp.clerk_phone or "",
            operating_hours=plantation_pb2.OperatingHours(
                weekdays=cp.operating_hours.weekdays,
                weekends=cp.operating_hours.weekends,
            ),
            collection_days=cp.collection_days,
            capacity=plantation_pb2.CollectionPointCapacity(
                max_daily_kg=cp.capacity.max_daily_kg,
                storage_type=cp.capacity.storage_type,
                has_weighing_scale=cp.capacity.has_weighing_scale,
                has_qc_device=cp.capacity.has_qc_device,
            ),
            status=cp.status,
            created_at=datetime_to_timestamp(cp.created_at),
            updated_at=datetime_to_timestamp(cp.updated_at),
        )

    async def GetCollectionPoint(
        self,
        request: plantation_pb2.GetCollectionPointRequest,
        context: grpc.aio.ServicerContext,
    ) -> plantation_pb2.CollectionPoint:
        """Get a collection point by ID."""
        cp = await self._cp_repo.get_by_id(request.id)
        if cp is None:
            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Collection point {request.id} not found",
            )
        return self._cp_to_proto(cp)

    async def ListCollectionPoints(
        self,
        request: plantation_pb2.ListCollectionPointsRequest,
        context: grpc.aio.ServicerContext,
    ) -> plantation_pb2.ListCollectionPointsResponse:
        """List collection points with optional filtering."""
        filters = {}
        if request.factory_id:
            filters["factory_id"] = request.factory_id
        if request.region_id:
            filters["region_id"] = request.region_id
        if request.status:
            filters["status"] = request.status
        if request.active_only:
            filters["status"] = "active"

        page_size = request.page_size if request.page_size > 0 else 100
        page_token = request.page_token if request.page_token else None

        cps, next_token, total = await self._cp_repo.list(
            filters=filters if filters else None,
            page_size=page_size,
            page_token=page_token,
        )

        return plantation_pb2.ListCollectionPointsResponse(
            collection_points=[self._cp_to_proto(cp) for cp in cps],
            next_page_token=next_token or "",
            total_count=total,
        )

    async def CreateCollectionPoint(
        self,
        request: plantation_pb2.CreateCollectionPointRequest,
        context: grpc.aio.ServicerContext,
    ) -> plantation_pb2.CollectionPoint:
        """Create a new collection point."""
        # Validate enum-like fields
        if request.status and request.status not in VALID_CP_STATUSES:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"Invalid status '{request.status}'. Must be one of: {', '.join(sorted(VALID_CP_STATUSES))}",
            )
        if request.capacity and request.capacity.storage_type:
            if request.capacity.storage_type not in VALID_STORAGE_TYPES:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"Invalid storage_type '{request.capacity.storage_type}'. Must be one of: {', '.join(sorted(VALID_STORAGE_TYPES))}",
                )
        if request.collection_days:
            invalid_days = set(request.collection_days) - VALID_COLLECTION_DAYS
            if invalid_days:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"Invalid collection_days: {', '.join(sorted(invalid_days))}. Must be one of: {', '.join(sorted(VALID_COLLECTION_DAYS))}",
                )

        # Verify factory exists
        factory = await self._factory_repo.get_by_id(request.factory_id)
        if factory is None:
            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Factory {request.factory_id} not found",
            )

        # Generate unique ID using region_id
        cp_id = await self._id_generator.generate_collection_point_id(request.region_id)

        # Fetch altitude from Google Elevation API
        altitude = await self._get_altitude_for_location(
            request.location.latitude,
            request.location.longitude,
        )

        # Create collection point
        now = datetime.now(timezone.utc)
        cp = CollectionPoint(
            id=cp_id,
            name=request.name,
            factory_id=request.factory_id,
            location=GeoLocation(
                latitude=request.location.latitude,
                longitude=request.location.longitude,
                altitude_meters=altitude,
            ),
            region_id=request.region_id,
            clerk_id=request.clerk_id if request.clerk_id else None,
            clerk_phone=request.clerk_phone if request.clerk_phone else None,
            operating_hours=OperatingHours(
                weekdays=request.operating_hours.weekdays
                if request.operating_hours
                else "06:00-10:00",
                weekends=request.operating_hours.weekends
                if request.operating_hours
                else "07:00-09:00",
            ),
            collection_days=list(request.collection_days)
            if request.collection_days
            else ["mon", "wed", "fri", "sat"],
            capacity=CollectionPointCapacity(
                max_daily_kg=request.capacity.max_daily_kg if request.capacity else 0,
                storage_type=request.capacity.storage_type
                if request.capacity
                else "covered_shed",
                has_weighing_scale=request.capacity.has_weighing_scale
                if request.capacity
                else False,
                has_qc_device=request.capacity.has_qc_device
                if request.capacity
                else False,
            ),
            status=request.status if request.status else "active",
            created_at=now,
            updated_at=now,
        )

        await self._cp_repo.create(cp)
        logger.info("Created collection point %s (%s)", cp.id, cp.name)

        return self._cp_to_proto(cp)

    async def UpdateCollectionPoint(
        self,
        request: plantation_pb2.UpdateCollectionPointRequest,
        context: grpc.aio.ServicerContext,
    ) -> plantation_pb2.CollectionPoint:
        """Update an existing collection point."""
        # Validate enum-like fields if provided
        if request.HasField("status") and request.status not in VALID_CP_STATUSES:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"Invalid status '{request.status}'. Must be one of: {', '.join(sorted(VALID_CP_STATUSES))}",
            )
        if request.HasField("capacity") and request.capacity.storage_type:
            if request.capacity.storage_type not in VALID_STORAGE_TYPES:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"Invalid storage_type '{request.capacity.storage_type}'. Must be one of: {', '.join(sorted(VALID_STORAGE_TYPES))}",
                )
        if request.collection_days:
            invalid_days = set(request.collection_days) - VALID_COLLECTION_DAYS
            if invalid_days:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"Invalid collection_days: {', '.join(sorted(invalid_days))}. Must be one of: {', '.join(sorted(VALID_COLLECTION_DAYS))}",
                )

        # Build updates dict from optional fields
        updates = {}

        if request.HasField("name"):
            updates["name"] = request.name
        if request.HasField("clerk_id"):
            updates["clerk_id"] = request.clerk_id
        if request.HasField("clerk_phone"):
            updates["clerk_phone"] = request.clerk_phone
        if request.HasField("operating_hours"):
            updates["operating_hours"] = OperatingHours(
                weekdays=request.operating_hours.weekdays,
                weekends=request.operating_hours.weekends,
            ).model_dump()
        if request.collection_days:
            updates["collection_days"] = list(request.collection_days)
        if request.HasField("capacity"):
            updates["capacity"] = CollectionPointCapacity(
                max_daily_kg=request.capacity.max_daily_kg,
                storage_type=request.capacity.storage_type,
                has_weighing_scale=request.capacity.has_weighing_scale,
                has_qc_device=request.capacity.has_qc_device,
            ).model_dump()
        if request.HasField("status"):
            updates["status"] = request.status

        if not updates:
            # No updates, just return current collection point
            cp = await self._cp_repo.get_by_id(request.id)
            if cp is None:
                await context.abort(
                    grpc.StatusCode.NOT_FOUND,
                    f"Collection point {request.id} not found",
                )
            return self._cp_to_proto(cp)

        cp = await self._cp_repo.update(request.id, updates)
        if cp is None:
            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Collection point {request.id} not found",
            )

        logger.info("Updated collection point %s", cp.id)
        return self._cp_to_proto(cp)

    async def DeleteCollectionPoint(
        self,
        request: plantation_pb2.DeleteCollectionPointRequest,
        context: grpc.aio.ServicerContext,
    ) -> plantation_pb2.DeleteCollectionPointResponse:
        """Delete a collection point by ID."""
        deleted = await self._cp_repo.delete(request.id)
        if not deleted:
            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Collection point {request.id} not found",
            )

        logger.info("Deleted collection point %s", request.id)
        return plantation_pb2.DeleteCollectionPointResponse(success=True)
