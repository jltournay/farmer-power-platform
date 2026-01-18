"""Farmer admin API routes.

Implements AC4 - Farmer Management Endpoints:
- GET /api/admin/farmers - List farmers with filters
- GET /api/admin/farmers/{farmer_id} - Get farmer detail
- POST /api/admin/farmers - Create farmer
- PUT /api/admin/farmers/{farmer_id} - Update farmer
- POST /api/admin/farmers/import - Bulk import from CSV
"""

import os

from bff.api.middleware.auth import require_platform_admin
from bff.api.schemas import ApiError, TokenClaims
from bff.api.schemas.admin.farmer_schemas import (
    AdminFarmerCreateRequest,
    AdminFarmerDetail,
    AdminFarmerListResponse,
    AdminFarmerUpdateRequest,
    FarmerImportResponse,
)
from bff.infrastructure.clients import NotFoundError, ServiceUnavailableError
from bff.infrastructure.clients.plantation_client import PlantationClient
from bff.services.admin.farmer_service import AdminFarmerService
from bff.transformers.admin.farmer_transformer import AdminFarmerTransformer
from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, UploadFile

router = APIRouter(prefix="/farmers", tags=["admin-farmers"])


def get_farmer_service() -> AdminFarmerService:
    """Dependency for AdminFarmerService."""
    direct_host = os.environ.get("PLANTATION_GRPC_HOST")
    return AdminFarmerService(
        plantation_client=PlantationClient(direct_host=direct_host),
        transformer=AdminFarmerTransformer(),
    )


@router.get(
    "",
    response_model=AdminFarmerListResponse,
    responses={
        200: {"description": "Paginated list of farmers"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="List farmers",
    description="List farmers with optional filters (region_id, factory_id, collection_point_id).",
)
async def list_farmers(
    region_id: str | None = Query(default=None, description="Filter by region ID"),
    factory_id: str | None = Query(default=None, description="Filter by factory ID"),
    collection_point_id: str | None = Query(default=None, description="Filter by CP ID"),
    page_size: int = Query(default=50, ge=1, le=100, description="Number per page"),
    page_token: str | None = Query(default=None, description="Pagination token"),
    active_only: bool = Query(default=False, description="Only return active farmers"),
    user: TokenClaims = require_platform_admin(),
    service: AdminFarmerService = Depends(get_farmer_service),
) -> AdminFarmerListResponse:
    """List farmers with filters."""
    try:
        return await service.list_farmers(
            region_id=region_id,
            factory_id=factory_id,
            collection_point_id=collection_point_id,
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
    "/{farmer_id}",
    response_model=AdminFarmerDetail,
    responses={
        200: {"description": "Farmer detail"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        404: {"description": "Farmer not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Get farmer detail",
    description="Get full farmer detail with profile, performance, and communication preferences.",
)
async def get_farmer(
    farmer_id: str = Path(
        ...,
        description="Farmer ID",
        pattern=r"^(?:WM|FRM-E2E)-\d{3,4}$",
        examples=["WM-0001", "FRM-E2E-001"],
    ),
    user: TokenClaims = require_platform_admin(),
    service: AdminFarmerService = Depends(get_farmer_service),
) -> AdminFarmerDetail:
    """Get farmer detail by ID."""
    try:
        return await service.get_farmer(farmer_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError.not_found("Farmer", farmer_id).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Plantation Model").model_dump(),
        ) from e


@router.post(
    "",
    response_model=AdminFarmerDetail,
    status_code=201,
    responses={
        201: {"description": "Farmer created"},
        400: {"description": "Invalid request", "model": ApiError},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        404: {"description": "Collection point not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Create farmer",
    description="Create a new farmer. ID is auto-generated, region is auto-assigned from GPS.",
)
async def create_farmer(
    data: AdminFarmerCreateRequest,
    user: TokenClaims = require_platform_admin(),
    service: AdminFarmerService = Depends(get_farmer_service),
) -> AdminFarmerDetail:
    """Create a new farmer."""
    try:
        return await service.create_farmer(data)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError.not_found("Collection Point", data.collection_point_id).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Plantation Model").model_dump(),
        ) from e


@router.put(
    "/{farmer_id}",
    response_model=AdminFarmerDetail,
    responses={
        200: {"description": "Farmer updated"},
        400: {"description": "Invalid request", "model": ApiError},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        404: {"description": "Farmer not found", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Update farmer",
    description="Update an existing farmer. Only provided fields are updated.",
)
async def update_farmer(
    data: AdminFarmerUpdateRequest,
    farmer_id: str = Path(
        ...,
        description="Farmer ID",
        pattern=r"^(?:WM|FRM-E2E)-\d{3,4}$",
    ),
    user: TokenClaims = require_platform_admin(),
    service: AdminFarmerService = Depends(get_farmer_service),
) -> AdminFarmerDetail:
    """Update an existing farmer."""
    try:
        return await service.update_farmer(farmer_id, data)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError.not_found("Farmer", farmer_id).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Plantation Model").model_dump(),
        ) from e


@router.post(
    "/import",
    response_model=FarmerImportResponse,
    responses={
        200: {"description": "Import results"},
        400: {"description": "Invalid CSV", "model": ApiError},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        503: {"description": "Service unavailable", "model": ApiError},
    },
    summary="Bulk import farmers from CSV",
    description="""
    Import farmers from CSV file. Expected columns:
    - first_name, last_name, phone, national_id
    - farm_size_hectares, latitude, longitude, grower_number (optional)

    Story 9.5a: collection_point_id removed - CP is assigned via delivery or separate API.
    """,
)
async def import_farmers(
    file: UploadFile = File(..., description="CSV file with farmer data"),
    skip_header: bool = Form(default=True, description="Skip header row"),
    user: TokenClaims = require_platform_admin(),
    service: AdminFarmerService = Depends(get_farmer_service),
) -> FarmerImportResponse:
    """Bulk import farmers from CSV."""
    try:
        # Read CSV content
        content = await file.read()
        csv_content = content.decode("utf-8")

        return await service.import_farmers(
            csv_content=csv_content,
            skip_header=skip_header,
        )
    except UnicodeDecodeError as e:
        raise HTTPException(
            status_code=400,
            detail=ApiError.bad_request("CSV file must be UTF-8 encoded").model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Plantation Model").model_dump(),
        ) from e
