"""Farmer service for admin API.

Orchestrates PlantationClient calls for farmer management.
"""

import csv
import io

from bff.api.schemas.admin.farmer_schemas import (
    AdminFarmerCreateRequest,
    AdminFarmerDetail,
    AdminFarmerListResponse,
    AdminFarmerSummary,
    AdminFarmerUpdateRequest,
    FarmerImportResponse,
    ImportErrorRow,
)
from bff.infrastructure.clients import NotFoundError
from bff.infrastructure.clients.plantation_client import PlantationClient
from bff.services.base_service import BaseService
from bff.transformers.admin.farmer_transformer import AdminFarmerTransformer
from fp_common.models import Farmer, QualityThresholds
from fp_common.models.farmer import FarmerCreate, FarmerUpdate
from fp_common.models.farmer_performance import FarmerPerformance


class AdminFarmerService(BaseService):
    """Service for admin farmer operations.

    Orchestrates PlantationClient calls and transforms to API schemas.
    Uses parallel fetch for enrichment (performance data).
    """

    def __init__(
        self,
        plantation_client: PlantationClient | None = None,
        transformer: AdminFarmerTransformer | None = None,
    ) -> None:
        """Initialize the farmer service.

        Args:
            plantation_client: Optional PlantationClient (created if not provided).
            transformer: Optional AdminFarmerTransformer (created if not provided).
        """
        super().__init__()
        self._plantation = plantation_client or PlantationClient()
        self._transformer = transformer or AdminFarmerTransformer()

    async def list_farmers(
        self,
        region_id: str | None = None,
        factory_id: str | None = None,
        collection_point_id: str | None = None,
        page_size: int = 50,
        page_token: str | None = None,
        active_only: bool = False,
    ) -> AdminFarmerListResponse:
        """List farmers with filters and pagination.

        Args:
            region_id: Optional region ID to filter by.
            factory_id: Optional factory ID to filter by.
            collection_point_id: Optional CP ID to filter by.
            page_size: Number of farmers per page.
            page_token: Pagination token for next page.
            active_only: If True, only return active farmers.

        Returns:
            AdminFarmerListResponse with paginated farmer summaries.
        """
        self._logger.info(
            "listing_farmers",
            region_id=region_id,
            factory_id=factory_id,
            collection_point_id=collection_point_id,
            page_size=page_size,
            has_page_token=page_token is not None,
            active_only=active_only,
        )

        # Story 9.5a: N:M Farmer-CP relationship
        # Filter by collection_point_id using CP.farmer_ids
        cp_id = collection_point_id
        if not cp_id and factory_id:
            # Get first CP for this factory
            cp_response = await self._plantation.list_collection_points(
                factory_id=factory_id,
                page_size=1,
                active_only=True,
            )
            if cp_response.data:
                cp_id = cp_response.data[0].id

        if cp_id:
            # Get farmers assigned to this CP using N:M relationship
            farmers = await self._plantation.get_farmers_for_collection_point(cp_id)

            # Filter by active_only if needed
            if active_only:
                farmers = [f for f in farmers if f.is_active]

            if not farmers:
                from bff.api.schemas.responses import PaginationMeta

                return AdminFarmerListResponse(
                    data=[],
                    pagination=PaginationMeta(
                        page=1,
                        page_size=page_size,
                        total_count=0,
                        total_pages=0,
                    ),
                )

            # Get factory for quality thresholds
            cp = await self._plantation.get_collection_point(cp_id)
            factory = await self._plantation.get_factory(cp.factory_id)
        else:
            # No CP filter - use region or return empty
            if not region_id:
                from bff.api.schemas.responses import PaginationMeta

                return AdminFarmerListResponse(
                    data=[],
                    pagination=PaginationMeta(
                        page=1,
                        page_size=page_size,
                        total_count=0,
                        total_pages=0,
                    ),
                )

            # List farmers by region
            response = await self._plantation.list_farmers(
                region_id=region_id,
                page_size=page_size,
                page_token=page_token,
                active_only=active_only,
            )
            farmers = response.data

            if not farmers:
                return AdminFarmerListResponse(
                    data=[],
                    pagination=response.pagination,
                )

            # Get first farmer's factory for thresholds (or use defaults)
            try:
                # Get CP for first farmer to get factory
                first_farmer = farmers[0]
                cps_response = await self._plantation.get_collection_points_for_farmer(first_farmer.id)
                if cps_response.data:
                    factory = await self._plantation.get_factory(cps_response.data[0].factory_id)
                else:
                    factory = None
            except Exception:
                factory = None

        # Enrich with performance data using parallel fetch
        # Use factory thresholds if available, otherwise use defaults
        from bff.api.schemas.responses import PaginationMeta
        from fp_common.models.value_objects import QualityThresholds

        thresholds = factory.quality_thresholds if factory else QualityThresholds()
        summaries = await self._enrich_farmers_to_summaries(
            farmers=farmers,
            thresholds=thresholds,
        )

        # Build pagination info
        total_count = len(farmers)
        total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1
        pagination = PaginationMeta(
            page=1,  # CP filter returns all, so always page 1
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
        )

        self._logger.info(
            "listed_farmers",
            count=len(summaries),
            total_count=total_count,
        )

        return AdminFarmerListResponse(
            data=summaries,
            pagination=pagination,
        )

    async def get_farmer(self, farmer_id: str) -> AdminFarmerDetail:
        """Get farmer detail by ID.

        Args:
            farmer_id: Farmer ID (e.g., "WM-0001").

        Returns:
            AdminFarmerDetail with full farmer information.

        Raises:
            NotFoundError: If farmer not found.
        """
        self._logger.info("getting_farmer", farmer_id=farmer_id)

        farmer = await self._plantation.get_farmer(farmer_id)

        # Story 9.5a: Get factory via N:M relationship (farmer -> CPs -> factory)
        cps_response = await self._plantation.get_collection_points_for_farmer(farmer_id)
        if cps_response.data:
            factory = await self._plantation.get_factory(cps_response.data[0].factory_id)
        else:
            # Farmer not assigned to any CP - use default thresholds
            factory = None

        # Get performance data
        try:
            performance = await self._plantation.get_farmer_summary(farmer_id)
        except NotFoundError:
            # No performance data yet - use defaults
            performance = FarmerPerformance.initialize_for_farmer(
                farmer_id=farmer_id,
                farm_size_hectares=farmer.farm_size_hectares,
                farm_scale=farmer.farm_scale,
                grading_model_id="default",
                grading_model_version="1.0.0",
            )

        # Use factory thresholds if available, otherwise use defaults
        from fp_common.models.value_objects import QualityThresholds

        thresholds = factory.quality_thresholds if factory else QualityThresholds()
        detail = self._transformer.to_detail(
            farmer=farmer,
            performance=performance,
            thresholds=thresholds,
        )

        self._logger.info(
            "got_farmer",
            farmer_id=farmer_id,
            tier=detail.performance.tier.value,
        )

        return detail

    async def create_farmer(self, data: AdminFarmerCreateRequest) -> AdminFarmerDetail:
        """Create a new farmer.

        Args:
            data: Farmer creation request.

        Returns:
            AdminFarmerDetail of created farmer.

        Raises:
            ValidationError: If farmer data is invalid.
        """
        # Story 9.5a: collection_point_id removed - CP assignment via delivery
        self._logger.info(
            "creating_farmer",
            first_name=data.first_name,
            last_name=data.last_name,
        )

        # Story 9.5a: Create farmer without CP - CP assignment happens on first delivery
        create_data = FarmerCreate(
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
            national_id=data.national_id,
            farm_size_hectares=data.farm_size_hectares,
            latitude=data.latitude,
            longitude=data.longitude,
            grower_number=data.grower_number,
        )

        farmer = await self._plantation.create_farmer(create_data)

        # New farmer has no performance data
        performance = FarmerPerformance.initialize_for_farmer(
            farmer_id=farmer.id,
            farm_size_hectares=farmer.farm_size_hectares,
            farm_scale=farmer.farm_scale,
            grading_model_id="default",
            grading_model_version="1.0.0",
        )

        # Story 9.5a: Use default thresholds for new farmers (no factory association yet)
        from fp_common.models.value_objects import QualityThresholds

        thresholds = QualityThresholds()
        detail = self._transformer.to_detail(
            farmer=farmer,
            performance=performance,
            thresholds=thresholds,
        )

        self._logger.info("created_farmer", farmer_id=farmer.id)

        return detail

    async def update_farmer(
        self,
        farmer_id: str,
        data: AdminFarmerUpdateRequest,
    ) -> AdminFarmerDetail:
        """Update an existing farmer.

        Args:
            farmer_id: Farmer ID to update.
            data: Farmer update request.

        Returns:
            AdminFarmerDetail of updated farmer.

        Raises:
            NotFoundError: If farmer not found.
            ValidationError: If update data is invalid.
        """
        self._logger.info("updating_farmer", farmer_id=farmer_id)

        # Create domain model for update
        update_data = FarmerUpdate(
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
            farm_size_hectares=data.farm_size_hectares,
            notification_channel=data.notification_channel,
            interaction_pref=data.interaction_pref,
            pref_lang=data.pref_lang,
            is_active=data.is_active,
        )

        farmer = await self._plantation.update_farmer(farmer_id, update_data)

        # Story 9.5a: Get factory via N:M relationship
        cps = await self._plantation.get_collection_points_for_farmer(farmer_id)
        if cps:
            factory = await self._plantation.get_factory(cps[0].factory_id)
        else:
            factory = None

        # Get performance data
        try:
            performance = await self._plantation.get_farmer_summary(farmer_id)
        except NotFoundError:
            performance = FarmerPerformance.initialize_for_farmer(
                farmer_id=farmer_id,
                farm_size_hectares=farmer.farm_size_hectares,
                farm_scale=farmer.farm_scale,
                grading_model_id="default",
                grading_model_version="1.0.0",
            )

        # Use factory thresholds if available, otherwise use defaults
        from fp_common.models.value_objects import QualityThresholds

        thresholds = factory.quality_thresholds if factory else QualityThresholds()
        detail = self._transformer.to_detail(
            farmer=farmer,
            performance=performance,
            thresholds=thresholds,
        )

        self._logger.info("updated_farmer", farmer_id=farmer_id)

        return detail

    async def import_farmers(
        self,
        csv_content: str,
        skip_header: bool = True,
    ) -> FarmerImportResponse:
        """Bulk import farmers from CSV content.

        Expected CSV columns:
        - first_name, last_name, phone, national_id
        - farm_size_hectares, latitude, longitude, grower_number (optional)

        Story 9.5a: collection_point_id removed - CP assignment via delivery.

        Args:
            csv_content: CSV content as string.
            skip_header: Whether to skip the first row.

        Returns:
            FarmerImportResponse with results.
        """
        self._logger.info(
            "importing_farmers",
            skip_header=skip_header,
        )

        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        created_count = 0
        error_rows: list[ImportErrorRow] = []

        async def process_row(row_num: int, row: dict) -> bool:
            """Process a single row. Returns True if successful."""
            try:
                # Story 9.5a: collection_point_id removed - CP assignment via delivery
                create_data = FarmerCreate(
                    first_name=row["first_name"],
                    last_name=row["last_name"],
                    phone=row["phone"],
                    national_id=row["national_id"],
                    farm_size_hectares=float(row["farm_size_hectares"]),
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                    grower_number=row.get("grower_number"),
                )

                await self._plantation.create_farmer(create_data)
                return True
            except Exception as e:
                error_rows.append(
                    ImportErrorRow(
                        row=row_num,
                        error=str(e),
                        data=row,
                    )
                )
                return False

        # Process rows with bounded concurrency
        for i, row in enumerate(rows):
            row_num = i + 2 if skip_header else i + 1  # Account for header
            if await process_row(row_num, row):
                created_count += 1

        self._logger.info(
            "imported_farmers",
            created_count=created_count,
            error_count=len(error_rows),
            total_rows=len(rows),
        )

        return FarmerImportResponse(
            created_count=created_count,
            error_count=len(error_rows),
            error_rows=error_rows,
            total_rows=len(rows),
        )

    async def _enrich_farmers_to_summaries(
        self,
        farmers: list[Farmer],
        thresholds: QualityThresholds,
    ) -> list[AdminFarmerSummary]:
        """Enrich farmers with performance data and transform to summaries.

        Uses bounded parallel execution (Semaphore(5)).

        Args:
            farmers: List of farmer domain models.
            thresholds: Factory quality thresholds for tier computation.

        Returns:
            List of AdminFarmerSummary in same order as input.
        """

        async def enrich_single(farmer: Farmer) -> AdminFarmerSummary:
            try:
                performance = await self._plantation.get_farmer_summary(farmer.id)
            except NotFoundError:
                # No performance data yet - use defaults
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
