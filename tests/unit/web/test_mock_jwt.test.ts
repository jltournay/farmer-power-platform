import { describe, it, expect, beforeEach } from 'vitest';
import {
  generateMockToken,
  decodeToken,
  isTokenExpired,
  getMockUserById,
  getMockUserByRole,
  MOCK_USERS,
} from '@fp/auth';
import type { MockUser } from '@fp/auth';

describe('Mock JWT', () => {
  const mockUser: MockUser = {
    id: 'test-user-001',
    sub: 'test-user-001',
    email: 'test@example.com',
    name: 'Test User',
    role: 'factory_manager',
    factory_id: 'KEN-FAC-001',
    factory_ids: ['KEN-FAC-001'],
    collection_point_id: null,
    region_ids: [],
    permissions: ['farmers:read', 'quality_events:read'],
  };

  beforeEach(() => {
    // Env is already set in test-setup.ts
  });

  describe('generateMockToken', () => {
    it('generates a valid JWT token', async () => {
      const token = await generateMockToken(mockUser);

      expect(token).toBeDefined();
      expect(typeof token).toBe('string');
      // JWT has 3 parts separated by dots
      expect(token.split('.').length).toBe(3);
    });

    it('includes all user claims in the token', async () => {
      const token = await generateMockToken(mockUser);
      const decoded = await decodeToken(token);

      expect(decoded).not.toBeNull();
      expect(decoded?.sub).toBe(mockUser.sub);
      expect(decoded?.email).toBe(mockUser.email);
      expect(decoded?.name).toBe(mockUser.name);
      expect(decoded?.role).toBe(mockUser.role);
      expect(decoded?.factory_id).toBe(mockUser.factory_id);
      expect(decoded?.factory_ids).toEqual(mockUser.factory_ids);
      expect(decoded?.collection_point_id).toBe(mockUser.collection_point_id);
      expect(decoded?.region_ids).toEqual(mockUser.region_ids);
      expect(decoded?.permissions).toEqual(mockUser.permissions);
    });

    it('generates different tokens for different users', async () => {
      const adminUser: MockUser = {
        ...mockUser,
        id: 'admin',
        sub: 'admin',
        role: 'platform_admin',
      };

      const token1 = await generateMockToken(mockUser);
      const token2 = await generateMockToken(adminUser);

      expect(token1).not.toBe(token2);
    });
  });

  describe('decodeToken', () => {
    it('decodes a valid token', async () => {
      const token = await generateMockToken(mockUser);
      const decoded = await decodeToken(token);

      expect(decoded).not.toBeNull();
      expect(decoded?.sub).toBe(mockUser.sub);
    });

    it('returns null for invalid token', async () => {
      const decoded = await decodeToken('invalid-token');

      expect(decoded).toBeNull();
    });

    it('returns null for tampered token', async () => {
      const token = await generateMockToken(mockUser);
      const tamperedToken = token.slice(0, -5) + 'XXXXX';

      const decoded = await decodeToken(tamperedToken);

      expect(decoded).toBeNull();
    });

    it('returns null for expired token', async () => {
      // Generate token with 0 second expiry (immediately expired)
      const token = await generateMockToken(mockUser, 0);

      // Wait a bit to ensure expiry
      await new Promise((resolve) => setTimeout(resolve, 100));

      const decoded = await decodeToken(token);

      expect(decoded).toBeNull();
    });
  });

  describe('isTokenExpired', () => {
    it('returns false for valid non-expired token', async () => {
      const token = await generateMockToken(mockUser);

      const expired = await isTokenExpired(token);

      expect(expired).toBe(false);
    });

    it('returns true for expired token', async () => {
      // Generate token with 0 second expiry
      const token = await generateMockToken(mockUser, 0);

      // Wait for expiry
      await new Promise((resolve) => setTimeout(resolve, 100));

      const expired = await isTokenExpired(token);

      expect(expired).toBe(true);
    });

    it('returns true for invalid token', async () => {
      const expired = await isTokenExpired('invalid-token');

      expect(expired).toBe(true);
    });

    it('returns true for tampered token', async () => {
      const token = await generateMockToken(mockUser);
      const tampered = token.slice(0, -5) + 'XXXXX';

      const expired = await isTokenExpired(tampered);

      expect(expired).toBe(true);
    });
  });

  describe('token structure', () => {
    it('matches BFF TokenClaims structure', async () => {
      const token = await generateMockToken(mockUser);
      const decoded = await decodeToken(token);

      // Verify all expected fields exist
      expect(decoded).toHaveProperty('sub');
      expect(decoded).toHaveProperty('email');
      expect(decoded).toHaveProperty('name');
      expect(decoded).toHaveProperty('role');
      expect(decoded).toHaveProperty('factory_id');
      expect(decoded).toHaveProperty('factory_ids');
      expect(decoded).toHaveProperty('collection_point_id');
      expect(decoded).toHaveProperty('region_ids');
      expect(decoded).toHaveProperty('permissions');
    });

    it('handles null factory_id correctly', async () => {
      const adminUser: MockUser = {
        ...mockUser,
        id: 'admin',
        factory_id: null,
        factory_ids: [],
      };

      const token = await generateMockToken(adminUser);
      const decoded = await decodeToken(token);

      expect(decoded?.factory_id).toBeNull();
      expect(decoded?.factory_ids).toEqual([]);
    });

    it('handles region_ids for regulators', async () => {
      const regulatorUser: MockUser = {
        ...mockUser,
        id: 'regulator',
        role: 'regulator',
        factory_id: null,
        factory_ids: [],
        region_ids: ['nandi', 'kericho'],
      };

      const token = await generateMockToken(regulatorUser);
      const decoded = await decodeToken(token);

      expect(decoded?.region_ids).toEqual(['nandi', 'kericho']);
    });
  });
});

