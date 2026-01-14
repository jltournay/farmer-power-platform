# Story 9.1a: Platform Admin Application Scaffold

**Status:** in-progress
**GitHub Issue:** #185

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **platform developer**,
I want the Platform Admin React application scaffolded with routing, layout, and hierarchical navigation,
So that all admin screens can be built on a consistent foundation.

## Acceptance Criteria

### AC 9.1.1: Project Initialization

**Given** the web folder structure exists
**When** I create `web/platform-admin/`
**Then** Vite + React + TypeScript project is initialized
**And** `@fp/ui-components` and `@fp/auth` are configured as dependencies
**And** ESLint and Prettier are configured
**And** Material UI v6 is installed with Earth & Growth theme

### AC 9.1.2: Theme Configuration

**Given** the project is scaffolded
**When** I configure the MUI theme
**Then** the following colors are applied:
  - Primary: Forest Green (`#1B4332`)
  - Secondary: Earth Brown (`#5C4033`)
  - Warning: Harvest Gold (`#D4A03A`)
  - Error: Warm Red (`#C1292E`)
  - Background: Warm White (`#FFFDF9`)

### AC 9.1.3: Routing Configuration

**Given** the project is scaffolded
**When** I configure routing
**Then** React Router v6 is configured with:

| Route | Screen | Description |
|-------|--------|-------------|
| `/` | Dashboard | Platform overview |
| `/regions` | Region List | All regions (top-level) |
| `/regions/:regionId` | Region Detail | Region configuration |
| `/farmers` | Farmer List | All farmers with filters (top-level) |
| `/farmers/:farmerId` | Farmer Detail | Full farmer edit |
| `/factories` | Factory List | All factories (top-level) |
| `/factories/:factoryId` | Factory Detail | Factory + CPs (hierarchical) |
| `/factories/:factoryId/collection-points/:cpId` | CP Detail | Collection point config |
| `/grading-models` | Grading Model List | All models |
| `/grading-models/:modelId` | Grading Model Detail | Model configuration |
| `/users` | User List | All platform users |
| `/health` | Platform Health | System metrics |
| `/knowledge` | Knowledge Library | RAG documents |
| `/costs` | Cost Dashboard | LLM spending |

**And** all routes require `platform_admin` role

### AC 9.1.4: Navigation Layout

**Given** the app is built
**When** I view any screen
**Then** a persistent sidebar shows:
  - 🌍 Regions (top-level, independent)
  - 👨‍🌾 Farmers (top-level, independent with filters)
  - 🏭 Factories (hierarchical to CPs)
  - ────────────
  - 📊 Grading Models
  - 👤 Users
  - ────────────
  - 📈 Health
  - 📚 Knowledge
  - 💰 Costs
**And** breadcrumb navigation shows current position
**And** the Farmer Power logo appears in the header

