/**
 * Authentication types for @fp/auth library.
 *
 * These types match the BFF TokenClaims model exactly per ADR-003.
 * @see services/bff/src/bff/api/schemas/auth.py
 */

/**
 * User type matching BFF TokenClaims exactly.
 *
 * Contains all user attributes extracted from the JWT token.
 * Used for authorization decisions throughout the frontend.
 */
export interface User {
  /** User ID (Azure AD object ID or mock user ID) */
  sub: string;
  /** User email address */
  email: string;
  /** User display name */
  name: string;
  /** Primary role (platform_admin, factory_owner, factory_manager, etc.) */
  role: string;
  /** Single factory assignment (for most users) */
  factory_id: string | null;
  /** Multiple factory assignments (for owners) */
  factory_ids: string[];
  /** Collection point assignment (for clerks) */
  collection_point_id: string | null;
  /** Region assignments (for regulators) */
  region_ids: string[];
  /** List of computed permissions */
  permissions: string[];
}

/**
 * Mock user type for development authentication.
 *
 * Extends User with additional mock-specific metadata.
 */
export interface MockUser extends User {
  /** Unique mock user identifier */
  id: string;
}

/**
 * Auth context value exposed by useAuth hook.
 */
export interface AuthContextValue {
  /** Whether the user is currently authenticated */
  isAuthenticated: boolean;
  /** Current user object (null if not authenticated) */
  user: User | null;
  /** Trigger login flow (shows selector in mock mode, redirects in B2C mode) */
  login: () => void;
  /** Clear session and tokens */
  logout: () => Promise<void>;
  /** Get access token for API calls */
  getAccessToken: () => Promise<string>;
  /** True while checking auth state on initial load */
  isLoading: boolean;
  /** Show login selector in mock mode */
  showLoginSelector: boolean;
  /** Select a mock user (mock mode only) */
  selectMockUser: (user: MockUser) => Promise<void>;
}

/**
 * Props for AuthProvider component.
 */
export interface AuthProviderProps {
  /** Child components to wrap */
  children: React.ReactNode;
}

/**
 * Props for ProtectedRoute component.
 */
export interface ProtectedRouteProps {
  /** Content to render when authorized */
  children: React.ReactNode;
  /** Required roles (user must have one of these) */
  roles?: string[];
  /** Required permissions (user must have all of these) */
  permissions?: string[];
  /** Custom loading component */
  fallback?: React.ReactNode;
  /** Custom access denied component */
  accessDenied?: React.ReactNode;
}

/**
 * Auth provider type for runtime selection.
 */
export type AuthProviderType = 'mock' | 'azure-b2c';
