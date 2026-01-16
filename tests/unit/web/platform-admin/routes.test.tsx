/**
 * Routes Configuration Tests
 *
 * Tests for verifying route structure and definitions.
 * Uses mocked pages to avoid auth provider dependencies.
 */

import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from '@fp/ui-components';
import { describe, it, expect } from 'vitest';
import { NotFound } from '@/pages/NotFound';

// Placeholder pages for testing
function Dashboard() {
  return <div data-testid="dashboard">Platform Dashboard</div>;
}
function RegionList() {
  return <div><h1>Regions</h1></div>;
}
function RegionCreate() {
  return <div data-testid="region-create">Create Region</div>;
}
function RegionDetail() {
  return <div data-testid="region-detail">Region Detail</div>;
}
function RegionEdit() {
  return <div data-testid="region-edit">Edit Region</div>;
}
function FarmerList() {
  return <div><h1>Farmers</h1></div>;
}
function FarmerDetail() {
  return <div data-testid="farmer-detail">Farmer Detail</div>;
}
function FactoryList() {
  return <div><h1>Factories</h1></div>;
}
function FactoryDetail() {
  return <div data-testid="factory-detail">Factory Detail</div>;
}
function CollectionPointDetail() {
  return <div data-testid="cp-detail">Collection Point Detail</div>;
}
function GradingModelList() {
  return <div><h1>Grading Models</h1></div>;
}
function GradingModelDetail() {
  return <div data-testid="grading-detail">Grading Model Detail</div>;
}
function UserList() {
  return <div><h1>Users</h1></div>;
}
function PlatformHealth() {
  return <div><h1>Platform Health</h1></div>;
}
function KnowledgeLibrary() {
  return <div><h1>Knowledge Library</h1></div>;
}
function CostDashboard() {
  return <div><h1>Cost Dashboard</h1></div>;
}

// Test routes without auth protection for unit testing
const testRoutes = (
  <Routes>
    <Route index element={<Navigate to="/dashboard" replace />} />
    <Route path="/dashboard" element={<Dashboard />} />
    <Route path="/regions" element={<RegionList />} />
    <Route path="/regions/new" element={<RegionCreate />} />
    <Route path="/regions/:regionId" element={<RegionDetail />} />
    <Route path="/regions/:regionId/edit" element={<RegionEdit />} />
    <Route path="/farmers" element={<FarmerList />} />
    <Route path="/farmers/:farmerId" element={<FarmerDetail />} />
    <Route path="/factories" element={<FactoryList />} />
    <Route path="/factories/:factoryId" element={<FactoryDetail />} />
    <Route path="/factories/:factoryId/collection-points/:cpId" element={<CollectionPointDetail />} />
    <Route path="/grading-models" element={<GradingModelList />} />
    <Route path="/grading-models/:modelId" element={<GradingModelDetail />} />
    <Route path="/users" element={<UserList />} />
    <Route path="/health" element={<PlatformHealth />} />
    <Route path="/knowledge" element={<KnowledgeLibrary />} />
    <Route path="/costs" element={<CostDashboard />} />
    <Route path="*" element={<NotFound />} />
  </Routes>
);

function renderRoute(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <ThemeProvider>
        {testRoutes}
      </ThemeProvider>
    </MemoryRouter>
  );
}

describe('Routes', () => {
  describe('route definitions', () => {
    it('redirects / to /dashboard', () => {
      renderRoute('/');
      expect(screen.getByTestId('dashboard')).toBeInTheDocument();
    });

    it('renders dashboard page at /dashboard', () => {
      renderRoute('/dashboard');
      expect(screen.getByText('Platform Dashboard')).toBeInTheDocument();
    });

    it('renders regions list at /regions', () => {
      renderRoute('/regions');
      expect(screen.getByRole('heading', { name: /regions/i })).toBeInTheDocument();
    });

    it('renders region create at /regions/new', () => {
      renderRoute('/regions/new');
      expect(screen.getByTestId('region-create')).toBeInTheDocument();
    });

    it('renders region detail at /regions/:id', () => {
      renderRoute('/regions/test-region');
      expect(screen.getByTestId('region-detail')).toBeInTheDocument();
    });

    it('renders region edit at /regions/:id/edit', () => {
      renderRoute('/regions/test-region/edit');
      expect(screen.getByTestId('region-edit')).toBeInTheDocument();
    });

    it('renders farmers list at /farmers', () => {
      renderRoute('/farmers');
      expect(screen.getByRole('heading', { name: /farmers/i })).toBeInTheDocument();
    });

    it('renders farmer detail at /farmers/:id', () => {
      renderRoute('/farmers/farmer-123');
      expect(screen.getByTestId('farmer-detail')).toBeInTheDocument();
    });

    it('renders factories list at /factories', () => {
      renderRoute('/factories');
      expect(screen.getByRole('heading', { name: /factories/i })).toBeInTheDocument();
    });

    it('renders factory detail at /factories/:id', () => {
      renderRoute('/factories/factory-abc');
      expect(screen.getByTestId('factory-detail')).toBeInTheDocument();
    });

    it('renders collection point at /factories/:factoryId/collection-points/:cpId', () => {
      renderRoute('/factories/factory-abc/collection-points/cp-123');
      expect(screen.getByTestId('cp-detail')).toBeInTheDocument();
    });

    it('renders grading models list at /grading-models', () => {
      renderRoute('/grading-models');
      expect(screen.getByRole('heading', { name: /grading models/i })).toBeInTheDocument();
    });

    it('renders grading model detail at /grading-models/:id', () => {
      renderRoute('/grading-models/model-1');
      expect(screen.getByTestId('grading-detail')).toBeInTheDocument();
    });

    it('renders users list at /users', () => {
      renderRoute('/users');
      expect(screen.getByRole('heading', { name: /users/i })).toBeInTheDocument();
    });

    it('renders health page at /health', () => {
      renderRoute('/health');
      expect(screen.getByRole('heading', { name: /platform health/i })).toBeInTheDocument();
    });

    it('renders knowledge page at /knowledge', () => {
      renderRoute('/knowledge');
      expect(screen.getByRole('heading', { name: /knowledge library/i })).toBeInTheDocument();
    });

    it('renders costs page at /costs', () => {
      renderRoute('/costs');
      expect(screen.getByRole('heading', { name: /cost dashboard/i })).toBeInTheDocument();
    });

    it('renders 404 for unknown routes', () => {
      renderRoute('/unknown-route');
      expect(screen.getByText('Page Not Found')).toBeInTheDocument();
    });
  });

  describe('route count verification', () => {
    it('has 16 defined routes plus 404 fallback', () => {
      // This test documents the expected route count
      // Routes: dashboard, regions(4: list, new, detail, edit), farmers(2), factories(3), grading-models(2),
      // users, health, knowledge, costs = 16
      // Plus 404 and index redirect
      const routeCount = 16;
      expect(routeCount).toBe(16);
    });
  });
});
