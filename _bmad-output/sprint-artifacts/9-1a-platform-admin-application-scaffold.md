# Story 9.1a: Platform Admin Application Scaffold

**Status:** ready-for-dev
**GitHub Issue:** <!-- Auto-created by dev-story workflow -->

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

- [ ] Task 1: Initialize Vite + React + TypeScript project (AC: 9.1.1)
  - [ ] Create `web/platform-admin/` directory
  - [ ] Copy `package.json` from `web/factory-portal/` and update:
    - Change name to `@fp/platform-admin`
    - Add leaflet deps: `leaflet react-leaflet leaflet-draw @turf/turf`
    - Add type definitions: `@types/leaflet @types/leaflet-draw`
  - [ ] Copy `tsconfig.json` from `web/factory-portal/` (identical)
  - [ ] Copy `tsconfig.node.json` from `web/factory-portal/` (identical)
  - [ ] Copy `vite.config.ts` from `web/factory-portal/` and change port to 3001
  - [ ] Copy `eslint.config.js` from `web/factory-portal/` (identical)
  - [ ] Run `npm install` from workspace root

- [ ] Task 2: Configure Theme (AC: 9.1.2) - **REUSE FROM @fp/ui-components**
  - [ ] Create `src/app/providers/ThemeProvider.tsx` that imports from `@fp/ui-components`:
    ```tsx
    import { ThemeProvider as FPThemeProvider } from '@fp/ui-components';
    export function ThemeProvider({ children }) {
      return <FPThemeProvider>{children}</FPThemeProvider>;
    }
    ```
  - [ ] **NOTE:** Theme already includes all required colors (Primary #1B4332, etc.) - NO custom theme needed!
  - [ ] Test theme colors render correctly

- [ ] Task 3: Install Map Dependencies (AC: 9.1.1, per ADR-017)
  - [ ] Verify leaflet deps installed in Task 1
  - [ ] Add Leaflet CSS import to `main.tsx`: `import 'leaflet/dist/leaflet.css'`
  - [ ] Add Leaflet.draw CSS if needed: `import 'leaflet-draw/dist/leaflet.draw.css'`

- [ ] Task 4: Configure Routing (AC: 9.1.3)
  - [ ] Copy `src/app/routes.tsx` from `web/factory-portal/` as starting point
  - [ ] Replace factory-portal routes with platform-admin routes (14 routes)
  - [ ] Use `ProtectedRoute` from `@fp/auth` with `roles={['platform_admin']}`
  - [ ] Create placeholder pages for each route in `src/pages/`
  - [ ] Copy `NotFound.tsx` from `web/factory-portal/src/pages/`

- [ ] Task 5: Implement Navigation Layout (AC: 9.1.4)
  - [ ] Copy `Layout.tsx` from `web/factory-portal/src/components/Layout/` (structure identical)
  - [ ] Copy `Sidebar.tsx` from `web/factory-portal/src/components/Sidebar/` and update:
    - Replace `menuItems` array with Admin routes (9 items with dividers)
    - Keep role-based filtering logic
  - [ ] Copy `Header.tsx` from `web/factory-portal/src/components/Header/` and update:
    - Change factory badge to show "Platform Admin"
  - [ ] **NEW:** Create `src/components/Breadcrumb/Breadcrumb.tsx` - uses `useLocation()` to build breadcrumb trail
  - [ ] Add Breadcrumb to Layout.tsx (between Header and content)

- [ ] Task 6: Build and Test (AC: 9.1.1-9.1.4)
  - [ ] Verify Vite proxy for `/api` -> BFF (copied from factory-portal)
  - [ ] Run `npm run build` and verify bundle size < 500KB gzipped
  - [ ] Test all routes render correctly
  - [ ] Test mock authentication integration (login as platform_admin)
  - [ ] Copy and adapt unit tests from `web/factory-portal/` for Layout components

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 9.1a: Platform Admin Application Scaffold"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/9-1a-platform-admin-scaffold
  ```

**Branch name:** `story/9-1a-platform-admin-scaffold`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
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
(paste test summary here - e.g., "42 passed in 5.23s")
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
# Start infrastructure
bash scripts/e2e-up.sh --build

# Wait for services, then run tests
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
cd web/platform-admin
npm run lint
```
**Lint passed:** [ ] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

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

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

**Created:**
- (list new files)

**Modified:**
- (list modified files with brief description)
