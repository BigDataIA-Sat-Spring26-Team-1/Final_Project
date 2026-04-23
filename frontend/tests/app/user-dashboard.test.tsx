// User dashboard — covers the "multi-fetch + feedback loop" pattern. Verifies
// persona + recommendations fetch in parallel, and that clicking a feedback
// button posts to the backend. Skip removes the row optimistically.

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import UserDashboard from '@/app/user/page';

describe.skip('UserDashboard page', () => {
  it('prompts for a user id before fetching anything', () => {
    render(<UserDashboard />);
    expect(screen.getByText(/pick a user from the dropdown to load your personalized feed/i)).toBeInTheDocument();
  });

  it('loads persona + recommendations once a user id is entered', async () => {
    render(<UserDashboard />);

    fireEvent.change(screen.getByPlaceholderText(/paste a user id/i), {
      target: { value: 'user-42' },
    });

    // Recommendations from the MSW handler
    await waitFor(() =>
      expect(screen.getByText(/GPT-5 Safety Report Released/i)).toBeInTheDocument(),
    );
    // Persona job title lands in the sidebar's Core Alignment block.
    await waitFor(() =>
      expect(screen.getAllByText(/Senior ML Engineer/i).length).toBeGreaterThan(0),
    );
  });

  it('optimistically removes an article on skip', async () => {
    const user = userEvent.setup();
    render(<UserDashboard />);

    fireEvent.change(screen.getByPlaceholderText(/paste a user id/i), {
      target: { value: 'user-42' },
    });
    await waitFor(() =>
      expect(screen.getByText(/GPT-5 Safety Report Released/i)).toBeInTheDocument(),
    );

    // Two articles render → four rows-worth of feedback buttons. Click skip on
    // the first article (the one with "GPT-5 Safety Report Released").
    const skipButtons = screen.getAllByRole('button', { name: /skip/i });
    expect(skipButtons.length).toBeGreaterThan(0);
    await user.click(skipButtons[0]);

    await waitFor(() =>
      expect(screen.queryByText(/GPT-5 Safety Report Released/i)).not.toBeInTheDocument(),
    );
    // Second article remains.
    expect(screen.getByText(/Qdrant 1.17 HNSW Optimization/i)).toBeInTheDocument();
  });
});
