# Story 9.12c: AI Agent & Prompt Viewer UI

**Status:** ready-for-dev
**GitHub Issue:** <!-- Auto-created by dev-story workflow -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **platform administrator**,
I want **a read-only AI Agent and Prompt viewer in the Admin Portal**,
so that **I can inspect agent configurations, their linked prompts, and prompt content without CLI access**.

## Use Case Context

**Epic:** 9 - Platform Admin Portal
**Use Case:** UC9.2: View AI Agent and Prompt Configurations
**Steps Covered:** Steps 1-5 (Full UI flow - list agents, filter, view detail, view prompts, expand prompt content)
**Input (from preceding steps):** BFF REST API endpoints `/api/admin/ai-agents`, `/api/admin/ai-agents/{agent_id}`, `/api/admin/ai-agents/{agent_id}/prompts` (Story 9.12b)
**Output (for subsequent steps):** Fully functional AI Agent & Prompt Viewer UI at `/ai-agents` route with full-page detail view
**E2E Verification:** Admin can navigate to AI Agents page, view paginated list, filter by type/status, click agent row to navigate to full-page detail view with Summary, LLM Config, RAG Config, Input/Output Contracts, and expandable linked prompts table with inline prompt content display

## Acceptance Criteria

### AC 9.12c.1: AI Agent List Page

**Given** I am authenticated as a platform administrator
**When** I navigate to `/ai-agents`
**Then** I see:
- PageHeader with title "AI Agents" and subtitle "AI agent configurations and linked prompts"
- FilterBar with filters: `agent_type` dropdown (extractor, explorer, generator, conversational, tiered-vision), `status` dropdown (active, staged, archived, draft)
- DataTable with columns: agent_id, type (Chip), version, status (Chip with color), model, prompt_count
- Pagination controls (page_size options: 10, 25, 50)
- Row click navigates to full-page Agent Detail view (`/ai-agents/{agent_id}`)
- Search field for filtering by agent_id or description

### AC 9.12c.2: AI Agent Detail Page (Full Page, NOT Drawer)

**Given** I click on an agent row OR navigate to `/ai-agents/{agent_id}`
**When** the detail page loads
**Then** I see:
- Back button "← Back to Agents" that navigates to `/ai-agents`
- PageHeader with agent_id as title
- **SUMMARY section**: agent_id, version, type (Chip), status (Chip), description, updated_at, created_at
- **LLM CONFIGURATION section**: model, temperature, max_tokens, top_p, response_format, retry config (max_retries, backoff, timeout)
- **RAG CONFIGURATION section**: rag_enabled (boolean), domains (array), top_k, score_threshold, namespace, include_metadata (or "Not configured" if no RAG)
- **INPUT CONTRACT section**: Required fields list with types and descriptions, Optional fields list
- **OUTPUT CONTRACT section**: Output schema name, field definitions with types and descriptions
- **RAW JSON section**: Collapsible section showing full `config_json` as formatted JSON
- Read-only indicator: "⚠️ Read-only view. Use `agent-config` and `prompt-config` CLIs to modify."

### AC 9.12c.3: Linked Prompts Table

**Given** I am on the agent detail page
**When** the page loads
**Then** I see a "LINKED PROMPTS" section with:
- DataTable with columns: prompt_id, version, status (Chip), author, updated_at
- Row count indicator (e.g., "3 linked prompts")
- Row click expands inline prompt detail (accordion pattern)

### AC 9.12c.4: Inline Prompt Detail Expansion

**Given** I click on a prompt row in the Linked Prompts table
**When** the row expands
**Then** I see:
- **Status & Metadata**: status chip, author, changelog, git_commit
- **System Prompt section**: Full text (collapsible if > 200 chars)
- **Template section**: Full text with {{variable}} highlighting (collapsible)
- **Output Schema section**: JSON schema display (collapsible)
- **Few-Shot Examples section**: Example list (collapsible, show count)
- **A/B Test Config section**: ab_test_enabled (boolean), ab_test_traffic_percentage (or "Disabled" if false)
- Click same row again to collapse

### AC 9.12c.5: Filter Functionality

**Given** the list page is loaded
**When** I select "extractor" from `agent_type` dropdown
**Then** only agents with `agent_type=extractor` are displayed

