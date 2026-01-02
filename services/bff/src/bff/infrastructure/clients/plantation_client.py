"""Plantation Model gRPC client for BFF.

This client provides typed access to the Plantation Model service via DAPR gRPC
service invocation. All methods return fp-common Pydantic domain models (NOT dicts).

Pattern follows:
- ADR-002 §"Service Invocation Pattern" (native gRPC with dapr-app-id metadata)
- ADR-005 for retry logic (3 attempts, exponential backoff 1-10s)

CRITICAL: Uses fp-common domain models for type safety. Never returns dict[str, Any].
"""

from datetime import datetime

import grpc
import grpc.aio
import structlog
from bff.infrastructure.clients.base import (
    BaseGrpcClient,
    grpc_retry,
)
from fp_common.models import (
    CollectionPoint,
    CollectionPointCapacity,
    ContactInfo,
    Factory,
    Farmer,
    FarmScale,
    Flush,
    FlushPeriod,
    GeoLocation,
    InteractionPreference,
    NotificationChannel,
    OperatingHours,
    PaymentPolicy,
    PaymentPolicyType,
    PreferredLanguage,
    QualityThresholds,
    Region,
    RegionalWeather,
)
from fp_common.models.farmer_performance import (
    FarmerPerformance,
    HistoricalMetrics,
    TodayMetrics,
    TrendDirection,
)
from fp_common.models.value_objects import (
    GPS,
    Agronomic,
    AltitudeBand,
    AltitudeBandLabel,
    FlushCalendar,
    Geography,
    WeatherConfig,
)
from fp_proto.plantation.v1 import plantation_pb2, plantation_pb2_grpc
from google.protobuf.timestamp_pb2 import Timestamp

logger = structlog.get_logger(__name__)


def _timestamp_to_datetime(ts: Timestamp) -> datetime | None:
    """Convert protobuf Timestamp to Python datetime."""
    if ts.seconds == 0 and ts.nanos == 0:
        return None
    return ts.ToDatetime()


def _proto_enum_to_str(proto_enum_value: int, proto_enum_class: type) -> str:
    """Convert protobuf enum value to lowercase string name."""
    name = proto_enum_class.Name(proto_enum_value)
    # Remove prefix (e.g., FARM_SCALE_SMALLHOLDER -> smallholder)
    parts = name.split("_")
    # Find where the actual value starts (after TYPE/SCALE/BAND etc prefix words)
    prefix_words = {
        "FARM",
        "SCALE",
        "NOTIFICATION",
        "CHANNEL",
        "INTERACTION",
        "PREFERENCE",
        "PREFERRED",
        "LANGUAGE",
        "TREND",
        "DIRECTION",
        "ALTITUDE",
        "BAND",
        "PAYMENT",
        "POLICY",
        "TYPE",
    }
    value_parts = []
    for i, part in enumerate(parts):
        if part not in prefix_words:
            value_parts = parts[i:]
            break
    return "_".join(value_parts).lower() if value_parts else name.lower()


