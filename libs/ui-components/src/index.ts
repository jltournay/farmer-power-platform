/**
 * @fp/ui-components
 *
 * Farmer Power Platform Shared Component Library
 *
 * This package exports React components following the Farmer Power design system.
 *
 * IMPORTANT: For map components, consumers must import Leaflet CSS:
 * ```tsx
 * import 'leaflet/dist/leaflet.css';
 * import 'leaflet-draw/dist/leaflet.draw.css'; // Only if using BoundaryDrawer
 * ```
 */

// Theme exports
export { ThemeProvider, farmerPowerTheme, colors, statusColors } from './theme/index';
export type { StatusType } from './theme';

// ============================================
// Existing Components (Story 0.5.5)
// ============================================

export { StatusBadge } from './components/StatusBadge';
export type { StatusBadgeProps } from './components/StatusBadge';

export { TrendIndicator } from './components/TrendIndicator';
export type { TrendIndicatorProps, TrendDirection } from './components/TrendIndicator';

export { LeafTypeTag } from './components/LeafTypeTag';
export type { LeafTypeTagProps, LeafType, SupportedLanguage } from './components/LeafTypeTag';

// ============================================
// Shell Components (Story 9.1b - AC 9.1b.1)
// ============================================

export { AdminShell } from './components/AdminShell';
export type { AdminShellProps } from './components/AdminShell';

export { Sidebar } from './components/Sidebar';
export type { SidebarProps, SidebarItem } from './components/Sidebar';

export { Breadcrumb } from './components/Breadcrumb';
export type { BreadcrumbProps, BreadcrumbItem } from './components/Breadcrumb';

export { PageHeader } from './components/PageHeader';
export type { PageHeaderProps, PageHeaderAction } from './components/PageHeader';

// ============================================
// Data Display Components (Story 9.1b - AC 9.1b.2)
// ============================================

export { DataTable } from './components/DataTable';
export type { DataTableProps, DataTableAction } from './components/DataTable';

export { EntityCard } from './components/EntityCard';
export type { EntityCardProps } from './components/EntityCard';

export { FilterBar } from './components/FilterBar';
export type { FilterBarProps, FilterDef, FilterOption, FilterValues } from './components/FilterBar';

export { MetricCard } from './components/MetricCard';
export type { MetricCardProps } from './components/MetricCard';

// ============================================
// Form Components (Story 9.1b - AC 9.1b.3)
// ============================================

export { InlineEditForm } from './components/InlineEditForm';
export type { InlineEditFormProps, InlineEditField } from './components/InlineEditForm';

export { ConfirmationDialog } from './components/ConfirmationDialog';
export type { ConfirmationDialogProps } from './components/ConfirmationDialog';

export { FileDropzone } from './components/FileDropzone';
export type { FileDropzoneProps, UploadedFile } from './components/FileDropzone';

// ============================================
// Map Components (Story 9.1b - AC 9.1b.4)
// ============================================

export { MapDisplay } from './components/MapDisplay';
export type { MapDisplayProps, MapMarker } from './components/MapDisplay';

export { GPSFieldWithMapAssist } from './components/GPSFieldWithMapAssist';
export type {
  GPSFieldWithMapAssistProps,
  GPSCoordinates,
} from './components/GPSFieldWithMapAssist';

export { BoundaryDrawer } from './components/BoundaryDrawer';
export type {
  BoundaryDrawerProps,
  GeoJSONPolygon,
  BoundaryMapMarker,
  BoundaryStats,
} from './components/BoundaryDrawer';
