# Story 9.6b: Grading Model Management UI

**Status:** ready-for-dev
**GitHub Issue:** #217

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **platform administrator**,
I want to view grading models and assign them to factories through the Admin Portal UI,
so that I can configure which quality assessment standards each factory uses without needing direct database access.

## Acceptance Criteria

### AC 9.6b.1: Grading Model List View

**Given** I navigate to `/grading-models`
**When** the page loads
**Then** I see a DataTable with all grading models showing:
  - Model ID and version
  - Crops name and market name
  - Grading type (Binary/Ternary/Multi-level) as a Chip
  - Number of factories using this model
  - Number of attributes
**And** I can filter by grading type
**And** I can search by model ID or crops name (client-side filter on visible data)
**And** clicking a row navigates to the detail view

### AC 9.6b.2: Grading Model Detail View (Read-Only)

**Given** I click on a grading model from the list
**When** the detail page loads at `/grading-models/:modelId`
**Then** I see (read-only):
  - Model metadata: model_id, model_version, regulatory_authority
  - Configuration: crops_name, market_name, grading_type
  - Grading attributes table: attribute name, number of classes, class names
  - Grade rules section: reject_conditions displayed as bullet list, conditional_reject as "IF...THEN REJECT" format
  - Grade labels: key-value display
  - Factories using this model: list with factory name and ID
  - Timestamps: created_at, updated_at
**And** I cannot edit the model configuration (managed by farmer-power-training)
**And** there is a "Back" button to return to the list

### AC 9.6b.3: Factory Assignment

**Given** I'm on a grading model detail page
**When** I click "Assign to Factory"
**Then** I see a dialog/modal with a dropdown of all factories
**And** factories already using this model are excluded from the dropdown
**And** I can select a factory and confirm the assignment
**And** on success, the factory list on the detail page updates
**And** on error, I see an appropriate error message (404, 409)

### AC 9.6b.4: Loading and Error States

**Given** any grading model page
**When** data is loading
**Then** I see a CircularProgress spinner
**And** when an error occurs, I see an Alert with the error message
**And** when no models exist, I see an appropriate empty state

## Tasks / Subtasks

- [x] Task 1: Add TypeScript types for grading models (AC: 1, 2, 3)
  - [x] 1.1 Add full GradingModel types to `web/platform-admin/src/api/types.ts` (GradingModelListSummary, GradingModelDetailResponse, GradingAttribute, ConditionalReject, GradeRules, FactoryReference, GradingModelListResponse, GradingModelListParams, AssignGradingModelRequest)
  - [x] 1.2 Add grading type display helper function

- [x] Task 2: Create API module for grading models (AC: 1, 2, 3)
  - [x] 2.1 Create `web/platform-admin/src/api/gradingModels.ts` with functions: `listGradingModels`, `getGradingModel`, `assignGradingModelToFactory`
  - [x] 2.2 Export from `web/platform-admin/src/api/index.ts`

- [x] Task 3: Implement GradingModelList page (AC: 1, 4) — see **Wireframe: Grading Model List**
  - [x] 3.1 Replace placeholder in `web/platform-admin/src/pages/grading-models/GradingModelList.tsx`
  - [x] 3.2 Implement DataTable with columns: Model ID, Version, Crops, Market, Grading Type (Chip), Factories, Attributes
  - [x] 3.3 Add grading type filter using FilterBar
  - [x] 3.4 Add client-side search filtering on model_id and crops_name
  - [x] 3.5 Add row click navigation to detail page
  - [x] 3.6 Add loading/error/empty states

- [x] Task 4: Implement GradingModelDetail page (AC: 2, 4) — see **Wireframe: Grading Model Detail**
  - [x] 4.1 Replace placeholder in `web/platform-admin/src/pages/grading-models/GradingModelDetail.tsx`
  - [x] 4.2 Display model metadata section (Paper with Grid layout)
  - [x] 4.3 Display grading attributes table (Table component)
  - [x] 4.4 Display grade rules section (reject conditions as bullet list, conditional rules as IF...THEN)
  - [x] 4.5 Display grade labels as key-value pairs
  - [x] 4.6 Display factory assignments list with names
  - [x] 4.7 Add "Assign to Factory" button
  - [x] 4.8 Add "Back" navigation button
  - [x] 4.9 Add loading/error states

