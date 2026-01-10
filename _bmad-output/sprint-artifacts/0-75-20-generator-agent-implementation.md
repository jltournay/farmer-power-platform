# Story 0.75.20: Generator Agent Implementation - Sample Config & Golden Tests

**Status:** ready-for-dev
**GitHub Issue:** #156

## Story

As a **developer**,
I want a sample Generator agent configuration (weekly-action-plan) with comprehensive golden sample tests,
So that the Generator workflow can be validated end-to-end and serve as a reference for future generator agents.

## Context

### What Already Exists (DO NOT RECREATE)

The Generator workflow infrastructure was fully implemented in **Story 0.75.16**:

| Component | Location | Lines | Status |
|-----------|----------|-------|--------|
| `GeneratorConfig` | `services/ai-model/src/ai_model/domain/agent_config.py:396-434` | 39 | **DONE** |
| `GeneratorState` | `services/ai-model/src/ai_model/workflows/states/generator.py` | 104 | **DONE** |
| `GeneratorWorkflow` | `services/ai-model/src/ai_model/workflows/generator.py` | **522** | **DONE** |
| `WorkflowExecutionService` | `services/ai-model/src/ai_model/workflows/execution_service.py` | 488 | **DONE** |
| `AgentExecutor` routing | `services/ai-model/src/ai_model/services/agent_executor.py` | - | **DONE** |

**Generator Workflow Features (from 0.75.16):**
- 5-node LangGraph workflow: `fetch_context` → `retrieve_knowledge` → `generate` → `format` → `output`
- RAG integration via `RankingService` for best practices grounding
- Multi-format output support (json, markdown, text)
- MCP context fetching via `AgentToolProvider`
- System prompt with format-specific instructions

### What This Story Creates

1. **Sample Agent Configuration** - `config/agents/weekly-action-plan.yaml`
2. **Sample Prompt Configuration** - `config/prompts/weekly-action-plan.json`
3. **Golden Samples (10+)** - `tests/golden/weekly_action_plan/samples.json`
4. **Golden Sample Test Runner** - `tests/golden/weekly_action_plan/test_weekly_action_plan_golden.py`
5. **Config Validation Tests** - `tests/golden/weekly_action_plan/test_config_validation.py`
6. **E2E Validation** - Verify generator workflow in Docker environment

### Architecture References

- Generator workflow: `services/ai-model/src/ai_model/workflows/generator.py`
- Agent types spec: `_bmad-output/architecture/ai-model-architecture/agent-types.md` @ Generator Type
- **Reference configs (MUST follow structure):**
  - `config/agents/disease-diagnosis.yaml` - Agent config structure (Story 0.75.19)
  - `config/prompts/disease-diagnosis.json` - Prompt config structure (Story 0.75.19)
  - `config/agents/qc-event-extractor.yaml` - Extractor pattern (Story 0.75.17)

### Generator Type Specification

From `agent-types.md`:

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
    model: "anthropic/claude-3-5-sonnet"   # Translation, simplification, cultural context
    temperature: 0.5                        # More creative
    output_format: "markdown"
  rag:
    enabled: true                           # For best practices
