# Story 9.1b: Shared Admin UI Components

As a **platform developer**,
I want a library of reusable UI components for the Admin Portal,
So that all Epic 9 screens are built consistently and efficiently.

## Acceptance Criteria

**AC 9.1b.1: Shell Components**

**Given** the platform-admin application is scaffolded (Story 9.1a)
**When** I build the shell components
**Then** the following components are available in `libs/ui-components`:

| Component | Description |
|-----------|-------------|
| `AdminShell` | Main layout wrapper with sidebar + content area + breadcrumb header |
| `Sidebar` | Collapsible navigation with grouped menu items and icons |
| `Breadcrumb` | Dynamic trail showing navigation hierarchy (e.g., Factories > Nyeri > CP-001) |
| `PageHeader` | Title + subtitle + action buttons (Add, Edit, Back) |

**AC 9.1b.2: Data Display Components**

**Given** the shell components are built
**When** I build the data display components
**Then** the following components are available:

| Component | Description |
|-----------|-------------|
| `DataTable` | Sortable, filterable table with row actions, pagination, and loading states |
| `EntityCard` | Card for grid display with icon, title, subtitle, status badge, and click action |
| `FilterBar` | Combined dropdown filters + search input with clear/reset |
| `MetricCard` | Hero metric display with number, label, trend indicator, and optional icon |

**AC 9.1b.3: Form Components**

**Given** the data display components are built
**When** I build the form components
**Then** the following components are available:

| Component | Description |
|-----------|-------------|
| `InlineEditForm` | Read mode → Edit mode toggle with Save/Cancel actions |
| `ConfirmationDialog` | Modal for destructive actions with customizable title, message, and buttons |
| `FileDropzone` | Drag-and-drop file upload with progress, validation, and file type restrictions |

**AC 9.1b.4: Map Components**

**Given** the form components are built
**When** I build the map components (per ADR-017)
**Then** the following components are available:

| Component | Description |
|-----------|-------------|
| `MapDisplay` | Read-only Leaflet map with markers (factories, CPs, farmers) |
| `GPSFieldWithMapAssist` | Lat/Lng text fields + collapsible map picker with two-way binding |
| `BoundaryDrawer` | Leaflet.draw polygon/circle drawing with area/perimeter stats |

**AC 9.1b.5: Component Documentation**

**Given** all components are built
**When** I document the components
**Then** each component has:
- TypeScript interface for props
- Usage example in Storybook or README
- Accessibility notes (keyboard navigation, ARIA labels)

## Components to Build

### Shell Components (2 points)

#### `AdminShell`
```
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

#### `Sidebar`
- Collapsible (icon-only mode for mobile)
- Grouped sections: Entities, Configuration, Monitoring
- Active item highlight
- Icons from MUI Icons

#### `Breadcrumb`
- Dynamic based on current route
- Clickable segments for navigation
- Truncation for long paths

#### `PageHeader`
```
┌─────────────────────────────────────────────────────────────────┐
│  📍 Nyeri Highland Region                        [Edit] [Delete]│
│  12 factories • 156 farmers                                     │
└─────────────────────────────────────────────────────────────────┘
```

### Data Display Components (2 points)

#### `DataTable`
- Column sorting (asc/desc)
- Row selection (single/multi)
- Pagination with page size selector
- Loading skeleton
- Empty state
- Row actions (view, edit, delete)

#### `EntityCard`
```
┌─────────────────────────┐
│  🏭 Nyeri Tea Factory   │
│  Nyeri Highland         │
│  ● Active    12 CPs     │
└─────────────────────────┘
```

#### `FilterBar`
```
┌─────────────────────────────────────────────────────────────────┐
│  Region: [All ▼]  Status: [Active ▼]  Search: [🔍 Search...  ] │
└─────────────────────────────────────────────────────────────────┘
```

#### `MetricCard`
```
┌─────────────────────┐
│  🏭 12              │
│  Active Factories   │
│  ↑ 2 this month     │
└─────────────────────┘
```

### Form Components (2 points)

#### `InlineEditForm`
- Read mode: displays field values as text
- Edit mode: displays form inputs
- Toggle button (Edit/Cancel)
- Save button with loading state
- Validation error display

#### `ConfirmationDialog`
```
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

#### `FileDropzone`
```
┌─────────────────────────────────────────┐
│                                         │
│     📁 Drag & drop files here           │
│        or click to browse               │
│                                         │
│     Supported: CSV, PDF (max 10MB)      │
│                                         │
└─────────────────────────────────────────┘
```

### Map Components (2 points)

#### `MapDisplay`
- Leaflet + OpenStreetMap tiles
- Marker clusters for many points
- Custom marker icons by entity type
- Popup on marker click
- Zoom controls

#### `GPSFieldWithMapAssist`
- Two text fields: Latitude, Longitude
- "Select on Map" button to expand map
- Click on map updates text fields
- Text field changes update map marker
- Collapsible map panel

#### `BoundaryDrawer`
- Leaflet.draw integration
- Polygon and circle drawing tools
- Edit/delete drawn shapes
- Live area/perimeter calculation
- GeoJSON export on change
- Reference markers (existing factories)

## Technical Notes

### Package Dependencies

```bash
# Map components (ADR-017)
npm install leaflet react-leaflet leaflet-draw @turf/turf
npm install -D @types/leaflet @types/leaflet-draw
```

### File Structure

```
libs/ui-components/src/components/
├── AdminShell/
│   ├── AdminShell.tsx
│   ├── AdminShell.stories.tsx
│   └── index.ts
├── Sidebar/
├── Breadcrumb/
├── PageHeader/
├── DataTable/
├── EntityCard/
├── FilterBar/
├── MetricCard/
├── InlineEditForm/
├── ConfirmationDialog/
├── FileDropzone/
├── MapDisplay/
├── GPSFieldWithMapAssist/
└── BoundaryDrawer/
```

### Accessibility Requirements

- All components must be keyboard navigable
- Focus indicators must be visible
- ARIA labels for interactive elements
- Color contrast ratio minimum 4.5:1

## Dependencies

- Story 9.1a: Platform Admin Application Scaffold
- Story 1.10: GPS-Based Region Assignment (for map component contracts)
- ADR-017: Map Services and GPS-Based Region Assignment

## Story Points: 8

## Human Validation Gate

**⚠️ MANDATORY: This story requires human validation before acceptance.**

| Validation Type | Requirement |
|-----------------|-------------|
| **Storybook Review** | Human must review and approve all 14 components in Storybook |
| **Checklist** | Shell, DataTable, Forms, Map components - visual + interactive behavior |
| **Approval** | Story cannot be marked "done" until human signs off |

---