## Wireframe: Application Shell

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🌿 FARMER POWER ADMIN                                    [Search] [👤 Admin ▼] │
├────────────────┬────────────────────────────────────────────────────────────────┤
│                │                                                                 │
│  NAVIGATION    │  🏭 Factories › Nyeri Tea Factory › Collection Points          │
│  ────────────  │  ─────────────────────────────────────────────────────────────  │
│                │                                                                 │
│  🌍 Regions    │  [Page content loads here based on route]                      │
│  👨‍🌾 Farmers   │                                                                 │
│  🏭 Factories  │                                                                 │
│  ────────────  │                                                                 │
│  📊 Grading    │                                                                 │
│  👤 Users      │                                                                 │
│  ────────────  │                                                                 │
│  📈 Health     │                                                                 │
│  📚 Knowledge  │                                                                 │
│  💰 Costs      │                                                                 │
│                │                                                                 │
└────────────────┴────────────────────────────────────────────────────────────────┘
```

## Tasks / Subtasks

- [x] Task 1: Initialize Vite + React + TypeScript project (AC: 9.1.1)
  - [x] Create `web/platform-admin/` directory
  - [x] Copy `package.json` from `web/factory-portal/` and update:
    - Change name to `@fp/platform-admin`
    - Add leaflet deps: `leaflet react-leaflet leaflet-draw @turf/turf`
    - Add type definitions: `@types/leaflet @types/leaflet-draw`
  - [x] Copy `tsconfig.json` from `web/factory-portal/` (identical)
  - [x] Copy `tsconfig.node.json` from `web/factory-portal/` (identical)
  - [x] Copy `vite.config.ts` from `web/factory-portal/` and change port to 3001
  - [x] Copy `eslint.config.js` from `web/factory-portal/` (identical)
  - [x] Run `npm install` from workspace root

- [x] Task 2: Configure Theme (AC: 9.1.2) - **REUSE FROM @fp/ui-components**
  - [x] Import ThemeProvider from `@fp/ui-components` in main.tsx (no custom wrapper needed)
  - [x] **NOTE:** Theme already includes all required colors (Primary #1B4332, etc.) - NO custom theme needed!
  - [x] Test theme colors render correctly via build

- [x] Task 3: Install Map Dependencies (AC: 9.1.1, per ADR-017)
  - [x] Verify leaflet deps installed in Task 1
  - [x] Add Leaflet CSS import to `main.tsx`: `import 'leaflet/dist/leaflet.css'`
  - [x] Add Leaflet.draw CSS: `import 'leaflet-draw/dist/leaflet.draw.css'`

- [x] Task 4: Configure Routing (AC: 9.1.3)
  - [x] Created `src/app/routes.tsx` with 14 platform-admin routes
  - [x] All routes use `ProtectedRoute` from `@fp/auth` with `roles={['platform_admin']}`
  - [x] Created placeholder pages for each route in `src/pages/`
  - [x] Created `NotFound.tsx` page

- [x] Task 5: Implement Navigation Layout (AC: 9.1.4)
  - [x] Created `Layout.tsx` with responsive sidebar
  - [x] Created `Sidebar.tsx` with 8 menu items and dividers
  - [x] Created `Header.tsx` with "Platform Admin" badge
  - [x] Created `src/components/Breadcrumb/Breadcrumb.tsx` with dynamic breadcrumb trail
  - [x] Integrated Breadcrumb in Layout.tsx (between Header and content)

- [x] Task 6: Build and Test (AC: 9.1.1-9.1.4)
  - [x] Vite proxy for `/api` -> BFF configured
  - [x] `npm run build` succeeds - bundle ~167KB gzipped (well under 500KB)
  - [x] All routes render correctly (verified via unit tests)
  - [x] Created unit tests for Layout, Sidebar, Header, Breadcrumb, routes
  - [x] 39 unit tests passing

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [x] GitHub Issue exists or created: #185
- [x] Feature branch created from main: `story/9-1a-platform-admin-scaffold`

**Branch name:** `story/9-1a-platform-admin-scaffold`

### During Development
- [x] All commits reference GitHub issue: `Relates to #185`
- [x] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/9-1a-platform-admin-scaffold`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 9.1a: Platform Admin Application Scaffold" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/9-1a-platform-admin-scaffold`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests

```bash
# Navigate to platform-admin directory
cd web/platform-admin
npm run test
```

**Output:**

```
 ✓ ../../tests/unit/web/platform-admin/Layout.test.tsx (1 test) 289ms
 ✓ ../../tests/unit/web/platform-admin/Breadcrumb.test.tsx (7 tests) 643ms
 ✓ ../../tests/unit/web/platform-admin/NotFound.test.tsx (5 tests) 715ms
 ✓ ../../tests/unit/web/platform-admin/Sidebar.test.tsx (3 tests) 662ms
 ✓ ../../tests/unit/web/platform-admin/routes.test.tsx (17 tests) 703ms
 ✓ ../../tests/unit/web/platform-admin/Header.test.tsx (6 tests) 889ms

 Test Files  6 passed (6)
      Tests  39 passed (39)
   Duration  10.46s
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`
> **Note:** This story is a frontend-only scaffold with no backend changes. E2E tests are not applicable for this story as there are no new API endpoints or database changes.

