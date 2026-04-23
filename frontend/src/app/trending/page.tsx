'use client';

// Trend intelligence page. Reads the latest ranked cluster snapshot from
// /api/v1/trend/top and visualises it as (1) a velocity bar chart driven by
// final_trend_score, (2) a couple of summary cards, and (3) an "emerging
// entities" sidebar sorted by cluster_size delta.
//
// The trend ranker runs out-of-band (Airflow DAG today / cron future), so
// this page never triggers /rank itself — it just paints whatever the last
// ranking pass produced. A manual "Re-rank" button is available for ops.

import {
  Activity,
  Flame,
  Globe,
  Loader2,
  RefreshCw,
  Search,
  TriangleAlert,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  EntityItem,
  TrendFeatureCard,
} from '@/components/DashboardComponents';
import { PageWrapper } from '@/components/PageWrapper';
import {
  ApiError,
  getTopTrends,
  rankDailyTrends,
  type TrendCluster,
} from '@/lib/api';

const CHART_BARS = 20;

export default function TrendingPage() {
  const [filter, setFilter] = useState('');
  const [trends, setTrends] = useState<TrendCluster[]>([]);
  // Start in a loading state so the first paint shows a spinner, not the
  // empty-chart copy, while getTopTrends is in flight.
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ranking, setRanking] = useState(false);
  const [rankMessage, setRankMessage] = useState<string | null>(null);

  const loadTrends = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getTopTrends(CHART_BARS, undefined, signal);
      setTrends(data.results);
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      setTrends([]);
      setError(
        err instanceof ApiError
          ? `${err.status}: ${err.detail ?? err.message}`
          : (err as Error).message,
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    loadTrends(controller.signal);
    return () => controller.abort();
  }, [loadTrends]);

  // Triggered by the "Re-rank" button. Cheap for operators; the ranker itself
  // is a heavy Snowflake MERGE but latency-wise it returns quickly.
  const handleRerank = async () => {
    setRanking(true);
    setRankMessage(null);
    try {
      await rankDailyTrends();
      setRankMessage('Ranking triggered — refreshing…');
      await loadTrends();
      setRankMessage('Snapshot refreshed.');
    } catch (err) {
      setRankMessage(
        err instanceof ApiError
          ? `Ranking failed: ${err.status} ${err.detail ?? err.message}`
          : `Ranking failed: ${(err as Error).message}`,
      );
    } finally {
      setRanking(false);
      // Clear the banner after a few seconds so it doesn't linger.
      setTimeout(() => setRankMessage(null), 4000);
    }
  };

  // Apply the client-side text filter so typing in the search box feels snappy.
  const filtered = useMemo(() => {
    if (!filter.trim()) return trends;
    const q = filter.trim().toLowerCase();
    return trends.filter((t) => t.title.toLowerCase().includes(q));
  }, [trends, filter]);

  // Normalise scores into chart bar heights (0–120 %). We use the filtered list
  // so the chart stays in sync with whatever the user is searching.
  const bars = useMemo(() => {
    const slots = filtered.slice(0, CHART_BARS);
    if (slots.length === 0) return Array(CHART_BARS).fill(20);
    const maxScore = Math.max(...slots.map((t) => t.final_trend_score), 1);
    const heights = slots.map((t) => Math.max(15, (t.final_trend_score / maxScore) * 120));
    // Pad with short bars if we don't have enough clusters to fill the chart.
    while (heights.length < CHART_BARS) heights.push(15);
    return heights;
  }, [filtered]);

  const highVelocityCount = filtered.filter((t) =>
    ['BREAKING', 'TRENDING', 'VIRAL', 'BREAKING-VIRAL'].includes((t.trend_status ?? '').toUpperCase()),
  ).length;

  const dominantCategory = useMemo(() => {
    // Aggregate category weights across every visible cluster and pick the
    // heaviest — a rough "what is everyone talking about" signal for the card.
    const tally: Record<string, number> = {};
    for (const t of filtered) {
      for (const [cat, w] of Object.entries(t.categories || {})) {
        tally[cat] = (tally[cat] || 0) + (typeof w === 'number' ? w : 0);
      }
    }
    const top = Object.entries(tally).sort(([, a], [, b]) => b - a)[0];
    return top ? top[0] : 'N/A';
  }, [filtered]);

  const blueOceanCandidate = useMemo(() => {
    // Pick the lowest cluster_size among visible TRENDING/BREAKING items —
    // those are stories with velocity that haven't been over-covered yet.
    const hot = filtered
      .filter((t) => (t.trend_status ?? '').toUpperCase().includes('TREND') || (t.trend_status ?? '').toUpperCase().includes('BREAK'))
      .sort((a, b) => a.cluster_size - b.cluster_size)[0];
    return hot ?? null;
  }, [filtered]);

  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between gap-4 flex-wrap">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">Trend Intelligence</h1>
            <p className="text-muted-foreground text-lg">Cross-source signals and topic velocity tracking.</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center glass rounded-xl px-4 py-2 border border-white/5 focus-within:border-primary/50 transition-all">
              <Search className="w-4 h-4 text-muted-foreground mr-2" />
              <input
                type="text"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Filter topics..."
                className="bg-transparent border-none outline-none text-sm w-48 placeholder:text-muted-foreground"
              />
            </div>
            <button
              onClick={handleRerank}
              disabled={ranking || loading}
              className="bg-primary hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed text-primary-foreground px-6 py-2 rounded-xl text-sm font-semibold transition-all flex items-center gap-2"
            >
              {ranking ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              {ranking ? 'Ranking...' : 'Re-rank'}
            </button>
          </div>
        </header>

        {rankMessage && (
          <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4 text-sm text-emerald-300">
            {rankMessage}
          </div>
        )}

        {error && (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-6 flex items-start gap-3">
            <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <p className="text-sm text-rose-200">{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          <div className="lg:col-span-3 space-y-6">
            <div className="glass rounded-3xl p-8 border border-white/5 h-[400px] flex flex-col items-center justify-center text-center relative overflow-hidden group">
              <div className="absolute inset-x-0 bottom-0 h-48 flex items-end gap-1 px-8">
                {bars.map((h, i) => (
                  <div
                    key={i}
                    className="flex-1 bg-primary/20 hover:bg-primary/40 transition-all rounded-t-sm"
                    style={{ height: `${h}%` }}
                  />
                ))}
              </div>
              <div className="z-10 bg-background/80 backdrop-blur-md p-6 rounded-2xl border border-white/10 shadow-2xl">
                <Activity className="w-10 h-10 text-primary mx-auto mb-4" />
                <h3 className="text-xl font-bold mb-2">Real-time Velocity Index</h3>
                <p className="text-muted-foreground text-sm max-w-sm">
                  Tracking <span className="text-white font-bold">{highVelocityCount} high-velocity</span> of{' '}
                  <span className="text-white font-bold">{filtered.length}</span> ranked clusters.
                  {loading && ' · loading'}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <TrendFeatureCard
                title="Dominant Category"
                value={humanizeCategory(dominantCategory)}
                icon={Globe}
                detail={filtered.length > 0 ? `Across ${filtered.length} clusters` : 'No data yet'}
              />
              <TrendFeatureCard
                title="Blue Ocean Score"
                value={blueOceanCandidate ? 'Low Competition' : 'N/A'}
                icon={Flame}
                detail={
                  blueOceanCandidate
                    ? `${blueOceanCandidate.title.slice(0, 48)}${blueOceanCandidate.title.length > 48 ? '…' : ''}`
                    : 'Re-rank to surface gaps'
                }
                isPrimary
              />
            </div>
          </div>

          <div className="space-y-6">
            <h2 className="text-xl font-bold">Emerging Entities</h2>
            <div className="space-y-4">
              {loading && filtered.length === 0 && (
                <p className="text-sm text-dim italic flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" /> Loading…
                </p>
              )}
              {!loading && filtered.length === 0 && (
                <p className="text-sm text-dim italic">
                  No clusters ranked yet — trigger an ingestion + rank.
                </p>
              )}
              {filtered.slice(0, 6).map((t) => (
                <EntityItem
                  key={t.cluster_id}
                  name={t.title.slice(0, 28)}
                  // EntityItem's score × 10 = "reliability %" — feed cluster_size
                  // so well-sourced stories look more reliable in the UI.
                  score={Math.min(10, t.cluster_size * 1.5)}
                  delta={Math.round(t.final_trend_score)}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}

// Shared with other pages — could be lifted into lib/utils, but one-off for now.
function humanizeCategory(key: string): string {
  if (!key || key === 'N/A') return key;
  return key
    .split('_')
    .map((w) => (w === 'ai' || w === 'llms' ? w.toUpperCase() : w[0]?.toUpperCase() + w.slice(1)))
    .join(' ');
}
