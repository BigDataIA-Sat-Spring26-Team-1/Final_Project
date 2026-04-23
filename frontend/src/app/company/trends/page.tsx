'use client';

// Keyword Velocity table for the enterprise console. Reads ranked clusters
// from /api/v1/trend/top, derives "company status" (LEADER / EMERGING /
// OPPORTUNITY / MATURE) from cluster_size + final_trend_score, and supports a
// client-side text filter. The "Generate Strategy Brief" shortcut jumps to
// /company/drafts where the actual B2B agent runs.

import {
  ArrowUpRight,
  Calendar,
  Loader2,
  Search,
  TriangleAlert,
} from 'lucide-react';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

import { PageWrapper } from '@/components/PageWrapper';
import {
  ApiError,
  getTopTrends,
  type TrendCluster,
} from '@/lib/api';
import { cn } from '@/lib/utils';

type CompanyStatus = 'LEADER' | 'EMERGING' | 'OPPORTUNITY' | 'MATURE';

type Row = TrendCluster & {
  company_status: CompanyStatus;
  authority: number;
  deltaPct: number;
};

const TODAY = new Date().toISOString().slice(0, 10);

export default function CompanyTrendsPage() {
  const [filter, setFilter] = useState('');
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [trends, setTrends] = useState<TrendCluster[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getTopTrends(
          30,
          undefined,
          controller.signal,
          selectedDate || undefined,
        );
        setTrends(data.results);
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
  }, [selectedDate]);

  // Map the raw cluster shape into the table's display row shape. Values are
  // heuristics — they're consistent across renders so the UI stays stable.
  const rows: Row[] = useMemo(
    () =>
      trends.map((t) => {
        const authority = Math.min(0.99, t.final_trend_score / 200);
        const status: CompanyStatus =
          t.cluster_size >= 5 && t.final_trend_score >= 100
            ? 'LEADER'
            : t.cluster_size <= 2 && t.final_trend_score >= 40
            ? 'OPPORTUNITY'
            : t.cluster_size >= 5
            ? 'MATURE'
            : 'EMERGING';
        // Momentum = final_trend_score normalised; let it go negative if the
        // cluster is large and stale relative to its peers.
        const deltaPct = Math.round(t.final_trend_score - t.cluster_size * 5);
        return { ...t, company_status: status, authority, deltaPct };
      }),
    [trends],
  );

  const filtered = useMemo(() => {
    if (!filter.trim()) return rows;
    const q = filter.trim().toLowerCase();
    return rows.filter((r) => r.title.toLowerCase().includes(q));
  }, [rows, filter]);

  const dominant = rows.find((r) => r.company_status === 'LEADER') ?? rows[0];
  const blueOcean = rows.find((r) => r.company_status === 'OPPORTUNITY');

  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between gap-4 flex-wrap">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">Keyword Velocity</h1>
            <p className="text-dim text-lg">
              Authority-weighted trend signals across ranked clusters.
            </p>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center glass rounded-xl px-4 py-2 border border-white/5 focus-within:border-primary/40">
              <Calendar className="w-4 h-4 text-dim mr-2" />
              <input
                type="date"
                value={selectedDate}
                max={TODAY}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="bg-transparent border-none outline-none text-sm placeholder:text-dim"
              />
              {selectedDate && (
                <button
                  type="button"
                  onClick={() => setSelectedDate('')}
                  className="ml-2 text-[10px] uppercase tracking-widest text-primary hover:underline"
                >
                  Clear
                </button>
              )}
            </div>
            <div className="flex items-center glass rounded-xl px-4 py-2 border border-white/5 focus-within:border-primary/40">
              <Search className="w-4 h-4 text-dim mr-2" />
              <input
                type="text"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Filter company keywords..."
                className="bg-transparent border-none outline-none text-sm w-48 placeholder:text-dim"
              />
            </div>
          </div>
        </header>

        {error && (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-6 flex items-start gap-3">
            <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <p className="text-sm text-rose-200">{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="glass rounded-3xl p-8 border border-white/5 space-y-4">
            <h3 className="text-xs font-black uppercase tracking-widest text-secondary">
              Dominant Authority Cluster
            </h3>
            <h4 className="text-3xl font-black">
              {dominant ? truncate(dominant.title, 48) : '—'}
            </h4>
            <p className="text-dim">
              {dominant
                ? `Alignment score ${dominant.authority.toFixed(2)} across ${dominant.cluster_size} independent sources.`
                : 'No ranked clusters yet.'}
            </p>
            {dominant && (
              <div className="flex items-center gap-2 text-emerald-400 text-sm font-bold">
                <ArrowUpRight className="w-4 h-4" />
                {dominant.trend_status ?? 'REGULAR'} · {dominant.deltaPct >= 0 ? '+' : ''}
                {dominant.deltaPct} momentum
              </div>
            )}
          </div>
          <div className="glass rounded-3xl p-8 border border-white/5 space-y-4 bg-gradient-to-br from-primary/5 to-transparent">
            <h3 className="text-xs font-black uppercase tracking-widest text-primary">
              Blue Ocean Opportunity
            </h3>
            <h4 className="text-3xl font-black">
              {blueOcean ? truncate(blueOcean.title, 48) : 'No candidate yet'}
            </h4>
            <p className="text-dim">
              {blueOcean
                ? 'High search velocity with low competitor authority overlap detected.'
                : 'Re-rank trends to surface under-covered clusters.'}
            </p>
            <Link
              href="/company/drafts"
              className="text-xs font-black text-primary hover:underline uppercase tracking-widest"
            >
              Generate Strategy Brief
            </Link>
          </div>
        </div>

        <div className="glass rounded-[2.5rem] border border-white/5 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-white/5 text-[10px] font-black uppercase tracking-widest text-dim border-b border-white/5">
                  <th className="px-8 py-5">Strategic Keyword</th>
                  <th className="px-8 py-5">Company Status</th>
                  <th className="px-8 py-5 text-center">Market Vol</th>
                  <th className="px-8 py-5 text-center">Our Authority</th>
                  <th className="px-8 py-5 text-right">Momentum</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {loading && filtered.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-8 py-10 text-center text-dim">
                      <Loader2 className="w-4 h-4 animate-spin inline mr-2" />
                      Loading trend snapshot...
                    </td>
                  </tr>
                )}
                {!loading && filtered.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-8 py-10 text-center text-dim italic">
                      No matching clusters. Clear the filter or run an ingestion + rank.
                    </td>
                  </tr>
                )}
                {filtered.map((row) => (
                  <CompanyTrendRow key={row.cluster_id} row={row} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}

function CompanyTrendRow({ row }: { row: Row }) {
  const isNegative = row.deltaPct < 0;
  const deltaLabel = `${row.deltaPct >= 0 ? '+' : ''}${row.deltaPct}`;
  return (
    <tr className="hover:bg-white/[0.02] transition-colors group">
      <td className="px-8 py-6 font-bold text-white group-hover:text-primary transition-colors">
        {truncate(row.title, 48)}
      </td>
      <td className="px-8 py-6">
        <span
          className={cn(
            'px-3 py-1 rounded-full text-[10px] font-black tracking-widest border uppercase',
            row.company_status === 'OPPORTUNITY'
              ? 'bg-primary/10 text-primary border-primary/20'
              : row.company_status === 'LEADER'
              ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
              : 'bg-white/5 text-dim border-white/10',
          )}
        >
          {row.company_status}
        </span>
      </td>
      <td className="px-8 py-6 text-center text-dim font-medium">
        {formatCount(row.cluster_size * 100 + Math.round(row.social_popularity_score || 0))}
      </td>
      <td className="px-8 py-6 text-center">
        <div className="flex flex-col items-center">
          <span className="text-xs font-bold text-white leading-none">{row.authority.toFixed(2)}</span>
          <div className="w-12 h-1 bg-white/5 rounded-full mt-1">
            <div className="h-full bg-secondary rounded-full" style={{ width: `${row.authority * 100}%` }} />
          </div>
        </div>
      </td>
      <td
        className={cn(
          'px-8 py-6 text-right font-black',
          isNegative ? 'text-red-500' : 'text-emerald-500',
        )}
      >
        {deltaLabel} {isNegative ? '↓' : '↑'}
      </td>
    </tr>
  );
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n - 1) + '…' : s;
}

function formatCount(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}m`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return n.toString();
}
