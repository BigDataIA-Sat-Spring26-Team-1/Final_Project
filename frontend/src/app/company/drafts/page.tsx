'use client';

// Strategic Drafts — the primary brief workspace for a corporate tenant.
// Auto-loads today's brief on mount. If one already exists we render it and
// lock the "Generate" action (regeneration is disallowed, same contract as
// the backend). A date picker below lets analysts jump back into any
// historical brief from the archive.

import { Calendar, FileText, Loader2, Plus, TriangleAlert } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { CompanySwitcher } from '@/components/CompanySwitcher';
import { PageWrapper } from '@/components/PageWrapper';
import { Spinner } from '@/components/Spinner';
import {
  generateB2BReport,
  getBriefArchive,
  type BriefArchiveItem,
} from '@/lib/api';
import { getLastCompanyId, setLastCompanyId } from '@/lib/b2b-cache';
import { cn } from '@/lib/utils';

const TODAY = new Date().toISOString().slice(0, 10);

export default function CompanyDraftsPage() {
  const [companyId, setCompanyId] = useState('');
  const [briefs, setBriefs] = useState<BriefArchiveItem[]>([]);
  const [selectedBrief, setSelectedBrief] = useState<BriefArchiveItem | null>(null);
  const [archiveLoading, setArchiveLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Hydrate last-used company id on mount.
  useEffect(() => {
    (async () => setCompanyId(getLastCompanyId()))();
  }, []);

  const fetchArchive = useCallback(async (id: string, signal?: AbortSignal) => {
    setArchiveLoading(true);
    setError(null);
    try {
      const res = await getBriefArchive(id, undefined, 50, signal);
      setBriefs(res.results);
      // Auto-select the newest brief so the reader lands on fresh content.
      setSelectedBrief(res.results[0] ?? null);
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      setError(err instanceof Error ? err.message : 'Failed to load briefs');
    } finally {
      setArchiveLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!companyId) {
      setBriefs([]);
      setSelectedBrief(null);
      return;
    }
    const controller = new AbortController();
    setLastCompanyId(companyId);
    fetchArchive(companyId, controller.signal);
    return () => controller.abort();
  }, [companyId, fetchArchive]);

  const hasToday = useMemo(
    () => briefs.some((b) => b.brief_date === TODAY),
    [briefs],
  );
  const generateDisabled = !companyId || generating || archiveLoading || hasToday;

  const handleGenerate = async () => {
    if (!companyId || hasToday) return;
    setGenerating(true);
    setError(null);
    setNotice(null);
    try {
      const res = await generateB2BReport({ user_id: companyId });
      setNotice(
        res.already_generated
          ? "Today's brief was already stored — fetched from the archive."
          : 'Brief generated and saved successfully.',
      );
      await fetchArchive(companyId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate brief');
    } finally {
      setGenerating(false);
    }
  };

  const statusClass = (urgency: string | null | undefined) => {
    switch (urgency) {
      case 'ACT_NOW':
        return 'bg-red-500/10 text-red-500 border-red-500/20';
      case 'HIDDEN_GEM':
        return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20';
      case 'MONITOR':
        return 'bg-amber-500/10 text-amber-500 border-amber-500/20';
      default:
        return 'bg-white/5 text-dim border-white/10';
    }
  };

  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between gap-4 flex-wrap">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">Strategic Drafts</h1>
            <p className="text-dim text-lg">
              Today&apos;s brief is auto-loaded. Flip through past dates on the right.
            </p>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <button
              onClick={handleGenerate}
              disabled={generateDisabled}
              title={hasToday ? "Today's brief is already stored." : undefined}
              className="flex items-center gap-2 bg-primary hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed text-primary-foreground px-6 py-3 rounded-2xl text-sm font-bold transition-all"
            >
              {generating ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" /> Generating…
                </>
              ) : hasToday ? (
                <>
                  <FileText className="w-5 h-5" /> Today&apos;s Brief Ready
                </>
              ) : (
                <>
                  <Plus className="w-5 h-5" /> Generate Today&apos;s Brief
                </>
              )}
            </button>
            <CompanySwitcher
              currentCompanyId={companyId || null}
              onSelect={(id) => setCompanyId(id)}
            />
          </div>
        </header>

        {notice && (
          <div className="rounded-2xl border border-blue-500/20 bg-blue-500/5 p-4 text-sm text-blue-200">
            {notice}
          </div>
        )}
        {error && (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-6 flex items-start gap-3">
            <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <p className="text-sm text-rose-200">{error}</p>
          </div>
        )}

        {!companyId ? (
          <div className="glass rounded-3xl p-10 border border-dashed border-white/20 text-center">
            <p className="text-dim">Pick a company from the dropdown to load its briefs.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            <aside className="glass rounded-3xl border border-white/5 p-6 space-y-4 h-fit">
              <h2 className="text-sm font-black uppercase tracking-widest text-dim flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                Brief History
              </h2>
              {archiveLoading ? (
                <Spinner label="Loading archive" />
              ) : briefs.length === 0 ? (
                <p className="text-sm text-dim italic">
                  No briefs yet. Generate today&apos;s to start the archive.
                </p>
              ) : (
                <ul className="space-y-2">
                  {briefs.map((b) => (
                    <li key={b.id}>
                      <button
                        onClick={() => setSelectedBrief(b)}
                        className={cn(
                          'w-full text-left px-3 py-2 rounded-xl text-sm transition',
                          selectedBrief?.id === b.id
                            ? 'bg-primary/10 border border-primary/20 text-white'
                            : 'hover:bg-white/5 text-dim',
                        )}
                      >
                        <p className="font-mono text-xs">{b.brief_date}</p>
                        {b.urgency_tier && (
                          <p className="text-[10px] uppercase tracking-widest text-dim mt-0.5">
                            {b.urgency_tier.replace(/_/g, ' ')}
                          </p>
                        )}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </aside>

            <div className="lg:col-span-3 glass rounded-3xl border border-white/5 p-8 space-y-6">
              {archiveLoading && !selectedBrief ? (
                <Spinner label="Loading latest brief" />
              ) : !selectedBrief ? (
                <div className="flex flex-col items-center justify-center py-12 text-dim">
                  <FileText className="w-12 h-12 mb-4" />
                  <p>Select a brief from the archive on the left.</p>
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between flex-wrap gap-3 pb-6 border-b border-white/5">
                    <div>
                      <h2 className="text-2xl font-bold">Brief · {selectedBrief.brief_date}</h2>
                      <p className="text-xs text-dim mt-1">
                        Generated{' '}
                        {selectedBrief.generated_at
                          ? new Date(selectedBrief.generated_at).toLocaleString()
                          : 'at an unknown time'}
                      </p>
                    </div>
                    {selectedBrief.urgency_tier && (
                      <span
                        className={cn(
                          'px-3 py-1 rounded-full text-[10px] font-black tracking-widest uppercase border',
                          statusClass(selectedBrief.urgency_tier),
                        )}
                      >
                        {selectedBrief.urgency_tier.replace(/_/g, ' ')}
                      </span>
                    )}
                  </div>
                  {selectedBrief.brief_content ? (
                    <pre className="whitespace-pre-wrap text-sm leading-relaxed text-white/90 font-mono bg-white/[0.02] rounded-2xl border border-white/10 p-6 max-h-[70vh] overflow-auto">
                      {selectedBrief.brief_content}
                    </pre>
                  ) : (
                    <p className="text-dim italic">No content recorded for this brief.</p>
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </PageWrapper>
  );
}
