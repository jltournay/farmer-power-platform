"""Factory service for admin API.

Orchestrates PlantationClient calls for factory management.
"""

import contextlib

from bff.api.schemas.admin.factory_schemas import (
    FactoryCreateRequest,
    FactoryDetail,
    FactoryListResponse,
    FactorySummary,
    FactoryUpdateRequest,
)
from bff.infrastructure.clients.plantation_client import PlantationClient
from bff.services.base_service import BaseService
from bff.transformers.admin.factory_transformer import FactoryTransformer
from fp_common.models import Factory
from fp_common.models.factory import FactoryCreate, FactoryUpdate
from fp_common.models.value_objects import QualityThresholds


class AdminFactoryService(BaseService):
    """Service for admin factory operations.

    Orchestrates PlantationClient calls and transforms to API schemas.
    Uses parallel fetch for enrichment (CP/farmer counts, grading model).
    """

    def __init__(
        self,
        plantation_client: PlantationClient | None = None,
        transformer: FactoryTransformer | None = None,
    ) -> None:
        """Initialize the factory service.

        Args:
            plantation_client: Optional PlantationClient (created if not provided).
            transformer: Optional FactoryTransformer (created if not provided).
        """
        super().__init__()
        self._plantation = plantation_client or PlantationClient()
        self._transformer = transformer or FactoryTransformer()

    async def list_factories(
        self,
        region_id: str | None = None,
        page_size: int = 50,
        page_token: str | None = None,
        active_only: bool = False,
    ) -> FactoryListResponse:
        """List factories with pagination.

        Args:
            region_id: Optional region ID to filter by.
            page_size: Number of factories per page.
            page_token: Pagination token for next page.
            active_only: If True, only return active factories.

        Returns:
            FactoryListResponse with paginated factory summaries.
        """
        self._logger.info(
            "listing_factories",
            region_id=region_id,
            page_size=page_size,
            has_page_token=page_token is not None,
            active_only=active_only,
        )

        response = await self._plantation.list_factories(
            region_id=region_id,
            page_size=page_size,
            page_token=page_token,
            active_only=active_only,
        )

        # Enrich with counts using parallel fetch
        summaries = await self._enrich_factories_to_summaries(response.data)

        self._logger.info(
            "listed_factories",
            count=len(summaries),
            total_count=response.pagination.total_count,
        )

        return FactoryListResponse(
            data=summaries,
            pagination=response.pagination,
        )

    async def get_factory(self, factory_id: str) -> FactoryDetail:
        """Get factory detail by ID.

        Args:
            factory_id: Factory ID (e.g., "KEN-FAC-001").

        Returns:
            FactoryDetail with full factory information.

        Raises:
            NotFoundError: If factory not found.
        """
        self._logger.info("getting_factory", factory_id=factory_id)

        factory = await self._plantation.get_factory(factory_id)

        # Get grading model and counts (grading model may not be assigned yet)
        grading_model = None
        with contextlib.suppress(Exception):
            grading_model = await self._plantation.get_factory_grading_model(factory_id)

        cp_count, farmer_count = await self._get_factory_counts(factory_id)

        detail = self._transformer.to_detail(
            factory=factory,
            grading_model=grading_model,
            collection_point_count=cp_count,
            farmer_count=farmer_count,
        )

        self._logger.info(
            "got_factory",
            factory_id=factory_id,
            cp_count=cp_count,
            farmer_count=farmer_count,
        )

        return detail

    async def create_factory(self, data: FactoryCreateRequest) -> FactoryDetail:
        """Create a new factory.

        Args:
            data: Factory creation request.

        Returns:
            FactoryDetail of created factory.

        Raises:
            ValidationError: If factory data is invalid.
            NotFoundError: If region_id doesn't exist.
        """
        self._logger.info("creating_factory", name=data.name, region_id=data.region_id)

        # Build quality thresholds (use defaults if not provided)
        quality_thresholds = None
        if data.quality_thresholds:
            quality_thresholds = QualityThresholds(
                tier_1=data.quality_thresholds.tier_1,
                tier_2=data.quality_thresholds.tier_2,
                tier_3=data.quality_thresholds.tier_3,
            )

        # Create domain model for creation
        create_data = FactoryCreate(
            name=data.name,
            code=data.code,
            region_id=data.region_id,
            location=data.location,
            contact=data.contact,
            processing_capacity_kg=data.processing_capacity_kg,
            quality_thresholds=quality_thresholds,
            payment_policy=data.payment_policy,
        )

        factory = await self._plantation.create_factory(create_data)

        detail = self._transformer.to_detail(
            factory=factory,
            grading_model=None,
            collection_point_count=0,
            farmer_count=0,
        )

        self._logger.info("created_factory", factory_id=factory.id)

        return detail

    async def update_factory(
        self,
        factory_id: str,
        data: FactoryUpdateRequest,
    ) -> FactoryDetail:
        """Update an existing factory.

        Args:
            factory_id: Factory ID to update.
            data: Factory update request.

        Returns:
            FactoryDetail of updated factory.

        Raises:
            NotFoundError: If factory not found.
            ValidationError: If update data is invalid.
        """
        self._logger.info("updating_factory", factory_id=factory_id)

        # Build quality thresholds if provided
        quality_thresholds = None
        if data.quality_thresholds:
            quality_thresholds = QualityThresholds(
                tier_1=data.quality_thresholds.tier_1,
                tier_2=data.quality_thresholds.tier_2,
                tier_3=data.quality_thresholds.tier_3,
            )

        # Create domain model for update
        update_data = FactoryUpdate(
            name=data.name,
            code=data.code,
            location=data.location,
            contact=data.contact,
            processing_capacity_kg=data.processing_capacity_kg,
            quality_thresholds=quality_thresholds,
            payment_policy=data.payment_policy,
            is_active=data.is_active,
        )

        factory = await self._plantation.update_factory(factory_id, update_data)

        # Get updated counts and grading model
        grading_model = None
        with contextlib.suppress(Exception):
            grading_model = await self._plantation.get_factory_grading_model(factory_id)

        cp_count, farmer_count = await self._get_factory_counts(factory_id)

        detail = self._transformer.to_detail(
            factory=factory,
            grading_model=grading_model,
            collection_point_count=cp_count,
            farmer_count=farmer_count,
        )

        self._logger.info("updated_factory", factory_id=factory_id)

        return detail

    async def _enrich_factories_to_summaries(
        self,
        factories: list[Factory],
    ) -> list[FactorySummary]:
        """Enrich factories with counts and transform to summaries.

        Uses bounded parallel execution for count fetching.

        Args:
            factories: List of factory domain models.

        Returns:
            List of FactorySummary with counts.
        """

        async def enrich_single(factory: Factory) -> FactorySummary:
            cp_count, farmer_count = await self._get_factory_counts(factory.id)
            return self._transformer.to_summary(
                factory=factory,
                collection_point_count=cp_count,
                farmer_count=farmer_count,
            )

        return await self._parallel_map(factories, enrich_single)

    async def _get_factory_counts(self, factory_id: str) -> tuple[int, int]:
        """Get collection point and farmer counts for a factory.

        Args:
            factory_id: Factory ID.

        Returns:
            Tuple of (collection_point_count, farmer_count).
        """
        # Get collection points for this factory
        cp_response = await self._plantation.list_collection_points(
            factory_id=factory_id,
            page_size=1,  # We only need the count
        )
        cp_count = cp_response.pagination.total_count

        # For farmer count, we'd need to aggregate across all CPs
        # For now, return 0 as this requires more complex aggregation
        farmer_count = 0

        return cp_count, farmer_count
