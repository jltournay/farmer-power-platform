# Story 9.11c: Source Configuration Viewer UI

**Status:** in-progress
**GitHub Issue:** #233

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **platform administrator**,
I want **a read-only Source Configuration viewer in the Admin Portal**,
so that **I can inspect active source configs without CLI access or direct MongoDB queries**.

## Use Case Context

**Epic:** 9 - Platform Admin Portal
**Use Case:** UC9.1: View Source Configurations
**Steps Covered:** Steps 1-4 (Full UI flow)
**Input (from preceding steps):** BFF REST API endpoints `/api/admin/source-configs` and `/api/admin/source-configs/{source_id}` (Story 9.11b)
**Output (for subsequent steps):** Fully functional Source Configuration Viewer UI at `/source-configs` route
**E2E Verification:** Admin can navigate to Source Configurations page, view paginated list, filter by mode/enabled, click a row to see structured detail panel, and view raw JSON

## Acceptance Criteria

### AC 9.11c.1: Source Config List Page

**Given** I am authenticated as a platform administrator
**When** I navigate to `/source-configs`
**Then** I see:
- PageHeader with title "Source Configurations" and subtitle
- FilterBar with filters: `enabled_only` toggle, `ingestion_mode` dropdown
- DataTable with columns: source_id, display_name, ingestion_mode, enabled (chip), ai_agent_id
- Pagination controls (page_size options: 10, 25, 50)
- Row click opens detail slide-out panel

### AC 9.11c.2: Source Config Detail Panel (Slide-Out)

**Given** I click on a source configuration row
**When** the detail panel opens
**Then** I see structured sections:
- **SUMMARY**: source_id, display_name, description, enabled status (chip), updated_at (if available)
- **INGESTION**: Mode-dependent fields (see conditional rendering below)
- **VALIDATION**: schema_name, schema_version, strict_mode (or "Not configured")
- **TRANSFORMATION**: ai_agent_id (with link to AI Agent detail if configured), link_field, extract_fields, field_mappings
- **STORAGE**: raw_container, index_collection, ttl_days
- **EVENTS**: on_success (topic, payload), on_failure (topic, payload) (or "Not configured")
- Read-only indicator: "⚠️ Read-only view. Use `source-config` CLI to modify."
- Close button (X)

### AC 9.11c.3: Conditional Rendering by Ingestion Mode

**Given** the source config has ingestion mode `blob_trigger`
**Then** the INGESTION section shows: landing_container, file_pattern, file_format, trigger_mechanism, processor_type, path_pattern (pattern, extract_fields), processed_file_config (action, archive_ttl)

**Given** the source config has ingestion mode `scheduled_pull`
**Then** the INGESTION section shows: provider, schedule, request (base_url, auth_type, timeout), iteration (foreach, source_mcp, source_tool, concurrency), retry (max_attempts, backoff)

### AC 9.11c.4: Filter Functionality

**Given** the list page is loaded
**When** I toggle `enabled_only` to true
**Then** only configs with `enabled=true` are displayed

**When** I select `blob_trigger` from `ingestion_mode` dropdown
**Then** only configs with `ingestion_mode=blob_trigger` are displayed

### AC 9.11c.5: Empty/Error States

**Given** no source configs exist or filters return empty
**Then** I see "No source configurations found" with appropriate icon

**Given** the BFF returns a 503 error
**Then** I see an error alert with retry option

### AC 9.11c.6: Navigation Integration

**Given** the Admin Portal sidebar
**Then** "Source Configs" menu item exists under "Configuration" section (after "Costs")
**And** clicking it navigates to `/source-configs`
**And** the route uses `ProtectedRoute` with `roles={['platform_admin']}`

### AC-E2E (from Use Case)

**Given** the E2E infrastructure is running with Collection Model containing seed source configs
**When** an admin navigates to `/source-configs` in the Admin Portal
**Then** the page displays at least 2 source configurations
**And** clicking a row opens a detail panel with all structured sections rendered (all config_json fields displayed)

## Tasks / Subtasks

### Task 1: TypeScript Interfaces (AC: 2, 3)

- [x] Create `web/platform-admin/src/types/source-config.ts`
- [x] Define `SourceConfigSummary` interface matching BFF response
- [x] Define `SourceConfigDetail` interface with full config structure
- [x] Define `IngestionConfig` interface with union type for mode-specific fields
- [x] Define `ValidationConfig`, `TransformationConfig`, `StorageConfig`, `EventsConfig` interfaces
- [x] Define `SourceConfigListResponse` and `SourceConfigDetailResponse` API response types

