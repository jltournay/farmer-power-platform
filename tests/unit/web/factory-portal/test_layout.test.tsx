/**
 * Layout Tests
 *
 * Tests for Layout, Sidebar, and Header components.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider } from '@fp/ui-components';
import { Layout } from '../../../../web/factory-portal/src/components/Layout';
import { Sidebar } from '../../../../web/factory-portal/src/components/Sidebar';
import { Header } from '../../../../web/factory-portal/src/components/Header';

// Mock user data
const mockFactoryManager = {
  sub: 'mock-manager-001',
  email: 'jane.mwangi@factory.example.com',
  name: 'Jane Mwangi',
  role: 'factory_manager',
  factory_id: 'KEN-FAC-001',
  factory_ids: ['KEN-FAC-001'],
  collection_point_id: null,
  region_ids: [],
  permissions: ['farmers:read', 'quality_events:read'],
};

const mockFactoryOwner = {
  ...mockFactoryManager,
  sub: 'mock-owner-001',
  name: 'John Ochieng',
  role: 'factory_owner',
  factory_ids: ['KEN-FAC-001', 'KEN-FAC-002'],
  permissions: ['farmers:read', 'quality_events:read', 'payment_policies:write'],
};

const mockPlatformAdmin = {
  sub: 'mock-admin-001',
  email: 'admin@farmerpower.example.com',
  name: 'Admin User',
  role: 'platform_admin',
  factory_id: null,
  factory_ids: [],
  collection_point_id: null,
  region_ids: [],
  permissions: ['*'],
};

// Mock @fp/auth
vi.mock('@fp/auth', () => ({
  useAuth: vi.fn(() => ({
    isAuthenticated: true,
    isLoading: false,
    user: mockFactoryManager,
    login: vi.fn(),
    logout: vi.fn(),
    getAccessToken: vi.fn(),
    showLoginSelector: false,
    selectMockUser: vi.fn(),
  })),
  ProtectedRoute: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

/**
 * Helper to render with providers.
 */
function renderWithProviders(ui: React.ReactElement) {
  return render(
    <MemoryRouter>
      <ThemeProvider>{ui}</ThemeProvider>
    </MemoryRouter>
  );
}

describe('Layout Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    renderWithProviders(<Layout />);
    expect(screen.getByText('Farmer Power')).toBeInTheDocument();
  });

  it('contains sidebar navigation', () => {
    renderWithProviders(<Layout />);
    expect(screen.getByText('Command Center')).toBeInTheDocument();
  });

  it('contains header with user info', () => {
    renderWithProviders(<Layout />);
    expect(screen.getByText('Jane Mwangi')).toBeInTheDocument();
  });
});

describe('Sidebar Component', () => {
  const defaultProps = {
    open: true,
    width: 240,
    collapsedWidth: 64,
    onToggle: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Farmer Power brand', () => {
    renderWithProviders(<Sidebar {...defaultProps} />);
    expect(screen.getByText('Farmer Power')).toBeInTheDocument();
  });

  it('shows Command Center menu item for factory manager', () => {
    renderWithProviders(<Sidebar {...defaultProps} />);
    // Find the menu item in the list
    expect(screen.getByRole('button', { name: /Command Center/i })).toBeInTheDocument();
  });

  it('does not show ROI Summary for factory manager', () => {
    renderWithProviders(<Sidebar {...defaultProps} />);
    expect(screen.queryByRole('button', { name: /ROI Summary/i })).not.toBeInTheDocument();
  });

  it('shows ROI Summary for factory owner', async () => {
    const { useAuth } = await import('@fp/auth');
    vi.mocked(useAuth).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: mockFactoryOwner,
      login: vi.fn(),
      logout: vi.fn(),
      getAccessToken: vi.fn(),
      showLoginSelector: false,
      selectMockUser: vi.fn(),
    });

    renderWithProviders(<Sidebar {...defaultProps} />);
    expect(screen.getByRole('button', { name: /ROI Summary/i })).toBeInTheDocument();
  });

  it('shows all menu items for platform admin', async () => {
    const { useAuth } = await import('@fp/auth');
    vi.mocked(useAuth).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: mockPlatformAdmin,
      login: vi.fn(),
      logout: vi.fn(),
      getAccessToken: vi.fn(),
      showLoginSelector: false,
      selectMockUser: vi.fn(),
    });

    renderWithProviders(<Sidebar {...defaultProps} />);
    expect(screen.getByRole('button', { name: /Command Center/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /ROI Summary/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Settings/i })).toBeInTheDocument();
  });

  it('calls onToggle when collapse button is clicked', () => {
    const onToggle = vi.fn();
    renderWithProviders(<Sidebar {...defaultProps} onToggle={onToggle} />);

    // Find the collapse button by its aria-label
    const collapseButton = screen.getByRole('button', { name: /collapse sidebar/i });
    fireEvent.click(collapseButton);

    expect(onToggle).toHaveBeenCalledTimes(1);
  });
});

describe('Header Component', () => {
  const defaultProps = {
    onMenuClick: vi.fn(),
    showMenuButton: false,
  };

  beforeEach(async () => {
    vi.clearAllMocks();
    // Reset to factory manager for header tests
    const { useAuth } = await import('@fp/auth');
    vi.mocked(useAuth).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: mockFactoryManager,
      login: vi.fn(),
      logout: vi.fn(),
      getAccessToken: vi.fn(),
      showLoginSelector: false,
      selectMockUser: vi.fn(),
    });
  });

  it('displays user name', () => {
    renderWithProviders(<Header {...defaultProps} />);
    expect(screen.getByText('Jane Mwangi')).toBeInTheDocument();
  });

  it('displays factory badge', () => {
    renderWithProviders(<Header {...defaultProps} />);
    expect(screen.getByText('Factory KEN-FAC-001')).toBeInTheDocument();
  });

  it('has logout button', () => {
    renderWithProviders(<Header {...defaultProps} />);
    expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument();
  });

  it('shows menu button when showMenuButton is true', () => {
    renderWithProviders(<Header {...defaultProps} showMenuButton={true} />);
    expect(screen.getByRole('button', { name: /open menu/i })).toBeInTheDocument();
  });

  it('calls onMenuClick when menu button is clicked', () => {
    const onMenuClick = vi.fn();
    renderWithProviders(<Header {...defaultProps} showMenuButton={true} onMenuClick={onMenuClick} />);

    fireEvent.click(screen.getByRole('button', { name: /open menu/i }));
    expect(onMenuClick).toHaveBeenCalledTimes(1);
  });

  it('calls logout when logout button is clicked', async () => {
    const { useAuth } = await import('@fp/auth');
    const mockLogout = vi.fn();
    vi.mocked(useAuth).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: mockFactoryManager,
      login: vi.fn(),
      logout: mockLogout,
      getAccessToken: vi.fn(),
      showLoginSelector: false,
      selectMockUser: vi.fn(),
    });

    renderWithProviders(<Header {...defaultProps} />);
    fireEvent.click(screen.getByRole('button', { name: /logout/i }));

    expect(mockLogout).toHaveBeenCalledTimes(1);
  });
});
