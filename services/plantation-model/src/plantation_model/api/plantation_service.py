"""PlantationService gRPC implementation."""

import logging
from datetime import UTC, datetime

import grpc
from fp_proto.plantation.v1 import plantation_pb2, plantation_pb2_grpc
from google.protobuf.timestamp_pb2 import Timestamp
from plantation_model.config import settings
from plantation_model.domain.events.farmer_events import FarmerRegisteredEvent
from plantation_model.domain.models.collection_point import CollectionPoint
from plantation_model.domain.models.factory import Factory
from plantation_model.domain.models.farmer import (
    Farmer,
    FarmScale,
    InteractionPreference,
    NotificationChannel,
    PreferredLanguage,
)
from plantation_model.domain.models.farmer_performance import (
    FarmerPerformance,
    TrendDirection,
)
from plantation_model.domain.models.grading_model import (
    ConditionalReject,
    GradeRules,
    GradingAttribute,
    GradingModel,
    GradingType,
)
from plantation_model.domain.models.id_generator import IDGenerator
from plantation_model.domain.models.value_objects import (
    CollectionPointCapacity,
    ContactInfo,
    GeoLocation,
    OperatingHours,
    QualityThresholds,
)
from plantation_model.infrastructure.dapr_client import DaprPubSubClient
from plantation_model.infrastructure.google_elevation import (
    GoogleElevationClient,
    assign_region_from_altitude,
)
from plantation_model.infrastructure.repositories.collection_point_repository import (
    CollectionPointRepository,
)
from plantation_model.infrastructure.repositories.factory_repository import (
    FactoryRepository,
)
from plantation_model.infrastructure.repositories.farmer_performance_repository import (
    FarmerPerformanceRepository,
)
from plantation_model.infrastructure.repositories.farmer_repository import (
    FarmerRepository,
)
from plantation_model.infrastructure.repositories.grading_model_repository import (
    GradingModelRepository,
)

logger = logging.getLogger(__name__)

# Valid values for enum-like fields
VALID_CP_STATUSES: set[str] = {"active", "inactive", "seasonal"}
VALID_STORAGE_TYPES: set[str] = {"covered_shed", "open_air", "refrigerated"}
VALID_COLLECTION_DAYS: set[str] = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}


def datetime_to_timestamp(dt: datetime) -> Timestamp:
    """Convert datetime to protobuf Timestamp."""
    ts = Timestamp()
    ts.FromDatetime(dt)
    return ts


def timestamp_to_datetime(ts: Timestamp) -> datetime:
    """Convert protobuf Timestamp to datetime."""
    return ts.ToDatetime().replace(tzinfo=UTC)


