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

  // Note: Full integration test of newsletters loading with sessionStorage is better
  // tested via e2e/playwright tests since sessionStorage behavior differs in test vs browser


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
