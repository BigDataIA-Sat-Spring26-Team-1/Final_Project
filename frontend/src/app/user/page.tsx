'use client';

// User dashboard — the "personalized feed" landing page a real consumer sees
// after onboarding. Pulls top recommendations from the RAG endpoint and
// renders the user's current persona alongside. Feedback buttons on each row
// post through to /personas/feedback, which shifts behavioral weights in
// Snowflake and therefore what gets recommended tomorrow.

import {
  Loader2,
  Mail,
  Newspaper,
  Sparkles,
  TriangleAlert,
  User as UserIcon,
} from 'lucide-react';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';

import { FeedableArticleRow } from '@/components/DashboardComponents';
import { PageWrapper } from '@/components/PageWrapper';
import { useAuth } from '@/components/AuthProvider';
import {
  ApiError,
  getPersona,
  getRecommendations,
  getTopTrends,
  type RankedArticle,
  type StoredPersona,
} from '@/lib/api';
import { cn } from '@/lib/utils';

type FeedMode = 'PERSONALIZED' | 'COMMON';

// Same session-scoped key as /user/persona so the two pages share context.
const STORAGE_KEY = 'curateai:user_id';
// Personalized feed keeps the 10-article ceiling (matches the newsletter
// pipeline); the global deck surfaces the top 20 trending clusters since
// that's what the common-highlights MCP tool also returns.
const PERSONAL_LIMIT = 10;
const COMMON_LIMIT = 20;

