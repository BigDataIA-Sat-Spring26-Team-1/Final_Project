import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { UserSwitcher } from '@/components/UserSwitcher';
import { CompanySwitcher } from '@/components/CompanySwitcher';
import * as api from '@/lib/api';

vi.mock('@/lib/api');

describe('User Switcher', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockUsers = [
    {
      id: 'user-1',
      email: 'alice@example.com',
      full_name: 'Alice Johnson',
      created_at: '2026-01-01T00:00:00Z',
    },
    {
      id: 'user-2',
      email: 'bob@example.com',
      full_name: 'Bob Smith',
      created_at: '2026-01-02T00:00:00Z',
    },
  ];

  it('renders with current user display', async () => {
    vi.mocked(api.listUsers).mockResolvedValueOnce({
      total: 2,
      results: mockUsers,
    });

    render(<UserSwitcher currentUserId="user-1" onSelect={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Alice Johnson')).toBeInTheDocument();
    });
  });

  it('opens dropdown and loads users on button click', async () => {
    vi.mocked(api.listUsers).mockResolvedValue({
      total: 2,
      results: mockUsers,
    });

    render(<UserSwitcher currentUserId="user-1" onSelect={vi.fn()} />);

    await waitFor(() => {
      expect(api.listUsers).toHaveBeenCalled();
    });

    const button = screen.getByRole('button', { name: /Alice Johnson/i });
    fireEvent.click(button);

    expect(screen.getByText('Bob Smith')).toBeInTheDocument();
  });

  it('calls onSelect when user is clicked', async () => {
    const onSelect = vi.fn();

    vi.mocked(api.listUsers).mockResolvedValue({
      total: 2,
      results: mockUsers,
    });

    render(<UserSwitcher currentUserId="user-1" onSelect={onSelect} />);

    await waitFor(() => {
      expect(api.listUsers).toHaveBeenCalled();
    });

    const button = screen.getByRole('button', { name: /Alice Johnson/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText('Bob Smith')).toBeInTheDocument();
    });

    const bobButton = screen.getByRole('button', { name: /bob@example.com/i });
    fireEvent.click(bobButton);

    expect(onSelect).toHaveBeenCalledWith('user-2');
  });

  it('displays error when user list fails to load', async () => {
    vi.mocked(api.listUsers).mockRejectedValueOnce(new Error('Network error'));

    render(<UserSwitcher currentUserId="user-1" onSelect={vi.fn()} />);

    const button = screen.getByRole('button', { name: /Select User/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
  });
});

describe('Company Switcher', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockCompanies = [
    {
      id: 'company-1',
      name: 'Acme Corp',
      domain: 'acme.com',
      industry: 'Technology',
      created_at: '2026-01-01T00:00:00Z',
    },
    {
      id: 'company-2',
      name: 'TechStart Inc',
      domain: 'techstart.io',
      industry: 'SaaS',
      created_at: '2026-01-02T00:00:00Z',
    },
  ];

  it('renders with current company display', async () => {
    vi.mocked(api.listCompanies).mockResolvedValueOnce({
      total: 2,
      results: mockCompanies,
    });

    render(<CompanySwitcher currentCompanyId="company-1" onSelect={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
  });

  it('opens dropdown and loads companies on button click', async () => {
    vi.mocked(api.listCompanies).mockResolvedValue({
      total: 2,
      results: mockCompanies,
    });

    render(<CompanySwitcher currentCompanyId="company-1" onSelect={vi.fn()} />);

    await waitFor(() => {
      expect(api.listCompanies).toHaveBeenCalled();
    });

    const button = screen.getByRole('button', { name: /Acme Corp/i });
    fireEvent.click(button);

    expect(screen.getByText('TechStart Inc')).toBeInTheDocument();
  });

  it('calls onSelect when company is clicked', async () => {
    const onSelect = vi.fn();

    vi.mocked(api.listCompanies).mockResolvedValue({
      total: 2,
      results: mockCompanies,
    });

    render(<CompanySwitcher currentCompanyId="company-1" onSelect={onSelect} />);

    await waitFor(() => {
      expect(api.listCompanies).toHaveBeenCalled();
    });

    const button = screen.getByRole('button', { name: /Acme Corp/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText('TechStart Inc')).toBeInTheDocument();
    });

    const techStartButtons = screen.getAllByRole('button');
    const techStartBtn = techStartButtons.find(b => b.textContent?.includes('TechStart Inc'));
    if (techStartBtn) {
      fireEvent.click(techStartBtn);
    }

    expect(onSelect).toHaveBeenCalledWith('company-2');
  });

  it('displays industry information in dropdown', async () => {
    vi.mocked(api.listCompanies).mockResolvedValue({
      total: 1,
      results: [mockCompanies[0]],
    });

    render(<CompanySwitcher currentCompanyId={null} onSelect={vi.fn()} />);

    await waitFor(() => {
      expect(api.listCompanies).toHaveBeenCalled();
    });

    const button = screen.getByRole('button', { name: /Select Company/i });
    fireEvent.click(button);

    expect(screen.getByText('Technology')).toBeInTheDocument();
  });
});
