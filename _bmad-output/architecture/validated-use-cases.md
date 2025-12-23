# Validated Use Cases

This section documents key use cases traced through the architecture to validate the design.

## Use Case 1: Batch ZIP Upload (Poor Quality Images)

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
│  { doc_id, farmer_id, factory_id, collection_point_id,                  │
│    classification: "secondary", leaf_type_distribution, image_url }     │
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

## Use Case 2: Image + Metadata Diagnosis

**Scenario:** Poor quality images need to be analyzed to diagnose why they failed quality control. The AI Model analyzes both the image (visual) and metadata (grade, score, farmer history) to produce a comprehensive diagnosis.

**Flow:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    DIAGNOSIS FLOW                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  EVENT: "collection.poor_quality_detected"                              │
│  { doc_id: "doc-001", farmer_id: "WM-4521", collection_point_id: "nyeri-cp-001", │
│    classification: "secondary", leaf_type_distribution: {...}, image_url }      │
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
│  │     │ • get_farmer(farmer_id) → region, farm_size_hectares,   │ │   │
│  │     │                           farm_scale (smallholder/       │ │   │
│  │     │                           medium/estate)                 │ │   │
│  │     │ • get_farmer_summary(farmer_id) → trends, past issues,  │ │   │
│  │     │                                   yield_kg_per_hectare,  │ │   │
│  │     │                                   yield_vs_regional_avg  │ │   │
│  │     │ • get_collection_point(cp_id) → factory, operating_hours│ │   │
│  │     └─────────────────────────────────────────────────────────┘ │   │
│  │                                                                  │   │
│  │  2. RAG QUERY (Pinecone)                                         │   │
│  │     Query: "tea leaf disease {classification} {leaf_types}"      │   │
│  │     Returns: Expert knowledge about diseases, treatments         │   │
│  │                                                                  │   │
│  │  3. VISION LLM ANALYSIS (Claude Sonnet)                          │   │
│  │     ┌─────────────────────────────────────────────────────────┐ │   │
│  │     │ Input:                                                   │ │   │
│  │     │ • [IMAGE] - tea leaf photo                               │ │   │
│  │     │ • TBK Classification: secondary (80% primary)            │ │   │
│  │     │ • Leaf types: coarse_leaf (15), banji (5)                │ │   │
│  │     │ • Farmer: Nyeri, smallholder (0.8 ha), declining yield   │ │   │
│  │     │ • RAG: Disease symptoms, regional patterns               │ │   │
│  │     │                                                          │ │   │
│  │     │ Output:                                                  │ │   │
│  │     │ • condition: "fungal_infection"                          │ │   │
│  │     │ • sub_type: "cercospora_leaf_spot"                       │ │   │
│  │     │ • confidence: 0.87                                       │ │   │
│  │     │ • severity: "high"                                       │ │   │
│  │     │ • visual_evidence: ["brown spots", "yellow margins"]     │ │   │
│  │     │ • metadata_evidence: ["coarse_leaf elevated suggests..."]│ │   │
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
│  { doc_id, farmer_id, collection_point_id,                              │
│    diagnosis: { condition, confidence, ... } }                          │
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