class PlantationClient(BaseGrpcClient):
    """Client for Plantation Model gRPC service via DAPR.

    Provides 13 read methods across 5 domains:
    - Farmer: get_farmer, get_farmer_by_phone, list_farmers, get_farmer_summary
    - Factory: get_factory, list_factories
    - Collection Point: get_collection_point, list_collection_points
    - Region: get_region, list_regions, get_region_weather, get_current_flush
    - Performance: get_performance_summary

    All methods return typed Pydantic models from fp-common.

    Example:
        >>> client = PlantationClient()
        >>> farmer = await client.get_farmer("WM-0001")
        >>> print(farmer.first_name)
        'Wanjiku'
    """

    def __init__(
        self,
        dapr_grpc_port: int = 50001,
        direct_host: str | None = None,
        channel: grpc.aio.Channel | None = None,
    ) -> None:
        """Initialize the Plantation client.

        Args:
            dapr_grpc_port: Port for DAPR sidecar gRPC endpoint (default: 50001).
            direct_host: Optional direct host for testing (bypasses DAPR).
            channel: Optional pre-configured channel for testing.
        """
        super().__init__(
            target_app_id="plantation-model",
            dapr_grpc_port=dapr_grpc_port,
            direct_host=direct_host,
            channel=channel,
        )

    async def _get_plantation_stub(self) -> plantation_pb2_grpc.PlantationServiceStub:
        """Get the Plantation service stub."""
        return await self._get_stub(plantation_pb2_grpc.PlantationServiceStub)

    # =========================================================================
    # Farmer Operations (4 read methods)
    # =========================================================================

    @grpc_retry
    async def get_farmer(self, farmer_id: str) -> Farmer:
        """Get farmer by ID.

        Args:
            farmer_id: The farmer ID (e.g., "WM-0001").

        Returns:
            Farmer domain model.

        Raises:
            NotFoundError: If farmer not found.
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_plantation_stub()
            request = plantation_pb2.GetFarmerRequest(id=farmer_id)
            response = await stub.GetFarmer(request, metadata=self._get_metadata())
            return self._proto_to_farmer(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Farmer {farmer_id}")
            raise  # unreachable, but makes type checker happy

    @grpc_retry
    async def get_farmer_by_phone(self, phone: str) -> Farmer:
        """Get farmer by phone number.

        Args:
            phone: Phone number (e.g., "+254712345678").

        Returns:
            Farmer domain model.

        Raises:
            NotFoundError: If farmer with phone not found.
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_plantation_stub()
            request = plantation_pb2.GetFarmerByPhoneRequest(phone=phone)
            response = await stub.GetFarmerByPhone(request, metadata=self._get_metadata())
            return self._proto_to_farmer(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Farmer with phone {phone}")
            raise

    @grpc_retry
    async def list_farmers(
        self,
        region_id: str | None = None,
        collection_point_id: str | None = None,
        page_size: int = 50,
        page_token: str | None = None,
        active_only: bool = True,
    ) -> tuple[list[Farmer], str | None, int]:
        """List farmers with optional filtering.

        Args:
            region_id: Optional filter by region.
            collection_point_id: Optional filter by collection point.
            page_size: Number of results per page (default: 50).
            page_token: Token for pagination.
            active_only: Only return active farmers (default: True).

        Returns:
            Tuple of (farmers list, next_page_token or None, total_count).

        Raises:
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_plantation_stub()
            request = plantation_pb2.ListFarmersRequest(
                region_id=region_id or "",
                collection_point_id=collection_point_id or "",
                page_size=page_size,
                page_token=page_token or "",
                active_only=active_only,
            )
            response = await stub.ListFarmers(request, metadata=self._get_metadata())
            farmers = [self._proto_to_farmer(f) for f in response.farmers]
            next_token = response.next_page_token if response.next_page_token else None
            return farmers, next_token, response.total_count
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Farmers list")
            raise

    @grpc_retry
    async def get_farmer_summary(self, farmer_id: str) -> FarmerPerformance:
        """Get farmer with performance metrics.

        This returns the FarmerSummary which includes historical and today metrics,
        mapped to the FarmerPerformance domain model.

        Args:
            farmer_id: The farmer ID.

        Returns:
            FarmerPerformance domain model with historical and today metrics.

        Raises:
            NotFoundError: If farmer not found.
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_plantation_stub()
            request = plantation_pb2.GetFarmerSummaryRequest(farmer_id=farmer_id)
            response = await stub.GetFarmerSummary(request, metadata=self._get_metadata())
            return self._proto_to_farmer_performance(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Farmer summary {farmer_id}")
            raise

    # =========================================================================
    # Factory Operations (2 read methods)
    # =========================================================================

    @grpc_retry
    async def get_factory(self, factory_id: str) -> Factory:
        """Get factory by ID.

        Args:
            factory_id: The factory ID (e.g., "KEN-FAC-001").

        Returns:
            Factory domain model with quality_thresholds.

        Raises:
            NotFoundError: If factory not found.
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_plantation_stub()
            request = plantation_pb2.GetFactoryRequest(id=factory_id)
            response = await stub.GetFactory(request, metadata=self._get_metadata())
            return self._proto_to_factory(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Factory {factory_id}")
            raise

    @grpc_retry
    async def list_factories(
        self,
        region_id: str | None = None,
        page_size: int = 50,
        page_token: str | None = None,
        active_only: bool = True,
    ) -> tuple[list[Factory], str | None, int]:
        """List factories with optional filtering.

        Args:
            region_id: Optional filter by region.
            page_size: Number of results per page (default: 50).
            page_token: Token for pagination.
            active_only: Only return active factories (default: True).

        Returns:
            Tuple of (factories list, next_page_token or None, total_count).

        Raises:
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_plantation_stub()
            request = plantation_pb2.ListFactoriesRequest(
                region_id=region_id or "",
                page_size=page_size,
                page_token=page_token or "",
                active_only=active_only,
            )
            response = await stub.ListFactories(request, metadata=self._get_metadata())
            factories = [self._proto_to_factory(f) for f in response.factories]
            next_token = response.next_page_token if response.next_page_token else None
            return factories, next_token, response.total_count
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Factories list")
            raise

    # =========================================================================
    # Collection Point Operations (2 read methods)
    # =========================================================================

    @grpc_retry
    async def get_collection_point(self, collection_point_id: str) -> CollectionPoint:
        """Get collection point by ID.

        Args:
            collection_point_id: The collection point ID (e.g., "nyeri-highland-cp-001").

        Returns:
            CollectionPoint domain model.

        Raises:
            NotFoundError: If collection point not found.
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_plantation_stub()
            request = plantation_pb2.GetCollectionPointRequest(id=collection_point_id)
            response = await stub.GetCollectionPoint(request, metadata=self._get_metadata())
            return self._proto_to_collection_point(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Collection point {collection_point_id}")
            raise

    @grpc_retry
    async def list_collection_points(
        self,
        factory_id: str | None = None,
        region_id: str | None = None,
        page_size: int = 50,
        page_token: str | None = None,
        active_only: bool = True,
    ) -> tuple[list[CollectionPoint], str | None, int]:
        """List collection points with optional filtering.

        Args:
            factory_id: Optional filter by factory.
            region_id: Optional filter by region.
            page_size: Number of results per page (default: 50).
            page_token: Token for pagination.
            active_only: Only return active collection points (default: True).

        Returns:
            Tuple of (collection_points list, next_page_token or None, total_count).

        Raises:
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_plantation_stub()
            request = plantation_pb2.ListCollectionPointsRequest(
                factory_id=factory_id or "",
                region_id=region_id or "",
                page_size=page_size,
                page_token=page_token or "",
                active_only=active_only,
            )
            response = await stub.ListCollectionPoints(request, metadata=self._get_metadata())
            collection_points = [self._proto_to_collection_point(cp) for cp in response.collection_points]
            next_token = response.next_page_token if response.next_page_token else None
            return collection_points, next_token, response.total_count
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Collection points list")
            raise

    # =========================================================================
    # Region Operations (4 read methods)
    # =========================================================================

    @grpc_retry
    async def get_region(self, region_id: str) -> Region:
        """Get region by ID.

        Args:
            region_id: The region ID (e.g., "nyeri-highland").

        Returns:
            Region domain model with geography and agronomic data.

        Raises:
            NotFoundError: If region not found.
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_plantation_stub()
            request = plantation_pb2.GetRegionRequest(region_id=region_id)
            response = await stub.GetRegion(request, metadata=self._get_metadata())
            return self._proto_to_region(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Region {region_id}")
            raise

    @grpc_retry
    async def list_regions(
        self,
        county: str | None = None,
        altitude_band: str | None = None,
        page_size: int = 50,
        page_token: str | None = None,
        active_only: bool = True,
    ) -> tuple[list[Region], str | None, int]:
        """List regions with optional filtering.

        Args:
            county: Optional filter by county name.
            altitude_band: Optional filter by altitude band (highland/midland/lowland).
            page_size: Number of results per page (default: 50).
            page_token: Token for pagination.
            active_only: Only return active regions (default: True).

        Returns:
            Tuple of (regions list, next_page_token or None, total_count).

        Raises:
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_plantation_stub()
            request = plantation_pb2.ListRegionsRequest(
                county=county or "",
                altitude_band=altitude_band or "",
                page_size=page_size,
                page_token=page_token or "",
                active_only=active_only,
            )
            response = await stub.ListRegions(request, metadata=self._get_metadata())
            regions = [self._proto_to_region(r) for r in response.regions]
            next_token = response.next_page_token if response.next_page_token else None
            return regions, next_token, response.total_count
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Regions list")
            raise

    @grpc_retry
    async def get_region_weather(
        self,
        region_id: str,
        days: int = 7,
    ) -> list[RegionalWeather]:
        """Get weather observations for a region.

        Args:
            region_id: The region ID.
            days: Number of days of history (default: 7).

        Returns:
            List of RegionalWeather observations.

        Raises:
            NotFoundError: If region not found.
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_plantation_stub()
            request = plantation_pb2.GetRegionWeatherRequest(
                region_id=region_id,
                days=days,
            )
            response = await stub.GetRegionWeather(request, metadata=self._get_metadata())
            return [self._proto_to_regional_weather(region_id, obs) for obs in response.observations]
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Weather for region {region_id}")
            raise

    @grpc_retry
    async def get_current_flush(self, region_id: str) -> Flush:
        """Get current flush period for a region.

        Args:
            region_id: The region ID.

        Returns:
            Flush domain model with current flush period info.

        Raises:
            NotFoundError: If region not found.
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_plantation_stub()
            request = plantation_pb2.GetCurrentFlushRequest(region_id=region_id)
            response = await stub.GetCurrentFlush(request, metadata=self._get_metadata())
            return self._proto_to_flush(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Current flush for region {region_id}")
            raise

    # =========================================================================
    # Performance Operations (1 read method)
    # =========================================================================

    @grpc_retry
    async def get_performance_summary(
        self,
        entity_type: str,
        entity_id: str,
        period: str,
        period_start: datetime | None = None,
    ) -> dict:
        """Get aggregated performance metrics for an entity.

        Args:
            entity_type: Type of entity ("farmer", "factory", "region").
            entity_id: ID of the entity.
            period: Period type ("daily", "weekly", "monthly", "yearly").
            period_start: Optional start of period (for specific date ranges).

        Returns:
            Dict with performance summary metrics.

        Raises:
            NotFoundError: If entity not found.
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_plantation_stub()
            request = plantation_pb2.GetPerformanceSummaryRequest(
                entity_type=entity_type,
                entity_id=entity_id,
                period=period,
            )
            if period_start:
                request.period_start.FromDatetime(period_start)
            response = await stub.GetPerformanceSummary(request, metadata=self._get_metadata())
            return self._proto_to_performance_summary(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Performance summary for {entity_type} {entity_id}")
            raise

    # =========================================================================
    # Proto to Domain Model Converters
    # =========================================================================

    def _proto_to_farmer(self, proto: plantation_pb2.Farmer) -> Farmer:
        """Convert Farmer proto to domain model."""
        # Map proto enum to Python enum
        farm_scale_str = _proto_enum_to_str(proto.farm_scale, plantation_pb2.FarmScale)
        notification_channel_str = _proto_enum_to_str(proto.notification_channel, plantation_pb2.NotificationChannel)
        interaction_pref_str = _proto_enum_to_str(proto.interaction_pref, plantation_pb2.InteractionPreference)
        pref_lang_str = _proto_enum_to_str(proto.pref_lang, plantation_pb2.PreferredLanguage)

        return Farmer(
            id=proto.id,
            grower_number=proto.grower_number if proto.grower_number else None,
            first_name=proto.first_name,
            last_name=proto.last_name,
            region_id=proto.region_id,
            collection_point_id=proto.collection_point_id,
            farm_location=GeoLocation(
                latitude=proto.farm_location.latitude if proto.farm_location else 0,
                longitude=proto.farm_location.longitude if proto.farm_location else 0,
                altitude_meters=proto.farm_location.altitude_meters if proto.farm_location else 0,
            ),
            contact=ContactInfo(
                phone=proto.contact.phone if proto.contact else "",
                email=proto.contact.email if proto.contact else "",
                address=proto.contact.address if proto.contact else "",
            ),
            farm_size_hectares=proto.farm_size_hectares,
            farm_scale=FarmScale(farm_scale_str),
            national_id=proto.national_id,
            registration_date=_timestamp_to_datetime(proto.registration_date) or datetime.now(),
            is_active=proto.is_active,
            notification_channel=NotificationChannel(notification_channel_str),
            interaction_pref=InteractionPreference(interaction_pref_str),
            pref_lang=PreferredLanguage(pref_lang_str),
            created_at=_timestamp_to_datetime(proto.created_at) or datetime.now(),
            updated_at=_timestamp_to_datetime(proto.updated_at) or datetime.now(),
        )

    def _proto_to_factory(self, proto: plantation_pb2.Factory) -> Factory:
        """Convert Factory proto to domain model."""
        # Payment policy type
        payment_policy_type_str = _proto_enum_to_str(
            proto.payment_policy.policy_type if proto.HasField("payment_policy") else 0,
            plantation_pb2.PaymentPolicyType,
        )

        return Factory(
            id=proto.id,
            name=proto.name,
            code=proto.code,
            region_id=proto.region_id,
            location=GeoLocation(
                latitude=proto.location.latitude if proto.location else 0,
                longitude=proto.location.longitude if proto.location else 0,
                altitude_meters=proto.location.altitude_meters if proto.location else 0,
            ),
            contact=ContactInfo(
                phone=proto.contact.phone if proto.contact else "",
                email=proto.contact.email if proto.contact else "",
                address=proto.contact.address if proto.contact else "",
            ),
            processing_capacity_kg=proto.processing_capacity_kg,
            quality_thresholds=QualityThresholds(
                tier_1=proto.quality_thresholds.tier_1 if proto.HasField("quality_thresholds") else 85.0,
                tier_2=proto.quality_thresholds.tier_2 if proto.HasField("quality_thresholds") else 70.0,
                tier_3=proto.quality_thresholds.tier_3 if proto.HasField("quality_thresholds") else 50.0,
            ),
            payment_policy=PaymentPolicy(
                policy_type=PaymentPolicyType(payment_policy_type_str)
                if payment_policy_type_str and payment_policy_type_str != "unspecified"
                else PaymentPolicyType.FEEDBACK_ONLY,
                tier_1_adjustment=proto.payment_policy.tier_1_adjustment if proto.HasField("payment_policy") else 0.0,
                tier_2_adjustment=proto.payment_policy.tier_2_adjustment if proto.HasField("payment_policy") else 0.0,
                tier_3_adjustment=proto.payment_policy.tier_3_adjustment if proto.HasField("payment_policy") else 0.0,
                below_tier_3_adjustment=proto.payment_policy.below_tier_3_adjustment
                if proto.HasField("payment_policy")
                else 0.0,
            ),
            is_active=proto.is_active,
            created_at=_timestamp_to_datetime(proto.created_at) or datetime.now(),
            updated_at=_timestamp_to_datetime(proto.updated_at) or datetime.now(),
        )

    def _proto_to_collection_point(self, proto: plantation_pb2.CollectionPoint) -> CollectionPoint:
        """Convert CollectionPoint proto to domain model."""
        return CollectionPoint(
            id=proto.id,
            name=proto.name,
            factory_id=proto.factory_id,
            location=GeoLocation(
                latitude=proto.location.latitude if proto.location else 0,
                longitude=proto.location.longitude if proto.location else 0,
                altitude_meters=proto.location.altitude_meters if proto.location else 0,
            ),
            region_id=proto.region_id,
            clerk_id=proto.clerk_id if proto.clerk_id else None,
            clerk_phone=proto.clerk_phone if proto.clerk_phone else None,
            operating_hours=OperatingHours(
                weekdays=proto.operating_hours.weekdays if proto.HasField("operating_hours") else "06:00-10:00",
                weekends=proto.operating_hours.weekends if proto.HasField("operating_hours") else "07:00-09:00",
            ),
            collection_days=list(proto.collection_days) if proto.collection_days else ["mon", "wed", "fri", "sat"],
            capacity=CollectionPointCapacity(
                max_daily_kg=proto.capacity.max_daily_kg if proto.HasField("capacity") else 5000,
                storage_type=proto.capacity.storage_type if proto.HasField("capacity") else "covered_shed",
                has_weighing_scale=proto.capacity.has_weighing_scale if proto.HasField("capacity") else True,
                has_qc_device=proto.capacity.has_qc_device if proto.HasField("capacity") else False,
            ),
            status=proto.status if proto.status else "active",
            created_at=_timestamp_to_datetime(proto.created_at) or datetime.now(),
            updated_at=_timestamp_to_datetime(proto.updated_at) or datetime.now(),
        )

    def _proto_to_region(self, proto: plantation_pb2.Region) -> Region:
        """Convert Region proto to domain model."""
        # Altitude band label
        altitude_label_str = _proto_enum_to_str(
            proto.geography.altitude_band.label
            if proto.HasField("geography") and proto.geography.HasField("altitude_band")
            else 0,
            plantation_pb2.AltitudeBandLabel,
        )

        # Build flush calendar
        flush_calendar = FlushCalendar(
            first_flush=FlushPeriod(
                start=proto.flush_calendar.first_flush.start if proto.HasField("flush_calendar") else "03-15",
                end=proto.flush_calendar.first_flush.end if proto.HasField("flush_calendar") else "05-15",
                characteristics=proto.flush_calendar.first_flush.characteristics
                if proto.HasField("flush_calendar")
                else "",
            ),
            monsoon_flush=FlushPeriod(
                start=proto.flush_calendar.monsoon_flush.start if proto.HasField("flush_calendar") else "06-15",
                end=proto.flush_calendar.monsoon_flush.end if proto.HasField("flush_calendar") else "09-30",
                characteristics=proto.flush_calendar.monsoon_flush.characteristics
                if proto.HasField("flush_calendar")
                else "",
            ),
            autumn_flush=FlushPeriod(
                start=proto.flush_calendar.autumn_flush.start if proto.HasField("flush_calendar") else "10-15",
                end=proto.flush_calendar.autumn_flush.end if proto.HasField("flush_calendar") else "12-15",
                characteristics=proto.flush_calendar.autumn_flush.characteristics
                if proto.HasField("flush_calendar")
                else "",
            ),
            dormant=FlushPeriod(
                start=proto.flush_calendar.dormant.start if proto.HasField("flush_calendar") else "12-16",
                end=proto.flush_calendar.dormant.end if proto.HasField("flush_calendar") else "03-14",
                characteristics=proto.flush_calendar.dormant.characteristics
                if proto.HasField("flush_calendar")
                else "",
            ),
        )

        return Region(
            region_id=proto.region_id,
            name=proto.name,
            county=proto.county,
            country=proto.country if proto.country else "Kenya",
            geography=Geography(
                center_gps=GPS(
                    lat=proto.geography.center_gps.lat
                    if proto.HasField("geography") and proto.geography.HasField("center_gps")
                    else 0,
                    lng=proto.geography.center_gps.lng
                    if proto.HasField("geography") and proto.geography.HasField("center_gps")
                    else 0,
                ),
                radius_km=proto.geography.radius_km if proto.HasField("geography") else 25,
                altitude_band=AltitudeBand(
                    min_meters=proto.geography.altitude_band.min_meters
                    if proto.HasField("geography") and proto.geography.HasField("altitude_band")
                    else 0,
                    max_meters=proto.geography.altitude_band.max_meters
                    if proto.HasField("geography") and proto.geography.HasField("altitude_band")
                    else 0,
                    label=AltitudeBandLabel(altitude_label_str) if altitude_label_str else AltitudeBandLabel.HIGHLAND,
                ),
            ),
            flush_calendar=flush_calendar,
            agronomic=Agronomic(
                soil_type=proto.agronomic.soil_type if proto.HasField("agronomic") else "",
                typical_diseases=list(proto.agronomic.typical_diseases) if proto.HasField("agronomic") else [],
                harvest_peak_hours=proto.agronomic.harvest_peak_hours if proto.HasField("agronomic") else "",
                frost_risk=proto.agronomic.frost_risk if proto.HasField("agronomic") else False,
            ),
            weather_config=WeatherConfig(
                api_location=GPS(
                    lat=proto.weather_config.api_location.lat
                    if proto.HasField("weather_config") and proto.weather_config.HasField("api_location")
                    else 0,
                    lng=proto.weather_config.api_location.lng
                    if proto.HasField("weather_config") and proto.weather_config.HasField("api_location")
                    else 0,
                ),
                altitude_for_api=proto.weather_config.altitude_for_api if proto.HasField("weather_config") else 0,
                collection_time=proto.weather_config.collection_time if proto.HasField("weather_config") else "06:00",
            ),
            is_active=proto.is_active,
            created_at=_timestamp_to_datetime(proto.created_at) or datetime.now(),
            updated_at=_timestamp_to_datetime(proto.updated_at) or datetime.now(),
        )

    def _proto_to_regional_weather(self, region_id: str, proto: plantation_pb2.RegionalWeather) -> RegionalWeather:
        """Convert RegionalWeather proto to domain model."""
        import datetime as dt

        return RegionalWeather(
            region_id=region_id,
            date=dt.date.fromisoformat(proto.date) if proto.date else dt.date.today(),
            temp_min=proto.temp_min,
            temp_max=proto.temp_max,
            precipitation_mm=proto.precipitation_mm,
            humidity_avg=proto.humidity_avg,
            source=proto.source if proto.source else "open-meteo",
            created_at=_timestamp_to_datetime(proto.created_at) or datetime.now(),
        )

    def _proto_to_flush(self, proto: plantation_pb2.GetCurrentFlushResponse) -> Flush:
        """Convert GetCurrentFlushResponse proto to Flush domain model."""
        if proto.HasField("current_flush"):
            cf = proto.current_flush
            return Flush(
                name=cf.flush_name,
                period=FlushPeriod(
                    start=cf.start_date,
                    end=cf.end_date,
                    characteristics=cf.characteristics,
                ),
                days_remaining=cf.days_remaining,
                characteristics=cf.characteristics,
            )
        # Return dormant as default if no flush data
        return Flush(
            name="dormant",
            period=FlushPeriod(start="12-16", end="03-14", characteristics="Minimal growth"),
            days_remaining=0,
            characteristics="Minimal growth",
        )

    def _proto_to_farmer_performance(self, proto: plantation_pb2.FarmerSummary) -> FarmerPerformance:
        """Convert FarmerSummary proto to FarmerPerformance domain model."""
        # Map farm scale enum
        farm_scale_str = _proto_enum_to_str(proto.farm_scale, plantation_pb2.FarmScale)

        # Build historical metrics
        historical = HistoricalMetrics()
        if proto.HasField("historical"):
            hist = proto.historical
            historical_trend_str = _proto_enum_to_str(hist.improvement_trend, plantation_pb2.TrendDirection)
            historical = HistoricalMetrics(
                grade_distribution_30d=dict(hist.grade_distribution_30d),
                grade_distribution_90d=dict(hist.grade_distribution_90d),
                grade_distribution_year=dict(hist.grade_distribution_year),
                attribute_distributions_30d={k: dict(v.counts) for k, v in hist.attribute_distributions_30d.items()},
                attribute_distributions_90d={k: dict(v.counts) for k, v in hist.attribute_distributions_90d.items()},
                attribute_distributions_year={k: dict(v.counts) for k, v in hist.attribute_distributions_year.items()},
                primary_percentage_30d=hist.primary_percentage_30d,
                primary_percentage_90d=hist.primary_percentage_90d,
                primary_percentage_year=hist.primary_percentage_year,
                total_kg_30d=hist.total_kg_30d,
                total_kg_90d=hist.total_kg_90d,
                total_kg_year=hist.total_kg_year,
                yield_kg_per_hectare_30d=hist.yield_kg_per_hectare_30d,
                yield_kg_per_hectare_90d=hist.yield_kg_per_hectare_90d,
                yield_kg_per_hectare_year=hist.yield_kg_per_hectare_year,
                improvement_trend=TrendDirection(historical_trend_str)
                if historical_trend_str
                else TrendDirection.STABLE,
                computed_at=_timestamp_to_datetime(hist.computed_at),
            )

        # Build today metrics
        import datetime as dt

        today = TodayMetrics()
        if proto.HasField("today"):
            t = proto.today
            today = TodayMetrics(
                deliveries=t.deliveries,
                total_kg=t.total_kg,
                grade_counts=dict(t.grade_counts),
                attribute_counts={k: dict(v.counts) for k, v in t.attribute_counts.items()},
                last_delivery=_timestamp_to_datetime(t.last_delivery),
                metrics_date=dt.date.fromisoformat(t.metrics_date) if t.metrics_date else dt.date.today(),
            )

        return FarmerPerformance(
            farmer_id=proto.farmer_id,
            grading_model_id=proto.grading_model_id,
            grading_model_version=proto.grading_model_version,
            farm_size_hectares=proto.farm_size_hectares,
            farm_scale=FarmScale(farm_scale_str) if farm_scale_str else FarmScale.SMALLHOLDER,
            historical=historical,
            today=today,
        )

    def _proto_to_performance_summary(self, proto: plantation_pb2.PerformanceSummary) -> dict:
        """Convert PerformanceSummary proto to dict.

        Note: This returns a dict because PerformanceSummary is a generic aggregation
        model that varies by entity_type (farmer/factory/region). For specific entity
        types, use get_farmer_summary which returns typed FarmerPerformance.
        """
        return {
            "id": proto.id,
            "entity_type": proto.entity_type,
            "entity_id": proto.entity_id,
            "period": proto.period,
            "period_start": _timestamp_to_datetime(proto.period_start),
            "period_end": _timestamp_to_datetime(proto.period_end),
            "total_green_leaf_kg": proto.total_green_leaf_kg,
            "total_made_tea_kg": proto.total_made_tea_kg,
            "collection_count": proto.collection_count,
            "average_quality_score": proto.average_quality_score,
            "created_at": _timestamp_to_datetime(proto.created_at),
            "updated_at": _timestamp_to_datetime(proto.updated_at),
        }
