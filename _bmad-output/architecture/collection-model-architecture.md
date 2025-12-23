# Collection Model Architecture

## Overview

The Collection Model is the **data gateway** for the Farmer Power Cloud Platform. It collects data from external sources using two modes: **push** (sources send data to platform) and **pull** (platform requests data from sources). All data flows through an intelligent ingestion pipeline and is made available to downstream consumers.

**Core Responsibility:** Collect, validate, transform, link, store, and serve documents.

**Does NOT:** Generate action plans, make business decisions, or verify farmer existence.

## Data Collection Modes

The platform supports two data collection patterns:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    DATA COLLECTION MODES                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  PUSH MODE (Source → Platform)                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │  ┌──────────────┐      webhook/API      ┌──────────────────┐    │   │
│  │  │ QC Analyzer  │ ────────────────────▶ │ Collection Model │    │   │
│  │  │ Factory POS  │      (event-driven)   │ /api/v1/ingest/* │    │   │
│  │  │ Mobile App   │                       └──────────────────┘    │   │
│  │  └──────────────┘                                               │   │
│  │                                                                  │   │
│  │  Characteristics:                                                │   │
│  │  • Source initiates data transfer                                │   │
│  │  • Real-time or near-real-time                                   │   │
│  │  • Platform reacts to incoming events                            │   │
│  │  • Requires source integration/configuration                     │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  PULL MODE (Platform → Source)                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │  ┌──────────────────┐     API request    ┌──────────────────┐   │   │
│  │  │ Collection Model │ ──────────────────▶│ Weather API      │   │   │
│  │  │ (Dapr Job)       │     (scheduled)    │ Market Price API │   │   │
│  │  │                  │◀────────────────── │ Exchange Rates   │   │   │
│  │  └──────────────────┘     response       └──────────────────┘   │   │
│  │                                                                  │   │
│  │  Characteristics:                                                │   │
│  │  • Platform initiates data request                               │   │
│  │  • Scheduled (daily, hourly) or on-demand                        │   │
│  │  • Platform controls timing and frequency                        │   │
│  │  • External API credentials managed by platform                  │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### When to Use Each Mode

| Criteria | Push Mode | Pull Mode |
|----------|-----------|-----------|
| **Data timing** | Real-time events as they happen | Periodic snapshots or aggregates |
| **Source control** | You control/configure the source | Third-party API you call |
| **Volume** | High-frequency individual events | Batch or aggregated data |
| **Examples** | Grading results, quality events, deliveries | Weather data, market prices, exchange rates |
| **Trigger** | Source event occurs | Schedule or platform need |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         COLLECTION MODEL                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  PUSH SOURCES                              PULL SOURCES                 │
│  ┌─────────────────┐                      ┌─────────────────┐          │
│  │ QC Analyzer     │──┐                ┌──│ Weather API     │          │
│  │ Factory POS     │──┼── webhook ──▶  │  │ Market Prices   │          │
│  │ Mobile App      │──┘                │  │ Exchange Rates  │          │
│  └─────────────────┘                   │  └─────────────────┘          │
│                                        │           ▲                    │
│                    ┌───────────────────┘           │ scheduled          │
│                    ▼                               │ API calls          │
│           ┌────────────────────────────────────────┴────────┐          │
│           │              INGEST PIPELINE                     │          │
│           │                                                  │          │
│           │  ┌──────────┐  ┌──────────┐  ┌──────────┐       │          │
│           │  │ Schema   │  │   LLM    │  │  Store   │       │          │
│           │  │ Validate │─▶│ Extract  │─▶│ Document │       │          │
│           │  │          │  │+Validate │  │          │       │          │
│           │  └──────────┘  └──────────┘  └──────────┘       │          │
│           └─────────────────────────────────────────────────┘          │
│                                    │                                    │
│                    ┌───────────────┼───────────────┐                   │
│                    ▼               ▼               ▼                   │
│               ┌────────┐     ┌────────┐     ┌────────┐                │
│               │Query   │     │Search  │     │  MCP   │                │
│               │  API   │     │  API   │     │ Server │                │
│               └────────┘     └────────┘     └────────┘                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Push Mode Sources

Push sources send data to the platform via webhooks or API calls. Each source is configured with its own ingestion rules:

```yaml
# Push Source: QC Analyzer
source: qc-analyzer
  mode: push
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

### Push Source Registry

| Source | Endpoint | Events | Data Type |
|--------|----------|--------|-----------|
| **QC Analyzer** | `/api/v1/ingest/qc-analyzer` | END_BAG, POOR_QUALITY_DETECTED | Quality grading results |
| **Factory POS** | `/api/v1/ingest/factory-pos` | DELIVERY_RECORDED, PAYMENT_ISSUED | Delivery and payment records |
| **Mobile App** | `/api/v1/ingest/mobile-app` | FARMER_CHECKIN, PHOTO_SUBMITTED | Farmer-submitted data |

## Pull Mode Sources

Pull sources are external APIs that the platform queries on a schedule. The platform initiates the request and processes the response through the same ingestion pipeline.

```yaml
# Pull Source: Weather API
source: weather-api
  mode: pull
  provider: open-meteo              # or: openweathermap, visual-crossing
  schedule: "0 6 * * *"             # Daily at 6 AM (Dapr Job)

  request:
    base_url: "https://api.open-meteo.com/v1/forecast"
    auth_type: api_key              # api_key | oauth2 | none
    parameters:
      latitude: "{region.center_lat}"    # Templated from Region entity
      longitude: "{region.center_lng}"
      daily: ["temperature_2m_max", "temperature_2m_min", "precipitation_sum", "rain_sum"]
      past_days: 7
      timezone: "Africa/Nairobi"

  iteration:
    foreach: regions                # Pull for each region
    source: plantation_mcp          # Get region list from Plantation Model

  transformation:
    agent: weather-extraction-agent
    extract_fields:
      - region_id
      - date
      - temp_max
      - temp_min
      - precipitation_mm
      - humidity_avg
    link_field: region_id

  storage:
    blob_container: weather-data
    mongo_collection: weather_index

  retry:
    max_attempts: 3
    backoff: exponential
```

```yaml
# Pull Source: Market Prices
source: market-prices
  mode: pull
  provider: internal-market-api     # Or external commodity exchange
  schedule: "0 8 * * 1"             # Weekly Monday 8 AM

  request:
    base_url: "https://market-api.example.com/v1/prices"
    auth_type: oauth2
    parameters:
      commodity: "tea"
      market: "mombasa_auction"
      date_range: "last_7_days"

  transformation:
    agent: market-extraction-agent
    extract_fields:
      - commodity
      - market
      - date
      - price_per_kg
      - volume_traded
      - grade_breakdown

  storage:
    blob_container: market-data
    mongo_collection: market_prices_index
```

### Pull Source Registry

| Source | Provider | Schedule | Data Type | Iteration |
|--------|----------|----------|-----------|-----------|
| **Weather API** | Open-Meteo | Daily 6 AM | Temperature, precipitation, humidity | Per region |
| **Market Prices** | Mombasa Auction API | Weekly Monday | Tea auction prices | Single call |
| **Exchange Rates** | Central Bank API | Daily 7 AM | KES/USD rates | Single call |

### Pull Mode Scheduling (Dapr Jobs)

```yaml
# dapr/jobs/weather-pull.yaml
apiVersion: dapr.io/v1alpha1
kind: Job
metadata:
  name: weather-data-pull
spec:
  schedule: "0 6 * * *"
  job:
    spec:
      template:
        spec:
          containers:
            - name: pull-weather
              image: farmer-power/collection-puller:latest
              env:
                - name: SOURCE_CONFIG
                  value: "weather-api"
          restartPolicy: OnFailure
```

### Pull Mode Error Handling

| Scenario | Handling |
|----------|----------|
| **API timeout** | Retry with exponential backoff (max 3 attempts) |
| **Rate limited** | Respect Retry-After header, queue for later |
| **Partial data** | Store what's available, flag incomplete |
| **API down** | Alert ops, use cached data if available |
| **Invalid response** | Log error, skip this pull cycle |

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
| `get_regional_weather` | Get weather data for a region | `region_id`, `days?` (default 7) |
| `get_market_prices` | Get market price data | `commodity?`, `market?`, `date_range?` |
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

## Data Flow Examples

### Push Mode Example (QC Analyzer)

```
QC Analyzer sends END_BAG event:
{
  "event_type": "END_BAG",
  "bag_id": "BAG-2025-001234",
  "farmer_id": "WM-4521",
  "factory_id": "KEN-FAC-001",
  "collection_point_id": "nyeri-cp-001",
  "timestamp": "2025-12-23T08:32:15Z",

  "grading_model_id": "tbk_kenya_tea_v1",
  "grading_model_version": "1.0.0",

  "leaf_classifications": [
    {
      "leaf_id": 1,
      "predictions": {
        "leaf_type": { "class": "two_leaves_bud", "confidence": 0.94 },
        "coarse_subtype": { "class": "none", "confidence": 0.99 },
        "banji_hardness": { "class": "soft", "confidence": 0.97 }
      },
      "grade": "primary",
      "grade_score": 1.0
    },
    {
      "leaf_id": 2,
      "predictions": {
        "leaf_type": { "class": "coarse_leaf", "confidence": 0.89 },
        "coarse_subtype": { "class": "hard_leaf", "confidence": 0.82 },
        "banji_hardness": { "class": "soft", "confidence": 0.95 }
      },
      "grade": "secondary",
      "grade_score": 0.0
    }
    // ... more leaf classifications
  ],

  "bag_summary": {
    "total_leaves": 150,
    "primary_count": 120,
    "secondary_count": 30,
    "primary_percentage": 80.0,
    "secondary_percentage": 20.0,

    "leaf_type_distribution": {
      "bud": 15,
      "one_leaf_bud": 45,
      "two_leaves_bud": 50,
      "three_plus_leaves_bud": 10,
      "single_soft_leaf": 10,
      "coarse_leaf": 15,
      "banji": 5
    },
    "coarse_subtype_distribution": {
      "double_luck": 3,
      "maintenance_leaf": 7,
      "hard_leaf": 5
    },
    "banji_distribution": {
      "soft": 3,
      "hard": 2
    }
  }
}

Collection Model processes:
1. Schema validation ✓
2. LLM extracts: farmer_id, collection_point_id, factory_id, bag_summary
3. LLM validates: primary_count + secondary_count = total_leaves ✓
4. Store: Blob (raw) + Mongo (index with farmer_ref, cp_ref, factory_ref)
5. Emit event: collection.document_stored
6. Available via Query API, Search API, MCP

Downstream consumer (Action Plan Model):
- Calls MCP: get_farmer_documents("WM-4521", last_7_days)
- Receives quality history with full TBK grading details
- Generates personalized action plan based on leaf_type distribution trends
```

**TBK Grading Model Reference:**

The Tea Board of Kenya (TBK) model is a **binary classification** (Primary/Secondary) based on leaf type:

| Leaf Type | Grade | Description |
|-----------|-------|-------------|
| `bud` | Primary | Unopened leaf tip, highest quality |
| `one_leaf_bud` | Primary | One open leaf + bud (fine plucking) |
| `two_leaves_bud` | Primary | Two open leaves + bud (standard fine plucking) |
| `three_plus_leaves_bud` | Secondary | Coarse plucking |
| `single_soft_leaf` | Primary | Tender young leaf |
| `coarse_leaf` | Secondary | Mature, fibrous leaves (subtypes: double_luck, maintenance_leaf, hard_leaf) |
| `banji` (soft) | Primary | Dormant but pliable shoot |
| `banji` (hard) | Secondary | Dormant and rigid shoot |

> **Full specification:** See [`tbk-kenya-tea-grading-model-specification.md`](../analysis/tbk-kenya-tea-grading-model-specification.md)

### Pull Mode Example (Weather API)

```
Dapr Job triggers daily at 6 AM:

Collection Model initiates pull:
1. Query Plantation MCP: list_regions() → [region-1, region-2, ...]
2. For each region:
   a. Build request: GET api.open-meteo.com/v1/forecast?lat={lat}&lng={lng}&past_days=7
   b. Receive response:
      {
        "daily": {
          "temperature_2m_max": [28, 27, 29, ...],
          "precipitation_sum": [0, 12, 45, ...],
          ...
        }
      }
   c. LLM extracts: region_id, date, temp_max, precipitation_mm
   d. Store: Blob (raw) + Mongo (index with region_ref)
   e. Emit event: collection.weather_updated

Downstream consumer (Knowledge Model - Weather Analyzer):
- Calls MCP: get_regional_weather("region-1", last_7_days)
- Correlates weather with quality issues
- Generates weather-related diagnoses
```

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Core Role** | Data gateway | Unified ingestion for all external data |
| **Collection Modes** | Push + Pull | Different sources need different patterns |
| **Push Mode** | Webhook endpoints | Real-time events from controlled sources |
| **Pull Mode** | Scheduled Dapr Jobs | Periodic data from third-party APIs |
| **Pipeline Unification** | Same pipeline for both modes | Consistent validation, extraction, storage |
| **LLM Extraction** | All sources use LLM | Handles format variations, semantic validation |
| **Trust Model** | Trust source IDs | No cross-model verification on ingest |
| **Storage** | Blob + Mongo | Immutable raw + queryable index |

---
