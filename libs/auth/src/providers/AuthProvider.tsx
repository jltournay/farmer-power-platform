/**
 * Main authentication provider wrapper.
 *
 * Selects the appropriate auth provider based on environment configuration.
 * - VITE_AUTH_PROVIDER=mock: Uses MockAuthProvider
 * - VITE_AUTH_PROVIDER=azure-b2c: Uses AzureB2CAuthProvider
 */

import type { AuthProviderProps, AuthProviderType } from '../types';
import { MockAuthProvider } from './MockAuthProvider';
import { AzureB2CAuthProvider } from './AzureB2CAuthProvider';

/**
 * Get the configured auth provider type from environment.
 */
function getAuthProviderType(): AuthProviderType {
  const provider = import.meta.env.VITE_AUTH_PROVIDER;
  if (provider === 'azure-b2c') {
    return 'azure-b2c';
  }
  // Default to mock for development
  return 'mock';
}

/**
 * Check if running in production environment.
 */
function isProduction(): boolean {
  return import.meta.env.PROD === true;
}

/**
 * Main authentication provider component.
 *
 * Automatically selects the appropriate provider based on VITE_AUTH_PROVIDER:
 * - 'mock': Development mode with mock users
 * - 'azure-b2c': Production mode with Azure AD B2C
 *
 * Security: Mock provider is blocked in production builds.
 *
 * @example
 * ```tsx
 * // In App.tsx
 * import { AuthProvider } from '@fp/auth';
 *
 * function App() {
 *   return (
 *     <AuthProvider>
 *       <Router>
 *         <Routes />
 *       </Router>
 *     </AuthProvider>
 *   );
 * }
 * ```
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const providerType = getAuthProviderType();

  // Security guard: Block mock provider in production
  if (providerType === 'mock' && isProduction()) {
    throw new Error(
      'Mock authentication provider cannot be used in production. ' +
        'Set VITE_AUTH_PROVIDER=azure-b2c for production builds.'
    );
  }

  // Select the appropriate provider
  if (providerType === 'azure-b2c') {
    return <AzureB2CAuthProvider>{children}</AzureB2CAuthProvider>;
  }

  return <MockAuthProvider>{children}</MockAuthProvider>;
}
