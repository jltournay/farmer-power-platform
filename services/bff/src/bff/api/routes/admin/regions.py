"""Region admin API routes.

Implements AC1 - Region Management Endpoints:
- GET /api/admin/regions - List all regions with pagination
- GET /api/admin/regions/{region_id} - Get region detail
- POST /api/admin/regions - Create new region
- PUT /api/admin/regions/{region_id} - Update region
"""

import os

from bff.api.middleware.auth import require_platform_admin
from bff.api.schemas import ApiError, TokenClaims
from bff.api.schemas.admin.region_schemas import (
    RegionCreateRequest,
    RegionDetail,
    RegionListResponse,
    RegionUpdateRequest,
)
from bff.infrastructure.clients import NotFoundError, ServiceUnavailableError
from bff.infrastructure.clients.plantation_client import PlantationClient
from bff.services.admin.region_service import AdminRegionService
from bff.transformers.admin.region_transformer import RegionTransformer
from fastapi import APIRouter, Depends, HTTPException, Path, Query

router = APIRouter(prefix="/regions", tags=["admin-regions"])


def get_region_service() -> AdminRegionService:
    """Dependency for AdminRegionService.

    Creates service with PlantationClient configured for environment.
    """
    direct_host = os.environ.get("PLANTATION_GRPC_HOST")
    return AdminRegionService(
        plantation_client=PlantationClient(direct_host=direct_host),
        transformer=RegionTransformer(),
    )


@router.get(
    "",
    response_model=RegionListResponse,
    responses={
        200: {"description": "Paginated list of regions"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="List all regions",
    description="List all regions with pagination. Requires platform_admin role.",
)
async def list_regions(
    page_size: int = Query(default=50, ge=1, le=100, description="Number of regions per page"),
    page_token: str | None = Query(default=None, description="Pagination token"),
    active_only: bool = Query(default=False, description="Only return active regions"),
    user: TokenClaims = require_platform_admin(),
    service: AdminRegionService = Depends(get_region_service),
) -> RegionListResponse:
    """List all regions with pagination.

    Returns region summaries with factory and farmer counts.
    """
    try:
        return await service.list_regions(
            page_size=page_size,
            page_token=page_token,
            active_only=active_only,
        )
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Plantation Model").model_dump(),
        ) from e


@router.get(
    "/{region_id}",
    response_model=RegionDetail,
    responses={
        200: {"description": "Region detail"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        404: {"description": "Region not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Get region detail",
    description="Get full region detail including weather config and polygon boundaries.",
)
async def get_region(
    region_id: str = Path(
        ...,
        description="Region ID",
        pattern=r"^[a-z][a-z0-9-]*-(highland|midland|lowland)$",
        examples=["nyeri-highland", "murang-a-midland"],
    ),
    user: TokenClaims = require_platform_admin(),
    service: AdminRegionService = Depends(get_region_service),
) -> RegionDetail:
    """Get region detail by ID."""
    try:
        return await service.get_region(region_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError.not_found("Region", region_id).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Plantation Model").model_dump(),
        ) from e


@router.post(
    "",
    response_model=RegionDetail,
    status_code=201,
    responses={
        201: {"description": "Region created"},
        400: {"description": "Invalid request", "model": ApiError},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        409: {"description": "Region already exists", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Create region",
    description="Create a new region with weather configuration and polygon boundaries.",
)
async def create_region(
    data: RegionCreateRequest,
    user: TokenClaims = require_platform_admin(),
    service: AdminRegionService = Depends(get_region_service),
) -> RegionDetail:
    """Create a new region."""
    try:
        return await service.create_region(data)
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Plantation Model").model_dump(),
        ) from e


@router.put(
    "/{region_id}",
    response_model=RegionDetail,
    responses={
        200: {"description": "Region updated"},
        400: {"description": "Invalid request", "model": ApiError},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        404: {"description": "Region not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Update region",
    description="Update an existing region. Only provided fields are updated.",
)
async def update_region(
    data: RegionUpdateRequest,
    region_id: str = Path(
        ...,
        description="Region ID",
        pattern=r"^[a-z][a-z0-9-]*-(highland|midland|lowland)$",
    ),
    user: TokenClaims = require_platform_admin(),
    service: AdminRegionService = Depends(get_region_service),
) -> RegionDetail:
    """Update an existing region."""
    try:
        return await service.update_region(region_id, data)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError.not_found("Region", region_id).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Plantation Model").model_dump(),
        ) from e
