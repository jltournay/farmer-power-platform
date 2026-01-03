/**
 * App Component Tests
 *
 * Tests for the root App component and application mounting.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider } from '@fp/ui-components';
import { App } from '../../../../web/factory-portal/src/app/App';

// Mock @fp/auth
vi.mock('@fp/auth', () => ({
  useAuth: vi.fn(() => ({
    isAuthenticated: true,
    isLoading: false,
    user: {
      sub: 'mock-manager-001',
      email: 'jane.mwangi@factory.example.com',
      name: 'Jane Mwangi',
      role: 'factory_manager',
      factory_id: 'KEN-FAC-001',
      factory_ids: ['KEN-FAC-001'],
      collection_point_id: null,
      region_ids: [],
      permissions: ['farmers:read', 'quality_events:read'],
    },
    login: vi.fn(),
    logout: vi.fn(),
    getAccessToken: vi.fn(),
    showLoginSelector: false,
    selectMockUser: vi.fn(),
  })),
  MockLoginSelector: () => <div data-testid="mock-login-selector">Mock Login</div>,
  ProtectedRoute: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

/**
 * Helper to render App with required providers.
 */
function renderApp(initialRoute = '/') {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <ThemeProvider>
        <App />
      </ThemeProvider>
    </MemoryRouter>
  );
}

describe('App Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    renderApp();
    // App should render the layout which contains the sidebar
    expect(document.body).toBeTruthy();
  });

  it('renders Command Center when navigating to /command-center', () => {
    renderApp('/command-center');
    // Use role to find the page heading specifically
    expect(screen.getByRole('heading', { name: 'Command Center', level: 1 })).toBeInTheDocument();
  });

  it('renders Farmer Detail when navigating to /farmers/:id', () => {
    renderApp('/farmers/123');
    expect(screen.getByRole('heading', { name: 'Farmer Detail', level: 1 })).toBeInTheDocument();
    expect(screen.getByText(/Farmer ID: 123/)).toBeInTheDocument();
  });

  it('renders 404 page for unknown routes', () => {
    renderApp('/unknown-route');
    expect(screen.getByRole('heading', { name: 'Page Not Found', level: 1 })).toBeInTheDocument();
  });

  it('shows mock login selector when showLoginSelector is true', async () => {
    const { useAuth } = await import('@fp/auth');
    vi.mocked(useAuth).mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      user: null,
      login: vi.fn(),
      logout: vi.fn(),
      getAccessToken: vi.fn(),
      showLoginSelector: true,
      selectMockUser: vi.fn(),
    });

    renderApp();
    expect(screen.getByTestId('mock-login-selector')).toBeInTheDocument();
  });
});
