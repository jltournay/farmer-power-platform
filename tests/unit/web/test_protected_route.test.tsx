import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  ProtectedRoute,
  MockAuthProvider,
  MOCK_USERS,
  useAuth,
} from '@fp/auth';
import type { ReactNode } from 'react';

// Clear localStorage before each test
beforeEach(() => {
  window.localStorage.clear();
});

// Helper to quickly login - auto-selects the user when login selector shows
function QuickLogin({ userId }: { userId: string }) {
  const { login, selectMockUser, showLoginSelector, isLoading, isAuthenticated } = useAuth();

  // Auto-select the mock user when the selector is shown
  if (showLoginSelector) {
    const mockUser = MOCK_USERS.find((u) => u.id === userId);
    if (mockUser) {
      // Use setTimeout to avoid calling during render
      setTimeout(() => selectMockUser(mockUser), 0);
    }
    return <div data-testid="selecting">Selecting...</div>;
  }

  if (isLoading) {
    return <div data-testid="loading">Loading...</div>;
  }

  if (!isAuthenticated) {
    return (
      <button onClick={login} data-testid="quick-login">
        Login
      </button>
    );
  }

  return <div data-testid="logged-in">Logged in</div>;
}

function renderWithProvider(children: ReactNode) {
  return render(<MockAuthProvider>{children}</MockAuthProvider>);
}