```

**Generator Type Purpose:** Create content (plans, reports, messages) - action plans, SMS summaries, voice scripts, reports.

---

## Acceptance Criteria

1. **AC1: Sample Agent Configuration** - Create `config/agents/weekly-action-plan.yaml`:
   - Valid `GeneratorConfig` schema
   - Agent ID: `weekly-action-plan`
   - LLM: Claude 3.5 Sonnet, temperature 0.5
   - RAG enabled with `tea-cultivation`, `regional-context`, `action-plan-best-practices` domains
   - Output format: markdown (with multi-format examples in samples)
   - MCP sources for farmer context and diagnosis results

2. **AC2: Sample Prompt Configuration** - Create `config/prompts/weekly-action-plan.json`:
   - **CRITICAL: `agent_id` field MUST match agent config (`weekly-action-plan`)**
   - System prompt for action plan generation inside `content` object
   - `output_schema` for structured content validation
   - `few_shot_examples` for format guidance
   - Validates against `Prompt` Pydantic model

3. **AC3: Golden Samples (10+ total)** - Create `tests/golden/weekly_action_plan/samples.json`:
   - Diverse farmer scenarios (high performers, struggling, weather-impacted, etc.)
   - Each sample with FULL expected_output structure
   - Multiple output formats tested (markdown, text, sms_summary)
   - Edge cases (missing context, conflicting diagnoses, urgent situations)

4. **AC4: Golden Sample Test Runner** - Create test infrastructure:
   - `tests/golden/weekly_action_plan/conftest.py` with fixtures
   - `tests/golden/weekly_action_plan/test_weekly_action_plan_golden.py`
   - Parametrized tests loading golden samples
   - Mock LLM returning expected responses
   - Full workflow execution path validation

5. **AC5: Config Validation** - Add config validation tests:
   - Test `weekly-action-plan.yaml` validates against `GeneratorConfig`
   - Test `weekly-action-plan.json` validates against `Prompt` model
   - Test `agent_id` in prompt matches agent config

6. **AC6: E2E Regression** - All existing E2E tests continue to pass

7. **AC7: CI Passes** - All lint checks and tests pass in CI

---

## Tasks / Subtasks

- [x] **Task 1: Create Sample Agent Configuration** (AC: #1) ✅ DONE
  - [x] Create `config/agents/weekly-action-plan.yaml` following `disease-diagnosis.yaml` structure:
    ```yaml
    # Weekly Action Plan Generator Agent Configuration
    # Story 0.75.20: Generator Agent Implementation
    #
    # This agent generates personalized weekly action plans for farmers
    # based on recent quality diagnoses, weather conditions, and best practices.
    #
    # See: _bmad-output/architecture/ai-model-architecture/agent-types.md @ Generator Type
    # Reference: GeneratorConfig in services/ai-model/src/ai_model/domain/agent_config.py:396-434

    id: "weekly-action-plan:1.0.0"
    agent_id: "weekly-action-plan"
    version: "1.0.0"
    type: generator
    status: active
    description: "Generates personalized weekly action plans for farmers based on diagnoses and conditions"

    # Input contract
    input:
      event: "ai.agent.requested"
      schema:
        type: object
        required:
          - farmer_id
        properties:
          farmer_id:
            type: string
            description: "Farmer identifier"
          diagnoses:
            type: array
            items:
              type: object
              properties:
                condition:
                  type: string
                severity:
                  type: string
                  enum: ["low", "moderate", "high", "critical"]
            description: "Recent diagnoses from Explorer agents"
          weather_forecast:
            type: object
            description: "7-day weather forecast"
          farmer_context:
            type: object
            description: "Farmer profile and recent performance"
          format_type:
            type: string
            enum: ["detailed", "sms_summary", "voice_script"]
            default: "detailed"

    # Output contract
    output:
      event: "ai.agent.weekly-action-plan.completed"
      schema:
        type: object
        required:
          - action_plan
          - summary
        properties:
          action_plan:
            type: object
            required:
              - week_of
              - priority_actions
            properties:
              week_of:
                type: string
                format: date
              priority_actions:
                type: array
                items:
                  type: object
                  properties:
                    action:
                      type: string
                    priority:
                      type: string
                      enum: ["critical", "high", "medium", "low"]
                    timing:
                      type: string
                    reason:
                      type: string
                minItems: 1
                maxItems: 5
              weather_considerations:
                type: array
                items:
                  type: string
              expected_outcomes:
                type: string
          summary:
            type: object
            properties:
              sms_message:
                type: string
                maxLength: 300
              voice_script:
                type: string
                maxLength: 2000
          metadata:
            type: object
            properties:
              diagnoses_used:
                type: integer
              rag_sources_used:
                type: integer

    # LLM configuration
    llm:
      model: "anthropic/claude-3-5-sonnet"
      temperature: 0.5
      max_tokens: 3000

    # RAG configuration (generator uses for best practices)
    rag:
      enabled: true
      query_template: "tea farming best practices for: {{conditions}} season: {{season}} region: {{region}}"
      knowledge_domains:
        - tea-cultivation
        - regional-context
        - action-plan-best-practices
      top_k: 5
      min_similarity: 0.65

    # Output format
    output_format: markdown

    # MCP sources for context fetching
    mcp_sources:
      - server: plantation-mcp
        tools:
          - get_farmer
          - get_region
          - get_weather_forecast
      - server: knowledge-mcp
        tools:
          - get_recent_diagnoses

    # Error handling
    error_handling:
      max_attempts: 3
      backoff_ms: [100, 500, 2000]
      on_failure: publish_error_event
      dead_letter_topic: null

    # Metadata
    metadata:
      author: "dev-story-0.75.20"
      created_at: "2026-01-10T00:00:00Z"
      updated_at: "2026-01-10T00:00:00Z"
      git_commit: null
    ```
  - [x] Validate YAML against `GeneratorConfig` Pydantic schema ✅

- [x] **Task 2: Create Sample Prompt Configuration** (AC: #2) ✅ DONE
  - [x] Create `config/prompts/weekly-action-plan.json` following `disease-diagnosis.json` structure:
    ```json
    {
      "id": "weekly-action-plan:1.0.0",
      "prompt_id": "weekly-action-plan",
      "agent_id": "weekly-action-plan",
      "version": "1.0.0",
      "status": "active",
      "content": {
        "system_prompt": "You are an expert tea farming advisor for the Farmer Power Platform.\n\nYour task is to create personalized weekly action plans for farmers based on:\n1. Recent quality diagnoses and issues\n2. Weather forecasts and conditions\n3. Farmer context (region, performance trends, farm size)\n4. Best practices from the knowledge base\n\nAction Plan Guidelines:\n- Maximum 5 priority actions (focus on most impactful)\n- Actions must be specific and actionable (start with verbs)\n- Consider farmer's capacity and resources\n- Adapt language for 6th-grade reading level\n- Include timing guidance (e.g., 'within 48 hours', 'before rain')\n\nPriority Levels:\n- critical: Immediate action required (disease outbreak, pest infestation)\n- high: Action needed this week (weather preparation, treatment follow-up)\n- medium: Beneficial if done this week (optimization, maintenance)\n- low: Can defer if needed (long-term improvements)\n\nSMS Summary: Max 300 characters, include most critical action and emoji\nVoice Script: Max 2000 characters, conversational tone, numbered actions\n\nRESPOND WITH ONLY VALID JSON matching the output schema.",
        "template": "Create a weekly action plan for the farmer based on the following context.\n\n## Farmer Context\n{{farmer_context}}\n\n## Recent Diagnoses\n{{diagnoses}}\n\n## Weather Forecast (7 days)\n{{weather_forecast}}\n\n## Best Practices (from knowledge base)\n{{rag_knowledge}}\n\n## Output Format Requested\n{{format_type}}\n\n## Required Output\nProvide a JSON object with:\n- action_plan: {week_of, priority_actions[], weather_considerations[], expected_outcomes}\n- summary: {sms_message (max 300 chars), voice_script (max 2000 chars)}",
        "output_schema": {
          "type": "object",
          "required": ["action_plan", "summary"],
          "properties": {
            "action_plan": {
              "type": "object",
              "required": ["week_of", "priority_actions"],
              "properties": {
                "week_of": {
                  "type": "string",
                  "format": "date"
                },
                "priority_actions": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "required": ["action", "priority", "timing"],
                    "properties": {
                      "action": {"type": "string"},
                      "priority": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                      "timing": {"type": "string"},
                      "reason": {"type": "string"}
                    }
                  },
                  "minItems": 1,
                  "maxItems": 5
                },
                "weather_considerations": {
                  "type": "array",
                  "items": {"type": "string"}
                },
                "expected_outcomes": {"type": "string"}
              }
            },
            "summary": {
              "type": "object",
              "properties": {
                "sms_message": {"type": "string", "maxLength": 300},
                "voice_script": {"type": "string", "maxLength": 2000}
              }
            }
          }
        },
        "few_shot_examples": [
          {
            "input": {
              "farmer_context": {"name": "John Kamau", "region": "Kericho-High", "farm_size": "small"},
              "diagnoses": [{"condition": "tea_blister_blight", "severity": "moderate"}],
              "weather_forecast": {"rain_probability": 0.7, "humidity_avg": 85},
              "format_type": "detailed"
            },
            "output": {
              "action_plan": {
                "week_of": "2026-01-13",
                "priority_actions": [
                  {
                    "action": "Apply copper-based fungicide to affected tea bushes",
                    "priority": "high",
                    "timing": "Within 48 hours, before rain",
                    "reason": "Treat blister blight before high humidity worsens spread"
                  },
                  {
                    "action": "Prune affected branches to improve air circulation",
                    "priority": "medium",
                    "timing": "After fungicide application",
                    "reason": "Reduce moisture retention that encourages fungal growth"
                  }
                ],
                "weather_considerations": [
                  "High humidity (85%) increases fungal disease risk",
                  "Apply fungicide before expected rain for absorption"
                ],
                "expected_outcomes": "With treatment, expect recovery in 2-3 weeks and reduced spread"
              },
              "summary": {
                "sms_message": "John, hatua ya wiki: 🌿 Nyunyiza dawa ya fungicide kwa majani yenye ugonjwa kabla ya mvua. Piga *384# kwa maelezo.",
                "voice_script": "Habari John. Hii ni mpango wako wa wiki. Kwanza, nyunyiza dawa ya fungicide kwa majani yenye ugonjwa ndani ya masaa 48. Pili, kata matawi yaliyoathirika baada ya kunyunyiza dawa. Mvua inatarajiwa, kwa hivyo fanya haraka."
              }
            }
          }
        ]
      },
      "metadata": {
        "author": "dev-story-0.75.20",
        "created_at": "2026-01-10T00:00:00Z",
        "updated_at": "2026-01-10T00:00:00Z",
        "changelog": "Initial version for Story 0.75.20",
        "git_commit": null
      },
      "ab_test": {
        "enabled": false,
        "traffic_percentage": 0.0,
        "test_id": null
      }
    }
    ```
  - [x] **VERIFY: `agent_id` matches agent config (`weekly-action-plan`)** ✅
  - [x] Validate JSON against `Prompt` Pydantic model ✅

- [x] **Task 3: Create Golden Samples** (AC: #3) ✅ DONE - 12 samples created
  - [x] Create `tests/golden/weekly_action_plan/samples.json` with 10+ samples:
    - [x] Sample 1: Standard weekly plan (moderate diagnosis, normal weather)
    - [x] Sample 2: Critical situation (disease outbreak, urgent actions)
    - [x] Sample 3: Weather-focused (heavy rain forecast, preventive actions)
    - [x] Sample 4: High-performer (maintenance focus, optimization)
    - [x] Sample 5: Struggling farmer (multiple issues, prioritized recovery)
    - [x] Sample 6: No active diagnoses (proactive best practices)
    - [x] Sample 7: SMS format request (short summary validation)
    - [x] Sample 8: Voice script format (Swahili conversational)
    - [x] Sample 9: Edge case - conflicting diagnoses
    - [x] Sample 10: Edge case - extreme weather (drought/frost)
  - [ ] Each sample MUST include this full expected_output structure:
    ```json
    {
      "input": {
        "farmer_id": "WM-XXXX",
        "diagnoses": [...],
        "weather_forecast": {...},
        "farmer_context": {...},
        "format_type": "detailed"
      },
      "expected_output": {
        "action_plan": {
          "week_of": "2026-01-13",
          "priority_actions": [...],
          "weather_considerations": [...],
          "expected_outcomes": "..."
        },
        "summary": {
          "sms_message": "...",
          "voice_script": "..."
        }
      },
      "acceptable_variance": {
        "priority_actions.length": 1
      },
      "metadata": {
        "sample_id": "GS-gen-XXX",
        "agent_name": "weekly_action_plan",
        "agent_type": "generator",
        "description": "Test scenario description",
        "source": "synthetic",
        "tags": ["tag1", "tag2"],
        "priority": "P0"
      }
    }
    ```

- [x] **Task 4: Create Golden Sample Test Runner** (AC: #4) ✅ DONE
  - [x] Create `tests/golden/weekly_action_plan/__init__.py`
  - [x] Create `tests/golden/weekly_action_plan/conftest.py`:
    - Fixtures for loading GeneratorConfig
    - Fixtures for loading golden samples
    - Mock LLM gateway returning expected outputs
  - [x] Create `tests/golden/weekly_action_plan/test_weekly_action_plan_golden.py`:
    - Parametrized tests for all 10+ samples
    - Workflow execution validation
    - Output structure validation
    - Format-specific tests (markdown, sms, voice)
  - [x] **CI Note:** Golden tests in `tests/golden/` use existing test infrastructure ✅

- [x] **Task 5: Add Config Validation Tests** (AC: #5) ✅ DONE
  - [x] Create `tests/golden/weekly_action_plan/test_config_validation.py`:
    - [x] Test weekly-action-plan.yaml validates against GeneratorConfig
    - [x] Test weekly-action-plan.json validates against Prompt model
    - [x] Test `agent_id` in prompt matches agent config
    - [x] Test config files can be loaded by AgentConfigCache
    - [x] Test output_format is valid (json/markdown/text)

- [x] **Task 6: E2E Regression Testing (MANDATORY)** (AC: #6) ✅ DONE
  - [x] Start E2E infrastructure: `bash scripts/e2e-up.sh --build`
  - [x] Run preflight validation: `bash scripts/e2e-preflight.sh`
  - [x] Run full E2E test suite: `bash scripts/e2e-test.sh --keep-up`
  - [x] Capture output in "Local Test Run Evidence" section
  - [x] Tear down: `bash scripts/e2e-up.sh --down`

- [ ] **Task 7: CI Verification (MANDATORY)** (AC: #7)
  - [x] Run lint: `ruff check . && ruff format --check .` ✅
  - [ ] Push and verify CI passes
  - [ ] Trigger E2E CI: `gh workflow run e2e.yaml --ref <branch>`
  - [ ] Verify E2E CI passes before code review

---

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.75.20: Generator Agent - Sample Config & Golden Tests"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/0-75-20-generator-agent-implementation
  ```

