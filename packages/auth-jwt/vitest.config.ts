import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
  },
  resolve: {
    alias: {
      '@weirdfingers/boards': path.resolve(__dirname, '../frontend/src/index.ts'),
    },
  },
});
