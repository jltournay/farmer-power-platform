import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useAuth, MockAuthProvider, MOCK_USERS } from '@fp/auth';
import type { ReactNode } from 'react';

// Clear localStorage before each test
beforeEach(() => {
  window.localStorage.clear();
});

// Test component that uses useAuth
function TestComponent() {
  const {
    isAuthenticated,
    user,
    login,
    logout,
    isLoading,
    showLoginSelector,
    selectMockUser,
  } = useAuth();

  if (isLoading) {
    return <div data-testid="loading">Loading...</div>;
  }

  if (showLoginSelector) {
    return (
      <div data-testid="login-selector">
        {MOCK_USERS.map((mockUser) => (
          <button
            key={mockUser.id}
            onClick={() => selectMockUser(mockUser)}
            data-testid={`select-${mockUser.id}`}
          >
            {mockUser.name}
          </button>
        ))}
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div>
        <span data-testid="not-authenticated">Not logged in</span>
        <button onClick={login} data-testid="login-button">
          Login
        </button>
      </div>
    );
  }

  return (
    <div>
      <span data-testid="user-name">{user?.name}</span>
      <span data-testid="user-role">{user?.role}</span>
      <button onClick={logout} data-testid="logout-button">
        Logout
      </button>
    </div>
  );
}

function renderWithProvider(children: ReactNode) {
  return render(<MockAuthProvider>{children}</MockAuthProvider>);
}

describe('useAuth hook', () => {
  describe('initial state', () => {
    it('shows not authenticated after loading when no token', async () => {
      renderWithProvider(<TestComponent />);

      // The loading state is very brief, so we check the final state
      await waitFor(() => {
        expect(screen.getByTestId('not-authenticated')).toBeInTheDocument();
      });
    });
  });

  describe('login flow', () => {
    it('shows login selector when login is triggered', async () => {
      const user = userEvent.setup();
      renderWithProvider(<TestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('login-button')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('login-button'));

      expect(screen.getByTestId('login-selector')).toBeInTheDocument();
    });

    it('authenticates when mock user is selected', async () => {
      const user = userEvent.setup();
      renderWithProvider(<TestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('login-button')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('login-button'));
      await user.click(screen.getByTestId('select-mock-manager-001'));

      await waitFor(() => {
        expect(screen.getByTestId('user-name')).toHaveTextContent('Jane Mwangi');
      });
    });

    it('sets correct role after login', async () => {
      const user = userEvent.setup();
      renderWithProvider(<TestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('login-button')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('login-button'));
      await user.click(screen.getByTestId('select-mock-manager-001'));

      await waitFor(() => {
        expect(screen.getByTestId('user-role')).toHaveTextContent('factory_manager');
      });
    });
  });

  describe('logout flow', () => {
    it('clears user on logout', async () => {
      const user = userEvent.setup();
      renderWithProvider(<TestComponent />);

      // Login first
      await waitFor(() => {
        expect(screen.getByTestId('login-button')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('login-button'));
      await user.click(screen.getByTestId('select-mock-manager-001'));

      await waitFor(() => {
        expect(screen.getByTestId('user-name')).toBeInTheDocument();
      });

      // Logout
      await user.click(screen.getByTestId('logout-button'));

      await waitFor(() => {
        expect(screen.getByTestId('not-authenticated')).toBeInTheDocument();
      });
    });
  });

  describe('session persistence', () => {
    it('restores session from localStorage', async () => {
      const user = userEvent.setup();

      // First render - login
      const { unmount } = renderWithProvider(<TestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('login-button')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('login-button'));
      await user.click(screen.getByTestId('select-mock-admin-001'));

      await waitFor(() => {
        expect(screen.getByTestId('user-name')).toHaveTextContent('Admin User');
      });

      // Unmount and remount
      unmount();
      renderWithProvider(<TestComponent />);

      // Should restore session
      await waitFor(() => {
        expect(screen.getByTestId('user-name')).toHaveTextContent('Admin User');
      });
    });
  });
});
