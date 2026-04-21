import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import UserProfilePage from '@/app/user/profile/page';
import * as api from '@/lib/api';

vi.mock('@/lib/api');

describe('User Profile Page', () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  it('renders user switcher and prompts for selection', async () => {
    render(<UserProfilePage />);
    expect(screen.getByText('User Profile')).toBeInTheDocument();
    expect(screen.getByText(/Please select a user/)).toBeInTheDocument();
  });

  it('loads and displays persona data when user is selected', async () => {
    const mockPersona = {
      user_id: 'user-123',
      job_title: 'Senior Engineer',
      seniority: 'senior',
      persona_archetype: 'ML_RESEARCHER',
      bio_summary: 'Passionate about machine learning.',
      explicit_category_weights: { llms: 0.9, ai_agents: 0.7 },
      behavioral_category_weights: { security: 0.5 },
    };

    vi.mocked(api.getPersona).mockResolvedValueOnce(mockPersona);

    const { rerender } = render(<UserProfilePage />);

    // Simulate selecting user
    sessionStorage.setItem('selectedUserId', 'user-123');
    rerender(<UserProfilePage />);

    await waitFor(() => {
      expect(api.getPersona).toHaveBeenCalledWith('user-123');
    });

    expect(screen.getByDisplayValue('Senior Engineer')).toBeInTheDocument();
    expect(screen.getByDisplayValue('senior')).toBeInTheDocument();
  });

  it('saves profile updates and shows success message', async () => {
    const mockPersona = {
      user_id: 'user-123',
      job_title: 'Engineer',
      seniority: 'mid',
      persona_archetype: null,
      bio_summary: null,
      explicit_category_weights: {},
      behavioral_category_weights: {},
    };

    vi.mocked(api.getPersona).mockResolvedValueOnce(mockPersona);
    vi.mocked(api.updateUserProfile).mockResolvedValueOnce({ user_id: 'user-123', status: 'updated' });

    sessionStorage.setItem('selectedUserId', 'user-123');
    const { rerender } = render(<UserProfilePage />);
    rerender(<UserProfilePage />);

    await waitFor(() => {
      expect(api.getPersona).toHaveBeenCalledWith('user-123');
    });

    const jobTitleInput = screen.getByPlaceholderText('e.g., Senior Machine Learning Engineer');
    fireEvent.change(jobTitleInput, { target: { value: 'Principal Engineer' } });

    const saveButton = screen.getByRole('button', { name: /Save Profile/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(api.updateUserProfile).toHaveBeenCalled();
      expect(screen.getByText('Profile updated successfully!')).toBeInTheDocument();
    });
  });

  it('displays error message on save failure', async () => {
    const mockPersona = {
      user_id: 'user-123',
      job_title: '',
      seniority: '',
      persona_archetype: null,
      bio_summary: null,
      explicit_category_weights: {},
      behavioral_category_weights: {},
    };

    vi.mocked(api.getPersona).mockResolvedValueOnce(mockPersona);
    vi.mocked(api.updateUserProfile).mockRejectedValueOnce(new Error('Network error'));

    sessionStorage.setItem('selectedUserId', 'user-123');
    const { rerender } = render(<UserProfilePage />);
    rerender(<UserProfilePage />);

    await waitFor(() => {
      expect(api.getPersona).toHaveBeenCalledWith('user-123');
    });

    const saveButton = screen.getByRole('button', { name: /Save Profile/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
  });
});
