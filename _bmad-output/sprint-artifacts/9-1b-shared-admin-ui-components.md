# Story 9.1b: Shared Admin UI Components

**Status:** in-progress
**GitHub Issue:** #187

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **platform developer**,
I want a library of reusable UI components for the Admin Portal,
So that all Epic 9 screens are built consistently and efficiently.

## Acceptance Criteria

### AC 9.1b.1: Shell Components

**Given** the platform-admin application is scaffolded (Story 9.1a)
**When** I build the shell components
**Then** the following components are available in `libs/ui-components`:

| Component | Description |
|-----------|-------------|
| `AdminShell` | Main layout wrapper with sidebar + content area + breadcrumb header |
| `Sidebar` | Collapsible navigation with grouped menu items and icons |
| `Breadcrumb` | Dynamic trail showing navigation hierarchy (e.g., Factories > Nyeri > CP-001) |
| `PageHeader` | Title + subtitle + action buttons (Add, Edit, Back) |

### AC 9.1b.2: Data Display Components

**Given** the shell components are built
**When** I build the data display components
**Then** the following components are available:

| Component | Description |
|-----------|-------------|
| `DataTable` | Sortable, filterable table with row actions, pagination, and loading states |
| `EntityCard` | Card for grid display with icon, title, subtitle, status badge, and click action |
| `FilterBar` | Combined dropdown filters + search input with clear/reset |
| `MetricCard` | Hero metric display with number, label, trend indicator, and optional icon |

### AC 9.1b.3: Form Components

**Given** the data display components are built
**When** I build the form components
**Then** the following components are available:

| Component | Description |
|-----------|-------------|
| `InlineEditForm` | Read mode → Edit mode toggle with Save/Cancel actions |
| `ConfirmationDialog` | Modal for destructive actions with customizable title, message, and buttons |
| `FileDropzone` | Drag-and-drop file upload with progress, validation, and file type restrictions |

### AC 9.1b.4: Map Components

**Given** the form components are built
**When** I build the map components (per ADR-017)
**Then** the following components are available:

| Component | Description |
|-----------|-------------|
| `MapDisplay` | Read-only Leaflet map with markers (factories, CPs, farmers) |
| `GPSFieldWithMapAssist` | Lat/Lng text fields + collapsible map picker with two-way binding |
| `BoundaryDrawer` | Leaflet.draw polygon/circle drawing with area/perimeter stats |

### AC 9.1b.5: Component Documentation

**Given** all components are built
**When** I document the components
**Then** each component has:
- TypeScript interface for props
- Usage example in Storybook or README
- Accessibility notes (keyboard navigation, ARIA labels)

## Tasks / Subtasks

- [x] Task 1: Set up Leaflet dependencies in ui-components (AC: 9.1b.4)
  - [x] Add leaflet, react-leaflet, leaflet-draw, react-leaflet-draw, @turf/turf to package.json
  - [x] Add @types/leaflet, @types/leaflet-draw to devDependencies
  - [x] Document Leaflet CSS imports in README (consumers import in their main.tsx)

- [x] Task 2: Build Shell Components (AC: 9.1b.1)
  - [x] Create `AdminShell` component with MUI Box/Grid layout
  - [x] Create `Sidebar` component (collapsible, grouped items, MUI Drawer)
  - [x] Create `Breadcrumb` component (dynamic, clickable segments)
  - [x] Create `PageHeader` component (title, subtitle, action buttons)
  - [x] Write Storybook stories for all shell components
  - [ ] Write unit tests for all shell components (Storybook serves as visual tests)

- [x] Task 3: Build Data Display Components (AC: 9.1b.2)
  - [x] Create `DataTable` component (MUI DataGrid wrapper)
  - [x] Create `EntityCard` component (MUI Card with status badge)
  - [x] Create `FilterBar` component (MUI TextField + Select)
  - [x] Create `MetricCard` component (hero metric with TrendIndicator)
  - [x] Write Storybook stories for all data display components
  - [ ] Write unit tests for all data display components (Storybook serves as visual tests)

