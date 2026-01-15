"""Region transformer for admin API.

Transforms Region domain models to admin API schemas.
"""

from bff.api.schemas.admin.region_schemas import RegionDetail, RegionSummary
from fp_common.models import Region


class RegionTransformer:
    """Transforms Region domain models to admin API schemas."""

    @staticmethod
    def to_summary(
        region: Region,
        factory_count: int = 0,
        farmer_count: int = 0,
    ) -> RegionSummary:
        """Transform Region to summary schema for list views.

        Args:
            region: Region domain model.
            factory_count: Number of factories in this region.
            farmer_count: Number of farmers in this region.

        Returns:
            RegionSummary for API response.
        """
        return RegionSummary(
            id=region.region_id,
            name=region.name,
            county=region.county,
            country=region.country,
            altitude_band=region.geography.altitude_band.label.value,
            factory_count=factory_count,
            farmer_count=farmer_count,
            is_active=region.is_active,
        )

    @staticmethod
    def to_detail(
        region: Region,
        factory_count: int = 0,
        farmer_count: int = 0,
    ) -> RegionDetail:
        """Transform Region to detail schema for single-entity views.

        Args:
            region: Region domain model.
            factory_count: Number of factories in this region.
            farmer_count: Number of farmers in this region.

        Returns:
            RegionDetail for API response.
        """
        return RegionDetail(
            id=region.region_id,
            name=region.name,
            county=region.county,
            country=region.country,
            geography=region.geography,
            flush_calendar=region.flush_calendar,
            agronomic=region.agronomic,
            weather_config=region.weather_config,
            factory_count=factory_count,
            farmer_count=farmer_count,
            is_active=region.is_active,
            created_at=region.created_at,
            updated_at=region.updated_at,
        )
