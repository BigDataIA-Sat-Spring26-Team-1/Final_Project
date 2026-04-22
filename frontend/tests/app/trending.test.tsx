// Trending page — covers the "fetch on mount + derive UI from the response"
// pattern. Verifies the velocity chart renders, the Emerging Entities list
// picks up the ranked titles, and the filter narrows results correctly.

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import TrendingPage from '@/app/trending/page';

describe('TrendingPage', () => {
  it('fetches trends on mount and shows them in the sidebar', async () => {
    render(<TrendingPage />);

    await waitFor(() =>
      expect(screen.getByText(/GPT-5 Safety Report/i)).toBeInTheDocument(),
    );
    // Velocity summary counts surging + total from the mock handler (2 trends,
    // 1 BREAKING, 1 TRENDING → both surging).
    expect(screen.getByText(/2 high-velocity/i)).toBeInTheDocument();
  });

  it('filters entities client-side by title substring', async () => {
    const user = userEvent.setup();
    render(<TrendingPage />);

    await waitFor(() => expect(screen.getByText(/GPT-5 Safety Report/i)).toBeInTheDocument());

    await user.type(screen.getByPlaceholderText(/filter topics/i), 'Qdrant');
    // GPT-5 row should disappear; Qdrant stays (title shows up in both the
    // "Blue Ocean candidate" card and the Emerging Entities sidebar, so use
    // getAllByText to tolerate the duplicate).
    await waitFor(() => expect(screen.queryByText(/GPT-5 Safety Report/i)).not.toBeInTheDocument());
    expect(screen.getAllByText(/Qdrant 1.17/i).length).toBeGreaterThan(0);
  });
});