### Task 2: API Module (AC: 1, 4)

- [x] Create `web/platform-admin/src/api/sourceConfigs.ts`
- [x] Implement `listSourceConfigs(params)` function with filter params
- [x] Implement `getSourceConfig(sourceId)` function
- [x] Export types and functions in `web/platform-admin/src/api/index.ts`
- [x] Follow existing API patterns (see `gradingModels.ts`)

### Task 3: Source Config List Page (AC: 1, 4, 5)

**Wireframe:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🔗 SOURCE CONFIGURATIONS                                    [Filter ▼]     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  source_id          │ display_name       │ mode          │ enabled │ agent  │
│  ───────────────────┼────────────────────┼───────────────┼─────────┼─────── │
│  qc-analyzer-result │ QC Analyzer Result │ blob_trigger  │ ✅      │ qc-ext │
│  qc-analyzer-except │ QC Exceptions      │ blob_trigger  │ ✅      │ exc-ex │
│  weather-forecast   │ Weather Forecast   │ scheduled_pull│ ✅      │ -      │
│  market-prices      │ Market Prices      │ scheduled_pull│ ❌      │ -      │
│                                                                              │
│  Showing 4 of 4                                       [← Previous] [Next →] │
└─────────────────────────────────────────────────────────────────────────────┘
```

- [x] Create `web/platform-admin/src/pages/source-configs/SourceConfigList.tsx`
- [x] Use `PageHeader` component with title "Source Configurations"
- [x] Use `FilterBar` with `enabled_only` toggle and `ingestion_mode` dropdown filter
- [x] Use `DataTable` with columns: source_id, display_name, ingestion_mode, enabled (Chip), ai_agent_id
- [x] Implement enabled chip with color (green=enabled, gray=disabled)
- [x] Handle loading, error, and empty states
- [x] Implement row click to open detail panel (NOT navigate to new page)
- [x] Create index export: `web/platform-admin/src/pages/source-configs/index.ts`

### Task 4: Source Config Detail Panel Component (AC: 2, 3)

**Wireframe (Blob Trigger Mode):**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🔗 SOURCE CONFIGURATION DETAIL                                    [✕ Close]│
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─ SUMMARY ──────────────────────────────────────────────────────────────┐ │
│  │  Source ID:     qc-analyzer-result                                     │ │
│  │  Display Name:  QC Analyzer Result                                     │ │
│  │  Description:   Tea leaf quality analysis results from QC Analyzer     │ │
│  │  Status:        ✅ Enabled                                             │ │
│  │  Updated:       2026-01-15 14:32 UTC                                   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ INGESTION ────────────────────────────────────────────────────────────┐ │
│  │  Mode:              blob_trigger                                       │ │
│  │  Landing Container: qc-analyzer-landing                                │ │
│  │  File Pattern:      *.json                                             │ │
│  │  File Format:       json                                               │ │
│  │  Trigger:           event_grid                                         │ │
│  │  Processor Type:    json-extraction                                    │ │
│  │                                                                        │ │
│  │  Path Pattern:                                                         │ │
│  │    Pattern:         {region}/{factory}/{date}/{filename}               │ │
│  │    Extract Fields:  region, factory, date                              │ │
│  │                                                                        │ │
│  │  Processed File Config:                                                │ │
│  │    Action:          archive                                            │ │
│  │    Archive TTL:     90 days                                            │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ VALIDATION ───────────────────────────────────────────────────────────┐ │
│  │  Schema Name:    data/qc-bag-result.json                               │ │
│  │  Schema Version: latest                                                │ │
│  │  Strict Mode:    ✅ Yes                                                │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ TRANSFORMATION ───────────────────────────────────────────────────────┐ │
│  │  AI Agent ID:    qc-event-extractor                          [View →]  │ │
│  │  Link Field:     farmer_id                                             │ │
│  │  Extract Fields: farmer_id, grade, weight_kg, leaf_type, attributes    │ │
│  │                                                                        │ │
│  │  Field Mappings:                                                       │ │
│  │    bag_weight     → weight_kg                                          │ │
│  │    quality_grade  → grade                                              │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ STORAGE ──────────────────────────────────────────────────────────────┐ │
│  │  Raw Container:     raw-documents                                      │ │
│  │  Index Collection:  qc_results                                         │ │
│  │  TTL Days:          365                                                │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ EVENTS ───────────────────────────────────────────────────────────────┐ │
│  │  On Success:                                                           │ │
│  │    Topic:         collection.quality_result.received                   │ │
│  │    Payload:       farmer_id, grade, weight_kg, collection_point_id     │ │
│  │                                                                        │ │
│  │  On Failure:                                                           │ │
│  │    Topic:         collection.ingestion.failed                          │ │
│  │    Payload:       source_id, error_message, document_id                │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ⚠️ Read-only view. Use `source-config` CLI to modify.                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Wireframe (Scheduled Pull Mode - INGESTION section differs):**
```
│  ┌─ INGESTION (Scheduled Pull) ───────────────────────────────────────────┐ │
│  │  Mode:              scheduled_pull                                     │ │
│  │  Provider:          open-meteo                                         │ │
│  │  Schedule:          0 6 * * * (daily at 6:00 AM)                       │ │
│  │                                                                        │ │
│  │  Request Config:                                                       │ │
│  │    Base URL:        https://api.open-meteo.com/v1/forecast             │ │
│  │    Auth Type:       none                                               │ │
│  │    Timeout:         30s                                                │ │
│  │                                                                        │ │
│  │  Iteration Config:                                                     │ │
│  │    Foreach:         region                                             │ │
│  │    Source MCP:      plantation                                         │ │
│  │    Source Tool:     list_regions                                       │ │
│  │    Concurrency:     5                                                  │ │
│  │                                                                        │ │
│  │  Retry Config:                                                         │ │
│  │    Max Attempts:    3                                                  │ │
│  │    Backoff:         exponential                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
```

**CRITICAL:** All fields from `config_json` MUST be rendered in the detail panel. The structured sections should display every field from the SourceConfig model - no fields should be omitted. Reference `libs/fp-common/fp_common/models/source_config.py` for the complete field list.

- [x] Create `web/platform-admin/src/pages/source-configs/SourceConfigDetailPanel.tsx`
- [x] Implement Drawer component (slide-out from right, width: 600-700px)
- [x] Parse `config_json` to render ALL fields in structured sections
- [x] Implement OVERVIEW section with status chip (source_id, display_name, description, enabled, ingestion_mode)
- [x] Implement INGESTION section with conditional rendering by mode (blob_trigger vs scheduled_pull) - render ALL ingestion fields
- [x] Implement VALIDATION section (schema_name, schema_version, strict_mode - handle null with "Not configured")
- [x] Implement TRANSFORMATION section (ai_agent_id, link_field, extract_fields, field_mappings)
- [x] Implement STORAGE section (raw_container, index_collection, file_container, ttl_days)
- [x] Implement EVENTS section (on_success topic/payload, on_failure topic/payload - handle null with "Not configured")
- [x] Add created_at/updated_at metadata footer
- [x] Verify ALL fields from SourceConfig model are displayed somewhere in the panel

### Task 5: Routing and Navigation (AC: 6)

- [x] Add route to `web/platform-admin/src/app/routes.tsx`:
  ```tsx
  {
    path: 'source-configs',
    element: (
      <ProtectedRoute roles={['platform_admin']}>
        <SourceConfigList />
      </ProtectedRoute>
    ),
  },
  ```
- [x] Add sidebar menu item in `web/platform-admin/src/components/Sidebar/Sidebar.tsx`:
  - Label: "Source Configs"
  - Path: `/source-configs`
  - Icon: `SettingsInputComponentIcon`
  - Place after "Costs" in menu order

### Task 6: Unit Tests (AC: All)

- [x] Create `tests/unit/web/platform-admin/types/sourceConfigs.test.ts`
- [x] Test type helper functions (getIngestionModeLabel, getIngestionModeColor, etc.)
- [x] Test parseConfigJson for blob_trigger and scheduled_pull configs
- [x] Test getAiAgentId with ai_agent_id, agent fallback, and null cases
- [x] Create `tests/unit/web/platform-admin/api/sourceConfigs.test.ts`
- [x] Test listSourceConfigs with pagination and filters
- [x] Test getSourceConfig for blob_trigger and scheduled_pull configs
- [x] Test error handling (network errors, 404, unauthorized)
- [x] All 24 unit tests passing

### Task 7: E2E Tests (MANDATORY - DO NOT SKIP)

> **This task is NON-NEGOTIABLE and BLOCKS story completion.**

- [ ] Add tests to existing E2E test file or create `tests/e2e/scenarios/test_14_source_config_ui.py`
- [ ] Test page loads at `/source-configs` with data
- [ ] Test enabled_only filter shows only enabled configs
- [ ] Test ingestion_mode filter shows only matching configs
- [ ] Test clicking row opens detail panel
- [ ] Test detail panel shows all sections for blob_trigger config (all fields rendered)
- [ ] Test detail panel shows all sections for scheduled_pull config (all fields rendered)
- [ ] Test close button closes detail panel

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 9.11c: Source Configuration Viewer UI"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/9-11c-source-config-viewer-ui
  ```

