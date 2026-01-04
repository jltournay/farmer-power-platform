# 3. Agent Development

## Creating a New Agent: Step-by-Step

### Step 1: Choose Agent Type

Determine which type fits your use case:

| If you need to... | Use Type |
|-------------------|----------|
| Extract structured data from documents | Extractor |
| Analyze, diagnose, find patterns | Explorer |
| Create content, reports, messages | Generator |
| Handle multi-turn dialogue with users | Conversational |
| Cost-optimized image analysis (screen → diagnose) | Tiered-Vision |

### Step 2: Create Instance Configuration

Create YAML file in `src/agents/instances/{type}s/`:

```yaml
# src/agents/instances/explorers/new-analysis.yaml
agent:
  id: "new-analysis"
  type: explorer
  version: "1.0.0"
  description: "Describe what this agent does"

  input:
    event: "domain.event.name"
    schema:
      required: [doc_id, farmer_id]
      optional: [additional_field]

  output:
    event: "ai.new_analysis.complete"
    schema:
      fields: [result_field_1, result_field_2]

  mcp_sources:
    - server: collection
      tools: [get_document]
    - server: plantation
      tools: [get_farmer]

  llm:
    model: "anthropic/claude-3-5-sonnet"   # Explicit model per agent
    temperature: 0.3
    max_tokens: 2000

  prompt:
    system_file: "prompts/explorers/new-analysis/system.md"
    template_file: "prompts/explorers/new-analysis/template.md"
    output_format: "json"
    output_schema:
      type: object
      properties:
        result_field_1: { type: string }
        result_field_2: { type: number }

  rag:
    enabled: true
    query_template: "relevant query {{input_field}}"
    knowledge_domains: [relevant_domain]
    top_k: 5

  error_handling:
    retry:
      max_attempts: 3
      backoff_ms: [100, 500, 2000]
    on_failure: "publish_error_event"
```

### Step 3: Create Prompts

Create prompt files:

```markdown
<!-- prompts/explorers/new-analysis/system.md -->
You are an expert analyst for the Farmer Power platform.

Your role is to [describe specific responsibility].

# Guidelines
- Be specific and actionable
- Include confidence levels
- Consider regional and seasonal factors

# Output Format
Respond in JSON format with the following structure:
{
  "result_field_1": "string description",
  "result_field_2": 0.0 to 1.0 confidence score
}
```

```markdown
<!-- prompts/explorers/new-analysis/template.md -->
# Input Document
{{document}}

# Farmer Context
{{farmer_context}}

# Expert Knowledge
{{rag_context}}

# Task
Analyze the above information and provide your assessment.
```

### Step 4: Register Event Subscription

Add trigger configuration in the domain model that owns this analysis:

```yaml
# In domain model configuration
triggers:
  - name: new-analysis-trigger
    type: event
    event: "domain.event.name"
    workflow: "new-analysis"
```

### Step 5: Test with Golden Samples

Create test data:

```json
// tests/golden_samples/explorers/new-analysis/input_001.json
{
  "doc_id": "test-doc-001",
  "farmer_id": "WM-TEST-001",
  "document": { /* mock document */ },
  "farmer_context": { /* mock context */ }
}
```

```json
// tests/golden_samples/explorers/new-analysis/expected_001.json
{
  "result_field_1": "expected value",
  "result_field_2": 0.85
}
```

## Agent Development Checklist

- [ ] Agent type selected based on use case
- [ ] Instance YAML created with all required fields
- [ ] System prompt created (clear role, guidelines, output format)
- [ ] Template prompt created (context injection points)
- [ ] MCP sources identified and configured
- [ ] RAG domains identified (if applicable)
- [ ] Input/output event schemas defined
- [ ] Error handling configured
- [ ] Golden sample tests created
- [ ] Trigger registered in domain model

**Additional for Tiered-Vision agents:**
- [ ] Both `tiered_llm.screen` and `tiered_llm.diagnose` configured
- [ ] Routing thresholds tuned for use case
- [ ] Thumbnail MCP tool available (collection.get_document_thumbnail)
- [ ] Original image MCP tool available (collection.get_document_original)
- [ ] Golden samples include test cases for all routing paths

## Advanced Patterns

### Triage Agent Pattern

For cost optimization, use a fast triage agent (Haiku) before invoking expensive analyzers (Sonnet):

```
┌───────────────────────────────────────────────────────────────────┐
│                     TRIAGE-FIRST PATTERN                          │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│   QC Event ──► Triage (Haiku) ──┬──► High Confidence (≥0.7)      │
│                   ~$0.001        │    Route to single analyzer    │
│                   ~200ms         │                                │
│                                  └──► Low Confidence (<0.7)       │
│                                       Invoke parallel analyzers   │
│                                                                   │
│   Result: 60-70% of events skip expensive parallel analysis      │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

**Triage Agent Configuration:**

```yaml
# src/agents/instances/triage/quality-triage.yaml
agent:
  id: "quality-triage"
  type: extractor  # Simple classification, use LangChain
  version: "1.0.0"
  description: "Fast classification of quality issues for routing"

  llm:
    model: "anthropic/claude-3-haiku"   # Fast, cheap for triage
    temperature: 0.1                     # Low temperature for consistent classification
    max_tokens: 200                      # Short response

  prompt:
    system_file: "prompts/triage/quality/system.md"
    template_file: "prompts/triage/quality/template.md"
    output_format: "json"
    output_schema:
      type: object
      properties:
        classification:
          type: string
          enum: [disease, weather, harvest, pest, nutrition, processing, unknown]
        confidence:
          type: number
          minimum: 0
          maximum: 1
        route_to:
          type: array
          items:
            type: string
        also_check:
          type: array
          items:
            type: string
          description: "Secondary analyzers to run if uncertain"

  # Few-shot examples improve triage accuracy
  few_shot:
    enabled: true
    examples_file: "prompts/triage/quality/examples.yaml"
    max_examples: 5
