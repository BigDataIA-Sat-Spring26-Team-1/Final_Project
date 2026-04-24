'use client';

// Global Archive — separate B2C + B2B surfaces driven by admin archive
// endpoints. Tab 1 (B2C) lets admins pick any user and read their latest +
// past newsletters. Tab 2 (B2B) does the same for companies with content
// briefs. Both tabs share a simple layout: selector → archive list → viewer.

import {
  Calendar,
  CheckCircle2,
  FileText,
  Loader2,
  Mail,
  Newspaper,
  Send,
  TriangleAlert,
  Users,
} from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';

import { CompanySwitcher } from '@/components/CompanySwitcher';
import { PageWrapper } from '@/components/PageWrapper';
import { Spinner } from '@/components/Spinner';
import { UserSwitcher } from '@/components/UserSwitcher';
import {
  ApiError,
  getBriefArchive,
  getNewsletterArchive,
  sendNewsletterEmail,
  sendNewslettersBatch,
  type BriefArchiveItem,
  type NewsletterArchiveItem,
  type NewsletterSendResponse,
} from '@/lib/api';
import { cn } from '@/lib/utils';

type Mode = 'B2C' | 'B2B';

export default function GlobalArchivePage() {
  const [mode, setMode] = useState<Mode>('B2C');

  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="space-y-3">
          <h1 className="text-4xl font-bold tracking-tight">Global Archive</h1>
          <p className="text-dim text-lg">
            Browse the full archive of newsletters and briefs, per tenant.
          </p>
        </header>

        <div className="flex items-center gap-1 p-1 glass rounded-2xl w-fit border border-white/5">
          <TabButton
            active={mode === 'B2C'}
            onClick={() => setMode('B2C')}
            icon={Users}
            label="B2C User Newsletters"
          />
          <TabButton
            active={mode === 'B2B'}
            onClick={() => setMode('B2B')}
            icon={FileText}
            label="B2B Company Briefs"
          />
        </div>

        {mode === 'B2C' ? <B2CArchive /> : <B2BArchive />}
      </div>
    </PageWrapper>
  );
}

function TabButton({
  active,
  onClick,
  icon: Icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'px-6 py-2 rounded-xl text-sm font-bold transition-all flex items-center gap-2',
        active
          ? 'bg-secondary text-white shadow-lg shadow-secondary/20'
          : 'text-dim hover:text-white',
      )}
    >
      <Icon className="w-4 h-4" />
      {label}
    </button>
  );
}

// Defensive client-side strip: older rows in Snowflake still carry a
// ```html ... ``` Markdown fence around the HTML body because the B2C
// writer node used to emit one. The agent now strips on write, but the
// admin archive has to cope with the historical data too.
const HTML_FENCE_RE = /^\s*```(?:html)?\s*\n?([\s\S]*?)\n?\s*```\s*$/i;
function stripHtmlFence(body: string): string {
  const m = body.match(HTML_FENCE_RE);
  return (m ? m[1] : body).trim();
}

