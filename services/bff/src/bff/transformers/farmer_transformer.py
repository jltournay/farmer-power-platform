"""Farmer transformer for domain model to API schema conversion.

Handles tier computation and trend mapping per ADR-012 Decision 2.
"""

from bff.api.schemas.farmer_schemas import (
    FarmerDetailResponse,
    FarmerPerformanceAPI,
    FarmerProfile,
    FarmerSummary,
    TierLevel,
    TrendIndicator,
)
from fp_common.models import Farmer, QualityThresholds
from fp_common.models.farmer_performance import FarmerPerformance, TrendDirection


class FarmerTransformer:
    """Transforms domain models to API schemas.

    Handles:
    - Tier computation from primary_percentage_30d vs factory thresholds
    - TrendDirection to TrendIndicator mapping
    - Domain model to API schema field mapping

    Example:
        >>> transformer = FarmerTransformer()
        >>> summary = transformer.to_summary(farmer, performance, thresholds)
        >>> detail = transformer.to_detail(farmer, performance, thresholds)
    """

    @staticmethod
    def compute_tier(primary_percentage: float, thresholds: QualityThresholds) -> TierLevel:
        """Compute quality tier from primary percentage and factory thresholds.

        Tiers are factory-configurable. Default thresholds are:
        - tier_1: >= 85%
        - tier_2: >= 70%
        - tier_3: >= 50%
        - below_tier_3: < 50%

        Args:
            primary_percentage: Farmer's primary grade percentage (0-100).
            thresholds: Factory's quality thresholds.

        Returns:
            TierLevel enum value.

        Example:
            >>> tier = FarmerTransformer.compute_tier(82.5, thresholds)
            >>> tier
            TierLevel.TIER_2
        """
        if primary_percentage >= thresholds.tier_1:
            return TierLevel.TIER_1
        elif primary_percentage >= thresholds.tier_2:
            return TierLevel.TIER_2
        elif primary_percentage >= thresholds.tier_3:
            return TierLevel.TIER_3
        else:
            return TierLevel.BELOW_TIER_3

    @staticmethod
    def map_trend(trend_direction: TrendDirection) -> TrendIndicator:
        """Map domain TrendDirection to API TrendIndicator.

        Args:
            trend_direction: Domain model trend direction.

        Returns:
            API trend indicator for UI display.
        """
        mapping = {
            TrendDirection.IMPROVING: TrendIndicator.UP,
            TrendDirection.DECLINING: TrendIndicator.DOWN,
            TrendDirection.STABLE: TrendIndicator.STABLE,
        }
        return mapping.get(trend_direction, TrendIndicator.STABLE)

    def to_summary(
        self,
        farmer: Farmer,
        performance: FarmerPerformance,
        thresholds: QualityThresholds,
    ) -> FarmerSummary:
        """Transform farmer and performance to summary schema.

        Used for farmer list endpoints where we need compact representations.

        Args:
            farmer: Farmer domain model.
            performance: FarmerPerformance with historical metrics.
            thresholds: Factory quality thresholds for tier computation.

        Returns:
            FarmerSummary for API response.
        """
        primary_pct = performance.historical.primary_percentage_30d
        tier = self.compute_tier(primary_pct, thresholds)
        trend = self.map_trend(performance.historical.improvement_trend)

        return FarmerSummary(
            id=farmer.id,
            name=f"{farmer.first_name} {farmer.last_name}",
            primary_percentage_30d=primary_pct,
            tier=tier,
            trend=trend,
        )

    def to_detail(
        self,
        farmer: Farmer,
        performance: FarmerPerformance,
        thresholds: QualityThresholds,
    ) -> FarmerDetailResponse:
        """Transform farmer and performance to detail schema.

        Used for single farmer detail endpoint with full profile and performance.

        Args:
            farmer: Farmer domain model.
            performance: FarmerPerformance with historical and today metrics.
            thresholds: Factory quality thresholds for tier computation.

        Returns:
            FarmerDetailResponse for API response.
        """
        primary_pct = performance.historical.primary_percentage_30d
        tier = self.compute_tier(primary_pct, thresholds)
        trend = self.map_trend(performance.historical.improvement_trend)

        profile = FarmerProfile(
            id=farmer.id,
            first_name=farmer.first_name,
            last_name=farmer.last_name,
            phone=farmer.contact.phone,
            region_id=farmer.region_id,
            collection_point_id=farmer.collection_point_id,
            farm_size_hectares=farmer.farm_size_hectares,
            registration_date=farmer.registration_date,
            is_active=farmer.is_active,
        )

        perf_api = FarmerPerformanceAPI(
            primary_percentage_30d=performance.historical.primary_percentage_30d,
            primary_percentage_90d=performance.historical.primary_percentage_90d,
            total_kg_30d=performance.historical.total_kg_30d,
            total_kg_90d=performance.historical.total_kg_90d,
            trend=trend,
            deliveries_today=performance.today.deliveries,
            kg_today=performance.today.total_kg,
        )

        return FarmerDetailResponse(
            profile=profile,
            performance=perf_api,
            tier=tier,
        )
