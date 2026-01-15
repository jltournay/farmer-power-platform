# @fp/ui-components

Farmer Power Platform Shared Component Library.

## Installation

```bash
npm install @fp/ui-components
```

## Usage

```tsx
import { ThemeProvider, StatusBadge, TrendIndicator } from '@fp/ui-components';

function App() {
  return (
    <ThemeProvider>
      <StatusBadge status="win" />
      <TrendIndicator direction="up" value={12} />
    </ThemeProvider>
  );
}
```

## Map Components Setup

When using map components (`MapDisplay`, `GPSFieldWithMapAssist`, `BoundaryDrawer`), you must import Leaflet CSS in your application's entry point (e.g., `main.tsx`):

```tsx
// In your app's main.tsx or index.tsx
import 'leaflet/dist/leaflet.css';
import 'leaflet-draw/dist/leaflet.draw.css';
```

This is required because Leaflet CSS cannot be bundled within the library and must be loaded by the consuming application.

## Components

### Shell Components
- `AdminShell` - Main layout wrapper with sidebar + content area
- `Sidebar` - Collapsible navigation with grouped menu items and icons
- `Breadcrumb` - Dynamic trail showing navigation hierarchy
- `PageHeader` - Title + subtitle + action buttons

### Data Display Components
- `DataTable` - Sortable, filterable table with row actions and pagination
- `EntityCard` - Card for grid display with icon, title, subtitle, status badge
- `FilterBar` - Combined dropdown filters + search input
- `MetricCard` - Hero metric display with number, label, trend indicator

### Form Components
- `InlineEditForm` - Read mode → Edit mode toggle with Save/Cancel
- `ConfirmationDialog` - Modal for destructive actions
- `FileDropzone` - Drag-and-drop file upload with progress and validation

### Map Components
- `MapDisplay` - Read-only Leaflet map with markers
- `GPSFieldWithMapAssist` - Lat/Lng text fields + collapsible map picker
- `BoundaryDrawer` - Polygon/circle drawing with area/perimeter stats

### Status Components
- `StatusBadge` - WIN/WATCH/ACTION status display
- `TrendIndicator` - Up/Down/Stable trend arrows
- `LeafTypeTag` - Tea leaf type badges

## Development

```bash
# Install dependencies
npm install

# Start Storybook
npm run storybook

# Run tests
npm run test

# Build library
npm run build
```
