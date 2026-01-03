/**
 * LeafTypeTag Component
 *
 * Displays leaf type with TBK color coding and coaching tooltips
 *
 * Accessibility:
 * - Tooltip accessible via focus AND hover
 * - role="button" when clickable
 * - Keyboard: Enter/Space triggers onClick
 */

import { useState } from 'react';
import { styled } from '@mui/material/styles';
import Box from '@mui/material/Box';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import { colors, statusColors } from '../../theme/palette';

/** Supported leaf types from TBK grading model */
export type LeafType = 'three_plus_leaves_bud' | 'coarse_leaf' | 'hard_banji';

/** Supported languages */
export type SupportedLanguage = 'en' | 'sw';

/** LeafTypeTag component props */
export interface LeafTypeTagProps {
  /** Leaf type to display */
  leafType: LeafType;
  /** Display language */
  language?: SupportedLanguage;
  /** Whether to show coaching tooltip */
  showTooltip?: boolean;
  /** Click handler (opens coaching card) */
  onClick?: () => void;
}

/** Leaf type labels in English and Swahili */
const leafLabels: Record<LeafType, Record<SupportedLanguage, string>> = {
  three_plus_leaves_bud: {
    en: '3+ leaves',
    sw: 'majani 3+',
  },
  coarse_leaf: {
    en: 'coarse leaf',
    sw: 'majani magumu',
  },
  hard_banji: {
    en: 'hard banji',
    sw: 'banji ngumu',
  },
};

/** Coaching tips in English and Swahili */
const coachingTips: Record<LeafType, Record<SupportedLanguage, string>> = {
  three_plus_leaves_bud: {
    en: 'Pick only 2 leaves + bud for best quality',
    sw: 'Chuma majani 2 na chipukizi tu kwa ubora bora',
  },
  coarse_leaf: {
    en: 'Avoid old/mature leaves - pick young leaves',
    sw: 'Epuka majani mazee - chuma majani machanga',
  },
  hard_banji: {
    en: 'Harvest earlier in morning for softer stems',
    sw: 'Vuna mapema asubuhi kwa mabua laini',
  },
};

/** Color coding for each leaf type (all are rejection categories) */
const leafColors: Record<LeafType, { bg: string; text: string }> = {
  three_plus_leaves_bud: statusColors.action,
  coarse_leaf: statusColors.action,
  hard_banji: statusColors.watch, // Less severe - conditional rejection
};

interface StyledTagProps {
  leafType: LeafType;
  isClickable: boolean;
}

const StyledTag = styled(Box, {
  shouldForwardProp: (prop) => prop !== 'leafType' && prop !== 'isClickable',
})<StyledTagProps>(({ leafType, isClickable }) => {
  const colorConfig = leafColors[leafType];

  return {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '4px 12px',
    backgroundColor: colorConfig.bg,
    color: colorConfig.text,
    borderRadius: '16px',
    fontSize: '0.875rem',
    fontWeight: 500,
    cursor: isClickable ? 'pointer' : 'default',
    transition: 'all 0.2s ease-in-out',
    minHeight: '28px',
    minWidth: '48px', // 48px minimum touch target

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

const TooltipContent = styled(Box)({
  padding: '8px',
  maxWidth: '220px',
});

/**
 * LeafTypeTag displays leaf type with coaching tooltips
 *
 * @example
 * ```tsx
 * <LeafTypeTag leafType="three_plus_leaves_bud" />
 * <LeafTypeTag leafType="coarse_leaf" language="sw" />
 * <LeafTypeTag leafType="hard_banji" onClick={() => openCoachingCard()} />
 * ```
 */
export function LeafTypeTag({
  leafType,
  language = 'en',
  showTooltip = true,
  onClick,
}: LeafTypeTagProps): JSX.Element {
  const [tooltipOpen, setTooltipOpen] = useState(false);
  const isClickable = onClick !== undefined;

  const label = leafLabels[leafType][language];
  const tip = coachingTips[leafType][language];

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

  // For accessibility: show tooltip on focus
  const handleFocus = () => {
    if (showTooltip) {
      setTooltipOpen(true);
    }
  };

  const handleBlur = () => {
    setTooltipOpen(false);
  };

  const tagElement = (
    <StyledTag
      role={isClickable ? 'button' : undefined}
      aria-label={showTooltip ? `${label}: ${tip}` : label}
      leafType={leafType}
      isClickable={isClickable}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      onFocus={handleFocus}
      onBlur={handleBlur}
      tabIndex={isClickable || showTooltip ? 0 : undefined}
    >
      <Typography
        component="span"
        sx={{
          fontSize: 'inherit',
          fontWeight: 'inherit',
          lineHeight: 1,
        }}
      >
        {label}
      </Typography>
    </StyledTag>
  );

  if (showTooltip) {
    return (
      <Tooltip
        open={tooltipOpen}
        onOpen={() => setTooltipOpen(true)}
        onClose={() => setTooltipOpen(false)}
        title={
          <TooltipContent>
            <Typography variant="body2" fontWeight={500}>
              {label}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {tip}
            </Typography>
          </TooltipContent>
        }
        arrow
        enterTouchDelay={0}
        leaveTouchDelay={3000}
      >
        {tagElement}
      </Tooltip>
    );
  }

  return tagElement;
}

export default LeafTypeTag;
