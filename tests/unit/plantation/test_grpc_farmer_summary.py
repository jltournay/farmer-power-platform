"""Unit tests for GetFarmerSummary gRPC service method and auto-init."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from fp_proto.plantation.v1 import plantation_pb2
from plantation_model.api.plantation_service import PlantationServiceServicer
from plantation_model.domain.models import (
    CollectionPoint,
    ContactInfo,
    Farmer,
    FarmerPerformance,
    FarmScale,
    GeoLocation,
    GradingAttribute,
    GradingModel,
    GradingType,
    HistoricalMetrics,
    OperatingHours,
    TodayMetrics,
    TrendDirection,
)
from plantation_model.domain.models.id_generator import IDGenerator
from plantation_model.infrastructure.google_elevation import GoogleElevationClient
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


class TestFarmerSummaryGrpcService:
    """Tests for GetFarmerSummary gRPC service method (Task 8.7)."""

    @pytest.fixture
    def mock_factory_repo(self) -> MagicMock:
        """Create a mock factory repository."""
        return MagicMock(spec=FactoryRepository)

    @pytest.fixture
    def mock_cp_repo(self) -> MagicMock:
        """Create a mock collection point repository."""
        return MagicMock(spec=CollectionPointRepository)

    @pytest.fixture
    def mock_farmer_repo(self) -> MagicMock:
        """Create a mock farmer repository."""
        return MagicMock(spec=FarmerRepository)

    @pytest.fixture
    def mock_farmer_performance_repo(self) -> MagicMock:
        """Create a mock farmer performance repository."""
        return MagicMock(spec=FarmerPerformanceRepository)

    @pytest.fixture
    def mock_grading_model_repo(self) -> MagicMock:
        """Create a mock grading model repository."""
        return MagicMock(spec=GradingModelRepository)

    @pytest.fixture
    def mock_id_generator(self) -> MagicMock:
        """Create a mock ID generator."""
        return MagicMock(spec=IDGenerator)

    @pytest.fixture
    def mock_elevation_client(self) -> MagicMock:
        """Create a mock elevation client."""
        return MagicMock(spec=GoogleElevationClient)

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create a mock gRPC context."""
        context = MagicMock(spec=grpc.aio.ServicerContext)
        context.abort = AsyncMock(side_effect=grpc.RpcError())
        return context

    @pytest.fixture
    def servicer(
        self,
        mock_factory_repo: MagicMock,
        mock_cp_repo: MagicMock,
        mock_farmer_repo: MagicMock,
        mock_farmer_performance_repo: MagicMock,
        mock_grading_model_repo: MagicMock,
        mock_id_generator: MagicMock,
        mock_elevation_client: MagicMock,
    ) -> PlantationServiceServicer:
        """Create a servicer with mock dependencies.

        Story 0.6.14: No longer requires dapr_client - uses module-level publish_event().
        """
        return PlantationServiceServicer(
            factory_repo=mock_factory_repo,
            collection_point_repo=mock_cp_repo,
            farmer_repo=mock_farmer_repo,
            id_generator=mock_id_generator,
            elevation_client=mock_elevation_client,
            grading_model_repo=mock_grading_model_repo,
            farmer_performance_repo=mock_farmer_performance_repo,
        )

    @pytest.fixture
    def sample_farmer(self) -> Farmer:
        """Create a sample farmer for testing."""
        return Farmer(
            id="WM-0001",
            first_name="John",
            last_name="Mwangi",
            collection_point_id="nyeri-highland-cp-001",
            region_id="nyeri-highland",
            farm_location=GeoLocation(latitude=-0.4, longitude=36.9, altitude_meters=1800.0),
            contact=ContactInfo(phone="+254712345678"),
            farm_size_hectares=1.5,
            farm_scale=FarmScale.MEDIUM,
            national_id="12345678",
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    @pytest.fixture
    def sample_collection_point(self) -> CollectionPoint:
        """Create a sample collection point for testing."""
        return CollectionPoint(
            id="nyeri-highland-cp-001",
            name="Test CP",
            factory_id="KEN-FAC-001",
            location=GeoLocation(latitude=-0.4, longitude=36.9),
            region_id="nyeri-highland",
            operating_hours=OperatingHours(),
            collection_days=["mon", "wed", "fri"],
        )

    @pytest.fixture
    def sample_grading_model(self) -> GradingModel:
        """Create a sample grading model for testing."""
        return GradingModel(
            model_id="tbk_kenya_tea_v1",
            model_version="1.0.0",
            crops_name="Tea",
            market_name="Kenya_TBK",
            grading_type=GradingType.BINARY,
            attributes={
                "leaf_type": GradingAttribute(
                    num_classes=3,
                    classes=["bud", "one_leaf_bud", "coarse_leaf"],
                ),
            },
            grade_labels={"ACCEPT": "Primary", "REJECT": "Secondary"},
            active_at_factory=["KEN-FAC-001"],
        )

    @pytest.fixture
    def sample_farmer_performance(self) -> FarmerPerformance:
        """Create a sample farmer performance for testing."""
        return FarmerPerformance(
            farmer_id="WM-0001",
            grading_model_id="tbk_kenya_tea_v1",
            grading_model_version="1.0.0",
            farm_size_hectares=1.5,
            farm_scale=FarmScale.MEDIUM,
            historical=HistoricalMetrics(
                grade_distribution_30d={"Primary": 100, "Secondary": 20},
                attribute_distributions_30d={
                    "leaf_type": {"bud": 50, "one_leaf_bud": 40, "coarse_leaf": 30},
                },
                primary_percentage_30d=83.3,
                total_kg_30d=150.0,
                improvement_trend=TrendDirection.IMPROVING,
            ),
            today=TodayMetrics(
                deliveries=2,
                total_kg=25.0,
                grade_counts={"Primary": 2},
            ),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    # =========================================================================
    # GetFarmerSummary Tests (Task 8.7)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_farmer_summary_with_performance(
        self,
        servicer: PlantationServiceServicer,
        mock_farmer_repo: MagicMock,
        mock_farmer_performance_repo: MagicMock,
        mock_context: MagicMock,
        sample_farmer: Farmer,
        sample_farmer_performance: FarmerPerformance,
    ) -> None:
        """Test GetFarmerSummary returns farmer with performance data."""
        mock_farmer_repo.get_by_id = AsyncMock(return_value=sample_farmer)
        mock_farmer_performance_repo.get_by_farmer_id = AsyncMock(return_value=sample_farmer_performance)

        request = plantation_pb2.GetFarmerSummaryRequest(farmer_id="WM-0001")
        result = await servicer.GetFarmerSummary(request, mock_context)

        assert result.farmer_id == "WM-0001"
        assert result.first_name == "John"
        assert result.grading_model_id == "tbk_kenya_tea_v1"
        assert result.historical.primary_percentage_30d == pytest.approx(83.3, 0.1)
        assert result.today.deliveries == 2
        assert result.today.total_kg == 25.0

    @pytest.mark.asyncio
    async def test_get_farmer_summary_farmer_not_found(
        self,
        servicer: PlantationServiceServicer,
        mock_farmer_repo: MagicMock,
        mock_context: MagicMock,
    ) -> None:
        """Test GetFarmerSummary aborts when farmer doesn't exist."""
        mock_farmer_repo.get_by_id = AsyncMock(return_value=None)

        request = plantation_pb2.GetFarmerSummaryRequest(farmer_id="NONEXISTENT")

        with pytest.raises(grpc.RpcError):
            await servicer.GetFarmerSummary(request, mock_context)

        mock_context.abort.assert_called_once()
        call_args = mock_context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_farmer_summary_no_performance_returns_defaults(
        self,
        servicer: PlantationServiceServicer,
        mock_farmer_repo: MagicMock,
        mock_farmer_performance_repo: MagicMock,
        mock_cp_repo: MagicMock,
        mock_grading_model_repo: MagicMock,
        mock_context: MagicMock,
        sample_farmer: Farmer,
        sample_collection_point: CollectionPoint,
        sample_grading_model: GradingModel,
    ) -> None:
        """Test GetFarmerSummary returns default metrics when no performance exists."""
        mock_farmer_repo.get_by_id = AsyncMock(return_value=sample_farmer)
        mock_farmer_performance_repo.get_by_farmer_id = AsyncMock(return_value=None)
        mock_cp_repo.get_by_id = AsyncMock(return_value=sample_collection_point)
        mock_grading_model_repo.get_by_factory = AsyncMock(return_value=sample_grading_model)

        request = plantation_pb2.GetFarmerSummaryRequest(farmer_id="WM-0001")
        result = await servicer.GetFarmerSummary(request, mock_context)

        # Should return farmer data with default empty performance
        assert result.farmer_id == "WM-0001"
        assert result.grading_model_id == "tbk_kenya_tea_v1"
        assert result.historical.primary_percentage_30d == 0.0
        assert result.today.deliveries == 0

    @pytest.mark.asyncio
    async def test_get_farmer_summary_with_attribute_distributions(
        self,
        servicer: PlantationServiceServicer,
        mock_farmer_repo: MagicMock,
        mock_farmer_performance_repo: MagicMock,
        mock_context: MagicMock,
        sample_farmer: Farmer,
        sample_farmer_performance: FarmerPerformance,
    ) -> None:
        """Test GetFarmerSummary includes attribute distributions for root-cause analysis."""
        mock_farmer_repo.get_by_id = AsyncMock(return_value=sample_farmer)
        mock_farmer_performance_repo.get_by_farmer_id = AsyncMock(return_value=sample_farmer_performance)

        request = plantation_pb2.GetFarmerSummaryRequest(farmer_id="WM-0001")
        result = await servicer.GetFarmerSummary(request, mock_context)

        # Should include attribute-level distributions
        assert "leaf_type" in result.historical.attribute_distributions_30d
        leaf_type_dist = result.historical.attribute_distributions_30d["leaf_type"]
        assert leaf_type_dist.counts["bud"] == 50
        assert leaf_type_dist.counts["coarse_leaf"] == 30

    @pytest.mark.asyncio
    async def test_get_farmer_summary_with_trend_direction(
        self,
        servicer: PlantationServiceServicer,
        mock_farmer_repo: MagicMock,
        mock_farmer_performance_repo: MagicMock,
        mock_context: MagicMock,
        sample_farmer: Farmer,
        sample_farmer_performance: FarmerPerformance,
    ) -> None:
        """Test GetFarmerSummary includes trend direction (AC #4)."""
        mock_farmer_repo.get_by_id = AsyncMock(return_value=sample_farmer)
        mock_farmer_performance_repo.get_by_farmer_id = AsyncMock(return_value=sample_farmer_performance)

        request = plantation_pb2.GetFarmerSummaryRequest(farmer_id="WM-0001")
        result = await servicer.GetFarmerSummary(request, mock_context)

        assert result.historical.improvement_trend == plantation_pb2.TREND_DIRECTION_IMPROVING


class TestFarmerPerformanceAutoInit:
    """Tests for auto-initialization of performance on farmer registration (Task 8.8)."""

    @pytest.fixture
    def mock_factory_repo(self) -> MagicMock:
        """Create a mock factory repository."""
        return MagicMock(spec=FactoryRepository)

    @pytest.fixture
    def mock_cp_repo(self) -> MagicMock:
        """Create a mock collection point repository."""
        return MagicMock(spec=CollectionPointRepository)

    @pytest.fixture
    def mock_farmer_repo(self) -> MagicMock:
        """Create a mock farmer repository."""
        return MagicMock(spec=FarmerRepository)

    @pytest.fixture
    def mock_farmer_performance_repo(self) -> MagicMock:
        """Create a mock farmer performance repository."""
        return MagicMock(spec=FarmerPerformanceRepository)

    @pytest.fixture
    def mock_grading_model_repo(self) -> MagicMock:
        """Create a mock grading model repository."""
        return MagicMock(spec=GradingModelRepository)

    @pytest.fixture
    def mock_id_generator(self) -> MagicMock:
        """Create a mock ID generator."""
        return MagicMock(spec=IDGenerator)

    @pytest.fixture
    def mock_elevation_client(self) -> MagicMock:
        """Create a mock elevation client."""
        return MagicMock(spec=GoogleElevationClient)

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create a mock gRPC context."""
        context = MagicMock(spec=grpc.aio.ServicerContext)
        context.abort = AsyncMock(side_effect=grpc.RpcError())
        return context

    @pytest.fixture
    def servicer(
        self,
        mock_factory_repo: MagicMock,
        mock_cp_repo: MagicMock,
        mock_farmer_repo: MagicMock,
        mock_farmer_performance_repo: MagicMock,
        mock_grading_model_repo: MagicMock,
        mock_id_generator: MagicMock,
        mock_elevation_client: MagicMock,
    ) -> PlantationServiceServicer:
        """Create a servicer with mock dependencies.

        Story 0.6.14: No longer requires dapr_client - uses module-level publish_event().
        """
        return PlantationServiceServicer(
            factory_repo=mock_factory_repo,
            collection_point_repo=mock_cp_repo,
            farmer_repo=mock_farmer_repo,
            id_generator=mock_id_generator,
            elevation_client=mock_elevation_client,
            grading_model_repo=mock_grading_model_repo,
            farmer_performance_repo=mock_farmer_performance_repo,
        )

    @pytest.fixture
    def sample_collection_point(self) -> CollectionPoint:
        """Create a sample collection point for testing."""
        return CollectionPoint(
            id="nyeri-highland-cp-001",
            name="Test CP",
            factory_id="KEN-FAC-001",
            location=GeoLocation(latitude=-0.4, longitude=36.9),
            region_id="nyeri-highland",
            operating_hours=OperatingHours(),
            collection_days=["mon", "wed", "fri"],
        )

    @pytest.fixture
    def sample_grading_model(self) -> GradingModel:
        """Create a sample grading model for testing."""
        return GradingModel(
            model_id="tbk_kenya_tea_v1",
            model_version="1.0.0",
            crops_name="Tea",
            market_name="Kenya_TBK",
            grading_type=GradingType.BINARY,
            attributes={
                "leaf_type": GradingAttribute(
                    num_classes=3,
                    classes=["bud", "one_leaf_bud", "coarse_leaf"],
                ),
            },
            grade_labels={"ACCEPT": "Primary", "REJECT": "Secondary"},
            active_at_factory=["KEN-FAC-001"],
        )

    @pytest.mark.asyncio
    async def test_create_farmer_initializes_performance(
        self,
        servicer: PlantationServiceServicer,
        mock_cp_repo: MagicMock,
        mock_farmer_repo: MagicMock,
        mock_farmer_performance_repo: MagicMock,
        mock_grading_model_repo: MagicMock,
        mock_id_generator: MagicMock,
        mock_elevation_client: MagicMock,
        mock_context: MagicMock,
        sample_collection_point: CollectionPoint,
        sample_grading_model: GradingModel,
    ) -> None:
        """Test CreateFarmer auto-initializes performance with grading model (AC #3)."""
        # Setup mocks
        mock_cp_repo.get_by_id = AsyncMock(return_value=sample_collection_point)
        mock_farmer_repo.get_by_phone = AsyncMock(return_value=None)
        mock_farmer_repo.get_by_national_id = AsyncMock(return_value=None)
        mock_farmer_repo.create = AsyncMock()
        mock_id_generator.generate_farmer_id = AsyncMock(return_value="WM-0001")
        mock_elevation_client.get_altitude = AsyncMock(return_value=1800.0)
        mock_grading_model_repo.get_by_factory = AsyncMock(return_value=sample_grading_model)
        mock_farmer_performance_repo.initialize_for_farmer = AsyncMock()

        # Create farmer request
        request = plantation_pb2.CreateFarmerRequest(
            first_name="John",
            last_name="Mwangi",
            collection_point_id="nyeri-highland-cp-001",
            farm_location=plantation_pb2.GeoLocation(latitude=-0.4, longitude=36.9),
            contact=plantation_pb2.ContactInfo(phone="+254712345678"),
            farm_size_hectares=1.5,
            national_id="12345678",
        )

        result = await servicer.CreateFarmer(request, mock_context)

        # Verify farmer was created
        assert result.id == "WM-0001"
        mock_farmer_repo.create.assert_called_once()

        # Verify performance was auto-initialized (Task 7, AC #3)
        mock_farmer_performance_repo.initialize_for_farmer.assert_called_once()
        call_args = mock_farmer_performance_repo.initialize_for_farmer.call_args
        # Check positional or keyword args
        if call_args.kwargs:
            assert call_args.kwargs["farmer_id"] == "WM-0001"
            assert call_args.kwargs["grading_model_id"] == "tbk_kenya_tea_v1"
            assert call_args.kwargs["grading_model_version"] == "1.0.0"
            assert call_args.kwargs["farm_size_hectares"] == 1.5
        else:
            # Positional args: farmer_id, farm_size_hectares, farm_scale, grading_model_id, grading_model_version
            assert call_args.args[0] == "WM-0001"  # farmer_id

    @pytest.mark.asyncio
    async def test_create_farmer_no_grading_model_skips_performance_init(
        self,
        servicer: PlantationServiceServicer,
        mock_cp_repo: MagicMock,
        mock_farmer_repo: MagicMock,
        mock_farmer_performance_repo: MagicMock,
        mock_grading_model_repo: MagicMock,
        mock_id_generator: MagicMock,
        mock_elevation_client: MagicMock,
        mock_context: MagicMock,
        sample_collection_point: CollectionPoint,
    ) -> None:
        """Test CreateFarmer skips performance init when no grading model exists."""
        # Setup mocks - no grading model assigned to factory
        mock_cp_repo.get_by_id = AsyncMock(return_value=sample_collection_point)
        mock_farmer_repo.get_by_phone = AsyncMock(return_value=None)
        mock_farmer_repo.get_by_national_id = AsyncMock(return_value=None)
        mock_farmer_repo.create = AsyncMock()
        mock_id_generator.generate_farmer_id = AsyncMock(return_value="WM-0002")
        mock_elevation_client.get_altitude = AsyncMock(return_value=1800.0)
        mock_grading_model_repo.get_by_factory = AsyncMock(return_value=None)

        # Create farmer request
        request = plantation_pb2.CreateFarmerRequest(
            first_name="Jane",
            last_name="Wanjiku",
            collection_point_id="nyeri-highland-cp-001",
            farm_location=plantation_pb2.GeoLocation(latitude=-0.4, longitude=36.9),
            contact=plantation_pb2.ContactInfo(phone="+254712345679"),
            farm_size_hectares=0.5,
            national_id="87654321",
        )

        result = await servicer.CreateFarmer(request, mock_context)

        # Farmer should still be created
        assert result.id == "WM-0002"
        mock_farmer_repo.create.assert_called_once()

        # Performance should NOT be initialized (no grading model)
        mock_farmer_performance_repo.initialize_for_farmer.assert_not_called()