class PlantationServiceServicer(plantation_pb2_grpc.PlantationServiceServicer):
    """gRPC servicer for Plantation operations."""

    def __init__(
        self,
        factory_repo: FactoryRepository,
        collection_point_repo: CollectionPointRepository,
        farmer_repo: FarmerRepository,
        id_generator: IDGenerator,
        elevation_client: GoogleElevationClient,
        dapr_client: DaprPubSubClient | None = None,
        grading_model_repo: GradingModelRepository | None = None,
        farmer_performance_repo: FarmerPerformanceRepository | None = None,
    ) -> None:
        """Initialize the servicer.

        Args:
            factory_repo: Factory repository instance.
            collection_point_repo: Collection point repository instance.
            farmer_repo: Farmer repository instance.
            id_generator: ID generator instance.
            elevation_client: Google Elevation API client.
            dapr_client: Optional Dapr pub/sub client for event publishing.
            grading_model_repo: Optional grading model repository instance.
            farmer_performance_repo: Optional farmer performance repository instance.

        """
        self._factory_repo = factory_repo
        self._cp_repo = collection_point_repo
        self._farmer_repo = farmer_repo
        self._id_generator = id_generator
        self._elevation_client = elevation_client
        self._dapr_client = dapr_client or DaprPubSubClient()
        self._grading_model_repo = grading_model_repo
        self._farmer_performance_repo = farmer_performance_repo

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
            quality_thresholds=plantation_pb2.QualityThresholds(
                tier_1=factory.quality_thresholds.tier_1,
                tier_2=factory.quality_thresholds.tier_2,
                tier_3=factory.quality_thresholds.tier_3,
            ),
            is_active=factory.is_active,
            created_at=datetime_to_timestamp(factory.created_at),
            updated_at=datetime_to_timestamp(factory.updated_at),
        )

    async def _get_altitude_for_location(self, latitude: float, longitude: float) -> float:
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
        now = datetime.now(UTC)
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
            quality_thresholds=QualityThresholds(
                tier_1=request.quality_thresholds.tier_1
                if request.HasField("quality_thresholds") and request.quality_thresholds.tier_1
                else 85.0,
                tier_2=request.quality_thresholds.tier_2
                if request.HasField("quality_thresholds") and request.quality_thresholds.tier_2
                else 70.0,
                tier_3=request.quality_thresholds.tier_3
                if request.HasField("quality_thresholds") and request.quality_thresholds.tier_3
                else 50.0,
            ),
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
        if request.HasField("quality_thresholds"):
            updates["quality_thresholds"] = QualityThresholds(
                tier_1=request.quality_thresholds.tier_1,
                tier_2=request.quality_thresholds.tier_2,
                tier_3=request.quality_thresholds.tier_3,
            ).model_dump()
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
        _cps, _, count = await self._cp_repo.list(
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
        if (
            request.capacity
            and request.capacity.storage_type
            and request.capacity.storage_type not in VALID_STORAGE_TYPES
        ):
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
        now = datetime.now(UTC)
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
                if request.operating_hours and request.operating_hours.weekdays
                else OperatingHours().weekdays,
                weekends=request.operating_hours.weekends
                if request.operating_hours and request.operating_hours.weekends
                else OperatingHours().weekends,
            ),
            collection_days=list(request.collection_days)
            if request.collection_days
            else CollectionPoint.model_fields["collection_days"].default_factory(),
            capacity=CollectionPointCapacity(
                max_daily_kg=request.capacity.max_daily_kg
                if request.capacity
                else CollectionPointCapacity().max_daily_kg,
                storage_type=request.capacity.storage_type
                if request.capacity and request.capacity.storage_type
                else CollectionPointCapacity().storage_type,
                has_weighing_scale=request.capacity.has_weighing_scale
                if request.capacity
                else CollectionPointCapacity().has_weighing_scale,
                has_qc_device=request.capacity.has_qc_device
                if request.capacity
                else CollectionPointCapacity().has_qc_device,
            ),
            status=request.status if request.status else CollectionPoint.model_fields["status"].default,
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
        if (
            request.HasField("capacity")
            and request.capacity.storage_type
            and request.capacity.storage_type not in VALID_STORAGE_TYPES
        ):
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

    # =========================================================================
    # Farmer Operations
    # =========================================================================

    def _farm_scale_to_proto(self, farm_scale: FarmScale) -> plantation_pb2.FarmScale:
        """Convert FarmScale domain enum to protobuf enum."""
        mapping = {
            FarmScale.SMALLHOLDER: plantation_pb2.FARM_SCALE_SMALLHOLDER,
            FarmScale.MEDIUM: plantation_pb2.FARM_SCALE_MEDIUM,
            FarmScale.ESTATE: plantation_pb2.FARM_SCALE_ESTATE,
        }
        return mapping.get(farm_scale, plantation_pb2.FARM_SCALE_UNSPECIFIED)

    def _notification_channel_to_proto(self, channel: NotificationChannel) -> plantation_pb2.NotificationChannel:
        """Convert NotificationChannel domain enum to protobuf enum."""
        mapping = {
            NotificationChannel.SMS: plantation_pb2.NOTIFICATION_CHANNEL_SMS,
            NotificationChannel.WHATSAPP: plantation_pb2.NOTIFICATION_CHANNEL_WHATSAPP,
        }
        return mapping.get(channel, plantation_pb2.NOTIFICATION_CHANNEL_UNSPECIFIED)

    def _notification_channel_from_proto(self, channel: plantation_pb2.NotificationChannel) -> NotificationChannel:
        """Convert protobuf NotificationChannel enum to domain enum."""
        mapping = {
            plantation_pb2.NOTIFICATION_CHANNEL_SMS: NotificationChannel.SMS,
            plantation_pb2.NOTIFICATION_CHANNEL_WHATSAPP: NotificationChannel.WHATSAPP,
        }
        return mapping.get(channel, NotificationChannel.SMS)

    def _interaction_pref_to_proto(self, pref: InteractionPreference) -> plantation_pb2.InteractionPreference:
        """Convert InteractionPreference domain enum to protobuf enum."""
        mapping = {
            InteractionPreference.TEXT: plantation_pb2.INTERACTION_PREFERENCE_TEXT,
            InteractionPreference.VOICE: plantation_pb2.INTERACTION_PREFERENCE_VOICE,
        }
        return mapping.get(pref, plantation_pb2.INTERACTION_PREFERENCE_UNSPECIFIED)

    def _interaction_pref_from_proto(self, pref: plantation_pb2.InteractionPreference) -> InteractionPreference:
        """Convert protobuf InteractionPreference enum to domain enum."""
        mapping = {
            plantation_pb2.INTERACTION_PREFERENCE_TEXT: InteractionPreference.TEXT,
            plantation_pb2.INTERACTION_PREFERENCE_VOICE: InteractionPreference.VOICE,
        }
        return mapping.get(pref, InteractionPreference.TEXT)

    def _pref_lang_to_proto(self, lang: PreferredLanguage) -> plantation_pb2.PreferredLanguage:
        """Convert PreferredLanguage domain enum to protobuf enum."""
        mapping = {
            PreferredLanguage.SWAHILI: plantation_pb2.PREFERRED_LANGUAGE_SW,
            PreferredLanguage.KIKUYU: plantation_pb2.PREFERRED_LANGUAGE_KI,
            PreferredLanguage.LUO: plantation_pb2.PREFERRED_LANGUAGE_LUO,
            PreferredLanguage.ENGLISH: plantation_pb2.PREFERRED_LANGUAGE_EN,
        }
        return mapping.get(lang, plantation_pb2.PREFERRED_LANGUAGE_UNSPECIFIED)

    def _pref_lang_from_proto(self, lang: plantation_pb2.PreferredLanguage) -> PreferredLanguage:
        """Convert protobuf PreferredLanguage enum to domain enum."""
        mapping = {
            plantation_pb2.PREFERRED_LANGUAGE_SW: PreferredLanguage.SWAHILI,
            plantation_pb2.PREFERRED_LANGUAGE_KI: PreferredLanguage.KIKUYU,
            plantation_pb2.PREFERRED_LANGUAGE_LUO: PreferredLanguage.LUO,
            plantation_pb2.PREFERRED_LANGUAGE_EN: PreferredLanguage.ENGLISH,
        }
        return mapping.get(lang, PreferredLanguage.SWAHILI)

    def _farmer_to_proto(self, farmer: Farmer) -> plantation_pb2.Farmer:
        """Convert Farmer domain model to protobuf message."""
        return plantation_pb2.Farmer(
            id=farmer.id,
            grower_number=farmer.grower_number or "",
            first_name=farmer.first_name,
            last_name=farmer.last_name,
            region_id=farmer.region_id,
            collection_point_id=farmer.collection_point_id,
            farm_location=plantation_pb2.GeoLocation(
                latitude=farmer.farm_location.latitude,
                longitude=farmer.farm_location.longitude,
                altitude_meters=farmer.farm_location.altitude_meters,
            ),
            contact=plantation_pb2.ContactInfo(
                phone=farmer.contact.phone,
                email=farmer.contact.email,
                address=farmer.contact.address,
            ),
            farm_size_hectares=farmer.farm_size_hectares,
            farm_scale=self._farm_scale_to_proto(farmer.farm_scale),
            national_id=farmer.national_id,
            registration_date=datetime_to_timestamp(farmer.registration_date),
            is_active=farmer.is_active,
            created_at=datetime_to_timestamp(farmer.created_at),
            updated_at=datetime_to_timestamp(farmer.updated_at),
            notification_channel=self._notification_channel_to_proto(farmer.notification_channel),
            interaction_pref=self._interaction_pref_to_proto(farmer.interaction_pref),
            pref_lang=self._pref_lang_to_proto(farmer.pref_lang),
        )

    async def GetFarmer(
        self,
        request: plantation_pb2.GetFarmerRequest,
        context: grpc.aio.ServicerContext,
    ) -> plantation_pb2.Farmer:
        """Get a farmer by ID."""
        farmer = await self._farmer_repo.get_by_id(request.id)
        if farmer is None:
            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Farmer {request.id} not found",
            )
        return self._farmer_to_proto(farmer)

    async def GetFarmerByPhone(
        self,
        request: plantation_pb2.GetFarmerByPhoneRequest,
        context: grpc.aio.ServicerContext,
    ) -> plantation_pb2.Farmer:
        """Get a farmer by phone number.

        Used for duplicate detection during registration.
        """
        farmer = await self._farmer_repo.get_by_phone(request.phone)
        if farmer is None:
            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"No farmer found with phone {request.phone}",
            )
        return self._farmer_to_proto(farmer)

    async def ListFarmers(
        self,
        request: plantation_pb2.ListFarmersRequest,
        context: grpc.aio.ServicerContext,
    ) -> plantation_pb2.ListFarmersResponse:
        """List farmers with optional filtering."""
        filters = {}
        if request.region_id:
            filters["region_id"] = request.region_id
        if request.collection_point_id:
            filters["collection_point_id"] = request.collection_point_id
        if request.active_only:
            filters["is_active"] = True

        page_size = request.page_size if request.page_size > 0 else 100
        page_token = request.page_token if request.page_token else None

        farmers, next_token, total = await self._farmer_repo.list(
            filters=filters if filters else None,
            page_size=page_size,
            page_token=page_token,
        )

        return plantation_pb2.ListFarmersResponse(
            farmers=[self._farmer_to_proto(f) for f in farmers],
            next_page_token=next_token or "",
            total_count=total,
        )

    async def CreateFarmer(
        self,
        request: plantation_pb2.CreateFarmerRequest,
        context: grpc.aio.ServicerContext,
    ) -> plantation_pb2.Farmer:
        """Create a new farmer.

        AC #1: Register farmer with name, phone, national_id, farm_size, gps_location
        AC #2: Duplicate phone detection returns existing farmer_id
        """
        # Check for duplicate phone
        existing_by_phone = await self._farmer_repo.get_by_phone(request.contact.phone)
        if existing_by_phone:
            await context.abort(
                grpc.StatusCode.ALREADY_EXISTS,
                f"Phone number already registered. Existing farmer_id: {existing_by_phone.id}",
            )

        # Check for duplicate national ID
        existing_by_national_id = await self._farmer_repo.get_by_national_id(request.national_id)
        if existing_by_national_id:
            await context.abort(
                grpc.StatusCode.ALREADY_EXISTS,
                f"National ID already registered. Existing farmer_id: {existing_by_national_id.id}",
            )

        # Validate collection point exists
        cp = await self._cp_repo.get_by_id(request.collection_point_id)
        if cp is None:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"Collection point {request.collection_point_id} not found",
            )

        # Generate unique farmer ID (format: WM-XXXX)
        farmer_id = await self._id_generator.generate_farmer_id()

        # Fetch altitude from Google Elevation API
        altitude = await self._get_altitude_for_location(
            request.farm_location.latitude,
            request.farm_location.longitude,
        )

        # Auto-assign region based on GPS + altitude
        region_id = assign_region_from_altitude(
            request.farm_location.latitude,
            request.farm_location.longitude,
            altitude,
        )

        # Auto-calculate farm scale from hectares
        farm_scale = FarmScale.from_hectares(request.farm_size_hectares)

        # Create farmer
        now = datetime.now(UTC)
        farmer = Farmer(
            id=farmer_id,
            grower_number=request.grower_number if request.grower_number else None,
            first_name=request.first_name,
            last_name=request.last_name,
            region_id=region_id,
            collection_point_id=request.collection_point_id,
            farm_location=GeoLocation(
                latitude=request.farm_location.latitude,
                longitude=request.farm_location.longitude,
                altitude_meters=altitude,
            ),
            contact=ContactInfo(
                phone=request.contact.phone,
                email=request.contact.email if request.contact.email else "",
                address=request.contact.address if request.contact.address else "",
            ),
            farm_size_hectares=request.farm_size_hectares,
            farm_scale=farm_scale,
            national_id=request.national_id,
            registration_date=now,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        await self._farmer_repo.create(farmer)
        logger.info(
            "Created farmer %s (%s %s) at collection point %s",
            farmer.id,
            farmer.first_name,
            farmer.last_name,
            farmer.collection_point_id,
        )

        # Publish farmer registered event (AC #4)
        event = FarmerRegisteredEvent(
            farmer_id=farmer.id,
            phone=farmer.contact.phone,
            collection_point_id=farmer.collection_point_id,
            factory_id=cp.factory_id,  # Derived from collection point
            region_id=farmer.region_id,
            farm_scale=farmer.farm_scale.value,
        )
        await self._dapr_client.publish_event(
            pubsub_name=settings.dapr_pubsub_name,
            topic=settings.dapr_farmer_events_topic,
            data=event,
        )

        # Auto-initialize farmer performance (Story 1.4, AC #3)
        if self._grading_model_repo and self._farmer_performance_repo:
            grading_model = await self._grading_model_repo.get_by_factory(cp.factory_id)
            if grading_model:
                await self._farmer_performance_repo.initialize_for_farmer(
                    farmer_id=farmer.id,
                    farm_size_hectares=farmer.farm_size_hectares,
                    farm_scale=farmer.farm_scale,
                    grading_model_id=grading_model.model_id,
                    grading_model_version=grading_model.model_version,
                )
                logger.info(
                    "Initialized performance for farmer %s with grading model %s",
                    farmer.id,
                    grading_model.model_id,
                )

        return self._farmer_to_proto(farmer)

    async def UpdateFarmer(
        self,
        request: plantation_pb2.UpdateFarmerRequest,
        context: grpc.aio.ServicerContext,
    ) -> plantation_pb2.Farmer:
        """Update an existing farmer."""
        # Build updates dict from optional fields
        updates = {}

        if request.HasField("first_name"):
            updates["first_name"] = request.first_name
        if request.HasField("last_name"):
            updates["last_name"] = request.last_name
        if request.HasField("farm_location"):
            # Fetch new altitude for updated location
            altitude = await self._get_altitude_for_location(
                request.farm_location.latitude,
                request.farm_location.longitude,
            )
            updates["farm_location"] = GeoLocation(
                latitude=request.farm_location.latitude,
                longitude=request.farm_location.longitude,
                altitude_meters=altitude,
            ).model_dump()
            # Recalculate region if location changed
            updates["region_id"] = assign_region_from_altitude(
                request.farm_location.latitude,
                request.farm_location.longitude,
                altitude,
            )
        if request.HasField("contact"):
            # Check for duplicate phone if phone is being updated
            if request.contact.phone:
                existing = await self._farmer_repo.get_by_phone(request.contact.phone)
                if existing and existing.id != request.id:
                    await context.abort(
                        grpc.StatusCode.ALREADY_EXISTS,
                        f"Phone number already registered to farmer {existing.id}",
                    )
            updates["contact"] = ContactInfo(
                phone=request.contact.phone,
                email=request.contact.email,
                address=request.contact.address,
            ).model_dump()
        if request.HasField("farm_size_hectares"):
            updates["farm_size_hectares"] = request.farm_size_hectares
            # Recalculate farm scale
            updates["farm_scale"] = FarmScale.from_hectares(request.farm_size_hectares).value
        if request.HasField("is_active"):
            updates["is_active"] = request.is_active

        if not updates:
            # No updates, just return current farmer
            farmer = await self._farmer_repo.get_by_id(request.id)
            if farmer is None:
                await context.abort(
                    grpc.StatusCode.NOT_FOUND,
                    f"Farmer {request.id} not found",
                )
            return self._farmer_to_proto(farmer)

        farmer = await self._farmer_repo.update(request.id, updates)
        if farmer is None:
            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Farmer {request.id} not found",
            )

        logger.info("Updated farmer %s", farmer.id)
        return self._farmer_to_proto(farmer)

    # =========================================================================
    # Grading Model Operations
    # =========================================================================

    def _grading_type_to_proto(self, grading_type: GradingType) -> plantation_pb2.GradingType:
        """Convert GradingType domain enum to protobuf enum."""
        mapping = {
            GradingType.BINARY: plantation_pb2.GRADING_TYPE_BINARY,
            GradingType.TERNARY: plantation_pb2.GRADING_TYPE_TERNARY,
            GradingType.MULTI_LEVEL: plantation_pb2.GRADING_TYPE_MULTI_LEVEL,
        }
        return mapping.get(grading_type, plantation_pb2.GRADING_TYPE_UNSPECIFIED)

    def _grading_type_from_proto(self, grading_type: plantation_pb2.GradingType) -> GradingType:
        """Convert protobuf GradingType enum to domain enum."""
        mapping = {
            plantation_pb2.GRADING_TYPE_BINARY: GradingType.BINARY,
            plantation_pb2.GRADING_TYPE_TERNARY: GradingType.TERNARY,
            plantation_pb2.GRADING_TYPE_MULTI_LEVEL: GradingType.MULTI_LEVEL,
        }
        return mapping.get(grading_type, GradingType.BINARY)

    def _grading_model_to_proto(self, model: GradingModel) -> plantation_pb2.GradingModel:
        """Convert GradingModel domain model to protobuf message."""
        # Convert attributes
        proto_attrs = {}
        for name, attr in model.attributes.items():
            proto_attrs[name] = plantation_pb2.GradingAttribute(
                num_classes=attr.num_classes,
                classes=attr.classes,
            )

        # Convert grade rules
        proto_reject_conditions = {}
        for attr_name, values in model.grade_rules.reject_conditions.items():
            proto_reject_conditions[attr_name] = plantation_pb2.StringList(values=values)

        proto_conditional = [
            plantation_pb2.ConditionalReject(
                if_attribute=cr.if_attribute,
                if_value=cr.if_value,
                then_attribute=cr.then_attribute,
                reject_values=cr.reject_values,
            )
            for cr in model.grade_rules.conditional_reject
        ]

        proto_rules = plantation_pb2.GradeRules(
            reject_conditions=proto_reject_conditions,
            conditional_reject=proto_conditional,
        )

        return plantation_pb2.GradingModel(
            model_id=model.model_id,
            model_version=model.model_version,
            regulatory_authority=model.regulatory_authority or "",
            crops_name=model.crops_name,
            market_name=model.market_name,
            grading_type=self._grading_type_to_proto(model.grading_type),
            attributes=proto_attrs,
            grade_rules=proto_rules,
            grade_labels=model.grade_labels,
            active_at_factory=model.active_at_factory,
            created_at=datetime_to_timestamp(model.created_at),
            updated_at=datetime_to_timestamp(model.updated_at),
        )

    async def CreateGradingModel(
        self,
        request: plantation_pb2.CreateGradingModelRequest,
        context: grpc.aio.ServicerContext,
    ) -> plantation_pb2.GradingModel:
        """Create a new grading model (AC #1)."""
        if not self._grading_model_repo:
            await context.abort(
                grpc.StatusCode.UNIMPLEMENTED,
                "Grading model repository not configured",
            )

        # Check for duplicate model_id
        existing = await self._grading_model_repo.get_by_id(request.model_id)
        if existing:
            await context.abort(
                grpc.StatusCode.ALREADY_EXISTS,
                f"Grading model {request.model_id} already exists",
            )

        # Convert attributes
        attributes = {}
        for name, proto_attr in request.attributes.items():
            attributes[name] = GradingAttribute(
                num_classes=proto_attr.num_classes,
                classes=list(proto_attr.classes),
            )

        # Convert grade rules
        reject_conditions = {}
        for attr_name, string_list in request.grade_rules.reject_conditions.items():
            reject_conditions[attr_name] = list(string_list.values)

        conditional_reject = [
            ConditionalReject(
                if_attribute=cr.if_attribute,
                if_value=cr.if_value,
                then_attribute=cr.then_attribute,
                reject_values=list(cr.reject_values),
            )
            for cr in request.grade_rules.conditional_reject
        ]

        grade_rules = GradeRules(
            reject_conditions=reject_conditions,
            conditional_reject=conditional_reject,
        )

        # Create grading model
        model = GradingModel(
            model_id=request.model_id,
            model_version=request.model_version,
            regulatory_authority=request.regulatory_authority or None,
            crops_name=request.crops_name,
            market_name=request.market_name,
            grading_type=self._grading_type_from_proto(request.grading_type),
            attributes=attributes,
            grade_rules=grade_rules,
            grade_labels=dict(request.grade_labels),
            active_at_factory=list(request.active_at_factory),
        )

        await self._grading_model_repo.create(model)
        logger.info("Created grading model %s", model.model_id)

        return self._grading_model_to_proto(model)

    async def GetGradingModel(
        self,
        request: plantation_pb2.GetGradingModelRequest,
        context: grpc.aio.ServicerContext,
    ) -> plantation_pb2.GradingModel:
        """Get a grading model by ID."""
        if not self._grading_model_repo:
            await context.abort(
                grpc.StatusCode.UNIMPLEMENTED,
                "Grading model repository not configured",
            )

        model = await self._grading_model_repo.get_by_id(request.model_id)
        if model is None:
            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Grading model {request.model_id} not found",
            )

        return self._grading_model_to_proto(model)

    async def GetFactoryGradingModel(
        self,
        request: plantation_pb2.GetFactoryGradingModelRequest,
        context: grpc.aio.ServicerContext,
    ) -> plantation_pb2.GradingModel:
        """Get the grading model assigned to a factory (AC #2)."""
        if not self._grading_model_repo:
            await context.abort(
                grpc.StatusCode.UNIMPLEMENTED,
                "Grading model repository not configured",
            )

        model = await self._grading_model_repo.get_by_factory(request.factory_id)
        if model is None:
            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"No grading model found for factory {request.factory_id}",
            )

        return self._grading_model_to_proto(model)

    async def AssignGradingModelToFactory(
        self,
        request: plantation_pb2.AssignGradingModelToFactoryRequest,
        context: grpc.aio.ServicerContext,
    ) -> plantation_pb2.GradingModel:
        """Assign a grading model to a factory."""
        if not self._grading_model_repo:
            await context.abort(
                grpc.StatusCode.UNIMPLEMENTED,
                "Grading model repository not configured",
            )

        # Verify factory exists
        factory = await self._factory_repo.get_by_id(request.factory_id)
        if factory is None:
            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Factory {request.factory_id} not found",
            )

        # Add assignment
        model = await self._grading_model_repo.add_factory_assignment(request.model_id, request.factory_id)
        if model is None:
            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Grading model {request.model_id} not found",
            )

        logger.info(
            "Assigned grading model %s to factory %s",
            model.model_id,
            request.factory_id,
        )
        return self._grading_model_to_proto(model)

    # =========================================================================
    # Farmer Performance Operations
    # =========================================================================

    def _trend_direction_to_proto(self, trend: TrendDirection) -> plantation_pb2.TrendDirection:
        """Convert TrendDirection domain enum to protobuf enum."""
        mapping = {
            TrendDirection.IMPROVING: plantation_pb2.TREND_DIRECTION_IMPROVING,
            TrendDirection.STABLE: plantation_pb2.TREND_DIRECTION_STABLE,
            TrendDirection.DECLINING: plantation_pb2.TREND_DIRECTION_DECLINING,
        }
        return mapping.get(trend, plantation_pb2.TREND_DIRECTION_UNSPECIFIED)

    def _farmer_summary_to_proto(self, farmer: Farmer, performance: FarmerPerformance) -> plantation_pb2.FarmerSummary:
        """Convert Farmer and FarmerPerformance to FarmerSummary proto (AC #4)."""
        # Convert historical metrics
        hist = performance.historical
        proto_hist_attr_30d = {}
        for attr_name, class_counts in hist.attribute_distributions_30d.items():
            proto_hist_attr_30d[attr_name] = plantation_pb2.DistributionCounts(counts=class_counts)
        proto_hist_attr_90d = {}
        for attr_name, class_counts in hist.attribute_distributions_90d.items():
            proto_hist_attr_90d[attr_name] = plantation_pb2.DistributionCounts(counts=class_counts)
        proto_hist_attr_year = {}
        for attr_name, class_counts in hist.attribute_distributions_year.items():
            proto_hist_attr_year[attr_name] = plantation_pb2.DistributionCounts(counts=class_counts)

        proto_historical = plantation_pb2.HistoricalMetrics(
            grade_distribution_30d=hist.grade_distribution_30d,
            grade_distribution_90d=hist.grade_distribution_90d,
            grade_distribution_year=hist.grade_distribution_year,
            attribute_distributions_30d=proto_hist_attr_30d,
            attribute_distributions_90d=proto_hist_attr_90d,
            attribute_distributions_year=proto_hist_attr_year,
            primary_percentage_30d=hist.primary_percentage_30d,
            primary_percentage_90d=hist.primary_percentage_90d,
            primary_percentage_year=hist.primary_percentage_year,
            total_kg_30d=hist.total_kg_30d,
            total_kg_90d=hist.total_kg_90d,
            total_kg_year=hist.total_kg_year,
            yield_kg_per_hectare_30d=hist.yield_kg_per_hectare_30d,
            yield_kg_per_hectare_90d=hist.yield_kg_per_hectare_90d,
            yield_kg_per_hectare_year=hist.yield_kg_per_hectare_year,
            improvement_trend=self._trend_direction_to_proto(hist.improvement_trend),
            computed_at=datetime_to_timestamp(hist.computed_at) if hist.computed_at else None,
        )

        # Convert today metrics
        today = performance.today
        proto_today_attr = {}
        for attr_name, class_counts in today.attribute_counts.items():
            proto_today_attr[attr_name] = plantation_pb2.DistributionCounts(counts=class_counts)

        proto_today = plantation_pb2.TodayMetrics(
            deliveries=today.deliveries,
            total_kg=today.total_kg,
            grade_counts=today.grade_counts,
            attribute_counts=proto_today_attr,
            last_delivery=datetime_to_timestamp(today.last_delivery) if today.last_delivery else None,
            metrics_date=today.metrics_date.isoformat(),
        )

        return plantation_pb2.FarmerSummary(
            farmer_id=farmer.id,
            first_name=farmer.first_name,
            last_name=farmer.last_name,
            phone=farmer.contact.phone,
            collection_point_id=farmer.collection_point_id,
            farm_size_hectares=farmer.farm_size_hectares,
            farm_scale=self._farm_scale_to_proto(farmer.farm_scale),
            grading_model_id=performance.grading_model_id,
            grading_model_version=performance.grading_model_version,
            historical=proto_historical,
            today=proto_today,
            trend_direction=self._trend_direction_to_proto(performance.historical.improvement_trend),
            created_at=datetime_to_timestamp(performance.created_at),
            updated_at=datetime_to_timestamp(performance.updated_at),
            notification_channel=self._notification_channel_to_proto(farmer.notification_channel),
            interaction_pref=self._interaction_pref_to_proto(farmer.interaction_pref),
            pref_lang=self._pref_lang_to_proto(farmer.pref_lang),
        )

    async def GetFarmerSummary(
        self,
        request: plantation_pb2.GetFarmerSummaryRequest,
        context: grpc.aio.ServicerContext,
    ) -> plantation_pb2.FarmerSummary:
        """Get farmer summary with performance details (AC #4).

        Returns default/empty performance metrics if no performance data exists
        yet for the farmer (Task 6.7).
        """
        if not self._farmer_performance_repo:
            await context.abort(
                grpc.StatusCode.UNIMPLEMENTED,
                "Farmer performance repository not configured",
            )

        # Get farmer
        farmer = await self._farmer_repo.get_by_id(request.farmer_id)
        if farmer is None:
            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Farmer {request.farmer_id} not found",
            )

        # Get performance - return defaults if not found (Task 6.7)
        performance = await self._farmer_performance_repo.get_by_farmer_id(request.farmer_id)
        if performance is None:
            # Return default empty performance metrics
            # Get grading model from farmer's collection point's factory
            cp = await self._cp_repo.get_by_id(farmer.collection_point_id)
            grading_model_id = ""
            grading_model_version = ""
            if cp and self._grading_model_repo:
                grading_model = await self._grading_model_repo.get_by_factory(cp.factory_id)
                if grading_model:
                    grading_model_id = grading_model.model_id
                    grading_model_version = grading_model.model_version

            performance = FarmerPerformance.initialize_for_farmer(
                farmer_id=farmer.id,
                farm_size_hectares=farmer.farm_size_hectares,
                farm_scale=farmer.farm_scale,
                grading_model_id=grading_model_id,
                grading_model_version=grading_model_version,
            )

        return self._farmer_summary_to_proto(farmer, performance)

    # =========================================================================
    # Communication Preferences Operations (Story 1.5)
    # =========================================================================

    async def UpdateCommunicationPreferences(
        self,
        request: plantation_pb2.UpdateCommunicationPreferencesRequest,
        context: grpc.aio.ServicerContext,
    ) -> plantation_pb2.UpdateCommunicationPreferencesResponse:
        """Update farmer communication preferences (Story 1.5).

        Args:
            request: Contains farmer_id, notification_channel, interaction_pref, pref_lang
            context: gRPC context

        Returns:
            UpdateCommunicationPreferencesResponse with updated Farmer

        Raises:
            NOT_FOUND: If farmer doesn't exist
            INVALID_ARGUMENT: If channel, interaction preference, or language is invalid

        """
        # Validate farmer exists
        farmer = await self._farmer_repo.get_by_id(request.farmer_id)
        if farmer is None:
            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Farmer not found: {request.farmer_id}",
            )

        # Validate notification channel (must be one of the valid proto enum values)
        valid_channels = {
            plantation_pb2.NOTIFICATION_CHANNEL_SMS,
            plantation_pb2.NOTIFICATION_CHANNEL_WHATSAPP,
        }
        if request.notification_channel not in valid_channels:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Invalid notification channel. Valid options: sms, whatsapp",
            )

        # Validate interaction preference
        valid_interaction_prefs = {
            plantation_pb2.INTERACTION_PREFERENCE_TEXT,
            plantation_pb2.INTERACTION_PREFERENCE_VOICE,
        }
        if request.interaction_pref not in valid_interaction_prefs:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Invalid interaction preference. Valid options: text, voice",
            )

        # Validate language (must be one of the valid proto enum values)
        valid_langs = {
            plantation_pb2.PREFERRED_LANGUAGE_SW,
            plantation_pb2.PREFERRED_LANGUAGE_KI,
            plantation_pb2.PREFERRED_LANGUAGE_LUO,
            plantation_pb2.PREFERRED_LANGUAGE_EN,
        }
        if request.pref_lang not in valid_langs:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Invalid language. Valid options: sw (Swahili), ki (Kikuyu), luo (Luo), en (English)",
            )

        # Map proto enums to domain enums
        domain_channel = self._notification_channel_from_proto(request.notification_channel)
        domain_interaction = self._interaction_pref_from_proto(request.interaction_pref)
        domain_lang = self._pref_lang_from_proto(request.pref_lang)

        # Convert to dict for repository update
        updates = {
            "notification_channel": domain_channel.value,
            "interaction_pref": domain_interaction.value,
            "pref_lang": domain_lang.value,
        }

        updated_farmer = await self._farmer_repo.update(request.farmer_id, updates)
        if updated_farmer is None:
            await context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Farmer not found: {request.farmer_id}",
            )

        logger.info(
            "Updated communication preferences for farmer %s: channel=%s, interaction=%s, lang=%s",
            request.farmer_id,
            domain_channel.value,
            domain_interaction.value,
            domain_lang.value,
        )

        return plantation_pb2.UpdateCommunicationPreferencesResponse(
            farmer=self._farmer_to_proto(updated_farmer),
        )
