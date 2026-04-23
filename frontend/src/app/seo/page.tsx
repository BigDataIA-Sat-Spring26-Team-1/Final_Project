'use client';

// Enterprise SEO intelligence. Same B2B report as /company/drafts; this page
// focuses on the "strategic opportunities" angle and surfaces the cached
// brief alongside top-trend data from the shared trend endpoint. Generating
// here also writes to the sessionStorage cache that the drafts page reads.

import {
  FileText,
  Loader2,
  MousePointer2,
  ShieldCheck,
  Target,
  TriangleAlert,
} from 'lucide-react';
import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { OpportunityItem } from '@/components/DashboardComponents';
import { PageWrapper } from '@/components/PageWrapper';
import { Spinner, SpinnerBlock } from '@/components/Spinner';
import {
  ApiError,
  generateB2BReport,
  getTopTrends,
  type B2BReportResponse,
  type TrendCluster,
} from '@/lib/api';
import {
  getLastCompanyId,
  loadReport,
  saveReport,
  setLastCompanyId,
} from '@/lib/b2b-cache';

// Opportunity tiers used by the B2B agent (per b2b_agent.py scoring).
const HIGH_TIER_SET = new Set(['HIDDEN GEM', 'ACT NOW']);

export default function SEOStrategyPage() {
  const [companyId, setCompanyId] = useState('');
  const [report, setReport] = useState<B2BReportResponse | null>(null);
  const [trends, setTrends] = useState<TrendCluster[]>([]);
  const [trendsLoading, setTrendsLoading] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Rehydrate the company id + cached report so switching in from /company
  // or /company/drafts shows the same brief without re-generating.
  useEffect(() => {
    const lastId = getLastCompanyId();
    if (lastId) {
      setCompanyId(lastId);
      const cached = loadReport(lastId);
      if (cached) setReport(cached.payload);
    }
  }, []);

  // Background pull — the "Strategic Opportunities" cards are enriched from
  // the ranked trend snapshot until a structured B2B endpoint exists.
  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      setTrendsLoading(true);
      try {
        const r = await getTopTrends(6, undefined, controller.signal);
        setTrends(r.results);
      } catch {
        setTrends([]);
      } finally {
        setTrendsLoading(false);
      }
    })();
    return () => controller.abort();
  }, []);

  const handleGenerate = useCallback(async () => {
    if (!companyId.trim()) {
      setError('Enter a corporate client id first.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await generateB2BReport({ user_id: companyId.trim() });
      setReport(response);
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
  }, [companyId]);

  // Pick the top-scored cluster as the "Top Keyword Cluster" headline.
  const topCluster = trends[0];
  const dominantCategory = useMemo(() => {
    if (!topCluster?.categories) return 'N/A';
    const sorted = Object.entries(topCluster.categories).sort(([, a], [, b]) => b - a);
    return sorted[0]?.[0] ?? 'N/A';
  }, [topCluster]);

  // Vector alignment = normalised final_trend_score of the top cluster.
  const alignment = topCluster
    ? Math.min(0.99, topCluster.final_trend_score / 200).toFixed(2)
    : '—';
  const alignmentPct = topCluster
    ? Math.min(99, Math.round((topCluster.final_trend_score / 200) * 100))
    : 0;

  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between gap-6 flex-wrap">
          <div className="flex flex-col gap-2">
            <h1 className="text-4xl font-bold tracking-tight">Enterprise SEO Intelligence</h1>
            <p className="text-muted-foreground text-lg">
              Cross-company authority matching and blue ocean discovery.
            </p>
          </div>
          <input
            type="text"
            placeholder="corporate client id"
            value={companyId}
            onChange={(e) => setCompanyId(e.target.value)}
            className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm outline-none focus:border-primary/40 font-mono min-w-[260px]"
          />
        </header>

        <div className="flex items-center gap-6 p-8 glass rounded-3xl border border-white/5 bg-gradient-to-r from-primary/5 to-transparent flex-wrap">
          <div className="w-16 h-16 rounded-2xl bg-primary flex items-center justify-center shadow-2xl shadow-primary/20">
            <ShieldCheck className="w-8 h-8 text-primary-foreground" />
          </div>
          <div className="flex-1 space-y-1 border-r border-white/10 pr-10 min-w-[180px]">
            <p className="text-sm font-semibold text-primary uppercase tracking-widest">
              Active Authority Profile
            </p>
            <h2 className="text-2xl font-bold">
              {companyId || '— select a client —'}
            </h2>
          </div>
          <div className="flex-1 space-y-1 px-10 border-r border-white/10 min-w-[200px]">
            <p className="text-xs text-muted-foreground uppercase font-bold tracking-tighter">
              Vector Alignment
            </p>
            <div className="flex items-center gap-3">
              <h3 className="text-2xl font-black">
                {trendsLoading ? <Spinner size="sm" /> : alignment}
              </h3>
              <div className="w-24 h-2 bg-white/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary transition-all"
                  style={{ width: `${alignmentPct}%` }}
                />
              </div>
            </div>
          </div>
          <div className="flex-1 space-y-1 pl-10 min-w-[160px]">
            <p className="text-xs text-muted-foreground uppercase font-bold tracking-tighter">
              Top Keyword Cluster
            </p>
            <h3 className="text-xl font-bold">
              {trendsLoading ? <Spinner size="sm" /> : topCluster ? truncate(topCluster.title, 32) : '—'}
            </h3>
          </div>
        </div>

        {error && (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-6 flex items-start gap-3">
            <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <p className="text-sm text-rose-200">{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
          <div className="space-y-6">
            <h2 className="text-xl font-bold flex items-center gap-2">
              <Target className="w-5 h-5 text-primary" />
              Strategic Opportunities
            </h2>
            <div className="space-y-4">
              {trendsLoading ? (
                <SpinnerBlock label="Loading trends" />
              ) : trends.length === 0 ? (
                <p className="text-sm text-dim italic">
                  No ranked trends yet — run ingestion + rank, then refresh.
                </p>
              ) : (
                trends.slice(0, 5).map((t) => (
                  <OpportunityItem
                    key={t.cluster_id}
                    topic={truncate(t.title, 48)}
                    relevance={Math.round(Math.min(99, t.final_trend_score))}
                    competition={
                      t.cluster_size <= 2
                        ? 'LOW'
                        : t.cluster_size <= 5
                        ? 'MEDIUM'
                        : 'HIGH'
                    }
                    category={(t.trend_status ?? 'REGULAR').replace(/-/g, ' ')}
                  />
                ))
              )}
            </div>
          </div>

          <div className="space-y-6">
            <h2 className="text-xl font-bold flex items-center gap-2">
              <FileText className="w-5 h-5 text-primary" />
              Intelligence Brief
            </h2>
            <div className="glass rounded-3xl p-8 border border-white/5 space-y-6">
              {report ? (
                <div className="bg-white/5 rounded-2xl p-5 border border-white/5 space-y-3">
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <h4 className="text-lg font-bold">
                        Strategy brief for {report.user_id}
                      </h4>
                      <p className="text-sm text-muted-foreground">
                        Cached in session · {report.report.length} chars of Markdown
                      </p>
                    </div>
                    <Link
                      href="/company/drafts"
                      className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-muted-foreground hover:text-white transition-all"
                      title="Open full brief"
                    >
                      <MousePointer2 className="w-4 h-4" />
                    </Link>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-primary/20 text-primary border border-primary/20 uppercase">
                      {report.status}
                    </span>
                    {HIGH_TIER_SET.has(report.status) && (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/20 uppercase">
                        Priority
                      </span>
                    )}
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-white/5 text-muted-foreground border border-white/10 uppercase">
                      {humanize(dominantCategory)}
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No cached brief yet. Generate one to see it here.
                </p>
              )}
              <button
                onClick={handleGenerate}
                disabled={loading || !companyId}
                className="w-full py-4 rounded-2xl bg-white text-black font-bold text-sm hover:bg-zinc-200 disabled:opacity-40 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> Generating...
                  </>
                ) : report ? (
                  'Regenerate Brief'
                ) : (
                  'Initialize Agentic Brief Generation'
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n - 1) + '…' : s;
}

function humanize(key: string): string {
  if (!key || key === 'N/A') return key;
  return key
    .split('_')
    .map((w) => (w === 'ai' || w === 'llms' ? w.toUpperCase() : w[0]?.toUpperCase() + w.slice(1)))
    .join(' ');
}
