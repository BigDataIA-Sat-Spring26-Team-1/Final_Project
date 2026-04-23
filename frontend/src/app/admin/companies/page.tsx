'use client';

// Enterprise Portfolio. Pure roster — lists every corporate tenant with
// metadata. Brief generation lives on /company/drafts; /admin/newsletters
// owns the historical archive view.

import { Loader2, TriangleAlert } from 'lucide-react';
import { useEffect, useState } from 'react';

import { PageWrapper } from '@/components/PageWrapper';
import {
  ApiError,
  listCompanies,
  type CompanyListItem,
} from '@/lib/api';

export default function AdminCompaniesPage() {
  const [companies, setCompanies] = useState<CompanyListItem[] | null>(null);
  const [rosterError, setRosterError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    listCompanies(100, 0, controller.signal)
      .then((r) => setCompanies(r.results))
      .catch((err) => {
        if ((err as Error).name === 'AbortError') return;
        setRosterError(
          err instanceof ApiError
            ? `${err.status}: ${err.detail ?? err.message}`
            : (err as Error).message,
        );
      });
    return () => controller.abort();
  }, []);

  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between gap-4 flex-wrap">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">Enterprise Portfolio</h1>
            <p className="text-dim text-lg">
              Inspect corporate authority profiles and B2B intelligence briefs.
            </p>
          </div>
        </header>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-black uppercase tracking-widest text-dim">
              Full Client Roster
            </h2>
            <span className="text-[10px] uppercase tracking-widest font-bold text-dim">
              {companies ? `${companies.length} clients` : 'loading…'}
            </span>
          </div>

          {rosterError ? (
            <div className="glass rounded-3xl border border-rose-500/20 p-6 flex items-start gap-3 text-rose-200">
              <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <p className="text-sm">{rosterError}</p>
            </div>
          ) : companies === null ? (
            <div className="glass rounded-3xl border border-white/10 p-12 text-center text-sm text-dim flex items-center justify-center gap-3">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading roster…
            </div>
          ) : companies.length === 0 ? (
            <div className="glass rounded-3xl border border-white/10 p-12 text-center text-sm text-dim italic">
              No companies yet. Create one from the Admin Console.
            </div>
          ) : (
            <div className="glass rounded-3xl border border-white/5 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-[10px] uppercase tracking-widest text-dim border-b border-white/5">
                    <th className="text-left font-bold px-6 py-3">Name</th>
                    <th className="text-left font-bold px-6 py-3">Industry</th>
                    <th className="text-left font-bold px-6 py-3">Domain</th>
                    <th className="text-left font-bold px-6 py-3">Created</th>
                    <th className="text-left font-bold px-6 py-3 font-mono">ID</th>
                    <th className="px-6 py-3" />
                  </tr>
                </thead>
                <tbody>
                  {companies.map((c) => (
                    <tr key={c.id} className="border-b border-white/5 hover:bg-white/5 transition">
                      <td className="px-6 py-3 font-medium">{c.name}</td>
                      <td className="px-6 py-3 text-dim">{c.industry ?? '—'}</td>
                      <td className="px-6 py-3 text-dim">{c.domain ?? '—'}</td>
                      <td className="px-6 py-3 text-dim">
                        {new Date(c.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-3 text-dim font-mono text-xs truncate max-w-[160px]">
                        {c.id}
                      </td>
                      <td className="px-6 py-3" />
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </PageWrapper>
  );
}
