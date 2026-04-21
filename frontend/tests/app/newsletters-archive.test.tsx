import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import NewslettersPage from '@/app/user/newsletters/page';
import * as api from '@/lib/api';

vi.mock('@/lib/api');

describe('Newsletters Archive Page', () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  const mockNewsletters = [
    {
      id: 'nl-1',
      user_id: 'user-123',
      edition_date: '2026-04-20',
      status: 'published',
      generated_at: '2026-04-20T10:30:00Z',
      execution_path_taken: 'init,curate,write,editor_review',
      final_content: '<h1>Newsletter</h1><p>Content here</p>',
      draft_content: null,
    },
    {
      id: 'nl-2',
      user_id: 'user-123',
      edition_date: '2026-04-19',
      status: 'draft',
      generated_at: '2026-04-19T09:00:00Z',
      execution_path_taken: null,
      final_content: null,
      draft_content: 'Draft content',
    },
  ];

  it('prompts for user selection when no user selected', () => {
    vi.mocked(api.listUsers).mockResolvedValue({ total: 0, results: [] });
    vi.mocked(api.getNewsletterArchive).mockResolvedValueOnce({
      total: 0,
      results: [],
    });

    render(<NewslettersPage />);
    expect(screen.getByText('Please select a user to view their newsletters.')).toBeInTheDocument();
  });

  it('loads and displays newsletter list when user is selected', async () => {
    vi.mocked(api.listUsers).mockResolvedValue({ total: 0, results: [] });
    vi.mocked(api.getNewsletterArchive).mockResolvedValue({
      total: 2,
      results: mockNewsletters,
    });

    sessionStorage.setItem('selectedUserId', 'user-123');
    render(<NewslettersPage />);

    // Wait for the API to be called and data to render
    await waitFor(() => {
      expect(api.getNewsletterArchive).toHaveBeenCalled();
    }, { timeout: 2000 });

    // Check for newsletter data in sidebar
    expect(screen.getByText(/4\/20/)).toBeInTheDocument();
  });

  it('displays selected newsletter content', async () => {
    vi.mocked(api.listUsers).mockResolvedValue({ total: 0, results: [] });
    vi.mocked(api.getNewsletterArchive).mockResolvedValueOnce({
      total: 1,
      results: [mockNewsletters[0]],
    });

    sessionStorage.setItem('selectedUserId', 'user-123');
    render(<NewslettersPage />);

    await waitFor(() => {
      expect(screen.getByText('Newsletter')).toBeInTheDocument();
      expect(screen.getByText('Content here')).toBeInTheDocument();
    });
  });

  it('filters newsletters by date when date is selected', async () => {
    vi.mocked(api.listUsers).mockResolvedValue({ total: 0, results: [] });
    vi.mocked(api.getNewsletterArchive).mockResolvedValue({
      total: 1,
      results: [mockNewsletters[0]],
    });

    sessionStorage.setItem('selectedUserId', 'user-123');
    render(<NewslettersPage />);

    await waitFor(() => {
      expect(api.getNewsletterArchive).toHaveBeenCalled();
    });

    const dateInput = screen.getByDisplayValue('') as HTMLInputElement;
    fireEvent.change(dateInput, { target: { value: '2026-04-20' } });

    await waitFor(() => {
      expect(api.getNewsletterArchive).toHaveBeenCalledWith('user-123', '2026-04-20', 30);
    });
  });

  it('shows empty state when no newsletters found', async () => {
    vi.mocked(api.listUsers).mockResolvedValue({ total: 0, results: [] });
    vi.mocked(api.getNewsletterArchive).mockResolvedValueOnce({
      total: 0,
      results: [],
    });

    sessionStorage.setItem('selectedUserId', 'user-123');
    render(<NewslettersPage />);

    await waitFor(() => {
      expect(screen.getByText('No newsletters found')).toBeInTheDocument();
    });
  });

  it('displays error when fetch fails', async () => {
    vi.mocked(api.listUsers).mockResolvedValue({ total: 0, results: [] });
    vi.mocked(api.getNewsletterArchive).mockRejectedValueOnce(new Error('API error'));

    sessionStorage.setItem('selectedUserId', 'user-123');
    render(<NewslettersPage />);

    await waitFor(() => {
      expect(screen.getByText('API error')).toBeInTheDocument();
    });
  });
});
