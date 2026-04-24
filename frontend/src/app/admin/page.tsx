'use client';

// Admin landing page — a read-only overview of platform state. User +
// company creation is now handled via the public signup flow, so the
// old Admin Management panel was removed. What's left is a grid of
// headline metrics backed by /admin/stats plus the live Prometheus
// panel.

import {
  Activity,
  Building2,
  FileText,
  Mail,
  Newspaper,
  Sparkles,
  TriangleAlert,
  Users,
} from 'lucide-react';
import { useEffect, useState } from 'react';

import { StatCard } from '@/components/DashboardComponents';
import { MetricsPanel } from '@/components/MetricsPanel';
import { PageWrapper } from '@/components/PageWrapper';
import { Spinner } from '@/components/Spinner';
import {
  ApiError,
  getAdminStats,
  getHealth,
  type AdminStatsResponse,
  type HealthResponse,
} from '@/lib/api';

export default function AdminDashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [stats, setStats] = useState<AdminStatsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      getHealth(controller.signal).catch((err) => {
        if ((err as Error).name === 'AbortError') return null;
        setError(
          err instanceof ApiError
            ? `${err.status}: ${err.detail ?? err.message}`
            : (err as Error).message,
        );
        return null;
      }),
      getAdminStats(controller.signal).catch(() => null),
    ]).then(([h, s]) => {
      if (controller.signal.aborted) return;
      setHealth(h);
      setStats(s);
      setLoading(false);
    });
    return () => controller.abort();
  }, []);

  const fmt = (n: number | undefined) =>
    typeof n === 'number' ? n.toLocaleString() : '—';

  return (
    <PageWrapper>
      <div className="space-y-10">
        <header>
          <h1 className="text-4xl font-bold tracking-tight">System Administration</h1>
          <p className="text-dim text-lg">Global infrastructure overview and cross-sector metrics.</p>
        </header>

        {error && (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-4 flex items-start gap-3">
            <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-bold text-rose-200">Backend unreachable</p>
              <p className="text-xs text-rose-300/80">{error}</p>
            </div>
          </div>
        )}

        {/* Identity + system health — the 3 top-level indicators that were already here. */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <StatCard
            title="B2C Readers"
            value={loading ? <Spinner size="sm" /> : fmt(stats?.users.total)}
            change={stats ? `${stats.personas.total} personas` : '—'}
            description="USER-role accounts on file"
            icon={Users}
          />
          <StatCard
            title="B2B Tenants"
            value={loading ? <Spinner size="sm" /> : fmt(stats?.companies.total)}
            change={stats ? `${stats.users.companies} logins` : '—'}
            description="Corporate rows in companies"
            icon={Building2}
          />
          <StatCard
            title="System Status"
            value={loading ? <Spinner size="sm" /> : health?.status ?? '—'}
            change={health ? '100%' : '—'}
            description={
              health
                ? `${health.app_name} v${health.version} · ${health.environment}`
                : 'Health probe failed'
            }
            icon={Activity}
          />
        </div>

        {/* Delivery funnel — newsletters + briefs generated vs sent. */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="Newsletters Generated"
            value={loading ? <Spinner size="sm" /> : fmt(stats?.newsletters.generated)}
            change={stats ? `${stats.newsletters.today_generated} today` : '—'}
            description="Rows with rendered HTML"
            icon={Newspaper}
          />
          <StatCard
            title="Newsletters Sent"
            value={loading ? <Spinner size="sm" /> : fmt(stats?.newsletters.sent)}
            change={
              stats && stats.newsletters.generated
                ? `${Math.round((stats.newsletters.sent / stats.newsletters.generated) * 100)}% delivery`
                : '—'
            }
            description="Gmail SMTP dispatches"
            icon={Mail}
          />
          <StatCard
            title="Strategic Briefs"
            value={loading ? <Spinner size="sm" /> : fmt(stats?.briefs.generated)}
            change={stats ? `${stats.briefs.today_generated} today` : '—'}
            description="B2B briefs in archive"
            icon={FileText}
          />
          <StatCard
            title="Ranked Clusters"
            value={loading ? <Spinner size="sm" /> : fmt(stats?.clusters.ranked)}
            change={stats ? `of ${fmt(stats.clusters.total)}` : '—'}
            description="Clusters with a trend score"
            icon={Sparkles}
          />
        </div>

        {/* Ingestion funnel — raw-article throughput. */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <StatCard
            title="Articles (Total)"
            value={loading ? <Spinner size="sm" /> : fmt(stats?.articles.total)}
            change={stats ? `${fmt(stats.articles.clustered)} clustered` : '—'}
            description="All rows in articles_raw"
            icon={Newspaper}
          />
          <StatCard
            title="Articles · Last 24h"
            value={loading ? <Spinner size="sm" /> : fmt(stats?.articles.last_24h)}
            change={
              stats && stats.articles.total
                ? `${Math.round((stats.articles.last_24h / stats.articles.total) * 1000) / 10}%`
                : '—'
            }
            description="Fresh articles by published_at"
            icon={Activity}
          />
          <StatCard
            title="Clustering Coverage"
            value={
              loading ? (
                <Spinner size="sm" />
              ) : stats && stats.articles.total
                ? `${Math.round((stats.articles.clustered / stats.articles.total) * 100)}%`
                : '—'
            }
            change={stats ? `${fmt(stats.articles.clustered)} linked` : '—'}
            description="articles_raw → article_clusters"
            icon={Sparkles}
          />
        </div>

        <MetricsPanel />
      </div>
    </PageWrapper>
  );
}
