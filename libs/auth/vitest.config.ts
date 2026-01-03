import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@fp/auth': resolve(__dirname, './src/index.ts'),
    },
  },
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: ['./src/test-setup.ts'],
    css: true,
    include: [
      '**/*.test.{ts,tsx}',
      '../../tests/unit/web/**/*auth*.test.{ts,tsx}',
      '../../tests/unit/web/**/*permission*.test.{ts,tsx}',
      '../../tests/unit/web/**/*protected*.test.{ts,tsx}',
      '../../tests/unit/web/**/*jwt*.test.{ts,tsx}',
    ],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'json-summary', 'html'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/test-setup.ts'],
    },
  },
});
