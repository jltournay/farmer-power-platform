---
stepsCompleted: [1]
inputDocuments: ['_bmad-output/analysis/product-brief-farmer-power-platform-2025-12-16.md']
workflowType: 'architecture'
lastStep: 1
project_name: 'farmer-power-platform'
user_name: 'Jeanlouistournay'
date: '2025-12-16'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

---

## Collection Model Architecture

### Overview

The Collection Model is the **data gateway** for the Farmer Power Cloud Platform. It receives data from external sources (QC Analyzers, Weather APIs, etc.), processes it through an intelligent ingestion pipeline, and provides retrieval mechanisms for downstream consumers.

**Core Responsibility:** Collect, validate, transform, link, store, and serve documents.

**Does NOT:** Generate action plans, make business decisions, or verify farmer existence.

### Architecture Diagram

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

### Configured Sources

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

### Ingestion Pipeline

#### Step 1: Schema Validation
- Fast, deterministic JSON schema validation
- Rejects malformed payloads immediately
- Returns structured error responses

#### Step 2: LLM Agent Extraction + Validation
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

#### Step 3: Farmer Linkage
- Extracts `farmer_id` from processed data
- Stores reference directly (no Plantation Model verification)
- Missing farmer ID stored as warning, not rejection

#### Step 4: Document Storage
- **Raw payload** → Azure Blob Storage (immutable)
- **Index metadata** → MongoDB (queryable)
- **Validation warnings** → Stored with document metadata

### Trust Model

| Aspect                  | Decision            | Rationale                                         |
|-------------------------|---------------------|---------------------------------------------------|
| **Source Trust**        | Trust provided IDs  | Fast ingestion, no cross-model dependency         |
| **Farmer Verification** | None on ingest      | Plantation Model lookup is downstream concern     |
| **Validation Failures** | Store with warnings | Best-effort semantic checking, not hard rejection |
| **Data Integrity**      | Source responsible  | Collection Model is intake, not police            |

### Retrieval APIs

#### Query API
```
GET /api/v1/documents/{document_id}
GET /api/v1/documents?farmer_id={id}&date_range={range}
```

#### Search API
```
POST /api/v1/documents/search
{
  "query": "quality issues moisture",
  "filters": { "factory_id": "F001", "grade": ["C", "D"] },
  "limit": 50
}
```

#### MCP Server Tools

| Tool | Purpose | Parameters |
|------|---------|------------|
| `get_farmer_documents` | Retrieve all documents for a farmer | `farmer_id`, `date_range?`, `source_type?` |
| `get_quality_events` | Get quality grading events | `farmer_id`, `factory_id?`, `grade_filter?` |
| `search_documents` | Semantic or criteria-based search | `query`, `filters`, `limit` |
| `get_document_by_id` | Retrieve specific document | `document_id` |

### Testing Strategy

| Test Type | Scope | Examples |
|-----------|-------|----------|
| **Schema Validation** | Unit | Valid/invalid JSON against schemas |
| **Extraction Accuracy** | Golden samples | Known payloads → expected extractions |
| **Semantic Validation** | Edge cases | Inconsistent grades, unreasonable weights |
| **API Contracts** | Integration | Request/response schema compliance |
| **MCP Tools** | Functional | Tool selection, response interpretation |

### Data Flow Example

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

## Knowledge Model Architecture

### Overview

The Knowledge Model is an **active analysis engine** that diagnoses situations based on collected data. It does NOT prescribe solutions - that's the Action Plan Model's responsibility.

**Core Responsibility:** DIAGNOSE situations (what's wrong? what's happening?)

**Does NOT:** Prescribe solutions, generate action plans, or tell farmers what to do.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         KNOWLEDGE MODEL                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    EXPLORER AGENT                                │   │
│  │  • Maintains tracking of what needs analysis                     │   │
│  │  • Triggers based on configuration (event OR scheduled)          │   │
│  │  • Routes to appropriate Analyzer workflow                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│           ┌──────────────────┼──────────────────┐                      │
│           ▼                  ▼                  ▼                       │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐           │
│  │ Disease Agent   │ │ Weather Agent   │ │ Trend Agent     │           │
│  │ Workflow        │ │ Workflow        │ │ Workflow        │           │
│  │                 │ │                 │ │                 │           │
│  │ event-triggered │ │ daily scheduled │ │ weekly scheduled│           │
│  │ RAG: enabled    │ │ RAG: enabled    │ │ RAG: disabled   │           │
│  └────────┬────────┘ └────────┬────────┘ └────────┬────────┘           │
│           │                   │                   │                     │
│           │    ┌──────────────┴───────────────┐   │                     │
│           │    │        VECTOR DB             │   │                     │
│           │    │        (Pinecone)            │   │                     │
│           │    │  Expert knowledge for RAG    │   │                     │
│           │    └──────────────────────────────┘   │                     │
│           │                                       │                     │
│           └───────────────┬───────────────────────┘                     │
│                           ▼                                             │
│              ┌─────────────────────────┐                                │
│              │      ANALYSIS DB        │                                │
│              │      (MongoDB)          │                                │
│              └───────────┬─────────────┘                                │
│                          │                                              │
│           ┌──────────────┼──────────────┐                               │
│           ▼              ▼              ▼                               │
│     ┌──────────┐  ┌──────────┐  ┌──────────┐                           │
│     │Query API │  │MCP Server│  │  Events  │                           │
│     └──────────┘  └──────────┘  └──────────┘                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Two-Agent Pattern

#### Explorer Agent
- **Responsibility:** Identify what needs analysis
- **Maintains:** Own tracking of analyzed vs. unanalyzed documents
- **Triggers:** Routes to appropriate Analyzer workflow based on configuration

#### Analyzer Agent Workflows
Different LLM Agent workflows based on analysis type:

| Workflow | Trigger | RAG | Purpose |
|----------|---------|-----|---------|
| Disease Detection | Event (`POOR_QUALITY_DETECTED`) | Yes | Identify plant diseases from quality issues |
| Weather Impact | Scheduled (daily) | Yes | Assess weather effects on crop quality |
| Quality Trend | Scheduled (weekly) | No | Analyze patterns in farmer's history |

### Two Databases

#### Analysis DB (MongoDB)
**Purpose:** Store diagnoses created by Knowledge Model

**Schema:** Single collection with `type` field for extensibility

```json
{
    "_id": "analysis-uuid",
    "type": "disease_detection",
    "farmer_id": "WM-4521",
    "source_documents": ["doc-123", "doc-456"],
    "diagnosis": {
        "condition": "fungal_infection",
        "confidence": 0.87,
        "details": "Leaf spots consistent with Cercospora...",
        "severity": "moderate"
    },
    "rag_context_used": true,
    "created_at": "2025-12-16T14:30:00Z",
    "agent_workflow": "disease-detection-v2"
}
```

**Design Choice:** Generic schema allows adding new analysis types dynamically without code changes.

#### Vector DB (Pinecone)
**Purpose:** Expert knowledge for RAG enrichment

**Content:**
- Industry best practices
- Tea cultivation guidelines
- Disease/pest identification
- Regional patterns and seasonal factors

**Curated by:** Domain experts (agronomists)

### RAG Pattern

Analyzer Agents use Retrieval-Augmented Generation:

```
Input: Poor quality document (image, grade D, moisture issues)
         │
         ▼
Query Vector DB: "tea leaf moisture problems causes"
         │
         ▼
Retrieved: Expert knowledge about moisture, common causes
         │
         ▼
LLM generates diagnosis WITH expert context:
"Diagnosis: Excessive moisture likely caused by late harvesting
 after morning dew. Pattern consistent with Nyeri region
 during October rains."
         │
         ▼
Store in Analysis DB (linked to farmer)
```

