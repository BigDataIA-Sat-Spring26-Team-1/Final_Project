// MSW server singleton shared across the whole test run.
//
// Tests can override individual handlers with `server.use(...)` when they need
// to simulate specific responses (errors, empty states, etc.). Handlers reset
// between tests — see tests/setup.ts.

import { setupServer } from 'msw/node';

import { handlers } from './handlers';

export const server = setupServer(...handlers);
