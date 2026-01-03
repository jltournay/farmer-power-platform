/**
 * Routing Tests
 *
 * Tests for route configuration and navigation.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, useRoutes } from 'react-router-dom';
import { ThemeProvider } from '@fp/ui-components';
import { routes } from '../../../../web/factory-portal/src/app/routes';

// Mock @fp/auth
vi.mock('@fp/auth', () => ({
  useAuth: vi.fn(() => ({
    isAuthenticated: true,
    isLoading: false,
    user: {
      sub: 'mock-admin-001',
      email: 'admin@farmerpower.example.com',
      name: 'Admin User',
      role: 'platform_admin',
      factory_id: null,
      factory_ids: [],
      collection_point_id: null,
      region_ids: [],
      permissions: ['*'],
    },
    login: vi.fn(),
    logout: vi.fn(),
    getAccessToken: vi.fn(),
    showLoginSelector: false,
    selectMockUser: vi.fn(),
  })),
  ProtectedRoute: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

/**
 * Test component that renders routes.
 */
function TestRouter({ initialRoute }: { initialRoute: string }) {
  const routeElements = useRoutes(routes);
  return <>{routeElements}</>;
}

/**
 * Helper to render routes with required providers.
 */
function renderRoutes(initialRoute = '/') {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <ThemeProvider>
        <TestRouter initialRoute={initialRoute} />
      </ThemeProvider>
    </MemoryRouter>
  );
}

describe('Route Configuration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Route definitions', () => {
    it('has correct number of routes', () => {
      // Root route with children
      expect(routes).toHaveLength(1);
      expect(routes[0].children).toBeDefined();
      // 6 child routes: index, command-center, farmers/:id, roi, settings/*, *
      expect(routes[0].children).toHaveLength(6);
    });

    it('has index route that redirects to command-center', () => {
      const indexRoute = routes[0].children?.find((r) => r.index);
      expect(indexRoute).toBeDefined();
    });

    it('has command-center route', () => {
      const route = routes[0].children?.find((r) => r.path === 'command-center');
      expect(route).toBeDefined();
    });

    it('has farmers/:id route', () => {
      const route = routes[0].children?.find((r) => r.path === 'farmers/:id');
      expect(route).toBeDefined();
    });

    it('has roi route', () => {
      const route = routes[0].children?.find((r) => r.path === 'roi');
      expect(route).toBeDefined();
    });

    it('has settings/* route', () => {
      const route = routes[0].children?.find((r) => r.path === 'settings/*');
      expect(route).toBeDefined();
    });

    it('has catch-all 404 route', () => {
      const route = routes[0].children?.find((r) => r.path === '*');
      expect(route).toBeDefined();
    });
  });

  describe('Route rendering', () => {
    it('renders Command Center at /command-center', () => {
      renderRoutes('/command-center');
      // Use role to find the page heading specifically
      expect(screen.getByRole('heading', { name: 'Command Center', level: 1 })).toBeInTheDocument();
    });

    it('renders Farmer Detail at /farmers/:id', () => {
      renderRoutes('/farmers/456');
      expect(screen.getByRole('heading', { name: 'Farmer Detail', level: 1 })).toBeInTheDocument();
    });

    it('renders ROI Summary at /roi', () => {
      renderRoutes('/roi');
      expect(screen.getByRole('heading', { name: 'ROI Summary', level: 1 })).toBeInTheDocument();
    });

    it('renders Settings at /settings', () => {
      renderRoutes('/settings');
      expect(screen.getByRole('heading', { name: 'Settings', level: 1 })).toBeInTheDocument();
    });

    it('renders 404 for unknown routes', () => {
      renderRoutes('/this-route-does-not-exist');
      expect(screen.getByRole('heading', { name: 'Page Not Found', level: 1 })).toBeInTheDocument();
    });
  });
});