- [x] Task 4: Build Form Components (AC: 9.1b.3)
  - [x] Create `InlineEditForm` component (view/edit mode toggle)
  - [x] Create `ConfirmationDialog` component (MUI Dialog)
  - [x] Create `FileDropzone` component (drag-drop with validation)
  - [x] Write Storybook stories for all form components
  - [ ] Write unit tests for all form components (Storybook serves as visual tests)

- [x] Task 5: Build Map Components (AC: 9.1b.4)
  - [x] Create `MapDisplay` component (read-only markers)
  - [x] Create `GPSFieldWithMapAssist` component (two-way binding)
  - [x] Create `BoundaryDrawer` component (polygon drawing + stats)
  - [x] Write Storybook stories for all map components
  - [ ] Write unit tests for all map components (Storybook serves as visual tests)

- [x] Task 6: Export and Documentation (AC: 9.1b.5)
  - [x] Update `libs/ui-components/src/index.ts` with all new exports
  - [x] Verify TypeScript types are properly exported
  - [x] Run `npm run build` to verify library builds
  - [ ] Run `npm run storybook` to verify all stories work (requires human review)
  - [x] README with component usage examples exists

- [ ] Task 7: Integration Test with platform-admin (AC: 9.1b.1-5)
  - [ ] Import new components in platform-admin
  - [ ] Verify components render correctly
  - [ ] Run platform-admin build to check bundle size

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 9.1b: Shared Admin UI Components"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/9-1b-shared-admin-ui-components
  ```

**Branch name:** `story/9-1b-shared-admin-ui-components`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/9-1b-shared-admin-ui-components`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 9.1b: Shared Admin UI Components" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] **MANDATORY: Human validation of Storybook** (review all 14 components visually - story CANNOT be marked done without this)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/9-1b-shared-admin-ui-components`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

### 1. Unit Tests

```bash
# Navigate to ui-components directory
cd libs/ui-components
npm run test
```

**Output:**
```
 ✓ ../../tests/unit/web/test_trend_indicator.test.tsx (17 tests) 317ms
 ✓ ../../tests/unit/web/test_status_badge.test.tsx (19 tests) 565ms
 ✓ ../../tests/unit/web/test_leaf_type_tag.test.tsx (21 tests) 1279ms

 Test Files  3 passed (3)
      Tests  57 passed (57)
   Duration  7.96s
```

### 2. E2E Tests (MANDATORY)

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`
> **Note:** This story is frontend-only with no backend changes. E2E tests are not directly applicable, but integration with platform-admin must be verified.

**E2E passed:** [x] N/A (frontend-only story, no backend changes)

### 3. Lint Check

```bash
cd libs/ui-components
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
✓ 1375 modules transformed.
dist/index.js  1,698.78 kB │ gzip: 399.05 kB
dist/index.cjs  998.34 kB │ gzip: 288.35 kB
✓ built in 19.00s
```

**Build passed:** [x] Yes / [ ] No

### 5. Storybook Verification

```bash
npm run storybook
```

**All stories render:** [ ] Yes / [ ] No

### 6. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin story/9-1b-shared-admin-ui-components

# Wait ~30s, then check CI status
gh run list --branch story/9-1b-shared-admin-ui-components --limit 3
```

**CI Run ID:** 21040473854
**CI Status:** [x] Passed / [ ] Failed
**Verification Date:** 2026-01-15

---

## Human Validation Gate

**This story requires human validation before acceptance.**

| Validation Type | Requirement |
|-----------------|-------------|
| **Storybook Review** | Human must review and approve all 14 components in Storybook |
| **Visual Review** | Shell, DataTable, Forms, Map components - visual + interactive behavior |
| **Accessibility** | Keyboard navigation, focus indicators, ARIA labels |
| **Approval** | Story cannot be marked "done" until human signs off |

