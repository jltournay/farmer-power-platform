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
 *
 * Security: Production deployments MUST set VITE_AUTH_PROVIDER=azure-b2c.
 * The mock provider should only be used in development.
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
 * Main authentication provider component.
 *
 * Automatically selects the appropriate provider based on VITE_AUTH_PROVIDER:
 * - 'mock': Development mode with mock users (default when not set)
 * - 'azure-b2c': Production mode with Azure AD B2C
 *
 * IMPORTANT: Production deployments MUST set VITE_AUTH_PROVIDER=azure-b2c
 * to ensure real authentication is used.
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

  // Select the appropriate provider based on environment configuration
  if (providerType === 'azure-b2c') {
    return <AzureB2CAuthProvider>{children}</AzureB2CAuthProvider>;
  }

  return <MockAuthProvider>{children}</MockAuthProvider>;
}