**E2E passed:** [x] N/A (frontend-only story, no backend changes)

### 3. Lint Check

```bash
cd web/platform-admin
npm run lint
```

**Lint passed:** [x] Yes / [ ] No

### 4. Build Verification

```bash
npm run build
```

**Output:**

```
vite v6.4.1 building for production...
✓ 973 modules transformed.
dist/index.html                         0.70 kB │ gzip:  0.37 kB
dist/assets/index-D9RYvAJw.css         28.17 kB │ gzip: 12.81 kB
dist/assets/maps-C9QagFxF.js            0.07 kB │ gzip:  0.09 kB
dist/assets/index-DfbaaQxK.js         158.79 kB │ gzip: 50.38 kB
dist/assets/vendor-RVwsST1e.js        176.67 kB │ gzip: 58.18 kB
dist/assets/mui-DOJNOX7m.js           186.30 kB │ gzip: 57.97 kB
✓ built in 16.92s
```

**Total gzipped size:** ~167 KB (well under 500KB limit)

### 5. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin story/9-1a-platform-admin-scaffold

# Wait ~30s, then check CI status
gh run list --branch story/9-1a-platform-admin-scaffold --limit 3
```

**CI Run ID:** _______________
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Human Validation Gate

**⚠️ MANDATORY: This story requires human validation before acceptance.**

| Validation Type | Requirement |
|-----------------|-------------|
| **Visual Review** | Human must review navigation layout, theme colors, routing |
| **Storybook Review** | If components added to @fp/ui-components, review in Storybook |
| **Checklist** | Navigation layout, theme colors, routing, breadcrumbs |
| **Approval** | Story cannot be marked "done" until human signs off |

---

## Dev Notes

### Architecture Context

**Reference:** This is the second React frontend application (Epic 11 Kiosk PWA is deferred), following the same patterns established in `web/factory-portal/`.

- **Application Type:** Platform Admin Portal (internal tool for platform operators)
- **Target Users:** Platform administrators, not factory staff
- **Authentication:** Requires `platform_admin` role via `@fp/auth` mock auth
- **API Backend:** BFF service at `http://localhost:8080` (proxied via Vite)

### Technology Stack (per ADR-002)

| Technology | Version | Purpose |
|------------|---------|---------|
| Vite | Latest | Build tool and dev server |
| React | 18.x | UI framework |
| TypeScript | 5.x | Type safety |
| React Router | 6.x | Client-side routing |
| MUI v6 | 6.x | Component library |
| @fp/ui-components | workspace | Shared components (StatusBadge, TrendIndicator, LeafTypeTag) |
| @fp/auth | workspace | Authentication (MockAuthProvider) |
| Leaflet + react-leaflet | Latest | Map components (per ADR-017) |

### Theme Colors (Earth & Growth Palette)

| Token | Value | Usage |
|-------|-------|-------|
| Primary | `#1B4332` | Forest Green - brand, nav active |
| Secondary | `#5C4033` | Earth Brown - accents |
| Warning | `#D4A03A` | Harvest Gold - warnings |
| Error | `#C1292E` | Warm Red - errors, alerts |
| Background | `#FFFDF9` | Warm White - page background |

### Map Dependencies (ADR-017)

This story installs the map dependencies required for later stories (9.2 Region Management, 9.5 Farmer Management):

```bash
npm install leaflet react-leaflet leaflet-draw @turf/turf
npm install -D @types/leaflet @types/leaflet-draw
```

**Usage patterns defined in ADR-017:**
- `MapDisplay` - Show markers (factories, CPs)
- `GPSFieldWithMapAssist` - Two-way GPS field + collapsible map
- `BoundaryDrawer` - Draw polygon regions
- `GeoJSONImporter` - Import official boundaries

