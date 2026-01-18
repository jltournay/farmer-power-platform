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

        Story 9.5a: Updated to use N:M farmer-CP relationship.
        Fetches CPs for factory, collects farmer IDs, then fetches farmers.

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

        # List collection points for this factory
        # Story 9.5a: CPs now contain farmer_ids list
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

        # Story 9.5a: Collect all farmer IDs from CPs
        farmer_ids: set[str] = set()
        for cp in cp_response.data:
            farmer_ids.update(cp.farmer_ids)

        if not farmer_ids:
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

        # Fetch farmers by region (using first CP's region for now)
        # In future, we could fetch specific farmers by ID if we have a bulk get RPC
        first_cp = cp_response.data[0]
        farmers_response = await self._plantation.list_farmers(
            region_id=first_cp.region_id,
            page_size=page_size,
            page_token=page_token,
            active_only=True,
        )

        # Filter to only farmers in our set (from CPs)
        farmers = [f for f in farmers_response.data if f.id in farmer_ids]

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
            total_count=len(farmer_ids),
        )

        return FarmerListResponse(
            data=summaries,
            pagination=PaginationMeta.from_client_response(
                total_count=len(farmer_ids),
                page_size=page_size,
                next_page_token=farmers_response.pagination.next_page_token,
            ),
        )

    async def get_farmer(
        self,
        farmer_id: str,
    ) -> FarmerDetailResponse:
        """Get farmer detail with performance and tier.

        Story 9.5a: Updated to use N:M farmer-CP relationship.
        Now fetches collection points via get_collection_points_for_farmer RPC.

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

        # Story 9.5a: Fetch collection points for farmer (N:M)
        cps_response = await self._plantation.get_collection_points_for_farmer(farmer_id)
        collection_points = cps_response.data

        # Get factory from first CP (or use default thresholds if no CPs)
        if collection_points:
            first_cp = collection_points[0]
            factory = await self._plantation.get_factory(first_cp.factory_id)
            thresholds = factory.quality_thresholds
        else:
            # No CPs assigned, use default thresholds
            from fp_common.models import QualityThresholds

            thresholds = QualityThresholds()

        # Fetch performance data
        performance = await self._plantation.get_farmer_summary(farmer_id)

        # Transform to detail response
        detail = self._transformer.to_detail(
            farmer=farmer,
            performance=performance,
            thresholds=thresholds,
            collection_points=collection_points,  # Story 9.5a: Pass CPs for N:M
        )

        self._logger.info(
            "got_farmer",
            farmer_id=farmer_id,
            tier=detail.tier.value,
            cp_count=len(collection_points),
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