```

**Triage Prompt with Few-Shot Examples:**

```markdown
<!-- prompts/triage/quality/system.md -->
You are a fast quality issue classifier for tea leaf analysis.

Your job is to quickly categorize the issue type and route to the appropriate analyzer.

# Classification Categories
- disease: Fungal, bacterial, or viral infections
- weather: Damage from rain, frost, drought, or extreme temperatures
- harvest: Timing, technique, or handling issues
- pest: Insect or animal damage
- nutrition: Soil deficiency or fertilizer issues
- processing: Factory handling problems
- unknown: Cannot determine from available information

# Output Rules
- Be decisive - pick the most likely category
- Set confidence based on how clear the symptoms are
- If confidence < 0.7, add secondary categories to also_check
- route_to contains the primary analyzer(s) to invoke
```

**Triage Feedback Loop:**

```python
# Agronomist corrections improve triage over time
async def record_triage_correction(
    triage_result: dict,
    actual_diagnosis: dict,
    agronomist_id: str
):
    """
    When agronomist corrects a diagnosis, update triage few-shot examples.
    This creates a continuous improvement loop.
    """
    if triage_result["classification"] != actual_diagnosis["condition_category"]:
        # Triage was wrong - this is a learning opportunity
        await store_few_shot_candidate(
            input_summary=triage_result["input_summary"],
            predicted=triage_result["classification"],
            actual=actual_diagnosis["condition_category"],
            agronomist_id=agronomist_id,
            context=actual_diagnosis.get("correction_notes")
        )

        # Periodically review candidates and add best ones to few-shot examples
        await trigger_few_shot_review_if_needed()
```

### Tiered Vision Processing

For image analysis, use the **tiered-vision** agent type to minimize expensive vision API calls. This is a dedicated agent type with two-tier LLM configuration:

```
┌───────────────────────────────────────────────────────────────────┐
│                   TIERED VISION PROCESSING                        │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│   Image ──► Tier 1: Haiku (256x256)                              │
│              Cost: ~$0.002                                        │
│              Purpose: Quick screening                             │
│                    │                                              │
│                    ├──► "Normal" (confidence > 0.8)              │
│                    │    → Skip Tier 2, output directly           │
│                    │                                              │
│                    └──► "Abnormal" or uncertain                  │
│                         → Proceed to Tier 2                       │
│                                                                   │
│             ──► Tier 2: Sonnet (full resolution)                 │
│                  Cost: ~$0.02                                     │
│                  Purpose: Detailed analysis                       │
│                                                                   │
│   Result: ~40% cost reduction for image-heavy workloads          │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

**Tiered-Vision Agent Configuration:**

```yaml
# src/agents/instances/tiered-vision/leaf-analysis.yaml
agent:
  id: "leaf-analysis"
  type: tiered-vision   # Dedicated type for two-tier processing
  version: "1.0.0"
  description: "Cost-optimized image analysis for tea leaf quality"

  input:
    event: "collection.poor_quality_detected"
    schema:
      required: [doc_id, thumbnail_url, original_url]
      optional: [metadata]

  output:
    event: "ai.leaf_analysis.complete"
    schema:
      fields: [classification, confidence, diagnosis, tier_used]

  mcp_sources:
    - server: collection
      tools: [get_document_thumbnail, get_document_original]
    - server: plantation
      tools: [get_farmer]

  # Two-tier LLM configuration (replaces single llm config)
  tiered_llm:
    screen:                              # Tier 1: Fast screening
      model: "anthropic/claude-3-haiku"
      temperature: 0.1
      max_tokens: 200
    diagnose:                            # Tier 2: Deep analysis
      model: "anthropic/claude-3-5-sonnet"
      temperature: 0.3
      max_tokens: 2000

  # Routing thresholds
  routing:
    screen_threshold: 0.7               # Escalate to Tier 2 if confidence < 0.7
    healthy_skip_threshold: 0.85        # Skip Tier 2 for "healthy" above this
    obvious_skip_threshold: 0.75        # Skip Tier 2 for "obvious_issue" above this

  rag:
    enabled: true                        # Used in Tier 2 only
    query_template: "tea leaf quality issues {{findings}}"
    knowledge_domains: [plant_diseases, tea_cultivation]
    top_k: 5

  error_handling:
    retry:
      max_attempts: 3
      backoff_ms: [100, 500, 2000]
    on_failure: "publish_error_event"
```