**When** I select "active" from `status` dropdown
**Then** only agents with `status=active` are displayed

**When** I clear all filters
**Then** all agents are displayed

### AC 9.12c.6: Empty/Error States

**Given** no agent configs exist or filters return empty
**Then** I see "No AI agents found" with appropriate icon

**Given** the BFF returns a 503 error
**Then** I see an error alert with retry option

**Given** agent detail load fails
**Then** I see an error message with back button to return to list

### AC 9.12c.7: Navigation Integration

**Given** the Admin Portal sidebar
**Then** "AI Agents" menu item exists under "Configuration" section (after "Source Configs")
**And** clicking it navigates to `/ai-agents`
**And** the route uses `ProtectedRoute` with `roles={['platform_admin']}`

### AC-E2E (from Use Case)

**Given** the E2E infrastructure is running with AI Model containing seed agent configs and prompts
**When** an admin navigates to `/ai-agents` in the Admin Portal
**Then** the page displays at least 3 agent configurations (qc-event-extractor, disease-diagnosis, weekly-action-plan)
**And** clicking an agent row navigates to detail page showing all structured sections
**And** clicking a prompt row in the detail page expands to show prompt content

## Tasks / Subtasks

### Task 1: TypeScript Interfaces (AC: 2, 3, 4)

- [ ] Create `web/platform-admin/src/types/agent-config.ts`
- [ ] Define `AgentConfigSummary` interface matching BFF response (agent_id, version, agent_type, status, description, model, prompt_count, updated_at)
- [ ] Define `AgentConfigDetail` interface with full config structure
- [ ] Define `LlmConfig` interface (model, temperature, max_tokens, top_p, response_format, retry)
- [ ] Define `RagConfig` interface (enabled, domains, top_k, score_threshold, namespace, include_metadata)
- [ ] Define `ContractConfig` interfaces for input/output contracts
- [ ] Define `PromptSummary` interface (id, prompt_id, agent_id, version, status, author, updated_at)
- [ ] Define `PromptDetail` interface (extends summary with system_prompt, template, output_schema_json, few_shot_examples_json, ab_test_enabled, ab_test_traffic_percentage, changelog, git_commit)
- [ ] Create helper functions: getAgentTypeLabel(), getAgentTypeColor(), getStatusLabel(), getStatusColor()

### Task 2: API Module (AC: 1, 5)

- [ ] Create `web/platform-admin/src/api/aiAgents.ts`
- [ ] Implement `listAiAgents(params)` function with filter params (page_size, page_token, agent_type, status)
- [ ] Implement `getAiAgent(agentId)` function returning AgentConfigDetail
- [ ] Implement `listPromptsByAgent(agentId)` function returning PromptSummary[]
- [ ] Export types and functions in `web/platform-admin/src/api/index.ts`
- [ ] Follow existing API patterns (see `sourceConfigs.ts`)

### Task 3: AI Agent List Page (AC: 1, 5, 6)

**Wireframe (ADR-019 Screen 2):**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🤖 AI AGENTS                                                [Filter ▼]     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  agent_id             │ type         │ version │ status  │ model   │prompts │
│  ─────────────────────┼──────────────┼─────────┼─────────┼─────────┼─────── │
│  disease-diagnosis    │ explorer     │ v1.0    │ 🟢 active│ gpt-4o  │   3    │
│  qc-event-extractor   │ extractor    │ v1.2    │ 🟢 active│ gpt-4o-m│   2    │
│  weekly-action-plan   │ generator    │ v1.0    │ 🟢 active│ gpt-4o  │   1    │
│  leaf-quality-analyzer│ tiered-vision│ v1.1    │ 🟢 active│ gpt-4o  │   2    │
│  farmer-chat          │ conversation │ v2.0    │ 🟡 staged│ gpt-4o  │   1    │
│                                                                              │
│  Showing 5 of 5                                       [← Previous] [Next →] │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Interaction:** Click row → Navigate to Agent Detail View (full page)

