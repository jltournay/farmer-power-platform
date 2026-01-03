"""Tests for FarmerTransformer.

Tests tier computation and domain-to-API schema transformation.
"""

from datetime import UTC, datetime

import pytest
from bff.api.schemas.farmer_schemas import TierLevel, TrendIndicator
from bff.transformers.farmer_transformer import FarmerTransformer
from fp_common.models import (
    ContactInfo,
    Farmer,
    FarmScale,
    GeoLocation,
    QualityThresholds,
)
from fp_common.models.farmer_performance import (
    FarmerPerformance,
    HistoricalMetrics,
    TodayMetrics,
    TrendDirection,
)


@pytest.fixture
def transformer() -> FarmerTransformer:
    """Create a FarmerTransformer instance."""
    return FarmerTransformer()


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
        farm_location=GeoLocation(
            latitude=-0.4197,
            longitude=36.9553,
            altitude_meters=1950.0,
        ),
        contact=ContactInfo(
            phone="+254712345678",
            email="wanjiku@test.com",
            address="",
        ),
        farm_size_hectares=1.5,
        farm_scale=FarmScale.MEDIUM,
        national_id="12345678",
        registration_date=datetime(2024, 6, 15, 10, 30, 0, tzinfo=UTC),
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
        today=TodayMetrics(
            deliveries=2,
            total_kg=35.5,
        ),
    )


@pytest.fixture
def default_thresholds() -> QualityThresholds:
    """Create default quality thresholds."""
    return QualityThresholds(
        tier_1=85.0,
        tier_2=70.0,
        tier_3=50.0,
    )


class TestComputeTier:
    """Tests for tier computation logic."""

    def test_tier_1_at_threshold(self, default_thresholds: QualityThresholds):
        """Test tier 1 at exact threshold."""
        tier = FarmerTransformer.compute_tier(85.0, default_thresholds)
        assert tier == TierLevel.TIER_1

    def test_tier_1_above_threshold(self, default_thresholds: QualityThresholds):
        """Test tier 1 above threshold."""
        tier = FarmerTransformer.compute_tier(95.0, default_thresholds)
        assert tier == TierLevel.TIER_1

    def test_tier_2_at_threshold(self, default_thresholds: QualityThresholds):
        """Test tier 2 at exact threshold."""
        tier = FarmerTransformer.compute_tier(70.0, default_thresholds)
        assert tier == TierLevel.TIER_2

    def test_tier_2_in_range(self, default_thresholds: QualityThresholds):
        """Test tier 2 in valid range."""
        tier = FarmerTransformer.compute_tier(82.0, default_thresholds)
        assert tier == TierLevel.TIER_2

    def test_tier_3_at_threshold(self, default_thresholds: QualityThresholds):
        """Test tier 3 at exact threshold."""
        tier = FarmerTransformer.compute_tier(50.0, default_thresholds)
        assert tier == TierLevel.TIER_3

    def test_tier_3_in_range(self, default_thresholds: QualityThresholds):
        """Test tier 3 in valid range."""
        tier = FarmerTransformer.compute_tier(65.0, default_thresholds)
        assert tier == TierLevel.TIER_3

    def test_below_tier_3(self, default_thresholds: QualityThresholds):
        """Test below tier 3 threshold."""
        tier = FarmerTransformer.compute_tier(45.0, default_thresholds)
        assert tier == TierLevel.BELOW_TIER_3

    def test_zero_percentage(self, default_thresholds: QualityThresholds):
        """Test zero percentage."""
        tier = FarmerTransformer.compute_tier(0.0, default_thresholds)
        assert tier == TierLevel.BELOW_TIER_3

    def test_hundred_percentage(self, default_thresholds: QualityThresholds):
        """Test 100% percentage."""
        tier = FarmerTransformer.compute_tier(100.0, default_thresholds)
        assert tier == TierLevel.TIER_1

    def test_custom_thresholds(self):
        """Test with custom factory thresholds."""
        custom = QualityThresholds(tier_1=90.0, tier_2=80.0, tier_3=60.0)
        # 82% is tier_2 with default (70%), but tier_3 with custom (80%)
        tier = FarmerTransformer.compute_tier(82.0, custom)
        assert tier == TierLevel.TIER_2  # 82 >= 80 = tier_2


class TestMapTrend:
    """Tests for trend direction mapping."""

    def test_improving_to_up(self):
        """Test IMPROVING maps to UP."""
        trend = FarmerTransformer.map_trend(TrendDirection.IMPROVING)
        assert trend == TrendIndicator.UP

    def test_declining_to_down(self):
        """Test DECLINING maps to DOWN."""
        trend = FarmerTransformer.map_trend(TrendDirection.DECLINING)
        assert trend == TrendIndicator.DOWN

    def test_stable_to_stable(self):
        """Test STABLE maps to STABLE."""
        trend = FarmerTransformer.map_trend(TrendDirection.STABLE)
        assert trend == TrendIndicator.STABLE


