"""Farmer transformer for admin API.

Transforms Farmer domain models to admin API schemas.
Handles tier computation and trend mapping per ADR-012.

Story 9.5a: Updated for N:M farmer-CP relationship.
- to_summary: now accepts cp_count instead of using farmer.collection_point_id
- to_detail: now accepts collection_points list
"""

from bff.api.schemas.admin.farmer_schemas import (
    AdminFarmerDetail,
    AdminFarmerSummary,
    CollectionPointSummaryForFarmer,
    CommunicationPreferencesAPI,
    FarmerPerformanceMetrics,
)
from bff.api.schemas.farmer_schemas import TierLevel, TrendIndicator
from fp_common.models import CollectionPoint, Farmer, QualityThresholds
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
        cp_count: int = 0,
    ) -> AdminFarmerSummary:
        """Transform Farmer to admin summary schema.

        Story 9.5a: cp_count parameter replaces farmer.collection_point_id.

        Args:
            farmer: Farmer domain model.
            performance: FarmerPerformance with historical metrics.
            thresholds: Factory quality thresholds for tier computation.
            cp_count: Number of collection points the farmer is assigned to (Story 9.5a).

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
            cp_count=cp_count,  # Story 9.5a: N:M relationship
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
        collection_points: list[CollectionPoint] | None = None,
    ) -> AdminFarmerDetail:
        """Transform Farmer to admin detail schema.

        Story 9.5a: collection_points parameter replaces farmer.collection_point_id.

        Args:
            farmer: Farmer domain model.
            performance: FarmerPerformance with historical and today metrics.
            thresholds: Factory quality thresholds for tier computation.
            collection_points: List of CPs the farmer is assigned to (Story 9.5a).

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

        # Story 9.5a: Transform CPs to API schema
        cp_summaries = [
            CollectionPointSummaryForFarmer(
                id=cp.id,
                name=cp.name,
                factory_id=cp.factory_id,
            )
            for cp in (collection_points or [])
        ]

        return AdminFarmerDetail(
            id=farmer.id,
            grower_number=farmer.grower_number,
            first_name=farmer.first_name,
            last_name=farmer.last_name,
            phone=farmer.contact.phone,
            national_id=farmer.national_id,
            region_id=farmer.region_id,
            collection_points=cp_summaries,  # Story 9.5a: N:M relationship
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
