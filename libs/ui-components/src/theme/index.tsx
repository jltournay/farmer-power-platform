/**
 * Farmer Power Platform Theme
 *
 * Material UI v6 theme with Farmer Power color palette and typography
 */

import { createTheme, ThemeProvider as MuiThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import type { ReactNode } from 'react';
import { colors } from './palette';
import { typography } from './typography';

/** Farmer Power MUI theme */
export const farmerPowerTheme = createTheme({
  palette: {
    primary: {
      main: colors.primary,
    },
    secondary: {
      main: colors.secondary,
    },
    warning: {
      main: colors.warning,
    },
    error: {
      main: colors.error,
    },
    success: {
      main: colors.success,
    },
    background: {
      default: colors.backgroundDefault,
      paper: colors.backgroundPaper,
    },
  },
  typography,
  shape: {
    borderRadius: 6,
  },
  spacing: 8, // 8px grid system
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 6,
          padding: '8px 16px',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 16,
        },
      },
    },
  },
});

/** Theme provider props */
interface ThemeProviderProps {
  children: ReactNode;
}

/**
 * ThemeProvider wrapper component
 *
 * Wraps children with Farmer Power theme and CSS baseline
 */
export function ThemeProvider({ children }: ThemeProviderProps): JSX.Element {
  return (
    <MuiThemeProvider theme={farmerPowerTheme}>
      <CssBaseline />
      {children}
    </MuiThemeProvider>
  );
}

// Re-export palette utilities
export { colors, statusColors } from './palette';
export type { StatusType } from './palette';
