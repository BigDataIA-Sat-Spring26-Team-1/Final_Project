'use client';

// Persona dashboard. Reads the user's explicit + behavioral weights from the
// backend and renders them side by side so the user can see how their
// onboarding profile has drifted as they've liked / disliked content.

import { Loader2, Plus, RefreshCw, TriangleAlert, Zap } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { PageWrapper } from '@/components/PageWrapper';
import { ApiError, getPersona, type StoredPersona } from '@/lib/api';
import { cn } from '@/lib/utils';

// Lightweight "remember last used id" — sessionStorage keeps it per-tab so
// multiple demo windows don't collide. Swap for real auth when available.
const STORAGE_KEY = 'curateai:user_id';

export default function UserPersonaPage() {
  const [userId, setUserId] = useState('');
  const [persona, setPersona] = useState<StoredPersona | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Restore the last-used id on mount so page refreshes don't wipe context.
  useEffect(() => {
    const saved = typeof window !== 'undefined' ? sessionStorage.getItem(STORAGE_KEY) : null;
    if (saved) setUserId(saved);
  }, []);

  const loadPersona = useCallback(async (id: string, signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getPersona(id, signal);
      setPersona(data);
      sessionStorage.setItem(STORAGE_KEY, id);
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      setPersona(null);
      setError(
        err instanceof ApiError
          ? err.status === 404
            ? 'No persona found — run onboarding first.'
            : `${err.status}: ${err.detail ?? err.message}`
          : (err as Error).message,
      );
    } finally {
      setLoading(false);
    }
  }, []);

  // Auto-load whenever userId is set (on mount or after rehydration).
  useEffect(() => {
    if (!userId) return;
    const controller = new AbortController();
    loadPersona(userId, controller.signal);
    return () => controller.abort();
  }, [userId, loadPersona]);

  const topInterests = useMemo(() => {
    if (!persona) return [];
    return Object.entries(persona.explicit_category_weights)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 6)
      .map(([cat]) => cat);
  }, [persona]);

  const topBehavioral = useMemo(() => {
    if (!persona) return [];
    return Object.entries(persona.behavioral_category_weights)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 3);
  }, [persona]);

  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between gap-6 flex-wrap">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">Persona Intelligence</h1>
            <p className="text-dim text-lg">
              Deep technical profile and behavioral refinement
              {persona?.job_title ? ` for ${persona.job_title}` : ''}.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="text"
              placeholder="user id"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm outline-none focus:border-primary/40 font-mono"
            />
            <button
              onClick={() => userId && loadPersona(userId)}
              disabled={!userId || loading}
              className="bg-primary hover:bg-primary/90 disabled:opacity-40 text-primary-foreground px-6 py-3 rounded-2xl text-sm font-bold transition-all flex items-center gap-2"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              {loading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </header>

        {error && (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-6 flex items-start gap-3">
            <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <p className="text-sm text-rose-200">{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-8">
            <div className="glass rounded-[2rem] p-10 border border-white/5 space-y-8">
              <div className="space-y-2">
                <h3 className="text-2xl font-bold">Dynamic Persona Logic</h3>
                <p className="text-sm text-dim">
                  Your persona is automatically evolved based on search intent and article interactions.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="space-y-4">
                  <h4 className="text-xs font-black uppercase tracking-widest text-secondary">
                    Explicit Category Weights
                  </h4>
                  <div className="space-y-3">
                    {persona ? (
                      Object.entries(persona.explicit_category_weights)
                        .sort(([, a], [, b]) => b - a)
                        .slice(0, 5)
                        .map(([cat, weight]) => (
                          <RoleItem
                            key={cat}
                            title={humanize(cat)}
                            score={Math.round(weight * 100)}
                          />
                        ))
                    ) : (
                      <EmptyHint loading={loading} hint="no persona loaded" />
                    )}
                  </div>
                </div>

                <div className="space-y-4">
                  <h4 className="text-xs font-black uppercase tracking-widest text-secondary">
                    Interest Clusters
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {persona ? (
                      topInterests.map((tag) => (
                        <span
                          key={tag}
                          className="px-3 py-1.5 rounded-xl bg-white/5 border border-white/10 text-xs font-bold text-white"
                        >
                          {humanize(tag)}
                        </span>
                      ))
                    ) : (
                      <EmptyHint loading={loading} hint="—" />
                    )}
                  </div>
                </div>
              </div>
            </div>

            <div className="glass rounded-[2rem] p-10 border border-white/5 space-y-4">
              <h3 className="text-xl font-bold">Behavioral Refinement</h3>
              <p className="text-sm text-dim">
                Weights learned from your like / dislike / skip feedback. These layer on top of the
                onboarding profile.
              </p>
              {persona ? (
                topBehavioral.length === 0 ? (
                  <p className="text-sm text-dim italic">
                    No behavioral signals yet — interact with articles to start shaping this.
                  </p>
                ) : (
                  topBehavioral.map(([cat, weight]) => (
                    <div key={cat} className="flex items-center gap-4 pt-2">
                      <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary"
                          style={{ width: `${Math.round(weight * 100)}%` }}
                        />
                      </div>
                      <span className="text-xs font-bold text-primary min-w-[160px] text-right">
                        {Math.round(weight * 100)}% · {humanize(cat)}
                      </span>
                    </div>
                  ))
                )
              ) : (
                <EmptyHint loading={loading} hint="—" />
              )}
            </div>
          </div>

          <div className="space-y-6">
            <div className="glass rounded-3xl p-8 border border-white/5 space-y-6">
              <h3 className="text-lg font-bold flex items-center gap-2">
                <Zap className="w-5 h-5 text-amber-400" />
                Agentic Hooks
              </h3>
              <div className="space-y-4">
                <HookItem title="LinkedIn Sync" active={!!persona?.bio_summary} />
                <HookItem title="GitHub Analyzer" />
                <HookItem title="X/Twitter Insights" />
              </div>
              <button className="w-full py-4 glass border-dashed border-white/10 rounded-2xl flex items-center justify-center gap-2 text-xs font-bold text-dim hover:text-white transition-all">
                <Plus className="w-4 h-4" />
                Add Integration
              </button>
            </div>

            {persona?.bio_summary && (
              <div className="glass rounded-3xl p-8 border border-white/5 space-y-3">
                <h3 className="text-lg font-bold">Bio</h3>
                <p className="text-sm text-dim leading-relaxed">{persona.bio_summary}</p>
                {persona.persona_archetype && (
                  <p className="text-[10px] font-mono uppercase tracking-widest text-primary">
                    {persona.persona_archetype}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}

// ---- Small presentational helpers -------------------------------------------

/** Turn `ai_agents` into `AI Agents` — the backend taxonomy uses snake_case. */
function humanize(key: string): string {
  return key
    .split('_')
    .map((w) => (w === 'ai' || w === 'llms' ? w.toUpperCase() : w[0]?.toUpperCase() + w.slice(1)))
    .join(' ');
}

function RoleItem({ title, score }: { title: string; score: number }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm font-bold text-white">{title}</span>
      <span className="text-xs font-bold text-primary">{score}%</span>
    </div>
  );
}

function HookItem({ title, active }: { title: string; active?: boolean }) {
  return (
    <div className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] border border-white/5">
      <span className="text-sm font-medium text-white">{title}</span>
      <span
        className={cn(
          'px-2 py-0.5 rounded-md text-[10px] font-black uppercase tracking-tighter',
          active ? 'bg-emerald-500/10 text-emerald-500' : 'text-dim',
        )}
      >
        {active ? 'Linked' : 'Offline'}
      </span>
    </div>
  );
}

function EmptyHint({ loading, hint }: { loading: boolean; hint: string }) {
  return (
    <p className="text-xs text-dim italic">
      {loading ? 'Loading...' : hint}
    </p>
  );
}
