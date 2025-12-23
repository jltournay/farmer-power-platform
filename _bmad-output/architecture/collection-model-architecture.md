# Collection Model Architecture

## Overview

The Collection Model is the **data gateway** for the Farmer Power Cloud Platform. It receives data from external sources (QC Analyzers, Weather APIs, etc.), processes it through an intelligent ingestion pipeline, and provides retrieval mechanisms for downstream consumers.

**Core Responsibility:** Collect, validate, transform, link, store, and serve documents.

**Does NOT:** Generate action plans, make business decisions, or verify farmer existence.

## Architecture Diagram

```
External Sources ──▶ COLLECTION MODEL
                         │
                    ┌────┴────┐
                    │ Ingest  │
                    │ Pipeline│
                    └────┬────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         ┌────────┐ ┌────────┐ ┌────────┐
         │Schema  │ │  LLM   │ │ Store  │
         │Validate│─▶│Extract │─▶│Document│
         │        │ │+Validate│ │        │
         └────────┘ └────────┘ └────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
               ┌────────┐     ┌────────┐     ┌────────┐
               │Query   │     │Search  │     │  MCP   │
               │  API   │     │  API   │     │ Server │
               └────────┘     └────────┘     └────────┘
```

## Configured Sources

Each data source is configured with its own ingestion rules:

```yaml
source: qc-analyzer
  endpoint: /api/v1/ingest/qc-analyzer
  events:
    - END_BAG
    - POOR_QUALITY_DETECTED
  validation:
    schema: qc-analyzer-event.json
  transformation:
    agent: qc-extraction-agent
    extract_fields:
      - farmer_id
      - bag_id
      - factory_id
      - grade
      - leaf_distribution
      - quality_issues
      - timestamp
    link_field: farmer_id
  storage:
    blob_container: quality-events
    mongo_collection: quality_events_index
```

## Ingestion Pipeline

### Step 1: Schema Validation
- Fast, deterministic JSON schema validation
- Rejects malformed payloads immediately
- Returns structured error responses

### Step 2: LLM Agent Extraction + Validation
The LLM Agent performs dual-purpose processing:

**Extraction:**
- Locates and extracts required fields from payload
- Handles format variations without code changes
- Adapts to schema drift in source systems

**Semantic Validation:**
- Cross-field consistency checks (e.g., grade vs. quality_score alignment)
- Reasonableness checks (e.g., bag weight within expected range)
- Domain rule validation (e.g., valid grade values)

**Output:**
```python
ProcessingResult(
    extracted_fields: dict,        # Normalized field values
    validation_warnings: list,     # Semantic issues found (non-blocking)
    validation_passed: bool,       # Overall assessment
    confidence: float              # LLM confidence score
)
```

### Step 3: Farmer Linkage
- Extracts `farmer_id` from processed data
- Stores reference directly (no Plantation Model verification)
- Missing farmer ID stored as warning, not rejection

### Step 4: Document Storage
- **Raw payload** → Azure Blob Storage (immutable)
- **Index metadata** → MongoDB (queryable)
- **Validation warnings** → Stored with document metadata

## Trust Model

| Aspect                  | Decision            | Rationale                                         |
|-------------------------|---------------------|---------------------------------------------------|
| **Source Trust**        | Trust provided IDs  | Fast ingestion, no cross-model dependency         |
| **Farmer Verification** | None on ingest      | Plantation Model lookup is downstream concern     |
| **Validation Failures** | Store with warnings | Best-effort semantic checking, not hard rejection |
| **Data Integrity**      | Source responsible  | Collection Model is intake, not police            |

## Retrieval APIs

### Query API
```
GET /api/v1/documents/{document_id}
GET /api/v1/documents?farmer_id={id}&date_range={range}
```

### Search API
```
POST /api/v1/documents/search
{
  "query": "quality issues moisture",
  "filters": {
    "factory_id": "F001",
    "grade_category": "low_quality",       // Semantic filter (recommended)
    // OR: "grade": ["C", "D"]             // Labels from factory's Grading Model
  },
  "limit": 50
}
```

### MCP Server Tools

| Tool | Purpose | Parameters |
|------|---------|------------|
| `get_farmer_documents` | Retrieve all documents for a farmer | `farmer_id`, `date_range?`, `source_type?` |
| `get_quality_events` | Get quality grading events | `farmer_id`, `factory_id?`, `grade_filter?` |
| `search_documents` | Semantic or criteria-based search | `query`, `filters`, `limit` |
| `get_document_by_id` | Retrieve specific document | `document_id` |

## Testing Strategy

| Test Type | Scope | Examples |
|-----------|-------|----------|
| **Schema Validation** | Unit | Valid/invalid JSON against schemas |
| **Extraction Accuracy** | Golden samples | Known payloads → expected extractions |
| **Semantic Validation** | Edge cases | Inconsistent grades, unreasonable weights |
| **API Contracts** | Integration | Request/response schema compliance |
| **MCP Tools** | Functional | Tool selection, response interpretation |

## Data Flow Example

```
QC Analyzer sends END_BAG event:
{
  "event_type": "END_BAG",
  "bag_id": "BAG-2025-001234",
  "qr_data": { "farmer_national_id": "12345678", ... },
  "grading_result": { "grade": "B", "score": 78, ... }
}

Collection Model processes:
1. Schema validation ✓
2. LLM extracts: farmer_id="WM-4521", grade="B", score=78
3. LLM validates: grade/score consistent ✓
4. Store: Blob (raw) + Mongo (index with farmer_ref)
5. Available via Query API, Search API, MCP

Downstream consumer (Action Plan Model):
- Calls MCP: get_farmer_documents("WM-4521", last_7_days)
- Receives quality history
- Generates personalized action plan
```

---
