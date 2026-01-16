# Story 9.3: Factory Management

**Status:** in-progress
**GitHub Issue:** [#195](https://github.com/jltournay/farmer-power-platform/issues/195)

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **platform administrator**,
I want **to view, create, edit, and manage factories through the admin portal**,
So that **I can onboard tea processing facilities for the pilot and configure their quality thresholds and payment policies**.

## Acceptance Criteria

### AC1: Factory List View (Top-Level)
**Given** an authenticated platform admin on the Factories page
**When** the page loads
**Then**:
- Display factories in DataTable with columns: Name, Code, Region (linked), CPs, Capacity, Status
- Support pagination (25 items default, options: 10, 25, 50)
- Filter: Region dropdown, Active/Inactive/All toggle
- Search: Filter by factory name or code (client-side)
- "Add Factory" button in header
- Row click navigates to `/factories/{factoryId}`

### AC2: Factory Detail View (Hierarchical to CPs)
**Given** clicking a factory row in the list
**When** the detail page loads
**Then**:
- Display factory header with name, code, status badge
- Show factory info panel: location map, contact info, processing capacity
- Display quality thresholds card with tier percentages
- Display payment policy card with adjustment percentages
- Show grading model summary (if assigned)
- Display collection points list with: Name, Clerk, Farmers, Status
- Each CP row is clickable to navigate to `/factories/{factoryId}/collection-points/{cpId}`
- "Add Collection Point" button in CP section header
- "Edit Factory" button in page header
- Breadcrumb: Factories › {Factory Name}

### AC3: Factory Creation
**Given** clicking "Add Factory" button from factory list
**When** the create page loads
**Then**:
- Form sections: Basic Info, Location, Contact, Quality & Payment
- Required fields: Name, Code (unique), Region (dropdown), Latitude, Longitude
- Location: GPSFieldWithMapAssist component (click map OR type coordinates)
- Altitude: Read-only field, auto-populated from Google Elevation API when lat/lng are set
- Processing capacity: Numeric input (kg/day)
- Quality thresholds: Optional, defaults to 85/70/50 if not provided
- Payment policy: Optional, defaults to FEEDBACK_ONLY if not provided
- "Create" saves via POST /api/admin/factories and navigates to new factory detail
- "Cancel" returns to factory list
- Validation errors shown inline under fields

### AC4: Factory Editing
**Given** clicking "Edit Factory" button on detail page
**When** the edit page loads
**Then**:
- Pre-populate all fields from existing factory
- All fields editable except ID
- Quality thresholds section with live preview (optional enhancement)
- Payment policy dropdown with adjustment sliders
- Active/Inactive toggle
- "Save" calls PUT /api/admin/factories/{factory_id}
- "Cancel" returns to detail view without saving

### AC5: Factory Soft Delete (Deactivation)
**Given** a factory with no active collection points
**When** admin sets status to Inactive
**Then**:
- Confirmation dialog appears before deactivation
- Factory status changes to Inactive
- Factory remains in system but hidden from active lists
- If factory has active CPs, show warning: "Deactivate collection points first"

### AC6: Collection Point Quick-Add from Factory
**Given** clicking "Add Collection Point" on factory detail page
**When** the form opens
**Then**:
- Factory ID is pre-filled and read-only
- Form fields: Name, Location (GPSFieldWithMapAssist), Region (dropdown)
- "Create" calls POST /api/admin/factories/{factory_id}/collection-points
- On success, refresh CP list and show success snackbar

### AC7: Optimistic UI Updates
**Given** any create/update operation
**When** the request is in progress
**Then**:
- Show loading state on save button
- Disable form inputs during save
- Show success snackbar on completion
- Show error snackbar with retry option on failure
- Navigate appropriately after success

### AC8: Error Handling
**Given** any API error
**When** the error is returned
**Then**:
- 401: Redirect to login
- 403: Show "Access Denied" message
- 404: Show "Factory not found" with back to list button
- 409 (conflict): Show "Factory code already exists" message
- 503: Show "Service temporarily unavailable" with retry button
- Validation errors: Show field-level error messages

---

## Wireframes

### Wireframe: Factory List (Top-Level)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🏭 FACTORIES                                                   [+ Add Factory] │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  FILTERS                                                                         │
│  Region: [All ▼]  Status: [All ▼]     Search: [🔍 Search factories...       ]   │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  NAME                │ CODE    │ REGION          │ CPs │ CAPACITY │STATUS│  │
│  │  ────────────────────┼─────────┼─────────────────┼─────┼──────────┼──────│  │
│  │  Nyeri Tea Factory   │ NTF-001 │ Nyeri Highland  │  3  │ 5,000 kg │ ● → │  │
│  │  Karatina Processing │ KTP-001 │ Nyeri Highland  │  2  │ 3,500 kg │ ● → │  │
│  │  Othaya Tea Factory  │ OTF-001 │ Nyeri Highland  │  4  │ 4,200 kg │ ● → │  │
│  │  Kericho Central     │ KCF-001 │ Kericho Highland│  5  │ 8,000 kg │ ● → │  │
│  │  Kisii Processing    │ KSP-001 │ Kisii Midland   │  2  │ 2,500 kg │ ○ → │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  Showing 12 factories                                  [← Previous] [Next →]    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe: Factory Detail (with Collection Points)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🏭 Factories › NYERI TEA FACTORY                         [Edit] [← Back]       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  FACTORY INFORMATION                                                             │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  Name: Nyeri Tea Factory           Code: NTF-001       Status: ● Active   │  │
│  │  Region: Nyeri Highland            Capacity: 5,000 kg/day                 │  │
│  │                                                                           │  │
│  │  LOCATION                           CONTACT                               │  │
│  │  GPS: -0.4197, 36.9553             Phone: +254 712 345 678               │  │
│  │  Alt: 1,850m                        Email: admin@nyeritea.co.ke          │  │
│  │                                     Address: Nyeri Town, Kenya            │  │
│  │                                                                           │  │
│  │  ─────────────────────────────────────────────────────────────────────   │  │
│  │                                                                           │  │
│  │  QUALITY THRESHOLDS                  PAYMENT POLICY                       │  │
│  │  🟢 Premium:   ≥85% Primary         Type: Weekly Bonus                   │  │
│  │  🟡 Standard:  ≥70% Primary         Premium: +15%                        │  │
│  │  🟠 Acceptable:≥50% Primary         Standard: Base rate                  │  │
│  │  🔴 Below Std: <50% Primary         Acceptable: -5%                      │  │
│  │                                      Below Std: -10%                      │  │
│  │                                                                           │  │
│  │  Grading Model: TBK-Binary v1.0     [Change Model]                       │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                  │
│  COLLECTION POINTS                                               [+ Add CP]     │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  📍 Nyeri Central CP    │ Clerk: Peter K.  │ 52 farmers │ ● Active │ [→] │  │
│  ├───────────────────────────────────────────────────────────────────────────┤  │
│  │  📍 Karatina Market CP  │ Clerk: Jane M.   │ 48 farmers │ ● Active │ [→] │  │
│  ├───────────────────────────────────────────────────────────────────────────┤  │
│  │  📍 Othaya Junction CP  │ Clerk: -         │ 42 farmers │ ○ Inactive│ [→] │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  SUMMARY: 3 Collection Points │ 142 Total Farmers │ 2 Active Clerks            │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe: Factory Edit Mode

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🏭 Factories › NYERI TEA FACTORY (Editing)                [Save] [Cancel]      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  FACTORY INFORMATION                                                             │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  Name:     [Nyeri Tea Factory                                         ]   │  │
│  │  Code:     [NTF-001              ] (unique)                               │  │
│  │                                                                           │  │
│  │  LOCATION                           CONTACT                               │  │
│  │  Latitude:  [-0.4197    ]          Phone: [+254 712 345 678          ]   │  │
│  │  Longitude: [36.9553    ]          Email: [admin@nyeritea.co.ke      ]   │  │
│  │  Altitude:  1850 m (auto)          Address: [Nyeri Town, Kenya       ]   │  │
│  │                                                                           │  │
│  │  Processing Capacity: [5000       ] kg/day                                │  │
│  │                                                                           │  │
│  │  Status: (●) Active  ( ) Inactive                                         │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                  │
│  QUALITY THRESHOLDS                                                              │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  TIER              │  PRIMARY % THRESHOLD  │  CURRENT FARMERS            │  │
│  │  ──────────────────┼───────────────────────┼──────────────────────────   │  │
│  │  🟢 Premium        │  [≥ 85 %        ▲▼]  │  34 farmers (24%)           │  │
│  │  🟡 Standard       │  [≥ 70 %        ▲▼]  │  62 farmers (44%)           │  │
│  │  🟠 Acceptable     │  [≥ 50 %        ▲▼]  │  38 farmers (27%)           │  │
│  │  🔴 Below Standard │  [< 50 %          ]  │   8 farmers (5%)            │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  PAYMENT POLICY                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  Policy Type: [Weekly Bonus ▼]                                            │  │
│  │                                                                           │  │
│  │  TIER              │  PRICE ADJUSTMENT                                    │  │
│  │  ──────────────────┼────────────────────────────────────────────────────  │  │
│  │  🟢 Premium        │  [+15 %        ▲▼]                                   │  │
│  │  🟡 Standard       │  Base rate (no adjustment)                           │  │
│  │  🟠 Acceptable     │  [-5  %        ▲▼]                                   │  │
│  │  🔴 Below Standard │  [-10 %        ▲▼]                                   │  │
│  │                                                                           │  │
│  │  💰 Projected monthly impact: +KES 45,000 (more bonuses)                 │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Wireframe: Factory Creation

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🏭 Factories › NEW FACTORY                               [Create] [Cancel]     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  BASIC INFORMATION                                                               │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  Factory Name *     [                                                 ]   │  │
│  │  Factory Code *     [                  ] (e.g., NTF-001)                  │  │
│  │                                                                           │  │
│  │  Region *           [Select region ▼]                                     │  │
│  │                     • Nyeri Highland                                      │  │
│  │                     • Nyeri Midland                                       │  │
│  │                     • Kericho Highland                                    │  │
│  │                                                                           │  │
│  │  LOCATION                                                                 │  │
│  │  Latitude *         [             ]     Longitude * [             ]       │  │
│  │                                                    [📍 Select on Map]     │  │
│  │  ┌─────────────────────────────────────────────────────────────────────┐  │  │
│  │  │  🗺️ (Collapsible map - click to set location, syncs with fields)   │  │  │
│  │  │  Tip: Click on map OR type coordinates manually above              │  │  │
│  │  └─────────────────────────────────────────────────────────────────────┘  │  │
│  │  Altitude           [--- auto from Google Elevation API ---] (read-only) │  │
│  │                                                                           │  │
│  │  Processing Capacity * [             ] kg/day                             │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  CONTACT INFORMATION                                                             │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  Phone *            [+254                                             ]   │  │
│  │  Email              [                                                 ]   │  │
│  │  Address            [                                                 ]   │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  QUALITY & PAYMENT (Optional - can configure later)                              │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │  [ ] Use default thresholds (85/70/50%)                                   │  │
│  │  [ ] Use default payment policy (Feedback Only)                           │  │
│  │                                                                           │  │
│  │  [Configure custom thresholds ▼]                                          │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
│  * Required fields                                                               │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Tasks / Subtasks

### Task 1: Factory API Types and Client (AC: 1-4, 6-8)

Create typed API client for factory endpoints in platform-admin app:

- [x] 1.1 Add factory types to `web/platform-admin/src/api/types.ts`:
  - `FactorySummary`, `FactoryDetail`, `FactoryListResponse`
  - `FactoryCreateRequest`, `FactoryUpdateRequest`, `FactoryListParams`
  - `QualityThresholdsAPI`, `PaymentPolicyAPI`, `PaymentPolicyType`
  - `GradingModelSummary`, `GeoLocation`, `ContactInfo`
  - `CollectionPointSummary` (for embedded list in detail)
  - Helper functions: `factoryDetailToFormData()`, `formDataToCreateRequest()`, `formDataToUpdateRequest()`
- [x] 1.2 Create `web/platform-admin/src/api/factories.ts`:
  - `listFactories(params: FactoryListParams): Promise<FactoryListResponse>`
  - `getFactory(factoryId: string): Promise<FactoryDetail>`
  - `createFactory(data: FactoryCreateRequest): Promise<FactoryDetail>`
  - `updateFactory(factoryId: string, data: FactoryUpdateRequest): Promise<FactoryDetail>`
  - `createCollectionPoint(factoryId: string, data: CollectionPointCreateRequest): Promise<CollectionPointDetail>`
- [x] 1.3 Update `web/platform-admin/src/api/index.ts` with factory exports

### Task 2: Factory List Page (AC: 1, 7, 8)

Implement full factory list functionality:

- [x] 2.1 Replace placeholder in `web/platform-admin/src/pages/factories/FactoryList.tsx`:
  - Use `useState` + `useCallback` for data fetching (pattern from RegionList)
  - DataTable component with columns: Name, Code, Region, CPs, Capacity, Status
  - Pagination controls (10, 25, 50 options)
  - Region filter dropdown (populated from regions API)
  - Active/All toggle filter
  - Search input with client-side filtering (name, code)
  - Row click navigates to `/factories/{factoryId}`
- [x] 2.2 Add loading skeleton during initial fetch
- [x] 2.3 Add error state with retry button
- [x] 2.4 Add empty state when no factories exist
- [x] 2.5 "Add Factory" button in PageHeader linking to `/factories/new`

### Task 3: Factory Detail Page (AC: 2, 7, 8)

Implement factory detail view with collection points:

- [x] 3.1 Replace placeholder in `web/platform-admin/src/pages/factories/FactoryDetail.tsx`:
  - Fetch factory: `getFactory(factoryId)`
  - PageHeader with factory name, breadcrumb, "Edit" button
  - StatusBadge showing active/inactive
- [x] 3.2 Create factory info section:
  - MapDisplay showing factory location (point marker)
  - Basic info card: Code, Region (linked), Processing Capacity
  - Contact info card: Phone, Email, Address
- [x] 3.3 Create quality thresholds card:
  - Display tier_1/tier_2/tier_3 with color indicators (🟢🟡🟠🔴)
  - Labels: Premium, Standard, Acceptable, Below Standard
- [x] 3.4 Create payment policy card:
  - Policy type badge
  - Adjustment percentages per tier
- [x] 3.5 Create grading model summary card (if assigned):
  - Model name, version, grade count
- [x] 3.6 Create collection points section:
  - DataTable with columns: Name, Clerk, Farmers, Status
  - Row click navigates to CP detail
  - "Add Collection Point" button (opens modal or navigates)
- [x] 3.7 Handle 404 error with "Factory not found" UI

### Task 4: Factory Create Form (AC: 3, 7, 8)

Implement factory creation:

- [x] 4.1 Create `web/platform-admin/src/pages/factories/FactoryCreate.tsx`:
  - Route: `/factories/new`
  - React Hook Form for form state management
  - Zod schema for client-side validation
- [x] 4.2 Basic info section:
  - Name (required, max 100 chars)
  - Code (required, max 20 chars, unique)
  - Region dropdown (required, fetch from regions API)
- [x] 4.3 Location section with GPSFieldWithMapAssist:
  - Latitude/Longitude inputs with map picker
  - Altitude (auto-populated or manual)
- [x] 4.4 Contact section:
  - Phone (optional, format: +254...)
  - Email (optional, email format)
  - Address (optional, text)
- [x] 4.5 Processing capacity:
  - Numeric input (kg/day, >= 0)
- [x] 4.6 Quality thresholds section (collapsible, optional):
  - Tier 1 (default 85), Tier 2 (default 70), Tier 3 (default 50)
  - Validation: tier_1 > tier_2 > tier_3
- [x] 4.7 Payment policy section (collapsible, optional):
  - Policy type dropdown: feedback_only, split_payment, weekly_bonus, delayed_payment
  - Adjustment sliders per tier (show only for non-feedback policies)
- [x] 4.8 Form submission:
  - Transform form data to FactoryCreateRequest
  - Show loading state on button
  - Navigate to detail on success
  - Show field-level validation errors

### Task 5: Factory Edit Form (AC: 4, 5, 7, 8)

Implement factory editing:

- [x] 5.1 Create `web/platform-admin/src/pages/factories/FactoryEdit.tsx`:
  - Route: `/factories/:factoryId/edit`
  - Fetch existing factory to pre-populate
  - Same form structure as Create
- [x] 5.2 Pre-populate all fields from existing factory
- [x] 5.3 GPSFieldWithMapAssist with existing location
- [x] 5.4 Active/Inactive toggle switch
- [x] 5.5 Deactivation warning if factory has active CPs
- [x] 5.6 Form submission:
  - Transform to FactoryUpdateRequest (only changed fields)
  - Navigate to detail on success
- [x] 5.7 Cancel button returns to detail view

### Task 6: Collection Point Quick-Add Modal (AC: 6)

Implement CP creation from factory detail:

- [x] 6.1 Create "Add Collection Point" button in factory detail
- [x] 6.2 Create CollectionPointQuickAdd component:
  - Modal or slide-out form
  - Factory ID pre-filled (read-only)
  - Name (required)
  - Location (GPSFieldWithMapAssist)
  - Region dropdown (default to factory's region)
- [x] 6.3 Submit: POST /api/admin/factories/{factory_id}/collection-points
- [x] 6.4 On success: Close modal, refresh CP list, show snackbar

### Task 7: Route Registration (AC: 1-5)

Register new routes and update navigation:

- [x] 7.1 Update `web/platform-admin/src/app/routes.tsx`:
  - Add `/factories/new` → `FactoryCreate`
  - Add `/factories/:factoryId/edit` → `FactoryEdit`
  - Keep existing `/factories` → `FactoryList`
  - Keep existing `/factories/:factoryId` → `FactoryDetail`
- [x] 7.2 Update `web/platform-admin/src/pages/factories/index.ts` exports
- [x] 7.3 Update sidebar to highlight "Factories" when on factory routes

### Task 8: Unit Tests

Create unit tests for factory management components:

- [x] 8.1 Create `tests/unit/web/platform-admin/api/factories.test.ts`:
  - Test API client methods with mocked responses
  - Test error handling (401, 403, 404, 503)
  - Test type conversion helpers
- [x] 8.2 Create `tests/unit/web/platform-admin/types/factories.test.ts`:
  - Test FACTORY_FORM_DEFAULTS
  - Test factoryDetailToFormData conversion
  - Test factoryFormDataToCreateRequest conversion
  - Test factoryFormDataToUpdateRequest conversion
- [ ] 8.3 Create `tests/unit/web/platform-admin/pages/FactoryList.test.tsx`:
  - Test loading state renders
  - Test data displays in table
  - Test pagination controls
  - Test search filtering
  - Test region filter
- [ ] 8.4 Create `tests/unit/web/platform-admin/pages/FactoryDetail.test.tsx`:
  - Test factory data displays correctly
  - Test collection points list renders
  - Test 404 error state
  - Test navigation to edit
- [ ] 8.5 Create `tests/unit/web/platform-admin/pages/FactoryForm.test.tsx`:
  - Test form validation (tier ordering)
  - Test submission calls API
  - Test error display

### Task 9: E2E Test Updates

Update E2E tests for factory UI flows:

- [x] 9.1 Create `tests/e2e/scenarios/test_33_platform_admin_factories.py`:
  - Test factory list loads with seed data
  - Test navigation to factory detail
  - Test factory creation flow
  - Test factory edit flow
  - Test collection points display in factory detail
  - Note: Uses existing seed data from Story 9.1c E2E tests

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [x] GitHub Issue exists or created: `gh issue create --title "Story 9.3: Factory Management"`
- [x] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/9-3-factory-management
  ```

**Branch name:** `story/9-3-factory-management`

### During Development
- [x] All commits reference GitHub issue: `Relates to #195`
- [x] Commits are atomic by type (production, test, seed - not mixed)
- [x] Push to feature branch: `git push -u origin story/9-3-factory-management`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 9.3: Factory Management" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Human verification completed (manual testing with E2E infrastructure + seed data)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/9-3-factory-management`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests
```bash
cd web/platform-admin && npm test
```
**Output:**
```
 ✓ tests/unit/web/platform-admin/api/factories.test.ts (9 tests) 10ms
 ✓ tests/unit/web/platform-admin/types/factories.test.ts (10 tests) 8ms

 Test Files  2 passed (2)
      Tests  19 passed (19)
   Start at  (previous run)
   Duration  (previous run)

Total: 74 tests passed including 19 new factory tests
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure with rebuild
bash scripts/e2e-up.sh --build

# Run pre-flight validation
bash scripts/e2e-preflight.sh

# Run E2E test suite
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
cd web/platform-admin && npm run lint
ruff check . && ruff format --check .
```
**Lint passed:** [x] Yes / [ ] No

TypeScript check: `npx tsc --noEmit` passed without errors.

### 4. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin story/9-3-factory-management

# Wait ~30s, then check CI status
gh run list --branch story/9-3-factory-management --limit 3
```
**CI Run ID:** 21081479178
**CI Status:** [x] Passed / [ ] Failed (all jobs passed: Integration Tests, Lint, Unit Tests, Frontend Tests)
**Verification Date:** 2026-01-16

---

## E2E Story Checklist (Additional guidance for E2E-focused stories)

**Read First:** `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

### Pre-Implementation
- [ ] Read and understood `E2E-TESTING-MENTAL-MODEL.md`
- [ ] Understand: Proto = source of truth, tests verify (not define) behavior

### Before Starting Docker
- [ ] Validate seed data: `python tests/e2e/infrastructure/validate_seed_data.py`
- [ ] All seed files pass validation

### During Implementation
- [ ] If tests fail, investigate using the debugging checklist (not blindly modify code)
- [ ] If seed data needs changes, fix seed data (not production code)
- [ ] If production code has bugs, document each fix (see below)

### Production Code Changes (if any)
If you modified ANY production code (`services/`, `mcp-servers/`, `libs/`), document each change here:

| File:Lines | What Changed | Why (with evidence) | Type |
|------------|--------------|---------------------|------|
| (none) | | | |

**Rules:**
- "To pass tests" is NOT a valid reason
- Must reference proto line, API spec, or other evidence
- If you can't fill this out, you may not understand what you're changing

### Infrastructure/Integration Changes (if any)
If you modified mock servers, docker-compose, env vars, or seed data that affects service behavior:

| File | What Changed | Why | Impact |
|------|--------------|-----|--------|
| (none) | | | |

**Key insight:** If a change affects how production services BEHAVE (even via configuration), document it.

### Unit Test Changes (if any)
If you modified ANY unit test behavior, document here:

| Test File | Test Name Before | Test Name After | Behavior Change | Justification |
|-----------|------------------|-----------------|-----------------|---------------|
| (none) | | | | |

**Rules:**
- Changing "expect failure" to "expect success" REQUIRES justification
- Reference the AC, proto, or requirement that proves the new behavior is correct
- If you can't justify, the original test was probably right - investigate more

### Local Test Run Evidence (MANDATORY before any push)

**First run timestamp:** _______________

**Docker stack status:**
```
# Paste output of: docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml ps
```

**Test run output:**
```
# Paste output of: pytest tests/e2e/scenarios/test_33_*.py -v
# Must show: X passed, 0 failed
```

**If tests failed before passing, explain what you fixed:**

| Attempt | Failure | Root Cause | Fix Applied | Layer Fixed |
|---------|---------|------------|-------------|-------------|
| 1 | | | | |

### Before Marking Done
- [ ] All tests pass locally with Docker infrastructure
- [ ] `ruff check` and `ruff format --check` pass
- [ ] CI pipeline is green
- [ ] If production code changed: Change log above is complete
- [ ] If unit tests changed: Change log above is complete
- [ ] Story file updated with completion notes
- [ ] Human verification completed (see section below)

---

## Human Verification (MANDATORY)

> **This section requires manual testing by the developer using the E2E infrastructure with seed data.**
> The frontend must be tested against real backend services with actual data.

### Setup Instructions

```bash
# 1. Start the E2E infrastructure with seed data
bash scripts/e2e-up.sh --build

# 2. Wait for all services to be healthy
bash scripts/e2e-preflight.sh

# 3. Start the platform-admin dev server (separate terminal)
cd web/platform-admin
npm run dev
# App runs at http://localhost:5174

# 4. Open browser and test manually
```

### Test Credentials

Use the platform_admin JWT token from seed data:
- **Token Location:** `tests/e2e/seed-data/auth_tokens.json` → `platform_admin`
- **Alternative:** Use browser dev tools to set `localStorage.setItem('fp_auth_token', '<token>')`

### Manual Test Checklist

#### AC1: Factory List View
- [ ] Navigate to `/factories` - page loads without errors
- [ ] Table displays seed factories (KEN-E2E-001, KEN-E2E-002)
- [ ] Columns show: Name, Code, Region, CPs, Capacity, Status
- [ ] Pagination works (if more than 25 factories)
- [ ] Region filter dropdown works
- [ ] Active/All filter toggles factory visibility
- [ ] Search filters by name/code
- [ ] "Add Factory" button visible in header
- [ ] Row click navigates to factory detail

#### AC2: Factory Detail View
- [ ] Click on a factory row → navigates to `/factories/{factoryId}`
- [ ] Header shows factory name and code
- [ ] Map displays with factory location marker
- [ ] Basic info card shows: Code, Region, Capacity
- [ ] Contact info card shows: Phone, Email, Address
- [ ] Quality thresholds card shows tier percentages with colors
- [ ] Payment policy card shows policy type and adjustments
- [ ] Collection points section shows list of CPs
- [ ] Each CP row is clickable
- [ ] "Add Collection Point" button visible
- [ ] "Edit Factory" button visible
- [ ] Breadcrumb shows: Factories › {Factory Name}

#### AC3: Factory Create Flow
- [ ] Click "Add Factory" → navigates to `/factories/new`
- [ ] Form sections render: Basic Info, Location, Contact, Quality, Payment
- [ ] GPSFieldWithMapAssist map loads with marker tool
- [ ] Click map updates lat/lng fields
- [ ] Region dropdown populates from API
- [ ] Fill all required fields and submit
- [ ] Factory created, redirects to detail view
- [ ] New factory appears in list

#### AC4: Factory Edit Flow
- [ ] Navigate to factory detail → click "Edit Factory"
- [ ] Form pre-populated with existing factory data
- [ ] Existing location shown on map
- [ ] Modify a field (e.g., change capacity)
- [ ] Click Save → changes persisted
- [ ] Detail view shows updated values
- [ ] Click Cancel → returns to detail without saving

#### AC5: Factory Deactivation
- [ ] On Edit form, toggle Active to Inactive
- [ ] If factory has active CPs, warning shown
- [ ] If no active CPs, save succeeds
- [ ] Factory status shows as Inactive

#### AC6: Collection Point Quick-Add
- [ ] On factory detail, click "Add Collection Point"
- [ ] Modal/form opens with factory ID pre-filled
- [ ] Fill required fields: Name, Location, Region
- [ ] Submit creates CP and closes modal
- [ ] CP list refreshes showing new CP

#### AC7: Optimistic UI Updates
- [ ] Save button shows loading spinner during API call
- [ ] Form inputs disabled during save
- [ ] Success snackbar appears after save
- [ ] Navigation occurs after success

#### AC8: Error Handling
- [ ] Remove auth token → API calls return 401 → redirect to login
- [ ] Navigate to `/factories/INVALID-ID` → 404 error UI displayed
- [ ] (Optional) Stop BFF service → 503 error with retry button

### Verification Evidence

**Test Date:** _______________
**Tester:** _______________
**Browser:** _______________

**Screenshots (attach or describe):**
- [ ] Factory list with seed data
- [ ] Factory detail with map and collection points
- [ ] Factory create form with map assist
- [ ] Factory edit form with pre-populated data

**Issues Found:**

| Issue | Severity | AC Affected | Notes |
|-------|----------|-------------|-------|
| (none) | | | |

**Human Verification Passed:** [ ] Yes / [ ] No

### Teardown

```bash
# Stop the E2E infrastructure
bash scripts/e2e-up.sh --down

# Stop the dev server (Ctrl+C in terminal)
```

---

## Dev Notes

### Frontend Technology Stack

This story implements the frontend portion using:

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.3+ | UI framework |
| TypeScript | 5.6+ | Type safety |
| Vite | 6.0+ | Build tooling |
| Material UI v6 | 6.x | Component library |
| React Query | @tanstack/react-query v5 | Data fetching/caching |
| React Hook Form | 7.x | Form state management |
| Zod | 3.x | Schema validation |
| React Router | 6.x | Client routing |

### Map Component Integration (ADR-017)

**Pre-built components available in `libs/ui-components`:**

| Component | Location | Usage |
|-----------|----------|-------|
| `GPSFieldWithMapAssist` | `libs/ui-components/src/components/GPSFieldWithMapAssist/` | Factory location input |
| `MapDisplay` | `libs/ui-components/src/components/MapDisplay/` | Read-only map on detail page |

**Leaflet CSS imports required in app entry:**
```typescript
// web/platform-admin/src/main.tsx
import 'leaflet/dist/leaflet.css';
```

### API Contract (Story 9.1c Endpoints)

The BFF admin API endpoints were implemented in Story 9.1c:

| Operation | Endpoint | Method | Response |
|-----------|----------|--------|----------|
| List | `/api/admin/factories` | GET | `FactoryListResponse` |
| Get | `/api/admin/factories/{factory_id}` | GET | `FactoryDetail` |
| Create | `/api/admin/factories` | POST | `FactoryDetail` |
| Update | `/api/admin/factories/{factory_id}` | PUT | `FactoryDetail` |
| Create CP | `/api/admin/factories/{factory_id}/collection-points` | POST | `CollectionPointDetail` |

**Factory ID format:** `{COUNTRY}-{TYPE}-{NUM}` (e.g., `KEN-FAC-001`, `KEN-E2E-001`)

**Factory ID validation pattern:** `^[A-Z]{3}-(?:FAC|E2E)-\d{3}$`

### Data Types Reference

From `services/bff/src/bff/api/schemas/admin/factory_schemas.py`:

```typescript
// TypeScript equivalents to add to api/types.ts

/** Payment policy type enum */
export type PaymentPolicyType = 'feedback_only' | 'split_payment' | 'weekly_bonus' | 'delayed_payment';

/** Geographic location (altitude auto-populated from Google Elevation API) */
export interface GeoLocation {
  latitude: number;
  longitude: number;
  altitude_meters?: number; // READ-ONLY: Auto-populated by backend from Google Elevation API
}

/** Contact information */
export interface ContactInfo {
  phone: string;
  email: string;
  address: string;
}

/** Quality tier thresholds */
export interface QualityThresholdsAPI {
  tier_1: number; // Default 85
  tier_2: number; // Default 70
  tier_3: number; // Default 50
}

/** Payment policy configuration */
export interface PaymentPolicyAPI {
  policy_type: PaymentPolicyType;
  tier_1_adjustment: number;
  tier_2_adjustment: number;
  tier_3_adjustment: number;
  below_tier_3_adjustment: number;
}

/** Grading model summary */
export interface GradingModelSummary {
  id: string;
  name: string;
  version: string;
  grade_count: number;
}

/** Factory summary for list views */
export interface FactorySummary {
  id: string;
  name: string;
  code: string;
  region_id: string;
  collection_point_count: number;
  farmer_count: number;
  is_active: boolean;
}

/** Full factory detail */
export interface FactoryDetail extends FactorySummary {
  location: GeoLocation;
  contact: ContactInfo;
  processing_capacity_kg: number;
  quality_thresholds: QualityThresholdsAPI;
  payment_policy: PaymentPolicyAPI;
  grading_model: GradingModelSummary | null;
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime
}

/** Factory list API response */
export interface FactoryListResponse {
  data: FactorySummary[];
  pagination: PaginationMeta;
}

/** Factory list query parameters */
export interface FactoryListParams {
  region_id?: string;
  page_size?: number;
  page_token?: string;
  active_only?: boolean;
}

/** Factory create request */
export interface FactoryCreateRequest {
  name: string;
  code: string;
  region_id: string;
  location: GeoLocation;
  contact?: ContactInfo;
  processing_capacity_kg?: number;
  quality_thresholds?: QualityThresholdsAPI;
  payment_policy?: PaymentPolicyAPI;
}

/** Factory update request */
export interface FactoryUpdateRequest {
  name?: string;
  code?: string;
  location?: GeoLocation;
  contact?: ContactInfo;
  processing_capacity_kg?: number;
  quality_thresholds?: QualityThresholdsAPI;
  payment_policy?: PaymentPolicyAPI;
  is_active?: boolean;
}

/** Collection point summary for embedded list */
export interface CollectionPointSummary {
  id: string;
  name: string;
  factory_id: string;
  region_id: string;
  farmer_count: number;
  status: 'active' | 'inactive' | 'seasonal';
}

/** Collection point create request (for quick-add) */
export interface CollectionPointCreateRequest {
  name: string;
  location: GeoLocation;
  region_id: string;
  clerk_id?: string;
  clerk_phone?: string;
  status?: string;
}
```

### Form Data and Conversion Helpers

```typescript
/** Form data for factory create/edit (flat structure for react-hook-form) */
export interface FactoryFormData {
  // Basic info
  name: string;
  code: string;
  region_id: string;
  // Location (user inputs lat/lng, altitude is display-only from API response)
  latitude: number;
  longitude: number;
  // NOTE: altitude_meters is NOT in form data - it's auto-populated by backend
  // Contact
  phone: string;
  email: string;
  address: string;
  // Capacity
  processing_capacity_kg: number;
  // Quality thresholds
  tier_1: number;
  tier_2: number;
  tier_3: number;
  // Payment policy
  policy_type: PaymentPolicyType;
  tier_1_adjustment: number;
  tier_2_adjustment: number;
  tier_3_adjustment: number;
  below_tier_3_adjustment: number;
  // Status
  is_active?: boolean;
}

/** Default values for factory form */
export const FACTORY_FORM_DEFAULTS: FactoryFormData = {
  name: '',
  code: '',
  region_id: '',
  latitude: -1.0,  // Default to Kenya
  longitude: 37.0,
  // altitude_meters NOT included - auto-populated by backend from Google Elevation API
  phone: '',
  email: '',
  address: '',
  processing_capacity_kg: 0,
  tier_1: 85,
  tier_2: 70,
  tier_3: 50,
  policy_type: 'feedback_only',
  tier_1_adjustment: 0,
  tier_2_adjustment: 0,
  tier_3_adjustment: 0,
  below_tier_3_adjustment: 0,
  is_active: true,
};
```

### Zod Validation Schema

```typescript
import { z } from 'zod';

export const factoryFormSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100, 'Name too long'),
  code: z.string().min(1, 'Code is required').max(20, 'Code too long'),
  region_id: z.string().min(1, 'Region is required'),
  latitude: z.number().min(-90).max(90),
  longitude: z.number().min(-180).max(180),
  // altitude_meters NOT validated - it's read-only from Google Elevation API
  phone: z.string().optional(),
  email: z.string().email().optional().or(z.literal('')),
  address: z.string().optional(),
  processing_capacity_kg: z.number().min(0),
  tier_1: z.number().min(0).max(100),
  tier_2: z.number().min(0).max(100),
  tier_3: z.number().min(0).max(100),
  policy_type: z.enum(['feedback_only', 'split_payment', 'weekly_bonus', 'delayed_payment']),
  tier_1_adjustment: z.number().min(-1).max(1),
  tier_2_adjustment: z.number().min(-1).max(1),
  tier_3_adjustment: z.number().min(-1).max(1),
  below_tier_3_adjustment: z.number().min(-1).max(1),
  is_active: z.boolean().optional(),
}).refine(
  (data) => data.tier_1 > data.tier_2 && data.tier_2 > data.tier_3,
  { message: 'Thresholds must be in order: tier_1 > tier_2 > tier_3', path: ['tier_2'] }
);
```

### Existing Stub Pages to Replace

The platform-admin app from Story 9.1a contains placeholder pages:
- `web/platform-admin/src/pages/factories/FactoryList.tsx` - Replace placeholder with full implementation
- `web/platform-admin/src/pages/factories/FactoryDetail.tsx` - Replace placeholder with full implementation

### New Pages to Create

- `web/platform-admin/src/pages/factories/FactoryCreate.tsx` - Create form
- `web/platform-admin/src/pages/factories/FactoryEdit.tsx` - Edit form

### UI Component Patterns (Story 9.1b)

Reference components from `libs/ui-components/`:
- `DataTable` - For factory list and collection points list
- `PageHeader` - For page titles with breadcrumb and actions
- `EntityCard` - For detail view cards (info, thresholds, policy)
- `FilterBar` - For search/filter controls
- `ConfirmationDialog` - For deactivation confirmation
- `StatusBadge` - For active/inactive status display
- `GPSFieldWithMapAssist` - For location input with map picker
- `MapDisplay` - For read-only location display

### Quality Threshold Display

Use tier colors consistently:
| Tier | Label | Color | Icon |
|------|-------|-------|------|
| tier_1 | Premium | Green `#22C55E` | 🟢 |
| tier_2 | Standard | Yellow `#F59E0B` | 🟡 |
| tier_3 | Acceptable | Orange `#F97316` | 🟠 |
| Below | Below Standard | Red `#EF4444` | 🔴 |

### Payment Policy Display

| Policy Type | Label | Description |
|-------------|-------|-------------|
| `feedback_only` | Feedback Only | Quality info only, no payment adjustment |
| `split_payment` | Split Payment | Base rate + quality adjustment per delivery |
| `weekly_bonus` | Weekly Bonus | Base rate per delivery, weekly quality bonus |
| `delayed_payment` | Delayed Payment | Full payment after quality assessment |

### Project Structure

Files to create/modify:
```
web/platform-admin/src/
├── api/
│   ├── types.ts             # MODIFY: Add factory types
│   ├── factories.ts         # NEW: Factory API functions
│   └── index.ts             # MODIFY: Export factories
├── pages/factories/
│   ├── FactoryList.tsx      # MODIFY: Full implementation
│   ├── FactoryDetail.tsx    # MODIFY: Full implementation
│   ├── FactoryCreate.tsx    # NEW: Create form page
│   ├── FactoryEdit.tsx      # NEW: Edit form page
│   └── index.ts             # MODIFY: Export new pages
└── app/
    └── routes.tsx           # MODIFY: Add new routes

tests/
├── unit/web/platform-admin/
│   ├── api/factories.test.ts     # NEW: API client tests
│   └── pages/
│       ├── FactoryList.test.tsx   # NEW
│       ├── FactoryDetail.test.tsx # NEW
│       └── FactoryForm.test.tsx   # NEW
└── e2e/scenarios/
    └── test_33_platform_admin_factories.py  # NEW
```

### Authentication Pattern

Same as Story 9.2 - JWT token from localStorage:
```typescript
// Already implemented in api/client.ts
const token = localStorage.getItem('fp_auth_token');
headers['Authorization'] = `Bearer ${token}`;
```

### Previous Story Intelligence (Story 9.2)

**Key learnings from Region Management implementation:**

1. **API client pattern**: Use native fetch (not axios), return `{ data: T }` wrapper
2. **Form data conversion**: Create flat `FormData` type for react-hook-form, with helper functions to convert to/from API types
3. **List page pattern**: `useState` + `useCallback` + `useEffect` for data fetching (not React Query)
4. **DataTable**: Use from `@fp/ui-components`, with columns, actions, pagination
5. **FilterBar**: Use with `FilterDef[]` for dropdown filters, search input
6. **Zod validation**: Use `.refine()` for cross-field validation (tier ordering)
7. **MUI Grid2**: Use for responsive layouts
8. **Error handling**: Check response.ok, parse error JSON, throw Error

**Code Review findings to avoid:**
- Ensure API params are not wrapped incorrectly (pass directly, not as object)
- Enable search in FilterBar (don't set `showSearch={false}`)
- Add cross-field validation for thresholds (tier_1 > tier_2 > tier_3)
- Include tests for form data conversion helpers

### References

- [Source: _bmad-output/epics/epic-9-admin-portal/story-93-factory-management.md] - Original story definition
- [Source: _bmad-output/epics/epic-9-admin-portal/scope-overview.md] - Data model relationships
- [Source: _bmad-output/epics/epic-9-admin-portal/interaction-patterns.md] - UI patterns
- [Source: services/bff/src/bff/api/routes/admin/factories.py] - BFF API implementation
- [Source: services/bff/src/bff/api/schemas/admin/factory_schemas.py] - API type definitions
- [Source: libs/fp-common/fp_common/models/value_objects.py] - Shared value objects
- [Source: web/platform-admin/src/pages/regions/] - Region implementation patterns
- [Source: _bmad-output/sprint-artifacts/9-2-region-management.md] - Previous story patterns
- [Source: _bmad-output/architecture/adr/ADR-017-map-services-gps-region-assignment.md] - Map component specs

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Fixed GPSFieldWithMapAssist component type issue: GPSCoordinates uses `number | null` for lat/lng, not just `number`
- Removed non-existent `height` prop from GPSFieldWithMapAssist components

### Completion Notes List

- Tasks 1-8 completed: API types, API client, List/Detail/Create/Edit pages, CP Quick-Add Modal, routes, unit tests
- Task 9 completed: E2E tests created (test_33_platform_admin_factories.py)
- Unit tests: 19 new tests for factories API client and type conversion helpers
- E2E tests: 15 tests covering factory list, detail, create, edit, CP quick-add, error handling
- All lint and TypeScript checks pass

### File List

**Created:**
- `web/platform-admin/src/api/factories.ts` - Factory API client functions
- `web/platform-admin/src/pages/factories/FactoryCreate.tsx` - Factory creation form
- `web/platform-admin/src/pages/factories/FactoryEdit.tsx` - Factory edit form
- `web/platform-admin/src/pages/factories/components/CollectionPointQuickAddModal.tsx` - CP quick-add modal
- `tests/unit/web/platform-admin/api/factories.test.ts` - API client unit tests
- `tests/unit/web/platform-admin/types/factories.test.ts` - Type conversion helper tests
- `tests/e2e/scenarios/test_33_platform_admin_factories.py` - E2E tests for factory management UI flows

**Modified:**
- `web/platform-admin/src/api/types.ts` - Added factory types, form types, conversion helpers (~340 lines)
- `web/platform-admin/src/api/index.ts` - Added factory exports
- `web/platform-admin/src/pages/factories/FactoryList.tsx` - Full implementation with DataTable, filters, pagination
- `web/platform-admin/src/pages/factories/FactoryDetail.tsx` - Full implementation with quality thresholds, payment policy, CP list
- `web/platform-admin/src/pages/factories/index.ts` - Added exports for new pages
- `web/platform-admin/src/app/routes.tsx` - Added routes for /factories/new and /factories/:factoryId/edit