## Use Case 3: Weekly Action Plan Generation

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
│  │  │Diagnoses│   │ Context │   │  tize   │   │ (Scale-Aware)   │  │   │
│  │  └─────────┘   └─────────┘   └─────────┘   └────────┬────────┘  │   │
│  │       │             │             │                  │           │   │
│  │  Knowledge     Plantation     By severity           │           │   │
│  │  MCP           MCP            & urgency              │           │   │
│  │  (3 diagnoses) (farm_scale,                          │           │   │
│  │                 yield metrics,                       │           │   │
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
      tools: [get_farmer_analyses, get_recent_diagnoses]
    - server: plantation
      tools: [get_farmer, get_farmer_summary, get_farmer_context]
      # Returns: farm_scale, farm_size_hectares, yield_kg_per_hectare,
      #          yield_vs_regional_avg, yield_percentile

  llm:
    task_type: "generation"
    model_override: "anthropic/claude-3-5-sonnet"
    temperature: 0.5

  rag:
    enabled: true
    knowledge_domains: [tea_cultivation, regional_practices, treatment_protocols]

  # Farm-Scale-Aware Recommendations
  # Recommendations are adapted based on farm_scale:
  scale_adaptations:
    smallholder:        # <1 ha
      - Focus on low-cost, manual solutions
      - Emphasize timing over equipment
      - Simple, actionable steps only
    medium:             # 1-5 ha
      - Balance cost vs efficiency
      - Include labor optimization tips
    estate:             # >5 ha
      - Include mechanization options
      - Reference bulk purchasing
      - Suggest systematic monitoring

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

## Use Case 4: Weather Data Pull and Correlation

**Scenario:** The platform proactively fetches weather data from external APIs (pull mode) to correlate with quality issues. When poor quality is detected, the system checks weather history to determine if weather events contributed to the problem.

**Flow:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    WEATHER PULL MODE FLOW                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  STEP 1: Scheduled Weather Fetch (Daily 5 AM via DAPR Jobs)            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Collection Model (Pull Mode)                                    │   │
│  │  1. Query configured weather sources for all factory regions    │   │
│  │  2. For each region:                                             │   │
│  │     GET https://api.openmeteo.com/v1/forecast?...                │   │
│  │     → temperature, precipitation, humidity, wind                 │   │
│  │  3. Store weather documents → MongoDB (weather_observations)    │   │
│  │  4. Emit event: "collection.weather.updated"                     │   │
│  │     { region_id, date, weather_summary }                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  STEP 2: Weather Impact Analysis (triggered by poor quality event)     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  EVENT: "collection.poor_quality_detected"                       │   │
│  │  { farmer_id: "WM-4521", collection_point_id: "nyeri-cp-001",   │   │
│  │    classification: "secondary", ... }                            │   │
│  │                          │                                       │   │
│  │                          ▼                                       │   │
│  │  AI MODEL - Weather Analyzer Agent (LangGraph)                   │   │
│  │  ┌─────────────────────────────────────────────────────────────┐ │   │
│  │  │ 1. FETCH DATA (via MCP)                                      │ │   │
│  │  │    Collection MCP:                                           │ │   │
│  │  │    • get_weather_history(region_id, days=7)                  │ │   │
│  │  │      → Returns: precipitation, frost events, humidity        │ │   │
│  │  │                                                              │ │   │
│  │  │ 2. APPLY LAG CORRELATION                                     │ │   │
│  │  │    ┌─────────────────────────────────────────────────────┐   │ │   │
│  │  │    │ Weather Event │ Impact Window │ Quality Impact      │   │ │   │
│  │  │    │───────────────│───────────────│─────────────────────│   │ │   │
│  │  │    │ Heavy rain    │ Days 3-5      │ Moisture, fungal    │   │ │   │
│  │  │    │ Frost (<2°C)  │ Days 3-5      │ Leaf damage         │   │ │   │
│  │  │    │ Drought       │ Days 4-7      │ Stress, stunting    │   │ │   │
│  │  │    │ High humidity │ Days 2-4      │ Fungal, pests       │   │ │   │
│  │  │    └─────────────────────────────────────────────────────┘   │ │   │
│  │  │                                                              │ │   │
│  │  │ 3. OUTPUT                                                    │ │   │
│  │  │    • weather_correlation: true/false                         │ │   │
│  │  │    • contributing_event: "heavy_rain_52mm_4days_ago"         │ │   │
│  │  │    • confidence: 0.78                                        │ │   │
│  │  └─────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                          │                                              │
│                          ▼                                              │
│  EVENT: "ai.weather_impact.complete"                                   │
│  { farmer_id, collection_point_id, weather_correlation,               │
│    contributing_event, confidence }                                    │
│                          │                                              │
│                          ▼                                              │
│  KNOWLEDGE MODEL                                                        │
│  Stores weather impact analysis in Analysis DB                         │
│  (Enriches disease diagnosis with weather context)                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Pull Source Configuration (Collection Model):**

```yaml
pull_sources:
  weather-openmeteo:
    schedule: "0 5 * * *"        # Daily 5 AM
    regions_from: plantation     # Get regions from Plantation Model

    api:
      base_url: https://api.open-meteo.com/v1/forecast
      params:
        hourly: temperature_2m,precipitation,relative_humidity_2m
        past_days: 7
        forecast_days: 3

    processing:
      normalize: true
      aggregate_to: daily

    storage:
      mongo_collection: weather_observations
      ttl_days: 90

    events:
      on_complete:
        topic: "collection.weather.updated"
```

**Weather Analyzer Agent Configuration:**

```yaml
agent:
  id: "weather-impact-analyzer"
  type: analyzer                    # LangGraph

  trigger:
    event: "collection.poor_quality_detected"
    # Runs in parallel with disease-diagnosis agent

  mcp_sources:
    - server: collection
      tools: [get_weather_history]
    - server: plantation
      tools: [get_farmer]           # For region lookup

  llm:
    task_type: "analysis"
    model_override: null            # Use default (Haiku for cost)

  correlation:
    lag_window_days: 7
    day_weights:                    # 3-5 day lag strongest
      day_0: 0.05
      day_1: 0.10
      day_2: 0.20
      day_3: 0.35
      day_4: 0.35
      day_5: 0.30
      day_6: 0.15
      day_7: 0.05
```

---

## Use Case Summary

| Use Case | Trigger | Models Involved | Key Features |
|----------|---------|-----------------|--------------|
| **Batch ZIP Upload** | HTTP (QC Analyzer) | Collection | Resumable upload, checksum, expand to documents |
| **Image Diagnosis** | Event (per image) | Collection → AI → Knowledge | Vision LLM, RAG, TBK classification |
| **Weekly Action Plan** | Schedule (Monday 6 AM) | Action Plan → AI → Notification | Farm-scale-aware, translation, length check |
| **Weather Pull & Correlation** | Schedule (5 AM) + Event | Collection (pull) → AI → Knowledge | Lag correlation, weather impact enrichment |

## Event Flow Summary

```
BATCH UPLOAD (Push Mode):
QC Analyzer ──HTTP──▶ Collection ──event──▶ DAPR Pub/Sub (N events)

WEATHER FETCH (Pull Mode):
DAPR Jobs (5 AM) ──▶ Collection ──API──▶ Weather Service
                          │
                          └──event──▶ "collection.weather.updated"

DIAGNOSIS (parallel analyzers):
Collection event ──▶ AI Model ──MCP──▶ Collection, Plantation
  "poor_quality"         │
                    ┌────┴────┐
                    ▼         ▼
              Disease    Weather
              Analyzer   Analyzer
                    │         │
                    └────┬────┘
                         ▼
                    Knowledge (stores merged diagnosis)

ACTION PLAN:
DAPR Jobs ──▶ Action Plan ──event──▶ AI Model ──MCP──▶ Knowledge, Plantation
                                         │
                                         └──event──▶ Action Plan ──event──▶ Notification
```

---
