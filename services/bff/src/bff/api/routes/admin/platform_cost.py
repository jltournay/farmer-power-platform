"""Platform Cost admin API routes (Story 9.10a).

Implements REST endpoints for platform cost monitoring:
- Cost Summary: GET /costs/summary
- Daily Trend: GET /costs/trend/daily
- Current Day: GET /costs/today
- LLM Breakdown: GET /costs/llm/by-agent-type, GET /costs/llm/by-model
- Document Costs: GET /costs/documents
- Embedding Costs: GET /costs/embeddings/by-domain
- Budget: GET /costs/budget, PUT /costs/budget
"""

import os
from datetime import date

from bff.api.middleware.auth import require_platform_admin
from bff.api.schemas import ApiError, TokenClaims
from bff.api.schemas.admin.platform_cost_schemas import (
    BudgetConfigRequest,
    BudgetConfigResponse,
    BudgetStatusResponse,
    CostSummaryResponse,
    CurrentDayCostResponse,
    DailyTrendResponse,
    DocumentCostResponse,
    EmbeddingByDomainResponse,
    LlmByAgentTypeResponse,
    LlmByModelResponse,
)
from bff.infrastructure.clients import ServiceUnavailableError
from bff.infrastructure.clients.platform_cost_client import PlatformCostClient
from bff.services.admin.platform_cost_service import AdminPlatformCostService
from bff.transformers.admin.platform_cost_transformer import PlatformCostTransformer
from fastapi import APIRouter, Depends, HTTPException, Query

router = APIRouter(prefix="/costs", tags=["admin-costs"])


def get_platform_cost_service() -> AdminPlatformCostService:
    """Dependency for AdminPlatformCostService."""
    direct_host = os.environ.get("PLATFORM_COST_GRPC_HOST")
    return AdminPlatformCostService(
        platform_cost_client=PlatformCostClient(direct_host=direct_host),
        transformer=PlatformCostTransformer(),
    )


# =========================================================================
# Cost Summary (AC 9.10a.1)
# =========================================================================


@router.get(
    "/summary",
    response_model=CostSummaryResponse,
    responses={
        200: {"description": "Cost summary with breakdown by type"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        503: {"description": "Platform Cost service unavailable", "model": ApiError},
    },
    summary="Get cost summary",
    description="Get total costs with breakdown by type for a date range. Requires platform_admin role.",
)
async def get_cost_summary(
    start_date: date = Query(description="Start of date range (YYYY-MM-DD)"),
    end_date: date = Query(description="End of date range (YYYY-MM-DD)"),
    factory_id: str | None = Query(default=None, description="Optional factory filter"),
    user: TokenClaims = require_platform_admin(),
    service: AdminPlatformCostService = Depends(get_platform_cost_service),
) -> CostSummaryResponse:
    """Get cost summary for a date range with optional factory filter."""
    try:
        return await service.get_cost_summary(
            start_date=start_date,
            end_date=end_date,
            factory_id=factory_id,
        )
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Platform Cost").model_dump(),
        ) from e


# =========================================================================
# Daily Trend (AC 9.10a.2)
# =========================================================================


@router.get(
    "/trend/daily",
    response_model=DailyTrendResponse,
    responses={
        200: {"description": "Daily cost trend entries"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        503: {"description": "Platform Cost service unavailable", "model": ApiError},
    },
    summary="Get daily cost trend",
    description="Get daily costs for stacked chart visualization. Requires platform_admin role.",
)
async def get_daily_cost_trend(
    start_date: date | None = Query(default=None, description="Optional start date"),
    end_date: date | None = Query(default=None, description="Optional end date"),
    days: int = Query(default=30, ge=1, le=365, description="Number of days (default: 30)"),
    user: TokenClaims = require_platform_admin(),
    service: AdminPlatformCostService = Depends(get_platform_cost_service),
) -> DailyTrendResponse:
    """Get daily cost trend for chart visualization."""
    try:
        return await service.get_daily_cost_trend(
            start_date=start_date,
            end_date=end_date,
            days=days,
        )
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Platform Cost").model_dump(),
        ) from e


# =========================================================================
# Current Day (AC 9.10a.3)
# =========================================================================


@router.get(
    "/today",
    response_model=CurrentDayCostResponse,
    responses={
        200: {"description": "Current day running cost total"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        503: {"description": "Platform Cost service unavailable", "model": ApiError},
    },
    summary="Get current day cost",
    description="Get real-time today's running cost total. Requires platform_admin role.",
)
async def get_current_day_cost(
    user: TokenClaims = require_platform_admin(),
    service: AdminPlatformCostService = Depends(get_platform_cost_service),
) -> CurrentDayCostResponse:
    """Get current day running cost total."""
    try:
        return await service.get_current_day_cost()
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Platform Cost").model_dump(),
        ) from e


# =========================================================================
# LLM Breakdown (AC 9.10a.4)
# =========================================================================


