"""Tests for Admin transformers.

Tests domain-to-API schema transformation for admin entities.
"""

from datetime import UTC, datetime

import pytest
from bff.api.schemas.farmer_schemas import TierLevel, TrendIndicator
from bff.transformers.admin.collection_point_transformer import CollectionPointTransformer
from bff.transformers.admin.factory_transformer import FactoryTransformer
from bff.transformers.admin.farmer_transformer import AdminFarmerTransformer
from bff.transformers.admin.region_transformer import RegionTransformer
from fp_common.models import (
    CollectionPoint,
    CollectionPointCapacity,
    ContactInfo,
    Factory,
    Farmer,
    FarmScale,
    GeoLocation,
    OperatingHours,
    QualityThresholds,
)
from fp_common.models.farmer_performance import (
    FarmerPerformance,
    HistoricalMetrics,
    TodayMetrics,
    TrendDirection,
)
from fp_common.models.grading_model import GradingAttribute, GradingModel, GradingType
from fp_common.models.region import Region
from fp_common.models.value_objects import (
    GPS,
    Agronomic,
    AltitudeBand,
    AltitudeBandLabel,
    FlushCalendar,
    FlushPeriod,
    Geography,
    PaymentPolicy,
    WeatherConfig,
)


@pytest.fixture
def sample_region() -> Region:
    """Create a sample Region domain model."""
    return Region(
        region_id="nyeri-highland",
        name="Nyeri Highland",
        county="Nyeri",
        country="Kenya",
        geography=Geography(
            center_gps=GPS(lat=-0.4197, lng=36.9553),
            radius_km=25.0,
            altitude_band=AltitudeBand(
                min_meters=1800,
                max_meters=2200,
                label=AltitudeBandLabel.HIGHLAND,
            ),
        ),
        flush_calendar=FlushCalendar(
            first_flush=FlushPeriod(start="03-15", end="05-15"),
            monsoon_flush=FlushPeriod(start="06-15", end="09-30"),
            autumn_flush=FlushPeriod(start="10-15", end="12-15"),
            dormant=FlushPeriod(start="12-16", end="03-14"),
        ),
        agronomic=Agronomic(soil_type="volcanic_red"),
        weather_config=WeatherConfig(
            api_location=GPS(lat=-0.4197, lng=36.9553),
            altitude_for_api=1950,
        ),
        is_active=True,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 6, 1, tzinfo=UTC),
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
        contact=ContactInfo(phone="+254700000001"),
        processing_capacity_kg=50000,
        quality_thresholds=QualityThresholds(tier_1=85.0, tier_2=70.0, tier_3=50.0),
        payment_policy=PaymentPolicy(),
        is_active=True,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 6, 1, tzinfo=UTC),
    )


@pytest.fixture
def sample_collection_point() -> CollectionPoint:
    """Create a sample CollectionPoint domain model."""
    return CollectionPoint(
        id="nyeri-highland-cp-001",
        name="Kamakwa Collection Point",
        factory_id="KEN-FAC-001",
        region_id="nyeri-highland",
        location=GeoLocation(latitude=-0.4150, longitude=36.9500, altitude_meters=1850.0),
        clerk_id="CLK-001",
        clerk_phone="+254700000002",
        operating_hours=OperatingHours(),
        collection_days=["mon", "wed", "fri", "sat"],
        capacity=CollectionPointCapacity(max_daily_kg=5000),
        status="active",
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 6, 1, tzinfo=UTC),
    )


