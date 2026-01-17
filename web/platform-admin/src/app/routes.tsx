/**
 * Platform Admin Route Definitions
 *
 * Configures all routes for the Platform Admin application.
 * Routes are protected by role-based access control requiring platform_admin role.
 */

import { Navigate, type RouteObject } from 'react-router-dom';
import { ProtectedRoute } from '@fp/auth';
import { Layout } from '@/components/Layout';
import { Dashboard } from '@/pages/Dashboard';
import { RegionList, RegionDetail, RegionCreate, RegionEdit } from '@/pages/regions';
import { FarmerList } from '@/pages/farmers/FarmerList';
import { FarmerDetail } from '@/pages/farmers/FarmerDetail';
import { FactoryList, FactoryDetail, FactoryCreate, FactoryEdit, CollectionPointDetail, CollectionPointEdit } from '@/pages/factories';
import { GradingModelList } from '@/pages/grading-models/GradingModelList';
import { GradingModelDetail } from '@/pages/grading-models/GradingModelDetail';
import { UserList } from '@/pages/users/UserList';
import { PlatformHealth } from '@/pages/health/PlatformHealth';
import { KnowledgeLibrary } from '@/pages/knowledge/KnowledgeLibrary';
import { CostDashboard } from '@/pages/costs/CostDashboard';
import { NotFound } from '@/pages/NotFound';

/**
 * Application routes with role-based protection.
 *
 * Routes:
 * - / -> redirects to /dashboard (Platform overview)
 * - /regions - All regions (top-level)
 * - /regions/new - Create new region
 * - /regions/:regionId - Region detail view
 * - /regions/:regionId/edit - Edit region
 * - /farmers - All farmers with filters (top-level)
 * - /farmers/:farmerId - Full farmer edit
 * - /factories - All factories (top-level)
 * - /factories/:factoryId - Factory + CPs (hierarchical)
 * - /factories/:factoryId/collection-points/:cpId - Collection point config
 * - /grading-models - All grading models
 * - /grading-models/:modelId - Model configuration
 * - /users - All platform users
 * - /health - Platform health metrics
 * - /knowledge - RAG document library
 * - /costs - LLM spending dashboard
 * - * - 404 Not Found
 *
 * All routes require platform_admin role.
 */
export const routes: RouteObject[] = [
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        element: <Navigate to="/dashboard" replace />,
      },
      {
        path: 'dashboard',
        element: (
          <ProtectedRoute roles={['platform_admin']}>
            <Dashboard />
          </ProtectedRoute>
        ),
      },
      {
        path: 'regions',
        element: (
          <ProtectedRoute roles={['platform_admin']}>
            <RegionList />
          </ProtectedRoute>
        ),
      },
      {
        path: 'regions/new',
        element: (
          <ProtectedRoute roles={['platform_admin']}>
            <RegionCreate />
          </ProtectedRoute>
        ),
      },
      {
        path: 'regions/:regionId',
        element: (
          <ProtectedRoute roles={['platform_admin']}>
            <RegionDetail />
          </ProtectedRoute>
        ),
      },
      {
        path: 'regions/:regionId/edit',
        element: (
          <ProtectedRoute roles={['platform_admin']}>
            <RegionEdit />
          </ProtectedRoute>
        ),
      },
      {
        path: 'farmers',
        element: (
          <ProtectedRoute roles={['platform_admin']}>
            <FarmerList />
          </ProtectedRoute>
        ),
      },
      {
        path: 'farmers/:farmerId',
        element: (
          <ProtectedRoute roles={['platform_admin']}>
            <FarmerDetail />
          </ProtectedRoute>
        ),
      },
      {
        path: 'factories',
        element: (
          <ProtectedRoute roles={['platform_admin']}>
            <FactoryList />
          </ProtectedRoute>
        ),
      },
      {
        path: 'factories/new',
        element: (
          <ProtectedRoute roles={['platform_admin']}>
            <FactoryCreate />
          </ProtectedRoute>
        ),
      },
      {
        path: 'factories/:factoryId',
        element: (
          <ProtectedRoute roles={['platform_admin']}>
            <FactoryDetail />
          </ProtectedRoute>
        ),
      },
      {
        path: 'factories/:factoryId/edit',
        element: (
          <ProtectedRoute roles={['platform_admin']}>
            <FactoryEdit />
          </ProtectedRoute>
        ),
      },
      {
        path: 'factories/:factoryId/collection-points/:cpId',
        element: (
          <ProtectedRoute roles={['platform_admin']}>
            <CollectionPointDetail />
          </ProtectedRoute>
        ),
      },
      {
        path: 'factories/:factoryId/collection-points/:cpId/edit',
        element: (
          <ProtectedRoute roles={['platform_admin']}>
            <CollectionPointEdit />
          </ProtectedRoute>
        ),
      },
      {
        path: 'grading-models',
        element: (
          <ProtectedRoute roles={['platform_admin']}>
            <GradingModelList />
          </ProtectedRoute>
        ),
      },
      {
        path: 'grading-models/:modelId',
        element: (
          <ProtectedRoute roles={['platform_admin']}>
            <GradingModelDetail />
          </ProtectedRoute>
        ),
      },
      {
        path: 'users',
        element: (
          <ProtectedRoute roles={['platform_admin']}>
            <UserList />
          </ProtectedRoute>
        ),
      },
      {
        path: 'health',
        element: (
          <ProtectedRoute roles={['platform_admin']}>
            <PlatformHealth />
          </ProtectedRoute>
        ),
      },
      {
        path: 'knowledge',
        element: (
          <ProtectedRoute roles={['platform_admin']}>
            <KnowledgeLibrary />
          </ProtectedRoute>
        ),
      },
      {
        path: 'costs',
        element: (
          <ProtectedRoute roles={['platform_admin']}>
            <CostDashboard />
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