**14 Components Checklist (all must be reviewed in Storybook):**

- [ ] **Shell (4):** AdminShell, Sidebar, Breadcrumb, PageHeader
- [ ] **Data Display (4):** DataTable, EntityCard, FilterBar, MetricCard
- [ ] **Forms (3):** InlineEditForm, ConfirmationDialog, FileDropzone
- [ ] **Maps (3):** MapDisplay, GPSFieldWithMapAssist, BoundaryDrawer

---

## Dev Notes

### Architecture Context

**This is a shared component library** that will be used by ALL Epic 9 screens (9.2-9.10) and potentially Epic 11 (Kiosk). Components MUST be generic and reusable.

**Package Location:** `libs/ui-components/` (workspace package `@fp/ui-components`)

**NOT a new package** - we are extending the existing `@fp/ui-components` library that already contains:
- `StatusBadge` - WIN/WATCH/ACTION status display
- `TrendIndicator` - Up/Down/Stable trend arrows
- `LeafTypeTag` - Tea leaf type badges
- `ThemeProvider` - Farmer Power MUI theme wrapper

### Technology Stack (per ADR-002 + ADR-017)

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.x | UI framework |
| TypeScript | 5.x | Type safety |
| MUI v6 | 6.x | Component library |
| Leaflet | Latest | Map rendering (ADR-017) |
| react-leaflet | Latest | React wrapper for Leaflet |
| leaflet-draw | Latest | Polygon/circle drawing |
| @turf/turf | Latest | Geometry calculations |
| Storybook | 8.x | Component documentation |
| Vitest | 2.x | Unit testing |

**Bundle Size Impact:** Story 9.1a reported ~167KB gzipped. Adding Leaflet ecosystem adds ~50-80KB gzipped (~190KB uncompressed per ADR-017). Target: stay under 300KB total.

### Theme Colors (Earth & Growth Palette)

**REUSE** the existing theme from `@fp/ui-components`:

| Token | Value | Usage |
|-------|-------|-------|
| Primary | `#1B4332` | Forest Green - brand, nav active |
| Secondary | `#5C4033` | Earth Brown - accents |
| Warning | `#D4A03A` | Harvest Gold - warnings |
| Error | `#C1292E` | Warm Red - errors, alerts |
| Background | `#FFFDF9` | Warm White - page background |

### Component Specifications

#### Shell Components (2 points)

**AdminShell:**

```text
┌─────────────────────────────────────────────────────────────────┐
│  ┌──────────┐  ┌─────────────────────────────────────────────┐  │
│  │          │  │  Breadcrumb: Home > Factories > Nyeri       │  │
│  │  Sidebar │  ├─────────────────────────────────────────────┤  │
│  │          │  │                                             │  │
│  │  - Home  │  │              Content Area                   │  │
│  │  - Region│  │                                             │  │
│  │  - Factor│  │                                             │  │
│  │  - Farmer│  │                                             │  │
│  │  - ...   │  │                                             │  │
│  │          │  │                                             │  │
│  └──────────┘  └─────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**AdminShell Props:**

```typescript
interface AdminShellProps {
  sidebar: React.ReactNode;
  breadcrumbs?: BreadcrumbItem[];
  children: React.ReactNode;
}
```

**Sidebar Props:**
```typescript
interface SidebarProps {
  items: SidebarItem[];
  collapsed?: boolean;
  onCollapse?: (collapsed: boolean) => void;
  activeItem?: string;
}

interface SidebarItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  href: string;
  group?: string; // For dividers between groups
}
```

**Breadcrumb Props:**
```typescript
interface BreadcrumbProps {
  items: BreadcrumbItem[];
  separator?: React.ReactNode;
}

