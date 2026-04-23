'use client';

// Admin landing page. Three top-level indicators (users, companies, system
// status) + the lightweight "Admin Management" tool and the Prometheus
// metrics panel. Detailed drill-downs live on the dedicated admin pages.

import {
  Building2,
  ShieldCheck,
  TriangleAlert,
  Users,
} from 'lucide-react';
import { useEffect, useState } from 'react';

import { StatCard } from '@/components/DashboardComponents';
import { AdminManagementPanel } from '@/components/AdminManagementPanel';
import { MetricsPanel } from '@/components/MetricsPanel';
import { PageWrapper } from '@/components/PageWrapper';
import { Spinner } from '@/components/Spinner';
import {
  ApiError,
  getHealth,
  listCompanies,
  listUsers,
  type HealthResponse,
} from '@/lib/api';

export default function AdminDashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [userTotal, setUserTotal] = useState<number | null>(null);
  const [companyTotal, setCompanyTotal] = useState<number | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);

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
      listUsers(1, 0, controller.signal).catch(() => null),
      listCompanies(1, 0, controller.signal).catch(() => null),
    ]).then(([h, u, c]) => {
      setHealth(h);
      if (u) setUserTotal(u.total);
      if (c) setCompanyTotal(c.total);
      setStatsLoading(false);
    });
    return () => controller.abort();
  }, []);

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

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <StatCard
            title="Total B2C Users"
            value={statsLoading ? <Spinner size="sm" /> : userTotal !== null ? String(userTotal) : '—'}
            change={userTotal ? `+${userTotal}` : '0'}
            description="Consumer personas on file"
            icon={Users}
          />
          <StatCard
            title="Total B2B Entities"
            value={statsLoading ? <Spinner size="sm" /> : companyTotal !== null ? String(companyTotal) : '—'}
            change={companyTotal ? `+${companyTotal}` : '0'}
            description="Corporate tenants in Snowflake"
            icon={Building2}
          />
          <StatCard
            title="System Status"
            value={statsLoading ? <Spinner size="sm" /> : health?.status ?? '—'}
            change={health ? '100%' : '0'}
            description={
              health
                ? `${health.app_name} v${health.version} · ${health.environment}`
                : 'Health probe failed'
            }
            icon={ShieldCheck}
          />
        </div>

        <AdminManagementPanel />

        <MetricsPanel />
      </div>
    </PageWrapper>
  );
}
