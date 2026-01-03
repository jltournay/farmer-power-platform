/**
 * Factory Portal Route Definitions
 *
 * Configures all routes for the Factory Portal application.
 * Routes are protected by role-based access control.
 */

import { Navigate, type RouteObject } from 'react-router-dom';
import { ProtectedRoute } from '@fp/auth';
import { Layout } from '@/components/Layout';
import { CommandCenter } from '@/pages/manager/CommandCenter';
import { FarmerDetail } from '@/pages/manager/FarmerDetail';
import { ROISummary } from '@/pages/owner/ROISummary';
import { Settings } from '@/pages/admin/Settings';
import { NotFound } from '@/pages/NotFound';

/**
 * Application routes with role-based protection.
 *
 * Routes:
 * - / -> redirects to /command-center
 * - /command-center - Factory Manager dashboard (manager, owner, admin)
 * - /farmers/:id - Farmer detail view (manager, owner, admin)
 * - /roi - ROI summary (owner, admin)
 * - /settings/* - Factory settings (factory_admin, admin)
 * - * - 404 Not Found
 */
export const routes: RouteObject[] = [
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        element: <Navigate to="/command-center" replace />,
      },
      {
        path: 'command-center',
        element: (
          <ProtectedRoute roles={['factory_manager', 'factory_owner', 'platform_admin']}>
            <CommandCenter />
          </ProtectedRoute>
        ),
      },
      {
        path: 'farmers/:id',
        element: (
          <ProtectedRoute roles={['factory_manager', 'factory_owner', 'platform_admin']}>
            <FarmerDetail />
          </ProtectedRoute>
        ),
      },
      {
        path: 'roi',
        element: (
          <ProtectedRoute roles={['factory_owner', 'platform_admin']}>
            <ROISummary />
          </ProtectedRoute>
        ),
      },
      {
        path: 'settings/*',
        element: (
          <ProtectedRoute roles={['factory_admin', 'platform_admin']}>
            <Settings />
          </ProtectedRoute>
        ),
      },
      {
        path: '*',
        element: <NotFound />,
      },
    ],
  },
];
