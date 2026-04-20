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
import {
  ApiError,
  getPersona,
  getRecommendations,
  type RankedArticle,
  type StoredPersona,
} from '@/lib/api';
import { cn } from '@/lib/utils';

type FeedMode = 'PERSONALIZED' | 'COMMON';

// Same session-scoped key as /user/persona so the two pages share context.
const STORAGE_KEY = 'curateai:user_id';
const FEED_LIMIT = 10;

export default function UserDashboard() {
  const [activeTab, setActiveTab] = useState<FeedMode>('PERSONALIZED');
  const [userId, setUserId] = useState('');
  const [persona, setPersona] = useState<StoredPersona | null>(null);
  const [articles, setArticles] = useState<RankedArticle[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Restore the id from the previous session.
  useEffect(() => {
    const saved = typeof window !== 'undefined' ? sessionStorage.getItem(STORAGE_KEY) : null;
    if (saved) setUserId(saved);
  }, []);

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
        getRecommendations(id, FEED_LIMIT, signal),
      ]);
      setPersona(personaData);
      setArticles(recsData.results ?? []);
      sessionStorage.setItem(STORAGE_KEY, id);
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
        <header className="flex items-start justify-between gap-6 flex-wrap">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2 text-primary font-bold text-sm uppercase tracking-widest">
              <Sparkles className="w-4 h-4" />
              Welcome back{persona ? `, ${persona.job_title ?? ''}` : ''}
            </div>
            <h1 className="text-4xl font-bold tracking-tight">Your Intelligence Loop</h1>
            <p className="text-dim text-lg">
              Daily tech updates curated for your <strong>{heroRole}</strong> persona.
            </p>
          </div>

          {/* Tiny user id input — the demo auth story until real login lands. */}
          <input
            type="text"
            placeholder="user id"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm outline-none focus:border-primary/40 font-mono min-w-[220px]"
          />
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
            disabled
            title="Global highlights endpoint not yet available"
            className={cn(
              'px-6 py-2 rounded-xl text-sm font-bold transition-all',
              activeTab === 'COMMON'
                ? 'bg-secondary text-white shadow-lg shadow-secondary/20'
                : 'text-dim hover:text-white opacity-50 cursor-not-allowed',
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
              {!userId && <PromptCard message="Enter a user id to load your personalized feed." />}

              {userId && !loading && articles.length === 0 && !error && (
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
