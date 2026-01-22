"""Grading Model service for admin API (Story 9.6a).

Orchestrates PlantationClient calls for grading model management.
"""

from bff.api.schemas.admin.grading_model_schemas import (
    GradingModelDetail,
    GradingModelListResponse,
)
from bff.infrastructure.clients.plantation_client import PlantationClient
from bff.services.base_service import BaseService
from bff.transformers.admin.grading_model_transformer import GradingModelTransformer


class AdminGradingModelService(BaseService):
    """Service for admin grading model operations.

    Orchestrates PlantationClient calls and transforms to API schemas.
    """

    def __init__(
        self,
        plantation_client: PlantationClient | None = None,
        transformer: GradingModelTransformer | None = None,
    ) -> None:
        """Initialize the grading model service.

        Args:
            plantation_client: Optional PlantationClient (created if not provided).
            transformer: Optional GradingModelTransformer (created if not provided).
        """
        super().__init__()
        self._plantation = plantation_client or PlantationClient()
        self._transformer = transformer or GradingModelTransformer()

    async def list_grading_models(
        self,
        market_name: str | None = None,
        crops_name: str | None = None,
        grading_type: str | None = None,
        page_size: int = 50,
        page_token: str | None = None,
    ) -> GradingModelListResponse:
        """List grading models with optional filtering.

        Args:
            market_name: Optional filter by market (e.g., "Kenya_TBK").
            crops_name: Optional filter by crop name (e.g., "Tea").
            grading_type: Optional filter by type ("binary", "ternary", "multi_level").
            page_size: Number of results per page (default: 50, max: 100).
            page_token: Token for pagination.

        Returns:
            GradingModelListResponse with paginated grading model summaries.
        """
        self._logger.info(
            "listing_grading_models",
            market_name=market_name,
            crops_name=crops_name,
            grading_type=grading_type,
            page_size=page_size,
            has_page_token=page_token is not None,
        )

        response = await self._plantation.list_grading_models(
            market_name=market_name,
            crops_name=crops_name,
            grading_type=grading_type,
            page_size=page_size,
            page_token=page_token,
        )

        # Transform to summaries
        summaries = [self._transformer.to_summary(model) for model in response.data]

        self._logger.info(
            "listed_grading_models",
            count=len(summaries),
            total_count=response.pagination.total_count,
        )

        return GradingModelListResponse(
            data=summaries,
            pagination=response.pagination,
        )

    async def get_grading_model(self, model_id: str) -> GradingModelDetail:
        """Get grading model detail by ID.

        Args:
            model_id: Grading model ID (e.g., "tbk_kenya_tea_v1").

        Returns:
            GradingModelDetail with full grading model information.

        Raises:
            NotFoundError: If grading model not found.
        """
        self._logger.info("getting_grading_model", model_id=model_id)

        model = await self._plantation.get_grading_model(model_id)

        # Resolve factory names for active_at_factory list
        factory_names = await self._resolve_factory_names(model.active_at_factory)

        detail = self._transformer.to_detail(
            model=model,
            factory_names=factory_names,
        )

        self._logger.info(
            "got_grading_model",
            model_id=model_id,
            factory_count=len(model.active_at_factory),
        )

        return detail

    async def assign_to_factory(
        self,
        model_id: str,
        factory_id: str,
    ) -> GradingModelDetail:
        """Assign a grading model to a factory.

        Args:
            model_id: Grading model ID to assign.
            factory_id: Factory ID to assign the model to.

        Returns:
            GradingModelDetail with updated factory assignments.

        Raises:
            NotFoundError: If grading model or factory not found.
        """
        self._logger.info(
            "assigning_grading_model",
            model_id=model_id,
            factory_id=factory_id,
        )

        model = await self._plantation.assign_grading_model_to_factory(
            model_id=model_id,
            factory_id=factory_id,
        )

        # Resolve factory names for the updated active_at_factory list
        factory_names = await self._resolve_factory_names(model.active_at_factory)

        detail = self._transformer.to_detail(
            model=model,
            factory_names=factory_names,
        )

        self._logger.info(
            "assigned_grading_model",
            model_id=model_id,
            factory_id=factory_id,
            factory_count=len(model.active_at_factory),
        )

        return detail

    async def _resolve_factory_names(
        self,
        factory_ids: list[str],
    ) -> dict[str, str]:
        """Resolve factory IDs to factory names.

        Uses parallel fetch for efficiency.

        Args:
            factory_ids: List of factory IDs to resolve.

        Returns:
            Dict mapping factory_id -> factory_name.
        """
        if not factory_ids:
            return {}

        async def get_factory_name(factory_id: str) -> tuple[str, str | None]:
            try:
                factory = await self._plantation.get_factory(factory_id)
                return factory_id, factory.name
            except Exception:
                # If factory not found, return None for name
                return factory_id, None

        results = await self._parallel_map(factory_ids, get_factory_name)

        return {fid: name for fid, name in results if name is not None}
