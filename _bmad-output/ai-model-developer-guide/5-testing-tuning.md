# 5. Testing & Tuning

## Tooling Strategy

We use a **custom CLI tool** (`farmer-cli`) as the primary testing/tuning interface. This choice over LangSmith provides:

- **DAPR Integration** - Direct integration with pub/sub for realistic event testing
- **Offline Testing** - Works fully offline with golden samples (factory networks are unstable)
- **Cost Control** - No per-trace pricing during intensive tuning sessions
- **Unified Stack** - Observability stays in Grafana Cloud (no additional silo)

## CLI Tool Commands

```bash
# Batch testing against golden samples
farmer-cli agent test batch --type extractor --samples ./golden/extractors/
farmer-cli agent test batch --agent disease-diagnosis --samples ./golden/explorers/disease-diagnosis/

# Single test with specific input
farmer-cli agent test single --agent plant-diagnosis --input ./test-input.json

# Interactive prompt playground (hot-reload prompts)
farmer-cli agent playground --agent disease-diagnosis

# A/B comparison between prompt versions
farmer-cli agent compare --agent disease-diagnosis --prompt-a v1.md --prompt-b v2.md --samples ./golden/

# Run with verbose output for debugging
farmer-cli agent test single --agent plant-diagnosis --input ./test.json --verbose

# Export results for analysis
farmer-cli agent test batch --agent disease-diagnosis --output ./results.json
```

## Test Pyramid for AI Agents

```
                    ┌─────────────────┐
                    │   End-to-End    │  Few, expensive
                    │   (Full flow)   │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │   Integration   │  MCP, Events, RAG
                    │                 │
                    └────────┬────────┘
                             │
           ┌─────────────────┴─────────────────┐
           │          Golden Samples           │  Many, deterministic
           │   (Known inputs → expected outputs)│
           └─────────────────┬─────────────────┘
                             │
    ┌────────────────────────┴────────────────────────┐
    │                  Unit Tests                      │  Fast, isolated
    │  (Nodes, parsers, validators, utilities)        │
    └──────────────────────────────────────────────────┘
```

## Golden Sample Testing

Golden samples test that the agent produces expected outputs for known inputs:

```python
# tests/golden_samples/test_disease_diagnosis.py
import pytest
import json
from pathlib import Path

SAMPLES_DIR = Path("tests/golden_samples/explorers/disease-diagnosis")

def load_sample(name: str):
    input_path = SAMPLES_DIR / f"input_{name}.json"
    expected_path = SAMPLES_DIR / f"expected_{name}.json"
    return json.loads(input_path.read_text()), json.loads(expected_path.read_text())

@pytest.mark.parametrize("sample_name", ["001", "002", "003"])
def test_golden_sample(sample_name, disease_diagnosis_agent):
    input_data, expected = load_sample(sample_name)

    result = disease_diagnosis_agent.run(input_data)

    # Exact match for critical fields
    assert result["condition"] == expected["condition"]
    assert result["severity"] == expected["severity"]

    # Fuzzy match for confidence (within tolerance)
    assert abs(result["confidence"] - expected["confidence"]) < 0.1

    # Structural validation
    assert len(result["recommendations"]) >= 1
```

## Mocking LLM Responses

For deterministic testing, mock LLM responses:

```python
# tests/conftest.py
import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def mock_llm():
    """Mock LLM that returns predetermined responses."""
    mock = Mock()
    mock.invoke.return_value = {
        "condition": "fungal_infection",
        "confidence": 0.85,
        "severity": "moderate",
        "details": "Test details",
        "recommendations": ["Test recommendation"]
    }
    return mock

@pytest.fixture
def disease_diagnosis_agent(mock_llm):
    """Agent with mocked LLM for testing."""
    with patch("src.agents.types.explorer.graph.get_llm", return_value=mock_llm):
        from src.agents.types.explorer import create_explorer_graph
        return create_explorer_graph()
```

## Evaluation Metrics

Track these metrics for agent quality:

