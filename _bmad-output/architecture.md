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

> **STATUS: PENDING** - To be documented after Market Analysis Model discussion.