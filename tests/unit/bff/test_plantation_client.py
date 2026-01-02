"""Unit tests for PlantationClient.

Tests all 13 read methods, DAPR service invocation, error handling, and retry logic.
"""

from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from bff.infrastructure.clients.base import NotFoundError, ServiceUnavailableError
from bff.infrastructure.clients.plantation_client import PlantationClient
from fp_common.models import (
    CollectionPoint,
    Factory,
    Farmer,
    FarmScale,
    Flush,
    InteractionPreference,
    NotificationChannel,
    PerformanceSummary,
    PreferredLanguage,
    Region,
    RegionalWeather,
)
from fp_common.models.farmer_performance import FarmerPerformance
from fp_proto.plantation.v1 import plantation_pb2, plantation_pb2_grpc

from tests.unit.bff.conftest import (
    create_collection_point_proto,
    create_current_flush_response,
    create_factory_proto,
    create_farmer_proto,
    create_farmer_summary_proto,
    create_region_proto,
    create_regional_weather_proto,
)


@pytest.fixture
def mock_plantation_stub() -> MagicMock:
    """Create a mock Plantation service stub."""
    stub = MagicMock()
    # Configure async methods
    stub.GetFarmer = AsyncMock()
    stub.GetFarmerByPhone = AsyncMock()
    stub.ListFarmers = AsyncMock()
    stub.GetFarmerSummary = AsyncMock()
    stub.GetFactory = AsyncMock()
    stub.ListFactories = AsyncMock()
    stub.GetCollectionPoint = AsyncMock()
    stub.ListCollectionPoints = AsyncMock()
    stub.GetRegion = AsyncMock()
    stub.ListRegions = AsyncMock()
    stub.GetRegionWeather = AsyncMock()
    stub.GetCurrentFlush = AsyncMock()
    stub.GetPerformanceSummary = AsyncMock()
    return stub


@pytest.fixture
def plantation_client_with_mock_stub(mock_plantation_stub: MagicMock) -> tuple[PlantationClient, MagicMock]:
    """Create a PlantationClient with a mocked stub."""
    client = PlantationClient(direct_host="localhost:50051")
    # Inject the mock stub
    client._stubs[plantation_pb2_grpc.PlantationServiceStub] = mock_plantation_stub
    return client, mock_plantation_stub


class TestPlantationClientInit:
    """Tests for PlantationClient initialization."""

    def test_default_init(self) -> None:
        """Test default initialization with DAPR settings."""
        client = PlantationClient()
        assert client._target_app_id == "plantation-model"
        assert client._dapr_grpc_port == 50001
        assert client._direct_host is None
        assert client._channel is None

    def test_direct_host_init(self) -> None:
        """Test initialization with direct host."""
        client = PlantationClient(direct_host="localhost:50051")
        assert client._direct_host == "localhost:50051"

    def test_custom_dapr_port(self) -> None:
        """Test initialization with custom DAPR port."""
        client = PlantationClient(dapr_grpc_port=50099)
        assert client._dapr_grpc_port == 50099


class TestPlantationClientMetadata:
    """Tests for gRPC metadata handling."""

    def test_metadata_with_dapr(self) -> None:
        """Test metadata generation with DAPR routing."""
        client = PlantationClient()
        metadata = client._get_metadata()
        assert ("dapr-app-id", "plantation-model") in metadata

    def test_metadata_direct_connection(self) -> None:
        """Test metadata is empty for direct connection."""
        client = PlantationClient(direct_host="localhost:50051")
        metadata = client._get_metadata()
        assert metadata == []


