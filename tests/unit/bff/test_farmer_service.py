"""Tests for FarmerService.

Tests service composition, parallel enrichment, and error handling.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from bff.api.schemas import PaginationMeta
from bff.api.schemas.farmer_schemas import TierLevel, TrendIndicator
from bff.infrastructure.clients import NotFoundError, ServiceUnavailableError
from bff.infrastructure.clients.plantation_client import PlantationClient
from bff.services.farmer_service import FarmerService
from bff.transformers.farmer_transformer import FarmerTransformer
from fp_common.models import (
    CollectionPoint,
    CollectionPointCapacity,
    ContactInfo,
    Factory,
    Farmer,
    FarmScale,
    GeoLocation,
    OperatingHours,
    PaymentPolicy,
    PaymentPolicyType,
    QualityThresholds,
)
from fp_common.models.farmer_performance import (
    FarmerPerformance,
    HistoricalMetrics,
    TodayMetrics,
    TrendDirection,
)


@pytest.fixture
def mock_plantation_client() -> MagicMock:
    """Create a mock PlantationClient.

    Story 9.5a: Added get_collection_points_for_farmer mock.
    """
    client = MagicMock(spec=PlantationClient)
    client.get_factory = AsyncMock()
    client.get_farmer = AsyncMock()
    client.get_farmer_summary = AsyncMock()
    client.get_collection_point = AsyncMock()
    client.get_collection_points_for_farmer = AsyncMock()  # Story 9.5a
    client.list_farmers = AsyncMock()
    client.list_collection_points = AsyncMock()
    return client


@pytest.fixture
def farmer_service(mock_plantation_client: MagicMock) -> FarmerService:
    """Create FarmerService with mock client."""
    return FarmerService(
        plantation_client=mock_plantation_client,
        transformer=FarmerTransformer(),
    )


@pytest.fixture
def sample_factory() -> Factory:
    """Create a sample Factory domain model."""
    return Factory(
        id="KEN-FAC-001",
        name="Nyeri Tea Factory",
        code="NTF",
        region_id="nyeri-highland",
        location=GeoLocation(latitude=-0.4232, longitude=36.9587, altitude_meters=1950.0),
        contact=ContactInfo(phone="+254712345678", email="factory@ntf.co.ke", address="P.O. Box 123"),
        processing_capacity_kg=50000,
        quality_thresholds=QualityThresholds(tier_1=85.0, tier_2=70.0, tier_3=50.0),
        payment_policy=PaymentPolicy(policy_type=PaymentPolicyType.FEEDBACK_ONLY),
        is_active=True,
    )


@pytest.fixture
def sample_collection_point() -> CollectionPoint:
    """Create a sample CollectionPoint domain model.

    Story 9.5a: Added farmer_ids for N:M relationship.
    """
    return CollectionPoint(
        id="nyeri-highland-cp-001",
        name="Kamakwa Collection Point",
        factory_id="KEN-FAC-001",
        location=GeoLocation(latitude=-0.4150, longitude=36.9500, altitude_meters=1850.0),
        region_id="nyeri-highland",
        clerk_id="CLK-001",
        clerk_phone="+254712345679",
        operating_hours=OperatingHours(weekdays="06:00-10:00", weekends="07:00-09:00"),
        collection_days=["mon", "wed", "fri", "sat"],
        capacity=CollectionPointCapacity(
            max_daily_kg=5000,
            storage_type="covered_shed",
            has_weighing_scale=True,
            has_qc_device=False,
        ),
        farmer_ids=["WM-0001"],  # Story 9.5a: N:M relationship
        status="active",
    )


@pytest.fixture
def sample_farmer() -> Farmer:
    """Create a sample Farmer domain model.

    Story 9.5a: collection_point_id removed - N:M relationship via CP.farmer_ids.
    """
    return Farmer(
        id="WM-0001",
        first_name="Wanjiku",
        last_name="Muthoni",
        region_id="nyeri-highland",
        farm_location=GeoLocation(latitude=-0.4197, longitude=36.9553, altitude_meters=1950.0),
        contact=ContactInfo(phone="+254712345678", email="", address=""),
        farm_size_hectares=1.5,
        farm_scale=FarmScale.MEDIUM,
        national_id="12345678",
        is_active=True,
    )


@pytest.fixture
def sample_performance() -> FarmerPerformance:
    """Create a sample FarmerPerformance domain model."""
    return FarmerPerformance(
        farmer_id="WM-0001",
        grading_model_id="tbk_kenya_tea_v1",
        grading_model_version="1.0.0",
        farm_size_hectares=1.5,
        farm_scale=FarmScale.MEDIUM,
        historical=HistoricalMetrics(
            primary_percentage_30d=82.5,
            primary_percentage_90d=78.0,
            total_kg_30d=450.0,
            total_kg_90d=1200.0,
            improvement_trend=TrendDirection.IMPROVING,
        ),
        today=TodayMetrics(deliveries=2, total_kg=35.5),
    )


class TestListFarmers:
    """Tests for list_farmers method."""

    @pytest.mark.asyncio
    async def test_list_farmers_success(
        self,
        farmer_service: FarmerService,
        mock_plantation_client: MagicMock,
        sample_factory: Factory,
        sample_collection_point: CollectionPoint,
        sample_farmer: Farmer,
        sample_performance: FarmerPerformance,
    ):
        """Test successful farmer listing.

        Story 9.5a: Updated test for N:M farmer-CP relationship.
        Service now collects farmer_ids from CPs and filters list_farmers results.
        """
        # Setup mocks
        mock_plantation_client.get_factory.return_value = sample_factory

        # Mock list_collection_points - CP has farmer_ids for N:M relationship
        cp_response = MagicMock()
        cp_response.data = [sample_collection_point]  # CP has farmer_ids=["WM-0001"]
        cp_response.pagination = PaginationMeta(page=1, page_size=100, total_count=1, has_next=False, has_prev=False)
        mock_plantation_client.list_collection_points.return_value = cp_response

        # Mock list_farmers - returns farmers by region, service filters by CP's farmer_ids
        farmers_response = MagicMock()
        farmers_response.data = [sample_farmer]  # sample_farmer.id == "WM-0001" is in CP's farmer_ids
        farmers_response.pagination = PaginationMeta(
            page=1,
            page_size=50,
            total_count=1,
            has_next=False,
            has_prev=False,
            next_page_token=None,
        )
        mock_plantation_client.list_farmers.return_value = farmers_response

        mock_plantation_client.get_farmer_summary.return_value = sample_performance

        # Execute
        result = await farmer_service.list_farmers(factory_id="KEN-FAC-001", page_size=50)

        # Verify
        assert len(result.data) == 1
        assert result.data[0].id == "WM-0001"
        assert result.data[0].name == "Wanjiku Muthoni"
        assert result.data[0].primary_percentage_30d == 82.5
        assert result.data[0].tier == TierLevel.TIER_2
        assert result.data[0].trend == TrendIndicator.UP
        assert result.pagination.total_count == 1

    @pytest.mark.asyncio
    async def test_list_farmers_empty_collection_points(
        self,
        farmer_service: FarmerService,
        mock_plantation_client: MagicMock,
        sample_factory: Factory,
    ):
        """Test listing farmers when factory has no collection points."""
        mock_plantation_client.get_factory.return_value = sample_factory

        cp_response = MagicMock()
        cp_response.data = []
        mock_plantation_client.list_collection_points.return_value = cp_response

        result = await farmer_service.list_farmers(factory_id="KEN-FAC-001")

        assert len(result.data) == 0
        assert result.pagination.total_count == 0

    @pytest.mark.asyncio
    async def test_list_farmers_factory_not_found(
        self,
        farmer_service: FarmerService,
        mock_plantation_client: MagicMock,
    ):
        """Test listing farmers when factory not found."""
        mock_plantation_client.get_factory.side_effect = NotFoundError("Factory KEN-FAC-999 not found")

        with pytest.raises(NotFoundError, match="Factory KEN-FAC-999 not found"):
            await farmer_service.list_farmers(factory_id="KEN-FAC-999")

    @pytest.mark.asyncio
    async def test_list_farmers_with_pagination_token(
        self,
        farmer_service: FarmerService,
        mock_plantation_client: MagicMock,
        sample_factory: Factory,
        sample_collection_point: CollectionPoint,
        sample_farmer: Farmer,
        sample_performance: FarmerPerformance,
    ):
        """Test listing farmers with pagination token.

        Story 9.5a: list_farmers now uses region_id instead of collection_point_id.
        """
        mock_plantation_client.get_factory.return_value = sample_factory

        cp_response = MagicMock()
        cp_response.data = [sample_collection_point]  # CP has farmer_ids=["WM-0001"]
        mock_plantation_client.list_collection_points.return_value = cp_response

        farmers_response = MagicMock()
        farmers_response.data = [sample_farmer]  # Farmer id in CP's farmer_ids
        farmers_response.pagination = PaginationMeta(
            page=2,
            page_size=50,
            total_count=100,
            has_next=True,
            has_prev=True,
            next_page_token="cursor-xyz",
        )
        mock_plantation_client.list_farmers.return_value = farmers_response

        mock_plantation_client.get_farmer_summary.return_value = sample_performance

        result = await farmer_service.list_farmers(
            factory_id="KEN-FAC-001",
            page_size=50,
            page_token="cursor-abc",
        )

        # Story 9.5a: list_farmers called with region_id, not collection_point_id
        mock_plantation_client.list_farmers.assert_called_once_with(
            region_id="nyeri-highland",  # From CP's region_id
            page_size=50,
            page_token="cursor-abc",
            active_only=True,
        )
        assert result.pagination.has_next is True
        assert result.pagination.next_page_token == "cursor-xyz"

    @pytest.mark.asyncio
    async def test_list_farmers_handles_missing_performance(
        self,
        farmer_service: FarmerService,
        mock_plantation_client: MagicMock,
        sample_factory: Factory,
        sample_collection_point: CollectionPoint,
        sample_farmer: Farmer,
    ):
        """Test that missing performance data uses defaults."""
        mock_plantation_client.get_factory.return_value = sample_factory

        cp_response = MagicMock()
        cp_response.data = [sample_collection_point]  # CP has farmer_ids=["WM-0001"]
        mock_plantation_client.list_collection_points.return_value = cp_response

        farmers_response = MagicMock()
        farmers_response.data = [sample_farmer]  # Farmer id in CP's farmer_ids
        farmers_response.pagination = PaginationMeta(
            page=1, page_size=50, total_count=1, has_next=False, has_prev=False, next_page_token=None
        )
        mock_plantation_client.list_farmers.return_value = farmers_response

        # Performance not found for this farmer
        mock_plantation_client.get_farmer_summary.side_effect = NotFoundError("No performance data")

        result = await farmer_service.list_farmers(factory_id="KEN-FAC-001")

        # Should still return farmer with default metrics
        assert len(result.data) == 1
        assert result.data[0].id == "WM-0001"
        assert result.data[0].primary_percentage_30d == 0.0  # Default
        assert result.data[0].tier == TierLevel.BELOW_TIER_3  # 0% < 50%


class TestGetFarmer:
    """Tests for get_farmer method."""

    @pytest.mark.asyncio
    async def test_get_farmer_success(
        self,
        farmer_service: FarmerService,
        mock_plantation_client: MagicMock,
        sample_farmer: Farmer,
        sample_collection_point: CollectionPoint,
        sample_factory: Factory,
        sample_performance: FarmerPerformance,
    ):
        """Test successful farmer detail retrieval.

        Story 9.5a: Uses get_collection_points_for_farmer instead of get_collection_point.
        """
        mock_plantation_client.get_farmer.return_value = sample_farmer

        # Story 9.5a: Mock get_collection_points_for_farmer instead of get_collection_point
        cps_response = MagicMock()
        cps_response.data = [sample_collection_point]
        mock_plantation_client.get_collection_points_for_farmer.return_value = cps_response

        mock_plantation_client.get_factory.return_value = sample_factory
        mock_plantation_client.get_farmer_summary.return_value = sample_performance

        result = await farmer_service.get_farmer("WM-0001")

        assert result.profile.id == "WM-0001"
        assert result.profile.first_name == "Wanjiku"
        assert result.profile.last_name == "Muthoni"
        assert result.profile.phone == "+254712345678"
        assert result.performance.primary_percentage_30d == 82.5
        assert result.performance.total_kg_30d == 450.0
        assert result.performance.deliveries_today == 2
        assert result.tier == TierLevel.TIER_2
        assert result.meta.request_id is not None
        # Story 9.5a: Verify collection_points returned
        assert len(result.profile.collection_points) == 1
        assert result.profile.collection_points[0].id == "nyeri-highland-cp-001"

    @pytest.mark.asyncio
    async def test_get_farmer_not_found(
        self,
        farmer_service: FarmerService,
        mock_plantation_client: MagicMock,
    ):
        """Test farmer not found error."""
        mock_plantation_client.get_farmer.side_effect = NotFoundError("Farmer WM-9999 not found")

        with pytest.raises(NotFoundError, match="Farmer WM-9999 not found"):
            await farmer_service.get_farmer("WM-9999")

    @pytest.mark.asyncio
    async def test_get_farmer_no_collection_points(
        self,
        farmer_service: FarmerService,
        mock_plantation_client: MagicMock,
        sample_farmer: Farmer,
        sample_performance: FarmerPerformance,
    ):
        """Test farmer with no assigned collection points uses defaults.

        Story 9.5a: Farmer without CPs should still work, using default thresholds.
        """
        mock_plantation_client.get_farmer.return_value = sample_farmer

        # Return empty collection points list
        cps_response = MagicMock()
        cps_response.data = []
        mock_plantation_client.get_collection_points_for_farmer.return_value = cps_response

        mock_plantation_client.get_farmer_summary.return_value = sample_performance

        result = await farmer_service.get_farmer("WM-0001")

        # Should succeed with default thresholds
        assert result.profile.id == "WM-0001"
        assert result.profile.collection_points == []
        # Default thresholds: tier_1=85, tier_2=70, tier_3=50
        # Performance is 82.5% which is >= 70% (tier_2)
        assert result.tier == TierLevel.TIER_2

    @pytest.mark.asyncio
    async def test_get_farmer_service_unavailable(
        self,
        farmer_service: FarmerService,
        mock_plantation_client: MagicMock,
    ):
        """Test service unavailable error propagation."""
        mock_plantation_client.get_farmer.side_effect = ServiceUnavailableError("Plantation Model unavailable")

        with pytest.raises(ServiceUnavailableError, match="Plantation Model unavailable"):
            await farmer_service.get_farmer("WM-0001")


class TestParallelEnrichment:
    """Tests for parallel enrichment logic."""

    @pytest.mark.asyncio
    async def test_enriches_multiple_farmers_in_parallel(
        self,
        farmer_service: FarmerService,
        mock_plantation_client: MagicMock,
        sample_factory: Factory,
    ):
        """Test that multiple farmers are enriched in parallel.

        Story 9.5a: Farmers no longer have collection_point_id.
        CP's farmer_ids list determines which farmers belong to a CP.
        """
        # Create multiple farmers (Story 9.5a: no collection_point_id)
        farmers = [
            Farmer(
                id=f"WM-000{i}",
                first_name=f"Farmer{i}",
                last_name="Test",
                region_id="nyeri-highland",
                farm_location=GeoLocation(latitude=-0.4197, longitude=36.9553, altitude_meters=1950.0),
                contact=ContactInfo(phone=f"+25471234567{i}", email="", address=""),
                farm_size_hectares=1.5,
                farm_scale=FarmScale.MEDIUM,
                national_id=f"1234567{i}",
                is_active=True,
            )
            for i in range(1, 4)
        ]

        performances = [
            FarmerPerformance(
                farmer_id=f"WM-000{i}",
                grading_model_id="tbk_kenya_tea_v1",
                grading_model_version="1.0.0",
                farm_size_hectares=1.5,
                farm_scale=FarmScale.MEDIUM,
                historical=HistoricalMetrics(
                    primary_percentage_30d=80.0 + i * 5,  # 85, 90, 95
                    improvement_trend=TrendDirection.STABLE,
                ),
            )
            for i in range(1, 4)
        ]

        # Story 9.5a: Create CP with all 3 farmer_ids for this test
        test_cp = CollectionPoint(
            id="nyeri-highland-cp-001",
            name="Test CP",
            factory_id="KEN-FAC-001",
            location=GeoLocation(latitude=-0.4150, longitude=36.9500, altitude_meters=1850.0),
            region_id="nyeri-highland",
            farmer_ids=["WM-0001", "WM-0002", "WM-0003"],  # All 3 test farmers
            status="active",
        )

        mock_plantation_client.get_factory.return_value = sample_factory

        cp_response = MagicMock()
        cp_response.data = [test_cp]
        mock_plantation_client.list_collection_points.return_value = cp_response

        farmers_response = MagicMock()
        farmers_response.data = farmers
        farmers_response.pagination = PaginationMeta(page=1, page_size=50, total_count=3)
        mock_plantation_client.list_farmers.return_value = farmers_response

        # Return different performance for each farmer
        mock_plantation_client.get_farmer_summary.side_effect = performances

        result = await farmer_service.list_farmers(factory_id="KEN-FAC-001")

        # Verify all farmers were enriched
        assert len(result.data) == 3
        assert mock_plantation_client.get_farmer_summary.call_count == 3

        # Verify tiers are computed correctly
        assert result.data[0].tier == TierLevel.TIER_1  # 85% >= 85%
        assert result.data[1].tier == TierLevel.TIER_1  # 90% >= 85%
        assert result.data[2].tier == TierLevel.TIER_1  # 95% >= 85%
