"""Factory transformer for admin API.

Transforms Factory domain models to admin API schemas.
"""

from bff.api.schemas.admin.factory_schemas import (
    FactoryDetail,
    FactorySummary,
    GradingModelSummary,
    QualityThresholdsAPI,
)
from fp_common.models import Factory
from fp_common.models.grading_model import GradingModel


class FactoryTransformer:
    """Transforms Factory domain models to admin API schemas."""

    @staticmethod
    def to_summary(
        factory: Factory,
        collection_point_count: int = 0,
        farmer_count: int = 0,
    ) -> FactorySummary:
        """Transform Factory to summary schema for list views.

        Args:
            factory: Factory domain model.
            collection_point_count: Number of collection points for this factory.
            farmer_count: Number of farmers for this factory.

        Returns:
            FactorySummary for API response.
        """
        return FactorySummary(
            id=factory.id,
            name=factory.name,
            code=factory.code,
            region_id=factory.region_id,
            collection_point_count=collection_point_count,
            farmer_count=farmer_count,
            is_active=factory.is_active,
        )

    @staticmethod
    def to_detail(
        factory: Factory,
        grading_model: GradingModel | None = None,
        collection_point_count: int = 0,
        farmer_count: int = 0,
    ) -> FactoryDetail:
        """Transform Factory to detail schema for single-entity views.

        Args:
            factory: Factory domain model.
            grading_model: Assigned grading model (if any).
            collection_point_count: Number of collection points.
            farmer_count: Number of farmers.

        Returns:
            FactoryDetail for API response.
        """
        grading_model_summary = None
        if grading_model:
            grading_model_summary = GradingModelSummary(
                id=grading_model.model_id,
                name=f"{grading_model.crops_name} - {grading_model.market_name}",
                version=grading_model.model_version,
                grade_count=len(grading_model.grade_labels),
            )

        return FactoryDetail(
            id=factory.id,
            name=factory.name,
            code=factory.code,
            region_id=factory.region_id,
            location=factory.location,
            contact=factory.contact,
            processing_capacity_kg=factory.processing_capacity_kg,
            quality_thresholds=QualityThresholdsAPI(
                tier_1=factory.quality_thresholds.tier_1,
                tier_2=factory.quality_thresholds.tier_2,
                tier_3=factory.quality_thresholds.tier_3,
            ),
            payment_policy=factory.payment_policy,
            grading_model=grading_model_summary,
            collection_point_count=collection_point_count,
            farmer_count=farmer_count,
            is_active=factory.is_active,
            created_at=factory.created_at,
            updated_at=factory.updated_at,
        )