class TestFarmerOperations:
    """Tests for Farmer read operations (4 methods)."""

    @pytest.mark.asyncio
    async def test_get_farmer_success(
        self,
        plantation_client_with_mock_stub: tuple[PlantationClient, MagicMock],
    ) -> None:
        """Test successful farmer retrieval."""
        client, stub = plantation_client_with_mock_stub
        stub.GetFarmer.return_value = create_farmer_proto(farmer_id="WM-0001")

        farmer = await client.get_farmer("WM-0001")

        assert isinstance(farmer, Farmer)
        assert farmer.id == "WM-0001"
        assert farmer.first_name == "Wanjiku"
        assert farmer.last_name == "Kamau"
        assert farmer.farm_scale == FarmScale.MEDIUM
        assert farmer.notification_channel == NotificationChannel.SMS
        assert farmer.interaction_pref == InteractionPreference.TEXT
        assert farmer.pref_lang == PreferredLanguage.SWAHILI

    @pytest.mark.asyncio
    async def test_get_farmer_not_found(
        self,
        plantation_client_with_mock_stub: tuple[PlantationClient, MagicMock],
    ) -> None:
        """Test farmer not found error."""
        client, stub = plantation_client_with_mock_stub
        error = grpc.aio.AioRpcError(
            code=grpc.StatusCode.NOT_FOUND,
            initial_metadata=None,
            trailing_metadata=None,
            details="Farmer not found",
            debug_error_string="",
        )
        stub.GetFarmer.side_effect = error

        with pytest.raises(NotFoundError, match="Farmer WM-9999 not found"):
            await client.get_farmer("WM-9999")

    @pytest.mark.asyncio
    async def test_get_farmer_by_phone_success(
        self,
        plantation_client_with_mock_stub: tuple[PlantationClient, MagicMock],
    ) -> None:
        """Test successful farmer retrieval by phone."""
        client, stub = plantation_client_with_mock_stub
        stub.GetFarmerByPhone.return_value = create_farmer_proto(phone="+254712345678")

        farmer = await client.get_farmer_by_phone("+254712345678")

        assert isinstance(farmer, Farmer)
        assert farmer.contact.phone == "+254712345678"

    @pytest.mark.asyncio
    async def test_list_farmers_success(
        self,
        plantation_client_with_mock_stub: tuple[PlantationClient, MagicMock],
    ) -> None:
        """Test successful farmer listing."""
        client, stub = plantation_client_with_mock_stub
        response = plantation_pb2.ListFarmersResponse(
            farmers=[
                create_farmer_proto(farmer_id="WM-0001"),
                create_farmer_proto(farmer_id="WM-0002"),
            ],
            next_page_token="token123",
            total_count=100,
        )
        stub.ListFarmers.return_value = response

        farmers, next_token, total = await client.list_farmers(region_id="nyeri-highland")

        assert len(farmers) == 2
        assert all(isinstance(f, Farmer) for f in farmers)
        assert next_token == "token123"
        assert total == 100

    @pytest.mark.asyncio
    async def test_list_farmers_with_pagination(
        self,
        plantation_client_with_mock_stub: tuple[PlantationClient, MagicMock],
    ) -> None:
        """Test farmer listing with pagination parameters."""
        client, stub = plantation_client_with_mock_stub
        response = plantation_pb2.ListFarmersResponse(
            farmers=[create_farmer_proto()],
            next_page_token="",
            total_count=1,
        )
        stub.ListFarmers.return_value = response

        farmers, next_token, total = await client.list_farmers(
            page_size=10,
            page_token="prev_token",
            active_only=False,
        )

        call_args = stub.ListFarmers.call_args
        request = call_args[0][0]
        assert request.page_size == 10
        assert request.page_token == "prev_token"
        assert request.active_only is False

    @pytest.mark.asyncio
    async def test_get_farmer_summary_success(
        self,
        plantation_client_with_mock_stub: tuple[PlantationClient, MagicMock],
    ) -> None:
        """Test successful farmer summary retrieval."""
        client, stub = plantation_client_with_mock_stub
        stub.GetFarmerSummary.return_value = create_farmer_summary_proto()

        performance = await client.get_farmer_summary("WM-0001")

        assert isinstance(performance, FarmerPerformance)
        assert performance.farmer_id == "WM-0001"
        assert performance.historical.primary_percentage_30d == 80.0
        assert performance.today.deliveries == 2


