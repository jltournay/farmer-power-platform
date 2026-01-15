"""Collection Point service for admin API.

Orchestrates PlantationClient calls for collection point management.
"""

from bff.api.schemas.admin.collection_point_schemas import (
    CollectionPointCreateRequest,
    CollectionPointDetail,
    CollectionPointListResponse,
    CollectionPointSummary,
    CollectionPointUpdateRequest,
)
from bff.infrastructure.clients.plantation_client import PlantationClient
from bff.services.base_service import BaseService
from bff.transformers.admin.collection_point_transformer import CollectionPointTransformer
from fp_common.models import CollectionPoint
from fp_common.models.collection_point import CollectionPointCreate, CollectionPointUpdate


class AdminCollectionPointService(BaseService):
    """Service for admin collection point operations.

    Orchestrates PlantationClient calls and transforms to API schemas.
    Uses parallel fetch for enrichment (farmer counts).
    """

    def __init__(
        self,
        plantation_client: PlantationClient | None = None,
        transformer: CollectionPointTransformer | None = None,
    ) -> None:
        """Initialize the collection point service.

        Args:
            plantation_client: Optional PlantationClient (created if not provided).
            transformer: Optional CollectionPointTransformer (created if not provided).
        """
        super().__init__()
        self._plantation = plantation_client or PlantationClient()
        self._transformer = transformer or CollectionPointTransformer()

    async def list_collection_points(
        self,
        factory_id: str,
        page_size: int = 50,
        page_token: str | None = None,
        active_only: bool = False,
    ) -> CollectionPointListResponse:
        """List collection points for a factory with pagination.

        Args:
            factory_id: Factory ID to filter by (required).
            page_size: Number of CPs per page.
            page_token: Pagination token for next page.
            active_only: If True, only return active CPs.

        Returns:
            CollectionPointListResponse with paginated CP summaries.
        """
        self._logger.info(
            "listing_collection_points",
            factory_id=factory_id,
            page_size=page_size,
            has_page_token=page_token is not None,
            active_only=active_only,
        )

        response = await self._plantation.list_collection_points(
            factory_id=factory_id,
            page_size=page_size,
            page_token=page_token,
            active_only=active_only,
        )

        # Enrich with counts using parallel fetch
        summaries = await self._enrich_cps_to_summaries(response.data)

        self._logger.info(
            "listed_collection_points",
            factory_id=factory_id,
            count=len(summaries),
            total_count=response.pagination.total_count,
        )

        return CollectionPointListResponse(
            data=summaries,
            pagination=response.pagination,
        )

    async def get_collection_point(self, cp_id: str) -> CollectionPointDetail:
        """Get collection point detail by ID.

        Args:
            cp_id: Collection point ID.

        Returns:
            CollectionPointDetail with full CP information.

        Raises:
            NotFoundError: If CP not found.
        """
        self._logger.info("getting_collection_point", cp_id=cp_id)

        cp = await self._plantation.get_collection_point(cp_id)

        # Get farmer count for this CP
        farmer_count = await self._get_cp_farmer_count(cp_id)

        # Lead farmer would need to be looked up separately
        # For now, we don't have that relationship stored
        lead_farmer = None

        detail = self._transformer.to_detail(
            cp=cp,
            lead_farmer=lead_farmer,
            farmer_count=farmer_count,
        )

        self._logger.info(
            "got_collection_point",
            cp_id=cp_id,
            farmer_count=farmer_count,
        )

        return detail

    async def create_collection_point(
        self,
        factory_id: str,
        data: CollectionPointCreateRequest,
    ) -> CollectionPointDetail:
        """Create a new collection point under a factory.

        Args:
            factory_id: Parent factory ID.
            data: Collection point creation request.

        Returns:
            CollectionPointDetail of created CP.

        Raises:
            ValidationError: If CP data is invalid.
            NotFoundError: If factory_id doesn't exist.
        """
        self._logger.info(
            "creating_collection_point",
            factory_id=factory_id,
            name=data.name,
        )

        # Create domain model for creation
        create_data = CollectionPointCreate(
            name=data.name,
            factory_id=factory_id,
            location=data.location,
            region_id=data.region_id,
            clerk_id=data.clerk_id,
            clerk_phone=data.clerk_phone,
            operating_hours=data.operating_hours,
            collection_days=data.collection_days,
            capacity=data.capacity,
            status=data.status,
        )

        cp = await self._plantation.create_collection_point(factory_id, create_data)

        detail = self._transformer.to_detail(
            cp=cp,
            lead_farmer=None,
            farmer_count=0,
        )

        self._logger.info("created_collection_point", cp_id=cp.id)

        return detail

    async def update_collection_point(
        self,
        cp_id: str,
        data: CollectionPointUpdateRequest,
    ) -> CollectionPointDetail:
        """Update an existing collection point.

        Args:
            cp_id: Collection point ID to update.
            data: Collection point update request.

        Returns:
            CollectionPointDetail of updated CP.

        Raises:
            NotFoundError: If CP not found.
            ValidationError: If update data is invalid.
        """
        self._logger.info("updating_collection_point", cp_id=cp_id)

        # Create domain model for update
        update_data = CollectionPointUpdate(
            name=data.name,
            clerk_id=data.clerk_id,
            clerk_phone=data.clerk_phone,
            operating_hours=data.operating_hours,
            collection_days=data.collection_days,
            capacity=data.capacity,
            status=data.status,
        )

        cp = await self._plantation.update_collection_point(cp_id, update_data)

        # Get farmer count for updated CP
        farmer_count = await self._get_cp_farmer_count(cp_id)

        detail = self._transformer.to_detail(
            cp=cp,
            lead_farmer=None,
            farmer_count=farmer_count,
        )

        self._logger.info("updated_collection_point", cp_id=cp_id)

        return detail

    async def _enrich_cps_to_summaries(
        self,
        cps: list[CollectionPoint],
    ) -> list[CollectionPointSummary]:
        """Enrich collection points with counts and transform to summaries.

        Uses bounded parallel execution for count fetching.

        Args:
            cps: List of CP domain models.

        Returns:
            List of CollectionPointSummary with counts.
        """

        async def enrich_single(cp: CollectionPoint) -> CollectionPointSummary:
            farmer_count = await self._get_cp_farmer_count(cp.id)
            return self._transformer.to_summary(
                cp=cp,
                farmer_count=farmer_count,
            )

        return await self._parallel_map(cps, enrich_single)

    async def _get_cp_farmer_count(self, cp_id: str) -> int:
        """Get farmer count for a collection point.

        Args:
            cp_id: Collection point ID.

        Returns:
            Number of farmers at this CP.
        """
        try:
            response = await self._plantation.list_farmers(
                collection_point_id=cp_id,
                page_size=1,  # We only need the count
            )
            return response.pagination.total_count
        except Exception:
            return 0