@pytest.fixture
def sample_farmer() -> Farmer:
    """Create a sample Farmer domain model."""
    return Farmer(
        id="WM-0001",
        grower_number="GN-001",
        first_name="Wanjiku",
        last_name="Muthoni",
        region_id="nyeri-highland",
        collection_point_id="nyeri-highland-cp-001",
        farm_location=GeoLocation(latitude=-0.4197, longitude=36.9553, altitude_meters=1950.0),
        contact=ContactInfo(phone="+254712345678"),
        farm_size_hectares=1.5,
        farm_scale=FarmScale.MEDIUM,
        national_id="12345678",
        registration_date=datetime(2024, 6, 15, tzinfo=UTC),
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


@pytest.fixture
def sample_grading_model() -> GradingModel:
    """Create a sample GradingModel domain model."""
    return GradingModel(
        model_id="tbk_kenya_tea_v1",
        model_version="1.0.0",
        crops_name="Tea",
        market_name="Kenya_TBK",
        grading_type=GradingType.BINARY,
        attributes={
            "leaf_type": GradingAttribute(
                num_classes=2,
                classes=["primary", "secondary"],
            ),
        },
        grade_labels={"ACCEPT": "Primary", "REJECT": "Secondary"},
    )


@pytest.fixture
def default_thresholds() -> QualityThresholds:
    """Create default quality thresholds."""
    return QualityThresholds(tier_1=85.0, tier_2=70.0, tier_3=50.0)


class TestRegionTransformer:
    """Tests for RegionTransformer."""

    def test_to_summary(self, sample_region: Region):
        """Test region summary transformation."""
        summary = RegionTransformer.to_summary(
            region=sample_region,
            factory_count=3,
            farmer_count=150,
        )

        assert summary.id == "nyeri-highland"
        assert summary.name == "Nyeri Highland"
        assert summary.county == "Nyeri"
        assert summary.altitude_band == "highland"
        assert summary.factory_count == 3
        assert summary.farmer_count == 150
        assert summary.is_active is True

    def test_to_detail(self, sample_region: Region):
        """Test region detail transformation."""
        detail = RegionTransformer.to_detail(
            region=sample_region,
            factory_count=3,
            farmer_count=150,
        )

        assert detail.id == "nyeri-highland"
        assert detail.name == "Nyeri Highland"
        assert detail.geography.center_gps.lat == -0.4197
        assert detail.weather_config.altitude_for_api == 1950
        assert detail.factory_count == 3
        assert detail.created_at == datetime(2024, 1, 1, tzinfo=UTC)


class TestFactoryTransformer:
    """Tests for FactoryTransformer."""

    def test_to_summary(self, sample_factory: Factory):
        """Test factory summary transformation."""
        summary = FactoryTransformer.to_summary(
            factory=sample_factory,
            collection_point_count=5,
            farmer_count=200,
        )

        assert summary.id == "KEN-FAC-001"
        assert summary.name == "Nyeri Tea Factory"
        assert summary.code == "NTF"
        assert summary.region_id == "nyeri-highland"
        assert summary.collection_point_count == 5
        assert summary.farmer_count == 200
        assert summary.is_active is True

    def test_to_detail_with_grading_model(
        self,
        sample_factory: Factory,
        sample_grading_model: GradingModel,
    ):
        """Test factory detail transformation with grading model."""
        detail = FactoryTransformer.to_detail(
            factory=sample_factory,
            grading_model=sample_grading_model,
            collection_point_count=5,
            farmer_count=200,
        )

        assert detail.id == "KEN-FAC-001"
        assert detail.quality_thresholds.tier_1 == 85.0
        assert detail.grading_model is not None
        assert detail.grading_model.id == "tbk_kenya_tea_v1"
        assert detail.grading_model.grade_count == 2

    def test_to_detail_without_grading_model(self, sample_factory: Factory):
        """Test factory detail transformation without grading model."""
        detail = FactoryTransformer.to_detail(
            factory=sample_factory,
            grading_model=None,
            collection_point_count=0,
            farmer_count=0,
        )

        assert detail.grading_model is None


class TestCollectionPointTransformer:
    """Tests for CollectionPointTransformer."""

    def test_to_summary(self, sample_collection_point: CollectionPoint):
        """Test CP summary transformation."""
        summary = CollectionPointTransformer.to_summary(
            cp=sample_collection_point,
            farmer_count=50,
        )

        assert summary.id == "nyeri-highland-cp-001"
        assert summary.name == "Kamakwa Collection Point"
        assert summary.factory_id == "KEN-FAC-001"
        assert summary.farmer_count == 50
        assert summary.status == "active"

    def test_to_detail_with_lead_farmer(
        self,
        sample_collection_point: CollectionPoint,
        sample_farmer: Farmer,
    ):
        """Test CP detail transformation with lead farmer."""
        detail = CollectionPointTransformer.to_detail(
            cp=sample_collection_point,
            lead_farmer=sample_farmer,
            farmer_count=50,
        )

        assert detail.id == "nyeri-highland-cp-001"
        assert detail.lead_farmer is not None
        assert detail.lead_farmer.id == "WM-0001"
        assert detail.lead_farmer.name == "Wanjiku Muthoni"

    def test_to_detail_without_lead_farmer(self, sample_collection_point: CollectionPoint):
        """Test CP detail transformation without lead farmer."""
        detail = CollectionPointTransformer.to_detail(
            cp=sample_collection_point,
            lead_farmer=None,
            farmer_count=50,
        )

        assert detail.lead_farmer is None


class TestAdminFarmerTransformer:
    """Tests for AdminFarmerTransformer."""

    def test_compute_tier_values(self, default_thresholds: QualityThresholds):
        """Test tier computation at boundary values."""
        # Tier 1
        assert AdminFarmerTransformer.compute_tier(85.0, default_thresholds) == TierLevel.TIER_1
        assert AdminFarmerTransformer.compute_tier(95.0, default_thresholds) == TierLevel.TIER_1

        # Tier 2
        assert AdminFarmerTransformer.compute_tier(70.0, default_thresholds) == TierLevel.TIER_2
        assert AdminFarmerTransformer.compute_tier(84.9, default_thresholds) == TierLevel.TIER_2

        # Tier 3
        assert AdminFarmerTransformer.compute_tier(50.0, default_thresholds) == TierLevel.TIER_3
        assert AdminFarmerTransformer.compute_tier(69.9, default_thresholds) == TierLevel.TIER_3

        # Below Tier 3
        assert AdminFarmerTransformer.compute_tier(49.9, default_thresholds) == TierLevel.BELOW_TIER_3

    def test_map_trend(self):
        """Test trend mapping."""
        assert AdminFarmerTransformer.map_trend(TrendDirection.IMPROVING) == TrendIndicator.UP
        assert AdminFarmerTransformer.map_trend(TrendDirection.DECLINING) == TrendIndicator.DOWN
        assert AdminFarmerTransformer.map_trend(TrendDirection.STABLE) == TrendIndicator.STABLE

    def test_to_summary(
        self,
        sample_farmer: Farmer,
        sample_performance: FarmerPerformance,
        default_thresholds: QualityThresholds,
    ):
        """Test farmer summary transformation."""
        transformer = AdminFarmerTransformer()
        summary = transformer.to_summary(sample_farmer, sample_performance, default_thresholds)

        assert summary.id == "WM-0001"
        assert summary.name == "Wanjiku Muthoni"
        assert summary.phone == "+254712345678"
        assert summary.collection_point_id == "nyeri-highland-cp-001"
        assert summary.farm_scale == FarmScale.MEDIUM
        assert summary.tier == TierLevel.TIER_2  # 82.5% >= 70%
        assert summary.trend == TrendIndicator.UP  # IMPROVING

    def test_to_detail(
        self,
        sample_farmer: Farmer,
        sample_performance: FarmerPerformance,
        default_thresholds: QualityThresholds,
    ):
        """Test farmer detail transformation."""
        transformer = AdminFarmerTransformer()
        detail = transformer.to_detail(sample_farmer, sample_performance, default_thresholds)

        assert detail.id == "WM-0001"
        assert detail.first_name == "Wanjiku"
        assert detail.last_name == "Muthoni"
        assert detail.performance.primary_percentage_30d == 82.5
        assert detail.performance.tier == TierLevel.TIER_2
        assert detail.communication_prefs.pref_lang.value == "sw"