### Trigger Configuration

```yaml
analysis_triggers:
  - name: poor-quality-analysis
    type: event
    event: "collection.poor_quality_detected"
    agent: disease-detection-agent
    rag_enabled: true
    rag_query_template: "tea leaf quality issues {quality_issues}"

  - name: weather-impact-analysis
    type: scheduled
    cron: "0 6 * * *"  # Daily at 6 AM
    agent: weather-impact-agent
    rag_enabled: true

  - name: trend-analysis
    type: scheduled
    cron: "0 0 * * 0"  # Weekly Sunday midnight
    agent: trend-analysis-agent
    rag_enabled: false
```

### MCP Server Tools

| Tool | Purpose | Parameters |
|------|---------|------------|
| `get_farmer_analyses` | Get all analyses for a farmer | `farmer_id`, `date_range?`, `type?` |
| `get_analysis_by_id` | Retrieve specific analysis | `analysis_id` |
| `search_analyses` | Search analyses by criteria | `query`, `filters`, `limit` |
| `get_recent_diagnoses` | Get diagnoses needing action | `farmer_id`, `since_date` |

**Primary Consumer:** Action Plan Model queries weekly: "Get all analyses for farmer X in past week"

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Core Role** | DIAGNOSE only | Clean separation from prescribing |
| **Agent Architecture** | Multiple specialized workflows | Different analyses need different approaches |
| **Trigger Mechanism** | Configurable (event OR scheduled) | Flexibility per analysis type |
| **Tracking** | Self-maintained | No dependency on Collection Model |
| **Analysis Storage** | Single collection + type field | Generic, dynamic extensibility |
| **Expert Knowledge** | Vector DB for RAG | Enriches diagnosis with domain expertise |

### Testing Strategy

| Test Type | Scope |
|-----------|-------|
| **Explorer Agent** | Correctly identifies unanalyzed items, no duplicates |
| **Analyzer Accuracy** | Diagnoses match expert-validated cases |
| **RAG Relevance** | Vector search returns useful context |
| **New Type Addition** | Can add analysis type without deployment |
| **MCP Queries** | Type filtering works correctly |

---

## Plantation Model Architecture

### Overview

The Plantation Model is the **master data registry** for the Farmer Power Cloud Platform. It stores core entities (farmers, factories), configuration (payment policies, grading model references), and pre-computed performance summaries.

**Core Responsibility:** Manage master data, store configuration, provide pre-computed summaries.

**Does NOT:** Collect raw data, perform analysis, or generate action plans.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       PLANTATION MODEL                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  STATIC DATA (via Admin UI):                                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐         │
│  │   FARMER    │  │   FACTORY   │  │  GRADING MODEL REF      │         │
│  │             │  │             │  │                         │         │
│  │ • farmer_id │  │ • factory_id│  │ • model_id              │         │
│  │ • name      │  │ • name      │  │ • version               │         │
│  │ • phone     │  │ • location  │  │ • active_at_factory[]   │         │
│  │ • national_id│ │ • region    │  │                         │         │
│  │ • farm_size │  │ • payment   │  │ (Definition managed in  │         │
│  │ • region    │  │   _policy   │  │  farmer-power-training  │         │
│  │ • factory_id│  │             │  │  project)               │         │
│  │             │  │             │  │                         │         │
│  │ COMMUNICATION:│ │             │  │                         │         │
│  │ • pref_channel│ │             │  │                         │         │
│  │   (SMS/Voice/ │ │             │  │                         │         │
│  │    WhatsApp)  │ │             │  │                         │         │
│  │ • pref_lang   │ │             │  │                         │         │
│  │ • literacy_lvl│ │             │  │                         │         │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘         │
│                                                                         │
│  COMPUTED DATA (via Scheduler - daily batch):                           │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐      │
│  │  FARMER PERFORMANCE         │  │  FACTORY PERFORMANCE        │      │
│  │                             │  │                             │      │
│  │  • avg_grade (30/90/yr)     │  │  • intake_quality_avg       │      │
│  │  • delivery_count           │  │  • farmer_improvement_rate  │      │
│  │  • improvement_trend        │  │  • rejection_rate           │      │
│  │  • last_delivery            │  │  • premium_percentage       │      │
│  └─────────────────────────────┘  └─────────────────────────────┘      │
│                                                                         │
│  EXTERNAL DATA (via Market Analysis Model):                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  BUYER PROFILES                                                  │   │
│  │  • buyer_id, preferences, quality_requirements                   │   │
│  │  • Created/updated by Market Analysis Model                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                         APIs + MCP                                │  │
│  │  REST API (Admin UI)  │  Internal API (Services)  │  MCP Server  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Data Ownership

| Entity | Writer | Mechanism | Frequency |
|--------|--------|-----------|-----------|
| Farmer | Admin UI | REST API (manual) | On registration/update |
| Factory | Admin UI | REST API (manual) | On setup/config change |
| Grading Model Ref | Admin UI | REST API (manual) | On model deployment |
| Farmer Performance | Scheduler | Batch job (automated) | Daily |
| Factory Performance | Scheduler | Batch job (automated) | Daily |
| Buyer Profiles | Market Analysis Model | Internal API (automated) | On market analysis |

### Farmer Power Ecosystem Context

The Plantation Model references grading models but does NOT store their definitions:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    FARMER POWER ECOSYSTEM                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │  CLOUD PLATFORM │  │  QC ANALYZER    │  │  CV TRAINING    │         │
│  │  (this project) │  │  (edge device)  │  │  (ML pipeline)  │         │
│  │                 │  │                 │  │                 │         │
│  │  Plantation     │  │  Uses grading   │  │  Defines grading│         │
│  │  stores REF to  │  │  model for      │  │  model (weights,│         │
│  │  grading model  │  │  inference      │  │  thresholds)    │         │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘         │
│                                                                         │
│  github.com/farmerpower-ai/farmer-power-platform                        │
│  github.com/farmerpower-ai/farmer-power-qc-analyzer                     │
│  github.com/farmerpower-ai/farmer-power-training                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Performance Summary Computation

```
┌─────────────────┐
│ Collection Model│ (raw quality events)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  BATCH JOB      │ (daily scheduler)
│                 │
│  • Query Collection for events since last run
│  • Aggregate per farmer: avg_grade, count, trend
│  • Aggregate per factory: quality_avg, improvement_rate
│  • Update Plantation Model summaries
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Plantation Model│ (summaries updated)
└─────────────────┘
```

### API Structure

#### Admin UI Endpoints (authenticated, role-based)

```
POST   /api/v1/farmers              # Create farmer
GET    /api/v1/farmers/{id}         # Get farmer
PUT    /api/v1/farmers/{id}         # Update farmer
DELETE /api/v1/farmers/{id}         # Deactivate farmer

POST   /api/v1/factories            # Create factory
GET    /api/v1/factories/{id}       # Get factory
PUT    /api/v1/factories/{id}       # Update factory config
```

#### Internal Endpoints (service-to-service)

```
PUT    /api/v1/internal/farmer-summary/{id}     # Scheduler writes
PUT    /api/v1/internal/factory-summary/{id}    # Scheduler writes
PUT    /api/v1/internal/buyer-profiles/{id}     # Market Analysis writes
```

### MCP Server Tools

| Tool | Purpose | Parameters |
|------|---------|------------|
| `get_farmer` | Farmer profile | `farmer_id` |
| `get_farmer_summary` | Performance summary | `farmer_id`, `period?` |
| `get_factory` | Factory details + payment_policy | `factory_id` |
| `get_factory_config` | Grading model ref, thresholds | `factory_id` |
| `get_buyer_profiles` | Market preferences | `region?`, `factory_id?` |
| `get_farmer_context` | Combined view (convenience) | `farmer_id` |

