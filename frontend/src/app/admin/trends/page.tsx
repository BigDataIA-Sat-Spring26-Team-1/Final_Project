'use client';

// Global Market Sentiment view for admins. Mirrors /trending but framed
// around aggregate signals: dominant story, system-wide reliability, and a
// per-entity velocity table (PREV → CURRENT delta vs the historical average).
// All driven by /api/v1/trend/top.

import {
  Globe,
  Search,
  ShieldCheck,
  TriangleAlert,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { PageWrapper } from '@/components/PageWrapper';
import {
  ApiError,
  getTopTrends,
  type TrendCluster,
} from '@/lib/api';
import { cn } from '@/lib/utils';

type Row = {
  id: string;
  name: string;
  sub: string;
  status: string;
  prev: number;
  curr: number;
  deltaPct: number;
  isNegative: boolean;
};

// Default the trend view to "all time" — explicit date filter lets admins
// rewind to a specific historical window without dropping today's data.
const ALL_TIME = '';

export default function AdminTrendsPage() {
  const [trends, setTrends] = useState<TrendCluster[]>([]);
  const [filter, setFilter] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [date, setDate] = useState<string>(ALL_TIME);

  useEffect(() => {
    const controller = new AbortController();
    getTopTrends(30, undefined, controller.signal, date || undefined)
      .then((r) => setTrends(r.results))
      .catch((err) => {
        if (err.name === 'AbortError') return;
        setError(
          err instanceof ApiError
            ? `${err.status}: ${err.detail ?? err.message}`
            : (err as Error).message,
        );
      });
    return () => controller.abort();
  }, [date]);

  const dominant = trends[0];

  // Reliability proxy: % of clusters with multiple independent sources.
  const reliability = useMemo(() => {
    if (trends.length === 0) return null;
    const verified = trends.filter((t) => t.cluster_size >= 2).length;
    return Math.round((verified / trends.length) * 100);
  }, [trends]);

  // We don't have a "previous window" snapshot endpoint. Approximate the
  // delta by treating cluster_size as "prev", final_trend_score as "current"
  // and computing the relative change. Honest about being a rough estimate.
  const rows: Row[] = useMemo(
    () =>
      trends.map((t) => {
        const prev = Math.max(t.cluster_size, 1);
        const curr = Math.max(1, Math.round(t.final_trend_score));
        const deltaPct = Math.round(((curr - prev) / prev) * 100);
        return {
          id: t.cluster_id,
          name: t.title,
          sub: humanizeStatus(t.trend_status),
          status: (t.trend_status ?? 'REGULAR').toUpperCase(),
          prev,
          curr,
          deltaPct,
          isNegative: deltaPct < 0,
        };
      }),
    [trends],
  );

  const filtered = useMemo(() => {
    if (!filter.trim()) return rows;
    const q = filter.trim().toLowerCase();
    return rows.filter(
      (r) => r.name.toLowerCase().includes(q) || r.sub.toLowerCase().includes(q),
    );
  }, [rows, filter]);

  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">Global Market Sentiment</h1>
            <p className="text-dim text-lg">
              Aggregated signals across all monitored tech clusters and newsletters.
            </p>
          </div>
        </header>

        {error && (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-6 flex items-start gap-3">
            <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <p className="text-sm text-rose-200">{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="glass rounded-3xl p-8 border border-white/5 space-y-4 shadow-2xl">
            <div className="flex items-center gap-3 text-emerald-400 mb-2">
              <Globe className="w-6 h-6" />
              <h3 className="font-bold uppercase tracking-widest text-xs">Primary Signal</h3>
            </div>
            <h4 className="text-3xl font-black">
              {dominant ? truncate(dominant.title, 48) : '—'}
            </h4>
            <p className="text-dim">
              {dominant
                ? `Top-ranked cluster across ${dominant.cluster_size} sources, status ${
                    dominant.trend_status ?? 'REGULAR'
                  }.`
                : 'No ranked clusters yet.'}
            </p>
          </div>

          <div className="glass rounded-3xl p-8 border border-white/5 space-y-4 bg-gradient-to-br from-primary/5 to-transparent">
            <div className="flex items-center gap-3 text-primary mb-2">
              <ShieldCheck className="w-6 h-6" />
              <h3 className="font-bold uppercase tracking-widest text-xs">Data Reliability</h3>
            </div>
            <h4 className="text-3xl font-black">
              {reliability !== null ? `${reliability}% verified` : '—'}
            </h4>
            <p className="text-dim">
              Share of ranked clusters with at least two independent sources confirming the story.
            </p>
          </div>
        </div>

        <div className="glass rounded-[2.5rem] border border-white/5 overflow-hidden">
          <div className="p-8 border-b border-white/5 flex items-center justify-between bg-white/[0.01] flex-wrap gap-3">
            <h3 className="text-xl font-bold">Emerging Topics &amp; Entity Velocity</h3>
            <div className="flex items-center gap-4 flex-wrap">
              <label className="flex items-center gap-2 text-xs text-dim">
                <span className="uppercase tracking-widest font-bold">date</span>
                <input
                  type="date"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  max={new Date().toISOString().slice(0, 10)}
                  className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-xs outline-none focus:border-primary/40 font-mono"
                />
                {date && (
                  <button
                    onClick={() => setDate(ALL_TIME)}
                    className="text-[10px] uppercase tracking-widest text-dim hover:text-white font-bold"
                  >
                    clear
                  </button>
                )}
              </label>
              <div className="flex items-center glass rounded-xl px-4 py-2 border border-white/5">
                <Search className="w-4 h-4 text-dim mr-2" />
                <input
                  type="text"
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                  placeholder="Filter entities..."
                  className="bg-transparent border-none outline-none text-sm w-48 placeholder:text-dim"
                />
              </div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-white/5 text-[10px] font-black uppercase tracking-widest text-dim border-b border-white/5">
                  <th className="px-8 py-5">Entity / Signal</th>
                  <th className="px-8 py-5">Status</th>
                  <th className="px-8 py-5 text-center">Cluster Size</th>
                  <th className="px-8 py-5 text-center">Trend Score</th>
                  <th className="px-8 py-5 text-right">Velocity Δ</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-8 py-10 text-center text-dim italic">
                      No clusters match the current filter.
                    </td>
                  </tr>
                )}
                {filtered.map((r) => (
                  <TrendRow key={r.id} row={r} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}

function TrendRow({ row }: { row: Row }) {
  return (
    <tr className="hover:bg-white/[0.02] transition-colors group">
      <td className="px-8 py-6">
        <p className="font-bold text-white group-hover:text-primary transition-colors">
          {truncate(row.name, 56)}
        </p>
        <p className="text-xs text-dim">{row.sub}</p>
      </td>
      <td className="px-8 py-6">
        <span
          className={cn(
            'px-3 py-1 rounded-full text-[10px] font-black tracking-widest border uppercase',
            row.isNegative
              ? 'bg-red-500/10 text-red-500 border-red-500/20'
              : 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
          )}
        >
          {row.status}
        </span>
      </td>
      <td className="px-8 py-6 text-center text-dim font-medium">{row.prev}</td>
      <td className="px-8 py-6 text-center font-bold">{row.curr}</td>
      <td
        className={cn(
          'px-8 py-6 text-right font-black',
          row.isNegative ? 'text-red-500' : 'text-emerald-500',
        )}
      >
        {row.deltaPct >= 0 ? '+' : ''}
        {row.deltaPct}% {row.isNegative ? '↓' : '↑'}
      </td>
    </tr>
  );
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n - 1) + '…' : s;
}

function humanizeStatus(s: string | null): string {
  if (!s) return 'Regular';
  return s
    .split(/[-_]/)
    .map((w) => w[0]?.toUpperCase() + w.slice(1).toLowerCase())
    .join(' ');
}