- [x] Task 5: Implement Factory Assignment Dialog (AC: 3) — triggered by `[+ Assign Factory]` button in **Wireframe: Grading Model Detail**
  - [x] 5.1 Create `AssignFactoryDialog` component within grading-models page folder
  - [x] 5.2 Fetch all factories and exclude already-assigned ones
  - [x] 5.3 Show factory dropdown with search/filter
  - [x] 5.4 Handle assignment via POST `/api/admin/grading-models/{id}/assign`
  - [x] 5.5 Show success/error feedback
  - [x] 5.6 Refresh detail page data on successful assignment

- [x] Task 6: Lint and Build Verification (AC: all)
  - [x] 6.1 Run `npm run lint` and fix any issues
  - [x] 6.2 Run `npm run build` and verify no TypeScript errors (pre-existing `initialExpanded` errors in unrelated files)
  - [x] 6.3 Run `ruff check . && ruff format --check .` for Python linting

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 9.6b: Grading Model Management UI"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/9-6b-grading-model-management-ui
  ```

**Branch name:** `story/9-6b-grading-model-management-ui`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/9-6b-grading-model-management-ui`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 9.6b: Grading Model Management UI" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/9-6b-grading-model-management-ui`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
# Frontend tests (if any vitest tests created)
cd web/platform-admin && npm run test -- --run
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

# Run grading model E2E tests (validates API that UI consumes)
PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/test_36_admin_grading_models.py -v

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
cd web/platform-admin && npm run lint && npm run build
```
**Lint passed:** [ ] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

```bash
# Push to story branch
git push origin story/9-6b-grading-model-management-ui

