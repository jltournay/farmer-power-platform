"""Farmer service for BFF layer.

Orchestrates calls to PlantationClient and transforms responses to API schemas.
Implements service composition pattern per ADR-012.
"""

import structlog
from bff.api.schemas import PaginationMeta
from bff.api.schemas.farmer_schemas import (
    FarmerDetailResponse,
    FarmerListResponse,
    FarmerSummary,
)
from bff.infrastructure.clients import NotFoundError
from bff.infrastructure.clients.plantation_client import PlantationClient
from bff.services.base_service import BaseService
from bff.transformers.farmer_transformer import FarmerTransformer
from fp_common.models import Farmer, QualityThresholds
from fp_common.models.farmer_performance import FarmerPerformance

logger = structlog.get_logger(__name__)


class FarmerService(BaseService):
    """Service for farmer-related operations.

    Orchestrates:
    - PlantationClient calls for farmer data
    - Parallel enrichment with performance data
    - Transformation to API schemas with tier computation

    Usage:
        >>> service = FarmerService(plantation_client)
        >>> response = await service.list_farmers(factory_id="KEN-FAC-001")
        >>> detail = await service.get_farmer("WM-0001")
    """

    def __init__(
        self,
        plantation_client: PlantationClient | None = None,
        transformer: FarmerTransformer | None = None,
    ) -> None:
        """Initialize the farmer service.

        Args:
            plantation_client: Optional PlantationClient (created if not provided).
            transformer: Optional FarmerTransformer (created if not provided).
        """
        super().__init__()
        self._plantation = plantation_client or PlantationClient()
        self._transformer = transformer or FarmerTransformer()

    async def list_farmers(
        self,
        factory_id: str,
        page_size: int = 50,
        page_token: str | None = None,
    ) -> FarmerListResponse:
        """List farmers for a factory with enriched summaries.

        Fetches farmers, enriches with performance data in parallel,
        and transforms to API summaries with tier computation.

        Args:
            factory_id: Factory ID to filter farmers by.
            page_size: Number of farmers per page (default: 50, max: 100).
            page_token: Pagination token for next page.

        Returns:
            FarmerListResponse with paginated farmer summaries.

        Raises:
            NotFoundError: If factory not found.
            ServiceUnavailableError: If downstream service unavailable.
        """
        self._logger.info(
            "listing_farmers",
            factory_id=factory_id,
            page_size=page_size,
            has_page_token=page_token is not None,
        )

        # Fetch factory for thresholds (needed for tier computation)
        factory = await self._plantation.get_factory(factory_id)

        # List collection points for this factory to find farmers
        cp_response = await self._plantation.list_collection_points(
            factory_id=factory_id,
            page_size=100,  # Fetch all CPs for this factory
            active_only=True,
        )

        if not cp_response.data:
            # No collection points = no farmers
            return FarmerListResponse(
                data=[],
                pagination=PaginationMeta(
                    page=1,
                    page_size=page_size,
                    total_count=0,
                    total_pages=0,
                    has_next=False,
                    has_prev=False,
                ),
            )

        # Get the first collection point to list farmers
        # In production, we'd aggregate across all CPs
        first_cp = cp_response.data[0]

        # List farmers for this collection point
        farmers_response = await self._plantation.list_farmers(
            collection_point_id=first_cp.id,
            page_size=page_size,
            page_token=page_token,
            active_only=True,
        )

        farmers = farmers_response.data

        if not farmers:
            return FarmerListResponse(
                data=[],
                pagination=farmers_response.pagination,
            )

        # Enrich with performance data in parallel (bounded by Semaphore(5))
        summaries = await self._enrich_farmers_to_summaries(
            farmers=farmers,
            thresholds=factory.quality_thresholds,
        )

        self._logger.info(
            "listed_farmers",
            factory_id=factory_id,
            count=len(summaries),
            total_count=farmers_response.pagination.total_count,
        )

        return FarmerListResponse(
            data=summaries,
            pagination=farmers_response.pagination,
        )

    async def get_farmer(
        self,
        farmer_id: str,
    ) -> FarmerDetailResponse:
        """Get farmer detail with performance and tier.

        Fetches farmer, collection point (for factory_id), factory (for thresholds),
        and performance data, then transforms to detail response.

        Args:
            farmer_id: Farmer ID (e.g., "WM-0001").

        Returns:
            FarmerDetailResponse with profile, performance, and tier.

        Raises:
            NotFoundError: If farmer not found.
            ServiceUnavailableError: If downstream service unavailable.
        """
        self._logger.info("getting_farmer", farmer_id=farmer_id)

        # Fetch farmer
        farmer = await self._plantation.get_farmer(farmer_id)

        # Fetch collection point to get factory_id
        collection_point = await self._plantation.get_collection_point(farmer.collection_point_id)

        # Fetch factory for quality thresholds
        factory = await self._plantation.get_factory(collection_point.factory_id)

        # Fetch performance data
        performance = await self._plantation.get_farmer_summary(farmer_id)

        # Transform to detail response
        detail = self._transformer.to_detail(
            farmer=farmer,
            performance=performance,
            thresholds=factory.quality_thresholds,
        )

        self._logger.info(
            "got_farmer",
            farmer_id=farmer_id,
            tier=detail.tier.value,
        )

        return detail

    async def _enrich_farmers_to_summaries(
        self,
        farmers: list[Farmer],
        thresholds: QualityThresholds,
    ) -> list[FarmerSummary]:
        """Enrich farmers with performance data and transform to summaries.

        Uses bounded parallel execution (Semaphore(5)) to fetch performance
        data for each farmer and transform to FarmerSummary.

        Args:
            farmers: List of farmer domain models.
            thresholds: Factory quality thresholds for tier computation.

        Returns:
            List of FarmerSummary in same order as input farmers.
        """

        async def enrich_single(farmer: Farmer) -> FarmerSummary:
            """Fetch performance and transform single farmer."""
            try:
                performance = await self._plantation.get_farmer_summary(farmer.id)
            except NotFoundError:
                # No performance data yet - use empty defaults
                self._logger.warning(
                    "no_performance_data",
                    farmer_id=farmer.id,
                )
                performance = FarmerPerformance.initialize_for_farmer(
                    farmer_id=farmer.id,
                    farm_size_hectares=farmer.farm_size_hectares,
                    farm_scale=farmer.farm_scale,
                    grading_model_id="default",
                    grading_model_version="1.0.0",
                )

            return self._transformer.to_summary(
                farmer=farmer,
                performance=performance,
                thresholds=thresholds,
            )

        return await self._parallel_map(farmers, enrich_single)
