// Admin editorial review page — covers URL-driven generation. Stubs
// `next/navigation` so `useSearchParams()` returns controlled values.
// Approve + Reject buttons should render disabled with explanatory tooltips.

import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import NewsletterReviewPage from '@/app/admin/newsletters/review/page';

// Next.js App Router navigation hooks aren't backed by a real router in
// jsdom; mock the pieces this page actually consumes.
vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams('user_id=user-42&mode=polished'),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => '/admin/newsletters/review',
}));

describe('Admin editorial review', () => {
  it('auto-generates a draft using the query params and renders the HTML', async () => {
    render(<NewsletterReviewPage />);

    // MSW returns <h1>Daily Brief for user-42</h1>
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /daily brief for user-42/i })).toBeInTheDocument(),
    );
  });

  it('keeps Approve and Reject disabled with tooltips pointing at the missing endpoints', async () => {
    render(<NewsletterReviewPage />);

    const reject = screen.getByRole('button', { name: /reject/i });
    const approve = screen.getByRole('button', { name: /approve & dispatch/i });

    expect(reject).toBeDisabled();
    expect(approve).toBeDisabled();
    expect(reject.getAttribute('title') ?? '').toMatch(/reject endpoint/i);
    expect(approve.getAttribute('title') ?? '').toMatch(/approve/i);
  });
});