class TestToSummary:
    """Tests for to_summary transformation."""

    def test_basic_summary(
        self,
        transformer: FarmerTransformer,
        sample_farmer: Farmer,
        sample_performance: FarmerPerformance,
        default_thresholds: QualityThresholds,
    ):
        """Test basic summary transformation."""
        summary = transformer.to_summary(sample_farmer, sample_performance, default_thresholds)

        assert summary.id == "WM-0001"
        assert summary.name == "Wanjiku Muthoni"
        assert summary.primary_percentage_30d == 82.5
        assert summary.tier == TierLevel.TIER_2  # 82.5 >= 70
        assert summary.trend == TrendIndicator.UP  # IMPROVING

    def test_tier_1_farmer(
        self,
        transformer: FarmerTransformer,
        sample_farmer: Farmer,
        default_thresholds: QualityThresholds,
    ):
        """Test summary for tier 1 farmer."""
        performance = FarmerPerformance(
            farmer_id="WM-0001",
            grading_model_id="tbk_kenya_tea_v1",
            grading_model_version="1.0.0",
            farm_size_hectares=1.5,
            farm_scale=FarmScale.MEDIUM,
            historical=HistoricalMetrics(
                primary_percentage_30d=92.0,
                improvement_trend=TrendDirection.STABLE,
            ),
        )

        summary = transformer.to_summary(sample_farmer, performance, default_thresholds)

        assert summary.tier == TierLevel.TIER_1
        assert summary.trend == TrendIndicator.STABLE

    def test_declining_farmer(
        self,
        transformer: FarmerTransformer,
        sample_farmer: Farmer,
        default_thresholds: QualityThresholds,
    ):
        """Test summary for declining farmer."""
        performance = FarmerPerformance(
            farmer_id="WM-0001",
            grading_model_id="tbk_kenya_tea_v1",
            grading_model_version="1.0.0",
            farm_size_hectares=1.5,
            farm_scale=FarmScale.MEDIUM,
            historical=HistoricalMetrics(
                primary_percentage_30d=55.0,
                improvement_trend=TrendDirection.DECLINING,
            ),
        )

        summary = transformer.to_summary(sample_farmer, performance, default_thresholds)

        assert summary.tier == TierLevel.TIER_3
        assert summary.trend == TrendIndicator.DOWN


class TestToDetail:
    """Tests for to_detail transformation."""

    def test_full_detail_response(
        self,
        transformer: FarmerTransformer,
        sample_farmer: Farmer,
        sample_performance: FarmerPerformance,
        default_thresholds: QualityThresholds,
    ):
        """Test full detail response transformation."""
        detail = transformer.to_detail(sample_farmer, sample_performance, default_thresholds)

        # Check profile
        assert detail.profile.id == "WM-0001"
        assert detail.profile.first_name == "Wanjiku"
        assert detail.profile.last_name == "Muthoni"
        assert detail.profile.phone == "+254712345678"
        assert detail.profile.region_id == "nyeri-highland"
        assert detail.profile.collection_point_id == "nyeri-highland-cp-001"
        assert detail.profile.farm_size_hectares == 1.5
        assert detail.profile.is_active is True

        # Check performance
        assert detail.performance.primary_percentage_30d == 82.5
        assert detail.performance.primary_percentage_90d == 78.0
        assert detail.performance.total_kg_30d == 450.0
        assert detail.performance.total_kg_90d == 1200.0
        assert detail.performance.trend == TrendIndicator.UP
        assert detail.performance.deliveries_today == 2
        assert detail.performance.kg_today == 35.5

        # Check tier
        assert detail.tier == TierLevel.TIER_2

        # Check meta is auto-generated
        assert detail.meta.request_id is not None
        assert detail.meta.timestamp is not None
        assert detail.meta.version == "1.0"

    def test_new_farmer_no_deliveries(
        self,
        transformer: FarmerTransformer,
        sample_farmer: Farmer,
        default_thresholds: QualityThresholds,
    ):
        """Test detail for new farmer with no deliveries."""
        performance = FarmerPerformance(
            farmer_id="WM-0001",
            grading_model_id="tbk_kenya_tea_v1",
            grading_model_version="1.0.0",
            farm_size_hectares=1.5,
            farm_scale=FarmScale.MEDIUM,
            # Empty historical and today metrics (defaults)
        )

        detail = transformer.to_detail(sample_farmer, performance, default_thresholds)

        assert detail.performance.primary_percentage_30d == 0.0
        assert detail.performance.deliveries_today == 0
        assert detail.performance.kg_today == 0.0
        assert detail.tier == TierLevel.BELOW_TIER_3  # 0% < 50%
