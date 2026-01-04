# RAG Knowledge Versioning

To prevent knowledge updates from degrading prompt effectiveness, the RAG system uses versioned namespaces with A/B testing.

## Document Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    RAG KNOWLEDGE VERSIONING                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  DOCUMENT STATES                                                        │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
│  │   DRAFT     │───▶│   STAGED    │───▶│   ACTIVE    │                 │
│  │             │    │             │    │             │                 │
│  │ Agronomist  │    │ Embeddings  │    │ Production  │                 │
│  │ edits       │    │ generated,  │    │ queries use │                 │
│  │             │    │ A/B ready   │    │ this version│                 │
│  └─────────────┘    └─────────────┘    └──────┬──────┘                 │
│                                               │                         │
│                                               ▼                         │
│                                        ┌─────────────┐                 │
│                                        │  ARCHIVED   │                 │
│                                        │  (rollback) │                 │
│                                        └─────────────┘                 │
│                                                                         │
│  PINECONE NAMESPACE STRATEGY                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  knowledge-v12 (ACTIVE)  ◀── 90% of production queries          │   │
│  │  knowledge-v13 (STAGED)  ◀── 10% A/B test queries               │   │
│  │  knowledge-v11 (ARCHIVED) ◀── Rollback target if needed         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Document Schema

```yaml
# MongoDB: rag_documents collection
rag_document:
  _id: ObjectId
  document_id: string            # Stable ID across versions
  version: int                   # Incrementing version number

  # Content
  title: string
  domain: string                 # plant_diseases, weather_patterns, etc.
  content: string                # Full document text
  content_hash: string           # SHA256 for change detection

  # Embedding reference
  pinecone_namespace: string     # knowledge-v{version}
  pinecone_ids: string[]         # Vector IDs in Pinecone

  # Lifecycle
  status: enum                   # draft, staged, active, archived
  created_at: datetime
  created_by: string             # Agronomist ID
  activated_at: datetime?
  archived_at: datetime?

  # Change tracking
  change_summary: string?        # What changed from previous version
  previous_version_id: ObjectId?
```

## A/B Testing Configuration

```yaml
# ai-model/config/rag-ab-test.yaml
ab_test:
  enabled: true
  staged_namespace: "knowledge-v13"
  active_namespace: "knowledge-v12"

  traffic_split:
    staged: 10                    # 10% of queries use staged
    active: 90                    # 90% use production

  evaluation:
    duration_days: 7
    metrics:
      - diagnosis_confidence_avg
      - agronomist_correction_rate
      - relevance_score_avg

  promotion_criteria:
    min_queries: 500
    confidence_delta: ">= -0.02"  # Can't drop more than 2%
    correction_rate_delta: "<= 0.05"

  auto_promote: false             # Require manual approval
  auto_rollback: true             # Auto rollback if metrics degrade >10%
```

## Rollback Procedure

| Trigger | Action | Duration |
|---------|--------|----------|
| **Manual** | Admin initiates rollback via UI | Immediate |
| **Auto** | Metrics degrade >10% during A/B | Immediate |
| **Mechanism** | Switch active_namespace pointer | <1 second |
| **Retention** | Keep last 5 versions for rollback | 90 days |

## Version Lifecycle Flow

```
Agronomist Updates Document
         │
         ▼
┌─────────────────┐
│  1. Save Draft  │ → MongoDB (status: draft)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. Generate    │ → Pinecone (new namespace: knowledge-v13)
│     Embeddings  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  3. Stage for   │ → MongoDB (status: staged)
│     A/B Test    │ → 10% traffic routes to v13
└────────┬────────┘
         │
         ▼ (after 7 days + metrics OK)
┌─────────────────┐
│  4. Promote     │ → MongoDB (status: active)
│     to Active   │ → 100% traffic routes to v13
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  5. Archive     │ → MongoDB (v12 status: archived)
│     Previous    │ → Keep for rollback
└─────────────────┘
```