function B2CArchive() {
  const [userId, setUserId] = useState<string>('');
  const [items, setItems] = useState<NewsletterArchiveItem[]>([]);
  const [selected, setSelected] = useState<NewsletterArchiveItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  // `sending[editionDate]` tracks the in-flight send per row so two quick
  // clicks don't double-fire. Cleared once the response lands.
  const [sending, setSending] = useState<Record<string, boolean>>({});
  const [sendNotice, setSendNotice] = useState<string | null>(null);
  const [batchSending, setBatchSending] = useState(false);

  const load = useCallback(async (id: string, signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    setItems([]);
    setSelected(null);
    try {
      const res = await getNewsletterArchive(id, undefined, 50, signal);
      setItems(res.results);
      setSelected(res.results[0] ?? null);
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
  }, []);

  useEffect(() => {
    if (!userId) return;
    const controller = new AbortController();
    load(userId, controller.signal);
    return () => controller.abort();
  }, [userId, load]);

  // Render the selected newsletter inside a sandboxed iframe so the
  // stored <!DOCTYPE html><html>… doesn't collide with the page chrome
  // and so any stray styles in the archived body stay isolated.
  useEffect(() => {
    const body = selected?.final_content || selected?.draft_content;
    if (!body || !iframeRef.current) return;
    const doc = iframeRef.current.contentDocument;
    if (!doc) return;
    doc.open();
    doc.write(stripHtmlFence(body));
    doc.close();
  }, [selected]);

  const formatResult = (res: NewsletterSendResponse): string => {
    if (res.status === 'SENT') return `Sent to ${res.recipient ?? 'recipient'}.`;
    if (res.status === 'ALREADY_SENT') return `Already delivered on ${res.sent_at ?? 'an earlier attempt'}.`;
    if (res.status === 'MAILER_DISABLED') return 'Mailer is disabled — set MAILERSEND_API_KEY to enable.';
    if (res.status === 'NO_RECIPIENT') return 'User has no email address on file.';
    if (res.status === 'USER_NOT_FOUND') return 'User id not found.';
    return res.detail ? `Send failed: ${res.detail}` : 'Send failed.';
  };

  const handleSend = async (item: NewsletterArchiveItem) => {
    setSending((s) => ({ ...s, [item.edition_date]: true }));
    setSendNotice(null);
    try {
      const res = await sendNewsletterEmail(item.user_id, item.edition_date);
      setSendNotice(formatResult(res));
      await load(item.user_id);
    } catch (err) {
      setSendNotice(err instanceof Error ? `Send failed: ${err.message}` : 'Send failed.');
    } finally {
      setSending((s) => {
        const copy = { ...s };
        delete copy[item.edition_date];
        return copy;
      });
    }
  };

  const handleBatchToday = async () => {
    setBatchSending(true);
    setSendNotice(null);
    try {
      const today = new Date().toISOString().slice(0, 10);
      const res = await sendNewslettersBatch(today);
      setSendNotice(
        `Batch for ${today}: attempted ${res.attempted}, sent ${res.sent ?? 0}, skipped ${res.skipped ?? 0}, failed ${res.failed ?? 0}.`,
      );
      if (userId) await load(userId);
    } catch (err) {
      setSendNotice(err instanceof Error ? `Batch failed: ${err.message}` : 'Batch failed.');
    } finally {
      setBatchSending(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="glass rounded-3xl p-6 border border-white/5 flex items-center gap-4 flex-wrap relative z-[60] overflow-visible">
        <Mail className="w-5 h-5 text-secondary" />
        <span className="text-sm font-bold">Select a user</span>
        <UserSwitcher currentUserId={userId || null} onSelect={(id) => setUserId(id)} />
        <div className="flex-1" />
        <button
          type="button"
          onClick={handleBatchToday}
          disabled={batchSending}
          title="Dispatch today's newsletter via email to every user whose row has not yet shipped."
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-primary/10 border border-primary/30 text-primary text-xs font-bold uppercase tracking-widest hover:bg-primary/20 disabled:opacity-40 disabled:cursor-not-allowed transition"
        >
          {batchSending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          Send Today to All Pending
        </button>
      </div>

      {sendNotice && (
        <div className="rounded-2xl border border-blue-500/20 bg-blue-500/5 p-4 text-sm text-blue-200">
          {sendNotice}
        </div>
      )}

      {error && (
        <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-6 flex items-start gap-3">
          <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <p className="text-sm text-rose-200">{error}</p>
        </div>
      )}

      {!userId ? (
        <div className="glass rounded-3xl p-10 border border-dashed border-white/20 text-center text-dim">
          Pick a user to load their newsletter history.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <aside className="glass rounded-3xl border border-white/5 p-6 space-y-3 h-fit">
            <h3 className="text-xs font-black uppercase tracking-widest text-dim flex items-center gap-2">
              <Calendar className="w-4 h-4" /> Editions
            </h3>
            {loading ? (
              <Spinner label="Loading archive" />
            ) : items.length === 0 ? (
              <p className="text-sm text-dim italic">No newsletters stored for this user yet.</p>
            ) : (
              <ul className="space-y-2">
                {items.map((n) => {
                  const isSending = Boolean(sending[n.edition_date]);
                  const alreadySent = Boolean(n.sent_at);
                  return (
                    <li key={n.id}>
                      {/* Single card per edition — the edition summary and
                          the send action share one visual row so the list
                          reads like distinct dates rather than a dup-card
                          per row. */}
                      <div
                        className={cn(
                          'rounded-xl border transition',
                          selected?.id === n.id
                            ? 'border-primary/30 bg-primary/10'
                            : 'border-white/10 bg-white/[0.02] hover:bg-white/5',
                        )}
                      >
                        <button
                          onClick={() => setSelected(n)}
                          className="w-full text-left px-3 pt-3 pb-2"
                        >
                          <p className="font-mono text-xs text-white">{n.edition_date}</p>
                          <p className="text-[10px] uppercase tracking-widest text-dim mt-0.5">
                            {n.status}
                          </p>
                          {alreadySent ? (
                            <p className="text-[10px] text-emerald-400 mt-1 flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3" />
                              sent {new Date(n.sent_at!).toLocaleString()}
                            </p>
                          ) : n.delivery_status === 'FAILED' ? (
                            <p className="text-[10px] text-rose-400 mt-1">
                              last attempt failed
                            </p>
                          ) : null}
                        </button>
                        {!alreadySent && (
                          <div className="px-3 pb-3">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleSend(n);
                              }}
                              disabled={isSending}
                              title="Send this edition via email."
                              className="w-full inline-flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-lg text-[10px] uppercase tracking-widest font-bold border border-white/10 hover:border-primary/40 hover:text-primary disabled:opacity-40 disabled:cursor-not-allowed transition"
                            >
                              {isSending ? (
                                <>
                                  <Loader2 className="w-3 h-3 animate-spin" /> Sending…
                                </>
                              ) : (
                                <>
                                  <Send className="w-3 h-3" /> Send Email
                                </>
                              )}
                            </button>
                          </div>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </aside>

          <div className="lg:col-span-3 glass rounded-3xl border border-white/5 p-8">
            {loading && !selected ? (
              <Spinner label="Loading newsletter" />
            ) : !selected ? (
              <div className="flex flex-col items-center justify-center py-12 text-dim">
                <Newspaper className="w-12 h-12 mb-4" />
                <p>Pick an edition on the left.</p>
              </div>
            ) : selected.final_content || selected.draft_content ? (
              // Sandboxed iframe — stored body starts with <!DOCTYPE html>
              // which would be invalid nested inside an <article>. The
              // iframe also isolates the newsletter's own styles from the
              // page chrome, and any stray ```html Markdown fence on
              // legacy rows is stripped before the write (see the useEffect
              // that drives this ref).
              <iframe
                ref={iframeRef}
                title="Newsletter preview"
                className="w-full rounded-2xl border border-white/10 bg-slate-900"
                style={{ height: '70vh' }}
              />
            ) : (
              <p className="text-dim italic">No content stored for this edition.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function B2BArchive() {
  const [companyId, setCompanyId] = useState<string>('');
  const [items, setItems] = useState<BriefArchiveItem[]>([]);
  const [selected, setSelected] = useState<BriefArchiveItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (id: string, signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    setItems([]);
    setSelected(null);
    try {
      const res = await getBriefArchive(id, undefined, 50, signal);
      setItems(res.results);
      setSelected(res.results[0] ?? null);
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
  }, []);

  useEffect(() => {
    if (!companyId) return;
    const controller = new AbortController();
    load(companyId, controller.signal);
    return () => controller.abort();
  }, [companyId, load]);

  return (
    <div className="space-y-6">
      <div className="glass rounded-3xl p-6 border border-white/5 flex items-center gap-4 flex-wrap relative z-[60] overflow-visible">
        <FileText className="w-5 h-5 text-secondary" />
        <span className="text-sm font-bold">Select a company</span>
        <CompanySwitcher currentCompanyId={companyId || null} onSelect={(id) => setCompanyId(id)} />
      </div>

      {error && (
        <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-6 flex items-start gap-3">
          <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <p className="text-sm text-rose-200">{error}</p>
        </div>
      )}

      {!companyId ? (
        <div className="glass rounded-3xl p-10 border border-dashed border-white/20 text-center text-dim">
          Pick a company to load its brief history.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <aside className="glass rounded-3xl border border-white/5 p-6 space-y-3 h-fit">
            <h3 className="text-xs font-black uppercase tracking-widest text-dim flex items-center gap-2">
              <Calendar className="w-4 h-4" /> Briefs
            </h3>
            {loading ? (
              <Spinner label="Loading archive" />
            ) : items.length === 0 ? (
              <p className="text-sm text-dim italic">No briefs stored for this company yet.</p>
            ) : (
              <ul className="space-y-2">
                {items.map((b) => (
                  <li key={b.id}>
                    <button
                      onClick={() => setSelected(b)}
                      className={cn(
                        'w-full text-left px-3 py-2 rounded-xl text-sm transition',
                        selected?.id === b.id
                          ? 'bg-primary/10 border border-primary/20 text-white'
                          : 'hover:bg-white/5 text-dim',
                      )}
                    >
                      <p className="font-mono text-xs">{b.brief_date}</p>
                      {b.urgency_tier && (
                        <p className="text-[10px] uppercase tracking-widest text-dim mt-0.5">
                          {b.urgency_tier.replace(/_/g, ' ')}
                        </p>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </aside>

          <div className="lg:col-span-3 glass rounded-3xl border border-white/5 p-8">
            {loading && !selected ? (
              <Spinner label="Loading brief" />
            ) : !selected ? (
              <div className="flex flex-col items-center justify-center py-12 text-dim">
                <FileText className="w-12 h-12 mb-4" />
                <p>Pick a brief on the left.</p>
              </div>
            ) : selected.brief_content ? (
              <pre className="whitespace-pre-wrap text-sm leading-relaxed text-white/90 font-mono bg-white/[0.02] rounded-2xl border border-white/10 p-6 max-h-[70vh] overflow-auto">
                {selected.brief_content}
              </pre>
            ) : (
              <p className="text-dim italic">No content stored for this brief.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