**Branch name:** `feature/9-11c-source-config-viewer-ui`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin feature/9-11c-source-config-viewer-ui`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 9.11c: Source Configuration Viewer UI" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d feature/9-11c-source-config-viewer-ui`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

> **⛔ REGRESSION RULE — NO EXCEPTIONS:**
> - Run the **FULL** test suite, not just tests you think are related to your change.
> - A previously passing test that now fails **IS a regression caused by your change**.
> - "Not related to my change" is **NEVER** a valid reason to skip or ignore a failing test.
> - **Zero failures** is the only acceptable outcome. Fix all regressions before proceeding.

### 1. Unit Tests
```bash
# Frontend unit tests for this story
cd web/platform-admin && npm test -- --coverage --watchAll=false

# All unit tests
pytest tests/unit/ -v
```
**Output:**
```
(paste test summary here - e.g., "42 passed in 5.23s")
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure
bash scripts/e2e-up.sh --build

# Pre-flight validation
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
# Backend
ruff check . && ruff format --check .

# Frontend
cd web/platform-admin && npm run lint
```
**Lint passed:** [ ] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin feature/9-11c-source-config-viewer-ui

# Trigger E2E CI workflow
gh workflow run e2e.yaml --ref feature/9-11c-source-config-viewer-ui

# Wait and check status
sleep 10
gh run list --workflow=e2e.yaml --branch feature/9-11c-source-config-viewer-ui --limit 1
```
**CI Run ID:** _______________
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### Architecture Compliance

**This is a Frontend UI story.** Final step in the ADR-019 Source Config visibility chain.

**Layer Architecture (ADR-019):**
```
Admin UI ← THIS STORY
    ↓ REST