@router.get(
    "/llm/by-agent-type",
    response_model=LlmByAgentTypeResponse,
    responses={
        200: {"description": "LLM cost breakdown by agent type"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        503: {"description": "Platform Cost service unavailable", "model": ApiError},
    },
    summary="Get LLM cost by agent type",
    description="Get LLM cost breakdown by agent type. Requires platform_admin role.",
)
async def get_llm_cost_by_agent_type(
    start_date: date | None = Query(default=None, description="Optional start date"),
    end_date: date | None = Query(default=None, description="Optional end date"),
    user: TokenClaims = require_platform_admin(),
    service: AdminPlatformCostService = Depends(get_platform_cost_service),
) -> LlmByAgentTypeResponse:
    """Get LLM cost breakdown by agent type."""
    try:
        return await service.get_llm_cost_by_agent_type(
            start_date=start_date,
            end_date=end_date,
        )
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Platform Cost").model_dump(),
        ) from e


@router.get(
    "/llm/by-model",
    response_model=LlmByModelResponse,
    responses={
        200: {"description": "LLM cost breakdown by model"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        503: {"description": "Platform Cost service unavailable", "model": ApiError},
    },
    summary="Get LLM cost by model",
    description="Get LLM cost breakdown by model. Requires platform_admin role.",
)
async def get_llm_cost_by_model(
    start_date: date | None = Query(default=None, description="Optional start date"),
    end_date: date | None = Query(default=None, description="Optional end date"),
    user: TokenClaims = require_platform_admin(),
    service: AdminPlatformCostService = Depends(get_platform_cost_service),
) -> LlmByModelResponse:
    """Get LLM cost breakdown by model."""
    try:
        return await service.get_llm_cost_by_model(
            start_date=start_date,
            end_date=end_date,
        )
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Platform Cost").model_dump(),
        ) from e


# =========================================================================
# Document Costs (AC 9.10a.5)
# =========================================================================


@router.get(
    "/documents",
    response_model=DocumentCostResponse,
    responses={
        200: {"description": "Document processing cost summary"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        503: {"description": "Platform Cost service unavailable", "model": ApiError},
    },
    summary="Get document cost summary",
    description="Get document processing cost summary for a date range. Requires platform_admin role.",
)
async def get_document_cost_summary(
    start_date: date = Query(description="Start of date range (YYYY-MM-DD)"),
    end_date: date = Query(description="End of date range (YYYY-MM-DD)"),
    user: TokenClaims = require_platform_admin(),
    service: AdminPlatformCostService = Depends(get_platform_cost_service),
) -> DocumentCostResponse:
    """Get document processing cost summary."""
    try:
        return await service.get_document_cost_summary(
            start_date=start_date,
            end_date=end_date,
        )
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Platform Cost").model_dump(),
        ) from e


# =========================================================================
# Embedding Costs (AC 9.10a.6)
# =========================================================================


@router.get(
    "/embeddings/by-domain",
    response_model=EmbeddingByDomainResponse,
    responses={
        200: {"description": "Embedding cost breakdown by knowledge domain"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        503: {"description": "Platform Cost service unavailable", "model": ApiError},
    },
    summary="Get embedding cost by domain",
    description="Get embedding costs grouped by knowledge domain. Requires platform_admin role.",
)
async def get_embedding_cost_by_domain(
    start_date: date | None = Query(default=None, description="Optional start date"),
    end_date: date | None = Query(default=None, description="Optional end date"),
    user: TokenClaims = require_platform_admin(),
    service: AdminPlatformCostService = Depends(get_platform_cost_service),
) -> EmbeddingByDomainResponse:
    """Get embedding cost breakdown by knowledge domain."""
    try:
        return await service.get_embedding_cost_by_domain(
            start_date=start_date,
            end_date=end_date,
        )
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Platform Cost").model_dump(),
        ) from e


# =========================================================================
# Budget (AC 9.10a.7)
# =========================================================================


@router.get(
    "/budget",
    response_model=BudgetStatusResponse,
    responses={
        200: {"description": "Current budget thresholds and utilization"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        503: {"description": "Platform Cost service unavailable", "model": ApiError},
    },
    summary="Get budget status",
    description="Get current budget thresholds and utilization. Requires platform_admin role.",
)
async def get_budget_status(
    user: TokenClaims = require_platform_admin(),
    service: AdminPlatformCostService = Depends(get_platform_cost_service),
) -> BudgetStatusResponse:
    """Get current budget thresholds and utilization."""
    try:
        return await service.get_budget_status()
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Platform Cost").model_dump(),
        ) from e


@router.put(
    "/budget",
    response_model=BudgetConfigResponse,
    responses={
        200: {"description": "Updated budget thresholds"},
        400: {"description": "Invalid threshold values", "model": ApiError},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        503: {"description": "Platform Cost service unavailable", "model": ApiError},
    },
    summary="Configure budget thresholds",
    description="Configure daily and/or monthly budget thresholds. Requires platform_admin role.",
)
async def configure_budget_threshold(
    request: BudgetConfigRequest,
    user: TokenClaims = require_platform_admin(),
    service: AdminPlatformCostService = Depends(get_platform_cost_service),
) -> BudgetConfigResponse:
    """Configure budget thresholds."""
    if request.daily_threshold_usd is None and request.monthly_threshold_usd is None:
        raise HTTPException(
            status_code=400,
            detail=ApiError(
                code="VALIDATION_ERROR",
                message="At least one threshold (daily or monthly) must be provided",
            ).model_dump(),
        )

    try:
        return await service.configure_budget_threshold(
            daily_threshold_usd=request.daily_threshold_usd,
            monthly_threshold_usd=request.monthly_threshold_usd,
        )
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("Platform Cost").model_dump(),
        ) from e
