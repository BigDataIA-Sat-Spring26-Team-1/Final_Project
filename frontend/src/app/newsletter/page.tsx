'use client';

// Newsletter generation page. Idempotent per (user, today): if a draft for
// today already exists in Snowflake we fetch + render it and disable the
// generate button. Regeneration is not offered — users go to /user/newsletters
// for the historical archive.

import {
  Loader2,
  Mail,
  Plus,
  Sparkles,
  TriangleAlert,
  Zap,
} from 'lucide-react';
import { useEffect, useState } from 'react';

import { PageWrapper } from '@/components/PageWrapper';
import {
  ApiError,
  generateB2CNewsletter,
  getNewsletterArchive,
  type B2CNewsletterResponse,
  type NewsletterExecutionMode,
} from '@/lib/api';
import { cn } from '@/lib/utils';

const STORAGE_KEY = 'curateai:user_id';

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function NewsletterPage() {
  const [userId, setUserId] = useState('');
  const [mode, setMode] = useState<NewsletterExecutionMode>('polished');
  const [draft, setDraft] = useState<B2CNewsletterResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const saved = typeof window !== 'undefined' ? sessionStorage.getItem(STORAGE_KEY) : null;
    if (saved) setUserId(saved);
  }, []);

  // Whenever the user id changes, look up today's existing draft before
  // offering to generate. Avoids accidental double-runs and matches the
  // backend's idempotent contract.
  useEffect(() => {
    const trimmed = userId.trim();
    if (!trimmed) {
      setDraft(null);
      return;
    }
    const controller = new AbortController();
    setChecking(true);
    setError(null);
    setDraft(null);
    (async () => {
      try {
        const res = await getNewsletterArchive(trimmed, todayIso(), 1, controller.signal);
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
    })();
    return () => controller.abort();
  }, [userId]);

  const handleGenerate = async () => {
    const trimmed = userId.trim();
    if (!trimmed) {
      setError('Enter a user id before generating.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await generateB2CNewsletter({
        user_id: trimmed,
        execution_mode: mode,
      });
      setDraft(response);
      sessionStorage.setItem(STORAGE_KEY, trimmed);
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
  const generateDisabled = loading || checking || hasToday || !userId.trim();

  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between gap-6 flex-wrap">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">Agentic Newsletters</h1>
            <p className="text-muted-foreground text-lg">
              One newsletter per user per day. If today&apos;s draft exists we show it directly.
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
                <Loader2 className="w-5 h-5 animate-spin" /> Generating...
              </>
            ) : hasToday ? (
              <>
                <Mail className="w-5 h-5" /> Today&apos;s Draft Ready
              </>
            ) : (
              <>
                <Plus className="w-5 h-5" /> Generate Today&apos;s Draft
              </>
            )}
          </button>
        </header>

        {/* Generation form — user_id + execution mode toggle. */}
        <div className="glass rounded-3xl p-8 border border-white/5 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <label className="space-y-2">
              <span className="text-xs uppercase tracking-widest text-dim font-bold">User ID</span>
              <input
                type="text"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                placeholder="e.g. user-demo-001"
                className="w-full rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm outline-none focus:border-primary/40 font-mono"
              />
            </label>
            <div className="space-y-2">
              <span className="text-xs uppercase tracking-widest text-dim font-bold">Execution Mode</span>
              <div className="grid grid-cols-2 gap-2">
                <ModeOption
                  label="Fast"
                  detail="Skips editor review"
                  icon={Zap}
                  active={mode === 'fast'}
                  disabled={hasToday}
                  onClick={() => setMode('fast')}
                />
                <ModeOption
                  label="Polished"
                  detail="Full fact-check loop"
                  icon={Sparkles}
                  active={mode === 'polished'}
                  disabled={hasToday}
                  onClick={() => setMode('polished')}
                />
              </div>
            </div>
          </div>
        </div>

        {error && (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-6 flex items-start gap-3">
            <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <p className="text-sm text-rose-200">{error}</p>
          </div>
        )}

        {checking ? (
          <div className="glass rounded-3xl p-10 border border-dashed border-white/20 text-center space-y-4">
            <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto" />
            <p className="text-dim">Checking for today&apos;s draft...</p>
          </div>
        ) : draft ? (
          <NewsletterPreview draft={draft} />
        ) : !loading ? (
          <div className="glass rounded-3xl p-10 border border-dashed border-white/20 text-center space-y-4">
            <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-6">
              <Mail className="w-8 h-8 text-muted-foreground" />
            </div>
            <h3 className="text-xl font-bold">No draft for today yet</h3>
            <p className="text-muted-foreground max-w-sm mx-auto">
              Enter a user id and hit Generate to run the newsletter agent. Fast mode returns in
              seconds; Polished takes longer but includes the fact-check loop.
            </p>
          </div>
        ) : null}
      </div>
    </PageWrapper>
  );
}

function ModeOption({
  label,
  detail,
  icon: Icon,
  active,
  disabled,
  onClick,
}: {
  label: string;
  detail: string;
  icon: React.ComponentType<{ className?: string }>;
  active: boolean;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'rounded-xl border p-3 text-left flex items-center gap-3 transition-all disabled:opacity-40 disabled:cursor-not-allowed',
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
  const generatedAt = draft.generated_at
    ? new Date(draft.generated_at).toLocaleString()
    : null;
  return (
    <div className="glass rounded-3xl p-8 border border-white/5 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h3 className="text-xl font-bold flex items-center gap-2">
          <Mail className="w-5 h-5 text-primary" />
          {draft.already_generated ? "Today's Newsletter" : 'Draft Preview'}
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
          {generatedAt && (
            <span className="text-[10px] text-dim">Generated {generatedAt}</span>
          )}
          {draft.execution_path_taken?.length > 0 && (
            <span className="text-[10px] font-mono uppercase tracking-widest text-dim">
              {draft.execution_path_taken.join(' → ')}
            </span>
          )}
        </div>
      </div>

      {/* The backend returns sanitised HTML from a trusted LLM prompt — render it
          directly. If we ever accept untrusted sources, sanitise with DOMPurify. */}
      <article
        className="newsletter-preview rounded-2xl border border-white/10 bg-white/[0.02] p-8 max-h-[70vh] overflow-auto prose prose-invert max-w-none"
        dangerouslySetInnerHTML={{ __html: draft.html_content }}
      />
    </div>
  );
}
