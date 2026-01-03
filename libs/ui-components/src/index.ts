/**
 * @fp/ui-components
 *
 * Farmer Power Platform Shared Component Library
 *
 * This package exports React components following the Farmer Power design system.
 */

// Theme exports
export { ThemeProvider, farmerPowerTheme, colors, statusColors } from './theme/index';
export type { StatusType } from './theme';

// Component exports
export { StatusBadge } from './components/StatusBadge';
export type { StatusBadgeProps } from './components/StatusBadge';

export { TrendIndicator } from './components/TrendIndicator';
export type { TrendIndicatorProps, TrendDirection } from './components/TrendIndicator';

export { LeafTypeTag } from './components/LeafTypeTag';
export type { LeafTypeTagProps, LeafType, SupportedLanguage } from './components/LeafTypeTag';
