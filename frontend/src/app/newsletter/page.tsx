'use client';

// Newsletter generation page. Hits the B2C LangGraph and renders the returned
// HTML in a preview frame. Fast mode skips the editor loop (cheaper, faster);
// polished mode runs the full write → review → revise cycle.
//
// NOTE: A listing of past drafts needs a GET endpoint that doesn't exist yet
// (backlog: /api/v1/newsletter/drafts). Until that lands we render just the
// freshly-generated draft plus a hint.

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
  type B2CNewsletterResponse,
  type NewsletterExecutionMode,
} from '@/lib/api';
import { cn } from '@/lib/utils';

const STORAGE_KEY = 'curateai:user_id';

export default function NewsletterPage() {
  const [userId, setUserId] = useState('');
  const [mode, setMode] = useState<NewsletterExecutionMode>('polished');
  const [draft, setDraft] = useState<B2CNewsletterResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const saved = typeof window !== 'undefined' ? sessionStorage.getItem(STORAGE_KEY) : null;
    if (saved) setUserId(saved);
  }, []);

  const handleGenerate = async () => {
    if (!userId.trim()) {
      setError('Enter a user id before generating.');
      return;
    }
    setLoading(true);
    setError(null);
    setDraft(null);
    try {
      const response = await generateB2CNewsletter({
        user_id: userId.trim(),
        execution_mode: mode,
      });
      setDraft(response);
      sessionStorage.setItem(STORAGE_KEY, userId.trim());
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

  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between gap-6 flex-wrap">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">Agentic Newsletters</h1>
            <p className="text-muted-foreground text-lg">
              Trigger the B2C LangGraph and preview the rendered HTML.
            </p>
          </div>
          <button
            onClick={handleGenerate}
            disabled={loading || !userId}
            className="flex items-center gap-2 bg-primary hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed text-primary-foreground px-6 py-3 rounded-2xl text-sm font-bold transition-all shadow-lg shadow-primary/20"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" /> Generating...
              </>
            ) : (
              <>
                <Plus className="w-5 h-5" /> Generate New Draft
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
          </div>
        </div>

        {error && (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-6 flex items-start gap-3">
            <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <p className="text-sm text-rose-200">{error}</p>
          </div>
        )}

        {draft ? (
          <NewsletterPreview draft={draft} />
        ) : !loading ? (
          <div className="glass rounded-3xl p-10 border border-dashed border-white/20 text-center space-y-4">
            <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-6">
              <Mail className="w-8 h-8 text-muted-foreground" />
            </div>
            <h3 className="text-xl font-bold">No draft generated yet</h3>
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
  return (
    <div className="glass rounded-3xl p-8 border border-white/5 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h3 className="text-xl font-bold flex items-center gap-2">
          <Mail className="w-5 h-5 text-primary" />
          Draft Preview
        </h3>
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={cn(
              'px-3 py-1 rounded-full text-[10px] font-black tracking-widest uppercase border',
              draft.status === 'SUCCESS' || draft.status === 'APPROVED'
                ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                : 'bg-amber-500/10 text-amber-500 border-amber-500/20',
            )}
          >
            {draft.status}
          </span>
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
