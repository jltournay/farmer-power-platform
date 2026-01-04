"""gRPC CostService implementation.

This module implements the CostService gRPC API for LLM cost observability.
It is consumed by Epic 9 (Platform Admin Dashboard) for cost monitoring.

Story 0.75.5: OpenRouter LLM Gateway with Cost Observability
"""

from datetime import UTC, datetime

import grpc
import structlog
from ai_model.infrastructure.repositories import LlmCostEventRepository
from ai_model.llm.budget_monitor import BudgetMonitor
from fp_proto.ai_model.v1 import ai_model_pb2, ai_model_pb2_grpc
from google.protobuf import empty_pb2, timestamp_pb2

logger = structlog.get_logger(__name__)


def _datetime_to_timestamp(dt: datetime) -> timestamp_pb2.Timestamp:
    """Convert datetime to protobuf Timestamp."""
    ts = timestamp_pb2.Timestamp()
    ts.FromDatetime(dt)
    return ts


def _timestamp_to_date(ts: timestamp_pb2.Timestamp) -> datetime:
    """Convert protobuf Timestamp to datetime."""
    return ts.ToDatetime().replace(tzinfo=UTC)


class CostServiceServicer(ai_model_pb2_grpc.CostServiceServicer):
    """gRPC CostService implementation.

    Provides cost observability APIs:
    - Daily cost summaries
    - Current day cost tracking
    - Cost breakdown by agent type and model
    - Cost alerts and threshold configuration
    """

    def __init__(
        self,
        repository: LlmCostEventRepository,
        budget_monitor: BudgetMonitor,
    ) -> None:
        """Initialize the CostService.

        Args:
            repository: Repository for cost event persistence.
            budget_monitor: Budget monitor for threshold tracking.
        """
        self._repository = repository
        self._budget_monitor = budget_monitor
        logger.info("CostService initialized")

    async def GetDailyCostSummary(
        self,
        request: ai_model_pb2.DateRangeRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.DailyCostSummaryResponse:
        """Get daily cost summaries for a date range.

        Args:
            request: DateRangeRequest with start_date and end_date.
            context: gRPC context.

        Returns:
            DailyCostSummaryResponse with daily cost breakdowns.
        """
        try:
            start_date = _timestamp_to_date(request.start_date).date()
            end_date = _timestamp_to_date(request.end_date).date()

            summaries = await self._repository.get_daily_summaries(start_date, end_date)

            daily_costs = []
            for summary in summaries:
                daily_costs.append(
                    ai_model_pb2.DailyCost(
                        date=_datetime_to_timestamp(summary.date),
                        total_cost_usd=str(summary.total_cost_usd),
                        total_requests=summary.total_requests,
                        total_tokens_in=summary.total_tokens_in,
                        total_tokens_out=summary.total_tokens_out,
                        success_count=summary.success_count,
                        failure_count=summary.failure_count,
                    )
                )

            logger.debug(
                "GetDailyCostSummary completed",
                start_date=str(start_date),
                end_date=str(end_date),
                day_count=len(daily_costs),
            )

            return ai_model_pb2.DailyCostSummaryResponse(daily_costs=daily_costs)

        except Exception as e:
            logger.error("GetDailyCostSummary failed", error=str(e))
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            raise  # For type checker; abort() raises

    async def GetCurrentDayCost(
        self,
        request: empty_pb2.Empty,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.CostSummaryResponse:
        """Get current day's running cost total.

        Args:
            request: Empty request.
            context: gRPC context.

        Returns:
            CostSummaryResponse with current day totals.
        """
        try:
            summary = await self._repository.get_current_day_cost()

            logger.debug(
                "GetCurrentDayCost completed",
                total_cost_usd=str(summary.total_cost_usd),
                total_requests=summary.total_requests,
            )

            return ai_model_pb2.CostSummaryResponse(
                total_cost_usd=str(summary.total_cost_usd),
                total_requests=summary.total_requests,
                total_tokens_in=summary.total_tokens_in,
                total_tokens_out=summary.total_tokens_out,
            )

        except Exception as e:
            logger.error("GetCurrentDayCost failed", error=str(e))
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            raise

    async def GetCostByAgentType(
        self,
        request: ai_model_pb2.DateRangeRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.CostByAgentTypeResponse:
        """Get cost breakdown by agent type.

        Args:
            request: DateRangeRequest with start_date and end_date.
            context: gRPC context.

        Returns:
            CostByAgentTypeResponse with costs grouped by agent type.
        """
        try:
            start_date = _timestamp_to_date(request.start_date).date()
            end_date = _timestamp_to_date(request.end_date).date()

            costs = await self._repository.get_cost_by_agent_type(start_date, end_date)

            agent_type_costs = [
                ai_model_pb2.AgentTypeCostEntry(
                    agent_type=c.agent_type,
                    total_cost_usd=str(c.total_cost_usd),
                    total_requests=c.total_requests,
                    total_tokens=c.total_tokens,
                )
                for c in costs
            ]

            logger.debug(
                "GetCostByAgentType completed",
                start_date=str(start_date),
                end_date=str(end_date),
                agent_type_count=len(agent_type_costs),
            )

            return ai_model_pb2.CostByAgentTypeResponse(agent_type_costs=agent_type_costs)

        except Exception as e:
            logger.error("GetCostByAgentType failed", error=str(e))
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            raise

    async def GetCostByModel(
        self,
        request: ai_model_pb2.DateRangeRequest,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.CostByModelResponse:
        """Get cost breakdown by model.

        Args:
            request: DateRangeRequest with start_date and end_date.
            context: gRPC context.

        Returns:
            CostByModelResponse with costs grouped by model.
        """
        try:
            start_date = _timestamp_to_date(request.start_date).date()
            end_date = _timestamp_to_date(request.end_date).date()

            costs = await self._repository.get_cost_by_model(start_date, end_date)

            model_costs = [
                ai_model_pb2.ModelCostEntry(
                    model=c.model,
                    total_cost_usd=str(c.total_cost_usd),
                    total_requests=c.total_requests,
                    total_tokens=c.total_tokens,
                )
                for c in costs
            ]

            logger.debug(
                "GetCostByModel completed",
                start_date=str(start_date),
                end_date=str(end_date),
                model_count=len(model_costs),
            )

            return ai_model_pb2.CostByModelResponse(model_costs=model_costs)

        except Exception as e:
            logger.error("GetCostByModel failed", error=str(e))
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            raise

    async def GetCostAlerts(
        self,
        request: empty_pb2.Empty,
        context: grpc.aio.ServicerContext,
    ) -> ai_model_pb2.CostAlertsResponse:
        """Get active cost alerts and budget status.

        Args:
            request: Empty request.
            context: gRPC context.

        Returns:
            CostAlertsResponse with alerts and current thresholds.
        """
        try:
            status = self._budget_monitor.get_status()

            logger.debug(
                "GetCostAlerts completed",
                daily_alert_triggered=status["daily_alert_triggered"],
                monthly_alert_triggered=status["monthly_alert_triggered"],
            )

            return ai_model_pb2.CostAlertsResponse(
                alerts=[],  # Historical alerts would be fetched from repository
                daily_threshold_usd=status["daily_threshold_usd"],
                daily_total_usd=status["daily_total_usd"],
                daily_alert_triggered=status["daily_alert_triggered"],
                monthly_threshold_usd=status["monthly_threshold_usd"],
                monthly_total_usd=status["monthly_total_usd"],
                monthly_alert_triggered=status["monthly_alert_triggered"],
            )

        except Exception as e:
            logger.error("GetCostAlerts failed", error=str(e))
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            raise

    async def ConfigureCostThreshold(
        self,
        request: ai_model_pb2.ThresholdConfigRequest,
        context: grpc.aio.ServicerContext,
    ) -> empty_pb2.Empty:
        """Configure cost thresholds at runtime.

        Args:
            request: ThresholdConfigRequest with new thresholds.
            context: gRPC context.

        Returns:
            Empty response on success.
        """
        try:
            # -1 means no change
            daily = None if request.daily_threshold_usd == -1 else request.daily_threshold_usd
            monthly = None if request.monthly_threshold_usd == -1 else request.monthly_threshold_usd

            self._budget_monitor.update_thresholds(
                daily_threshold_usd=daily,
                monthly_threshold_usd=monthly,
            )

            logger.info(
                "Cost thresholds configured",
                daily_threshold_usd=daily,
                monthly_threshold_usd=monthly,
            )

            return empty_pb2.Empty()

        except Exception as e:
            logger.error("ConfigureCostThreshold failed", error=str(e))
            await context.abort(grpc.StatusCode.INTERNAL, str(e))
            raise