# Wait ~30s, then check CI status
gh run list --branch story/9-6b-grading-model-management-ui --limit 3
```
**CI Run ID:** _______________
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Wireframes

### Grading Model List

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  📊 GRADING MODELS                                                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Search: [🔍 Search models...                                              ]    │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  MODEL ID        │ TYPE    │ CROPS    │ MARKET │ FACTORIES │ STATUS │     │  │
│  │  ────────────────┼─────────┼──────────┼────────┼───────────┼────────┼──── │  │
│  │  TBK-Binary-v1.0 │ Binary  │ Tea      │ Kenya  │ 12        │ Active │  →  │  │
│  │  TBK-Ternary-v1.0│ Ternary │ Tea      │ Export │  3        │ Active │  →  │  │
│  │  KTDA-Multi-v2.1 │ Multi   │ Tea      │ Kenya  │  5        │ Active │  →  │  │
│  │  Coffee-Binary   │ Binary  │ Coffee   │ Kenya  │  0        │ Draft  │  →  │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  Showing 4 grading models                                                       │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Grading Model Detail

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  📊 Grading Models › TBK-BINARY-V1.0                                 [← Back] │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  MODEL INFORMATION                                                               │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  Model ID: TBK-Binary-v1.0          Version: 1.0                          │  │
│  │  Regulatory Authority: Tea Board of Kenya                                 │  │
│  │  Crops: Tea                          Market: Kenya Domestic               │  │
│  │  Grading Type: Binary (Primary/Secondary)                                 │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  GRADING ATTRIBUTES                                                              │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  ATTRIBUTE         │ CLASSES                                              │  │
│  │  ──────────────────┼────────────────────────────────────────────────────  │  │
│  │  leaf_appearance   │ fine_plucking, coarse_plucking, withered, damaged   │  │
│  │  leaf_maturity     │ two_leaves_bud, three_leaves, mature_leaf           │  │
│  │  foreign_matter    │ none, minimal, moderate, excessive                   │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  GRADE RULES                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  ALWAYS REJECT:                                                           │  │
│  │  • leaf_appearance = damaged                                              │  │
│  │  • foreign_matter = excessive                                             │  │
│  │                                                                           │  │
│  │  CONDITIONAL REJECT:                                                      │  │
│  │  • IF leaf_maturity = mature_leaf AND leaf_appearance = withered → REJECT│  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  GRADE LABELS                                                                    │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  primary   → "Primary Grade" (Premium quality)                            │  │
│  │  secondary → "Secondary Grade" (Standard quality)                         │  │
│  │  reject    → "Rejected" (Below standard)                                  │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                  │
│  FACTORIES USING THIS MODEL                                 [+ Assign Factory]  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  🏭 Nyeri Tea Factory       │ Nyeri Highland    │ Since: 2024-03-15       │  │
│  │  🏭 Karatina Processing     │ Nyeri Highland    │ Since: 2024-04-01       │  │
│  │  🏭 Kericho Central         │ Kericho Highland  │ Since: 2024-03-20       │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  12 factories using this model                                                  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Dev Notes

### CRITICAL: This is a Frontend-Only Story

This story implements the **UI layer only**. The backend (gRPC + BFF endpoints) is already complete from Story 9.6a. You are consuming existing endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `GET /api/admin/grading-models` | GET | List grading models (with filters) |
| `GET /api/admin/grading-models/{model_id}` | GET | Get grading model detail |
| `POST /api/admin/grading-models/{model_id}/assign` | POST | Assign model to factory |

**DO NOT modify any backend code (BFF, Plantation Service, proto files).**

### Existing Code to Extend (NOT Reinvent)

**Placeholder Pages Already Exist (REPLACE these):**
- `web/platform-admin/src/pages/grading-models/GradingModelList.tsx` - Currently a placeholder
- `web/platform-admin/src/pages/grading-models/GradingModelDetail.tsx` - Currently a placeholder

**Routes Already Configured (NO changes needed):**
- `/grading-models` → `GradingModelList`
- `/grading-models/:modelId` → `GradingModelDetail`

**Existing GradingModelSummary in types.ts (line 514) - REPLACE:**
The existing type is a simplified version used by FactoryDetail. You need to create the full types matching the BFF schema response.

**Navigation Already Configured:**
- Sidebar already has "Grading Models" link with GradingIcon

### API Response Shapes (from BFF schemas)

**List Response (`GET /api/admin/grading-models`):**
```json
{
  "data": [
    {
      "model_id": "tbk_kenya_tea_v1",
      "model_version": "2024.1",
      "crops_name": "Tea",
      "market_name": "Kenya_TBK",
      "grading_type": "binary",
      "attribute_count": 3,
      "factory_count": 5
    }
  ],
  "pagination": {
    "total_count": 4,
    "page_size": 50,
    "page": 0,
    "next_page_token": null,
    "has_next": false
  }
}
```

**Detail Response (`GET /api/admin/grading-models/{id}`):**
```json
{
  "model_id": "tbk_kenya_tea_v1",
  "model_version": "2024.1",
  "regulatory_authority": "Tea Board of Kenya",
  "crops_name": "Tea",
  "market_name": "Kenya_TBK",
  "grading_type": "binary",
  "attributes": {
    "leaf_type": {
      "num_classes": 7,
      "classes": ["bud", "one_leaf_bud", "two_leaves_bud", "three_leaves_bud", "three_plus_leaves_bud", "coarse_leaf", "banji"]
    },
    "coarse_subtype": {
      "num_classes": 4,
      "classes": ["none", "double_luck", "single_luck", "no_luck"]
    }
  },
  "grade_rules": {
    "reject_conditions": {
      "leaf_type": ["three_plus_leaves_bud", "coarse_leaf"]
    },
    "conditional_reject": [
      {
        "if_attribute": "leaf_type",
        "if_value": "banji",
        "then_attribute": "banji_hardness",
        "reject_values": ["hard"]
      }
    ]
  },
  "grade_labels": {
    "ACCEPT": "Primary",
    "REJECT": "Secondary"
  },
  "active_at_factories": [
    {"factory_id": "factory-001", "name": "Nyeri Tea Factory"},
    {"factory_id": "factory-002", "name": "Kericho Central"}
  ],
  "created_at": "2024-03-15T10:30:00Z",
  "updated_at": "2024-06-01T14:00:00Z"
}
```

**Assign Request (`POST /api/admin/grading-models/{id}/assign`):**
```json
{ "factory_id": "factory-003" }
```

**Query Parameters for List:**
- `crops_name` (string, optional) - Filter by crop
- `market_name` (string, optional) - Filter by market
- `grading_type` (string, optional) - Filter: "binary", "ternary", "multi_level"
- `page_size` (int, default 50, max 100)
- `page_token` (string, optional)

### UI Patterns to Follow (from existing pages)

**List Page Pattern (follow FactoryList.tsx / FarmerList.tsx):**
```typescript
// 1. State: data, loading, error, paginationModel, filters, searchQuery
// 2. fetchData with useCallback + pagination + filters
// 3. GridColDef[] columns with renderCell for Chips
// 4. Row actions with view icon (navigate to detail)
// 5. PageHeader + FilterBar + DataTable
```

**Detail Page Pattern (follow FactoryDetail.tsx / RegionDetail.tsx):**
```typescript
// 1. useParams for modelId
// 2. fetchData on mount with useCallback
// 3. Loading/error/not-found states
// 4. PageHeader with statusBadge and actions
// 5. Grid layout with Paper/Card sections
// 6. Table for structured data (attributes)
// 7. Typography for labels/values
```

**Dialog Pattern (follow CollectionPointQuickAddModal.tsx):**
```typescript
// 1. Dialog with title and close button
// 2. Form content with select/autocomplete
// 3. DialogActions with Cancel + Confirm buttons
// 4. Loading state on submit
// 5. Error display in dialog
```

### Grading Type Display Mapping

| API Value | Display Label | Chip Color |
|-----------|---------------|------------|
| `binary` | Binary | `default` |
| `ternary` | Ternary | `primary` |
| `multi_level` | Multi-level | `secondary` |

### Component Library Imports

```typescript
// From @fp/ui-components (already available)
import { PageHeader, DataTable, FilterBar, type FilterDef, type FilterValues } from '@fp/ui-components';

