"""Factory admin API routes.

Implements AC2 - Factory Management Endpoints:
- GET /api/admin/factories - List all factories with pagination
- GET /api/admin/factories/{factory_id} - Get factory detail
- POST /api/admin/factories - Create new factory
- PUT /api/admin/factories/{factory_id} - Update factory
- POST /api/admin/factories/{factory_id}/collection-points - Create CP under factory
"""

import os

from bff.api.middleware.auth import require_platform_admin
from bff.api.schemas import ApiError, TokenClaims
from bff.api.schemas.admin.collection_point_schemas import (
    CollectionPointCreateRequest,
    CollectionPointDetail,
)
from bff.api.schemas.admin.factory_schemas import (
    FactoryCreateRequest,
    FactoryDetail,
    FactoryListResponse,
    FactoryUpdateRequest,
)
from bff.infrastructure.clients import NotFoundError, ServiceUnavailableError
from bff.infrastructure.clients.plantation_client import PlantationClient
from bff.services.admin.collection_point_service import AdminCollectionPointService
from bff.services.admin.factory_service import AdminFactoryService
from bff.transformers.admin.collection_point_transformer import CollectionPointTransformer
from bff.transformers.admin.factory_transformer import FactoryTransformer
from fastapi import APIRouter, Depends, HTTPException, Path, Query

router = APIRouter(prefix="/factories", tags=["admin-factories"])


def get_factory_service() -> AdminFactoryService:
    """Dependency for AdminFactoryService."""
    direct_host = os.environ.get("PLANTATION_GRPC_HOST")
    return AdminFactoryService(
        plantation_client=PlantationClient(direct_host=direct_host),
        transformer=FactoryTransformer(),
    )


def get_collection_point_service() -> AdminCollectionPointService:
    """Dependency for AdminCollectionPointService."""
    direct_host = os.environ.get("PLANTATION_GRPC_HOST")
    return AdminCollectionPointService(
        plantation_client=PlantationClient(direct_host=direct_host),
        transformer=CollectionPointTransformer(),
    )


@router.get(
    "",
    response_model=FactoryListResponse,
    responses={
        200: {"description": "Paginated list of factories"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="List all factories",
    description="List all factories with optional region filter. Requires platform_admin role.",
)
async def list_factories(
    region_id: str | None = Query(default=None, description="Filter by region ID"),
    page_size: int = Query(default=50, ge=1, le=100, description="Number per page"),
    page_token: str | None = Query(default=None, description="Pagination token"),
    active_only: bool = Query(default=False, description="Only return active factories"),
    user: TokenClaims = require_platform_admin(),
    service: AdminFactoryService = Depends(get_factory_service),
) -> FactoryListResponse:
    """List all factories with pagination."""
    try:
        return await service.list_factories(
            region_id=region_id,
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
    "/{factory_id}",
    response_model=FactoryDetail,
    responses={
        200: {"description": "Factory detail"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        404: {"description": "Factory not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Get factory detail",
    description="Get full factory detail including quality thresholds and grading model.",
)
async def get_factory(
    factory_id: str = Path(
        ...,
        description="Factory ID",
        pattern=r"^[A-Z]{3}-(?:FAC|E2E)-\d{3}$",
        examples=["KEN-FAC-001", "KEN-E2E-001"],
    ),
    user: TokenClaims = require_platform_admin(),
    service: AdminFactoryService = Depends(get_factory_service),
) -> FactoryDetail:
    """Get factory detail by ID."""
    try:
        return await service.get_factory(factory_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError.not_found("Factory", factory_id).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Plantation Model").model_dump(),
        ) from e


@router.post(
    "",
    response_model=FactoryDetail,
    status_code=201,
    responses={
        201: {"description": "Factory created"},
        400: {"description": "Invalid request", "model": ApiError},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        404: {"description": "Region not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Create factory",
    description="Create a new factory with quality thresholds.",
)
async def create_factory(
    data: FactoryCreateRequest,
    user: TokenClaims = require_platform_admin(),
    service: AdminFactoryService = Depends(get_factory_service),
) -> FactoryDetail:
    """Create a new factory."""
    try:
        return await service.create_factory(data)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError.not_found("Region", data.region_id).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Plantation Model").model_dump(),
        ) from e


@router.put(
    "/{factory_id}",
    response_model=FactoryDetail,
    responses={
        200: {"description": "Factory updated"},
        400: {"description": "Invalid request", "model": ApiError},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        404: {"description": "Factory not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Update factory",
    description="Update an existing factory. Only provided fields are updated.",
)
async def update_factory(
    data: FactoryUpdateRequest,
    factory_id: str = Path(
        ...,
        description="Factory ID",
        pattern=r"^[A-Z]{3}-(?:FAC|E2E)-\d{3}$",
    ),
    user: TokenClaims = require_platform_admin(),
    service: AdminFactoryService = Depends(get_factory_service),
) -> FactoryDetail:
    """Update an existing factory."""
    try:
        return await service.update_factory(factory_id, data)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError.not_found("Factory", factory_id).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Plantation Model").model_dump(),
        ) from e


@router.post(
    "/{factory_id}/collection-points",
    response_model=CollectionPointDetail,
    status_code=201,
    responses={
        201: {"description": "Collection point created"},
        400: {"description": "Invalid request", "model": ApiError},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        404: {"description": "Factory not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Create collection point under factory",
    description="Create a new collection point nested under a factory.",
)
async def create_collection_point(
    data: CollectionPointCreateRequest,
    factory_id: str = Path(
        ...,
        description="Factory ID",
        pattern=r"^[A-Z]{3}-(?:FAC|E2E)-\d{3}$",
    ),
    user: TokenClaims = require_platform_admin(),
    service: AdminCollectionPointService = Depends(get_collection_point_service),
) -> CollectionPointDetail:
    """Create a new collection point under a factory."""
    try:
        return await service.create_collection_point(factory_id, data)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError.not_found("Factory", factory_id).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Plantation Model").model_dump(),
        ) from e
