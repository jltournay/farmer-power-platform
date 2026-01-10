# Story 0.75.19: Explorer Agent Implementation - Sample Config & Golden Tests

**Status:** ready-for-dev
**GitHub Issue:** <!-- Auto-created by dev-story workflow -->

## Story

As a **developer**,
I want a sample Explorer agent configuration (disease-diagnosis) with comprehensive golden sample tests,
So that the Explorer workflow can be validated end-to-end and serve as a reference for future explorer agents.

## Context

### What Already Exists (DO NOT RECREATE)

The Explorer workflow infrastructure was fully implemented in **Story 0.75.16**:

| Component | Location | Lines | Status |
|-----------|----------|-------|--------|
| `ExplorerConfig` | `services/ai-model/src/ai_model/domain/agent_config.py:359-393` | 35 | **DONE** |
| `ExplorerState` | `services/ai-model/src/ai_model/workflows/states/explorer.py` | 132 | **DONE** |
| `ExplorerWorkflow` | `services/ai-model/src/ai_model/workflows/explorer.py` | **724** | **DONE** |
| `ExplorerAgentResult` | `libs/fp-common/fp_common/events/ai_model_events.py:149-178` | 30 | **DONE** |
| `WorkflowExecutionService` | `services/ai-model/src/ai_model/workflows/execution_service.py` | 488 | **DONE** |
| `AgentExecutor` routing | `services/ai-model/src/ai_model/services/agent_executor.py` | - | **DONE** |
| Unit tests | `tests/unit/ai_model/workflows/test_explorer.py` | **438** | **DONE** |
| Golden samples (3) | `tests/golden/disease_diagnosis/samples.json` | 186 | **Partial** |

**Explorer Workflow Features (from 0.75.16):**
- 6-node LangGraph workflow: `fetch_context` -> `triage` -> `single/parallel_analyze` -> `aggregate` -> `output`
- Saga pattern with conditional routing (high confidence -> single analyzer, low -> parallel)
- RAG integration via `RankingService`
- MCP context fetching via `AgentToolProvider`
- Parallel analyzer execution with timeout
- Result aggregation with confidence-based ranking

### What This Story Creates

1. **Sample Agent Configuration** - `config/agents/disease-diagnosis.yaml`
2. **Sample Prompt Configuration** - `config/prompts/disease-diagnosis.json`
3. **Expanded Golden Samples** - Add 7+ more samples (total 10+)
4. **Golden Sample Test Runner** - `tests/golden/disease_diagnosis/test_disease_diagnosis_golden.py`
5. **E2E Validation** - Verify explorer workflow in Docker environment

### Architecture References

- Explorer workflow: `services/ai-model/src/ai_model/workflows/explorer.py`
- Agent types spec: `_bmad-output/architecture/ai-model-architecture/agent-types.md` @ Explorer Type
- **Reference configs (MUST follow structure):**
  - `config/agents/qc-event-extractor.yaml` - Agent config structure
  - `config/prompts/qc-event-extractor.json` - Prompt config structure

---

## Acceptance Criteria

1. **AC1: Sample Agent Configuration** - Create `config/agents/disease-diagnosis.yaml`:
   - Valid `ExplorerConfig` schema (see Quick Reference below)
   - Agent ID: `disease-diagnosis`
   - LLM: Claude 3.5 Sonnet, temperature 0.3
   - RAG enabled with `tea-disease`, `plant-pathology` domains
   - MCP sources configured for plantation/collection context
   - Output schema for diagnosis results

2. **AC2: Sample Prompt Configuration** - Create `config/prompts/disease-diagnosis.json`:
   - **CRITICAL: `agent_id` field MUST match agent config (`disease-diagnosis`)**
   - System prompt and template inside `content` object (see Prompt Structure below)
   - `output_schema` for JSON validation
   - `few_shot_examples` for in-context learning
   - Validates against `Prompt` Pydantic model in `domain/prompt.py`

3. **AC3: Expanded Golden Samples (10+ total)** - Update `tests/golden/disease_diagnosis/samples.json`:
   - 3 existing samples (blister blight, nutrient deficiency, red spider mite)
   - Add 7+ new samples with FULL expected_output structure (see Golden Sample Structure below)
   - Each sample must include: `diagnosis`, `recommendations`, `contributing_factors`, `expected_recovery`

