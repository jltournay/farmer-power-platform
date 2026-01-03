/**
 * ProtectedRoute component for route-level authorization.
 *
 * Guards routes based on authentication status, roles, and permissions.
 */

import { useEffect, type ReactNode } from 'react';
import { useAuth } from '../hooks/useAuth';
import type { ProtectedRouteProps } from '../types';

/**
 * Default loading component.
 */
function DefaultLoading() {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '200px',
        color: '#6b7280',
      }}
    >
      Loading...
    </div>
  );
}

/**
 * Default access denied component.
 */
function DefaultAccessDenied() {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '200px',
        color: '#dc2626',
        gap: '8px',
      }}
    >
      <div style={{ fontSize: '24px' }}>Access Denied</div>
      <div style={{ fontSize: '14px', color: '#6b7280' }}>
        You don&apos;t have permission to access this page.
      </div>
    </div>
  );
}

/**
 * Protected route component for authorization.
 *
 * Wraps content that requires authentication and/or specific roles/permissions.
 *
 * Features:
 * - Redirects to login if not authenticated
 * - Shows access denied if authenticated but lacks required role/permission
 * - Shows loading state during auth check
 * - Platform admin bypasses all role/permission checks
 *
 * @example
 * ```tsx
 * // Require authentication only
 * <ProtectedRoute>
 *   <Dashboard />
 * </ProtectedRoute>
 *
 * // Require specific roles
 * <ProtectedRoute roles={['factory_manager', 'factory_owner']}>
 *   <FactoryDashboard />
 * </ProtectedRoute>
 *
 * // Require specific permissions
 * <ProtectedRoute permissions={['farmers:write']}>
 *   <FarmerEditor />
 * </ProtectedRoute>
 *
 * // Custom loading/error components
 * <ProtectedRoute
 *   roles={['platform_admin']}
 *   fallback={<Spinner />}
 *   accessDenied={<CustomErrorPage />}
 * >
 *   <AdminPanel />
 * </ProtectedRoute>
 * ```
 */
export function ProtectedRoute({
  children,
  roles,
  permissions,
  fallback,
  accessDenied,
}: ProtectedRouteProps): ReactNode {
  const { isAuthenticated, isLoading, user, login } = useAuth();

  // Trigger login in useEffect to avoid React state update during render
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      login();
    }
  }, [isLoading, isAuthenticated, login]);

  // Show loading state while checking auth
  if (isLoading) {
    return fallback ?? <DefaultLoading />;
  }

  // Show loading while redirecting to login
  if (!isAuthenticated) {
    return fallback ?? <DefaultLoading />;
  }

  // Platform admin bypasses all checks
  const isPlatformAdmin = user?.role === 'platform_admin';

  // Check role access
  if (roles && roles.length > 0 && !isPlatformAdmin) {
    const hasRole = user?.role && roles.includes(user.role);
    if (!hasRole) {
      return accessDenied ?? <DefaultAccessDenied />;
    }
  }

  // Check permission access
  if (permissions && permissions.length > 0 && !isPlatformAdmin) {
    const userPermissions = user?.permissions ?? [];
    const hasAllPermissions = permissions.every(
      (p) => userPermissions.includes(p) || userPermissions.includes('*')
    );
    if (!hasAllPermissions) {
      return accessDenied ?? <DefaultAccessDenied />;
    }
  }

  return <>{children}</>;
}
