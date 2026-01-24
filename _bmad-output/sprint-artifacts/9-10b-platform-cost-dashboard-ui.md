# Story 9.10b: Platform Cost Dashboard UI

**Status:** ready-for-dev
**GitHub Issue:** #227

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **Platform Administrator**,
I want **a cost dashboard UI with tabs, charts, and budget configuration**,
so that **I can monitor platform spending across LLM, Document, and Embedding costs, identify cost drivers, and set budget thresholds**.

## Use Case Context

**Epic:** 9 - Platform Admin Portal
**Use Case:** UC9.3: Monitor Platform Costs
**Steps Covered:** 1-5 (frontend layer)
**Input (from preceding steps):** REST API endpoints operational from Story 9.10a (all `/api/admin/costs/*` endpoints)
**Output (for subsequent steps):** Complete cost monitoring UI accessible at `/costs` in the Admin Portal
**E2E Verification:** Admin navigates to `/costs` → sees total cost overview with live today's cost, daily trend chart, and cost breakdown tabs → can configure budget thresholds

## Acceptance Criteria

### AC 9.10b.1: Cost Overview Page (Default Tab)

**Given** I navigate to `/costs`
**When** the page loads
**Then** I see the Cost Dashboard with:
- **Today's Live Cost** metric card (polling every 60s, no caching) showing total_cost_usd + by_type breakdown
- **Budget Utilization** metric cards: daily utilization % with progress bar + monthly utilization %
- **Daily Cost Trend Chart** (stacked area/bar chart, last 30 days, stacked by cost type: LLM, Documents, Embeddings)
- **Cost Breakdown by Type** summary cards showing each type's total, request_count, and percentage
- **Date Range Picker** defaulting to last 30 days, updates all data when changed
**And** the page title is "Platform Costs"
**And** loading states show skeleton screens matching layout

### AC 9.10b.2: LLM Cost Tab

**Given** I am on the Cost Dashboard
**When** I click the "LLM" tab
**Then** I see:
- **By Agent Type** table/chart: agent_type, cost_usd, request_count, tokens_in, tokens_out, percentage
- **By Model** table/chart: model name, cost_usd, request_count, tokens_in, tokens_out, percentage
- Both respect the selected date range
- Totals shown at the top: total_llm_cost_usd

### AC 9.10b.3: Documents Cost Tab

**Given** I am on the Cost Dashboard
**When** I click the "Documents" tab
**Then** I see:
- Total document processing cost
- Total pages processed
- Average cost per page
- Document count for the period
- Date range respected from overview selection

### AC 9.10b.4: Embeddings Cost Tab

**Given** I am on the Cost Dashboard
**When** I click the "Embeddings" tab
**Then** I see:
- **By Domain** table/chart: knowledge_domain, cost_usd, tokens_total, texts_count, percentage
- Total embedding cost at the top
- Date range respected from overview selection

### AC 9.10b.5: Budget Configuration

**Given** I am on the Cost Dashboard
**When** I click "Configure Budget" button
**Then** I see a dialog/form with:
- Daily threshold (USD) input with current value pre-filled
- Monthly threshold (USD) input with current value pre-filled
- Validation: values must be > 0
- Save button calls PUT /api/admin/costs/budget
- Success shows confirmation snackbar with updated values
- Cancel closes dialog without changes

### AC 9.10b.6: Date Range Selection

**Given** I am on the Cost Dashboard
**When** I select a custom date range (start_date, end_date)
**Then** all endpoints are called with the new date range
**And** all charts, tables, and metrics update
**And** the trend chart adjusts its X-axis to match the date range

### AC 9.10b.7: Error & Loading States

