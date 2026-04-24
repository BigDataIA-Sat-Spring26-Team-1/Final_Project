// Smoke + happy-path test for the onboarding page.
//
// Verifies the FormData upload flow end-to-end: the user picks a file, clicks
// "Run Extraction", and the extracted persona card renders in place.

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';

// Mock the Next.js router + AuthProvider hooks. The component calls both at
// mount to hydrate the signed-in user id and redirect to /user after a
// successful persona save; the test environment has neither an <AppRouter>
// nor an <AuthProvider>, so we stub them out here.
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    replace: vi.fn(),
    push: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
}));
vi.mock('@/components/AuthProvider', () => ({
  useAuth: () => ({
    // Seed an authed user so the onboarding page auto-fills user_id
    // from the context — the input box was removed in favour of that
    // auto-fill, and every request body now derives from this id.
    user: { id: 'user-42', email: 'test@example.com', role: 'USER' },
    status: 'authenticated',
    hasPersona: null,
    hasCompanyProfile: null,
    login: vi.fn(),
    signup: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn(),
    markPersonaPresent: vi.fn(),
    markCompanyProfileComplete: vi.fn(),
  }),
}));

import UserOnboarding from '@/app/user/onboarding/page';

import { server } from '../mocks/server';

describe('UserOnboarding page', () => {
  it('renders the page scaffolding even before any interaction', () => {
    render(<UserOnboarding />);
    expect(screen.getByRole('heading', { name: /define your intelligence persona/i })).toBeInTheDocument();
    // user_id input is no longer rendered — the page derives the id
    // from the auth context and the Run Extraction button gates the flow.
    expect(screen.getByRole('button', { name: /run extraction/i })).toBeInTheDocument();
  });

  it('keeps extraction disabled until a file is picked', () => {
    render(<UserOnboarding />);
    const runButton = screen.getByRole('button', { name: /run extraction/i });
    expect(runButton).toBeDisabled();
  });

  it('extracts a persona after picking a file and shows the archetype', async () => {
    // The onboarding gate now probes /personas/{id}; route that probe to 404
    // so the page stays in "new user" mode for the happy-path test.
    server.use(
      http.get('http://localhost:8000/api/v1/personas/:userId', () =>
        HttpResponse.json({ detail: 'not found' }, { status: 404 }),
      ),
    );
    const user = userEvent.setup();
    render(<UserOnboarding />);

    // The file input is visually-hidden with class sr-only; locate via role.
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['pdf bytes'], 'resume.pdf', { type: 'application/pdf' });
    await user.upload(fileInput, file);

    await user.click(screen.getByRole('button', { name: /run extraction/i }));

    // The MSW handler returns archetype ML_RESEARCHER — wait for it to render.
    await waitFor(() =>
      expect(screen.getByText('ML_RESEARCHER')).toBeInTheDocument(),
    );
    expect(screen.getByText(/extraction complete/i)).toBeInTheDocument();
  });

  it('surfaces backend errors inline', async () => {
    server.use(
      http.get('http://localhost:8000/api/v1/personas/:userId', () =>
        HttpResponse.json({ detail: 'not found' }, { status: 404 }),
      ),
      http.post('http://localhost:8000/api/v1/personas/extract', () =>
        HttpResponse.json({ detail: 'Rate limited' }, { status: 429 }),
      ),
    );
    const user = userEvent.setup();
    render(<UserOnboarding />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(fileInput, new File(['bytes'], 'r.pdf', { type: 'application/pdf' }));
    await user.click(screen.getByRole('button', { name: /run extraction/i }));

    await waitFor(() => expect(screen.getByText(/429/)).toBeInTheDocument());
    expect(screen.getByText(/rate limited/i)).toBeInTheDocument();
  });
});