- [ ] Create `web/platform-admin/src/pages/ai-agents/AiAgentList.tsx`
- [ ] Use `PageHeader` component with title "AI Agents"
- [ ] Use `FilterBar` with `agent_type` dropdown and `status` dropdown filters
- [ ] Use `DataTable` with columns: agent_id, type (Chip), version, status (Chip), model, prompt_count
- [ ] Implement type chips with color: extractor=info, explorer=warning, generator=success, conversational=secondary, tiered-vision=primary
- [ ] Implement status chips with color: active=success, staged=warning, archived=default, draft=info
- [ ] Handle loading, error, and empty states
- [ ] Implement row click to navigate to detail page (`/ai-agents/${agentId}`)
- [ ] Implement search by agent_id or description
- [ ] Create index export: `web/platform-admin/src/pages/ai-agents/index.ts`

### Task 4: AI Agent Detail Page Component (AC: 2, 3, 4)

**IMPORTANT: This is a FULL PAGE detail view, NOT a Drawer/slide-out panel (differs from Source Config pattern)**

**Wireframe (ADR-019 Screen 2b):**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  [← Back to Agents]                                                          │
│                                                                              │
│  🤖 AI AGENT DETAIL: disease-diagnosis                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─ SUMMARY ──────────────────────────────────────────────────────────────┐ │
│  │  Agent ID:       disease-diagnosis                                     │ │
│  │  Version:        v1.0                                                  │ │
│  │  Type:           explorer                                              │ │
│  │  Status:         🟢 active                                             │ │
│  │  Description:    Diagnoses tea plant diseases from quality events      │ │
│  │                  and environmental data using RAG knowledge base       │ │
│  │  Updated:        2026-01-12 10:45 UTC                                  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ LLM CONFIGURATION ────────────────────────────────────────────────────┐ │
│  │  Model:              openai/gpt-4o                                     │ │
│  │  Temperature:        0.3                                               │ │
│  │  Max Tokens:         2048                                              │ │
│  │  Top P:              0.95                                              │ │
│  │  Response Format:    json_object                                       │ │
│  │                                                                        │ │
│  │  Retry Config:                                                         │ │
│  │    Max Retries:      3                                                 │ │
│  │    Backoff:          exponential                                       │ │
│  │    Timeout:          60s                                               │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ RAG CONFIGURATION ────────────────────────────────────────────────────┐ │
│  │  RAG Enabled:        ✅ Yes                                            │ │
│  │  Domains:            plant_diseases, tea_cultivation, weather_patterns │ │
│  │  Top K:              5                                                 │ │
│  │  Score Threshold:    0.75                                              │ │
│  │  Namespace:          knowledge-v12                                     │ │
│  │  Include Metadata:   ✅ Yes                                            │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ INPUT CONTRACT ───────────────────────────────────────────────────────┐ │
│  │  Required Fields:                                                      │ │
│  │    • farmer_id        (string)   - Farmer identifier                   │ │
│  │    • quality_events   (array)    - Recent quality event data           │ │
│  │    • weather_data     (object)   - Weather context for correlation     │ │
│  │                                                                        │ │
│  │  Optional Fields:                                                      │ │
│  │    • historical_data  (object)   - Past performance metrics            │ │
│  │    • region_context   (object)   - Regional agronomic context          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ OUTPUT CONTRACT ──────────────────────────────────────────────────────┐ │
│  │  Output Schema:      DiagnosisResult                                   │ │
│  │  Fields:                                                               │ │
│  │    • diagnosis_id     (string)   - Unique diagnosis identifier         │ │
│  │    • disease_name     (string)   - Identified disease or issue         │ │
│  │    • confidence       (float)    - Confidence score 0-1                │ │
│  │    • severity         (enum)     - low, medium, high, critical         │ │
│  │    • contributing_factors (array)- Factors that led to diagnosis       │ │
│  │    • recommendations  (array)    - Suggested actions                   │ │
│  │    • knowledge_refs   (array)    - RAG sources used                    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  (continued in Task 5: Linked Prompts section below...)                     │
│                                                                              │
│  ┌─ RAW JSON ─────────────────────────────────────────────────────────────┐ │
│  │  [▼ Expand to view full agent configuration JSON]                      │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ⚠️ Read-only view. Use `agent-config` and `prompt-config` CLIs to modify.  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

