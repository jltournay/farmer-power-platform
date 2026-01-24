# Story 9.10a: Platform Cost BFF REST API

As a **frontend developer**,
I want **REST API endpoints in the BFF for platform cost monitoring**,
So that **the Platform Cost Dashboard UI can display cost summaries, breakdowns, trends, and configure budget thresholds**.

## Acceptance Criteria

**AC 9.10a.1: Cost Summary Endpoint**

**Given** the BFF is running
**When** I call the cost summary endpoint
**Then** the following operation is available:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/admin/costs/summary` | Get total costs with type breakdown for date range |

**And** it accepts query parameters: `start_date` (ISO YYYY-MM-DD, required), `end_date` (ISO YYYY-MM-DD, required)
**And** the response includes: total_cost_usd, total_requests, by_type[] (cost_type, total_cost_usd, total_quantity, request_count, percentage), period_start, period_end
**And** response is cached for 5 minutes in BFF

**AC 9.10a.2: Daily Cost Trend Endpoint**

**Given** the BFF is running
**When** I call the daily trend endpoint
**Then** the following operation is available:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/admin/costs/trend/daily` | Get daily costs for stacked chart |

**And** it accepts query parameters: `start_date` (optional), `end_date` (optional), `days` (optional, default 30)
**And** the response includes: entries[] (date, total_cost_usd, llm_cost_usd, document_cost_usd, embedding_cost_usd), data_available_from

**AC 9.10a.3: Current Day Cost Endpoint**

**Given** the BFF is running
**When** I call the current day cost endpoint
**Then** the following operation is available:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/admin/costs/today` | Get real-time today's running cost |

**And** the response includes: date, total_cost_usd, by_type (map of cost_type to cost_usd), updated_at
**And** response is NOT cached (real-time data)

**AC 9.10a.4: LLM Cost Breakdown Endpoints**

**Given** the BFF is running
**When** I call the LLM breakdown endpoints
**Then** the following operations are available:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/admin/costs/llm/by-agent-type` | LLM cost breakdown by agent type |
| `GET` | `/api/v1/admin/costs/llm/by-model` | LLM cost breakdown by model |

**And** both accept query parameters: `start_date` (optional), `end_date` (optional)
**And** by-agent-type response includes: agent_costs[] (agent_type, cost_usd, request_count, tokens_in, tokens_out, percentage), total_llm_cost_usd
**And** by-model response includes: model_costs[] (model, cost_usd, request_count, tokens_in, tokens_out, percentage), total_llm_cost_usd

**AC 9.10a.5: Document Cost Summary Endpoint**

**Given** the BFF is running
**When** I call the document cost endpoint
**Then** the following operation is available:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/admin/costs/documents` | Document processing cost summary |

**And** it accepts query parameters: `start_date` (required), `end_date` (required)
**And** the response includes: total_cost_usd, total_pages, avg_cost_per_page_usd, document_count, period_start, period_end

**AC 9.10a.6: Embedding Cost by Domain Endpoint**

**Given** the BFF is running
**When** I call the embedding cost endpoint
**Then** the following operation is available:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/admin/costs/embeddings/by-domain` | Embedding costs by knowledge domain |

**And** it accepts query parameters: `start_date` (optional), `end_date` (optional)
**And** the response includes: domain_costs[] (knowledge_domain, cost_usd, tokens_total, texts_count, percentage), total_embedding_cost_usd

**AC 9.10a.7: Budget Status and Configuration Endpoints**

**Given** the BFF is running
**When** I call the budget endpoints
**Then** the following operations are available:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/admin/costs/budget` | Get current budget status |
| `PUT` | `/api/v1/admin/costs/budget` | Update budget thresholds |

**And** GET response includes: daily_threshold_usd, daily_total_usd, daily_remaining_usd, daily_utilization_percent, monthly_threshold_usd, monthly_total_usd, monthly_remaining_usd, monthly_utilization_percent, by_type (map), current_day, current_month
**And** PUT accepts body: daily_threshold_usd (optional), monthly_threshold_usd (optional)
**And** PUT response includes: daily_threshold_usd, monthly_threshold_usd, message, updated_at

**AC 9.10a.8: Pydantic Request/Response Schemas**

**Given** the endpoints are implemented
**Then** all request/response models use Pydantic v2 schemas
**And** schemas are defined in `services/bff/src/bff/api/schemas/admin/cost_schemas.py`
**And** schemas include proper validation (e.g., date format, threshold > 0)

**AC 9.10a.9: Route Registration**

**Given** the cost routes are implemented
**Then** they are registered in the admin router
**And** accessible under the `/api/v1/admin/costs` prefix
**And** protected by admin authentication

## Technical Notes

- **gRPC Client:** Create `PlatformCostClient` in `services/bff/src/bff/infrastructure/clients/platform_cost_client.py` to call UnifiedCostService RPCs
- **DAPR Integration:** All gRPC calls go through DAPR sidecar service invocation (app-id: `platform-cost`)
- **Caching:** `GetCostSummary` response cached 5 minutes; `GetCurrentDayCost` not cached
- **Proto Source of Truth:** All request/response shapes derive from `proto/platform_cost/v1/platform_cost.proto` UnifiedCostService definitions
- **Alert delivery:** Handled by AlertManager via OTEL metrics — BFF does NOT manage alert notifications

### gRPC RPCs Wrapped

| BFF Endpoint | gRPC RPC |
|---|---|
| `GET /costs/summary` | `GetCostSummary` |
| `GET /costs/trend/daily` | `GetDailyCostTrend` |
| `GET /costs/today` | `GetCurrentDayCost` |
| `GET /costs/llm/by-agent-type` | `GetLlmCostByAgentType` |
| `GET /costs/llm/by-model` | `GetLlmCostByModel` |
| `GET /costs/documents` | `GetDocumentCostSummary` |
| `GET /costs/embeddings/by-domain` | `GetEmbeddingCostByDomain` |
| `GET /costs/budget` | `GetBudgetStatus` |
| `PUT /costs/budget` | `ConfigureBudgetThreshold` |

## Dependencies

- Story 9.1a: Platform Admin Application Scaffold
- Story 0.5.6: BFF Service Setup
- Epic 13 / Story 13.4: UnifiedCostService gRPC implementation

## Story Points: 3

---
