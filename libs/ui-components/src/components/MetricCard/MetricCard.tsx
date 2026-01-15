/**
 * MetricCard Component
 *
 * Hero metric display with number, label, and trend indicator.
 * Used for KPI dashboards and summary statistics.
 *
 * Accessibility:
 * - Uses proper heading hierarchy
 * - Color + icon for trend (not color alone)
 * - role="figure" for semantic grouping
 */

import { Box, Card, Typography, useTheme } from '@mui/material';
import type { ReactNode } from 'react';
import type { TrendDirection } from '../TrendIndicator';
import { TrendIndicator } from '../TrendIndicator';

/** MetricCard component props */
export interface MetricCardProps {
  /** Metric value (number or formatted string) */
  value: string | number;
  /** Metric label */
  label: string;
  /** Optional trend direction */
  trend?: TrendDirection;
  /** Optional trend percentage value */
  trendValue?: number;
  /** Optional trend period description */
  trendPeriod?: string;
  /** Optional icon */
  icon?: ReactNode;
  /** Card color variant */
  color?: 'default' | 'primary' | 'success' | 'warning' | 'error';
  /** Optional click handler */
  onClick?: () => void;
  /** Description text for accessibility */
  description?: string;
}

const colorMap = {
  default: {
    bg: 'background.paper',
    value: 'text.primary',
    icon: 'text.secondary',
  },
  primary: {
    bg: 'primary.light',
    value: 'primary.main',
    icon: 'primary.main',
  },
  success: {
    bg: '#D8F3DC',
    value: '#1B4332',
    icon: '#1B4332',
  },
  warning: {
    bg: '#FFF8E7',
    value: '#D4A03A',
    icon: '#D4A03A',
  },
  error: {
    bg: '#FFE5E5',
    value: '#C1292E',
    icon: '#C1292E',
  },
} as const;

/**
 * MetricCard displays a key metric with optional trend indicator.
 *
 * @example
 * ```tsx
 * <MetricCard
 *   value={342}
 *   label="Active Farmers"
 *   trend="up"
 *   trendValue={12}
 *   trendPeriod="vs last month"
 *   icon={<PeopleIcon />}
 *   color="success"
 * />
 * ```
 */
export function MetricCard({
  value,
  label,
  trend,
  trendValue,
  trendPeriod,
  icon,
  color = 'default',
  onClick,
  description,
}: MetricCardProps): JSX.Element {
  const theme = useTheme();
  const colors = colorMap[color];
  const isClickable = onClick !== undefined;

  return (
    <Card
      role="figure"
      aria-label={description ?? `${label}: ${value}`}
      onClick={onClick}
      sx={{
        p: 2.5,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: colors.bg,
        cursor: isClickable ? 'pointer' : 'default',
        transition: 'all 0.2s ease-in-out',
        '&:hover': isClickable
          ? {
              boxShadow: theme.shadows[4],
              transform: 'translateY(-2px)',
            }
          : undefined,
        '&:focus-visible': isClickable
          ? {
              outline: `3px solid ${theme.palette.primary.main}`,
              outlineOffset: '2px',
            }
          : undefined,
      }}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={
        isClickable
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
    >
      {/* Header with icon */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          mb: 1,
        }}
      >
        <Typography
          variant="body2"
          sx={{
            color: 'text.secondary',
            fontWeight: 500,
            textTransform: 'uppercase',
            letterSpacing: 0.5,
          }}
        >
          {label}
        </Typography>
        {icon && (
          <Box
            sx={{
              color: colors.icon,
              display: 'flex',
              alignItems: 'center',
              '& svg': { fontSize: 24 },
            }}
          >
            {icon}
          </Box>
        )}
      </Box>

      {/* Main value */}
      <Typography
        variant="h3"
        sx={{
          color: colors.value,
          fontWeight: 700,
          lineHeight: 1.2,
          mb: trend !== undefined ? 1 : 0,
        }}
      >
        {value}
      </Typography>

      {/* Trend indicator */}
      {trend !== undefined && trendValue !== undefined && (
        <Box sx={{ mt: 'auto' }}>
          <TrendIndicator
            direction={trend}
            value={trendValue}
            period={trendPeriod}
            size="small"
          />
        </Box>
      )}
    </Card>
  );
}

export default MetricCard;
