"""Platform Cost gRPC client for BFF.

Story 13.6: BFF Integration Layer

This client provides typed access to the Platform Cost service via DAPR gRPC
service invocation. All methods return fp-common Pydantic domain models (NOT dicts).

Pattern follows:
- ADR-002 §"Service Invocation Pattern" (native gRPC with dapr-app-id metadata)
- ADR-005 for retry logic (3 attempts, exponential backoff 1-10s)
- ADR-016 for unified cost aggregation

CRITICAL: Uses fp-common domain models for type safety. Never returns dict[str, Any].
"""

from datetime import date
from decimal import Decimal

import grpc
import grpc.aio
import structlog
from bff.infrastructure.clients.base import (
    BaseGrpcClient,
    grpc_retry,
)
from fp_common.converters import (
    budget_status_from_proto,
    budget_threshold_config_from_proto,
    cost_summary_from_proto,
    current_day_cost_from_proto,
    daily_cost_trend_from_proto,
    document_cost_summary_from_proto,
    embedding_cost_by_domain_from_proto,
    llm_cost_by_agent_type_from_proto,
    llm_cost_by_model_from_proto,
)
from fp_common.models import (
    BudgetStatus,
    BudgetThresholdConfig,
    CostSummary,
    CurrentDayCost,
    DailyCostTrend,
    DocumentCostSummary,
    EmbeddingCostByDomain,
    LlmCostByAgentType,
    LlmCostByModel,
)
from fp_proto.platform_cost.v1 import platform_cost_pb2, platform_cost_pb2_grpc

logger = structlog.get_logger(__name__)


