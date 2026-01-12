# Platform Cost Service

Unified cost aggregation service for the Farmer Power Platform.

## Overview

The Platform Cost Service receives cost events from other services (ai-model, etc.) via DAPR pub/sub, aggregates costs by time window, and provides query APIs for cost visibility. It implements ADR-016 (Unified Cost Model).

## Architecture

```
┌─────────────────┐    DAPR pub/sub     ┌───────────────────┐
│   ai-model      │ ─────────────────── │  platform-cost    │
│                 │  platform.cost.*    │                   │
└─────────────────┘                     │  ┌─────────────┐  │
                                        │  │ Budget      │  │
┌─────────────────┐                     │  │ Monitor     │  │
│ future services │ ─────────────────── │  └─────────────┘  │
└─────────────────┘                     │        │          │
                                        │        ▼          │
                                        │  ┌─────────────┐  │
                                        │  │  MongoDB    │  │
                                        │  │ (TTL index) │  │
                                        │  └─────────────┘  │
                                        └───────────────────┘
```

## Ports

| Port | Purpose |
|------|---------|
| 8000 | FastAPI health endpoints (`/health`, `/ready`) |
| 50054 | gRPC UnifiedCostService (via DAPR sidecar) |

## Configuration

Environment variables (prefix: `PLATFORM_COST_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGODB_URI` | mongodb://localhost:27017 | MongoDB connection string |
| `MONGODB_DATABASE` | platform_cost | Database name |
| `DAPR_PUBSUB_NAME` | pubsub | DAPR pub/sub component |
| `COST_EVENT_TOPIC` | platform.cost.recorded | Topic to subscribe |
| `BUDGET_DAILY_THRESHOLD_USD` | 10.0 | Daily cost threshold |
| `BUDGET_MONTHLY_THRESHOLD_USD` | 100.0 | Monthly cost threshold |
| `COST_EVENT_RETENTION_DAYS` | 90 | TTL for cost events |
| `GRPC_PORT` | 50054 | gRPC server port |

## Development

```bash
# Install dependencies
cd services/platform-cost
poetry install

# Run locally
poetry run python -m uvicorn platform_cost.main:app --reload

# Run tests
poetry run pytest
```

## Docker Build

```bash
# From repository root
docker build -f services/platform-cost/Dockerfile -t farmer-power/platform-cost .
```

## Stories

- Story 13.2: Service scaffold (FastAPI + DAPR + gRPC)
- Story 13.3: Cost Repository and Budget Monitor
- Story 13.4: gRPC UnifiedCostService
- Story 13.5: DAPR Cost Event Subscription
- Story 13.6: AI Model Refactor (publish costs via DAPR)
- Story 13.7: E2E Integration Tests

## References

- [ADR-016: Unified Cost Model](_bmad-output/architecture/adr/ADR-016-unified-cost-model.md)
- [ADR-011: Service Architecture](_bmad-output/architecture/adr/ADR-011-service-architecture-grpc-fastapi-dapr.md)
