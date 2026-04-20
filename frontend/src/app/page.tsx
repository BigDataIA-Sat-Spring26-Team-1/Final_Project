'use client';

// Home / system overview. Reads liveness + Snowflake readiness from the
// backend and (when a user id is set) shows the top personalized recs as the
// "recent ingestion stream". The numerical stat cards currently hold
// placeholder values — they'll wire up once a dedicated /admin/stats endpoint
// exists (tracked in the pending tasks doc).

import {
  Activity,
  Brain,
  CheckCircle2,
  Clock,
  Loader2,
  Newspaper,
  TrendingUp,
  TriangleAlert,
  Zap,
} from 'lucide-react';
import { useEffect, useState } from 'react';

import {
  ActivityItem,
  StatCard,
  TrendTag,
} from '@/components/DashboardComponents';
import { PageWrapper } from '@/components/PageWrapper';
import {
  ApiError,
  getHealth,
  getRecommendations,
  type HealthResponse,
  type RankedArticle,
} from '@/lib/api';

const STORAGE_KEY = 'curateai:user_id';

export default function Home() {
  const [userId, setUserId] = useState('');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [articles, setArticles] = useState<RankedArticle[]>([]);
  const [loadingArticles, setLoadingArticles] = useState(false);

  // Pull health on mount — gives us an immediate signal of whether the backend
  // is even reachable, and surfaces the Snowflake version we're talking to.
  useEffect(() => {
    const controller = new AbortController();
    getHealth(controller.signal)
      .then(setHealth)
      .catch((err) => {
        if (err.name === 'AbortError') return;
        setHealthError(
          err instanceof ApiError
            ? `${err.status}: ${err.detail ?? err.message}`
            : (err as Error).message,
        );
      });
    const saved = sessionStorage.getItem(STORAGE_KEY);
    if (saved) setUserId(saved);
    return () => controller.abort();
  }, []);

  // Ingestion stream = top personalized articles. Only meaningful when a
  // user id is available; otherwise we leave the section empty rather than
  // filling it with stale fake data. The loading flag flips via the async
  // chain (not synchronously in the effect body) to satisfy React 19's
  // set-state-in-effect linter.
  useEffect(() => {
    if (!userId) return;
    const controller = new AbortController();
    (async () => {
      setLoadingArticles(true);
      try {
        const r = await getRecommendations(userId, 4, controller.signal);
        setArticles(r.results ?? []);
      } catch (err) {
        if ((err as Error).name !== 'AbortError') setArticles([]);
      } finally {
        setLoadingArticles(false);
      }
    })();
    return () => controller.abort();
  }, [userId]);

  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between gap-6 flex-wrap">
          <div className="flex flex-col gap-2">
            <h1 className="text-4xl font-bold tracking-tight">Intelligence Overview</h1>
            <p className="text-muted-foreground text-lg">
              System heartbeat and content curation metrics.
            </p>
          </div>
          <input
            type="text"
            placeholder="user id for personalized stream"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            onBlur={() => userId && sessionStorage.setItem(STORAGE_KEY, userId)}
            className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm outline-none focus:border-primary/40 font-mono min-w-[280px]"
          />
        </header>

        {/* System status banner — only rendered when something interesting to say. */}
        {healthError ? (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-4 flex items-start gap-3">
            <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-bold text-rose-200">Backend unreachable</p>
              <p className="text-xs text-rose-300/80">{healthError}</p>
            </div>
          </div>
        ) : health ? (
          <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4 flex items-center gap-3 flex-wrap">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <p className="text-sm">
              <strong className="text-emerald-400">{health.status}</strong>
              <span className="text-dim"> — {health.app_name} v{health.version}</span>
              <span className="text-dim"> · env: {health.environment}</span>
              <span className="text-dim"> · snowflake: {health.snowflake_version}</span>
            </p>
          </div>
        ) : null}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* TODO: wire these once /api/v1/admin/stats endpoint exists. */}
          <StatCard
            title="Daily Ingestion"
            value="—"
            change="0"
            description="Articles processed today"
            icon={Zap}
          />
          <StatCard
            title="Avg. Relevancy"
            value="—"
            change="0"
            description="Personalization score"
            icon={CheckCircle2}
          />
          <StatCard
            title="Agent Cycles"
            value="—"
            change="0"
            description="LangGraph executions"
            icon={Brain}
          />
          <StatCard
            title="Drafts Ready"
            value="—"
            change="0"
            description="Pending human review"
            icon={Newspaper}
            isWarning
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold flex items-center gap-2">
                <Clock className="w-5 h-5 text-primary" />
                Recent Ingestion Stream
              </h2>
              {loadingArticles && <Loader2 className="w-4 h-4 animate-spin text-dim" />}
            </div>

            <div className="space-y-4">
              {!userId && (
                <div className="glass rounded-2xl p-6 border border-dashed border-white/10 text-sm text-dim text-center">
                  Enter a user id above to preview today&apos;s curated stream.
                </div>
              )}

              {userId && articles.length === 0 && !loadingArticles && (
                <div className="glass rounded-2xl p-6 border border-dashed border-white/10 text-sm text-dim text-center">
                  No recommendations yet. Trigger an ingestion run, then revisit.
                </div>
              )}

              {articles.map((article) => (
                <ActivityItem
                  key={article.cluster_id}
                  title={article.title}
                  source={(article.trend_status as string) ?? 'RECOMMENDED'}
                  time={article.cluster_size ? `${article.cluster_size} sources` : 'fresh'}
                  status={article.trend_status ?? 'QUALIFIED'}
                  relevancy={Math.round((article.score ?? 0) * 100)}
                />
              ))}
            </div>
          </div>

          <div className="space-y-6">
            <h2 className="text-xl font-bold flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-primary" />
              Active Trends
            </h2>
            {/* TODO: wire to GET /api/v1/trend once a read endpoint exists. */}
            <div className="glass rounded-2xl p-6 space-y-5 border border-white/5">
              <TrendTag name="LLM Safety" count={42} velocity="High" />
              <TrendTag name="HNSW Indexing" count={18} velocity="Stable" />
              <TrendTag name="EU AI Policy" count={31} velocity="Surging" />
              <TrendTag name="RAG Architectures" count={56} velocity="Peak" />
              <div className="text-[10px] uppercase font-bold tracking-widest text-dim flex items-center gap-1 pt-2">
                <Activity className="w-3 h-3" /> placeholder · live trend API pending
              </div>
            </div>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}
