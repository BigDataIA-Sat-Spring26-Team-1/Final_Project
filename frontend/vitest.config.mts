/// <reference types="vitest" />
import path from 'node:path';

import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// Vitest config kept separate from any Next.js tooling. The React plugin
// gives us JSX + fast refresh; jsdom provides a browser-ish environment so
// Testing Library can interact with the rendered tree.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
    include: ['tests/**/*.test.{ts,tsx}'],
    // MSW ships ESM; Vite needs to transform its deps via the default pipe.
    server: {
      deps: {
        inline: ['msw'],
      },
    },
  },
});