4. **AC4: Golden Sample Test Runner** - Create test infrastructure:
   - `tests/golden/disease_diagnosis/conftest.py` with fixtures
   - `tests/golden/disease_diagnosis/test_disease_diagnosis_golden.py`:
     - Parametrized tests loading golden samples
     - Mock LLM returning expected responses
     - Variance comparison for confidence scores (acceptable: 0.1)
     - Test full workflow execution path

5. **AC5: Config Validation** - Add config validation tests:
   - Test `disease-diagnosis.yaml` validates against `ExplorerConfig`
   - Test `disease-diagnosis.json` validates against `Prompt` model
   - Add to `tests/unit/ai_model/` or config validation suite

6. **AC6: E2E Regression** - All existing E2E tests continue to pass

7. **AC7: CI Passes** - All lint checks and tests pass in CI

---

## Tasks / Subtasks

- [ ] **Task 1: Create Sample Agent Configuration** (AC: #1)
  - [ ] Create `config/agents/disease-diagnosis.yaml` following `qc-event-extractor.yaml` structure:
    ```yaml
    # Disease Diagnosis Explorer Agent Configuration
    # Story 0.75.19: Explorer Agent Implementation
    #
    # This agent analyzes quality issues and diagnoses tea plant diseases.
    # Uses RAG for expert knowledge retrieval.
    #
    # See: _bmad-output/architecture/ai-model-architecture/agent-types.md

    id: "disease-diagnosis:1.0.0"
    agent_id: "disease-diagnosis"
    version: "1.0.0"
    type: explorer
    status: active
    description: "Diagnoses tea plant diseases from quality events and farmer context using RAG knowledge"

    # Input contract
    input:
      event: "ai.agent.requested"
      schema:
        type: object
        required:
          - farmer_id
          - quality_issues
        properties:
          farmer_id:
            type: string
            description: "Farmer identifier"
          doc_id:
            type: string
            description: "Collection document ID"
          quality_issues:
            type: array
            items:
              type: string
            description: "List of observed quality issues"
          grade:
            type: string
            enum: ["A", "B", "C", "D", "REJECT"]
          quality_score:
            type: number
            minimum: 0
            maximum: 100
          image_url:
            type: string
            format: uri
          weather_history:
            type: object
            description: "Recent weather data"

    # Output contract
    output:
      event: "ai.agent.disease-diagnosis.completed"
      schema:
        type: object
        required:
          - diagnosis
          - recommendations
        properties:
          diagnosis:
            type: object
            required:
              - condition
              - confidence
              - severity
            properties:
              condition:
                type: string
                description: "Identified condition (e.g., tea_blister_blight)"
              confidence:
                type: number
                minimum: 0
                maximum: 1
              severity:
                type: string
                enum: ["low", "moderate", "high", "critical"]
              details:
                type: string
          recommendations:
            type: array
            items:
              type: string
          contributing_factors:
            type: array
            items:
              type: string
          expected_recovery:
            type: string

    # LLM configuration
    llm:
      model: "anthropic/claude-3-5-sonnet"
      temperature: 0.3
      max_tokens: 2000

    # RAG configuration (explorer-specific)
    rag:
      enabled: true
      knowledge_domains:
        - tea-disease
        - plant-pathology
      top_k: 5
      min_similarity: 0.7

    # MCP sources for context fetching
    mcp_sources:
      - server: plantation-mcp
        tool: get_farmer
        arg_mapping:
          farmer_id: farmer_id
      - server: collection-mcp
        tool: get_document
        arg_mapping:
          doc_id: doc_id

    # Error handling
    error_handling:
      max_attempts: 3
      backoff_ms: [100, 500, 2000]
      on_failure: publish_error_event
      dead_letter_topic: null

    # Metadata
    metadata:
      author: "dev-story-0.75.19"
      created_at: "2026-01-10T00:00:00Z"
      updated_at: "2026-01-10T00:00:00Z"
      git_commit: null
    ```
  - [ ] Validate YAML against `ExplorerConfig` Pydantic schema

- [ ] **Task 2: Create Sample Prompt Configuration** (AC: #2)
  - [ ] Create `config/prompts/disease-diagnosis.json` following `qc-event-extractor.json` structure:
    ```json
    {
      "id": "disease-diagnosis:1.0.0",
      "prompt_id": "disease-diagnosis",
      "agent_id": "disease-diagnosis",
      "version": "1.0.0",
      "status": "active",
      "content": {
        "system_prompt": "You are an expert tea plant pathologist for the Farmer Power Platform.\n\nYour task is to analyze quality issues, farmer context, and expert knowledge to diagnose tea plant diseases or conditions.\n\nYou must:\n1. Analyze all provided quality issues and symptoms\n2. Consider farmer context (region, altitude, recent performance trends)\n3. Incorporate weather history as contributing factors\n4. Use RAG expert knowledge to support your diagnosis\n5. Provide actionable recommendations\n6. Estimate expected recovery time\n\nDiagnosis confidence levels:\n- 0.9+: High confidence, clear symptoms match known condition\n- 0.7-0.9: Moderate confidence, most symptoms align\n- 0.5-0.7: Low confidence, inconclusive symptoms\n- <0.5: Very low confidence, insufficient data\n\nSeverity levels:\n- low: Minimal impact, monitor situation\n- moderate: Action needed within 1-2 weeks\n- high: Urgent action required within days\n- critical: Immediate intervention required\n\nRESPOND WITH ONLY VALID JSON matching the output schema.",
        "template": "Analyze the following tea quality data and diagnose any plant diseases or conditions.\n\n## Farmer Context\n{{context}}\n\n## Quality Issues Observed\n{{quality_issues}}\n\n## Weather History\n{{weather_history}}\n\n## Expert Knowledge (RAG)\n{{rag_knowledge}}\n\n## Required Output\nProvide a JSON object with:\n- diagnosis: {condition, confidence, severity, details}\n- recommendations: array of actionable steps\n- contributing_factors: array of factors leading to condition\n- expected_recovery: estimated recovery timeframe",
        "output_schema": {
          "type": "object",
          "required": ["diagnosis", "recommendations"],
          "properties": {
            "diagnosis": {
              "type": "object",
              "required": ["condition", "confidence", "severity"],
              "properties": {
                "condition": {
                  "type": "string",
                  "description": "Identified condition (snake_case)"
                },
                "confidence": {
                  "type": "number",
                  "minimum": 0,
                  "maximum": 1
                },
                "severity": {
                  "type": "string",
                  "enum": ["low", "moderate", "high", "critical"]
                },
                "details": {
                  "type": "string"
                }
              }
            },
            "recommendations": {
              "type": "array",
              "items": {"type": "string"},
              "minItems": 1
            },
            "contributing_factors": {
              "type": "array",
              "items": {"type": "string"}
            },
            "expected_recovery": {
              "type": "string"
            }
          }
        },
        "few_shot_examples": [
          {
            "input": {
              "quality_issues": ["brown_spots", "wilting"],
              "weather_history": {"humidity": 90, "rainfall_mm": 85},
              "region": "Kericho-High"
            },
            "output": {
              "diagnosis": {
                "condition": "tea_blister_blight",
                "confidence": 0.88,
                "severity": "moderate",
                "details": "Blister blight caused by high humidity conditions"
              },
              "recommendations": [
                "Apply copper-based fungicide within 48 hours",
                "Improve air circulation by pruning"
              ],
              "contributing_factors": ["High humidity (90%)", "Recent heavy rainfall"],
              "expected_recovery": "2-3 weeks with treatment"
            }
          }
        ]
      },
      "metadata": {
        "author": "dev-story-0.75.19",
        "created_at": "2026-01-10T00:00:00Z",
        "updated_at": "2026-01-10T00:00:00Z",
        "changelog": "Initial version for Story 0.75.19",
        "git_commit": null
      },
      "ab_test": {
        "enabled": false,
        "traffic_percentage": 0.0,
        "test_id": null
      }
    }
    ```
  - [ ] **VERIFY: `agent_id` matches agent config (`disease-diagnosis`)**
  - [ ] Validate JSON against `Prompt` Pydantic model

- [ ] **Task 3: Expand Golden Samples** (AC: #3)
  - [ ] Add samples to `tests/golden/disease_diagnosis/samples.json` with FULL structure:
    - [ ] Sample 4: Multiple disease detection (rust + blight)
    - [ ] Sample 5: Healthy plant / no disease detected
    - [ ] Sample 6: Low confidence - insufficient data
    - [ ] Sample 7: Weather-related damage (frost, drought)
    - [ ] Sample 8: Technique issue (over-pruning, improper harvest)
    - [ ] Sample 9: Edge case - contradictory symptoms
    - [ ] Sample 10: Edge case - unusual regional pattern
  - [ ] Each sample MUST include this full expected_output structure:
    ```json
    {
      "expected_output": {
        "diagnosis": {
          "condition": "condition_name_snake_case",
          "confidence": 0.XX,
          "severity": "low|moderate|high|critical",
          "details": "Explanation of diagnosis..."
        },
        "recommendations": [
          "First actionable recommendation",
          "Second recommendation"
        ],
        "contributing_factors": [
          "Factor 1",
          "Factor 2"
        ],
        "expected_recovery": "X-Y weeks with treatment"
      },
      "acceptable_variance": {
        "diagnosis.confidence": 0.1
      },
      "metadata": {
        "sample_id": "GS-diag-XXX",
        "agent_name": "disease_diagnosis",
        "agent_type": "explorer",
        "description": "Description of test scenario",
        "source": "synthetic",
        "tags": ["tag1", "tag2"],
        "priority": "P0|P1|P2"
      }
    }
    ```

- [ ] **Task 4: Create Golden Sample Test Runner** (AC: #4)
  - [ ] Create `tests/golden/disease_diagnosis/__init__.py`
  - [ ] Create `tests/golden/disease_diagnosis/conftest.py`:
    ```python
    import json
    from pathlib import Path
    import pytest
    from ai_model.domain.agent_config import ExplorerConfig
    from ai_model.workflows.explorer import ExplorerWorkflow

    SAMPLES_PATH = Path(__file__).parent / "samples.json"

    @pytest.fixture
    def explorer_config() -> ExplorerConfig:
        """Load disease-diagnosis config from YAML."""
        config_path = Path("config/agents/disease-diagnosis.yaml")
        # Load and parse YAML to ExplorerConfig
        ...

    @pytest.fixture
    def load_golden_samples() -> list[dict]:
        """Load all samples from samples.json."""
        with open(SAMPLES_PATH) as f:
            data = json.load(f)
        return data["samples"]

    @pytest.fixture
    def mock_llm_gateway_for_golden(mocker, load_golden_samples):
        """Mock LLM to return expected output for golden sample."""
        def _create_mock(sample_index: int):
            sample = load_golden_samples[sample_index]
            mock = mocker.patch("ai_model.llm.gateway.LLMGateway.complete")
            mock.return_value = sample["expected_output"]
            return mock
        return _create_mock
    ```
  - [ ] Create `tests/golden/disease_diagnosis/test_disease_diagnosis_golden.py`:
    ```python
    import pytest
    from ai_model.workflows.explorer import ExplorerWorkflow

    @pytest.mark.parametrize("sample_index", range(10))
    async def test_golden_sample(
        sample_index,
        explorer_config,
        load_golden_samples,
        mock_llm_gateway_for_golden,
    ):
        """Test workflow produces expected output for golden sample."""
        sample = load_golden_samples[sample_index]
        mock_llm_gateway_for_golden(sample_index)

        # Execute workflow
        workflow = ExplorerWorkflow(...)
        result = await workflow.execute(sample["input"])

        # Compare with variance
        expected = sample["expected_output"]
        variance = sample.get("acceptable_variance", {})

        assert result["diagnosis"]["condition"] == expected["diagnosis"]["condition"]

        conf_variance = variance.get("diagnosis.confidence", 0.1)
        assert abs(result["diagnosis"]["confidence"] - expected["diagnosis"]["confidence"]) <= conf_variance

        assert result["diagnosis"]["severity"] == expected["diagnosis"]["severity"]
    ```
  - [ ] **CI Note:** Golden tests in `tests/golden/` use existing test infrastructure. If imports fail, verify `conftest.py` imports from root `tests/conftest.py`.

- [ ] **Task 5: Add Config Validation Tests** (AC: #5)
  - [ ] Create or update `tests/unit/ai_model/test_config_validation.py`:
    - [ ] Test disease-diagnosis.yaml validates against ExplorerConfig
    - [ ] Test disease-diagnosis.json validates against Prompt model
    - [ ] Test `agent_id` in prompt matches agent config
    - [ ] Test config files can be loaded by AgentConfigCache

- [ ] **Task 6: E2E Regression Testing (MANDATORY)** (AC: #6)
  - [ ] Start E2E infrastructure: `bash scripts/e2e-up.sh --build`
  - [ ] Run preflight validation: `bash scripts/e2e-preflight.sh`
  - [ ] Run full E2E test suite: `bash scripts/e2e-test.sh --keep-up`
  - [ ] Capture output in "Local Test Run Evidence" section
  - [ ] Tear down: `bash scripts/e2e-up.sh --down`

- [ ] **Task 7: CI Verification (MANDATORY)** (AC: #7)
  - [ ] Run lint: `ruff check . && ruff format --check .`
  - [ ] Push and verify CI passes
  - [ ] Trigger E2E CI: `gh workflow run e2e.yaml --ref <branch>`
  - [ ] Verify E2E CI passes before code review

---

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.75.19: Explorer Agent - Sample Config & Golden Tests"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/0-75-19-explorer-agent-implementation
  ```

**Branch name:** `feature/0-75-19-explorer-agent-implementation`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (config, test - not mixed)
- [ ] Push to feature branch: `git push -u origin feature/0-75-19-explorer-agent-implementation`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.75.19: Explorer Agent - Sample Config & Golden Tests" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d feature/0-75-19-explorer-agent-implementation`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
pytest tests/unit/ai_model/ tests/golden/disease_diagnosis/ -v --tb=no -q
```
**Output:**
```
(paste test summary here - e.g., "XXX passed in X.XXs")
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure with rebuild
bash scripts/e2e-up.sh --build

# Run preflight validation
bash scripts/e2e-preflight.sh

# Run E2E tests
bash scripts/e2e-test.sh --keep-up

# Tear down
bash scripts/e2e-up.sh --down
```
**Output:**
```
(paste E2E test output here - story is NOT ready for review without this)
```
**E2E passed:** [ ] Yes / [ ] No

### 3. Lint Check
```bash
ruff check . && ruff format --check .
```
**Lint passed:** [ ] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin feature/0-75-19-explorer-agent-implementation

# Trigger E2E CI
gh workflow run e2e.yaml --ref feature/0-75-19-explorer-agent-implementation

# Wait and check status
gh run list --branch feature/0-75-19-explorer-agent-implementation --limit 3
```
**CI Run ID:** _______________
**CI E2E Run ID:** _______________
**CI Status:** [ ] Passed / [ ] Failed
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### Quick Reference (CRITICAL - Use These Exact Structures)

| Config Element | Source File | Key Fields |
|----------------|-------------|------------|
| `ExplorerConfig` | `domain/agent_config.py:359-393` | `type: explorer`, `rag: RAGConfig` |
| `RAGConfig` | `domain/agent_config.py:89-119` | `enabled`, `knowledge_domains`, `top_k`, `min_similarity` |
| `Prompt` | `domain/prompt.py` | `content: {system_prompt, template, output_schema, few_shot_examples}` |
| `PromptContent` | `domain/prompt.py:38-53` | `system_prompt`, `template`, `output_schema`, `few_shot_examples` |

### Prompt Structure (CRITICAL - agent_id MUST be present)

```json
{
  "id": "disease-diagnosis:1.0.0",
  "prompt_id": "disease-diagnosis",
  "agent_id": "disease-diagnosis",     // MUST match agent config!
  "version": "1.0.0",
  "status": "active",
  "content": {                          // All prompt content goes HERE
    "system_prompt": "...",
    "template": "...",
    "output_schema": {...},
    "few_shot_examples": [...]
  },
  "metadata": {...},
  "ab_test": {...}
}
```

### Agent Config Structure (from qc-event-extractor.yaml)

```yaml
id: "agent-id:version"
agent_id: "agent-id"
version: "X.Y.Z"
type: explorer                    # Must be "explorer" for ExplorerConfig
status: active
description: "..."

input:
  event: "topic.name"
  schema:
    type: object
    required: [field1, field2]
    properties:
      field1: {type: string, description: "..."}

output:
  event: "topic.name"
  schema:
    type: object
    required: [field1]
    properties: {...}

llm:
  model: "provider/model"
  temperature: 0.3
  max_tokens: 2000

rag:                              # Explorer-specific
  enabled: true
  knowledge_domains: [domain1, domain2]
  top_k: 5
  min_similarity: 0.7

mcp_sources: [...]
error_handling: {...}
metadata: {...}
```

### Golden Sample Expected Output Structure

Each sample MUST have this full structure:

```json
{
  "input": {
    "farmer_id": "WM-XXXX",
    "doc_id": "DOC-XXXXX",
    "quality_issues": ["issue1", "issue2"],
    "grade": "X",
    "quality_score": XX.X,
    "farmer_context": {...},
    "weather_history": {...}
  },
  "expected_output": {
    "diagnosis": {
      "condition": "condition_snake_case",
      "confidence": 0.XX,
      "severity": "low|moderate|high|critical",
      "details": "Explanation..."
    },
    "recommendations": ["Action 1", "Action 2"],
    "contributing_factors": ["Factor 1", "Factor 2"],
    "expected_recovery": "X-Y weeks with treatment"
  },
  "acceptable_variance": {
    "diagnosis.confidence": 0.1
  },
  "metadata": {
    "sample_id": "GS-diag-XXX",
    "agent_name": "disease_diagnosis",
    "agent_type": "explorer",
    "description": "Test scenario description",
    "source": "synthetic",
    "tags": ["tag1", "tag2"],
    "priority": "P0"
  }
}
```

### Existing Explorer Workflow Architecture (from 0.75.16)

```
START -> fetch_context -> triage -> (router) -> analyze -> aggregate -> output -> END
                                       |
                          single_analyze OR parallel_analyze
```

**Key Features Already Implemented:**
- Saga pattern with conditional routing
- High confidence (>=0.7) -> single analyzer
- Low confidence (<0.7) -> parallel analyzers with timeout
- RAG context fetching from `RankingService`
- MCP context fetching via `AgentToolProvider`
- Result aggregation with confidence-based ranking

### Existing Golden Samples (3 samples)

| Sample ID | Condition | Confidence | Tags |
|-----------|-----------|------------|------|
| GS-diag-001 | tea_blister_blight | 0.88 | fungal, weather-correlation |
| GS-diag-002 | nutrient_deficiency_nitrogen | 0.82 | soil-health |
| GS-diag-003 | red_spider_mite_infestation | 0.91 | pest, dry-conditions |

### New Samples to Add (7+ samples)

| Sample ID | Category | Confidence | Severity | Key Scenario |
|-----------|----------|------------|----------|--------------|
| GS-diag-004 | Multiple diseases | ~0.75 | high | Rust + secondary infection |
| GS-diag-005 | Healthy | 0.95+ | N/A | No disease - control sample (condition: "healthy") |
| GS-diag-006 | Insufficient data | ~0.40 | low | Missing context, low confidence |
| GS-diag-007 | Weather damage | ~0.85 | moderate | Frost/drought damage |
| GS-diag-008 | Technique issue | ~0.78 | moderate | Over-pruning symptoms |
| GS-diag-009 | Contradictory | ~0.55 | low | Edge case - conflicting symptoms |
| GS-diag-010 | Regional anomaly | ~0.70 | moderate | Unusual pattern for region |

### Anti-Patterns to AVOID

1. **DO NOT** recreate ExplorerConfig, ExplorerState, ExplorerWorkflow - they exist!
2. **DO NOT** modify the existing workflow implementation
3. **DO NOT** skip variance comparison in golden sample tests
4. **DO NOT** test with real LLM calls - always mock
5. **DO NOT** put `system_prompt`/`template` at top level of prompt JSON - they go inside `content`
6. **DO NOT** forget `agent_id` in prompt - it MUST match the agent config

### Files to Create

| File | Type | Purpose |
|------|------|---------|
| `config/agents/disease-diagnosis.yaml` | Config | Sample explorer agent config |
| `config/prompts/disease-diagnosis.json` | Config | Sample prompt template |
| `tests/golden/disease_diagnosis/__init__.py` | Test | Package init |
| `tests/golden/disease_diagnosis/conftest.py` | Test | Test fixtures |
| `tests/golden/disease_diagnosis/test_disease_diagnosis_golden.py` | Test | Golden sample tests |

### Files to Modify

| File | Change |
|------|--------|
| `tests/golden/disease_diagnosis/samples.json` | Add 7+ new samples with full structure |

### References

- [Source: `services/ai-model/src/ai_model/workflows/explorer.py`]
- [Source: `services/ai-model/src/ai_model/domain/agent_config.py` @ ExplorerConfig:359-393]
- [Source: `services/ai-model/src/ai_model/domain/agent_config.py` @ RAGConfig:89-119]
- [Source: `services/ai-model/src/ai_model/domain/prompt.py` @ Prompt model]
- [Source: `tests/unit/ai_model/workflows/test_explorer.py`]
- [Source: `tests/golden/disease_diagnosis/samples.json`]
- [Source: `config/agents/qc-event-extractor.yaml` - Reference config structure]
- [Source: `config/prompts/qc-event-extractor.json` - Reference prompt structure]
- [Source: `_bmad-output/epics/epic-0-75-ai-model.md` @ Story 0.75.19]

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

**Created:**
- (list new files)

**Modified:**
- (list modified files with brief description)

---

_Story created: 2026-01-10_
_Story revised: 2026-01-10 - Reduced scope to config + golden tests (workflow already exists)_
_Story validated: 2026-01-10 - Fixed prompt structure, added Quick Reference, ensured agent_id in prompt_
_Created by: BMAD create-story workflow (SM Agent)_
