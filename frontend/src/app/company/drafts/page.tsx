'use client';

// Strategic Drafts — the primary brief workspace for a corporate tenant.
// Auto-loads today's brief on mount. If one already exists we render it and
// lock the "Generate" action (regeneration is disallowed, same contract as
// the backend). A date picker below lets analysts jump back into any
// historical brief from the archive.

import { Calendar, FileText, Loader2, Plus, RefreshCw, TriangleAlert } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';

import { useAuth } from '@/components/AuthProvider';
import { PageWrapper } from '@/components/PageWrapper';
import { Spinner } from '@/components/Spinner';
import { StrategicBriefCard } from '@/components/StrategicBriefCard';
import {
  generateB2BReport,
  getAvailableBriefDates,
  getBriefArchive,
  type BriefArchiveItem,
} from '@/lib/api';
import { cn } from '@/lib/utils';

const TODAY = new Date().toISOString().slice(0, 10);

export default function CompanyDraftsPage() {
  const { user } = useAuth();
  const companyId = user?.company_id ?? '';
  const [briefs, setBriefs] = useState<BriefArchiveItem[]>([]);
  const [selectedBrief, setSelectedBrief] = useState<BriefArchiveItem | null>(null);
  // Start loading so the archive sidebar + main pane render a spinner on
  // first paint rather than the "no briefs" copy while the fetch is in
  // flight.
  const [archiveLoading, setArchiveLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const fetchArchive = useCallback(async (id: string, signal?: AbortSignal) => {
    setArchiveLoading(true);
    setError(null);
    try {
      // Use /available-brief-dates as the source of truth for which
      // dates to surface — mirrors the B2C newsletter page and filters
      // out rows without real brief_content. Cap to last 5 so long-
      // tenured tenants don't get an unbounded scroll. We then hydrate
      // the actual content for those exact dates from /briefs/archive.
      const avail = await getAvailableBriefDates(id, 5, signal);
      if (avail.dates.length === 0) {
        setBriefs([]);
        setSelectedBrief(null);
        return;
      }
      const res = await getBriefArchive(id, undefined, 50, signal);
      const allowed = new Set(avail.dates);
      const trimmed = res.results.filter((b) => allowed.has(b.brief_date));
      setBriefs(trimmed);
      setSelectedBrief(trimmed[0] ?? null);
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
    fetchArchive(companyId, controller.signal);
    return () => controller.abort();
  }, [companyId, fetchArchive]);

  const hasToday = useMemo(
    () => briefs.some((b) => b.brief_date === TODAY),
    [briefs],
  );
  const generateDisabled = !companyId || generating || archiveLoading || hasToday;

  const handleGenerate = async (options: { force?: boolean } = {}) => {
    if (!companyId) return;
    if (!options.force && hasToday) return;
    setGenerating(true);
    setError(null);
    setNotice(null);
    try {
      const res = await generateB2BReport(
        { user_id: companyId },
        { force: options.force },
      );
      setNotice(
        options.force
          ? 'Brief regenerated with the latest agent output.'
          : res.already_generated
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
            {hasToday && (
              <button
                onClick={() => handleGenerate({ force: true })}
                disabled={!companyId || generating || archiveLoading}
                title="Re-run today's brief with the latest agent"
                className="flex items-center gap-2 bg-white/5 hover:bg-white/10 border border-white/10 disabled:opacity-40 disabled:cursor-not-allowed text-white px-5 py-3 rounded-2xl text-sm font-bold transition-all"
              >
                <RefreshCw className={cn('w-4 h-4', generating && 'animate-spin')} />
                Regenerate
              </button>
            )}
            <button
              onClick={() => handleGenerate()}
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
            <p className="text-dim">
              Your account isn&apos;t linked to a company yet. Contact an admin
              to assign your tenant.
            </p>
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

            <div className="lg:col-span-3 space-y-6">
              {archiveLoading && !selectedBrief ? (
                <div className="glass rounded-3xl border border-white/5 p-8">
                  <Spinner label="Loading latest brief" />
                </div>
              ) : !selectedBrief ? (
                <div className="glass rounded-3xl border border-white/5 p-8 flex flex-col items-center justify-center py-12 text-dim">
                  <FileText className="w-12 h-12 mb-4" />
                  <p>Select a brief from the archive on the left.</p>
                </div>
              ) : selectedBrief.structured_brief?.brief ? (
                <>
                  <StrategicBriefCard
                    envelope={selectedBrief.structured_brief}
                    briefDate={selectedBrief.brief_date}
                    briefId={selectedBrief.id}
                  />
                  {selectedBrief.brief_content && (
                    <details className="glass rounded-2xl border border-white/5 p-6">
                      <summary className="cursor-pointer text-xs font-black uppercase tracking-[0.16em] text-dim hover:text-white transition-colors">
                        View raw Markdown brief
                      </summary>
                      <div className="brief-sections space-y-4 mt-5 max-h-[60vh] overflow-auto pr-2">
                        {splitBriefIntoCards(selectedBrief.brief_content).map((section, idx) => (
                          <article
                            key={idx}
                            className="rounded-2xl border border-white/10 bg-white/[0.02] p-6 prose prose-invert max-w-none prose-headings:mt-0 prose-headings:mb-3 prose-p:text-white/80 prose-li:text-white/80 prose-strong:text-white"
                          >
                            <ReactMarkdown>{section}</ReactMarkdown>
                          </article>
                        ))}
                      </div>
                    </details>
                  )}
                </>
              ) : (
                // Legacy brief without structured output — render Markdown split.
                <div className="glass rounded-3xl border border-white/5 p-8 space-y-6">
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
                    <div className="brief-sections space-y-4 max-h-[70vh] overflow-auto pr-2">
                      {splitBriefIntoCards(selectedBrief.brief_content).map((section, idx) => (
                        <article
                          key={idx}
                          className="rounded-2xl border border-white/10 bg-white/[0.02] p-6 prose prose-invert max-w-none prose-headings:mt-0 prose-headings:mb-3 prose-p:text-white/80 prose-li:text-white/80 prose-strong:text-white"
                        >
                          <ReactMarkdown>{section}</ReactMarkdown>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <p className="text-dim italic">No content recorded for this brief.</p>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </PageWrapper>
  );
}

/**
 * Split the B2B agent's Markdown brief into per-section cards.
 *
 * The agent emits a stable set of H1/H2 headings (Executive Intelligence
 * Briefing, Key Opportunity Signals, Market Trends Overview, Recommended
 * Actions). Rendering each heading's block as its own card mirrors the
 * tiled layout in the SEO prototype UI. If the content has no headings
 * we fall back to a single tile so nothing gets dropped.
 */
function splitBriefIntoCards(markdown: string): string[] {
  const lines = markdown.split('\n');
  const sections: string[] = [];
  let current: string[] = [];

  for (const line of lines) {
    const isHeading = /^#{1,3}\s+/.test(line);
    if (isHeading && current.length > 0) {
      sections.push(current.join('\n').trim());
      current = [line];
    } else {
      current.push(line);
    }
  }
  if (current.length > 0) sections.push(current.join('\n').trim());

  return sections.filter((s) => s.length > 0);
}