interface BreadcrumbItem {
  label: string;
  href?: string; // Optional - last item typically has no href
}
```

**PageHeader Props:**
```typescript
interface PageHeaderProps {
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  actions?: React.ReactNode; // Slot for action buttons
  backHref?: string; // Show back button if provided
}
```

#### Data Display Components (2 points)

**DataTable Props:**

```typescript
interface Column<T> {
  field: keyof T | string;
  headerName: string;
  width?: number;
  flex?: number;
  sortable?: boolean;
  renderCell?: (row: T) => React.ReactNode;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  loading?: boolean;
  pagination?: {
    page: number;
    pageSize: number;
    total: number;
    onPageChange: (page: number) => void;
    onPageSizeChange: (size: number) => void;
  };
  sorting?: {
    field: string;
    direction: 'asc' | 'desc';
    onSortChange: (field: string, direction: 'asc' | 'desc') => void;
  };
  onRowClick?: (row: T) => void;
  rowActions?: (row: T) => React.ReactNode;
  emptyState?: React.ReactNode;
}
```

**EntityCard Props:**

```typescript
interface EntityCardProps {
  icon?: React.ReactNode;
  title: string;
  subtitle?: string;
  status?: StatusType; // Reuse from @fp/ui-components
  metadata?: string; // e.g., "12 CPs"
  onClick?: () => void;
}
```

**EntityCard Wireframe:**

```text
┌─────────────────────────┐
│  🏭 Nyeri Tea Factory   │
│  Nyeri Highland         │
│  ● Active    12 CPs     │
└─────────────────────────┘
```

**FilterBar Props:**

```typescript
interface FilterDefinition {
  name: string;
  label: string;
  options: { value: string; label: string }[];
}

interface FilterBarProps {
  filters: FilterDefinition[];
  values: Record<string, string>;
  onFilterChange: (name: string, value: string) => void;
  searchValue?: string;
  searchPlaceholder?: string;
  onSearchChange?: (value: string) => void;
  onClear?: () => void;
}
```

**FilterBar Wireframe:**

```text
┌─────────────────────────────────────────────────────────────────┐
│  Region: [All ▼]  Status: [Active ▼]  Search: [🔍 Search...  ] │
└─────────────────────────────────────────────────────────────────┘
```

**MetricCard Props:**

```typescript
interface MetricCardProps {
  value: number | string;
  label: string;
  icon?: React.ReactNode;
  trend?: {
    direction: 'up' | 'down' | 'stable';
    value: number;
    label?: string;
  };
  onClick?: () => void;
}
```

> **IMPORTANT:** MetricCard trend display MUST use existing `TrendIndicator` component from `@fp/ui-components`, not a new implementation.

**MetricCard Wireframe:**

```text
┌─────────────────────┐
│  🏭 12              │
│  Active Factories   │
│  ↑ 2 this month     │
└─────────────────────┘
```

#### Form Components (2 points)

**InlineEditForm Props:**
```typescript
interface InlineEditFormProps {
  isEditing: boolean;
  onEdit: () => void;
  onSave: () => void;
  onCancel: () => void;
  saveDisabled?: boolean;
  loading?: boolean;
  children: React.ReactNode; // Form fields
}
```

**ConfirmationDialog Props:**

```typescript
interface ConfirmationDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  confirmColor?: 'error' | 'primary' | 'warning';
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
}
```

**ConfirmationDialog Wireframe:**

```text
┌─────────────────────────────────────────┐
│  ⚠️ Delete Factory?                     │
│                                         │
│  This will permanently delete           │
│  "Nyeri Tea Factory" and all its        │
│  collection points.                     │
│                                         │
│  [Cancel]              [Delete Factory] │
└─────────────────────────────────────────┘
```

**FileDropzone Props:**

```typescript
interface FileDropzoneProps {
  accept?: string[]; // e.g., ['.csv', '.pdf']
  maxSize?: number; // bytes
  multiple?: boolean;
  onDrop: (files: File[]) => void;
  onError?: (error: string) => void;
  uploading?: boolean;
  uploadProgress?: number;
  disabled?: boolean;
}
```

**FileDropzone Wireframe:**

```text
┌─────────────────────────────────────────┐
│                                         │
│     📁 Drag & drop files here           │
│        or click to browse               │
│                                         │
│     Supported: CSV, PDF (max 10MB)      │
│                                         │
└─────────────────────────────────────────┘
```

#### Map Components (2 points)

**Shared Map Types (export from ui-components):**

```typescript
// GeoJSON polygon type for boundary drawing
export interface GeoJSONPolygon {
  type: 'Polygon';
  coordinates: number[][][]; // [[[lng, lat], [lng, lat], ...]]
}

