// Vitest global setup.
//
// Runs before any test file. Wires up:
//   * jest-dom matchers (toBeInTheDocument, toHaveTextContent, etc.)
//   * MSW server so every `fetch` in a component lands on our handlers
//   * Automatic cleanup after each test so DOM state doesn't leak between
//     tests and one test's handlers don't survive into the next.

import '@testing-library/jest-dom/vitest';

import { cleanup } from '@testing-library/react';
import { afterAll, afterEach, beforeAll } from 'vitest';

import { server } from './mocks/server';

beforeAll(() => {
  // `error` fails the test if a component makes an un-handled network call,
  // which catches "forgot to stub this endpoint" bugs immediately.
  server.listen({ onUnhandledRequest: 'error' });
});

afterEach(() => {
  cleanup();
  server.resetHandlers();
});

afterAll(() => {
  server.close();
});
