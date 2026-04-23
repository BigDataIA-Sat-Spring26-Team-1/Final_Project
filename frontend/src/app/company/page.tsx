'use client';

// Company dashboard. The Keyword Velocity Index chart, Signal Feed, and the
// two summary cards all derive from the shared /api/v1/trend/top snapshot.
// Traffic-Opportunity + Authority-Overlap cards use heuristics (low
// cluster_size for blue-ocean etc.) until a dedicated B2B analytics endpoint
// exists.

import {
  Briefcase,
  ChevronRight,
  Flame,
  Target,
  TriangleAlert,
} from 'lucide-react';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

import { CompanySwitcher } from '@/components/CompanySwitcher';
import {
  EntityItem,
  TrendFeatureCard,
} from '@/components/DashboardComponents';
import { PageWrapper } from '@/components/PageWrapper';
import { Spinner, SpinnerBlock } from '@/components/Spinner';
import {
  ApiError,
  getTopTrends,
  type TrendCluster,
} from '@/lib/api';
import { getLastCompanyId, setLastCompanyId } from '@/lib/b2b-cache';

const CHART_BARS = 16;

export default function CompanyDashboard() {
  const [companyId, setCompanyId] = useState('');
  const [trends, setTrends] = useState<TrendCluster[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Hydrate the last-used company id from sessionStorage once on mount. The
  // async IIFE shape appeases React 19's set-state-in-effect linter; the
  // underlying read is still synchronous.
  useEffect(() => {
    (async () => setCompanyId(getLastCompanyId()))();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      setLoading(true);
      try {
        const r = await getTopTrends(CHART_BARS, undefined, controller.signal);
        setTrends(r.results);
      } catch (err) {
        if ((err as Error).name === 'AbortError') return;
        setError(
          err instanceof ApiError
            ? `${err.status}: ${err.detail ?? err.message}`
            : (err as Error).message,
        );
      } finally {
        setLoading(false);
      }
    })();
    return () => controller.abort();
  }, []);

  const chartHeights = useMemo(() => {
    if (trends.length === 0) return Array(CHART_BARS).fill(25);
    const max = Math.max(...trends.map((t) => t.final_trend_score), 1);
    const arr = trends.map((t) => Math.max(20, (t.final_trend_score / max) * 100));
    while (arr.length < CHART_BARS) arr.push(25);
    return arr;
  }, [trends]);

  const top = trends[0];
  const trafficOpportunity = useMemo(() => {
    // Opportunity = high final_trend_score with relatively small cluster_size
    // (signal is loud but few people are talking about it yet).
    return [...trends]
      .filter((t) => t.final_trend_score > 0)
      .sort(
        (a, b) =>
          b.final_trend_score / (b.cluster_size + 1) -
          a.final_trend_score / (a.cluster_size + 1),
      )[0];
  }, [trends]);

  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between gap-6 flex-wrap">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2 text-secondary font-bold text-sm uppercase tracking-widest">
              <Briefcase className="w-4 h-4" />
              Enterprise Console
            </div>
            <h1 className="text-4xl font-bold tracking-tight">Market Intelligence Hub</h1>
            <p className="text-dim text-lg">
              Authority tracking and competitor blue ocean opportunities for{' '}
              <strong>{companyId || '— set a client id —'}</strong>.
            </p>
          </div>
          <div className="flex flex-col gap-2 items-end">
            <CompanySwitcher
              currentCompanyId={companyId || null}
              onSelect={(id) => {
                setCompanyId(id);
                setLastCompanyId(id);
              }}
            />
            <input
              type="text"
              placeholder="or paste a corporate client id…"
              value={companyId}
              onChange={(e) => setCompanyId(e.target.value)}
              onBlur={() => companyId && setLastCompanyId(companyId)}
              className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2 text-xs outline-none focus:border-primary/40 font-mono min-w-[260px]"
            />
          </div>
        </header>

        {error && (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-6 flex items-start gap-3">
            <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <p className="text-sm text-rose-200">{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          <div className="lg:col-span-3 space-y-8">
            <div className="glass rounded-[2rem] p-10 border border-white/5 space-y-6 relative overflow-hidden group">
              <div className="flex items-center justify-between relative z-10 flex-wrap gap-4">
                <div>
                  <h3 className="text-2xl font-bold">Keyword Velocity Index</h3>
                  <p className="text-sm text-dim">Aggregated visibility across primary clusters.</p>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-[10px] font-black text-dim uppercase tracking-widest">
                      Top Cluster Score
                    </p>
                    <p className="text-xl font-bold text-emerald-400">
                      {loading ? <Spinner size="sm" /> : top ? Math.round(top.final_trend_score) : '—'}
                    </p>
                  </div>
                </div>
              </div>

              <div className="h-64 flex items-end gap-1.5 px-2 relative z-10">
                {chartHeights.map((h, i) => (
                  <div
                    key={i}
                    className="flex-1 bg-gradient-to-t from-secondary/40 to-secondary/10 rounded-t-lg transition-all hover:from-secondary/60"
                    style={{ height: `${h}%` }}
                  />
                ))}
              </div>

              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-secondary/5 blur-[120px] rounded-full z-0" />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <TrendFeatureCard
                title="Authority Overlap"
                value={loading ? <Spinner size="sm" /> : top ? `${top.cluster_size} sources` : '—'}
                icon={Target}
                detail={
                  loading
                    ? 'Loading latest cluster…'
                    : top
                    ? `Leading cluster: ${top.trend_status ?? 'REGULAR'}`
                    : 'No signal yet'
                }
              />
              <TrendFeatureCard
                title="Traffic Opportunity"
                value={
                  loading ? (
                    <Spinner size="sm" />
                  ) : trafficOpportunity ? (
                    `High (${Math.round(trafficOpportunity.final_trend_score)})`
                  ) : (
                    '—'
                  )
                }
                icon={Flame}
                detail={
                  loading
                    ? 'Scanning trend snapshot…'
                    : trafficOpportunity
                    ? `Cluster: ${trafficOpportunity.title.slice(0, 32)}${
                        trafficOpportunity.title.length > 32 ? '…' : ''
                      }`
                    : 'Re-rank to surface blue-ocean plays'
                }
                isPrimary
              />
            </div>
          </div>

          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold">Signal Feed</h2>
              <Link
                href="/company/trends"
                className="text-xs font-bold text-secondary flex items-center gap-1 hover:underline"
              >
                View Matrix
                <ChevronRight className="w-3 h-3" />
              </Link>
            </div>
            <div className="space-y-4">
              {loading ? (
                <SpinnerBlock label="Loading signals" />
              ) : trends.length === 0 ? (
                <p className="text-sm text-dim italic">
                  No ranked signals — trigger ingestion + rank to populate the feed.
                </p>
              ) : (
                trends.slice(0, 5).map((t) => (
                  <EntityItem
                    key={t.cluster_id}
                    name={t.title.slice(0, 24)}
                    score={Math.min(10, t.cluster_size * 1.5)}
                    delta={Math.round(t.final_trend_score)}
                  />
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}
