# Analytics Architecture

## Cross-Model Data Access Strategy

The platform uses different strategies for different consumers, respecting model boundaries while enabling efficient data access.

### Consumer-Specific Strategies

| Consumer | Strategy | Rationale |
|----------|----------|-----------|
| **AI Agents** | MCP aggregation | Single farmer queries, parallel calls, production-optimized |
| **Admin Dashboard** | Event-driven materialized views | Pre-joined data, fast reads, uses existing Dapr |
| **Future Analytics** | Migrate to ClickHouse when needed | Don't over-engineer MVP |

### AI Agent Queries (Production)

AI agents query for **one farmer at a time** using parallel MCP calls:

```
Action Plan Generator needs farmer context:
  → Plantation MCP: get_farmer_context("WM-4521")      ─┐
  → Knowledge MCP: get_farmer_analyses("WM-4521")      ─┼─ Parallel
  → Collection MCP: get_farmer_documents("WM-4521")    ─┘

3 parallel MCP calls, ~100ms total, no joins needed
```

**Why this works:** AI agents have predictable query patterns (farmer_id → get everything about this farmer). No complex cross-model joins needed.

### Admin Dashboard (Analytics Read Model)

For dashboards and reports requiring cross-model data, use event-driven materialized views via Dapr pub/sub:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ANALYTICS READ MODEL                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Dapr Subscriptions:                                                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │ collection.     │  │ knowledge.      │  │ action_plan.    │         │
│  │ document_stored │  │ diagnosis_      │  │ created         │         │
│  │                 │  │ complete        │  │                 │         │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘         │
│           │                    │                    │                   │
│           └────────────────────┼────────────────────┘                   │
│                                ▼                                        │
│           ┌─────────────────────────────────────┐                       │
│           │      REPORTING SERVICE              │                       │
│           │                                     │                       │
│           │  • Subscribes to domain events      │                       │
│           │  • Updates denormalized views       │                       │
│           │  • Pre-joins farmer + events +      │                       │
│           │    diagnoses + action plans         │                       │
│           │  • Aggregates by factory, region    │                       │
│           └─────────────────────────────────────┘                       │
│                                │                                        │
│                                ▼                                        │
│           ┌─────────────────────────────────────┐                       │
│           │   farmer_dashboard_view (MongoDB)   │                       │
│           │                                     │                       │
│           │   {                                 │                       │
│           │     farmer_id: "WM-4521",           │                       │
│           │     region: "nyeri-highland",       │                       │
│           │     factory: "F001",                │                       │
│           │     recent_deliveries: [...],       │                       │
│           │     recent_diagnoses: [...],        │                       │
│           │     action_plans: [...],            │                       │
│           │     performance_30d: {...},         │                       │
│           │     last_updated: "2025-12-16T10:00:00Z"                    │
│           │   }                                 │                       │
│           └─────────────────────────────────────┘                       │
│                                │                                        │
│                                ▼                                        │
│           ┌─────────────────────────────────────┐                       │
│           │         ADMIN DASHBOARD             │                       │
│           │   Fast queries, no joins needed     │                       │
│           └─────────────────────────────────────┘                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Materialized View Schema

```yaml
# MongoDB: farmer_dashboard_view collection
farmer_dashboard_view:
  _id: string                    # farmer_id
  farmer_id: string
  name: string
  region_id: string
  factory_id: string

  # Denormalized from Collection Model
  recent_deliveries:
    - date: datetime
      grade: string
      quality_score: number
      issues: string[]
  delivery_count_30d: number

  # Denormalized from Knowledge Model
  recent_diagnoses:
    - date: datetime
      type: string
      condition: string
      severity: string
      confidence: number
  active_issues_count: number

  # Denormalized from Action Plan Model
  recent_action_plans:
    - week: string
      priority_actions: number
      delivery_status: string

  # Aggregated metrics
  performance_30d:
    avg_grade: number
    improvement_trend: string    # "improving" | "stable" | "declining"
    grade_distribution: object

  last_updated: datetime
```

### Why NOT Other Options

| Option | Why Not |
|--------|---------|
| **Shared MongoDB** | Breaks model isolation. Schema changes in one model could break others. MongoDB `$lookup` is slow at scale. |
| **Dedicated Analytics DB (ClickHouse)** | Overkill for MVP. Not doing OLAP queries yet. Can migrate later if needed. |
| **MCP for dashboards** | N+1 query problem for lists. Fine for single-farmer views, slow for "all farmers in region" reports. |

---
