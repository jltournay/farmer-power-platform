/**
 * Authentication context for @fp/auth library.
 *
 * Provides auth state and methods to all child components.
 */

import { createContext } from 'react';
import type { AuthContextValue } from '../types';

/**
 * Default auth context value (not authenticated).
 */
const defaultContextValue: AuthContextValue = {
  isAuthenticated: false,
  user: null,
  login: () => {
    throw new Error('AuthProvider not initialized');
  },
  logout: async () => {
    throw new Error('AuthProvider not initialized');
  },
  getAccessToken: async () => {
    throw new Error('AuthProvider not initialized');
  },
  isLoading: true,
  showLoginSelector: false,
  selectMockUser: async () => {
    throw new Error('AuthProvider not initialized');
  },
};

/**
 * Auth context for sharing authentication state.
 *
 * Use the useAuth hook to access this context in components.
 */
export const AuthContext = createContext<AuthContextValue>(defaultContextValue);