**Given** the Platform Cost service is unavailable
**When** any API call fails with 503
**Then** an error alert is displayed: "Platform Cost service is unavailable. Please try again later."
**And** a retry button is available
**And** individual sections show error state independently (one failing doesn't block others)

### AC 9.10b.8: CSV Export

**Given** I am on any tab of the Cost Dashboard
**When** I click the "Export CSV" button
**Then** a CSV file is generated client-side from the currently displayed data
**And** the filename includes the date range and tab name (e.g., `costs-overview-2026-01-01-to-2026-01-31.csv`)

### AC-E2E (from Use Case)

**Given** the Platform Cost Service (Epic 13) is running with cost data populated and the BFF endpoints from Story 9.10a are operational
**When** the admin navigates to `/costs` in the Admin Portal
**Then** the overview tab displays total_cost_usd > 0 with a daily trend chart showing stacked costs and budget utilization bars reflecting configured thresholds

## Tasks / Subtasks

### Task 1: Add Recharts charting library (AC: 1, 2, 4)

- [x] Add `recharts` to `web/platform-admin/package.json` dependencies
- [x] Verify build still works after adding dependency

### Task 2: Create TypeScript types for cost API (AC: 1-8)

- [x] Add cost-related types to `web/platform-admin/src/api/types.ts`:
  - `CostSummaryResponse`, `CostTypeBreakdown`
  - `DailyTrendResponse`, `DailyTrendEntry`
  - `CurrentDayCostResponse`
  - `LlmByAgentTypeResponse`, `AgentTypeCostEntry`
  - `LlmByModelResponse`, `ModelCostEntry`
  - `DocumentCostResponse`
  - `EmbeddingByDomainResponse`, `DomainCostEntry`
  - `BudgetStatusResponse`, `BudgetConfigRequest`, `BudgetConfigResponse`
  - `CostDateRangeParams` (shared query param type)

### Task 3: Create cost API module (AC: 1-8)

- [x] Create `web/platform-admin/src/api/costs.ts`
- [x] Implement API functions: `getCostSummary`, `getDailyTrend`, `getCurrentDayCost`, `getLlmByAgentType`, `getLlmByModel`, `getDocumentCosts`, `getEmbeddingsByDomain`, `getBudgetStatus`, `configureBudget`
- [x] Follow pattern from `knowledge.ts` (use `apiClient` singleton)

### Task 4: Create reusable cost components (AC: 1-5) — See WF-5

- [x] Create `web/platform-admin/src/pages/costs/components/` directory
- [x] `MetricCard.tsx` — Reusable card showing label, value, subtitle, optional trend indicator
- [x] `BudgetBar.tsx` — Linear progress bar with utilization percentage and threshold
- [x] `DateRangePicker.tsx` — MUI-based date range selector (start_date, end_date)
- [x] `CostTrendChart.tsx` — Recharts stacked area chart for daily trend data
- [x] `CostBreakdownCards.tsx` — Grid of CostTypeBreakdown cards
- [x] `BudgetConfigDialog.tsx` — Dialog with form for budget threshold editing
- [x] `ExportButton.tsx` — CSV export button

### Task 5: Implement Overview Tab (AC: 1, 6, 7) — See WF-1

- [x] Create `web/platform-admin/src/pages/costs/tabs/OverviewTab.tsx`
- [x] Today's live cost with 60s polling interval (useEffect + setInterval)
- [x] Budget utilization bars (daily + monthly)
- [x] Daily trend stacked area chart
- [x] Cost breakdown cards
- [x] Skeleton loading states
- [x] Error states with retry button

### Task 6: Implement LLM Tab (AC: 2, 6, 7) — See WF-2

- [x] Create `web/platform-admin/src/pages/costs/tabs/LlmTab.tsx`
- [x] Agent type breakdown table with columns: agent_type, cost, requests, tokens_in, tokens_out, %
- [x] Model breakdown table with same columns
- [x] Respect date range from parent

### Task 7: Implement Documents Tab (AC: 3, 6, 7) — See WF-3

- [x] Create `web/platform-admin/src/pages/costs/tabs/DocumentsTab.tsx`
- [x] Metric cards: total cost, pages, avg cost/page, document count
- [x] Respect date range from parent

### Task 8: Implement Embeddings Tab (AC: 4, 6, 7) — See WF-4

- [x] Create `web/platform-admin/src/pages/costs/tabs/EmbeddingsTab.tsx`
- [x] Domain breakdown table: domain, cost, tokens, texts, %
- [x] Respect date range from parent

### Task 9: Implement CostDashboard page with tabs (AC: 1-8) — See WF-1

- [x] Replace placeholder in `web/platform-admin/src/pages/costs/CostDashboard.tsx`
- [x] MUI `Tabs` component with: Overview, LLM, Documents, Embeddings
- [x] Date range state lifted to page level, shared across tabs
- [x] Budget configure button in page header
- [x] Export CSV button in page header

### Task 10: Unit tests with Vitest (AC: all)

- [x] Test API module functions (mock fetch) — 11 tests in `tests/unit/web/platform-admin/api/costs.test.ts`
- [x] Test each tab component renders correctly with mock data — 20 tests in `tests/unit/web/platform-admin/pages/costs/CostDashboard.test.tsx`
- [x] Test date range changes trigger API refetch
- [x] Test budget dialog validation and submit
- [x] Test CSV export generates correct file content
- [x] Test 60s polling for today's cost
- [x] Test error states display correctly

### Task 11: Create E2E tests for AC-E2E (MANDATORY — CANNOT BE SKIPPED OR DEFERRED)

> **BLOCKER:** Story CANNOT be marked as "review" or "done" without this task completed.
> This task corresponds to the AC-E2E acceptance criterion and the E2E gate in CLAUDE.md Steps 9 & 13.
> Skipping, deferring, or marking as "to be verified later" is NOT acceptable.

- [x] Add tests to `tests/e2e/scenarios/test_11_platform_cost_bff.py` (extend existing file)
- [x] Test: GET `/api/admin/costs/summary` with date range returns `total_cost_usd > 0` and `by_type` array with entries
- [x] Test: GET `/api/admin/costs/trend/daily` returns `entries[]` with at least one day of data
- [x] Test: GET `/api/admin/costs/budget` returns budget status with `daily_threshold_usd` and `monthly_threshold_usd` > 0
- [x] Test: GET `/api/admin/costs/llm/by-agent-type` returns `agent_costs[]` with at least one entry
- [x] Test: GET `/api/admin/costs/embeddings/by-domain` returns `domain_costs[]`
- [ ] All tests MUST pass locally (`bash scripts/e2e-test.sh --keep-up`) before proceeding
- [ ] All tests MUST pass in CI (`gh workflow run e2e.yaml --ref <branch>`) before code review

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [x] GitHub Issue exists or created: #227
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/9-10b-platform-cost-dashboard-ui
  ```

**Branch name:** `story/9-10b-platform-cost-dashboard-ui`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/9-10b-platform-cost-dashboard-ui`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 9.10b: Platform Cost Dashboard UI" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/9-10b-platform-cost-dashboard-ui`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

> **REGRESSION RULE - NO EXCEPTIONS:**
> - Run the **FULL** test suite, not just tests you think are related to your change.
> - A previously passing test that now fails **IS a regression caused by your change**.
> - **Zero failures** is the only acceptable outcome. Fix all regressions before proceeding.
> - If you believe a test was already broken before your change, provide `git stash && pytest` evidence proving it fails on clean main too.

### 1. Unit Tests (Frontend)
```bash
cd web/platform-admin && npm test
```
**Output:**
```
(paste test summary here)
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
bash scripts/e2e-up.sh --build
bash scripts/e2e-preflight.sh
bash scripts/e2e-test.sh --keep-up
```
**Output:**
```
(paste E2E test output here - story is NOT ready for review without this)
```
**E2E passed:** [ ] Yes / [ ] No

### 3. Lint Check
```bash
cd web/platform-admin && npm run lint
ruff check . && ruff format --check .
```
**Lint passed:** [ ] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
git push origin story/9-10b-platform-cost-dashboard-ui
gh run list --branch story/9-10b-platform-cost-dashboard-ui --limit 3
```
**CI Run ID:** _______________
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### Architecture Compliance

**This is a frontend-only story.** No backend (Python/BFF/gRPC) changes needed.

**Layer Architecture:**
```
CostDashboard (page) → Tab Components → API Module → BFF REST Endpoints (Story 9.10a)
```

### Critical: API Endpoints Already Exist (DO NOT MODIFY BACKEND)

All REST endpoints were created in Story 9.10a. The frontend consumes:

| HTTP Method | Path | Response Type | Notes |
|-------------|------|---------------|-------|
| `GET` | `/api/admin/costs/summary` | `CostSummaryResponse` | Cached 5min in BFF |
| `GET` | `/api/admin/costs/trend/daily` | `DailyTrendResponse` | For stacked chart |
| `GET` | `/api/admin/costs/today` | `CurrentDayCostResponse` | NOT cached, poll 60s |
| `GET` | `/api/admin/costs/llm/by-agent-type` | `LlmByAgentTypeResponse` | LLM tab |
| `GET` | `/api/admin/costs/llm/by-model` | `LlmByModelResponse` | LLM tab |
| `GET` | `/api/admin/costs/documents` | `DocumentCostResponse` | Docs tab |
| `GET` | `/api/admin/costs/embeddings/by-domain` | `EmbeddingByDomainResponse` | Embeddings tab |
| `GET` | `/api/admin/costs/budget` | `BudgetStatusResponse` | Budget status |
| `PUT` | `/api/admin/costs/budget` | `BudgetConfigResponse` | Budget config |

**Query Parameters (shared across endpoints):**
- `start_date` (YYYY-MM-DD) - required for summary, documents
- `end_date` (YYYY-MM-DD) - required for summary, documents
- `days` (int, default 30) - for trend/daily
- `factory_id` (optional string) - for summary only

### Charting Library Decision: Recharts

**Why Recharts:**
- React-native (JSX component API, not imperative)
- Lightweight (~45KB gzipped)
- Built on D3 but with React components
- Excellent for area charts, bar charts, pie charts
- Active maintenance, 22k+ GitHub stars
- Compatible with MUI theming via custom colors

**Install:** `npm install recharts`

**Key components to use:**
- `<AreaChart>` with `<Area stackId="1">` for stacked daily trend
- `<BarChart>` for agent type / model breakdowns (alternative to table)
- `<ResponsiveContainer>` for responsive sizing

### Data Types (Frontend TypeScript)

All monetary values from the API are **strings** (decimal precision). Convert to number for display:
```typescript
const displayCost = parseFloat(response.total_cost_usd).toFixed(2);
```

Dates from API are ISO strings (`"2026-01-24"`). Use native `Date` or keep as strings for display.

### Polling Pattern (Today's Cost)

```typescript
useEffect(() => {
  const fetchToday = async () => { /* ... */ };
  fetchToday(); // Initial fetch
  const interval = setInterval(fetchToday, 60000); // 60s poll
  return () => clearInterval(interval);
}, []);
```

### CSV Export (Client-Side)

Generate CSV from current tab data without additional API calls:
```typescript
function exportToCsv(data: Record<string, unknown>[], filename: string) {
  const headers = Object.keys(data[0]);
  const csvContent = [
    headers.join(','),
    ...data.map(row => headers.map(h => JSON.stringify(row[h] ?? '')).join(','))
  ].join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
```

### UI Design Patterns (from project-context.md)

| Pattern | Implementation |
|---------|---------------|
| Design tokens | Use `--color-primary` (#16A34A), `--color-action` (#EF4444) for budget alerts |
| Loading states | Skeleton screens matching layout (not spinner-only) |
| Empty states | "No cost data for this period" with illustration |
| Error states | Alert with retry button, independent per section |
| Touch targets | 48x48px minimum for buttons |
| Budget alerts | Red (`--color-action`) when utilization > 90%, amber (`--color-watch`) > 75% |

### Budget Utilization Thresholds

| Utilization % | Color | Meaning |
|---------------|-------|---------|
| 0-75% | Green (`#22C55E`) | Healthy spending |
| 75-90% | Amber (`#F59E0B`) | Approaching limit |
| 90-100% | Red (`#EF4444`) | Near/over budget |

### File Structure (New Files)

```
web/platform-admin/src/
├── api/
│   ├── costs.ts                          # NEW - Cost API module
│   └── types.ts                          # MODIFIED - Add cost types
├── pages/
│   └── costs/
│       ├── CostDashboard.tsx             # MODIFIED - Replace placeholder
│       ├── components/
│       │   ├── MetricCard.tsx            # NEW
│       │   ├── BudgetBar.tsx             # NEW
│       │   ├── DateRangePicker.tsx       # NEW
│       │   ├── CostTrendChart.tsx        # NEW
│       │   ├── CostBreakdownCards.tsx    # NEW
│       │   ├── BudgetConfigDialog.tsx    # NEW
│       │   └── ExportButton.tsx          # NEW
│       └── tabs/
│           ├── OverviewTab.tsx           # NEW
│           ├── LlmTab.tsx               # NEW
│           ├── DocumentsTab.tsx         # NEW
│           └── EmbeddingsTab.tsx        # NEW
```

### Existing Route Already Configured

The route `/costs → CostDashboard` is already registered in `src/app/routes.tsx` (from Story 9.1a). The sidebar navigation item "Costs" already exists. No routing changes needed.

### MUI Components to Use

| MUI Component | Usage |
|---------------|-------|
| `Tabs` + `Tab` | Tab navigation (Overview, LLM, Documents, Embeddings) |
| `Card` + `CardContent` | Metric cards and section containers |
| `LinearProgress` | Budget utilization bars |
| `Table` / `TableBody` / `TableRow` | Breakdown tables (agent, model, domain) |
| `Dialog` + `DialogActions` | Budget configuration form |
| `TextField` (type="number") | Budget threshold inputs |
| `Snackbar` + `Alert` | Success/error notifications |
| `Skeleton` | Loading state placeholders |
| `IconButton` | Export, refresh actions |
| `CircularProgress` | Inline loading for today's cost refresh |

### Previous Story Intelligence (from 9.10a)

**Key learnings applied:**
1. All monetary values are `string` type from API (DecimalStr) — parse to float for display
2. Date parameters use ISO format `YYYY-MM-DD` — use native date inputs or MUI DatePicker
3. Budget PUT requires at least one threshold — validate before submit
4. BFF caches summary for 5 min — frontend can poll today's cost more frequently
5. Error responses are RFC 7807 format — parse `detail.message` for user display
6. Factory filter available on summary only — do NOT expose factory filter UI (admin-level view)
7. Infrastructure fix from 9-10a: platform-cost-dapr sidecar uses gRPC protocol (port 50054)

### Git Intelligence

**Recent commits (context):**
- `6811ea9` Story 9.10a: Platform Cost BFF REST API (#226) — The backend this story consumes
- `51ca9f5` Story 0.8.6: Cost Event Demo Data Generator — Demo data available for dev testing
- `4aab759` fix: Add platform-cost path to load_demo_data.py — Platform cost service integrated

### Testing Strategy

**Frontend tests (Vitest + Testing Library):**
- Mock `apiClient` calls with `vi.mock('./api/client')`
- Test component rendering with mock data
- Test user interactions (tab switching, date range, budget dialog)
- Test polling behavior with fake timers (`vi.useFakeTimers()`)
- Test CSV export generates correct content

**E2E tests required for AC-E2E** — extend `tests/e2e/scenarios/test_11_platform_cost_bff.py` to verify the full UC9.3 flow (BFF returns data that the UI can render: summary with total > 0, trend entries, budget thresholds). Frontend rendering is verified via Vitest unit tests with mock data.

### Dependencies

- Story 9.10a: Platform Cost BFF REST API (DONE - provides all endpoints)
- Story 9.1a: Platform Admin Application Scaffold (DONE - provides app shell, routing)
- Story 9.1b: Shared Admin UI Components (DONE - provides PageHeader, shared patterns)
- Story 0.8.6: Cost Event Demo Data Generator (DONE - provides test data)

### References

- [Source: services/bff/src/bff/api/schemas/admin/platform_cost_schemas.py] - API response schemas
- [Source: services/bff/src/bff/api/routes/admin/platform_cost.py] - API endpoint definitions
- [Source: web/platform-admin/src/api/knowledge.ts] - API module pattern reference
- [Source: web/platform-admin/src/pages/costs/CostDashboard.tsx] - Current placeholder to replace
- [Source: web/platform-admin/package.json] - Current dependencies
- [Source: _bmad-output/epics/epic-9-admin-portal/use-cases.md#UC9.3] - Use case definition
- [Source: _bmad-output/project-context.md#UI/UX Rules] - Design tokens and patterns

### Wireframes

#### WF-1: Total Cost Overview (Tasks 5, 9)

```
+---------------------------------------------------------------------------------+
|  PLATFORM COSTS                                          [Export v] [Budget]     |
+---------------------------------------------------------------------------------+
|                                                                                  |
|  [Total Overview]  [LLM]  [Documents]  [Embeddings]                             |
|  ===============                                                                 |
|                                                                                  |
|  DATE RANGE: [Last 30 days v]  [Custom: _____ to _____]                         |
|                                                                                  |
|  +-------------------+  +-------------------+  +-------------------+            |
|  |  TOTAL COST       |  |  TODAY (LIVE)     |  |  BUDGET STATUS    |            |
|  |  $1,892.30        |  |  $66.40           |  |  Monthly: 47%     |            |
|  |  Last 30 days     |  |  Updated 14:32    |  |  $1,892 / $4,000  |            |
|  |  3,386 requests   |  |  LLM: $45.20     |  |  Daily: 44%       |            |
|  +-------------------+  +-------------------+  +-------------------+            |
|                                                                                  |
|  +----------------------------------------------------------------------+       |
|  |  DAILY COST TREND (Stacked by Type)                                   |       |
|  |  $150 -+-------------------------------------------------------------+       |
|  |        |  LLM [solid]  Document [dots]  Embedding [hash]              |       |
|  |        |     ####        ####                                         |       |
|  |  $100 -+---####..------####..--------------------------------------   |       |
|  |        |  ####..##    ####..##                                        |       |
|  |   $50 -+-####..##----####..##--------------------------------------   |       |
|  |        |                                                              |       |
|  |    $0 -+--------------------------------------------------------------+       |
|  |        1   5   10   15   20   25   30                                 |       |
|  |  (i) Data available from: 2025-11-01 (TTL boundary)                   |       |
|  +----------------------------------------------------------------------+       |
|                                                                                  |
|  COST BY TYPE                                                                    |
|  +----------------------------------------------------------------------+       |
|  |  Type             | Cost (period) | Requests | Quantity  | % Total   |       |
|  |  -----------------+---------------+----------+-----------+-----------+       |
|  |  LLM (OpenRouter) | $1,195.50     | 2,340    | --        | 63%       |       |
|  |  Documents (Azure)| $412.30       | 156      | 1,240 pg  | 22%       |       |
|  |  Embeddings (Pine)| $284.50       | 890      | 45,200 tk | 15%       |       |
|  +----------------------------------------------------------------------+       |
|                                                                                  |
+---------------------------------------------------------------------------------+
```

#### WF-2: LLM Cost Detail (Task 6)

```
+---------------------------------------------------------------------------------+
|  PLATFORM COSTS                                          [Export v] [Budget]     |
+---------------------------------------------------------------------------------+
|                                                                                  |
|  [Total Overview]  [LLM]  [Documents]  [Embeddings]                             |
|                    =====                                                         |
|                                                                                  |
|  DATE RANGE: [Last 30 days v]  [Custom: _____ to _____]                         |
|                                                                                  |
|  +-------------------+  +-------------------+  +-------------------+            |
|  |  LLM TOTAL        |  |  REQUESTS         |  |  AVG COST/REQ     |            |
|  |  $1,195.50        |  |  2,340             |  |  $0.51            |            |
|  |  63% of total     |  |  Last 30 days     |  |  (calculated)     |            |
|  +-------------------+  +-------------------+  +-------------------+            |
|                                                                                  |
|  +---------------------------------+  +-------------------------------------+   |
|  |  COST BY AGENT TYPE             |  |  COST BY MODEL                       |   |
|  |                                  |  |                                      |   |
|  |  Agent Type    | Cost   | %      |  |  Model             | Cost   | %     |   |
|  |  --------------+--------+----    |  |  ------------------+--------+----   |   |
|  |  explorer      | $538   | 45%    |  |  claude-3-haiku    | $717   | 60%   |   |
|  |  generator     | $358   | 30%    |  |  gpt-4o-mini       | $299   | 25%   |   |
|  |  extractor     | $180   | 15%    |  |  gpt-4o            | $180   | 15%   |   |
|  |  other         | $120   | 10%    |  |                                      |   |
|  |                                  |  |                                      |   |
|  |  Reqs: 1,053  Tok-in: 2.1M     |  |  Reqs: 2,340  Tok-in: 4.8M          |   |
|  |                Tok-out: 890K    |  |                Tok-out: 1.9M         |   |
|  +---------------------------------+  +-------------------------------------+   |
|                                                                                  |
|  DETAILED AGENT TYPE BREAKDOWN                                                   |
|  +----------------------------------------------------------------------+       |
|  |  Agent Type  | Requests | Tokens In  | Tokens Out | Cost    | %      |       |
|  |  ------------+----------+------------+------------+---------+--------+       |
|  |  explorer    | 1,053    | 2,106,000  | 890,000    | $538.00 | 45%    |       |
|  |  generator   | 745      | 1,490,000  | 620,000    | $358.00 | 30%    |       |
|  |  extractor   | 342      | 684,000    | 285,000    | $180.00 | 15%    |       |
|  |  other       | 200      | 520,000    | 105,000    | $120.00 | 10%    |       |
|  +----------------------------------------------------------------------+       |
|                                                                                  |
+---------------------------------------------------------------------------------+
```

#### WF-3: Documents Cost Detail (Task 7)

```
+---------------------------------------------------------------------------------+
|  PLATFORM COSTS                                          [Export v] [Budget]     |
+---------------------------------------------------------------------------------+
|                                                                                  |
|  [Total Overview]  [LLM]  [Documents]  [Embeddings]                             |
|                            ===========                                           |
|                                                                                  |
|  DATE RANGE: [Last 30 days v]  [Custom: _____ to _____]                         |
|                                                                                  |
|  +-------------------+  +-------------------+  +-------------------+            |
|  |  DOCUMENT TOTAL   |  |  PAGES PROCESSED  |  |  AVG COST/PAGE    |            |
|  |  $412.30          |  |  1,240            |  |  $0.33            |            |
|  |  22% of total     |  |  156 documents    |  |  Azure Doc Intel  |            |
|  +-------------------+  +-------------------+  +-------------------+            |
|                                                                                  |
|  SUMMARY METRICS                                                                 |
|  +----------------------------------------------------------------------+       |
|  |  Metric              | Value                                         |       |
|  |  --------------------+-----------------------------------------------+       |
|  |  Total Cost          | $412.30                                       |       |
|  |  Documents Processed | 156                                           |       |
|  |  Total Pages         | 1,240                                         |       |
|  |  Avg Cost per Page   | $0.33                                         |       |
|  |  Period              | 2025-12-25 to 2026-01-24                       |       |
|  +----------------------------------------------------------------------+       |
|                                                                                  |
+---------------------------------------------------------------------------------+
```

#### WF-4: Embeddings Cost Detail (Task 8)

```
+---------------------------------------------------------------------------------+
|  PLATFORM COSTS                                          [Export v] [Budget]     |
+---------------------------------------------------------------------------------+
|                                                                                  |
|  [Total Overview]  [LLM]  [Documents]  [Embeddings]                             |
|                                        ============                              |
|                                                                                  |
|  DATE RANGE: [Last 30 days v]  [Custom: _____ to _____]                         |
|                                                                                  |
|  +-------------------+  +-------------------+  +-------------------+            |
|  |  EMBEDDING TOTAL  |  |  TEXTS EMBEDDED   |  |  TOTAL TOKENS     |            |
|  |  $284.50          |  |  4,520            |  |  3.2M             |            |
|  |  15% of total     |  |  Last 30 days     |  |  Pinecone         |            |
|  +-------------------+  +-------------------+  +-------------------+            |
|                                                                                  |
|  COST BY KNOWLEDGE DOMAIN                                                        |
|  +----------------------------------------------------------------------+       |
|  |  Domain              | Texts  | Tokens    | Cost    | % of Embedding |       |
|  |  --------------------+--------+-----------+---------+----------------+       |
|  |  tea-quality         | 1,890  | 1,340,000 | $119.00 | 42%            |       |
|  |  farming-practices   | 1,245  | 890,000   | $82.50  | 29%            |       |
|  |  pest-management     | 780    | 560,000   | $46.80  | 16%            |       |
|  |  weather-advisory    | 605    | 430,000   | $36.20  | 13%            |       |
|  +----------------------------------------------------------------------+       |
|                                                                                  |
+---------------------------------------------------------------------------------+
```

#### WF-5: Budget Configuration Modal (Task 4 — BudgetConfigDialog)

```
+---------------------------------------------------------------------------------+
|  BUDGET CONFIGURATION                                                      [X]  |
+---------------------------------------------------------------------------------+
|                                                                                  |
|  CURRENT STATUS                                                                  |
|  +----------------------------------------------------------------------+       |
|  |                                                                       |       |
|  |  DAILY BUDGET                          MONTHLY BUDGET                 |       |
|  |  +----------------------------+       +----------------------------+  |       |
|  |  |  Threshold: $150.00        |       |  Threshold: $4,000.00      |  |       |
|  |  |  Today:     $66.40 (44%)   |       |  This month: $1,892 (47%) |  |       |
|  |  |  Remaining: $83.60         |       |  Remaining:  $2,108        |  |       |
|  |  |                            |       |                             |  |       |
|  |  |  [########..........] 44%  |       |  [#########........] 47%   |  |       |
|  |  +----------------------------+       +----------------------------+  |       |
|  |                                                                       |       |
|  |  TODAY'S BREAKDOWN (by_type map):                                     |       |
|  |  LLM: $45.20 | Document: $12.80 | Embedding: $8.40                   |       |
|  |                                                                       |       |
|  +----------------------------------------------------------------------+       |
|                                                                                  |
|  CONFIGURE THRESHOLDS                                                            |
|  +----------------------------------------------------------------------+       |
|  |                                                                       |       |
|  |  Daily Threshold:    [$150.00     ]   (alert triggers when exceeded)  |       |
|  |  Monthly Threshold:  [$4,000.00   ]   (alert triggers when exceeded) |       |
|  |                                                                       |       |
|  |  (i) Alerts delivered by AlertManager via OTEL metrics.               |       |
|  |      Dashboard shows status only.                                     |       |
|  |                                                                       |       |
|  +----------------------------------------------------------------------+       |
|                                                                                  |
|                                                    {Cancel}  {Save Thresholds}  |
|                                                                                  |
+---------------------------------------------------------------------------------+
```

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
