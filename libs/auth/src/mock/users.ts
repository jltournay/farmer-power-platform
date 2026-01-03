/**
 * Mock user personas for development authentication.
 *
 * These personas match ADR-003 specification exactly.
 * @see _bmad-output/architecture/adr/ADR-003-identity-access-management.md
 */

import type { MockUser } from '../types';

/**
 * Factory manager permissions.
 * Can view farmers, quality events, diagnoses, and action plans for their factory.
 */
const FACTORY_MANAGER_PERMISSIONS = [
  'farmers:read',
  'quality_events:read',
  'diagnoses:read',
  'action_plans:read',
];

/**
 * Factory owner permissions.
 * Inherits manager permissions plus write access to policies and settings.
 */
const FACTORY_OWNER_PERMISSIONS = [
  ...FACTORY_MANAGER_PERMISSIONS,
  'payment_policies:write',
  'factory_settings:write',
];

/**
 * Platform admin permissions.
 * Wildcard access to all resources.
 */
const PLATFORM_ADMIN_PERMISSIONS = ['*'];

/**
 * Registration clerk permissions.
 * Can create new farmers at collection points.
 */
const REGISTRATION_CLERK_PERMISSIONS = ['farmers:create'];

/**
 * Regulator permissions.
 * Read-only access to regional and national statistics.
 */
const REGULATOR_PERMISSIONS = ['national_stats:read', 'regional_stats:read'];

/**
 * Mock users available for development authentication.
 *
 * These personas represent the different roles in the system:
 * - Factory Manager: Day-to-day operations at a single factory
 * - Factory Owner: Business oversight across multiple factories
 * - Platform Admin: Full system access
 * - Registration Clerk: Farmer onboarding at collection points
 * - Regulator: Government oversight and reporting
 */
export const MOCK_USERS: MockUser[] = [
  {
    id: 'mock-manager-001',
    sub: 'mock-manager-001',
    email: 'jane.mwangi@factory.example.com',
    name: 'Jane Mwangi',
    role: 'factory_manager',
    factory_id: 'KEN-FAC-001',
    factory_ids: ['KEN-FAC-001'],
    collection_point_id: null,
    region_ids: [],
    permissions: FACTORY_MANAGER_PERMISSIONS,
  },
  {
    id: 'mock-owner-001',
    sub: 'mock-owner-001',
    email: 'john.ochieng@factory.example.com',
    name: 'John Ochieng',
    role: 'factory_owner',
    factory_id: 'KEN-FAC-001',
    factory_ids: ['KEN-FAC-001', 'KEN-FAC-002'],
    collection_point_id: null,
    region_ids: [],
    permissions: FACTORY_OWNER_PERMISSIONS,
  },
  {
    id: 'mock-admin-001',
    sub: 'mock-admin-001',
    email: 'admin@farmerpower.example.com',
    name: 'Admin User',
    role: 'platform_admin',
    factory_id: null,
    factory_ids: [],
    collection_point_id: null,
    region_ids: [],
    permissions: PLATFORM_ADMIN_PERMISSIONS,
  },
  {
    id: 'mock-clerk-001',
    sub: 'mock-clerk-001',
    email: 'mary.wanjiku@factory.example.com',
    name: 'Mary Wanjiku',
    role: 'registration_clerk',
    factory_id: 'KEN-FAC-001',
    factory_ids: ['KEN-FAC-001'],
    collection_point_id: 'KEN-CP-001',
    region_ids: [],
    permissions: REGISTRATION_CLERK_PERMISSIONS,
  },
  {
    id: 'mock-regulator-001',
    sub: 'mock-regulator-001',
    email: 'inspector@tbk.go.ke',
    name: 'TBK Inspector',
    role: 'regulator',
    factory_id: null,
    factory_ids: [],
    collection_point_id: null,
    region_ids: ['nandi', 'kericho'],
    permissions: REGULATOR_PERMISSIONS,
  },
];

/**
 * Get a mock user by ID.
 */
export function getMockUserById(id: string): MockUser | undefined {
  return MOCK_USERS.find((user) => user.id === id);
}

/**
 * Get a mock user by role.
 */
export function getMockUserByRole(role: string): MockUser | undefined {
  return MOCK_USERS.find((user) => user.role === role);
}