**Primary Consumer:** Action Plan Model queries via MCP for complete farmer context when generating recommendations.

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Core Role** | Master data + summaries | Single source of truth for entities |
| **Performance Summaries** | Pre-computed (daily batch) | Fast access, no real-time computation |
| **Grading Model** | Reference only | Definition in separate training project |
| **Buyer Profiles** | Stored here, written by Market Analysis | Centralized profile storage |
| **MCP Server** | Yes | AI agents need rich farmer/factory context |
| **Data Ownership** | Clear per-entity | Admin UI, Scheduler, Market Analysis |

### Testing Strategy

| Test Type | Focus |
|-----------|-------|
| **Admin API** | Input validation, authorization, audit trail |
| **Scheduler Job** | Reliability, computation accuracy, idempotency |
| **Market Analysis Integration** | API contract, data integrity |
| **MCP Tools** | Correct data retrieval, access control |
| **Performance Summaries** | Aggregation accuracy vs. raw data |

---

## Action Plan Model Architecture

### Overview

The Action Plan Model is the **prescription engine** that transforms diagnoses from the Knowledge Model into actionable recommendations for farmers. It generates dual-format outputs: detailed reports for experts and simplified communications for farmers.

**Core Responsibility:** PRESCRIBE actions (what should the farmer do?)

**Does NOT:** Diagnose problems, collect data, or deliver messages (SMS delivery is infrastructure).

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       ACTION PLAN MODEL                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  INPUTS (via MCP):                                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐     │
│  │ Knowledge MCP   │    │ Plantation MCP  │    │ Collection MCP  │     │
│  │ (analyses)      │    │ (farmer context)│    │ (raw data)      │     │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘     │
│           │                      │                      │               │
│           └──────────────────────┼──────────────────────┘               │
│                                  ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      SELECTOR AGENT                              │   │
│  │  • Runs weekly (scheduled)                                       │   │
│  │  • Queries: "What analyses were created for farmer X this week?" │   │
│  │  • Routes to Action Plan Generator with combined context         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                  │                                       │
│                                  ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                 ACTION PLAN GENERATOR AGENT                      │   │
│  │                                                                   │   │
│  │  INPUT: Combined analyses + farmer context                        │   │
│  │                                                                   │   │
│  │  OUTPUT:                                                          │   │
│  │  ┌──────────────────────┐  ┌──────────────────────┐              │   │
│  │  │  DETAILED REPORT     │  │  FARMER MESSAGE      │              │   │
│  │  │  (Markdown)          │  │  (Simplified)        │              │   │
│  │  │                      │  │                      │              │   │
│  │  │  • Full analysis     │  │  • Local language    │              │   │
│  │  │  • Expert details    │  │  • Simple actions    │              │   │
│  │  │  • Confidence scores │  │  • SMS-ready format  │              │   │
│  │  │  • Source references │  │  • Cultural context  │              │   │
│  │  └──────────────────────┘  └──────────────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                  │                                       │
│                                  ▼                                       │
│              ┌─────────────────────────────────────┐                    │
│              │         ACTION PLAN DB              │                    │
│              │         (MongoDB)                   │                    │
│              │                                     │                    │
│              │  Both formats stored per plan       │                    │
│              └─────────────────────────────────────┘                    │
│                                  │                                       │
│                                  ▼                                       │
│              ┌─────────────────────────────────────┐                    │
│              │      INFRASTRUCTURE LAYER           │                    │
│              │      (Message Delivery - External)  │                    │
│              │                                     │                    │
│              │  SMS Gateway, Push Notifications    │                    │
│              └─────────────────────────────────────┘                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Two-Agent Pattern

#### Selector Agent
- **Trigger:** Weekly scheduled (e.g., every Monday at 6 AM)
- **Responsibility:** For each active farmer, query Knowledge MCP for analyses created in past 7 days
- **Logic:**
  - Has analyses → Route to Action Plan Generator with combined context
  - No analyses → Can trigger informational message (no action plan created)

#### Action Plan Generator Agent
- **Input:** All analyses for one farmer (combined) + farmer context from Plantation MCP
- **Output:** Dual-format action plan stored in MongoDB
- **Behavior:** Combines multiple diagnoses into a coherent, prioritized action plan

### Dual-Format Output

Both formats are generated in the same workflow and stored together:

```json
{
    "_id": "action-plan-uuid",
    "farmer_id": "WM-4521",
    "week": "2025-W51",
    "created_at": "2025-12-16T06:00:00Z",
    "source_analyses": ["analysis-123", "analysis-456", "analysis-789"],

    "detailed_report": {
        "format": "markdown",
        "content": "# Weekly Action Plan for WM-4521\n\n## Summary\nBased on 3 analyses this week...\n\n## Priority Actions\n1. **Fungal Treatment Required** (High Priority)\n   - Diagnosis: Cercospora leaf spot detected\n   - Confidence: 87%\n   - Action: Apply copper-based fungicide within 3 days...\n\n## Full Analysis Details\n...",
        "priority_actions": 2,
        "analyses_summarized": 3
    },

    "farmer_message": {
        "language": "sw",
        "content": "Habari! Wiki hii tuligundua ugonjwa wa majani. Tafadhali...",
        "sms_segments": 2,
        "character_count": 280,
        "delivery_status": "pending"
    }
}
```

### Farmer Communication Preferences

The Action Plan Generator queries Plantation MCP for farmer profile including:
- **pref_channel:** SMS, Voice, WhatsApp - determines output format
- **pref_lang:** Swahili, Kikuyu, English, etc. - determines translation target
- **literacy_lvl:** Low, Medium, High - determines simplification level

### Translation and Simplification

The Action Plan Generator Agent handles (based on farmer preferences):
- **Language Translation:** From English analysis to farmer's `pref_lang`
- **Simplification:** Adjusted to farmer's `literacy_lvl` (low = very simple, high = more detail)
- **Prioritization:** Multiple issues → Ordered by urgency/impact
- **Cultural Context:** Region-appropriate recommendations
- **Format Adaptation:** Based on `pref_channel` (SMS length, voice script, WhatsApp rich text)

### Empty State Handling

When Selector Agent finds no analyses for a farmer:
- **No action plan created** (nothing to prescribe)
- **Optional:** Trigger informational message ("No issues detected this week, keep up the good work!")
- **Tracking:** Record that farmer was checked but had no analyses

### No MCP Server

**Decision:** Action Plan Model does NOT expose an MCP Server.

**Rationale:**
- This is the **final output** of the analysis pipeline
- Consumers are the messaging infrastructure and dashboard UI
- No downstream AI agents need to query action plans
- Direct database access or REST API is sufficient

### Message Delivery Separation

**Architecture Decision:** Message delivery is NOT part of Action Plan Model - it's handled by a **Unified Notification Infrastructure Component**.

```
Action Plan Model                 NOTIFICATION INFRASTRUCTURE
┌─────────────────┐               ┌─────────────────────────────────────────┐
│ Generates plans │──────────────▶│           Notification Service          │
│ Stores in DB    │   publish     │                                         │
│                 │   event       │  ┌─────────────────────────────────┐    │
└─────────────────┘               │  │   Unified Channel Abstraction   │    │
                                  │  │                                 │    │
                                  │  │  notify(farmer_id, message)     │    │
                                  │  │  → Reads pref_channel from      │    │
                                  │  │    Plantation Model             │    │
                                  │  │  → Routes to appropriate        │    │
                                  │  │    channel adapter              │    │
                                  │  └─────────────────────────────────┘    │
                                  │                  │                      │
                                  │    ┌─────────────┼─────────────┐        │
                                  │    ▼             ▼             ▼        │
                                  │  ┌─────┐     ┌─────┐     ┌─────┐       │
                                  │  │ SMS │     │Whats│     │Tele │       │
                                  │  │     │     │App  │     │gram │       │
                                  │  └─────┘     └─────┘     └─────┘       │
                                  │    ▼             ▼             ▼        │
                                  │  ┌─────┐     ┌─────┐     ┌─────┐       │
                                  │  │Email│     │Mobile│    │Future│      │
                                  │  │     │     │ App  │    │Channel│     │
                                  │  └─────┘     └─────┘     └─────┘       │
                                  └─────────────────────────────────────────┘
```