- [ ] Create `web/platform-admin/src/pages/ai-agents/AiAgentDetail.tsx`
- [ ] Implement back navigation with `useNavigate()` to `/ai-agents`
- [ ] Fetch agent detail on mount using `agentId` from URL params
- [ ] Parse `config_json` to render structured sections
- [ ] Implement SUMMARY section with status/type chips
- [ ] Implement LLM CONFIGURATION section with all model settings
- [ ] Implement RAG CONFIGURATION section (conditional - show "Not configured" if RAG disabled)
- [ ] Implement INPUT CONTRACT section with required/optional field lists
- [ ] Implement OUTPUT CONTRACT section with schema field definitions
- [ ] Implement collapsible RAW JSON section using MUI Accordion
- [ ] Add read-only warning alert

### Task 5: Linked Prompts Component (AC: 3, 4)

**Wireframe (ADR-019 Screen 2b - Linked Prompts section):**
```
│  ┌─ LINKED PROMPTS (3) ───────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  prompt_id              │ version │ status    │ author    │ updated    │ │
│  │  ───────────────────────┼─────────┼───────────┼───────────┼─────────── │ │
│  │  disease-diagnosis-main │ v2.1.0  │ 🟢 active │ jlt       │ 2026-01-15 │ │
│  │  disease-diagnosis-main │ v2.0.0  │ 📦 archived│ jlt       │ 2026-01-02 │ │
│  │  disease-diagnosis-main │ v1.0.0  │ 📦 archived│ agronomist│ 2025-12-20 │ │
│  │                                                                        │ │
│  │  [Click row to expand prompt detail below]                             │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ PROMPT DETAIL: disease-diagnosis-main v2.1.0 ─────────────────────────┐ │
│  │                                                                        │ │
│  │  Status:     🟢 active                                                 │ │
│  │  Author:     jlt                                                       │ │
│  │  Changelog:  Improved few-shot examples for blister blight detection   │ │
│  │  Git Commit: a1b2c3d                                                   │ │
│  │                                                                        │ │
│  │  ┌─ System Prompt ───────────────────────────────────────────────────┐ │ │
│  │  │ You are an expert tea plant pathologist and agronomist with deep  │ │ │
│  │  │ knowledge of East African tea cultivation. Your role is to        │ │ │
│  │  │ diagnose plant health issues based on quality metrics, weather    │ │ │
│  │  │ patterns, and historical data.                                    │ │ │
│  │  │                                                                   │ │ │
│  │  │ Guidelines:                                                       │ │ │
│  │  │ - Always consider weather lag effects (7-14 days)                 │ │ │
│  │  │ - Cross-reference with regional disease prevalence                │ │ │
│  │  │ - Provide actionable recommendations suitable for smallholders    │ │ │
│  │  │ ...                                                               │ │ │
│  │  │                                            [▼ Show full prompt]   │ │ │
│  │  └───────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                        │ │
│  │  ┌─ Template ────────────────────────────────────────────────────────┐ │ │
│  │  │ Analyze the following quality data for farmer {{farmer_id}}:      │ │ │
│  │  │                                                                   │ │ │
│  │  │ ## Quality Events (last 30 days)                                  │ │ │
│  │  │ {{quality_events}}                                                │ │ │
│  │  │                                                                   │ │ │
│  │  │ ## Weather Context                                                │ │ │
│  │  │ {{weather_data}}                                                  │ │ │
│  │  │                                                                   │ │ │
│  │  │ ## Knowledge Context                                              │ │ │
│  │  │ {{rag_context}}                                                   │ │ │
│  │  │                                            [▼ Show full template] │ │ │
│  │  └───────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                        │ │
│  │  ┌─ Output Schema ───────────────────────────────────────────────────┐ │ │
│  │  │ {                                                                 │ │ │
│  │  │   "type": "object",                                               │ │ │
│  │  │   "properties": {                                                 │ │ │
│  │  │     "diagnosis_id": { "type": "string" },                         │ │ │
│  │  │     "disease_name": { "type": "string" },                         │ │ │
│  │  │     "confidence": { "type": "number", "minimum": 0, "maximum": 1 }│ │ │
│  │  │     ...                                                           │ │ │
│  │  │   }                                                               │ │ │
│  │  │ }                                          [▼ Show full schema]   │ │ │
│  │  └───────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                        │ │
│  │  ┌─ Few-Shot Examples (2) ───────────────────────────────────────────┐ │ │
│  │  │ Example 1: Blister Blight Detection                               │ │ │
│  │  │ Example 2: Weather-Related Quality Drop                           │ │ │
│  │  │                                            [▼ Show examples]      │ │ │
│  │  └───────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                        │ │
│  │  ┌─ A/B Test Config ─────────────────────────────────────────────────┐ │ │
│  │  │ A/B Testing:      ❌ Disabled                                     │ │ │
│  │  └───────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
```

