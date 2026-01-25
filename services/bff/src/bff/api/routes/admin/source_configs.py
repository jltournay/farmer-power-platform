"""Source Config admin API routes (Story 9.11b).

Implements AC 9.11b.3 and AC 9.11b.4 - Source Configuration Viewer Endpoints:
- GET /api/admin/source-configs - List source configs with filters
- GET /api/admin/source-configs/{source_id} - Get source config detail

All routes require platform_admin role (ADR-019 §"Authorization").
"""

import os

from bff.api.middleware.auth import require_platform_admin
from bff.api.schemas import ApiError, PaginationMeta, TokenClaims
from bff.api.schemas.admin.source_config_schemas import (
    SourceConfigDetailResponse,
    SourceConfigListResponse,
    SourceConfigSummaryResponse,
)
from bff.infrastructure.clients import NotFoundError, ServiceUnavailableError
from bff.infrastructure.clients.source_config_client import SourceConfigClient
from fastapi import APIRouter, Depends, HTTPException, Path, Query

router = APIRouter(prefix="/source-configs", tags=["admin-source-configs"])


def get_source_config_client() -> SourceConfigClient:
    """Dependency for SourceConfigClient.

    Uses COLLECTION_GRPC_HOST environment variable for direct connection
    in testing environments, otherwise routes via DAPR.
    """
    direct_host = os.environ.get("COLLECTION_GRPC_HOST")
    return SourceConfigClient(direct_host=direct_host)


@router.get(
    "",
    response_model=SourceConfigListResponse,
    responses={
        200: {"description": "Paginated list of source configurations"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        503: {"description": "Collection Model service unavailable", "model": ApiError},
    },
    summary="List source configurations",
    description="List all source configurations with optional filters. Requires platform_admin role.",
)
async def list_source_configs(
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page (max 100)",
    ),
    page_token: str | None = Query(
        default=None,
        description="Pagination token from previous response",
    ),
    enabled_only: bool = Query(
        default=False,
        description="If true, only return enabled source configs",
    ),
    ingestion_mode: str | None = Query(
        default=None,
        description="Filter by ingestion mode: 'blob_trigger' or 'scheduled_pull'",
    ),
    user: TokenClaims = require_platform_admin(),
    client: SourceConfigClient = Depends(get_source_config_client),
) -> SourceConfigListResponse:
    """List all source configurations with optional filtering and pagination.

    Returns a paginated list of source configuration summaries.
    Use page_token from the response to fetch subsequent pages.
    """
    try:
        result = await client.list_source_configs(
            page_size=page_size,
            page_token=page_token,
            enabled_only=enabled_only,
            ingestion_mode=ingestion_mode,
        )

        return SourceConfigListResponse(
            data=[SourceConfigSummaryResponse.from_domain(item) for item in result.data],
            pagination=PaginationMeta(
                page_size=result.pagination.page_size,
                total_count=result.pagination.total_count,
                next_page_token=result.pagination.next_page_token,
            ),
        )
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Collection Model").model_dump(),
        ) from e


@router.get(
    "/{source_id}",
    response_model=SourceConfigDetailResponse,
    responses={
        200: {"description": "Source configuration detail"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        404: {"description": "Source configuration not found", "model": ApiError},
        503: {"description": "Collection Model service unavailable", "model": ApiError},
    },
    summary="Get source configuration detail",
    description="Get full source configuration detail including config_json. Requires platform_admin role.",
)
async def get_source_config(
    source_id: str = Path(
        description="Source configuration ID (e.g., 'qc-analyzer-result')",
    ),
    user: TokenClaims = require_platform_admin(),
    client: SourceConfigClient = Depends(get_source_config_client),
) -> SourceConfigDetailResponse:
    """Get source configuration detail by ID.

    Returns the full source configuration including the complete
    config_json blob with all configuration settings.
    """
    try:
        result = await client.get_source_config(source_id)
        return SourceConfigDetailResponse.from_domain(result)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError(
                code="SOURCE_CONFIG_NOT_FOUND",
                message=f"Source configuration '{source_id}' not found",
            ).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Collection Model").model_dump(),
        ) from e