| Metric | Description | Target |
|--------|-------------|--------|
| **Accuracy** | Correct diagnosis/extraction vs. expert-labeled data | >90% |
| **Confidence Calibration** | High confidence = high accuracy | Correlation >0.8 |
| **Latency** | Time from input to output | <5s (p95) |
| **Token Efficiency** | Tokens used per request | Monitor trend |
| **Error Rate** | Failed requests / total requests | <1% |

## Golden Sample Structure

Organize golden samples with evaluation criteria for each test case:

```
tests/golden_samples/
├── explorers/
│   └── disease-diagnosis/
│       ├── sample_001/
│       │   ├── input.json          # Input event payload
│       │   ├── expected.json       # Expected output
│       │   ├── evaluation.yaml     # Evaluation rules
│       │   └── context.json        # Mock MCP/RAG responses (optional)
│       ├── sample_002/
│       │   └── ...
│       └── manifest.yaml           # Sample metadata
└── generators/
    └── action-plan/
        └── ...
```

**Evaluation criteria file:**

```yaml
# evaluation.yaml
criteria:
  exact_match:
    - field: condition
    - field: severity

  fuzzy_match:
    - field: confidence
      tolerance: 0.1

  contains:
    - field: recommendations
      must_include: ["fungicide", "drainage"]

  semantic:
    - field: details
      similarity_threshold: 0.8
      reference: "Should mention leaf discoloration and rainy season"

metadata:
  category: "fungal_infection"
  difficulty: "medium"
  added_date: "2024-01-15"
  author: "agronomist_team"
```

**Manifest for test organization:**

```yaml
# manifest.yaml
agent: disease-diagnosis
samples:
  - id: sample_001
    description: "Clear fungal infection case"
    tags: [fungal, rainy_season, moderate_severity]

  - id: sample_002
    description: "Edge case - multiple conditions"
    tags: [complex, multiple_conditions]

  - id: sample_003
    description: "Low confidence expected"
    tags: [ambiguous, low_confidence]
```

## Prompt Playground

The interactive playground enables rapid prompt iteration without modifying files:

```bash
# Start playground for an agent
farmer-cli agent playground --agent disease-diagnosis

# Playground REPL commands:
> load                    # Reload prompts from disk
> test sample_001         # Run specific sample
> test --all              # Run all samples
> set-temp 0.5            # Adjust temperature
> set-model claude-3-5    # Switch model
> diff                    # Show changes vs. saved prompt
> save                    # Save current prompt to file
> history                 # Show recent runs
> export session.json     # Export session for review
```

**Playground features:**

1. **Hot-reload prompts** - Edit `.md` files in your editor, type `load` to test
2. **Variable injection** - Override template variables for testing edge cases
3. **Response inspection** - View full LLM response, tokens used, latency
4. **Iteration history** - Track what you tried and results

**Example session:**

```
$ farmer-cli agent playground --agent disease-diagnosis

🎮 Prompt Playground - disease-diagnosis (Explorer)
   System prompt: prompts/explorers/disease-diagnosis/system.md
   Template: prompts/explorers/disease-diagnosis/template.md
   Model: claude-3-5-sonnet | Temp: 0.3

> test sample_001

📥 Input: sample_001 (fungal infection case)
📤 Output:
   condition: fungal_infection ✓
   confidence: 0.87 (expected: 0.85, diff: +0.02) ✓
   severity: moderate ✓
   recommendations: [✓ fungicide, ✓ drainage, ✓ remove leaves]

⏱️  Latency: 1.2s | Tokens: 450 in / 120 out | Cost: $0.002

> set-temp 0.5
Temperature set to 0.5

> test sample_001

📥 Input: sample_001 (fungal infection case)
📤 Output:
   condition: fungal_infection ✓
   confidence: 0.82 (expected: 0.85, diff: -0.03) ✓
   severity: moderate ✓

⏱️  Latency: 1.4s | Tokens: 450 in / 135 out | Cost: $0.002

> save
Prompt saved to prompts/explorers/disease-diagnosis/system.md
```

## A/B Prompt Comparison

Compare prompt versions systematically:

