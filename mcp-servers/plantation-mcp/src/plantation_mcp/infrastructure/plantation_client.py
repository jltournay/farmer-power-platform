"""Plantation Model service client."""

import grpc
import structlog
from fp_common.converters import (
    collection_point_from_proto,
    factory_from_proto,
    farmer_from_proto,
    farmer_summary_from_proto,
    region_from_proto,
)
from fp_common.models import CollectionPoint, Factory, Farmer, Region
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

    Note:
        All methods return Pydantic models instead of dicts.
        Call model.model_dump() at serialization boundaries if needed.
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
                if settings.plantation_grpc_host:
                    # Direct connection to Plantation Model gRPC server
                    # Used when DAPR service invocation is not available
                    target = settings.plantation_grpc_host
                    logger.info(
                        "Connecting directly to Plantation Model gRPC",
                        target=target,
                    )
                else:
                    # Connect via DAPR sidecar (localhost:50001 is DAPR's gRPC port)
                    # DAPR routes to plantation-model app
                    dapr_grpc_port = 50001
                    target = f"localhost:{dapr_grpc_port}"
                    logger.info(
                        "Connecting via DAPR service invocation",
                        target=target,
                        app_id=settings.plantation_app_id,
                    )
                self._channel = grpc.aio.insecure_channel(target)
            self._stub = plantation_pb2_grpc.PlantationServiceStub(self._channel)
        return self._stub

    def _get_metadata(self) -> list[tuple[str, str]]:
        """Get gRPC call metadata.

        Returns DAPR metadata for service invocation when using DAPR,
        or empty list for direct connections.
        """
        if settings.plantation_grpc_host:
            # Direct connection - no DAPR metadata needed
            return []
        # DAPR service invocation - add app-id metadata
        return [("dapr-app-id", settings.plantation_app_id)]

    @retry(
        retry=retry_if_exception_type(grpc.aio.AioRpcError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def get_farmer(self, farmer_id: str) -> Farmer:
        """Get farmer by ID.

        Args:
            farmer_id: The farmer ID (e.g., WM-0001).

        Returns:
            Farmer Pydantic model.

        Raises:
            NotFoundError: If farmer not found.
            ServiceUnavailableError: If service is unavailable.

        """
        try:
            stub = await self._get_stub()
            request = plantation_pb2.GetFarmerRequest(id=farmer_id)

            response = await stub.GetFarmer(request, metadata=self._get_metadata())

            return farmer_from_proto(response)

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
    async def get_farmer_summary(self, farmer_id: str) -> dict:
        """Get farmer performance summary.

        Args:
            farmer_id: The farmer ID.

        Returns:
            Dict with farmer summary including performance metrics.
            (Returns dict because FarmerSummary is a composite view)

        Raises:
            NotFoundError: If farmer not found.
            ServiceUnavailableError: If service is unavailable.

        """
        try:
            stub = await self._get_stub()
            request = plantation_pb2.GetFarmerSummaryRequest(farmer_id=farmer_id)

            response = await stub.GetFarmerSummary(request, metadata=self._get_metadata())

            return farmer_summary_from_proto(response)

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
    async def get_collection_point(self, collection_point_id: str) -> CollectionPoint:
        """Get collection point by ID.

        Args:
            collection_point_id: The collection point ID.

        Returns:
            CollectionPoint Pydantic model.

        Raises:
            NotFoundError: If collection point not found.
            ServiceUnavailableError: If service is unavailable.

        """
        try:
            stub = await self._get_stub()
            request = plantation_pb2.GetCollectionPointRequest(id=collection_point_id)

            response = await stub.GetCollectionPoint(request, metadata=self._get_metadata())

            return collection_point_from_proto(response)

        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                raise NotFoundError(f"Collection point not found: {collection_point_id}") from e
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                raise ServiceUnavailableError(f"Plantation service unavailable: {e.details()}") from e
            raise

    @retry(
        retry=retry_if_exception_type(grpc.aio.AioRpcError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def get_collection_points(self, factory_id: str) -> list[CollectionPoint]:
        """Get collection points for a factory.

        Args:
            factory_id: The factory ID.

        Returns:
            List of CollectionPoint Pydantic models.

        Raises:
            ServiceUnavailableError: If service is unavailable.

        """
        try:
            stub = await self._get_stub()
            request = plantation_pb2.ListCollectionPointsRequest(factory_id=factory_id)

            response = await stub.ListCollectionPoints(request, metadata=self._get_metadata())

            return [collection_point_from_proto(cp) for cp in response.collection_points]

        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                raise ServiceUnavailableError(f"Plantation service unavailable: {e.details()}") from e
            raise

    async def get_farmers_by_collection_point(self, collection_point_id: str) -> list[Farmer]:
        """Get farmers at a collection point.

        Story 9.5a: Farmer-CP relationship is now N:M via CollectionPoint.farmer_ids.
        This method gets the CP first, then fetches each farmer by ID.

        Args:
            collection_point_id: The collection point ID.

        Returns:
            List of Farmer Pydantic models.

        Raises:
            NotFoundError: If collection point not found.
            ServiceUnavailableError: If service is unavailable.

        """
        # Get the collection point to access farmer_ids (Story 9.5a)
        cp = await self.get_collection_point(collection_point_id)

        if not cp.farmer_ids:
            return []

        # Fetch each farmer by ID
        farmers = []
        for farmer_id in cp.farmer_ids:
            try:
                farmer = await self.get_farmer(farmer_id)
                farmers.append(farmer)
            except NotFoundError:
                # Skip farmers that no longer exist (data consistency issue)
                logger.warning(
                    "Farmer in CP farmer_ids not found",
                    farmer_id=farmer_id,
                    collection_point_id=collection_point_id,
                )
                continue

        return farmers

    @retry(
        retry=retry_if_exception_type(grpc.aio.AioRpcError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def get_factory(self, factory_id: str) -> Factory:
        """Get factory by ID.

        Args:
            factory_id: The factory ID (e.g., KEN-FAC-001).

        Returns:
            Factory Pydantic model with quality_thresholds.

        Raises:
            NotFoundError: If factory not found.
            ServiceUnavailableError: If service is unavailable.

        """
        try:
            stub = await self._get_stub()
            request = plantation_pb2.GetFactoryRequest(id=factory_id)

            response = await stub.GetFactory(request, metadata=self._get_metadata())

            return factory_from_proto(response)

        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                raise NotFoundError(f"Factory not found: {factory_id}") from e
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                raise ServiceUnavailableError(f"Plantation service unavailable: {e.details()}") from e
            raise

    # =========================================================================
    # Region Methods (Story 1.8)
    # =========================================================================

    @retry(
        retry=retry_if_exception_type(grpc.aio.AioRpcError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def get_region(self, region_id: str) -> Region:
        """Get region by ID.

        Args:
            region_id: The region ID (e.g., nyeri-highland).

        Returns:
            Region Pydantic model.

        Raises:
            NotFoundError: If region not found.
            ServiceUnavailableError: If service is unavailable.

        """
        try:
            stub = await self._get_stub()
            request = plantation_pb2.GetRegionRequest(region_id=region_id)

            response = await stub.GetRegion(request, metadata=self._get_metadata())

            return region_from_proto(response)

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
    ) -> list[Region]:
        """List regions with optional filtering.

        Args:
            county: Optional county filter.
            altitude_band: Optional altitude band filter (highland/midland/lowland).

        Returns:
            List of Region Pydantic models.

        Raises:
            ServiceUnavailableError: If service is unavailable.

        """
        try:
            stub = await self._get_stub()
            request = plantation_pb2.ListRegionsRequest(
                county=county or "",
                altitude_band=altitude_band or "",
            )

            response = await stub.ListRegions(request, metadata=self._get_metadata())

            return [region_from_proto(r) for r in response.regions]

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
    async def get_current_flush(self, region_id: str) -> dict:
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

            response = await stub.GetCurrentFlush(request, metadata=self._get_metadata())

            result: dict = {
                "region_id": response.region_id,
            }
            if response.HasField("current_flush"):
                flush = response.current_flush
                result["flush_name"] = flush.flush_name
                result["start_date"] = flush.start_date
                result["end_date"] = flush.end_date
                result["characteristics"] = flush.characteristics
                result["days_remaining"] = flush.days_remaining
            return result

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
    async def get_region_weather(self, region_id: str, days: int = 7) -> dict:
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

            response = await stub.GetRegionWeather(request, metadata=self._get_metadata())

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

    async def close(self) -> None:
        """Close the gRPC channel."""
        if self._channel:
            await self._channel.close()
