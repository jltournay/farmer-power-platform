import { describe, it, expect, beforeEach } from 'vitest';
import { generateMockToken, decodeToken } from '@fp/auth';
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