BFF REST API (Story 9.11b)
    ↓ gRPC
Collection Model gRPC (Story 9.11a)
    ↓
MongoDB source_configs collection
```

### Critical: Follow Existing Admin Portal Patterns

**MUST USE THESE PATTERNS:**

1. **List Page Pattern** - See `GradingModelList.tsx`:
   - Use `PageHeader`, `FilterBar`, `DataTable` from `@fp/ui-components`
   - State management: loading, error, data, paginationModel, filters
   - `useCallback` for data fetching
   - `useEffect` to trigger fetch on dependency change

2. **Detail Panel Pattern** - Use MUI `Drawer` component:
   - Anchor: right
   - Width: 480px (fixed)
   - Close button in header
   - Scrollable content area
   - Structured sections with `Box` and `Typography`

3. **API Module Pattern** - See `gradingModels.ts`:
   - Use `apiClient` from `./client`
   - Export async functions with typed params and responses
   - BASE_PATH constant

4. **Filter Pattern** - See `GradingModelList.tsx`:
   - `FilterDef[]` array for filter definitions
   - `FilterValues` object for filter state
   - `onFilterChange` handler

### JSON Parsing Responsibility (ADR-019 Implementation Notes)

**CRITICAL:** The `config_json` field from the API is a **JSON string**, not a parsed object. The frontend MUST parse it:

```tsx
// In SourceConfigDetailPanel.tsx
const configData = JSON.parse(sourceConfigDetail.config_json);
// Now access: configData.ingestion, configData.validation, etc.
```

### TypeScript Interfaces (Mirror Pydantic Models)

Create interfaces that mirror `libs/fp-common/fp_common/models/source_config.py`:

```typescript
// Key interfaces needed
interface SourceConfig {
  source_id: string;
  display_name: string;
  description: string;
  enabled: boolean;
  ingestion: IngestionConfig;
  validation: ValidationConfig | null;
  transformation: TransformationConfig;
  storage: StorageConfig;
  events: EventsConfig | null;
}

