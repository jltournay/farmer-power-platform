/**
 * Mock login selector component for development.
 *
 * Displays available mock personas as buttons for quick login.
 * Uses inline styles to avoid MUI dependency.
 */

import { MOCK_USERS } from '../mock/users';
import type { MockUser } from '../types';

interface MockLoginSelectorProps {
  /** Callback when a user is selected */
  onSelect: (user: MockUser) => void;
}

/**
 * Get background color for role badge.
 */
function getRoleBadgeColor(role: string): string {
  switch (role) {
    case 'platform_admin':
      return '#fce7f3'; // Pink
    case 'factory_owner':
      return '#dbeafe'; // Blue
    case 'factory_manager':
      return '#d1fae5'; // Green
    case 'registration_clerk':
      return '#fef3c7'; // Yellow
    case 'regulator':
      return '#e0e7ff'; // Indigo
    default:
      return '#f3f4f6'; // Gray
  }
}

/**
 * Get text color for role badge.
 */
function getRoleBadgeTextColor(role: string): string {
  switch (role) {
    case 'platform_admin':
      return '#9d174d';
    case 'factory_owner':
      return '#1e40af';
    case 'factory_manager':
      return '#065f46';
    case 'registration_clerk':
      return '#92400e';
    case 'regulator':
      return '#3730a3';
    default:
      return '#374151';
  }
}

/**
 * Format role name for display.
 */
function formatRoleName(role: string): string {
  return role
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Mock login selector component.
 *
 * Displays all available mock personas with role badges and factory info.
 * Clicking a persona triggers the onSelect callback.
 *
 * @example
 * ```tsx
 * <MockLoginSelector onSelect={(user) => handleLogin(user)} />
 * ```
 */
export function MockLoginSelector({ onSelect }: MockLoginSelectorProps) {
  return (
    <div
      style={{
        padding: '24px',
        maxWidth: '480px',
        margin: '40px auto',
        fontFamily: 'Inter, system-ui, sans-serif',
      }}
    >
      <h2
        style={{
          marginBottom: '8px',
          fontSize: '24px',
          fontWeight: 600,
          color: '#1f2937',
        }}
      >
        Development Login
      </h2>
      <p
        style={{
          marginBottom: '24px',
          fontSize: '14px',
          color: '#6b7280',
        }}
      >
        Select a test user to continue
      </p>
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
        }}
      >
        {MOCK_USERS.map((user) => (
          <button
            key={user.id}
            onClick={() => onSelect(user)}
            style={{
              padding: '16px',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              cursor: 'pointer',
              textAlign: 'left',
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
              backgroundColor: '#ffffff',
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = '#16a34a';
              e.currentTarget.style.boxShadow = '0 2px 4px rgba(0, 0, 0, 0.05)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = '#e5e7eb';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            <span
              style={{
                padding: '4px 10px',
                backgroundColor: getRoleBadgeColor(user.role),
                color: getRoleBadgeTextColor(user.role),
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                whiteSpace: 'nowrap',
              }}
            >
              {formatRoleName(user.role)}
            </span>
            <div style={{ flex: 1 }}>
              <div
                style={{
                  fontWeight: 500,
                  color: '#1f2937',
                  fontSize: '15px',
                }}
              >
                {user.name}
              </div>
              <div
                style={{
                  fontSize: '13px',
                  color: '#6b7280',
                  marginTop: '2px',
                }}
              >
                {user.factory_id || user.region_ids.join(', ') || 'All access'}
              </div>
            </div>
          </button>
        ))}
      </div>
      <p
        style={{
          marginTop: '24px',
          fontSize: '12px',
          color: '#9ca3af',
          textAlign: 'center',
        }}
      >
        Mock authentication is only available in development mode
      </p>
    </div>
  );
}
