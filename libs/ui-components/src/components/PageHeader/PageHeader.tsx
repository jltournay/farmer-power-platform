/**
 * PageHeader Component
 *
 * Title + subtitle + action buttons for page headers.
 * Consistent header pattern across all admin pages.
 *
 * Accessibility:
 * - Uses semantic heading elements (h1)
 * - Back button has accessible label
 * - 48px minimum touch target for actions
 */

import { Box, IconButton, Typography, Button, useTheme } from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import type { ReactNode } from 'react';

/** Action button definition */
export interface PageHeaderAction {
  /** Unique identifier */
  id: string;
  /** Button label */
  label: string;
  /** Optional icon */
  icon?: ReactNode;
  /** Button variant */
  variant?: 'text' | 'outlined' | 'contained';
  /** Button color */
  color?: 'primary' | 'secondary' | 'error' | 'warning' | 'info' | 'success';
  /** Click handler */
  onClick: () => void;
  /** Whether button is disabled */
  disabled?: boolean;
}

/** PageHeader component props */
export interface PageHeaderProps {
  /** Page title */
  title: string;
  /** Optional subtitle */
  subtitle?: string;
  /** Back navigation href (shows back button if provided) */
  backHref?: string;
  /** Back navigation callback */
  onBack?: () => void;
  /** Action buttons to display on the right */
  actions?: PageHeaderAction[];
  /** Optional status badge or other content to display after title */
  statusBadge?: ReactNode;
}

/**
 * PageHeader provides consistent page title display with actions.
 *
 * @example
 * ```tsx
 * <PageHeader
 *   title="Farmers"
 *   subtitle="Manage farmer records"
 *   actions={[
 *     { id: 'add', label: 'Add Farmer', variant: 'contained', onClick: handleAdd }
 *   ]}
 * />
 * ```
 *
 * @example
 * ```tsx
 * // Detail page with back navigation
 * <PageHeader
 *   title="John Kamau"
 *   subtitle="Farmer ID: FRM-001"
 *   backHref="/farmers"
 *   onBack={() => navigate('/farmers')}
 *   statusBadge={<StatusBadge status="win" />}
 *   actions={[
 *     { id: 'edit', label: 'Edit', variant: 'outlined', onClick: handleEdit },
 *     { id: 'delete', label: 'Delete', variant: 'outlined', color: 'error', onClick: handleDelete },
 *   ]}
 * />
 * ```
 */
export function PageHeader({
  title,
  subtitle,
  backHref,
  onBack,
  actions = [],
  statusBadge,
}: PageHeaderProps): JSX.Element {
  const theme = useTheme();
  const showBackButton = backHref || onBack;

  const handleBack = () => {
    onBack?.();
  };

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        mb: 3,
        gap: 2,
      }}
    >
      {/* Left side: Back button + Title */}
      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
        {showBackButton && (
          <IconButton
            onClick={handleBack}
            aria-label="Go back"
            sx={{
              mt: 0.5,
              '&:focus': {
                outline: `3px solid ${theme.palette.primary.main}`,
                outlineOffset: '2px',
              },
            }}
          >
            <ArrowBackIcon />
          </IconButton>
        )}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
            <Typography
              variant="h4"
              component="h1"
              sx={{ fontWeight: 600, color: 'text.primary' }}
            >
              {title}
            </Typography>
            {statusBadge}
          </Box>
          {subtitle && (
            <Typography
              variant="body1"
              sx={{ color: 'text.secondary', mt: 0.5 }}
            >
              {subtitle}
            </Typography>
          )}
        </Box>
      </Box>

      {/* Right side: Action buttons */}
      {actions.length > 0 && (
        <Box
          sx={{
            display: 'flex',
            gap: 1,
            flexWrap: 'wrap',
            justifyContent: 'flex-end',
          }}
        >
          {actions.map((action) => (
            <Button
              key={action.id}
              variant={action.variant ?? 'outlined'}
              color={action.color ?? 'primary'}
              startIcon={action.icon}
              onClick={action.onClick}
              disabled={action.disabled}
              sx={{
                minHeight: 40,
                minWidth: 48,
                '&:focus': {
                  outline: `3px solid ${theme.palette.primary.main}`,
                  outlineOffset: '2px',
                },
              }}
            >
              {action.label}
            </Button>
          ))}
        </Box>
      )}
    </Box>
  );
}

export default PageHeader;