describe('Mock User Utilities', () => {
  describe('getMockUserById', () => {
    it('returns mock user by ID', () => {
      const user = getMockUserById('mock-manager-001');

      expect(user).not.toBeUndefined();
      expect(user?.id).toBe('mock-manager-001');
      expect(user?.name).toBe('Jane Mwangi');
      expect(user?.role).toBe('factory_manager');
    });

    it('returns undefined for non-existent ID', () => {
      const user = getMockUserById('non-existent-id');

      expect(user).toBeUndefined();
    });

    it('finds all 5 mock users by ID', () => {
      const ids = [
        'mock-manager-001',
        'mock-owner-001',
        'mock-admin-001',
        'mock-clerk-001',
        'mock-regulator-001',
      ];

      ids.forEach((id) => {
        const user = getMockUserById(id);
        expect(user).not.toBeUndefined();
        expect(user?.id).toBe(id);
      });
    });
  });

  describe('getMockUserByRole', () => {
    it('returns mock user by role', () => {
      const user = getMockUserByRole('factory_manager');

      expect(user).not.toBeUndefined();
      expect(user?.role).toBe('factory_manager');
    });

    it('returns undefined for non-existent role', () => {
      const user = getMockUserByRole('non_existent_role');

      expect(user).toBeUndefined();
    });

    it('finds users for all 5 roles', () => {
      const roles = [
        'factory_manager',
        'factory_owner',
        'platform_admin',
        'registration_clerk',
        'regulator',
      ];

      roles.forEach((role) => {
        const user = getMockUserByRole(role);
        expect(user).not.toBeUndefined();
        expect(user?.role).toBe(role);
      });
    });
  });

  describe('MOCK_USERS constant', () => {
    it('contains exactly 5 mock users', () => {
      expect(MOCK_USERS.length).toBe(5);
    });

    it('each mock user has required fields', () => {
      MOCK_USERS.forEach((user) => {
        expect(user.id).toBeDefined();
        expect(user.sub).toBeDefined();
        expect(user.email).toBeDefined();
        expect(user.name).toBeDefined();
        expect(user.role).toBeDefined();
        expect(user.permissions).toBeDefined();
        expect(Array.isArray(user.permissions)).toBe(true);
      });
    });
  });
});