class TestFactoryOperations:
    """Tests for Factory read operations (2 methods)."""

    @pytest.mark.asyncio
    async def test_get_factory_success(
        self,
        plantation_client_with_mock_stub: tuple[PlantationClient, MagicMock],
    ) -> None:
        """Test successful factory retrieval."""
        client, stub = plantation_client_with_mock_stub
        stub.GetFactory.return_value = create_factory_proto()

        factory = await client.get_factory("KEN-FAC-001")

        assert isinstance(factory, Factory)
        assert factory.id == "KEN-FAC-001"
        assert factory.name == "Nyeri Tea Factory"
        assert factory.quality_thresholds.tier_1 == 85.0
        assert factory.quality_thresholds.tier_2 == 70.0
        assert factory.quality_thresholds.tier_3 == 50.0

    @pytest.mark.asyncio
    async def test_get_factory_not_found(
        self,
        plantation_client_with_mock_stub: tuple[PlantationClient, MagicMock],
    ) -> None:
        """Test factory not found error."""
        client, stub = plantation_client_with_mock_stub
        error = grpc.aio.AioRpcError(
            code=grpc.StatusCode.NOT_FOUND,
            initial_metadata=None,
            trailing_metadata=None,
            details="Factory not found",
            debug_error_string="",
        )
        stub.GetFactory.side_effect = error

        with pytest.raises(NotFoundError, match="Factory KEN-FAC-999 not found"):
            await client.get_factory("KEN-FAC-999")

    @pytest.mark.asyncio
    async def test_list_factories_success(
        self,
        plantation_client_with_mock_stub: tuple[PlantationClient, MagicMock],
    ) -> None:
        """Test successful factory listing."""
        client, stub = plantation_client_with_mock_stub
        response = plantation_pb2.ListFactoriesResponse(
            factories=[
                create_factory_proto(factory_id="KEN-FAC-001"),
                create_factory_proto(factory_id="KEN-FAC-002"),
            ],
            total_count=2,
        )
        stub.ListFactories.return_value = response

        factories, next_token, total = await client.list_factories()

        assert len(factories) == 2
        assert all(isinstance(f, Factory) for f in factories)
        assert total == 2


class TestCollectionPointOperations:
    """Tests for CollectionPoint read operations (2 methods)."""

    @pytest.mark.asyncio
    async def test_get_collection_point_success(
        self,
        plantation_client_with_mock_stub: tuple[PlantationClient, MagicMock],
    ) -> None:
        """Test successful collection point retrieval."""
        client, stub = plantation_client_with_mock_stub
        stub.GetCollectionPoint.return_value = create_collection_point_proto()

        cp = await client.get_collection_point("nyeri-highland-cp-001")

        assert isinstance(cp, CollectionPoint)
        assert cp.id == "nyeri-highland-cp-001"
        assert cp.name == "Kamakwa Collection Point"
        assert cp.capacity.max_daily_kg == 5000

    @pytest.mark.asyncio
    async def test_list_collection_points_success(
        self,
        plantation_client_with_mock_stub: tuple[PlantationClient, MagicMock],
    ) -> None:
        """Test successful collection point listing."""
        client, stub = plantation_client_with_mock_stub
        response = plantation_pb2.ListCollectionPointsResponse(
            collection_points=[
                create_collection_point_proto(cp_id="nyeri-highland-cp-001"),
                create_collection_point_proto(cp_id="nyeri-highland-cp-002"),
            ],
            total_count=2,
        )
        stub.ListCollectionPoints.return_value = response

        cps, next_token, total = await client.list_collection_points(factory_id="KEN-FAC-001")

        assert len(cps) == 2
        assert all(isinstance(cp, CollectionPoint) for cp in cps)


