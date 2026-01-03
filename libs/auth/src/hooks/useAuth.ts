/**
 * useAuth hook for accessing authentication context.
 *
 * Provides access to auth state and methods in any component.
 */

import { useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import type { AuthContextValue } from '../types';

/**
 * Hook to access authentication context.
 *
 * Provides access to:
 * - isAuthenticated: Whether user is logged in
 * - user: Current user object (null if not authenticated)
 * - login(): Trigger login flow
 * - logout(): Clear session
 * - getAccessToken(): Get token for API calls
 * - isLoading: True while checking initial auth state
 *
 * @returns AuthContextValue with all auth state and methods
 *
 * @throws Error if used outside of AuthProvider
 *
 * @example
 * ```tsx
 * function Header() {
 *   const { isAuthenticated, user, logout } = useAuth();
 *
 *   if (!isAuthenticated) {
 *     return <LoginButton />;
 *   }
 *
 *   return (
 *     <div>
 *       Welcome, {user.name}
 *       <button onClick={logout}>Logout</button>
 *     </div>
 *   );
 * }
 * ```
 */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }

  return context;
}
