"""gRPC UnifiedCostService implementation.

Story 13.4: gRPC UnifiedCostService (ADR-016)

This module implements the UnifiedCostService gRPC servicer that exposes
all cost query and budget management APIs. It delegates to the repository
and budget monitor for data access and state management.

Key methods:
- GetCostSummary: Total costs with type breakdown
- GetDailyCostTrend: Daily costs for stacked chart (includes data_available_from)
- GetCurrentDayCost: Real-time today's cost
- GetLlmCostByAgentType: LLM breakdown by agent
- GetLlmCostByModel: LLM breakdown by model
- GetDocumentCostSummary: Document processing costs
- GetEmbeddingCostByDomain: Embedding costs by knowledge domain
- GetBudgetStatus: Current thresholds and utilization
- ConfigureBudgetThreshold: Update thresholds (persisted to MongoDB)
"""

from datetime import UTC, date, datetime
from decimal import Decimal

import grpc
import structlog
from fp_proto.platform_cost.v1 import platform_cost_pb2, platform_cost_pb2_grpc

from platform_cost.infrastructure.repositories.cost_repository import (
    UnifiedCostRepository,
)
from platform_cost.infrastructure.repositories.threshold_repository import (
    ThresholdRepository,
)
from platform_cost.services.budget_monitor import BudgetMonitor

logger = structlog.get_logger(__name__)