```bash
# Compare two prompt versions across all samples
farmer-cli agent compare \
  --agent disease-diagnosis \
  --prompt-a prompts/explorers/disease-diagnosis/system-v1.md \
  --prompt-b prompts/explorers/disease-diagnosis/system-v2.md \
  --samples ./golden/explorers/disease-diagnosis/

# Output format options
farmer-cli agent compare ... --format table   # Terminal table (default)
farmer-cli agent compare ... --format json    # JSON for further analysis
farmer-cli agent compare ... --format html    # HTML report
```

**Comparison output:**

```
┌─────────────────────────────────────────────────────────────────────┐
│ A/B Comparison: disease-diagnosis                                   │
│ Prompt A: system-v1.md | Prompt B: system-v2.md                     │
│ Samples: 15 | Model: claude-3-5-sonnet                              │
├─────────────────────────────────────────────────────────────────────┤
│ Metric                  │ Prompt A      │ Prompt B      │ Winner   │
├─────────────────────────┼───────────────┼───────────────┼──────────┤
│ Accuracy (condition)    │ 93.3% (14/15) │ 100% (15/15)  │ B (+6.7%)│
│ Accuracy (severity)     │ 86.7% (13/15) │ 93.3% (14/15) │ B (+6.7%)│
│ Avg confidence diff     │ 0.08          │ 0.05          │ B        │
│ Avg latency             │ 1.3s          │ 1.5s          │ A (-0.2s)│
│ Avg tokens (output)     │ 125           │ 145           │ A (-20)  │
│ Avg cost                │ $0.0018       │ $0.0021       │ A        │
├─────────────────────────┴───────────────┴───────────────┴──────────┤
│ RECOMMENDATION: Prompt B - Better accuracy outweighs cost increase │
└─────────────────────────────────────────────────────────────────────┘

Detailed results by sample:
┌───────────┬──────────────┬──────────────┬────────────────────────────┐
│ Sample    │ A Result     │ B Result     │ Notes                      │
├───────────┼──────────────┼──────────────┼────────────────────────────┤
│ sample_001│ ✓ Pass       │ ✓ Pass       │                            │
│ sample_002│ ✗ Fail       │ ✓ Pass       │ B correctly identified     │
│           │              │              │ secondary condition        │
│ sample_003│ ✓ Pass       │ ✓ Pass       │ B more detailed reasoning  │
│ ...       │              │              │                            │
└───────────┴──────────────┴──────────────┴────────────────────────────┘
```

## Prompt Tuning Workflow

Recommended workflow for prompt optimization:

```
1. BASELINE
   └─→ Run batch test with current prompt
   └─→ Record metrics as baseline

2. HYPOTHESIS
   └─→ Identify specific improvement goal
   └─→ Example: "Improve severity classification accuracy"

3. ITERATE
   └─→ Start playground session
   └─→ Make targeted changes to prompt
   └─→ Test against failing samples
   └─→ Verify passing samples still pass

4. VALIDATE
   └─→ Run A/B comparison vs. baseline
   └─→ Check all metrics (not just target)
   └─→ Watch for regressions

5. DEPLOY
   └─→ Update prompt version in config
   └─→ Add changelog entry
   └─→ Commit with samples that drove changes
```

**Prompt tuning checklist:**

- [ ] Baseline metrics recorded
- [ ] Specific improvement goal defined
- [ ] Changes tested in playground
- [ ] A/B comparison shows improvement
- [ ] No regressions on passing samples
- [ ] Cost impact acceptable
- [ ] Prompt version updated
- [ ] Changelog entry added

## Production Feedback Loop

Monitor production performance and feed back into golden samples:

```python
# Capture production outcomes for tuning
async def record_production_feedback(
    agent_id: str,
    input_event: dict,
    output: dict,
    feedback: dict  # From downstream validation or user
):
    """Record production runs for potential golden sample creation."""

    if feedback.get("quality") == "excellent":
        # Candidate for golden sample
        await store_candidate_sample(
            agent_id=agent_id,
            input=input_event,
            output=output,
            source="production",
            feedback=feedback
        )

    elif feedback.get("quality") == "incorrect":
        # Flag for prompt tuning
        await flag_for_review(
            agent_id=agent_id,
            input=input_event,
            actual_output=output,
            expected=feedback.get("expected"),
            reason=feedback.get("reason")
        )
```

