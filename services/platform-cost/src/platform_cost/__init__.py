"""Platform Cost Service - Unified cost aggregation for Farmer Power Platform.

This service receives cost events from other services (ai-model, etc.) via DAPR pub/sub,
aggregates costs by time window, and provides query APIs for cost visibility.

Architecture (ADR-016):
- Subscribes to platform.cost.recorded events from all services
- Aggregates costs by service, model, time window (daily/monthly)
- Provides gRPC UnifiedCostService for cost queries and budget checks
- Supports budget thresholds with alerting

Story 13.2: Service scaffold with FastAPI + DAPR + gRPC.
"""

__version__ = "0.1.0"