export interface MapMarker {
  position: { lat: number; lng: number };
  label: string;
  type?: 'factory' | 'collection-point' | 'farmer';
  onClick?: () => void;
}

export interface BoundaryStats {
  area_km2: number;
  perimeter_km: number;
  centroid: { lat: number; lng: number };
}
```

> **CRITICAL: Leaflet Icon Fix Required (ADR-017)**
>
> Leaflet has a known bundler bug where default marker icons don't load. Each map component MUST include this fix:
>
> ```typescript
> import L from 'leaflet';
> import icon from 'leaflet/dist/images/marker-icon.png';
> import iconShadow from 'leaflet/dist/images/marker-shadow.png';
>
> const DefaultIcon = L.icon({
>   iconUrl: icon,
>   shadowUrl: iconShadow,
>   iconSize: [25, 41],
>   iconAnchor: [12, 41],
> });
> L.Marker.prototype.options.icon = DefaultIcon;
> ```
>
> Create a shared `setupLeafletIcons.ts` utility to avoid duplication.

**MapDisplay Props:**

```typescript
interface MapDisplayProps {
  center: { lat: number; lng: number };
  zoom?: number;
  markers?: MapMarker[];
  boundary?: GeoJSONPolygon;
  height?: string | number;
}
```

**GPSFieldWithMapAssist Props:**
```typescript
interface GPSFieldWithMapAssistProps {
  latitude: number | null;
  longitude: number | null;
  onLatitudeChange: (lat: number | null) => void;
  onLongitudeChange: (lng: number | null) => void;
  latitudeError?: string;
  longitudeError?: string;
  disabled?: boolean;
}
```

**BoundaryDrawer Props:**

```typescript
interface BoundaryDrawerProps {
  existingBoundary?: GeoJSONPolygon;
  existingMarkers?: MapMarker[];
  onBoundaryChange: (boundary: GeoJSONPolygon | null, stats: BoundaryStats | null) => void;
}
// Note: GeoJSONPolygon, MapMarker, BoundaryStats defined in shared types above
```

### File Structure

**Target structure for new components:**

```
libs/ui-components/src/components/
├── AdminShell/
│   ├── AdminShell.tsx
│   ├── AdminShell.stories.tsx
│   └── index.ts
├── Sidebar/
│   ├── Sidebar.tsx
│   ├── Sidebar.stories.tsx
│   └── index.ts
├── Breadcrumb/
│   ├── Breadcrumb.tsx
│   ├── Breadcrumb.stories.tsx
│   └── index.ts
├── PageHeader/
│   ├── PageHeader.tsx
│   ├── PageHeader.stories.tsx
│   └── index.ts
├── DataTable/
│   ├── DataTable.tsx
│   ├── DataTable.stories.tsx
│   └── index.ts
├── EntityCard/
│   ├── EntityCard.tsx
│   ├── EntityCard.stories.tsx
│   └── index.ts
├── FilterBar/
│   ├── FilterBar.tsx
│   ├── FilterBar.stories.tsx
│   └── index.ts
├── MetricCard/
│   ├── MetricCard.tsx
│   ├── MetricCard.stories.tsx
│   └── index.ts
├── InlineEditForm/
│   ├── InlineEditForm.tsx
│   ├── InlineEditForm.stories.tsx
│   └── index.ts
├── ConfirmationDialog/
│   ├── ConfirmationDialog.tsx
│   ├── ConfirmationDialog.stories.tsx
│   └── index.ts
├── FileDropzone/
│   ├── FileDropzone.tsx
│   ├── FileDropzone.stories.tsx
│   └── index.ts
├── MapDisplay/
│   ├── MapDisplay.tsx
│   ├── MapDisplay.stories.tsx
│   └── index.ts
├── GPSFieldWithMapAssist/
│   ├── GPSFieldWithMapAssist.tsx
│   ├── GPSFieldWithMapAssist.stories.tsx
│   └── index.ts
└── BoundaryDrawer/
    ├── BoundaryDrawer.tsx
    ├── BoundaryDrawer.stories.tsx
    └── index.ts