**Grafana dashboard queries for tuning insights:**

```promql
# Accuracy trend by agent
sum(rate(agent_correct_total[1h])) by (agent_id) /
sum(rate(agent_invocations_total[1h])) by (agent_id)

# Confidence vs. accuracy correlation
histogram_quantile(0.5, sum(rate(agent_confidence_bucket[1h])) by (le, correct))

# Cost per correct output
sum(rate(llm_cost_total[1h])) by (agent_id) /
sum(rate(agent_correct_total[1h])) by (agent_id)
```

## Agronomist Feedback Loop

When agronomists correct diagnoses, capture this feedback to improve triage and analysis agents:

```
┌───────────────────────────────────────────────────────────────────┐
│                   CONTINUOUS IMPROVEMENT LOOP                      │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│   Production Diagnosis ──► Agronomist Review                     │
│          │                        │                               │
│          │                        ├──► Approved ──► No action     │
│          │                        │                               │
│          │                        └──► Corrected                  │
│          │                                │                       │
│          │                                ▼                       │
│          │                        Store Correction                │
│          │                                │                       │
│          │                                ▼                       │
│          │         ┌──────────────────────┴───────────────┐      │
│          │         │                                       │      │
│          │         ▼                                       ▼      │
│          │   Update Triage                         Create New    │
│          │   Few-Shot Examples                     Golden Sample │
│          │         │                                       │      │
│          │         └──────────────────────┬───────────────┘      │
│          │                                │                       │
│          │                                ▼                       │
│          └────────────────────► Improved Agents                   │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

**Feedback Capture Implementation:**

```python
async def handle_agronomist_correction(
    diagnosis_id: str,
    original_diagnosis: dict,
    corrected_diagnosis: dict,
    agronomist_id: str,
    correction_notes: str
):
    """
    Process agronomist correction and route to appropriate improvement path.
    """
    correction = {
        "diagnosis_id": diagnosis_id,
        "original": original_diagnosis,
        "corrected": corrected_diagnosis,
        "agronomist_id": agronomist_id,
        "notes": correction_notes,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Determine correction type
    if original_diagnosis["condition"] != corrected_diagnosis["condition"]:
        # Classification was wrong - triage improvement opportunity
        await update_triage_examples(correction)

    if abs(original_diagnosis["confidence"] - 0.5) > 0.3:
        # High confidence but wrong - prompt tuning needed
        await flag_for_prompt_review(correction)

    # Always store for golden sample consideration
    await store_correction_candidate(correction)

    # Update metrics for monitoring
    await metrics.increment(
        "agronomist_corrections_total",
        tags={
            "original_condition": original_diagnosis["condition"],
            "corrected_condition": corrected_diagnosis["condition"],
            "agent_id": original_diagnosis.get("agent_id")
        }
    )

async def update_triage_examples(correction: dict):
    """
    Add correction to triage few-shot example candidates.
    Reviewed periodically and best examples promoted to production.
    """
    candidate = {
        "input_summary": extract_input_summary(correction["original"]),
        "predicted_category": correction["original"]["condition_category"],
        "actual_category": correction["corrected"]["condition_category"],
        "symptoms": correction["original"].get("symptoms", []),
        "agronomist_notes": correction["notes"],
        "quality_score": 0,  # Updated during review
        "status": "pending_review"
    }

    await db.triage_example_candidates.insert_one(candidate)

    # Check if we have enough candidates for review
    pending_count = await db.triage_example_candidates.count_documents(
        {"status": "pending_review"}
    )

    if pending_count >= 10:
        await trigger_example_review_workflow()
```

**Few-Shot Example Review Workflow:**

```python
async def review_triage_examples():
    """
    Periodic review of correction candidates to promote to few-shot examples.
    Run weekly or when candidate count threshold reached.
    """
    candidates = await db.triage_example_candidates.find(
        {"status": "pending_review"}
    ).to_list(100)

    # Group by category mismatch type
    grouped = group_by_correction_type(candidates)

    for correction_type, examples in grouped.items():
        # Select best example for each type
        best = select_best_example(examples, criteria=[
            "clear_symptoms",
            "representative_case",
            "agronomist_confidence"
        ])

        if best and best["quality_score"] >= 0.8:
            # Promote to production few-shot examples
            await promote_to_few_shot(best, correction_type)

            # Update status
            await db.triage_example_candidates.update_one(
                {"_id": best["_id"]},
                {"$set": {"status": "promoted"}}
            )

    # Archive old candidates
    await archive_old_candidates(days=30)
```

## RAG Knowledge A/B Testing

Test new knowledge base versions before full deployment:

```yaml
# config/rag-ab-test.yaml
ab_tests:
  - test_id: "disease-kb-v2"
    description: "Testing improved fungal disease documentation"
    status: active
    started: "2024-01-15"

    control:
      knowledge_version: "disease-kb-v1.2"
      traffic_percentage: 80

    variant:
      knowledge_version: "disease-kb-v2.0-staged"
      traffic_percentage: 20

    metrics:
      - accuracy_vs_agronomist_review
      - confidence_calibration
      - recommendation_acceptance_rate

    success_criteria:
      accuracy_improvement: ">= 5%"
      no_regression_on: ["latency", "cost"]

    auto_promote:
      enabled: true
      minimum_samples: 500
      confidence_level: 0.95
```

**A/B Test Implementation:**

```python
class RAGABTestRouter:
    """Route RAG queries to control or variant knowledge versions."""

    def __init__(self, test_config: dict):
        self.test_id = test_config["test_id"]
        self.control = test_config["control"]
        self.variant = test_config["variant"]

    def get_knowledge_version(self, farmer_id: str) -> tuple[str, str]:
        """
        Deterministic routing based on farmer_id.
        Returns (version, group) tuple.
        """
        # Hash farmer_id for consistent assignment
        hash_val = int(hashlib.md5(farmer_id.encode()).hexdigest(), 16)
        bucket = hash_val % 100

        if bucket < self.variant["traffic_percentage"]:
            return self.variant["knowledge_version"], "variant"
        return self.control["knowledge_version"], "control"

    async def query_with_tracking(
        self,
        query: str,
        farmer_id: str,
        domains: list[str]
    ) -> dict:
        """Query RAG with A/B test tracking."""
        version, group = self.get_knowledge_version(farmer_id)

        # Query the appropriate version
        result = await rag_engine.query(
            query=query,
            domains=domains,
            knowledge_version=version
        )

        # Track for analysis
        await metrics.record_ab_query(
            test_id=self.test_id,
            group=group,
            version=version,
            farmer_id=farmer_id,
            query_hash=hashlib.md5(query.encode()).hexdigest()
        )

        return {**result, "ab_test_group": group, "knowledge_version": version}
```

**A/B Test Analysis:**

```python
async def analyze_ab_test(test_id: str) -> dict:
    """
    Analyze A/B test results and determine if variant should be promoted.
    """
    test_config = await load_test_config(test_id)

    # Gather metrics for control and variant
    control_metrics = await gather_group_metrics(test_id, "control")
    variant_metrics = await gather_group_metrics(test_id, "variant")

    # Statistical significance testing
    results = {}
    for metric in test_config["metrics"]:
        control_val = control_metrics[metric]
        variant_val = variant_metrics[metric]

        # Calculate statistical significance
        p_value, significant = calculate_significance(
            control_val,
            variant_val,
            confidence_level=test_config["auto_promote"]["confidence_level"]
        )

        results[metric] = {
            "control": control_val,
            "variant": variant_val,
            "difference": variant_val - control_val,
            "p_value": p_value,
            "significant": significant
        }

    # Check success criteria
    should_promote = check_success_criteria(
        results,
        test_config["success_criteria"]
    )

    return {
        "test_id": test_id,
        "sample_size": {
            "control": control_metrics["sample_count"],
            "variant": variant_metrics["sample_count"]
        },
        "results": results,
        "recommendation": "promote" if should_promote else "continue",
        "analysis_timestamp": datetime.utcnow().isoformat()
    }
```

---
