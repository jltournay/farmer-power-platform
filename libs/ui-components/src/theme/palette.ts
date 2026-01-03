/**
 * Farmer Power Platform Color Palette
 *
 * Design tokens from _bmad-output/ux-design-specification/design-system-foundation.md
 */

/** Primary brand colors */
export const colors = {
  /** Forest Green - Primary brand color */
  primary: '#1B4332',
  /** Earth Brown - Secondary brand color */
  secondary: '#5C4033',
  /** Harvest Gold - Warning states, WATCH category */
  warning: '#D4A03A',
  /** Warm Red - Error states, ACTION category */
  error: '#C1292E',
  /** Forest Green - Success states, WIN category */
  success: '#1B4332',
  /** Warm White - Default background */
  backgroundDefault: '#FFFDF9',
  /** Pure White - Paper/card background */
  backgroundPaper: '#FFFFFF',
  /** Slate Gray - Neutral/stable indicators */
  neutral: '#64748B',
} as const;

/** Status-specific color tokens for StatusBadge component */
export const statusColors = {
  win: {
    /** Light green background */
    bg: '#D8F3DC',
    /** Forest green text */
    text: '#1B4332',
    /** Checkmark icon */
    icon: '\u2705',
  },
  watch: {
    /** Light amber background */
    bg: '#FFF8E7',
    /** Harvest gold text */
    text: '#D4A03A',
    /** Warning icon */
    icon: '\u26A0\uFE0F',
  },
  action: {
    /** Light red background */
    bg: '#FFE5E5',
    /** Warm red text */
    text: '#C1292E',
    /** Red circle icon */
    icon: '\uD83D\uDD34',
  },
} as const;

/** Status type for type safety */
export type StatusType = keyof typeof statusColors;
