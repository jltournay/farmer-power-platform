/**
 * usePermission hook for checking user permissions.
 *
 * Provides a simple way to check if the current user has a specific permission.
 */

import { useAuth } from './useAuth';

/**
 * Hook to check if the current user has a specific permission.
 *
 * Checks the permissions array in the user's claims.
 * Returns true for platform_admin role (wildcard "*" permission).
 * Returns false if not authenticated.
 *
 * @param permission - Permission string to check (e.g., "farmers:read")
 * @returns True if user has the permission
 *
 * @example
 * ```tsx
 * function EditButton() {
 *   const canEdit = usePermission('sms_templates:write');
 *
 *   if (!canEdit) {
 *     return null;
 *   }
 *
 *   return <button>Edit Template</button>;
 * }
 * ```
 *
 * @example
 * ```tsx
 * function AdminPanel() {
 *   // Platform admin has wildcard "*" permission
 *   const isAdmin = usePermission('admin:access');
 *
 *   if (!isAdmin) {
 *     return <div>Admin access required</div>;
 *   }
 *
 *   return <AdminDashboard />;
 * }
 * ```
 */
export function usePermission(permission: string): boolean {
  const { isAuthenticated, user } = useAuth();

  // Not authenticated = no permissions
  if (!isAuthenticated || !user) {
    return false;
  }

  // Wildcard permission grants all access (platform_admin)
  if (user.permissions.includes('*')) {
    return true;
  }

  // Check if user has the specific permission
  return user.permissions.includes(permission);
}

/**
 * Hook to check if the current user has any of the specified permissions.
 *
 * @param permissions - Array of permission strings
 * @returns True if user has at least one of the permissions
 *
 * @example
 * ```tsx
 * function ActionButton() {
 *   const canAct = useHasAnyPermission(['farmers:write', 'farmers:delete']);
 *
 *   if (!canAct) {
 *     return null;
 *   }
 *
 *   return <button>Take Action</button>;
 * }
 * ```
 */
export function useHasAnyPermission(permissions: string[]): boolean {
  const { isAuthenticated, user } = useAuth();

  if (!isAuthenticated || !user) {
    return false;
  }

  if (user.permissions.includes('*')) {
    return true;
  }

  return permissions.some((permission) => user.permissions.includes(permission));
}

/**
 * Hook to check if the current user has all of the specified permissions.
 *
 * @param permissions - Array of permission strings
 * @returns True if user has all the permissions
 *
 * @example
 * ```tsx
 * function AdvancedPanel() {
 *   const hasAll = useHasAllPermissions(['settings:read', 'settings:write']);
 *
 *   if (!hasAll) {
 *     return <div>Insufficient permissions</div>;
 *   }
 *
 *   return <SettingsEditor />;
 * }
 * ```
 */
export function useHasAllPermissions(permissions: string[]): boolean {
  const { isAuthenticated, user } = useAuth();

  if (!isAuthenticated || !user) {
    return false;
  }

  if (user.permissions.includes('*')) {
    return true;
  }

  return permissions.every((permission) => user.permissions.includes(permission));
}