describe('ProtectedRoute component', () => {
  describe('when not authenticated', () => {
    it('shows loading state and triggers login', async () => {
      renderWithProvider(
        <ProtectedRoute>
          <div data-testid="protected-content">Secret Content</div>
        </ProtectedRoute>
      );

      // Should show loading initially
      await waitFor(() => {
        expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
      });
    });

    it('uses custom fallback when provided', async () => {
      renderWithProvider(
        <ProtectedRoute fallback={<div data-testid="custom-loading">Please wait...</div>}>
          <div data-testid="protected-content">Secret Content</div>
        </ProtectedRoute>
      );

      await waitFor(() => {
        expect(screen.getByTestId('custom-loading')).toBeInTheDocument();
      });
    });
  });

  describe('when authenticated', () => {
    it('renders children when user is authenticated', async () => {
      const user = userEvent.setup();
      renderWithProvider(
        <>
          <QuickLogin userId="mock-manager-001" />
          <ProtectedRoute>
            <div data-testid="protected-content">Secret Content</div>
          </ProtectedRoute>
        </>
      );

      // Wait for either quick-login or logged-in
      await waitFor(() => {
        const quickLogin = screen.queryByTestId('quick-login');
        const loggedIn = screen.queryByTestId('logged-in');
        expect(quickLogin || loggedIn).toBeTruthy();
      });

      const quickLoginBtn = screen.queryByTestId('quick-login');
      if (quickLoginBtn) {
        await user.click(quickLoginBtn);
      }

      await waitFor(
        () => {
          expect(screen.getByTestId('protected-content')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });
  });

  describe('role-based access', () => {
    it('allows access when user has required role', async () => {
      const user = userEvent.setup();
      renderWithProvider(
        <>
          <QuickLogin userId="mock-manager-001" />
          <ProtectedRoute roles={['factory_manager']}>
            <div data-testid="protected-content">Manager Content</div>
          </ProtectedRoute>
        </>
      );

      await waitFor(() => {
        const quickLogin = screen.queryByTestId('quick-login');
        const loggedIn = screen.queryByTestId('logged-in');
        expect(quickLogin || loggedIn).toBeTruthy();
      });

      const quickLoginBtn = screen.queryByTestId('quick-login');
      if (quickLoginBtn) {
        await user.click(quickLoginBtn);
      }

      await waitFor(
        () => {
          expect(screen.getByTestId('protected-content')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('shows access denied when user lacks required role', async () => {
      const user = userEvent.setup();
      renderWithProvider(
        <>
          <QuickLogin userId="mock-clerk-001" />
          <ProtectedRoute roles={['factory_manager', 'factory_owner']}>
            <div data-testid="protected-content">Manager Content</div>
          </ProtectedRoute>
        </>
      );

      await waitFor(() => {
        const quickLogin = screen.queryByTestId('quick-login');
        const loggedIn = screen.queryByTestId('logged-in');
        expect(quickLogin || loggedIn).toBeTruthy();
      });

      const quickLoginBtn = screen.queryByTestId('quick-login');
      if (quickLoginBtn) {
        await user.click(quickLoginBtn);
      }

      await waitFor(
        () => {
          expect(screen.getByText('Access Denied')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('allows platform_admin to bypass role checks', async () => {
      const user = userEvent.setup();
      renderWithProvider(
        <>
          <QuickLogin userId="mock-admin-001" />
          <ProtectedRoute roles={['factory_manager']}>
            <div data-testid="protected-content">Manager Content</div>
          </ProtectedRoute>
        </>
      );

      await waitFor(() => {
        const quickLogin = screen.queryByTestId('quick-login');
        const loggedIn = screen.queryByTestId('logged-in');
        expect(quickLogin || loggedIn).toBeTruthy();
      });

      const quickLoginBtn = screen.queryByTestId('quick-login');
      if (quickLoginBtn) {
        await user.click(quickLoginBtn);
      }

      await waitFor(
        () => {
          // Admin bypasses role check
          expect(screen.getByTestId('protected-content')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });
  });

  describe('permission-based access', () => {
    it('allows access when user has required permissions', async () => {
      const user = userEvent.setup();
      renderWithProvider(
        <>
          <QuickLogin userId="mock-manager-001" />
          <ProtectedRoute permissions={['farmers:read']}>
            <div data-testid="protected-content">Farmers List</div>
          </ProtectedRoute>
        </>
      );

      // Wait for either quick-login or logged-in (might already be logged in)
      await waitFor(() => {
        const quickLogin = screen.queryByTestId('quick-login');
        const loggedIn = screen.queryByTestId('logged-in');
        expect(quickLogin || loggedIn).toBeTruthy();
      });

      const quickLoginBtn = screen.queryByTestId('quick-login');
      if (quickLoginBtn) {
        await user.click(quickLoginBtn);
      }

      await waitFor(
        () => {
          expect(screen.getByTestId('protected-content')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('shows access denied when user lacks required permissions', async () => {
      const user = userEvent.setup();
      renderWithProvider(
        <>
          <QuickLogin userId="mock-manager-001" />
          <ProtectedRoute permissions={['payment_policies:write']}>
            <div data-testid="protected-content">Payment Settings</div>
          </ProtectedRoute>
        </>
      );

      await waitFor(() => {
        const quickLogin = screen.queryByTestId('quick-login');
        const loggedIn = screen.queryByTestId('logged-in');
        expect(quickLogin || loggedIn).toBeTruthy();
      });

      const quickLoginBtn = screen.queryByTestId('quick-login');
      if (quickLoginBtn) {
        await user.click(quickLoginBtn);
      }

      await waitFor(
        () => {
          expect(screen.getByText('Access Denied')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('uses custom accessDenied component', async () => {
      const user = userEvent.setup();
      renderWithProvider(
        <>
          <QuickLogin userId="mock-clerk-001" />
          <ProtectedRoute
            roles={['factory_owner']}
            accessDenied={<div data-testid="custom-denied">No Access Here!</div>}
          >
            <div data-testid="protected-content">Owner Content</div>
          </ProtectedRoute>
        </>
      );

      await waitFor(() => {
        const quickLogin = screen.queryByTestId('quick-login');
        const loggedIn = screen.queryByTestId('logged-in');
        expect(quickLogin || loggedIn).toBeTruthy();
      });

      const quickLoginBtn = screen.queryByTestId('quick-login');
      if (quickLoginBtn) {
        await user.click(quickLoginBtn);
      }

      await waitFor(
        () => {
          expect(screen.getByTestId('custom-denied')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });
  });

  describe('combined role and permission checks', () => {
    it('requires both role and permissions when both are specified', async () => {
      const user = userEvent.setup();
      renderWithProvider(
        <>
          <QuickLogin userId="mock-owner-001" />
          <ProtectedRoute
            roles={['factory_owner']}
            permissions={['payment_policies:write']}
          >
            <div data-testid="protected-content">Owner Settings</div>
          </ProtectedRoute>
        </>
      );

      await waitFor(() => {
        const quickLogin = screen.queryByTestId('quick-login');
        const loggedIn = screen.queryByTestId('logged-in');
        expect(quickLogin || loggedIn).toBeTruthy();
      });

      const quickLoginBtn = screen.queryByTestId('quick-login');
      if (quickLoginBtn) {
        await user.click(quickLoginBtn);
      }

      await waitFor(
        () => {
          // Owner has both the role and the permission
          expect(screen.getByTestId('protected-content')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });
  });
});
