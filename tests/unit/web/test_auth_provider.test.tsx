import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  MockAuthProvider,
  MockLoginSelector,
  useAuth,
  MOCK_USERS,
} from '@fp/auth';
import type { ReactNode } from 'react';

// Clear localStorage before each test
beforeEach(() => {
  window.localStorage.clear();
});

function renderWithProvider(children: ReactNode) {
  return render(<MockAuthProvider>{children}</MockAuthProvider>);
}

// Test component that displays auth state
function AuthStatus() {
  const { isAuthenticated, user, isLoading } = useAuth();

  if (isLoading) {
    return <div data-testid="status-loading">Loading...</div>;
  }

  if (!isAuthenticated) {
    return <div data-testid="status-unauthenticated">Not logged in</div>;
  }

  return (
    <div data-testid="status-authenticated">
      <span data-testid="user-email">{user?.email}</span>
      <span data-testid="user-factory">{user?.factory_id || 'No factory'}</span>
    </div>
  );
}

describe('MockAuthProvider', () => {
  describe('initial state', () => {
    it('transitions to unauthenticated state when no token', async () => {
      renderWithProvider(<AuthStatus />);

      // The loading state is very brief, so we check the final state
      await waitFor(() => {
        expect(screen.getByTestId('status-unauthenticated')).toBeInTheDocument();
      });
    });
  });

  describe('localStorage persistence', () => {
    it('persists token to localStorage on login', async () => {
      const user = userEvent.setup();

      function LoginComponent() {
        const { login, showLoginSelector, selectMockUser } = useAuth();

        if (showLoginSelector) {
          return (
            <button
              onClick={() => selectMockUser(MOCK_USERS[0]!)}
              data-testid="select-user"
            >
              Select
            </button>
          );
        }

        return (
          <button onClick={login} data-testid="login">
            Login
          </button>
        );
      }

      renderWithProvider(<LoginComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('login')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('login'));
      await user.click(screen.getByTestId('select-user'));

      await waitFor(() => {
        expect(localStorage.getItem('fp_auth_token')).not.toBeNull();
      });
    });

    it('clears localStorage on logout', async () => {
      const user = userEvent.setup();

      function LogoutComponent() {
        const { login, logout, isAuthenticated, showLoginSelector, selectMockUser, isLoading } =
          useAuth();

        if (isLoading) return <div>Loading...</div>;

        if (showLoginSelector) {
          return (
            <button
              onClick={() => selectMockUser(MOCK_USERS[0]!)}
              data-testid="select-user"
            >
              Select
            </button>
          );
        }

        if (isAuthenticated) {
          return (
            <button onClick={logout} data-testid="logout">
              Logout
            </button>
          );
        }

        return (
          <button onClick={login} data-testid="login">
            Login
          </button>
        );
      }

      renderWithProvider(<LogoutComponent />);

      // Login
      await waitFor(() => {
        expect(screen.getByTestId('login')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('login'));
      await user.click(screen.getByTestId('select-user'));

      // Verify logged in
      await waitFor(() => {
        expect(screen.getByTestId('logout')).toBeInTheDocument();
      });

      // Logout
      await user.click(screen.getByTestId('logout'));

      await waitFor(() => {
        expect(localStorage.getItem('fp_auth_token')).toBeNull();
      });
    });
  });

  describe('getAccessToken', () => {
    it('returns token when authenticated', async () => {
      const user = userEvent.setup();
      let capturedToken: string | null = null;

      function TokenComponent() {
        const {
          login,
          getAccessToken,
          isAuthenticated,
          showLoginSelector,
          selectMockUser,
          isLoading,
        } = useAuth();

        const handleGetToken = async () => {
          const token = await getAccessToken();
          capturedToken = token;
        };

        if (isLoading) return <div>Loading...</div>;

        if (showLoginSelector) {
          return (
            <button
              onClick={() => selectMockUser(MOCK_USERS[0]!)}
              data-testid="select-user"
            >
              Select
            </button>
          );
        }

        if (isAuthenticated) {
          return (
            <button onClick={handleGetToken} data-testid="get-token">
              Get Token
            </button>
          );
        }

        return (
          <button onClick={login} data-testid="login">
            Login
          </button>
        );
      }

      renderWithProvider(<TokenComponent />);

      // Login
      await waitFor(() => {
        expect(screen.getByTestId('login')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('login'));
      await user.click(screen.getByTestId('select-user'));

      // Get token
      await waitFor(() => {
        expect(screen.getByTestId('get-token')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('get-token'));

      await waitFor(() => {
        expect(capturedToken).not.toBeNull();
        expect(typeof capturedToken).toBe('string');
      });
    });

    it('throws when not authenticated', async () => {
      let thrownError: Error | null = null;

      function ThrowingComponent() {
        const { getAccessToken, isLoading } = useAuth();

        const handleGetToken = async () => {
          try {
            await getAccessToken();
          } catch (e) {
            thrownError = e as Error;
          }
        };

        if (isLoading) return <div data-testid="loading">Loading...</div>;

        return (
          <button onClick={handleGetToken} data-testid="get-token">
            Get Token
          </button>
        );
      }

      const user = userEvent.setup();
      renderWithProvider(<ThrowingComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('get-token')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('get-token'));

      await waitFor(() => {
        expect(thrownError).not.toBeNull();
        expect(thrownError?.message).toBe('Not authenticated');
      });
    });
  });
});

describe('MockLoginSelector', () => {
  it('renders all 5 mock users', () => {
    const onSelect = vi.fn();
    render(<MockLoginSelector onSelect={onSelect} />);

    expect(screen.getByText('Jane Mwangi')).toBeInTheDocument();
    expect(screen.getByText('John Ochieng')).toBeInTheDocument();
    expect(screen.getByText('Admin User')).toBeInTheDocument();
    expect(screen.getByText('Mary Wanjiku')).toBeInTheDocument();
    expect(screen.getByText('TBK Inspector')).toBeInTheDocument();
  });

  it('displays role badges', () => {
    const onSelect = vi.fn();
    render(<MockLoginSelector onSelect={onSelect} />);

    expect(screen.getByText('Factory Manager')).toBeInTheDocument();
    expect(screen.getByText('Factory Owner')).toBeInTheDocument();
    expect(screen.getByText('Platform Admin')).toBeInTheDocument();
    expect(screen.getByText('Registration Clerk')).toBeInTheDocument();
    expect(screen.getByText('Regulator')).toBeInTheDocument();
  });

  it('calls onSelect when user is clicked', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<MockLoginSelector onSelect={onSelect} />);

    await user.click(screen.getByText('Jane Mwangi'));

    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'mock-manager-001',
        name: 'Jane Mwangi',
        role: 'factory_manager',
      })
    );
  });

  it('displays factory IDs for users', () => {
    const onSelect = vi.fn();
    render(<MockLoginSelector onSelect={onSelect} />);

    // Multiple users have this factory, so use getAllByText
    expect(screen.getAllByText('KEN-FAC-001').length).toBeGreaterThan(0);
  });

  it('displays region IDs for regulators', () => {
    const onSelect = vi.fn();
    render(<MockLoginSelector onSelect={onSelect} />);

    expect(screen.getByText('nandi, kericho')).toBeInTheDocument();
  });
});
