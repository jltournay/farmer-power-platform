/**
 * TrendIndicator Component
 *
 * Shows quality trajectory with up/down/stable indicators
 *
 * Accessibility:
 * - Uses icon + text + color (not color alone)
 * - aria-label describes the trend direction and value
 */

import { styled } from '@mui/material/styles';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import TrendingFlatIcon from '@mui/icons-material/TrendingFlat';
import { colors } from '../../theme/palette';

/** Trend direction */
export type TrendDirection = 'up' | 'down' | 'stable';

/** TrendIndicator component props */
export interface TrendIndicatorProps {
  /** Trend direction */
  direction: TrendDirection;
  /** Percentage change value */
  value: number;
  /** Optional period description (e.g., "vs last week") */
  period?: string;
  /** Size variant */
  size?: 'small' | 'medium';
}

/** Color mapping for each direction */
const directionColors: Record<TrendDirection, string> = {
  up: colors.primary, // Forest Green - positive
  down: colors.error, // Warm Red - negative
  stable: colors.neutral, // Slate Gray - neutral
};

/** Icon mapping for each direction */
const DirectionIcons: Record<TrendDirection, typeof ArrowUpwardIcon> = {
  up: ArrowUpwardIcon,
  down: ArrowDownwardIcon,
  stable: TrendingFlatIcon,
};

/** Size configurations */
const sizes = {
  small: {
    iconSize: 16,
    fontSize: '0.75rem',
    gap: '2px',
  },
  medium: {
    iconSize: 20,
    fontSize: '0.875rem',
    gap: '4px',
  },
} as const;

interface StyledContainerProps {
  trendDirection: TrendDirection;
  indicatorSize: 'small' | 'medium';
}

const StyledContainer = styled(Box, {
  shouldForwardProp: (prop) =>
    prop !== 'trendDirection' && prop !== 'indicatorSize',
})<StyledContainerProps>(({ trendDirection, indicatorSize }) => {
  const color = directionColors[trendDirection];
  const sizeConfig = sizes[indicatorSize];

  return {
    display: 'inline-flex',
    alignItems: 'center',
    gap: sizeConfig.gap,
    color,
    fontSize: sizeConfig.fontSize,
    fontWeight: 500,
  };
});

/**
 * TrendIndicator displays quality trajectory
 *
 * @example
 * ```tsx
 * <TrendIndicator direction="up" value={12} />
 * <TrendIndicator direction="down" value={5} period="vs last week" />
 * <TrendIndicator direction="stable" value={0} size="small" />
 * ```
 */
export function TrendIndicator({
  direction,
  value,
  period,
  size = 'medium',
}: TrendIndicatorProps): JSX.Element {
  const Icon = DirectionIcons[direction];
  const sizeConfig = sizes[size];

  // Format value with sign
  const formattedValue =
    direction === 'up'
      ? `+${Math.abs(value)}%`
      : direction === 'down'
        ? `-${Math.abs(value)}%`
        : `${value}%`;

  const ariaLabel = `Quality trend: ${direction} ${Math.abs(value)}%${period ? ` ${period}` : ''}`;

  return (
    <StyledContainer
      trendDirection={direction}
      indicatorSize={size}
      role="img"
      aria-label={ariaLabel}
    >
      <Icon
        sx={{ fontSize: sizeConfig.iconSize }}
        aria-hidden="true"
      />
      <Typography
        component="span"
        sx={{
          fontSize: 'inherit',
          fontWeight: 'inherit',
          lineHeight: 1,
        }}
      >
        {formattedValue}
      </Typography>
      {period && (
        <Typography
          component="span"
          sx={{
            fontSize: 'inherit',
            fontWeight: 400,
            color: colors.neutral,
            lineHeight: 1,
          }}
        >
          {period}
        </Typography>
      )}
    </StyledContainer>
  );
}

export default TrendIndicator;