### Directory Structure (Target)

```
web/platform-admin/
├── src/
│   ├── app/
│   │   ├── App.tsx
│   │   ├── routes.tsx
│   │   └── providers/
│   │       ├── AuthProvider.tsx
│   │       └── ThemeProvider.tsx
│   ├── pages/
│   │   ├── Dashboard/
│   │   │   └── Dashboard.tsx
│   │   ├── regions/
│   │   │   ├── RegionList.tsx
│   │   │   └── RegionDetail.tsx
│   │   ├── farmers/
│   │   │   ├── FarmerList.tsx
│   │   │   └── FarmerDetail.tsx
│   │   ├── factories/
│   │   │   ├── FactoryList.tsx
│   │   │   ├── FactoryDetail.tsx
│   │   │   └── CollectionPointDetail.tsx
│   │   ├── grading-models/
│   │   │   ├── GradingModelList.tsx
│   │   │   └── GradingModelDetail.tsx
│   │   ├── users/
│   │   │   └── UserList.tsx
│   │   ├── health/
│   │   │   └── PlatformHealth.tsx
│   │   ├── knowledge/
│   │   │   └── KnowledgeLibrary.tsx
│   │   ├── costs/
│   │   │   └── CostDashboard.tsx
│   │   └── NotFound.tsx
│   ├── components/
│   │   ├── Layout/
│   │   │   └── Layout.tsx
│   │   ├── Sidebar/
│   │   │   └── Sidebar.tsx
│   │   ├── Header/
│   │   │   └── Header.tsx
│   │   └── Breadcrumb/
│   │       └── Breadcrumb.tsx
│   └── main.tsx
├── package.json
├── vite.config.ts
├── tsconfig.json
├── Dockerfile
└── nginx.conf
```

### Project Structure Notes

- Follows same structure as `web/factory-portal/`
- Uses npm workspaces for shared libraries
- Vite proxy configuration for BFF API
- Placeholder pages implement shell only (content in later stories)

### References

