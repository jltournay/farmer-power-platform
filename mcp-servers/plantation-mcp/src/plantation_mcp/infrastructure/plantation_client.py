"""Plantation Model service client."""

from typing import Any

import grpc
import structlog
from fp_proto.plantation.v1 import plantation_pb2, plantation_pb2_grpc
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from plantation_mcp.config import settings

logger = structlog.get_logger(__name__)


class ServiceUnavailableError(Exception):
    """Raised when the Plantation Model service is unavailable."""


class NotFoundError(Exception):
    """Raised when a resource is not found."""


class PlantationClient:
    """Client for Plantation Model service via gRPC.

    Uses DAPR sidecar for service discovery when deployed in Kubernetes.
    """

    def __init__(self, channel: grpc.aio.Channel | None = None) -> None:
        """Initialize the client.

        Args:
            channel: Optional gRPC channel. If not provided, creates one to DAPR sidecar.

        """
        self._channel = channel
        self._stub: plantation_pb2_grpc.PlantationServiceStub | None = None

    async def _get_stub(self) -> plantation_pb2_grpc.PlantationServiceStub:
        """Get or create the gRPC stub."""
        if self._stub is None:
            if self._channel is None:
                # Connect via DAPR sidecar (localhost:50001 is DAPR's gRPC port)
                # DAPR routes to plantation-model app
                dapr_grpc_port = 50001
                target = f"localhost:{dapr_grpc_port}"
                self._channel = grpc.aio.insecure_channel(target)
            self._stub = plantation_pb2_grpc.PlantationServiceStub(self._channel)
        return self._stub

    @retry(
        retry=retry_if_exception_type(grpc.aio.AioRpcError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def get_farmer(self, farmer_id: str) -> dict[str, Any]:
        """Get farmer by ID.

        Args:
            farmer_id: The farmer ID (e.g., WM-0001).

        Returns:
            Dict with farmer details.

        Raises:
            NotFoundError: If farmer not found.
            ServiceUnavailableError: If service is unavailable.

        """
        try:
            stub = await self._get_stub()
            request = plantation_pb2.GetFarmerRequest(id=farmer_id)

            # Add DAPR metadata for service invocation
            metadata = [("dapr-app-id", settings.plantation_app_id)]

            response = await stub.GetFarmer(request, metadata=metadata)

            return self._farmer_to_dict(response)

        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                raise NotFoundError(f"Farmer not found: {farmer_id}") from e
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                raise ServiceUnavailableError(f"Plantation service unavailable: {e.details()}") from e
            raise

    @retry(
        retry=retry_if_exception_type(grpc.aio.AioRpcError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def get_farmer_summary(self, farmer_id: str) -> dict[str, Any]:
        """Get farmer performance summary.

        Args:
            farmer_id: The farmer ID.

        Returns:
            Dict with farmer summary including performance metrics.

        Raises:
            NotFoundError: If farmer not found.
            ServiceUnavailableError: If service is unavailable.

        """
        try:
            stub = await self._get_stub()
            request = plantation_pb2.GetFarmerSummaryRequest(farmer_id=farmer_id)
            metadata = [("dapr-app-id", settings.plantation_app_id)]

            response = await stub.GetFarmerSummary(request, metadata=metadata)

            return self._farmer_summary_to_dict(response)

        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                raise NotFoundError(f"Farmer summary not found: {farmer_id}") from e
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                raise ServiceUnavailableError(f"Plantation service unavailable: {e.details()}") from e
            raise

    @retry(
        retry=retry_if_exception_type(grpc.aio.AioRpcError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def get_collection_points(self, factory_id: str) -> list[dict[str, Any]]:
        """Get collection points for a factory.

        Args:
            factory_id: The factory ID.

        Returns:
            List of collection point dicts.

        Raises:
            ServiceUnavailableError: If service is unavailable.

        """
        try:
            stub = await self._get_stub()
            request = plantation_pb2.ListCollectionPointsRequest(factory_id=factory_id)
            metadata = [("dapr-app-id", settings.plantation_app_id)]

            response = await stub.ListCollectionPoints(request, metadata=metadata)

            return [self._collection_point_to_dict(cp) for cp in response.collection_points]

        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                raise ServiceUnavailableError(f"Plantation service unavailable: {e.details()}") from e
            raise

    @retry(
        retry=retry_if_exception_type(grpc.aio.AioRpcError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def get_farmers_by_collection_point(self, collection_point_id: str) -> list[dict[str, Any]]:
        """Get farmers at a collection point.

        Args:
            collection_point_id: The collection point ID.

        Returns:
            List of farmer dicts.

        Raises:
            ServiceUnavailableError: If service is unavailable.

        """
        try:
            stub = await self._get_stub()
            request = plantation_pb2.ListFarmersRequest(collection_point_id=collection_point_id)
            metadata = [("dapr-app-id", settings.plantation_app_id)]

            response = await stub.ListFarmers(request, metadata=metadata)

            return [self._farmer_to_dict(f) for f in response.farmers]

        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                raise ServiceUnavailableError(f"Plantation service unavailable: {e.details()}") from e
            raise

    @retry(
        retry=retry_if_exception_type(grpc.aio.AioRpcError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def get_factory(self, factory_id: str) -> dict[str, Any]:
        """Get factory by ID.

        Args:
            factory_id: The factory ID (e.g., KEN-FAC-001).

        Returns:
            Dict with factory details including quality_thresholds.

        Raises:
            NotFoundError: If factory not found.
            ServiceUnavailableError: If service is unavailable.

        """
        try:
            stub = await self._get_stub()
            request = plantation_pb2.GetFactoryRequest(id=factory_id)
            metadata = [("dapr-app-id", settings.plantation_app_id)]

            response = await stub.GetFactory(request, metadata=metadata)

            return self._factory_to_dict(response)

        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                raise NotFoundError(f"Factory not found: {factory_id}") from e
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                raise ServiceUnavailableError(f"Plantation service unavailable: {e.details()}") from e
            raise

    def _factory_to_dict(self, factory: plantation_pb2.Factory) -> dict[str, Any]:
        """Convert Factory proto to dict."""
        result = {
            "factory_id": factory.id,
            "name": factory.name,
            "code": factory.code,
            "region_id": factory.region_id,
            "location": {
                "latitude": factory.location.latitude if factory.location else 0,
                "longitude": factory.location.longitude if factory.location else 0,
                "altitude_meters": factory.location.altitude_meters if factory.location else 0,
            },
            "processing_capacity_kg": factory.processing_capacity_kg,
            "is_active": factory.is_active,
        }

        # Add quality thresholds (Story 1.7)
        if factory.HasField("quality_thresholds"):
            result["quality_thresholds"] = {
                "tier_1": factory.quality_thresholds.tier_1,
                "tier_2": factory.quality_thresholds.tier_2,
                "tier_3": factory.quality_thresholds.tier_3,
            }
        else:
            # Return defaults if not set
            result["quality_thresholds"] = {
                "tier_1": 85.0,
                "tier_2": 70.0,
                "tier_3": 50.0,
            }

        return result

    def _farmer_to_dict(self, farmer: plantation_pb2.Farmer) -> dict[str, Any]:
        """Convert Farmer proto to dict."""
        return {
            "farmer_id": farmer.id,
            "first_name": farmer.first_name,
            "last_name": farmer.last_name,
            "phone": farmer.contact.phone if farmer.contact else "",
            "farm_size_hectares": farmer.farm_size_hectares,
            "farm_scale": plantation_pb2.FarmScale.Name(farmer.farm_scale),
            "region_id": farmer.region_id,
            "collection_point_id": farmer.collection_point_id,
            "notification_channel": plantation_pb2.NotificationChannel.Name(farmer.notification_channel),
            "interaction_pref": plantation_pb2.InteractionPreference.Name(farmer.interaction_pref),
            "pref_lang": plantation_pb2.PreferredLanguage.Name(farmer.pref_lang),
            "is_active": farmer.is_active,
        }

    def _farmer_summary_to_dict(self, summary: plantation_pb2.FarmerSummary) -> dict[str, Any]:
        """Convert FarmerSummary proto to dict."""
        result: dict[str, Any] = {
            "farmer_id": summary.farmer_id,
            "first_name": summary.first_name,
            "last_name": summary.last_name,
            "phone": summary.phone,
            "collection_point_id": summary.collection_point_id,
            "farm_size_hectares": summary.farm_size_hectares,
            "farm_scale": plantation_pb2.FarmScale.Name(summary.farm_scale),
            "grading_model_id": summary.grading_model_id,
            "grading_model_version": summary.grading_model_version,
            "trend_direction": plantation_pb2.TrendDirection.Name(summary.trend_direction),
            "notification_channel": plantation_pb2.NotificationChannel.Name(summary.notification_channel),
            "interaction_pref": plantation_pb2.InteractionPreference.Name(summary.interaction_pref),
            "pref_lang": plantation_pb2.PreferredLanguage.Name(summary.pref_lang),
        }

        # Add historical metrics if present
        if summary.HasField("historical"):
            hist = summary.historical
            result["historical"] = {
                "avg_grade": hist.avg_grade,
                "total_kg": hist.total_kg,
                "delivery_count": hist.delivery_count,
                "improvement_trend": plantation_pb2.TrendDirection.Name(hist.improvement_trend),
            }

        # Add today metrics if present
        if summary.HasField("today"):
            today = summary.today
            result["today"] = {
                "metrics_date": today.metrics_date,
                "total_kg": today.total_kg,
                "avg_grade": today.avg_grade,
                "delivery_count": today.delivery_count,
            }

        return result

    def _collection_point_to_dict(self, cp: plantation_pb2.CollectionPoint) -> dict[str, Any]:
        """Convert CollectionPoint proto to dict."""
        return {
            "collection_point_id": cp.id,
            "name": cp.name,
            "code": cp.code,
            "factory_id": cp.factory_id,
            "region_id": cp.region_id,
            "location": {
                "latitude": cp.location.latitude if cp.location else 0,
                "longitude": cp.location.longitude if cp.location else 0,
            },
            "is_active": cp.is_active,
        }

    # =========================================================================
    # Region Methods (Story 1.8)
    # =========================================================================

    @retry(
        retry=retry_if_exception_type(grpc.aio.AioRpcError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def get_region(self, region_id: str) -> dict[str, Any]:
        """Get region by ID.

        Args:
            region_id: The region ID (e.g., nyeri-highland).

        Returns:
            Dict with region details.

        Raises:
            NotFoundError: If region not found.
            ServiceUnavailableError: If service is unavailable.

        """
        try:
            stub = await self._get_stub()
            request = plantation_pb2.GetRegionRequest(region_id=region_id)
            metadata = [("dapr-app-id", settings.plantation_app_id)]

            response = await stub.GetRegion(request, metadata=metadata)

            return self._region_to_dict(response)

        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                raise NotFoundError(f"Region not found: {region_id}") from e
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                raise ServiceUnavailableError(f"Plantation service unavailable: {e.details()}") from e
            raise

    @retry(
        retry=retry_if_exception_type(grpc.aio.AioRpcError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def list_regions(
        self,
        county: str | None = None,
        altitude_band: str | None = None,
    ) -> list[dict[str, Any]]:
        """List regions with optional filtering.

        Args:
            county: Optional county filter.
            altitude_band: Optional altitude band filter (highland/midland/lowland).

        Returns:
            List of region dicts.

        Raises:
            ServiceUnavailableError: If service is unavailable.

        """
        try:
            stub = await self._get_stub()
            request = plantation_pb2.ListRegionsRequest(
                county=county or "",
                altitude_band=altitude_band or "",
            )
            metadata = [("dapr-app-id", settings.plantation_app_id)]

            response = await stub.ListRegions(request, metadata=metadata)

            return [self._region_to_dict(r) for r in response.regions]

        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                raise ServiceUnavailableError(f"Plantation service unavailable: {e.details()}") from e
            raise

    @retry(
        retry=retry_if_exception_type(grpc.aio.AioRpcError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def get_current_flush(self, region_id: str) -> dict[str, Any]:
        """Get current flush period for a region.

        Args:
            region_id: The region ID.

        Returns:
            Dict with current flush period info.

        Raises:
            NotFoundError: If region not found.
            ServiceUnavailableError: If service is unavailable.

        """
        try:
            stub = await self._get_stub()
            request = plantation_pb2.GetCurrentFlushRequest(region_id=region_id)
            metadata = [("dapr-app-id", settings.plantation_app_id)]

            response = await stub.GetCurrentFlush(request, metadata=metadata)

            return {
                "region_id": response.region_id,
                "flush_name": response.flush_name,
                "start": response.start,
                "end": response.end,
                "characteristics": response.characteristics,
                "days_remaining": response.days_remaining,
            }

        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                raise NotFoundError(f"Region not found: {region_id}") from e
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                raise ServiceUnavailableError(f"Plantation service unavailable: {e.details()}") from e
            raise

    @retry(
        retry=retry_if_exception_type(grpc.aio.AioRpcError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def get_region_weather(self, region_id: str, days: int = 7) -> dict[str, Any]:
        """Get weather observations for a region.

        Args:
            region_id: The region ID.
            days: Number of days of history (default: 7).

        Returns:
            Dict with weather observations list.

        Raises:
            NotFoundError: If region not found.
            ServiceUnavailableError: If service is unavailable.

        """
        try:
            stub = await self._get_stub()
            request = plantation_pb2.GetRegionWeatherRequest(
                region_id=region_id,
                days=days,
            )
            metadata = [("dapr-app-id", settings.plantation_app_id)]

            response = await stub.GetRegionWeather(request, metadata=metadata)

            observations = []
            for obs in response.observations:
                observations.append(
                    {
                        "date": obs.date,
                        "temp_min": obs.temp_min,
                        "temp_max": obs.temp_max,
                        "precipitation_mm": obs.precipitation_mm,
                        "humidity_avg": obs.humidity_avg,
                        "source": obs.source,
                    }
                )

            return {
                "region_id": response.region_id,
                "observations": observations,
            }

        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                raise NotFoundError(f"Region not found: {region_id}") from e
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                raise ServiceUnavailableError(f"Plantation service unavailable: {e.details()}") from e
            raise

    def _region_to_dict(self, region: plantation_pb2.Region) -> dict[str, Any]:
        """Convert Region proto to dict."""
        result: dict[str, Any] = {
            "region_id": region.region_id,
            "name": region.name,
            "county": region.county,
            "country": region.country,
            "is_active": region.is_active,
        }

        # Geography
        if region.HasField("geography"):
            geo = region.geography
            result["geography"] = {
                "center_gps": {
                    "lat": geo.center_gps.lat if geo.HasField("center_gps") else 0,
                    "lng": geo.center_gps.lng if geo.HasField("center_gps") else 0,
                },
                "radius_km": geo.radius_km,
            }
            if geo.HasField("altitude_band"):
                result["geography"]["altitude_band"] = {
                    "min_meters": geo.altitude_band.min_meters,
                    "max_meters": geo.altitude_band.max_meters,
                    "label": plantation_pb2.AltitudeBandLabel.Name(geo.altitude_band.label),
                }

        # Flush calendar
        if region.HasField("flush_calendar"):
            fc = region.flush_calendar
            result["flush_calendar"] = {}
            for period_name in ["first_flush", "monsoon_flush", "autumn_flush", "dormant"]:
                period = getattr(fc, period_name, None)
                if period:
                    result["flush_calendar"][period_name] = {
                        "start": period.start,
                        "end": period.end,
                        "characteristics": period.characteristics,
                    }

        # Agronomic
        if region.HasField("agronomic"):
            result["agronomic"] = {
                "soil_type": region.agronomic.soil_type,
            }

        # Weather config
        if region.HasField("weather_config"):
            wc = region.weather_config
            result["weather_config"] = {
                "altitude_for_api": wc.altitude_for_api,
            }
            if wc.HasField("api_location"):
                result["weather_config"]["api_location"] = {
                    "lat": wc.api_location.lat,
                    "lng": wc.api_location.lng,
                }

        return result

    async def close(self) -> None:
        """Close the gRPC channel."""
        if self._channel:
            await self._channel.close()
