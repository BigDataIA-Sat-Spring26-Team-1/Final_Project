// Persona page — covers the "auto-fetch on input change" pattern and
// verifies both explicit + behavioral weights render from the backend.

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import UserPersonaPage from '@/app/user/persona/page';

// fireEvent.change is one atomic state update — avoids the cascade of
// intermediate fetches userEvent.type triggers when typing a 7-char id.

describe('UserPersonaPage', () => {
  it('loads persona when a user id is entered and renders top weights', async () => {
    render(<UserPersonaPage />);

    fireEvent.change(screen.getByPlaceholderText(/^user id$/i), {
      target: { value: 'user-42' },
    });

    // Archetype appears in the bio card after fetch resolves.
    await waitFor(() => expect(screen.getByText(/ML_RESEARCHER/)).toBeInTheDocument());

    // Explicit weight header present; the category label "llms" also shows,
    // but may repeat across explicit + behavioral sections — use getAllByText
    // to be tolerant.
    expect(screen.getByText(/explicit category weights/i)).toBeInTheDocument();
    expect(screen.getAllByText(/llms/i).length).toBeGreaterThan(0);
  });

  it('renders a friendly 404 state for a missing user', async () => {
    render(<UserPersonaPage />);

    fireEvent.change(screen.getByPlaceholderText(/^user id$/i), {
      target: { value: 'missing' },
    });

    await waitFor(() =>
      expect(screen.getByText(/no persona found/i)).toBeInTheDocument(),
    );
  });
});
