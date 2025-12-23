# CQRS Architecture Pattern

## Overview

The platform implements an **implicit CQRS (Command Query Responsibility Segregation)** pattern. Rather than introducing explicit CQRS infrastructure, we leverage existing MongoDB capabilities and event-driven architecture to separate read and write concerns.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CQRS IMPLEMENTATION                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  COMMAND SIDE (Writes)                 QUERY SIDE (Reads)                   │
│  ┌─────────────────────┐               ┌─────────────────────┐              │
│  │  Ingestion APIs     │               │   MCP Servers       │              │
│  │  - /api/v1/ingest/* │               │   (stateless)       │              │
│  │  - Event processors │               │   - get_farmer_*    │              │
│  │  - Action plan gen  │               │   - search_*        │              │
│  └──────────┬──────────┘               └──────────┬──────────┘              │
│             │                                     │                         │
│             ▼                                     ▼                         │
│  ┌─────────────────────┐               ┌─────────────────────┐              │
│  │   MongoDB PRIMARY   │  ─────────▶   │   MongoDB READ      │              │
│  │                     │  replication  │   REPLICAS          │              │
│  │  Handles all writes │               │   Handles all reads │              │
│  └─────────────────────┘               └─────────────────────┘              │
│             │                                     ▲                         │
│             │ events                              │                         │
│             ▼                                     │                         │
│  ┌─────────────────────┐               ┌─────────────────────┐              │
│  │   Dapr Pub/Sub      │  ─────────▶   │   Materialized      │              │
│  │   Event Bus         │               │   Views             │              │
│  │                     │               │   (farmer_dashboard │              │
│  │  - document_stored  │               │    _view, etc.)     │              │
│  │  - diagnosis_done   │               │                     │              │
│  │  - action_plan_sent │               │   Optimized for     │              │
│  └─────────────────────┘               │   specific queries  │              │
│                                        └─────────────────────┘              │
│                                                   │                         │
│                                                   ▼                         │
│                                        ┌─────────────────────┐              │
│                                        │  Admin Dashboard    │              │
│                                        │  Reporting APIs     │              │
│                                        └─────────────────────┘              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Read/Write Separation Layers

| Layer | Write Path | Read Path |
|-------|------------|-----------|
| **API Gateway** | Ingestion endpoints (`POST /ingest/*`) | MCP Server methods (`get_*`, `search_*`) |
| **Database** | MongoDB Primary (single writer) | MongoDB Read Replicas (multiple readers) |
| **Analytics** | Domain events via Dapr | Materialized views (pre-computed) |
| **Connection Strings** | `mongodb://primary:27017` | `mongodb://replica1,replica2:27017?readPreference=secondary` |

## MongoDB Read Replica Configuration

```yaml
# Each model's read path configuration
mongodb_read_config:
  readPreference: secondary        # Route reads to replicas
  readPreferenceTags:
    - region: same-az              # Prefer same availability zone
  maxStalenessSeconds: 90          # Accept up to 90s staleness for reads

# Write path always uses primary
mongodb_write_config:
  writeConcern:
    w: majority                    # Wait for majority acknowledgment
    j: true                        # Journal write before acknowledging
```

## Query Patterns by Consumer

| Consumer | Read Path | Write Path | Consistency |
|----------|-----------|------------|-------------|
| **AI Agents (MCP)** | Read replicas | N/A (read-only) | Eventually consistent (90s max) |
| **Admin Dashboard** | Materialized views | N/A (read-only) | Event-driven (~1s delay) |
| **Ingestion APIs** | N/A | Primary only | Strongly consistent |
| **Action Plan Generator** | Read replicas | Primary (plans) | Read: eventual, Write: strong |

## Why Implicit CQRS (Not Explicit)

| Explicit CQRS | Implicit CQRS (Our Approach) |
|---------------|------------------------------|
| Separate read/write databases | MongoDB replicas (same data, different instances) |
| Event sourcing for write model | Standard document updates + Dapr events |
| Dedicated projection services | Lightweight event handlers update materialized views |
| Complex eventual consistency | Simple replication lag (< 100ms typical) |
| High operational overhead | Minimal ops - MongoDB handles replication |

**Our approach gives us:**
- ✅ Read/write load separation
- ✅ Independent scaling of reads vs writes
- ✅ Eventual consistency where acceptable
- ✅ Strong consistency where required (primary reads when needed)
- ✅ No additional infrastructure complexity

## When to Evolve to Explicit CQRS

Consider formal CQRS migration if:

| Trigger | Threshold | Response |
|---------|-----------|----------|
| Read replica lag exceeds SLA | > 500ms consistently | Add more replicas or consider ClickHouse |
| Complex read models needed | > 5 materialized views | Consider dedicated projection service |
| Write throughput bottleneck | > 10,000 writes/sec | Consider event sourcing with write-optimized store |
| Cross-region requirements | Multiple continents | Consider geo-distributed CQRS with conflict resolution |

**Current architecture supports:** ~1,000 writes/sec, ~10,000 reads/sec, < 100ms replica lag.

---
