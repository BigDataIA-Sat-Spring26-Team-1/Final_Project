import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AdminManagementPanel } from '@/components/AdminManagementPanel';
import * as api from '@/lib/api';

vi.mock('@/lib/api');

describe('Admin Management Panel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Create User Tab', () => {
    it('renders create user form', () => {
      render(<AdminManagementPanel />);
      expect(screen.getByPlaceholderText('user@example.com')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('John Doe')).toBeInTheDocument();
    });

    it('requires email before submission', () => {
      render(<AdminManagementPanel />);
      const createButton = screen.getByRole('button', { name: /Create User/i });
      expect(createButton).toBeDisabled();
    });

    it('creates user successfully and shows success message', async () => {
      vi.mocked(api.createUser).mockResolvedValueOnce({
        id: 'user-123',
        email: 'test@example.com',
        status: 'created',
      });

      render(<AdminManagementPanel />);

      const emailInput = screen.getByPlaceholderText('user@example.com');
      const nameInput = screen.getByPlaceholderText('John Doe');
      const createButton = screen.getByRole('button', { name: /Create User/i });

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.change(nameInput, { target: { value: 'John Doe' } });
      fireEvent.click(createButton);

      await waitFor(() => {
        expect(api.createUser).toHaveBeenCalledWith('test@example.com', 'John Doe');
        expect(screen.getByText('User created successfully!')).toBeInTheDocument();
      });

      expect((emailInput as HTMLInputElement).value).toBe('');
    });

    it('displays error on creation failure', async () => {
      vi.mocked(api.createUser).mockRejectedValueOnce(new Error('Email already exists'));

      render(<AdminManagementPanel />);

      const emailInput = screen.getByPlaceholderText('user@example.com');
      const createButton = screen.getByRole('button', { name: /Create User/i });

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.click(createButton);

      await waitFor(() => {
        expect(screen.getByText('Email already exists')).toBeInTheDocument();
      });
    });
  });

  describe('Create Company Tab', () => {
    it('renders create company form', () => {
      render(<AdminManagementPanel />);
      const companyTab = screen.getByRole('button', { name: /Create Company/i });
      fireEvent.click(companyTab);

      expect(screen.getByPlaceholderText('Acme Corporation')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('acme.com')).toBeInTheDocument();
    });

    it('requires company name before submission', () => {
      render(<AdminManagementPanel />);
      const companyTab = screen.getByRole('button', { name: /Create Company/i });
      fireEvent.click(companyTab);

      const createButton = screen.getAllByRole('button', { name: /Create Company/i })[1];
      expect(createButton).toBeDisabled();
    });

    it('creates company successfully', async () => {
      vi.mocked(api.createCompany).mockResolvedValueOnce({
        id: 'company-123',
        name: 'Acme Corp',
        status: 'created',
      });

      render(<AdminManagementPanel />);
      const companyTab = screen.getByRole('button', { name: /Create Company/i });
      fireEvent.click(companyTab);

      const nameInput = screen.getByPlaceholderText('Acme Corporation');
      fireEvent.change(nameInput, { target: { value: 'Acme Corp' } });

      const buttons = screen.getAllByRole('button');
      const createButton = buttons.find(btn => btn.textContent?.includes('Create Company'));
      if (createButton) {
        fireEvent.click(createButton);
      }

      await waitFor(() => {
        expect(api.createCompany).toHaveBeenCalled();
        expect(screen.getByText('Company created successfully!')).toBeInTheDocument();
      });
    });
  });

  describe('Trigger Pipeline Tab', () => {
    it('renders pipeline trigger section', () => {
      render(<AdminManagementPanel />);
      const pipelineTab = screen.getByRole('button', { name: /Trigger Pipeline/i });
      fireEvent.click(pipelineTab);

      expect(screen.getByText(/Fetch articles from RSS/)).toBeInTheDocument();
    });

    it('triggers ingestion pipeline and shows result', async () => {
      vi.mocked(api.triggerAdminIngestion).mockResolvedValueOnce({
        status: 'accepted',
        message: 'Pipeline started with 150 articles.',
        started_at: '2026-04-21T12:00:00Z',
        job_id: null,
      });

      render(<AdminManagementPanel />);
      const pipelineTab = screen.getByRole('button', { name: /Trigger Pipeline/i });
      fireEvent.click(pipelineTab);

      const triggerButton = screen.getByRole('button', { name: /Trigger Force Sync/i });
      fireEvent.click(triggerButton);

      await waitFor(() => {
        expect(api.triggerAdminIngestion).toHaveBeenCalled();
        expect(screen.getByText('Pipeline triggered successfully!')).toBeInTheDocument();
        expect(screen.getByText('Pipeline started with 150 articles.')).toBeInTheDocument();
      });
    });

    it('displays error on pipeline failure', async () => {
      vi.mocked(api.triggerAdminIngestion).mockRejectedValueOnce(
        new Error('Pipeline already running'),
      );

      render(<AdminManagementPanel />);
      const pipelineTab = screen.getByRole('button', { name: /Trigger Pipeline/i });
      fireEvent.click(pipelineTab);

      const triggerButton = screen.getByRole('button', { name: /Trigger Force Sync/i });
      fireEvent.click(triggerButton);

      await waitFor(() => {
        expect(screen.getByText('Pipeline already running')).toBeInTheDocument();
      });
    });
  });
});
