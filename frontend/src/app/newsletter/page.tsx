'use client';

// Newsletter page for the logged-in user. Auto-checks Snowflake for today's
// draft on mount. If it exists, it renders immediately. If not, one click
// runs the agent — the backend emails the newsletter after generating.
// Regeneration is not allowed once today's copy is stored.

import { Loader2, Mail, Plus, Sparkles, TriangleAlert, Zap } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { PageWrapper } from '@/components/PageWrapper';
import { useAuth } from '@/components/AuthProvider';
import {
  ApiError,
  generateB2CNewsletter,
  getNewsletterArchive,
  type B2CNewsletterResponse,
  type NewsletterExecutionMode,
} from '@/lib/api';
import { cn } from '@/lib/utils';

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function NewsletterPage() {
  const { user } = useAuth();
  const userId = user?.id ?? '';

  const [mode, setMode] = useState<NewsletterExecutionMode>('polished');
  const [draft, setDraft] = useState<B2CNewsletterResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hydrateFromArchive = useCallback(
    async (id: string, signal?: AbortSignal) => {
      setChecking(true);
      setError(null);
      setDraft(null);
      try {
        const res = await getNewsletterArchive(id, todayIso(), 1, signal);
        const today = res.results[0];
        if (today && (today.final_content || today.draft_content)) {
          setDraft({
            status: today.status || 'PUBLISHED',
            html_content: today.final_content || today.draft_content || '',
            execution_path_taken: today.execution_path_taken
              ? today.execution_path_taken.split(',').filter(Boolean)
              : [],
            already_generated: true,
            generated_at: today.generated_at,
            edition_date: today.edition_date,
          });
        }
      } catch (err) {
        if ((err as Error).name === 'AbortError') return;
        setError(
          err instanceof ApiError
            ? `${err.status}: ${err.detail ?? err.message}`
            : (err as Error).message,
        );
      } finally {
        setChecking(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (!userId) return;
    const controller = new AbortController();
    hydrateFromArchive(userId, controller.signal);
    return () => controller.abort();
  }, [userId, hydrateFromArchive]);

  const handleGenerate = async () => {
    if (!userId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await generateB2CNewsletter({
        user_id: userId,
        execution_mode: mode,
      });
      setDraft(response);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? `${err.status}: ${err.detail ?? err.message}`
          : (err as Error).message,
      );
    } finally {
      setLoading(false);
    }
  };

  const hasToday = Boolean(draft && draft.already_generated);
  const generateDisabled = loading || checking || hasToday || !userId;

  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between gap-6 flex-wrap">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">Today&apos;s Newsletter</h1>
            <p className="text-muted-foreground text-lg">
              Your personalized tech deck for {todayIso()}. One draft per day, auto-emailed to
              your inbox when it&apos;s ready.
            </p>
          </div>
          <button
            onClick={handleGenerate}
            disabled={generateDisabled}
            title={hasToday ? "Today's newsletter already exists." : undefined}
            className="flex items-center gap-2 bg-primary hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed text-primary-foreground px-6 py-3 rounded-2xl text-sm font-bold transition-all shadow-lg shadow-primary/20"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" /> Generating &amp; emailing…
              </>
            ) : hasToday ? (
              <>
                <Mail className="w-5 h-5" /> Today&apos;s Draft Ready
              </>
            ) : (
              <>
                <Plus className="w-5 h-5" /> Generate &amp; Email My Draft
              </>
            )}
          </button>
        </header>

        {/* Execution-mode toggle. Locked once today's draft exists. */}
        {!hasToday && (
          <div className="glass rounded-3xl p-6 border border-white/5 flex items-center justify-between gap-6 flex-wrap">
            <div>
              <p className="text-sm font-bold">Agent execution mode</p>
              <p className="text-xs text-dim">
                Polished runs the full writer + editor loop. Fast skips the editor for quicker turnarounds.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2 min-w-[320px]">
              <ModeOption
                label="Fast"
                detail="Skips editor review"
                icon={Zap}
                active={mode === 'fast'}
                onClick={() => setMode('fast')}
              />
              <ModeOption
                label="Polished"
                detail="Full fact-check loop"
                icon={Sparkles}
                active={mode === 'polished'}
                onClick={() => setMode('polished')}
              />
            </div>
          </div>
        )}

        {error && (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-6 flex items-start gap-3">
            <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <p className="text-sm text-rose-200">{error}</p>
          </div>
        )}

        {checking ? (
          <div className="glass rounded-3xl p-10 border border-dashed border-white/20 text-center space-y-4">
            <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto" />
            <p className="text-dim">Loading today&apos;s newsletter…</p>
          </div>
        ) : loading ? (
          <div className="glass rounded-3xl p-10 border border-dashed border-white/20 text-center space-y-4">
            <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto" />
            <p className="text-dim">
              Agent is assembling your deck. This takes ~30–60s in Polished mode.
            </p>
          </div>
        ) : draft ? (
          <NewsletterPreview draft={draft} />
        ) : (
          <div className="glass rounded-3xl p-10 border border-dashed border-white/20 text-center space-y-4">
            <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-6">
              <Mail className="w-8 h-8 text-muted-foreground" />
            </div>
            <h3 className="text-xl font-bold">No draft for today yet</h3>
            <p className="text-muted-foreground max-w-sm mx-auto">
              Hit <em>Generate &amp; Email My Draft</em> — it runs the agent, stores the result,
              and emails the deck to the address on your account.
            </p>
          </div>
        )}
      </div>
    </PageWrapper>
  );
}

function ModeOption({
  label,
  detail,
  icon: Icon,
  active,
  onClick,
}: {
  label: string;
  detail: string;
  icon: React.ComponentType<{ className?: string }>;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'rounded-xl border p-3 text-left flex items-center gap-3 transition-all',
        active
          ? 'border-primary/40 bg-primary/5 text-white'
          : 'border-white/10 bg-white/[0.02] text-dim hover:border-white/20 hover:text-white',
      )}
    >
      <Icon className={cn('w-5 h-5', active ? 'text-primary' : 'text-dim')} />
      <div>
        <p className="text-sm font-bold">{label}</p>
        <p className="text-[10px] text-muted-foreground">{detail}</p>
      </div>
    </button>
  );
}

function NewsletterPreview({ draft }: { draft: B2CNewsletterResponse }) {
  const generatedAt = draft.generated_at ? new Date(draft.generated_at).toLocaleString() : null;
  return (
    <div className="glass rounded-3xl p-8 border border-white/5 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h3 className="text-xl font-bold flex items-center gap-2">
          <Mail className="w-5 h-5 text-primary" />
          Today&apos;s Newsletter
        </h3>
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={cn(
              'px-3 py-1 rounded-full text-[10px] font-black tracking-widest uppercase border',
              draft.status === 'SUCCESS' || draft.status === 'APPROVED' || draft.status === 'PUBLISHED'
                ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                : 'bg-amber-500/10 text-amber-500 border-amber-500/20',
            )}
          >
            {draft.status}
          </span>
          {draft.edition_date && (
            <span className="text-[10px] font-mono uppercase tracking-widest text-dim">
              {draft.edition_date}
            </span>
          )}
          {generatedAt && <span className="text-[10px] text-dim">Generated {generatedAt}</span>}
        </div>
      </div>

      <article
        className="newsletter-preview rounded-2xl border border-white/10 bg-white/[0.02] p-8 max-h-[70vh] overflow-auto prose prose-invert max-w-none"
        dangerouslySetInnerHTML={{ __html: draft.html_content }}
      />
    </div>
  );
}
