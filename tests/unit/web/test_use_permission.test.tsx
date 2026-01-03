import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  usePermission,
  useHasAnyPermission,
  useHasAllPermissions,
  MockAuthProvider,
  MOCK_USERS,
  useAuth,
} from '@fp/auth';
import type { ReactNode } from 'react';

// Clear localStorage before each test
beforeEach(() => {
  window.localStorage.clear();
});

// Helper component to select a mock user
function LoginAs({ userId }: { userId: string }) {
  const { login, selectMockUser, showLoginSelector, isLoading } = useAuth();

  if (isLoading) {
    return <div data-testid="loading">Loading...</div>;
  }

  if (showLoginSelector) {
    const mockUser = MOCK_USERS.find((u) => u.id === userId);
    if (mockUser) {
      // Trigger selection after render
      setTimeout(() => selectMockUser(mockUser), 0);
    }
    return <div data-testid="selecting">Selecting...</div>;
  }

  return (
    <button onClick={login} data-testid="login-trigger">
      Login
    </button>
  );
}

// Test component for usePermission
function PermissionTest({ permission }: { permission: string }) {
  const hasPermission = usePermission(permission);
  return (
    <div data-testid="permission-result">{hasPermission ? 'granted' : 'denied'}</div>
  );
}

// Test component for useHasAnyPermission
function AnyPermissionTest({ permissions }: { permissions: string[] }) {
  const hasAny = useHasAnyPermission(permissions);
  return <div data-testid="any-result">{hasAny ? 'granted' : 'denied'}</div>;
}

// Test component for useHasAllPermissions
function AllPermissionsTest({ permissions }: { permissions: string[] }) {
  const hasAll = useHasAllPermissions(permissions);
  return <div data-testid="all-result">{hasAll ? 'granted' : 'denied'}</div>;
}

function renderWithProvider(children: ReactNode) {
  return render(<MockAuthProvider>{children}</MockAuthProvider>);
}

describe('usePermission hook', () => {
  describe('when not authenticated', () => {
    it('returns false for any permission', async () => {
      renderWithProvider(<PermissionTest permission="farmers:read" />);

      await waitFor(() => {
        expect(screen.getByTestId('permission-result')).toHaveTextContent('denied');
      });
    });
  });

  describe('when authenticated as factory_manager', () => {
    it('returns true for farmers:read permission', async () => {
      const user = userEvent.setup();
      renderWithProvider(
        <>
          <LoginAs userId="mock-manager-001" />
          <PermissionTest permission="farmers:read" />
        </>
      );

      await waitFor(() => {
        expect(screen.getByTestId('login-trigger')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('login-trigger'));

      await waitFor(
        () => {
          expect(screen.getByTestId('permission-result')).toHaveTextContent('granted');
        },
        { timeout: 3000 }
      );
    });

    it('returns false for payment_policies:write permission', async () => {
      const user = userEvent.setup();
      renderWithProvider(
        <>
          <LoginAs userId="mock-manager-001" />
          <PermissionTest permission="payment_policies:write" />
        </>
      );

      await waitFor(() => {
        expect(screen.getByTestId('login-trigger')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('login-trigger'));

      await waitFor(
        () => {
          // Manager doesn't have payment_policies:write
          expect(screen.getByTestId('permission-result')).toHaveTextContent('denied');
        },
        { timeout: 3000 }
      );
    });
  });

  describe('when authenticated as platform_admin', () => {
    it('returns true for any permission (wildcard)', async () => {
      const user = userEvent.setup();
      renderWithProvider(
        <>
          <LoginAs userId="mock-admin-001" />
          <PermissionTest permission="anything:at:all" />
        </>
      );

      await waitFor(() => {
        expect(screen.getByTestId('login-trigger')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('login-trigger'));

      await waitFor(
        () => {
          expect(screen.getByTestId('permission-result')).toHaveTextContent('granted');
        },
        { timeout: 3000 }
      );
    });
  });
});

describe('useHasAnyPermission hook', () => {
  it('returns true if user has any of the permissions', async () => {
    const user = userEvent.setup();
    renderWithProvider(
      <>
        <LoginAs userId="mock-manager-001" />
        <AnyPermissionTest permissions={['farmers:read', 'payment_policies:write']} />
      </>
    );

    await waitFor(() => {
      expect(screen.getByTestId('login-trigger')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('login-trigger'));

    await waitFor(
      () => {
        // Manager has farmers:read
        expect(screen.getByTestId('any-result')).toHaveTextContent('granted');
      },
      { timeout: 3000 }
    );
  });

  it('returns false if user has none of the permissions', async () => {
    const user = userEvent.setup();
    renderWithProvider(
      <>
        <LoginAs userId="mock-clerk-001" />
        <AnyPermissionTest permissions={['payment_policies:write', 'factory_settings:write']} />
      </>
    );

    await waitFor(() => {
      expect(screen.getByTestId('login-trigger')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('login-trigger'));

    await waitFor(
      () => {
        // Clerk has only farmers:create
        expect(screen.getByTestId('any-result')).toHaveTextContent('denied');
      },
      { timeout: 3000 }
    );
  });
});

describe('useHasAllPermissions hook', () => {
  it('returns true if user has all permissions', async () => {
    const user = userEvent.setup();
    renderWithProvider(
      <>
        <LoginAs userId="mock-manager-001" />
        <AllPermissionsTest permissions={['farmers:read', 'quality_events:read']} />
      </>
    );

    await waitFor(() => {
      expect(screen.getByTestId('login-trigger')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('login-trigger'));

    await waitFor(
      () => {
        // Manager has both
        expect(screen.getByTestId('all-result')).toHaveTextContent('granted');
      },
      { timeout: 3000 }
    );
  });

  it('returns false if user is missing any permission', async () => {
    const user = userEvent.setup();
    renderWithProvider(
      <>
        <LoginAs userId="mock-manager-001" />
        <AllPermissionsTest permissions={['farmers:read', 'payment_policies:write']} />
      </>
    );

    await waitFor(() => {
      expect(screen.getByTestId('login-trigger')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('login-trigger'));

    await waitFor(
      () => {
        // Manager doesn't have payment_policies:write
        expect(screen.getByTestId('all-result')).toHaveTextContent('denied');
      },
      { timeout: 3000 }
    );
  });

  it('returns true for platform_admin regardless of permissions', async () => {
    const user = userEvent.setup();
    renderWithProvider(
      <>
        <LoginAs userId="mock-admin-001" />
        <AllPermissionsTest permissions={['any:permission', 'another:one']} />
      </>
    );

    await waitFor(() => {
      expect(screen.getByTestId('login-trigger')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('login-trigger'));

    await waitFor(
      () => {
        expect(screen.getByTestId('all-result')).toHaveTextContent('granted');
      },
      { timeout: 3000 }
    );
  });
});
