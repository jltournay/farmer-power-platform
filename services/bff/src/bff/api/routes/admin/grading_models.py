"""Grading Model admin API routes (Story 9.6a).

Implements AC 9.6a.3 - Grading Model Management Endpoints:
- GET /api/admin/grading-models - List grading models with filters
- GET /api/admin/grading-models/{model_id} - Get grading model detail
- POST /api/admin/grading-models/{model_id}/assign - Assign model to factory
"""

import os

from bff.api.middleware.auth import require_platform_admin
from bff.api.schemas import ApiError, TokenClaims
from bff.api.schemas.admin.grading_model_schemas import (
    AssignGradingModelRequest,
    GradingModelDetail,
    GradingModelListResponse,
)
from bff.infrastructure.clients import NotFoundError, ServiceUnavailableError
from bff.infrastructure.clients.plantation_client import PlantationClient
from bff.services.admin.grading_model_service import AdminGradingModelService
from bff.transformers.admin.grading_model_transformer import GradingModelTransformer
from fastapi import APIRouter, Depends, HTTPException, Path, Query

router = APIRouter(prefix="/grading-models", tags=["admin-grading-models"])


def get_grading_model_service() -> AdminGradingModelService:
    """Dependency for AdminGradingModelService."""
    direct_host = os.environ.get("PLANTATION_GRPC_HOST")
    return AdminGradingModelService(
        plantation_client=PlantationClient(direct_host=direct_host),
        transformer=GradingModelTransformer(),
    )


@router.get(
    "",
    response_model=GradingModelListResponse,
    responses={
        200: {"description": "Paginated list of grading models"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="List grading models",
    description="List all grading models with optional filters. Requires platform_admin role.",
)
async def list_grading_models(
    market_name: str | None = Query(default=None, description="Filter by market (e.g., 'Kenya_TBK')"),
    crops_name: str | None = Query(default=None, description="Filter by crop name (e.g., 'Tea')"),
    grading_type: str | None = Query(
        default=None,
        description="Filter by grading type: 'binary', 'ternary', or 'multi_level'",
    ),
    page_size: int = Query(default=50, ge=1, le=100, description="Number per page"),
    page_token: str | None = Query(default=None, description="Pagination token"),
    user: TokenClaims = require_platform_admin(),
    service: AdminGradingModelService = Depends(get_grading_model_service),
) -> GradingModelListResponse:
    """List all grading models with optional filtering and pagination."""
    try:
        return await service.list_grading_models(
            market_name=market_name,
            crops_name=crops_name,
            grading_type=grading_type,
            page_size=page_size,
            page_token=page_token,
        )
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Plantation Model").model_dump(),
        ) from e


@router.get(
    "/{model_id}",
    response_model=GradingModelDetail,
    responses={
        200: {"description": "Grading model detail"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        404: {"description": "Grading model not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Get grading model detail",
    description="Get full grading model detail including attributes and rules. Requires platform_admin role.",
)
async def get_grading_model(
    model_id: str = Path(description="Grading model ID (e.g., 'tbk_kenya_tea_v1')"),
    user: TokenClaims = require_platform_admin(),
    service: AdminGradingModelService = Depends(get_grading_model_service),
) -> GradingModelDetail:
    """Get grading model detail by ID."""
    try:
        return await service.get_grading_model(model_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError(
                code="GRADING_MODEL_NOT_FOUND",
                message=f"Grading model {model_id} not found",
            ).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Plantation Model").model_dump(),
        ) from e


@router.post(
    "/{model_id}/assign",
    response_model=GradingModelDetail,
    responses={
        200: {"description": "Grading model assigned successfully"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        404: {"description": "Grading model or factory not found", "model": ApiError},
        422: {"description": "Invalid request", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Assign grading model to factory",
    description="Assign a grading model to a factory. Requires platform_admin role.",
)
async def assign_grading_model(
    model_id: str = Path(description="Grading model ID to assign"),
    request: AssignGradingModelRequest = ...,
    user: TokenClaims = require_platform_admin(),
    service: AdminGradingModelService = Depends(get_grading_model_service),
) -> GradingModelDetail:
    """Assign a grading model to a factory."""
    try:
        return await service.assign_to_factory(
            model_id=model_id,
            factory_id=request.factory_id,
        )
    except NotFoundError as e:
        # Check error message to determine which entity was not found
        error_msg = str(e)
        if "factory" in error_msg.lower():
            raise HTTPException(
                status_code=404,
                detail=ApiError(
                    code="FACTORY_NOT_FOUND",
                    message=f"Factory {request.factory_id} not found",
                ).model_dump(),
            ) from e
        else:
            raise HTTPException(
                status_code=404,
                detail=ApiError(
                    code="GRADING_MODEL_NOT_FOUND",
                    message=f"Grading model {model_id} not found",
                ).model_dump(),
            ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Plantation Model").model_dump(),
        ) from e
