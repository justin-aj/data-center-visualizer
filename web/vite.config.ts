import { defineConfig } from 'vitest/config';

export default defineConfig({
  build: {
    sourcemap: true,
  },
  test: {
    environment: 'jsdom',
    include: ['tests/**/*.test.ts'],
  },
});