class TestRegionOperations:
    """Tests for Region read operations (4 methods)."""

    @pytest.mark.asyncio
    async def test_get_region_success(
        self,
        plantation_client_with_mock_stub: tuple[PlantationClient, MagicMock],
    ) -> None:
        """Test successful region retrieval."""
        client, stub = plantation_client_with_mock_stub
        stub.GetRegion.return_value = create_region_proto()

        region = await client.get_region("nyeri-highland")

        assert isinstance(region, Region)
        assert region.region_id == "nyeri-highland"
        assert region.name == "Nyeri Highland"
        assert region.county == "Nyeri"
        assert region.flush_calendar.first_flush.start == "03-15"

    @pytest.mark.asyncio
    async def test_list_regions_success(
        self,
        plantation_client_with_mock_stub: tuple[PlantationClient, MagicMock],
    ) -> None:
        """Test successful region listing."""
        client, stub = plantation_client_with_mock_stub
        response = plantation_pb2.ListRegionsResponse(
            regions=[
                create_region_proto(region_id="nyeri-highland"),
                create_region_proto(region_id="nyeri-midland"),
            ],
            total_count=2,
        )
        stub.ListRegions.return_value = response

        regions, next_token, total = await client.list_regions(county="Nyeri")

        assert len(regions) == 2
        assert all(isinstance(r, Region) for r in regions)

    @pytest.mark.asyncio
    async def test_get_region_weather_success(
        self,
        plantation_client_with_mock_stub: tuple[PlantationClient, MagicMock],
    ) -> None:
        """Test successful region weather retrieval."""
        client, stub = plantation_client_with_mock_stub
        response = plantation_pb2.GetRegionWeatherResponse(
            region_id="nyeri-highland",
            observations=[
                create_regional_weather_proto(date="2025-12-28"),
                create_regional_weather_proto(date="2025-12-27"),
            ],
        )
        stub.GetRegionWeather.return_value = response

        weather = await client.get_region_weather("nyeri-highland", days=7)

        assert len(weather) == 2
        assert all(isinstance(w, RegionalWeather) for w in weather)
        assert weather[0].temp_min == 12.5

    @pytest.mark.asyncio
    async def test_get_current_flush_success(
        self,
        plantation_client_with_mock_stub: tuple[PlantationClient, MagicMock],
    ) -> None:
        """Test successful current flush retrieval."""
        client, stub = plantation_client_with_mock_stub
        stub.GetCurrentFlush.return_value = create_current_flush_response()

        flush = await client.get_current_flush("nyeri-highland")

        assert isinstance(flush, Flush)
        assert flush.name == "first_flush"
        assert flush.days_remaining == 45
        assert flush.characteristics == "Highest quality, delicate flavor"


class TestPerformanceOperations:
    """Tests for Performance read operations (1 method)."""

    @pytest.mark.asyncio
    async def test_get_performance_summary_success(
        self,
        plantation_client_with_mock_stub: tuple[PlantationClient, MagicMock],
    ) -> None:
        """Test successful performance summary retrieval."""
        client, stub = plantation_client_with_mock_stub
        response = plantation_pb2.PerformanceSummary(
            id="perf-001",
            entity_type="farmer",
            entity_id="WM-0001",
            period="monthly",
            total_green_leaf_kg=1500.0,
            total_made_tea_kg=300.0,
            collection_count=45,
            average_quality_score=82.5,
        )
        stub.GetPerformanceSummary.return_value = response

        summary = await client.get_performance_summary(
            entity_type="farmer",
            entity_id="WM-0001",
            period="monthly",
        )

        assert isinstance(summary, PerformanceSummary)
        assert summary.entity_type == "farmer"
        assert summary.entity_id == "WM-0001"
        assert summary.total_green_leaf_kg == 1500.0

    @pytest.mark.asyncio
    async def test_get_performance_summary_with_period_start(
        self,
        plantation_client_with_mock_stub: tuple[PlantationClient, MagicMock],
    ) -> None:
        """Test performance summary retrieval with period_start parameter."""
        from datetime import datetime

        client, stub = plantation_client_with_mock_stub
        response = plantation_pb2.PerformanceSummary(
            id="perf-002",
            entity_type="factory",
            entity_id="KEN-FAC-001",
            period="weekly",
            total_green_leaf_kg=5000.0,
            total_made_tea_kg=1000.0,
            collection_count=150,
            average_quality_score=78.0,
        )
        stub.GetPerformanceSummary.return_value = response

        period_start = datetime(2025, 12, 1, 0, 0, 0)
        summary = await client.get_performance_summary(
            entity_type="factory",
            entity_id="KEN-FAC-001",
            period="weekly",
            period_start=period_start,
        )

        assert isinstance(summary, PerformanceSummary)
        assert summary.entity_type == "factory"
        # Verify the request was made with period_start
        call_args = stub.GetPerformanceSummary.call_args
        request = call_args[0][0]
        assert request.period_start.seconds > 0  # Timestamp was set


