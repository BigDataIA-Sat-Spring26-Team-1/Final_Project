'use client';

import { useEffect, useState } from 'react';
import { ChevronDown, Loader2 } from 'lucide-react';
import { listCompanies } from '@/lib/api';
import type { CompanyListItem } from '@/lib/api';

interface CompanySwitcherProps {
  currentCompanyId: string | null;
  onSelect: (companyId: string) => void;
}

export function CompanySwitcher({ currentCompanyId, onSelect }: CompanySwitcherProps) {
  const [companies, setCompanies] = useState<CompanyListItem[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentCompany = companies.find(c => c.id === currentCompanyId);

  useEffect(() => {
    const fetchCompanies = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const res = await listCompanies(100);
        setCompanies(res.results);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load companies');
      } finally {
        setIsLoading(false);
      }
    };

    fetchCompanies();
  }, []);

  const handleSelect = (companyId: string) => {
    onSelect(companyId);
    setIsOpen(false);
  };

  return (
    <div className="relative inline-block">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 transition"
      >
        <span className="text-sm font-medium text-slate-700">
          {currentCompany?.name || 'Select Company'}
        </span>
        <ChevronDown className="w-4 h-4 text-slate-500" />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-64 bg-white border border-slate-200 rounded-lg shadow-lg z-50">
          {isLoading ? (
            <div className="p-4 flex items-center justify-center gap-2 text-slate-500">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Loading companies...</span>
            </div>
          ) : error ? (
            <div className="p-4 text-sm text-red-600">{error}</div>
          ) : companies.length === 0 ? (
            <div className="p-4 text-sm text-slate-500">No companies found</div>
          ) : (
            <ul className="max-h-64 overflow-y-auto">
              {companies.map(company => (
                <li key={company.id}>
                  <button
                    onClick={() => handleSelect(company.id)}
                    className={`w-full text-left px-4 py-2 text-sm hover:bg-slate-50 transition ${
                      company.id === currentCompanyId ? 'bg-slate-100' : ''
                    }`}
                  >
                    <div className="font-medium text-slate-900">{company.name}</div>
                    {company.industry && (
                      <div className="text-xs text-slate-500">{company.industry}</div>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