**Branch name:** `feature/0-75-20-generator-agent-implementation`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (config, test - not mixed)
- [ ] Push to feature branch: `git push -u origin feature/0-75-20-generator-agent-implementation`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.75.20: Generator Agent - Sample Config & Golden Tests" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d feature/0-75-20-generator-agent-implementation`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
pytest tests/golden/weekly_action_plan/ -v --tb=no -q
```
**Output:**
```
============================= test session starts ==============================
collected 63 items
tests/golden/weekly_action_plan/test_config_validation.py ... 35 passed
tests/golden/weekly_action_plan/test_weekly_action_plan_golden.py ... 28 passed
================= 63 passed, 8 warnings in 1.21s ===============================
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
================== 107 passed, 1 skipped in 130.57s (0:02:10) ==================
E2E Tests Complete
Infrastructure stopped and volumes removed
```
**E2E passed:** [x] Yes / [ ] No

### 3. Lint Check
```bash
ruff check . && ruff format --check .
```
**Lint passed:** [x] Yes / [ ] No
**Output:** All checks passed! 555 files already formatted

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin feature/0-75-20-generator-agent-implementation

# Trigger E2E CI
gh workflow run "E2E Tests" --ref feature/0-75-20-generator-agent-implementation

# Wait and check status
gh run list --branch feature/0-75-20-generator-agent-implementation --limit 3
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
| `GeneratorConfig` | `domain/agent_config.py:396-434` | `type: generator`, `rag: RAGConfig`, `output_format` |
| `RAGConfig` | `domain/agent_config.py:89-119` | `enabled`, `knowledge_domains`, `top_k`, `min_similarity` |
| `Prompt` | `domain/prompt.py` | `content: {system_prompt, template, output_schema, few_shot_examples}` |
| `PromptContent` | `domain/prompt.py:38-53` | `system_prompt`, `template`, `output_schema`, `few_shot_examples` |

### Generator-Specific Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `output_format` | `Literal["json", "markdown", "text"]` | No (default: markdown) | Target output format |
| `rag.query_template` | `str` | No | Template for RAG query construction |

### Prompt Structure (CRITICAL - agent_id MUST be present)

```json
{
  "id": "weekly-action-plan:1.0.0",
  "prompt_id": "weekly-action-plan",
  "agent_id": "weekly-action-plan",     // MUST match agent config!
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

### Generator Workflow Architecture (from 0.75.16)

```
START -> fetch_context -> retrieve_knowledge -> generate -> format -> output -> END
```

**Key Features Already Implemented:**
- Multi-format output (json, markdown, text)
- RAG knowledge retrieval via RankingService
- MCP context fetching via AgentToolProvider
- Template-based user prompt construction
- JSON/Markdown format cleanup in format node

### Golden Sample Categories

| Sample ID | Category | Priority | Scenario |
|-----------|----------|----------|----------|
| GS-gen-001 | Standard | P0 | Normal conditions, moderate diagnosis |
| GS-gen-002 | Critical | P0 | Disease outbreak, urgent actions |
| GS-gen-003 | Weather | P0 | Heavy rain forecast, preventive |
| GS-gen-004 | High-performer | P1 | Maintenance and optimization |
| GS-gen-005 | Struggling | P0 | Multiple issues, recovery focus |
| GS-gen-006 | Proactive | P1 | No diagnoses, best practices |
| GS-gen-007 | SMS Format | P0 | Short summary validation |
| GS-gen-008 | Voice Script | P1 | Swahili conversational |
| GS-gen-009 | Edge: Conflicts | P1 | Conflicting diagnoses |
| GS-gen-010 | Edge: Extreme | P1 | Drought or frost conditions |

### Anti-Patterns to AVOID

1. **DO NOT** recreate GeneratorConfig, GeneratorState, GeneratorWorkflow - they exist!
2. **DO NOT** modify the existing workflow implementation
3. **DO NOT** test with real LLM calls - always mock
4. **DO NOT** put `system_prompt`/`template` at top level of prompt JSON - they go inside `content`
5. **DO NOT** forget `agent_id` in prompt - it MUST match the agent config
6. **DO NOT** exceed SMS limit (300 chars) or voice script limit (2000 chars)

### Files to Create

| File | Type | Purpose |
|------|------|---------|
| `config/agents/weekly-action-plan.yaml` | Config | Sample generator agent config |
| `config/prompts/weekly-action-plan.json` | Config | Sample prompt template |
| `tests/golden/weekly_action_plan/__init__.py` | Test | Package init |
| `tests/golden/weekly_action_plan/conftest.py` | Test | Test fixtures |
| `tests/golden/weekly_action_plan/samples.json` | Test | 10+ golden samples |
| `tests/golden/weekly_action_plan/test_weekly_action_plan_golden.py` | Test | Golden sample tests |
| `tests/golden/weekly_action_plan/test_config_validation.py` | Test | Config validation tests |

### Previous Story Intelligence (from 0.75.19)

**Lessons Learned from Explorer Agent Implementation:**
- Config validation tests should be separate file (26 tests in 0.75.19)
- Golden sample tests may need skip decorator for schema alignment issues
- Workflow output schema may differ from expected_output - document explicitly
- Local E2E tests (107 passed) - important for regression
- CI E2E may have flaky tests (httpx.ReadTimeout) unrelated to story

**Code Review Findings to Avoid:**
- HIGH: Misleading test evidence (don't claim tests passed if they're skipped)
- MEDIUM: Register custom pytest markers in pytest.ini
- MEDIUM: Document workflow output schema differences explicitly

### References

- [Source: `services/ai-model/src/ai_model/workflows/generator.py`]
- [Source: `services/ai-model/src/ai_model/domain/agent_config.py` @ GeneratorConfig:396-434]
- [Source: `services/ai-model/src/ai_model/domain/agent_config.py` @ RAGConfig:89-119]
- [Source: `services/ai-model/src/ai_model/domain/prompt.py` @ Prompt model]
- [Source: `config/agents/disease-diagnosis.yaml` - Reference config structure]
- [Source: `config/prompts/disease-diagnosis.json` - Reference prompt structure]
- [Source: `_bmad-output/epics/epic-0-75-ai-model.md` @ Story 0.75.20]
- [Source: `_bmad-output/architecture/ai-model-architecture/agent-types.md` @ Generator Type]

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### Code Review Record

**Review Date:** _______________
**Reviewer:** _______________

### File List

**Created:**
- (list new files)

**Modified:**
- (list modified files with brief description)

---

_Story created: 2026-01-10_
_Created by: BMAD create-story workflow (SM Agent)_