**Key Features:**
- Linked prompts table with version history
- Expandable prompt detail panel (click row to view)
- Prompt content sections: System Prompt, Template, Output Schema, Few-Shot Examples, A/B Test
- Collapsible sections for long content (system prompt, template, schema)
- `{{variable}}` placeholders highlighted in template text

- [ ] Create `web/platform-admin/src/pages/ai-agents/components/LinkedPromptsTable.tsx`
- [ ] Fetch prompts using `listPromptsByAgent(agentId)`
- [ ] Display prompts in DataTable with expandable rows (MUI DataGrid with detail panel or custom Accordion)
- [ ] Implement row expansion showing full prompt detail
- [ ] Create `web/platform-admin/src/pages/ai-agents/components/PromptDetailExpansion.tsx`
- [ ] Render all prompt sections: System Prompt, Template, Output Schema, Few-Shot Examples, A/B Test Config
- [ ] Implement collapsible sections for long content (> 200 chars)
- [ ] Highlight `{{variable}}` placeholders in template text with different color

### Task 6: Routing and Navigation (AC: 7)

- [ ] Add routes to `web/platform-admin/src/app/routes.tsx`:
  ```tsx
  {
    path: 'ai-agents',
    element: (
      <ProtectedRoute roles={['platform_admin']}>
        <AiAgentList />
      </ProtectedRoute>
    ),
  },
  {
    path: 'ai-agents/:agentId',
    element: (
      <ProtectedRoute roles={['platform_admin']}>
        <AiAgentDetail />
      </ProtectedRoute>
    ),
  },
  ```
- [ ] Add sidebar menu item in `web/platform-admin/src/components/Sidebar/Sidebar.tsx`:
  - Label: "AI Agents"
  - Path: `/ai-agents`
  - Icon: `SmartToyIcon` (or `PsychologyIcon`)
  - Place after "Source Configs" in menu order

### Task 7: Unit Tests (AC: All)

- [ ] Create `tests/unit/web/platform-admin/types/agentConfig.test.ts`
- [ ] Test type helper functions (getAgentTypeLabel, getAgentTypeColor, getStatusLabel, getStatusColor)
- [ ] Test parseConfigJson for different agent types
- [ ] Create `tests/unit/web/platform-admin/api/aiAgents.test.ts`
- [ ] Test listAiAgents with pagination and filters
- [ ] Test getAiAgent returning full detail with prompts
- [ ] Test listPromptsByAgent with status filter
- [ ] Test error handling (network errors, 404, unauthorized)
- [ ] Create component tests for AiAgentList and AiAgentDetail pages

### Task 8: E2E Tests (MANDATORY - DO NOT SKIP)

> **This task is NON-NEGOTIABLE and BLOCKS story completion.**

- [ ] API E2E tests exist in `tests/e2e/scenarios/test_38_admin_ai_agents.py` (Story 9.12b)
- [ ] Verify UI can consume API responses correctly
- [ ] Test list returns paginated data with 3+ configs
- [ ] Test agent_type filter shows only matching agents
- [ ] Test status filter shows only matching agents
- [ ] Test detail endpoint returns full config with config_json
- [ ] Test prompts endpoint returns linked prompts
- [ ] Test 404 for not found, 403 for non-admin

Note: Browser-based UI E2E tests require Playwright/Cypress which is out of scope.
The BFF API E2E tests validate the data layer that the UI consumes (22 tests passing).

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 9.12c: AI Agent & Prompt Viewer UI"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/9-12c-agent-prompt-viewer-ui
  ```

**Branch name:** `feature/9-12c-agent-prompt-viewer-ui`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, chore - not mixed)
- [ ] Push to feature branch: `git push -u origin feature/9-12c-agent-prompt-viewer-ui`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 9.12c: AI Agent & Prompt Viewer UI" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d feature/9-12c-agent-prompt-viewer-ui`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

