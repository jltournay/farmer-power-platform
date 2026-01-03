/**
 * Mock JWT generation for development authentication.
 *
 * Uses jose library for HS256 signing, matching BFF mock token validation.
 * @see services/bff/src/bff/api/middleware/auth.py
 */

import { SignJWT, jwtVerify } from 'jose';
import type { MockUser, User } from '../types';

/** Default token expiry time in seconds (1 hour) */
const DEFAULT_EXPIRY_SECONDS = 3600;

/** JWT issuer for mock tokens */
const MOCK_ISSUER = 'mock-auth';

/** JWT audience for mock tokens */
const MOCK_AUDIENCE = 'farmer-power-bff';

/** Default secret for development/testing */
const DEFAULT_TEST_SECRET = 'default-test-secret-for-development-32-chars';

/**
 * Get the mock JWT secret from environment.
 *
 * Falls back to a default secret in development/test environments.
 */
function getSecret(): Uint8Array {
  const secret = import.meta.env.VITE_MOCK_JWT_SECRET || DEFAULT_TEST_SECRET;
  return new TextEncoder().encode(String(secret));
}

/**
 * Generate a mock JWT token for a user.
 *
 * Creates a JWT with HS256 signing containing all user claims.
 * Token structure matches BFF TokenClaims model exactly.
 *
 * @param user - Mock user to generate token for
 * @param expirySeconds - Token expiry time in seconds (default: 1 hour)
 * @returns Promise resolving to signed JWT string
 *
 * @example
 * ```typescript
 * const token = await generateMockToken(mockUser);
 * localStorage.setItem('auth_token', token);
 * ```
 */
export async function generateMockToken(
  user: MockUser,
  expirySeconds: number = DEFAULT_EXPIRY_SECONDS
): Promise<string> {
  const secret = getSecret();

  const token = await new SignJWT({
    sub: user.sub,
    email: user.email,
    name: user.name,
    role: user.role,
    factory_id: user.factory_id,
    factory_ids: user.factory_ids,
    collection_point_id: user.collection_point_id,
    region_ids: user.region_ids,
    permissions: user.permissions,
  })
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime(`${expirySeconds}s`)
    .setIssuer(MOCK_ISSUER)
    .setAudience(MOCK_AUDIENCE)
    .sign(secret);

  return token;
}

/**
 * Decode and verify a mock JWT token.
 *
 * Verifies the token signature and extracts user claims.
 *
 * @param token - JWT token string to decode
 * @returns Promise resolving to User object, or null if invalid/expired
 *
 * @example
 * ```typescript
 * const token = localStorage.getItem('auth_token');
 * if (token) {
 *   const user = await decodeToken(token);
 *   if (user) {
 *     // Token is valid, user is authenticated
 *   }
 * }
 * ```
 */
export async function decodeToken(token: string): Promise<User | null> {
  try {
    const secret = getSecret();
    const { payload } = await jwtVerify(token, secret, {
      issuer: MOCK_ISSUER,
      audience: MOCK_AUDIENCE,
    });

    // Extract user claims from payload
    const user: User = {
      sub: payload.sub as string,
      email: payload.email as string,
      name: payload.name as string,
      role: payload.role as string,
      factory_id: (payload.factory_id as string | null) ?? null,
      factory_ids: (payload.factory_ids as string[]) ?? [],
      collection_point_id: (payload.collection_point_id as string | null) ?? null,
      region_ids: (payload.region_ids as string[]) ?? [],
      permissions: (payload.permissions as string[]) ?? [],
    };

    return user;
  } catch {
    // Token is invalid or expired
    return null;
  }
}

/**
 * Check if a token is expired.
 *
 * @param token - JWT token string to check
 * @returns True if token is expired or invalid
 */
export async function isTokenExpired(token: string): Promise<boolean> {
  const user = await decodeToken(token);
  return user === null;
}
