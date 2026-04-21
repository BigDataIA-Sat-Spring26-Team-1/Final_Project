'use client';

// Enterprise Portfolio. Mirrors /admin/users — no list endpoint exists for
// corporate clients, so this page operates as a single-record inspector. The
// admin types a corporate client id and we look for a cached B2B brief in
// sessionStorage; if none is cached we offer to generate one.

import {
  ChevronRight,
  Filter,
  Loader2,
  Search,
  TriangleAlert,
} from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import { PageWrapper } from '@/components/PageWrapper';
import {
  ApiError,
  generateB2BReport,
  type B2BReportResponse,
} from '@/lib/api';
import {
  getLastCompanyId,
  loadReport,
  saveReport,
  setLastCompanyId,
} from '@/lib/b2b-cache';

export default function AdminCompaniesPage() {
  const [companyId, setCompanyId] = useState('');
  const [report, setReport] = useState<B2BReportResponse | null>(null);
  const [generatedAt, setGeneratedAt] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Hydrate from cache (sessionStorage) — set by /seo or /company/drafts.
  useEffect(() => {
    (async () => {
      const lastId = getLastCompanyId();
      if (!lastId) return;
      setCompanyId(lastId);
    })();
  }, []);

  // When the id changes, reach into the cache; never auto-generate.
  useEffect(() => {
    if (!companyId.trim()) {
      setReport(null);
      setGeneratedAt(null);
      return;
    }
    const cached = loadReport(companyId.trim());
    if (cached) {
      setReport(cached.payload);
      setGeneratedAt(cached.generated_at);
    } else {
      setReport(null);
      setGeneratedAt(null);
    }
  }, [companyId]);

  const handleGenerate = async () => {
    if (!companyId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const response = await generateB2BReport({ user_id: companyId.trim() });
      setReport(response);
      const now = Date.now();
      setGeneratedAt(now);
      saveReport(companyId.trim(), response);
      setLastCompanyId(companyId.trim());
    } catch (err) {
      setError(
        err instanceof ApiError
          ? `${err.status}: ${err.detail ?? err.message}`
          : (err as Error).message,
      );
    } finally {
      setLoading(false);
    }
  };

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
          <div className="flex items-center gap-3">
            <div className="flex items-center glass rounded-xl px-4 py-2 border border-white/5 focus-within:border-primary/40">
              <Search className="w-4 h-4 text-dim mr-2" />
              <input
                type="text"
                value={companyId}
                onChange={(e) => setCompanyId(e.target.value)}
                placeholder="Lookup by client id..."
                className="bg-transparent border-none outline-none text-sm w-56 placeholder:text-dim font-mono"
              />
            </div>
            <button
              type="button"
              title="Filtering needs the list endpoint."
              disabled
              className="p-2.5 glass rounded-xl border border-white/5 opacity-50 cursor-not-allowed"
            >
              <Filter className="w-5 h-5 text-dim" />
            </button>
          </div>
        </header>

        <div className="glass rounded-3xl border border-white/5 p-8 space-y-6">
          {!companyId.trim() ? (
            <p className="text-sm text-dim italic">
              Type a corporate client id to inspect that account&apos;s cached intelligence brief.
            </p>
          ) : (
            <>
              <div className="flex items-center gap-4 flex-wrap">
                <div className="w-14 h-14 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold text-lg uppercase">
                  {companyId.charAt(0)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xl font-bold">{companyId}</p>
                  <p className="text-sm text-dim">
                    {report
                      ? `Cached brief · ${report.report.length} chars · ${
                          generatedAt ? new Date(generatedAt).toLocaleString() : ''
                        }`
                      : 'No cached brief — generate one to populate this view.'}
                  </p>
                </div>
                <Link
                  href="/company/drafts"
                  className="p-2 hover:bg-white/5 rounded-lg text-dim hover:text-white"
                  title="Open full draft view"
                >
                  <ChevronRight className="w-4 h-4" />
                </Link>
              </div>

              <button
                onClick={handleGenerate}
                disabled={loading}
                className="px-6 py-3 rounded-xl bg-primary text-primary-foreground font-bold text-sm hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> Generating...
                  </>
                ) : report ? (
                  'Regenerate Brief'
                ) : (
                  'Generate B2B Brief'
                )}
              </button>

              {error && (
                <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 p-4 flex items-start gap-3">
                  <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                  <p className="text-sm text-rose-200">{error}</p>
                </div>
              )}

              {report && (
                <pre className="whitespace-pre-wrap text-sm leading-relaxed text-white/90 font-mono bg-white/[0.02] rounded-2xl border border-white/10 p-6 max-h-[60vh] overflow-auto">
                  {report.report || 'Empty report payload.'}
                </pre>
              )}
            </>
          )}
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-black uppercase tracking-widest text-dim">
              Full Client Roster
            </h2>
            <span className="text-[10px] uppercase tracking-widest font-bold text-amber-400">
              pending /api/v1/companies endpoint
            </span>
          </div>
          <div className="glass rounded-3xl border border-dashed border-white/10 p-12 text-center text-sm text-dim italic">
            The full enterprise roster will render here once the list endpoint
            is available. Use the lookup above to inspect individual clients
            in the meantime.
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}
