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

    pass


class NotFoundError(Exception):
    """Raised when a resource is not found."""

    pass


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
                raise ServiceUnavailableError(
                    f"Plantation service unavailable: {e.details()}"
                ) from e
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
                raise ServiceUnavailableError(
                    f"Plantation service unavailable: {e.details()}"
                ) from e
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
                raise ServiceUnavailableError(
                    f"Plantation service unavailable: {e.details()}"
                ) from e
            raise

    @retry(
        retry=retry_if_exception_type(grpc.aio.AioRpcError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def get_farmers_by_collection_point(
        self, collection_point_id: str
    ) -> list[dict[str, Any]]:
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
            request = plantation_pb2.ListFarmersRequest(
                collection_point_id=collection_point_id
            )
            metadata = [("dapr-app-id", settings.plantation_app_id)]

            response = await stub.ListFarmers(request, metadata=metadata)

            return [self._farmer_to_dict(f) for f in response.farmers]

        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                raise ServiceUnavailableError(
                    f"Plantation service unavailable: {e.details()}"
                ) from e
            raise

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
            "notification_channel": plantation_pb2.NotificationChannel.Name(
                farmer.notification_channel
            ),
            "interaction_pref": plantation_pb2.InteractionPreference.Name(
                farmer.interaction_pref
            ),
            "pref_lang": plantation_pb2.PreferredLanguage.Name(farmer.pref_lang),
            "is_active": farmer.is_active,
        }

    def _farmer_summary_to_dict(
        self, summary: plantation_pb2.FarmerSummary
    ) -> dict[str, Any]:
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
            "trend_direction": plantation_pb2.TrendDirection.Name(
                summary.trend_direction
            ),
            "notification_channel": plantation_pb2.NotificationChannel.Name(
                summary.notification_channel
            ),
            "interaction_pref": plantation_pb2.InteractionPreference.Name(
                summary.interaction_pref
            ),
            "pref_lang": plantation_pb2.PreferredLanguage.Name(summary.pref_lang),
        }

        # Add historical metrics if present
        if summary.HasField("historical"):
            hist = summary.historical
            result["historical"] = {
                "avg_grade": hist.avg_grade,
                "total_kg": hist.total_kg,
                "delivery_count": hist.delivery_count,
                "improvement_trend": plantation_pb2.TrendDirection.Name(
                    hist.improvement_trend
                ),
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

    def _collection_point_to_dict(
        self, cp: plantation_pb2.CollectionPoint
    ) -> dict[str, Any]:
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

    async def close(self) -> None:
        """Close the gRPC channel."""
        if self._channel:
            await self._channel.close()