export default function UserDashboard() {
  const { user } = useAuth();
  const userId = user?.id ?? '';
  const [activeTab, setActiveTab] = useState<FeedMode>('PERSONALIZED');
  const [persona, setPersona] = useState<StoredPersona | null>(null);
  const [articles, setArticles] = useState<RankedArticle[]>([]);
  const [globalArticles, setGlobalArticles] = useState<RankedArticle[]>([]);
  // Start in a loading state so the first paint shows a spinner rather than
  // the "no articles" empty copy — the fetch is kicked off in an effect.
  const [loading, setLoading] = useState(true);
  const [globalLoading, setGlobalLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Keep the "last used user" session key in sync for the legacy pages that
  // still read from it — avoids ripping out every other sessionStorage read.
  useEffect(() => {
    if (userId && typeof window !== 'undefined') {
      sessionStorage.setItem(STORAGE_KEY, userId);
    }
  }, [userId]);

  const loadFeed = useCallback(async (id: string, signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      // Persona + recs in parallel — persona request is small, recs drives the UI.
      const [personaData, recsData] = await Promise.all([
        getPersona(id, signal).catch((err) => {
          // A missing persona shouldn't hide the feed — just show the empty sidebar.
          if (err instanceof ApiError && err.status === 404) return null;
          throw err;
        }),
        getRecommendations(id, PERSONAL_LIMIT, signal),
      ]);
      setPersona(personaData);
      setArticles(recsData.results ?? []);
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      setArticles([]);
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
    if (!userId) return;
    const controller = new AbortController();
    loadFeed(userId, controller.signal);
    return () => controller.abort();
  }, [userId, loadFeed]);

  // Global highlights are the same-day top-ranked clusters, independent of
  // any single user. Fetched once on mount so tab switching is instant.
  useEffect(() => {
    const controller = new AbortController();
    getTopTrends(COMMON_LIMIT, undefined, controller.signal)
      .then((r) => {
        setGlobalArticles(
          r.results.map((t) => ({
            cluster_id: t.cluster_id,
            title: t.title,
            summary: t.summary ?? undefined,
            url: t.url ?? undefined,
            source_name: t.source_name ?? undefined,
            score: t.final_trend_score / 100,
            cluster_size: t.cluster_size,
            categories: t.categories,
            trend_status: t.trend_status,
          })),
        );
      })
      .catch(() => {
        // Tab stays empty on failure — personalized tab has its own error banner.
      })
      .finally(() => {
        if (!controller.signal.aborted) setGlobalLoading(false);
      });
    return () => controller.abort();
  }, []);

  // Optimistic removal on skip — keeps the feed interesting as the user rates.
  const handleArticleFeedback = useCallback(
    (type: 'like' | 'dislike' | 'skip', article: RankedArticle) => {
      if (type === 'skip') {
        setArticles((current) => current.filter((a) => a.cluster_id !== article.cluster_id));
      }
    },
    [],
  );

  const heroRole = persona?.job_title ?? 'Tech Professional';
  const heroArchetype = persona?.persona_archetype;

  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-start gap-6 flex-wrap">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2 text-primary font-bold text-sm uppercase tracking-widest">
              <Sparkles className="w-4 h-4" />
              Welcome back{user?.full_name ? `, ${user.full_name}` : ''}
            </div>
            <h1 className="text-4xl font-bold tracking-tight">Your Daily Feed</h1>
            <p className="text-dim text-lg">
              Daily tech updates curated for your <strong>{heroRole}</strong> persona.
            </p>
          </div>
        </header>

        <div className="flex items-center gap-1 p-1 glass rounded-2xl w-fit border border-white/5">
          <button
            onClick={() => setActiveTab('PERSONALIZED')}
            className={cn(
              'px-6 py-2 rounded-xl text-sm font-bold transition-all',
              activeTab === 'PERSONALIZED'
                ? 'bg-secondary text-white shadow-lg shadow-secondary/20'
                : 'text-dim hover:text-white',
            )}
          >
            Personalized Feed
          </button>
          <button
            onClick={() => setActiveTab('COMMON')}
            className={cn(
              'px-6 py-2 rounded-xl text-sm font-bold transition-all',
              activeTab === 'COMMON'
                ? 'bg-secondary text-white shadow-lg shadow-secondary/20'
                : 'text-dim hover:text-white',
            )}
          >
            Global Highlights
          </button>
        </div>

        {error && (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-6 flex items-start gap-3">
            <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <p className="text-sm text-rose-200">{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
          <div className="lg:col-span-2 space-y-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold flex items-center gap-2">
                <Newspaper className="w-5 h-5 text-primary" />
                {activeTab === 'PERSONALIZED' ? 'Curated Just For You' : 'Top 20 Technical Daily'}
              </h2>
              {loading && <Loader2 className="w-4 h-4 animate-spin text-dim" />}
            </div>

            <div className="space-y-4">
              {activeTab === 'PERSONALIZED' ? (
                <>
                  {loading && articles.length === 0 ? (
                    <FeedSkeleton />
                  ) : (
                    <>
                      {userId && articles.length === 0 && !error && (
                        <PromptCard message="No articles queued — run onboarding, then trigger an ingestion to populate the feed." />
                      )}
                      {articles.map((article) => (
                        <FeedableArticleRow
                          key={article.cluster_id}
                          article={article}
                          userId={userId}
                          onFeedback={handleArticleFeedback}
                        />
                      ))}
                    </>
                  )}
                </>
              ) : (
                <>
                  {globalLoading && globalArticles.length === 0 ? (
                    <FeedSkeleton />
                  ) : (
                    <>
                      {globalArticles.length === 0 && (
                        <PromptCard message="No ranked clusters yet — trigger ingestion + ranking to populate." />
                      )}
                      {globalArticles.map((article) => (
                        <FeedableArticleRow
                          key={article.cluster_id}
                          article={article}
                          userId={userId}
                          onFeedback={handleArticleFeedback}
                        />
                      ))}
                    </>
                  )}
                </>
              )}
            </div>
          </div>

          <div className="space-y-8">
            <div className="glass rounded-3xl p-8 border border-white/5 space-y-6">
              <h3 className="text-lg font-bold flex items-center gap-2">
                <UserIcon className="w-5 h-5 text-secondary" />
                Your Profile
              </h3>

              {persona ? (
                <div className="space-y-4">
                  <div className="space-y-1">
                    <p className="text-[10px] font-black text-dim uppercase tracking-widest leading-none mb-2">
                      Core Alignment
                    </p>
                    <p className="text-sm font-bold text-white">
                      {persona.job_title ?? '—'}
                      {persona.seniority ? ` · ${persona.seniority}` : ''}
                    </p>
                    {heroArchetype && (
                      <p className="text-[10px] font-mono uppercase tracking-widest text-primary">
                        {heroArchetype}
                      </p>
                    )}
                  </div>
                  <div className="space-y-1">
                    <p className="text-[10px] font-black text-dim uppercase tracking-widest leading-none mb-2">
                      Primary Interests
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(persona.explicit_category_weights)
                        .sort(([, a], [, b]) => b - a)
                        .slice(0, 4)
                        .map(([cat]) => (
                          <span
                            key={cat}
                            className="px-2 py-1 rounded-md bg-white/5 text-[10px] font-bold border border-white/10 uppercase"
                          >
                            {cat.replace(/_/g, ' ')}
                          </span>
                        ))}
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-dim">
                  {userId
                    ? 'No persona yet — head to onboarding to set one up.'
                    : 'Enter a user id to see your profile.'}
                </p>
              )}

              <Link
                href="/user/persona"
                className="block w-full py-3 text-center bg-white text-black rounded-xl text-xs font-black uppercase tracking-widest hover:bg-zinc-200 transition-colors"
              >
                Update Persona
              </Link>
            </div>

            <div className="glass rounded-3xl p-8 border border-white/5 space-y-4 bg-gradient-to-br from-secondary/10 to-transparent">
              <Mail className="w-6 h-6 text-secondary mb-2" />
              <h3 className="text-lg font-bold">Newsletter</h3>
              <p className="text-xs text-dim leading-relaxed">
                Generate an on-demand newsletter from your current feed.
              </p>
              <Link
                href="/newsletter"
                className="block w-full py-2 text-center rounded-xl bg-secondary/20 text-secondary text-xs font-black border border-secondary/30 uppercase"
              >
                Open Newsletter Page
              </Link>
            </div>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}

function PromptCard({ message }: { message: string }) {
  return (
    <div className="glass rounded-2xl p-6 border border-dashed border-white/10 text-sm text-dim text-center">
      {message}
    </div>
  );
}

function FeedSkeleton() {
  return (
    <>
      <div className="glass rounded-2xl border border-white/5 p-6 flex items-center gap-3 text-dim text-sm">
        <Loader2 className="w-4 h-4 animate-spin text-primary" />
        Loading your feed…
      </div>
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="glass rounded-2xl border border-white/5 p-6 animate-pulse space-y-3"
        >
          <div className="h-3 bg-white/5 rounded w-1/4" />
          <div className="h-5 bg-white/10 rounded w-3/4" />
          <div className="h-3 bg-white/5 rounded w-full" />
          <div className="h-3 bg-white/5 rounded w-2/3" />
        </div>
      ))}
    </>
  );
}
