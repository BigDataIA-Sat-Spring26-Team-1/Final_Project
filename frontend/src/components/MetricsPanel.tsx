'use client';

// Live Prometheus metrics panel.
//
// Polls /api/v1/metrics/summary every 10 seconds. The backend does the
// histogram/counter aggregation — we just render. If the summary endpoint
// fails (deploy mid-flight, backend down) we keep the last good snapshot
// and show a staleness badge instead of wiping the UI.

import { Activity, AlertCircle, Cpu, Gauge, Workflow } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { ApiError, getMetricsSummary, type MetricsSummary } from '@/lib/api';

const REFRESH_MS = 10_000;

export function MetricsPanel() {
  const [summary, setSummary] = useState<MetricsSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    const abort = new AbortController();

    const fetchOnce = async () => {
      try {
        const next = await getMetricsSummary(abort.signal);
        if (!mounted.current) return;
        setSummary(next);
        setLastUpdated(new Date());
        setError(null);
      } catch (err) {
        if (!mounted.current || abort.signal.aborted) return;
        setError(
          err instanceof ApiError
            ? `${err.status}: ${err.detail ?? err.message}`
            : (err as Error).message,
        );
      }
    };

    fetchOnce();
    const id = setInterval(fetchOnce, REFRESH_MS);
    return () => {
      mounted.current = false;
      clearInterval(id);
      abort.abort();
    };
  }, []);

  const totalLlmRequests = summary
    ? Object.values(summary.llm.requests_by_status).reduce((a, b) => a + b, 0)
    : 0;
  const totalTokens = summary
    ? Object.values(summary.llm.tokens_by_type).reduce((a, b) => a + b, 0)
    : 0;
  const totalCost = summary
    ? Object.values(summary.llm.cost_usd_by_model).reduce((a, b) => a + b, 0)
    : 0;
  const dagAccepted = summary?.dags.triggers_by_outcome.accepted ?? 0;
  const dagRejected = summary?.dags.triggers_by_outcome.rejected ?? 0;

  const topNodes = summary
    ? Object.entries(summary.agents.node_latency)
        .map(([label, v]) => ({ label: label.replace('node_name=', ''), ...v }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 6)
    : [];

  return (
    <div className="glass rounded-3xl border border-white/5 p-8 space-y-6">
      <header className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <Activity className="w-5 h-5 text-secondary" />
          <h2 className="text-xl font-bold">Live Prometheus Metrics</h2>
        </div>
        <span className="text-[10px] uppercase tracking-widest font-bold text-dim">
          {lastUpdated
            ? `updated ${lastUpdated.toLocaleTimeString()}`
            : 'fetching…'}
        </span>
      </header>

      {error && (
        <div className="p-3 bg-rose-500/5 border border-rose-500/20 rounded-lg flex items-start gap-2 text-xs">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <span className="text-rose-200 font-mono">{error}</span>
        </div>
      )}

      {/* Top-level stat row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat
          label="LLM calls"
          value={totalLlmRequests.toLocaleString()}
          sub={`${formatNumber(totalTokens)} tokens`}
          icon={Cpu}
        />
        <Stat
          label="LLM spend"
          value={`$${totalCost.toFixed(2)}`}
          sub="estimated"
          icon={Gauge}
        />
        <Stat
          label="DAG triggers"
          value={dagAccepted.toFixed(0)}
          sub={dagRejected > 0 ? `${dagRejected} rejected` : 'all accepted'}
          tone={dagRejected > 0 ? 'warn' : 'ok'}
          icon={Workflow}
        />
        <Stat
          label="Editor rejections"
          value={(summary?.agents.newsletter_rejections ?? 0).toFixed(0)}
          sub="newsletter loop"
          icon={AlertCircle}
        />
      </div>

      {/* LangGraph node latency */}
      <div className="space-y-3">
        <h3 className="text-sm font-bold text-dim uppercase tracking-widest">
          Agent node latency (avg)
        </h3>
        {topNodes.length === 0 ? (
          <p className="text-xs text-dim italic">
            No agent runs recorded yet. Trigger a newsletter or B2B brief.
          </p>
        ) : (
          <div className="space-y-2">
            {topNodes.map((n) => (
              <LatencyRow key={n.label} label={n.label} avg={n.avg_seconds} count={n.count} />
            ))}
          </div>
        )}
      </div>

      {/* DAG trigger latency */}
      <div className="space-y-3">
        <h3 className="text-sm font-bold text-dim uppercase tracking-widest">
          Airflow trigger latency
        </h3>
        {summary && Object.keys(summary.dags.trigger_latency).length === 0 ? (
          <p className="text-xs text-dim italic">
            No DAG triggers this session.
          </p>
        ) : (
          <div className="space-y-2">
            {summary &&
              Object.entries(summary.dags.trigger_latency)
                .sort(([, a], [, b]) => b.count - a.count)
                .slice(0, 6)
                .map(([k, v]) => (
                  <LatencyRow
                    key={k}
                    label={k.replace('dag_id=', '')}
                    avg={v.avg_seconds}
                    count={v.count}
                  />
                ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  sub,
  icon: Icon,
  tone = 'ok',
}: {
  label: string;
  value: string;
  sub: string;
  icon: React.ComponentType<{ className?: string }>;
  tone?: 'ok' | 'warn';
}) {
  const subColor = tone === 'warn' ? 'text-amber-400' : 'text-emerald-400';
  return (
    <div className="rounded-2xl border border-white/5 bg-white/5 p-4 space-y-1">
      <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-dim font-bold">
        <Icon className="w-3.5 h-3.5" /> {label}
      </div>
      <div className="text-2xl font-black">{value}</div>
      <div className={`text-[11px] font-bold ${subColor}`}>{sub}</div>
    </div>
  );
}

function LatencyRow({
  label,
  avg,
  count,
}: {
  label: string;
  avg: number;
  count: number;
}) {
  // Scale bar against a 2-second ceiling — tasks beyond that are saturated.
  const pct = Math.max(3, Math.min(100, (avg / 2) * 100));
  return (
    <div className="space-y-1">
      <div className="flex items-baseline justify-between text-xs">
        <span className="font-mono truncate max-w-[60%]">{label}</span>
        <span className="text-dim font-bold">
          {avg.toFixed(3)}s · {count.toFixed(0)} samples
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
        <div className="h-full bg-secondary" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return n.toFixed(0);
}
