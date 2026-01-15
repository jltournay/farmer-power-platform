"""Collection Point transformer for admin API.

Transforms CollectionPoint domain models to admin API schemas.
"""

from bff.api.schemas.admin.collection_point_schemas import (
    CollectionPointDetail,
    CollectionPointSummary,
    LeadFarmerSummary,
)
from fp_common.models import CollectionPoint, Farmer


class CollectionPointTransformer:
    """Transforms CollectionPoint domain models to admin API schemas."""

    @staticmethod
    def to_summary(
        cp: CollectionPoint,
        farmer_count: int = 0,
    ) -> CollectionPointSummary:
        """Transform CollectionPoint to summary schema for list views.

        Args:
            cp: CollectionPoint domain model.
            farmer_count: Number of farmers assigned to this CP.

        Returns:
            CollectionPointSummary for API response.
        """
        return CollectionPointSummary(
            id=cp.id,
            name=cp.name,
            factory_id=cp.factory_id,
            region_id=cp.region_id,
            farmer_count=farmer_count,
            status=cp.status,
        )

    @staticmethod
    def to_detail(
        cp: CollectionPoint,
        lead_farmer: Farmer | None = None,
        farmer_count: int = 0,
    ) -> CollectionPointDetail:
        """Transform CollectionPoint to detail schema for single-entity views.

        Args:
            cp: CollectionPoint domain model.
            lead_farmer: Lead farmer assigned to this CP (if any).
            farmer_count: Number of farmers assigned.

        Returns:
            CollectionPointDetail for API response.
        """
        lead_farmer_summary = None
        if lead_farmer:
            lead_farmer_summary = LeadFarmerSummary(
                id=lead_farmer.id,
                name=f"{lead_farmer.first_name} {lead_farmer.last_name}",
                phone=lead_farmer.contact.phone,
            )

        return CollectionPointDetail(
            id=cp.id,
            name=cp.name,
            factory_id=cp.factory_id,
            region_id=cp.region_id,
            location=cp.location,
            clerk_id=cp.clerk_id,
            clerk_phone=cp.clerk_phone,
            operating_hours=cp.operating_hours,
            collection_days=cp.collection_days,
            capacity=cp.capacity,
            lead_farmer=lead_farmer_summary,
            farmer_count=farmer_count,
            status=cp.status,
            created_at=cp.created_at,
            updated_at=cp.updated_at,
        )
