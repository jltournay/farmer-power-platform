# 10. RAG Knowledge Management

## Overview

RAG (Retrieval-Augmented Generation) documents are managed through a **gRPC API** exposed by the AI Model service. This enables:

- **Admin UI** for agronomists (non-technical experts) to manage knowledge via web interface
- **CLI** (`farmer-cli rag`) for Ops team automation and bulk operations

> **Architecture Reference:** See `architecture/ai-model-architecture.md` → "RAG Document API" for complete Pydantic models and proto definitions.

## Knowledge Document Lifecycle

Knowledge documents follow a versioned lifecycle to ensure safe updates and rollback capability:

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

## Storage Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         STORAGE ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Admin UI / CLI                                                         │
│       │                                                                 │
│       │ gRPC (RAGDocumentService)                                       │
│       ▼                                                                 │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                        AI MODEL SERVICE                           │  │
│  │                                                                   │  │
│  │  ┌─────────────────┐    ┌─────────────────┐                      │  │
│  │  │  RAGDocument    │    │  Vectorization  │                      │  │
│  │  │  Service        │───▶│  Pipeline       │                      │  │
│  │  └─────────────────┘    └─────────────────┘                      │  │
│  │          │                      │                                 │  │
│  └──────────┼──────────────────────┼─────────────────────────────────┘  │
│             │                      │                                    │
│             ▼                      ▼                                    │
│  ┌─────────────────┐    ┌─────────────────┐                            │
│  │    MongoDB      │    │    Pinecone     │                            │
│  │  (documents)    │    │   (vectors)     │                            │
│  │                 │    │                 │                            │
│  │  • RAGDocument  │    │  • Embeddings   │                            │
│  │  • Metadata     │    │  • Namespaces   │                            │
│  │  • Versions     │    │  • Filters      │                            │
│  └─────────────────┘    └─────────────────┘                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Document Model

RAG documents use the following structure (stored in MongoDB):

```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class RAGDocumentMetadata(BaseModel):
    """Metadata for RAG document."""
    author: str                              # Agronomist who created/updated
    source: str | None = None                # Original source (book, paper, etc.)
    region: str | None = None                # Geographic relevance
    season: str | None = None                # Seasonal relevance
    tags: list[str] = []                     # Searchable tags


class SourceFile(BaseModel):
    """Original uploaded file reference (for PDF/DOCX uploads)."""
    filename: str                            # "blister-blight-guide.pdf"
    file_type: Literal["pdf", "docx", "md", "txt"]
    blob_path: str                           # Azure Blob path to original
    file_size_bytes: int
    extraction_method: Literal[
        "manual",           # User typed content directly
        "text_extraction",  # PyMuPDF for digital PDFs
        "azure_doc_intel",  # Azure Document Intelligence
        "vision_llm"        # Vision LLM for diagrams
    ] | None = None
    extraction_confidence: float | None = None
    page_count: int | None = None


class RAGDocument(BaseModel):
    """RAG knowledge document."""
    document_id: str                         # Stable ID across versions
    version: int = 1                         # Incrementing version number

    # Content
    title: str
    domain: Literal[
        "plant_diseases",
        "tea_cultivation",
        "weather_patterns",
        "quality_standards",
        "regional_context"
    ]
    content: str                             # Extracted/authored markdown

    # Source file (if uploaded as PDF/DOCX)
    source_file: SourceFile | None = None

    # Lifecycle
    status: Literal["draft", "staged", "active", "archived"] = "draft"
    created_at: datetime
    updated_at: datetime

    # Metadata
    metadata: RAGDocumentMetadata

    # Change tracking
    change_summary: str | None = None

    # Embedding reference (populated after vectorization)
    pinecone_namespace: str | None = None
    pinecone_ids: list[str] = []
    content_hash: str | None = None
```

## PDF Ingestion

Agronomists can upload PDFs directly. The system auto-extracts text using the appropriate method:

| Method | Use Case | Speed | Cost |
|--------|----------|-------|------|
| **PyMuPDF** | Digital PDFs with text | ~100ms/page | Free |
| **Azure Document Intelligence** | Scanned PDFs, tables | ~2-5s/page | $0.01/page |
| **Vision LLM** | Complex diagrams | ~5-10s/page | $0.02-0.05/page |

The extraction method is auto-detected:
1. Try PyMuPDF text extraction first (fast, free)
2. If confidence < 0.9, fall back to Azure Document Intelligence
3. Vision LLM used only for documents with complex diagrams

> **Architecture Reference:** See `architecture/ai-model-architecture.md` → "PDF Ingestion Pipeline" for implementation details.

## Knowledge Domains

| Domain | Content | Used By Agents |
|--------|---------|----------------|
| `plant_diseases` | Symptoms, identification, treatments | diagnose-quality-issue |
| `tea_cultivation` | Best practices, seasonal guidance | analyze-weather-impact, generate-action-plan |
| `weather_patterns` | Regional climate, crop impact | analyze-weather-impact |
| `quality_standards` | Grading criteria, buyer expectations | extract-and-validate, analyze-market |
| `regional_context` | Local practices, cultural factors | generate-action-plan |