interface IngestionConfig {
  mode: 'blob_trigger' | 'scheduled_pull';
  // blob_trigger fields (optional)
  landing_container?: string;
  path_pattern?: PathPatternConfig;
  file_pattern?: string;
  file_format?: 'json' | 'zip';
  trigger_mechanism?: 'event_grid';
  processed_file_config?: ProcessedFileConfig;
  processor_type?: string;
  // scheduled_pull fields (optional)
  provider?: string;
  schedule?: string;
  request?: RequestConfig;
  iteration?: IterationConfig;
  retry?: RetryConfig;
}
```

### Conditional Rendering by Ingestion Mode

```tsx
{configData.ingestion.mode === 'blob_trigger' ? (
  <BlobTriggerSection ingestion={configData.ingestion} />
) : (
  <ScheduledPullSection ingestion={configData.ingestion} />
)}
```

### Timestamp Field Handling

The `SourceConfig` Pydantic model does **NOT include timestamps** (`created_at`, `updated_at`). Proto fields exist but return `null`.

**Recommendation:** Hide the "Updated" field if null:

```tsx
{sourceConfigDetail.updated_at && (
  <DetailRow label="Updated" value={formatDate(sourceConfigDetail.updated_at)} />
)}
```

### Null Safety for Optional Fields

Many config sections are optional. Use null coalescing:

```tsx
const schemaName = configData.validation?.schema_name ?? 'Not configured';
const aiAgentId = configData.transformation?.ai_agent_id || '-';
```

### Component Imports

```typescript
// From @fp/ui-components
import { PageHeader, DataTable, FilterBar, type FilterDef, type FilterValues } from '@fp/ui-components';

// From MUI
import { Box, Chip, Drawer, Typography, IconButton, Collapse, Alert, CircularProgress } from '@mui/material';
import type { GridColDef, GridPaginationModel } from '@mui/x-data-grid';
import CloseIcon from '@mui/icons-material/Close';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import SettingsInputComponentIcon from '@mui/icons-material/SettingsInputComponent';
```

### File Structure (Changes)

```
web/platform-admin/src/
├── api/
│   ├── index.ts                              # MODIFIED - Export sourceConfigs
│   └── sourceConfigs.ts                      # NEW - API functions
├── types/
│   └── source-config.ts                      # NEW - TypeScript interfaces
├── pages/
│   └── source-configs/
│       ├── index.ts                          # NEW - Page exports
│       ├── SourceConfigList.tsx              # NEW - List page
│       └── components/
│           └── SourceConfigDetailPanel.tsx   # NEW - Detail slide-out
├── app/
│   └── routes.tsx                            # MODIFIED - Add route
├── components/
│   └── Sidebar/
│       └── Sidebar.tsx                       # MODIFIED - Add menu item

tests/
├── unit/web/platform-admin/pages/source-configs/
│   ├── SourceConfigList.test.tsx             # NEW
│   └── SourceConfigDetailPanel.test.tsx      # NEW
├── e2e/scenarios/
│   └── test_14_source_config_ui.py           # NEW (or add to existing)
```

### Previous Story Intelligence (9.11b)

**From Story 9.11b completed 2026-01-25:**
- BFF REST endpoints: `GET /api/admin/source-configs` and `GET /api/admin/source-configs/{source_id}`
- Response format: `{ data: SourceConfigSummary[], pagination: { total_count, page_size, next_page_token } }`
- Detail response: `{ source_id, display_name, ..., config_json: string }`
- E2E tests confirm 5+ source configs exist in seed data
- Filters: `page_size`, `page_token`, `enabled_only`, `ingestion_mode`

**Key learnings from 9.11b:**
- `config_json` is a **string** - must be parsed client-side
- `ingestion_mode` and `ai_agent_id` are extracted from `config_json` in BFF converters
- Empty `ai_agent_id` returns as empty string, convert to null/"-" for display
- Pagination uses `page_token` cursor-based pagination

### Git History Context (Recent Commits)

```
58cb6a2 chore: Mark story 9.11b as done
e06f2e4 Story 9.11b: Source Config gRPC Client + REST API in BFF (#232)
cf0b599 Story 9.11a: SourceConfigService gRPC in Collection Model (#230)
07c3569 Story 9.10b: Platform Cost Dashboard UI (#228)
```

Pattern: Each story creates comprehensive tests before marking complete.

### References

- [Source: _bmad-output/architecture/adr/ADR-019-admin-configuration-visibility.md#Decision-5] - Screen wireframes and implementation notes
- [Source: _bmad-output/epics/epic-9-admin-portal/story-911c-source-config-viewer-ui.md] - Story requirements
- [Source: _bmad-output/epics/epic-9-admin-portal/use-cases.md#UC9.1] - Use case flow
- [Source: web/platform-admin/src/pages/grading-models/GradingModelList.tsx] - List page pattern
- [Source: web/platform-admin/src/api/gradingModels.ts] - API module pattern
- [Source: web/platform-admin/src/components/Sidebar/Sidebar.tsx] - Navigation pattern
- [Source: web/platform-admin/src/app/routes.tsx] - Routing pattern
- [Source: libs/fp-common/fp_common/models/source_config.py] - SourceConfig model reference
- [Source: _bmad-output/sprint-artifacts/9-11b-source-config-bff-client-rest.md] - Previous story learnings
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