**Tiered Vision Implementation (workflow logic):**

```python
async def analyze_image_tiered(
    image_path: str,
    farmer_context: dict
) -> dict:
    """
    Two-tier vision analysis for cost optimization.
    """
    # Tier 1: Quick screening with downscaled image
    thumbnail = resize_image(image_path, max_size=256)

    tier1_result = await llm_gateway.complete_vision(
        model="haiku",
        image=thumbnail,
        prompt=TIER1_SCREENING_PROMPT,
        max_tokens=100
    )

    # If clearly normal, skip expensive analysis
    if tier1_result["assessment"] == "normal" and tier1_result["confidence"] > 0.8:
        return {
            "condition": "healthy",
            "confidence": tier1_result["confidence"],
            "tier": 1,
            "cost": tier1_result["cost"]
        }

    # Tier 2: Detailed analysis with full resolution
    tier2_result = await llm_gateway.complete_vision(
        model="sonnet",
        image=load_image(image_path),  # Full resolution
        prompt=TIER2_ANALYSIS_PROMPT.format(
            tier1_findings=tier1_result["findings"],
            farmer_context=farmer_context
        ),
        max_tokens=500
    )

    return {
        **tier2_result,
        "tier": 2,
        "cost": tier1_result["cost"] + tier2_result["cost"]
    }
```

### Diagnosis Aggregation Rules

When multiple analyzers produce diagnoses, apply these aggregation rules:

```yaml
# config/aggregation-rules.yaml
aggregation:
  # Primary diagnosis selection
  primary:
    strategy: highest_confidence
    minimum_confidence: 0.5
    tie_breaker: severity  # If tied, pick more severe

  # Secondary diagnoses
  secondary:
    max_count: 2
    minimum_confidence: 0.5
    must_be_different_category: true

  # Conflict resolution
  conflicts:
    # When two analyzers disagree on the same category
    same_category_conflict:
      strategy: highest_confidence
      require_minimum_gap: 0.15  # Winner must be 15% more confident

    # When results are contradictory (e.g., "too wet" vs "too dry")
    contradictory_results:
      strategy: flag_for_review
      notify: true

  # Output rules
  output:
    include_all_analyzer_results: true  # For transparency
    include_aggregation_reasoning: true
    confidence_penalty_for_disagreement: 0.1  # Reduce confidence when analyzers disagree
```

**Aggregation Implementation:**

```python
def aggregate_diagnoses(
    analyzer_results: dict[str, dict],
    rules: AggregationRules
) -> AggregatedDiagnosis:
    """
    Aggregate results from multiple parallel analyzers.
    """
    # Filter to successful results only
    valid_results = {
        k: v for k, v in analyzer_results.items()
        if v.get("status") == "success" and v.get("confidence", 0) >= rules.primary.minimum_confidence
    }

    if not valid_results:
        return AggregatedDiagnosis(
            primary={"condition": "inconclusive", "confidence": 0},
            secondary=[],
            reasoning="No analyzer produced confident results"
        )

    # Sort by confidence (and severity as tie-breaker)
    sorted_results = sorted(
        valid_results.items(),
        key=lambda x: (x[1]["confidence"], severity_score(x[1].get("severity", "low"))),
        reverse=True
    )

    # Select primary
    primary = sorted_results[0][1]

    # Check for conflicts
    conflict_detected = detect_conflicts(sorted_results, rules)
    if conflict_detected:
        primary["confidence"] -= rules.output.confidence_penalty_for_disagreement
        primary["conflict_warning"] = conflict_detected

    # Select secondaries (different categories only)
    primary_category = primary.get("condition_category")
    secondaries = [
        r[1] for r in sorted_results[1:]
        if r[1].get("condition_category") != primary_category
        and r[1].get("confidence", 0) >= rules.secondary.minimum_confidence
    ][:rules.secondary.max_count]

    return AggregatedDiagnosis(
        primary=primary,
        secondary=secondaries,
        all_results=analyzer_results,
        reasoning=generate_aggregation_reasoning(sorted_results, conflict_detected)
    )
```

### Diagnosis Deduplication

Before running expensive analysis, check if similar conditions were already diagnosed recently:

```python
async def check_existing_diagnosis(
    farmer_id: str,
    symptoms: dict,
    lookback_days: int = 7
) -> Optional[dict]:
    """
    Check if farmer has recent diagnosis for similar symptoms.
    Prevents duplicate analysis for ongoing conditions.
    """
    recent_diagnoses = await knowledge_mcp.get_recent_diagnoses(
        farmer_id=farmer_id,
        days=lookback_days
    )

    for diagnosis in recent_diagnoses:
        similarity = calculate_symptom_similarity(
            symptoms,
            diagnosis["original_symptoms"]
        )

        if similarity > 0.85:  # 85% similar symptoms
            # Return existing diagnosis with freshness indicator
            return {
                **diagnosis,
                "source": "cached",
                "original_date": diagnosis["created_at"],
                "similarity_score": similarity,
                "note": "Similar condition diagnosed recently - using existing analysis"
            }

    return None  # No match, proceed with fresh analysis
```

---