## CLI Commands (for Ops)

### Document CRUD

```bash
# Create document from PDF (auto-extraction)
farmer-cli rag create --title "Blister Blight Treatment" \
  --domain plant_diseases \
  --pdf ./documents/blister-blight-guide.pdf \
  --author "Dr. Wanjiku" \
  --region Kenya

# Output:
# ✓ Uploaded PDF (2.3 MB, 15 pages)
# ✓ Extracted using azure_doc_intel (confidence: 0.96)
# ✓ Document created: doc-789 (status: draft)

# Create document from markdown file
farmer-cli rag create --title "Frost Protection" \
  --domain weather_patterns \
  --file frost-protection.md \
  --author "Operations"

# Create document with inline content
farmer-cli rag create --title "Quick Tip" \
  --domain tea_cultivation \
  --content "When temperatures drop below 4°C..." \
  --author "Operations"

# List documents with filters
farmer-cli rag list --domain plant_diseases --status active
farmer-cli rag list --author "Dr. Wanjiku"

# Get specific document
farmer-cli rag get --id doc-123
farmer-cli rag get --id doc-123 --version 2

# Update document (creates new version)
farmer-cli rag update --id doc-123 \
  --file updated-guide.md \
  --change-summary "Added new treatment protocol for resistant strains"

# Delete document (soft delete - archives all versions)
farmer-cli rag delete --id doc-123
```

### Lifecycle Management

```bash
# Stage document for testing/review
farmer-cli rag stage --id doc-123

# Activate (promote to production)
farmer-cli rag activate --id doc-123

# Archive document
farmer-cli rag archive --id doc-123

# Rollback to previous version
farmer-cli rag rollback --id doc-123 --to-version 2
```

### A/B Testing

```bash
# Start A/B test with staged version
farmer-cli rag ab-test start --id doc-123 --traffic 20 --duration 7

# Check A/B test status
farmer-cli rag ab-test status --test-id test-456

# End A/B test (promote or rollback)
farmer-cli rag ab-test end --test-id test-456 --promote
farmer-cli rag ab-test end --test-id test-456 --rollback
```

### Bulk Operations

```bash
# Bulk import from directory
farmer-cli rag import --dir ./knowledge-base/ --domain tea_cultivation --author "Import"

# Export all documents in a domain
farmer-cli rag export --domain plant_diseases --output ./backup/

# Sync all documents to Pinecone (for recovery)
farmer-cli rag sync --domain tea_diseases
```

## Admin UI Workflow (for Agronomists)

Non-technical experts use the Admin UI web interface:

```
┌───────────────────────────────────────────────────────────────────┐
│                   AGRONOMIST WORKFLOW (Admin UI)                   │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. CREATE                                                        │
│     └─→ Navigate to Knowledge Management                         │
│     └─→ Click "New Document"                                     │
│     └─→ Fill form: Title, Domain, Content (markdown editor)      │
│     └─→ Add metadata: Region, Season, Tags                       │
│     └─→ Save as Draft                                            │
│                                                                   │
│  2. REVIEW                                                        │
│     └─→ Senior agronomist reviews draft                          │
│     └─→ Request changes or approve                               │
│     └─→ Approved documents can be staged                         │
│                                                                   │
│  3. STAGE                                                         │
│     └─→ Click "Stage for Testing"                                │
│     └─→ System vectorizes and uploads to Pinecone                │
│     └─→ Document available for A/B testing                       │
│                                                                   │
│  4. A/B TEST (Optional)                                           │
│     └─→ Configure traffic percentage (e.g., 20%)                 │
│     └─→ Set duration (e.g., 7 days)                              │
│     └─→ Monitor accuracy metrics in dashboard                    │
│                                                                   │
│  5. ACTIVATE                                                      │
│     └─→ Review A/B test results                                  │
│     └─→ Click "Activate" to promote to production                │
│     └─→ Previous version automatically archived                  │
│                                                                   │
│  6. MONITOR                                                       │
│     └─→ View usage metrics in dashboard                          │
│     └─→ If issues detected: Click "Rollback"                     │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

## Pinecone Namespace Strategy

Versions are isolated using Pinecone namespaces:

```python
def get_namespace(version: int, status: str) -> str:
    """
    Namespace naming convention:
    - Active:   knowledge-v{version}
    - Staged:   knowledge-v{version}-staged
    - Archived: knowledge-v{version}-archived
    """
    if status == "active":
        return f"knowledge-v{version}"
    return f"knowledge-v{version}-{status}"