> **REGRESSION RULE - NO EXCEPTIONS:**
> - Run the **FULL** test suite, not just tests you think are related to your change.
> - A previously passing test that now fails **IS a regression caused by your change**.
> - **Zero failures** is the only acceptable outcome. Fix all regressions before proceeding.

### 1. Unit Tests
```bash
# Frontend unit tests for this story
npx vitest run tests/unit/web/platform-admin/types/agentConfig.test.ts tests/unit/web/platform-admin/api/aiAgents.test.ts
```
**Output:**
```
(paste test summary here)
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure
bash scripts/e2e-up.sh --build

# Pre-flight validation
bash scripts/e2e-preflight.sh

# Run AI Agent BFF E2E tests (validates API layer for UI)
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/test_38_admin_ai_agents.py -v

# Tear down
bash scripts/e2e-up.sh --down
```
**Output:**
```
(paste E2E test output here)
```
**E2E passed:** [ ] Yes / [ ] No

### 3. Lint Check
```bash
# Backend
ruff check . && ruff format --check .

# Frontend build (includes TypeScript check)
npm run build -w @fp/platform-admin
```
**Lint passed:** [ ] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin feature/9-12c-agent-prompt-viewer-ui

# Trigger E2E CI workflow
gh workflow run "E2E Tests" --ref feature/9-12c-agent-prompt-viewer-ui

# Wait and check status
gh run view <run_id> --json status,conclusion
```
**CI Run ID:** _______________
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### Architecture Compliance

**This is a Frontend UI story.** Final step in the ADR-019 AI Agent visibility chain.

**Layer Architecture (ADR-019):**
```
Admin UI ← THIS STORY
    ↓ REST
BFF REST API (Story 9.12b)
    ↓ gRPC
AI Model gRPC (Story 9.12a)
    ↓
MongoDB agent_configs + prompts collections
```

### CRITICAL: Full-Page Detail View (NOT Drawer)

**Unlike Source Config story 9.11c which uses a slide-out Drawer, this story uses a FULL-PAGE detail view.**

Reason: Content density is significantly higher for AI Agents:
- Multiple configuration sections (LLM, RAG, Input/Output Contracts)
- Linked Prompts table with expandable rows
- Prompt content can be lengthy (system prompts, templates, schemas, examples)
- ADR-019 Screen 2b explicitly shows full-page layout

### Pattern: Navigate to Detail Page (NOT Open Drawer)

```tsx
// In AiAgentList.tsx - Row click navigates
const handleRowClick = (row: AgentConfigSummary) => {
  navigate(`/ai-agents/${row.agent_id}`);
};

// In AiAgentDetail.tsx - Back button navigates
const navigate = useNavigate();
const handleBack = () => navigate('/ai-agents');
```

### JSON Parsing Responsibility (Same as Source Config)

The `config_json` field from the API is a **JSON string**, not a parsed object. The frontend MUST parse it:

```tsx
// In AiAgentDetail.tsx
const configData = useMemo(() => {
  try {
    return JSON.parse(agentDetail.config_json);
  } catch {
    return null;
  }
}, [agentDetail.config_json]);
```

### TypeScript Interfaces (Mirror BFF Response Models)

Create interfaces that mirror `libs/fp-common/fp_common/models/agent_config_summary.py`:

```typescript
// web/platform-admin/src/types/agent-config.ts

export interface AgentConfigSummary {
  agent_id: string;
  version: string;
  agent_type: AgentType;
  status: AgentStatus;
  description: string;
  model: string;
  prompt_count: number;
  updated_at: string;
}

export type AgentType = 'extractor' | 'explorer' | 'generator' | 'conversational' | 'tiered-vision';
export type AgentStatus = 'draft' | 'staged' | 'active' | 'archived';

export interface AgentConfigDetail extends AgentConfigSummary {
  config_json: string;  // JSON string - must parse client-side
  prompts: PromptSummary[];
  created_at: string;
}

export interface PromptSummary {
  id: string;           // Format: {prompt_id}:{version}
  prompt_id: string;
  agent_id: string;
  version: string;
  status: string;
  author: string;
  updated_at: string;
}

