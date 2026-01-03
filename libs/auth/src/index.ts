/**
 * @fp/auth - Shared authentication library for Farmer Power Platform
 *
 * Provides authentication with swappable providers:
 * - Mock: Development mode with predefined personas
 * - Azure AD B2C: Production mode (Story 0.5.8)
 *
 * @packageDocumentation
 */

// Types
export type {
  User,
  MockUser,
  AuthContextValue,
  AuthProviderProps,
  ProtectedRouteProps,
  AuthProviderType,
} from './types';

// Providers
export { AuthProvider, MockAuthProvider, AzureB2CAuthProvider } from './providers';

// Context
export { AuthContext } from './context';

// Hooks
export { useAuth } from './hooks/useAuth';
export { usePermission, useHasAnyPermission, useHasAllPermissions } from './hooks/usePermission';

// Components
export { MockLoginSelector, ProtectedRoute } from './components';

// Mock utilities (for testing and development)
export { MOCK_USERS, getMockUserById, getMockUserByRole } from './mock/users';
export { generateMockToken, decodeToken, isTokenExpired } from './mock/jwt';
