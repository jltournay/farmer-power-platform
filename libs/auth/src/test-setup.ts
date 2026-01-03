import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

// Create a proper localStorage mock with state
function createLocalStorageMock() {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: vi.fn((index: number) => Object.keys(store)[index] ?? null),
  };
}

const localStorageMock = createLocalStorageMock();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true,
});

// Set default mock environment variables
import.meta.env.VITE_MOCK_JWT_SECRET = 'test-secret-key-for-jwt-signing-32-chars';
import.meta.env.VITE_AUTH_PROVIDER = 'mock';