// Parsed config_json structure
export interface AgentConfig {
  agent_id: string;
  version: string;
  agent_type: AgentType;
  status: AgentStatus;
  description: string;
  llm: LlmConfig;
  rag?: RagConfig;
  input_contract?: ContractConfig;
  output_contract?: ContractConfig;
}

export interface LlmConfig {
  model: string;
  temperature: number;
  max_tokens: number;
  top_p?: number;
  response_format?: string;
  retry?: {
    max_retries: number;
    backoff: string;
    timeout_seconds: number;
  };
}

export interface RagConfig {
  enabled: boolean;
  domains?: string[];
  top_k?: number;
  score_threshold?: number;
  namespace?: string;
  include_metadata?: boolean;
}
```

### Status and Type Chip Colors

```typescript
// Helper functions in agent-config.ts

export function getAgentTypeLabel(type: AgentType): string {
  const labels: Record<AgentType, string> = {
    extractor: 'Extractor',
    explorer: 'Explorer',
    generator: 'Generator',
    conversational: 'Conversational',
    'tiered-vision': 'Tiered Vision',
  };
  return labels[type] || type;
}

export function getAgentTypeColor(type: AgentType): 'info' | 'warning' | 'success' | 'secondary' | 'primary' {
  const colors: Record<AgentType, 'info' | 'warning' | 'success' | 'secondary' | 'primary'> = {
    extractor: 'info',
    explorer: 'warning',
    generator: 'success',
    conversational: 'secondary',
    'tiered-vision': 'primary',
  };
  return colors[type] || 'default';
}

export function getStatusColor(status: AgentStatus): 'success' | 'warning' | 'default' | 'info' {
  const colors: Record<AgentStatus, 'success' | 'warning' | 'default' | 'info'> = {
    active: 'success',
    staged: 'warning',
    archived: 'default',
    draft: 'info',
  };
  return colors[status] || 'default';
}
```

### Expandable Rows for Prompts

Use MUI DataGrid with detail panel OR custom Accordion pattern:

```tsx
// Option A: Custom Accordion pattern (simpler, recommended)
import { Accordion, AccordionSummary, AccordionDetails } from '@mui/material';

function LinkedPromptsTable({ prompts }: { prompts: PromptSummary[] }) {
  const [expanded, setExpanded] = useState<string | false>(false);

  return (
    <Box>
      {prompts.map((prompt) => (
        <Accordion
          key={prompt.id}
          expanded={expanded === prompt.id}
          onChange={(_, isExpanded) => setExpanded(isExpanded ? prompt.id : false)}
        >
          <AccordionSummary>
            {/* Prompt summary row */}
          </AccordionSummary>
          <AccordionDetails>
            <PromptDetailExpansion prompt={prompt} />
          </AccordionDetails>
        </Accordion>
      ))}
    </Box>
  );
}
```

### Template Variable Highlighting

Highlight `{{variable}}` patterns in template text:

```tsx
function TemplateDisplay({ template }: { template: string }) {
  // Split by variable pattern and highlight
  const parts = template.split(/(\{\{[^}]+\}\})/g);

  return (
    <Typography component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
      {parts.map((part, i) =>
        part.startsWith('{{') ? (
          <Box component="span" key={i} sx={{ color: 'primary.main', fontWeight: 600 }}>
            {part}
          </Box>
        ) : (
          part
        )
      )}
    </Typography>
  );
}
```

### File Structure (Changes)

```
web/platform-admin/src/
├── api/
│   ├── index.ts                              # MODIFIED - Export aiAgents
│   └── aiAgents.ts                           # NEW - API functions
├── types/
│   └── agent-config.ts                       # NEW - TypeScript interfaces
├── pages/
│   └── ai-agents/
│       ├── index.ts                          # NEW - Page exports
│       ├── AiAgentList.tsx                   # NEW - List page
│       ├── AiAgentDetail.tsx                 # NEW - Full-page detail
│       └── components/
│           ├── LinkedPromptsTable.tsx        # NEW - Prompts table
│           └── PromptDetailExpansion.tsx     # NEW - Inline prompt detail
├── app/
│   └── routes.tsx                            # MODIFIED - Add routes
├── components/
│   └── Sidebar/
│       └── Sidebar.tsx                       # MODIFIED - Add menu item

