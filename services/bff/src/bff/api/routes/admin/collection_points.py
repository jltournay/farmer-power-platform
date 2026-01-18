"""Collection Point admin API routes.

Implements AC3 - Collection Point Management Endpoints:
- GET /api/admin/collection-points - List CPs with factory_id filter (required)
- GET /api/admin/collection-points/{cp_id} - Get CP detail
- PUT /api/admin/collection-points/{cp_id} - Update CP

Note: CP creation is via POST /api/admin/factories/{factory_id}/collection-points
"""

import os

from bff.api.middleware.auth import require_platform_admin
from bff.api.schemas import ApiError, TokenClaims
from bff.api.schemas.admin.collection_point_schemas import (
    CollectionPointDetail,
    CollectionPointListResponse,
    CollectionPointUpdateRequest,
    FarmerAssignmentResponse,
)
from bff.infrastructure.clients import NotFoundError, ServiceUnavailableError
from bff.infrastructure.clients.plantation_client import PlantationClient
from bff.services.admin.collection_point_service import AdminCollectionPointService
from bff.transformers.admin.collection_point_transformer import CollectionPointTransformer
from fastapi import APIRouter, Depends, HTTPException, Path, Query

router = APIRouter(prefix="/collection-points", tags=["admin-collection-points"])


def get_collection_point_service() -> AdminCollectionPointService:
    """Dependency for AdminCollectionPointService."""
    direct_host = os.environ.get("PLANTATION_GRPC_HOST")
    return AdminCollectionPointService(
        plantation_client=PlantationClient(direct_host=direct_host),
        transformer=CollectionPointTransformer(),
    )


@router.get(
    "",
    response_model=CollectionPointListResponse,
    responses={
        200: {"description": "Paginated list of collection points"},
        400: {"description": "factory_id is required", "model": ApiError},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="List collection points",
    description="List collection points for a factory. factory_id filter is required.",
)
async def list_collection_points(
    factory_id: str = Query(
        ...,
        description="Factory ID (required)",
        pattern=r"^[A-Z]{3}-(?:FAC|E2E)-\d{3}$",
    ),
    page_size: int = Query(default=50, ge=1, le=100, description="Number per page"),
    page_token: str | None = Query(default=None, description="Pagination token"),
    active_only: bool = Query(default=False, description="Only return active CPs"),
    user: TokenClaims = require_platform_admin(),
    service: AdminCollectionPointService = Depends(get_collection_point_service),
) -> CollectionPointListResponse:
    """List collection points for a factory."""
    try:
        return await service.list_collection_points(
            factory_id=factory_id,
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
    "/{cp_id}",
    response_model=CollectionPointDetail,
    responses={
        200: {"description": "Collection point detail"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        404: {"description": "Collection point not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Get collection point detail",
    description="Get full collection point detail including location and farmer count.",
)
async def get_collection_point(
    cp_id: str = Path(
        ...,
        description="Collection point ID",
        pattern=r"^[a-z][a-z0-9-]*-cp-\d{3}$",
        examples=["nyeri-highland-cp-001"],
    ),
    user: TokenClaims = require_platform_admin(),
    service: AdminCollectionPointService = Depends(get_collection_point_service),
) -> CollectionPointDetail:
    """Get collection point detail by ID."""
    try:
        return await service.get_collection_point(cp_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError.not_found("Collection Point", cp_id).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Plantation Model").model_dump(),
        ) from e


@router.put(
    "/{cp_id}",
    response_model=CollectionPointDetail,
    responses={
        200: {"description": "Collection point updated"},
        400: {"description": "Invalid request", "model": ApiError},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        404: {"description": "Collection point not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Update collection point",
    description="Update an existing collection point. Only provided fields are updated.",
)
async def update_collection_point(
    data: CollectionPointUpdateRequest,
    cp_id: str = Path(
        ...,
        description="Collection point ID",
        pattern=r"^[a-z][a-z0-9-]*-cp-\d{3}$",
    ),
    user: TokenClaims = require_platform_admin(),
    service: AdminCollectionPointService = Depends(get_collection_point_service),
) -> CollectionPointDetail:
    """Update an existing collection point."""
    try:
        return await service.update_collection_point(cp_id, data)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError.not_found("Collection Point", cp_id).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Plantation Model").model_dump(),
        ) from e


# ============================================================================
# Farmer-CollectionPoint Assignment Endpoints (Story 9.5a)
# ============================================================================


@router.post(
    "/{cp_id}/farmers/{farmer_id}",
    response_model=FarmerAssignmentResponse,
    responses={
        200: {"description": "Farmer assigned to collection point"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        404: {"description": "Collection point or farmer not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Assign farmer to collection point",
    description="Assign a farmer to a collection point. Idempotent - assigning twice has no effect. (Story 9.5a)",
)
async def assign_farmer_to_collection_point(
    cp_id: str = Path(
        ...,
        description="Collection point ID",
        pattern=r"^[a-z][a-z0-9-]*-cp-\d{3}$",
        examples=["nyeri-highland-cp-001"],
    ),
    farmer_id: str = Path(
        ...,
        description="Farmer ID to assign",
        pattern=r"^(WM-\d{4}|FRM-E2E-\d{3})$",
        examples=["WM-0001", "FRM-E2E-001"],
    ),
    user: TokenClaims = require_platform_admin(),
    service: AdminCollectionPointService = Depends(get_collection_point_service),
) -> FarmerAssignmentResponse:
    """Assign a farmer to a collection point (AC 9.5a.3)."""
    try:
        return await service.assign_farmer(cp_id, farmer_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError.not_found("Collection Point or Farmer", f"{cp_id}/{farmer_id}").model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Plantation Model").model_dump(),
        ) from e


@router.delete(
    "/{cp_id}/farmers/{farmer_id}",
    response_model=FarmerAssignmentResponse,
    responses={
        200: {"description": "Farmer unassigned from collection point"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        404: {"description": "Collection point or farmer not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Unassign farmer from collection point",
    description="Unassign a farmer from a collection point. Idempotent - non-member unassign is no-op.",
)
async def unassign_farmer_from_collection_point(
    cp_id: str = Path(
        ...,
        description="Collection point ID",
        pattern=r"^[a-z][a-z0-9-]*-cp-\d{3}$",
        examples=["nyeri-highland-cp-001"],
    ),
    farmer_id: str = Path(
        ...,
        description="Farmer ID to unassign",
        pattern=r"^(WM-\d{4}|FRM-E2E-\d{3})$",
        examples=["WM-0001", "FRM-E2E-001"],
    ),
    user: TokenClaims = require_platform_admin(),
    service: AdminCollectionPointService = Depends(get_collection_point_service),
) -> FarmerAssignmentResponse:
    """Unassign a farmer from a collection point (AC 9.5a.3)."""
    try:
        return await service.unassign_farmer(cp_id, farmer_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError.not_found("Collection Point or Farmer", f"{cp_id}/{farmer_id}").model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Plantation Model").model_dump(),
        ) from e
