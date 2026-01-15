"""Farmer transformer for admin API.

Transforms Farmer domain models to admin API schemas.
Handles tier computation and trend mapping per ADR-012.
"""

from bff.api.schemas.admin.farmer_schemas import (
    AdminFarmerDetail,
    AdminFarmerSummary,
    CommunicationPreferencesAPI,
    FarmerPerformanceMetrics,
)
from bff.api.schemas.farmer_schemas import TierLevel, TrendIndicator
from fp_common.models import Farmer, QualityThresholds
from fp_common.models.farmer_performance import FarmerPerformance, TrendDirection


class AdminFarmerTransformer:
    """Transforms Farmer domain models to admin API schemas.

    Handles tier computation and trend mapping for admin context.
    """

    @staticmethod
    def compute_tier(primary_percentage: float, thresholds: QualityThresholds) -> TierLevel:
        """Compute quality tier from primary percentage and factory thresholds.

        Args:
            primary_percentage: Farmer's primary grade percentage (0-100).
            thresholds: Factory's quality thresholds.

        Returns:
            TierLevel enum value.
        """
        if primary_percentage >= thresholds.tier_1:
            return TierLevel.TIER_1
        if primary_percentage >= thresholds.tier_2:
            return TierLevel.TIER_2
        if primary_percentage >= thresholds.tier_3:
            return TierLevel.TIER_3
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
    ) -> AdminFarmerSummary:
        """Transform Farmer to admin summary schema.

        Args:
            farmer: Farmer domain model.
            performance: FarmerPerformance with historical metrics.
            thresholds: Factory quality thresholds for tier computation.

        Returns:
            AdminFarmerSummary for API response.
        """
        primary_pct = performance.historical.primary_percentage_30d
        tier = self.compute_tier(primary_pct, thresholds)
        trend = self.map_trend(performance.historical.improvement_trend)

        return AdminFarmerSummary(
            id=farmer.id,
            name=f"{farmer.first_name} {farmer.last_name}",
            phone=farmer.contact.phone,
            collection_point_id=farmer.collection_point_id,
            region_id=farmer.region_id,
            farm_scale=farmer.farm_scale,
            tier=tier,
            trend=trend,
            is_active=farmer.is_active,
        )

    def to_detail(
        self,
        farmer: Farmer,
        performance: FarmerPerformance,
        thresholds: QualityThresholds,
    ) -> AdminFarmerDetail:
        """Transform Farmer to admin detail schema.

        Args:
            farmer: Farmer domain model.
            performance: FarmerPerformance with historical and today metrics.
            thresholds: Factory quality thresholds for tier computation.

        Returns:
            AdminFarmerDetail for API response.
        """
        primary_pct = performance.historical.primary_percentage_30d
        tier = self.compute_tier(primary_pct, thresholds)
        trend = self.map_trend(performance.historical.improvement_trend)

        performance_metrics = FarmerPerformanceMetrics(
            primary_percentage_30d=performance.historical.primary_percentage_30d,
            primary_percentage_90d=performance.historical.primary_percentage_90d,
            total_kg_30d=performance.historical.total_kg_30d,
            total_kg_90d=performance.historical.total_kg_90d,
            tier=tier,
            trend=trend,
            deliveries_today=performance.today.deliveries,
            kg_today=performance.today.total_kg,
        )

        communication_prefs = CommunicationPreferencesAPI(
            notification_channel=farmer.notification_channel,
            interaction_pref=farmer.interaction_pref,
            pref_lang=farmer.pref_lang,
        )

        return AdminFarmerDetail(
            id=farmer.id,
            grower_number=farmer.grower_number,
            first_name=farmer.first_name,
            last_name=farmer.last_name,
            phone=farmer.contact.phone,
            national_id=farmer.national_id,
            region_id=farmer.region_id,
            collection_point_id=farmer.collection_point_id,
            farm_location=farmer.farm_location,
            farm_size_hectares=farmer.farm_size_hectares,
            farm_scale=farmer.farm_scale,
            performance=performance_metrics,
            communication_prefs=communication_prefs,
            is_active=farmer.is_active,
            registration_date=farmer.registration_date,
            created_at=farmer.created_at,
            updated_at=farmer.updated_at,
        )