### Unified Notification Infrastructure

**Purpose:** Generic infrastructure component providing unified abstraction for farmer communication across all channels.

**Supported Channels:**

| Channel    | Adapter                       | Use Case                   |
|------------|-------------------------------|----------------------------|
| SMS        | Twilio, Africa's Talking      | Basic phones, low literacy |
| WhatsApp   | WhatsApp Business API         | Rich media, most farmers   |
| Telegram   | Telegram Bot API              | Tech-savvy farmers         |
| Email      | SendGrid / SMTP               | Factory managers, reports  |
| Mobile App | Push Notifications (FCM/APNs) | App users                  |

**Unified Interface:**
```typescript
interface NotificationService {
  // Simple: auto-routes based on farmer preference
  notify(farmerId: string, message: NotificationPayload): Promise<DeliveryResult>;

  // Explicit: override channel if needed
  notifyVia(farmerId: string, channel: Channel, message: NotificationPayload): Promise<DeliveryResult>;

  // Bulk: weekly action plan distribution
  notifyBatch(notifications: BatchNotification[]): Promise<BatchResult>;
}

interface NotificationPayload {
  content: string;           // Pre-formatted for channel (from Action Plan)
  priority: 'low' | 'normal' | 'high';
  metadata: {
    source: 'action_plan' | 'alert' | 'info';
    actionPlanId?: string;
    farmerId: string;
  };
}
```

**Channel Selection Logic:**
1. Query Plantation MCP for farmer's `pref_channel`
2. Check channel availability (e.g., WhatsApp requires opt-in)
3. Fallback chain: preferred → SMS → store for later

**Benefits:**
- Action Plan Model focuses on content generation only
- Single abstraction for all notification consumers
- Easy to add new channels without changing producers
- Centralized delivery tracking, retry logic, rate limiting
- Channel-specific formatting handled by adapters

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Core Role** | PRESCRIBE only | Clean separation from diagnosis |
| **Agent Architecture** | Two-agent (Selector + Generator) | Separation of routing and content generation |
| **Schedule** | Weekly | Matches farmer planning cycles |
| **Output Format** | Dual (detailed + simplified) | Serves both experts and farmers |
| **Translation** | In-agent workflow | LLM naturally handles translation |
| **Multiple Analyses** | Combined into one plan | One coherent weekly recommendation |
| **MCP Server** | No | Final output, no AI agent consumers |
| **Message Delivery** | Infrastructure layer | Separation of concerns |

### Testing Strategy

| Test Type | Focus |
|-----------|-------|
| **Selector Agent** | Correct weekly aggregation, no duplicates |
| **Plan Generation** | Quality of recommendations, prioritization |
| **Translation Accuracy** | Language correctness, cultural appropriateness |
| **Simplification** | Readability for farmers, SMS length compliance |
| **Empty State** | Correct handling of no-analysis weeks |
| **Multi-Analysis** | Coherent combination of diverse diagnoses |

---

## Market Analysis Model Architecture

> **STATUS: PENDING DISCUSSION** - Details to be confirmed with colleague. Documenting known information below.

### Overview

The Market Analysis Model connects internal plantation data with external market intelligence to create Buyer Profiles and market insights.

**Core Responsibility:** Analyze market conditions, buyer requirements, and match factory output to market opportunities.

**Does NOT:** [TBD]

### Known Data Sources

| Source | Type | Purpose |
|--------|------|---------|
| Plantation Model | Internal | Factory summaries, quality levels, farmer performance |
| Starfish Network API | External | Supply chain traceability, buyer data, market standards |

### Starfish Network Integration