// From MUI (already in package.json)
import { Box, Paper, Grid2 as Grid, Typography, Chip, Alert, CircularProgress,
         Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
         Button, Dialog, DialogTitle, DialogContent, DialogActions,
         Select, MenuItem, FormControl, InputLabel } from '@mui/material';

// Icons (already in package.json)
import GradingIcon from '@mui/icons-material/Grading';
import VisibilityIcon from '@mui/icons-material/Visibility';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import AddIcon from '@mui/icons-material/Add';
import FactoryIcon from '@mui/icons-material/Factory';
```

### API Client Pattern

```typescript
// Follow pattern from src/api/factories.ts
import { apiClient } from './client';
import type { GradingModelListResponse, GradingModelDetailResponse, GradingModelListParams } from './types';

export async function listGradingModels(params?: GradingModelListParams): Promise<GradingModelListResponse> {
  const { data } = await apiClient.get<GradingModelListResponse>('/admin/grading-models', params);
  return data;
}

export async function getGradingModel(modelId: string): Promise<GradingModelDetailResponse> {
  const { data } = await apiClient.get<GradingModelDetailResponse>(`/admin/grading-models/${modelId}`);
  return data;
}

export async function assignGradingModelToFactory(modelId: string, factoryId: string): Promise<GradingModelDetailResponse> {
  const { data } = await apiClient.post<GradingModelDetailResponse>(
    `/admin/grading-models/${modelId}/assign`,
    { factory_id: factoryId }
  );
  return data;
}
```

### Previous Story Intelligence (Story 9.6a)

**Key Learnings from 9.6a:**
1. Backend returns `crops_name` and `market_name` (NOT `crop_type` / `market`)
2. GradingType is a string enum: "binary", "ternary", "multi_level"
3. `active_at_factories` contains `FactoryReference` objects with `factory_id` and resolved `name`
4. Pagination follows standard BFF pattern with `PaginationMeta`
5. Assignment returns updated `GradingModelDetail` (with factory list refreshed)
6. 404 for nonexistent model/factory, 409 if already assigned (handled by BFF)

**Files Created by 9.6a (DO NOT modify):**
- `services/bff/src/bff/api/routes/admin/grading_models.py` - REST endpoints
- `services/bff/src/bff/services/admin/grading_model_service.py` - Business logic
- `services/bff/src/bff/api/schemas/admin/grading_model_schemas.py` - Response schemas
- `services/bff/src/bff/transformers/admin/grading_model_transformer.py` - Converters

### File Structure for This Story

**Files to MODIFY:**
- `web/platform-admin/src/api/types.ts` - Add GradingModel types (replace simplified version at line 514)
- `web/platform-admin/src/api/index.ts` - Export new gradingModels module
- `web/platform-admin/src/pages/grading-models/GradingModelList.tsx` - Replace placeholder
- `web/platform-admin/src/pages/grading-models/GradingModelDetail.tsx` - Replace placeholder

**Files to CREATE:**
- `web/platform-admin/src/api/gradingModels.ts` - API functions
- `web/platform-admin/src/pages/grading-models/components/AssignFactoryDialog.tsx` - Assignment modal

**Files NOT to touch (routes already configured in routes.tsx, sidebar already has link):**
- `web/platform-admin/src/app/routes.tsx` - Already has grading-models routes
- `web/platform-admin/src/components/Sidebar/Sidebar.tsx` - Already has menu item

### Technical Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.3 | UI framework |
| TypeScript | 5.x | Type safety |
| MUI | 6.3 | Component library |
| MUI X Data Grid | 7.x | DataTable |
| React Router | 7.1 | Routing |
| Vite | 6.0 | Build tool |
| @fp/ui-components | workspace | Shared components |
| @fp/auth | workspace | Authentication |

### Project Structure Notes

- Path alias: `@/*` → `./src/*` (configured in tsconfig.json)
- Pages follow pattern: `pages/{resource}/ResourceList.tsx`, `ResourceDetail.tsx`
- Sub-components go in `pages/{resource}/components/`
- API modules: one file per resource in `src/api/`
- No React Query - uses useState + useEffect + useCallback pattern

### Accessibility Requirements

- All interactive elements must have 48x48px minimum touch targets
- Chips must have appropriate ARIA labels
- Table must have proper header associations
- Dialog must trap focus and support Escape to close
- Status indicators must not rely on color alone

### References

- [Source: _bmad-output/epics/epic-9-admin-portal/story-96b-grading-model-management-ui.md] - Epic story definition with wireframes
- [Source: _bmad-output/sprint-artifacts/9-6a-grading-model-grpc-bff-api.md] - Backend implementation details
- [Source: services/bff/src/bff/api/schemas/admin/grading_model_schemas.py] - BFF response schemas
- [Source: web/platform-admin/src/pages/factories/FactoryList.tsx] - List page pattern
- [Source: web/platform-admin/src/pages/factories/FactoryDetail.tsx] - Detail page pattern
- [Source: web/platform-admin/src/pages/factories/components/CollectionPointQuickAddModal.tsx] - Dialog pattern
- [Source: web/platform-admin/src/api/factories.ts] - API module pattern
- [Source: web/platform-admin/src/api/types.ts:514] - Existing GradingModelSummary (to replace)
- [Source: web/platform-admin/src/app/routes.tsx] - Routes already configured
- [Source: _bmad-output/project-context.md] - Project rules

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Pre-existing TS errors in CollectionPointQuickAddModal.tsx, FactoryCreate.tsx, FarmerCreate.tsx (`initialExpanded` prop) - not related to this story

### Completion Notes List

- All 6 tasks completed with all subtasks
- TypeScript types match BFF API response schemas exactly
- GradingModelList follows FactoryList.tsx pattern with DataTable, FilterBar, search
- GradingModelDetail displays all model sections (metadata, attributes, rules, labels, factories)
- AssignFactoryDialog follows CollectionPointQuickAddModal.tsx pattern (simpler - select instead of form)
- PageHeader used with onBack for detail page navigation (no breadcrumbs prop available)
- DataTable requires `id` field on rows - mapped model_id to id
- Client-side search on model_id and crops_name as specified in AC 9.6b.1
- Grading type chips with proper color mapping (default/primary/secondary)
- Error/loading/empty states implemented per AC 9.6b.4

### File List

**Created:**
- `web/platform-admin/src/api/gradingModels.ts` - API module with list/get/assign functions
- `web/platform-admin/src/pages/grading-models/components/AssignFactoryDialog.tsx` - Factory assignment dialog

**Modified:**
- `web/platform-admin/src/api/types.ts` - Added GradingModel types (GradingType, GradingModelListSummary, GradingModelDetailResponse, GradingAttribute, ConditionalReject, GradeRules, FactoryReference, GradingModelListResponse, GradingModelListParams, AssignGradingModelRequest, getGradingTypeLabel, getGradingTypeColor)
- `web/platform-admin/src/api/index.ts` - Added gradingModels export
- `web/platform-admin/src/pages/grading-models/GradingModelList.tsx` - Replaced placeholder with full list page implementation
- `web/platform-admin/src/pages/grading-models/GradingModelDetail.tsx` - Replaced placeholder with full detail page implementation
- `_bmad-output/sprint-artifacts/sprint-status.yaml` - Updated story status to in-progress
- `_bmad-output/sprint-artifacts/9-6b-grading-model-management-ui.md` - Story file updates
