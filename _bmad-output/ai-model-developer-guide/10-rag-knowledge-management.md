# 10. RAG Knowledge Management

## Knowledge Document Lifecycle

Knowledge documents in Pinecone follow a versioned lifecycle to ensure safe updates and rollback capability:

```
┌───────────────────────────────────────────────────────────────────┐
│                   DOCUMENT LIFECYCLE                               │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│   New Document ──► DRAFT                                          │
│                      │                                            │
│                      │ Review + Approval                          │
│                      ▼                                            │
│                   STAGED ◄──────────────────────┐                │
│                      │                           │                │
│                      │ A/B Test (optional)       │                │
│                      ▼                           │                │
│                   ACTIVE ────────────────────────┤                │
│                      │                           │ Rollback       │
│                      │ Superseded by new version │                │
│                      ▼                           │                │
│                   ARCHIVED ──────────────────────┘                │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

**Document States:**

| State | Description | Queryable |
|-------|-------------|-----------|
| `draft` | Being edited, not yet reviewed | No |
| `staged` | Approved, ready for A/B test or promotion | A/B test only |
| `active` | Live in production | Yes |
| `archived` | Replaced by newer version, kept for rollback | Rollback only |

## Versioning Schema

```yaml
# knowledge/documents/disease/fungal-blister-blight.yaml
document:
  id: "disease-fungal-blister-blight"
  version: "2.1.0"
  status: active
  domain: "tea_diseases"

  metadata:
    title: "Blister Blight (Exobasidium vexans)"
    author: "agronomist_team"
    created_at: "2024-01-10"
    updated_at: "2024-06-15"
    review_status: approved
    reviewer: "dr_ochieng"

  versioning:
    previous_version: "2.0.0"
    changelog:
      - "2.1.0: Added regional severity variations for highland vs lowland"
      - "2.0.0: Updated treatment recommendations based on 2024 research"
      - "1.0.0: Initial version"
    rollback_available: true

  content:
    description: |
      Blister blight is a fungal disease affecting tea plants,
      caused by Exobasidium vexans...

    symptoms:
      - "Pale, translucent spots on young leaves"
      - "Blisters that turn white and velvety"
      - "Leaf curling and distortion"

    conditions:
      - "High humidity (>80%)"
      - "Cool temperatures (15-20°C)"
      - "Frequent rainfall"

    recommendations:
      immediate:
        - "Remove and destroy infected leaves"
        - "Improve air circulation by pruning"
      preventive:
        - "Apply copper-based fungicide before rainy season"
        - "Maintain proper spacing between plants"

  embedding_config:
    chunk_strategy: section  # Embed each section separately
    include_metadata: true   # Include metadata in embeddings
```

## Pinecone Namespace Strategy

Use Pinecone namespaces for version isolation:

```python
class KnowledgeVersionManager:
    """Manage knowledge versions in Pinecone."""

    def __init__(self, pinecone_index):
        self.index = pinecone_index

    def get_namespace(self, version: str, status: str) -> str:
        """
        Namespace naming convention:
        - Active: knowledge-v{version}
        - Staged: knowledge-v{version}-staged
        - Archived: knowledge-v{version}-archived
        """
        if status == "active":
            return f"knowledge-v{version}"
        return f"knowledge-v{version}-{status}"

    async def promote_staged_to_active(
        self,
        document_id: str,
        new_version: str,
        old_version: str
    ):
        """
        Promote staged document to active, archive old version.
        """
        # 1. Copy staged vectors to active namespace
        staged_ns = self.get_namespace(new_version, "staged")
        active_ns = self.get_namespace(new_version, "active")

        await self._copy_vectors(
            source_ns=staged_ns,
            target_ns=active_ns,
            doc_id_prefix=document_id
        )

        # 2. Archive old active version
        old_active_ns = self.get_namespace(old_version, "active")
        old_archived_ns = self.get_namespace(old_version, "archived")

        await self._move_vectors(
            source_ns=old_active_ns,
            target_ns=old_archived_ns,
            doc_id_prefix=document_id
        )

        # 3. Update routing config
        await self._update_routing(document_id, new_version)

    async def rollback(self, document_id: str, to_version: str):
        """
        Rollback to a previous archived version.
        """
        # Restore archived version to active
        archived_ns = self.get_namespace(to_version, "archived")
        active_ns = self.get_namespace(to_version, "active")

        await self._copy_vectors(
            source_ns=archived_ns,
            target_ns=active_ns,
            doc_id_prefix=document_id
        )

        # Update routing
        await self._update_routing(document_id, to_version)

        logger.info(
            "Knowledge rollback completed",
            document_id=document_id,
            rolled_back_to=to_version
        )
```

## Knowledge Update Workflow

```
┌───────────────────────────────────────────────────────────────────┐
│                   KNOWLEDGE UPDATE WORKFLOW                        │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. AUTHOR                                                        │
│     └─→ Create/update document in Git                            │
│     └─→ farmer-cli knowledge validate --doc disease/xxx.yaml     │
│     └─→ Commit with status: draft                                │
│                                                                   │
│  2. REVIEW                                                        │
│     └─→ Agronomist/domain expert reviews                         │
│     └─→ farmer-cli knowledge review --doc disease/xxx.yaml       │
│     └─→ Approve or request changes                               │
│                                                                   │
│  3. STAGE                                                         │
│     └─→ farmer-cli knowledge stage --doc disease/xxx.yaml        │
│     └─→ Embed and upload to staged namespace                     │
│     └─→ Run integration tests against staged version             │
│                                                                   │
│  4. TEST (Optional)                                               │
│     └─→ Configure A/B test with 10-20% traffic                   │
│     └─→ Monitor accuracy metrics                                 │
│     └─→ Wait for statistical significance                        │
│                                                                   │
│  5. PROMOTE                                                       │
│     └─→ farmer-cli knowledge promote --doc disease/xxx.yaml      │
│     └─→ Archive previous version                                 │
│     └─→ Route all traffic to new version                         │
│                                                                   │
│  6. MONITOR                                                       │
│     └─→ Watch for accuracy regressions                           │
│     └─→ If issues: farmer-cli knowledge rollback --to v1.0.0     │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

