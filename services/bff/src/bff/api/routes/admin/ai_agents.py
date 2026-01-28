"""AI Agent Config admin API routes (Story 9.12b).

Implements AC 9.12b.3, AC 9.12b.4, AC 9.12b.5 - AI Agent Configuration Viewer Endpoints:
- GET /api/admin/ai-agents - List agent configs with filters
- GET /api/admin/ai-agents/{agent_id} - Get agent config detail
- GET /api/admin/ai-agents/{agent_id}/prompts - List prompts by agent

All routes require platform_admin role (ADR-019 "Authorization").
"""

import os

from bff.api.middleware.auth import require_platform_admin
from bff.api.schemas import ApiError, PaginationMeta, TokenClaims
from bff.api.schemas.admin.agent_config_schemas import (
    AgentConfigDetailResponse,
    AgentConfigListResponse,
    AgentConfigSummaryResponse,
    PromptListResponse,
    PromptSummaryResponse,
)
from bff.infrastructure.clients import NotFoundError, ServiceUnavailableError
from bff.infrastructure.clients.agent_config_client import AgentConfigClient
from fastapi import APIRouter, Depends, HTTPException, Path, Query

router = APIRouter(prefix="/ai-agents", tags=["admin-ai-agents"])


def get_agent_config_client() -> AgentConfigClient:
    """Dependency for AgentConfigClient.

    Uses AI_MODEL_GRPC_HOST environment variable for direct connection
    in testing environments, otherwise routes via DAPR.
    """
    direct_host = os.environ.get("AI_MODEL_GRPC_HOST")
    return AgentConfigClient(direct_host=direct_host)


@router.get(
    "",
    response_model=AgentConfigListResponse,
    responses={
        200: {"description": "Paginated list of agent configurations"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        503: {"description": "AI Model service unavailable", "model": ApiError},
    },
    summary="List AI agent configurations",
    description="List all AI agent configurations with optional filters. Requires platform_admin role.",
)
async def list_ai_agents(
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
    agent_type: str | None = Query(
        default=None,
        description="Filter by agent type: 'extractor', 'explorer', 'generator', 'conversational', 'tiered-vision'",
    ),
    status: str | None = Query(
        default=None,
        description="Filter by status: 'draft', 'staged', 'active', 'archived'",
    ),
    user: TokenClaims = require_platform_admin(),
    client: AgentConfigClient = Depends(get_agent_config_client),
) -> AgentConfigListResponse:
    """List all AI agent configurations with optional filtering and pagination.

    Returns a paginated list of agent configuration summaries.
    Use page_token from the response to fetch subsequent pages.
    """
    try:
        result = await client.list_agent_configs(
            page_size=page_size,
            page_token=page_token,
            agent_type=agent_type,
            status=status,
        )

        return AgentConfigListResponse(
            data=[AgentConfigSummaryResponse.from_domain(item) for item in result.data],
            pagination=PaginationMeta(
                page_size=result.pagination.page_size,
                total_count=result.pagination.total_count,
                next_page_token=result.pagination.next_page_token,
            ),
        )
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("AI Model").model_dump(),
        ) from e


@router.get(
    "/{agent_id}",
    response_model=AgentConfigDetailResponse,
    responses={
        200: {"description": "Agent configuration detail"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        404: {"description": "Agent configuration not found", "model": ApiError},
        503: {"description": "AI Model service unavailable", "model": ApiError},
    },
    summary="Get AI agent configuration detail",
    description="Get full AI agent configuration detail including config_json and linked prompts. Requires platform_admin role.",
)
async def get_ai_agent(
    agent_id: str = Path(
        description="Agent configuration ID (e.g., 'disease-diagnosis')",
    ),
    user: TokenClaims = require_platform_admin(),
    client: AgentConfigClient = Depends(get_agent_config_client),
) -> AgentConfigDetailResponse:
    """Get AI agent configuration detail by ID.

    Returns the full agent configuration including the complete
    config_json blob with all configuration settings and linked prompts.
    """
    try:
        result = await client.get_agent_config(agent_id)
        return AgentConfigDetailResponse.from_domain(result)
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError(
                code="AGENT_CONFIG_NOT_FOUND",
                message=f"Agent configuration '{agent_id}' not found",
            ).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("AI Model").model_dump(),
        ) from e


@router.get(
    "/{agent_id}/prompts",
    response_model=PromptListResponse,
    responses={
        200: {"description": "List of prompts for this agent"},
        401: {"description": "Authentication required", "model": ApiError},
        403: {"description": "Platform admin access required", "model": ApiError},
        404: {"description": "Agent not found", "model": ApiError},
        503: {"description": "AI Model service unavailable", "model": ApiError},
    },
    summary="List prompts by agent",
    description="List all prompts linked to a specific AI agent. Requires platform_admin role.",
)
async def list_prompts_by_agent(
    agent_id: str = Path(
        description="Agent configuration ID (e.g., 'disease-diagnosis')",
    ),
    status: str | None = Query(
        default=None,
        description="Filter by prompt status: 'draft', 'staged', 'active', 'archived'",
    ),
    user: TokenClaims = require_platform_admin(),
    client: AgentConfigClient = Depends(get_agent_config_client),
) -> PromptListResponse:
    """List all prompts linked to a specific AI agent.

    Returns a list of prompt summaries for the specified agent.
    Use the optional status filter to filter by prompt lifecycle status.
    """
    try:
        prompts = await client.list_prompts_by_agent(agent_id, status=status)
        return PromptListResponse(
            data=[PromptSummaryResponse.from_domain(p) for p in prompts],
            total_count=len(prompts),
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=ApiError(
                code="AGENT_NOT_FOUND",
                message=f"Agent '{agent_id}' not found",
            ).model_dump(),
        ) from e
    except ServiceUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=ApiError.service_unavailable("AI Model").model_dump(),
        ) from e
