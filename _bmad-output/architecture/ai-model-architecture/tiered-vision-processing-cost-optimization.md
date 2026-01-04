# Tiered Vision Processing (Cost Optimization)

To optimize vision model costs at scale, the Disease Diagnosis workflow uses a two-tier approach with **two agents**.

> **Implementation details:** See `ai-model-developer-guide/8-performance.md` for image preprocessing, batching strategies, and token efficiency.

## Thumbnail Generation (Collection Model Responsibility)

**Key Decision:** Collection Model generates thumbnails at ingestion time, not AI Model on-demand.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    IMAGE INGESTION FLOW                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  QC Analyzer ──────► Collection Model                                   │
│  (sends image)            │                                             │
│                           │ 1. Store original image                     │
│                           │ 2. Generate thumbnail (256x256, JPEG 60%)   │
│                           │ 3. Store thumbnail                          │
│                           ▼                                             │
│                    Azure Blob Storage                                   │
│                    ┌─────────────────────────────────────────────┐     │
│                    │  /documents/{doc_id}/                       │     │
│                    │  ├── original.jpg    (full resolution)      │     │
│                    │  └── thumbnail.jpg   (256x256)              │     │
│                    └─────────────────────────────────────────────┘     │
│                           │                                             │
│                           │ 4. Store metadata in MongoDB                │
│                           ▼                                             │
│                    ┌─────────────────────────────────────────────┐     │
│                    │  { doc_id, original_url, thumbnail_url,     │     │
│                    │    thumbnail_generated: true }              │     │
│                    └─────────────────────────────────────────────┘     │
│                           │                                             │
│                           │ 5. Publish event                            │
│                           ▼                                             │
│                    Event: collection.document.received                  │
│                    Payload: { doc_id, has_thumbnail: true }             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Why Collection Model owns thumbnail generation:**

| Aspect | Rationale |
|--------|-----------|
| **Done once** | Generated at ingestion, reused for all analysis |
| **No wasted bandwidth** | AI Model fetches only what it needs |
| **Separation of concerns** | Collection owns blob storage, AI owns analysis |
| **40% savings** | "Healthy" images never need full image fetch |

## Tiered Processing Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    TIERED VISION PROCESSING                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Event: collection.poor_quality_detected                                │
│  Payload: { doc_id, thumbnail_url, original_url }                       │
│                          │                                              │
│                          ▼                                              │
│  TIER 1: vision-screen (Extractor, Haiku)                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Input: Fetch THUMBNAIL only (256x256) + basic metadata         │   │
│  │  Cost: ~$0.001/image                                            │   │
│  │                                                                  │   │
│  │  Classification:                                                 │   │
│  │    • "healthy" (40%)         → Skip, log as no_issue            │   │
│  │    • "obvious_issue" (25%)   → Metadata-based diagnosis (Haiku) │   │
│  │    • "needs_expert" (35%)    → Escalate to Tier 2               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                          │                                              │
│              ┌───────────┴───────────┬───────────────┐                 │
│              ▼                       ▼               ▼                  │
│         "healthy"            "obvious_issue"   "needs_expert"          │
│              │                       │               │                  │
│              ▼                       ▼               ▼                  │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐      │
│  │  No diagnosis   │   │  Haiku analysis │   │  TIER 2: SONNET │      │
│  │  needed         │   │  metadata-only  │   │  Full analysis  │      │
│  │  conf: 0.9      │   │  conf: 0.7-0.85 │   │  conf: 0.85+    │      │
│  └─────────────────┘   └─────────────────┘   └─────────────────┘      │
│                                                     │                  │
│                                                     ▼                  │
│                         disease-diagnosis (Explorer, Sonnet)           │
│                         ┌─────────────────────────────────────────┐   │
│                         │  Input: Fetch ORIGINAL image            │   │
│                         │         + farmer context (MCP)          │   │
│                         │         + RAG knowledge                 │   │
│                         │  Cost: ~$0.012/image                    │   │
│                         └─────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Agent Types Summary

| Tier | Agent ID | Agent Type | Model | Fetches | Purpose |
|------|----------|------------|-------|---------|---------|
| **1** | `vision-screen` | Extractor | Haiku | Thumbnail only | Fast screening, routing |
| **2** | `disease-diagnosis` | Explorer | Sonnet | Original + context | Deep analysis with RAG |

## Cost Impact at Scale (10,000 images/day)

| Approach | Calculation | Daily Cost | Annual Cost |
|----------|-------------|------------|-------------|
| **All Sonnet** | 10,000 × $0.012 | $120 | ~$43,800 |
| **Tiered** | 10,000 × $0.001 + 3,500 × $0.012 | $52 | ~$19,000 |
| **Savings** | | **57%** | **~$24,800** |

**Additional bandwidth savings:** 40% of images ("healthy") never require full image fetch.

## Tier 1 Screening Agent

```yaml
agent:
  id: "vision-screen"
  type: extractor
  version: "1.0.0"
  description: "Fast screening of quality images using thumbnail"

  input:
    event: "collection.poor_quality_detected"
    schema:
      required: [doc_id, thumbnail_url]
      optional: [original_url, metadata]

  # Fetches thumbnail from Collection MCP (pre-generated by Collection Model)
  mcp_sources:
    - server: collection
      tools: [get_document_thumbnail]

  llm:
    model: "anthropic/claude-3-haiku"
    temperature: 0.1
    max_tokens: 200

  output:
    event: "ai.vision_screen.complete"
    schema:
      classification: enum           # healthy, obvious_issue, needs_expert
      confidence: number
      reason: string
      route_to: string               # null, "haiku-metadata", "disease-diagnosis"
```

**Routing Logic:**

| Screen Result | Confidence | Action |
|---------------|------------|--------|
| `healthy` | ≥ 0.85 | Log as no_issue, no further analysis |
| `healthy` | < 0.85 | Escalate to Tier 2 (uncertain) |
| `obvious_issue` | ≥ 0.75 | Haiku metadata analysis (no vision) |
| `obvious_issue` | < 0.75 | Escalate to Tier 2 |
| `needs_expert` | any | Always Tier 2 (Sonnet + vision) |