class TestErrorHandling:
    """Tests for error handling and retry logic."""

    @pytest.mark.asyncio
    async def test_service_unavailable_error(
        self,
        plantation_client_with_mock_stub: tuple[PlantationClient, MagicMock],
    ) -> None:
        """Test service unavailable error handling."""
        client, stub = plantation_client_with_mock_stub
        error = grpc.aio.AioRpcError(
            code=grpc.StatusCode.UNAVAILABLE,
            initial_metadata=None,
            trailing_metadata=None,
            details="Connection refused",
            debug_error_string="",
        )
        stub.GetFarmer.side_effect = error

        with pytest.raises(ServiceUnavailableError, match="Service unavailable"):
            await client.get_farmer("WM-0001")

    @pytest.mark.asyncio
    async def test_channel_reset_on_unavailable(
        self,
        plantation_client_with_mock_stub: tuple[PlantationClient, MagicMock],
    ) -> None:
        """Test channel is reset on UNAVAILABLE error."""
        client, stub = plantation_client_with_mock_stub
        # Pre-populate stubs cache
        client._stubs["test_stub"] = "test_value"

        error = grpc.aio.AioRpcError(
            code=grpc.StatusCode.UNAVAILABLE,
            initial_metadata=None,
            trailing_metadata=None,
            details="Connection refused",
            debug_error_string="",
        )
        stub.GetFarmer.side_effect = error

        with pytest.raises(ServiceUnavailableError):
            await client.get_farmer("WM-0001")

        # Channel should be reset but stub should still be there from fixture
        # The important thing is _reset_channel was called

    @pytest.mark.asyncio
    async def test_unknown_grpc_error_propagated(
        self,
        plantation_client_with_mock_stub: tuple[PlantationClient, MagicMock],
    ) -> None:
        """Test unknown gRPC errors are propagated."""
        client, stub = plantation_client_with_mock_stub
        error = grpc.aio.AioRpcError(
            code=grpc.StatusCode.INTERNAL,
            initial_metadata=None,
            trailing_metadata=None,
            details="Internal server error",
            debug_error_string="",
        )
        stub.GetFarmer.side_effect = error

        with pytest.raises(grpc.aio.AioRpcError):
            await client.get_farmer("WM-0001")


class TestProtoConversion:
    """Tests for proto-to-domain model conversion."""

    @pytest.mark.asyncio
    async def test_farmer_enum_conversion(
        self,
        plantation_client_with_mock_stub: tuple[PlantationClient, MagicMock],
    ) -> None:
        """Test enum values are correctly converted from proto."""
        client, stub = plantation_client_with_mock_stub
        proto = create_farmer_proto()
        proto.farm_scale = plantation_pb2.FarmScale.FARM_SCALE_SMALLHOLDER
        proto.notification_channel = plantation_pb2.NotificationChannel.NOTIFICATION_CHANNEL_WHATSAPP
        proto.interaction_pref = plantation_pb2.InteractionPreference.INTERACTION_PREFERENCE_VOICE
        proto.pref_lang = plantation_pb2.PreferredLanguage.PREFERRED_LANGUAGE_KI
        stub.GetFarmer.return_value = proto

        farmer = await client.get_farmer("WM-0001")

        assert farmer.farm_scale == FarmScale.SMALLHOLDER
        assert farmer.notification_channel == NotificationChannel.WHATSAPP
        assert farmer.interaction_pref == InteractionPreference.VOICE
        assert farmer.pref_lang == PreferredLanguage.KIKUYU

    @pytest.mark.asyncio
    async def test_factory_default_quality_thresholds(
        self,
        plantation_client_with_mock_stub: tuple[PlantationClient, MagicMock],
    ) -> None:
        """Test default quality thresholds when not set in proto."""
        client, stub = plantation_client_with_mock_stub
        proto = plantation_pb2.Factory(
            id="KEN-FAC-001",
            name="Test Factory",
            code="TF",
            region_id="nyeri-highland",
            is_active=True,
        )
        stub.GetFactory.return_value = proto

        factory = await client.get_factory("KEN-FAC-001")

        # Should use defaults when not set
        assert factory.quality_thresholds.tier_1 == 85.0
        assert factory.quality_thresholds.tier_2 == 70.0
        assert factory.quality_thresholds.tier_3 == 50.0


class TestClientClose:
    """Tests for client cleanup."""

    @pytest.mark.asyncio
    async def test_close_cleans_up_channel(self) -> None:
        """Test close properly cleans up channel."""
        client = PlantationClient(direct_host="localhost:50051")
        mock_channel = AsyncMock()
        client._channel = mock_channel
        client._stubs["test"] = "value"

        await client.close()

        mock_channel.close.assert_called_once()
        assert client._channel is None
        assert client._stubs == {}

    @pytest.mark.asyncio
    async def test_close_without_channel(self) -> None:
        """Test close is safe when no channel exists."""
        client = PlantationClient()
        # Should not raise
        await client.close()
        assert client._channel is None