class UnifiedCostServiceServicer(platform_cost_pb2_grpc.UnifiedCostServiceServicer):
    """gRPC servicer for unified cost queries and budget management.

    Implements all 9 RPC methods defined in platform_cost.proto.
    Delegates to repository for data access and budget monitor for state.
    """

    def __init__(
        self,
        cost_repository: UnifiedCostRepository,
        budget_monitor: BudgetMonitor,
        threshold_repository: ThresholdRepository,
    ) -> None:
        """Initialize the servicer with dependencies.

        Args:
            cost_repository: Repository for cost event queries.
            budget_monitor: In-memory budget tracking.
            threshold_repository: Persistent threshold storage.
        """
        self._cost_repository = cost_repository
        self._budget_monitor = budget_monitor
        self._threshold_repository = threshold_repository

    async def GetCostSummary(
        self,
        request: platform_cost_pb2.CostSummaryRequest,
        context: grpc.aio.ServicerContext,
    ) -> platform_cost_pb2.CostSummaryResponse:
        """Get total costs with breakdown by type for a date range.

        Args:
            request: Contains start_date, end_date, optional factory_id.
            context: gRPC context.

        Returns:
            CostSummaryResponse with total and per-type breakdown.
        """
        logger.debug(
            "GetCostSummary called",
            start_date=request.start_date,
            end_date=request.end_date,
        )

        try:
            start_date = date.fromisoformat(request.start_date)
            end_date = date.fromisoformat(request.end_date)
        except ValueError as e:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"Invalid date format: {e}. Use YYYY-MM-DD.",
            )
            # Never reached but helps type checker
            raise  # pragma: no cover

        summaries = await self._cost_repository.get_summary_by_type(
            start_date=start_date,
            end_date=end_date,
        )

        # Calculate total
        total_cost = sum(s.total_cost_usd for s in summaries)
        total_requests = sum(s.request_count for s in summaries)

        # Build response
        by_type = [
            platform_cost_pb2.CostTypeBreakdown(
                cost_type=s.cost_type,
                total_cost_usd=str(s.total_cost_usd),
                total_quantity=s.total_quantity,
                request_count=s.request_count,
                percentage=s.percentage,
            )
            for s in summaries
        ]

        return platform_cost_pb2.CostSummaryResponse(
            total_cost_usd=str(total_cost),
            by_type=by_type,
            period_start=request.start_date,
            period_end=request.end_date,
            total_requests=total_requests,
        )

    async def GetDailyCostTrend(
        self,
        request: platform_cost_pb2.DailyCostTrendRequest,
        context: grpc.aio.ServicerContext,
    ) -> platform_cost_pb2.DailyCostTrendResponse:
        """Get daily costs for stacked chart visualization.

        Args:
            request: Optional start_date, end_date, or days.
            context: gRPC context.

        Returns:
            DailyCostTrendResponse with daily entries and data_available_from.
        """
        logger.debug("GetDailyCostTrend called")

        # Parse optional dates
        start_date = None
        end_date = None
        days = request.days if request.HasField("days") else 30

        if request.HasField("start_date"):
            try:
                start_date = date.fromisoformat(request.start_date)
            except ValueError as e:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"Invalid start_date format: {e}. Use YYYY-MM-DD.",
                )
                raise  # pragma: no cover

        if request.HasField("end_date"):
            try:
                end_date = date.fromisoformat(request.end_date)
            except ValueError as e:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"Invalid end_date format: {e}. Use YYYY-MM-DD.",
                )
                raise  # pragma: no cover

        entries = await self._cost_repository.get_daily_trend(
            start_date=start_date,
            end_date=end_date,
            days=days,
        )

        # Build proto entries
        proto_entries = [
            platform_cost_pb2.DailyCostEntry(
                date=e.entry_date.isoformat(),
                total_cost_usd=str(e.total_cost_usd),
                llm_cost_usd=str(e.llm_cost_usd),
                document_cost_usd=str(e.document_cost_usd),
                embedding_cost_usd=str(e.embedding_cost_usd),
                sms_cost_usd=str(e.sms_cost_usd),
            )
            for e in entries
        ]

        # Get data availability date from repository
        data_available_from = self._cost_repository.data_available_from.date().isoformat()

        return platform_cost_pb2.DailyCostTrendResponse(
            entries=proto_entries,
            data_available_from=data_available_from,
        )

    async def GetCurrentDayCost(
        self,
        request: platform_cost_pb2.CurrentDayCostRequest,
        context: grpc.aio.ServicerContext,
    ) -> platform_cost_pb2.CurrentDayCostResponse:
        """Get real-time today's running cost total.

        Args:
            request: Empty request.
            context: gRPC context.

        Returns:
            CurrentDayCostResponse with today's running total.
        """
        logger.debug("GetCurrentDayCost called")

        current_day = await self._cost_repository.get_current_day_cost()

        return platform_cost_pb2.CurrentDayCostResponse(
            date=current_day.cost_date.isoformat(),
            total_cost_usd=str(current_day.total_cost_usd),
            by_type={k: str(v) for k, v in current_day.by_type.items()},
            updated_at=current_day.updated_at.isoformat(),
        )

    async def GetLlmCostByAgentType(
        self,
        request: platform_cost_pb2.LlmCostByAgentTypeRequest,
        context: grpc.aio.ServicerContext,
    ) -> platform_cost_pb2.LlmCostByAgentTypeResponse:
        """Get LLM cost breakdown by agent type.

        Args:
            request: Optional start_date and end_date.
            context: gRPC context.

        Returns:
            LlmCostByAgentTypeResponse with per-agent breakdown.
        """
        logger.debug("GetLlmCostByAgentType called")

        start_date = None
        end_date = None

        if request.HasField("start_date"):
            try:
                start_date = date.fromisoformat(request.start_date)
            except ValueError as e:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"Invalid start_date format: {e}. Use YYYY-MM-DD.",
                )
                raise  # pragma: no cover

        if request.HasField("end_date"):
            try:
                end_date = date.fromisoformat(request.end_date)
            except ValueError as e:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"Invalid end_date format: {e}. Use YYYY-MM-DD.",
                )
                raise  # pragma: no cover

        agent_costs = await self._cost_repository.get_llm_cost_by_agent_type(
            start_date=start_date,
            end_date=end_date,
        )

        total_cost = sum(a.cost_usd for a in agent_costs)

        proto_costs = [
            platform_cost_pb2.AgentTypeCost(
                agent_type=a.agent_type,
                cost_usd=str(a.cost_usd),
                request_count=a.request_count,
                tokens_in=a.tokens_in,
                tokens_out=a.tokens_out,
                percentage=a.percentage,
            )
            for a in agent_costs
        ]

        return platform_cost_pb2.LlmCostByAgentTypeResponse(
            agent_costs=proto_costs,
            total_llm_cost_usd=str(total_cost),
            period_start=start_date.isoformat() if start_date else "",
            period_end=end_date.isoformat() if end_date else "",
        )

    async def GetLlmCostByModel(
        self,
        request: platform_cost_pb2.LlmCostByModelRequest,
        context: grpc.aio.ServicerContext,
    ) -> platform_cost_pb2.LlmCostByModelResponse:
        """Get LLM cost breakdown by model.

        Args:
            request: Optional start_date and end_date.
            context: gRPC context.

        Returns:
            LlmCostByModelResponse with per-model breakdown.
        """
        logger.debug("GetLlmCostByModel called")

        start_date = None
        end_date = None

        if request.HasField("start_date"):
            try:
                start_date = date.fromisoformat(request.start_date)
            except ValueError as e:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"Invalid start_date format: {e}. Use YYYY-MM-DD.",
                )
                raise  # pragma: no cover

        if request.HasField("end_date"):
            try:
                end_date = date.fromisoformat(request.end_date)
            except ValueError as e:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"Invalid end_date format: {e}. Use YYYY-MM-DD.",
                )
                raise  # pragma: no cover

        model_costs = await self._cost_repository.get_llm_cost_by_model(
            start_date=start_date,
            end_date=end_date,
        )

        total_cost = sum(m.cost_usd for m in model_costs)

        proto_costs = [
            platform_cost_pb2.ModelCost(
                model=m.model,
                cost_usd=str(m.cost_usd),
                request_count=m.request_count,
                tokens_in=m.tokens_in,
                tokens_out=m.tokens_out,
                percentage=m.percentage,
            )
            for m in model_costs
        ]

        return platform_cost_pb2.LlmCostByModelResponse(
            model_costs=proto_costs,
            total_llm_cost_usd=str(total_cost),
            period_start=start_date.isoformat() if start_date else "",
            period_end=end_date.isoformat() if end_date else "",
        )

    async def GetDocumentCostSummary(
        self,
        request: platform_cost_pb2.DocumentCostSummaryRequest,
        context: grpc.aio.ServicerContext,
    ) -> platform_cost_pb2.DocumentCostSummaryResponse:
        """Get document processing cost summary.

        Args:
            request: Contains start_date and end_date (required).
            context: gRPC context.

        Returns:
            DocumentCostSummaryResponse with total, pages, avg cost per page.
        """
        logger.debug(
            "GetDocumentCostSummary called",
            start_date=request.start_date,
            end_date=request.end_date,
        )

        try:
            start_date = date.fromisoformat(request.start_date)
            end_date = date.fromisoformat(request.end_date)
        except ValueError as e:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"Invalid date format: {e}. Use YYYY-MM-DD.",
            )
            raise  # pragma: no cover

        summary = await self._cost_repository.get_document_cost_summary(
            start_date=start_date,
            end_date=end_date,
        )

        return platform_cost_pb2.DocumentCostSummaryResponse(
            total_cost_usd=str(summary.total_cost_usd),
            total_pages=summary.total_pages,
            avg_cost_per_page_usd=str(summary.avg_cost_per_page_usd),
            document_count=summary.document_count,
            period_start=request.start_date,
            period_end=request.end_date,
        )

    async def GetEmbeddingCostByDomain(
        self,
        request: platform_cost_pb2.EmbeddingCostByDomainRequest,
        context: grpc.aio.ServicerContext,
    ) -> platform_cost_pb2.EmbeddingCostByDomainResponse:
        """Get embedding costs grouped by knowledge domain.

        Args:
            request: Optional start_date and end_date.
            context: gRPC context.

        Returns:
            EmbeddingCostByDomainResponse with per-domain breakdown.
        """
        logger.debug("GetEmbeddingCostByDomain called")

        start_date = None
        end_date = None

        if request.HasField("start_date"):
            try:
                start_date = date.fromisoformat(request.start_date)
            except ValueError as e:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"Invalid start_date format: {e}. Use YYYY-MM-DD.",
                )
                raise  # pragma: no cover

        if request.HasField("end_date"):
            try:
                end_date = date.fromisoformat(request.end_date)
            except ValueError as e:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"Invalid end_date format: {e}. Use YYYY-MM-DD.",
                )
                raise  # pragma: no cover

        domain_costs = await self._cost_repository.get_embedding_cost_by_domain(
            start_date=start_date,
            end_date=end_date,
        )

        total_cost = sum(d.cost_usd for d in domain_costs)

        proto_costs = [
            platform_cost_pb2.DomainCost(
                knowledge_domain=d.knowledge_domain,
                cost_usd=str(d.cost_usd),
                tokens_total=d.tokens_total,
                texts_count=d.texts_count,
                percentage=d.percentage,
            )
            for d in domain_costs
        ]

        return platform_cost_pb2.EmbeddingCostByDomainResponse(
            domain_costs=proto_costs,
            total_embedding_cost_usd=str(total_cost),
            period_start=start_date.isoformat() if start_date else "",
            period_end=end_date.isoformat() if end_date else "",
        )

    async def GetBudgetStatus(
        self,
        request: platform_cost_pb2.BudgetStatusRequest,
        context: grpc.aio.ServicerContext,
    ) -> platform_cost_pb2.BudgetStatusResponse:
        """Get current budget thresholds and utilization.

        Args:
            request: Empty request.
            context: gRPC context.

        Returns:
            BudgetStatusResponse with current thresholds and running totals.
        """
        logger.debug("GetBudgetStatus called")

        status = self._budget_monitor.get_status()

        return platform_cost_pb2.BudgetStatusResponse(
            daily_threshold_usd=status.daily_threshold_usd,
            daily_total_usd=status.daily_total_usd,
            daily_alert_triggered=status.daily_alert_triggered,
            daily_remaining_usd=status.daily_remaining_usd,
            daily_utilization_percent=status.daily_utilization_percent,
            monthly_threshold_usd=status.monthly_threshold_usd,
            monthly_total_usd=status.monthly_total_usd,
            monthly_alert_triggered=status.monthly_alert_triggered,
            monthly_remaining_usd=status.monthly_remaining_usd,
            monthly_utilization_percent=status.monthly_utilization_percent,
            by_type=status.by_type,
            current_day=status.current_day or "",
            current_month=status.current_month or "",
        )

    async def ConfigureBudgetThreshold(
        self,
        request: platform_cost_pb2.ConfigureBudgetThresholdRequest,
        context: grpc.aio.ServicerContext,
    ) -> platform_cost_pb2.ConfigureBudgetThresholdResponse:
        """Configure budget thresholds (persisted to MongoDB).

        Updates both MongoDB (persistence) and in-memory budget monitor.

        Args:
            request: Optional daily_threshold_usd and monthly_threshold_usd.
            context: gRPC context.

        Returns:
            ConfigureBudgetThresholdResponse with updated thresholds.
        """
        logger.info(
            "ConfigureBudgetThreshold called",
            daily=request.daily_threshold_usd if request.HasField("daily_threshold_usd") else None,
            monthly=request.monthly_threshold_usd if request.HasField("monthly_threshold_usd") else None,
        )

        # Parse thresholds
        daily_threshold = None
        monthly_threshold = None

        if request.HasField("daily_threshold_usd"):
            try:
                daily_threshold = Decimal(request.daily_threshold_usd)
                if daily_threshold < 0:
                    await context.abort(
                        grpc.StatusCode.INVALID_ARGUMENT,
                        "daily_threshold_usd must be >= 0",
                    )
                    raise ValueError("Negative threshold")  # pragma: no cover
            except Exception as e:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"Invalid daily_threshold_usd: {e}",
                )
                raise  # pragma: no cover

        if request.HasField("monthly_threshold_usd"):
            try:
                monthly_threshold = Decimal(request.monthly_threshold_usd)
                if monthly_threshold < 0:
                    await context.abort(
                        grpc.StatusCode.INVALID_ARGUMENT,
                        "monthly_threshold_usd must be >= 0",
                    )
                    raise ValueError("Negative threshold")  # pragma: no cover
            except Exception as e:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"Invalid monthly_threshold_usd: {e}",
                )
                raise  # pragma: no cover

        # Persist to MongoDB
        config = await self._threshold_repository.set_thresholds(
            daily_threshold_usd=daily_threshold,
            monthly_threshold_usd=monthly_threshold,
            updated_by="grpc_client",
        )

        # Update in-memory budget monitor
        if daily_threshold is not None:
            self._budget_monitor.update_thresholds(daily_threshold_usd=float(daily_threshold))
        if monthly_threshold is not None:
            self._budget_monitor.update_thresholds(monthly_threshold_usd=float(monthly_threshold))

        logger.info(
            "Budget thresholds updated",
            daily_threshold_usd=str(config.daily_threshold_usd),
            monthly_threshold_usd=str(config.monthly_threshold_usd),
        )

        return platform_cost_pb2.ConfigureBudgetThresholdResponse(
            daily_threshold_usd=str(config.daily_threshold_usd),
            monthly_threshold_usd=str(config.monthly_threshold_usd),
            message="Thresholds updated successfully",
            updated_at=datetime.now(UTC).isoformat(),
        )
