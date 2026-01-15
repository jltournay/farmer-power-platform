/**
 * EntityCard Component
 *
 * Card for grid display with icon, title, subtitle, and status badge.
 * Used for entity overviews in grid layouts.
 *
 * Accessibility:
 * - 48px minimum touch target when clickable
 * - Focus ring: 3px Forest Green outline
 * - role="article" for semantic grouping
 */

import { Box, Card, CardActionArea, Typography, useTheme } from '@mui/material';
import type { ReactNode } from 'react';

/** EntityCard component props */
export interface EntityCardProps {
  /** Card title (entity name) */
  title: string;
  /** Optional subtitle */
  subtitle?: string;
  /** Icon or avatar to display */
  icon?: ReactNode;
  /** Status badge to display */
  statusBadge?: ReactNode;
  /** Optional metric value to highlight */
  metric?: string | number;
  /** Optional metric label */
  metricLabel?: string;
  /** Click handler (makes card interactive) */
  onClick?: () => void;
  /** Whether card is selected */
  selected?: boolean;
  /** Additional content to display in card body */
  children?: ReactNode;
}

/**
 * EntityCard displays an entity in a card format for grid layouts.
 *
 * @example
 * ```tsx
 * <EntityCard
 *   title="John Kamau"
 *   subtitle="Nyeri County"
 *   icon={<PersonIcon />}
 *   statusBadge={<StatusBadge status="win" size="small" />}
 *   metric="92%"
 *   metricLabel="Primary"
 *   onClick={() => navigate(`/farmers/${id}`)}
 * />
 * ```
 */
export function EntityCard({
  title,
  subtitle,
  icon,
  statusBadge,
  metric,
  metricLabel,
  onClick,
  selected = false,
  children,
}: EntityCardProps): JSX.Element {
  const theme = useTheme();
  const isClickable = onClick !== undefined;

  const content = (
    <Box sx={{ p: 2 }}>
      {/* Header: Icon + Title + Status */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 1,
          mb: subtitle || metric ? 1 : 0,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flex: 1 }}>
          {icon && (
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 40,
                height: 40,
                borderRadius: 1,
                backgroundColor: 'primary.light',
                color: 'primary.contrastText',
                flexShrink: 0,
                '& svg': {
                  fontSize: 24,
                },
              }}
            >
              {icon}
            </Box>
          )}
          <Box sx={{ minWidth: 0, flex: 1 }}>
            <Typography
              variant="subtitle1"
              sx={{
                fontWeight: 600,
                lineHeight: 1.3,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {title}
            </Typography>
            {subtitle && (
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {subtitle}
              </Typography>
            )}
          </Box>
        </Box>
        {statusBadge && <Box sx={{ flexShrink: 0 }}>{statusBadge}</Box>}
      </Box>

      {/* Metric display */}
      {metric !== undefined && (
        <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, mt: 1 }}>
          <Typography
            variant="h4"
            sx={{ fontWeight: 600, color: 'primary.main', lineHeight: 1 }}
          >
            {metric}
          </Typography>
          {metricLabel && (
            <Typography variant="body2" color="text.secondary">
              {metricLabel}
            </Typography>
          )}
        </Box>
      )}

      {/* Additional content */}
      {children}
    </Box>
  );

  return (
    <Card
      role="article"
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        border: selected ? `2px solid ${theme.palette.primary.main}` : '1px solid',
        borderColor: selected ? 'primary.main' : 'divider',
        transition: 'all 0.2s ease-in-out',
        ...(isClickable && {
          '&:hover': {
            boxShadow: theme.shadows[4],
            transform: 'translateY(-2px)',
          },
        }),
      }}
    >
      {isClickable ? (
        <CardActionArea
          onClick={onClick}
          sx={{
            flexGrow: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'stretch',
            '&:focus': {
              outline: `3px solid ${theme.palette.primary.main}`,
              outlineOffset: '-3px',
            },
          }}
        >
          {content}
        </CardActionArea>
      ) : (
        content
      )}
    </Card>
  );
}

export default EntityCard;
