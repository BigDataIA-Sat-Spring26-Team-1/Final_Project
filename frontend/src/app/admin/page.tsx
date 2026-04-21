'use client';

// Admin landing page. The four "global" stat cards mostly need a dedicated
// /admin/stats endpoint that doesn't exist yet — until that lands they read
// "—" with a clear placeholder label. The two real signals available today
// are system health (from /api/v1/health) and the top high-velocity clusters
// (from /api/v1/trend/top), so we show those for real.

import {
  AlertCircle,
  Building2,
  ShieldCheck,
  TrendingUp,
  TriangleAlert,
  Users,
  Zap,
} from 'lucide-react';
import { useEffect, useState } from 'react';

import { ActivityItem, StatCard } from '@/components/DashboardComponents';
import { PageWrapper } from '@/components/PageWrapper';
import {
  ApiError,
  getHealth,
  getTopTrends,
  type HealthResponse,
  type TrendCluster,
} from '@/lib/api';

export default function AdminDashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [trends, setTrends] = useState<TrendCluster[]>([]);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      getHealth(controller.signal).catch((err) => {
        setHealthError(
          err instanceof ApiError
            ? `${err.status}: ${err.detail ?? err.message}`
            : (err as Error).message,
        );
        return null;
      }),
      getTopTrends(5, undefined, controller.signal).catch(() => null),
    ]).then(([h, t]) => {
      setHealth(h);
      if (t) setTrends(t.results);
    });
    return () => controller.abort();
  }, []);

  const surgingCount = trends.filter((t) =>
    ['BREAKING', 'TRENDING', 'VIRAL', 'BREAKING-VIRAL'].includes(
      (t.trend_status ?? '').toUpperCase(),
    ),
  ).length;

  return (
    <PageWrapper>
      <div className="space-y-10">
        <header>
          <h1 className="text-4xl font-bold tracking-tight">System Administration</h1>
          <p className="text-dim text-lg">Global infrastructure overview and cross-sector metrics.</p>
        </header>

        {healthError && (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-4 flex items-start gap-3">
            <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-bold text-rose-200">Backend unreachable</p>
              <p className="text-xs text-rose-300/80">{healthError}</p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* TODO: wire to /api/v1/admin/users when endpoint lands. */}
          <StatCard
            title="Total B2C Users"
            value="—"
            change="0"
            description="Pending /admin/users endpoint"
            icon={Users}
          />
          <StatCard
            title="Total B2B Entities"
            value="—"
            change="0"
            description="Pending /admin/companies endpoint"
            icon={Building2}
          />
          <StatCard
            title="High-Velocity Clusters"
            value={String(surgingCount)}
            change={surgingCount > 0 ? `+${surgingCount}` : '0'}
            description="From the last trend ranking pass"
            icon={Zap}
          />
          <StatCard
            title="System Status"
            value={health?.status ?? '—'}
            change={health ? '100%' : '0'}
            description={
              health
                ? `${health.app_name} v${health.version} · ${health.environment}`
                : 'Health probe failed'
            }
            icon={ShieldCheck}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="space-y-6">
            <h2 className="text-xl font-bold flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-secondary" />
              High Velocity Clusters
            </h2>
            <div className="space-y-4">
              {trends.length === 0 && (
                <p className="text-sm text-dim italic">
                  No ranked clusters yet — trigger ingestion + rank to populate.
                </p>
              )}
              {trends.slice(0, 4).map((t) => (
                <ActivityItem
                  key={t.cluster_id}
                  title={t.title}
                  source={t.trend_status ?? 'REGULAR'}
                  time={`${t.cluster_size} sources`}
                  status={t.trend_status ?? 'QUEUED'}
                  relevancy={Math.min(100, Math.round(t.final_trend_score))}
                />
              ))}
            </div>
          </div>

          <div className="space-y-6">
            <h2 className="text-xl font-bold flex items-center gap-2 text-amber-400">
              <AlertCircle className="w-5 h-5" />
              Pending Admin Reviews
            </h2>
            <div className="glass rounded-3xl p-6 border border-white/5 space-y-3">
              <p className="text-sm text-dim italic">
                Newsletter approval queue requires the
                <code className="font-mono bg-white/5 mx-1 px-1.5 py-0.5 rounded">
                  GET /admin/newsletters/pending
                </code>
                endpoint, which is on Abhinav&apos;s backlog. UI is wired and ready
                to consume the response once it ships.
              </p>
            </div>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}
