/**
 * Azure AD B2C authentication provider stub.
 *
 * Full implementation will be added in Story 0.5.8.
 * This stub exists to maintain the provider architecture.
 *
 * @see _bmad-output/sprint-artifacts/0-5-8-azure-ad-b2c-configuration.md (future)
 */

import { useMemo } from 'react';
import { AuthContext } from '../context/AuthContext';
import type { AuthProviderProps, AuthContextValue } from '../types';

/**
 * Azure AD B2C authentication provider component (STUB).
 *
 * This is a placeholder implementation. Full B2C integration
 * will be implemented in Story 0.5.8 for production deployment.
 *
 * @throws Error when any auth method is called
 *
 * @example
 * ```tsx
 * // This will throw - use MockAuthProvider for development
 * <AzureB2CAuthProvider>
 *   <App />
 * </AzureB2CAuthProvider>
 * ```
 */
export function AzureB2CAuthProvider({ children }: AuthProviderProps) {
  const notImplementedError = () => {
    throw new Error(
      'Azure AD B2C authentication is not yet implemented. ' +
        'Use VITE_AUTH_PROVIDER=mock for development. ' +
        'See Story 0.5.8 for production B2C implementation.'
    );
  };

  // Stub context value that throws on any method call
  const contextValue: AuthContextValue = useMemo(
    () => ({
      isAuthenticated: false,
      user: null,
      login: notImplementedError,
      logout: async () => {
        notImplementedError();
      },
      getAccessToken: async () => {
        notImplementedError();
        return ''; // Never reached
      },
      isLoading: false,
      showLoginSelector: false,
      selectMockUser: async () => {
        throw new Error('selectMockUser is not available in B2C mode');
      },
    }),
    []
  );

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
}