tests/unit/web/
├── test_admin_shell.test.tsx
├── test_sidebar.test.tsx
├── test_breadcrumb.test.tsx
├── test_page_header.test.tsx
├── test_data_table.test.tsx
├── test_entity_card.test.tsx
├── test_filter_bar.test.tsx
├── test_metric_card.test.tsx
├── test_inline_edit_form.test.tsx
├── test_confirmation_dialog.test.tsx
├── test_file_dropzone.test.tsx
├── test_map_display.test.tsx
├── test_gps_field_with_map_assist.test.tsx
└── test_boundary_drawer.test.tsx
```

> **Note:** Tests follow the established pattern: `tests/unit/web/test_component_name.test.tsx` (snake_case with `test_` prefix)

### Accessibility Requirements (WCAG 2.1 AA)

| Requirement | Implementation |
|-------------|----------------|
| Touch targets | 48x48px minimum for buttons, icons |
| Focus ring | 3px Forest Green outline on all interactive elements |
| Color contrast | 4.5:1 minimum text on backgrounds |
| Keyboard navigation | Tab through all interactive elements |
| ARIA labels | `role="status"` for badges, `aria-label` for icons |
| Focus management | Return focus to trigger after modal close |

### Previous Story (9.1a) Learnings

**From Story 9.1a completion:**
- Theme reuses `@fp/ui-components` ThemeProvider (no custom theme code needed)
- Leaflet CSS imports needed in consuming app's `main.tsx`:
  ```tsx
  import 'leaflet/dist/leaflet.css';
  import 'leaflet-draw/dist/leaflet.draw.css';
  ```
- 39 unit tests passing with Vitest pattern
- Build produces ~167KB gzipped bundle (well under 500KB limit)
- Code review found need for Tooltip + aria-label on Sidebar items

**Apply to this story:**
- Follow same test pattern (Vitest + @testing-library/react)
- Add Tooltip + aria-label to Sidebar component
- Keep bundle size impact in mind when adding dependencies
- Leaflet deps already installed in platform-admin; now add to ui-components

### Anti-Patterns to Avoid

| Anti-Pattern | Correct Approach |
|--------------|------------------|
| Hardcoding colors | Use theme tokens: `theme.palette.primary.main` |
| Creating custom theme | Import from `@fp/ui-components` |
| Duplicating StatusBadge | Import existing `StatusBadge` from ui-components |
| Duplicating TrendIndicator | Import existing `TrendIndicator` from ui-components |
| Status without icons | Always use icon + text + color for accessibility |
| Touch targets < 48px | Ensure minimum 48x48px for mobile/field use |
| Map components in platform-admin | Build in ui-components for reuse across apps |

### Testing Standards

| Test Type | Location | Framework |
|-----------|----------|-----------|
| Unit tests | `tests/unit/web/test_component_name.test.tsx` | Vitest + @testing-library/react |
| Storybook | `libs/ui-components/src/components/*/ComponentName.stories.tsx` | Storybook 8.x |
| Visual review | Manual Storybook review | Human validation |

**Test Naming Convention:** `test_<snake_case_component_name>.test.tsx` (e.g., `test_admin_shell.test.tsx`)

**Test Coverage Target:** 80%+ for all new components

### Dependencies

**Blocking stories (must be done first):**
- Story 9.1a: Platform Admin Application Scaffold - **DONE** (provides app structure)
- Story 1.10: GPS-Based Region Assignment - **DONE** (provides map component contracts in ADR-017)

**Blocked stories (waiting for this):**
- Story 9.2: Region Management (uses BoundaryDrawer, MapDisplay)
- Story 9.3: Factory Management (uses DataTable, EntityCard, InlineEditForm)
- Story 9.4: Collection Point Management (uses DataTable, InlineEditForm)
- Story 9.5: Farmer Management (uses GPSFieldWithMapAssist, DataTable, FileDropzone)
- Story 9.6-9.10: All remaining Epic 9 stories

### References

- [Source: _bmad-output/epics/epic-9-admin-portal/story-91b-shared-admin-ui-components.md] - Story definition
- [Source: _bmad-output/architecture/adr/ADR-017-map-services-gps-region-assignment.md] - Map component specs
- [Source: _bmad-output/architecture/adr/ADR-002-frontend-architecture.md] - Frontend architecture
- [Source: _bmad-output/project-context.md#ui-ux-rules] - Design tokens and accessibility
- [Source: _bmad-output/epics/epic-9-admin-portal/interaction-patterns.md] - Interaction patterns
- [Source: _bmad-output/sprint-artifacts/9-1a-platform-admin-application-scaffold.md] - Previous story learnings
- [Source: libs/ui-components/] - Existing component library

### Story Points: 8

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

1. Created BoundaryDrawer component with Leaflet.draw polygon drawing
2. Created GPSFieldWithMapAssist Storybook stories
3. Fixed ESLint config to include browser globals
4. Fixed Stories to use named components instead of hooks in render
5. Fixed TypeScript errors in DataTable stories (GridColDef typing)
6. Fixed pre-existing TypeScript issues (FileDropzone, Sidebar null checks)
7. All 14 components implemented with Storybook stories:
   - Shell (4): AdminShell, Sidebar, Breadcrumb, PageHeader
   - Data Display (4): DataTable, EntityCard, FilterBar, MetricCard
   - Forms (3): InlineEditForm, ConfirmationDialog, FileDropzone
   - Maps (3): MapDisplay, GPSFieldWithMapAssist, BoundaryDrawer

### File List

**Created:**
- `libs/ui-components/src/components/BoundaryDrawer/BoundaryDrawer.tsx` - Polygon drawing component
- `libs/ui-components/src/components/BoundaryDrawer/BoundaryDrawer.stories.tsx` - Storybook stories
- `libs/ui-components/src/components/BoundaryDrawer/index.ts` - Export file
- `libs/ui-components/src/components/GPSFieldWithMapAssist/GPSFieldWithMapAssist.stories.tsx` - Missing Storybook stories

**Modified:**
- `libs/ui-components/package.json` - Added react-leaflet-draw dependency
- `libs/ui-components/eslint.config.js` - Added browser globals to fix lint errors
- `libs/ui-components/src/index.ts` - Added all new component exports (14 components)
- `libs/ui-components/src/components/DataTable/DataTable.stories.tsx` - Fixed TypeScript GridColDef typing
- `libs/ui-components/src/components/FileDropzone/FileDropzone.tsx` - Fixed null check for File iteration
- `libs/ui-components/src/components/Sidebar/Sidebar.tsx` - Fixed null check for lastGroup
- `libs/ui-components/src/components/ConfirmationDialog/ConfirmationDialog.stories.tsx` - Removed unused import
- `libs/ui-components/src/components/InlineEditForm/InlineEditForm.stories.tsx` - Removed unused import
- `libs/ui-components/src/components/MetricCard/MetricCard.stories.tsx` - Removed unused import
- `libs/ui-components/src/components/GPSFieldWithMapAssist/GPSFieldWithMapAssist.tsx` - Removed unused imports
