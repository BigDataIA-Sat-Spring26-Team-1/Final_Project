'use client';

// Keyword Velocity dashboard for the enterprise console. Powered by the
// SpaCy NER endpoint (/api/v1/b2b/keyword-velocity) — the response is a list
// of entities (companies, products, people) with mention counts and a
// SURGING / STABLE / DECLINING tag. Matches the S5 prototype layout:
//
//   ENTITY | CURR 24h | PREV 24h | TOTAL | STATUS | VELOCITY
//
// The date picker anchors the "current" window; max is yesterday because the
// ingestion DAG runs daily and today's partial window is noisy.

import { ArrowDownRight, ArrowUpRight, Calendar, Loader2, Search, TriangleAlert } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { PageWrapper } from '@/components/PageWrapper';
import { Spinner } from '@/components/Spinner';
import {
  ApiError,
  getKeywordVelocity,
  type KeywordVelocityResponse,
  type KeywordVelocityRow,
} from '@/lib/api';
import { cn } from '@/lib/utils';

function yesterdayIso(): string {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().slice(0, 10);
}

export default function KeywordVelocityPage() {
  const [date, setDate] = useState<string>(yesterdayIso());
  const [filter, setFilter] = useState('');
  const [data, setData] = useState<KeywordVelocityResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      setLoading(true);
      setError(null);
      setData(null);
      try {
        const res = await getKeywordVelocity(date || undefined, 30, controller.signal);
        if (controller.signal.aborted) return;
        setData(res);
      } catch (err) {
        if ((err as Error).name === 'AbortError') return;
        setError(
          err instanceof ApiError
            ? `${err.status}: ${err.detail ?? err.message}`
            : (err as Error).message,
        );
      } finally {
        // Only flip loading off when this effect is still the active one.
        // React 19 strict mode double-mounts each effect; without this guard
        // the first (aborted) pass clears loading before the real fetch
        // finishes, making the spinners disappear while the page is empty.
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    })();
    return () => controller.abort();
  }, [date]);

  const filtered = useMemo(() => {
    if (!data) return [];
    if (!filter.trim()) return data.results;
    const q = filter.trim().toLowerCase();
    return data.results.filter((r) => r.entity.toLowerCase().includes(q));
  }, [data, filter]);

  const surgingCount = useMemo(
    () => (data?.results ?? []).filter((r) => r.status === 'SURGING').length,
    [data],
  );
  const topEntity = data?.results?.[0];

  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between gap-4 flex-wrap">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">Keyword Velocity</h1>
            <p className="text-dim text-lg">
              SpaCy NER-discovered entities with 24-hour mention velocity.
            </p>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center glass rounded-xl px-4 py-2 border border-white/5 focus-within:border-primary/40">
              <Calendar className="w-4 h-4 text-dim mr-2" />
              <input
                type="date"
                value={date}
                max={yesterdayIso()}
                onChange={(e) => setDate(e.target.value)}
                className="bg-transparent border-none outline-none text-sm placeholder:text-dim"
              />
            </div>
            <div className="flex items-center glass rounded-xl px-4 py-2 border border-white/5 focus-within:border-primary/40">
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
        </header>

        {error && (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-6 flex items-start gap-3">
            <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <p className="text-sm text-rose-200">{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="glass rounded-3xl p-8 border border-white/5 space-y-2">
            <p className="text-[10px] font-black text-dim uppercase tracking-widest">
              Current Window
            </p>
            <h3 className="text-xl font-black font-mono">
              {loading ? <Spinner size="sm" /> : data?.target_date ?? '—'}
            </h3>
            <p className="text-xs text-dim">
              compared against {data?.previous_date ?? 'the prior day'}
            </p>
          </div>
          <div className="glass rounded-3xl p-8 border border-white/5 space-y-2 bg-gradient-to-br from-emerald-500/5 to-transparent">
            <p className="text-[10px] font-black text-emerald-400 uppercase tracking-widest">
              Surging Entities
            </p>
            <h3 className="text-3xl font-black">
              {loading ? <Spinner size="sm" /> : surgingCount}
            </h3>
            <p className="text-xs text-dim">velocity &gt; +50% vs prior window</p>
          </div>
          <div className="glass rounded-3xl p-8 border border-white/5 space-y-2 bg-gradient-to-br from-primary/5 to-transparent">
            <p className="text-[10px] font-black text-primary uppercase tracking-widest">
              Top Entity
            </p>
            <h3 className="text-xl font-black truncate">
              {loading ? <Spinner size="sm" /> : topEntity?.entity ?? '—'}
            </h3>
            <p className="text-xs text-dim">
              {topEntity
                ? `${topEntity.total_mentions} mentions · ${topEntity.status}`
                : 'No signals yet'}
            </p>
          </div>
        </div>

        <div className="glass rounded-[2.5rem] border border-white/5 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-white/5 text-[10px] font-black uppercase tracking-widest text-dim border-b border-white/5">
                  <th className="px-8 py-5">Entity</th>
                  <th className="px-8 py-5 text-center">Current 24h</th>
                  <th className="px-8 py-5 text-center">Previous 24h</th>
                  <th className="px-8 py-5 text-center">Total Mentions</th>
                  <th className="px-8 py-5 text-right">Velocity</th>
                  <th className="px-8 py-5">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {loading && (
                  <tr>
                    <td colSpan={6} className="px-8 py-10 text-center">
                      <Loader2 className="w-5 h-5 animate-spin inline text-dim" />
                      <span className="ml-3 text-dim text-sm">Running SpaCy NER…</span>
                    </td>
                  </tr>
                )}
                {!loading && filtered.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-8 py-10 text-center text-dim italic">
                      No entities for the selected day — try a different date or widen the filter.
                    </td>
                  </tr>
                )}
                {!loading && filtered.map((row) => <VelocityRow key={row.entity} row={row} />)}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}

function VelocityRow({ row }: { row: KeywordVelocityRow }) {
  const positive = row.velocity_pct >= 0;
  const statusClass =
    row.status === 'SURGING'
      ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
      : row.status === 'DECLINING'
      ? 'bg-red-500/10 text-red-500 border-red-500/20'
      : 'bg-white/5 text-dim border-white/10';

  return (
    <tr className="hover:bg-white/[0.02] transition-colors">
      <td className="px-8 py-5 font-bold text-white">{row.entity}</td>
      <td className="px-8 py-5 text-center font-mono">{row.current}</td>
      <td className="px-8 py-5 text-center font-mono text-dim">{row.previous}</td>
      <td className="px-8 py-5 text-center font-bold">{row.total_mentions}</td>
      <td
        className={cn(
          'px-8 py-5 text-right font-black',
          positive ? 'text-emerald-500' : 'text-red-500',
        )}
      >
        <span className="inline-flex items-center gap-1">
          {positive ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
          {positive ? '+' : ''}
          {row.velocity_pct.toFixed(1)}%
        </span>
      </td>
      <td className="px-8 py-5">
        <span
          className={cn(
            'px-3 py-1 rounded-full text-[10px] font-black tracking-widest border uppercase',
            statusClass,
          )}
        >
          {row.status}
        </span>
      </td>
    </tr>
  );
}