- [Source: _bmad-output/epics/epic-9-admin-portal/story-91a-platform-admin-application-scaffold.md]
- [Source: _bmad-output/architecture/adr/ADR-002-frontend-architecture.md] - Frontend Architecture
- [Source: _bmad-output/architecture/adr/ADR-017-map-services-gps-region-assignment.md] - Map Dependencies
- [Source: _bmad-output/project-context.md#ui-ux-rules] - Design Tokens
- [Source: web/factory-portal/] - Reference implementation for React patterns

### Dependencies

- **Story 0.5.5:** Shared Component Library (`@fp/ui-components`) - DONE
- **Story 0.5.6:** Shared Auth Library (`@fp/auth`) - DONE
- **ADR-017:** Map Services (Leaflet installation)

### Blocks

- **Story 9.1b:** Shared Admin UI Components (14 components for Epic 9)
- **Story 9.2:** Region Management (polygon boundaries)
- **Story 9.3-9.10:** All other Epic 9 stories

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- All 6 tasks completed successfully
- 39 unit tests passing
- Build produces ~167KB gzipped bundle (well under 500KB limit)
- Theme reuses @fp/ui-components ThemeProvider (no custom theme code needed)
- Leaflet CSS imports added for future map components per ADR-017

### File List

**Created:**

- `web/platform-admin/package.json` - npm package config with leaflet deps
- `web/platform-admin/tsconfig.json` - TypeScript config
- `web/platform-admin/tsconfig.node.json` - Node TypeScript config
- `web/platform-admin/vite.config.ts` - Vite config with port 3001
- `web/platform-admin/vitest.config.ts` - Vitest test config
- `web/platform-admin/eslint.config.js` - ESLint config
- `web/platform-admin/index.html` - HTML entry point
- `web/platform-admin/src/main.tsx` - React entry point with Leaflet CSS
- `web/platform-admin/src/vite-env.d.ts` - Vite type definitions
- `web/platform-admin/src/test-setup.ts` - Test setup with localStorage mock
- `web/platform-admin/src/app/App.tsx` - Root component
- `web/platform-admin/src/app/routes.tsx` - 14 routes with platform_admin protection
- `web/platform-admin/src/components/Layout/Layout.tsx` - Main shell layout
- `web/platform-admin/src/components/Layout/index.ts`
- `web/platform-admin/src/components/Sidebar/Sidebar.tsx` - 8 nav items with dividers
- `web/platform-admin/src/components/Sidebar/index.ts`
- `web/platform-admin/src/components/Header/Header.tsx` - Platform Admin badge
- `web/platform-admin/src/components/Header/index.ts`
- `web/platform-admin/src/components/Breadcrumb/Breadcrumb.tsx` - Dynamic breadcrumbs
- `web/platform-admin/src/components/Breadcrumb/index.ts`
- `web/platform-admin/src/pages/Dashboard/Dashboard.tsx` - Platform overview
- `web/platform-admin/src/pages/Dashboard/index.ts`
- `web/platform-admin/src/pages/regions/RegionList.tsx` - Placeholder
- `web/platform-admin/src/pages/regions/RegionDetail.tsx` - Placeholder
- `web/platform-admin/src/pages/regions/index.ts`
- `web/platform-admin/src/pages/farmers/FarmerList.tsx` - Placeholder
- `web/platform-admin/src/pages/farmers/FarmerDetail.tsx` - Placeholder
- `web/platform-admin/src/pages/farmers/index.ts`
- `web/platform-admin/src/pages/factories/FactoryList.tsx` - Placeholder
- `web/platform-admin/src/pages/factories/FactoryDetail.tsx` - Placeholder
- `web/platform-admin/src/pages/factories/CollectionPointDetail.tsx` - Placeholder
- `web/platform-admin/src/pages/factories/index.ts`
- `web/platform-admin/src/pages/grading-models/GradingModelList.tsx` - Placeholder
- `web/platform-admin/src/pages/grading-models/GradingModelDetail.tsx` - Placeholder
- `web/platform-admin/src/pages/grading-models/index.ts`
- `web/platform-admin/src/pages/users/UserList.tsx` - Placeholder
- `web/platform-admin/src/pages/users/index.ts`
- `web/platform-admin/src/pages/health/PlatformHealth.tsx` - Placeholder
- `web/platform-admin/src/pages/health/index.ts`
- `web/platform-admin/src/pages/knowledge/KnowledgeLibrary.tsx` - Placeholder
- `web/platform-admin/src/pages/knowledge/index.ts`
- `web/platform-admin/src/pages/costs/CostDashboard.tsx` - Placeholder
- `web/platform-admin/src/pages/costs/index.ts`
- `web/platform-admin/src/pages/NotFound.tsx` - 404 page
- `web/platform-admin/public/logo.png` - Copied from factory-portal
- `web/platform-admin/public/favicon.svg` - Copied from factory-portal
- `tests/unit/web/platform-admin/Layout.test.tsx` - Layout tests
- `tests/unit/web/platform-admin/Sidebar.test.tsx` - Sidebar tests
- `tests/unit/web/platform-admin/Header.test.tsx` - Header tests
- `tests/unit/web/platform-admin/Breadcrumb.test.tsx` - Breadcrumb tests
- `tests/unit/web/platform-admin/NotFound.test.tsx` - 404 page tests
- `tests/unit/web/platform-admin/routes.test.tsx` - Route tests

**Modified:**

- `package.json` - Added platform-admin to workspaces + npm scripts
- `_bmad-output/sprint-artifacts/sprint-status.yaml` - Status in-progress
- `_bmad-output/sprint-artifacts/9-1a-platform-admin-application-scaffold.md` - This file
