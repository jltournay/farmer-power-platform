"""Plantation Model gRPC client for BFF.

This client provides typed access to the Plantation Model service via DAPR gRPC
service invocation. All methods return fp-common Pydantic domain models (NOT dicts).

Pattern follows:
- ADR-002 §"Service Invocation Pattern" (native gRPC with dapr-app-id metadata)
- ADR-005 for retry logic (3 attempts, exponential backoff 1-10s)
- ADR-012 for response wrappers (list methods return PaginatedResponse)

CRITICAL: Uses fp-common domain models for type safety. Never returns dict[str, Any].
"""

from datetime import datetime

import grpc
import grpc.aio
import structlog
from bff.api.schemas import PaginatedResponse
from bff.infrastructure.clients.base import (
    BaseGrpcClient,
    grpc_retry,
)
from fp_common.models import (
    CollectionPoint,
    CollectionPointCapacity,
    CollectionPointCreate,
    CollectionPointUpdate,
    ContactInfo,
    Factory,
    FactoryCreate,
    FactoryUpdate,
    Farmer,
    FarmerCreate,
    FarmerUpdate,
    FarmScale,
    Flush,
    FlushPeriod,
    GeoLocation,
    InteractionPreference,
    NotificationChannel,
    OperatingHours,
    PaymentPolicy,
    PaymentPolicyType,
    PerformanceSummary,
    PreferredLanguage,
    QualityThresholds,
    Region,
    RegionalWeather,
    RegionCreate,
    RegionUpdate,
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

    Provides 13 read methods and 11 write methods across 5 domains:

    Read Operations:
    - Farmer: get_farmer, get_farmer_by_phone, list_farmers, get_farmer_summary
    - Factory: get_factory, list_factories
    - Collection Point: get_collection_point, list_collection_points
    - Region: get_region, list_regions, get_region_weather, get_current_flush
    - Performance: get_performance_summary

    Write Operations:
    - Farmer: create_farmer, update_farmer
    - Factory: create_factory, update_factory, delete_factory
    - Collection Point: create_collection_point, update_collection_point, delete_collection_point
    - Region: create_region, update_region
    - Communication: update_communication_preferences

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
    ) -> PaginatedResponse[Farmer]:
        """List farmers with optional filtering.

        Args:
            region_id: Optional filter by region.
            collection_point_id: Optional filter by collection point.
            page_size: Number of results per page (default: 50).
            page_token: Token for pagination.
            active_only: Only return active farmers (default: True).

        Returns:
            PaginatedResponse containing farmers list with pagination metadata.

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
            return PaginatedResponse.from_client_response(
                items=farmers,
                total_count=response.total_count,
                page_size=page_size,
                next_page_token=next_token,
            )
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
    ) -> PaginatedResponse[Factory]:
        """List factories with optional filtering.

        Args:
            region_id: Optional filter by region.
            page_size: Number of results per page (default: 50).
            page_token: Token for pagination.
            active_only: Only return active factories (default: True).

        Returns:
            PaginatedResponse containing factories list with pagination metadata.

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
            return PaginatedResponse.from_client_response(
                items=factories,
                total_count=response.total_count,
                page_size=page_size,
                next_page_token=next_token,
            )
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
    ) -> PaginatedResponse[CollectionPoint]:
        """List collection points with optional filtering.

        Args:
            factory_id: Optional filter by factory.
            region_id: Optional filter by region.
            page_size: Number of results per page (default: 50).
            page_token: Token for pagination.
            active_only: Only return active collection points (default: True).

        Returns:
            PaginatedResponse containing collection points with pagination metadata.

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
            return PaginatedResponse.from_client_response(
                items=collection_points,
                total_count=response.total_count,
                page_size=page_size,
                next_page_token=next_token,
            )
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
    ) -> PaginatedResponse[Region]:
        """List regions with optional filtering.

        Args:
            county: Optional filter by county name.
            altitude_band: Optional filter by altitude band (highland/midland/lowland).
            page_size: Number of results per page (default: 50).
            page_token: Token for pagination.
            active_only: Only return active regions (default: True).

        Returns:
            PaginatedResponse containing regions with pagination metadata.

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
            return PaginatedResponse.from_client_response(
                items=regions,
                total_count=response.total_count,
                page_size=page_size,
                next_page_token=next_token,
            )
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
    ) -> PerformanceSummary:
        """Get aggregated performance metrics for an entity.

        Args:
            entity_type: Type of entity ("farmer", "factory", "region").
            entity_id: ID of the entity.
            period: Period type ("daily", "weekly", "monthly", "yearly").
            period_start: Optional start of period (for specific date ranges).

        Returns:
            PerformanceSummary domain model with aggregated metrics.

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
    # Farmer Write Operations (2 methods)
    # =========================================================================

    @grpc_retry
    async def create_farmer(self, farmer_data: FarmerCreate) -> Farmer:
        """Create a new farmer.

        Args:
            farmer_data: FarmerCreate model with required farmer information.

        Returns:
            Created Farmer domain model.

        Raises:
            ValidationError: If data is invalid.
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_plantation_stub()
            request = plantation_pb2.CreateFarmerRequest(
                first_name=farmer_data.first_name,
                last_name=farmer_data.last_name,
                collection_point_id=farmer_data.collection_point_id,
                farm_location=plantation_pb2.GeoLocation(
                    latitude=farmer_data.latitude,
                    longitude=farmer_data.longitude,
                    altitude_meters=0,  # Will be fetched by service
                ),
                contact=plantation_pb2.ContactInfo(
                    phone=farmer_data.phone,
                ),
                farm_size_hectares=farmer_data.farm_size_hectares,
                national_id=farmer_data.national_id,
                grower_number=farmer_data.grower_number or "",
            )
            response = await stub.CreateFarmer(request, metadata=self._get_metadata())
            return self._proto_to_farmer(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Create farmer")
            raise

    @grpc_retry
    async def update_farmer(self, farmer_id: str, farmer_data: FarmerUpdate) -> Farmer:
        """Update an existing farmer.

        Args:
            farmer_id: The farmer ID (e.g., "WM-0001").
            farmer_data: FarmerUpdate model with fields to update.

        Returns:
            Updated Farmer domain model.

        Raises:
            NotFoundError: If farmer not found.
            ValidationError: If data is invalid.
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_plantation_stub()
            request = plantation_pb2.UpdateFarmerRequest(id=farmer_id)

            if farmer_data.first_name is not None:
                request.first_name = farmer_data.first_name
            if farmer_data.last_name is not None:
                request.last_name = farmer_data.last_name
            if farmer_data.phone is not None:
                request.contact.phone = farmer_data.phone
            if farmer_data.farm_size_hectares is not None:
                request.farm_size_hectares = farmer_data.farm_size_hectares
            if farmer_data.is_active is not None:
                request.is_active = farmer_data.is_active

            response = await stub.UpdateFarmer(request, metadata=self._get_metadata())
            return self._proto_to_farmer(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Update farmer {farmer_id}")
            raise

    # =========================================================================
    # Factory Write Operations (3 methods)
    # =========================================================================

    @grpc_retry
    async def create_factory(self, factory_data: FactoryCreate) -> Factory:
        """Create a new factory.

        Args:
            factory_data: FactoryCreate model with required factory information.

        Returns:
            Created Factory domain model.

        Raises:
            ValidationError: If data is invalid.
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_plantation_stub()
            request = plantation_pb2.CreateFactoryRequest(
                name=factory_data.name,
                code=factory_data.code,
                region_id=factory_data.region_id,
                location=plantation_pb2.GeoLocation(
                    latitude=factory_data.location.latitude,
                    longitude=factory_data.location.longitude,
                    altitude_meters=factory_data.location.altitude_meters,
                ),
                processing_capacity_kg=factory_data.processing_capacity_kg,
            )
            if factory_data.contact:
                request.contact.CopyFrom(
                    plantation_pb2.ContactInfo(
                        phone=factory_data.contact.phone,
                        email=factory_data.contact.email or "",
                        address=factory_data.contact.address or "",
                    )
                )
            if factory_data.quality_thresholds:
                request.quality_thresholds.CopyFrom(
                    plantation_pb2.QualityThresholds(
                        tier_1=factory_data.quality_thresholds.tier_1,
                        tier_2=factory_data.quality_thresholds.tier_2,
                        tier_3=factory_data.quality_thresholds.tier_3,
                    )
                )
            if factory_data.payment_policy:
                policy_type = self._payment_policy_type_to_proto(factory_data.payment_policy.policy_type)
                request.payment_policy.CopyFrom(
                    plantation_pb2.PaymentPolicy(
                        policy_type=policy_type,
                        tier_1_adjustment=factory_data.payment_policy.tier_1_adjustment,
                        tier_2_adjustment=factory_data.payment_policy.tier_2_adjustment,
                        tier_3_adjustment=factory_data.payment_policy.tier_3_adjustment,
                        below_tier_3_adjustment=factory_data.payment_policy.below_tier_3_adjustment,
                    )
                )
            response = await stub.CreateFactory(request, metadata=self._get_metadata())
            return self._proto_to_factory(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Create factory")
            raise

    @grpc_retry
    async def update_factory(self, factory_id: str, factory_data: FactoryUpdate) -> Factory:
        """Update an existing factory.

        Args:
            factory_id: The factory ID (e.g., "KEN-FAC-001").
            factory_data: FactoryUpdate model with fields to update.

        Returns:
            Updated Factory domain model.

        Raises:
            NotFoundError: If factory not found.
            ValidationError: If data is invalid.
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_plantation_stub()
            request = plantation_pb2.UpdateFactoryRequest(id=factory_id)

            if factory_data.name is not None:
                request.name = factory_data.name
            if factory_data.code is not None:
                request.code = factory_data.code
            if factory_data.location is not None:
                request.location.CopyFrom(
                    plantation_pb2.GeoLocation(
                        latitude=factory_data.location.latitude,
                        longitude=factory_data.location.longitude,
                        altitude_meters=factory_data.location.altitude_meters,
                    )
                )
            if factory_data.contact is not None:
                request.contact.CopyFrom(
                    plantation_pb2.ContactInfo(
                        phone=factory_data.contact.phone,
                        email=factory_data.contact.email or "",
                        address=factory_data.contact.address or "",
                    )
                )
            if factory_data.processing_capacity_kg is not None:
                request.processing_capacity_kg = factory_data.processing_capacity_kg
            if factory_data.quality_thresholds is not None:
                request.quality_thresholds.CopyFrom(
                    plantation_pb2.QualityThresholds(
                        tier_1=factory_data.quality_thresholds.tier_1,
                        tier_2=factory_data.quality_thresholds.tier_2,
                        tier_3=factory_data.quality_thresholds.tier_3,
                    )
                )
            if factory_data.payment_policy is not None:
                policy_type = self._payment_policy_type_to_proto(factory_data.payment_policy.policy_type)
                request.payment_policy.CopyFrom(
                    plantation_pb2.PaymentPolicy(
                        policy_type=policy_type,
                        tier_1_adjustment=factory_data.payment_policy.tier_1_adjustment,
                        tier_2_adjustment=factory_data.payment_policy.tier_2_adjustment,
                        tier_3_adjustment=factory_data.payment_policy.tier_3_adjustment,
                        below_tier_3_adjustment=factory_data.payment_policy.below_tier_3_adjustment,
                    )
                )
            if factory_data.is_active is not None:
                request.is_active = factory_data.is_active

            response = await stub.UpdateFactory(request, metadata=self._get_metadata())
            return self._proto_to_factory(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Update factory {factory_id}")
            raise

    @grpc_retry
    async def delete_factory(self, factory_id: str) -> bool:
        """Delete a factory (soft delete).

        Args:
            factory_id: The factory ID (e.g., "KEN-FAC-001").

        Returns:
            True if deletion was successful.

        Raises:
            NotFoundError: If factory not found.
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_plantation_stub()
            request = plantation_pb2.DeleteFactoryRequest(id=factory_id)
            response = await stub.DeleteFactory(request, metadata=self._get_metadata())
            return response.success
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Delete factory {factory_id}")
            raise

    # =========================================================================
    # Collection Point Write Operations (3 methods)
    # =========================================================================

    @grpc_retry
    async def create_collection_point(self, cp_data: CollectionPointCreate) -> CollectionPoint:
        """Create a new collection point.

        Args:
            cp_data: CollectionPointCreate model with required CP information.

        Returns:
            Created CollectionPoint domain model.

        Raises:
            ValidationError: If data is invalid.
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_plantation_stub()
            request = plantation_pb2.CreateCollectionPointRequest(
                name=cp_data.name,
                factory_id=cp_data.factory_id,
                location=plantation_pb2.GeoLocation(
                    latitude=cp_data.location.latitude,
                    longitude=cp_data.location.longitude,
                    altitude_meters=cp_data.location.altitude_meters,
                ),
                region_id=cp_data.region_id,
                clerk_id=cp_data.clerk_id or "",
                clerk_phone=cp_data.clerk_phone or "",
                status=cp_data.status,
            )
            if cp_data.operating_hours:
                request.operating_hours.CopyFrom(
                    plantation_pb2.OperatingHours(
                        weekdays=cp_data.operating_hours.weekdays,
                        weekends=cp_data.operating_hours.weekends,
                    )
                )
            if cp_data.collection_days:
                request.collection_days.extend(cp_data.collection_days)
            if cp_data.capacity:
                request.capacity.CopyFrom(
                    plantation_pb2.CollectionPointCapacity(
                        max_daily_kg=cp_data.capacity.max_daily_kg,
                        storage_type=cp_data.capacity.storage_type,
                        has_weighing_scale=cp_data.capacity.has_weighing_scale,
                        has_qc_device=cp_data.capacity.has_qc_device,
                    )
                )
            response = await stub.CreateCollectionPoint(request, metadata=self._get_metadata())
            return self._proto_to_collection_point(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Create collection point")
            raise

    @grpc_retry
    async def update_collection_point(
        self, collection_point_id: str, cp_data: CollectionPointUpdate
    ) -> CollectionPoint:
        """Update an existing collection point.

        Args:
            collection_point_id: The collection point ID (e.g., "nyeri-highland-cp-001").
            cp_data: CollectionPointUpdate model with fields to update.

        Returns:
            Updated CollectionPoint domain model.

        Raises:
            NotFoundError: If collection point not found.
            ValidationError: If data is invalid.
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_plantation_stub()
            request = plantation_pb2.UpdateCollectionPointRequest(id=collection_point_id)

            if cp_data.name is not None:
                request.name = cp_data.name
            if cp_data.clerk_id is not None:
                request.clerk_id = cp_data.clerk_id
            if cp_data.clerk_phone is not None:
                request.clerk_phone = cp_data.clerk_phone
            if cp_data.operating_hours is not None:
                request.operating_hours.CopyFrom(
                    plantation_pb2.OperatingHours(
                        weekdays=cp_data.operating_hours.weekdays,
                        weekends=cp_data.operating_hours.weekends,
                    )
                )
            if cp_data.collection_days is not None:
                request.collection_days.extend(cp_data.collection_days)
            if cp_data.capacity is not None:
                request.capacity.CopyFrom(
                    plantation_pb2.CollectionPointCapacity(
                        max_daily_kg=cp_data.capacity.max_daily_kg,
                        storage_type=cp_data.capacity.storage_type,
                        has_weighing_scale=cp_data.capacity.has_weighing_scale,
                        has_qc_device=cp_data.capacity.has_qc_device,
                    )
                )
            if cp_data.status is not None:
                request.status = cp_data.status

            response = await stub.UpdateCollectionPoint(request, metadata=self._get_metadata())
            return self._proto_to_collection_point(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Update collection point {collection_point_id}")
            raise

    @grpc_retry
    async def delete_collection_point(self, collection_point_id: str) -> bool:
        """Delete a collection point (soft delete).

        Args:
            collection_point_id: The collection point ID (e.g., "nyeri-highland-cp-001").

        Returns:
            True if deletion was successful.

        Raises:
            NotFoundError: If collection point not found.
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_plantation_stub()
            request = plantation_pb2.DeleteCollectionPointRequest(id=collection_point_id)
            response = await stub.DeleteCollectionPoint(request, metadata=self._get_metadata())
            return response.success
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Delete collection point {collection_point_id}")
            raise

    # =========================================================================
    # Region Write Operations (2 methods)
    # =========================================================================

    @grpc_retry
    async def create_region(self, region_data: RegionCreate) -> Region:
        """Create a new region.

        Args:
            region_data: RegionCreate model with required region information.

        Returns:
            Created Region domain model.

        Raises:
            ValidationError: If data is invalid.
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_plantation_stub()
            request = plantation_pb2.CreateRegionRequest(
                name=region_data.name,
                county=region_data.county,
                country=region_data.country,
            )
            # Build geography
            geography_proto = plantation_pb2.Geography(
                center_gps=plantation_pb2.GPS(
                    lat=region_data.geography.center_gps.lat,
                    lng=region_data.geography.center_gps.lng,
                ),
                radius_km=region_data.geography.radius_km,
                altitude_band=plantation_pb2.AltitudeBand(
                    min_meters=region_data.geography.altitude_band.min_meters,
                    max_meters=region_data.geography.altitude_band.max_meters,
                    label=self._altitude_band_to_proto(region_data.geography.altitude_band.label),
                ),
            )
            # Story 9.2: Include polygon boundary if provided
            if region_data.geography.boundary is not None:
                boundary = region_data.geography.boundary
                geography_proto.boundary.CopyFrom(
                    plantation_pb2.RegionBoundary(
                        type=boundary.type,
                        rings=[
                            plantation_pb2.PolygonRing(
                                points=[
                                    plantation_pb2.Coordinate(
                                        longitude=coord.longitude,
                                        latitude=coord.latitude,
                                    )
                                    for coord in ring.points
                                ]
                            )
                            for ring in boundary.rings
                        ],
                    )
                )
            # Story 9.2: Include computed area and perimeter if provided
            if region_data.geography.area_km2 is not None:
                geography_proto.area_km2 = region_data.geography.area_km2
            if region_data.geography.perimeter_km is not None:
                geography_proto.perimeter_km = region_data.geography.perimeter_km
            request.geography.CopyFrom(geography_proto)
            # Build flush calendar
            request.flush_calendar.CopyFrom(
                plantation_pb2.FlushCalendar(
                    first_flush=plantation_pb2.FlushPeriod(
                        start=region_data.flush_calendar.first_flush.start,
                        end=region_data.flush_calendar.first_flush.end,
                        characteristics=region_data.flush_calendar.first_flush.characteristics or "",
                    ),
                    monsoon_flush=plantation_pb2.FlushPeriod(
                        start=region_data.flush_calendar.monsoon_flush.start,
                        end=region_data.flush_calendar.monsoon_flush.end,
                        characteristics=region_data.flush_calendar.monsoon_flush.characteristics or "",
                    ),
                    autumn_flush=plantation_pb2.FlushPeriod(
                        start=region_data.flush_calendar.autumn_flush.start,
                        end=region_data.flush_calendar.autumn_flush.end,
                        characteristics=region_data.flush_calendar.autumn_flush.characteristics or "",
                    ),
                    dormant=plantation_pb2.FlushPeriod(
                        start=region_data.flush_calendar.dormant.start,
                        end=region_data.flush_calendar.dormant.end,
                        characteristics=region_data.flush_calendar.dormant.characteristics or "",
                    ),
                )
            )
            # Build agronomic
            request.agronomic.CopyFrom(
                plantation_pb2.Agronomic(
                    soil_type=region_data.agronomic.soil_type,
                    typical_diseases=region_data.agronomic.typical_diseases,
                    harvest_peak_hours=region_data.agronomic.harvest_peak_hours,
                    frost_risk=region_data.agronomic.frost_risk,
                )
            )
            # Build weather config
            request.weather_config.CopyFrom(
                plantation_pb2.WeatherConfig(
                    api_location=plantation_pb2.GPS(
                        lat=region_data.weather_config.api_location.lat,
                        lng=region_data.weather_config.api_location.lng,
                    ),
                    altitude_for_api=region_data.weather_config.altitude_for_api,
                    collection_time=region_data.weather_config.collection_time,
                )
            )
            response = await stub.CreateRegion(request, metadata=self._get_metadata())
            return self._proto_to_region(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Create region")
            raise

    @grpc_retry
    async def update_region(self, region_id: str, region_data: RegionUpdate) -> Region:
        """Update an existing region.

        Args:
            region_id: The region ID (e.g., "nyeri-highland").
            region_data: RegionUpdate model with fields to update.

        Returns:
            Updated Region domain model.

        Raises:
            NotFoundError: If region not found.
            ValidationError: If data is invalid.
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_plantation_stub()
            request = plantation_pb2.UpdateRegionRequest(region_id=region_id)

            if region_data.name is not None:
                request.name = region_data.name
            if region_data.geography is not None:
                geography_proto = plantation_pb2.Geography(
                    center_gps=plantation_pb2.GPS(
                        lat=region_data.geography.center_gps.lat,
                        lng=region_data.geography.center_gps.lng,
                    ),
                    radius_km=region_data.geography.radius_km,
                    altitude_band=plantation_pb2.AltitudeBand(
                        min_meters=region_data.geography.altitude_band.min_meters,
                        max_meters=region_data.geography.altitude_band.max_meters,
                        label=self._altitude_band_to_proto(region_data.geography.altitude_band.label),
                    ),
                )
                # Story 9.2: Include polygon boundary if provided
                if region_data.geography.boundary is not None:
                    boundary = region_data.geography.boundary
                    geography_proto.boundary.CopyFrom(
                        plantation_pb2.RegionBoundary(
                            type=boundary.type,
                            rings=[
                                plantation_pb2.PolygonRing(
                                    points=[
                                        plantation_pb2.Coordinate(
                                            longitude=coord.longitude,
                                            latitude=coord.latitude,
                                        )
                                        for coord in ring.points
                                    ]
                                )
                                for ring in boundary.rings
                            ],
                        )
                    )
                # Story 9.2: Include computed area and perimeter if provided
                if region_data.geography.area_km2 is not None:
                    geography_proto.area_km2 = region_data.geography.area_km2
                if region_data.geography.perimeter_km is not None:
                    geography_proto.perimeter_km = region_data.geography.perimeter_km
                request.geography.CopyFrom(geography_proto)
            if region_data.flush_calendar is not None:
                request.flush_calendar.CopyFrom(
                    plantation_pb2.FlushCalendar(
                        first_flush=plantation_pb2.FlushPeriod(
                            start=region_data.flush_calendar.first_flush.start,
                            end=region_data.flush_calendar.first_flush.end,
                            characteristics=region_data.flush_calendar.first_flush.characteristics or "",
                        ),
                        monsoon_flush=plantation_pb2.FlushPeriod(
                            start=region_data.flush_calendar.monsoon_flush.start,
                            end=region_data.flush_calendar.monsoon_flush.end,
                            characteristics=region_data.flush_calendar.monsoon_flush.characteristics or "",
                        ),
                        autumn_flush=plantation_pb2.FlushPeriod(
                            start=region_data.flush_calendar.autumn_flush.start,
                            end=region_data.flush_calendar.autumn_flush.end,
                            characteristics=region_data.flush_calendar.autumn_flush.characteristics or "",
                        ),
                        dormant=plantation_pb2.FlushPeriod(
                            start=region_data.flush_calendar.dormant.start,
                            end=region_data.flush_calendar.dormant.end,
                            characteristics=region_data.flush_calendar.dormant.characteristics or "",
                        ),
                    )
                )
            if region_data.agronomic is not None:
                request.agronomic.CopyFrom(
                    plantation_pb2.Agronomic(
                        soil_type=region_data.agronomic.soil_type,
                        typical_diseases=region_data.agronomic.typical_diseases,
                        harvest_peak_hours=region_data.agronomic.harvest_peak_hours,
                        frost_risk=region_data.agronomic.frost_risk,
                    )
                )
            if region_data.weather_config is not None:
                request.weather_config.CopyFrom(
                    plantation_pb2.WeatherConfig(
                        api_location=plantation_pb2.GPS(
                            lat=region_data.weather_config.api_location.lat,
                            lng=region_data.weather_config.api_location.lng,
                        ),
                        altitude_for_api=region_data.weather_config.altitude_for_api,
                        collection_time=region_data.weather_config.collection_time,
                    )
                )
            if region_data.is_active is not None:
                request.is_active = region_data.is_active

            response = await stub.UpdateRegion(request, metadata=self._get_metadata())
            return self._proto_to_region(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Update region {region_id}")
            raise

    # =========================================================================
    # Communication Preferences Write Operations (1 method)
    # =========================================================================

    @grpc_retry
    async def update_communication_preferences(
        self,
        farmer_id: str,
        notification_channel: NotificationChannel | None = None,
        interaction_pref: InteractionPreference | None = None,
        pref_lang: PreferredLanguage | None = None,
    ) -> Farmer:
        """Update farmer communication preferences.

        Args:
            farmer_id: The farmer ID (e.g., "WM-0001").
            notification_channel: Optional new notification channel.
            interaction_pref: Optional new interaction preference.
            pref_lang: Optional new preferred language.

        Returns:
            Updated Farmer domain model.

        Raises:
            NotFoundError: If farmer not found.
            ValidationError: If data is invalid.
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_plantation_stub()
            request = plantation_pb2.UpdateCommunicationPreferencesRequest(
                farmer_id=farmer_id,
            )
            if notification_channel is not None:
                request.notification_channel = self._notification_channel_to_proto(notification_channel)
            if interaction_pref is not None:
                request.interaction_pref = self._interaction_pref_to_proto(interaction_pref)
            if pref_lang is not None:
                request.pref_lang = self._preferred_language_to_proto(pref_lang)

            response = await stub.UpdateCommunicationPreferences(request, metadata=self._get_metadata())
            return self._proto_to_farmer(response.farmer)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, f"Update communication preferences for farmer {farmer_id}")
            raise

    # =========================================================================
    # Domain Model to Proto Converters (for write operations)
    # =========================================================================

    def _payment_policy_type_to_proto(self, policy_type: PaymentPolicyType) -> int:
        """Convert PaymentPolicyType to proto enum value."""
        mapping = {
            PaymentPolicyType.SPLIT_PAYMENT: plantation_pb2.PaymentPolicyType.PAYMENT_POLICY_TYPE_SPLIT_PAYMENT,
            PaymentPolicyType.WEEKLY_BONUS: plantation_pb2.PaymentPolicyType.PAYMENT_POLICY_TYPE_WEEKLY_BONUS,
            PaymentPolicyType.DELAYED_PAYMENT: plantation_pb2.PaymentPolicyType.PAYMENT_POLICY_TYPE_DELAYED_PAYMENT,
            PaymentPolicyType.FEEDBACK_ONLY: plantation_pb2.PaymentPolicyType.PAYMENT_POLICY_TYPE_FEEDBACK_ONLY,
        }
        return mapping.get(policy_type, plantation_pb2.PaymentPolicyType.PAYMENT_POLICY_TYPE_FEEDBACK_ONLY)

    def _altitude_band_to_proto(self, label: AltitudeBandLabel) -> int:
        """Convert AltitudeBandLabel to proto enum value."""
        mapping = {
            AltitudeBandLabel.HIGHLAND: plantation_pb2.AltitudeBandLabel.ALTITUDE_BAND_HIGHLAND,
            AltitudeBandLabel.MIDLAND: plantation_pb2.AltitudeBandLabel.ALTITUDE_BAND_MIDLAND,
            AltitudeBandLabel.LOWLAND: plantation_pb2.AltitudeBandLabel.ALTITUDE_BAND_LOWLAND,
        }
        return mapping.get(label, plantation_pb2.AltitudeBandLabel.ALTITUDE_BAND_HIGHLAND)

    def _notification_channel_to_proto(self, channel: NotificationChannel) -> int:
        """Convert NotificationChannel to proto enum value."""
        mapping = {
            NotificationChannel.SMS: plantation_pb2.NotificationChannel.NOTIFICATION_CHANNEL_SMS,
            NotificationChannel.WHATSAPP: plantation_pb2.NotificationChannel.NOTIFICATION_CHANNEL_WHATSAPP,
        }
        return mapping.get(channel, plantation_pb2.NotificationChannel.NOTIFICATION_CHANNEL_SMS)

    def _interaction_pref_to_proto(self, pref: InteractionPreference) -> int:
        """Convert InteractionPreference to proto enum value."""
        mapping = {
            InteractionPreference.TEXT: plantation_pb2.InteractionPreference.INTERACTION_PREFERENCE_TEXT,
            InteractionPreference.VOICE: plantation_pb2.InteractionPreference.INTERACTION_PREFERENCE_VOICE,
        }
        return mapping.get(pref, plantation_pb2.InteractionPreference.INTERACTION_PREFERENCE_TEXT)

    def _preferred_language_to_proto(self, lang: PreferredLanguage) -> int:
        """Convert PreferredLanguage to proto enum value."""
        mapping = {
            PreferredLanguage.SWAHILI: plantation_pb2.PreferredLanguage.PREFERRED_LANGUAGE_SW,
            PreferredLanguage.KIKUYU: plantation_pb2.PreferredLanguage.PREFERRED_LANGUAGE_KI,
            PreferredLanguage.LUO: plantation_pb2.PreferredLanguage.PREFERRED_LANGUAGE_LUO,
            PreferredLanguage.ENGLISH: plantation_pb2.PreferredLanguage.PREFERRED_LANGUAGE_EN,
        }
        return mapping.get(lang, plantation_pb2.PreferredLanguage.PREFERRED_LANGUAGE_SW)

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

        # Story 9.2: Convert boundary if present
        boundary = None
        if proto.HasField("geography") and proto.geography.HasField("boundary"):
            from fp_common.models.value_objects import Coordinate, PolygonRing, RegionBoundary

            boundary = RegionBoundary(
                type=proto.geography.boundary.type or "Polygon",
                rings=[
                    PolygonRing(
                        points=[
                            Coordinate(
                                longitude=coord.longitude,
                                latitude=coord.latitude,
                            )
                            for coord in ring.points
                        ]
                    )
                    for ring in proto.geography.boundary.rings
                ],
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
                # Story 9.2: Include boundary and computed values
                boundary=boundary,
                area_km2=proto.geography.area_km2
                if proto.HasField("geography") and proto.geography.HasField("area_km2")
                else None,
                perimeter_km=proto.geography.perimeter_km
                if proto.HasField("geography") and proto.geography.HasField("perimeter_km")
                else None,
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

    def _proto_to_performance_summary(self, proto: plantation_pb2.PerformanceSummary) -> PerformanceSummary:
        """Convert PerformanceSummary proto to domain model."""
        return PerformanceSummary(
            id=proto.id,
            entity_type=proto.entity_type,
            entity_id=proto.entity_id,
            period=proto.period,
            period_start=_timestamp_to_datetime(proto.period_start),
            period_end=_timestamp_to_datetime(proto.period_end),
            total_green_leaf_kg=proto.total_green_leaf_kg,
            total_made_tea_kg=proto.total_made_tea_kg,
            collection_count=proto.collection_count,
            average_quality_score=proto.average_quality_score,
            created_at=_timestamp_to_datetime(proto.created_at),
            updated_at=_timestamp_to_datetime(proto.updated_at),
        )
