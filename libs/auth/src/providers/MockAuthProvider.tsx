/**
 * Mock authentication provider for development.
 *
 * Provides mock authentication with localStorage persistence.
 * Active when VITE_AUTH_PROVIDER=mock.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { AuthContext } from '../context/AuthContext';
import { generateMockToken, decodeToken } from '../mock/jwt';
import type { AuthProviderProps, User, MockUser, AuthContextValue } from '../types';

/** localStorage key for auth token */
const TOKEN_STORAGE_KEY = 'fp_auth_token';

/**
 * Mock authentication provider component.
 *
 * Manages authentication state using localStorage for token persistence.
 * Automatically restores session on mount if a valid token exists.
 *
 * @example
 * ```tsx
 * <MockAuthProvider>
 *   <App />
 * </MockAuthProvider>
 * ```
 */
export function MockAuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showLoginSelector, setShowLoginSelector] = useState(false);

  // Restore session from localStorage on mount
  useEffect(() => {
    async function restoreSession() {
      try {
        const storedToken = localStorage.getItem(TOKEN_STORAGE_KEY);
        if (storedToken) {
          const decodedUser = await decodeToken(storedToken);
          if (decodedUser) {
            setUser(decodedUser);
            setToken(storedToken);
          } else {
            // Token is expired or invalid, clear it
            localStorage.removeItem(TOKEN_STORAGE_KEY);
          }
        }
      } catch {
        // Error restoring session, clear storage
        localStorage.removeItem(TOKEN_STORAGE_KEY);
      } finally {
        setIsLoading(false);
      }
    }

    restoreSession();
  }, []);

  // Trigger login by showing the mock user selector
  const login = useCallback(() => {
    setShowLoginSelector(true);
  }, []);

  // Select a mock user and generate token
  const selectMockUser = useCallback(async (mockUser: MockUser) => {
    try {
      const newToken = await generateMockToken(mockUser);
      localStorage.setItem(TOKEN_STORAGE_KEY, newToken);
      setToken(newToken);
      setUser(mockUser);
      setShowLoginSelector(false);
    } catch (error) {
      console.error('Failed to generate mock token:', error);
      throw error;
    }
  }, []);

  // Clear session and logout
  const logout = useCallback(async () => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setUser(null);
    setShowLoginSelector(false);
  }, []);

  // Get the current access token
  const getAccessToken = useCallback(async (): Promise<string> => {
    if (!token) {
      throw new Error('Not authenticated');
    }
    return token;
  }, [token]);

  // Build context value
  const contextValue: AuthContextValue = useMemo(
    () => ({
      isAuthenticated: !!user,
      user,
      login,
      logout,
      getAccessToken,
      isLoading,
      showLoginSelector,
      selectMockUser,
    }),
    [user, login, logout, getAccessToken, isLoading, showLoginSelector, selectMockUser]
  );

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
}