## CLI Commands for Knowledge Management

```bash
# Validate document structure and content
farmer-cli knowledge validate --doc knowledge/disease/fungal-xxx.yaml

# Stage a document (embed and upload to staged namespace)
farmer-cli knowledge stage --doc knowledge/disease/fungal-xxx.yaml

# Start A/B test with staged version
farmer-cli knowledge ab-test start \
  --doc knowledge/disease/fungal-xxx.yaml \
  --traffic 20 \
  --duration 7d

# Check A/B test status
farmer-cli knowledge ab-test status --doc knowledge/disease/fungal-xxx.yaml

# Promote staged to active
farmer-cli knowledge promote --doc knowledge/disease/fungal-xxx.yaml

# Rollback to previous version
farmer-cli knowledge rollback \
  --doc knowledge/disease/fungal-xxx.yaml \
  --to-version 1.0.0

# List all versions of a document
farmer-cli knowledge versions --doc knowledge/disease/fungal-xxx.yaml

# Sync all knowledge to Pinecone (for initial setup or recovery)
farmer-cli knowledge sync --domain tea_diseases
```

## Knowledge Query Routing

The RAG engine routes queries to the appropriate knowledge version:

```python
class RAGEngine:
    """RAG engine with version-aware querying."""

    async def query(
        self,
        query: str,
        domains: list[str],
        knowledge_version: str = None,  # For A/B testing
        farmer_id: str = None
    ) -> dict:
        """
        Query knowledge base with version routing.
        """
        # Determine version to use
        if knowledge_version:
            # Explicit version (from A/B test)
            version = knowledge_version
        else:
            # Use active version
            version = await self._get_active_version(domains)

        # Build namespace
        namespace = f"knowledge-v{version}"

        # Embed query
        query_embedding = await self.embedder.embed(query)

        # Query Pinecone
        results = await self.pinecone_index.query(
            vector=query_embedding,
            namespace=namespace,
            top_k=5,
            include_metadata=True,
            filter={"domain": {"$in": domains}}
        )

        # Format results
        context_chunks = [
            {
                "content": r.metadata["content"],
                "source": r.metadata["document_id"],
                "version": r.metadata["version"],
                "relevance": r.score
            }
            for r in results.matches
        ]

        return {
            "context": context_chunks,
            "version_used": version,
            "namespace": namespace
        }
```

## Knowledge Quality Metrics

Track knowledge effectiveness:

```python
# Metrics to capture for knowledge quality
knowledge_metrics = {
    "rag_retrieval_relevance": Histogram(
        "rag_retrieval_relevance_score",
        "Relevance scores of retrieved chunks",
        ["domain", "version"],
        buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0]
    ),

    "rag_context_usage": Counter(
        "rag_context_usage_total",
        "How often each document is retrieved",
        ["document_id", "version"]
    ),

    "diagnosis_with_rag_accuracy": Gauge(
        "diagnosis_with_rag_accuracy",
        "Accuracy of diagnoses using specific knowledge version",
        ["domain", "version"]
    ),

    "knowledge_staleness": Gauge(
        "knowledge_staleness_days",
        "Days since knowledge document was last updated",
        ["document_id"]
    )
}
```

**Grafana Queries:**

```promql
# Retrieval relevance by version (are newer versions better?)
histogram_quantile(0.5,
  sum(rate(rag_retrieval_relevance_score_bucket[1h]))
  by (le, version)
)

# Most frequently used documents
topk(10,
  sum(rate(rag_context_usage_total[24h])) by (document_id)
)

# Documents that may need updating
knowledge_staleness_days > 180

# Accuracy comparison between versions
diagnosis_with_rag_accuracy{version="2.0.0"}
  - diagnosis_with_rag_accuracy{version="1.0.0"}
```

## Knowledge Document Best Practices

**DO:**
- Use clear, structured content with sections
- Include specific symptoms, conditions, and recommendations
- Add regional variations where applicable
- Version all changes with meaningful changelogs
- Test with A/B before major updates

**DON'T:**
- Mix multiple diseases/conditions in one document
- Use overly technical language (farmers read these via LLM)
- Remove information without archiving first
- Skip the staging/review process for "small" changes

**Document Structure Template:**

```markdown
# {Condition Name}

# Overview
Brief description of the condition.

# Identification
## Visual Symptoms
- Symptom 1
- Symptom 2

## Affected Plant Parts
- Leaves, stems, roots, etc.

# Conditions Favoring Development
- Environmental factors
- Seasonal patterns
- Regional variations

# Severity Assessment
| Level | Indicators | Urgency |
|-------|------------|---------|
| Low | ... | Monitor |
| Moderate | ... | Treat within 1 week |
| High | ... | Immediate action |

# Recommendations
## Immediate Actions
1. Action 1
2. Action 2

## Preventive Measures
1. Measure 1
2. Measure 2

## Product Recommendations
- Product A: For severe cases
- Product B: For prevention

# Regional Notes
## Highland (>1500m)
- Specific considerations

## Lowland (<1500m)
- Specific considerations
```

---

_Last Updated: 2025-12-22_
_Maintainer: Platform AI Team_