class PlatformCostClient(BaseGrpcClient):
    """Client for Platform Cost gRPC service via DAPR.

    Provides 9 query methods for cost data:

    Read Operations:
    - Cost Summary: get_cost_summary
    - Daily Trend: get_daily_cost_trend
    - Current Day: get_current_day_cost
    - LLM Breakdown: get_llm_cost_by_agent_type, get_llm_cost_by_model
    - Document Costs: get_document_cost_summary
    - Embedding Costs: get_embedding_cost_by_domain
    - Budget: get_budget_status

    Write Operations:
    - Budget: configure_budget_threshold

    All methods return typed Pydantic models from fp-common.

    Example:
        >>> client = PlatformCostClient()
        >>> summary = await client.get_cost_summary(
        ...     start_date=date(2025, 1, 1),
        ...     end_date=date(2025, 1, 31)
        ... )
        >>> print(summary.total_cost_usd)
        Decimal('123.45')
    """

    def __init__(
        self,
        dapr_grpc_port: int = 50001,
        direct_host: str | None = None,
        channel: grpc.aio.Channel | None = None,
    ) -> None:
        """Initialize the Platform Cost client.

        Args:
            dapr_grpc_port: Port for DAPR sidecar gRPC endpoint (default: 50001).
            direct_host: Optional direct host for testing (bypasses DAPR).
            channel: Optional pre-configured channel for testing.
        """
        super().__init__(
            target_app_id="platform-cost",
            dapr_grpc_port=dapr_grpc_port,
            direct_host=direct_host,
            channel=channel,
        )

    async def _get_cost_stub(self) -> platform_cost_pb2_grpc.UnifiedCostServiceStub:
        """Get the Unified Cost service stub."""
        return await self._get_stub(platform_cost_pb2_grpc.UnifiedCostServiceStub)

    # =========================================================================
    # Cost Summary Operations
    # =========================================================================

    @grpc_retry
    async def get_cost_summary(
        self,
        start_date: date,
        end_date: date,
        factory_id: str | None = None,
    ) -> CostSummary:
        """Get total costs with breakdown by type for a date range.

        Args:
            start_date: Start of date range (inclusive).
            end_date: End of date range (inclusive).
            factory_id: Optional filter by factory.

        Returns:
            CostSummary with total and per-type breakdown.

        Raises:
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_cost_stub()
            request = platform_cost_pb2.CostSummaryRequest(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
            if factory_id:
                request.factory_id = factory_id

            response = await stub.GetCostSummary(request, metadata=self._get_metadata())
            return cost_summary_from_proto(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Cost summary")
            raise

    @grpc_retry
    async def get_daily_cost_trend(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        days: int = 30,
    ) -> DailyCostTrend:
        """Get daily costs for stacked chart visualization.

        Args:
            start_date: Optional start of date range (inclusive).
            end_date: Optional end of date range (inclusive).
            days: Number of days to include if dates not specified (default: 30).

        Returns:
            DailyCostTrend with daily entries and data_available_from.

        Raises:
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_cost_stub()
            request = platform_cost_pb2.DailyCostTrendRequest(days=days)
            if start_date:
                request.start_date = start_date.isoformat()
            if end_date:
                request.end_date = end_date.isoformat()

            response = await stub.GetDailyCostTrend(request, metadata=self._get_metadata())
            return daily_cost_trend_from_proto(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Daily cost trend")
            raise

    @grpc_retry
    async def get_current_day_cost(self) -> CurrentDayCost:
        """Get real-time today's running cost total.

        Returns:
            CurrentDayCost with today's running total and breakdown.

        Raises:
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_cost_stub()
            request = platform_cost_pb2.CurrentDayCostRequest()
            response = await stub.GetCurrentDayCost(request, metadata=self._get_metadata())
            return current_day_cost_from_proto(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Current day cost")
            raise

    # =========================================================================
    # LLM Cost Breakdown Operations
    # =========================================================================

    @grpc_retry
    async def get_llm_cost_by_agent_type(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> LlmCostByAgentType:
        """Get LLM cost breakdown by agent type.

        Args:
            start_date: Optional start of date range.
            end_date: Optional end of date range.

        Returns:
            LlmCostByAgentType with per-agent breakdown.

        Raises:
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_cost_stub()
            request = platform_cost_pb2.LlmCostByAgentTypeRequest()
            if start_date:
                request.start_date = start_date.isoformat()
            if end_date:
                request.end_date = end_date.isoformat()

            response = await stub.GetLlmCostByAgentType(request, metadata=self._get_metadata())
            return llm_cost_by_agent_type_from_proto(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "LLM cost by agent type")
            raise

    @grpc_retry
    async def get_llm_cost_by_model(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> LlmCostByModel:
        """Get LLM cost breakdown by model.

        Args:
            start_date: Optional start of date range.
            end_date: Optional end of date range.

        Returns:
            LlmCostByModel with per-model breakdown.

        Raises:
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_cost_stub()
            request = platform_cost_pb2.LlmCostByModelRequest()
            if start_date:
                request.start_date = start_date.isoformat()
            if end_date:
                request.end_date = end_date.isoformat()

            response = await stub.GetLlmCostByModel(request, metadata=self._get_metadata())
            return llm_cost_by_model_from_proto(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "LLM cost by model")
            raise

    # =========================================================================
    # Document and Embedding Cost Operations
    # =========================================================================

    @grpc_retry
    async def get_document_cost_summary(
        self,
        start_date: date,
        end_date: date,
    ) -> DocumentCostSummary:
        """Get document processing cost summary.

        Args:
            start_date: Start of date range (required).
            end_date: End of date range (required).

        Returns:
            DocumentCostSummary with total, pages, avg cost per page.

        Raises:
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_cost_stub()
            request = platform_cost_pb2.DocumentCostSummaryRequest(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
            response = await stub.GetDocumentCostSummary(request, metadata=self._get_metadata())
            return document_cost_summary_from_proto(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Document cost summary")
            raise

    @grpc_retry
    async def get_embedding_cost_by_domain(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> EmbeddingCostByDomain:
        """Get embedding costs grouped by knowledge domain.

        Args:
            start_date: Optional start of date range.
            end_date: Optional end of date range.

        Returns:
            EmbeddingCostByDomain with per-domain breakdown.

        Raises:
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_cost_stub()
            request = platform_cost_pb2.EmbeddingCostByDomainRequest()
            if start_date:
                request.start_date = start_date.isoformat()
            if end_date:
                request.end_date = end_date.isoformat()

            response = await stub.GetEmbeddingCostByDomain(request, metadata=self._get_metadata())
            return embedding_cost_by_domain_from_proto(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Embedding cost by domain")
            raise

    # =========================================================================
    # Budget Operations
    # =========================================================================

    @grpc_retry
    async def get_budget_status(self) -> BudgetStatus:
        """Get current budget thresholds and utilization.

        Returns:
            BudgetStatus with current thresholds and running totals.

        Raises:
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_cost_stub()
            request = platform_cost_pb2.BudgetStatusRequest()
            response = await stub.GetBudgetStatus(request, metadata=self._get_metadata())
            return budget_status_from_proto(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Budget status")
            raise

    @grpc_retry
    async def configure_budget_threshold(
        self,
        daily_threshold_usd: Decimal | None = None,
        monthly_threshold_usd: Decimal | None = None,
    ) -> BudgetThresholdConfig:
        """Configure budget thresholds (persisted to MongoDB).

        Args:
            daily_threshold_usd: Optional new daily threshold.
            monthly_threshold_usd: Optional new monthly threshold.

        Returns:
            BudgetThresholdConfig with updated thresholds.

        Raises:
            ServiceUnavailableError: If service is unavailable.
        """
        try:
            stub = await self._get_cost_stub()
            request = platform_cost_pb2.ConfigureBudgetThresholdRequest()
            if daily_threshold_usd is not None:
                request.daily_threshold_usd = str(daily_threshold_usd)
            if monthly_threshold_usd is not None:
                request.monthly_threshold_usd = str(monthly_threshold_usd)

            response = await stub.ConfigureBudgetThreshold(request, metadata=self._get_metadata())
            return budget_threshold_config_from_proto(response)
        except grpc.aio.AioRpcError as e:
            self._handle_grpc_error(e, "Configure budget threshold")
            raise
