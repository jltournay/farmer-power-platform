"""Region service for admin API.

Orchestrates PlantationClient calls for region management.
"""

from bff.api.schemas.admin.region_schemas import (
    RegionCreateRequest,
    RegionDetail,
    RegionListResponse,
    RegionSummary,
    RegionUpdateRequest,
)
from bff.infrastructure.clients.plantation_client import PlantationClient
from bff.services.base_service import BaseService
from bff.transformers.admin.region_transformer import RegionTransformer
from fp_common.models import Region
from fp_common.models.region import RegionCreate, RegionUpdate


class AdminRegionService(BaseService):
    """Service for admin region operations.

    Orchestrates PlantationClient calls and transforms to API schemas.
    Uses parallel fetch for enrichment (factory/farmer counts).
    """

    def __init__(
        self,
        plantation_client: PlantationClient | None = None,
        transformer: RegionTransformer | None = None,
    ) -> None:
        """Initialize the region service.

        Args:
            plantation_client: Optional PlantationClient (created if not provided).
            transformer: Optional RegionTransformer (created if not provided).
        """
        super().__init__()
        self._plantation = plantation_client or PlantationClient()
        self._transformer = transformer or RegionTransformer()

    async def list_regions(
        self,
        page_size: int = 50,
        page_token: str | None = None,
        active_only: bool = False,
    ) -> RegionListResponse:
        """List regions with pagination.

        Args:
            page_size: Number of regions per page.
            page_token: Pagination token for next page.
            active_only: If True, only return active regions.

        Returns:
            RegionListResponse with paginated region summaries.
        """
        self._logger.info(
            "listing_regions",
            page_size=page_size,
            has_page_token=page_token is not None,
            active_only=active_only,
        )

        response = await self._plantation.list_regions(
            page_size=page_size,
            page_token=page_token,
            active_only=active_only,
        )

        # Enrich with counts using parallel fetch
        summaries = await self._enrich_regions_to_summaries(response.data)

        self._logger.info(
            "listed_regions",
            count=len(summaries),
            total_count=response.pagination.total_count,
        )

        return RegionListResponse(
            data=summaries,
            pagination=response.pagination,
        )

    async def get_region(self, region_id: str) -> RegionDetail:
        """Get region detail by ID.

        Args:
            region_id: Region ID (e.g., "nyeri-highland").

        Returns:
            RegionDetail with full region information.

        Raises:
            NotFoundError: If region not found.
        """
        self._logger.info("getting_region", region_id=region_id)

        region = await self._plantation.get_region(region_id)

        # Get counts for this region
        factory_count, farmer_count = await self._get_region_counts(region_id)

        detail = self._transformer.to_detail(
            region=region,
            factory_count=factory_count,
            farmer_count=farmer_count,
        )

        self._logger.info(
            "got_region",
            region_id=region_id,
            factory_count=factory_count,
            farmer_count=farmer_count,
        )

        return detail

    async def create_region(self, data: RegionCreateRequest) -> RegionDetail:
        """Create a new region.

        Args:
            data: Region creation request.

        Returns:
            RegionDetail of created region.

        Raises:
            ValidationError: If region data is invalid.
            ConflictError: If region already exists.
        """
        self._logger.info("creating_region", name=data.name, county=data.county)

        # Create domain model for creation
        create_data = RegionCreate(
            name=data.name,
            county=data.county,
            country=data.country,
            geography=data.geography,
            flush_calendar=data.flush_calendar,
            agronomic=data.agronomic,
            weather_config=data.weather_config,
        )

        region = await self._plantation.create_region(create_data)

        detail = self._transformer.to_detail(
            region=region,
            factory_count=0,
            farmer_count=0,
        )

        self._logger.info("created_region", region_id=region.region_id)

        return detail

    async def update_region(
        self,
        region_id: str,
        data: RegionUpdateRequest,
    ) -> RegionDetail:
        """Update an existing region.

        Args:
            region_id: Region ID to update.
            data: Region update request.

        Returns:
            RegionDetail of updated region.

        Raises:
            NotFoundError: If region not found.
            ValidationError: If update data is invalid.
        """
        self._logger.info("updating_region", region_id=region_id)

        # Create domain model for update
        update_data = RegionUpdate(
            name=data.name,
            geography=data.geography,
            flush_calendar=data.flush_calendar,
            agronomic=data.agronomic,
            weather_config=data.weather_config,
            is_active=data.is_active,
        )

        region = await self._plantation.update_region(region_id, update_data)

        # Get counts for updated region
        factory_count, farmer_count = await self._get_region_counts(region_id)

        detail = self._transformer.to_detail(
            region=region,
            factory_count=factory_count,
            farmer_count=farmer_count,
        )

        self._logger.info("updated_region", region_id=region_id)

        return detail

    async def _enrich_regions_to_summaries(
        self,
        regions: list[Region],
    ) -> list[RegionSummary]:
        """Enrich regions with counts and transform to summaries.

        Uses bounded parallel execution for count fetching.

        Args:
            regions: List of region domain models.

        Returns:
            List of RegionSummary with counts.
        """

        async def enrich_single(region: Region) -> RegionSummary:
            factory_count, farmer_count = await self._get_region_counts(region.region_id)
            return self._transformer.to_summary(
                region=region,
                factory_count=factory_count,
                farmer_count=farmer_count,
            )

        return await self._parallel_map(regions, enrich_single)

    async def _get_region_counts(self, region_id: str) -> tuple[int, int]:
        """Get factory and farmer counts for a region.

        Aggregates farmer counts by querying farmers directly by region_id.

        Args:
            region_id: Region ID.

        Returns:
            Tuple of (factory_count, farmer_count).
        """
        # Get factory count for this region
        factory_response = await self._plantation.list_factories(
            region_id=region_id,
            page_size=1,  # Only need the count
        )
        factory_count = factory_response.pagination.total_count

        # Get farmer count for this region directly
        farmer_response = await self._plantation.list_farmers(
            region_id=region_id,
            page_size=1,  # Only need the count
        )
        farmer_count = farmer_response.pagination.total_count

        return factory_count, farmer_count