```

**Example:**
- Document `doc-123` version 1 active: `knowledge-v1`
- Document `doc-123` version 2 staged: `knowledge-v2-staged`
- After promotion: version 2 in `knowledge-v2`, version 1 in `knowledge-v1-archived`

## Vectorization Process

When a document is staged or activated:

1. **Chunk content** - Split into semantic chunks (by heading or paragraph)
2. **Generate embeddings** - Using `text-embedding-3-small`
3. **Store in Pinecone** - With namespace based on version
4. **Update document record** - Store `pinecone_namespace` and `pinecone_ids`

```python
async def vectorize_document(document: RAGDocument) -> RAGDocument:
    """Vectorize document content and store in Pinecone."""
    # 1. Chunk content by markdown headings
    chunks = chunk_by_heading(document.content)

    # 2. Generate embeddings
    embeddings = await embedding_client.embed(
        texts=[chunk.text for chunk in chunks],
        model="text-embedding-3-small"
    )

    # 3. Store in Pinecone with metadata
    namespace = f"knowledge-v{document.version}"
    vectors = [
        {
            "id": f"{document.document_id}-{i}",
            "values": embedding,
            "metadata": {
                "document_id": document.document_id,
                "domain": document.domain,
                "chunk_index": i,
                "title": document.title,
                "region": document.metadata.region,
                "tags": document.metadata.tags,
            }
        }
        for i, embedding in enumerate(embeddings)
    ]
    await pinecone_client.upsert(vectors, namespace=namespace)

    # 4. Update document record
    document.pinecone_namespace = namespace
    document.pinecone_ids = [v["id"] for v in vectors]
    document.content_hash = hashlib.sha256(document.content.encode()).hexdigest()

    return document
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
        ab_test_version: int | None = None,
        farmer_id: str | None = None
    ) -> dict:
        """Query knowledge base with version routing."""
        # Determine version (A/B test or active)
        if ab_test_version:
            namespace = f"knowledge-v{ab_test_version}-staged"
        else:
            namespace = await self._get_active_namespace(domains)

        # Embed query
        query_embedding = await self.embedder.embed(query)

        # Query Pinecone with domain filter
        results = await self.pinecone_index.query(
            vector=query_embedding,
            namespace=namespace,
            top_k=5,
            include_metadata=True,
            filter={"domain": {"$in": domains}}
        )

        # Format results
        return {
            "context": [
                {
                    "content": r.metadata["content"],
                    "source": r.metadata["document_id"],
                    "relevance": r.score
                }
                for r in results.matches
            ],
            "namespace": namespace
        }
```

## Knowledge Quality Metrics

Track knowledge effectiveness with these metrics:

```python
# OpenTelemetry metrics for knowledge quality
knowledge_metrics = {
    "rag_retrieval_relevance": Histogram(
        "rag_retrieval_relevance_score",
        "Relevance scores of retrieved chunks",
        ["domain", "version"],
        buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0]
    ),

    "rag_document_usage": Counter(
        "rag_document_usage_total",
        "How often each document is retrieved",
        ["document_id", "version"]
    ),

    "rag_ab_test_queries": Counter(
        "rag_ab_test_queries_total",
        "Queries served by A/B test variants",
        ["test_id", "variant"]  # variant: "staged" or "active"
    ),

    "knowledge_staleness": Gauge(
        "knowledge_staleness_days",
        "Days since knowledge document was last updated",
        ["document_id", "domain"]
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
  sum(rate(rag_document_usage_total[24h])) by (document_id)
)

# Documents that may need updating (stale > 180 days)
knowledge_staleness_days > 180

# A/B test traffic distribution
sum(rate(rag_ab_test_queries_total[1h])) by (test_id, variant)
```

## Document Content Best Practices

### DO:
- Use clear, structured content with markdown headings
- Include specific symptoms, conditions, and recommendations
- Add regional variations where applicable
- Write for farmer comprehension (LLM will relay this content)
- Include severity levels and urgency indicators
- Provide actionable recommendations

### DON'T:
- Mix multiple diseases/conditions in one document
- Use overly technical jargon without explanation
- Skip the staging/review process for "small" changes
- Leave documents without regional context
- Create duplicate content across documents

### Document Structure Template

```markdown
# {Condition Name}

## Overview
Brief description of the condition.

## Identification

### Visual Symptoms
- Symptom 1
- Symptom 2

### Affected Plant Parts
- Leaves, stems, roots, etc.

## Conditions Favoring Development
- Environmental factors
- Seasonal patterns
- Regional variations

## Severity Assessment

| Level | Indicators | Urgency |
|-------|------------|---------|
| Low | ... | Monitor |
| Moderate | ... | Treat within 1 week |
| High | ... | Immediate action |

## Recommendations

### Immediate Actions
1. Action 1
2. Action 2

### Preventive Measures
1. Measure 1
2. Measure 2

### Product Recommendations
- Product A: For severe cases
- Product B: For prevention

## Regional Notes

### Highland (>1500m)
- Specific considerations

### Lowland (<1500m)
- Specific considerations
```

## Troubleshooting

### Document not appearing in queries

1. Check document status is `active`
2. Verify vectorization completed (`pinecone_ids` not empty)
3. Check domain filter matches query

```bash
farmer-cli rag get --id doc-123
# Look for: status=active, pinecone_ids=[...]
```

### A/B test not routing traffic

1. Verify test is running
2. Check traffic percentage
3. Confirm staged version is vectorized

```bash
farmer-cli rag ab-test status --test-id test-456
```

### Rollback not working

1. Check archived version exists
2. Verify Pinecone namespace still has vectors

```bash
farmer-cli rag get --id doc-123 --version 2
# Should show status=archived
```

---

_Last Updated: 2025-01-04_
_Maintainer: Platform AI Team_
