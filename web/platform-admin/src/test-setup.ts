/**
 * Test setup for Platform Admin
 *
 * Configures testing environment with happy-dom and testing-library matchers.
 */

import '@testing-library/jest-dom/vitest';

// Mock localStorage for happy-dom
const localStorageMock = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
  clear: () => {},
  length: 0,
  key: () => null,
};

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true,
});

// eslint-disable-next-line no-undef
Object.defineProperty(global, 'localStorage', {
  value: localStorageMock,
  writable: true,
});