[Starfish Network](https://www.starfish-network.com/) is a supply chain data exchange platform:
- **Protocol:** GS1 standardized traceability data
- **Purpose:** Multi-party data sharing across agricultural supply chains
- **Data Types:** Buyer requirements, compliance standards, trading partner profiles

### Known Outputs

- **Buyer Profiles** → Written to Plantation Model via internal API

### Open Questions (To Discuss)

1. **Trigger Mechanism:** Scheduled batch? Event-driven? On-demand?
2. **Additional Outputs:** Price forecasts? Market trends? Quality-to-price mapping?
3. **MCP Server:** Does it expose one for AI agent queries?
4. **Agent Pattern:** Single agent or two-agent pattern?
5. **Update Frequency:** How often are buyer profiles refreshed?
6. **Starfish API Scope:** Which specific endpoints/data types are consumed?

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     MARKET ANALYSIS MODEL                                │
│                     (Architecture TBD)                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  INPUTS:                                                                │
│  ┌─────────────────┐    ┌─────────────────────────────────────────┐    │
│  │ Plantation MCP  │    │ Starfish Network API                    │    │
│  │ (factory data)  │    │ (traceability, buyer data, GS1 format)  │    │
│  └────────┬────────┘    └──────────────────┬──────────────────────┘    │
│           │                                │                            │
│           └────────────────┬───────────────┘                            │
│                            ▼                                            │
│           ┌────────────────────────────────┐                            │
│           │     MARKET ANALYSIS AGENT      │                            │
│           │     (Pattern TBD)              │                            │
│           └────────────────┬───────────────┘                            │
│                            │                                            │
│                            ▼                                            │
│           ┌────────────────────────────────┐                            │
│           │        OUTPUTS                 │                            │
│           │  • Buyer Profiles → Plantation │                            │
│           │  • [Other outputs TBD]         │                            │
│           └────────────────────────────────┘                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## AI Model Architecture

### Overview

The AI Model is the **6th Domain Model** - the centralized intelligence layer for the Farmer Power Cloud Platform. Unlike the previous design where AI agents were embedded in each domain model, all AI logic is centralized here.

**Core Responsibility:** Execute AI workflows (extraction, diagnosis, content generation) on behalf of other domain models.

**Does NOT:** Own business data, make business decisions about when to run, or store results persistently.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           AI MODEL                                       │
│                   (6th Domain Model)                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    WORKFLOW ENGINE                               │   │
│  │                                                                  │   │
│  │  Agent Types (in code):                                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │   │
│  │  │  EXTRACTOR  │  │  EXPLORER   │  │  GENERATOR  │              │   │
│  │  │             │  │             │  │             │              │   │
│  │  │ • Extract   │  │ • Analyze   │  │ • Create    │              │   │
│  │  │ • Validate  │  │ • Diagnose  │  │ • Translate │              │   │
│  │  │ • Normalize │  │ • Pattern   │  │ • Format    │              │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │   │
│  │                                                                  │   │
│  │  Agent Instances (YAML config):                                  │   │
│  │  • qc-event-extractor                                            │   │
│  │  • disease-diagnosis                                             │   │
│  │  • weather-impact-analyzer                                       │   │
│  │  • trend-analyzer                                                │   │
│  │  • weekly-action-plan                                            │   │
│  │  • market-analyzer                                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                          │                                              │
│            ┌─────────────┴─────────────┐                                │
│            ▼                           ▼                                │
│  ┌──────────────────┐       ┌──────────────────────┐                   │
│  │   LLM GATEWAY    │       │     RAG ENGINE       │                   │
│  │                  │       │                      │                   │
│  │  • OpenRouter    │       │  ┌────────────────┐  │                   │
│  │  • Model routing │       │  │  Vector DB     │  │                   │
│  │  • Cost tracking │       │  │  (Pinecone)    │  │                   │
│  │  • Retry/fallback│       │  │                │  │                   │
│  │                  │       │  │  • Tea diseases│  │                   │
│  └──────────────────┘       │  │  • Best practices│ │                   │
│                             │  │  • Weather patterns│                   │
│                             │  │  • Regional knowledge                  │
│                             │  └────────────────┘  │                   │
│                             │                      │                   │
│                             │  Access: internal    │                   │
│                             │  Curation: Admin UI  │                   │
│                             └──────────────────────┘                   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    MCP CLIENTS                                   │   │
│  │  • Collection MCP (fetch documents)                              │   │
│  │  • Plantation MCP (fetch farmer context)                         │   │
│  │  • Knowledge MCP (fetch analyses)                                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Persistence: STATELESS (results published via events)                  │
│  MCP Server: NONE (domain models don't query AI Model)                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Communication Pattern

The AI Model uses **event-driven async communication** via DAPR:

```
Domain Models                          AI Model
┌─────────────────┐                   ┌─────────────────────────────┐
│                 │   publish event   │                             │
│  Collection     │──────────────────▶│   1. Receive event (ref)    │
│  Knowledge      │   { doc_id }      │   2. Fetch data via MCP     │
│  Action Plan    │                   │   3. Run agent workflow     │
│  Plantation     │◀──────────────────│   4. Publish result event   │
│  Market         │   result event    │                             │
│                 │   { result }      │                             │
└─────────────────┘                   └─────────────────────────────┘
     No AI logic                           All AI logic here
     No RAG access
```

**Event Flow Example - Quality Document Processing:**

```
1. Collection Model receives QC payload via API
2. Collection stores raw document → doc_id = "doc-123"
3. Collection publishes via DAPR Pub/Sub:
   topic: "collection.document.received"
   payload: { doc_id: "doc-123", source: "qc-analyzer", event_type: "END_BAG" }

4. AI Model subscribes, receives event
5. AI Model calls Collection MCP: get_document("doc-123")
6. AI Model runs extraction agent workflow
7. AI Model publishes via DAPR Pub/Sub:
   topic: "ai.extraction.complete"
   payload: {
     doc_id: "doc-123",
     success: true,
     result: {
       farmer_id: "WM-4521",
       grade: "B",
       quality_score: 78,
       validation_warnings: []
     }
   }

8. Collection Model subscribes, receives result
9. Collection updates document with extracted fields
```

### Agent Types

Three agent types are implemented in code, each with a specific workflow pattern:

#### Extractor Type

**Purpose:** Extract structured data from unstructured/semi-structured input

```yaml
agent_type: extractor
workflow:
  1_fetch: "Fetch document via MCP"
  2_extract: "LLM extracts fields per schema"
  3_validate: "Validate extracted data"
  4_normalize: "Normalize values (dates, IDs, etc.)"
  5_output: "Publish extraction result"

defaults:
  llm:
    task_type: "extraction"
    temperature: 0.1           # Very deterministic
    output_format: "json"
  rag:
    enabled: false             # Extractors typically don't need RAG
```

#### Explorer Type

**Purpose:** Analyze data, find patterns, produce diagnoses

```yaml
agent_type: explorer
workflow:
  1_fetch: "Fetch relevant documents via MCP"
  2_context: "Build context (farmer history, regional data)"
  3_rag: "Retrieve expert knowledge if enabled"
  4_analyze: "LLM analyzes with full context"
  5_output: "Publish analysis result"

defaults:
  llm:
    task_type: "diagnosis"
    temperature: 0.3
    output_format: "json"
  rag:
    enabled: true
    top_k: 5
```

#### Generator Type

**Purpose:** Create content (plans, reports, messages)

```yaml
agent_type: generator
workflow:
  1_fetch: "Fetch source analyses via MCP"
  2_context: "Build farmer/recipient context"
  3_prioritize: "Rank and prioritize inputs"
  4_generate: "LLM generates content"
  5_format: "Apply output formatting"
  6_output: "Publish generated content"

defaults:
  llm:
    task_type: "generation"
    temperature: 0.5           # More creative
    output_format: "markdown"
  rag:
    enabled: true              # For best practices
```

### Agent Configuration Schema

Agent instances are defined in YAML files in Git:

```yaml
agent:
  # ═══════════════════════════════════════════════════════════════════
  # IDENTITY
  # ═══════════════════════════════════════════════════════════════════
  id: "disease-diagnosis"
  type: explorer                     # Uses explorer workflow
  version: "1.0.0"
  description: "Analyzes quality issues and produces diagnosis"

  # ═══════════════════════════════════════════════════════════════════
  # INPUT / OUTPUT CONTRACT
  # ═══════════════════════════════════════════════════════════════════
  input:
    event: "collection.poor_quality_detected"
    schema:
      required: [doc_id, farmer_id]
      optional: [quality_issues, grade]

  output:
    event: "ai.diagnosis.complete"
    schema:
      fields: [diagnosis, confidence, severity, details, recommendations]

  # ═══════════════════════════════════════════════════════════════════
  # DATA SOURCES (MCP)
  # ═══════════════════════════════════════════════════════════════════
  mcp_sources:
    - server: collection
      tools: [get_document, get_farmer_documents]
    - server: plantation
      tools: [get_farmer, get_farmer_summary]

  # ═══════════════════════════════════════════════════════════════════
  # LLM CONFIGURATION
  # ═══════════════════════════════════════════════════════════════════
  llm:
    task_type: "diagnosis"          # Routes to appropriate model
    model_override: null            # Or specific: "anthropic/claude-3-5-sonnet"
    temperature: 0.3
    max_tokens: 2000

  # ═══════════════════════════════════════════════════════════════════
  # PROMPT CONFIGURATION
  # ═══════════════════════════════════════════════════════════════════
  prompt:
    system_file: "prompts/explorers/disease-diagnosis.system.md"
    template_file: "prompts/explorers/disease-diagnosis.template.md"
    output_format: "json"
    output_schema:
      type: object
      properties:
        diagnosis:
          type: object
          properties:
            condition: { type: string }
            confidence: { type: number, min: 0, max: 1 }
            severity: { enum: [low, moderate, high, critical] }
            details: { type: string }
        recommendations: { type: array, items: { type: string } }

  # ═══════════════════════════════════════════════════════════════════
  # RAG CONFIGURATION
  # ═══════════════════════════════════════════════════════════════════
  rag:
    enabled: true
    query_template: "tea leaf quality issues {{quality_issues}} {{grade}}"
    knowledge_domains: [plant_diseases, tea_cultivation, quality_standards]
    top_k: 5
    min_similarity: 0.7

  # ═══════════════════════════════════════════════════════════════════
  # ERROR HANDLING
  # ═══════════════════════════════════════════════════════════════════
  error_handling:
    retry:
      max_attempts: 3
      backoff_ms: [100, 500, 2000]
    on_failure: "publish_error_event"
    dead_letter_topic: "ai.errors.dead_letter"
```

### Agent Type Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Number of types** | 3 (Extractor, Explorer, Generator) | Covers fundamental AI patterns; add more when needed |
| **Type location** | In code | Workflow logic requires conditionals, loops, error handling |
| **Instance location** | YAML in Git | Declarative, version controlled, PR reviewable |
| **Inheritance** | Flat (Type → Instance only) | Avoids complexity; use parameters for variations |
| **Prompts** | Separate .md files | Better diffs, easier review, can be long |

### Triggering

**Key Decision:** Triggering is the responsibility of domain models, NOT the AI Model.

Domain models configure triggers that specify when to invoke AI workflows:

```yaml
# In Knowledge Model configuration
triggers:
  - name: poor-quality-analysis
    type: event
    event: "collection.poor_quality_detected"
    workflow: "diagnose-quality-issue"

  - name: daily-weather-analysis
    type: schedule
    cron: "0 6 * * *"
    workflow: "analyze-weather-impact"
    params: { region: "all" }

  - name: weekly-trend-analysis
    type: schedule
    cron: "0 0 * * 0"
    workflow: "analyze-trends"
    params: { scope: "all_farmers" }
```

**Trigger Schema:**

```yaml
trigger:
  name: string              # Unique identifier
  type: event | schedule    # Trigger mechanism

  # If type: event
  event: string             # Event topic to subscribe to

  # If type: schedule
  cron: string              # Cron expression

  workflow: string          # AI Model workflow to invoke
  params: object            # Optional parameters to pass
  enabled: boolean          # Can disable without removing
```

**Infrastructure:**

| Trigger Type | DAPR Component | Agnostic Of |
|--------------|----------------|-------------|
| Event | DAPR Pub/Sub | Message broker (Azure SB, Kafka, Redis...) |
| Schedule | DAPR Jobs | Scheduler backend |

### LLM Gateway

[OpenRouter.ai](https://openrouter.ai) serves as the unified LLM gateway:

| Benefit | Description |
|---------|-------------|
| **Multi-Provider** | Access OpenAI, Anthropic, Google, Meta, Mistral through single API |
| **Model Flexibility** | Switch models per task without code changes |
| **Cost Optimization** | Route simple tasks to cheaper models, complex to capable ones |
| **Fallback** | Automatic failover if one provider is down |
| **Unified Billing** | Single invoice, per-model cost breakdown |
| **No Vendor Lock-in** | Can switch providers without changing integration |

**Model Routing Strategy:**

| Task Type | Recommended Model | Rationale |
|-----------|-------------------|-----------|
| **Extraction** | Claude Haiku / GPT-4o-mini | Fast, cheap, structured output |
| **Diagnosis** | Claude Sonnet / GPT-4o | Complex reasoning, accuracy critical |
| **Generation** | Claude Sonnet | Translation, simplification, cultural context |
| **Market Analysis** | GPT-4o | Data synthesis, pattern recognition |
| **RAG Queries** | Claude Haiku | Fast retrieval augmentation |

**Configuration:**

```yaml
# ai-model/config/llm-gateway.yaml
openrouter:
  api_key: ${OPENROUTER_API_KEY}
  base_url: https://openrouter.ai/api/v1

  default_models:
    extraction: "anthropic/claude-3-haiku"
    diagnosis: "anthropic/claude-3-5-sonnet"
    generation: "anthropic/claude-3-5-sonnet"
    market_analysis: "openai/gpt-4o"
    rag_query: "anthropic/claude-3-haiku"

  fallback_chain:
    - "anthropic/claude-3-5-sonnet"
    - "openai/gpt-4o"
    - "google/gemini-pro"

  retry:
    max_attempts: 3
    backoff_ms: [100, 500, 2000]
```

### RAG Engine

The RAG (Retrieval-Augmented Generation) engine is internal to the AI Model:

| Aspect | Decision |
|--------|----------|
| **Vector DB** | Pinecone |
| **Access** | Internal only - domain models cannot query directly |
| **Curation (v1)** | Manual upload via Admin UI by agronomists |
| **Curation (future)** | Separate knowledge curation workflow |

**Knowledge Domains:**

| Domain | Content | Used By |
|--------|---------|---------|
| Plant Diseases | Symptoms, identification, treatments | diagnose-quality-issue |
| Tea Cultivation | Best practices, seasonal guidance | analyze-weather-impact, generate-action-plan |
| Weather Patterns | Regional climate, crop impact | analyze-weather-impact |
| Quality Standards | Grading criteria, buyer expectations | extract-and-validate, analyze-market |
| Regional Context | Local practices, cultural factors | generate-action-plan |

### Configuration Strategy

**Hybrid approach - Git for technical config, Admin UI for business data:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     CONFIGURATION STRATEGY                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  GIT (YAML files) - Infrastructure & Technical Config                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  • Agent instance definitions                                    │   │
│  │  • Trigger configurations (event mappings, cron schedules)       │   │
│  │  • LLM routing (model per task type)                             │   │
│  │  • DAPR component configs                                        │   │
│  │  • Prompt templates (separate .md files)                         │   │
│  │                                                                  │   │
│  │  Changed by: Developers, Architects                              │   │
│  │  Process: PR → Review → Merge → Deploy                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ADMIN UI + MongoDB - Business & Operational Config                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  • RAG knowledge documents (upload interface)                    │   │
│  │  • Farmer/Factory data (Plantation Model)                        │   │
│  │  • Buyer profiles                                                │   │
│  │                                                                  │   │
│  │  Changed by: Operations, Agronomists, Factory managers          │   │
│  │  Process: Login → Edit → Save → Immediate effect                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Observability

**DAPR provides OpenTelemetry instrumentation out of the box:**

| Aspect | Approach |
|--------|----------|
| **Tracing** | DAPR automatic trace context propagation |
| **Backend** | Grafana Cloud (OpenTelemetry compatible, swappable) |
| **Cost Tracking** | Per-call logging (tokens, cost, model, farmer_id) |
| **Metrics** | Latency, error rates, token usage per agent/model |

**Trace propagation across events:**

```
Collection ──▶ DAPR ──▶ AI Model ──▶ MCP calls ──▶ DAPR ──▶ Collection
    │            │          │            │           │          │
 span-1      span-2      span-3      span-4       span-5     span-6
    └──────────────────────┴────────────────────────┴──────────┘
                          same trace_id
```

**Infrastructure Agnosticism:**

| Infrastructure | Abstraction | Current Choice | Can Switch To |
|----------------|-------------|----------------|---------------|
| Message Broker | DAPR Pub/Sub | TBD | Azure SB, Kafka, Redis, RabbitMQ |
| Observability | OpenTelemetry | Grafana Cloud | Azure Monitor, Datadog, Jaeger |
| LLM Provider | OpenRouter | Multi-provider | Any supported model |
| Scheduler | DAPR Jobs | TBD | Any DAPR-supported backend |

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **AI as Domain Model** | Yes (6th model) | Centralized intelligence, clean separation |
| **Agent Logic** | All in AI Model | Domain models stay simple, no AI dependencies |
| **Communication** | Event-driven async | Non-blocking, scalable, resilient |
| **Event Broker** | DAPR Pub/Sub | Broker-agnostic |
| **Event Payload** | References (IDs) | Small events, MCP for data fetch |
| **Result Delivery** | In completion event | Stateless AI Model, domain owns data |
| **Triggering** | Domain model responsibility | Business logic stays in domain |
| **Scheduler** | DAPR Jobs | Scheduler-backend agnostic |
| **RAG Access** | Internal only | Domain models don't need to know about RAG |
| **RAG Curation** | Admin UI (manual) | Agronomists manage knowledge |
| **Agent Types** | 3 (Extractor, Explorer, Generator) | Covers patterns, extensible when needed |
| **Type Implementation** | In code | Workflow logic is code |
| **Instance Config** | YAML in Git | Declarative, version controlled |
| **Prompts** | Separate .md files | Better review, can be long |
| **Observability** | DAPR OpenTelemetry | Backend-agnostic |

### Testing Strategy

| Test Type | Focus |
|-----------|-------|
| **Agent Type Workflows** | Step execution, error handling, retries |
| **Extraction Accuracy** | Golden samples → expected extractions |
| **Diagnosis Quality** | Expert-validated cases |
| **RAG Relevance** | Query → useful context retrieval |
| **Event Contracts** | Input/output schema compliance |
| **MCP Integration** | Correct data fetching |
| **LLM Gateway** | Routing, fallback, cost tracking |
| **End-to-End** | Full event flow through system |

### Developer Guide

> **See:** `ai-model-developer-guide.md` for comprehensive developer guidelines including:
> - LangChain vs LangGraph usage patterns
> - Project structure and naming conventions
> - Step-by-step agent creation guide
> - Prompt engineering standards
> - Testing strategies (golden samples, mocking)
> - Error handling patterns
> - Security guidelines (prompt injection, PII)
> - Performance optimization (caching, batching, token efficiency)
> - Observability standards (logging, tracing, metrics)

---

## Validated Use Cases

This section documents key use cases traced through the architecture to validate the design.

### Use Case 1: Batch ZIP Upload (Poor Quality Images)

**Scenario:** QC Analyzer at factory detects tea leaves that don't reach minimum quality. Instead of sending images individually over an unstable network, it batches multiple images with a JSON index into a ZIP archive.

**Flow:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    BATCH ZIP INGESTION                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  QC ANALYZER (Factory)                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 1. Collect poor quality images during intake                     │   │
│  │ 2. Create batch ZIP:                                             │   │
│  │    batch_001.zip                                                 │   │
│  │    ├── index.json (metadata for all images)                      │   │
│  │    ├── img_001.jpg                                               │   │
│  │    ├── img_002.jpg                                               │   │
│  │    └── img_003.jpg ...                                           │   │
│  │ 3. Calculate SHA256 checksum                                     │   │
│  │ 4. Upload via resumable protocol (survives network drops)        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                          │                                              │
│                          ▼                                              │
│  COLLECTION MODEL                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 1. Receive ZIP via resumable upload endpoint                     │   │
│  │ 2. Verify SHA256 checksum                                        │   │
│  │ 3. Store original ZIP → Blob (quality-archives) for audit        │   │
│  │ 4. Extract and validate index.json                               │   │
│  │ 5. For each image:                                               │   │
│  │    a. Store image → Blob (quality-images)                        │   │
│  │    b. Create document → MongoDB (quality_events)                 │   │
│  │    c. Emit event → DAPR Pub/Sub                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                          │                                              │
│                          ▼                                              │
│  DAPR PUB/SUB: N events emitted                                         │
│  topic: "collection.poor_quality_detected"                              │
│  { doc_id, farmer_id, factory_id, grade, quality_score, image_url }     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Collection Model Configuration:**

```yaml
source: qc-analyzer-batch
  endpoint: /api/v1/ingest/qc-analyzer/batch
  content_type: application/zip

  upload:
    resumable: true                   # Survives network drops
    checksum:
      algorithm: sha256
      header: X-Checksum-SHA256
    timeout_seconds: 300

  archive:
    format: zip
    index_file: "index.json"
    index_schema: qc-batch-index.json

  processing:
    mode: expand                      # Expand to individual documents
    document_per: image

  storage:
    archive:
      container: quality-archives
      retention_days: 90
    images:
      container: quality-images
      path_template: "{factory_id}/{date}/{batch_id}/{filename}"
    documents:
      mongo_collection: quality_events

  events:
    per_document:
      topic: "collection.poor_quality_detected"
```

**Resumable Upload API:**

```yaml
endpoints:
  # Initialize upload
  POST /api/v1/ingest/qc-analyzer/batch/init
    → Returns: upload_id

  # Upload chunk (resume from any point)
  PATCH /api/v1/ingest/qc-analyzer/batch/{upload_id}
    Content-Range: bytes {start}-{end}/{total}

  # Check progress (for resume after disconnect)
  HEAD /api/v1/ingest/qc-analyzer/batch/{upload_id}
    → Returns: Upload-Offset header

  # Complete upload
  POST /api/v1/ingest/qc-analyzer/batch/{upload_id}/complete
    → Triggers processing
```

---

### Use Case 2: Image + Metadata Diagnosis

**Scenario:** Poor quality images need to be analyzed to diagnose why they failed quality control. The AI Model analyzes both the image (visual) and metadata (grade, score, farmer history) to produce a comprehensive diagnosis.

**Flow:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    DIAGNOSIS FLOW                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  EVENT: "collection.poor_quality_detected"                              │
│  { doc_id: "doc-001", farmer_id: "WM-4521", grade: "D", image_url }     │
│                          │                                              │
│                          ▼                                              │
│  AI MODEL - disease-diagnosis agent (Explorer/LangGraph)                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │  1. FETCH DATA (via MCP)                                         │   │
│  │     ┌─────────────────────────────────────────────────────────┐ │   │
│  │     │ Collection MCP:                                          │ │   │
│  │     │ • get_document(doc_id) → metadata, quality_issues        │ │   │
│  │     │ • get_image_base64(image_url) → image for vision LLM     │ │   │
│  │     │ • get_farmer_documents(farmer_id, 30d) → history         │ │   │
│  │     │                                                          │ │   │
│  │     │ Plantation MCP:                                          │ │   │
│  │     │ • get_farmer(farmer_id) → region, farm_size              │ │   │
│  │     │ • get_farmer_summary(farmer_id) → trends, past issues    │ │   │
│  │     └─────────────────────────────────────────────────────────┘ │   │
│  │                                                                  │   │
│  │  2. RAG QUERY (Pinecone)                                         │   │
│  │     Query: "tea leaf disease symptoms {grade} {quality_issues}"  │   │
│  │     Returns: Expert knowledge about diseases, treatments         │   │
│  │                                                                  │   │
│  │  3. VISION LLM ANALYSIS (Claude Sonnet)                          │   │
│  │     ┌─────────────────────────────────────────────────────────┐ │   │
│  │     │ Input:                                                   │ │   │
│  │     │ • [IMAGE] - tea leaf photo                               │ │   │
│  │     │ • Metadata: grade D, score 35, moisture_excess           │ │   │
│  │     │ • Farmer: Nyeri region, declining trend, 2 past fungal   │ │   │
│  │     │ • RAG: Disease symptoms, regional patterns               │ │   │
│  │     │                                                          │ │   │
│  │     │ Output:                                                  │ │   │
│  │     │ • condition: "fungal_infection"                          │ │   │
│  │     │ • sub_type: "cercospora_leaf_spot"                       │ │   │
│  │     │ • confidence: 0.87                                       │ │   │
│  │     │ • severity: "high"                                       │ │   │
│  │     │ • visual_evidence: ["brown spots", "yellow margins"]     │ │   │
│  │     │ • metadata_evidence: ["grade D aligns with fungal..."]   │ │   │
│  │     │ • recommendations: ["copper fungicide within 48h"]       │ │   │
│  │     └─────────────────────────────────────────────────────────┘ │   │
│  │                                                                  │   │
│  │  4. CONFIDENCE CHECK                                             │   │
│  │     confidence >= 0.7 → Output                                   │   │
│  │     confidence < 0.7 → Retry with more context (max 3x)         │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                          │                                              │
│                          ▼                                              │
│  EVENT: "ai.diagnosis.complete"                                         │
│  { doc_id, farmer_id, diagnosis: { condition, confidence, ... } }       │
│                          │                                              │
│                          ▼                                              │
│  KNOWLEDGE MODEL                                                        │
│  Stores diagnosis in Analysis DB (MongoDB)                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Agent Configuration:**

```yaml
agent:
  id: "disease-diagnosis"
  type: explorer                     # LangGraph

  input:
    event: "collection.poor_quality_detected"

  mcp_sources:
    - server: collection
      tools: [get_document, get_image_base64, get_farmer_documents]
    - server: plantation
      tools: [get_farmer, get_farmer_summary]

  llm:
    task_type: "diagnosis"
    model_override: "anthropic/claude-3-5-sonnet"  # Vision capable
    vision:
      enabled: true
    temperature: 0.3

  rag:
    enabled: true
    knowledge_domains: [plant_diseases, tea_cultivation, regional_patterns]
    top_k: 5

  workflow:
    max_iterations: 3
    confidence_threshold: 0.7
```

**Diagnosis Output Schema:**

```yaml
output_schema:
  condition: string           # Primary diagnosis
  sub_type: string            # Specific variant
  confidence: number          # 0.0 to 1.0
  severity: enum              # low, moderate, high, critical
  visual_evidence: string[]   # What was seen in the image
  metadata_evidence: string[] # Insights from grade, score, history
  contributing_factors: string[]
  recommendations: string[]
  urgency: enum               # immediate, within_48h, within_week, routine
```

---

### Use Case 3: Weekly Action Plan Generation

**Scenario:** Every Monday at 6 AM, the system generates personalized action plans for all farmers who had quality diagnoses in the past week. Each plan includes a detailed report (for experts) and a simplified message (for the farmer, in their preferred language).

**Flow:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                 WEEKLY ACTION PLAN GENERATION                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  STEP 1: Scheduled Trigger (Monday 6 AM)                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  DAPR Jobs → triggers Action Plan Model                          │   │
│  │  Action Plan Model queries Knowledge MCP:                        │   │
│  │  "Get farmers with diagnoses in past 7 days" → 47 farmers        │   │
│  │                                                                  │   │
│  │  For each farmer, emit event:                                    │   │
│  │  topic: "actionplan.generation.requested"                        │   │
│  │  { farmer_id: "WM-4521", week: "2025-W51" }                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                          │                                              │
│                          ▼                                              │
│  STEP 2: AI Model - Generator Agent (LangGraph)                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────────────┐  │   │
│  │  │ Fetch   │──▶│ Fetch   │──▶│ Priori- │──▶│ Generate Report │  │   │
│  │  │Diagnoses│   │ Context │   │  tize   │   │   (Detailed)    │  │   │
│  │  └─────────┘   └─────────┘   └─────────┘   └────────┬────────┘  │   │
│  │       │             │             │                  │           │   │
│  │  Knowledge     Plantation     By severity           │           │   │
│  │  MCP           MCP            & urgency              │           │   │
│  │  (3 diagnoses) (profile,                             │           │   │
│  │                 pref_lang)                           │           │   │
│  │                                                      ▼           │   │
│  │                                          ┌─────────────────────┐ │   │
│  │                                          │ Generate Farmer Msg │ │   │
│  │                                          │ (Simplified, 3 max  │ │   │
│  │                                          │  actions)           │ │   │
│  │                                          └──────────┬──────────┘ │   │
│  │                                                     │            │   │
│  │                                          ┌──────────▼──────────┐ │   │
│  │                                          │ Translate to        │ │   │
│  │                                          │ pref_lang (Swahili) │ │   │
│  │                                          └──────────┬──────────┘ │   │
│  │                                                     │            │   │
│  │                                          ┌──────────▼──────────┐ │   │
│  │                                          │ Check Length        │ │   │
│  │                                          │ (max 480 chars)     │ │   │
│  │                                          └──────────┬──────────┘ │   │
│  │                                              OK │    │ Too long  │   │
│  │                                                 │    └──▶ Simplify│  │
│  │                                                 ▼         & retry │  │
│  │                                          ┌─────────────────────┐ │   │
│  │                                          │ Output Both Formats │ │   │
│  │                                          └─────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                          │                                              │
│                          ▼                                              │
│  STEP 3: Result Published                                               │
│  topic: "ai.action_plan.complete"                                       │
│  {                                                                      │
│    farmer_id: "WM-4521",                                                │
│    detailed_report: { format: "markdown", content: "# Weekly..." },     │
│    farmer_message: { language: "sw", content: "Habari...", chars: 215 } │
│  }                                                                      │
│                          │                                              │
│                          ▼                                              │
│  STEP 4: Action Plan Model stores plan                                  │
│  → MongoDB (action_plans collection)                                    │
│  → Emits: "actionplan.ready_for_delivery"                               │
│                          │                                              │
│                          ▼                                              │
│  STEP 5: Notification Service delivers                                  │
│  → Reads pref_channel (SMS/WhatsApp)                                    │
│  → Sends farmer_message to farmer                                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Trigger Configuration (Action Plan Model):**

```yaml
triggers:
  - name: weekly-action-plan-generation
    type: schedule
    cron: "0 6 * * 1"              # Monday 6 AM
    workflow: "generate-action-plans"
```

**Generator Agent Configuration:**

```yaml
agent:
  id: "weekly-action-plan"
  type: generator                    # LangGraph

  mcp_sources:
    - server: knowledge
      tools: [get_farmer_analyses]
    - server: plantation
      tools: [get_farmer, get_farmer_summary, get_farmer_context]

  llm:
    task_type: "generation"
    model_override: "anthropic/claude-3-5-sonnet"
    temperature: 0.5

  rag:
    enabled: true
    knowledge_domains: [tea_cultivation, regional_practices, treatment_protocols]

  outputs:
    detailed_report:
      format: markdown
      audience: expert

    farmer_message:
      format: text
      audience: farmer
      localization:
        translate: true
        language_field: "farmer.pref_lang"
        simplification_field: "farmer.literacy_lvl"
      constraints:
        max_characters: 480
        max_actions: 3
```

**Dual Output Example:**

```json
{
  "detailed_report": {
    "format": "markdown",
    "content": "# Weekly Action Plan - WM-4521\n## Week 51, 2025\n\n### Priority Actions\n\n#### 1. Fungal Infection Treatment (HIGH)\n- Diagnosis: Cercospora leaf spot\n- Confidence: 87%\n- Action: Apply copper-based fungicide within 48 hours\n..."
  },

  "farmer_message": {
    "language": "sw",
    "content": "Habari John! Wiki hii tumegundua ugonjwa wa kuvu. Tafadhali: 1) Nyunyiza dawa ya kuvu ndani ya siku 2 2) Vuna baada ya saa 3 asubuhi. Maswali? Jibu ujumbe huu.",
    "character_count": 178,
    "sms_segments": 2
  }
}
```

---

### Use Case Summary

| Use Case | Trigger | Models Involved | Key Features |
|----------|---------|-----------------|--------------|
| **Batch ZIP Upload** | HTTP (QC Analyzer) | Collection | Resumable upload, checksum, expand to documents |
| **Image Diagnosis** | Event (per image) | Collection → AI → Knowledge | Vision LLM, RAG, confidence retry |
| **Weekly Action Plan** | Schedule (Monday 6 AM) | Action Plan → AI → Notification | Dual output, translation, length check |

### Event Flow Summary

```
BATCH UPLOAD:
QC Analyzer ──HTTP──▶ Collection ──event──▶ DAPR Pub/Sub (N events)

DIAGNOSIS:
Collection event ──▶ AI Model ──MCP──▶ Collection, Plantation
                         │
                         └──event──▶ Knowledge (stores)

ACTION PLAN:
DAPR Jobs ──▶ Action Plan ──event──▶ AI Model ──MCP──▶ Knowledge, Plantation
                                         │
                                         └──event──▶ Action Plan ──event──▶ Notification
```