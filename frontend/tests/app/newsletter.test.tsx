// Smoke + happy-path test for the newsletter page.
//
// Verifies the user can set a user id, pick a mode, and generate a draft that
// renders the returned HTML in the preview pane.

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import NewsletterPage from '@/app/newsletter/page';

describe('NewsletterPage', () => {
  it('renders heading and disables generate until user_id is set', () => {
    render(<NewsletterPage />);
    expect(screen.getByRole('heading', { name: /agentic newsletters/i })).toBeInTheDocument();
    const generateButton = screen.getByRole('button', { name: /generate new draft/i });
    expect(generateButton).toBeDisabled();
  });

  it('generates a draft and renders the returned HTML', async () => {
    const user = userEvent.setup();
    render(<NewsletterPage />);

    await user.type(screen.getByPlaceholderText(/e\.g\. user-demo-001/i), 'user-42');

    const generateButton = screen.getByRole('button', { name: /generate new draft/i });
    expect(generateButton).not.toBeDisabled();

    await user.click(generateButton);

    // MSW returns <h1>Daily Brief for user-42</h1>
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /daily brief for user-42/i })).toBeInTheDocument(),
    );

    // Polished mode is the default → execution path includes editor_review.
    expect(screen.getByText(/editor_review/)).toBeInTheDocument();
  });

  it('fast-mode toggle omits editor_review in the execution path', async () => {
    const user = userEvent.setup();
    render(<NewsletterPage />);

    await user.type(screen.getByPlaceholderText(/e\.g\. user-demo-001/i), 'user-42');
    await user.click(screen.getByRole('button', { name: /^fast/i }));
    await user.click(screen.getByRole('button', { name: /generate new draft/i }));

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /daily brief for user-42/i })).toBeInTheDocument(),
    );
    expect(screen.queryByText(/editor_review/)).not.toBeInTheDocument();
  });
});
