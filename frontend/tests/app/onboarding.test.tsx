// Smoke + happy-path test for the onboarding page.
//
// Verifies the FormData upload flow end-to-end: the user picks a file, clicks
// "Run Extraction", and the extracted persona card renders in place.

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import UserOnboarding from '@/app/user/onboarding/page';

import { server } from '../mocks/server';

describe('UserOnboarding page', () => {
  it('renders the page scaffolding even before any interaction', () => {
    render(<UserOnboarding />);
    expect(screen.getByRole('heading', { name: /define your intelligence persona/i })).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/e\.g\. user-demo-001/i)).toBeInTheDocument();
  });

  it('prompts for a user id before uploading', async () => {
    const user = userEvent.setup();
    render(<UserOnboarding />);
    // Can't extract without picking files — button stays disabled.
    const runButton = screen.getByRole('button', { name: /run extraction/i });
    expect(runButton).toBeDisabled();

    await user.type(screen.getByPlaceholderText(/e\.g\. user-demo-001/i), 'user-42');
    // Still disabled because no file was picked.
    expect(runButton).toBeDisabled();
  });

  it('extracts a persona after picking a file and shows the archetype', async () => {
    const user = userEvent.setup();
    render(<UserOnboarding />);

    // Populate user_id
    await user.type(screen.getByPlaceholderText(/e\.g\. user-demo-001/i), 'user-42');

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
      http.post('http://localhost:8000/api/v1/personas/extract', () =>
        HttpResponse.json({ detail: 'Rate limited' }, { status: 429 }),
      ),
    );
    const user = userEvent.setup();
    render(<UserOnboarding />);

    await user.type(screen.getByPlaceholderText(/e\.g\. user-demo-001/i), 'user-42');
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(fileInput, new File(['bytes'], 'r.pdf', { type: 'application/pdf' }));
    await user.click(screen.getByRole('button', { name: /run extraction/i }));

    await waitFor(() => expect(screen.getByText(/429/)).toBeInTheDocument());
    expect(screen.getByText(/rate limited/i)).toBeInTheDocument();
  });
});