tests/
├── unit/web/platform-admin/
│   ├── types/agentConfig.test.ts             # NEW
│   ├── api/aiAgents.test.ts                  # NEW
│   └── pages/ai-agents/
│       ├── AiAgentList.test.tsx              # NEW
│       └── AiAgentDetail.test.tsx            # NEW
```

### Previous Story Intelligence (9.12b)

**From Story 9.12b completed 2026-01-28:**
- BFF REST endpoints:
  - `GET /api/admin/ai-agents` - List with pagination and filters
  - `GET /api/admin/ai-agents/{agent_id}` - Detail with config_json and prompts array
  - `GET /api/admin/ai-agents/{agent_id}/prompts` - Prompts list with status filter
- Response format: `{ data: AgentConfigSummary[], pagination: { total_count, page_size, next_page_token } }`
- Detail response includes `prompts[]` array directly (denormalized)
- 22 E2E tests passing in `test_38_admin_ai_agents.py`
- Seed data: 3 agent configs (qc-event-extractor, disease-diagnosis, weekly-action-plan), 3 prompts

**Key learnings from 9.12b:**
- `config_json` is a **string** - must be parsed client-side
- `prompts[]` array included in AgentConfigDetail (no separate fetch needed for detail page)
- Empty strings for nullable proto fields convert to None for API response
- Page token is skip offset encoded as string

### Reference Pattern (Story 9.11c)

**From Story 9.11c completed 2026-01-25:**
- Source Config viewer uses slide-out Drawer pattern
- **This story uses FULL-PAGE detail view instead** (content density difference)
- Same API module pattern: `listSourceConfigs()`, `getSourceConfig()`
- Same TypeScript interface pattern mirroring Pydantic models
- Same JSON parsing responsibility on frontend
- Same filter patterns with FilterBar and FilterDef[]

### Component Imports

```typescript
// From @fp/ui-components
import { PageHeader, DataTable, FilterBar, type FilterDef, type FilterValues } from '@fp/ui-components';

// From MUI
import {
  Box,
  Chip,
  Typography,
  IconButton,
  Button,
  Card,
  CardContent,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableBody,
  TableRow,
  TableCell,
  Alert,
  CircularProgress,
} from '@mui/material';
import type { GridColDef, GridPaginationModel } from '@mui/x-data-grid';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import SmartToyIcon from '@mui/icons-material/SmartToy';
```

### E2E Seed Data Available

From Story 9.12a/9.12b, seed data exists:
- `tests/e2e/infrastructure/seed/agent_configs.json` - 3 agent configs
- `tests/e2e/infrastructure/seed/prompts.json` - 3 prompts

Agent configs:
- qc-event-extractor (type: extractor, status: active)
- disease-diagnosis (type: explorer, status: active)
- weekly-action-plan (type: generator, status: active)

Prompts (linked to agents):
- qc-extraction → qc-event-extractor
- disease-diagnosis-main → disease-diagnosis
- weekly-action-plan-main → weekly-action-plan

### References

- [Source: _bmad-output/architecture/adr/ADR-019-admin-configuration-visibility.md#Decision-5] - Screen wireframes (Screen 2, 2b)
- [Source: _bmad-output/epics/epic-9-admin-portal/story-912c-agent-prompt-viewer-ui.md] - Story requirements
- [Source: _bmad-output/epics/epic-9-admin-portal/use-cases.md#UC9.2] - Use case flow
- [Source: web/platform-admin/src/pages/source-configs/SourceConfigList.tsx] - Reference list page pattern
- [Source: web/platform-admin/src/pages/source-configs/SourceConfigDetailPanel.tsx] - Reference detail pattern (but use full-page instead)
- [Source: web/platform-admin/src/api/sourceConfigs.ts] - API module pattern
- [Source: libs/fp-common/fp_common/models/agent_config_summary.py] - Pydantic models reference
- [Source: _bmad-output/sprint-artifacts/9-12b-agent-config-bff-client-rest.md] - Previous story learnings
- [Source: _bmad-output/sprint-artifacts/9-11c-source-config-viewer-ui.md] - Reference UI story
- [Source: _bmad-output/project-context.md#UI/UX-Rules] - Design system and accessibility rules

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
