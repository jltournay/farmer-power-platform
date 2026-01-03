/**
 * StatusBadge Component
 *
 * Displays farmer quality status with WIN/WATCH/ACTION variants
 *
 * Accessibility:
 * - role="status" for screen readers
 * - aria-label describes the quality status
 * - 48px minimum touch target
 * - Focus ring: 3px Forest Green outline
 */

import { styled } from '@mui/material/styles';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import type { StatusType } from '../../theme/palette';
import { statusColors, colors } from '../../theme/palette';

/** StatusBadge component props */
export interface StatusBadgeProps {
  /** Status variant: win, watch, or action */
  status: StatusType;
  /** Custom label override (default: "WIN", "WATCH", "ACTION NEEDED") */
  label?: string;
  /** Optional count to display (for action strip counts) */
  count?: number;
  /** Click handler for interactive badges */
  onClick?: () => void;
  /** Size variant */
  size?: 'small' | 'medium' | 'large';
}

/** Default labels for each status */
const defaultLabels: Record<StatusType, string> = {
  win: 'WIN',
  watch: 'WATCH',
  action: 'ACTION NEEDED',
};

/** Size configurations */
const sizes = {
  small: {
    padding: '4px 8px',
    fontSize: '0.75rem',
    iconSize: '0.875rem',
    minHeight: '24px',
  },
  medium: {
    padding: '6px 12px',
    fontSize: '0.875rem',
    iconSize: '1rem',
    minHeight: '32px',
  },
  large: {
    padding: '8px 16px',
    fontSize: '1rem',
    iconSize: '1.25rem',
    minHeight: '40px',
  },
} as const;

interface StyledBadgeProps {
  status: StatusType;
  isClickable: boolean;
  badgeSize: 'small' | 'medium' | 'large';
}

const StyledBadge = styled(Box, {
  shouldForwardProp: (prop) =>
    prop !== 'status' && prop !== 'isClickable' && prop !== 'badgeSize',
})<StyledBadgeProps>(({ status, isClickable, badgeSize }) => {
  const statusColor = statusColors[status];
  const sizeConfig = sizes[badgeSize];

  return {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: sizeConfig.padding,
    minHeight: sizeConfig.minHeight,
    minWidth: '48px', // 48px minimum touch target
    backgroundColor: statusColor.bg,
    color: statusColor.text,
    borderRadius: '16px',
    fontWeight: 500,
    fontSize: sizeConfig.fontSize,
    cursor: isClickable ? 'pointer' : 'default',
    transition: 'all 0.2s ease-in-out',
    border: '2px solid transparent',
    userSelect: 'none',

    '&:focus': {
      outline: `3px solid ${colors.primary}`,
      outlineOffset: '2px',
    },

    '&:focus-visible': {
      outline: `3px solid ${colors.primary}`,
      outlineOffset: '2px',
    },

    ...(isClickable && {
      '&:hover': {
        filter: 'brightness(0.95)',
        transform: 'translateY(-1px)',
      },
      '&:active': {
        transform: 'translateY(0)',
      },
    }),
  };
});

const IconSpan = styled('span')({
  display: 'inline-flex',
  alignItems: 'center',
  lineHeight: 1,
});

const CountBadge = styled(Box)<{ status: StatusType }>(({ status }) => ({
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  minWidth: '20px',
  height: '20px',
  padding: '0 6px',
  borderRadius: '10px',
  backgroundColor: statusColors[status].text,
  color: statusColors[status].bg,
  fontSize: '0.75rem',
  fontWeight: 600,
}));

/**
 * StatusBadge displays farmer quality status
 *
 * @example
 * ```tsx
 * <StatusBadge status="win" />
 * <StatusBadge status="watch" label="Monitoring" />
 * <StatusBadge status="action" count={7} onClick={() => filterByAction()} />
 * ```
 */
export function StatusBadge({
  status,
  label,
  count,
  onClick,
  size = 'medium',
}: StatusBadgeProps): JSX.Element {
  const displayLabel = label ?? defaultLabels[status];
  const statusColor = statusColors[status];
  const isClickable = onClick !== undefined;

  const handleClick = () => {
    if (onClick) {
      onClick();
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (onClick && (event.key === 'Enter' || event.key === ' ')) {
      event.preventDefault();
      onClick();
    }
  };

  return (
    <StyledBadge
      role="status"
      aria-label={`Quality status: ${status}`}
      status={status}
      isClickable={isClickable}
      badgeSize={size}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      tabIndex={isClickable ? 0 : undefined}
    >
      <IconSpan aria-hidden="true">{statusColor.icon}</IconSpan>
      <Typography
        component="span"
        sx={{
          fontSize: 'inherit',
          fontWeight: 'inherit',
          lineHeight: 1,
        }}
      >
        {displayLabel}
      </Typography>
      {count !== undefined && count > 0 && (
        <CountBadge status={status} aria-label={`${count} items`}>
          {count}
        </CountBadge>
      )}
    </StyledBadge>
  );
}

export default StatusBadge;
