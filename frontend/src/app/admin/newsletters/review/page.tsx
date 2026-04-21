'use client';

// Editorial Review (HITL).
//
// Driven by URL query params: ?user_id=...&mode=fast|polished. We generate the
// draft on mount and render the returned HTML in the email frame. Approve and
// Reject actions are intentionally surfaced but disabled — neither
// /admin/newsletters/{id}/approve nor /reject exist on the backend yet.
// Hovering the buttons explains why; the rest of the page is fully functional.

import {
  ArrowLeft,
  CheckCircle2,
  Loader2,
  RefreshCcw,
  Send,
  Sparkles,
  TriangleAlert,
  XCircle,
} from 'lucide-react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Suspense, useCallback, useEffect, useState } from 'react';

import { PageWrapper } from '@/components/PageWrapper';
import {
  ApiError,
  generateB2CNewsletter,
  type B2CNewsletterResponse,
  type NewsletterExecutionMode,
} from '@/lib/api';

export default function NewsletterReviewPage() {
  // Suspense wraps useSearchParams per Next.js 13+ requirement (the hook
  // suspends during static generation otherwise).
  return (
    <Suspense fallback={<PageWrapper><Loader2 className="w-5 h-5 animate-spin" /></PageWrapper>}>
      <ReviewPageInner />
    </Suspense>
  );
}

function ReviewPageInner() {
  const params = useSearchParams();
  const userId = params.get('user_id') ?? '';
  const mode = (params.get('mode') as NewsletterExecutionMode) || 'polished';

  const [draft, setDraft] = useState<B2CNewsletterResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = useCallback(async (signal?: AbortSignal) => {
    if (!userId) return;
    setLoading(true);
    setError(null);
    try {
      // The B2C agent ignores AbortSignal (it's server-side); we still pass
      // one so React's cleanup can ignore the late response on unmount.
      const response = await generateB2CNewsletter({ user_id: userId, execution_mode: mode }, signal);
      setDraft(response);
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      setError(
        err instanceof ApiError
          ? `${err.status}: ${err.detail ?? err.message}`
          : (err as Error).message,
      );
    } finally {
      setLoading(false);
    }
  }, [userId, mode]);

  useEffect(() => {
    const controller = new AbortController();
    generate(controller.signal);
    return () => controller.abort();
  }, [generate]);

  return (
    <PageWrapper>
      <div className="space-y-8 pb-20">
        <header className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-4">
            <Link
              href="/admin/newsletters"
              className="p-2.5 glass rounded-xl border border-white/5 hover:bg-white/5 transition-all"
            >
              <ArrowLeft className="w-5 h-5 text-dim" />
            </Link>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Editorial Review</h1>
              <p className="text-dim text-sm italic">
                {userId
                  ? `Draft for ${userId} · mode: ${mode}`
                  : 'No user_id supplied — open from the queue page.'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              disabled
              title="Reject endpoint not implemented yet (POST /admin/newsletters/{id}/reject)"
              className="px-5 py-2.5 glass border border-red-500/20 text-red-500 rounded-xl text-sm font-bold transition-all flex items-center gap-2 opacity-40 cursor-not-allowed"
            >
              <XCircle className="w-4 h-4" /> Reject
            </button>
            <button
              type="button"
              onClick={() => generate()}
              disabled={loading || !userId}
              className="px-5 py-2.5 glass border border-primary/20 text-primary rounded-xl text-sm font-bold hover:bg-primary/5 disabled:opacity-40 disabled:cursor-not-allowed transition-all flex items-center gap-2"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCcw className="w-4 h-4" />
              )}
              Regenerate
            </button>
            <button
              type="button"
              disabled
              title="Approve & dispatch endpoint not implemented yet (POST /admin/newsletters/{id}/approve)"
              className="px-8 py-2.5 bg-primary text-primary-foreground rounded-xl text-sm font-black uppercase tracking-widest opacity-40 cursor-not-allowed flex items-center gap-2"
            >
              <Send className="w-4 h-4" /> Approve &amp; Dispatch
            </button>
          </div>
        </header>

        {error && (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-6 flex items-start gap-3">
            <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <p className="text-sm text-rose-200">{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          <div className="lg:col-span-1 space-y-6">
            <div className="glass rounded-[2rem] p-8 border border-white/5 space-y-6">
              <h3 className="text-xs font-black uppercase tracking-widest text-secondary flex items-center gap-2">
                <Sparkles className="w-4 h-4" />
                Agent Reasoning
              </h3>
              <p className="text-sm text-dim leading-relaxed">
                {draft
                  ? `Status: ${draft.status}. Mode: ${mode}. The execution path below shows which LangGraph nodes ran for this draft.`
                  : 'Awaiting first generation.'}
              </p>
              <div className="pt-4 space-y-2 border-t border-white/5">
                <p className="text-xs uppercase tracking-widest text-dim font-bold">
                  Execution Path
                </p>
                {draft?.execution_path_taken?.length ? (
                  <ol className="text-xs space-y-1 font-mono text-dim">
                    {draft.execution_path_taken.map((node, i) => (
                      <li key={i} className="flex items-center gap-2">
                        <span className="text-primary">{(i + 1).toString().padStart(2, '0')}</span>
                        {node}
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="text-xs text-dim italic">—</p>
                )}
              </div>
            </div>

            <div className="glass rounded-[2rem] p-8 border border-white/5 space-y-3">
              <h3 className="text-xs font-black uppercase tracking-widest text-dim">
                HITL Actions
              </h3>
              <ul className="space-y-2 text-xs text-dim">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-3 h-3 text-emerald-500 mt-0.5 shrink-0" />
                  Generate &amp; Regenerate are wired to <code className="font-mono bg-white/5 px-1 rounded">POST /api/v1/newsletter/b2c</code>.
                </li>
                <li className="flex items-start gap-2">
                  <TriangleAlert className="w-3 h-3 text-amber-400 mt-0.5 shrink-0" />
                  Approve &amp; Reject need new backend endpoints (Abhinav&apos;s backlog).
                </li>
              </ul>
            </div>
          </div>

          <div className="lg:col-span-3">
            <div className="glass rounded-[2.5rem] p-2 border border-white/10 shadow-2xl relative overflow-hidden">
              <div className="bg-white rounded-[2.25rem] overflow-hidden flex flex-col min-h-[600px]">
                <div className="bg-white border-b-4 border-slate-900 text-left p-12">
                  <h2 className="text-slate-900 font-black text-3xl tracking-tighter">
                    The Intelligence <span className="text-secondary">Loop</span>
                  </h2>
                  <p className="text-slate-400 text-sm font-medium mt-1 uppercase tracking-widest">
                    {new Date().toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' })}
                    {userId ? ` • Curated for ${userId}` : ''}
                  </p>
                </div>

                <div className="flex-1 p-12 text-slate-800">
                  {loading && (
                    <div className="flex items-center gap-3 text-slate-500">
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Generating draft for {userId}…
                    </div>
                  )}
                  {!loading && !draft && !error && (
                    <p className="text-slate-500 italic">
                      No draft yet. Use the controls above to generate one.
                    </p>
                  )}
                  {/* Backend returns sanitised HTML from a controlled prompt — safe
                      to render. If we ever accept untrusted sources, sanitise here. */}
                  {draft && (
                    <article
                      className="newsletter-preview prose max-w-none"
                      dangerouslySetInnerHTML={{ __html: draft.html_content }}
                    />
                  )}
                </div>

                <div className="bg-slate-50 p-12 text-center text-slate-400 text-[10px] font-bold">
                  STAY CURATED. STAY INFORMED. CURATEAI 2026.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}
